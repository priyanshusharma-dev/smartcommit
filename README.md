# SmartCommit 🤖

**AI-Powered Git Commit Message Generator**

A fast, privacy-first CLI tool that automatically analyzes your staged Git changes and generates high-quality **Conventional Commit** messages using local LLMs (Ollama) with an intelligent rule-based fallback.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![CLI](https://img.shields.io/badge/CLI-Typer-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Ollama](https://img.shields.io/badge/LLM-Ollama-orange)
![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen)

---

## 📖 Overview

Writing meaningful, standardized commit messages is time-consuming. **SmartCommit** solves this by analyzing your code diffs and producing clear, consistent Conventional Commits with zero cloud dependencies.

**Everything runs locally** — your proprietary code never leaves your workstation.

---

## ✨ Key Features

- ⚡ **Local AI Inference**: Powered by local Ollama models (`llama3.2:3b`, `qwen2.5-coder:7b`, etc.) with direct low-latency inference.
- 📏 **Strict Conventional Commits 1.0.0**: Precise type (`feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`), scope extraction, imperative mood, and breaking change (`!`) syntax.
- 📝 **Single-Line & Detailed Modes**: Generate crisp one-line subjects or full multi-line commit messages with motivation paragraphs and change bullet points (`-d` / `--detailed`).
- 💡 **Developer Hints**: Steer generation with your intent using `-H` / `--hint` (e.g. `smartcommit -H "fixes auth token refresh race condition"`).
- 🎯 **Multiple Candidate Options**: Generate up to 5 alternative commit messages (`-n 3`) and pick the best one interactively.
- 🧹 **Noise & Lockfile Filtering**: Automatically prevents huge lockfiles (`package-lock.json`, `poetry.lock`, etc.) from blowing prompt context, keeping diffs focused on semantic code changes.
- 🤝 **Interactive Workflow**: Commit directly (`[c]`), edit message inline (`[e]`), regenerate with a hint (`[r]`), copy to clipboard (`[y]`), or quit (`[q]`).
- 🧠 **Semantic Rule-Based Fallback**: Seamlessly generates smart, context-aware commit messages even if Ollama is offline or times out.
- ✨ **Gitmoji Support**: Optional gitmoji prefixes tailored to commit types (`--emoji`).
- 📋 **Cross-Platform Clipboard**: Instant clipboard copying with `--copy` on Windows, macOS, and Linux.

---

## 🚀 Quick Start

### 1. Stage your changes
```bash
git add .
```

### 2. Run SmartCommit
```bash
smartcommit
```

### Example Outputs

**Single-Line (Default):**
```text
feat(auth): add JWT authentication middleware
```

**Detailed Mode (`smartcommit -d`):**
```text
feat(auth): add JWT bearer token authentication middleware

Implement token decoding and claims verification for incoming API requests.
Includes automatic token refresh handling and unauthorized response interceptors.

- Validate token signatures against public key
- Implement refresh token rotation logic
- Add unit tests for expired credentials
```

---

## 💡 Usage & CLI Options

```text
Usage: smartcommit [OPTIONS]

Options:
  -m, --model TEXT            Ollama model to use for generation [default: llama3.2:3b]
  -d, --detailed              Generate detailed multi-line message with body and bullets
  -s, --short                 Force single-line commit subject
  -H, --hint TEXT             Provide developer context/intent (e.g. 'closes #42')
  -n, --candidates INTEGER    Number of candidate commit messages to generate (1 to 5) [default: 1]
  -y, --commit, --yes         Commit staged changes directly with generated message
  -c, --copy                  Copy generated message to clipboard
  --emoji / --no-emoji        Prefix commit messages with Conventional Commit gitmoji
  --stat, --diff              Display staged diff summary stats before generating
  --dry-run                   Generate and print message without interactive prompts
  -v, --version               Show the smartcommit version and exit
  --help                      Show this message and exit
```

### Common Workflows

```bash
# 1. Interactive generation with prompt to commit, edit, or copy
smartcommit

# 2. Generate a detailed multi-line commit message
smartcommit --detailed

# 3. Guide the AI with custom intent
smartcommit --hint "fixes memory leak in event loop"

# 4. Generate 3 candidate commit messages to pick from
smartcommit --candidates 3

# 5. Automatically generate and commit in one step
smartcommit --commit

# 6. Show staged diff stats and add gitmoji
smartcommit --diff --emoji
```

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Git
- [Ollama](https://ollama.com) installed and running

```bash
# Pull a recommended model
ollama pull llama3.2:3b
# Or a specialized coding model
ollama pull qwen2.5-coder:7b
```

### Install from Source

```bash
git clone https://github.com/priyanshusharma-dev/smartcommit.git
cd smartcommit

python -m venv venv
venv\Scripts\activate      # Windows (or: source venv/bin/activate on Unix)

pip install -e .
```

---

## ⚙️ Configuration

All settings can be customized using environment variables or a `.env` file:

| Environment Variable | Default | Description |
|---|---|---|
| `SMARTCOMMIT_DEFAULT_MODEL` | `llama3.2:3b` | Default Ollama model |
| `SMARTCOMMIT_OLLAMA_HOST` | `http://localhost:11434` | Ollama server API URL |
| `SMARTCOMMIT_MAX_DIFF_CHARS` | `8000` | Max characters of staged diff sent to AI |
| `SMARTCOMMIT_AI_TIMEOUT_SECONDS` | `40` | Timeout before fallback engages |
| `SMARTCOMMIT_MAX_LENGTH` | `72` | Max length of subject header |
| `SMARTCOMMIT_USE_EMOJI` | `false` | Enable gitmoji prefixes by default |
| `SMARTCOMMIT_DETAILED` | `false` | Enable detailed body messages by default |
| `SMARTCOMMIT_INTERACTIVE` | `true` | Enable interactive action menu |

---

## 🧪 Testing

SmartCommit includes an extensive unit test suite covering AI generation, fallback heuristics, diff filtering, and CLI interactions:

```bash
# Run tests
pytest

# Run tests with verbose output
pytest -v

# Run linter
ruff check smartcommit tests
```

---

## 📂 Project Structure

```text
smartcommit/
├── smartcommit/
│   ├── __init__.py
│   ├── ai_generator.py      # Dual-backend AI inference & semantic fallback engine
│   ├── cli.py               # Typer CLI with interactive actions & candidate picker
│   ├── config.py            # Pydantic Settings configuration & env overrides
│   ├── git_utils.py         # Safe Git subprocess helpers, stats, & lockfile filter
│   └── utils.py             # Prompt loader, ANSI cleaner, cross-platform clipboard
├── prompts/
│   └── conventional_prompt.txt # Conventional Commits 1.0.0 few-shot prompt
├── tests/
│   ├── test_ai_generator.py # Tests for AI generation, multi-line, & heuristics
│   ├── test_cli.py          # Tests for Typer CLI commands and options
│   └── test_git_utils.py    # Tests for Git interaction and diff filtering
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 🔒 Privacy & Security

- **100% Local**: Uses your local Ollama runtime.
- **Zero Cloud Leakage**: No telemetry, no external API keys, no cloud data transmission.
- **Safe for Enterprise**: Perfect for proprietary and closed-source enterprise repositories.

---

## 📜 License

MIT License — feel free to use and modify.

**Made with ❤️ for clean Git hygiene and developer productivity.**
