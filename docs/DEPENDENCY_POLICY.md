# Dependency Policy

Status: active
Owner: engine / platform
Related audit finding: STRAT-06 (dependency-floor drift)

This document defines how Python dependencies are declared across the project and
the rationale behind the version constraints. It exists so that a developer
checkout (`pip install -e .`) cannot silently pull a drifting numerical library
that changes engine math.

## TL;DR

| File                | Purpose                                       | Constraint style                  |
| ------------------- | --------------------------------------------- | --------------------------------- |
| `pyproject.toml`    | Dev installability + supported version window | Ranges (floors, capped for drift) |
| `requirements.txt`  | Reproducible / shipped runtime builds         | Exact pins (`==`), direct deps    |
| `requirements.lock` | Byte-reproducible full transitive freeze      | Exact pins (`==`), all transitive |

(There is no `requirements-dev.txt` in this repo; dev/test tooling lives in
`pyproject.toml` optional-dependency groups — see below.)

## The three layers

### 1. `pyproject.toml` — ranges (the contract for `pip install -e .`)

`pyproject.toml` declares the *supported version window* for each direct
dependency. It uses **ranges, never exact `==` pins**, because:

- A library/source checkout must remain installable alongside a developer's
  existing environment. Pinning `==` in `pyproject.toml` makes `pip install -e .`
  brittle and frequently uninstallable (it would conflict with any other pinned
  package in the same environment).
- Exact reproducibility is the job of `requirements.txt` / `requirements.lock`,
  not of package metadata.

The floors are kept current with the validated/shipped versions (see
`requirements.txt`). When the shipped pins are bumped, the corresponding
`pyproject.toml` floors should be raised toward them so a dev install does not
land on an ancient, untested version.

Dev/test/docs/gpu tooling is declared in
`[project.optional-dependencies]` (groups `dev`, `test`, `docs`, `gpu`) and is
also range-based. Install with e.g. `pip install -e .[dev]`.

### 2. `requirements.txt` — exact pins (reproducible / shipped builds)

`requirements.txt` holds **exact `==` pins** of the direct runtime
dependencies. These are the versions validated on the known-good build machine
and bundled into the shipped artifacts (Electron bundle, `pyserver` under
`electron-app/server/pyserver/_internal/`). This is what guarantees that what we
test is what we ship.

### 3. `requirements.lock` — full transitive freeze (byte-reproducible rebuilds)

`requirements.lock` is a full `pip freeze` including every transitive
dependency. It exists for byte-reproducible rebuilds / forensic regression
chasing. It is generated, not hand-edited:

```
python -m pip freeze > requirements.lock   # then re-add the header
```

## Drift-sensitive dependencies: numpy and scipy

`numpy` and `scipy` are **engine-math drift-sensitive**. The render engine
performs deterministic floating-point math (procedural noise fields, scipy
filters, numpy array ops) whose output is part of the shipped product. A
major-version jump in either can change numerical behavior (dtype promotion
rules, default algorithms, rounding, RNG, deprecated/changed APIs), which would
silently alter engine paint/spec output pixel-for-pixel.

Because of this, and only for these two, `pyproject.toml` adds an **upper major
cap** in addition to the raised floor:

```toml
"numpy>=2.4,<3",
"scipy>=1.17,<2",
```

The floor matches the validated/shipped version (numpy 2.4.x, scipy 1.17.x), and
the `<3` / `<2` cap prevents a dev checkout from silently jumping to a new major
that has not been validated against the engine. Raising the cap is a deliberate,
reviewed action that must be accompanied by re-validation of engine output.

The remaining runtime dependencies (flask, flask-cors, Pillow,
opencv-python-headless, requests, colorama, noise) are not engine
numerical-math dependencies; they carry **raised floors but no upper cap**, to
stay maximally installable while still excluding stale versions.

## Current constraints

`pyproject.toml` `[project].dependencies` (ranges):

```toml
"flask>=3.1",
"flask-cors>=6.0",
"numpy>=2.4,<3",
"scipy>=1.17,<2",
"Pillow>=11.0",
"opencv-python-headless>=4.8",
"requests>=2.32",
"colorama>=0.4",
"noise>=1.2",
```

`requirements.txt` (exact pins — the validated/shipped versions):

```
Flask==3.1.2
flask-cors==6.0.2
requests==2.32.5
numpy==2.4.2
scipy==1.17.0
Pillow==12.1.0
opencv-python-headless==4.13.0.92
colorama==0.4.6
noise==1.2.2
```

Every exact pin satisfies its `pyproject.toml` range, so the layers are mutually
consistent. Floors for the non-drift deps are set conservatively (at or below
the shipped major) to keep `pip install -e .` broad while still excluding
long-stale versions; the exact shipped versions remain those pinned in
`requirements.txt`.

`noise==1.2.2` is the last published release and is treated as a floor; it was
not present in the frozen known-good environment, so it has no validated `==`
beyond the published release (see the note in `requirements.txt`).

## How to bump a dependency

1. Update the exact pin in `requirements.txt`.
2. Regenerate `requirements.lock` (`python -m pip freeze > requirements.lock`,
   then re-add the header).
3. Raise the matching floor in `pyproject.toml` toward the new pin. Keep it a
   range; do not introduce `==`.
4. For `numpy` / `scipy` only: if the bump crosses the upper cap (`<3` / `<2`),
   re-validate engine paint/spec output (engine test suite + visual-diff
   harness) **before** widening the cap, and widen it deliberately in the same
   change.
