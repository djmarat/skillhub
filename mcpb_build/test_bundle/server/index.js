#!/usr/bin/env node
/**
 * Skillhub MCP bundle launcher (Node.js wrapper).
 *
 * Spawns the bundled Python MCP server as a subprocess and bridges stdio
 * between the MCP host (Claude / Smithery / any MCP client) and Python.
 *
 * Why Node + Python? The MCPB spec recommends Node distribution because
 * Node ships with most host apps. The skill registry / scoring is already
 * implemented in Python, so we keep that and bridge with a 50-line Node
 * wrapper.
 */
"use strict";

const { spawn } = require("node:child_process");
const path = require("node:path");

const PYTHON = process.env.SKILLHUB_PYTHON || "python3";

const bundleRoot = path.resolve(__dirname, "..");
const srcDir = path.join(bundleRoot, "server", "lib");
const registry = path.join(bundleRoot, "registry", "skills.jsonl");
const collections = path.join(bundleRoot, "registry", "collections.json");

const args = [
  "-m", "skillhub_mcp.server",
  "--registry", registry,
  "--collections", collections,
];

const env = { ...process.env, PYTHONPATH: srcDir };
const child = spawn(PYTHON, args, { env, stdio: ["pipe", "pipe", "inherit"] });

process.stdin.pipe(child.stdin);
child.stdout.pipe(process.stdout);

child.on("error", (err) => {
  process.stderr.write(`skillhub-mcp: failed to spawn python: ${err.message}\n`);
  process.exit(127);
});

child.on("exit", (code) => process.exit(code === null ? 1 : code));
for (const sig of ["SIGTERM", "SIGINT", "SIGHUP"]) {
  process.on(sig, () => { try { child.kill(sig); } catch (_) {} });
}
