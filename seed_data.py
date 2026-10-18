"""
ResQAI - Realistic Emergency Demonstration Seed Data
Populates SQLite database with structured incidents, simulated rescue fleet,
evacuation shelters, and initial alerts.
"""

from datetime import datetime, timezone
import json
from backend.database import get_db, init_db
from backend.risk_engine import calculate_risk
from backend.audit_service import log_event


def seed_database(force_reset=False):
    """Populate database with initial emergency management dataset."""
    init_db()

    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()

        # Check if already seeded
        cursor.execute("SELECT COUNT(*) as count FROM incidents")
        count = cursor.fetchone()['count']
        if count > 0 and not force_reset:
            return {'message': 'Database already contains data. Skipped seeding.', 'seeded': False}

        if force_reset:
            cursor.execute("DELETE FROM dispatches")
            cursor.execute("DELETE FROM alerts")
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM resources")
            cursor.execute("DELETE FROM shelters")
            cursor.execute("DELETE FROM incidents")
            try:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('incidents', 'resources', 'shelters', 'dispatches', 'alerts', 'audit_logs')")
            except Exception:
                pass

        # 1. Seed Shelters
        shelters_data = [
            (
                'SHL-01', 'Balewadi Sports Complex Evacuation Center', 'stadium',
                18.5775, 73.7583, 'Balewadi Stadium Road, Pune', 1500, 320,
                json.dumps(['medical', 'food', 'power_backup', 'clean_water', 'wheelchair_accessible']),
                'verified', '+91-20-2569-8001', now_iso
            ),
            (
                'SHL-02', 'Shivajinagar College Gymnasium Emergency Shelter', 'school',
                18.5284, 73.8567, 'Wellesley Road, Shivajinagar, Pune', 800, 160,
                json.dumps(['medical', 'food', 'power_backup', 'clean_water']),
                'verified', '+91-20-2569-8002', now_iso
            ),
            (
                'SHL-03', 'Hadapsar Municipal High-Ground Relief Center', 'community_center',
                18.5050, 73.9310, 'Gadital High Ground, Hadapsar, Pune', 600, 85,
                json.dumps(['food', 'clean_water', 'power_backup']),
                'verified', '+91-20-2569-8003', now_iso
            ),
            (
                'SHL-04', 'Kothrud Community Relief Camp', 'relief_camp',
                18.5020, 73.8040, 'Near Karve Statue, Kothrud, Pune', 450, 210,
                json.dumps(['medical', 'clean_water', 'wheelchair_accessible']),
                'verified', '+91-20-2569-8004', now_iso
            ),
            (
                'SHL-05', 'Pimpri Civic Administrative Disaster Shelter', 'community_center',
                18.6279, 73.7990, 'Old Mumbai-Pune Highway, Pimpri', 1000, 140,
                json.dumps(['medical', 'food', 'power_backup', 'clean_water', 'wheelchair_accessible']),
                'verified', '+91-20-2569-8005', now_iso
            )
        ]

        cursor.executemany("""
            INSERT INTO shelters (
                shelter_code, name, type, latitude, longitude, address,
                total_capacity, current_occupancy, amenities, verification_status,
                contact_phone, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, shelters_data)

        # 2. Seed Resources (Simulated Fleet)
        resources_data = [
            (
                'RES-AMB-01', 'ALS Trauma Ambulance 01', 'ambulance',
                json.dumps(['als', 'first_aid', 'trauma', 'oxygen']),
                18.5284, 73.8439, 'Sassoon General Hospital Outpost', 'available', None, now_iso, 1
            ),
            (
                'RES-AMB-02', 'BLS Rapid Response Ambulance 02', 'ambulance',
                json.dumps(['bls', 'first_aid', 'patient_transport']),
                18.5912, 73.7820, 'Aundh District Hospital', 'available', None, now_iso, 1
            ),
            (
                'RES-AMB-03', 'Mobile Intensive Care Ambulance 03', 'ambulance',
                json.dumps(['als', 'pediatric', 'ventilator', 'oxygen']),
                18.5020, 73.8150, 'Kothrud Medical Station', 'available', None, now_iso, 1
            ),
            (
                'RES-FIR-01', 'Heavy Water Tender Unit 101', 'fire_unit',
                json.dumps(['firefighting', 'water_tender', 'foam_discharge']),
                18.5300, 73.8480, 'Shivajinagar Central Fire HQ', 'available', None, now_iso, 1
            ),
            (
                'RES-FIR-02', 'Industrial Hazmat Foam Unit 102', 'fire_unit',
                json.dumps(['firefighting', 'hazmat', 'gas_containment']),
                18.6320, 73.8310, 'Bhosari MIDC Fire Depot', 'available', None, now_iso, 1
            ),
            (
                'RES-BOT-01', 'Gemini Inflatable Flood Rescue Craft 201', 'rescue_boat',
                json.dumps(['water_rescue', 'evacuation', 'shallow_draft']),
                18.5240, 73.8720, 'Yerawada Riverbank Outpost', 'available', None, now_iso, 1
            ),
            (
                'RES-BOT-02', 'Tactical Motorized Swiftwater Boat 202', 'rescue_boat',
                json.dumps(['water_rescue', 'night_search', 'swiftwater']),
                18.5080, 73.8340, 'Sinhagad River Logistics Depot', 'available', None, now_iso, 1
            ),
            (
                'RES-NDR-01', 'NDRF Battalion Alpha Search Team', 'ndrf_team',
                json.dumps(['search_and_rescue', 'structural_collapse', 'k9', 'water_rescue']),
                18.5750, 73.8690, 'Khadki Disaster Command HQ', 'available', None, now_iso, 1
            ),
            (
                'RES-NDR-02', 'NDRF Quick Response Team Bravo', 'ndrf_team',
                json.dumps(['search_and_rescue', 'debris_clearing', 'first_aid']),
                18.5150, 73.7920, 'Warje Emergency Reserve Hub', 'available', None, now_iso, 1
            ),
            (
                'RES-HVY-01', 'Heavy Extrication & Debris Crane 301', 'heavy_rescue',
                json.dumps(['extrication', 'heavy_machinery', 'concrete_cutting']),
                18.4900, 73.8700, 'Swargate Civil Engineering Yard', 'available', None, now_iso, 1
            )
        ]

        cursor.executemany("""
            INSERT INTO resources (
                resource_code, name, type, capabilities, latitude, longitude,
                base_station, status, assigned_incident_id, last_status_update, is_simulated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, resources_data)

        # 3. Seed Incidents with Calculated Risk
        raw_incidents = [
            {
                'incident_code': 'INC-2026-001',
                'type': 'flood',
                'title': 'Mula River Flash Inundation & Bank Overflow',
                'location_name': 'Sangamwadi Bridge Lowlands, Pune',
                'latitude': 18.5312,
                'longitude': 73.8682,
                'reported_severity': 'severe',
                'affected_people': 42,
                'vulnerability_tags': ['elderly', 'trapped', 'mobility_impaired'],
                'description': 'Rapidly rising water levels due to dam discharge upstream. Multiple single-story homes flooded with 4-5 feet of standing water. Several elderly residents unable to self-evacuate.',
                'reporter_name': 'Anand Verma (Ward Officer)',
                'reporter_contact': '+91-98220-11223',
                'status': 'verified',
                'is_demo': 1
            },
            {
                'incident_code': 'INC-2026-002',
                'type': 'landslide',
                'title': 'Katraj Ghat Ridge Mudslide & Road Blockage',
                'location_name': 'Katraj Tunnel Bypass Corridor',
                'latitude': 18.4485,
                'longitude': 73.8589,
                'reported_severity': 'severe',
                'affected_people': 15,
                'vulnerability_tags': ['trapped'],
                'description': 'Heavy hillside slope failure deposited boulder debris across both lanes. Two passenger vehicles partially trapped in embankment mud.',
                'reporter_name': 'Highway Patrol Unit 4',
                'reporter_contact': '+91-98220-44556',
                'status': 'reported',
                'is_demo': 1
            },
            {
                'incident_code': 'INC-2026-003',
                'type': 'fire',
                'title': 'Industrial Chemical Warehouse Blaze',
                'location_name': 'Bhosari MIDC Industrial Zone',
                'latitude': 18.6280,
                'longitude': 73.8420,
                'reported_severity': 'catastrophic',
                'affected_people': 28,
                'vulnerability_tags': ['medical_equipment'],
                'description': 'Explosive drum rupture in solvent storage unit. Thick toxic plume moving south-west. Factory floor evacuated but adjacent clinic reports vulnerable patients.',
                'reporter_name': 'Security Chief R. Shinde',
                'reporter_contact': '+91-98220-77889',
                'status': 'reported',
                'is_demo': 1
            },
            {
                'incident_code': 'INC-2026-004',
                'type': 'accident',
                'title': 'Multi-Vehicle Collision with Fuel Leakage',
                'location_name': 'Wakad Highway Flyover Ramp',
                'latitude': 18.5987,
                'longitude': 73.7663,
                'reported_severity': 'moderate',
                'affected_people': 8,
                'vulnerability_tags': ['children'],
                'description': 'Collision involving mini-bus and cargo truck in rainy conditions. Fuel spill on asphalt; 3 injured passengers require immediate hospital transfer.',
                'reporter_name': 'Traffic Warden D. Patil',
                'reporter_contact': '+91-98220-99001',
                'status': 'reported',
                'is_demo': 1
            },
            {
                'incident_code': 'INC-2026-005',
                'type': 'severe_weather',
                'title': 'Gale Storm Tree Fall on Overhead Transit Wire',
                'location_name': 'Shivajinagar Bus Station Terminal',
                'latitude': 18.5314,
                'longitude': 73.8446,
                'reported_severity': 'minor',
                'affected_people': 4,
                'vulnerability_tags': ['elderly'],
                'description': 'High wind gusts snapped large banyan tree limb onto electric distribution cables. Minor burns reported; traffic transit halted.',
                'reporter_name': 'Station Master Joshi',
                'reporter_contact': '+91-98220-33445',
                'status': 'reported',
                'is_demo': 1
            }
        ]

        for item in raw_incidents:
            # Calculate risk using deterministic engine
            risk = calculate_risk(item, weather_data={'precipitation': 18.0, 'wind_speed': 25.0, 'temperature': 24.0})

            cursor.execute("""
                INSERT INTO incidents (
                    incident_code, type, title, location_name, latitude, longitude,
                    reported_severity, affected_people, vulnerability_tags, description,
                    reporter_name, reporter_contact, calculated_risk_score, risk_category,
                    risk_factors_json, status, is_demo, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item['incident_code'], item['type'], item['title'], item['location_name'],
                item['latitude'], item['longitude'], item['reported_severity'], item['affected_people'],
                json.dumps(item['vulnerability_tags']), item['description'], item['reporter_name'],
                item['reporter_contact'], risk['score'], risk['category'],
                json.dumps(risk['factor_breakdown']), item['status'], item['is_demo'],
                now_iso, now_iso
            ))

        # 4. Seed Alerts
        cursor.execute("SELECT id FROM incidents WHERE incident_code = 'INC-2026-001'")
        inc1_row = cursor.fetchone()
        inc1_id = inc1_row['id'] if inc1_row else None

        cursor.execute("SELECT id FROM incidents WHERE incident_code = 'INC-2026-003'")
        inc3_row = cursor.fetchone()
        inc3_id = inc3_row['id'] if inc3_row else None

        alerts_data = [
            (
                'CRITICAL: Flash Flood Evacuation Priority',
                'Mula River overflow at Sangamwadi Bridge (INC-2026-001). Risk Score 88.0. Watercraft & boat rescue mobilization advised.',
                'critical', inc1_id, 'Risk Intelligence Engine', 0, now_iso
            ),
            (
                'HIGH SEVERITY: Chemical Fire Plume Alert',
                'Hazardous smoke plume at Bhosari MIDC (INC-2026-003). Hazmat containment units & downwind air safety perimeter requested.',
                'critical', inc3_id, 'Risk Intelligence Engine', 0, now_iso
            ),
            (
                'WEATHER ADVISORY: Heavy Monsoon Rain Band',
                'Localized precipitation forecast exceeding 20 mm/hr in river basin zones. Maintain heightened alert status.',
                'warning', None, 'Open-Meteo Weather Integration', 0, now_iso
            )
        ]

        cursor.executemany("""
            INSERT INTO alerts (
                title, message, severity, incident_id, source, is_acknowledged, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, alerts_data)

        # 5. Log audit event
        log_event('DATABASE_SEEDED', 'system', None, {'incidents': len(raw_incidents), 'resources': len(resources_data), 'shelters': len(shelters_data)}, 'system', conn=conn)

    return {'message': 'Database successfully seeded with realistic emergency dataset.', 'seeded': True}


if __name__ == '__main__':
    res = seed_database(force_reset=True)
    print(res)
