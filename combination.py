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

    weights = [0.25, 0.35, 0.20, 0.15, 0.30, 0.25, 0.20, 0.10]
    learning_rate = 0.01

    def predict(combined):
        z = 0.1
        for w, x in zip(weights, combined):
            z += w * x
        return sigmoid(z)

    training_examples = [
        {
            "weather_vector": [0.35, 0.70, 0.40, 1],
            "route_vector": [0.30, 0.50, 0.25, 1],
            "actual_time": 70
        },
        {
            "weather_vector": [0.20, 0.10, 0.20, 0],
            "route_vector": [0.20, 0.35, 0.10, 0],
            "actual_time": 45
        }
    ]

    for epoch in range(1000):
        total_error = 0
        for example in training_examples:
            combined = example["weather_vector"] + example["route_vector"]
            pred = predict(combined)
            actual = example["actual_time"] / 100.0
            error = pred - actual

            total_error += error ** 2

            for i in range(len(weights)):
                weights[i] -= learning_rate * error * combined[i]

        if epoch % 100 == 0:
            print(f"epoch {epoch}: error = {total_error}")

    def combine_data(self):
        # combine the two vectors into one input vector
        combined = self.weather_vector + self.route_vector

        # simple neural net weights
        
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
