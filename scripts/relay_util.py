#!/usr/bin/env python3
"""Helpers for relay.sh. Run with `python3 -I relay_util.py <command> ...`.

  screen-secrets <file>   Find credentials before a prompt leaves the machine. Prints one
                          "rule (line N)" per finding, never the value. Exit 1 on a finding.
  screen-output <file>    Find prompt-injection and exfiltration text in a worker's reply.
                          Prints one "rule (line N): excerpt" per finding. Exit 1 on a finding.
  spent <LOG.md>          Sum of the dollar costs recorded in LOG.md.
  status <LOG.md> [budget]  One line per step, then totals.

The patterns follow ruflo's shared secret and injection screens (plugins/ruflo-deepseek-harness/
hooks/screen.ts, v3/@claude-flow/aidefence), cut down to what a bash relay needs.
"""
import math
import re
import sys

MAX_SCREEN_BYTES = 2_000_000
INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")

SECRET_RULES = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Slack webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{20,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("OpenAI/Anthropic key", re.compile(r"\bsk-(?:ant|proj|svcacct|admin)-[A-Za-z0-9_-]{20,}")),
    ("sk- key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("Stripe live key", re.compile(r"\b[rs]k_live_[A-Za-z0-9]{16,}")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    ("SendGrid key", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{24,}")),
]
URL_CREDENTIALS = re.compile(r"\b[a-z][a-z0-9+.-]*://([^\s:/@]+):([^\s/@]+)@")
KEY_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|token|passw(?:or)?d|credential)s?\b[\"']?\s*[:=]\s*[\"']?([^\s\"',;]{8,})")
PLACEHOLDER = re.compile(
    r"(?i)your[_-]|example|changeme|change_me|redacted|placeholder|dummy|xxxx|\*\*\*|<[^>]*>|^\$|\$\{|"
    r"process\.env|os\.environ|getenv|vault:|op://|arn:|\(|\)")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
DOTTED = re.compile(r"^[A-Za-z_][\w]*(\.[A-Za-z_][\w]*)+$")

INJECTION_RULES = [
    ("override instructions", re.compile(
        r"(?i)\b(ignore|disregard|forget|override)(?:\s+\S+){0,6}?\s+(instructions?|prompts?|rules?|system prompt)\b")),
    ("role hijack", re.compile(r"(?i)\byou are now\b|\bnew instructions\s*:")),
    ("fake system tag", re.compile(r"(?i)<\s*/?\s*(system|assistant)\s*>")),
    ("hide from user", re.compile(r"(?i)\bdo not (tell|inform|mention (?:this )?to) the user\b")),
    ("pipe to shell", re.compile(r"(?i)\b(curl|wget)\b[^\n|]*\|\s*(ba|z)?sh\b")),
    ("collector host", re.compile(
        r"(?i)\b(webhook\.site|ngrok(?:-free)?\.(?:io|app|dev)|oastify\.com|interact\.sh|requestbin|"
        r"pipedream\.net|burpcollaborator\.net)\b")),
    # Needs a destination as well, so "added tests for POST /api/tokens" stays quiet.
    ("send secrets", re.compile(
        r"(?i)\b(send|post|upload|exfiltrate|paste|forward)\b[^\n]{0,60}?(\.env\b|\bapi[ _-]?keys?\b|\bsecrets?\b|"
        r"\bcredentials\b|\btokens?\b|\bpasswords?\b)[^\n]{0,60}?\b(to|into)\s+(https?://|[\w.+-]+@[\w-]+\.|"
        r"[\w-]+(\.[\w-]+)+/)")),
]


def read_text(path):
    data = open(path, "rb").read()
    if len(data) > MAX_SCREEN_BYTES:
        return None
    return INVISIBLE.sub("", data.decode("utf-8", errors="replace"))


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def looks_random(value):
    classes = sum(bool(re.search(p, value)) for p in (r"[a-z]", r"[A-Z]", r"[0-9]", r"[^A-Za-z0-9]"))
    if classes < 2:
        return False
    counts = {c: value.count(c) for c in set(value)}
    entropy = -sum(n / len(value) * math.log2(n / len(value)) for n in counts.values())
    return entropy >= 2.5


def is_placeholder(value):
    return bool(PLACEHOLDER.search(value) or UUID.match(value) or DOTTED.match(value)
                or value.startswith(("./", "../", "/")))


def screen_secrets(path):
    text = read_text(path)
    if text is None:
        return ["input too large to screen (over %d bytes)" % MAX_SCREEN_BYTES]
    found = []
    for name, rx in SECRET_RULES:
        for m in rx.finditer(text):
            if name == "sk- key" and not re.search(r"\d", m.group(0)):
                continue
            found.append("%s (line %d)" % (name, line_of(text, m.start())))
    for m in URL_CREDENTIALS.finditer(text):
        if not is_placeholder(m.group(2)):
            found.append("password in URL (line %d)" % line_of(text, m.start()))
    for m in KEY_ASSIGNMENT.finditer(text):
        value = m.group(1)
        if not is_placeholder(value) and looks_random(value):
            found.append("key assignment (line %d)" % line_of(text, m.start()))
    return sorted(set(found), key=lambda s: int(re.search(r"line (\d+)", s).group(1)) if "line" in s else 0)


def screen_output(path):
    text = read_text(path)
    if text is None:
        return ["output too large to screen (over %d bytes)" % MAX_SCREEN_BYTES]
    found = []
    for name, rx in INJECTION_RULES:
        for m in rx.finditer(text):
            excerpt = text[m.start():m.end()].replace("\n", " ")[:80]
            found.append("%s (line %d): %s" % (name, line_of(text, m.start()), excerpt))
    return found


HEADER = re.compile(
    r"^## (\S+?): (.*), (?:(\d+)s|done in-session by the conductor), (\d{4}-\d\d-\d\d \d\d:\d\d)$")
COST = re.compile(r"\bcost \$([0-9]+(?:\.[0-9]+)?)")
TOKENS = re.compile(r"\btokens ([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)")


def parse_log(path):
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except FileNotFoundError:
        return []
    steps, cur = [], None
    for line in lines:
        h = HEADER.match(line)
        if h:
            cur = {"id": h.group(1), "status": h.group(2), "secs": h.group(3), "cost": None, "tokens": None}
            steps.append(cur)
            continue
        if cur is None or not line.startswith("- "):
            continue
        c = COST.search(line)
        if c and cur["cost"] is None:
            cur["cost"] = float(c.group(1))
        t = TOKENS.search(line)
        if t and cur["tokens"] is None:
            cur["tokens"] = t.group(1)
    return steps


def spent(path):
    return sum(s["cost"] or 0.0 for s in parse_log(path))


def status(path, budget=None):
    steps = parse_log(path)
    if not steps:
        print("no steps recorded in %s" % path)
        return
    print("%-12s %-46s %6s %10s" % ("step", "status", "time", "cost"))
    tally = {}
    for s in steps:
        word = s["status"].split(" ", 1)[0].rstrip(",")
        tally[word] = tally.get(word, 0) + 1
        cost = "$%.4f" % s["cost"] if s["cost"] is not None else (s["tokens"] + " tok" if s["tokens"] else "-")
        st = s["status"] if len(s["status"]) <= 46 else s["status"][:43] + "..."
        print("%-12s %-46s %6s %10s" % (s["id"], st, (s["secs"] + "s") if s["secs"] else "-", cost))
    total = sum(s["cost"] or 0.0 for s in steps)
    summary = ", ".join("%d %s" % (n, w) for w, n in sorted(tally.items()))
    line = "total: %d entries (%s); recorded cost $%.4f" % (len(steps), summary, total)
    if budget:
        line += " of a $%.2f budget (%.0f%%)" % (budget, 100 * total / budget)
    print(line)
    unverified = [s["id"] for s in steps if s["id"].endswith(("-codex", "-agy", "-claude", "-vibe"))
                  and s["status"].startswith(("ok", "partial"))]
    verified = [s for s in steps if s["id"].endswith("-verify")]
    if unverified and not verified:
        print("note: no verify entries yet; run relay.sh verify for each deliverable you accept")


def main(argv):
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, path = argv[1], argv[2]
    if cmd == "screen-secrets":
        found = screen_secrets(path)
    elif cmd == "screen-output":
        found = screen_output(path)
    elif cmd == "spent":
        print("%.6f" % spent(path))
        return 0
    elif cmd == "status":
        status(path, float(argv[3]) if len(argv) > 3 and argv[3] else None)
        return 0
    else:
        print("unknown command: %s" % cmd, file=sys.stderr)
        return 2
    for f in found:
        print(f)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
