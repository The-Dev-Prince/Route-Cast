# Route-Cast

RouteCast recommends a driving route using weather risk, route distance, estimated
traffic, and turn-by-turn directions. The web UI calls the Python weather, routing,
and combination agents through a local API.

## Run the UI

```bash
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Without API keys, the app
uses demo weather and routing data for locations in its built-in city list.
`OPENWEATHER_API_KEY` is needed for other location searches and live weather.
`GOOGLE_MAPS_API_KEY` enables live traffic-aware route alternatives; without it,
the routing agent uses demo routes.

Get your own keys from the OpenWeather and Google Maps Platform accounts, then
set them in the same terminal session before starting the app.

**macOS/Linux (bash):**

```bash
export OPENWEATHER_API_KEY="paste-your-openweather-key-here"
export GOOGLE_MAPS_API_KEY="paste-your-google-maps-key-here"
python app.py
```

**Windows (PowerShell):**

```powershell
$env:OPENWEATHER_API_KEY = "paste-your-openweather-key-here"
$env:GOOGLE_MAPS_API_KEY = "paste-your-google-maps-key-here"
python app.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). Replace the example
values with keys from your provider accounts. Do not commit keys to source files
or share them in browser code. Revoke and replace any key that was previously
committed to the repository.
