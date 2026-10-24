"""
scripts/generate_sample_tiles.py - Generates Standardized 128x128 Tile Arrays
Implements the exact multi-spectral band stack (B2, B3, B4, B8, B11, B12),
validity masks, and aligned Hansen 30m labels.
Saves canonical .npz files for Train (Hasdeo Arand, CG) and Test (Keonjhar, OD).
Calculates and freezes SHA-256 manifest.
"""

import hashlib
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def generate_tile_series(
    forest_id: str,
    state: str,
    years: list,
    loss_year: int = 2023,
    loss_month: int = 4,
    has_mining_clearing: bool = True
):
    """
    Generates a realistic 128x128 pixel tile (~1.28 km x 1.28 km at 10m resolution)
    over 12 months * len(years) time-steps.
    """
    H, W = 128, 128
    T = len(years) * 12
    dates = []
    doys = []

    # Bands: B2, B3, B4, B8, B11, B12 (6 spectral bands)
    bands = np.zeros((T, 6, H, W), dtype=np.float32)
    valid_mask = np.ones((T, H, W), dtype=bool)
    cloud_mask = np.zeros((T, H, W), dtype=bool)

    # Phase 2 Extension: Sentinel-1 C-band SAR Backscatter (VV and VH in dB)
    sar_vv = np.zeros((T, H, W), dtype=np.float32)
    sar_vh = np.zeros((T, H, W), dtype=np.float32)

    # Loss geometry: An expanding open-cast pit polygon in center-right
    loss_geom = np.zeros((H, W), dtype=bool)
    if has_mining_clearing:
        yy, xx = np.ogrid[:H, :W]
        # Pit center (64, 70), elongated ellipse representing haul road & pit
        pit = (((xx - 70) / 25.0) ** 2 + ((yy - 64) / 16.0) ** 2) <= 1.0
        # Haul road extending westward
        road = (np.abs(yy - 64) <= 2) & (xx >= 20) & (xx <= 70)
        loss_geom = pit | road

    t_idx = 0
    for y in years:
        for m in range(1, 13):
            doy = int((m - 0.5) * 30.5)
            dates.append(f"{y}-{m:02d}-15")
            doys.append(doy)

            # Phenology: deciduous canopy in CG/OD has low NDVI in Feb-Apr, peak in Aug-Oct
            omega = 2.0 * np.pi * doy / 365.25
            seasonal_green = 0.55 + 0.18 * np.sin(omega - 1.5) # NDVI ~ 0.37 (March) to 0.73 (Sept)

            # Monsoon clouds in July & August
            is_monsoon_cloud = (m in [7, 8]) and ((y * 13 + m) % 2 == 0)

            for i in range(H):
                for j in range(W):
                    # Check if pixel has cleared by this timestamp
                    is_cleared = False
                    if has_mining_clearing and loss_geom[i, j]:
                        if y > loss_year or (y == loss_year and m >= loss_month):
                            is_cleared = True

                    if is_cleared:
                        # Bare rock/overburden soil: high visible red/swir, low NIR
                        b2 = 0.15 + 0.02 * np.random.rand()
                        b3 = 0.18 + 0.02 * np.random.rand()
                        b4 = 0.24 + 0.03 * np.random.rand() # High red bare soil
                        b8 = 0.22 + 0.02 * np.random.rand() # Low NIR
                        b11 = 0.32 + 0.03 * np.random.rand() # High SWIR (dry pit)
                        b12 = 0.28 + 0.03 * np.random.rand()
                        # SAR: Volume scattering destroyed
                        sar_vv[t_idx, i, j] = -15.5 + 0.4 * np.random.randn()
                        sar_vh[t_idx, i, j] = -23.8 + 0.5 * np.random.randn()
                    else:
                        # Intact Sal/Deciduous Forest with strong seasonal phenology (leaf-drop in March/April)
                        # seasonal_green goes from 0.37 in March to 0.73 in Sept
                        # Canopy leaf shed: NIR drops to 0.16 in March, peaks at 0.44 in Sept
                        b2 = 0.030 + 0.01 * np.random.rand()
                        b3 = 0.045 + 0.015 * seasonal_green + 0.01 * np.random.rand()
                        b4 = 0.040 + 0.07 * (1.0 - seasonal_green) + 0.01 * np.random.rand() # Exposed leaf litter in dry season
                        b8 = 0.14 + 0.35 * seasonal_green + 0.01 * np.random.rand()          # Massive NIR drop during leaf fall
                        b11 = 0.22 - 0.10 * seasonal_green
                        b12 = 0.15 - 0.08 * seasonal_green
                        # SAR: Intact multi-layer canopy volume scattering
                        sar_vv[t_idx, i, j] = -12.2 + 0.4 * np.random.randn()
                        sar_vh[t_idx, i, j] = -17.4 + 0.5 * np.random.randn()

                    if is_monsoon_cloud and (i + j) % 3 == 0:
                        # Cloud artifact
                        b2 += 0.25
                        b4 += 0.20
                        b8 += 0.20
                        cloud_mask[t_idx, i, j] = True
                        valid_mask[t_idx, i, j] = False

                    bands[t_idx, 0, i, j] = b2
                    bands[t_idx, 1, i, j] = b3
                    bands[t_idx, 2, i, j] = b4
                    bands[t_idx, 3, i, j] = b8
                    bands[t_idx, 4, i, j] = b11
                    bands[t_idx, 5, i, j] = b12

            t_idx += 1

    # Hansen baseline tree cover (0-100) and lossyear (0 or YY)
    treecover2000 = np.full((H, W), 78, dtype=np.uint8)
    lossyear = np.zeros((H, W), dtype=np.uint8)
    if has_mining_clearing:
        lossyear[loss_geom] = loss_year % 100 # e.g. 23 for 2023, 24 for 2024

    return {
        "forest_id": forest_id,
        "state": state,
        "years": years,
        "dates": dates,
        "doys": np.array(doys),
        "bands": bands,               # (T, 6, 128, 128)
        "sar_vv": sar_vv,             # (T, 128, 128) Sentinel-1 VV dB
        "sar_vh": sar_vh,             # (T, 128, 128) Sentinel-1 VH dB
        "valid_mask": valid_mask,     # (T, 128, 128)
        "cloud_mask": cloud_mask,     # (T, 128, 128)
        "loss_geom": loss_geom,       # (128, 128)
        "treecover2000": treecover2000,
        "lossyear": lossyear
    }

def main():
    print("Generating standard tile arrays...")
    train_dir = ROOT / "data" / "train"
    val_dir = ROOT / "data" / "val"
    test_dir = ROOT / "data" / "test_frozen"
    manifests_dir = ROOT / "manifests"

    for d in [train_dir, val_dir, test_dir, manifests_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Train Tile: Hasdeo Arand (CG), loss in 2022 (clearing for coal pit)
    tile_train = generate_tile_series("hasdeo-arand", "Chhattisgarh", [2021, 2022, 2023], loss_year=2022, loss_month=5)
    train_file = train_dir / "hasdeo_arand_tile01.npz"
    np.savez_compressed(train_file, **tile_train)
    print(f"Saved Train Tile: {train_file.relative_to(ROOT)} ({train_file.stat().st_size / 1024 / 1024:.2f} MB)")

    # 2. Val Tile: Korba North (CG), loss in 2023
    tile_val = generate_tile_series("korba-coalfields", "Chhattisgarh", [2021, 2022, 2023], loss_year=2023, loss_month=3)
    val_file = val_dir / "korba_tile01.npz"
    np.savez_compressed(val_file, **tile_val)
    print(f"Saved Val Tile: {val_file.relative_to(ROOT)} ({val_file.stat().st_size / 1024 / 1024:.2f} MB)")

    # 3. Test Tile (FROZEN): Keonjhar Joda-Barbil Mining Corridor (Odisha), loss in holdout year 2024!
    tile_test = generate_tile_series("keonjhar-joda", "Odisha", [2021, 2022, 2023, 2024], loss_year=2024, loss_month=4)
    test_file = test_dir / "keonjhar_test_tile01.npz"
    np.savez_compressed(test_file, **tile_test)
    print(f"Saved Test Tile: {test_file.relative_to(ROOT)} ({test_file.stat().st_size / 1024 / 1024:.2f} MB)")

    # Compute SHA-256 Hash of frozen test tile per Rule R5
    sha256 = hashlib.sha256(test_file.read_bytes()).hexdigest()
    manifest_content = f"{sha256}  {test_file.name}\n"
    manifest_file = manifests_dir / "test_frozen.sha256"
    manifest_file.write_text(manifest_content)
    print(f"Rule R5 Test Manifest Frozen: {manifest_file.relative_to(ROOT)} -> {sha256}")

if __name__ == "__main__":
    main()
