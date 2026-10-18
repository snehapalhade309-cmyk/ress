"""
ResQAI - Evacuation & Emergency Routing Service
Integrates with Public OSRM (Open Source Routing Machine) API with geodesic polyline fallback.
"""

import math
import time
import requests
from datetime import datetime, timezone

# Cache for computed routes: (lat1, lon1, lat2, lon2) -> (timestamp, route_data)
_ROUTE_CACHE = {}
CACHE_TTL = 1800  # 30 minutes

_INTEGRATION_STATUS = {
    'name': 'OSRM Public Driving Router',
    'status': 'untested',
    'last_checked': None,
    'last_success': None,
    'last_error': None,
    'latency_ms': None,
    'endpoint': 'http://router.project-osrm.org/route/v1/driving',
    'auth_required': False,
    'rate_limit': 'Standard public usage',
    'attribution': 'OpenStreetMap contributors / OSRM Project'
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on the earth in kilometers.
    """
    r = 6371.0  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(r * c, 2)


def get_route(origin_lat, origin_lon, dest_lat, dest_lon):
    """
    Calculate emergency evacuation route from origin to destination.
    Uses OSRM driving service, falls back to geodesic path if unreachable.
    """
    global _INTEGRATION_STATUS

    key = (round(float(origin_lat), 4), round(float(origin_lon), 4),
           round(float(dest_lat), 4), round(float(dest_lon), 4))
    now = time.time()

    if key in _ROUTE_CACHE:
        c_time, c_data = _ROUTE_CACHE[key]
        if now - c_time < CACHE_TTL:
            cached_copy = dict(c_data)
            cached_copy['cached'] = True
            return cached_copy

    # OSRM coordinate order is {longitude},{latitude}
    url = f"http://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"

    start_t = time.time()
    _INTEGRATION_STATUS['last_checked'] = datetime.now(timezone.utc).isoformat()

    try:
        resp = requests.get(url, timeout=3.5)
        latency = int((time.time() - start_t) * 1000)
        _INTEGRATION_STATUS['latency_ms'] = latency

        if resp.status_code == 200:
            payload = resp.json()
            routes = payload.get('routes', [])
            if routes:
                best = routes[0]
                distance_km = round(best.get('distance', 0) / 1000.0, 2)
                duration_min = round(best.get('duration', 0) / 60.0, 1)
                geometry = best.get('geometry', {})

                result = {
                    'status': 'success',
                    'distance_km': distance_km,
                    'duration_minutes': duration_min,
                    'geometry': geometry,
                    'origin': {'lat': origin_lat, 'lon': origin_lon},
                    'destination': {'lat': dest_lat, 'lon': dest_lon},
                    'routing_engine': 'OSRM Public Service',
                    'safety_disclaimer': 'Evacuation route calculation is advisory. Field conditions, flood depths, and official barriers take precedence.',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'fallback': False,
                    'cached': False
                }

                _ROUTE_CACHE[key] = (now, result)
                _INTEGRATION_STATUS['status'] = 'operational'
                _INTEGRATION_STATUS['last_success'] = datetime.now(timezone.utc).isoformat()
                _INTEGRATION_STATUS['last_error'] = None
                return result

        # If OSRM returned non-200 or empty routes
        err = f"OSRM returned status {resp.status_code}"
        _INTEGRATION_STATUS['status'] = 'degraded'
        _INTEGRATION_STATUS['last_error'] = err
        return _fallback_geodesic_route(origin_lat, origin_lon, dest_lat, dest_lon, err)

    except Exception as e:
        err = f"OSRM request failed: {str(e)}"
        _INTEGRATION_STATUS['status'] = 'offline'
        _INTEGRATION_STATUS['last_error'] = err
        return _fallback_geodesic_route(origin_lat, origin_lon, dest_lat, dest_lon, err)


def _fallback_geodesic_route(lat1, lon1, lat2, lon2, reason=""):
    """
    Generate an interpolated geodesic path with direct distance calculation
    when routing server is offline.
    """
    direct_dist_km = haversine_distance(lat1, lon1, lat2, lon2)
    # Estimate driving distance with 1.35x urban road curvature factor
    est_driving_km = round(direct_dist_km * 1.35, 2)
    # Estimate duration at 40 km/h emergency speed
    est_duration_min = round((est_driving_km / 40.0) * 60.0, 1)

    # Generate 5 intermediate waypoints along geodesic
    coordinates = []
    steps = 6
    for i in range(steps + 1):
        fraction = i / float(steps)
        curr_lat = round(lat1 + (lat2 - lat1) * fraction, 5)
        curr_lon = round(lon1 + (lon2 - lon1) * fraction, 5)
        coordinates.append([curr_lon, curr_lat])  # GeoJSON format: [lon, lat]

    return {
        'status': 'fallback',
        'distance_km': est_driving_km,
        'duration_minutes': est_duration_min,
        'geometry': {
            'type': 'LineString',
            'coordinates': coordinates
        },
        'origin': {'lat': lat1, 'lon': lon1},
        'destination': {'lat': lat2, 'lon': lon2},
        'routing_engine': 'ResQAI Geodesic Waypoint Interpolator (Offline Fallback)',
        'safety_disclaimer': 'Caution: Direct vector estimate. Actual road network geometry unavailable offline.',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'fallback': True,
        'cached': False,
        'fallback_reason': reason
    }


def get_integration_status():
    """Return status for System Health dashboard."""
    return _INTEGRATION_STATUS
