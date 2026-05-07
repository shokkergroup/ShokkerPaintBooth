#!/usr/bin/env node
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = dirname(here);
const script = join(root, "tools", "export_full_dna_bible.py");

if (!existsSync(script)) {
  console.error(`Missing exporter script: ${script}`);
  process.exit(1);
}

const candidates = [
  process.env.PYTHON,
  "python",
  "py",
].filter(Boolean);

function runWith(pythonExe) {
  return new Promise((resolve) => {
    const child = spawn(pythonExe, [script, ...process.argv.slice(2)], {
      cwd: root,
      stdio: "inherit",
      shell: false,
      env: process.env,
    });
    child.on("error", (error) => resolve({ ok: false, code: 127, error }));
    child.on("exit", (code) => resolve({ ok: code === 0 || code === 2, code: code ?? 1 }));
  });
}

let last = null;
for (const candidate of candidates) {
  last = await runWith(candidate);
  if (last.ok) {
    process.exit(last.code);
  }
}

if (last?.error) console.error(last.error.message);
console.error("Could not launch Python. Set PYTHON to a Python 3.11+ executable and retry.");
process.exit(last?.code || 1);
