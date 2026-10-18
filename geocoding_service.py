"""
ResQAI - Geocoding & Location Search Service
Integrates with OpenStreetMap Nominatim Public API (No-Key-Required) with cache and fallback.
"""

import time
import requests
from datetime import datetime, timezone

_GEOCODE_CACHE = {}
CACHE_TTL = 3600  # 1 hour

_INTEGRATION_STATUS = {
    'name': 'OpenStreetMap Nominatim Geocoding',
    'status': 'untested',
    'last_checked': None,
    'last_success': None,
    'last_error': None,
    'latency_ms': None,
    'endpoint': 'https://nominatim.openstreetmap.org/search',
    'auth_required': False,
    'rate_limit': '1 request/second (Nominatim Usage Policy)',
    'attribution': '© OpenStreetMap contributors (ODbL)'
}

# Preloaded regional coordinate anchors (Pune / Maharashtra / Urban Disaster Belt)
KNOWN_ANCHORS = {
    'pune': {'lat': 18.5204, 'lon': 73.8567, 'display_name': 'Pune, Maharashtra, India'},
    'mumbai': {'lat': 19.0760, 'lon': 72.8777, 'display_name': 'Mumbai, Maharashtra, India'},
    'delhi': {'lat': 28.6139, 'lon': 77.2090, 'display_name': 'New Delhi, Delhi, India'},
    'kothrud': {'lat': 18.5074, 'lon': 73.8077, 'display_name': 'Kothrud, Pune, Maharashtra, India'},
    'shivajinagar': {'lat': 18.5314, 'lon': 73.8446, 'display_name': 'Shivajinagar, Pune, Maharashtra, India'},
    'hadapsar': {'lat': 18.5089, 'lon': 73.9260, 'display_name': 'Hadapsar, Pune, Maharashtra, India'},
    'pimpri': {'lat': 18.6279, 'lon': 73.8009, 'display_name': 'Pimpri-Chinchwad, Pune, Maharashtra, India'},
    'baner': {'lat': 18.5590, 'lon': 73.7868, 'display_name': 'Baner, Pune, Maharashtra, India'},
    'wakad': {'lat': 18.5987, 'lon': 73.7663, 'display_name': 'Wakad, Pune, Maharashtra, India'}
}


def search_location(query):
    """
    Search location string and return list of matching coordinates.
    """
    global _INTEGRATION_STATUS

    if not query or len(query.strip()) < 2:
        return []

    q = query.strip().lower()
    now = time.time()

    if q in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[q]

    # Check local offline anchors first for instant response
    for key, anchor in KNOWN_ANCHORS.items():
        if key in q:
            result = [{
                'lat': anchor['lat'],
                'lon': anchor['lon'],
                'display_name': anchor['display_name'],
                'type': 'preloaded_anchor'
            }]
            _GEOCODE_CACHE[q] = result
            return result

    # Query Nominatim
    url = "https://nominatim.openstreetmap.org/search"
    headers = {
        'User-Agent': 'ResQAI-EmergencySystem/2.0 (contact: emergency-ops@resqai.local)'
    }
    params = {
        'q': query,
        'format': 'json',
        'limit': 5,
        'addressdetails': 1
    }

    start_t = time.time()
    _INTEGRATION_STATUS['last_checked'] = datetime.now(timezone.utc).isoformat()

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=3.0)
        latency = int((time.time() - start_t) * 1000)
        _INTEGRATION_STATUS['latency_ms'] = latency

        if resp.status_code == 200:
            raw_results = resp.json()
            results = []
            for item in raw_results:
                results.append({
                    'lat': float(item.get('lat')),
                    'lon': float(item.get('lon')),
                    'display_name': item.get('display_name'),
                    'type': item.get('type')
                })

            _GEOCODE_CACHE[q] = results
            _INTEGRATION_STATUS['status'] = 'operational'
            _INTEGRATION_STATUS['last_success'] = datetime.now(timezone.utc).isoformat()
            _INTEGRATION_STATUS['last_error'] = None
            return results
        else:
            err = f"Nominatim status {resp.status_code}"
            _INTEGRATION_STATUS['status'] = 'degraded'
            _INTEGRATION_STATUS['last_error'] = err
            return _fallback_search(q)

    except Exception as e:
        err = f"Nominatim error: {str(e)}"
        _INTEGRATION_STATUS['status'] = 'offline'
        _INTEGRATION_STATUS['last_error'] = err
        return _fallback_search(q)


def _fallback_search(query):
    """Provides fallback search using known regional anchors."""
    matches = []
    for key, anchor in KNOWN_ANCHORS.items():
        if key in query or query in key:
            matches.append({
                'lat': anchor['lat'],
                'lon': anchor['lon'],
                'display_name': anchor['display_name'] + " (Offline Safe)",
                'type': 'offline_fallback'
            })
    if not matches:
        # Default center anchor
        matches.append({
            'lat': 18.5204,
            'lon': 73.8567,
            'display_name': f"Estimated Center for '{query}' (Offline Anchor)",
            'type': 'default_fallback'
        })
    return matches


def get_integration_status():
    """Return status for System Health dashboard."""
    return _INTEGRATION_STATUS
