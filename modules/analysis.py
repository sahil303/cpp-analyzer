"""
modules/analysis.py
Runs cppcheck, lizard, and clang-tidy on the repo.
Saves raw outputs to output/raw/.
"""

import os
import subprocess
import shutil
import json
from pathlib import Path


def run_analysis(repo_path: str, output_dir: str) -> dict:
    """
    Run all available analysis tools on the repo.
    Returns a dict of raw results paths.
    """
    raw_dir = os.path.join(output_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    results = {}

    results["cppcheck"] = _run_cppcheck(repo_path, raw_dir)
    results["lizard"]   = _run_lizard(repo_path, raw_dir)
    results["clang_tidy"] = _run_clang_tidy(repo_path, raw_dir)

    # Save index of what ran
    index_path = os.path.join(raw_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump(results, f, indent=2)

    return results


# ─── cppcheck ────────────────────────────────────────────────────────────────

def _run_cppcheck(repo_path: str, raw_dir: str) -> dict:
    output_file = os.path.join(raw_dir, "cppcheck.xml")

    if not shutil.which("cppcheck"):
        print("    [SKIP] cppcheck not installed.")
        return {"status": "skipped", "file": None}

    print("    Running cppcheck...")
    result = subprocess.run(
        [
            "cppcheck",
            "--enable=all",
            "--inconclusive",
            "--xml",
            "--xml-version=2",
            "--suppress=missingIncludeSystem",
            repo_path,
        ],
        capture_output=True,
        text=True,
    )

    # cppcheck writes XML to stderr
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result.stderr)

    print(f"    cppcheck done → {output_file}")
    return {"status": "ok", "file": output_file}


# ─── lizard ──────────────────────────────────────────────────────────────────

def _run_lizard(repo_path: str, raw_dir: str) -> dict:
    output_file = os.path.join(raw_dir, "lizard.csv")

    if not shutil.which("lizard"):
        print("    [SKIP] lizard not installed.")
        return {"status": "skipped", "file": None}

    print("    Running lizard...")
    result = subprocess.run(
        [
            "lizard",
            repo_path,
            "--languages", "cpp",
            "--csv",
            "--output_file", output_file,
            "--length", "30",        # flag functions > 30 lines
            "--CCN", "10",           # flag cyclomatic complexity > 10
            "--arguments", "5",      # flag functions with > 5 args
        ],
        capture_output=True,
        text=True,
    )

    print(f"    lizard done → {output_file}")
    return {"status": "ok", "file": output_file}


# ─── clang-tidy ──────────────────────────────────────────────────────────────

def _run_clang_tidy(repo_path: str, raw_dir: str) -> dict:
    output_file = os.path.join(raw_dir, "clang_tidy.txt")

    if not shutil.which("clang-tidy"):
        print("    [SKIP] clang-tidy not installed.")
        return {"status": "skipped", "file": None}

    # Find all cpp files
    cpp_files = list(Path(repo_path).rglob("*.cpp"))
    if not cpp_files:
        print("    [SKIP] No .cpp files found for clang-tidy.")
        return {"status": "skipped", "file": None}

    print(f"    Running clang-tidy on {len(cpp_files)} files...")

    all_output = []
    # Run on first 50 files max to keep it manageable
    for cpp_file in cpp_files[:50]:
        result = subprocess.run(
            [
                "clang-tidy",
                str(cpp_file),
                "--checks=readability-*,cppcoreguidelines-*,modernize-*",
                "--",
                "-std=c++17",
            ],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            all_output.append(result.stdout)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(all_output))

    print(f"    clang-tidy done → {output_file}")
    return {"status": "ok", "file": output_file}
