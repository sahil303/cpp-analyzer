# cpp_analyzer — C++ OO Analysis Tool

Automated C++ code smell detection, OO principle violation mapping,
and AI-powered comprehensive reports with refactoring suggestions. Outputs a PDF report.

## Quick Start

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Install external tools (Windows)

**cppcheck:**
```
winget install Cppcheck.Cppcheck
```

**clang-tidy** (via LLVM):
```
winget install LLVM.LLVM
```

### 3. Get an AI API key (optional)
- **Groq** (default): Sign up at https://console.groq.com (free, no credit card needed)
- **Gemini**: Get API key from https://makersuite.google.com/app/apikey

### 4. Run the analyzer

**On a local repo:**
```bash
python analyze.py --repo C:\path\to\your\cpp\project --output ./output
```

**On a GitHub repo (auto-clones):**
```bash
python analyze.py --repo https://github.com/owner/repo --output ./output
```

**With AI-powered comprehensive analysis (Groq):**
```bash
set AI_API_KEY=your_groq_key_here
python analyze.py --repo C:\path\to\project --output ./output
```

**With AI-powered comprehensive analysis (Gemini):**
```bash
set AI_API_KEY=your_gemini_key_here
python analyze.py --repo C:\path\to\project --ai-model gemini --output ./output
```

Or pass it inline:
```bash
python analyze.py --repo C:\path\to\project --ai-key YOUR_KEY --ai-model groq --output ./output
```

## Output
```
output/
├── raw/
│   ├── cppcheck.xml
│   ├── lizard.csv
│   └── clang_tidy.txt
├── metrics.json
└── <project_name>_analysis_report.pdf   ← Final report
```

## What It Detects

| Smell | OO Principle Violated |
|---|---|
| God Class (>500 LOC) | SRP, Encapsulation |
| Long Method (>30 lines) | SRP |
| High Complexity (CCN>10) | SRP, OCP |
| Too Many Parameters (>5) | Encapsulation, SRP |

## Project Structure
```
cpp_analyzer/
├── analyze.py          ← CLI entry point
├── requirements.txt
└── modules/
    ├── setup.py        ← Repo cloning & tool checks
    ├── analysis.py     ← Runs cppcheck, lizard, clang-tidy
    ├── metrics.py      ← Parses outputs, detects smells
    ├── ai_agent.py     ← AI-powered analysis and refactoring suggestions (Groq/Gemini)
    └── report.py       ← PDF report generation
```
