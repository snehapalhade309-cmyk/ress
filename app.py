"""
ResQAI - Emergency Management & Response System
Flask REST API Server & SPA Static File Handler
"""

import os
import json
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory, render_template

from backend.database import get_db, row_to_dict, init_db
from backend.risk_engine import calculate_risk
from backend.dispatch_engine import get_recommendations, assign_resource, release_resource
from backend.weather_service import get_weather, get_integration_status as get_weather_status
from backend.routing_service import get_route, get_integration_status as get_routing_status
from backend.geocoding_service import search_location, get_integration_status as get_geocoding_status
from backend.ai_service import generate_incident_ai_brief, get_integration_status as get_ai_status
from backend.audit_service import log_event, get_recent_logs
from backend.seed_data import seed_database

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR)
app.config['JSON_SORT_KEYS'] = False

# Ensure database is initialized on server startup
init_db()


# -------------------------------------------------------------
# Frontend Static Routing
# -------------------------------------------------------------
@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)


@app.route('/vendor/<path:filename>')
def serve_vendor(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'vendor'), filename)


# -------------------------------------------------------------
# System & Diagnostic Endpoints
# -------------------------------------------------------------
@app.route('/api/health', methods=['GET'])
def get_system_health():
    """Return health telemetry for database and all external service integrations."""
    db_status = {'status': 'healthy', 'error': None, 'tables': {}}
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            for tbl in ['incidents', 'resources', 'shelters', 'dispatches', 'alerts', 'audit_logs']:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {tbl}")
                db_status['tables'][tbl] = cursor.fetchone()['cnt']
    except Exception as e:
        db_status['status'] = 'error'
        db_status['error'] = str(e)

    integrations = {
        'database': db_status,
        'osm_tiles': {
            'name': 'OpenStreetMap Cartographic Tile Server',
            'status': 'operational',
            'auth_required': False,
            'attribution': '© OpenStreetMap contributors',
            'endpoint': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        },
        'weather_api': get_weather_status(),
        'routing_engine': get_routing_status(),
        'geocoding_service': get_geocoding_status(),
        'ai_service': get_ai_status()
    }

    return jsonify({
        'system': 'ResQAI Emergency Command Center',
        'status': 'operational' if db_status['status'] == 'healthy' else 'degraded',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'integrations': integrations
    })


@app.route('/api/stats', methods=['GET'])
def get_dashboard_stats():
    """Return aggregated KPIs for Command Center overview."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Incidents KPI
        cursor.execute("SELECT COUNT(*) as total FROM incidents")
        total_inc = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as active FROM incidents WHERE status != 'resolved'")
        active_inc = cursor.fetchone()['active']

        cursor.execute("SELECT COUNT(*) as critical FROM incidents WHERE risk_category = 'Critical' AND status != 'resolved'")
        critical_inc = cursor.fetchone()['critical']

        cursor.execute("SELECT COUNT(*) as high FROM incidents WHERE risk_category = 'High' AND status != 'resolved'")
        high_inc = cursor.fetchone()['high']

        # Resources KPI
        cursor.execute("SELECT COUNT(*) as total FROM resources")
        total_res = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as avail FROM resources WHERE status = 'available'")
        avail_res = cursor.fetchone()['avail']

        cursor.execute("SELECT COUNT(*) as dispatched FROM resources WHERE status = 'dispatched'")
        dispatched_res = cursor.fetchone()['dispatched']

        # Shelters KPI
        cursor.execute("SELECT SUM(total_capacity) as cap, SUM(current_occupancy) as occ FROM shelters")
        shelter_row = cursor.fetchone()
        tot_cap = shelter_row['cap'] or 0
        tot_occ = shelter_row['occ'] or 0
        util_pct = round((tot_occ / tot_cap * 100.0), 1) if tot_cap > 0 else 0.0

        # Unacknowledged alerts count
        cursor.execute("SELECT COUNT(*) as unack FROM alerts WHERE is_acknowledged = 0")
        unack_alerts = cursor.fetchone()['unack']

        return jsonify({
            'incidents': {
                'total': total_inc,
                'active': active_inc,
                'critical_active': critical_inc,
                'high_active': high_inc,
                'resolved': total_inc - active_inc
            },
            'resources': {
                'total': total_res,
                'available': avail_res,
                'dispatched': dispatched_res,
                'in_maintenance': total_res - avail_res - dispatched_res,
                'utilization_pct': round((dispatched_res / total_res * 100.0), 1) if total_res > 0 else 0.0
            },
            'shelters': {
                'total_capacity': tot_cap,
                'current_occupancy': tot_occ,
                'utilization_pct': util_pct,
                'available_capacity': max(0, tot_cap - tot_occ)
            },
            'alerts': {
                'unacknowledged': unack_alerts
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        })


# -------------------------------------------------------------
# Incidents Management
# -------------------------------------------------------------
@app.route('/api/incidents', methods=['GET'])
def list_incidents():
    """List incidents with filtering by type, severity, status, or search query."""
    inc_type = request.args.get('type')
    severity = request.args.get('severity')
    status = request.args.get('status')
    search = request.args.get('search')
    limit = int(request.args.get('limit', 100))

    query = "SELECT * FROM incidents WHERE 1=1"
    params = []

    if inc_type and inc_type != 'all':
        query += " AND type = ?"
        params.append(inc_type)
    if severity and severity != 'all':
        query += " AND (reported_severity = ? OR risk_category = ?)"
        params.extend([severity, severity.capitalize()])
    if status and status != 'all':
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (title LIKE ? OR location_name LIKE ? OR incident_code LIKE ? OR description LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    query += " ORDER BY CASE risk_category WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, id DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/incidents/<int:incident_id>', methods=['GET'])
def get_incident_detail(incident_id):
    """Retrieve detailed view of an incident, including risk breakdown, AI summary, and dispatch options."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Incident not found'}), 404

        incident = row_to_dict(row)

        # Fetch active weather for the incident coordinates
        weather = None
        if incident.get('latitude') is not None and incident.get('longitude') is not None:
            weather = get_weather(incident['latitude'], incident['longitude'])

        # Re-evaluate live risk details
        risk_result = calculate_risk(incident, weather)

        # Generate decision support brief
        brief = generate_incident_ai_brief(incident, risk_result, weather)

        # Fetch smart dispatch recommendations
        dispatch_recs = get_recommendations(incident_id)

        # Fetch assigned resources if any
        cursor.execute("""
            SELECT r.*, d.dispatch_time, d.status as dispatch_status, d.notes as dispatch_notes
            FROM resources r
            JOIN dispatches d ON d.resource_id = r.id
            WHERE d.incident_id = ? AND d.status != 'completed'
        """, (incident_id,))
        assigned_units = [row_to_dict(r) for r in cursor.fetchall()]

        return jsonify({
            'incident': incident,
            'weather': weather,
            'risk_evaluation': risk_result,
            'decision_brief': brief,
            'recommendations': dispatch_recs.get('recommendations', []),
            'assigned_units': assigned_units
        })


@app.route('/api/incidents', methods=['POST'])
def create_incident():
    """Create a new emergency incident report with validation and instant risk intelligence."""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    # Required validation
    inc_type = str(data.get('type', '')).strip().lower()
    title = str(data.get('title', '')).strip()
    location_name = str(data.get('location_name', '')).strip()
    reported_severity = str(data.get('reported_severity', 'moderate')).strip().lower()

    if not inc_type or not title or not location_name:
        return jsonify({'error': 'Fields "type", "title", and "location_name" are required.'}), 400

    # Parse coordinates safely
    lat = None
    lon = None
    try:
        if data.get('latitude') not in [None, '']:
            lat = float(data['latitude'])
        if data.get('longitude') not in [None, '']:
            lon = float(data['longitude'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Coordinates must be valid numbers.'}), 400

    # Parse affected people count
    try:
        raw_ppl = data.get('affected_people', 0)
        affected_people = max(0, int(float(raw_ppl))) if raw_ppl is not None else 0
    except (ValueError, TypeError):
        affected_people = 0

    # Parse vulnerability tags
    vulnerability_tags = data.get('vulnerability_tags', [])
    if isinstance(vulnerability_tags, str):
        vulnerability_tags = [t.strip().lower() for t in vulnerability_tags.split(',') if t.strip()]

    description = str(data.get('description', '')).strip()
    reporter_name = str(data.get('reporter_name', 'Anonymous Citizen')).strip()
    reporter_contact = str(data.get('reporter_contact', '')).strip()

    # Fetch real-time weather if coordinates exist
    weather = None
    if lat is not None and lon is not None:
        weather = get_weather(lat, lon)

    # Compute risk score
    risk = calculate_risk({
        'type': inc_type,
        'reported_severity': reported_severity,
        'affected_people': affected_people,
        'vulnerability_tags': vulnerability_tags,
        'latitude': lat,
        'longitude': lon
    }, weather)

    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM incidents")
        next_num = cursor.fetchone()['total'] + 1
        incident_code = f"INC-2026-{next_num:03d}"

        cursor.execute("""
            INSERT INTO incidents (
                incident_code, type, title, location_name, latitude, longitude,
                reported_severity, affected_people, vulnerability_tags, description,
                reporter_name, reporter_contact, calculated_risk_score, risk_category,
                risk_factors_json, status, is_demo, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'reported', 0, ?, ?)
        """, (
            incident_code, inc_type, title, location_name, lat, lon,
            reported_severity, affected_people, json.dumps(vulnerability_tags), description,
            reporter_name, reporter_contact, risk['score'], risk['category'],
            json.dumps(risk['factor_breakdown']), now_iso, now_iso
        ))
        new_id = cursor.lastrowid

        # Generate immediate in-app alert for high/critical incidents
        if risk['category'] in ['High', 'Critical']:
            alert_sev = 'critical' if risk['category'] == 'Critical' else 'warning'
            cursor.execute("""
                INSERT INTO alerts (title, message, severity, incident_id, source, is_acknowledged, created_at)
                VALUES (?, ?, ?, ?, 'Risk Intelligence Engine', 0, ?)
            """, (
                f"{risk['category'].upper()} HAZARD: {title}",
                f"{inc_type.upper()} at {location_name}. Risk Score {risk['score']}/100. Affected: ~{affected_people} people.",
                alert_sev, new_id, now_iso
            ))

        # Log audit trail
        audit_details = {
            'incident_code': incident_code,
            'type': inc_type,
            'risk_score': risk['score'],
            'risk_category': risk['category']
        }
        log_event('INCIDENT_CREATED', 'incident', new_id, audit_details, reporter_name, conn=conn)

        # Retrieve created record
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (new_id,))
        created_record = row_to_dict(cursor.fetchone())

    return jsonify({
        'message': 'Incident reported and processed successfully.',
        'incident': created_record,
        'risk_evaluation': risk
    }), 201


@app.route('/api/incidents/<int:incident_id>/status', methods=['PATCH'])
def update_incident_status(incident_id):
    """Update incident operational status."""
    data = request.get_json(force=True, silent=True) or {}
    new_status = str(data.get('status', '')).strip().lower()
    allowed = ['reported', 'verified', 'dispatched', 'on_scene', 'resolved']

    if new_status not in allowed:
        return jsonify({'error': f"Invalid status. Must be one of: {', '.join(allowed)}"}), 400

    now_iso = datetime.now(timezone.utc).isoformat()
    actor = data.get('actor', 'Command Dispatcher')

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Incident not found'}), 404
        prev_status = row['status']

        cursor.execute("""
            UPDATE incidents
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (new_status, now_iso, incident_id))

        log_event('INCIDENT_STATUS_UPDATED', 'incident', incident_id, {
            'previous_status': prev_status,
            'new_status': new_status
        }, actor, conn=conn)

        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        return jsonify(row_to_dict(cursor.fetchone()))


@app.route('/api/incidents/evaluate-risk', methods=['POST'])
def preview_risk():
    """Live risk calculator endpoint for real-time form preview."""
    data = request.get_json(force=True, silent=True) or {}

    lat = None
    lon = None
    try:
        if data.get('latitude') not in [None, '']:
            lat = float(data['latitude'])
        if data.get('longitude') not in [None, '']:
            lon = float(data['longitude'])
    except Exception:
        pass

    weather = None
    if lat is not None and lon is not None:
        weather = get_weather(lat, lon)

    risk = calculate_risk(data, weather)
    return jsonify({
        'risk': risk,
        'weather_snapshot': weather
    })


# -------------------------------------------------------------
# Resources & Smart Dispatch Management
# -------------------------------------------------------------
@app.route('/api/resources', methods=['GET'])
def list_resources():
    """List all emergency response fleet units."""
    status = request.args.get('status')
    res_type = request.args.get('type')

    query = "SELECT * FROM resources WHERE 1=1"
    params = []
    if status and status != 'all':
        query += " AND status = ?"
        params.append(status)
    if res_type and res_type != 'all':
        query += " AND type = ?"
        params.append(res_type)

    query += " ORDER BY id ASC"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return jsonify([row_to_dict(r) for r in cursor.fetchall()])


@app.route('/api/resources/<int:resource_id>', methods=['GET'])
def get_resource_detail(resource_id):
    """Retrieve resource status and history."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = ?", (resource_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Resource not found'}), 404

        res = row_to_dict(row)

        cursor.execute("""
            SELECT d.*, i.incident_code, i.title, i.location_name
            FROM dispatches d
            JOIN incidents i ON i.id = d.incident_id
            WHERE d.resource_id = ?
            ORDER BY d.id DESC LIMIT 10
        """, (resource_id,))
        history = [row_to_dict(h) for h in cursor.fetchall()]

        return jsonify({
            'resource': res,
            'dispatch_history': history
        })


@app.route('/api/dispatch', methods=['POST'])
def dispatch_unit():
    """Assign resource to incident via atomic transaction."""
    data = request.get_json(force=True, silent=True) or {}
    incident_id = data.get('incident_id')
    resource_id = data.get('resource_id')
    notes = data.get('notes', 'Standard tactical dispatch')
    dispatcher = data.get('dispatcher_name', 'Command Dispatcher')

    if not incident_id or not resource_id:
        return jsonify({'error': 'Both incident_id and resource_id are required.'}), 400

    result = assign_resource(incident_id, resource_id, notes, dispatcher)
    if not result.get('success'):
        return jsonify(result), 409  # Conflict / resource unavailable

    return jsonify(result), 200


@app.route('/api/dispatch/release', methods=['POST'])
def release_unit():
    """Release a dispatched unit back to available status."""
    data = request.get_json(force=True, silent=True) or {}
    resource_id = data.get('resource_id')
    notes = data.get('notes', 'Mission accomplished')
    actor = data.get('actor', 'Command Dispatcher')

    if not resource_id:
        return jsonify({'error': 'resource_id is required.'}), 400

    result = release_resource(resource_id, notes, actor)
    if not result.get('success'):
        return jsonify(result), 400

    return jsonify(result), 200


# -------------------------------------------------------------
# Shelters & Evacuation Routing
# -------------------------------------------------------------
@app.route('/api/shelters', methods=['GET'])
def list_shelters():
    """List all verified evacuation shelters with capacity metrics."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shelters ORDER BY id ASC")
        shelters = [row_to_dict(r) for r in cursor.fetchall()]

        for s in shelters:
            cap = s.get('total_capacity', 1)
            occ = s.get('current_occupancy', 0)
            s['occupancy_pct'] = round((occ / cap * 100.0), 1) if cap > 0 else 0.0
            s['available_spaces'] = max(0, cap - occ)

        return jsonify(shelters)


@app.route('/api/routes/evacuation', methods=['GET'])
def calculate_evacuation_route():
    """Calculate driving route from incident or coordinates to nearest/chosen shelter."""
    try:
        origin_lat = float(request.args.get('origin_lat'))
        origin_lon = float(request.args.get('origin_lon'))
        dest_lat = float(request.args.get('dest_lat'))
        dest_lon = float(request.args.get('dest_lon'))
    except (ValueError, TypeError):
        return jsonify({'error': 'Valid origin_lat, origin_lon, dest_lat, dest_lon required.'}), 400

    route_res = get_route(origin_lat, origin_lon, dest_lat, dest_lon)
    return jsonify(route_res)


# -------------------------------------------------------------
# Public Weather & Geocoding APIs (No Mandatory Keys)
# -------------------------------------------------------------
@app.route('/api/weather', methods=['GET'])
def query_weather():
    """Retrieve weather data for given coordinates."""
    try:
        lat = float(request.args.get('lat', 18.5204))
        lon = float(request.args.get('lon', 73.8567))
    except (ValueError, TypeError):
        return jsonify({'error': 'Valid lat and lon parameters required.'}), 400

    weather = get_weather(lat, lon)
    return jsonify(weather)


@app.route('/api/geocode', methods=['GET'])
def query_geocode():
    """Search location names for coordinates using Nominatim / offline anchors."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    results = search_location(q)
    return jsonify(results)


# -------------------------------------------------------------
# In-App Alerts & Audit Trails
# -------------------------------------------------------------
@app.route('/api/alerts', methods=['GET'])
def list_alerts():
    """List in-app emergency alerts."""
    unack_only = request.args.get('unacknowledged_only') == '1'
    query = "SELECT * FROM alerts"
    if unack_only:
        query += " WHERE is_acknowledged = 0"
    query += " ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END, id DESC LIMIT 50"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return jsonify([row_to_dict(r) for r in cursor.fetchall()])


@app.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Mark an alert as acknowledged."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE alerts SET is_acknowledged = 1 WHERE id = ?", (alert_id,))
        if cursor.rowcount == 0:
            return jsonify({'error': 'Alert not found'}), 404
        log_event('ALERT_ACKNOWLEDGED', 'alert', alert_id, None, 'operator', conn=conn)
        return jsonify({'success': True, 'alert_id': alert_id})


@app.route('/api/audit-logs', methods=['GET'])
def list_audit_logs():
    """List recent activity and dispatch audit events."""
    limit = int(request.args.get('limit', 50))
    logs = get_recent_logs(limit)
    return jsonify(logs)


@app.route('/api/system/reset-demo', methods=['POST'])
def reset_demo_database():
    """Reset the database to clean seed state (requires confirmation parameter)."""
    data = request.get_json(force=True, silent=True) or {}
    if not data.get('confirm'):
        return jsonify({'error': 'Explicit confirmation required. Send {"confirm": true}'}), 400

    result = seed_database(force_reset=True)
    return jsonify(result)


# -------------------------------------------------------------
# Application Runner
# -------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"ResQAI Emergency Command Center launching on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=debug)
