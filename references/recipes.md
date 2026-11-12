# Relay recipes

Three chains that come up often. Each step names the agent, what it gets and the gate
the conductor runs before the next step starts. A gate is a `relay.sh verify` entry
whenever the check can be a command. Adjust the agents to what the user asked for.

## 1. Feature: spec, build, test, review, docs

For a new feature or module that deserves more than one pass.

| # | Who | Gets | Produces | Gate |
|---|---|---|---|---|
| 1 | conductor | the user's request | `.relay/SPEC.md`: behaviour, interfaces, error cases, and acceptance checks written as commands | the user's go-ahead, if the request was vague |
| 2 | Claude Code (in-session) | SPEC.md | the code | it builds or imports: `verify … -- <build or smoke command>` |
| 3 | vibe, tester add-on | SPEC.md (not the code) | `tests/…` | `verify … -- <test command>`; failures go to recipe 2 |
| 4 | Codex, reviewer add-on | `.relay/NN-review.diff` + SPEC.md | `.relay/REVIEW.md` | the conductor checks each finding, fixes the real ones, re-runs step 3's verify |
| 5 | agy, doc writer add-on | the code + SPEC.md | `README.md` or `docs/…` | commands in the docs run; paths exist |

Steps 2 and 3 can run in parallel, because tests written from the spec don't need
the code to exist yet. They write different files, so no worktree is needed. Writing
the tests from the spec rather than from the code is what lets them catch a bug.

## 2. Test-driven repair loop

For a failing test, a bug report with a reproduction, or step 3 above failing.

1. Conductor: reproduce the failure with `verify` and keep its log
   (`.relay/NN-verify.log`). No reproduction, no repair: ask for one first.
2. Worker (implementer add-on): gets the failing command, the log, and the files
   likely involved. Rule for this prompt: "Fix the code, not the tests. Don't edit
   files under tests/. If you think a test itself is wrong, say why and report
   STATUS: partial instead of changing it."
3. Conductor: run the same `verify` again, plus the full test suite to catch
   regressions.
4. Still failing: one more round with the new log. After two failed rounds, stop and
   report what was tried; a third blind attempt rarely does better.

## 3. Bulk migration or audit in batches

For one mechanical rule over many files (an API rename, a lint rule, a header), or a
read-only audit of a large codebase. vibe is the default worker, because its runs are
cheap. Each run still starts with about 12k tokens of vibe's own instructions, so
give it a batch rather than one file at a time.

1. Conductor: write the rule with one before/after example, and a manifest listing the
   files (`git grep -l <old pattern> > .relay/MANIFEST.txt`). Split it into batches of
   roughly 10–30 files, by directory where possible.
2. Run a pilot batch first (bulk editor or triage reader add-on). Read its whole diff
   yourself. Fix the rule wording until the pilot is right.
3. Each later batch: run the step, then the gate. For a migration that means build and
   tests through `verify`, plus a count of the old pattern
   (`verify … -- sh -c '! git grep -q <old pattern> -- <batch paths>'`). For an audit,
   spot-check three findings per batch against the code.
4. Skim the diff of every batch, not only the failing ones. A batch that fails its gate
   twice goes back to the conductor; don't let the worker retry indefinitely.
5. Set `RELAY_BUDGET_USD` for the whole job, and check `relay.sh status` between
   batches.

Batches that touch disjoint files can run in parallel in separate git worktrees (see
"Parallel steps" in SKILL.md). Merge them one at a time, re-running the gate after
each merge.

## Patterns from other orchestrators that this skill leaves out

ruflo (ruvnet/ruflo) was reviewed for ideas on 2026-11-10. These were adopted: the
process-group timeout kill, per-step cost and token records, a job budget, quota
detection, the secret screen before sending a prompt, the injection screen on replies,
verify entries with a workspace digest, the STATUS line, role add-ons, reviewers that
get the diff, and these recipes. These were not:

- Swarms, hive-mind queens, consensus and "agent spawn" records. In ruflo these mostly
  write records rather than start processes. A relay runs real CLIs one step at a time,
  and the conductor already coordinates them.
- Self-learning, pattern stores and neural routing. They add state that is hard to
  check, and the user picks the vendors on purpose.
- Daemons, background workers and federation. The relay is one job started by one
  conductor; nothing should keep running after it ends.
