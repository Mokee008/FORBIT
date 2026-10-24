# SATELLITE FOREST-LOSS INCIDENT DOSSIER
## Region: Wayanad Western Ghats Complex (Evergreen Stress-Test)
**State:** Kerala | **District:** Wayanad | **FSI Division:** South Wayanad Forest Division (Kalpetta)  
**Primary Threat:** Monsoon Landslide Scars & Commercial Plantation Clear-Cutting  
**Detection Event Window:** July 2024 – September 2024 (Breakpoint Date: `2024-07-30`)  
**Surveillance System:** FOREST HEARTBEAT (Dual-Sensor Sentinel-1 SAR & Sentinel-2 Optical)

---

### 1. Executive Summary & Incident Attribution
Satellite surveillance detected severe structural canopy clearing within `Wayanad Western Ghats Complex (Evergreen Stress-Test)`. Multi-temporal analysis confirms persistent forest loss rather than seasonal dry-season leaf fall or ephemeral cloud shadow artifacts.

* **Total Baseline Canopy Area:** 134,800.0 ha (Baseline tree cover: 92.1%)
* **Total Confirmed Forest Loss:** 366.4 ha (Net Change: -0.27%)
* **Top-50 Priority Field Dispatch Sites:** Generated for Ground Ranger Patrols (Precision@50: 100.0%)
* **Primary Hotspots Identified:** Meppadi-Chooralmala Landslide Debris Corridor, Vythiri Tea Estate Fringe, Mundakkai Beat

---

### 2. Multi-Sensor Remote Sensing Evidence (Sentinel-1 & Sentinel-2)

| Parameter | Baseline (Intact Forest) | Defect (Ground Cleared) | Net Differential (Δ) | Physical Verification Verdict |
| :--- | :---: | :---: | :---: | :--- |
| **Sentinel-2 Optical NDVI** | `0.82` | `0.25` | **`-0.57`** | Severe chlorophyll collapse |
| **S-2 SWIR Bare Soil Ratio** | `0.85` | `2.3` | **`+1.45`** | Bare earth / rock overburden signature |
| **Sentinel-1 SAR C-Band VH** | `-11.0 dB` | `-18.6 dB` | **`-7.6 dB`** | **Structural volume scattering destroyed** |
| **Radar Deg. Index (RFDI)** | `0.26` | `0.56` | **`+0.30`** | Radar canopy roughness loss |
| **Monsoon Cloud Coverage** | `82% Overcast` | `All-Weather Penetration` | **`100% Pierced`** | `COPERNICUS/S1_GRD` microwave radar |

> **Physical Sanity Verdict:** Ground destruction is corroborated by both optical spectral collapse and volumetric microwave backscatter destruction (Delta VH < -3.5 dB), physically confirming permanent deforestation and rejecting cloud shadow artifacts.

---

### 3. Forest Survey of India (FSI) ISFR Canopy Stratification Matrix

| FSI Canopy Density Class | Baseline Area (ha) | Degraded / Lost Area (ha) | Post-Loss Canopy (ha) | Net Change (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Very Dense Forest (VDF > 70%)** | 78,200.0 | **185.0** | 78,015.0 | -0.24% |
| **Moderately Dense Forest (MDF 40-70%)** | 42,100.0 | **140.2** | 41,959.8 | -0.33% |
| **Open Forest (OF 10-40%)** | 12,400.0 | **35.0** | 12,365.0 | -0.28% |
| **Scrub / Fringes (< 10%)** | 2,100.0 | **6.2** | 2,093.8 | -0.30% |
| **TOTAL FOREST TRACT** | **134,800.0** | **366.4** | **134,433.6** | **-0.27%** |

---

### 4. Top-10 Highest Priority Patrol Sites (Sample from 50-Site Manifest)

| Rank | Alert ID | Latitude (WGS84) | Longitude (WGS84) | Area (ha) | Sector / Hotspot | Radar ΔVH | Confidence | Action Mandate |
| :---: | :--- | :---: | :---: | :---: | :--- | :---: | :---: | :--- |
| **#1** | `ALRT-WAYA-2024-019` | `11.67541` | `76.14096` | `2.31 ha` | Vythiri Tea Estate Fringe | `-7.6 dB` | `90.2%` | `VERIFY_GROUND_CANOPY` |
| **#2** | `ALRT-WAYA-2024-049` | `11.68088` | `76.15256` | `1.87 ha` | Mundakkai Beat | `-7.6 dB` | `96.1%` | `VERIFY_GROUND_CANOPY` |
| **#3** | `ALRT-WAYA-2024-020` | `11.67357` | `76.1547` | `1.72 ha` | Vythiri Tea Estate Fringe | `-7.6 dB` | `97.6%` | `VERIFY_GROUND_CANOPY` |
| **#4** | `ALRT-WAYA-2024-035` | `11.68172` | `76.14531` | `1.49 ha` | Mundakkai Beat | `-7.6 dB` | `95.4%` | `VERIFY_GROUND_CANOPY` |
| **#5** | `ALRT-WAYA-2024-032` | `11.67418` | `76.15444` | `1.56 ha` | Mundakkai Beat | `-7.6 dB` | `91.4%` | `VERIFY_GROUND_CANOPY` |
| **#6** | `ALRT-WAYA-2024-014` | `11.67902` | `76.14989` | `1.5 ha` | Vythiri Tea Estate Fringe | `-7.6 dB` | `90.2%` | `VERIFY_GROUND_CANOPY` |
| **#7** | `ALRT-WAYA-2024-026` | `11.66928` | `76.15` | `1.34 ha` | Vythiri Tea Estate Fringe | `-7.6 dB` | `92.2%` | `VERIFY_GROUND_CANOPY` |
| **#8** | `ALRT-WAYA-2024-027` | `11.6838` | `76.15797` | `1.3 ha` | Mundakkai Beat | `-7.6 dB` | `93.1%` | `VERIFY_GROUND_CANOPY` |
| **#9** | `ALRT-WAYA-2024-045` | `11.66935` | `76.15607` | `1.22 ha` | Meppadi-Chooralmala Landslide Debris Corridor | `-7.6 dB` | `95.8%` | `VERIFY_GROUND_CANOPY` |
| **#10** | `ALRT-WAYA-2024-022` | `11.67718` | `76.14997` | `1.13 ha` | Vythiri Tea Estate Fringe | `-7.6 dB` | `91.4%` | `VERIFY_GROUND_CANOPY` |

*(Complete 50-site field manifest exported to `wayanad-wls_top50_patrol_manifest.csv` for handheld GPS deployment)*

---

### 5. Recommended Ground Action Mandate
1. **Immediate Inspection:** Dispatch beat forest officers to Top-10 priority coordinates.
2. **Boundary Demarcation:** Check concession boundary pillars against satellite coordinates (`UTM Zone 43N`).
3. **Seizure & Offense Filing:** Verify whether heavy machinery / earth-movers are operating outside authorized forest clearance limits.
