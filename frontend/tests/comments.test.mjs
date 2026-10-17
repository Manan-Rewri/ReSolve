import assert from "node:assert/strict";
import { lineRange, toggleComment, placeholderFor, syntaxFor } from "../assets/js/core/comments.js";

let passed = 0;
const failures = [];

function check(name, fn) {
  try {
    fn();
    passed += 1;
  } catch (error) {
    failures.push(`${name}\n    ${error.message.split("\n").slice(0, 4).join("\n    ")}`);
  }
}

/** Toggles the whole text and returns the result. */
function all(text, lang) {
  const r = toggleComment(text, 0, text.length, lang);
  return r.changed ? r.text : text;
}

// ---- syntax per language ----

check("python uses #", () => {
  assert.equal(syntaxFor("python").line, "#");
  assert.equal(placeholderFor("python"), "# Write your solution here");
});

check("cpp/java/js/c use //", () => {
  for (const lang of ["cpp", "c", "java", "javascript"]) {
    assert.equal(syntaxFor(lang).line, "//");
    assert.equal(placeholderFor(lang), "// Write your solution here");
  }
});

check("python has no block comment", () => {
  assert.equal(syntaxFor("python").block, false);
});

check("unknown language falls back to cpp", () => {
  assert.equal(syntaxFor("brainfuck").line, "//");
});

// ---- basic toggle ----

check("comments a python line with #", () => {
  assert.equal(all("return x", "python"), "# return x");
});

check("comments a cpp line with //", () => {
  assert.equal(all("return x;", "cpp"), "// return x;");
});

check("toggles back off", () => {
  const once = all("return x", "python");
  assert.equal(all(once, "python"), "return x");
});

// ---- indentation preserved ----

check("keeps leading indentation before the marker", () => {
  assert.equal(all("    return x", "python"), "    # return x");
  assert.equal(all("        return x;", "cpp"), "        // return x;");
});

check("uncomments from an indented line", () => {
  assert.equal(all("    # return x", "python"), "    return x");
  assert.equal(all("        // return x;", "cpp"), "        return x;");
});

// ---- multi-line ----

check("comments every line of a block", () => {
  const src = "int a = 1;\nint b = 2;";
  assert.equal(all(src, "cpp"), "// int a = 1;\n// int b = 2;");
});

check("uncomments a whole block", () => {
  const src = "// int a = 1;\n// int b = 2;";
  assert.equal(all(src, "cpp"), "int a = 1;\nint b = 2;");
});

check("skips blank lines instead of marking them", () => {
  const src = "a();\n\nb();";
  assert.equal(all(src, "cpp"), "// a();\n\n// b();");
});

check("mixed commented and uncommented comments everything", () => {
  const src = "// a();\nb();";
  assert.equal(all(src, "cpp"), "// // a();\n// b();");
});

check("block with blank line round-trips", () => {
  const src = "# a()\n\n# b()";
  assert.equal(all(src, "python"), "a()\n\nb()");
});

// ---- string literals must not be mistaken for comments ----

check("url inside a string is not treated as a comment", () => {
  const src = 'print("http://x")';
  const commented = all(src, "python");
  assert.equal(commented, '# print("http://x")');
  assert.equal(all(commented, "python"), src);
});

check("hash inside a string is not treated as a comment", () => {
  const src = 'cout << "a // b";';
  assert.equal(all(src, "cpp"), '// cout << "a // b";');
  assert.equal(all('// cout << "a // b";', "cpp"), src);
});

check("escaped quote does not end the string early", () => {
  const src = 'print("a\\" // b")';
  const commented = all(src, "python");
  assert.equal(commented, `# ${src}`);
  assert.equal(all(commented, "python"), src);
});

// ---- selection behaviour ----

check("no selection comments only the caret line", () => {
  const text = "a();\nb();\nc();";
  const r = toggleComment(text, 5, 5, "cpp"); // caret on line 1
  assert.equal(r.text, "a();\n// b();\nc();");
});

check("selection at column 0 does not drag in the next line", () => {
  const text = "a();\nb();";
  // Select "a();" only (0..4), which stops exactly at the newline.
  const r = toggleComment(text, 0, 4, "cpp");
  assert.equal(r.text, "// a();\nb();");
});

check("selection whose last character is the newline stops there", () => {
  // 0..5 is "a();\n" - it covers the break but not the start of line 2.
  const r = toggleComment("a();\nb();\n", 0, 5, "cpp");
  assert.equal(r.text, "// a();\nb();\n");
});

check("a selection spanning several lines still covers them all", () => {
  const r = toggleComment("a();\nb();\nc();\n", 0, 14, "cpp");
  assert.equal(r.text, "// a();\n// b();\n// c();\n");
});

check("lineRange reports the touched lines", () => {
  // "a\nb\nc"
  assert.deepEqual(lineRange("a\nb\nc", 0, 5), { first: 0, last: 2 }, "whole text");
  assert.deepEqual(lineRange("a\nb\nc", 2, 2), { first: 1, last: 1 }, "caret on line 1");
  assert.deepEqual(lineRange("a\nb\nc", 0, 4), { first: 0, last: 1 }, "ends on the newline");
  assert.deepEqual(lineRange("a\nb\nc", 0, 3), { first: 0, last: 1 }, '"a\\nb" touches lines 0 and 1');
  assert.deepEqual(lineRange("a\nb\nc", 1, 1), { first: 0, last: 0 }, "caret on line 0");
});

check("restores a selection over the commented block", () => {
  const text = "a();\nb();";
  const r = toggleComment(text, 0, 9, "cpp");
  assert.equal(r.selectionStart, 0);
  assert.equal(r.selectionEnd, r.text.length);
  assert.equal(r.text.slice(r.selectionStart, r.selectionEnd), "// a();\n// b();");
});

check("selection offsets point at the commented text, not the file start", () => {
  // Commenting lines 1 and 2 must leave the selection over those two lines,
  // so pressing Ctrl+/ again uncomments exactly what was toggled.
  const text = "keep();\na();\nb();\ntail();";
  const start = text.indexOf("a();");
  const end = text.indexOf("b();") + "b();".length;
  const r = toggleComment(text, start, end, "cpp");

  assert.equal(r.text, "keep();\n// a();\n// b();\ntail();");
  assert.equal(
    r.text.slice(r.selectionStart, r.selectionEnd),
    "// a();\n// b();",
    "selection must cover the commented block"
  );

  // Toggling again returns to the original text - the round trip only closes
  // if the offsets were right.
  const back = toggleComment(r.text, r.selectionStart, r.selectionEnd, "cpp");
  assert.equal(back.text, text);
});

check("a trailing comment is not mistaken for an owned one", () => {
  // Uncommenting a line whose only marker follows code would break it.
  const src = "a(); // note";
  const commented = all(src, "cpp");
  assert.equal(commented, "// a(); // note");
  assert.equal(all(commented, "cpp"), src);
});

check("blank selection reports no change", () => {
  const r = toggleComment("   \n", 0, 3, "python");
  assert.equal(r.changed, false);
  assert.equal(r.text, "   \n");
});

// ---- round trip is the real invariant ----

const ROUND_TRIP = [
  ["cpp", "int main() {\n    int x = 1;\n    return x;\n}"],
  ["python", "def f(x):\n    return x\n\n\nprint(f(1))"],
  ["java", "class A {\n    int x = 1;\n}"],
  ["javascript", "function f() {\n  return 1;\n}"],
  ["c", "int main(void) {\n    return 0;\n}"],
  ["python", '# already commented\nx = 1'],
  ["cpp", "/* block */\nint x;"],
  ["cpp", ""],
  ["python", "\n\n"],
  ["cpp", 'const char* s = "// not a comment";'],
  ["python", 's = "# not a comment"'],
];

for (const [lang, src] of ROUND_TRIP) {
  check(`round trips (${lang}): ${JSON.stringify(src).slice(0, 46)}`, () => {
    const once = all(src, lang);
    const twice = all(once, lang);
    assert.equal(twice, src, `\n  once:  ${JSON.stringify(once)}\n  twice: ${JSON.stringify(twice)}`);
  });
}

console.log(`${passed} passed, ${failures.length} failed`);
for (const failure of failures) console.log(`\nFAIL ${failure}`);
process.exit(failures.length ? 1 : 0);
