import unittest
import numpy as np
import pandas as pd

from q2_pipeline import (
    to_daily_matrices, build_features_for_day, forecast_metrics,
    model_metrics_table, rolling_gru_forecasts,
    rolling_original_ridge_forecasts, load_project_data,
    solve_plan_lp, settle_day
)


class TestQ2Pipeline(unittest.TestCase):
    def test_end_timestamp_is_assigned_to_correct_plan_day(self):
        ts = pd.date_range('2025-01-01 00:10', '2025-01-02 00:00', freq='10min')
        raw = pd.DataFrame({'时间': ts, '小区负载': np.arange(144.), '光伏发电实际功率': 0.})
        dates, load, pv = to_daily_matrices(raw, year=2025)
        self.assertEqual(load.shape, (1, 144))
        self.assertEqual(dates[0], pd.Timestamp('2025-01-01'))
        self.assertEqual(load[0, -1], 143.)

    def test_features_do_not_use_future_values(self):
        y = np.arange(20 * 144, dtype=float).reshape(20, 144)
        dates = pd.date_range('2025-01-01', periods=20)
        x1 = build_features_for_day(y, dates, 15)
        y[16:] = -999999
        x2 = build_features_for_day(y, dates, 15)
        np.testing.assert_allclose(x1, x2)

    def test_metrics_follow_requested_definitions(self):
        eps = np.array([[1., -2., 3.], [-1., -1., -1.]])
        m = forecast_metrics(eps)
        self.assertAlmostEqual(m['逐时段RMSE'], np.sqrt(17 / 6))
        self.assertAlmostEqual(m['平均日电量绝对误差'], 2.5)
        self.assertAlmostEqual(m['平均日Pinball损失'], (1.6 + 0.6) / 2)
        self.assertAlmostEqual(m['平均最大累计缺口'], 1.0)

    def test_general_metric_table_uses_requested_date_slice(self):
        load = np.ones((4, 3))*12
        pv = np.zeros_like(load)
        f = np.full_like(load, np.nan)
        f[2:] = 6
        forecasts = {'m': {'load': (f, f), 'pv': (np.zeros_like(f), np.zeros_like(f))}}
        tab = model_metrics_table(forecasts, load, pv, start=2, end=4)
        self.assertAlmostEqual(tab.loc['m', '平均日电量绝对误差'], 3.0)

    def test_gru_forecast_uses_completed_days_not_future_days(self):
        rng = np.random.default_rng(0)
        y = np.maximum(10 + rng.normal(size=(18, 8)), 0)
        dates = pd.date_range('2025-01-01', periods=18)
        a1, _ = rolling_gru_forecasts(y.copy(), dates, 'load', start=10, end=11,
                                      hidden_size=4, initial_epochs=2, update_epochs=1)
        y[12:] = 999999
        a2, _ = rolling_gru_forecasts(y, dates, 'load', start=10, end=11,
                                      hidden_size=4, initial_epochs=2, update_epochs=1)
        np.testing.assert_allclose(a1[10], a2[10], atol=1e-6)

    def test_original_ridge_reproduces_existing_notebook(self):
        base = pd.io.common.stringify_path(__file__)
        from pathlib import Path
        root = Path(base).resolve().parents[1]
        dates, load, _ = load_project_data(
            root/'附件2_训练集_2025年1月.csv', root/'附件2_预测集_2025年2月起.csv')
        pred, _ = rolling_original_ridge_forecasts(
            load, dates, 'load', start=10, end=len(dates))
        mae = np.abs(pred[31:]-load[31:]).mean()
        self.assertAlmostEqual(mae, 138.21780734644912, places=6)

    def test_original_ridge_does_not_use_future_values(self):
        rng = np.random.default_rng(7)
        y = np.maximum(100 + rng.normal(size=(20, 8)), 0)
        dates = pd.date_range('2025-01-01', periods=20)
        p1, p2 = rolling_original_ridge_forecasts(y.copy(), dates, 'load', start=14, end=15)
        y[15:] = 999999
        q1, q2 = rolling_original_ridge_forecasts(y, dates, 'load', start=14, end=15)
        np.testing.assert_allclose(p1[14], q1[14], atol=1e-9)
        np.testing.assert_allclose(p2[14], q2[14], atol=1e-9)

    def test_lp_and_settlement_respect_soc_bounds(self):
        T = 4
        q, status = solve_plan_lp(
            load_energy=np.full(2*T, 100.), pv_energy=np.zeros(2*T),
            price=np.ones(2*T), s0=6000., periods_per_day=T,
            eta=.9, rmax=100., smin=1200., smax=10800.)
        self.assertTrue(status['success'])
        out = settle_day(q, np.full(T, 100.), 6000., eta=.9, rmax=100., smin=1200., smax=10800.)
        self.assertTrue(np.all((out['soc'] >= 1200.-1e-8) & (out['soc'] <= 10800.+1e-8)))
        np.testing.assert_allclose(out['emergency'], 0., atol=1e-7)


if __name__ == '__main__':
    unittest.main()
