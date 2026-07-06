# SmartCommit 🤖

**AI-Powered Git Commit Message Generator**

A smart CLI tool that automatically generates high-quality **Conventional Commit** messages by analyzing your staged Git changes using a local LLM (Ollama).

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![CLI](https://img.shields.io/badge/CLI-Typer-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Ollama](https://img.shields.io/badge/LLM-Ollama-orange)

---

## 📖 Overview

Writing meaningful commit messages is time-consuming. **SmartCommit** solves this by using **local AI** (Ollama) to analyze your code changes and generate clear, consistent, and professional Conventional Commit messages.

**Everything runs locally** — your code never leaves your machine.

---

## ✨ Key Features

- ⚡ Fast AI-powered commit message generation
- 🔍 Analyzes only staged changes (`git diff --cached`)
- 📏 Strictly follows **Conventional Commits** specification
- 🔒 Fully local & private (no cloud, no API keys)
- 🎨 Beautiful terminal output using Rich
- 🛠 Easy installation with `pip`
- 🧠 Smart fallback when AI is slow

---

## 🚀 Quick Start

```bash
# Stage your changes
git add .

**Example Output:**
```text
feat(auth): add JWT authentication middleware

- Implemented token validation
- Added refresh token logic
```

---

## 🛠 Tech Stack

| Technology     | Purpose                          |
|----------------|----------------------------------|
| Python 3.10+   | Core language                    |
| Typer          | Modern CLI framework             |
| Rich           | Beautiful terminal formatting    |
| Ollama         | Local LLM inference              |
| Subprocess     | Git integration                  |

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Git
- [Ollama](https://ollama.com) installed

```bash
# Install a model (recommended)
ollama pull llama3.2:3b
```

### Project Setup

```bash
git clone https://github.com/yourusername/smartcommit.git
cd smartcommit

python -m venv venv
venv\Scripts\activate      # Windows

pip install -e .
```

---

## 💡 Usage

```bash
git add .
smartcommit
```

**Options:**
```bash
smartcommit --help
```

---

## 📂 Project Structure

```text
smartcommit/
├── smartcommit/
│   ├── __init__.py
│   ├── cli.py
│   ├── git_utils.py
│   ├── ai_generator.py
│   ├── config.py
│   └── utils.py
├── prompts/
│   └── conventional_prompt.txt
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 🔒 Privacy & Security

- Runs 100% locally using Ollama
- No internet required after model download
- No API keys or data sharing
- Ideal for private and enterprise codebases

---

## 🎯 What I Learned

- Building production-ready CLI tools with Typer & Rich
- Integrating local LLMs (Ollama) into developer workflows
- Working with Git programmatically
- Proper Python packaging (`pyproject.toml`)
- Error handling and user experience design

---

## 📜 License

MIT License — feel free to use and modify.

---

**Made with ❤️ for better Git hygiene.**

---

---

### Next Step:
