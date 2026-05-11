"""
modules/metrics.py
Parses raw tool outputs into a unified metrics JSON.

CK Metrics computed per file:
  WMC  - Weighted Methods per Class   (sum of CCN across all methods)
  RFC  - Response for a Class         (WMC + unique external calls, approx)
  CCN  - Max Cyclomatic Complexity    (worst function in file)
  NLOC - Lines of Code                (total function lines in file)
  CBO  - Coupling Between Objects     (unique #include dependencies)
  LCOM - Lack of Cohesion in Methods  (approx ratio of uncohesive functions)
  DIT  - Depth of Inheritance Tree    (parsed from class hierarchy)
  NOC  - Number of Children           (direct subclass count)

All smells mapped to full SOLID + OO principles.
"""

import os
import re
import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict


# ─── Full SOLID + OO Principle Mapping ───────────────────────────────────────
SMELL_TO_SOLID = {
    "god_class": {
        "principles": [
            "S — Single Responsibility Principle",
            "O — Open/Closed Principle",
            "Encapsulation",
        ],
        "explanation": "A God Class handles too many responsibilities, making it hard to extend without modification and breaking encapsulation boundaries.",
    },
    "long_method": {
        "principles": [
            "S — Single Responsibility Principle",
            "Cohesion",
        ],
        "explanation": "A Long Method performs multiple sub-tasks that should be separate, reducing cohesion and making testing harder.",
    },
    "high_complexity": {
        "principles": [
            "S — Single Responsibility Principle",
            "O — Open/Closed Principle",
        ],
        "explanation": "High CCN indicates tangled conditional logic that should be replaced with polymorphism (OCP) or split into focused methods (SRP).",
    },
    "too_many_parameters": {
        "principles": [
            "S — Single Responsibility Principle",
            "Encapsulation",
            "I — Interface Segregation Principle",
        ],
        "explanation": "Excessive parameters suggest a missing abstraction — parameters should be grouped into an object (Encapsulation) and the interface simplified (ISP).",
    },
    "high_coupling": {
        "principles": [
            "D — Dependency Inversion Principle",
            "O — Open/Closed Principle",
            "Coupling",
        ],
        "explanation": "High CBO indicates direct dependencies on concrete classes rather than abstractions, violating DIP and making extension without modification (OCP) difficult.",
    },
    "high_wmc": {
        "principles": [
            "S — Single Responsibility Principle",
            "Cohesion",
        ],
        "explanation": "High WMC means the class has too many weighted methods, suggesting it handles too many responsibilities (SRP violation).",
    },
    "low_cohesion": {
        "principles": [
            "S — Single Responsibility Principle",
            "Cohesion",
        ],
        "explanation": "High LCOM indicates methods in the class do not share instance variables — the class should be split into more focused classes.",
    },
    "deep_inheritance": {
        "principles": [
            "L — Liskov Substitution Principle",
            "O — Open/Closed Principle",
        ],
        "explanation": "Deep inheritance hierarchies increase the risk of LSP violations and make the hierarchy fragile when extending behaviour.",
    },
    "high_rfc": {
        "principles": [
            "S — Single Responsibility Principle",
            "D — Dependency Inversion Principle",
            "Coupling",
        ],
        "explanation": "High RFC means the class responds to too many message types, indicating excessive coupling and multiple responsibilities.",
    },
    "missing_override": {
        "principles": ["L — Liskov Substitution Principle"],
        "explanation": "Missing override specifier can mask LSP violations where subtype behaviour diverges from the base type contract.",
    },
    "poor_naming": {
        "principles": ["Encapsulation"],
        "explanation": "Poor naming obscures intent and breaks encapsulation by making the internal contract of a class unclear.",
    },
}

# ─── CK Metric Thresholds ────────────────────────────────────────────────────
THRESHOLDS = {
    "wmc":        {"high": 20,   "very_high": 40},
    "cbo":        {"high": 10,   "very_high": 20},
    "rfc":        {"high": 50,   "very_high": 100},
    "lcom":       {"high": 0.7,  "very_high": 0.9},
    "dit":        {"high": 3,    "very_high": 5},
    "noc":        {"high": 10,   "very_high": 20},
    "ccn":        {"high": 10,   "very_high": 20},
    "nloc":       {"high": 30,   "very_high": 60},
    "total_nloc": {"high": 500,  "very_high": 1000},
    "params":     {"high": 5,    "very_high": 8},
}


def parse_metrics(raw_results: dict, output_dir: str, repo_path: str = None) -> dict:
    """Parse all raw tool outputs, compute CK metrics, detect smells, map to SOLID."""
    metrics = {
        "summary": {},
        "files": {},
        "ck_metrics": {},
        "smells": {},
        "principle_violations": {},
    }

    if raw_results.get("lizard", {}).get("status") == "ok":
        _parse_lizard(raw_results["lizard"]["file"], metrics)

    if raw_results.get("cppcheck", {}).get("status") == "ok":
        _parse_cppcheck(raw_results["cppcheck"]["file"], metrics)

    if raw_results.get("clang_tidy", {}).get("status") == "ok":
        _parse_clang_tidy(raw_results["clang_tidy"]["file"], metrics)

    if repo_path:
        _compute_source_metrics(repo_path, metrics)

    _compute_ck_metrics(metrics)
    _detect_smells(metrics)
    _map_to_principles(metrics)

    metrics["summary"]["total_files"]       = len(metrics["files"])
    metrics["summary"]["total_smells"]      = sum(len(v) for v in metrics["smells"].values())
    metrics["summary"]["files_with_smells"] = len(metrics["smells"])
    metrics["summary"]["ck_averages"]       = _compute_averages(metrics)

    metrics_path = os.path.join(output_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"    Metrics saved → {metrics_path}")
    return metrics


# ─── Lizard Parser ────────────────────────────────────────────────────────────

def _parse_lizard(csv_path: str, metrics: dict):
    if not csv_path or not os.path.exists(csv_path):
        return
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            try:
                if len(row) < 8:
                    continue
                nloc, ccn, params = int(float(row[0])), int(float(row[1])), int(float(row[3]))
                filename, func_name = row[6].strip(), row[7].strip()
                short = _shorten_path(filename)
                if short not in metrics["files"]:
                    metrics["files"][short] = {"functions": [], "max_ccn": 0, "total_nloc": 0, "full_path": filename}
                metrics["files"][short]["functions"].append({"name": func_name, "ccn": ccn, "nloc": nloc, "params": params})
                metrics["files"][short]["max_ccn"]    = max(metrics["files"][short]["max_ccn"], ccn)
                metrics["files"][short]["total_nloc"] += nloc
            except (ValueError, KeyError):
                continue


# ─── CppCheck Parser ──────────────────────────────────────────────────────────

def _parse_cppcheck(xml_path: str, metrics: dict):
    if not xml_path or not os.path.exists(xml_path):
        return
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        print("    [WARNING] Could not parse cppcheck XML.")
        return
    for error in root.iter("error"):
        severity, msg, eid = error.get("severity", ""), error.get("msg", ""), error.get("id", "")
        for loc in error.findall("location"):
            short = _shorten_path(loc.get("file", "unknown"))
            if short not in metrics["files"]:
                metrics["files"][short] = {"functions": [], "max_ccn": 0, "total_nloc": 0}
            metrics["files"][short].setdefault("cppcheck_issues", []).append(
                {"id": eid, "severity": severity, "message": msg, "line": loc.get("line", "0")}
            )


# ─── Clang-tidy Parser ───────────────────────────────────────────────────────

def _parse_clang_tidy(txt_path: str, metrics: dict):
    if not txt_path or not os.path.exists(txt_path):
        return
    with open(txt_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if ": warning:" in line or ": error:" in line:
                parts = line.split(":")
                if len(parts) >= 4:
                    short = _shorten_path(parts[0].strip())
                    if short not in metrics["files"]:
                        metrics["files"][short] = {"functions": [], "max_ccn": 0, "total_nloc": 0}
                    metrics["files"][short].setdefault("clang_tidy_warnings", []).append(":".join(parts[3:]).strip())


# ─── Source-level CK Metrics ─────────────────────────────────────────────────

def _compute_source_metrics(repo_path: str, metrics: dict):
    """Compute CBO, DIT, NOC, LCOM by scanning source files."""
    inheritance_map = defaultdict(set)

    for filepath in Path(repo_path).rglob("*"):
        if filepath.suffix not in (".h", ".hpp", ".cpp", ".cc", ".cxx"):
            continue
        short = filepath.name
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if short not in metrics["files"]:
            metrics["files"][short] = {"functions": [], "max_ccn": 0, "total_nloc": 0}

        # CBO: unique local includes
        local_includes = set(re.findall(r'#include\s+"([^"]+)"', content))
        metrics["files"][short]["cbo"]      = len(local_includes)
        metrics["files"][short]["includes"] = list(local_includes)

        # Inheritance
        for m in re.finditer(r'\bclass\s+(\w+)\s*(?:final\s*)?:\s*(?:public|protected|private)\s+(\w+)', content):
            inheritance_map[m.group(2)].add(m.group(1))

        # LCOM approximation
        funcs = metrics["files"][short].get("functions", [])
        if len(funcs) > 1:
            short_funcs = sum(1 for f in funcs if f["nloc"] <= 5)
            metrics["files"][short]["lcom"] = round(short_funcs / len(funcs), 2)
        else:
            metrics["files"][short]["lcom"] = 0.0

    # DIT via BFS
    def get_dit(cls, visited=None):
        visited = visited or set()
        if cls in visited:
            return 0
        visited.add(cls)
        parents = [p for p, ch in inheritance_map.items() if cls in ch]
        return (1 + max(get_dit(p, visited) for p in parents)) if parents else 0

    noc_map = {p: len(ch) for p, ch in inheritance_map.items()}
    all_cls = set(inheritance_map.keys()) | {c for ch in inheritance_map.values() for c in ch}
    dit_map = {cls: get_dit(cls) for cls in all_cls}

    for filepath in Path(repo_path).rglob("*"):
        if filepath.suffix not in (".h", ".hpp", ".cpp", ".cc", ".cxx"):
            continue
        short = filepath.name
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        classes = re.findall(r'\bclass\s+(\w+)', content)
        if classes and short in metrics["files"]:
            metrics["files"][short]["dit"] = max((dit_map.get(c, 0) for c in classes), default=0)
            metrics["files"][short]["noc"] = max((noc_map.get(c, 0) for c in classes), default=0)
            metrics["files"][short]["classes"] = classes


# ─── Compute CK Metrics per File ─────────────────────────────────────────────

def _compute_ck_metrics(metrics: dict):
    for filename, data in metrics["files"].items():
        funcs = data.get("functions", [])
        wmc   = sum(f["ccn"] for f in funcs)
        rfc   = wmc + len(data.get("cppcheck_issues", []))
        metrics["ck_metrics"][filename] = {
            "WMC":        wmc,
            "RFC":        rfc,
            "CBO":        data.get("cbo", 0),
            "LCOM":       data.get("lcom", 0.0),
            "DIT":        data.get("dit", 0),
            "NOC":        data.get("noc", 0),
            "CCN_max":    data.get("max_ccn", 0),
            "NLOC_total": data.get("total_nloc", 0),
            "functions":  len(funcs),
        }


# ─── Smell Detection ──────────────────────────────────────────────────────────

def _detect_smells(metrics: dict):
    for filename, data in metrics["files"].items():
        ck, file_smells = metrics["ck_metrics"].get(filename, {}), []

        def check(val, key, smell_type, label):
            t = THRESHOLDS.get(key, {})
            if val > t.get("very_high", float("inf")):
                file_smells.append(_smell(smell_type, f"{label}={val} (very high >{t['very_high']})", "high"))
            elif val > t.get("high", float("inf")):
                file_smells.append(_smell(smell_type, f"{label}={val} (high >{t['high']})", "medium"))

        check(data.get("total_nloc", 0), "total_nloc", "god_class",    "NLOC")
        check(ck.get("WMC", 0),          "wmc",        "high_wmc",     "WMC")
        check(ck.get("CBO", 0),          "cbo",        "high_coupling", "CBO")
        check(ck.get("RFC", 0),          "rfc",        "high_rfc",     "RFC")
        check(ck.get("DIT", 0),          "dit",        "deep_inheritance", "DIT")

        lcom = ck.get("LCOM", 0.0)
        t = THRESHOLDS["lcom"]
        if lcom > t["very_high"]:
            file_smells.append(_smell("low_cohesion", f"LCOM={lcom:.2f} (very high >{t['very_high']})", "high"))
        elif lcom > t["high"]:
            file_smells.append(_smell("low_cohesion", f"LCOM={lcom:.2f} (high >{t['high']})", "medium"))

        for func in data.get("functions", []):
            check(func["nloc"],   "nloc",   "long_method",        f"Function '{func['name']}' NLOC")
            check(func["ccn"],    "ccn",    "high_complexity",    f"Function '{func['name']}' CCN")
            check(func["params"], "params", "too_many_parameters", f"Function '{func['name']}' params")

        if file_smells:
            metrics["smells"][filename] = file_smells


def _smell(t, d, s):
    return {"type": t, "detail": d, "severity": s}


# ─── SOLID Principle Mapping ──────────────────────────────────────────────────

def _map_to_principles(metrics: dict):
    violations = defaultdict(list)
    for filename, smells in metrics["smells"].items():
        for smell in smells:
            mapping = SMELL_TO_SOLID.get(smell["type"], {})
            for principle in mapping.get("principles", ["Unknown"]):
                violations[principle].append({
                    "file":        filename,
                    "smell":       smell["type"],
                    "detail":      smell["detail"],
                    "explanation": mapping.get("explanation", ""),
                    "severity":    smell["severity"],
                })
    metrics["principle_violations"] = dict(violations)


# ─── CK Averages ─────────────────────────────────────────────────────────────

def _compute_averages(metrics: dict) -> dict:
    ck_all = list(metrics["ck_metrics"].values())
    if not ck_all:
        return {}
    def avg(key):
        vals = [v.get(key, 0) for v in ck_all if v.get(key, 0) > 0]
        return round(sum(vals) / len(vals), 2) if vals else 0
    return {
        "avg_WMC": avg("WMC"), "avg_CBO": avg("CBO"),
        "avg_RFC": avg("RFC"), "avg_LCOM": avg("LCOM"),
        "avg_DIT": avg("DIT"), "avg_NOC": avg("NOC"),
        "avg_CCN_max": avg("CCN_max"), "avg_NLOC": avg("NLOC_total"),
    }


def _shorten_path(path: str) -> str:
    return Path(path).name if path else "unknown"
