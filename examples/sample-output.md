# Sample output

## Example 1 — AI available (Ollama running)

```bash
$ git add smartcommit/ai_generator.py
$ smartcommit

Generating commit message...
Calling llama3.2:3b via Ollama...
✓ Generated with AI

Suggested Commit Message
fix(ai_generator): handle empty Ollama responses gracefully

Tip: git commit -m "fix(ai_generator): handle empty Ollama responses gracefully"
```

## Example 2 — AI unavailable (rule-based fallback)

```bash
$ git add smartcommit_demo/math_utils.py
$ smartcommit

Generating commit message...
Calling llama3.2:3b via Ollama...
⚠ Ollama isn't installed or isn't on PATH. Install it from https://ollama.ai to enable AI-generated messages.
↪ Using rule-based fallback (analyzing changed files)...

Suggested Commit Message
feat(smartcommit_demo): update smartcommit_demo/math_utils.py

Tip: git commit -m "feat(smartcommit_demo): update smartcommit_demo/math_utils.py"
```

The fallback isn't a placeholder string — it inspects which files changed
(added/modified/deleted, extensions, directory) to infer a real type and scope.