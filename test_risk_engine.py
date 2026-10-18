"""
ResQAI - AI Risk Intelligence Engine Unit Tests
Tests scoring boundaries, invalid inputs, vulnerability weighting, and weather amplification.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.risk_engine import calculate_risk


class TestRiskEngine(unittest.TestCase):

    def test_baseline_scoring(self):
        """Test baseline hazard profiles without extra factors."""
        inc = {'type': 'flood', 'reported_severity': 'minor', 'affected_people': 0}
        res = calculate_risk(inc)
        self.assertGreaterEqual(res['score'], 35.0)
        self.assertIn(res['category'], ['Medium', 'Low'])
        self.assertIsInstance(res['factor_breakdown'], list)

    def test_critical_flood_scenario(self):
        """Test extreme compound flood with mass affected population and trapped civilians."""
        inc = {
            'type': 'flood',
            'reported_severity': 'catastrophic',
            'affected_people': 120,
            'vulnerability_tags': ['trapped', 'elderly', 'medical_equipment'],
            'latitude': 18.53,
            'longitude': 73.85
        }
        weather = {'precipitation': 35.0, 'wind_speed': 20.0, 'temperature': 24.0}
        res = calculate_risk(inc, weather)
        self.assertGreaterEqual(res['score'], 85.0)
        self.assertEqual(res['category'], 'Critical')
        self.assertEqual(res['confidence'], 'High')

    def test_negative_population_clamped(self):
        """Test defensive handling of negative affected people."""
        inc = {'type': 'fire', 'reported_severity': 'moderate', 'affected_people': -15}
        res = calculate_risk(inc)
        self.assertGreater(res['score'], 0)
        self.assertTrue(any('clamped' in str(n) for n in res['missing_data_notes']))

    def test_unknown_hazard_type_graceful_fallback(self):
        """Test unrecognized hazard type assigned default baseline without crashing."""
        inc = {'type': 'space_debris_strike', 'reported_severity': 'moderate', 'affected_people': 3}
        res = calculate_risk(inc)
        self.assertIsNotNone(res['score'])
        self.assertTrue(any('Unrecognized' in str(n) for n in res['missing_data_notes']))

    def test_vulnerability_capping(self):
        """Test that vulnerability points do not exceed maximum cap of 25.0 points."""
        inc = {
            'type': 'accident',
            'reported_severity': 'minor',
            'affected_people': 1,
            'vulnerability_tags': ['trapped', 'medical_equipment', 'mobility_impaired', 'elderly', 'children']
        }
        res = calculate_risk(inc)
        vuln_factor = next((f for f in res['factor_breakdown'] if 'Vulnerability Needs' in f['factor']), None)
        self.assertIsNotNone(vuln_factor)
        self.assertLessEqual(vuln_factor['points'], 25.0)

    def test_weather_amplification(self):
        """Test that heavy rainfall amplifies flood risk score."""
        inc = {'type': 'flood', 'reported_severity': 'moderate', 'affected_people': 5}
        res_calm = calculate_risk(inc, {'precipitation': 0.0, 'wind_speed': 5.0})
        res_storm = calculate_risk(inc, {'precipitation': 30.0, 'wind_speed': 20.0})
        self.assertGreater(res_storm['score'], res_calm['score'])


if __name__ == '__main__':
    unittest.main()
