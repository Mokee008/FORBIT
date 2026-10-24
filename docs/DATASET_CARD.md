# DATASET CARD: FOREST HEARTBEAT (CL-01)

## 1. Overview & Problem Definition
* **Name:** FOREST HEARTBEAT Benchmark & Training Corpus
* **Task:** Satellite Forest-Loss Alerts in India between two arbitrary dates under severe cloud occlusion and phenological canopy fluctuations.
* **Target Resolution:** 10 m native pixel size (Sentinel-2 L2A).
* **Weak Supervised Label:** Hansen Global Forest Change v1.12 (`UMD/hansen/global_forest_change_2024_v1_12`) 30 m annual loss product (`lossyear` 21-24) + `treecover2000` baseline.

## 2. Spatial & Temporal Splits (Zero-Leakage Guarantee)
* **Training State (`TRAIN_STATE`):** Chhattisgarh (Hasdeo Arand moist deciduous forest & Korba coal mining belt) + Jharkhand expansion (Saranda iron ore forest).
  * Training years: 2021 – 2023.
  * Spatial partitioning: 5 km disjoint blocks with 1 km inter-block buffer zones.
* **Testing State (`TEST_STATE` - Frozen Holdout):** Odisha (Keonjhar/Joda-Barbil mining corridor + Similipal tiger reserve / deciduous fire belt).
  * Holdout year: 2024 (spatial AND temporal hold-out).
  * Hashed manifest locked at `manifests/test_frozen.sha256`. Never touched during hyperparameter selection or calibration.
* **Stress-Test Failure Benchmarks:**
  * Kerala (Wayanad): 4-month monsoon cloud occlusion stress test.
  * Mizoram (Dampa): Rapid regrowth / Jhum shifting cultivation ambiguity.

## 3. Data Sources & Rule Compliance
* **Imagery:** Sentinel-2 Level-2A Bottom-Of-Atmosphere (BOA) Reflectance. Bands: B2, B3, B4, B8, B11, B12.
* **Cloud Masking:** Custom 4-stage rule-based mask (`SCL` QA classes + Blue/SWIR whiteness + NIR-dark shadow geometry projection + temporal outlier rejection).
* **Rule R1 Audit:** Strict zero-pretrained backbone policy. All neural modules initialized via `torch.nn.init.kaiming_normal_`. Zero external ML products (no Cloud Score+, s2cloudless, Dynamic World, WorldCover). Verified via `scripts/audit_no_pretrained.py`.

## 4. Known Biases & Inherent Limitations
1. **Monsoon Blind Spots:** Up to 120 continuous days with 0 valid optical observations across July–September. Forest loss during this window is reported as an interval with `UNKNOWN_CLOUD_GAP` flag.
2. **Coarse-to-Fine Label Mismatch:** Hansen 30 m labels carry boundary discretization noise and temporal lag relative to Sentinel-2 10 m real-time clearing.
3. **Selective Logging:** Tree felling under closed canopy without total canopy collapse remains undetectable at 10 m optical resolution.
