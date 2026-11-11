import requests
from typing import Dict, Any, List


class WeatherAgent:
    """
    Weather Agent (Model-Based Reflex):
    Perceives raw weather API data, maintains internal evaluation rules,
    and returns a normalized vector dataset for the Combination Agent.
    """
    
    @staticmethod
    def calculate_impact_vector(raw_json: Dict[str, Any]) -> Dict[str, Any]:
        if not raw_json or raw_json.get("cod") != 200:
            # Fallback zero-vector if request fails
            return {
                "status": "error",
                "weather_vector": {
                    "precipitation_score": 0.0,
                    "temperature_score": 0.0,
                    "visibility_score": 0.0,
                    "wind_score": 0.0
                },
                "hazards": ["Data Unavailable"],
                "raw_metrics": {}
            }

        # --- Extract Raw Metrics ---
        weather_main = raw_json.get("weather", [{}])[0].get("main", "").lower()
        temp_f = raw_json.get("main", {}).get("temp", 70.0)
        visibility_meters = raw_json.get("visibility", 10000)
        wind_speed_mph = raw_json.get("wind", {}).get("speed", 0.0)
        rain_1h = raw_json.get("rain", {}).get("1h", 0.0)
        snow_1h = raw_json.get("snow", {}).get("1h", 0.0)

        hazards: List[str] = []

        # --- 1. Precipitation Metric Score (0.0 to 1.0) ---
        precip_score = 0.0
        if "snow" in weather_main or snow_1h > 0:
            precip_score = min(1.0, 0.4 + (snow_1h * 0.1))
            hazards.append("Snowy Road Conditions")
        elif "rain" in weather_main or rain_1h > 0:
            precip_score = min(1.0, 0.2 + (rain_1h * 0.05))
            hazards.append("Wet Pavement")

        # --- 2. Temperature / Ice Metric Score (0.0 to 1.0) ---
        temp_score = 0.0
        if temp_f <= 32:
            # Higher score as temp drops further below freezing
            temp_score = min(1.0, 0.3 + (32 - temp_f) * 0.02)
            if precip_score > 0:
                temp_score = min(1.0, temp_score + 0.3)
                hazards.append("Black Ice Hazard")

        # --- 3. Visibility Metric Score (0.0 to 1.0) ---
        # 10,000m (6.2 mi) is clear. Below 1,000m (0.6 mi) is severe fog/blizzard
        vis_miles = visibility_meters / 1609.34
        vis_score = 0.0
        if vis_miles < 6.0:
            vis_score = round(min(1.0, (6.0 - vis_miles) / 5.0), 2)
            if vis_score > 0.4:
                hazards.append("Low Visibility")

        # --- 4. Wind Metric Score (0.0 to 1.0) ---
        wind_score = 0.0
        if wind_speed_mph > 15:
            wind_score = round(min(1.0, (wind_speed_mph - 15) / 35.0), 2)
            if wind_score > 0.4:
                hazards.append("High Crosswinds")

        # --- Assemble Vector Payload ---
        return {
            "status": "success",
            "weather_vector": {
                "precipitation_score": round(precip_score, 2),
                "temperature_score": round(temp_score, 2),
                "visibility_score": round(vis_score, 2),
                "wind_score": round(wind_score, 2)
            },
            "hazards": hazards if hazards else ["Clear Conditions"],
            "raw_metrics": {
                "temp_f": temp_f,
                "wind_speed_mph": wind_speed_mph,
                "visibility_miles": round(vis_miles, 1),
                "snow_1h_mm": snow_1h,
                "rain_1h_mm": rain_1h
            }
        }


# --- QUICK TEST ---
sample_snow_payload = {
    "weather": [{"main": "Snow"}],
    "main": {"temp": 24.0},
    "visibility": 2000,
    "wind": {"speed": 28.0},
    "snow": {"1h": 2.5},
    "cod": 200
}

output = WeatherAgent.calculate_impact_vector(sample_snow_payload)
print(output)

# Paste your actual key inside the quotes
API_KEY = "bf128d55bea8090653e6c0b0fce93a5a"

def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=imperial"
    
    response = requests.get(url)
    data = response.json()
    
    # Extract temperature and main weather condition
    temp = data["main"]["temp"]
    condition = data["weather"][0]["main"]
    
    return {
        "temp": temp,
        "condition": condition,
        "raw": data
    }

# Test with Salt Lake City coordinates
if __name__ == "__main__":
    result = get_weather(40.7608, -111.8910)
    print("API Response:", result)
