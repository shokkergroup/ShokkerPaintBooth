# Customer client readiness — private diagnostic, Oct9 2026

SPB's current `server_routes/codex_setup.py` prepares/installs an MCP configuration and shows a `codex mcp add` command. It does not launch a client or choose an executable. Its existing-entry preservation and explicit configuration confirmation remain intact. The earlier subscription acceptance probe deliberately used an explicit installed desktop executable; that does not establish that the customer's PATH command uses the same client.

`client_readiness.py` checks up to four explicitly supplied installed clients, or the Codex command on PATH by default. It executes only `--version` and optional `login status`, with fixed arguments, no shell, bounded timeouts and hidden Windows processes. It removes API keys/base URLs and supplied token overrides from the child environment, preserves normal local Codex settings, and retains only classified results. Raw process output is never saved. It does not read credential files, install/update a client, alter model settings, launch listening, or select a client automatically.

Private local receipt: `_codex_mcp_work/chatgpt-dev/59910/client-readiness-native.json`. Installed npm client0.124.0 reports configuration_error; explicit desktop-bundled client0.162.0-alpha.2 reports ChatGPT sign-in. Both report inference_verified:false. Earlier real subscription inference/colour/Save/Undo receipts independently verify that explicit desktop client. An internal desktop executable location is evidence for this machine, not a supported universal customer installation path.

Nine focused checks pass in `test_client_readiness.py`: real failure boundaries include API-login refusal, configuration errors, failed/unknown version, missing login/client, timeouts, mismatched versions and no implicit selection. A first fixture path-normalization mismatch was corrected; the actual diagnostic reproduced the intended two-version case. Customer-facing setup wiring, a fresh profile and reconnect/wake acceptance remain open. The live59910 server was not restarted and shared setup source was not edited.

## Direct sign-in option to evaluate separately

OpenAI's [Sep28 Sign in with ChatGPT guide](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt) describes optional plan-use permission for eligible Plus/Pro accounts; launch availability includes open-source projects, locally running personal projects and selected private apps. SPB's eligibility has not been established. No client registration, OAuth flow or credential migration was performed.

The [official Codex app-server integration](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server) documents app identity, plan-authorized OAuth, RPC lifecycle and token renewal. Its returned model catalog does not prove entitlement; a completed inference establishes access for that request.

The [preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations) distinguish local MCP execution from unsupported hosted MCP/Responses tools and require separate conversation/history and token-renewal handling. This route uses Responses transport while authorizing eligible ChatGPT plan usage; the API hostname alone does not establish separate API-key billing. It is a distinct integration, not an automatic extension of the existing MCP connection. It does not establish a matching Claude route.

Shared lesson for both providers: show configuration, installed client, authenticated plan, listening status and successful conversation as separate checks. Keep the working provider's known result when another provider/client fails. Never silently switch to API usage or claim a model works from sign-in/version information alone.
