"""
src/confounder_filter.py - Explicit Confounder Filtering Module
Part of 10% Extension: Filters out seasonal false positives:
1. Deciduous leaf fall (phenological teak/sal winter canopy shedding)
2. Agricultural cyclical harvesting (regular fields with rapid 60-90 day crop rebound)
3. River boundary shifts (seasonal monsoon expansion/contraction of waterbodies)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple

class ConfounderFilter:
    """
    Modular post-processing & temporal attention filter to isolate true permanent
    forest clearing from environmental and land-use confounders.
    """
    def __init__(
        self,
        leaf_fall_z_thresh: float = -2.2,
        agri_rebound_days: int = 90,
        river_mndwi_thresh: float = 0.15
    ):
        self.leaf_fall_z_thresh = leaf_fall_z_thresh
        self.agri_rebound_days = agri_rebound_days
        self.river_mndwi_thresh = river_mndwi_thresh

    def filter_deciduous_leaf_fall(
        self,
        z_scores: np.ndarray,
        expected_seasonal: np.ndarray,
        actual_ndvi: np.ndarray,
        doys: np.ndarray
    ) -> Tuple[bool, str]:
        """
        Distinguishes deciduous winter/dry-season leaf fall (Feb-Apr) from permanent clearing.
        - Deciduous leaf-fall tracks the harmonic seasonal expectation: z-score stays ~ 0 even when raw NDVI drops.
        - Clearing causes a severe structural deviation below the seasonal envelope (z < z_threshold).
        """
        # If minimum z-score does not break the dynamic seasonal threshold, it is phenological shedding
        min_z = np.nanmin(z_scores)
        if min_z > self.leaf_fall_z_thresh:
            return True, "FILTERED: Deciduous leaf fall (tracks seasonal harmonic baseline, no break)"
        
        # Check if NDVI recovers with monsoon green-up
        dry_season_mask = (doys >= 45) & (doys <= 120)
        monsoon_mask = (doys >= 180) & (doys <= 270)
        
        if np.any(dry_season_mask) and np.any(monsoon_mask):
            dry_min = np.nanmin(actual_ndvi[dry_season_mask])
            monsoon_mean = np.nanmean(actual_ndvi[monsoon_mask])
            # If canopy rebounds back above 0.60 in monsoon, it was temporary leaf shedding
            if dry_min < 0.40 and monsoon_mean > 0.62:
                return True, "FILTERED: Seasonal phenology confirmed by monsoon canopy rebound"

        return False, "CONFIRMED_ANOMALY: Structural loss deviates from seasonal cycle"

    def filter_agricultural_harvesting(
        self,
        dates: List[str],
        ndvi_series: np.ndarray,
        patch_compactness: float = 0.85
    ) -> Tuple[bool, str]:
        """
        Distinguishes agricultural harvesting from permanent deforestation.
        - Agriculture exhibits cyclical sharp drops followed by rapid greening within 60-90 days.
        - Forest clearing remains flatlined in bare soil / secondary scrub indefinitely.
        - High patch compactness / rectangularity indicates agricultural parcels.
        """
        if len(ndvi_series) < 4:
            return False, "INSUFFICIENT_DATA: Keep candidate"

        # Check for rapid rebound post-drop
        drop_idx = np.argmin(np.diff(ndvi_series))
        if drop_idx + 2 < len(ndvi_series):
            post_drop_values = ndvi_series[drop_idx + 1: drop_idx + 4]
            rebound_delta = np.nanmax(post_drop_values) - ndvi_series[drop_idx + 1]
            if rebound_delta > 0.25 and patch_compactness > 0.75:
                return True, "FILTERED: Agricultural crop cycle (rapid replanting rebound detected)"

        return False, "CONFIRMED_DEFORESTATION: Persistent low canopy without crop rebound"

    def filter_river_boundary_shifts(
        self,
        green_band: np.ndarray,
        swir_band: np.ndarray,
        distance_to_water_px: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Distinguishes river channel migration / monsoon flooding from deforestation.
        MNDWI = (Green - SWIR) / (Green + SWIR). Water has positive MNDWI.
        """
        denom = np.maximum(green_band + swir_band, 1e-4)
        mndwi = (green_band - swir_band) / denom

        # If pixel converted to standing/flowing water (MNDWI > 0.15) near existing river
        if np.nanmean(mndwi) > self.river_mndwi_thresh and distance_to_water_px < 3.0:
            return True, "FILTERED: River course migration / seasonal waterbody expansion"

        return False, "CONFIRMED_TERRESTRIAL: Dry-land deforestation"

    def apply_all_filters(
        self,
        z_scores: np.ndarray,
        expected_seasonal: np.ndarray,
        actual_ndvi: np.ndarray,
        doys: np.ndarray,
        dates: List[str],
        green_band: Optional[np.ndarray] = None,
        swir_band: Optional[np.ndarray] = None
    ) -> Dict:
        """Runs all 3 confounder checks and returns filtered decision."""
        is_leaf_fall, leaf_reason = self.filter_deciduous_leaf_fall(
            z_scores, expected_seasonal, actual_ndvi, doys
        )
        if is_leaf_fall:
            return {"is_loss": False, "confounder_type": "DECIDUOUS_LEAF_FALL", "reason": leaf_reason}

        is_agri, agri_reason = self.filter_agricultural_harvesting(dates, actual_ndvi)
        if is_agri:
            return {"is_loss": False, "confounder_type": "AGRICULTURAL_HARVEST", "reason": agri_reason}

        if green_band is not None and swir_band is not None:
            is_river, river_reason = self.filter_river_boundary_shifts(green_band, swir_band)
            if is_river:
                return {"is_loss": False, "confounder_type": "RIVER_SHIFT", "reason": river_reason}

        return {"is_loss": True, "confounder_type": "NONE", "reason": "Verified permanent loss"}
