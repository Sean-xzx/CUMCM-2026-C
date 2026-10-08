from pathlib import Path
import tempfile
import unittest

import numpy as np

from solve_q1 import (
    DispatchData,
    DispatchSolution,
    interval_labels_from_end_times,
    interval_plot_coordinates,
    load_attachment1,
    run_pipeline,
    solve_dispatch,
    validate_solution,
)


SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_ATTACHMENT1 = SCRIPT_DIR / "附件1.xlsx"
ATTACHMENT1 = (
    LOCAL_ATTACHMENT1
    if LOCAL_ATTACHMENT1.exists()
    else SCRIPT_DIR.parent / "附件1.xlsx"
)


class TestQuestion1Solver(unittest.TestCase):
    def test_real_attachment_has_144_intervals_and_converts_kw_to_kwh(self):
        data = load_attachment1(ATTACHMENT1)

        self.assertEqual(len(data.price), 144)
        self.assertEqual(data.end_times[0], "00:10")
        self.assertEqual(data.end_times[-1], "0:00+1")
        self.assertAlmostEqual(data.load_energy[0], data.load_power[0] / 6)
        self.assertAlmostEqual(data.pv_energy[0], data.pv_power[0] / 6)

    def test_interval_labels_treat_sheet_times_as_interval_endpoints(self):
        labels = interval_labels_from_end_times(["00:10", "00:20", "0:00+1"])

        self.assertEqual(
            labels,
            ["00:00-00:10", "00:10-00:20", "23:50-24:00"],
        )

    def test_plot_coordinates_place_interval_values_at_centres(self):
        edges, centres = interval_plot_coordinates(2)

        np.testing.assert_allclose(edges, [0.0, 1.0 / 6.0, 2.0 / 6.0])
        np.testing.assert_allclose(centres, [1.0 / 12.0, 3.0 / 12.0])

    def test_solver_shifts_purchase_from_expensive_to_cheap_period(self):
        data = DispatchData(
            end_times=["00:10", "00:20"],
            price=np.array([1.0, 10.0]),
            load_power=np.array([0.0, 600.0]),
            pv_power=np.array([0.0, 0.0]),
            load_energy=np.array([0.0, 100.0]),
            pv_energy=np.array([0.0, 0.0]),
        )

        solution = solve_dispatch(
            data,
            eta=1.0,
            rate_limit=100.0,
            soc_min=0.0,
            soc_max=200.0,
            soc_initial=100.0,
            soc_terminal=100.0,
        )

        self.assertTrue(solution.success)
        self.assertAlmostEqual(solution.q_to_storage[0], 100.0, places=7)
        self.assertAlmostEqual(solution.discharge[1], 100.0, places=7)
        self.assertAlmostEqual(solution.total_cost, 100.0, places=7)

    def test_validation_rejects_charge_discharge_time_overrun(self):
        data = DispatchData(
            end_times=["00:10"],
            price=np.array([1.0]),
            load_power=np.array([0.0]),
            pv_power=np.array([0.0]),
            load_energy=np.array([0.0]),
            pv_energy=np.array([0.0]),
        )
        solution = solve_dispatch(
            data,
            eta=1.0,
            rate_limit=100.0,
            soc_min=0.0,
            soc_max=200.0,
            soc_initial=100.0,
            soc_terminal=100.0,
        )
        solution.pv_to_storage[0] = 60.0
        solution.discharge[0] = 60.0

        with self.assertRaisesRegex(ValueError, "充放电总量超过单时段上限"):
            validate_solution(
                data,
                solution,
                eta=1.0,
                rate_limit=100.0,
                soc_min=0.0,
                soc_max=200.0,
                soc_initial=100.0,
                soc_terminal=100.0,
            )

    def test_validation_rejects_non_finite_values(self):
        data = DispatchData(
            end_times=["00:10"],
            price=np.array([1.0]),
            load_power=np.array([0.0]),
            pv_power=np.array([0.0]),
            load_energy=np.array([0.0]),
            pv_energy=np.array([0.0]),
        )
        solution = DispatchSolution(
            success=True,
            status=0,
            message="synthetic",
            total_cost=0.0,
            pv_to_load=np.array([np.nan]),
            pv_to_storage=np.array([0.0]),
            q_to_load=np.array([0.0]),
            q_to_storage=np.array([0.0]),
            discharge=np.array([0.0]),
            soc=np.array([100.0]),
        )
        with self.assertRaisesRegex(ValueError, "有限数"):
            validate_solution(
                data,
                solution,
                eta=1.0,
                rate_limit=100.0,
                soc_min=0.0,
                soc_max=200.0,
                soc_initial=100.0,
                soc_terminal=100.0,
            )

    def test_validation_reports_allowed_supply_surplus(self):
        data = DispatchData(
            end_times=["00:10"],
            price=np.array([1.0]),
            load_power=np.array([60.0]),
            pv_power=np.array([0.0]),
            load_energy=np.array([10.0]),
            pv_energy=np.array([0.0]),
        )
        solution = DispatchSolution(
            success=True,
            status=0,
            message="synthetic",
            total_cost=12.0,
            pv_to_load=np.array([0.0]),
            pv_to_storage=np.array([0.0]),
            q_to_load=np.array([12.0]),
            q_to_storage=np.array([0.0]),
            discharge=np.array([0.0]),
            soc=np.array([100.0]),
        )
        validation = validate_solution(
            data,
            solution,
            eta=1.0,
            rate_limit=100.0,
            soc_min=0.0,
            soc_max=200.0,
            soc_initial=100.0,
            soc_terminal=100.0,
        )
        self.assertAlmostEqual(validation["max_supply_surplus_kwh"], 2.0)

    def test_pipeline_creates_verified_workbook_json_and_png_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_pipeline(ATTACHMENT1, Path(temp_dir))

            self.assertEqual(result["summary"]["solver_status"], "Optimal")
            self.assertAlmostEqual(
                result["summary"]["total_cost_yuan"],
                35126.94858928964,
                places=6,
            )
            self.assertLessEqual(
                result["summary"]["validation"]["max_state_residual_kwh"],
                1e-6,
            )
            for key in ("workbook", "summary_json", "overview_png", "key_data_png"):
                output_path = Path(result[key])
                self.assertTrue(output_path.exists(), key)
                self.assertGreater(output_path.stat().st_size, 100, key)
            for key in ("overview_png", "key_data_png"):
                with Path(result[key]).open("rb") as file:
                    self.assertEqual(file.read(8), b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
