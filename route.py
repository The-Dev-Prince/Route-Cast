import os
import googlemaps

# Initialize the client using an environment variable
api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "AIzaSyCjZcHLk1WYBCYjL2fsjC1F806ro221UY8")
gmaps = googlemaps.Client(key=api_key)

# Geocode an address
address = "1600 Amphitheatre Parkway, Mountain View, CA"
geocode_result = gmaps.geocode(address)

if geocode_result:
    location = geocode_result[0]["geometry"]["location"]
    print(f"Latitude: {location['lat']}, Longitude: {location['lng']}")

