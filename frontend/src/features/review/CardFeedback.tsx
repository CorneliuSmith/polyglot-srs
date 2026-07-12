import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { submitCardFeedback } from '../../api/review'

/**
 * Lets a learner flag a problem with the card they just answered. Collapsed by
 * default; the feedback is routed to contributors for that language.
 */
export default function CardFeedback({ cardId }: { cardId: string }) {
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')

  const mutation = useMutation({
    mutationFn: () => submitCardFeedback(cardId, message.trim()),
  })

  if (mutation.isSuccess) {
    return <p className="text-xs text-gray-400">Thanks — your feedback was sent.</p>
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs text-gray-400 hover:text-gray-600 hover:underline"
      >
        Report an issue with this card
      </button>
    )
  }

  return (
    <div className="space-y-1">
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={2}
        placeholder="What looks wrong? (e.g. the answer or translation seems off)"
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang"
      />
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={!message.trim() || mutation.isPending}
          className="bg-gray-700 hover:bg-gray-800 disabled:opacity-50 text-white rounded-lg px-3 py-1.5 text-xs"
        >
          {mutation.isPending ? 'Sending…' : 'Send feedback'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-gray-400 hover:underline"
        >
          Cancel
        </button>
        {mutation.isError && <span className="text-xs text-red-500">Could not send.</span>}
      </div>
    </div>
  )
}
