"""Regression checks for staffing changes; run: python3 -m unittest test_simulate."""
import unittest
from unittest.mock import patch

import numpy as np
import simulate as sim


class StaffingBoundaryTests(unittest.TestCase):
    def run_fixed(self, arrivals, staffing, service=120.0, balk=None):
        cfg = sim.SimConfig(
            hourly_lambda=[0] * len(staffing), class_mix={2: 1.0},
            mean_service_min=service, servers_by_hour=staffing,
            days=1, balk_queue=balk,
        )
        reqs = [sim.Request(i + 1, 1, 2, t) for i, t in enumerate(arrivals)]
        with patch.object(sim, "_generate_arrivals", return_value=reqs), \
                patch.object(sim, "_service_sample", return_value=service):
            return sim.run_day(cfg, np.random.default_rng(0), 1, 1)[0]

    def test_increase_starts_waiter_at_boundary_without_other_event(self):
        reqs = self.run_fixed([0, 1], [1, 2])
        self.assertEqual(reqs[1].t_start, 60.0)

    def test_decrease_preserves_service_and_limits_new_starts(self):
        reqs = self.run_fixed([0, 1, 61], [2, 1])
        self.assertEqual([r.t_end for r in reqs[:2]], [120.0, 121.0])
        self.assertEqual(reqs[2].t_start, 121.0)

    def test_capacity_update_precedes_balking_at_same_instant(self):
        reqs = self.run_fixed([0, 1, 60], [1, 2], balk=1)
        self.assertEqual(reqs[1].t_start, 60.0)
        self.assertFalse(reqs[2].balked)
        self.assertEqual(reqs[2].t_start, 120.0)


if __name__ == "__main__":
    unittest.main()
