# agent-relay

Chain coding agents from different vendors (`claude`, `codex`, `agy`, `vibe`) into one headless relay, using your current interactive agent session as the conductor and plain files in a shared Git working directory as the handoff layer.

Zero daemon, zero custom protocol, zero third-party dependencies (Bash + Python 3 stdlib only).

## Why `agent-relay`?

Developers often hold subscriptions across multiple coding CLIs whose strengths complement one another:
- **Codex (`codex exec`)** — Built-in image generation and independent second-opinion code review.
- **Claude Code (`claude -p`)** — Core implementation, complex refactors, architecture.
- **Mistral Vibe (`vibe -p`)** — Fast, low-cost bulk edits, spec-driven unit tests, log/code triage.
- **Antigravity (`agy -p`)** — Documentation, READMEs, tutorials, walkthroughs.

Instead of orchestrating nested frameworks or shared-memory servers, `agent-relay` runs each step headlessly against the same Git working tree, enforces safety/timeout/budget guardrails, and logs every baton pass under `<workdir>/.relay/`.

## Key Features

- **Recursion Guard**: Refuses to spawn nested relays if a worker sees the shared skill (`RELAY_WORKER` guard + prompt header check).
- **Pre-Send Secret Blocking**: Blocks accidental API keys, private keys, or bearer tokens in prompts before invoking external CLIs.
- **Output Injection & Exfiltration Triage**: Flags suspicious prompt-injection or credential-read patterns in worker transcripts.
- **Process-Group Timeout & Budget Caps**: Cleanly terminates hung workers and enforces `RELAY_BUDGET_USD` across metered CLIs.
- **First-Principles Verification**: `relay.sh verify` runs real test/build commands and records exit codes into `.relay/LOG.md` rather than trusting worker claims.
- **Clean Git Hygiene**: Automatically adds `.relay/` to `.git/info/exclude` without touching the target project's `.gitignore`.

## Installation

Install via [`skills`](https://github.com/vercel-labs/skills):

```bash
npx skills add zxu756/agent-relay -g
```

Or clone directly into your shared skills directory (`~/.agents/skills` works out of the box with OpenCode, Codex, and symlinked Claude Code / Antigravity setups):

```bash
git clone https://github.com/zxu756/agent-relay.git ~/.agents/skills/agent-relay
```

## CLI Reference (`scripts/relay.sh`)

```bash
# 1. Verify installed agent CLIs, auth status, and configured models
~/.agents/skills/agent-relay/scripts/relay.sh check

# 2. Run one headless worker step
~/.agents/skills/agent-relay/scripts/relay.sh run <workdir> <codex|claude|agy|vibe> "<self-contained prompt>"

# 3. Record a step performed directly by the conductor itself
~/.agents/skills/agent-relay/scripts/relay.sh note <workdir> <agent> "<one-line summary>"

# 4. Verify deliverables with an explicit command and log the result
~/.agents/skills/agent-relay/scripts/relay.sh verify <workdir> -- npm test

# 5. Print summary of steps, elapsed time, changed files, and metered cost
~/.agents/skills/agent-relay/scripts/relay.sh status <workdir>
```

## Repository Layout

- `SKILL.md` — Full conductor workflow, prompt rules, failure handling, and guardrails.
- `scripts/relay.sh` — Headless runner, CLI discovery, timeout/budget enforcement, `.relay/` logging.
- `scripts/relay_util.py` — Secret scanning, output auditing, cost accounting, JSONL parsing.
- `references/roles.md` — Role-specific prompt add-ons (implementer, tester, reviewer, doc writer, image).
- `references/recipes.md` — Ready-made multi-agent chains (spec-to-docs, TDD repair loop, batched migration).
- `examples/RELAY_KICKOFF.md` — Copy-paste kickoff prompts to start a relay session.

## License

[MIT](./LICENSE)
