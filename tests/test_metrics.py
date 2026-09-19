"""Impact-metric extraction on synthetic obstacle pressure histories."""

import math

import numpy as np
import pytest

import compute_robust_peak_metrics as robust
import extract_surrogate_database_metrics as extract
import train_robust_surrogate_models as train


def history(times, pressure, alpha):
    return [(float(t), float(p), float(a)) for t, p, a in zip(times, pressure, alpha)]


def test_read_surface_file_skips_comments(tmp_path):
    path = tmp_path / "surfaceFieldValue.dat"
    path.write_text("# Time areaAverage(p_rgh) areaAverage(alpha.water)\n"
                    "0 10 0\n0.005 20 0.6\n\n")
    assert extract.read_surface_file(path) == [(0.0, 10.0, 0.0), (0.005, 20.0, 0.6)]


def test_wetting_times_and_duration():
    t = np.arange(0, 1.0001, 0.1)
    alpha = [0, 0, 0.2, 0.6, 0.9, 0.9, 0.7, 0.3, 0, 0, 0]
    rows = history(t, np.zeros_like(t), alpha)
    assert extract.first_time_above(rows, 2, 0.5) == pytest.approx(0.3)
    assert extract.last_time_above(rows, 2, 0.5) == pytest.approx(0.6)
    assert extract.duration_above(rows, 2, 0.5) == pytest.approx(0.3)
    assert extract.first_time_above(rows, 2, 0.95) is None
    assert extract.duration_above(rows, 2, 0.95) == 0.0


def test_impulse_integrates_only_positive_pressure():
    t = np.linspace(0, 1, 101)
    rows = history(t, np.sin(2 * np.pi * t), np.zeros_like(t))
    # Integral of the positive half-lobe of sin(2 pi t) is 1/pi.
    assert extract.positive_trapezoidal_integral(rows, 1) == pytest.approx(1 / math.pi, rel=1e-3)


def test_percentile_and_top_fraction():
    values = [float(v) for v in range(1, 101)]
    assert robust.percentile(values, 50) == pytest.approx(np.percentile(values, 50))
    assert robust.percentile(values, 95) == pytest.approx(np.percentile(values, 95))
    assert robust.top_fraction_mean(values, 0.05) == pytest.approx(np.mean(values[-5:]))
    assert robust.top_fraction_mean(values, 0.001) == 100.0


def test_rolling_peak_damps_a_single_spike():
    dt = 0.005
    t = np.arange(0, 1.0, dt)
    p = np.where((t > 0.4) & (t < 0.5), 1000.0, 0.0)   # 0.1 s plateau
    p[20] = 5_000.0     # one-sample spike: 5x the plateau, but only 1/11 of a window
    rows = history(t, p, np.zeros_like(t))
    peak, when = robust.rolling_average_peak(rows, 1, window_seconds=0.05)
    assert peak == pytest.approx(1000.0)
    assert 0.4 < when < 0.5


def test_normalised_rmse_is_scaled_by_range():
    y = np.array([0.0, 10.0, 20.0])
    assert train.rmse(y, y + 2.0) == pytest.approx(2.0)
    assert train.normalised_rmse(y, y + 2.0) == pytest.approx(0.1)
    assert math.isnan(train.normalised_rmse(np.ones(3), np.ones(3)))
