"""
modules/ai_agent.py
Sends worst-offending files/metrics to AI models and gets refactoring suggestions.

Provider fallback chain (automatic):
  1. Groq (llama3-70b-8192)   — primary, free, fast
  2. Gemini Flash              — fallback if Groq token expired/rate-limited
  3. Skip with warning         — if both fail

Pass --ai-provider groq|gemini|auto (default: auto)
Pass --groq-key and/or --gemini-key
"""

import json
import time
import urllib.request
import urllib.error

GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama3-70b-8192"

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

MAX_FILES_TO_REVIEW = 5

# Errors that mean the token/quota is exhausted — trigger fallback
QUOTA_ERRORS = {429, 401, 403}


def get_refactoring_suggestions(
    metrics: dict,
    groq_key: str = None,
    gemini_key: str = None,
    provider: str = "auto",       # "auto" | "groq" | "gemini"
) -> dict:
    """
    Pick worst-offending files and get AI refactoring suggestions.
    Automatically falls back from Groq → Gemini on token expiry.
    Returns dict: { filename: suggestion_text }
    """
    worst_files = _pick_worst_files(metrics)
    if not worst_files:
        print("    No significant smells found — skipping AI suggestions.")
        return {}

    # Resolve provider order
    if provider == "groq":
        providers = [("groq", groq_key)]
    elif provider == "gemini":
        providers = [("gemini", gemini_key)]
    else:  # auto
        providers = []
        if groq_key:
            providers.append(("groq", groq_key))
        if gemini_key:
            providers.append(("gemini", gemini_key))

    if not providers:
        print("    [WARNING] No AI API key provided. Skipping AI suggestions.")
        print("              Set GROQ_API_KEY or GEMINI_API_KEY environment variable.")
        return {}

    suggestions = {}
    for filename, smells in worst_files.items():
        print(f"    Analyzing: {filename}")
        result = _query_with_fallback(filename, smells, metrics, providers)
        if result:
            suggestions[filename] = result

    return suggestions


# ─── Fallback Chain ───────────────────────────────────────────────────────────

def _query_with_fallback(filename, smells, metrics, providers):
    """Try each provider in order; fall back on quota/auth errors."""
    for name, key in providers:
        if not key:
            continue
        print(f"      → Trying {name}...")
        result, should_fallback = _query_provider(name, key, filename, smells, metrics)
        if result:
            return result
        if should_fallback:
            print(f"      → {name} quota/token expired. Trying next provider...")
            continue
        else:
            # Non-quota error — don't retry
            break
    print(f"      [WARNING] All AI providers failed for {filename}. Skipping.")
    return None


def _query_provider(name, key, filename, smells, metrics):
    """
    Returns (result_text, should_fallback).
    should_fallback=True means quota/auth issue → try next provider.
    """
    prompt = _build_prompt(filename, smells, metrics)
    try:
        if name == "groq":
            return _query_groq(prompt, key), False
        elif name == "gemini":
            return _query_gemini(prompt, key), False
    except _QuotaError as e:
        print(f"      [QUOTA] {name}: {e}")
        return None, True
    except Exception as e:
        print(f"      [ERROR] {name}: {e}")
        return None, False
    return None, False


class _QuotaError(Exception):
    pass


# ─── Prompt Builder ───────────────────────────────────────────────────────────

def _build_prompt(filename, smells, metrics):
    smell_descriptions = "\n".join(
        f"  - [{s['severity'].upper()}] {s['type']}: {s['detail']}" for s in smells
    )
    file_data  = metrics.get("files", {}).get(filename, {})
    ck         = metrics.get("ck_metrics", {}).get(filename, {})
    func_count = len(file_data.get("functions", []))

    ck_summary = "\n".join(
        f"  - {k}: {v}" for k, v in ck.items() if k != "functions"
    )

    return f"""You are an expert C++ software engineer specializing in Object-Oriented design, refactoring, and code quality analysis.

Analyze the following code smell report for a C++ file and provide a comprehensive refactoring plan.

FILE: {filename}

CK METRICS:
{ck_summary}
  - Number of functions: {func_count}

DETECTED SMELLS (mapped to SOLID principles):
{smell_descriptions}

Provide a detailed analysis in the following structure:

### 1. Problem Summary
Briefly summarize the main design issues.

### 2. Violated SOLID Principles
List which SOLID principles (S/O/L/I/D) are violated and why.

### 3. Root Cause Analysis
Explain why these issues exist.

### 4. Refactoring Strategy
High-level approach (e.g., Extract Class, Strategy Pattern, DIP via interfaces).

### 5. Step-by-Step Refactoring Plan
Detailed actionable steps with C++ code snippets where helpful.

### 6. Expected Metric Improvements
State expected improvements in WMC, CBO, CCN, LCOM after refactoring.

### 7. Potential Risks
Mention risks in implementing these changes.

Format response strictly as Markdown."""


# ─── Groq ────────────────────────────────────────────────────────────────────

def _query_groq(prompt: str, api_key: str) -> str:
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a C++ OO design expert. Give precise, actionable refactoring advice mapped to SOLID principles."},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": 2048,
        "temperature": 0.3,
    }
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        GROQ_API_URL, data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        if e.code in QUOTA_ERRORS:
            raise _QuotaError(f"HTTP {e.code}: {body[:120]}")
        raise Exception(f"Groq HTTP {e.code}: {body[:120]}")


# ─── Gemini ──────────────────────────────────────────────────────────────────

def _query_gemini(prompt: str, api_key: str) -> str:
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    data    = json.dumps(payload).encode("utf-8")
    url     = f"{GEMINI_API_URL}?key={api_key}"
    req     = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        if e.code in QUOTA_ERRORS:
            raise _QuotaError(f"HTTP {e.code}: {body[:120]}")
        raise Exception(f"Gemini HTTP {e.code}: {body[:120]}")


# ─── File Selection ───────────────────────────────────────────────────────────

def _pick_worst_files(metrics: dict) -> dict:
    smell_counts = {f: len(s) for f, s in metrics.get("smells", {}).items()}
    sorted_files = sorted(smell_counts.items(), key=lambda x: x[1], reverse=True)
    return {f: metrics["smells"][f] for f, _ in sorted_files[:MAX_FILES_TO_REVIEW]}
