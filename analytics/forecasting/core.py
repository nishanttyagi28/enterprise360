"""Pure forecasting logic (no database): selection by rolling-origin CV, backtest, forecast, anomalies.

Method (simple and transparent; ~20 usable months, < 2 full years -> no yearly seasonality):
* Candidates: Holt's additive damped trend (ETS A,Ad,N) and simple exponential smoothing (ETS A,N,N),
  statsmodels ETSModel; baseline = last-value naive (seasonal-naive needs >= 2 full years: infeasible).
* Splits (chronological): train | validation | test (last ``test_months``) | forecast.
* Selection uses ONLY train+validation: expanding-window rolling-origin CV (origins from ``min_train``
  months, up to ``cv_horizon`` steps ahead, never past the end of validation). The best candidate by mean
  CV sMAPE is selected only if it beats the baseline's CV sMAPE; otherwise the BASELINE is published.
  The test window is never used for selection; test metrics are stored for every model, honestly.
* Intervals: split-conformal from rolling-origin CV absolute errors per horizon (method
  ``conformal_abs_cv``): half-width_h = the ceil((n+1)*level)/n empirical quantile of |error_h| (the max
  when n is small). Validation/test rows use CV on the months before their cutoff; forecast rows use CV
  on all usable months.
* Anomalies: expected = one-step in-sample fit of the selected model with parameters estimated on ALL
  usable months (naive -> previous month); robust z = |r - median(r)| / (1.4826 * MAD(r)) > 3.5.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
import pandas as pd
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

Split = Literal["train", "validation", "test", "forecast"]
MetricSplit = Literal["cv", "validation", "test"]
FloatArray = npt.NDArray[np.float64]
Numbers = Sequence[float] | FloatArray

ANOMALY_Z_THRESHOLD = 3.5
MAD_SCALE = 1.4826
INTERVAL_LEVEL = 0.95
INTERVAL_METHOD = "conformal_abs_cv"
BASELINE = "naive_last_value"
CANDIDATES: dict[str, dict[str, Any]] = {
    "holt_damped": {"trend": "add", "damped_trend": True},
    "ses": {"trend": None, "damped_trend": False},
}


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


@dataclass(frozen=True, slots=True)
class MonthlySeries:
    """A contiguous monthly series (month_start dates, first of month)."""

    name: str
    months: tuple[date, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.months) != len(self.values):
            raise ValueError("months and values differ in length")
        if any(m.day != 1 for m in self.months):
            raise ValueError(f"{self.name}: months must be month starts")
        for a, b in zip(self.months, self.months[1:], strict=False):
            if add_months(a, 1) != b:
                raise ValueError(f"{self.name}: series is not contiguous between {a} and {b}")


@dataclass(frozen=True, slots=True)
class BacktestMetric:
    series: str
    model: str
    split: MetricSplit
    n: int
    mae: float
    smape: float
    mape: float


def _f(x: object) -> float | None:
    return None if x is None else float(x)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class ForecastRow:
    month: date
    split: Split
    training_cutoff: date
    horizon: int | None
    actual: float | None
    fitted: float | None  # train rows only: in-sample one-step fit
    forecast: float | None  # null on train rows
    lower: float | None
    upper: float | None
    baseline: float | None
    baseline_lower: float | None
    baseline_upper: float | None
    expected: float | None = None  # anomaly reference (fit on all months)
    robust_z: float | None = None
    is_anomaly: bool = False

    def __post_init__(self) -> None:
        for name in (
            "actual",
            "fitted",
            "forecast",
            "lower",
            "upper",
            "baseline",
            "baseline_lower",
            "baseline_upper",
            "expected",
            "robust_z",
        ):
            object.__setattr__(self, name, _f(getattr(self, name)))


@dataclass(slots=True)
class ForecastResult:
    series: str
    model: str  # published (selected) model: a candidate or BASELINE
    selection_reason: str
    rows: list[ForecastRow] = field(default_factory=list)
    metrics: list[BacktestMetric] = field(default_factory=list)
    cv_smape: dict[str, float] = field(default_factory=dict)


def smape(actual: Numbers, pred: Numbers) -> float:
    """Symmetric MAPE in percent (0..200); pairs with both values 0 contribute 0."""
    a, p = np.asarray(actual, dtype=np.float64), np.asarray(pred, dtype=np.float64)
    denom = np.abs(a) + np.abs(p)
    terms = np.divide(2 * np.abs(a - p), denom, out=np.zeros_like(a), where=denom != 0)
    return float(100 * terms.mean())


def _metric(series: str, model: str, split: MetricSplit, actual: Numbers, pred: Numbers) -> BacktestMetric:
    a, p = np.asarray(actual, dtype=np.float64), np.asarray(pred, dtype=np.float64)
    mape = float(100 * np.mean(np.abs((a - p) / a))) if np.all(a != 0) else math.nan
    return BacktestMetric(series, model, split, len(a), float(np.mean(np.abs(a - p))), smape(a, p), mape)


def robust_z_scores(residuals: Numbers) -> FloatArray:
    """|r - median(r)| / (1.4826 * MAD). MAD == 0 -> z = 0 (no spread, nothing anomalous)."""
    r = np.asarray(residuals, dtype=np.float64)
    med = np.median(r)
    mad = float(np.median(np.abs(r - med)))
    if mad == 0:
        return np.zeros_like(r)
    return np.asarray(np.abs(r - med) / (MAD_SCALE * mad), dtype=np.float64)


def _fit(y: FloatArray, spec: dict[str, Any]) -> Any:  # statsmodels results are untyped
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # convergence chatter on tiny series
        model = ETSModel(pd.Series(y), error="add", seasonal=None, initialization_method="estimated", **spec)
        return model.fit(disp=False)


def point_forecast(model: str, y: FloatArray, steps: int) -> FloatArray:
    if model == BASELINE:
        return np.full(steps, y[-1], dtype=np.float64)
    fit = _fit(y, CANDIDATES[model])
    return np.asarray(fit.forecast(steps), dtype=np.float64)


def in_sample_fit(model: str, y: FloatArray) -> FloatArray:
    """One-step in-sample fit with parameters estimated on all of ``y`` (naive: previous value)."""
    if model == BASELINE:
        return np.concatenate([[y[0]], y[:-1]]).astype(np.float64)
    return np.asarray(_fit(y, CANDIDATES[model]).fittedvalues, dtype=np.float64)


@dataclass(frozen=True, slots=True)
class CvResult:
    actual: FloatArray
    pred: FloatArray
    abs_err_by_h: dict[int, list[float]]


def rolling_cv(model: str, y: FloatArray, *, min_train: int, cv_horizon: int) -> CvResult:
    """Expanding-window rolling-origin CV inside ``y`` (origins min_train..len(y)-1)."""
    actual: list[float] = []
    pred: list[float] = []
    errs: dict[int, list[float]] = {h: [] for h in range(1, cv_horizon + 1)}
    for origin in range(min_train, len(y)):
        steps = min(cv_horizon, len(y) - origin)
        p = point_forecast(model, y[:origin], steps)
        for h in range(steps):
            actual.append(float(y[origin + h]))
            pred.append(float(p[h]))
            errs[h + 1].append(abs(float(y[origin + h] - p[h])))
    return CvResult(np.asarray(actual), np.asarray(pred), errs)


def conformal_half_widths(cv: CvResult, horizon: int, level: float = INTERVAL_LEVEL) -> FloatArray:
    """Per-horizon split-conformal half-width; horizons without samples reuse the last available one."""
    widths: list[float] = []
    last = 0.0
    for h in range(1, horizon + 1):
        e = sorted(cv.abs_err_by_h.get(h, []))
        if e:
            k = min(math.ceil((len(e) + 1) * level), len(e))
            last = max(e[k - 1], last)  # non-decreasing in h
        widths.append(last)
    return np.asarray(widths, dtype=np.float64)


def select_model(y_sel: FloatArray, *, min_train: int, cv_horizon: int) -> tuple[str, str, dict[str, float]]:
    scores = {
        m: smape(cv.actual, cv.pred)
        for m in [*CANDIDATES, BASELINE]
        if (cv := rolling_cv(m, y_sel, min_train=min_train, cv_horizon=cv_horizon))
    }
    best = min(CANDIDATES, key=lambda k: scores[k])
    if scores[best] < scores[BASELINE]:
        reason = f"{best} CV sMAPE {scores[best]:.2f}% < baseline {scores[BASELINE]:.2f}%"
        return best, reason, scores
    reason = (
        f"fallback to baseline: best candidate {best} CV sMAPE {scores[best]:.2f}% "
        f">= baseline {scores[BASELINE]:.2f}%"
    )
    return BASELINE, reason, scores


def run_forecast(
    series: MonthlySeries,
    *,
    validation_months: int = 3,
    test_months: int = 3,
    horizon: int = 6,
    min_train: int = 8,
) -> ForecastResult:
    y = np.asarray(series.values, dtype=np.float64)
    n = len(y)
    n_train = n - validation_months - test_months
    n_sel = n_train + validation_months  # train+validation: the only data used for selection
    if n_train < min_train:
        raise ValueError(f"{series.name}: need >= {min_train} training months, have {n_train}")
    months = series.months
    cv_h = max(horizon, test_months, validation_months)

    selected, reason, scores = select_model(y[:n_sel], min_train=min_train, cv_horizon=cv_h)
    res = ForecastResult(series.name, selected, reason, cv_smape=scores)
    best_candidate = min(CANDIDATES, key=lambda k: scores[k])
    for m in [*CANDIDATES, BASELINE]:
        cv = rolling_cv(m, y[:n_sel], min_train=min_train, cv_horizon=cv_h)
        res.metrics.append(_metric(series.name, m, "cv", cv.actual, cv.pred))

    def block(cut: int, steps: int, model: str) -> tuple[FloatArray, FloatArray]:
        """Point forecast from y[:cut] + conformal half-widths from CV inside y[:cut]."""
        mean = point_forecast(model, y[:cut], steps)
        cv = rolling_cv(model, y[:cut], min_train=min(min_train, cut - 2), cv_horizon=steps)
        return mean, conformal_half_widths(cv, steps)

    # train rows: in-sample one-step fit of the selected model (params from train only)
    fitted_train = in_sample_fit(selected, y[:n_train])
    base_fit_train = in_sample_fit(BASELINE, y[:n_train])
    expected = in_sample_fit(selected, y)  # anomaly reference: params on ALL usable months
    z = robust_z_scores(y - expected)
    cut_train, cut_sel, cut_all = months[n_train - 1], months[n_sel - 1], months[-1]
    for i in range(n_train):
        res.rows.append(
            ForecastRow(
                months[i],
                "train",
                cut_train,
                None,
                y[i],
                fitted_train[i],
                None,
                None,
                None,
                base_fit_train[i],
                None,
                None,
                expected[i],
                z[i],
                bool(z[i] > ANOMALY_Z_THRESHOLD),
            )
        )

    blocks: tuple[tuple[Literal["validation", "test"], int, int, date], ...] = (
        ("validation", n_train, validation_months, cut_train),
        ("test", n_sel, test_months, cut_sel),
    )
    for split, start, steps, cut_month in blocks:
        mean, hw = block(start, steps, selected)
        bmean, bhw = block(start, steps, BASELINE)
        for h in range(steps):
            i = start + h
            res.rows.append(
                ForecastRow(
                    months[i],
                    split,
                    cut_month,
                    h + 1,
                    y[i],
                    None,
                    mean[h],
                    mean[h] - hw[h],
                    mean[h] + hw[h],
                    bmean[h],
                    bmean[h] - bhw[h],
                    bmean[h] + bhw[h],
                    expected[i],
                    z[i],
                    bool(z[i] > ANOMALY_Z_THRESHOLD),
                )
            )
        actual = y[start : start + steps]
        for m in dict.fromkeys([best_candidate, selected, BASELINE]):  # honest: model AND baseline
            res.metrics.append(_metric(series.name, m, split, actual, point_forecast(m, y[:start], steps)))

    mean, hw = block(n, horizon, selected)
    bmean, bhw = block(n, horizon, BASELINE)
    for h in range(horizon):
        res.rows.append(
            ForecastRow(
                add_months(cut_all, h + 1),
                "forecast",
                cut_all,
                h + 1,
                None,
                None,
                mean[h],
                max(mean[h] - hw[h], 0.0),
                mean[h] + hw[h],
                bmean[h],
                max(bmean[h] - bhw[h], 0.0),
                bmean[h] + bhw[h],
            )
        )
    return res
