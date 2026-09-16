import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronRight, Circle, Play } from 'lucide-react'
import { getWritePath, markLesson } from '../../api/write'
import { getAlphabet, getLettersProgress } from '../../api/strokes'
import type { Glyph } from '../../api/strokes'
import LanguageWrapper from '../../components/LanguageWrapper'
import LettersMode, { shapedForm } from './LettersMode'
import WordsMode from './WordsMode'
import { buildPath, lessonDone, nextLesson } from './curriculum'
import type { Lesson } from './curriculum'
import { isProvisionalId } from './strokes/provisional'

/** Word and sentence steps finish after this many clean writes. */
const PASSES_TO_FINISH = 3

/**
 * The learning path (docs/plans/handwriting.md, §13): the script's
 * writing course as a list of lessons, the next one open. Letter lessons
 * finish themselves as their forms become known; drills, words and
 * sentences finish after a few clean writes, or when marked. Nothing is
 * locked — an adult who can already write skips ahead.
 */
export default function PathMode({
  languageId,
  code,
  style,
  glyphs,
  fontFamily,
}: {
  languageId: string
  code: string | undefined
  style: string
  glyphs: Glyph[]
  fontFamily: string
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { data: alphabet } = useQuery({
    queryKey: ['write-alphabet', languageId],
    queryFn: () => getAlphabet(languageId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
  const { data: progress = [] } = useQuery({
    queryKey: ['write-progress', languageId, style],
    queryFn: () => getLettersProgress(languageId, style),
    retry: false,
  })
  const { data: marked = [] } = useQuery({
    queryKey: ['write-path', languageId, style],
    queryFn: () => getWritePath(languageId, style),
    retry: false,
  })
  const mark = useMutation({
    mutationFn: (args: { lessonId: string; done: boolean }) =>
      markLesson({ languageId, style, lessonId: args.lessonId, done: args.done }),
    onSuccess: (done) => queryClient.setQueryData(['write-path', languageId, style], done),
  })

  const lessons = useMemo(() => (alphabet ? buildPath(alphabet, style) : []), [alphabet, style])
  // Which authored forms are known, by key.
  const authoredKnown = useMemo(() => {
    const known = new Set(progress.filter((p) => p.known).map((p) => p.glyph_id))
    const m = new Map<string, boolean>()
    // A bundled (provisional) form cannot be known: nothing records against it.
    for (const g of glyphs) if (!isProvisionalId(g.id)) m.set(`${g.glyph}|${g.form}`, known.has(g.id))
    return m
  }, [progress, glyphs])
  const markedSet = useMemo(() => new Set(marked), [marked])
  const done = (l: Lesson) => lessonDone(l, authoredKnown, markedSet)
  const next = nextLesson(lessons, done)
  const [open, setOpen] = useState<number | null>(null)
  const [passes, setPasses] = useState(0)
  useEffect(() => {
    setPasses(0)
  }, [open])
  const current = open ?? Math.min(next, Math.max(0, lessons.length - 1))
  const lesson = lessons[current]
  const script = alphabet?.script ?? 'latin'

  // A drill, word or sentence step finishes after a few clean writes.
  const onPass = () => {
    if (!lesson || done(lesson)) return
    const n = passes + 1
    setPasses(n)
    if (n >= PASSES_TO_FINISH) mark.mutate({ lessonId: lesson.id, done: true })
  }

  if (!alphabet) return <p className="text-sm text-gray-500">{t('common.loading')}</p>
  if (lessons.length === 0) return null

  const title = (l: Lesson) => {
    const letters = l.group.map((g) => shapedForm(script, g, l.kind === 'capitals' ? 'upper' : 'isolated')).join(' ')
    return t(`write.lesson_${l.kind}`, { letters })
  }
  const doneCount = lessons.filter(done).length

  return (
    <div data-testid="path-mode" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-gray-900">
            {next >= lessons.length
              ? t('write.pathAllDone')
              : t('write.pathProgress', { n: doneCount, total: lessons.length })}
          </p>
          <p className="text-xs text-gray-500">{t('write.pathIntro')}</p>
        </div>
        {next < lessons.length && open !== next && (
          <button
            type="button"
            data-testid="path-continue"
            onClick={() => setOpen(next)}
            className="inline-flex items-center gap-1 rounded-xl bg-lang px-3 py-1.5 text-sm font-bold text-lang-on"
          >
            <Play className="h-4 w-4" aria-hidden /> {t('write.continue')}
          </button>
        )}
      </div>

      {/* The lessons, the open one expanded in place. */}
      <ol className="space-y-1" data-testid="path-lessons">
        {lessons.map((l, i) => {
          const isDone = done(l)
          const isOpen = i === current
          return (
            <li key={l.id}>
              <button
                type="button"
                data-testid={`lesson-${l.id}`}
                data-state={isDone ? 'done' : i === next ? 'next' : 'later'}
                aria-expanded={isOpen}
                onClick={() => setOpen(i)}
                className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-start ${
                  isOpen ? 'border-lang bg-white'
                  : isDone ? 'border-green-100 bg-green-50/60'
                  : i === next ? 'border-gray-300 bg-white'
                  : 'border-gray-100 bg-white/60 text-gray-500'
                }`}
              >
                {isDone ? (
                  <Check className="h-4 w-4 shrink-0 text-green-700" aria-hidden />
                ) : i === next ? (
                  <Play className="h-4 w-4 shrink-0 text-lang" aria-hidden />
                ) : (
                  <Circle className="h-4 w-4 shrink-0 text-gray-300" aria-hidden />
                )}
                <span className="w-6 shrink-0 text-xs text-gray-400">{i + 1}</span>
                <LanguageWrapper languageCode={code ?? 'en'} inline>
                  <span className={`min-w-0 flex-1 text-sm ${isDone ? 'text-gray-700' : 'text-gray-900'}`}>
                    {title(l)}
                  </span>
                </LanguageWrapper>
                {!isOpen && <ChevronRight className="h-4 w-4 shrink-0 text-gray-300" aria-hidden />}
              </button>

              {isOpen && (
                <div className="mt-2 space-y-3 ps-2 border-s-2 border-lang/30" data-testid="lesson-open">
                  {(l.kind === 'letters' || l.kind === 'forms' || l.kind === 'capitals') && (
                    <LettersMode languageId={languageId} code={code} style={style} fontFamily={fontFamily} only={l.forms} />
                  )}
                  {l.kind === 'forms' && l.drills.length > 0 && (
                    <WordsMode
                      languageId={languageId} code={code} style={style} glyphs={glyphs}
                      fontFamily={fontFamily} texts={l.drills} onPass={onPass}
                    />
                  )}
                  {l.kind === 'joins' && (
                    <WordsMode
                      languageId={languageId} code={code} style={style} glyphs={glyphs}
                      fontFamily={fontFamily} texts={l.drills} onPass={onPass}
                    />
                  )}
                  {(l.kind === 'words' || l.kind === 'sentences') && (
                    <WordsMode
                      languageId={languageId} code={code} style={style} glyphs={glyphs}
                      fontFamily={fontFamily} letters={l.letters}
                      initialSource={l.kind === 'words' ? 'word' : 'sentence'} onPass={onPass}
                    />
                  )}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    {isDone ? (
                      <button
                        type="button"
                        onClick={() => mark.mutate({ lessonId: l.id, done: false })}
                        className="text-xs text-gray-500 hover:underline"
                      >
                        {t('write.markUndone')}
                      </button>
                    ) : (
                      <button
                        type="button"
                        data-testid="lesson-mark-done"
                        onClick={() => mark.mutate({ lessonId: l.id, done: true })}
                        className="text-xs text-lang hover:underline"
                      >
                        {t('write.markDone')}
                      </button>
                    )}
                    {i + 1 < lessons.length && (
                      <button
                        type="button"
                        data-testid="lesson-next"
                        onClick={() => setOpen(i + 1)}
                        className="inline-flex items-center gap-1 rounded-xl border border-lang px-3 py-1.5 text-sm font-semibold text-lang"
                      >
                        {t('write.lessonNext')} <ChevronRight className="h-4 w-4" aria-hidden />
                      </button>
                    )}
                  </div>
                </div>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
