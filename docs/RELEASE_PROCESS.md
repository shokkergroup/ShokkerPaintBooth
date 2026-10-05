# SPB Release Process

Status: current release contract for the 10.x line. The executable release workflow is
`spb_release.ps1`; this document explains the gates around it.

Release identity covers `VERSION.txt`, `electron-app/package.json`, `config.py`
(`VERSION` and `BUILD_TAG`), and the browser `CLIENT_VERSION` in
`paint-booth-5-api-render.js`. `node scripts/spb_current_state.js --check-version`
is the fast non-mutating check, and the release preflight runs it automatically.

> **Executed walkthrough:** `docs/RELEASE_HANDOFF_CODEX_2026-09-09.md` — every step as actually run for 10.0.1 and 10.0.2, the helpers in `scripts/release/`, and the traps in the order they bite. Read it before your first release.

## Non-negotiable rule

A release command verifies a prepared candidate and its version identity. It never repairs, synchronizes,
re-baselines, or silently accepts the candidate while building it.

## Candidate requirements and identity

Before `spb_release.ps1 -Phase build`:

- Use the canonical workspace from `WORKSPACE_LOCATION.md`.
- Choose a new SemVer version. Never reuse a version whose installer/feed was
  already staged or published.
- Keep `electron-app/package.json`, `config.py`, and `VERSION.txt` consistent.
- Root is the hand-edited source; `electron-app/server/` is the only runtime
  mirror. The deleted PyInstaller `_internal` tree must not be recreated.
- Run root-to-mirror synchronization deliberately, review what changed, then
  require `node scripts/sync-runtime-copies.js --check` to pass.
- Resolve every P0 in the current release lane or explicitly scope it out in the
  dated gauntlet with owner approval.
- Use canonical fixture `spb-chevy-truck-2048-v1` exactly as pinned (including
  SHA-256 and five-zone setup) in `docs/SPB_RELEASE_GAUNTLET.md`.

For a compact, machine-readable snapshot of version identity, critical source
hashes, dirty-source count, mirror state, manifest pins, gates, and blockers:

```powershell
node scripts/spb_current_state.js
```

This command is read-only. Its `release.eligible` field stays false until the
isolated suites, dated gauntlet, and packaged-smoke evidence exist; a green
manifest check alone is never reported as a suite run.

## Required gates and phase boundary

The preflight is non-mutating and phase-aware:

```powershell
node scripts/spb_release_preflight.js --mode=prebuild
node scripts/spb_release_preflight.js --mode=prestage
node scripts/spb_release_preflight.js --mode=activate
node scripts/spb_release_gate_status.js
```

Every mode checks version identity, context integrity, pinned Layer/Easy plans,
featured-Easy quality, the canonical fixture, two-copy sync, file budgets, and
generated drift. `prebuild` requires source/isolated/gauntlet evidence but does
not require an installer or packaged smoke. `prestage` requires the built
distributable/feed hashes but not packaged smoke; `activate` requires the full
clean-machine record as well. The manifest and isolated proof must match
the current Git HEAD, with no tracked, staged, or non-ignored untracked changes.
Ignored build/evidence outputs do not make the candidate dirty.

Also require:

- syntax checks for every changed Python/JS file;
- focused tests for every defect, demonstrated failing against the old behavior;
- standing Layer and Easy suites from an isolated matching backend/profile;
- a dated PASS in `docs/SPB_RELEASE_GAUNTLET.md`;
- a packaged install/smoke on a clean Windows environment.

Focused suite totals are pinned. A missing or duplicate check is a broken suite,
not a smaller green denominator.

Run the real app from a disposable server and Chrome profile without touching
the standing `:59876` process:

```powershell
node scripts/spb_isolated_verify.js --suite all
```

This writes a hashed `isolated-proof.json`, logs, and screenshots under
`_release_evidence/<config-version>/isolated-<timestamp>/`. After the manual
five-zone gauntlet passes, create schema-2
`_release_evidence/<VERSION.txt>/release-evidence.json` with `version`,
`sourceHash`, `gitHead`, isolated-proof path/SHA-256, and the dated gauntlet
PASS/fixture/record path/SHA-256. That source evidence is sufficient for build.

After building, add:

- exactly three `distributables`: `updaterPackage` (`channels: ["r2"]`),
  `webInstaller` (`channels: ["r2", "payhip"]`), and `payhipBundle`
  (`channels: ["payhip"]`), each with root-relative `path`, `bytes`, and SHA-256;
- `latestYml` with its own path/bytes/SHA-256 and mappings
  `filesUrl -> webInstaller`, `path -> webInstaller`,
  `packagesX64Path -> updaterPackage`, and
  `packagesX64File -> updaterPackage`. That is the `prestage` contract.

After staging, run the staged installer on the clean machine and add
`packagedSmoke`: PASS, UTC `completedAt`, `cleanMachine: true`, hashed record,
and `artifactRoles: ["webInstaller", "updaterPackage"]`. Only this full contract
can activate.

The gate also recomputes both SHA-512 values and the package size embedded in
`latest.yml`; a feed that names different local bytes is rejected.
Use UTC ISO-8601 timestamps (for example, `2026-08-22T23:15:00Z`) for every
`completedAt` field.

`node scripts/spb_release_evidence_gate.js` re-hashes every referenced file and
requires an exact passing Layer+Easy isolated run with the security kill switch
active. A handwritten PASS label alone cannot satisfy the release preflight.

## Owner scope-outs (added 2026-09-05)

A standing suite can be scoped out of one release only by the owner, only in the evidence manifest,
and never silently. `evidence.scopeOuts.easySuite = { approvedBy: "owner", approvedAt: <UTC ISO>, reason: <>= 40 chars> }`
lets `scripts/spb_release_evidence_gate.js` accept an isolated all-suite proof whose ONLY failing suite is
Easy; the Layer suite must still pass, the Easy logs and screenshots must still be present and hashed,
and the gate prints `SCOPE-OUT ...` every time it runs. First use: 10.0.1 - the 2026-08-22 Easy shot plan
predates the owner's 2026-09-02 stripped-shell first-run decision and has never been green since; it is
being modernized separately (see the 10.0.1 run record). Remove the scope-out as soon as the plan is green.

## Lessons from 10.0.1 (2026-09-05)

- Check `electron-app/package.json` `build.compression` before building: an uncommitted `"store"` made a 7 GB payload out of a 4.1 GB one.
- The Easy runner pins the plan file's exact bytes; `git checkout` with autocrlf rewrites LF to CRLF and the runner aborts before any screenshot. Restore plan bytes from the blob, not via checkout.
- The proof binds Git HEAD and harness hashes: no repo edits (and no editing agents) between commit and activation; park concurrent shared-doc edits with `git stash` for the gate window.
- The build's copy-server-assets step dirties the mirror (scripts, _copy-manifest.json, 2048-only textures); revert + `sync --write` after every build before running a gate.
- Windows Sandbox needs `<MemoryInMB>` (24 GB used) and `<vGpu>Enable</vGpu>` or the engine hits MemoryError on first render.
- Never launch a background worker with DETACHED_PROCESS from the server; use CREATE_NO_WINDOW or its children pop consoles over the app.

## Build, smoke, stage, and activate

```powershell
.\spb_release.ps1 -Phase build
```

The build phase runs only the source/prebuild preflight, builds with
`SPB_BUNDLE_ALL=1`, enforces the payload-size floor, and prepares the
sandbox/PayHip kit. It performs sync **checks only**. Record the three built
distributables plus `latest.yml` in schema-2 evidence, then run:

To upload without activating the public update feed:

```powershell
.\spb_release.ps1 -Phase stage
```

`stage` never builds. It runs `prestage`, uploads the exact evidence-listed
payload and web installer with `spb-sha256` object metadata, and requires
authenticated R2 HEAD checks to match both SHA-256 metadata and byte size. It
does not upload `latest.yml`.

For an offline check of the identical local contract (no credentials/client):

```powershell
py -3 deploy_r2.py electron-app\dist --hold-latest --check-release-contract
```

Now install the staged web installer in the clean Windows environment, hash its
smoke record into `packagedSmoke`, and activate separately:

```powershell
.\spb_release.ps1 -Phase activate
```

Activation never builds or restages. It reruns the full preflight immediately
before `GO`, revalidates both staged R2 objects against the local evidence, then
uploads and HEAD-verifies the exact evidence-listed `latest.yml`. Public
confirmation compares the downloaded feed's SHA-256 with the local file; retry
exhaustion is a hard failure. `-Phase deploy` is the explicit combined
stage/human-pause/activate workflow. `-Phase all` and `-SkipBuild` are retired and
abort without building or uploading.

`-Phase verify` is also fail-closed: it exits nonzero when the public feed cannot
be read, has no parseable top-level version, or does not match the local package
version. It exits zero only for an exact version match.

`spb-sha256` is client-asserted S3 metadata, not an independent server-side byte
rehash. Missing or mismatched metadata always blocks activation; a streamed GET
hash or verified R2-native checksum would be required for independent remote-byte
proof.

## Final proof record

Record for every candidate:

- version and build tag;
- Git HEAD, canonical source hash, and clean-candidate result;
- UI/server hash, PID/start time, port, and restart status;
- focused/standing suite manifests and totals;
- release-gauntlet result;
- runtime-sync result;
- updater payload, web installer, PayHip bundle, and `latest.yml` SHA-256/bytes;
- authenticated staged-object SHA metadata checks and exact feed mapping;
- clean-install smoke result;
- known limitations and owner-approved scope-outs.

## Rollback

If a release is unsafe:

1. Stop activation or remove it from the latest feed; do not delete evidence.
2. Disable the affected PayHip download and post a clear customer notice.
3. Restore the previous known-good feed/artifact.
4. Fix from the exact released source, issue a new patch version, and rerun every
   release gate. Never replace an artifact under the same version.

## References

- `docs/SPB_ALPHA_RELEASE_PLAN.md`
- `docs/SPB_RELEASE_GAUNTLET.md`
- `scripts/spb_release_preflight.js`
- `spb_release.ps1`
- `CHANGELOG.md`
