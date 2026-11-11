import requests


BASE_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(lat, lon, timezone="auto"):
    """Fetch current weather data for a given latitude and longitude.

    Uses Open-Meteo, a free weather API that does not require an API key.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
        "timezone": timezone,
        "forecast_days": 1,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not fetch weather data: {exc}") from exc

    current = data.get("current", {})
    return {
        "latitude": lat,
        "longitude": lon,
        "temperature_c": current.get("temperature_2m"),
        "precipitation_mm": current.get("precipitation"),
        "wind_speed_kph": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
        "timezone": data.get("timezone"),
    }


if __name__ == "__main__":
    # Example: downtown Salt Lake City
    weather = get_weather(40.7608, -111.8910)
    print(weather)
