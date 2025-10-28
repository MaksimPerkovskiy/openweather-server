# How to get an OpenWeatherMap API key:
# 1. Visit https://openweathermap.org/ and create a free account (Sign Up).
# 2. After verifying your email, log in and go to "API keys" in your account page.
# 3. Create or copy the API key shown there. New keys may take a few minutes to become active.
# 4. Set the key in your environment before running the app:
#    export OPENWEATHER_API_KEY=your_key_here
#    or create a .env file with: OPENWEATHER_API_KEY=your_key_here
# 5. Run the app:
#    uvicorn main:app --reload --host 0.0.0.0 --port 8000
# 6. Test the endpoint:
#    curl 'http://127.0.0.1:8000/weather?city=London'

from os import getenv
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
# Add dotenv support so a local .env file is picked up
from dotenv import load_dotenv

from openweather_adapter import OpenWeatherAdapter, OpenWeatherError
from openweather_interactor import OpenWeatherInteractor

load_dotenv()  # loads .env into environment if present

app = FastAPI(title="OpenWeather proxy")

class WeatherResponse(BaseModel):
    city: str
    country: str
    temperature: float | None
    feels_like: float | None
    humidity: int | None
    description: str | None
    wind_speed: float | None
    raw: dict

API_KEY = getenv("OPENWEATHER_API_KEY")


def get_openweather_adapter() -> OpenWeatherAdapter:
    """Dependency factory for OpenWeatherAdapter. Raises HTTP 500 when no API key is configured."""
    api_key = getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENWEATHER_API_KEY not set. See top comments for how to obtain and set it.")
    return OpenWeatherAdapter(api_key=api_key)


def get_openweather_interactor(adapter: OpenWeatherAdapter = Depends(get_openweather_adapter)) -> OpenWeatherInteractor:
    """Dependency factory for OpenWeatherInteractor."""
    return OpenWeatherInteractor(adapter=adapter)


@app.get("/check-key")
async def check_api_key(adapter: OpenWeatherAdapter = Depends(get_openweather_adapter)):
    """Sanity-check the configured OPENWEATHER_API_KEY by making a lightweight call to the Geocoding API.

    Returns 200 if the key appears valid, otherwise returns a 502 with an actionable message so the
    operator can distinguish 'missing key' vs 'upstream rejected key'.
    """
    try:
        await adapter.geocode("London")
        return {"status": "ok", "detail": "OPENWEATHER_API_KEY appears valid"}
    except OpenWeatherError as e:
        if e.status_code == 401:
            raise HTTPException(status_code=502, detail=f"Upstream unauthorized: {e.message}")
        raise HTTPException(status_code=502, detail=f"OpenWeather responded with {e.status_code}: {e.message}")

@app.get("/weather", response_model=WeatherResponse)
async def get_weather(city: str = Query(..., min_length=1), interactor: OpenWeatherInteractor = Depends(get_openweather_interactor)):
    try:
        result = await interactor.get_weather(city)
    except OpenWeatherError as e:
        if e.status_code == 401:
            raise HTTPException(status_code=502, detail=f"Upstream unauthorized: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=f"OpenWeather API error: {e.message}")
    except LookupError:
        raise HTTPException(status_code=404, detail="City not found (geocoding returned no results)")

    return WeatherResponse(**result)
