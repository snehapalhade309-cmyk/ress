"""
ResQAI - Smart Resource Dispatch Engine
Provides suitability matching, proximity estimation, atomic transaction dispatching,
and double-assignment prevention.
"""

from datetime import datetime, timezone
import json
import sqlite3
from backend.database import get_db, row_to_dict
from backend.routing_service import haversine_distance

# Capability matrix mapping incident types to primary/secondary resource requirements
INCIDENT_CAPABILITY_REQUIREMENTS = {
    'flood': {
        'primary_types': ['rescue_boat', 'ndrf_team'],
        'secondary_types': ['ambulance'],
        'required_tags': ['water_rescue', 'evacuation', 'first_aid']
    },
    'landslide': {
        'primary_types': ['heavy_rescue', 'ndrf_team'],
        'secondary_types': ['ambulance'],
        'required_tags': ['extrication', 'debris_clearing', 'trauma_care']
    },
    'fire': {
        'primary_types': ['fire_unit'],
        'secondary_types': ['ambulance', 'heavy_rescue'],
        'required_tags': ['firefighting', 'hazmat', 'burn_treatment']
    },
    'earthquake': {
        'primary_types': ['ndrf_team', 'heavy_rescue'],
        'secondary_types': ['ambulance'],
        'required_tags': ['structural_collapse', 'search_and_rescue', 'triage']
    },
    'severe_weather': {
        'primary_types': ['ndrf_team', 'rescue_boat'],
        'secondary_types': ['ambulance', 'fire_unit'],
        'required_tags': ['storm_response', 'tree_clearing']
    },
    'accident': {
        'primary_types': ['ambulance', 'fire_unit'],
        'secondary_types': ['heavy_rescue'],
        'required_tags': ['als', 'bls', 'extrication', 'trauma']
    },
    'industrial': {
        'primary_types': ['fire_unit', 'ndrf_team'],
        'secondary_types': ['ambulance'],
        'required_tags': ['hazmat', 'gas_containment', 'oxygen']
    }
}


def get_recommendations(incident_id):
    """
    Generate ranked resource recommendations for a specific incident based on:
    1. Incident hazard type and vulnerability requirements
    2. Geographic distance (Haversine formula)
    3. Resource capability tags
    4. Current resource availability
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        inc_row = cursor.fetchone()
        if not inc_row:
            return {'error': 'Incident not found', 'recommendations': []}

        incident = row_to_dict(inc_row)
        inc_type = incident.get('type', 'accident').lower()
        inc_lat = incident.get('latitude')
        inc_lon = incident.get('longitude')
        vuln_tags = incident.get('vulnerability_tags', [])

        reqs = INCIDENT_CAPABILITY_REQUIREMENTS.get(inc_type, {
            'primary_types': ['ambulance', 'ndrf_team'],
            'secondary_types': ['fire_unit'],
            'required_tags': ['first_aid']
        })

        # Fetch only currently available simulated resources
        cursor.execute("SELECT * FROM resources WHERE status = 'available'")
        avail_rows = cursor.fetchall()

        recommendations = []
        for r_row in avail_rows:
            res = row_to_dict(r_row)
            res_lat = res.get('latitude')
            res_lon = res.get('longitude')
            res_type = res.get('type')
            res_caps = res.get('capabilities', [])

            # Compute distance if coordinates exist
            dist_km = None
            eta_minutes = None
            if inc_lat is not None and inc_lon is not None and res_lat is not None and res_lon is not None:
                dist_km = haversine_distance(inc_lat, inc_lon, res_lat, res_lon)
                # Assume 45 km/h urban emergency response speed
                eta_minutes = max(3, round((dist_km / 45.0) * 60))

            # Score suitability (0 - 100)
            score = 0.0
            reasons = []

            # 1. Type match
            if res_type in reqs['primary_types']:
                score += 45.0
                reasons.append(f"Primary operational match for {inc_type}")
            elif res_type in reqs['secondary_types']:
                score += 25.0
                reasons.append(f"Support tier unit for {inc_type}")
            else:
                score += 10.0
                reasons.append("Secondary general emergency capability")

            # 2. Capability tags overlap
            cap_overlap = [c for c in res_caps if c in reqs.get('required_tags', [])]
            if cap_overlap:
                bonus = len(cap_overlap) * 10.0
                score += bonus
                reasons.append(f"Specialized equipment: {', '.join(cap_overlap)}")

            # 3. Vulnerability handling bonus
            if 'medical_equipment' in vuln_tags and 'als' in res_caps:
                score += 15.0
                reasons.append("Equipped for critical medical life-support")
            if 'trapped' in vuln_tags and ('extrication' in res_caps or 'boat' in res_type):
                score += 15.0
                reasons.append("Extrication / boat gear suitable for trapped civilians")

            # 4. Proximity penalty / bonus
            if dist_km is not None:
                if dist_km <= 3.0:
                    score += 20.0
                    reasons.append(f"Immediate vicinity ({dist_km} km)")
                elif dist_km <= 7.0:
                    score += 12.0
                    reasons.append(f"Close operational radius ({dist_km} km)")
                elif dist_km <= 15.0:
                    score += 5.0
                    reasons.append(f"Moderate distance ({dist_km} km)")
                else:
                    score -= 5.0
                    reasons.append(f"Extended travel distance ({dist_km} km)")
            else:
                reasons.append("Distance estimation pending GPS coordinate fix")

            final_suitability = round(min(100.0, max(10.0, score)), 1)

            recommendations.append({
                'resource_id': res['id'],
                'resource_code': res['resource_code'],
                'name': res['name'],
                'type': res['type'],
                'base_station': res['base_station'],
                'capabilities': res_caps,
                'distance_km': dist_km,
                'eta_minutes': eta_minutes,
                'suitability_score': final_suitability,
                'match_reasons': reasons,
                'is_simulated': bool(res.get('is_simulated', 1))
            })

        # Sort descending by suitability score, then ascending by distance
        recommendations.sort(key=lambda x: (-x['suitability_score'], x['distance_km'] if x['distance_km'] is not None else 999))

        return {
            'incident_id': incident_id,
            'incident_code': incident.get('incident_code'),
            'hazard_type': inc_type,
            'total_available_resources': len(avail_rows),
            'recommendations': recommendations[:5],  # Top 5 best candidates
            'disclaimer': 'Simulated response fleet matching for decision support.'
        }


def assign_resource(incident_id, resource_id, notes="", dispatcher_name="ResQAI Dispatcher"):
    """
    Atomically dispatches a resource to an incident with race-condition protection.
    Uses SQLite immediate transaction to prevent double assignment.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        # Use BEGIN IMMEDIATE to lock writing and prevent concurrent double assignment
        cursor.execute("BEGIN IMMEDIATE")

        # 1. Verify resource availability
        cursor.execute("SELECT * FROM resources WHERE id = ?", (resource_id,))
        res_row = cursor.fetchone()
        if not res_row:
            return {'success': False, 'error': f"Resource with ID {resource_id} does not exist."}

        res = row_to_dict(res_row)
        if res['status'] != 'available':
            return {
                'success': False,
                'error': f"Resource '{res['name']}' ({res['resource_code']}) is currently {res['status']}. Cannot assign."
            }

        # 2. Verify incident existence
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        inc_row = cursor.fetchone()
        if not inc_row:
            return {'success': False, 'error': f"Incident with ID {incident_id} not found."}
        incident = row_to_dict(inc_row)

        # 3. Update resource state to 'dispatched'
        cursor.execute("""
            UPDATE resources
            SET status = 'dispatched',
                assigned_incident_id = ?,
                last_status_update = ?
            WHERE id = ? AND status = 'available'
        """, (incident_id, now_iso, resource_id))

        if cursor.rowcount == 0:
            return {'success': False, 'error': 'Resource assignment collision: Resource was locked by another process.'}

        # 4. Insert into dispatches table
        cursor.execute("""
            INSERT INTO dispatches (incident_id, resource_id, dispatch_time, status, notes, dispatched_by)
            VALUES (?, ?, ?, 'dispatched', ?, ?)
        """, (incident_id, resource_id, now_iso, notes, dispatcher_name))
        dispatch_id = cursor.lastrowid

        # 5. Elevate incident status to 'dispatched' if it was 'reported' or 'verified'
        if incident['status'] in ['reported', 'verified']:
            cursor.execute("""
                UPDATE incidents
                SET status = 'dispatched',
                    updated_at = ?
                WHERE id = ?
            """, (now_iso, incident_id))

        # 6. Generate In-App Alert
        alert_title = f"DISPATCH: {res['name']} Assigned"
        alert_msg = f"{res['name']} ({res['type']}) deployed to {incident['incident_code']} at {incident['location_name']}."
        cursor.execute("""
            INSERT INTO alerts (title, message, severity, incident_id, source, is_acknowledged, created_at)
            VALUES (?, ?, 'warning', ?, 'Dispatch Engine', 0, ?)
        """, (alert_title, alert_msg, incident_id, now_iso))

        # 7. Record Audit Log
        audit_details = json.dumps({
            'incident_code': incident['incident_code'],
            'resource_code': res['resource_code'],
            'dispatch_id': dispatch_id,
            'notes': notes
        })
        cursor.execute("""
            INSERT INTO audit_logs (action, entity_type, entity_id, details, timestamp, actor)
            VALUES ('RESOURCE_DISPATCHED', 'resource', ?, ?, ?, ?)
        """, (resource_id, audit_details, now_iso, dispatcher_name))

        return {
            'success': True,
            'dispatch_id': dispatch_id,
            'incident_id': incident_id,
            'incident_code': incident['incident_code'],
            'resource_id': resource_id,
            'resource_name': res['name'],
            'status': 'dispatched',
            'dispatched_at': now_iso,
            'message': f"Successfully dispatched {res['name']} to {incident['incident_code']}."
        }


def release_resource(resource_id, notes="", actor="ResQAI Dispatcher"):
    """
    Releases a dispatched resource, returning its status to 'available'
    and closing the open dispatch record.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("SELECT * FROM resources WHERE id = ?", (resource_id,))
        res_row = cursor.fetchone()
        if not res_row:
            return {'success': False, 'error': f"Resource with ID {resource_id} not found."}

        res = row_to_dict(res_row)
        prev_incident_id = res.get('assigned_incident_id')

        # Update resource back to available
        cursor.execute("""
            UPDATE resources
            SET status = 'available',
                assigned_incident_id = NULL,
                last_status_update = ?
            WHERE id = ?
        """, (now_iso, resource_id))

        # Close active dispatch record
        if prev_incident_id:
            cursor.execute("""
                UPDATE dispatches
                SET status = 'completed',
                    resolution_time = ?,
                    notes = CASE WHEN notes IS NULL THEN ? ELSE notes || ' | ' || ? END
                WHERE resource_id = ? AND incident_id = ? AND status != 'completed'
            """, (now_iso, f"Released: {notes}", f"Released: {notes}", resource_id, prev_incident_id))

        # Record audit log
        audit_details = json.dumps({
            'resource_code': res['resource_code'],
            'previous_incident_id': prev_incident_id,
            'notes': notes
        })
        cursor.execute("""
            INSERT INTO audit_logs (action, entity_type, entity_id, details, timestamp, actor)
            VALUES ('RESOURCE_RELEASED', 'resource', ?, ?, ?, ?)
        """, (resource_id, audit_details, now_iso, actor))

        return {
            'success': True,
            'resource_id': resource_id,
            'resource_code': res['resource_code'],
            'status': 'available',
            'released_at': now_iso,
            'message': f"Resource {res['name']} has been released and is now Available."
        }
