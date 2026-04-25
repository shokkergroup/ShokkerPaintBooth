# Security Policy

## Supported Versions

During the Gold-to-Platinum experimental phase, only the **latest tagged release** receives security patches. Older versions are not back-patched. Once SPB hits Platinum GA (target: late 2026), we will establish an LTS branch and a formal support window.

| Version | Status | Security fixes |
|---|---|---|
| v6.2.x (Boil the Ocean) | Current | Yes |
| v6.1.x (Finish Mixer) | Maintenance | Critical only |
| v6.0.x | End of life | No |
| < v6.0 | End of life | No |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security problems.** Instead, contact us privately so we can investigate and patch before disclosure.

Preferred channels (in order):

1. **Email:** `ricky@shokkergroup.com` — subject line `[SPB SECURITY]` and a short description.
2. **Discord DM:** Any moderator on the [SPB Discord](https://discord.gg/shokker) flagged as `@moderator`.
3. **GitHub:** Private security advisory via GitHub's "Report a vulnerability" flow on the repo's Security tab.

Please include:

- A description of the issue and its impact
- Steps to reproduce (or a proof-of-concept)
- The SPB version, Windows version, and install method (Setup.exe, source, etc.)
- Any mitigating factors you're aware of

## Our Commitment

When you report a vulnerability responsibly, we commit to:

- **Acknowledge** receipt within **72 hours**.
- Provide a **triage update** within **7 days** indicating severity and planned action.
- **Keep you informed** during the fix process.
- **Credit** you in the release notes and `AUTHORS.md` unless you prefer to remain anonymous.
- **Coordinate** on any CVE assignment if applicable.

## Scope

The following are in-scope for security reports:

- Code execution via malformed PSD/TGA inputs loaded by SPB
- Code execution via crafted `.spb` project files
- Server-side vulnerabilities in the embedded Flask render server (`server.py`)
- Privilege escalation via the Electron main process
- Data exfiltration through SPB's network calls
- Crypto issues in license validation
- Bypass of the content-security-policy in renderer windows

The following are generally **out-of-scope**:

- Rendering artifacts or visual glitches (file a normal bug report)
- Denial-of-service against an SPB running on the user's own machine (it's single-user)
- Social-engineering of the maintainers
- Vulnerabilities in third-party dependencies for which an upstream fix is already available (though we still want to know so we can bump versions)
- SmartScreen / unsigned-binary warnings (we sign at Platinum GA)

## Disclosure

We follow a **coordinated disclosure** model. After a fix ships we will:

1. Publish a GitHub Security Advisory.
2. Note the fix in `CHANGELOG.md` under the release that contains it.
3. Credit the reporter (with permission).
4. Provide a workaround for users on older builds where possible.

## Bounty

SPB does not currently run a bug-bounty program. We may introduce one at Platinum GA. In the meantime, severe-impact reporters may receive Shokker Group swag, a free SPB commercial license, or both — at our discretion.

## Thanks

Security researchers make software better. Thank you for helping keep SPB painters safe.
