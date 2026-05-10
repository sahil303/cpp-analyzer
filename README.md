# cpp_analyzer — C++ OO Analysis Tool

Automated C++ code smell detection, OO principle violation mapping,
and AI-powered refactoring suggestions. Outputs a PDF report.

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

### 3. Get a free Groq API key
Sign up at https://console.groq.com (free, no credit card needed)

### 4. Run the analyzer

**On a local repo:**
```bash
python analyze.py --repo C:\path\to\your\cpp\project --output ./output
```

**On a GitHub repo (auto-clones):**
```bash
python analyze.py --repo https://github.com/owner/repo --output ./output
```

**With AI suggestions:**
```bash
set GROQ_API_KEY=your_key_here
python analyze.py --repo C:\path\to\project --output ./output
```

Or pass it inline:
```bash
python analyze.py --repo C:\path\to\project --groq-key YOUR_KEY --output ./output
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
    ├── ai_agent.py     ← Groq AI refactoring suggestions
    └── report.py       ← PDF report generation
```
