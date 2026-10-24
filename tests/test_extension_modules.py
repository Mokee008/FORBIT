"""
tests/test_extension_modules.py - Verification for all 5 Phase 1 & 2 Extension Modules
Tests:
1. Sentinel-1 SAR radar fusion & monsoon cloud penetration
2. Confounder filtering (deciduous leaf-fall, agriculture, river shifts)
3. Precise date-of-loss estimation & benchmark evaluation
4. Top-50 precision ranking & F1 retention check
5. Coarse (30m) & noisy label consistency loss
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
import torch
from src.radar_fusion import RadarOpticalFusionHeartbeat
from src.confounder_filter import ConfounderFilter
from src.date_estimation import DateOfLossEstimator
from src.ranking import PatrolRankingEngine
from src.coarse_noisy_loss import CoarseConsistencyLoss, NoiseRobustLoss

def test_sentinel1_radar_fusion():
    fusion = RadarOpticalFusionHeartbeat()
    T = 24
    dates = [f"2024-{(i%12)+1:02d}-15" for i in range(T)]
    doys = np.array([((i % 12) + 0.5) * 30.5 for i in range(T)])

    # Optical series with monsoon cloud gap (indices 6, 7, 8)
    opt_ndvi = np.full(T, 0.70)
    opt_valid = np.ones(T, dtype=bool)
    opt_valid[6:9] = False # Optical blinded by monsoon clouds

    # SAR C-band series: clear drop during monsoon
    sar_vv = np.full(T, -8.0)
    sar_vh = np.full(T, -13.0)
    sar_vh[7:] = -19.5 # 6.5 dB drop (canopy clearing)

    res = fusion.analyze_pixel_multimodal(
        dates=dates,
        doys=doys,
        optical_ndvi=opt_ndvi,
        optical_valid=opt_valid,
        sar_vv_db=sar_vv,
        sar_vh_db=sar_vh,
        baseline_months_count=6
    )

    assert res["status"] == "VERIFIED_LOSS", f"SAR should detect loss even when optical is blinded by monsoon clouds, got {res['status']}"
    assert "SAR" in res["break_modality"], f"Expected SAR modality, got {res['break_modality']}"
    print("✓ test_sentinel1_radar_fusion passed")

def test_confounder_filtering():
    filter_engine = ConfounderFilter()
    doys = np.array([15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345])
    dates = [f"2024-{i+1:02d}-15" for i in range(12)]

    # 1. Deciduous leaf-fall: z-scores stay around 0 (tracks harmonic expectation)
    z_scores_deciduous = np.array([0.1, -0.2, -0.3, -0.1, 0.2, 0.3, 0.2, 0.1, 0.0, -0.1, 0.1, 0.2])
    exp_seasonal = np.array([0.65, 0.55, 0.35, 0.38, 0.58, 0.72, 0.75, 0.74, 0.70, 0.68, 0.66, 0.65])
    act_ndvi = exp_seasonal + 0.02

    is_leaf, reason = filter_engine.filter_deciduous_leaf_fall(
        z_scores_deciduous, exp_seasonal, act_ndvi, doys
    )
    assert is_leaf, f"Expected leaf fall to be filtered, reason: {reason}"

    # 2. Agricultural harvesting with rapid 60-day crop rebound
    agri_ndvi = np.array([0.65, 0.68, 0.20, 0.55, 0.70]) # sharp dip at idx 2 then fast rebound
    is_agri, reason = filter_engine.filter_agricultural_harvesting(dates[:5], agri_ndvi, patch_compactness=0.9)
    assert is_agri, f"Expected agricultural harvest to be filtered, reason: {reason}"

    # 3. River boundary expansion (positive MNDWI near water)
    green = np.array([0.30])
    swir = np.array([0.10])
    is_river, reason = filter_engine.filter_river_boundary_shifts(green, swir, distance_to_water_px=1.5)
    assert is_river, f"Expected river shift to be filtered, reason: {reason}"

    print("✓ test_confounder_filtering passed")

def test_date_estimation():
    estimator = DateOfLossEstimator()
    dates = ["2024-01-15", "2024-02-15", "2024-03-15", "2024-04-15", "2024-05-15"]
    z_scores = np.array([0.1, -0.2, -0.1, -3.5, -3.8])
    valid_mask = np.ones(5, dtype=bool)

    res = estimator.estimate_pixel_loss_date(dates, z_scores, valid_mask)
    assert res["loss_detected"], "Loss should be detected at index 3"
    assert res["first_cleared_date"] == "2024-04-15", f"Expected 2024-04-15, got {res['first_cleared_date']}"

    # Benchmark error calculation
    eval_res = estimator.evaluate_against_public_benchmarks(
        estimated_dates=["2024-04-15", "2024-05-15"],
        public_alert_dates=["2024-04-28", "2024-05-30"],
        intervals=[("2024-03-15", "2024-04-30"), ("2024-04-15", "2024-06-05")]
    )
    assert eval_res["median_error_days"] <= 15.0, f"Expected error <= 15 days, got {eval_res['median_error_days']}"
    assert eval_res["interval_hit_rate"] == 1.0, "Expected 100% interval hit rate"
    print("✓ test_date_estimation passed")

def test_ranking_and_f1():
    ranking = PatrolRankingEngine(target_monthly_capacity=50)

    # Generate 80 candidate alerts
    candidates = []
    for i in range(80):
        candidates.append({
            "alert_id": f"ALRT-{i:03d}",
            "confidence": 0.85 + (i % 15) * 0.01,
            "area_ha": 0.05 + (i % 10) * 0.05,
            "cause": "MINING_QUARRY" if i % 2 == 0 else "FELLING_LOGGING",
            "state": "Odisha",
            "is_true_loss": True
        })

    top_50, stats = ranking.rank_top_alerts(candidates, held_out_state="Odisha")
    assert len(top_50) == 50, f"Expected exactly 50 alerts, got {len(top_50)}"
    assert stats["precision_at_50"] == 1.0, f"Expected P@50 = 1.0, got {stats['precision_at_50']}"

    # Verify F1 retention
    f1_check = ranking.verify_f1_retention(phase_1_f1=0.884, phase_2_multimodal_f1=0.866)
    assert f1_check["status"] == "PASS", f"F1 delta exceeded tolerance: {f1_check}"
    print("✓ test_ranking_and_f1 passed")

def test_coarse_noisy_loss():
    loss_fn = CoarseConsistencyLoss(shift_tol=1)
    
    # Batch size 2, 1 channel, 128x128 10m prediction logits
    pred_10m = torch.randn(2, 1, 128, 128, requires_grad=True)
    
    # 42x42 coarse 30m target (128 // 3 = 42)
    target_30m = torch.randint(0, 2, (2, 1, 42, 42)).float()

    loss = loss_fn(pred_10m, target_30m)
    assert torch.isfinite(loss), "Loss must be finite"
    loss.backward()
    assert pred_10m.grad is not None, "Gradient should propagate back to 10m logits"

    # Symmetric noise-robust loss
    robust_loss_fn = NoiseRobustLoss()
    loss_robust = robust_loss_fn(pred_10m, target_30m)
    assert torch.isfinite(loss_robust), "Noise robust loss must be finite"
    print("✓ test_coarse_noisy_loss passed")

def main():
    print("==================================================")
    print("  Auditing & Testing 5 Extension Modules")
    print("==================================================")
    test_sentinel1_radar_fusion()
    test_confounder_filtering()
    test_date_estimation()
    test_ranking_and_f1()
    test_coarse_noisy_loss()
    print("==================================================")
    print("  ALL 5 EXTENSION MODULES PASSED AUDIT (100%)")
    print("==================================================")

if __name__ == "__main__":
    main()
