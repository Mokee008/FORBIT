"""
src/dataset.py - Dataset Loader for Multi-Temporal Sentinel-2 Patches & Aligned Labels
Enforces Rule R1 and R5.
Supports both PyTorch Dataset and NumPy batch iteration.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from src.cloud_mask import RuleBasedCloudMasker

class ForestPatchDataset:
    def __init__(self, data_dir: str, patch_size: int = 128):
        self.data_dir = Path(data_dir)
        self.patch_size = patch_size
        self.files = sorted(list(self.data_dir.glob("*.npz")))
        self.masker = RuleBasedCloudMasker(dilation_px=2)

    def __len__(self) -> int:
        return len(self.files)

    def load_tile(self, idx: int) -> Dict:
        tile_path = self.files[idx]
        data = np.load(tile_path, allow_pickle=True)
        return {
            "forest_id": str(data["forest_id"]),
            "state": str(data["state"]),
            "dates": list(data["dates"]),
            "doys": data["doys"],
            "bands": data["bands"],                 # (T, 6, H, W)
            "valid_mask": data["valid_mask"],       # (T, H, W)
            "cloud_mask": data["cloud_mask"],       # (T, H, W)
            "loss_geom": data["loss_geom"],         # (H, W)
            "treecover2000": data["treecover2000"], # (H, W)
            "lossyear": data["lossyear"],           # (H, W)
            "file_name": tile_path.name
        }

    def get_two_date_pair(self, idx: int, date_a_idx: int = 0, date_b_idx: int = -1) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extracts two-date pair for Baseline A0:
        Returns:
            x: (12, H, W) stack of bands at Date A and Date B
            y_loss: (1, H, W) binary loss mask between A and B
            valid_pair: (H, W) boolean mask where both acquisitions are valid
        """
        tile = self.load_tile(idx)
        bands_a = tile["bands"][date_a_idx] # (6, H, W)
        bands_b = tile["bands"][date_b_idx] # (6, H, W)
        x = np.concatenate([bands_a, bands_b], axis=0) # (12, H, W)

        # Loss occurred if lossyear is within this period
        y_loss = tile["loss_geom"].astype(np.float32)[np.newaxis, ...] # (1, H, W)
        valid_pair = tile["valid_mask"][date_a_idx] & tile["valid_mask"][date_b_idx]

        return x, y_loss, valid_pair
