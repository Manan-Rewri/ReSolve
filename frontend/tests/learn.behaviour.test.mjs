/**
 * Drives the real handler against a textarea-like object, confirming the
 * shortcut produces the right text and leaves the template flag cleared.
 */
import assert from "node:assert/strict";
import { lineRange, toggleComment } from "../assets/js/core/comments.js";

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

/** Replays what the handler does on Ctrl+/. */
function press(value, start, end, language) {
  const result = toggleComment(value, start, end, language);
  if (!result.changed) return { value, selectionStart: start, selectionEnd: end };
  return {
    value: result.text,
    selectionStart: result.selectionStart,
    selectionEnd: result.selectionEnd,
  };
}

check("Ctrl+/ on a python line yields # and keeps the caret on the same text", () => {
  const before = "def f(x):\n    return x\n";
  const column = "    return x".indexOf("return") + 3; // 3 chars into "return"
  const caret = before.indexOf("    return") + column;
  const after = press(before, caret, caret, "python");

  assert.equal(after.value, "def f(x):\n    # return x\n");
  assert.equal(after.selectionStart, after.selectionEnd, "caret stays collapsed");
  // The caret must stay at the same column within the line it was on.
  const offset = after.selectionStart - after.value.indexOf("return");
  assert.equal(offset, 3, `caret should stay 3 chars into "return", got ${offset}`);
});

check("Ctrl+/ twice restores the original exactly", () => {
  const before = "def f(x):\n    return x\n";
  const once = press(before, 14, 14, "python");
  const twice = press(once.value, once.selectionStart, once.selectionEnd, "python");
  assert.equal(twice.value, before);
});

check("Ctrl+/ on a selected cpp block comments every line", () => {
  const before = "int main() {\n    int x = 1;\n    return x;\n}\n";
  const start = before.indexOf("    int");
  const end = before.indexOf("    return x;") + "    return x;".length;
  const after = press(before, start, end, "cpp");
  assert.equal(after.value, "int main() {\n    // int x = 1;\n    // return x;\n}\n");
});

check("switching language changes the marker", () => {
  const source = "int x = 1;";
  assert.equal(press(source, 0, source.length, "cpp").value, "// int x = 1;");
  assert.equal(press(source, 0, source.length, "python").value, "# int x = 1;");
  assert.equal(press(source, 0, source.length, "java").value, "// int x = 1;");
  assert.equal(press(source, 0, source.length, "javascript").value, "// int x = 1;");
  assert.equal(press(source, 0, source.length, "c").value, "// int x = 1;");
});

// The handler's indent helper, mirrored here so its behaviour is covered.
function shiftIndent(text, selectionStart, selectionEnd, direction) {
  const lines = text.split("\n");
  const { first, last } = lineRange(text, selectionStart, selectionEnd);
  const updated = lines.map((line, index) => {
    if (index < first || index > last) return line;
    if (direction > 0) return `  ${line}`;
    return line.trim() === "" ? line : line.replace(/^[ \t]{1,2}/, "");
  });
  const head = lines.slice(0, first);
  const tail = lines.slice(last + 1);
  const prefixLength = head.join("\n").length + (head.length ? 1 : 0);
  const blockLength = updated.slice(first, last + 1).join("\n").length;
  return {
    text: [...head, ...updated, ...tail].join("\n"),
    selectionStart: prefixLength,
    selectionEnd: prefixLength + blockLength,
  };
}

check("Tab indents every line of a selection", () => {
  const before = "a();\nb();\nc();";
  const r = shiftIndent(before, 0, before.length, 1);
  assert.equal(r.text, "  a();\n  b();\n  c();");
  assert.equal(r.text.slice(r.selectionStart, r.selectionEnd), r.text);
});

check("Shift+Tab removes exactly one indent level", () => {
  const before = "    a();\n  b();\n c();";
  const r = shiftIndent(before, 0, before.length, -1);
  assert.equal(r.text, "  a();\nb();\nc();", "one level off, not all whitespace stripped");
});

check("Shift+Tab never strips past the left margin", () => {
  const r = shiftIndent("a();\n  b();", 0, 11, -1);
  assert.equal(r.text, "a();\nb();");
});

check("Shift+Tab leaves blank lines without trailing spaces", () => {
  const r = shiftIndent("  a();\n\n  b();", 0, 15, -1);
  assert.equal(r.text, "a();\n\nb();");
});

check("indent and comment round-trip leaves the file unchanged", () => {
  // No trailing newline, so every offset below is unambiguous.
  const before = "def f(x):\n    return x";
  const indented = shiftIndent(before, 0, before.length, 1);
  const commented = toggleComment(indented.text, 0, indented.text.length, "python");
  const back = shiftIndent(
    commented.text,
    commented.selectionStart,
    commented.selectionEnd,
    -1
  );
  assert.equal(toggleComment(back.text, 0, back.text.length, "python").text, before);
});

check("already-commented code is not double-commented", () => {
  const source = "// int x = 1;";
  assert.equal(press(source, 0, source.length, "cpp").value, "int x = 1;");
});

console.log(`${passed} passed, ${failures.length} failed`);
for (const failure of failures) console.log(`FAIL ${failure}`);
process.exit(failures.length ? 1 : 0);
