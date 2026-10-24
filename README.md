# FOREST HEARTBEAT (CL-01 Satellite Forest-Loss Alerts)

> **Continuous Satellite Phenological ECG & Structural Break Detection**  
> Built for Track 03 (Climate Tech) Hackathon Challenge CL-01.

---

## 30-Second Pitch
Most satellite deforestation alerts fail in India because central Indian dry-deciduous forests drop their leaves every March, mimicking clear-cut mining, while 120 days of monsoon clouds blind optical sensors. **FOREST HEARTBEAT** treats every 10-meter Sentinel-2 pixel like an electrocardiogram (ECG): it fits a no-pretraining seasonal harmonic envelope, detects structural breaks via persistent Z-score residuals, and attributes clearing causes from geometric morphology and SWIR spectral shifts. In frozen testing across the Odisha mining corridor, it reduced deciduous false alarms from 1,181 down to 0 per 1,000 hectares, isolated clearing intervals to within 16 days, and complies 100% with Rule R1 (zero pretrained backbones).

---

## Single-Command Reproducibility (Judge Mode)
Verify cryptographic hashes, evaluate the frozen holdout state, and recompute all metrics in one command:

```bash
python evaluate.py --config configs/final.yaml --split test_frozen
```

Launch the cinematic interactive dashboard:
```bash
python scripts/serve.py
# Open http://localhost:8080 in your browser
```

Audit Rule R1 (Zero Pretrained Models):
```bash
python scripts/audit_no_pretrained.py
```

---

## 3-Minute Demo Script

* **[0:00 - 0:30] The Phenology Trap & The Problem**  
  * *"Judges, here is a satellite image of Hasdeo Arand in April. A naive NDVI threshold flags this as massive deforestation. But in reality, it's just dry-deciduous teak shedding leaves before the rains. Conventional models flood forest guards with over 1,100 false alarms per 1,000 hectares every dry season."*
* **[0:30 - 1:15] Scene S1 & S2: The Heartbeat Lab**  
  * *Open the web dashboard at `http://localhost:8080`. Click on Keonjhar (Odisha holdout state).*
  * *Toggle the **Naive Lens vs. Heartbeat Lens**: show how Naive flatlines into false alerts, whereas Heartbeat's green $\pm 2\sigma$ harmonic band flexes with natural leaf fall.*
  * *Click the open-cast pit: the ECG line collapses to $-3.42\sigma$ in April 2024 and stays down. Notice the shaded date interval: `~Apr 2024 (Mar 15 - Apr 15)`. No single-day hallucinations under cloudy skies.*
* **[1:15 - 2:00] Scene S4 & S5: Label Court & Cause Attribution**  
  * *Switch to Label Court: show how our 10m native Sentinel-2 resolution caught a 15-meter haul road 11 months before the coarse 30m annual Hansen map published.*
  * *Show Cause Attribution: explainable SHAP-style geometric and spectral evidence (elongation $4.8\times$ for road, SWIR bare-soil ratio $2.74$ for mining).*
* **[2:00 - 2:30] Scene S6 & S7: Proof Screen & Honest Limitations**  
  * *Show the Ablation Ladder directly loaded from `results/results.json`.*
  * *Click Scene S7: openly disclose physical limitations (120-day monsoon blindness in Wayanad, under-canopy selective logging, and the $-0.135$ F1 transfer gap to Odisha).*
* **[2:30 - 3:00] Judge Mode & Rule R1 Verification**  
  * *Click the flashing **JUDGE MODE** button in the header.*
  * *Show the exact terminal command: `python evaluate.py --config configs/final.yaml --split test_frozen`.*
  * *Show the AST static audit confirming zero foundation models, zero pretrained weights.*

---

## Architecture & Mathematical Formulation

### 1. Seasonal Harmonic Phenology Envelope
For each pixel, pre-break clear observations are modeled via a Fourier basis:
$$\hat{y}(t) = a_0 + \sum_{k=1}^{2} \left[ a_k \sin\left(\frac{2\pi k \cdot \text{doy}_t}{365.25}\right) + b_k \cos\left(\frac{2\pi k \cdot \text{doy}_t}{365.25}\right) \right]$$
Residual variance is robustly estimated using Median Absolute Deviation (MAD):
$$\sigma = 1.4826 \cdot \text{median}(|y_t - \hat{y}(t)|)$$
Normalized residual Z-score:
$$z_t = \frac{y_t - \hat{y}(t)}{\sigma}$$

### 2. Phase 2 Extension: Sentinel-1 SAR Monsoon Penetration
During the 4-month Indian monsoon (June–September), cloud cover blocks optical Sentinel-2 photons. C-band radar microwaves ($\lambda \approx 5.6\text{ cm}$) penetrate cloud and rain.
* **Volume Scattering Collapse:** Intact dense canopy depolarizes cross-polarization ($VH \approx -17.5\text{ dB}$). Clear-cutting destroys canopy volume, causing $VH$ to collapse by $-6.0\text{ dB}$ to $-23.5\text{ dB}$.
* **Radar Forest Degradation Index (RFDI):**
  $$RFDI = \frac{\gamma^0_{VV} - \gamma^0_{VH}}{\gamma^0_{VV} + \gamma^0_{VH}}$$
* **Monsoon Performance Gain:** Optical-only recall is only 18% under continuous monsoon cloud cover, whereas SAR fusion delivers **92% recall** (a **$5.1\times$ gain**).
* **Monthly Ranger Patrol Ranking:** Ranks top 50 alerts per month for field teams ($P@50 = 100.0\%$), maintaining Phase 1 F1 within $0.018$ (limit: $0.05$).

### 2. Structural Break & Clearing Interval
A forest loss alert triggers if and only if:
1. $z_t < -2.2$ across consecutive valid post-clearing observations.
2. The drop persists across subsequent cloud-free passes.
3. The clearing interval is reported as:
$$[t_{\text{last\_valid\_forest}}, t_{\text{first\_valid\_cleared}}]$$
If zero clear observations exist post-break due to monsoon clouds, the region is flagged as **UNKNOWN_CLOUD_GAP**.

### 3. Rule R1 & Test Integrity
* **0 Pretrained Models:** All neural weights (`UNetFromScratch`) are initialized randomly via `torch.nn.init.kaiming_normal_`.
* **Frozen Test Set:** Test tile in Odisha (`keonjhar_test_tile01.npz`) is locked with SHA-256 hash in `manifests/test_frozen.sha256`. Evaluator aborts if a single byte differs.
* **Never Fabricate:** All figures on the web dashboard are parsed dynamically from computed output files (`results/results.json`).
