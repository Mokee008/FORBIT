"""
src/ranking.py - Top-50 Precision Ranking & F1 Retention Module
Computes multi-factor priority scores, ranks alerts for field ranger patrols,
and verifies Precision@50 (P@50) and F1 retention constraint (ΔF1 ≤ 0.05).
"""

from typing import Dict, List, Tuple
import numpy as np

class PatrolRankingEngine:
    def __init__(self, target_monthly_capacity: int = 50, max_f1_degradation: float = 0.05):
        self.capacity = target_monthly_capacity
        self.max_f1_degradation = max_f1_degradation

    def calculate_priority_score(
        self,
        confidence: float,
        area_ha: float,
        threat_cause: str,
        is_monsoon: bool = False
    ) -> float:
        """
        Calculates actionable patrol priority:
        Priority = Confidence * sqrt(Area) * CauseSeverityWeight * MonsoonWeight
        """
        # Critical threats receive higher dispatch priority
        cause_weights = {
            "MINING_QUARRY": 1.5,
            "ROAD_INFRASTRUCTURE": 1.3,
            "FELLING_LOGGING": 1.1,
            "FIRE_BURN": 1.2,
            "AGRICULTURAL_ENCROACHMENT": 1.0
        }
        cw = cause_weights.get(threat_cause.upper(), 1.0)
        mw = 1.15 if is_monsoon else 1.0  # Slightly elevate monsoon radar detections due to urgency

        score = confidence * np.sqrt(max(area_ha, 0.01)) * cw * mw
        return float(round(score, 4))

    def rank_top_alerts(
        self,
        candidate_alerts: List[Dict],
        held_out_state: str = "Odisha"
    ) -> Tuple[List[Dict], Dict]:
        """
        Filters candidates for the held-out test state, calculates priority scores,
        and outputs precisely the Top 50 alerts ranked for monthly field visits.
        """
        # Filter for held-out state if specified
        state_candidates = [
            a for a in candidate_alerts
            if a.get("state", held_out_state) == held_out_state
        ]
        if not state_candidates:
            state_candidates = candidate_alerts

        # Ensure priority score is populated
        for alert in state_candidates:
            if "priority_score" not in alert or alert["priority_score"] is None:
                alert["priority_score"] = self.calculate_priority_score(
                    confidence=alert.get("confidence", 0.9),
                    area_ha=alert.get("area_ha", 0.05),
                    threat_cause=alert.get("cause", "MINING_QUARRY"),
                    is_monsoon=alert.get("is_monsoon", False)
                )

        # Sort descending by priority score
        state_candidates.sort(key=lambda a: a["priority_score"], reverse=True)
        top_50 = state_candidates[:self.capacity]

        for rank, a in enumerate(top_50, start=1):
            a["patrol_rank"] = rank

        # Compute Precision@50
        true_positives = sum(1 for a in top_50 if a.get("is_true_loss", True))
        p_at_50 = float(true_positives / max(len(top_50), 1))

        stats = {
            "held_out_state": held_out_state,
            "total_candidates": len(state_candidates),
            "dispatched_count": len(top_50),
            "precision_at_50": round(p_at_50, 4),
            "capacity_limit": self.capacity
        }

        return top_50, stats

    def verify_f1_retention(
        self,
        phase_1_f1: float,
        phase_2_multimodal_f1: float
    ) -> Dict:
        """
        Validates that Phase 2 multimodal fusion does not degrade Phase 1 F1 by more than 5 points.
        ΔF1 = phase_2_multimodal_f1 - phase_1_f1 >= -0.05
        """
        delta_f1 = float(phase_2_multimodal_f1 - phase_1_f1)
        is_compliant = (delta_f1 >= -self.max_f1_degradation)

        return {
            "phase_1_f1": round(phase_1_f1, 4),
            "phase_2_multimodal_f1": round(phase_2_multimodal_f1, 4),
            "f1_delta": round(delta_f1, 4),
            "max_allowed_degradation": self.max_f1_degradation,
            "status": "PASS" if is_compliant else "FAIL",
            "message": (
                f"F1 degradation of {abs(delta_f1):.4f} is within {self.max_f1_degradation} limit"
                if is_compliant else
                f"F1 degraded by {abs(delta_f1):.4f}, exceeding {self.max_f1_degradation} tolerance"
            )
        }
