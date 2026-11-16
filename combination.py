import math
from typing import Dict, Any, List, Optional
from weather import WeatherAgent
from route import RoutingAgent


class CombinationAgent:
    """
    Combination Agent (Utility-Based):
    Receives normalized weather and route data, weighs speed against
    weather risk across candidate routes, and outputs the optimal route,
    adjusted travel time estimate, and weather suggestions.
    """

    def __init__(
        self,
        weather_data: Dict[str, Any],
        route_data: Dict[str, Any],
        risk_aversion: float = 0.5
    ):
        """
        :param weather_data: Output payload from WeatherAgent.calculate_impact_vector()
        :param route_data: Output payload from RoutingAgent.fetch_routes()
        :param risk_aversion: Trade-off weight (0.0 = pure speed, 1.0 = maximum safety)
        """
        self.weather_data = weather_data
        self.route_data = route_data
        self.risk_aversion = max(0.0, min(1.0, risk_aversion))

        # Extract 4-element weather vector
        if "weather_vector" in weather_data:
            self.weather_vector = list(weather_data["weather_vector"].values())
        else:
            self.weather_vector = list(weather_data.values())

        self.hazards: List[str] = weather_data.get("hazards", ["Clear Conditions"])
        self.candidate_routes: List[Dict[str, Any]] = route_data.get("candidate_routes", [])

        # Fallback route vector if candidate_routes list isn't provided
        self.default_route_vector: List[float] = route_data.get(
            "route_vector", [0.0, 0.0, 0.0, 0.0]
        )

        # Model parameters (8 weights: 4 weather + 4 route)
        self.weights: List[float] = [0.25, 0.35, 0.20, 0.15, 0.30, 0.25, 0.20, 0.10]
        self.bias: float = 0.1
        self.learning_rate: float = 0.01

    @staticmethod
    def sigmoid(x: float) -> float:
        # Clamp x to prevent math overflow on extreme inputs
        x = max(-500.0, min(500.0, x))
        return 1.0 / (1.0 + math.exp(-x))

    def predict(self, combined_vector: List[float]) -> float:
        """Computes a normalized risk/delay severity score between 0.0 and 1.0."""
        z = self.bias
        for w, x in zip(self.weights, combined_vector):
            z += w * x
        return self.sigmoid(z)

    def train(
        self,
        training_examples: Optional[List[Dict[str, Any]]] = None,
        epochs: int = 1000,
        verbose: bool = False
    ) -> None:
        """
        Trains the perceptron weights on historical trip data.
        Each example should contain 'weather_vector', 'route_vector', and 'target_risk'
        (or 'actual_time' and 'base_time' to derive delay ratio).
        """
        if training_examples is None:
            training_examples = [
                {
                    "weather_vector": [0.35, 0.70, 0.40, 1.0],
                    "route_vector": [0.30, 0.50, 0.25, 1.0],
                    "target_risk": 0.70
                },
                {
                    "weather_vector": [0.20, 0.10, 0.20, 0.0],
                    "route_vector": [0.20, 0.35, 0.10, 0.0],
                    "target_risk": 0.25
                }
            ]

        for epoch in range(epochs):
            total_error = 0.0
            for example in training_examples:
                combined = example["weather_vector"] + example["route_vector"]
                pred = self.predict(combined)

                # Support either explicit target_risk (0-1) or actual_time/100 fallback
                if "target_risk" in example:
                    target = example["target_risk"]
                else:
                    target = example.get("actual_time", 45.0) / 100.0

                error = pred - target
                total_error += error ** 2

                for i in range(len(self.weights)):
                    self.weights[i] -= self.learning_rate * error * combined[i]
                self.bias -= self.learning_rate * error

            if verbose and epoch % 200 == 0:
                print(f"Epoch {epoch}: MSE = {total_error / len(training_examples):.6f}")

    @staticmethod
    def _vectorize_route(route: Dict[str, Any]) -> List[float]:
        """Normalizes an individual candidate route into the 4-element route vector."""
        normal_duration = route.get("normal_duration_mins", 0.0)
        traffic_delay = route.get("traffic_delay_mins", 0.0)
        return [
            min(1.0, route.get("distance_km", 0.0) / 100.0),
            min(1.0, route.get("traffic_duration_mins", 0.0) / 120.0),
            min(1.0, traffic_delay / 60.0),
            min(1.0, traffic_delay / normal_duration) if normal_duration > 0 else 0.0
        ]

    def _generate_suggestions(self, risk_score: float, chosen_summary: str) -> List[str]:
        """Produces actionable weather-related trip suggestions based on active hazards."""
        suggestions = []
        hazard_set = set(self.hazards)

        if "Black Ice Hazard" in hazard_set:
            suggestions.append("Black ice likely: increase following distance and avoid sudden braking.")
        if "Snowy Road Conditions" in hazard_set:
            suggestions.append("Snow on roadway: stick to plowed main highways and avoid steep canyon grades.")
            if "canyon" in chosen_summary.lower() or "89" in chosen_summary.lower():
                suggestions.append("Caution: selected route includes canyon/secondary roads that may plow slower.")
        if "Wet Pavement" in hazard_set:
            suggestions.append("Wet roads: reduce speed on curves and watch for hydroplaning.")
        if "Low Visibility" in hazard_set:
            suggestions.append("Low visibility: use low-beam headlights and allow extra buffer time.")
        if "High Crosswinds" in hazard_set:
            suggestions.append("High crosswinds: keep both hands on the wheel, especially on exposed highways.")

        if not suggestions:
            if risk_score > 0.6:
                suggestions.append("Moderate traffic/weather congestion expected; leave 10–15 minutes early.")
            else:
                suggestions.append("Conditions look favorable; normal driving precautions apply.")

        return suggestions

    def combine_data(self) -> Dict[str, Any]:
        """
        Evaluates all candidate routes, calculates weather-adjusted ETAs and utility scores,
        and selects the best overall route.
        """
        # Fallback if only a single route_vector was passed without candidate_routes
        if not self.candidate_routes:
            combined = self.weather_vector + self.default_route_vector
            risk_score = self.predict(combined)
            adjusted_time = 30.0 + (risk_score * 40.0)
            return {
                "status": "success_vector_only",
                "risk_score": round(risk_score, 4),
                "estimated_time_minutes": round(adjusted_time, 2),
                "weather_vector": self.weather_vector,
                "route_vector": self.default_route_vector,
                "suggestions": self._generate_suggestions(risk_score, "")
            }

        evaluated_routes = []
        weather_severity = sum(self.weather_vector) / max(1, len(self.weather_vector))

        for route in self.candidate_routes:
            r_vec = self._vectorize_route(route)
            combined = self.weather_vector + r_vec
            risk_score = self.predict(combined)

            # Scale base traffic duration by weather severity (up to +50% delay in severe storms)
            base_traffic_mins = route.get("traffic_duration_mins", route.get("normal_duration_mins", 30.0))
            weather_multiplier = 1.0 + (0.5 * weather_severity * risk_score)
            adjusted_time = base_traffic_mins * weather_multiplier

            # Utility score (higher is better): penalizes both travel time and weather risk
            # Extra penalty applied to secondary/canyon routes when snow/ice is present
            summary = route.get("summary", f"Route {route.get('route_id', 0)}")
            terrain_penalty = 0.0
            if any(h in self.hazards for h in ["Snowy Road Conditions", "Black Ice Hazard"]):
                if "canyon" in summary.lower() or "sr-" in summary.lower() or "state route" in summary.lower():
                    terrain_penalty = 15.0 * self.risk_aversion

            expected_cost = adjusted_time + (self.risk_aversion * 30.0 * risk_score) + terrain_penalty
            utility_score = round(100.0 / (1.0 + (expected_cost / 30.0)), 2)

            evaluated_routes.append({
                "route_id": route.get("route_id"),
                "summary": summary,
                "distance_km": route.get("distance_km"),
                "base_traffic_mins": base_traffic_mins,
                "estimated_time_minutes": round(adjusted_time, 2),
                "risk_score": round(risk_score, 4),
                "utility_score": utility_score,
                "steps": route.get("steps", []),
                "route_vector": r_vec
            })

        # Select the route with the highest utility score
        best_route = max(evaluated_routes, key=lambda r: r["utility_score"])

        return {
            "status": "success",
            "origin": self.route_data.get("origin", "Unknown"),
            "destination": self.route_data.get("destination", "Unknown"),
            "recommended_route": best_route,
            "all_evaluated_routes": evaluated_routes,
            "active_hazards": self.hazards,
            "suggestions": self._generate_suggestions(
                best_route["risk_score"], best_route["summary"]
            ),
            "weather_vector": self.weather_vector
        }


# --- END-TO-END DEMO ---
if __name__ == "__main__":
    import json

    # 1. Simulate Weather Agent output (Winter storm scenario)
    sample_weather_raw = {
        "weather": [{"main": "Snow"}],
        "main": {"temp": 24.0},
        "visibility": 2000,
        "wind": {"speed": 28.0},
        "snow": {"1h": 2.5},
        "cod": 200
    }
    weather_output = WeatherAgent.calculate_impact_vector(sample_weather_raw)

    # 2. Fetch Routing Agent output (Demo mode: I-15 vs State Route 89 Canyon)
    routing_agent = RoutingAgent(use_demo=True)
    route_output = routing_agent.fetch_routes(origin="Provo, UT", destination="Salt Lake City, UT")

    # 3. Combine and select optimal route
    combiner = CombinationAgent(
        weather_data=weather_output,
        route_data=route_output,
        risk_aversion=0.6
    )
    combiner.train(epochs=1000, verbose=False)
    decision = combiner.combine_data()

    print(json.dumps(decision, indent=2))