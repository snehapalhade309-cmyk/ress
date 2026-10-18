"""
ResQAI - Smart Dispatch & Double-Assignment Protection Tests
Verifies suitability matching, atomic dispatch transactions, and concurrency locking.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import init_db, get_db
from backend.seed_data import seed_database
from backend.dispatch_engine import get_recommendations, assign_resource, release_resource


class TestSmartDispatch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database(force_reset=True)
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM incidents WHERE incident_code = 'INC-2026-001'")
            cls.inc1_id = c.fetchone()['id']
            c.execute("SELECT id FROM incidents WHERE incident_code = 'INC-2026-002'")
            cls.inc2_id = c.fetchone()['id']

    def test_flood_recommendations_suitability(self):
        """Test that flood incidents prioritize watercraft and NDRF rescue teams."""
        recs = get_recommendations(self.inc1_id)
        self.assertIn('recommendations', recs)
        self.assertGreater(len(recs['recommendations']), 0)

        top = recs['recommendations'][0]
        # Top recommended unit for flood must be boat or ndrf
        self.assertIn(top['type'], ['rescue_boat', 'ndrf_team'])
        self.assertGreaterEqual(top['suitability_score'], 50.0)

    def test_atomic_assignment_and_double_dispatch_lock(self):
        """Test that a dispatched unit cannot be assigned to another incident concurrently."""
        recs = get_recommendations(self.inc1_id)
        target_res_id = recs['recommendations'][0]['resource_id']
        unit_name = recs['recommendations'][0]['name']

        # 1. First assignment succeeds
        res1 = assign_resource(incident_id=self.inc1_id, resource_id=target_res_id, notes="Initial primary response")
        self.assertTrue(res1['success'])
        self.assertEqual(res1['status'], 'dispatched')

        # 2. Second assignment of same resource MUST FAIL with conflict error
        res2 = assign_resource(incident_id=self.inc2_id, resource_id=target_res_id, notes="Conflicting assignment")
        self.assertFalse(res2['success'])
        self.assertIn('Cannot assign', res2['error'])

        # 3. Release resource back to available
        rel = release_resource(resource_id=target_res_id, notes="Mission resolved")
        self.assertTrue(rel['success'])
        self.assertEqual(rel['status'], 'available')

        # 4. Now assignment should succeed again
        res3 = assign_resource(incident_id=self.inc2_id, resource_id=target_res_id, notes="Secondary redeployment")
        self.assertTrue(res3['success'])

        # Clean up
        release_resource(resource_id=target_res_id)


if __name__ == '__main__':
    unittest.main()
