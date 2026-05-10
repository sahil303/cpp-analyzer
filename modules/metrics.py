"""
modules/metrics.py
Parses raw tool outputs into a unified metrics JSON.
Detects OO smells and maps them to principle violations.
"""

import os
import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path


# OO Principle violation mappings
SMELL_PRINCIPLES = {
    "god_class":            ["SRP - Single Responsibility Principle", "Encapsulation"],
    "long_method":          ["SRP - Single Responsibility Principle"],
    "high_complexity":      ["SRP - Single Responsibility Principle", "Open/Closed Principle"],
    "too_many_parameters":  ["Encapsulation", "SRP"],
    "high_coupling":        ["DIP - Dependency Inversion Principle", "OCP - Open/Closed Principle"],
    "poor_naming":          ["Readability / Maintainability"],
    "missing_override":     ["LSP - Liskov Substitution Principle"],
}


def parse_metrics(raw_results: dict, output_dir: str) -> dict:
    """
    Parse all raw tool outputs, detect smells, return unified metrics dict.
    """
    metrics = {
        "summary": {},
        "files": {},
        "smells": {},
        "principle_violations": {},
    }

    # Parse lizard CSV → complexity & length metrics
    if raw_results.get("lizard", {}).get("status") == "ok":
        _parse_lizard(raw_results["lizard"]["file"], metrics)

    # Parse cppcheck XML → code issues
    if raw_results.get("cppcheck", {}).get("status") == "ok":
        _parse_cppcheck(raw_results["cppcheck"]["file"], metrics)

    # Parse clang-tidy text → style/design issues
    if raw_results.get("clang_tidy", {}).get("status") == "ok":
        _parse_clang_tidy(raw_results["clang_tidy"]["file"], metrics)

    # Derive smells from metrics
    _detect_smells(metrics)

    # Map smells to principle violations
    _map_to_principles(metrics)

    # Summary counts
    metrics["summary"]["total_files"] = len(metrics["files"])
    metrics["summary"]["total_smells"] = sum(len(v) for v in metrics["smells"].values())
    metrics["summary"]["files_with_smells"] = len(metrics["smells"])

    # Save unified metrics JSON
    metrics_path = os.path.join(output_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"    Metrics saved → {metrics_path}")
    return metrics


# ─── Lizard Parser ────────────────────────────────────────────────────────────

def _parse_lizard(csv_path: str, metrics: dict):
    """Parse lizard CSV: function complexity and length per file."""
    if not csv_path or not os.path.exists(csv_path):
        return

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                filename = row.get("filename") or row.get("file_name") or ""
                func_name = row.get("name") or row.get("function_name") or "unknown"
                ccn = int(row.get("cyclomatic_complexity") or row.get("CCN") or 0)
                length = int(row.get("nloc") or row.get("length") or 0)
                params = int(row.get("parameter_count") or row.get("args") or 0)

                short_name = _shorten_path(filename)

                if short_name not in metrics["files"]:
                    metrics["files"][short_name] = {"functions": [], "max_ccn": 0, "total_nloc": 0}

                metrics["files"][short_name]["functions"].append({
                    "name": func_name,
                    "ccn": ccn,
                    "nloc": length,
                    "params": params,
                })

                if ccn > metrics["files"][short_name]["max_ccn"]:
                    metrics["files"][short_name]["max_ccn"] = ccn

                metrics["files"][short_name]["total_nloc"] = (
                    metrics["files"][short_name].get("total_nloc", 0) + length
                )

            except (ValueError, KeyError):
                continue


# ─── CppCheck Parser ──────────────────────────────────────────────────────────

def _parse_cppcheck(xml_path: str, metrics: dict):
    """Parse cppcheck XML output for errors and warnings."""
    if not xml_path or not os.path.exists(xml_path):
        return

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError:
        print("    [WARNING] Could not parse cppcheck XML.")
        return

    for error in root.iter("error"):
        severity = error.get("severity", "")
        msg = error.get("msg", "")
        error_id = error.get("id", "")

        for location in error.findall("location"):
            filename = location.get("file", "unknown")
            line = location.get("line", "0")
            short_name = _shorten_path(filename)

            if short_name not in metrics["files"]:
                metrics["files"][short_name] = {"functions": [], "max_ccn": 0, "total_nloc": 0}

            if "cppcheck_issues" not in metrics["files"][short_name]:
                metrics["files"][short_name]["cppcheck_issues"] = []

            metrics["files"][short_name]["cppcheck_issues"].append({
                "id": error_id,
                "severity": severity,
                "message": msg,
                "line": line,
            })


# ─── Clang-tidy Parser ───────────────────────────────────────────────────────

def _parse_clang_tidy(txt_path: str, metrics: dict):
    """Parse clang-tidy text output for warnings."""
    if not txt_path or not os.path.exists(txt_path):
        return

    with open(txt_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            # Format: /path/file.cpp:10:5: warning: message [check-name]
            if ": warning:" in line or ": error:" in line:
                parts = line.split(":")
                if len(parts) >= 4:
                    filename = parts[0].strip()
                    short_name = _shorten_path(filename)
                    message = ":".join(parts[3:]).strip()

                    if short_name not in metrics["files"]:
                        metrics["files"][short_name] = {"functions": [], "max_ccn": 0, "total_nloc": 0}

                    if "clang_tidy_warnings" not in metrics["files"][short_name]:
                        metrics["files"][short_name]["clang_tidy_warnings"] = []

                    metrics["files"][short_name]["clang_tidy_warnings"].append(message)


# ─── Smell Detection ──────────────────────────────────────────────────────────

def _detect_smells(metrics: dict):
    """Detect OO smells based on metric thresholds."""
    for filename, data in metrics["files"].items():
        file_smells = []

        # God Class: file > 500 lines
        if data.get("total_nloc", 0) > 500:
            file_smells.append({
                "type": "god_class",
                "detail": f"File has {data['total_nloc']} lines of code (threshold: 500)",
                "severity": "high",
            })

        # Long Method: any function > 30 lines
        for func in data.get("functions", []):
            if func["nloc"] > 30:
                file_smells.append({
                    "type": "long_method",
                    "detail": f"Function '{func['name']}' has {func['nloc']} lines (threshold: 30)",
                    "severity": "medium",
                })

            # High Complexity
            if func["ccn"] > 10:
                file_smells.append({
                    "type": "high_complexity",
                    "detail": f"Function '{func['name']}' CCN={func['ccn']} (threshold: 10)",
                    "severity": "high",
                })

            # Too Many Parameters
            if func["params"] > 5:
                file_smells.append({
                    "type": "too_many_parameters",
                    "detail": f"Function '{func['name']}' has {func['params']} parameters (threshold: 5)",
                    "severity": "medium",
                })

        if file_smells:
            metrics["smells"][filename] = file_smells


# ─── Principle Mapping ────────────────────────────────────────────────────────

def _map_to_principles(metrics: dict):
    """Map detected smells to OO principle violations."""
    violations = {}
    for filename, smells in metrics["smells"].items():
        for smell in smells:
            principles = SMELL_PRINCIPLES.get(smell["type"], ["Unknown"])
            for p in principles:
                if p not in violations:
                    violations[p] = []
                violations[p].append({
                    "file": filename,
                    "smell": smell["type"],
                    "detail": smell["detail"],
                })

    metrics["principle_violations"] = violations


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _shorten_path(path: str) -> str:
    """Shorten absolute path to just filename for readability."""
    return Path(path).name if path else "unknown"
