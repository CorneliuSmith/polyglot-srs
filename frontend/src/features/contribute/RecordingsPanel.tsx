import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getMyRecordings,
  getRecordingAudio,
  getRecordingsQueue,
  reviewRecording,
  submitRecording,
  type RecordingRow,
} from '../../api/contribute'
import { useRecorder, recordingSupported } from '../speak/useRecorder'

/**
 * Human audio for languages with no neural voice (owner: Jamaican Patois —
 * "build in some contributor functionality to provide recordings").
 *
 * A contributor records one clip for one exact text — the word or sentence
 * as it appears on the card — and it queues for review. Once a reviewer
 * approves it, the audio endpoint serves the clip everywhere that text
 * plays, exactly where TTS would have been.
 */

// MediaRecorder reports e.g. 'audio/webm;codecs=opus' — the backend wants
// the bare container type.
function bareMime(blobType: string): string {
  const bare = blobType.split(';')[0].trim()
  return bare || 'audio/webm'
}

async function blobToBase64(blob: Blob): Promise<string> {
  const buf = await blob.arrayBuffer()
  let binary = ''
  const bytes = new Uint8Array(buf)
  const CHUNK = 0x8000
  for (let i = 0; i < bytes.length; i += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK))
  }
  return btoa(binary)
}

function StatusChip({ status }: { status: RecordingRow['status'] }) {
  const tone =
    status === 'approved'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : status === 'rejected'
        ? 'bg-red-50 text-red-600 border-red-200'
        : 'bg-amber-50 text-amber-700 border-amber-200'
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${tone}`}>
      {status}
    </span>
  )
}

export default function RecordingsPanel({
  languageId,
  languageName,
}: {
  languageId: string
  languageName?: string
}) {
  const queryClient = useQueryClient()
  const [text, setText] = useState('')
  const [clip, setClip] = useState<{ blob: Blob; url: string } | null>(null)
  const recorder = useRecorder()
  const fileInput = useRef<HTMLInputElement>(null)

  const { data: mine = [] } = useQuery({
    queryKey: ['my-recordings', languageId],
    queryFn: () => getMyRecordings(languageId),
    retry: false,
  })

  const submit = useMutation({
    mutationFn: async () => {
      const b64 = await blobToBase64(clip!.blob)
      await submitRecording(languageId, text.trim(), b64, bareMime(clip!.blob.type))
    },
    onSuccess: () => {
      setText('')
      setClip(null)
      queryClient.invalidateQueries({ queryKey: ['my-recordings', languageId] })
    },
  })

  const takeClip = (blob: Blob) =>
    setClip({ blob, url: URL.createObjectURL(blob) })

  const toggleRecord = async () => {
    if (recorder.recording) {
      const rec = await recorder.stop()
      if (rec) takeClip(rec.blob)
    } else {
      setClip(null)
      await recorder.start()
    }
  }

  const canSubmit = !!clip && text.trim().length > 0 && !submit.isPending

  return (
    <section
      data-testid="recordings-panel"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
    >
      <div>
        <h2 className="font-semibold text-gray-800">Recordings</h2>
        <p className="text-xs text-gray-500">
          {languageName ?? 'This language'} has no synthetic voice, so audio
          comes from speakers — you. Type the exact word or sentence as it
          appears on the card, record it (or attach a file), and a reviewer
          will approve it. Approved clips play for every learner wherever
          that text appears.
        </p>
      </div>

      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={300}
        placeholder="The exact word or sentence, e.g. “Wah gwaan?”"
        className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm"
        dir="auto"
      />

      <div className="flex flex-wrap items-center gap-2">
        {recordingSupported() && (
          <button
            type="button"
            onClick={() => void toggleRecord()}
            className={`rounded-xl px-4 py-2 text-sm font-semibold border ${
              recorder.recording
                ? 'bg-red-600 border-red-600 text-white'
                : 'border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {recorder.recording ? 'Stop' : 'Record'}
          </button>
        )}
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          className="rounded-xl border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Attach audio file
        </button>
        <input
          ref={fileInput}
          type="file"
          accept="audio/*"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) takeClip(f)
            e.target.value = ''
          }}
        />
        {clip && (
          // eslint-disable-next-line jsx-a11y/media-has-caption -- a pronunciation clip IS the content
          <audio controls src={clip.url} className="h-9" data-testid="recording-preview" />
        )}
        <button
          type="button"
          onClick={() => submit.mutate()}
          disabled={!canSubmit}
          className="rounded-xl bg-lang px-4 py-2 text-sm font-semibold text-lang-on disabled:opacity-40"
        >
          {submit.isPending ? 'Submitting…' : 'Submit for review'}
        </button>
      </div>
      {recorder.error && (
        <p className="text-xs text-red-600">
          {recorder.error === 'denied'
            ? 'The microphone was blocked — allow it in your browser, or attach a file.'
            : 'The microphone didn’t work — attach a file instead.'}
        </p>
      )}
      {submit.isError && (
        <p className="text-sm text-red-600">That didn’t submit — try again.</p>
      )}

      {mine.length > 0 && (
        <div className="space-y-1 pt-1">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            Your submissions
          </h3>
          {mine.map((r) => (
            <div
              key={r.id}
              className="flex items-center gap-2 border-t border-gray-100 py-1.5 text-sm"
            >
              <span className="min-w-0 flex-1 truncate text-gray-800" dir="auto">
                {r.text}
              </span>
              <StatusChip status={r.status} />
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

/** The reviewer's queue: listen to each pending clip, approve or reject.
 *  Approval is immediate — the clip starts playing for learners. */
export function RecordingsReviewQueue({ languageId }: { languageId: string }) {
  const queryClient = useQueryClient()
  const [playing, setPlaying] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const { data: pending = [] } = useQuery({
    queryKey: ['recordings-queue', languageId],
    queryFn: () => getRecordingsQueue(languageId),
    retry: false,
  })

  const play = async (id: string) => {
    const { audio_b64, mime } = await getRecordingAudio(id)
    const bytes = Uint8Array.from(atob(audio_b64), (c) => c.charCodeAt(0))
    const url = URL.createObjectURL(new Blob([bytes], { type: mime }))
    audioRef.current?.pause()
    const el = new Audio(url)
    audioRef.current = el
    setPlaying(id)
    el.onended = () => setPlaying(null)
    void el.play().catch(() => setPlaying(null))
  }

  const verdict = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      reviewRecording(id, approve),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['recordings-queue', languageId] }),
  })

  if (pending.length === 0) return null

  return (
    <section
      data-testid="recordings-queue"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-2"
    >
      <div>
        <h2 className="font-semibold text-gray-800">
          Recordings awaiting review
        </h2>
        <p className="text-xs text-gray-500">
          Listen before approving — an approved clip plays for every learner
          wherever this text appears.
        </p>
      </div>
      {pending.map((r) => (
        <div
          key={r.id}
          className="flex flex-wrap items-center gap-2 border-t border-gray-100 py-2 text-sm"
        >
          <span className="min-w-0 flex-1 truncate text-gray-800" dir="auto">
            {r.text}
          </span>
          {r.contributor_email && (
            <span className="text-xs text-gray-400">{r.contributor_email}</span>
          )}
          <button
            type="button"
            onClick={() => void play(r.id)}
            className="rounded-lg border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
          >
            {playing === r.id ? 'Playing…' : 'Play'}
          </button>
          <button
            type="button"
            onClick={() => verdict.mutate({ id: r.id, approve: true })}
            disabled={verdict.isPending}
            className="rounded-lg bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white disabled:opacity-40"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => verdict.mutate({ id: r.id, approve: false })}
            disabled={verdict.isPending}
            className="rounded-lg border border-red-200 px-2.5 py-1 text-xs font-medium text-red-600 disabled:opacity-40"
          >
            Reject
          </button>
        </div>
      ))}
    </section>
  )
}
