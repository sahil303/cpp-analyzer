#!/usr/bin/env python3
"""
cpp_analyzer - Automated C++ OO Analysis & Refactoring Suggestion Tool

Usage:
  python analyze.py --repo <path_or_url> --output ./output
  python analyze.py --repo <path> --groq-key <key>
  python analyze.py --repo <path> --gemini-key <key>
  python analyze.py --repo <path> --groq-key <key> --gemini-key <key> --ai-provider auto

AI Provider:
  auto   → tries Groq first, falls back to Gemini on token expiry (default)
  groq   → Groq only  (set GROQ_API_KEY or --groq-key)
  gemini → Gemini only (set GEMINI_API_KEY or --gemini-key)
"""

import argparse
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
    parser.add_argument("--repo",     required=True, help="Local path or GitHub URL")
    parser.add_argument("--output",   default="./output", help="Output directory (default: ./output)")
    parser.add_argument("--name",     default=None,  help="Project name override")

    # AI provider flags
    parser.add_argument("--ai-provider", default="auto", choices=["auto", "groq", "gemini"],
                        help="AI provider: auto (default), groq, or gemini")
    parser.add_argument("--groq-key",   default=None, help="Groq API key (or set GROQ_API_KEY)")
    parser.add_argument("--gemini-key", default=None, help="Gemini API key (or set GEMINI_API_KEY)")

    args = parser.parse_args()

    # Resolve keys from args or environment
    groq_key   = args.groq_key   or os.environ.get("GROQ_API_KEY")
    gemini_key = args.gemini_key or os.environ.get("GEMINI_API_KEY")

    if not groq_key and not gemini_key:
        print("[WARNING] No AI API key provided. AI suggestions will be skipped.")
        print("          Set GROQ_API_KEY or GEMINI_API_KEY environment variable.\n")

    print("=" * 60)
    print("  C++ OO Analyzer — Dissertation Analysis Tool")
    print("=" * 60)

    # Step 1: Setup
    print("\n[1/5] Setting up repository...")
    repo_path, project_name = setup_repo(args.repo, args.output)
    if args.name:
        project_name = args.name
    print(f"      Project : {project_name}")
    print(f"      Path    : {repo_path}")

    # Step 2: Run tools
    print("\n[2/5] Running analysis tools (cppcheck, lizard, clang-tidy)...")
    raw_results = run_analysis(repo_path, args.output)
    print(f"      Done. Raw results saved to {args.output}/raw/")

    # Step 3: Parse metrics + compute full CK suite
    print("\n[3/5] Computing CK metrics and detecting smells...")
    metrics = parse_metrics(raw_results, args.output, repo_path=repo_path)
    summary = metrics.get("summary", {})
    avgs    = summary.get("ck_averages", {})
    print(f"      Files analyzed  : {summary.get('total_files', 0)}")
    print(f"      Smells detected : {summary.get('total_smells', 0)}")
    print(f"      Avg WMC={avgs.get('avg_WMC',0)}  CBO={avgs.get('avg_CBO',0)}  "
          f"RFC={avgs.get('avg_RFC',0)}  LCOM={avgs.get('avg_LCOM',0)}")

    # Step 4: AI suggestions with fallback
    suggestions = {}
    if groq_key or gemini_key:
        print(f"\n[4/5] Getting AI refactoring suggestions (provider: {args.ai_provider})...")
        suggestions = get_refactoring_suggestions(
            metrics,
            groq_key=groq_key,
            gemini_key=gemini_key,
            provider=args.ai_provider,
        )
        print(f"      Suggestions generated for {len(suggestions)} files.")
    else:
        print("\n[4/5] Skipping AI suggestions (no API key).")

    # Step 5: Generate PDF
    print("\n[5/5] Generating PDF report...")
    report_path = generate_report(project_name, metrics, suggestions, args.output)
    print(f"      Report saved: {report_path}")

    print("\n" + "=" * 60)
    print("  Analysis Complete!")
    print(f"  Report : {report_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
