/**
 * The Topic Lens taxonomy, frontend side (docs/plans/topic-lens.md).
 *
 * Order here IS the display order of topic decks — everyday domains first,
 * abstract ones last. Slugs must match backend/services/topic_taxonomy.py
 * (the backend's test pins that module to the migration; this list only
 * ever renders what the server sends, so an unknown slug simply shows —
 * via the i18n defaultValue — rather than crashing a view).
 *
 * The two hidden buckets (abstract_general, function_words) never reach
 * the client: the summary endpoint excludes them in SQL.
 */

export const TOPIC_ORDER = [
  'food_drink',
  'home_living',
  'family_people',
  'relationships_social',
  'body_health',
  'clothing_appearance',
  'travel_transport',
  'city_places',
  'nature_weather_animals',
  'time_dates',
  'numbers_measure',
  'work_professions',
  'school_learning',
  'sports_leisure',
  'arts_media',
  'technology',
  'communication',
  'shopping_money',
  'emotions_mind',
  'society_politics',
  'religion_culture',
  'science_world',
] as const

const ORDER_INDEX = new Map(TOPIC_ORDER.map((slug, i) => [slug as string, i]))

/** Sort server rows into display order; unknown slugs sink to the end
 *  (a server ahead of this bundle must not scramble the list). */
export function inTopicOrder<T extends { topic: string }>(rows: T[]): T[] {
  return [...rows].sort(
    (a, b) =>
      (ORDER_INDEX.get(a.topic) ?? TOPIC_ORDER.length) -
      (ORDER_INDEX.get(b.topic) ?? TOPIC_ORDER.length),
  )
}
