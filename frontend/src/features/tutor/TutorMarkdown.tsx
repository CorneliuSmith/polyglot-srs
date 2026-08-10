import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Markdown for tutor turns. The tutor writes real Markdown — comparison
 * tables above all (catalán vs español pronouns was the owner's example),
 * plus bold and lists — and the chat was rendering the raw pipes and
 * asterisks as plain text.
 *
 * GFM is required for tables. Styling is inline (no typography plugin):
 * tight sizes to sit inside a chat bubble, horizontal scroll for wide
 * tables on phones, and dir=auto on the wrapper since tutor turns mix the
 * UI language with RTL practice text.
 */
export default function TutorMarkdown({ content }: { content: string }) {
  return (
    <div dir="auto" className="tutor-markdown space-y-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => (
            <p className="whitespace-pre-wrap">{children}</p>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="my-1 border-collapse text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-gray-200 bg-gray-50 px-2.5 py-1.5 text-start font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-gray-200 px-2.5 py-1.5">{children}</td>
          ),
          ul: ({ children }) => (
            <ul className="ms-4 list-disc space-y-0.5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="ms-4 list-decimal space-y-0.5">{children}</ol>
          ),
          code: ({ children }) => (
            <code className="rounded bg-gray-100 px-1 py-0.5 text-[0.9em]">
              {children}
            </code>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-lang underline"
            >
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
