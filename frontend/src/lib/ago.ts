/** "4 min ago" — a timestamp alone doesn't answer "is it alive right now",
 * which is the only reason anyone reads a "last ran" line. Same rule as
 * TranslationStatusPanel's private copy; shared here because the content
 * health panel, its drill-down and the Deployment panel's Content section
 * all read the same nightly clock. */
export function ago(iso: string | null | undefined): string {
  if (!iso) return 'never'
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (!Number.isFinite(secs)) return 'never'
  if (secs < 90) return 'just now'
  const mins = Math.round(secs / 60)
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 48) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}
