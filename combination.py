from weather import WeatherAgent
from route import RoutingAgent
import math

class CombinationAgent:
    def __init__(self, weather_data, route_data):
        if "weather_vector" in weather_data:
            self.weather_vector = list(weather_data["weather_vector"].values())
        else:
            self.weather_vector = list(weather_data.values())
        self.route_data = route_data

    def sigmoid(self, x):
        return 1 / (1 + math.exp(-x))

    def combine_data(self):
        # combine the two vectors into one input vector
        combined = self.weather_vector + self.route_vector

        # simple neural net weights
        weights = [0.25, 0.35, 0.20, 0.15, 0.30, 0.25, 0.20, 0.10]
        bias = 0.1

        # compute weighted sum
        z = bias
        for weight, value in zip(weights, combined):
            z += weight * value

        # apply activation
        risk_score = self.sigmoid(z)

        # convert to a useful output
        adjusted_time = 30 + (risk_score * 40)

        return {
            "risk_score": round(risk_score, 4),
            "estimated_time_minutes": round(adjusted_time, 2),
            "weather_vector": self.weather_vector,
            "route_vector": self.route_vector
        }
