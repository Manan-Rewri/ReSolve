import { Fragment } from 'react'
import type { ReactNode } from 'react'

/**
 * A deliberately tiny markdown renderer.
 *
 * Only the subset the problem statements actually use: fenced code, ATX
 * headings, bullet lists, and paragraphs, with `code`, **bold** and *italic*
 * inline. Rendering to React elements rather than HTML means there is no
 * dangerouslySetInnerHTML anywhere and therefore no XSS surface, even though
 * statements will eventually come from user input.
 */

type Block =
  | { kind: 'code'; lines: string[] }
  | { kind: 'heading'; level: number; text: string }
  | { kind: 'list'; items: string[] }
  | { kind: 'paragraph'; text: string }

function parse(source: string): Block[] {
  const blocks: Block[] = []
  const lines = source.replace(/\r\n/g, '\n').split('\n')

  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    if (!line.trim()) {
      i += 1
      continue
    }

    // Fenced code block
    if (line.trimStart().startsWith('```')) {
      const indent = line.length - line.trimStart().length
      const body: string[] = []
      i += 1
      while (i < lines.length && !lines[i].trimStart().startsWith('```')) {
        body.push(lines[i].slice(indent))
        i += 1
      }
      i += 1 // closing fence
      blocks.push({ kind: 'code', lines: body })
      continue
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line.trim())
    if (heading) {
      blocks.push({ kind: 'heading', level: heading[1].length, text: heading[2] })
      i += 1
      continue
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ''))
        i += 1
      }
      blocks.push({ kind: 'list', items })
      continue
    }

    // Paragraph: consume until a blank line or the start of another block.
    const paragraph: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trimStart().startsWith('```') &&
      !/^(#{1,6})\s+/.test(lines[i].trim()) &&
      !/^\s*[-*]\s+/.test(lines[i])
    ) {
      paragraph.push(lines[i].trim())
      i += 1
    }
    blocks.push({ kind: 'paragraph', text: paragraph.join(' ') })
  }

  return blocks
}

const INLINE = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  let match: RegExpExecArray | null

  INLINE.lastIndex = 0
  while ((match = INLINE.exec(text)) !== null) {
    if (match.index > last) out.push(text.slice(last, match.index))
    const token = match[0]
    const key = `${keyPrefix}-${match.index}`

    if (token.startsWith('`')) {
      out.push(
        <code className="md-code" key={key}>
          {token.slice(1, -1)}
        </code>,
      )
    } else if (token.startsWith('**')) {
      out.push(<strong key={key}>{token.slice(2, -2)}</strong>)
    } else {
      out.push(<em key={key}>{token.slice(1, -1)}</em>)
    }

    last = match.index + token.length
  }

  if (last < text.length) out.push(text.slice(last))
  return out
}

export function Markdown({ source }: { source: string }) {
  const blocks = parse(source)

  return (
    <div className="md">
      {blocks.map((block, index) => {
        const key = `b${index}`

        if (block.kind === 'code') {
          return (
            <pre className="md-pre" key={key}>
              <code>{block.lines.join('\n')}</code>
            </pre>
          )
        }

        if (block.kind === 'heading') {
          const Tag = `h${Math.min(block.level + 2, 6)}` as 'h3'
          return <Tag key={key}>{renderInline(block.text, key)}</Tag>
        }

        if (block.kind === 'list') {
          return (
            <ul key={key}>
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-${itemIndex}`}>{renderInline(item, `${key}-${itemIndex}`)}</li>
              ))}
            </ul>
          )
        }

        return <p key={key}>{renderInline(block.text, key)}</p>
      })}
    </div>
  )
}

export { Fragment }
