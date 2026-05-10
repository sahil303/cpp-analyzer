#!/usr/bin/env python3
"""
cpp_analyzer - Automated C++ OO Analysis & Refactoring Suggestion Tool
Usage: python analyze.py --repo <path_or_url> --output ./output
"""

import argparse
import sys
import os
from modules.setup import setup_repo
from modules.analysis import run_analysis
from modules.metrics import parse_metrics
from modules.ai_agent import get_refactoring_suggestions
from modules.report import generate_report


def main():
    parser = argparse.ArgumentParser(
        description="Automated C++ OO code smell detector and refactoring advisor"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Path to local C++ repo OR a GitHub URL to clone"
    )
    parser.add_argument(
        "--output",
        default="./output",
        help="Directory to save results (default: ./output)"
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Project name (used in report). Auto-detected if not given."
    )
    parser.add_argument(
        "--groq-key",
        default=None,
        help="Groq API key. Can also be set via GROQ_API_KEY env variable."
    )

    args = parser.parse_args()

    # Resolve Groq API key
    groq_key = args.groq_key or os.environ.get("GROQ_API_KEY")
    if not groq_key:
        print("[WARNING] No Groq API key provided. AI suggestions will be skipped.")
        print("          Set via --groq-key or GROQ_API_KEY environment variable.\n")

    print("=" * 60)
    print("  C++ OO Analyzer — Dissertation Analysis Tool")
    print("=" * 60)

    # Step 1: Setup — clone or validate repo
    print("\n[1/5] Setting up repository...")
    repo_path, project_name = setup_repo(args.repo, args.output)
    if args.name:
        project_name = args.name
    print(f"      Project: {project_name}")
    print(f"      Path:    {repo_path}")

    # Step 2: Run analysis tools
    print("\n[2/5] Running analysis tools (cppcheck, lizard, clang-tidy)...")
    raw_results = run_analysis(repo_path, args.output)
    print(f"      Done. Raw results saved to {args.output}/raw/")

    # Step 3: Parse & unify metrics
    print("\n[3/5] Parsing metrics and detecting smells...")
    metrics = parse_metrics(raw_results, args.output)
    smell_count = sum(len(v) for v in metrics.get("smells", {}).values())
    print(f"      Files analyzed: {metrics.get('summary', {}).get('total_files', 0)}")
    print(f"      Smells detected: {smell_count}")

    # Step 4: AI refactoring suggestions
    suggestions = {}
    if groq_key:
        print("\n[4/5] Getting AI refactoring suggestions via Groq...")
        suggestions = get_refactoring_suggestions(metrics, groq_key)
        print(f"      Suggestions generated for {len(suggestions)} files.")
    else:
        print("\n[4/5] Skipping AI suggestions (no API key).")

    # Step 5: Generate PDF report
    print("\n[5/5] Generating PDF report...")
    report_path = generate_report(project_name, metrics, suggestions, args.output)
    print(f"      Report saved: {report_path}")

    print("\n" + "=" * 60)
    print("  Analysis Complete!")
    print(f"  Report: {report_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
