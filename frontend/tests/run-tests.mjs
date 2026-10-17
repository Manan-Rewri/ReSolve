/**
 * Runs every frontend test file.
 *   node frontend/assets/js/run-tests.mjs
 */
import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

function collect(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) return collect(full);
    return entry.name.endsWith(".test.mjs") ? [full] : [];
  });
}

const files = collect(here);
let failed = 0;

for (const file of files) {
  const name = `tests/${file.split(/[\\/]/).pop()}`;
  process.stdout.write(`${name.padEnd(44)} `);
  try {
    const out = execFileSync("node", [file], { encoding: "utf8" });
    process.stdout.write(`${out.split("\n")[0]}\n`);
  } catch (error) {
    failed += 1;
    process.stdout.write("FAILED\n");
    process.stdout.write(`${error.stdout ?? ""}\n`);
  }
}

console.log(`\n${files.length - failed}/${files.length} test files passed`);
process.exit(failed ? 1 : 0);
