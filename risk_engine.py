"""
ResQAI - AI Risk Intelligence Engine (Deterministic Heuristic Model v2.1)
Provides transparent, explainable, and multi-factor emergency risk assessment.
"""

from datetime import datetime, timezone
import math


# Base risk weights per hazard type (0-100 scale anchor)
HAZARD_BASE_WEIGHTS = {
    'flood': 35.0,           # High kinetic water hazard, rapid rise risk, submerged infra
    'landslide': 40.0,       # Mass soil movement, structural collapse, cut off access
    'fire': 35.0,            # Rapid spread velocity, smoke toxicity, structural ignition
    'earthquake': 45.0,      # Wide area structural compromise, secondary liquefaction/aftershocks
    'severe_weather': 25.0,  # Gale winds, heavy downpour, lightning strikes
    'accident': 25.0,        # Traffic collision, structural failure, localized hazard
    'industrial': 35.0       # Toxic fumes, chemical hazard, containment failure
}

# Reported severity multipliers
SEVERITY_POINTS = {
    'minor': 5.0,
    'moderate': 15.0,
    'severe': 28.0,
    'catastrophic': 40.0
}

# Voluntarily reported vulnerability weights
VULNERABILITY_WEIGHTS = {
    'elderly': 7.0,
    'children': 6.0,
    'mobility_impaired': 9.0,
    'medical_equipment': 12.0,   # Requires uninterrupted electricity / oxygen
    'trapped': 15.0              # Immediate peril / waterbound / structural entrapment
}


def calculate_risk(incident_data, weather_data=None):
    """
    Computes a deterministic, explainable risk score (0-100) based on incident parameters
    and environmental weather amplification.

    Args:
        incident_data (dict):
            - type: str (e.g. 'flood', 'fire')
            - reported_severity: str ('minor', 'moderate', 'severe', 'catastrophic')
            - affected_people: int or float
            - vulnerability_tags: list of str
            - latitude: float (optional)
            - longitude: float (optional)
        weather_data (dict, optional):
            - precipitation: float (mm)
            - wind_speed: float (km/h)
            - temperature: float (°C)

    Returns:
        dict:
            - score: float (0.0 to 100.0)
            - category: 'Low' | 'Medium' | 'High' | 'Critical'
            - factor_breakdown: list of dicts with explanation and points
            - missing_data_notes: list of str
            - confidence: 'High' | 'Medium' | 'Low'
            - calculated_at: ISO string
            - engine_version: str
            - limitations: str
    """
    factors = []
    missing_notes = []
    total_score = 0.0

    # 1. Hazard Type Base Weight
    inc_type = str(incident_data.get('type', 'accident')).lower().strip()
    if inc_type in HAZARD_BASE_WEIGHTS:
        base_pts = HAZARD_BASE_WEIGHTS[inc_type]
        factors.append({
            'factor': f"Hazard Category ({inc_type.replace('_', ' ').title()})",
            'points': base_pts,
            'description': f"Baseline hazard profile for {inc_type.replace('_', ' ')}"
        })
    else:
        base_pts = 20.0
        missing_notes.append(f"Unrecognized incident type '{inc_type}'. Assigned default baseline 20.0.")
        factors.append({
            'factor': f"Unknown Hazard ({inc_type})",
            'points': base_pts,
            'description': "Default baseline hazard score"
        })
    total_score += base_pts

    # 2. Reported Severity
    sev = str(incident_data.get('reported_severity', 'moderate')).lower().strip()
    if sev in SEVERITY_POINTS:
        sev_pts = SEVERITY_POINTS[sev]
        factors.append({
            'factor': f"Reported Severity ({sev.title()})",
            'points': sev_pts,
            'description': f"Initial on-scene reported urgency level"
        })
    else:
        sev_pts = SEVERITY_POINTS['moderate']
        missing_notes.append(f"Severity '{sev}' unspecified or invalid; defaulted to 'moderate'.")
        factors.append({
            'factor': "Default Severity (Moderate)",
            'points': sev_pts,
            'description': "Default moderate severity assigned"
        })
    total_score += sev_pts

    # 3. Affected Population Scale
    try:
        raw_people = incident_data.get('affected_people', 0)
        people = int(float(raw_people)) if raw_people is not None else 0
        if people < 0:
            people = 0
            missing_notes.append("Negative affected people count received; clamped to 0.")
    except (ValueError, TypeError):
        people = 0
        missing_notes.append("Invalid affected people format; defaulted to 0.")

    if people == 0:
        pop_pts = 2.0
        factors.append({
            'factor': "Affected Population (0 reported)",
            'points': pop_pts,
            'description': "No civilian casualties currently indicated"
        })
    elif people <= 5:
        pop_pts = 8.0
        factors.append({
            'factor': f"Affected Population ({people} people)",
            'points': pop_pts,
            'description': "Small cluster impact"
        })
    elif people <= 20:
        pop_pts = 16.0
        factors.append({
            'factor': f"Affected Population ({people} people)",
            'points': pop_pts,
            'description': "Moderate community group at risk"
        })
    elif people <= 50:
        pop_pts = 24.0
        factors.append({
            'factor': f"Affected Population ({people} people)",
            'points': pop_pts,
            'description': "Significant civilian count in hazard envelope"
        })
    else:
        pop_pts = 30.0
        factors.append({
            'factor': f"Affected Population ({people}+ mass impact)",
            'points': pop_pts,
            'description': "Mass casualty / high-density humanitarian hazard"
        })
    total_score += pop_pts

    # 4. Voluntarily Reported Vulnerability Needs
    vuln_tags = incident_data.get('vulnerability_tags', [])
    if isinstance(vuln_tags, str):
        vuln_tags = [t.strip().lower() for t in vuln_tags.split(',') if t.strip()]
    elif not isinstance(vuln_tags, list):
        vuln_tags = []

    vuln_pts_total = 0.0
    active_vulns = []
    for tag in vuln_tags:
        cleaned_tag = str(tag).lower().strip()
        if cleaned_tag in VULNERABILITY_WEIGHTS:
            pts = VULNERABILITY_WEIGHTS[cleaned_tag]
            vuln_pts_total += pts
            active_vulns.append(f"{cleaned_tag.replace('_', ' ').title()} (+{pts} pts)")

    # Cap maximum vulnerability modifier to 25.0 points to prevent single-factor runaway
    capped_vuln_pts = min(25.0, vuln_pts_total)
    if active_vulns:
        factors.append({
            'factor': f"Vulnerability Needs ({len(active_vulns)} flagged)",
            'points': capped_vuln_pts,
            'description': "; ".join(active_vulns) + (f" (capped at {capped_vuln_pts})" if vuln_pts_total > 25.0 else "")
        })
        total_score += capped_vuln_pts
    else:
        factors.append({
            'factor': "Vulnerability Needs (None declared)",
            'points': 0.0,
            'description': "No special medical, mobility or entrapment needs reported"
        })

    # 5. Environmental & Climate Weather Amplification
    weather_pts = 0.0
    weather_desc = []
    if weather_data and isinstance(weather_data, dict):
        precip = weather_data.get('precipitation', 0.0)
        wind = weather_data.get('wind_speed', 0.0)
        temp = weather_data.get('temperature', 25.0)

        # Precipitation compound risk for flood / landslide
        if inc_type in ['flood', 'landslide']:
            if precip >= 25.0:
                weather_pts += 15.0
                weather_desc.append(f"Heavy rainfall ({precip:.1f} mm/hr) escalates water/soil saturation")
            elif precip >= 10.0:
                weather_pts += 10.0
                weather_desc.append(f"Moderate rainfall ({precip:.1f} mm/hr) elevates flood risk")
            elif precip >= 3.0:
                weather_pts += 4.0
                weather_desc.append(f"Light active rain ({precip:.1f} mm/hr)")

        # Wind compound risk for fire / severe weather
        if inc_type in ['fire', 'severe_weather']:
            if wind >= 45.0:
                weather_pts += 14.0
                weather_desc.append(f"High wind velocity ({wind:.1f} km/h) dramatically accelerates spread")
            elif wind >= 25.0:
                weather_pts += 8.0
                weather_desc.append(f"Breezy conditions ({wind:.1f} km/h) assist ember propagation")

        # Temperature compound risk for fire
        if inc_type == 'fire' and temp >= 38.0:
            weather_pts += 6.0
            weather_desc.append(f"Extreme ambient heat ({temp:.1f} °C) heightens flammability")

        if weather_pts > 0:
            factors.append({
                'factor': "Climate & Weather Amplification",
                'points': weather_pts,
                'description': "; ".join(weather_desc)
            })
            total_score += weather_pts
        else:
            factors.append({
                'factor': "Environmental Weather Impact",
                'points': 0.0,
                'description': "Current weather parameters within safe / non-amplifying threshold"
            })
    else:
        missing_notes.append("Real-time localized weather data not linked; weather amplification factor unapplied.")

    # Bound final score to 5.0 - 100.0
    final_score = round(max(5.0, min(100.0, total_score)), 1)

    # Classify into emergency tier
    if final_score < 30.0:
        category = 'Low'
    elif final_score < 55.0:
        category = 'Medium'
    elif final_score < 78.0:
        category = 'High'
    else:
        category = 'Critical'

    # Determine confidence
    has_coords = incident_data.get('latitude') is not None and incident_data.get('longitude') is not None
    if has_coords and weather_data:
        confidence = 'High'
    elif has_coords or weather_data:
        confidence = 'Medium'
    else:
        confidence = 'Moderate (Awaiting GPS & Sensor Telementry)'

    return {
        'score': final_score,
        'category': category,
        'factor_breakdown': factors,
        'missing_data_notes': missing_notes,
        'confidence': confidence,
        'calculated_at': datetime.now(timezone.utc).isoformat(),
        'engine_version': 'ResQAI Deterministic Heuristic Model v2.1',
        'limitations': 'Advisory decision-support heuristic for incident prioritization. Must be verified alongside official emergency service directives.'
    }
