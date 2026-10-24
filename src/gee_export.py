"""
src/gee_export.py - Google Earth Engine Ingestion & Monthly Compositing
Uses COPERNICUS/S2_SR_HARMONIZED and UMD/hansen/global_forest_change_2024_v1_12.
Rule R1 Compliant: Extracts raw L2A reflectance (B2, B3, B4, B8, B11, B12, SCL).
Zero pretrained cloud products.
"""

import json
from pathlib import Path

GEE_SCRIPT_TEMPLATE = """
// GEE Code Editor / Python export for FOREST HEARTBEAT
// Target State: Chhattisgarh (Train) & Odisha (Test)

var hansen = ee.Image("UMD/hansen/global_forest_change_2024_v1_12");
var treecover2000 = hansen.select('treecover2000');
var lossyear = hansen.select('lossyear'); // 21=2021, 22=2022, 23=2023, 24=2024

// Hasdeo Arand ROI (12.8 km x 12.8 km target tile)
var roi_hasdeo = ee.Geometry.Rectangle([82.60, 22.75, 82.75, 22.90]);

// Sentinel-2 L2A Surface Reflectance Harmonized
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(roi_hasdeo)
  .filterDate('2021-01-01', '2024-12-31')
  .select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'SCL']);

// Function to compute monthly median composites
var months = ee.List.sequence(1, 12);
var years = ee.List.sequence(2021, 2024);

var monthlyComposites = years.map(function(y) {
  return months.map(function(m) {
    var startDate = ee.Date.fromYMD(y, m, 1);
    var endDate = startDate.advance(1, 'month');
    var filtered = s2.filterDate(startDate, endDate);
    var median = filtered.median().set('system:time_start', startDate.millis());
    var count = filtered.select('B8').count().rename('obs_count');
    return median.addBands(count).clip(roi_hasdeo);
  });
}).flatten();

print("Ready for export to Google Drive / Cloud Storage bucket.");
"""

def generate_gee_export_config():
    root = Path(__file__).resolve().parent.parent
    registry_file = root / "configs" / "forest_registry.json"
    forests = json.loads(registry_file.read_text())

    export_tasks = []
    for f in forests:
        export_tasks.append({
            "forest_id": f["id"],
            "name": f["name"],
            "state": f["state"],
            "bounds": f["bounds"],
            "split_role": f["split_role"],
            "hansen_asset": "UMD/hansen/global_forest_change_2024_v1_12",
            "s2_collection": "COPERNICUS/S2_SR_HARMONIZED",
            "bands": ["B2", "B3", "B4", "B8", "B11", "B12", "SCL"]
        })

    out_path = root / "configs" / "gee_tasks.json"
    out_path.write_text(json.dumps(export_tasks, indent=2))
    print(f"Generated {len(export_tasks)} GEE export task configs in {out_path}")

if __name__ == "__main__":
    generate_gee_export_config()
