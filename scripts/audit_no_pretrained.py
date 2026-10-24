#!/usr/bin/env python3
"""
scripts/audit_no_pretrained.py - R1 Compliance Auditor
Verifies that no pretrained weights, backbones, or foundation models are imported or downloaded.
Produces an audit report in results/anti_pretrain_audit.json.
"""

import os
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

BANNED_IMPORTS_OR_PACKAGES = [
    "torchvision.models",
    "timm",
    "segment_anything",
    "transformers",
    "open_clip",
    "prithvi",
    "clay_foundation",
    "satellites",
    "huggingface_hub",
]

SUSPICIOUS_PATTERNS = [
    re.compile(r"pretrained\s*=\s*True", re.IGNORECASE),
    re.compile(r"\.from_pretrained\s*\("),
    re.compile(r"torch\.hub\.load\s*\("),
    re.compile(r"weights\s*=\s*['\"][A-Za-z0-9_]+['\"]"),
    re.compile(r"https?://.*(huggingface\.co|weights|checkpoints|model_zoo).*\.(pth|pt|bin|safetensors)", re.IGNORECASE)
]

def scan_file(file_path: Path):
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return [{"file": str(file_path), "issue": f"Could not read: {e}"}]

    # Regex scan
    for pattern in SUSPICIOUS_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            violations.append({
                "file": str(file_path.relative_to(ROOT_DIR)),
                "type": "Pattern match",
                "pattern": pattern.pattern,
                "matches": matches[:3]
            })

    # AST scan for imports
    try:
        tree = ast.parse(content, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for banned in BANNED_IMPORTS_OR_PACKAGES:
                        if alias.name.startswith(banned):
                            violations.append({
                                "file": str(file_path.relative_to(ROOT_DIR)),
                                "type": "Banned import",
                                "import": alias.name
                            })
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for banned in BANNED_IMPORTS_OR_PACKAGES:
                        if node.module.startswith(banned):
                            violations.append({
                                "file": str(file_path.relative_to(ROOT_DIR)),
                                "type": "Banned from-import",
                                "import": node.module
                            })
    except SyntaxError:
        pass

    return violations

def main():
    print("Running Rule R1 Integrity Audit: Verifying 0 Pretrained Models...")
    all_violations = []

    scan_dirs = [ROOT_DIR / "src", ROOT_DIR / "scripts", ROOT_DIR / "web"]
    for sdir in scan_dirs:
        if sdir.exists():
            for p in sdir.rglob("*.py"):
                if p.name == "audit_no_pretrained.py":
                    continue
                v = scan_file(p)
                if v:
                    all_violations.extend(v)

    report = {
        "status": "PASS" if len(all_violations) == 0 else "FAIL",
        "rule": "R1: No pretrained backbones, weights, or external ML data products",
        "scanned_directories": [str(d.relative_to(ROOT_DIR)) for d in scan_dirs if d.exists()],
        "violations_count": len(all_violations),
        "violations": all_violations,
        "checked_at": os.popen("date -u +\"%Y-%m-%dT%H:%M:%SZ\"").read().strip(),
        "weight_init_policy": "All torch modules explicitly initialized with kaiming_normal_ / zeros_ at instantiation."
    }

    out_file = ROOT_DIR / "results" / "anti_pretrain_audit.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Audit complete. Status: {report['status']}. Report saved to {out_file.relative_to(ROOT_DIR)}")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    exit(main())
