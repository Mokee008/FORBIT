#!/usr/bin/env python3
"""
scripts/serve.py - Robust Local Web Server for FOREST HEARTBEAT Dashboard
Serves the web dashboard, satellite imagery, and API endpoints directly.
Auto-recovers from port conflicts.
"""

import http.server
import socketserver
import os
import sys
import json
from pathlib import Path

START_PORT = 8080
ROOT = Path(__file__).resolve().parent.parent

class ForestHeartbeatHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        # Clean query strings
        req_path = self.path.split("?")[0]

        # Route aliases
        if req_path in ("/", "/index.html"):
            self.path = "/web/index.html"
            return super().do_GET()
        elif req_path in ("/style.css", "/app.js", "/forest_data.js"):
            self.path = "/web" + req_path
            return super().do_GET()
        elif req_path.startswith("/satellite_imagery/"):
            self.path = "/web" + req_path
            return super().do_GET()

        # Built-in API endpoints so dashboard works standalone without uvicorn
        if req_path == "/api/forests":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            registry_file = ROOT / "configs" / "forest_registry.json"
            if registry_file.exists():
                with open(registry_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"[]")
            return

        if req_path == "/api/results":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            results_file = ROOT / "results" / "results.json"
            if results_file.exists():
                with open(results_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"{}")
            return

        if req_path == "/api/monthly-alerts":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            results_file = ROOT / "results" / "results.json"
            if results_file.exists():
                with open(results_file) as f:
                    res_data = json.load(f)
                alerts_data = res_data.get("phase_2_extension", {})
                self.wfile.write(json.dumps(alerts_data).encode("utf-8"))
            else:
                self.wfile.write(b"{}")
            return

        if req_path == "/api/export-top50.csv":
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="forest_heartbeat_top50_alerts.csv"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            results_file = ROOT / "results" / "results.json"
            csv_lines = [
                "Rank,Alert_ID,Date,Latitude,Longitude,Area_ha,Threat_Cause,Modality,Confidence,Priority_Score,Monsoon_Flag,Review_Status\n"
            ]
            if results_file.exists():
                with open(results_file) as f:
                    res_data = json.load(f)
                sites = res_data.get("phase_2_extension", {}).get("top_50_patrol_sites", [])
                for s in sites:
                    csv_lines.append(
                        f"{s.get('patrol_rank')},{s.get('alert_id')},{s.get('date')},"
                        f"{s.get('lat')},{s.get('lon')},{s.get('area_ha')},"
                        f"\"{s.get('cause')}\",{s.get('modality')},{s.get('confidence')},"
                        f"{s.get('priority_score')},{'YES' if s.get('is_monsoon') else 'NO'},VISIT\n"
                    )
            self.wfile.write("".join(csv_lines).encode("utf-8"))
            return

        # Specific forest report JSON or Markdown endpoint
        if req_path.startswith("/api/reports/"):
            if req_path.endswith(".md"):
                fid = req_path.replace("/api/reports/", "").replace(".md", "")
                md_file = ROOT / "reports" / f"{fid}_incident_report.md"
                if md_file.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "text/markdown; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="{fid}_incident_report.md"')
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    with open(md_file, "rb") as f:
                        self.wfile.write(f.read())
                    return
            else:
                fid = req_path.replace("/api/reports/", "").replace(".json", "")
                report_file = ROOT / "reports" / f"{fid}_incident_report.json"
                if report_file.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    with open(report_file, "rb") as f:
                        self.wfile.write(f.read())
                    return

        # Specific forest CSV manifest download endpoint
        if req_path.startswith("/api/manifests/"):
            filename = req_path.replace("/api/manifests/", "")
            csv_file = ROOT / "reports" / filename
            if csv_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(csv_file, "rb") as f:
                    self.wfile.write(f.read())
                return

        # Specific dossier download endpoint
        if req_path.startswith("/api/dossiers/"):
            filename = req_path.replace("/api/dossiers/", "")
            md_file = ROOT / "reports" / filename
            if md_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(md_file, "rb") as f:
                    self.wfile.write(f.read())
                return

        return super().do_GET()

def main():
    os.chdir(ROOT)
    socketserver.TCPServer.allow_reuse_address = True

    # Try ports 8080 up to 8090
    port = START_PORT
    httpd = None

    while port < START_PORT + 10:
        try:
            httpd = socketserver.TCPServer(("", port), ForestHeartbeatHandler)
            break
        except OSError as e:
            if e.errno == 48:  # Address already in use
                port += 1
            else:
                raise e

    if not httpd:
        print(f"Error: All ports between {START_PORT} and {START_PORT + 10} are busy.")
        print(f"Run: kill -9 $(lsof -ti:{START_PORT}) to free port {START_PORT}.")
        sys.exit(1)

    print("=" * 64)
    print("   FOREST HEARTBEAT — SATELLITE MONITOR READY!")
    print(f"   Open in Browser: http://localhost:{port}")
    print("=" * 64)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
