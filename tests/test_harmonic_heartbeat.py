"""
tests/test_harmonic_heartbeat.py - Unit test for Rule R1 seasonal harmonic detector.
"""

import sys
from pathlib import Path

# Auto-bootstrap local virtual environment (.venv) if running via system python3
_ROOT = Path(__file__).resolve().parent.parent
_VENV_LIB = _ROOT / ".venv" / "lib"
if _VENV_LIB.exists():
    for _sp in _VENV_LIB.glob("python*/site-packages"):
        if _sp.exists() and str(_sp) not in sys.path:
            sys.path.insert(0, str(_sp))
for _p in [str(_ROOT), str(_ROOT / "src")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
from src.harmonic_heartbeat import HarmonicHeartbeatDetector

def test_deciduous_leaf_fall_suppresses_false_alarm():
    detector = HarmonicHeartbeatDetector()
    # 36 months (3 years) of monthly observations
    # Deciduous forest: peak in Aug/Sep (~0.75), natural trough in March (~0.40)
    dates = []
    doys = []
    values = []
    valid = []

    for year in [2021, 2022, 2023]:
        for month in range(1, 13):
            doy = int((month - 0.5) * 30.5)
            dates.append(f"{year}-{month:02d}-15")
            doys.append(doy)
            # Seasonal curve
            omega = 2 * np.pi * doy / 365.25
            seasonal_ndvi = 0.58 + 0.16 * np.sin(omega - 1.5) # Minimum around March/April
            # Add small random noise
            val = seasonal_ndvi + 0.015 * np.sin(year)
            # Monsoon cloud gaps in July/August
            is_clear = not (month in [7, 8] and year == 2022)
            values.append(val if is_clear else 0.0)
            valid.append(is_clear)

    res = detector.analyze_pixel_series(dates, np.array(doys), np.array(values), np.array(valid))
    # Crucial assertion: Natural dry-season dip in March 2023 MUST NOT be flagged as loss!
    assert res["status"] in ["STABLE_FOREST", "SEASONAL_DECIDUOUS"]
    assert res["break_date_interval"] is None
    print(f"Deciduous test passed. Status: {res['status']}, Max Z: {max(res['z_scores']):.2f}, Min Z: {min(res['z_scores']):.2f}")

def test_real_clearing_detected_with_interval():
    detector = HarmonicHeartbeatDetector()
    dates = []
    doys = []
    values = []
    valid = []

    for year in [2021, 2022, 2023]:
        for month in range(1, 13):
            doy = int((month - 0.5) * 30.5)
            dates.append(f"{year}-{month:02d}-15")
            doys.append(doy)
            omega = 2 * np.pi * doy / 365.25
            seasonal_ndvi = 0.65 + 0.10 * np.sin(omega - 1.5)

            # Forest clearing happens in May 2023! Canopy collapses to 0.18 (bare pit/soil)
            if year == 2023 and month >= 5:
                val = 0.18 + 0.01 * np.cos(doy)
            else:
                val = seasonal_ndvi

            is_clear = not (month in [7, 8] and year == 2021)
            values.append(val if is_clear else 0.0)
            valid.append(is_clear)

    res = detector.analyze_pixel_series(dates, np.array(doys), np.array(values), np.array(valid))
    assert res["status"] == "VERIFIED_LOSS"
    assert res["break_date_interval"] is not None
    # Pre-break valid was 2023-04-15, post-break first drop was 2023-05-15
    assert res["break_date_interval"][0] == "2023-04-15"
    assert res["break_date_interval"][1] == "2023-05-15"
    assert res["confidence"] >= 0.70
    print(f"Clearing test passed. Interval: {res['break_date_interval']}, Confidence: {res['confidence']}")

if __name__ == "__main__":
    test_deciduous_leaf_fall_suppresses_false_alarm()
    test_real_clearing_detected_with_interval()
    print("All Heartbeat unit tests passed successfully!")
