"""
ResQAI - Climate & Weather Service
Integrates with Open-Meteo Public API (100% Free, No-Key-Required) with in-memory TTL caching
and graceful offline fallback.
"""

import time
import requests
from datetime import datetime, timezone

# In-memory cache: (rounded_lat, rounded_lon) -> (timestamp, data)
_WEATHER_CACHE = {}
CACHE_TTL_SECONDS = 900  # 15 minutes

# Integration registry tracker
_INTEGRATION_STATUS = {
    'name': 'Open-Meteo Public Weather API',
    'status': 'untested',
    'last_checked': None,
    'last_success': None,
    'last_error': None,
    'latency_ms': None,
    'endpoint': 'https://api.open-meteo.com/v1/forecast',
    'auth_required': False,
    'rate_limit': '10,000 requests/day (Free tier)',
    'attribution': 'Weather data by Open-Meteo.com under CC BY 4.0'
}

WMO_WEATHER_CODES = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Fog',
    48: 'Depositing rime fog',
    51: 'Light drizzle',
    53: 'Moderate drizzle',
    55: 'Dense drizzle',
    61: 'Slight rain',
    63: 'Moderate rain',
    65: 'Heavy rain',
    71: 'Slight snow fall',
    73: 'Moderate snow fall',
    75: 'Heavy snow fall',
    80: 'Slight rain showers',
    81: 'Moderate rain showers',
    82: 'Violent rain showers',
    95: 'Thunderstorm (Slight or moderate)',
    96: 'Thunderstorm with slight hail',
    99: 'Thunderstorm with heavy hail'
}


def get_weather(lat, lon):
    """
    Fetch current weather metrics for given coordinates.
    Returns structured weather observation with units, source, and timestamps.
    """
    global _INTEGRATION_STATUS

    if lat is None or lon is None:
        return _get_fallback_weather(lat, lon, "Coordinates not specified")

    # Round coordinates to ~1.1km grid for effective caching
    cache_key = (round(float(lat), 2), round(float(lon), 2))
    now = time.time()

    if cache_key in _WEATHER_CACHE:
        cached_time, cached_data = _WEATHER_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            cached_copy = dict(cached_data)
            cached_copy['cached'] = True
            return cached_copy

    # Fetch from Open-Meteo
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': lat,
        'longitude': lon,
        'current': 'temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m',
        'timezone': 'auto'
    }

    start_t = time.time()
    _INTEGRATION_STATUS['last_checked'] = datetime.now(timezone.utc).isoformat()

    try:
        resp = requests.get(url, params=params, timeout=4.0)
        latency = int((time.time() - start_t) * 1000)
        _INTEGRATION_STATUS['latency_ms'] = latency

        if resp.status_code == 200:
            payload = resp.json()
            curr = payload.get('current', {})

            weather_code = curr.get('weather_code', 0)
            desc = WMO_WEATHER_CODES.get(weather_code, 'Atmospheric Condition Active')

            precip = float(curr.get('precipitation', 0.0))
            wind = float(curr.get('wind_speed_10m', 0.0))
            temp = float(curr.get('temperature_2m', 25.0))
            humidity = float(curr.get('relative_humidity_2m', 60.0))

            # Threat indicators
            flood_threat = precip >= 15.0
            storm_threat = wind >= 40.0

            result = {
                'temperature': temp,
                'temperature_unit': '°C',
                'precipitation': precip,
                'precipitation_unit': 'mm/hr',
                'wind_speed': wind,
                'wind_speed_unit': 'km/h',
                'humidity': humidity,
                'humidity_unit': '%',
                'weather_code': weather_code,
                'condition': desc,
                'flood_threat_flag': flood_threat,
                'storm_threat_flag': storm_threat,
                'latitude': lat,
                'longitude': lon,
                'source': 'Open-Meteo Live API',
                'attribution': 'Weather data by Open-Meteo.com under CC BY 4.0',
                'timestamp': curr.get('time', datetime.now(timezone.utc).isoformat()),
                'cached': False
            }

            _WEATHER_CACHE[cache_key] = (now, result)
            _INTEGRATION_STATUS['status'] = 'operational'
            _INTEGRATION_STATUS['last_success'] = datetime.now(timezone.utc).isoformat()
            _INTEGRATION_STATUS['last_error'] = None
            return result
        else:
            err = f"Open-Meteo returned status {resp.status_code}"
            _INTEGRATION_STATUS['status'] = 'degraded'
            _INTEGRATION_STATUS['last_error'] = err
            return _get_fallback_weather(lat, lon, err)

    except Exception as e:
        err = f"Open-Meteo query failed: {str(e)}"
        _INTEGRATION_STATUS['status'] = 'offline'
        _INTEGRATION_STATUS['last_error'] = err
        return _get_fallback_weather(lat, lon, err)


def _get_fallback_weather(lat, lon, reason=""):
    """Provides safe baseline weather estimates when remote service is unavailable."""
    return {
        'temperature': 26.5,
        'temperature_unit': '°C',
        'precipitation': 0.0,
        'precipitation_unit': 'mm/hr',
        'wind_speed': 12.0,
        'wind_speed_unit': 'km/h',
        'humidity': 65.0,
        'humidity_unit': '%',
        'weather_code': 1,
        'condition': 'Mainly Clear (Estimated Baseline)',
        'flood_threat_flag': False,
        'storm_threat_flag': False,
        'latitude': lat,
        'longitude': lon,
        'source': 'ResQAI Climate Baseline (Offline Safe Fallback)',
        'attribution': 'Local deterministic meteorological estimate',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'cached': False,
        'fallback_reason': reason
    }


def get_integration_status():
    """Return live integration health information for System Health dashboard."""
    return _INTEGRATION_STATUS
