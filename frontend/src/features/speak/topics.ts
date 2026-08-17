/**
 * Conversation starters for Speak (owner: "add a bunch more default
 * questions for speech").
 *
 * The topic box was one placeholder and a blinking cursor, which is the
 * hardest thing to answer in any language: a learner who opens Speak has
 * already decided to practise and then has to invent a scenario before the
 * practice can start. Eighteen taps remove that step.
 *
 * They are grouped by what the conversation DEMANDS rather than by CEFR
 * level, because the level of a scenario is set by how you handle it —
 * ordering a coffee can be four words or a complaint about the order — and
 * a hard label ("B2 only") would put people off the thing they can already
 * do. Everyday asks for transactions, practical for problems, opinion for
 * argument.
 *
 * Ids are permanent: the copy lives in the i18n catalogs under
 * `speak.topics.<id>`, so a starter reads naturally in the learner's own
 * language before it becomes a prompt about it.
 */

export type SpeakTopicGroup = 'everyday' | 'practical' | 'opinion'

export interface SpeakTopicGroupSpec {
  group: SpeakTopicGroup
  ids: string[]
}

export const SPEAK_TOPICS: SpeakTopicGroupSpec[] = [
  {
    group: 'everyday',
    ids: [
      'coffee',
      'directions',
      'introductions',
      'clothes',
      'weekend',
      'neighbour',
    ],
  },
  {
    group: 'practical',
    ids: [
      'doctor',
      'flat',
      'hotel',
      'missedTrain',
      'interview',
      'returnItem',
    ],
  },
  {
    group: 'opinion',
    ids: [
      'film',
      'changedMind',
      'cityBestWorst',
      'explainJob',
      'habit',
      'disagree',
    ],
  },
]
