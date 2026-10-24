"""
src/date_estimation.py - Temporal Breakpoint & Date-of-Loss Estimation Module
Upgrades binary change detection into precise temporal date-of-loss tracking:
- Determines exact observation interval [t_last_seen_forest, t_first_seen_cleared]
- Computes estimated single-day loss date
- Evaluates median absolute error (days) and interval hit rate against public benchmarks
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

class DateOfLossEstimator:
    def __init__(self, min_consecutive_drops: int = 2):
        self.min_consecutive_drops = min_consecutive_drops

    def estimate_pixel_loss_date(
        self,
        dates: List[str],
        z_scores: np.ndarray,
        valid_mask: np.ndarray,
        z_threshold: float = -2.2
    ) -> Dict:
        """
        Scans valid optical and SAR acquisitions to locate the structural break point.
        Returns exact estimated date and interval [last_forest, first_cleared].
        """
        valid_indices = np.where(valid_mask)[0]
        if len(valid_indices) == 0:
            return {"loss_detected": False, "estimated_date": None, "interval": None}

        consecutive = 0
        first_break_idx = None

        for pos, idx in enumerate(valid_indices):
            if z_scores[idx] < z_threshold:
                consecutive += 1
                if consecutive >= self.min_consecutive_drops and first_break_idx is None:
                    first_break_idx = valid_indices[pos - (self.min_consecutive_drops - 1)]
                    break
            else:
                consecutive = 0

        if first_break_idx is None:
            return {"loss_detected": False, "estimated_date": None, "interval": None}

        first_cleared_date = dates[first_break_idx]
        
        # Last confirmed forest observation
        prior_valid = [i for i in valid_indices if i < first_break_idx]
        last_forest_date = dates[prior_valid[-1]] if len(prior_valid) > 0 else dates[0]

        # Calculate midpoint date as best point estimate
        d1 = datetime.strptime(last_forest_date, "%Y-%m-%d")
        d2 = datetime.strptime(first_cleared_date, "%Y-%m-%d")
        interval_width_days = abs((d2 - d1).days)
        midpoint_ts = d1.timestamp() + (d2.timestamp() - d1.timestamp()) / 2.0
        estimated_date = datetime.fromtimestamp(midpoint_ts).strftime("%Y-%m-%d")

        return {
            "loss_detected": True,
            "estimated_date": estimated_date,
            "first_cleared_date": first_cleared_date,
            "last_forest_date": last_forest_date,
            "interval": [last_forest_date, first_cleared_date],
            "interval_width_days": interval_width_days
        }

    def evaluate_against_public_benchmarks(
        self,
        estimated_dates: List[str],
        public_alert_dates: List[str],
        intervals: Optional[List[Tuple[str, str]]] = None
    ) -> Dict:
        """
        Calculates median error and MAE against public benchmark alert dates
        (e.g., Hansen Global Forest Change / RADD alerts).
        """
        errors_days = []
        hits = 0

        for i, (est_str, pub_str) in enumerate(zip(estimated_dates, public_alert_dates)):
            t_est = datetime.strptime(est_str, "%Y-%m-%d")
            t_pub = datetime.strptime(pub_str, "%Y-%m-%d")
            err = abs((t_est - t_pub).days)
            errors_days.append(err)

            if intervals and i < len(intervals):
                t_start = datetime.strptime(intervals[i][0], "%Y-%m-%d")
                t_end = datetime.strptime(intervals[i][1], "%Y-%m-%d")
                if t_start <= t_pub <= t_end:
                    hits += 1

        median_error = float(np.median(errors_days)) if errors_days else 0.0
        mae_error = float(np.mean(errors_days)) if errors_days else 0.0
        hit_rate = float(hits / len(estimated_dates)) if (intervals and len(estimated_dates) > 0) else 1.0

        return {
            "median_error_days": round(median_error, 1),
            "mae_days": round(mae_error, 1),
            "interval_hit_rate": round(hit_rate, 4),
            "sample_count": len(errors_days),
            "note": "Public alert reference dates typically lag by 15-45 days due to reporting cycles."
        }
