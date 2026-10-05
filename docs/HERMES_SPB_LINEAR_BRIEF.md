# Hermes SPB Linear Brief

Status: active handoff for Hermes Agent / Hermes Desktop working on Shokker Paint Booth.

## Canonical Workspace

Work only in:

```text
C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum
```

Do not use the stale E: copy:

```text
C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum
```

Read `WORKSPACE_LOCATION.md` first.

## Linear Source Of Truth

Primary current Linear issue for repo-wide token efficiency and modularization:

- SPB-103: Repo-wide token efficiency & modularization initiative
- URL: https://linear.app/shokker-poster-engine-gold/issue/SPB-103/repo-wide-token-efficiency-and-modularization-initiative

Tool-system hardening issue:

- SPB-93: Shokker Paint Booth tool-system hardening

Follow `docs/SPB_LINEAR_LOW_USAGE.md` before reading Linear. Do not hydrate long discussion threads by default. Read the issue description and latest few comments, then update the compact local mirror.

## Required Local Context

For SPB work, read:

1. `WORKSPACE_LOCATION.md`
2. `docs/SPB_LOW_USAGE_PROTOCOL.md`
3. `docs/HERMES_SPB_LINEAR_BRIEF.md`
4. A focused target from `scripts/spb_context.js --list`

For current token-efficiency work, also read:

- `docs/SPB_103_TOKEN_EFFICIENCY_HANDOFF.md`

For painting/tool-system work, also read:

- `docs/TOOL_ARCHITECTURE.md`
- `docs/SPB_93_LOW_USAGE_PROTOCOL.md`

## Hermes Operating Rule

Hermes should help as a low-cost scout and planner unless explicitly asked to edit code.

- Prefer DeepSeek V4 Flash for routine analysis.
- Use DeepSeek V4 Pro, Qwen3 Coder Next, Kimi K2.6, GLM 4.7 Flash, or GLM 4.7 only when the task fits.
- Avoid expensive Anthropic/Sonnet models for SPB unless Ricky explicitly requests them.
- Do not create 10-15 minute loops unless Ricky explicitly asks.
- Do not read monster files directly; use `scripts/spb_context.js`.

## Linear Write Shape

When Hermes updates Linear, keep comments compact:

```text
Focus:
Done:
Verified:
Risks:
Next:
```

If Linear API access is not configured, write the same update into the local handoff file so Codex/Claude can relay it.
