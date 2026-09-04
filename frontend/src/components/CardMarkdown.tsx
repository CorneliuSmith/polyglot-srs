import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'

/**
 * Markdown for card text (explanations, culture and function notes),
 * "like Anki" — brief item 7c phase 2.
 *
 * Reached only for a block that carries markdown syntax (see
 * ExplanationView's hasMarkdown): the corpus is plain text typeset by the
 * regex shapes, and this must not change how a single existing card reads.
 *
 * The allow-list is deliberately small: bold, italic, lists, tables, inline
 * code, links (http(s) only — rehype-sanitize's default protocols) and line
 * breaks. No raw HTML (there is no rehype-raw, so a tag prints literally
 * and the server strips it anyway), no images (a card must not fetch from
 * elsewhere), no headings (the card title is the heading). The server
 * cleans the same things on the way in (services/markdown.py); this is the
 * last line, not the only one.
 */
const SCHEMA = {
  ...defaultSchema,
  tagNames: [
    'p', 'strong', 'em', 'del', 'br', 'ul', 'ol', 'li', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a', 'blockquote',
  ],
  attributes: {
    a: ['href'],
    td: ['align'],
    th: ['align'],
  },
}

export default function CardMarkdown({ content }: { content: string }) {
  return (
    <div className="card-markdown space-y-2" data-testid="card-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, SCHEMA]]}
        components={{
          p: ({ children }) => <p>{children}</p>,
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="text-sm border border-gray-100 rounded-lg overflow-hidden">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="px-2.5 py-1 bg-gray-50 text-start font-semibold text-lang-dark">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-2.5 py-1 text-gray-700 border-t border-gray-50">
              {children}
            </td>
          ),
          ul: ({ children }) => <ul className="ms-4 list-disc space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="ms-4 list-decimal space-y-0.5">{children}</ol>,
          code: ({ children }) => (
            <code className="rounded bg-gray-100 px-1 py-0.5 text-[0.9em] font-medium text-lang-dark">
              {children}
            </code>
          ),
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-lang underline">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
