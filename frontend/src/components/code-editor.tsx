import { useEffect, useRef } from 'react'
// monaco-editor's `exports` map already prepends `esm/vs/`, so these
// specifiers look shallow but resolve to esm/vs/editor/... on disk.
import * as monaco from 'monaco-editor/editor/editor.api'

// `editor.api` is the API only. Without these standalone contributions the
// suggest widget, folding, find and hover simply do not exist — registering a
// completion provider does nothing on its own.
import 'monaco-editor/editor/contrib/suggest/browser/suggestController'
import 'monaco-editor/editor/contrib/find/browser/findController'
import 'monaco-editor/features/find/register'
import 'monaco-editor/editor/contrib/folding/browser/folding'
import 'monaco-editor/editor/contrib/bracketMatching/browser/bracketMatching'
import 'monaco-editor/editor/contrib/hover/browser/hoverContribution'
import 'monaco-editor/editor/contrib/contextmenu/browser/contextmenu'
import 'monaco-editor/editor/contrib/comment/browser/comment'

// Only the C++ grammar. `editor.main` would pull in all ~90 languages.
import 'monaco-editor/languages/definitions/cpp/register'
import editorWorker from 'monaco-editor/editor/editor.worker?worker'

// `MonacoEnvironment` is declared by monaco-editor's own types; we only fill
// it in. Vite turns the `?worker` import into a standalone worker chunk.
globalThis.MonacoEnvironment = {
  getWorker: () => new editorWorker(),
}

/**
 * The ReSolve editor theme. Monochrome by rule: emphasis comes from weight
 * and grey value, never hue.
 */
monaco.editor.defineTheme('resolve', {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: '', foreground: 'FFFFFF' },
    { token: 'comment', foreground: '6E6E6E', fontStyle: 'italic' },
    { token: 'keyword', foreground: 'FFFFFF', fontStyle: 'bold' },
    { token: 'string', foreground: 'B8B8B8' },
    { token: 'number', foreground: 'E8E8E8' },
    { token: 'type', foreground: 'FFFFFF', fontStyle: 'bold' },
    { token: 'type.identifier', foreground: 'FFFFFF' },
    { token: 'delimiter', foreground: 'A3A3A3' },
    { token: 'identifier', foreground: 'FFFFFF' },
    { token: 'preprocessor', foreground: 'B8B8B8' },
  ],
  colors: {
    'editor.background': '#0A0A0A',
    'editor.foreground': '#FFFFFF',
    'editorLineNumber.foreground': '#4A4A4A',
    'editorLineNumber.activeForeground': '#FFFFFF',
    'editor.lineHighlightBackground': '#121212',
    'editor.lineHighlightBorder': '#00000000',
    'editorCursor.foreground': '#FFFFFF',
    'editor.selectionBackground': '#262626',
    'editor.inactiveSelectionBackground': '#1F1F1F',
    'editorIndentGuide.background1': '#1F1F1F',
    'editorWidget.background': '#0A0A0A',
    'editorWidget.border': '#242424',
    'input.background': '#0A0A0A',
    'scrollbarSlider.background': '#26262680',
    'minimap.background': '#00000000',
  },
})

import { registerCppCompletions } from '@/lib/cpp-completions'

// Register once, at module load, alongside the theme.
registerCppCompletions()

type CodeEditorProps = {
  value: string
  onChange: (value: string) => void
  language?: string
}

/**
 * Monaco, wired for C++. Gives the VS Code editing experience: bracket
 * auto-close and colourisation, multi-cursor, find/replace, folding,
 * word-wrap toggle and a minimap.
 *
 * Note: full C++ IntelliSense needs a clangd language server over
 * monaco-languageclient. That is deliberately not used — it is a ~75MB wasm
 * download requiring cross-origin-isolation headers. See
 * `src/lib/cpp-completions.ts` for the curated completion set instead.
 */
export function CodeEditor({ value, onChange, language = 'cpp' }: CodeEditorProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null)
  const changeRef = useRef(onChange)

  // Refs must not be written during render.
  useEffect(() => {
    changeRef.current = onChange
  })

  useEffect(() => {
    const host = hostRef.current
    if (!host) return

    const editor = monaco.editor.create(host, {
      value,
      language,
      theme: 'resolve',
      fontFamily: "'JetBrains Mono', ui-monospace, monospace",
      fontSize: 13,
      lineHeight: 21,
      fontLigatures: true,
      tabSize: 4,
      insertSpaces: true,
      padding: { top: 14, bottom: 14 },
      automaticLayout: true,
      minimap: { enabled: true, renderCharacters: false },
      scrollBeyondLastLine: false,
      renderLineHighlight: 'line',
      bracketPairColorization: { enabled: true },
      guides: { bracketPairs: true, indentation: true },
      smoothScrolling: true,
      cursorBlinking: 'smooth',
      multiCursorModifier: 'ctrlCmd',
      suggest: { showWords: true },
      quickSuggestions: { other: true, comments: false, strings: false },
      formatOnPaste: true,
      wordWrap: 'off',
      contextmenu: true,
    })

    editorRef.current = editor

    const subscription = editor.onDidChangeModelContent(() => {
      changeRef.current(editor.getValue())
    })

    return () => {
      subscription.dispose()
      editor.dispose()
      editorRef.current = null
    }
    // Created once. `value` is pushed in by the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language])

  // Keep the buffer in sync when the parent replaces the value (e.g. Reset).
  useEffect(() => {
    const editor = editorRef.current
    if (editor && editor.getValue() !== value) {
      editor.setValue(value)
    }
  }, [value])

  // `automaticLayout: true` handles the flex parent settling.
  return <div className="h-full w-full" ref={hostRef} />
}
