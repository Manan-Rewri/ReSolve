/**
 * Language-aware comment toggling for the plain-textarea editor.
 *
 * Each supported language is described by the tokens it actually recognises,
 * so the editor never writes Python's `#` into C++ or C++'s `//` into Python.
 * Python has no block comment, so it is declared without one and the toggle
 * falls back to line comments for every selection.
 */

export const COMMENT_SYNTAX = {
  cpp: { line: "//", blockOpen: "/*", blockClose: "*/", block: true },
  c: { line: "//", blockOpen: "/*", blockClose: "*/", block: true },
  java: { line: "//", blockOpen: "/*", blockClose: "*/", block: true },
  javascript: { line: "//", blockOpen: "/*", blockClose: "*/", block: true },
  python: { line: "#", block: false },
};

const DEFAULT_SYNTAX = COMMENT_SYNTAX.cpp;

/** A sample of this language's comment style, used for the editor placeholder. */
export function placeholderFor(languageId) {
  return languageId === "python"
    ? "# Write your solution here"
    : "// Write your solution here";
}

export function syntaxFor(languageId) {
  return COMMENT_SYNTAX[languageId] ?? DEFAULT_SYNTAX;
}

/**
 * Index of the first occurrence of `token` that is real code rather than part
 * of a string literal, or -1. Without this, `print("a // b")` would look
 * commented out.
 */
function findTokenOutsideStrings(line, token) {
  let quote = null;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];

    if (quote) {
      if (char === "\\") {
        index += 1;
      } else if (char === quote) {
        quote = null;
      }
      continue;
    }

    if (char === '"' || char === "'") {
      quote = char;
      continue;
    }

    if (line.startsWith(token, index)) return index;
  }

  return -1;
}

/**
 * Index of a line comment that owns the whole line, or -1. A trailing comment
 * after code does not count: commenting the line must not double up on it.
 */
function owningCommentIndex(line, syntax) {
  const index = findTokenOutsideStrings(line, syntax.line);
  if (index === -1) return -1;
  return line.slice(0, index).trim() === "" ? index : -1;
}

/** First and last line touched by a selection, both zero-based. */
export function lineRange(text, start, end) {
  const first = text.slice(0, start).split("\n").length - 1;
  // A caret with no selection only touches the line it sits on.
  if (start === end) return { first, last: first };

  // A selection whose final character is the line break stops on that line,
  // the same way every mainstream editor behaves, rather than reaching into
  // the next one.
  const endsOnBreak = text[end - 1] === "\n";
  const reached = text.slice(0, end).split("\n").length - 1;
  return { first, last: endsOnBreak ? reached - 1 : reached };
}

function addLineComment(line, syntax) {
  const indent = line.slice(0, line.length - line.trimStart().length);
  return `${indent}${syntax.line} ${line.slice(indent.length)}`;
}

function removeLineComment(line, syntax) {
  const index = owningCommentIndex(line, syntax);
  if (index === -1) return line;

  let after = index + syntax.line.length;
  if (line[after] === " ") after += 1;
  return line.slice(0, index) + line.slice(after);
}

/**
 * Toggles comments on the selection, or on the current line when nothing is
 * selected.
 *
 * Follows the behaviour of every mainstream editor: when every non-blank line
 * in the selection is already commented, the comment is removed, otherwise it
 * is added to all of them. Blank lines are skipped so a commented block does
 * not sprout lone `#` markers.
 *
 * Returns the new text plus the selection to restore, in character offsets.
 */
export function toggleComment(text, selectionStart, selectionEnd, languageId) {
  const syntax = syntaxFor(languageId);
  const { first, last } = lineRange(text, selectionStart, selectionEnd);

  const all = text.split("\n");
  const selected = all.slice(first, last + 1);
  const commentable = selected.filter((line) => line.trim() !== "");

  if (!commentable.length) {
    return { text, selectionStart, selectionEnd, changed: false };
  }

  const uncommenting = commentable.every(
    (line) => owningCommentIndex(line, syntax) !== -1
  );

  const updated = selected.map((line) => {
    if (line.trim() === "") return line;
    return uncommenting ? removeLineComment(line, syntax) : addLineComment(line, syntax);
  });

  const head = all.slice(0, first);
  const tail = all.slice(last + 1);
  const prefixLength = head.join("\n").length + (head.length ? 1 : 0);
  // `updated` is already exactly the selected block.
  const blockLength = updated.join("\n").length;

  // With no selection the caret is inside the edited line, so keep it over the
  // same text. The marker is written at the indent, which is before the caret,
  // so the column moves by however much the line grew ahead of that point.
  if (selectionStart === selectionEnd) {
    const column = selectionStart - prefixLength;
    const kept = Math.min(column, selected[0].length);
    const caret = prefixLength + kept + (updated[0].length - selected[0].length);
    return {
      text: [...head, ...updated, ...tail].join("\n"),
      selectionStart: caret,
      selectionEnd: caret,
      changed: true,
    };
  }

  return {
    text: [...head, ...updated, ...tail].join("\n"),
    selectionStart: prefixLength,
    selectionEnd: prefixLength + blockLength,
    changed: true,
  };
}
