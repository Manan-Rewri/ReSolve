/**
 * C++ completions for Monaco.
 *
 * Deliberately *not* clangd. Real type-aware IntelliSense needs a ~75MB wasm
 * language server plus cross-origin-isolation headers, which breaks the Google
 * Fonts we load and cannot be relied on to load in time on stage wifi.
 *
 * This is a curated completion set tuned for the Judge0 toolchain we actually
 * target: g++, so GCC-only facilities like `<bits/stdc++.h>` are offered.
 * Not type-aware — it will not know your variable is a vector. But it covers
 * what people actually reach for, costs zero extra bytes, and cannot fail.
 */
import * as monaco from 'monaco-editor/editor/editor.api'

type Entry = { label: string; insert: string; detail: string }

const KEYWORDS = [
  'auto', 'break', 'case', 'catch', 'class', 'const', 'constexpr', 'continue',
  'default', 'delete', 'do', 'else', 'enum', 'explicit', 'false', 'for',
  'friend', 'if', 'inline', 'namespace', 'new', 'noexcept', 'nullptr',
  'operator', 'private', 'protected', 'public', 'return', 'sizeof', 'static',
  'static_cast', 'struct', 'switch', 'template', 'this', 'throw', 'true',
  'try', 'typename', 'using', 'virtual', 'while',
]

/** Headers that exist on the Judge0 image. */
const HEADERS = [
  'bits/stdc++.h', 'iostream', 'vector', 'string', 'map', 'set',
  'unordered_map', 'unordered_set', 'queue', 'stack', 'array', 'deque',
  'tuple', 'utility', 'algorithm', 'numeric', 'cmath', 'climits',
  'functional', 'bitset',
]

const STD_TYPES = [
  'vector', 'string', 'array', 'deque', 'list', 'map', 'multimap', 'set',
  'multiset', 'unordered_map', 'unordered_set', 'queue', 'priority_queue',
  'stack', 'pair', 'tuple', 'optional', 'bitset',
]

const STD_FUNCTIONS = [
  'sort', 'stable_sort', 'reverse', 'unique', 'find', 'find_if', 'lower_bound',
  'upper_bound', 'count', 'count_if', 'accumulate', 'min', 'max',
  'min_element', 'max_element', 'swap', 'fill', 'fill_n', 'copy', 'rotate',
  'shuffle', 'abs', 'sqrt', 'pow', 'floor', 'ceil', 'round', 'gcd', 'lcm',
  'to_string', 'stoi', 'stoll', 'make_pair', 'make_tuple', 'get', 'begin',
  'end', 'size', 'cout', 'cin', 'cerr', 'endl', 'flush',
]

/** Members offered after `.` or `->`. */
const METHODS: Entry[] = [
  { label: 'push_back', insert: 'push_back($0)', detail: 'vector · append' },
  { label: 'emplace_back', insert: 'emplace_back($0)', detail: 'vector · append, in place' },
  { label: 'pop_back', insert: 'pop_back()', detail: 'vector · remove last' },
  { label: 'push', insert: 'push($0)', detail: 'stack · append' },
  { label: 'pop', insert: 'pop()', detail: 'stack · remove last' },
  { label: 'top', insert: 'top()', detail: 'stack · peek' },
  { label: 'front', insert: 'front()', detail: 'first element' },
  { label: 'back', insert: 'back()', detail: 'last element' },
  { label: 'size', insert: 'size()', detail: 'length' },
  { label: 'length', insert: 'length()', detail: 'string · length' },
  { label: 'empty', insert: 'empty()', detail: 'is it empty?' },
  { label: 'clear', insert: 'clear()', detail: 'remove all' },
  { label: 'begin', insert: 'begin()', detail: 'iterator to first' },
  { label: 'end', insert: 'end()', detail: 'iterator past last' },
  { label: 'insert', insert: 'insert($0)', detail: 'insert at position' },
  { label: 'erase', insert: 'erase($0)', detail: 'erase at position' },
  { label: 'at', insert: 'at($0)', detail: 'bounds-checked element' },
  { label: 'resize', insert: 'resize($0)', detail: 'change length' },
  { label: 'reserve', insert: 'reserve($0)', detail: 'preallocate' },
  { label: 'assign', insert: 'assign($0)', detail: 'overwrite contents' },
  { label: 'find', insert: 'find($0)', detail: 'locate a key' },
  { label: 'count', insert: 'count($0)', detail: 'how many' },
  { label: 'sort', insert: 'sort($0.begin(), $0.end())', detail: 'sort in place' },
  { label: 'first', insert: 'first', detail: 'pair · first' },
  { label: 'second', insert: 'second', detail: 'pair · second' },
  { label: 'substr', insert: 'substr($0, $1)', detail: 'string · slice' },
  { label: 'append', insert: 'append($0)', detail: 'string · concatenate' },
]

/** Block-shaped snippets. */
const SNIPPETS: Entry[] = [
  { label: 'main', insert: 'int main() {\n\t$0\n\treturn 0;\n}', detail: 'entry point' },
  {
    label: 'for',
    insert: 'for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n\t$0\n}',
    detail: 'indexed loop',
  },
  {
    label: 'for_range',
    insert: 'for (auto &${1:x} : ${2:container}) {\n\t$0\n}',
    detail: 'range-based loop',
  },
  { label: 'while', insert: 'while (${1:condition}) {\n\t$0\n}', detail: 'while loop' },
  { label: 'if', insert: 'if (${1:condition}) {\n\t$0\n}', detail: 'if' },
  {
    label: 'if_else',
    insert: 'if (${1:condition}) {\n\t$2\n} else {\n\t$0\n}',
    detail: 'if / else',
  },
  {
    label: 'include_bits',
    insert: '#include <bits/stdc++.h>',
    detail: 'GCC shortcut, valid on Judge0',
  },
]

let registered = false

export function registerCppCompletions(): void {
  if (registered) return
  registered = true

  const { CompletionItemKind, CompletionItemInsertTextRule } = monaco.languages
  const snippet = CompletionItemInsertTextRule.InsertAsSnippet

  monaco.languages.registerCompletionItemProvider('cpp', {
    triggerCharacters: ['.', '>', ':', '<'],

    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position)
      const range: monaco.IRange = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      }

      const beforeCursor = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      })

      // After `.` or `->` only members make sense.
      if (/(?:\.|->)\s*[A-Za-z_]*$/.test(beforeCursor)) {
        return {
          suggestions: METHODS.map((m) => ({
            label: m.label,
            kind: CompletionItemKind.Method,
            insertText: m.insert,
            insertTextRules: snippet,
            detail: m.detail,
            range,
          })),
        }
      }

      return {
        suggestions: [
          ...SNIPPETS.map((s) => ({
            label: s.label,
            kind: CompletionItemKind.Snippet,
            insertText: s.insert,
            insertTextRules: snippet,
            detail: s.detail,
            sortText: `0_${s.label}`,
            range,
          })),
          ...HEADERS.map((h) => ({
            label: `<${h}>`,
            kind: CompletionItemKind.Module,
            insertText: `#include <${h}>`,
            detail: 'header',
            sortText: `1_${h}`,
            range,
          })),
          ...STD_TYPES.map((t) => ({
            label: t,
            kind: CompletionItemKind.Class,
            insertText: `std::${t}<$0>`,
            insertTextRules: snippet,
            detail: 'std type',
            sortText: `2_${t}`,
            range,
          })),
          ...STD_FUNCTIONS.map((f) => ({
            label: f,
            kind: CompletionItemKind.Function,
            insertText: `std::${f}($0)`,
            insertTextRules: snippet,
            detail: 'std function',
            sortText: `3_${f}`,
            range,
          })),
          ...KEYWORDS.map((k) => ({
            label: k,
            kind: CompletionItemKind.Keyword,
            insertText: k,
            detail: 'keyword',
            sortText: `4_${k}`,
            range,
          })),
        ],
      }
    },
  })
}
