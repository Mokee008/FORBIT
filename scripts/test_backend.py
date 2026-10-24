#!/usr/bin/env python3
"""
scripts/test_backend.py - Comprehensive Backend Server & API Test Suite for VS Code
Tests all backend routes, static file serving, satellite image delivery, and REST APIs.
Works both with live running server (http://localhost:8082) and with in-process mock handler.
"""

import sys
import os
import json
import io
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Color formatting for terminal
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

from scripts.serve import ForestHeartbeatHandler

class MockSocket:
    def __init__(self, data=b""):
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        if "r" in mode:
            return self.rfile
        return self.wfile

    def sendall(self, b):
        self.wfile.write(b)

class DummyServer:
    pass

class InProcessTestClient:
    """Simulates HTTP requests directly against ForestHeartbeatHandler without needing open sockets."""
    def __init__(self):
        self.handler_class = ForestHeartbeatHandler
        self.server = DummyServer()

    def get(self, path):
        req_bytes = f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("utf-8")
        sock = MockSocket(req_bytes)
        try:
            handler = self.handler_class(sock, ("127.0.0.1", 12345), self.server)
            sock.wfile.seek(0)
            res_raw = sock.wfile.read()
            header_end = res_raw.find(b"\r\n\r\n")
            if header_end != -1:
                header_text = res_raw[:header_end].decode("utf-8", errors="ignore")
                body = res_raw[header_end + 4:]
                status_line = header_text.splitlines()[0]
                status_code = int(status_line.split()[1])
            else:
                status_code = 200
                body = res_raw
            return status_code, body
        except Exception as e:
            return 500, str(e).encode("utf-8")

def find_server_port():
    """Probes ports 8080 through 8090 to check if live server is answering."""
    for port in range(8080, 8091):
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/forests")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                if resp.status == 200:
                    return port
        except Exception:
            continue
    return None

def main():
    print(f"\n{BOLD}{'=' * 72}{RESET}")
    print(f"{BOLD}{CYAN}  FOREST HEARTBEAT — VS CODE BACKEND SERVER & API TEST SUITE{RESET}")
    print(f"{BOLD}{'=' * 72}{RESET}\n")

    port = find_server_port()
    live_mode = (port is not None)

    if live_mode:
        print(f"  {GREEN}✓ Live Server Detected on:{RESET} {BOLD}http://localhost:{port}{RESET}")
        print(f"  Running live HTTP requests against daemon...\n")
    else:
        print(f"  {CYAN}ℹ Testing in-process against ForestHeartbeatHandler (zero-network sandbox mode)...{RESET}\n")

    client = InProcessTestClient()

    def request_path(path):
        if live_mode:
            try:
                url = f"http://127.0.0.1:{port}{path}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    return resp.status, resp.read()
            except Exception:
                pass
        return client.get(path)

    passed = 0
    total = 0

    def run_check(section_name, path, validator):
        nonlocal passed, total
        total += 1
        status, body = request_path(path)
        ok, msg = validator(status, body)
        if ok:
            passed += 1
            print(f"  {GREEN}✓ PASS{RESET} {path} {CYAN}({status} OK, {len(body):,} bytes){RESET}")
        else:
            print(f"  {RED}✗ FAIL{RESET} {path} — {msg}")

    # Section 1: Core Static Web Assets
    print(f"{BOLD}[1] Testing Core Web Assets & Dashboard UI Shell:{RESET}")
    run_check("HTML", "/", lambda s, b: (s == 200 and b"<!DOCTYPE html>" in b, "Missing <!DOCTYPE html>"))
    run_check("CSS", "/style.css", lambda s, b: (s == 200 and len(b) > 200, "Stylesheet empty or missing"))
    run_check("JS", "/app.js", lambda s, b: (s == 200 and b"FOREST HEARTBEAT" in b, "App script missing header"))
    run_check("DATA", "/forest_data.js", lambda s, b: (s == 200 and b"window.REAL_FOREST_DATA" in b, "Missing forest_data.js"))

    # Section 2: Forest Registry API
    print(f"\n{BOLD}[2] Testing Forest Registry & Metadata API:{RESET}")
    def validate_forests(s, b):
        if s != 200: return False, f"Expected 200, got {s}"
        data = json.loads(b.decode("utf-8"))
        if len(data) < 8: return False, f"Expected >= 8 forests, got {len(data)}"
        return True, ""
    run_check("Forests", "/api/forests", validate_forests)

    # Section 3: Regional Incident Reports JSON (All 8 Biomes)
    print(f"\n{BOLD}[3] Testing Real-World Regional Incident Reports (All 8 Forests):{RESET}")
    forest_ids = [
        "keonjhar-joda", "similipal-biosphere", "dhenkanal-hindol",
        "hasdeo-arand", "korba-coalfields", "saranda-forest",
        "wayanad-wls", "dampa-tiger-reserve"
    ]
    for fid in forest_ids:
        def validate_report(s, b, target_fid=fid):
            if s != 200: return False, f"Expected 200, got {s}"
            data = json.loads(b.decode("utf-8"))
            if data.get("forest_id") != target_fid: return False, "Mismatched forest_id"
            if "top_50_summary" not in data: return False, "Missing top_50_summary"
            if len(data.get("monthly_breakdown", [])) != 12: return False, "Missing 12-month breakdown"
            return True, ""
        run_check(fid, f"/api/reports/{fid}", validate_report)

    # Section 4: Markdown Incident Dossiers
    print(f"\n{BOLD}[4] Testing Markdown Incident Dossiers (.md Streaming):{RESET}")
    for fid in ["keonjhar-joda", "hasdeo-arand", "wayanad-wls"]:
        def validate_md(s, b):
            if s != 200: return False, f"Expected 200, got {s}"
            text = b.decode("utf-8")
            if "SATELLITE FOREST-LOSS INCIDENT DOSSIER" not in text: return False, "Missing title"
            if "Forest Survey of India" not in text: return False, "Missing FSI section"
            return True, ""
        run_check(fid, f"/api/reports/{fid}.md", validate_md)

    # Section 5: Field Patrol CSV Manifests
    print(f"\n{BOLD}[5] Testing Field Patrol GPS Manifest Downloads (CSV):{RESET}")
    csv_files = [
        "keonjhar-joda_top50_patrol_manifest.csv",
        "hasdeo-arand_top50_patrol_manifest.csv",
        "all_8_forests_top400_patrol_manifest.csv"
    ]
    for cf in csv_files:
        def validate_csv(s, b):
            if s != 200: return False, f"Expected 200, got {s}"
            text = b.decode("utf-8")
            lines = text.strip().splitlines()
            if len(lines) < 50: return False, f"Expected >= 50 rows, got {len(lines)}"
            if "Alert_ID" not in lines[0]: return False, "Missing Alert_ID header"
            return True, ""
        run_check(cf, f"/api/manifests/{cf}", validate_csv)

    # Section 6: High-Resolution Satellite Image Delivery
    print(f"\n{BOLD}[6] Testing High-Resolution Before & After Satellite Imagery:{RESET}")
    images = [
        "/satellite_imagery/keonjhar-joda_before.png",
        "/satellite_imagery/keonjhar-joda_after.png",
        "/satellite_imagery/hasdeo-arand_before.png",
        "/satellite_imagery/hasdeo-arand_after.png",
        "/satellite_imagery/wayanad-wls_before.png",
        "/satellite_imagery/wayanad-wls_after.png"
    ]
    for img in images:
        def validate_img(s, b):
            if s != 200: return False, f"Expected 200, got {s}"
            if len(b) < 100000: return False, f"Image file too small ({len(b)} bytes)"
            if not b.startswith(b"\x89PNG"): return False, "Not a valid PNG header"
            return True, ""
        run_check(img, img, validate_img)

    # Summary
    pct = (passed / total) * 100
    print(f"\n{BOLD}{'=' * 72}{RESET}")
    if passed == total:
        print(f"{GREEN}{BOLD}  SUCCESS: ALL {passed}/{total} BACKEND TESTS PASSED ({pct:.1f}%)!{RESET}")
        print(f"{GREEN}  The server and all REST/static endpoints are fully operational for VS Code.{RESET}")
    else:
        print(f"{YELLOW}{BOLD}  RESULT: {passed}/{total} PASSED ({pct:.1f}%){RESET}")
    print(f"{BOLD}{'=' * 72}{RESET}\n")

if __name__ == "__main__":
    main()
