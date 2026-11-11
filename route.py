
"""
route.py
Routing Agent for RouteCast
Perceives the road network, traffic conditions, and candidate routes 
from the Google Maps API (or a demo mock response).
"""

import os
import requests
from typing import Dict, Any, List, Optional


class RoutingAgent:
    def __init__(self, api_key: Optional[str] = None, use_demo: bool = False):
        """
        Initializes the Routing Agent.
        :param api_key: Google Maps API key. If None, checks environment variables.
        :param use_demo: If True, forces the use of mock/demo route data without making external API calls.
        """
        self.api_key = api_key or os.getenv("AIzaSyCjZcHLk1WYBCYjL2fsjC1F806ro221UY8")
        self.use_demo = use_demo or not self.api_key
        self.base_url = "https://maps.googleapis.com/maps/api/directions/json"

    def fetch_routes(self, origin: str, destination: str) -> Dict[Any, Any]:
        """
        Fetches candidate routes between an origin and destination.
        Uses the Google Maps Directions API if configured, otherwise falls back to demo data.
        """
        if self.use_demo:
            return self._get_demo_routes(origin, destination)

        params = {
            "origin": origin,
            "destination": destination,
            "key": self.api_key,
            "alternatives": "true",
            "departure_time": "now",  # Enables traffic-dependent duration (duration_in_traffic)
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                raise ValueError(f"Google Maps API error: {data.get('status')}")

            return self._process_api_response(data)

        except Exception as e:
            print(f"Warning: Failed to reach Google Maps API ({e}). Falling back to demo route data.")
            return self._get_demo_routes(origin, destination)

    def _process_api_response(self, api_data: Dict[Any, Any]) -> Dict[str, Any]:
        """
        Parses raw Google Maps API output into structured candidate routes for the Routing Agent.
        """
        candidate_routes = []

        for idx, route in enumerate(api_data.get("routes", [])):
            leg = route["legs"][0]
            
            # Extract basic metrics
            distance_meters = leg["distance"]["value"]
            duration_normal_seconds = leg["duration"]["value"]
            
            # Traffic duration might not be present if departure_time wasn't accepted or traffic data is missing
            duration_traffic_seconds = leg.get("duration_in_traffic", leg["duration"])["value"]
            
            summary = route.get(
                "summary", 
                route.get("warnings", [f"Route Option {idx + 1}"])
            )
            if isinstance(summary, list):
                summary = ", ".join(summary)

            candidate_routes.append({
                "route_id": idx,
                "summary": summary,
                "distance_km": round(distance_meters / 1000.0, 2),
                "normal_duration_mins": round(duration_normal_seconds / 60.0, 1),
                "traffic_duration_mins": round(duration_traffic_seconds / 60.0, 1),
                "traffic_delay_mins": round(max(0, duration_traffic_seconds - duration_normal_seconds) / 60.0, 1),
                "steps": [step["html_instructions"] for step in leg.get("steps", [])]
            })

        return {
            "status": "success",
            "origin": api_data["routes"][0]["legs"][0]["start_address"],
            "destination": api_data["routes"][0]["legs"][0]["end_address"],
            "candidate_routes": candidate_routes
        }

    def _get_demo_routes(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        Provides mock route data simulating the Google Maps Demo API output 
        for testing traffic and weather integration.
        """
        return {
            "status": "success_demo",
            "origin": origin,
            "destination": destination,
            "candidate_routes": [
                {
                    "route_id": 0,
                    "summary": "I-15 N (Main Highway)",
                    "distance_km": 42.5,
                    "normal_duration_mins": 35.0,
                    "traffic_duration_mins": 52.0,
                    "traffic_delay_mins": 17.0,
                    "steps": [
                        "Head north on main corridor",
                        "Merge onto I-15 N via the ramp to Salt Lake",
                        "Take exit 305 for destination"
                    ]
                },
                {
                    "route_id": 1,
                    "summary": "State Route 89 (Canyon Alternative)",
                    "distance_km": 48.1,
                    "normal_duration_mins": 45.0,
                    "traffic_duration_mins": 48.0,
                    "traffic_delay_mins": 3.0,
                    "steps": [
                        "Take local eastbound connectors",
                        "Turn left onto State Route 89 N",
                        "Follow signs to destination bypass"
                    ]
                }
            ]
        }


if __name__ == "__main__":
    # Quick test execution using demo mode
    agent = RoutingAgent(use_demo=True)
    result = agent.fetch_routes(origin="Provo, UT", destination="Salt Lake City, UT")
    
    import json
    print(json.dumps(result, indent=2))