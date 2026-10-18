"""
ResQAI - AI Summarization & Decision Support Service
Integrates with local Ollama LLM (if installed & active) with deterministic rule-based fallback.
"""

import time
import requests
from datetime import datetime, timezone

_INTEGRATION_STATUS = {
    'name': 'Local AI (Ollama Service)',
    'status': 'offline',
    'last_checked': None,
    'last_success': None,
    'last_error': None,
    'latency_ms': None,
    'endpoint': 'http://localhost:11434',
    'auth_required': False,
    'rate_limit': 'Local host compute',
    'attribution': 'Local inference engine'
}


def check_ollama_status():
    """Check if local Ollama daemon is active and responsive."""
    global _INTEGRATION_STATUS
    start_t = time.time()
    _INTEGRATION_STATUS['last_checked'] = datetime.now(timezone.utc).isoformat()

    try:
        resp = requests.get('http://localhost:11434/api/tags', timeout=1.5)
        latency = int((time.time() - start_t) * 1000)
        _INTEGRATION_STATUS['latency_ms'] = latency

        if resp.status_code == 200:
            models = resp.json().get('models', [])
            _INTEGRATION_STATUS['status'] = 'operational'
            _INTEGRATION_STATUS['last_success'] = datetime.now(timezone.utc).isoformat()
            _INTEGRATION_STATUS['last_error'] = None
            return True, [m.get('name') for m in models]
        else:
            _INTEGRATION_STATUS['status'] = 'degraded'
            _INTEGRATION_STATUS['last_error'] = f"Status {resp.status_code}"
            return False, []
    except Exception as e:
        _INTEGRATION_STATUS['status'] = 'offline'
        _INTEGRATION_STATUS['last_error'] = 'Ollama service not running locally (Normal in standard setups)'
        return False, []


def generate_incident_ai_brief(incident_data, risk_data, weather_data=None):
    """
    Generate an emergency decision-support briefing.
    Uses local Ollama if available; otherwise uses deterministic rule-based synthesis.
    """
    inc_type = str(incident_data.get('type', 'accident')).title()
    title = incident_data.get('title', 'Emergency Incident')
    location = incident_data.get('location_name', 'Unknown Location')
    severity = str(incident_data.get('reported_severity', 'moderate')).upper()
    people = incident_data.get('affected_people', 0)
    vulns = incident_data.get('vulnerability_tags', [])
    score = risk_data.get('score', 0)
    category = risk_data.get('category', 'Medium')

    is_ollama_up, models = check_ollama_status()

    if is_ollama_up and models:
        # Attempt prompt to Ollama
        model_to_use = models[0]
        prompt = (
            f"You are ResQAI emergency incident analyst. Write a concise 3-bullet emergency action brief for: "
            f"Type: {inc_type}, Title: {title}, Location: {location}, Severity: {severity}, "
            f"Affected: {people}, Vulnerabilities: {', '.join(vulns)}, Calculated Risk: {score}/100 ({category}). "
            f"Return 3 short tactical recommendations for first responders."
        )
        try:
            r = requests.post('http://localhost:11434/api/generate', json={
                'model': model_to_use,
                'prompt': prompt,
                'stream': False
            }, timeout=6.0)
            if r.status_code == 200:
                text = r.json().get('response', '').strip()
                return {
                    'provider': f'Ollama Local LLM ({model_to_use})',
                    'brief': text,
                    'is_ai_generated': True,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
        except Exception:
            pass  # Fall through to deterministic synthesizer

    # High-quality deterministic rule-based emergency tactical synthesizer
    summary = f"Priority {category.upper()} alert ({score}/100) for {inc_type} at {location}."

    actions = []
    if inc_type.lower() == 'flood':
        actions.append("Deploy inflatable water rescue craft and NDRF flood rescue teams to coordinates.")
        actions.append("Establish perimeter 100m outside active water rise zone; identify high-ground evacuation path.")
    elif inc_type.lower() == 'fire':
        actions.append("Mobilize primary fire engine units and foam/water tenders immediately.")
        actions.append("Establish structural perimeter; initiate downwind smoke clearance protocol.")
    elif inc_type.lower() == 'landslide':
        actions.append("Dispatch heavy extrication equipment and canine search & rescue teams.")
        actions.append("Suspend vehicular transit along approach ridge; check slope geotechnical stability.")
    elif inc_type.lower() == 'accident':
        actions.append("Dispatch Advanced Life Support (ALS) ambulances and hydraulic cutter units.")
        actions.append("Establish emergency vehicle corridor with traffic police assistance.")
    else:
        actions.append("Deploy nearest multipurpose disaster response unit to secure the perimeter.")
        actions.append("Initiate rapid civilian census and on-scene triage.")

    # Vulnerability actions
    if 'trapped' in vulns:
        actions.append("URGENT: Extrication priority flag active. Prepare cutting and floatation rescue gear.")
    if 'medical_equipment' in vulns or 'elderly' in vulns:
        actions.append("Medical life-support needs flagged. Route ALS ambulance with portable oxygen units.")

    if weather_data and weather_data.get('precipitation', 0) > 10:
        actions.append("Adverse weather warning: High precipitation will impair visibility and traction.")

    return {
        'provider': 'ResQAI Deterministic Heuristic Synthesizer',
        'summary': summary,
        'tactical_recommendations': actions,
        'is_ai_generated': False,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'safety_notice': 'Heuristic decision support. All operational actions must be vetted by on-scene incident commander.'
    }


def get_integration_status():
    """Return status for System Health dashboard."""
    check_ollama_status()
    return _INTEGRATION_STATUS
