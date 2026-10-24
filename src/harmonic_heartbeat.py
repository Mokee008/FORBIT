"""
src/harmonic_heartbeat.py - Rule R1 Compliant Seasonal Harmonic Heartbeat
Implements the no-training harmonic / prior-year seasonal curve + Z-score residual detector.
Pure mathematical formulation, random-init/no-pretraining principle, highly explainable.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple

class HarmonicHeartbeatDetector:
    def __init__(self, num_harmonics: int = 2, z_threshold: float = -2.2, min_consecutive_drops: int = 2):
        self.num_harmonics = num_harmonics
        self.z_threshold = z_threshold
        self.min_consecutive_drops = min_consecutive_drops

    def _build_harmonic_features(self, doys: np.ndarray) -> np.ndarray:
        """Constructs Fourier harmonic basis for annual phenological cycle."""
        omega = 2.0 * np.pi * doys / 365.25
        features = [np.ones_like(doys)]
        for k in range(1, self.num_harmonics + 1):
            features.append(np.sin(k * omega))
            features.append(np.cos(k * omega))
        return np.column_stack(features)

    def fit_baseline(self, doys: np.ndarray, values: np.ndarray, valid_mask: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Fits harmonic coefficients (a0, a_k, b_k) using regularized ordinary least squares
        on valid historical forest observations.
        """
        valid_idx = np.where(valid_mask)[0]
        if len(valid_idx) < 6:
            # Insufficient clear observations: fallback to robust median and conservative sigma
            median_val = np.nanmedian(values) if len(values) > 0 else 0.65
            coeffs = np.zeros(1 + 2 * self.num_harmonics)
            coeffs[0] = median_val
            sigma = 0.12
            return coeffs, sigma

        X = self._build_harmonic_features(doys[valid_idx])
        y = values[valid_idx]

        # Ridge regression to prevent runaway coefficients in patchy cloud series
        reg = 1e-3 * np.eye(X.shape[1])
        reg[0, 0] = 0.0  # Do not regularize intercept
        try:
            coeffs = np.linalg.solve(X.T @ X + reg, X.T @ y)
        except np.linalg.LinAlgError:
            coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)

        y_pred = X @ coeffs
        residuals = y - y_pred
        # Robust sigma using MAD (Median Absolute Deviation)
        mad = np.median(np.abs(residuals - np.median(residuals)))
        sigma = float(max(1.4826 * mad, 0.035)) # Floor at 0.035 to prevent division by zero in calm waters/forests

        return coeffs, sigma

    def predict_expected(self, coeffs: np.ndarray, doys: np.ndarray) -> np.ndarray:
        """Evaluates expected seasonal canopy trajectory."""
        X = self._build_harmonic_features(doys)
        return X @ coeffs

    def analyze_pixel_series(
        self,
        dates: List[str],
        doys: np.ndarray,
        values: np.ndarray,
        valid_mask: np.ndarray,
        baseline_mask: Optional[np.ndarray] = None
    ) -> Dict:
        """
        Full Heartbeat analysis on a single pixel time-series:
        1. Fits harmonic baseline on valid observations in baseline period (e.g. 2021-2022).
        2. Computes continuous expected curve & +/- 2 sigma bounds.
        3. Computes Z-score residuals z = (actual - expected) / sigma.
        4. Detects abrupt, sustained structural clearing break.
        5. Assigns exact observation interval [last_seen_forest, first_seen_cleared].
        """
        T = len(dates)
        if baseline_mask is None:
            # Default baseline: first 60% of time series (or pre-clearing years)
            baseline_mask = np.zeros(T, dtype=bool)
            baseline_mask[:max(int(T * 0.5), 12)] = True

        fit_mask = valid_mask & baseline_mask
        coeffs, sigma = self.fit_baseline(doys, values, fit_mask)
        expected = self.predict_expected(coeffs, doys)

        z_scores = np.zeros(T)
        valid_indices = np.where(valid_mask)[0]

        for idx in range(T):
            if valid_mask[idx]:
                z_scores[idx] = (values[idx] - expected[idx]) / sigma
            else:
                z_scores[idx] = 0.0

        # Structural break detection:
        # Looking for sustained negative anomaly in valid observations
        break_detected = False
        break_start_idx = None
        break_end_idx = None
        consecutive_drops = 0
        min_z_in_break = 0.0

        for idx in valid_indices:
            # We evaluate after the baseline learning phase
            if not baseline_mask[idx]:
                if z_scores[idx] < self.z_threshold:
                    consecutive_drops += 1
                    min_z_in_break = min(min_z_in_break, z_scores[idx])
                    if consecutive_drops >= self.min_consecutive_drops and not break_detected:
                        break_detected = True
                        # The first drop index was (consecutive_drops - 1) steps earlier in valid_indices
                        current_pos_in_valid = list(valid_indices).index(idx)
                        first_drop_pos = current_pos_in_valid - (self.min_consecutive_drops - 1)
                        first_drop_idx = valid_indices[first_drop_pos]
                        last_valid_forest_pos = first_drop_pos - 1
                        
                        break_end_idx = first_drop_idx
                        break_start_idx = valid_indices[last_valid_forest_pos] if last_valid_forest_pos >= 0 else max(0, first_drop_idx - 1)
                else:
                    if not break_detected:
                        consecutive_drops = 0

        # Check post-break persistence: does it stay deforested or was it a transient drop?
        status = "STABLE_FOREST"
        confidence = 0.0
        date_interval = None

        if break_detected and break_end_idx is not None and break_start_idx is not None:
            post_break_valid = [i for i in valid_indices if i >= break_end_idx]
            if len(post_break_valid) == 0:
                # Cloud occlusion right after potential break -> Honesty rule: UNKNOWN_CLOUD_GAP
                status = "UNKNOWN_CLOUD_GAP"
                confidence = 0.35
            else:
                post_break_z = [z_scores[i] for i in post_break_valid]
                mean_post_z = np.mean(post_break_z)
                if mean_post_z < -1.8:
                    status = "VERIFIED_LOSS"
                    # Confidence derived from depth of drop and count of confirming observations
                    confidence = float(min(0.98, 0.65 + 0.05 * len(post_break_valid) + 0.05 * abs(mean_post_z)))
                    date_interval = (dates[break_start_idx], dates[break_end_idx])
                else:
                    # Temporary dip that regreened (e.g. crop cycle or cloud shadow artifact)
                    status = "SEASONAL_DECIDUOUS"
                    confidence = 0.85

        return {
            "dates": dates,
            "doys": doys.tolist(),
            "actual_values": np.where(valid_mask, np.round(values, 3), None).tolist(),
            "valid_mask": valid_mask.tolist(),
            "expected_curve": np.round(expected, 3).tolist(),
            "sigma_band_upper": np.round(expected + 2.0 * sigma, 3).tolist(),
            "sigma_band_lower": np.round(expected - 2.0 * sigma, 3).tolist(),
            "sigma": round(sigma, 4),
            "z_scores": np.round(z_scores, 2).tolist(),
            "status": status,
            "confidence": round(confidence, 3),
            "break_date_interval": date_interval,
            "valid_post_break_count": len([i for i in valid_indices if break_end_idx and i >= break_end_idx]) if break_detected else 0
        }
