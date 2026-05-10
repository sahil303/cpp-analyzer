"""
modules/setup.py
Handles repo cloning (if URL given) and tool installation checks.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


REQUIRED_TOOLS = {
    "cppcheck": "cppcheck",
    "lizard":   "lizard",
    "clang-tidy": "clang-tidy",
}


def setup_repo(repo_input: str, output_dir: str) -> tuple[str, str]:
    """
    Clone repo if URL is given, or validate local path.
    Returns (repo_path, project_name).
    """
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "raw"), exist_ok=True)

    _check_and_install_tools()

    if repo_input.startswith("http://") or repo_input.startswith("https://"):
        return _clone_repo(repo_input, output_dir)
    else:
        return _validate_local_repo(repo_input)


# ─── Tool Installation ────────────────────────────────────────────────────────

def _check_and_install_tools():
    """Check each required tool; install if missing (Windows-friendly)."""
    print("\n  Checking required tools...")

    # lizard via pip (cross-platform)
    if not shutil.which("lizard"):
        print("    [+] Installing lizard via pip...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "lizard", "-q"],
            check=True
        )

    # cppcheck
    if not shutil.which("cppcheck"):
        _install_cppcheck()

    # clang-tidy
    if not shutil.which("clang-tidy"):
        _install_clang_tidy()

    print("  All tools ready.\n")


def _install_cppcheck():
    """Guide user to install cppcheck on Windows."""
    print("\n  [!] cppcheck not found.")
    print("      Windows: Download installer from https://cppcheck.sourceforge.io/")
    print("      Or via winget: winget install Cppcheck.Cppcheck")
    print("      After installing, restart this script.\n")
    # Non-fatal: we continue, analysis module handles missing tools gracefully


def _install_clang_tidy():
    """Guide user to install clang-tidy on Windows."""
    print("\n  [!] clang-tidy not found.")
    print("      Windows: Install LLVM from https://releases.llvm.org/")
    print("      Or via winget: winget install LLVM.LLVM")
    print("      After installing, restart this script.\n")
    # Non-fatal: we continue, analysis module handles missing tools gracefully


# ─── Repo Handling ────────────────────────────────────────────────────────────

def _clone_repo(url: str, output_dir: str) -> tuple[str, str]:
    """Clone a GitHub repo into output_dir/repos/."""
    project_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    repos_dir = os.path.join(output_dir, "repos")
    os.makedirs(repos_dir, exist_ok=True)
    repo_path = os.path.join(repos_dir, project_name)

    if os.path.exists(repo_path):
        print(f"  Repo already cloned at {repo_path}. Using existing.")
    else:
        print(f"  Cloning {url}...")
        result = subprocess.run(
            ["git", "clone", "--depth=1", url, repo_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  [ERROR] Clone failed:\n{result.stderr}")
            sys.exit(1)
        print(f"  Cloned into {repo_path}")

    return repo_path, project_name


def _validate_local_repo(path: str) -> tuple[str, str]:
    """Validate that a local path exists and contains C++ files."""
    abs_path = os.path.abspath(path)

    if not os.path.exists(abs_path):
        print(f"  [ERROR] Path does not exist: {abs_path}")
        sys.exit(1)

    cpp_files = list(Path(abs_path).rglob("*.cpp")) + list(Path(abs_path).rglob("*.h"))
    if not cpp_files:
        print(f"  [WARNING] No .cpp or .h files found in {abs_path}")

    project_name = os.path.basename(abs_path)
    return abs_path, project_name
