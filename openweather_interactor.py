from typing import Any, Dict

from openweather_adapter import OpenWeatherAdapter, OpenWeatherError


class OpenWeatherInteractor:
    """Business logic for resolving a city and returning structured weather data.

    Responsibilities:
    - Use the provided adapter to geocode a city and fetch current weather.
    - Map upstream JSON into a normalized dict that the web layer can convert to a response model.

    Error behavior:
    - Raises OpenWeatherError when the adapter surfaces an upstream HTTP error.
    - Raises LookupError when the city cannot be resolved.
    """

    def __init__(self, adapter: OpenWeatherAdapter):
        self.adapter = adapter

    async def get_weather(self, city: str) -> Dict[str, Any]:
        """Resolve `city` -> coordinates, then fetch and normalize current weather.

        Returns a dict with keys: city, country, temperature, feels_like, humidity, description, wind_speed, raw
        """
        # 1) Geocode
        geo_data = await self.adapter.geocode(city)
        if not geo_data:
            raise LookupError("City not found (geocoding returned no results)")

        item = geo_data[0]
        lat = item.get("lat")
        lon = item.get("lon")
        resolved_name = item.get("name") or city
        country = item.get("country", "")

        # 2) Current weather
        data = await self.adapter.current_weather(lat, lon)

        main = data.get("main", {})
        weather_arr = data.get("weather") or [{}]
        wind = data.get("wind", {})
        sys = data.get("sys", {})

        api_city_name = data.get("name") or resolved_name
        api_country = sys.get("country", country)

        return {
            "city": api_city_name,
            "country": api_country,
            "temperature": main.get("temp"),
            "feels_like": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "description": weather_arr[0].get("description"),
            "wind_speed": wind.get("speed"),
            "raw": data,
        }
