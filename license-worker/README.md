# SPB License Device-Activation Service

Caps each Payhip license key to a fixed number of **distinct PCs** (policy: **2 devices,
hard block**) so keys can't be shared around. Runs as a Cloudflare Worker backed by a KV
namespace — same Cloudflare account as the R2 bucket.

## What it does
- App sends `{key, fingerprint}` on activation → Worker verifies the key at Payhip, then
  registers the device in KV up to the cap.
- Known device = always allowed (your reinstalls / sandbox re-tests are free).
- New device over the cap = **blocked** with a clear "deactivate a PC or contact support"
  message.
- Self-service `/deactivate` frees a slot; idle devices auto-expire after 60 days.
- Owner/comp keys (`OWNER_KEYS`) are unlimited — your testing never hits the cap.
- **Security bonus:** the Payhip secret lives here, not in the shipped app.

## Deploy (one time)

Prereqs: Node + `npm i -g wrangler` (or use `npx wrangler`).

```bash
cd license-worker

# 1. Auth. Either:
#    wrangler login                 (interactive, opens a browser)
#  OR set a scoped API token:
#    export CLOUDFLARE_API_TOKEN=...   (needs: Account > Workers Scripts:Edit,
#                                       Account > Workers KV Storage:Edit, and the account id)

# 2. Create the KV namespace, paste the printed id into wrangler.toml (kv_namespaces[].id)
wrangler kv namespace create LICENSES

# 3. Set secrets (you'll be prompted to paste each value)
wrangler secret put PAYHIP_SECRET     # = spb-license-secrets.json -> payhipProductSecret
wrangler secret put TOKEN_SECRET      # any random 32+ char string
wrangler secret put ADMIN_SECRET      # any random 32+ char string (keep private)
wrangler secret put OWNER_KEYS        # your test license key(s), comma-separated

# 4. Ship it
wrangler deploy
# -> prints the live URL, e.g. https://spb-license.<your-subdir>.workers.dev
```

That `workers.dev` URL is what the app calls. (Optional later: map a custom route like
`activate.shokkergroup.com` in the Cloudflare dashboard.)

## Admin / support
```bash
# View a key's devices
curl -H "Authorization: Bearer $ADMIN_SECRET" "$URL/admin/key?key=ABC-123"

# Reset a key (free all slots) — for "I got a new PC" tickets
curl -X POST -H "Authorization: Bearer $ADMIN_SECRET" -H "content-type: application/json" \
     -d '{"key":"ABC-123","action":"clear"}' "$URL/admin/reset"
# actions: clear | disable | enable | unlimited | limited
```

## What I need to deploy this for you
Either **(a)** a Cloudflare API token with **Workers Scripts: Edit** + **Workers KV Storage:
Edit** (plus the account id) — then I run steps 1–4 from here — **or (b)** you run the four
commands above yourself (I'll hand you the exact secret values to paste). The R2 token from
earlier is R2-only, so it won't work for this.

## Notes
- KV is eventually-consistent; a determined sharer racing two activations in the same second
  could in theory beat the cap by one. For this scale that's negligible; if it ever matters,
  swap KV for D1 (transactional) — same endpoints.
- The app keeps a signed offline token (30-day grace) so it still launches without internet,
  re-checking on a heartbeat.
