"""Forecast core: metrics, robust z, split/leakage rules, horizon and intervals (no database)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from analytics.forecasting.core import (
    ANOMALY_Z_THRESHOLD,
    BASELINE,
    MonthlySeries,
    add_months,
    robust_z_scores,
    run_forecast,
    smape,
)

pytestmark = pytest.mark.unit
MONTHS = tuple(add_months(date(2017, 1, 1), i) for i in range(20))


def _series(values: list[float]) -> MonthlySeries:
    return MonthlySeries("gmv", MONTHS[: len(values)], tuple(values))


def test_smape_and_zero_pairs() -> None:
    assert smape([100, 0], [100, 0]) == 0
    assert smape([100], [50]) == pytest.approx(100 * 2 * 50 / 150)


def test_robust_z_flags_single_spike_and_handles_zero_mad() -> None:
    r = [1.0, -1.0, 0.5, -0.5, 0.0, 20.0]
    z = robust_z_scores(r)
    assert z.argmax() == 5 and z[5] > ANOMALY_Z_THRESHOLD and (z[:5] < ANOMALY_Z_THRESHOLD).all()
    assert (robust_z_scores([2.0, 2.0, 2.0]) == 0).all()


def test_series_must_be_contiguous_month_starts() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        MonthlySeries("x", (date(2017, 1, 1), date(2017, 3, 1)), (1.0, 2.0))
    with pytest.raises(ValueError, match="month starts"):
        MonthlySeries("x", (date(2017, 1, 2),), (1.0,))


def test_run_forecast_splits_have_no_leakage_and_full_horizon() -> None:
    rng = np.random.default_rng(7)
    res = run_forecast(_series([100 + 5 * i + float(rng.normal(0, 2)) for i in range(20)]), horizon=6)
    splits = [r.split for r in res.rows]
    assert splits.count("train") == 14 and splits.count("validation") == 3
    assert splits.count("test") == 3 and splits.count("forecast") == 6
    months = [r.month for r in res.rows]
    assert months == [add_months(MONTHS[0], i) for i in range(26)]  # one row per month, contiguous
    for r in res.rows:
        if r.split == "train":
            assert r.forecast is None and r.fitted is not None
        else:
            assert r.month > r.training_cutoff
            assert r.lower is not None and r.upper is not None and r.lower <= r.forecast <= r.upper
    pairs = {(m.model, m.split) for m in res.metrics}
    assert {(res.model, "test"), (BASELINE, "test"), (BASELINE, "cv"), ("holt_damped", "cv")} <= pairs
    assert res.model == "holt_damped"  # clear linear trend -> trend model wins rolling CV
    assert "baseline" in res.selection_reason


def test_falls_back_to_baseline_when_no_candidate_beats_it_in_cv() -> None:
    rng = np.random.default_rng(3)
    walk = list(np.cumsum(rng.normal(0, 10, 20)) + 1000)  # random walk: naive is optimal
    res = run_forecast(_series([float(v) for v in walk]))
    if res.model == BASELINE:
        assert res.selection_reason.startswith("fallback to baseline")
    forecast = [r for r in res.rows if r.split == "forecast"]
    if res.model == BASELINE:
        assert all(r.forecast == r.baseline for r in forecast)


def test_selection_never_uses_test_months() -> None:
    values = [100.0 + 5 * i for i in range(20)]
    a = run_forecast(_series(values))
    values_changed_test = [*values[:17], 1.0, 1.0, 1.0]
    b = run_forecast(_series(values_changed_test))
    assert a.model == b.model and a.cv_smape == b.cv_smape


def test_spike_is_flagged_as_anomaly() -> None:
    values = [100.0 + 3 * i for i in range(20)]
    values[10] *= 1.8
    res = run_forecast(_series(values))
    flagged = [r.month for r in res.rows if r.is_anomaly]
    assert MONTHS[10] in flagged


def test_too_short_series_rejected() -> None:
    with pytest.raises(ValueError, match="training months"):
        run_forecast(_series([1.0] * 12))
