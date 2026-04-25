# SPB Release Process

> How to ship a tagged release.

This is the checklist the Release Agent runs. If you're cutting a release manually, follow it step-by-step.

---

## Release Cadence

- **Patch releases** (`6.1.1`, `6.1.2`): as needed for bug fixes, usually weekly during Gold-to-Platinum.
- **Minor releases** (`6.1.0`, `6.2.0`): every 3–4 weeks; new features bundled.
- **Major releases** (`7.0.0`): reserved for breaking changes or Platinum GA.

Version numbers follow **SemVer** even during the pre-1.0-equivalent Gold-to-Platinum phase.

---

## Pre-Release Checklist

### T-minus 1 week
- [ ] Merge all targeted PRs to `main`.
- [ ] Verify CI is green (if configured).
- [ ] Update `PRIORITIES.md` to reflect what made it in vs. slipped.
- [ ] Tag candidate Discord testers for a beta flight.

### T-minus 3 days
- [ ] Run `pytest tests/` — must be green.
- [ ] Run `benchmark_finishes.py` — compare against prior release; flag regressions.
- [ ] Smoke-test: render 10 liveries across 10 different finishes.
- [ ] Verify 3-copy sync on all modified Python/JS files.
- [ ] Draft `CHANGELOG.md` entry (let release agent own, but review).
- [ ] Draft `SPB_RELEASE_NOTES.md` entry (user-facing; let docs agent own).

### T-minus 1 day
- [ ] Update version in `electron-app/package.json`.
- [ ] Update version in `README.md` (Top 10 Features if relevant).
- [ ] Update version in `SPB_FEATURES.md` header.
- [ ] Final review of `CHANGELOG.md`.
- [ ] Build a test installer via `npm run build`.
- [ ] Install on a clean VM and run the [BUILD.md verification steps](BUILD.md#verifying-the-build).

---

## Cutting the Release

### 1. Tag
```bash
git tag -a v6.2.0 -m "v6.2.0 — Boil the Ocean"
git push origin v6.2.0
```

### 2. Build
```bash
cd electron-app
npm run build
```

### 3. Verify
- Run installer on a fresh Windows VM.
- Check file size is reasonable (<250 MB).
- Launch and render a test livery.

### 4. Upload to GitHub Release
- Create release on GitHub using tag `v6.2.0`.
- Title: `v6.2.0 — Boil the Ocean` (or whatever codename).
- Body: paste `SPB_RELEASE_NOTES.md` contents for that version.
- Attach `Shokker Paint Booth Setup 6.2.0.exe`.
- Mark as latest release (uncheck pre-release).

### 5. Upload to PayHip
- Log into PayHip admin.
- Upload new installer to the SPB product.
- Update changelog on the product page.
- Notify existing customers via PayHip email automation.

### 6. Announce
- Post to Discord `#announcements` channel.
- Use template from `SPB_DISCORD_ANNOUNCEMENT.md`.
- Post to Trading Paints if release is notable.
- Tweet / BlueSky (if Shokker social handles are active).

---

## Post-Release

- [ ] Bump `main` branch version to next patch (`6.2.1-dev`) — optional, depends on team pref.
- [ ] Close related GitHub issues and milestones.
- [ ] Start fresh `CHANGELOG.md` "Unreleased" section.
- [ ] Monitor Discord + email for regression reports for ~48h.
- [ ] Update `PRIORITIES.md` with rollover items.
- [ ] Update `memory/heartbeats_history.md` with a release-day summary.

---

## Hotfix Process

If a critical bug is found post-release:

1. Branch from the release tag: `git checkout -b hotfix/v6.2.1 v6.2.0`.
2. Apply minimal fix.
3. Bump version to `6.2.1`.
4. Re-run the full Cutting the Release flow.
5. Merge hotfix branch back to `main` (`git merge --no-ff hotfix/v6.2.1`).

Hotfix timelines should be hours, not days. If it takes longer than a day, it's not a hotfix — it's a patch release.

---

## Versioning Rules

| Change type | Bump |
|---|---|
| Bug fix, no API change | PATCH (`6.2.0` → `6.2.1`) |
| New feature, backward-compatible | MINOR (`6.2.0` → `6.3.0`) |
| Breaking change to `.spb` file format | MAJOR (`6.x.y` → `7.0.0`) |
| Breaking change to server API | MAJOR |
| New finish | MINOR (usually grouped) |
| Docs-only change | No version bump |

---

## Release Codenames

Each major/minor release gets a codename. Recent history:

- `6.0.0` — "Major Engine Overhaul"
- `6.0.1` — "Deep Audit"
- `6.0.2` — "Quality Pass"
- `6.1.0` — "Finish Mixer"
- `6.1.1` — "Pattern Strength Zones"
- `6.2.0` — "Boil the Ocean"

Pick codenames that capture the spirit of the release. Two to four words. Evocative.

---

## Rollback

If a release goes catastrophically wrong:

1. **Unlist** on GitHub Releases (don't delete — users may have downloaded).
2. **Disable** on PayHip.
3. **Post** pinned Discord message with workaround or downgrade steps.
4. **Investigate**, patch, and ship a hotfix.

Rollback is rare. Prevention (pre-release checklist) is much cheaper.

---

## See Also

- [BUILD.md](BUILD.md) — producing the installer
- [../CHANGELOG.md](../CHANGELOG.md) — historical release record
- [../SPB_RELEASE_NOTES.md](../SPB_RELEASE_NOTES.md) — user-facing release notes
- [../SPB_DISCORD_ANNOUNCEMENT.md](../SPB_DISCORD_ANNOUNCEMENT.md) — announcement template
