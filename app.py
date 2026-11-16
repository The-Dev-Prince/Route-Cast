"""Local web/API entry point for the RouteCast UI."""

import json
import math
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

import requests

from combination import CombinationAgent
from route import RoutingAgent
from weather import WeatherAgent, get_weather


ROOT = Path(__file__).resolve().parent
UI_FILE = ROOT / "routecast_multi_agent_traffic_weather_route_optimizer.html"


def geocode_location(query: str) -> Dict[str, Any]:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise ValueError(
            "Location not in the built-in city list. Set OPENWEATHER_API_KEY to search other locations."
        )

    response = requests.get(
        "https://api.openweathermap.org/geo/1.0/direct",
        params={"q": query, "limit": 1, "appid": api_key},
        timeout=10,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise ValueError(f'Could not find location "{query}". Try a city and state.')

    item = results[0]
    return {
        "name": f'{item["name"]}, {item.get("state") or item["country"]}',
        "lat": item["lat"],
        "lon": item["lon"],
    }


def _validate_location(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} location is required.")
    name = value.get("name")
    lat = value.get("lat")
    lon = value.get("lon")
    if (
        not isinstance(name, str)
        or not name.strip()
        or isinstance(lat, bool)
        or not isinstance(lat, (int, float))
        or not math.isfinite(lat)
        or isinstance(lon, bool)
        or not isinstance(lon, (int, float))
        or not math.isfinite(lon)
        or not -90 <= lat <= 90
        or not -180 <= lon <= 180
    ):
        raise ValueError(f"{label} location is invalid.")
    return {"name": name.strip(), "lat": lat, "lon": lon}


def calculate_route(origin: Dict[str, Any], destination: Dict[str, Any]) -> Dict[str, Any]:
    route_data = RoutingAgent().fetch_routes(origin["name"], destination["name"])
    midpoint_lat = (origin["lat"] + destination["lat"]) / 2
    midpoint_lon = (origin["lon"] + destination["lon"]) / 2
    midpoint_raw = get_weather(midpoint_lat, midpoint_lon)
    destination_raw = get_weather(destination["lat"], destination["lon"])

    midpoint_weather = WeatherAgent.calculate_impact_vector(midpoint_raw)
    destination_weather = WeatherAgent.calculate_impact_vector(destination_raw)
    vector_keys = (
        "precipitation_score",
        "temperature_score",
        "visibility_score",
        "wind_score",
    )
    hazards = list(
        dict.fromkeys(
            hazard
            for result in (midpoint_weather, destination_weather)
            for hazard in result["hazards"]
            if hazard != "Clear Conditions"
        )
    )
    weather_data = {
        "status": "success",
        "weather_vector": {
            key: max(
                midpoint_weather["weather_vector"][key],
                destination_weather["weather_vector"][key],
            )
            for key in vector_keys
        },
        "hazards": hazards or ["Clear Conditions"],
        "raw_metrics": destination_weather["raw_metrics"],
    }

    combiner = CombinationAgent(weather_data, route_data, risk_aversion=0.6)
    combiner.train(epochs=1000)
    decision = combiner.combine_data()
    best = decision["recommended_route"]

    return {
        "origin": origin["name"],
        "destination": destination["name"],
        "best_route": best,
        "weather": {
            "hazards": weather_data["hazards"],
            "raw_metrics": weather_data["raw_metrics"],
        },
        "demo": route_data["status"] != "success"
        or bool(midpoint_raw.get("_demo"))
        or bool(destination_raw.get("_demo")),
    }


class RouteCastHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid request body.") from exc
        if length <= 0 or length > 32_768:
            raise ValueError("Request body must be between 1 byte and 32 KB.")
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = UI_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "Not found."})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/api/geocode", "/api/route"):
            self._send_json(404, {"error": "Not found."})
            return

        try:
            payload = self._read_json()
            if path == "/api/geocode":
                query = payload.get("query")
                if not isinstance(query, str) or not query.strip():
                    raise ValueError("Enter a location to search.")
                self._send_json(200, geocode_location(query.strip()))
                return

            origin = _validate_location(payload.get("origin"), "Starting")
            destination = _validate_location(payload.get("destination"), "Ending")
            if origin["lat"] == destination["lat"] and origin["lon"] == destination["lon"]:
                raise ValueError("Starting and ending locations must be different.")
            self._send_json(200, calculate_route(origin, destination))
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except requests.RequestException:
            self._send_json(
                502,
                {"error": "A data provider could not complete the request. Check API keys and connectivity."},
            )
        except KeyError:
            self._send_json(502, {"error": "A data provider returned an unexpected response."})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    host = os.getenv("ROUTECAST_HOST", "127.0.0.1")
    port = int(os.getenv("ROUTECAST_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), RouteCastHandler)
    print(f"RouteCast UI available at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping RouteCast.")
    finally:
        server.server_close()
