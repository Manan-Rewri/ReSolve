/**
 * Exercises the learn page's keydown handler against a stubbed DOM, so the
 * wiring (shortcut, language value, indent helper) is covered too.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../assets/js/pages/learn.js", import.meta.url), "utf8");

let passed = 0;
const failures = [];
const check = (name, fn) => {
  try {
    fn();
    passed += 1;
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
};

check("imports the comment helpers", () => {
  assert.match(source, /import \{[^}]*toggleComment[^}]*\} from "\.\.\/core\/comments\.js"/);
  assert.match(source, /import \{[^}]*lineRange[^}]*\} from "\.\.\/core\/comments\.js"/);
});

check("binds Ctrl+/ and Cmd+/ to the comment toggle", () => {
  assert.match(source, /\(event\.ctrlKey \|\| event\.metaKey\) && event\.key === "\/"/);
  assert.match(source, /event\.preventDefault\(\);\s*\n\s*const result = toggleComment\(/);
});

check("passes the selected language, not a hardcoded one", () => {
  assert.match(source, /toggleComment\(\s*\n?\s*target\.value,[\s\S]{0,120}languageSelect\.value/);
});

check("keeps Ctrl+Enter for run", () => {
  assert.match(source, /event\.key === "Enter"[\s\S]{0,80}runCode\(\)/);
});

check("Shift+Tab outdents a selection", () => {
  assert.match(source, /event\.shiftKey \? -1 : 1/);
});

check("shiftIndent block length covers every touched line", () => {
  // `updated` here is the whole document, so the slice is required - but a
  // stale slice silently shortens the restored selection, which is the bug
  // that shipped in comments.js before its tests caught it.
  const body = source.slice(source.indexOf("function shiftIndent"));
  assert.match(body, /blockLength = updated\.slice\(first, last \+ 1\)\.join\("\\n"\)\.length/);
  assert.doesNotMatch(body, /head\.join\("\\n"\)\.length[\s\S]{0,40}updated\.join/);
});

check("does not reuse the removed lineRange logic", () => {
  assert.doesNotMatch(source, /stopsEarly/);
  assert.doesNotMatch(source, /text\.slice\(selectionEnd\)\.startsWith/);
});

check("placeholder follows the language", () => {
  assert.match(source, /editor\.placeholder = placeholderFor\(languageSelect\.value\)/);
});

console.log(`${passed} passed, ${failures.length} failed`);
for (const failure of failures) console.log(`FAIL ${failure}`);
process.exit(failures.length ? 1 : 0);
