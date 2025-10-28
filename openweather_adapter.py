from typing import Any
import httpx


class OpenWeatherError(Exception):
    """Raised when OpenWeather returns a non-200 response.

    Attributes:
        status_code: HTTP status code returned by OpenWeather
        message: textual error message parsed from the response
    """

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class OpenWeatherAdapter:
    """Adapter that encapsulates HTTP calls to OpenWeather and returns parsed JSON.

    This class raises OpenWeatherError for non-200 responses so callers (the web layer)
    can map upstream errors to appropriate HTTP responses.
    """

    def __init__(self, api_key: str, timeout: float = 10.0):
        self.api_key = api_key
        self.timeout = timeout

    async def _get(self, url: str, params: dict) -> Any:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=self.timeout)

        if resp.status_code != 200:
            try:
                err = resp.json()
                msg = err.get("message") or err.get("error") or str(err)
            except Exception:
                msg = resp.text or "unknown error"
            raise OpenWeatherError(resp.status_code, msg)

        return resp.json()

    async def geocode(self, city: str) -> list:
        url = "https://api.openweathermap.org/geo/1.0/direct"
        params = {"q": city, "limit": 1, "appid": self.api_key}
        return await self._get(url, params)

    async def current_weather(self, lat: float, lon: float) -> dict:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"lat": lat, "lon": lon, "units": "metric", "appid": self.api_key}
        return await self._get(url, params)
