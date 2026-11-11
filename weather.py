import requests

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
