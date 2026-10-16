# ChatGPT subscription path review

Checked October10,2026; official documentation and private acceptance evidence. Shared AI/MCP/UI remains Claude-owned and unchanged.

## Product path

OpenAI documents optional ChatGPT plan usage within Sign in with ChatGPT for open-source and locally hosted apps. It directs paid or remotely hosted apps to an interest form. SPB's commercial eligibility is therefore **unconfirmed**; these docs are not authorization to ship a paid-app OAuth implementation. No registration, consent, token exchange or interest submission was performed. [Official overview](https://developers.openai.com/siwc/token-sharing-open-source), Introduction.

The preview requires stateless streaming Responses requests and limits supported hosted tools. Local MCP and local conversation storage are distinct from hosted MCP tools. An app using this future route needs its own authorized OAuth lifecycle. [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations).

The documented app-server route distinguishes model catalog availability from a successfully completed model turn. It describes initialize, saved thread IDs and token renewal with restart/resume. Do not infer entitlement from a model list or copy credentials from another app. [Official app-server guide](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server).

Existing Codex CLI execution reuses its saved authentication and exposes structured events; it can target a particular prior session. Our current SPB proof intentionally uses isolated ephemeral turns and reconstructs context from the current app transcript. [Official non-interactive guide](https://learn.chatgpt.com/docs/non-interactive-mode).

## Measured local improvement

`subscription-listener.cjs` is a bounded private59910 developer controller, using the installed ChatGPT-authenticated Codex client. It waits over local HTTP with zero idle model inference, commits a pending question before starting a model, and stops after a failed/unconfirmed worker. It never repeats paint operations: the worker exposes only wait, fresh assistant context and reply, rejecting all other MCP requests at the protocol boundary.

Explicit `--recover-pending` validates exact provider, document scope, sequence, text and30-minute age against the current transcript. A delivered answer settles a lost terminal journal write without inference. New-process recovery consumed one actual plan-backed model turn, with exact fresh query and shown_in_app receipt. Eight exposed paint fields and both original fixture hashes stayed exact. Six-second idle acceptance started zero model turns. CLI0.162.0-alpha.17.2 replaced the removed earlier binary path; no installed configuration/auth file was edited.

Evidence: `_codex_mcp_work/chatgpt-dev/59910/subscription-listener-recovery-2026-10-11T01-42-28-229Z.json`, corresponding worker receipt and `subscription-listener-idle-acceptance.json`; verifier `verify_subscription_listener.py`. Core/controller and actual three-tool MCP boundary tests pass.

Still open: customer Send UI, persistent startup/wake and crash-lock UX, busy/listening status beyond the server's20-second grace, actual process death/network loss during inference, installed Claude parity, shared/package adoption and commercial SIWC eligibility. The journal contains a single bounded buyer batch; do not package test conversations or pairing tokens. Receive-only checkpoint and controlled lost journal receipt are measured, not arbitrary crash recovery. Next universal lesson for Claude: preserve a received question, verify current context and delivery, and never use message redelivery as authority to repeat an edit.
