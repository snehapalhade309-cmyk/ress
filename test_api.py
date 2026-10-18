"""
ResQAI - REST API Endpoints Integration Tests
Tests Flask routes, JSON contracts, validation errors, and end-to-end incident lifecycle.
"""

import os
import sys
import unittest
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app import app
from backend.seed_data import seed_database


class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        seed_database(force_reset=True)
        cls.client = app.test_client()

    def test_health_endpoint(self):
        """Test GET /api/health returns operational status."""
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'operational')
        self.assertIn('integrations', data)

    def test_stats_endpoint(self):
        """Test GET /api/stats returns aggregated metrics."""
        resp = self.client.get('/api/stats')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('incidents', data)
        self.assertIn('resources', data)
        self.assertIn('shelters', data)

    def test_create_incident_validations(self):
        """Test POST /api/incidents handles valid inputs and rejects missing fields."""
        # 1. Missing required field
        bad_resp = self.client.post('/api/incidents', json={'type': 'flood'})
        self.assertEqual(bad_resp.status_code, 400)

        # 2. Valid creation
        good_resp = self.client.post('/api/incidents', json={
            'type': 'flood',
            'title': 'Test API Flash Flood',
            'location_name': 'Sector 4 Canal Bank',
            'latitude': 18.5204,
            'longitude': 73.8567,
            'reported_severity': 'severe',
            'affected_people': 35,
            'vulnerability_tags': ['trapped', 'elderly'],
            'description': 'Integration test incident'
        })
        self.assertEqual(good_resp.status_code, 201)
        res_data = good_resp.get_json()
        self.assertIn('incident', res_data)
        self.assertIn('risk_evaluation', res_data)
        self.assertGreaterEqual(res_data['risk_evaluation']['score'], 75.0)

    def test_evacuation_route_endpoint(self):
        """Test GET /api/routes/evacuation returns valid driving geometry or geodesic fallback."""
        resp = self.client.get('/api/routes/evacuation?origin_lat=18.5204&origin_lon=73.8567&dest_lat=18.5775&dest_lon=73.7583')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('distance_km', data)
        self.assertIn('geometry', data)
        self.assertIn('safety_disclaimer', data)

    def test_alerts_and_acknowledgement(self):
        """Test alerts listing and acknowledgment flow."""
        # Get alerts
        resp = self.client.get('/api/alerts')
        self.assertEqual(resp.status_code, 200)
        alerts = resp.get_json()
        self.assertGreater(len(alerts), 0)

        first_id = alerts[0]['id']
        # Acknowledge
        ack_resp = self.client.post(f'/api/alerts/{first_id}/acknowledge')
        self.assertEqual(ack_resp.status_code, 200)


if __name__ == '__main__':
    unittest.main()
