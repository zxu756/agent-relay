# Multi-Agent Relay Kickoff Templates / 多 Agent 接力开工模板

Paste either template into a new conductor session (recommended: Claude Code, OpenCode, Codex, or Antigravity) after installing `agent-relay`.

## Quick Start (One-Liner)

```text
/agent-relay Build <target> in ~/Projects/<repo>: have codex generate the assets and review the diff, claude implement the core logic, vibe write tests, and agy write the README.
```

## Full Structured Template (Chinese)

```text
/agent-relay
你是这次接力的总调度，按 agent-relay 的流程走：预检 → 写 PLAN.md → 逐棒执行并亲自验收 → 汇报。

任务：<一句话说清要做出什么>
工作目录：<~/Projects/项目名>（不是 git 仓库就先 git init；已有项目就开新分支）
分工（没写的按 skill 默认）：
- Codex：<出图 / 第二意见审查 / 不用>
- Claude Code（你自己）：<核心实现>
- vibe：<测试 / 批量改写 / 读代码初筛 / 不用>
- agy：<README / 文档 / 不用>
每棒产出：<尽量写死文件路径，比如 assets/logo.png、tests/、README.md>
验收标准：<要跑的命令、要通过的测试、要看的页面>
限制：不提交、不推送、不装依赖（除非我说）；<语言、风格、篇幅>
预算：<整单最多 N 美元 / 不设>
计划写好直接开跑，不用等我确认。
```

## Notes

- **Filesystem handoffs only**: Workers do not share conversation history. Everything a worker needs must live in files under `<workdir>` or in its step prompt.
- **Independent verification**: Always run `scripts/relay.sh verify <workdir> -- <cmd...>` after each worker finishes instead of trusting self-reported completion.
- **Audit trail**: `.relay/PLAN.md` and `.relay/LOG.md` are recorded under `<workdir>/.relay/` and automatically added to `.git/info/exclude` (never polluting `.gitignore`).
