# SPB Linear Low-Usage Workflow

Status: mandatory for AI agents using Linear on Shokker Paint Booth.

Linear is valuable because it stores decisions, owner notes, and cross-agent handoffs. It can also become expensive if agents repeatedly read entire long discussions. Treat Linear as the source of truth, but use bounded reads and local compact mirrors.

## Default Rule

Do not read an entire long Linear thread by default.

Use this order:

1. Read `WORKSPACE_LOCATION.md`.
2. Read `docs/SPB_LOW_USAGE_PROTOCOL.md`.
3. Read this file.
4. Read the local compact handoff if one exists.
5. Query Linear only for the specific issue and latest relevant comments.

## Safe Linear Read Pattern

For a known issue:

- Fetch the issue metadata/description.
- Fetch the latest 3-5 comments.
- Search/list broader comments only when the latest context is insufficient.
- Summarize what you learned into a local handoff or the issue description so the next agent does not need the whole thread.

For unknown issue discovery:

- Query by exact issue id or title keyword.
- Limit results.
- Prefer active project/team filters.

## Hard Bans

- Do not read hundreds of Linear comments just to orient.
- Do not treat Linear discussion as the only durable memory; write compact local mirrors for active workstreams.
- Do not paste long Linear transcripts into chat.
- Do not ask every agent to rediscover the same Linear history.

## Local Mirrors

Use local files for compact working state:

- `SPB_LINEAR_HANDOFF.md` for broad project handoff.
- `docs/SPB_103_TOKEN_EFFICIENCY_HANDOFF.md` for repo-wide token efficiency/modularization.
- Domain docs for specialized work, such as `docs/TOOL_ARCHITECTURE.md` and `docs/SPB_93_LOW_USAGE_PROTOCOL.md`.

When Linear context changes materially, update the matching local mirror with:

```text
Current Issue:
Owner Intent:
Recent Decisions:
Changed Files:
Verification:
Next:
```

## Linear Comment Shape

Keep Linear comments compact:

```text
Focus:
Done:
Verified:
Risks:
Next:
```

This gives future agents high-signal updates without forcing them to read the whole discussion.

## Current SPB-103 Rule

SPB-103 is the umbrella for repo-wide token efficiency and modularization. Agents working on file breakup or context-database improvements should:

- Read `docs/SPB_103_TOKEN_EFFICIENCY_HANDOFF.md`.
- Read the SPB-103 issue description.
- Read only the latest few SPB-103 comments unless specific history is needed.
- Update both Linear and the local handoff after meaningful structural changes.
