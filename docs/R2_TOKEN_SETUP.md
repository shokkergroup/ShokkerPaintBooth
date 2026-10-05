# The R2 token — do this ONCE, then never again

Owner ask 2026-08-09: *"I get so freaking lost in their interface… I want it where I never
have to look for the freaking tokens."*

**You do not need a new token per deploy.** The old runbook said to rotate every time; that
was caution, not a requirement. One long-lived token, scoped to one bucket, stored encrypted
on your PC, is the normal way to do this. Create it once and you are done forever.

---

## Skip their menus entirely — use the deep link

Paste this in your browser. It lands you directly on the R2 API-tokens page, no navigating:

**https://dash.cloudflare.com/?to=/:account/r2/api-tokens**

(The `:account` part is a Cloudflare placeholder — it fills in your account automatically. If
you have more than one account it will ask which first.)

If that link ever stops working, the manual path is:
`dash.cloudflare.com` → left sidebar **R2** → the **{ } API** button, top right of the R2
page → **Manage API tokens**.

---

## Create the token — 6 clicks

1. Click **Create API token** (sometimes **Create Account API token**).
2. **Token name:** `SPB Release (permanent)` — name it so future-you knows not to delete it.
3. **Permissions:** choose **Object Read & Write**.
   *Not* "Admin Read & Write" — that can create and delete whole buckets and the deploy
   never needs that. Object Read & Write is exactly enough to upload the payload and
   publish `latest.yml`.
4. **Specify bucket(s):** pick **only** `shokkerpaintbooth`. (If you leave it on "all
   buckets" the token is broader than it needs to be.)
5. **TTL / Expiration:** set to **no expiry / forever** if offered. This is the whole point —
   an expiring token is a future 2am surprise. If Cloudflare forces a maximum, pick the
   longest and note the date in `PRIORITIES.md`.
6. Click **Create API Token**.

## Then copy TWO values — this screen shows the secret ONCE

After creating, Cloudflare shows a summary. You need exactly two things:

| What you need | What it looks like | Where it is |
|---|---|---|
| **Access Key ID** | 32 hex characters | listed under "S3 Client" / "Use the following credentials" |
| **Secret Access Key** | 64 hex characters | right below it, usually behind a **Click to reveal** |

Ignore everything else on that page (the long "API token value", the jurisdiction endpoints).
The deploy only wants those two.

> **The secret is displayed once.** If you close the page without copying it, you cannot get
> it back — you just delete that token and make another. No harm done, but it wastes a trip.

---

## Store it (this is the "never look for it again" part)

In PowerShell, in the project folder:

```powershell
.\spb_release.ps1 -SaveKey
```

It asks for the two values, then:

- **Checks the shape before saving** — if a paste was truncated or picked up a stray
  character, it tells you *while Cloudflare still has the secret on screen*, so you can
  re-copy instead of starting over.
- **Encrypts with Windows DPAPI** into `.r2_credentials.xml` (gitignored). The ciphertext is
  bound to your Windows account on this machine — useless if copied anywhere else. Verified:
  the secret does not appear in that file in plaintext.
- **Immediately tests it against R2** (read-only) so you know it works before you ever
  depend on it.

From then on, every release just adds `-UseStoredKey` and never prompts again.

---

## "Is my saved token still good?"

```powershell
.\spb_release.ps1 -TestKey
```

Read-only — uploads nothing, changes nothing. It prints what is in the bucket, biggest first,
plus your free-tier usage, and warns when you are near the 10 GB ceiling. It also translates
R2's unhelpful errors:

| What you see | What it means |
|---|---|
| `OK - the key works` | nothing to do |
| *malformed - this is a paste problem* | re-copy both values, run `-SaveKey` again |
| `Unauthorized` / `AccessDenied` | key is well-formed but the token was deleted, expired, or lacks Object Read & Write on the bucket → make a new one |
| `cannot reach the endpoint` | network, not credentials |

## Revoking

Two steps, both needed: delete `.r2_credentials.xml`, **and** delete the token in Cloudflare
(same deep link). Deleting only the local file leaves a live token in your account.

---

## Where this fits

Once the token is stored, a release is:

```powershell
.\spb_release.ps1 -Phase build                   # no credentials at all
.\spb_release.ps1 -Phase stage -UseStoredKey     # upload; feed untouched, nobody updates
#   ... installer test: RELEASE_GATE_<version>.txt ...
.\spb_release.ps1 -Phase activate -UseStoredKey  # type GO -> live -> auto-verified
```

No token hunting, no dashboard, no env vars. The only Cloudflare visit you may still need is
deleting old payloads when the 10 GB free tier gets tight — and `-TestKey` tells you when that
is, so you are not guessing.
