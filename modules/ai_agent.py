"""
modules/ai_agent.py
Sends worst-offending files/metrics to Groq (free API)
and gets back structured refactoring suggestions.
"""

import json
import urllib.request
import urllib.error


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama3-70b-8192"   # Free, fast, great for code

# How many worst files to send for AI review
MAX_FILES_TO_REVIEW = 5


def get_refactoring_suggestions(metrics: dict, api_key: str) -> dict:
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
        suggestion = _query_groq(filename, smells, metrics, api_key)
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

    prompt = f"""You are an expert C++ software engineer specializing in Object-Oriented design and refactoring.

Analyze the following code smell report for a C++ file and provide concrete refactoring suggestions.

FILE: {filename}
METRICS:
  - Total lines of code: {total_lines}
  - Number of functions: {func_count}
  - Max cyclomatic complexity: {max_ccn}

DETECTED SMELLS:
{smell_descriptions}

Provide:
1. A brief diagnosis of the main OO design problem
2. Which OO principles are violated (SOLID, Encapsulation, Cohesion, Coupling)
3. Step-by-step refactoring recommendations with specific C++ techniques
4. Expected improvement in metrics after refactoring

Be specific and practical. Format your response clearly with numbered sections."""

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
        "max_tokens": 1024,
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
