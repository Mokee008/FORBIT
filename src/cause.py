"""
src/cause.py - Evidence-Based Forest Loss Cause Attribution Engine
Rule R1 Compliant: Pure geometric, spectral, and temporal trajectory features.
Zero pretrained foundation models.
Provides explainable SHAP-style feature contributions for why an alert was triggered.
"""

from typing import Dict, List, Tuple
import numpy as np
from scipy import ndimage

CAUSE_CLASSES = [
    "MINING_QUARRY",
    "ROAD_INFRASTRUCTURE",
    "AGRICULTURE_EXPANSION",
    "FOREST_FIRE",
    "FELLING_LOGGING"
]

WHAT_WE_CANNOT_TELL = [
    "Legal concession status / environmental clearance validity (not determinable from space)",
    "Commercial timber volume / board feet lost",
    "Specific tree species composition (requires sub-meter hyperspectral / field botanist ground survey)"
]

class CauseAttributionEngine:
    def __init__(self):
        pass

    def compute_polygon_metrics(self, binary_polygon: np.ndarray, pixel_size_m: float = 10.0) -> Dict[str, float]:
        """Calculates area, perimeter, compactness, and elongation of a clearing patch."""
        area_px = float(np.sum(binary_polygon))
        area_ha = (area_px * (pixel_size_m ** 2)) / 10000.0

        if area_px == 0:
            return {"area_ha": 0.0, "compactness": 0.0, "elongation": 0.0, "solidity": 0.0}

        # Estimate perimeter using morphological gradient
        struct = ndimage.generate_binary_structure(2, 1)
        eroded = ndimage.binary_erosion(binary_polygon, structure=struct)
        perimeter_px = float(np.sum(binary_polygon ^ eroded))
        perimeter_m = perimeter_px * pixel_size_m

        # Polsby-Popper Compactness = 4 * pi * Area / (Perimeter^2)
        compactness = (4.0 * np.pi * (area_px * pixel_size_m ** 2)) / max(perimeter_m ** 2, 1.0)
        compactness = float(np.clip(compactness, 0.0, 1.0))

        # Elongation from inertia tensor eigenvalues
        y_coords, x_coords = np.where(binary_polygon)
        if len(y_coords) > 2:
            y_c = y_coords - np.mean(y_coords)
            x_c = x_coords - np.mean(x_coords)
            cov = np.cov(np.vstack([y_c, x_c]))
            try:
                eigvals = np.linalg.eigvalsh(cov)
                major = max(eigvals)
                minor = min(eigvals)
                elongation = float(np.sqrt(max(major / max(minor, 1e-4), 1.0)))
            except Exception:
                elongation = 1.0
        else:
            elongation = 1.0

        return {
            "area_ha": round(area_ha, 3),
            "perimeter_m": round(perimeter_m, 1),
            "compactness": round(compactness, 3),
            "elongation": round(min(elongation, 25.0), 2)
        }

    def attribute_cause(
        self,
        polygon_mask: np.ndarray,
        pre_bands: np.ndarray,      # (6, H, W) B2, B3, B4, B8, B11, B12
        post_bands: np.ndarray,     # (6, H, W)
        post_trajectory_ndvi: List[float]
    ) -> Dict:
        """
        Attributes loss cause from geometric morphology + spectral changes:
        - Linear + high elongation (> 4.5) -> ROAD_INFRASTRUCTURE
        - High SWIR bare soil index + concentrated pit shape -> MINING_QUARRY
        - High NBR drop + rapid charcoal spectral signature -> FOREST_FIRE
        - Cyclic seasonal regreening -> AGRICULTURE_EXPANSION
        - Patchy canopy thinning with intact soil -> FELLING_LOGGING
        """
        geom = self.compute_polygon_metrics(polygon_mask)
        poly_idx = np.where(polygon_mask)

        if len(poly_idx[0]) == 0:
            return {
                "predicted_cause": "UNCLEAR",
                "cause": "UNCLEAR",  # Backward-compatible alias for older callers.
                "confidence": 0.0,
                "evidence": ["No pixels in polygon."],
                "geometry": geom,
                "spectral_signatures": {"ndvi_drop": 0.0, "swir_bare_ratio": 0.0},
                "post_clearing_state": "Unknown",
                "what_we_cannot_tell": WHAT_WE_CANNOT_TELL
            }

        # Spectral shifts
        b4_post = np.mean(post_bands[2][poly_idx]) # Red
        b8_pre = np.mean(pre_bands[3][poly_idx])   # NIR
        b8_post = np.mean(post_bands[3][poly_idx])
        b11_post = np.mean(post_bands[4][poly_idx]) # SWIR1
        b12_post = np.mean(post_bands[5][poly_idx]) # SWIR2

        # Indices
        ndvi_drop = float(((b8_pre - np.mean(pre_bands[2][poly_idx])) / max(b8_pre + np.mean(pre_bands[2][poly_idx]), 1e-4)) -
                          ((b8_post - b4_post) / max(b8_post + b4_post, 1e-4)))

        swir_bare_ratio = float((b11_post + b12_post) / max(b8_post + 1e-4, 1e-4))

        evidence = []
        scores = {c: 0.10 for c in CAUSE_CLASSES}

        # Rule 1: High elongation indicates linear road or haul corridor
        if geom["elongation"] > 4.0:
            scores["ROAD_INFRASTRUCTURE"] += 0.55
            evidence.append(f"High geometric elongation ratio ({geom['elongation']}x) with low compactness ({geom['compactness']}).")

        # Rule 2: High SWIR bare rock/soil + compact pit excavation indicates mining
        if swir_bare_ratio > 1.8 and geom["elongation"] <= 4.0:
            scores["MINING_QUARRY"] += 0.60
            evidence.append(f"Extreme bare-rock/soil SWIR ratio ({swir_bare_ratio:.2f}) consistent with open-cast excavation/overburden.")

        # Rule 3: Sharp NIR collapse with post-fire signature
        if ndvi_drop > 0.45 and b12_post > 0.25 and swir_bare_ratio < 1.6:
            scores["FOREST_FIRE"] += 0.45
            evidence.append(f"Sharp instantaneous NBR/NDVI collapse ({ndvi_drop:.2f}) characteristic of thermal burn.")

        # Rule 4: Post-loss trajectory regreening (Agriculture)
        if len(post_trajectory_ndvi) >= 3 and np.std(post_trajectory_ndvi) > 0.12:
            scores["AGRICULTURE_EXPANSION"] += 0.50
            evidence.append("Cyclic post-clearing vegetation pulse indicates agricultural cropping cycle.")
        elif geom["compactness"] > 0.4 and geom["area_ha"] < 2.0:
            scores["FELLING_LOGGING"] += 0.35
            evidence.append("Localized, discrete canopy hole geometry indicates targeted felling.")

        # Normalize probability distribution
        total = sum(scores.values())
        probs = {k: round(v / total, 3) for k, v in scores.items()}
        top_cause = max(probs, key=probs.get)
        confidence = probs[top_cause]

        # Post-clearing land state
        if swir_bare_ratio > 1.8:
            land_state = "Bare Soil / Pit Excavation"
        elif len(post_trajectory_ndvi) >= 3 and np.mean(post_trajectory_ndvi[-3:]) > 0.45:
            land_state = "Regrowing Scrub / Cropland"
        else:
            land_state = "Cleared Non-Forest Land"

        return {
            "predicted_cause": top_cause,
            "confidence": confidence,
            "probabilities": probs,
            "evidence": evidence,
            "geometry": geom,
            "spectral_signatures": {
                "ndvi_drop": round(ndvi_drop, 3),
                "swir_bare_ratio": round(swir_bare_ratio, 2)
            },
            "post_clearing_state": land_state,
            "what_we_cannot_tell": WHAT_WE_CANNOT_TELL
        }
