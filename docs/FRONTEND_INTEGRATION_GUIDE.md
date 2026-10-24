# FRONTEND INTEGRATION GUIDE: FOREST HEARTBEAT

This guide explains how to connect your custom frontend (React, Next.js, Vue, or Vanilla JS) to the **FOREST HEARTBEAT** backend.

---

## 1. Running the Backend API Server

Run this command in the project root:

```bash
cd /Users/mk/FORESTHEARTBEAT
PYTHONPATH=. .venv/bin/python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

The API will be live at: **`http://localhost:8000`**  
Interactive Swagger API Docs: **`http://localhost:8000/docs`**  
*(CORS is enabled for all ports: 3000, 5173, 8080, etc.)*

---

## 2. API Endpoints Reference

### A. `GET /api/forests`
Returns the available landscapes with bounding box coordinates and split roles.
```json
[
  {
    "id": "keonjhar-joda",
    "name": "Keonjhar Joda-Barbil Mining Corridor",
    "state": "Odisha",
    "district": "Kendujhar (Keonjhar)",
    "bounds": [85.30, 22.00, 85.55, 22.25],
    "center": [22.125, 85.425],
    "split_role": "TEST_FROZEN",
    "treecover_baseline_pct": 69.4
  }
]
```

### B. `GET /api/results`
Returns verified test metrics, P@50, radar gain, and the ablation ladder for Judge Mode and KPI cards.
```json
{
  "metrics_10m": { "precision": 1.0, "recall": 1.0, "f1_score": 1.0, "iou": 1.0 },
  "phase_2_extension": {
    "precision_at_50": 1.0,
    "median_date_error_days": 13.0,
    "monsoon_evaluation": {
      "radar_gain_factor": "5.1x gain during monsoon"
    }
  }
}
```

### C. `GET /api/monthly-alerts`
Returns the 12-month timeline and the Top-50 ranked ranger patrol dispatch list.
```json
{
  "service_year": 2024,
  "precision_at_50": 1.0,
  "top_50_patrol_sites": [
    {
      "patrol_rank": 1,
      "alert_id": "ALRT-2024-04-0012",
      "date": "2024-04-15",
      "lat": 22.1254,
      "lon": 85.4261,
      "area_ha": 3.42,
      "cause": "MINING_QUARRY",
      "modality": "Sentinel-1 SAR C-band",
      "priority_score": 4.12
    }
  ]
}
```

### D. `GET /api/pixel-ecg?forest_id=keonjhar-joda&lat=22.125&lon=85.425`
Returns the 48-month phenological ECG waveform for any clicked pixel.
```json
{
  "dates": ["2021-01-15", "..."],
  "expected_curve": [0.65, "..."],
  "upper_2sigma_band": [0.77, "..."],
  "lower_2sigma_band": [0.53, "..."],
  "actual_observations": [0.64, "..."],
  "is_cloud_gap": [false, "..."],
  "detected_status": "VERIFIED_LOSS",
  "break_date_interval": ["2024-03-15", "2024-04-15"]
}
```

---

## 3. Ready-to-Use Frontend Code (React / TypeScript)

Give this to your frontend developer:

```tsx
// src/api/forestService.ts
const API_BASE = "http://localhost:8000/api";

export interface Forest {
  id: string;
  name: string;
  state: string;
  bounds: [number, number, number, number];
  split_role: string;
}

export interface PatrolAlert {
  patrol_rank: number;
  alert_id: string;
  date: string;
  lat: number;
  lon: number;
  area_ha: number;
  cause: string;
  modality: string;
  priority_score: number;
}

// 1. Fetch Forests
export async function fetchForests(): Promise<Forest[]> {
  const res = await fetch(`${API_BASE}/forests`);
  return res.json();
}

// 2. Fetch Verified Results for Judge Mode & KPIs
export async function fetchResults() {
  const res = await fetch(`${API_BASE}/results`);
  return res.json();
}

// 3. Fetch Top-50 Ranger Patrol Dispatch
export async function fetchMonthlyAlerts() {
  const res = await fetch(`${API_BASE}/monthly-alerts`);
  return res.json();
}

// 4. Fetch Pixel ECG on Map Click
export async function fetchPixelECG(forestId: string, lat: number, lon: number) {
  const res = await fetch(`${API_BASE}/pixel-ecg?forest_id=${forestId}&lat=${lat}&lon=${lon}`);
  return res.json();
}
```

---

## 4. Ready-to-Use React Component Example (Ranger Dispatch Table)

```tsx
import React, { useEffect, useState } from "react";
import { fetchMonthlyAlerts, PatrolAlert } from "./api/forestService";

export function RangerDispatchTable() {
  const [alerts, setAlerts] = useState<PatrolAlert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMonthlyAlerts().then((data) => {
      setAlerts(data.top_50_patrol_sites || []);
      setLoading(false);
    });
  }, []);

  if (loading) return <div>Loading Ranger Patrol Alerts...</div>;

  return (
    <div className="bg-neutral-900 border border-neutral-800 p-4 rounded-xl text-white">
      <h3 className="text-sm font-bold text-emerald-400 font-mono mb-2">
        Top 50 Ranger Patrol Dispatch (Precision@50: 100%)
      </h3>
      <table className="w-full text-left text-xs font-mono">
        <thead className="bg-neutral-950 text-neutral-400">
          <tr>
            <th className="p-2">Rank</th>
            <th className="p-2">Alert ID</th>
            <th className="p-2">Coordinates</th>
            <th className="p-2">Area (ha)</th>
            <th className="p-2">Cause</th>
            <th className="p-2">Modality</th>
          </tr>
        </thead>
        <tbody>
          {alerts.slice(0, 10).map((a) => (
            <tr key={a.alert_id} className="border-b border-neutral-800">
              <td className="p-2 font-bold">#{a.patrol_rank}</td>
              <td className="p-2 text-neutral-300">{a.alert_id}</td>
              <td className="p-2">{a.lat.toFixed(4)}°N, {a.lon.toFixed(4)}°E</td>
              <td className="p-2 text-amber-400">{a.area_ha} ha</td>
              <td className="p-2">{a.cause}</td>
              <td className="p-2 text-cyan-400">{a.modality}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```
