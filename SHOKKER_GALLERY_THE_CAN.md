# Shokker Gallery — "The Can"

**Planned feature.** A community hub where users share and download paint recipes. *Shoot your SHOKK files to The Can.*

---

## Name & branding

- **Official name:** Shokker Gallery  
- **Nickname:** **The Can**  
- **Tagline / call to action:** *Shoot your SHOKK files to The Can.*  
- **Rationale:** Aligns with the existing spray-can logo and makes sharing easy to say (“I put it on The Can,” “Check The Can”).

---

## What it is

A **website** (plus optional in-app entry) where:

- Users **register / log in** (e.g. email or Discord).
- Users **upload** paints: thumbnail image + .shokk file + title, description, optional tags (car type, sim, style).
- Anyone can **browse** (newest, popular, search by name or artist).
- Anyone can **download** a .shokk and open it in Shokker Paint Booth.
- **Leaderboard** (e.g. by downloads or likes) and **favorites** (heart a paint or follow an artist) drive engagement.

Same idea as Trading Paints for iRacing: central place to discover and grab other people’s schemes; the difference is our “scheme” is a SHOKK recipe and the target app is Shokker Paint Booth.

---

## How it fits with the app

- **Shokker Paint Booth** = where you design (zones, bases, patterns, spec, SHOKK save/load).
- **Shokker Gallery (The Can)** = where you share and discover. One central repository.
- **Flow:** Design in the app → “Share to The Can” (upload thumbnail + .shokk) → Others browse on the site → Download .shokk → Open in Paint Booth.
- **In-app integration (future):** e.g. “The Can” or “Gallery” button that opens the Gallery URL in the default browser (or an in-app browser tab) so users don’t have to remember the address.

---

## What we’d need (high level)

| Piece | Purpose | Ballpark |
|-------|---------|----------|
| **Domain** | e.g. `shokkergallery.com` or `thecan.shokker.com` | ~$10–15/year |
| **Web host** | Serves the site (pages, auth, API) | ~$5–20/month |
| **Database** | Users, paints (metadata), likes, favorites | Often included or ~$0–15/month |
| **File storage** | Store .shokk files + thumbnails (e.g. S3, R2, B2) | ~$5–25/month at early scale |
| **CDN (e.g. Cloudflare)** | Cache thumbnails, reduce bandwidth | Free tier often enough |

No need to host the main site and the files on the same box; the site stores **metadata + URLs**, and the actual files live in object storage so bandwidth scales cleanly.

---

## Bandwidth & scale (so it’s not scary)

- **“Pop off” scenario:** e.g. 500–1,000 people using the site, each downloading a few to a dozen paints per month.
- **Rough math:** 10,000 downloads/month × ~5 MB per .shokk ≈ 50 GB/month. Many hosts/CDNs include 100 GB–1 TB or charge a few cents per GB → **on the order of tens of dollars per month**, not “eating you alive.”
- **If it grows 10x:** CDN + storage pricing still keeps things in a manageable range (e.g. $50–150/month) and can be tuned as we go.

So: **yes, we host the files;** at the scale we’re aiming for, cost is predictable and manageable.

---

## Engagement features (future)

- **Leaderboard:** Top paints by downloads or likes; “This week” / “All time”; optional filter by car type.
- **Favorites:** Heart a paint → “My Favorites”; optional “Follow this artist” → feed of their uploads.
- **Search & discover:** By paint name, artist name, tags (car type, sim, style).
- **Featured:** Curated slot so strong work is always visible.
- **Low-friction share:** In-app “Share to The Can” → one flow to upload thumbnail + .shokk + title/description.

---

## Implementation outline (when we build it)

1. **Minimum viable Gallery**
   - Register / log in (e.g. email or Discord).
   - Upload: thumbnail + .shokk, title, description.
   - Browse: grid of thumbnails (e.g. newest first).
   - Download: button that serves the .shokk (from object storage).

2. **Then add**
   - Search (name, artist).
   - Leaderboard (downloads/likes).
   - Favorites (and optionally “follow artist”).
   - Optional: tags, car type, sim.

3. **App integration**
   - “The Can” / “Gallery” button in Shokker Paint Booth → opens Gallery URL.
   - “Share to The Can” from the app (upload current design as .shokk + thumbnail).
   - Download links that open in the app or save .shokk for the user to open manually.

4. **Infrastructure**
   - One backend (API + auth + DB).
   - One object-storage bucket for .shokk + thumbnails.
   - CDN in front to keep bandwidth and latency under control.

---

## Status

- **Name:** Shokker Gallery — “The Can.”  
- **Tagline:** *Shoot your SHOKK files to The Can.*  
- **Status:** Planned for the near future; not yet implemented.  
- This document is the single reference for the feature until we start building.
