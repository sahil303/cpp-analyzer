"""
modules/ai_agent.py
Sends worst-offending files/metrics to AI models (Groq or Gemini)
and gets back structured refactoring suggestions.
"""


import json
import urllib.request
import urllib.error


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama3-70b-8192"   # Free, fast, great for code

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

# How many worst files to send for AI review
MAX_FILES_TO_REVIEW = 5


def get_refactoring_suggestions(metrics: dict, model: str, api_key: str) -> dict:
    """
    Pick the worst offending files and get AI refactoring suggestions.
    Returns dict: { filename: suggestion_text }
    """
    worst_files = _pick_worst_files(metrics)

    if not worst_files:
        print("    No significant smells found — skipping AI suggestions.")
        return {}

    suggestions = {}
    for filename, smells in worst_files.items():
        print(f"    Analyzing: {filename}")
        if model == "groq":
            suggestion = _query_groq(filename, smells, metrics, api_key)
        elif model == "gemini":
            suggestion = _query_gemini(filename, smells, metrics, api_key)
        else:
            print(f"    Unsupported model: {model}")
            suggestion = None
        if suggestion:
            suggestions[filename] = suggestion

    return suggestions


# ─── File Selection ───────────────────────────────────────────────────────────

def _pick_worst_files(metrics: dict) -> dict:
    """Pick files with the most/worst smells for AI review."""
    smell_counts = {
        filename: len(smells)
        for filename, smells in metrics.get("smells", {}).items()
    }

    # Sort by smell count descending, take top N
    sorted_files = sorted(smell_counts.items(), key=lambda x: x[1], reverse=True)
    top_files = dict(sorted_files[:MAX_FILES_TO_REVIEW])

    result = {}
    for filename in top_files:
        result[filename] = metrics["smells"][filename]

    return result


# ─── Groq API Call ────────────────────────────────────────────────────────────

def _query_groq(filename: str, smells: list, metrics: dict, api_key: str) -> str:
    """Send file smells to Groq and return refactoring suggestion."""

    # Build the prompt
    smell_descriptions = "\n".join(
        f"  - [{s['severity'].upper()}] {s['type']}: {s['detail']}"
        for s in smells
    )

    # Get file metrics if available
    file_data = metrics.get("files", {}).get(filename, {})
    func_count = len(file_data.get("functions", []))
    total_lines = file_data.get("total_nloc", "unknown")
    max_ccn = file_data.get("max_ccn", "unknown")

    prompt = f"""You are an expert C++ software engineer specializing in Object-Oriented design, refactoring, and code quality analysis.

Analyze the following code smell report for a C++ file and provide a comprehensive refactoring plan.

FILE: {filename}
METRICS:
  - Total lines of code: {total_lines}
  - Number of functions: {func_count}
  - Max cyclomatic complexity: {max_ccn}

DETECTED SMELLS:
{smell_descriptions}

Provide a detailed analysis and refactoring plan in the following structure:

### 1. Problem Summary
Briefly summarize the main issues identified from the smells and metrics.

### 2. Violated OO Principles
List the SOLID principles and other OO design principles that are violated, with specific explanations.

### 3. Root Cause Analysis
Explain why these issues exist (e.g., feature creep, tight coupling, lack of abstraction).

### 4. Refactoring Strategy
Outline the high-level approach to fix the issues (e.g., Extract Class, Introduce Strategy Pattern).

### 5. Step-by-Step Refactoring Plan
Provide detailed, actionable steps with:
- Specific C++ code changes
- New class/method signatures
- Dependency injections or interfaces to introduce
- Code snippets where helpful

### 6. Expected Benefits
Describe the improvements in:
- Code metrics (e.g., reduced complexity, smaller classes)
- Maintainability, testability, and extensibility
- Performance implications if any

### 7. Potential Risks
Mention any risks or challenges in implementing these changes.

Format your response strictly as Markdown. Use blank lines between sections and paragraphs. Use ### for section headings, - for bullet points, **bold** for emphasis, `code` for code references, and ``` for code blocks. Do not merge section headings with paragraph text. Each numbered heading must start on its own line with a blank line before it. Be specific, practical, and provide concrete C++ examples where relevant."""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a C++ software engineering expert. Give precise, actionable refactoring advice."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 2048,
        "temperature": 0.3,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            GROQ_API_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"    [ERROR] Groq API error {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"    [ERROR] AI request failed: {e}")
        return None


# ─── Gemini API Call ──────────────────────────────────────────────────────────

def _query_gemini(filename: str, smells: list, metrics: dict, api_key: str) -> str:
    """Send file smells to Gemini and return refactoring suggestion."""

    # Build the prompt (same as Groq)
    smell_descriptions = "\n".join(
        f"  - [{s['severity'].upper()}] {s['type']}: {s['detail']}"
        for s in smells
    )

    # Get file metrics if available
    file_data = metrics.get("files", {}).get(filename, {})
    func_count = len(file_data.get("functions", []))
    total_lines = file_data.get("total_nloc", "unknown")
    max_ccn = file_data.get("max_ccn", "unknown")

    prompt = f"""You are an expert C++ software engineer specializing in Object-Oriented design, refactoring, and code quality analysis.

Analyze the following code smell report for a C++ file and provide a comprehensive refactoring plan.

FILE: {filename}
METRICS:
  - Total lines of code: {total_lines}
  - Number of functions: {func_count}
  - Max cyclomatic complexity: {max_ccn}

DETECTED SMELLS:
{smell_descriptions}

Provide a detailed analysis and refactoring plan in the following structure:

### 1. Problem Summary
Briefly summarize the main issues identified from the smells and metrics.

### 2. Violated OO Principles
List the SOLID principles and other OO design principles that are violated, with specific explanations.

### 3. Root Cause Analysis
Explain why these issues exist (e.g., feature creep, tight coupling, lack of abstraction).

### 4. Refactoring Strategy
Outline the high-level approach to fix the issues (e.g., Extract Class, Introduce Strategy Pattern).

### 5. Step-by-Step Refactoring Plan
Provide detailed, actionable steps with:
- Specific C++ code changes
- New class/method signatures
- Dependency injections or interfaces to introduce
- Code snippets where helpful

### 6. Expected Benefits
Describe the improvements in:
- Code metrics (e.g., reduced complexity, smaller classes)
- Maintainability, testability, and extensibility
- Performance implications if any

### 7. Potential Risks
Mention any risks or challenges in implementing these changes.

Format your response strictly as Markdown. Use blank lines between sections and paragraphs. Use ### for section headings, - for bullet points, **bold** for emphasis, `code` for code references, and ``` for code blocks. Do not merge section headings with paragraph text. Each numbered heading must start on its own line with a blank line before it. Be specific, practical, and provide concrete C++ examples where relevant."""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    try:
        url = f"{GEMINI_API_URL}?key={api_key}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"    [ERROR] Gemini API error {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"    [ERROR] AI request failed: {e}")
        return None

