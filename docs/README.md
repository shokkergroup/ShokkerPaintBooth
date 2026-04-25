# SPB Documentation Index

This directory holds the **developer-facing** documentation for Shokker Paint Booth. It is separate from the user-facing `SPB_*.md` files at the project root, which cover "how to paint a livery" rather than "how the app is built."

If you are a **painter** looking for how to use SPB, start at [../SPB_GUIDE.md](../SPB_GUIDE.md) and [../SPB_QUICKSTART.md](../SPB_QUICKSTART.md).

If you are a **developer** looking to build, extend, or debug SPB, you are in the right place.

---

## Directory Structure

```
docs/
├── README.md              ← you are here
├── ARCHITECTURE.md        ← high-level system architecture
├── DEVELOPMENT.md         ← dev environment setup
├── BUILD.md               ← building Setup.exe
├── RELEASE_PROCESS.md     ← shipping a tagged release
├── DEBUGGING.md           ← debugging tips and tools
├── PERFORMANCE.md         ← perf tuning and profiling
└── TESTING.md             ← test strategy and layout
```

---

## Reading Order (New Contributors)

Follow these in order your first week:

1. **[../README.md](../README.md)** — project overview and what SPB is
2. **[../CONTRIBUTING.md](../CONTRIBUTING.md)** — the 3-copy sync rule, ownership, code style
3. **[ARCHITECTURE.md](ARCHITECTURE.md)** — how the pieces fit together
4. **[DEVELOPMENT.md](DEVELOPMENT.md)** — getting a local dev loop going
5. **[BUILD.md](BUILD.md)** — producing a Setup.exe
6. **[DEBUGGING.md](DEBUGGING.md)** — what to do when it breaks
7. **[TESTING.md](TESTING.md)** — how to prove your change works
8. **[PERFORMANCE.md](PERFORMANCE.md)** — when you need to make it fast
9. **[RELEASE_PROCESS.md](RELEASE_PROCESS.md)** — only once you're cutting releases

---

## Also Relevant (at Project Root)

- [../CHANGELOG.md](../CHANGELOG.md) — every version's notes
- [../PRIORITIES.md](../PRIORITIES.md) — current engineering priorities (if present)
- [../RESEARCH.md](../RESEARCH.md) — reference research (spec maps, PBR theory)
- [../QA_REPORT.md](../QA_REPORT.md) — audit flags and resolution status
- [../AUTHORS.md](../AUTHORS.md) — credits and contributors
- [../SECURITY.md](../SECURITY.md) — reporting vulnerabilities

## When to Add a New Doc Here

Create a new `docs/*.md` when:

- A topic is **developer-only** (painters won't care)
- It is **more than 300 words** (shorter items belong in existing docs)
- It is **cross-cutting** (not tied to a single file or module)

For file-specific or module-specific documentation, put a header comment at the top of the file itself.

## Contributing to Docs

Doc PRs are some of the most welcome kind. If you hit something confusing while getting set up, document it, and open a PR against the file that failed you. Future-you will thank past-you.
