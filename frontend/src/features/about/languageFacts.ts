/**
 * "Things to know about this language" — a brief-but-comprehensive per-language
 * reference: where it sits in the world's language families, who speaks it and
 * where, how its sentences are built (word order), a short history, and the
 * handful of features that make it genuinely distinctive. Written for a curious
 * learner, not a linguist — every entry is meant to be read in a minute.
 *
 * Rendered by LanguageAboutPage in the same card style as Letters & Sounds.
 * Codes mirror the LETTERS map so the two references cover the same languages.
 */

export interface LanguageFacts {
  /** One-line hook shown under the title. */
  tagline: string
  /** Family › branch, e.g. "Indo-European › Romance". */
  family: string
  /** Rough speaker count (native, unless noted). */
  speakers: string
  /** Where it's spoken — regions/countries. */
  whereSpoken: string
  /** Script + any direction/spacing note. */
  writingSystem: string
  /** Basic word order, plus how rigid it is. */
  wordOrder: string
  /** Two or three sentences on where it came from. */
  history: string
  /** The distinctive features a learner will actually notice. */
  unique: string[]
}

const es: LanguageFacts = {
  tagline: 'A Romance language of remarkable reach and honest spelling.',
  family: 'Indo-European › Italic › Romance (Ibero-Romance)',
  speakers: '~485 million native — second only to Mandarin.',
  whereSpoken: 'Spain, almost all of Latin America, Equatorial Guinea, and widely across the United States.',
  writingSystem: 'Latin alphabet, plus ñ and the marks á é í ó ú ü. Written left to right.',
  wordOrder: 'Subject–Verb–Object, but flexible — endings carry so much that the subject is usually dropped.',
  history:
    'Grew out of the spoken Latin of Roman Hispania, taking shape as Castilian in the medieval kingdoms of northern Spain. The empire then carried it across the Atlantic, where most of its speakers now live.',
  unique: [
    'Verbs do the heavy lifting: one word can mark person, tense, and mood, so pronouns are usually left out.',
    'Every noun is masculine or feminine, and adjectives agree with it.',
    'Two verbs for "to be" — ser (permanent) vs. estar (temporary or location).',
    'Inverted ¿ and ¡ open questions and exclamations.',
  ],
}

const fr: LanguageFacts = {
  tagline: 'A Romance language where much is written but not said.',
  family: 'Indo-European › Italic › Romance (Gallo-Romance)',
  speakers: '~80 million native, ~300 million total across five continents.',
  whereSpoken: 'France, Belgium, Switzerland, Québec, and much of West and Central Africa.',
  writingSystem: 'Latin alphabet with accents (é è ê ë), the cedilla (ç), and ligatures (œ). Left to right.',
  wordOrder: 'Subject–Verb–Object, fairly rigid — the subject pronoun stays put.',
  history:
    'Descended from the Vulgar Latin of Gaul, emerging as the langue d’oïl of the north. Centuries of court prestige and the Académie française shaped the tidy standard used today.',
  unique: [
    'Many final letters are silent — but reappear as liaisons before a vowel.',
    'Nasal vowels (on, an, in) have no direct English equivalent.',
    'Nouns carry gender, and articles/adjectives agree.',
    'Formal vous vs. familiar tu marks the social register of every "you".',
  ],
}

const de: LanguageFacts = {
  tagline: 'A Germanic language that saves the verb for last.',
  family: 'Indo-European › Germanic (West Germanic)',
  speakers: '~95 million native — the most-spoken first language in the EU.',
  whereSpoken: 'Germany, Austria, Switzerland, Liechtenstein, and pockets of Belgium, Italy, and beyond.',
  writingSystem: 'Latin alphabet plus ä ö ü and ß. Nouns are always capitalised. Left to right.',
  wordOrder: 'Verb-second in main clauses, verb-final in subordinate ones — the famous "verb at the end".',
  history:
    'Emerged from West Germanic dialects reshaped by the High German consonant shift. Luther’s Bible translation did much to forge a single written standard.',
  unique: [
    'Four cases (nominative, accusative, dative, genitive) change articles and endings.',
    'Three genders — and der/die/das rarely follow meaning.',
    'Words stack into long compounds (Handschuh = hand-shoe = glove).',
    'Separable verbs split apart: "ich stehe früh auf" (I get up early).',
  ],
}

const it: LanguageFacts = {
  tagline: 'The Romance language closest to its Latin parent.',
  family: 'Indo-European › Italic › Romance (Italo-Dalmatian)',
  speakers: '~65 million native.',
  whereSpoken: 'Italy, San Marino, Vatican City, and Swiss Ticino.',
  writingSystem: 'Latin alphabet with grave/acute accents (à, é). Left to right.',
  wordOrder: 'Subject–Verb–Object, flexible — the subject is often dropped.',
  history:
    'Standard Italian grew from the Tuscan of Florence, elevated by Dante, Petrarch, and Boccaccio, and only became a shared spoken language nationwide after unification in the 1860s.',
  unique: [
    'Double consonants are pronounced long and can change meaning (pala vs. palla).',
    'Grammatically the most conservative major Romance language — very close to Latin.',
    'Nouns and adjectives agree in gender and number.',
    'Rich, musical intonation and clear open vowels.',
  ],
}

const ca: LanguageFacts = {
  tagline: 'A Romance language bridging Spain and France.',
  family: 'Indo-European › Italic › Romance (Occitano-Romance)',
  speakers: '~9 million native.',
  whereSpoken: 'Catalonia, Valencia, the Balearic Islands, Andorra (where it is the sole official language), and Alghero in Sardinia.',
  writingSystem: 'Latin alphabet with the middot (l·l) and accents. Left to right.',
  wordOrder: 'Subject–Verb–Object, flexible with pro-drop.',
  history:
    'Formed from Vulgar Latin and flourished as a medieval literary and legal language. Suppressed under Franco, it was revived and is now central to Catalan identity.',
  unique: [
    'Sits between Spanish and French — familiar to both, identical to neither.',
    'Weak object pronouns (em, et, es, hi, en) attach around the verb.',
    'Distinctive neutral vowel (schwa) in eastern dialects.',
    'A full literary and official language, not a dialect of Spanish.',
  ],
}

const pt: LanguageFacts = {
  tagline: 'A Romance language of the Atlantic world.',
  family: 'Indo-European › Italic › Romance (Ibero-Romance)',
  speakers: '~230 million native — most of them in Brazil.',
  whereSpoken: 'Brazil, Portugal, Angola, Mozambique, Cape Verde, and other former maritime colonies.',
  writingSystem: 'Latin alphabet with ã õ, ç, and accents. Left to right.',
  wordOrder: 'Subject–Verb–Object, flexible with pro-drop.',
  history:
    'Grew from Galician-Portuguese in the northwest of the Iberian Peninsula and spread worldwide on Portugal’s sea routes, splitting into distinct European and Brazilian standards.',
  unique: [
    'Nasal vowels and diphthongs (pão, mãe, coração).',
    'A personal infinitive — the infinitive can take endings for each person.',
    'A living future subjunctive, lost in most Romance languages.',
    'European and Brazilian varieties differ noticeably in sound and rhythm.',
  ],
}

const ro: LanguageFacts = {
  tagline: 'The Romance language of the East, shaped by its neighbours.',
  family: 'Indo-European › Italic › Romance (Eastern Romance)',
  speakers: '~24 million native.',
  whereSpoken: 'Romania and Moldova.',
  writingSystem: 'Latin alphabet with ă, â, î, ș, ț. Left to right.',
  wordOrder: 'Subject–Verb–Object, flexible thanks to case marking.',
  history:
    'Descends from the Latin of Roman Dacia and evolved for centuries cut off from the rest of the Romance world, deeply marked by Slavic and other Balkan neighbours.',
  unique: [
    'The only major Romance language that kept grammatical cases.',
    'The definite article attaches to the end of the noun: lup → lupul (the wolf).',
    'Retained a neuter gender alongside masculine and feminine.',
    'Shares Balkan features (like the postposed article) with unrelated neighbours.',
  ],
}

const tr: LanguageFacts = {
  tagline: 'A Turkic language built by stacking suffixes.',
  family: 'Turkic › Oghuz',
  speakers: '~80 million native.',
  whereSpoken: 'Turkey and Cyprus, with large communities across Europe.',
  writingSystem: 'A tailored Latin alphabet (adopted 1928) with ç, ğ, ı, ö, ş, ü. Left to right.',
  wordOrder: 'Subject–Object–Verb — the verb comes last.',
  history:
    'An Oghuz Turkic language carried west from Central Asia. Ottoman Turkish was written in Arabic script and steeped in Persian and Arabic; Atatürk’s 1920s reforms Latinised and "purified" it.',
  unique: [
    'Agglutinative: whole sentences can be built from one root plus a chain of suffixes.',
    'Vowel harmony — suffix vowels shift to match the word’s vowels.',
    'No grammatical gender and no definite article.',
    'A dedicated evidential form (-miş) marks hearsay or inference.',
  ],
}

const sw: LanguageFacts = {
  tagline: 'East Africa’s great connector, Bantu at heart.',
  family: 'Niger-Congo › Atlantic-Congo › Bantu',
  speakers: '~5 million native, but 80+ million as a shared second language.',
  whereSpoken: 'Tanzania, Kenya, Uganda, the DRC, and across the African Great Lakes.',
  writingSystem: 'Latin alphabet (historically also Arabic script). Left to right.',
  wordOrder: 'Subject–Verb–Object.',
  history:
    'A Bantu language of the East African coast, shaped by a thousand years of Indian Ocean trade — hence its many Arabic loanwords — and later spread inland as a lingua franca.',
  unique: [
    'Nouns fall into ~15 classes; the class drives agreement across the whole sentence.',
    'Verbs agglutinate subject, tense, object, and more into one word.',
    'Unusually for a Bantu language, it is not tonal.',
    'A rich layer of Arabic vocabulary (safari, kitabu, asante) sits on the Bantu base.',
  ],
}

const yo: LanguageFacts = {
  tagline: 'A West African language where pitch carries meaning.',
  family: 'Niger-Congo › Atlantic-Congo › Volta-Niger',
  speakers: '~45 million.',
  whereSpoken: 'Southwestern Nigeria, Benin, and Togo — plus a deep diaspora in the Americas.',
  writingSystem: 'Latin alphabet with sub-dots (ẹ, ọ, ṣ) and tone marks. Left to right.',
  wordOrder: 'Subject–Verb–Object.',
  history:
    'The language of the Ifẹ̀ and Ọ̀yọ́ civilisations, carried across the Atlantic during the slave trade and preserved in Cuban and Brazilian religious traditions.',
  unique: [
    'Three tones (high, mid, low) distinguish otherwise identical words.',
    'Serial verb constructions string several verbs together in one clause.',
    'Sub-dotted letters mark distinct vowels and consonants.',
    'A rich tradition of proverbs woven into everyday speech.',
  ],
}

const ha: LanguageFacts = {
  tagline: 'A Chadic tongue and the Sahel’s trade language.',
  family: 'Afro-Asiatic › Chadic',
  speakers: '~50+ million, and a lingua franca for many more.',
  whereSpoken: 'Northern Nigeria and Niger, and across West Africa and the Sahel.',
  writingSystem: 'Latin (Boko) alphabet with hooked letters (ɓ, ɗ, ƙ); also written in Arabic script (Ajami). Left to right.',
  wordOrder: 'Subject–Verb–Object.',
  history:
    'A Chadic language — a distant cousin of Arabic and Hebrew — spread far beyond its homeland by centuries of trans-Saharan trade and Islamic scholarship.',
  unique: [
    'Two tones plus vowel length shape the meaning of words.',
    'Glottalised "hooked" consonants ɓ, ɗ, ƙ.',
    'Grammatical gender appears in the singular but disappears in the plural.',
    'A system of verb "grades" encodes direction and completion.',
  ],
}

const xh: LanguageFacts = {
  tagline: 'A Nguni language famous for its clicks.',
  family: 'Niger-Congo › Atlantic-Congo › Bantu (Nguni)',
  speakers: '~8 million native.',
  whereSpoken: 'South Africa, especially the Eastern Cape — one of its 11 official languages.',
  writingSystem: 'Latin alphabet; the letters c, x, q spell three different clicks. Left to right.',
  wordOrder: 'Subject–Verb–Object.',
  history:
    'A Bantu language of the Nguni group, closely related to Zulu. Contact with Khoisan peoples gave it the click consonants that make it instantly recognisable.',
  unique: [
    'Three click consonants — dental (c), lateral (x), and palatal (q) — borrowed from Khoisan.',
    'A noun-class system that threads agreement through the sentence.',
    'It is tonal, though tone is not written.',
    'Concord prefixes link every word back to the noun class.',
  ],
}

const mi: LanguageFacts = {
  tagline: 'The Polynesian language of Aotearoa, verb-first.',
  family: 'Austronesian › Malayo-Polynesian › Polynesian',
  speakers: '~150,000–190,000, and steadily reviving.',
  whereSpoken: 'New Zealand (Aotearoa).',
  writingSystem: 'Latin alphabet; macrons (ā, ē, ī, ō, ū) mark long vowels. Left to right.',
  wordOrder: 'Verb–Subject–Object — the verb comes first.',
  history:
    'An Eastern Polynesian language brought to New Zealand around the 1300s. Pushed to the brink in the 20th century, it has been revitalised through kōhanga reo (language nests) and immersion schooling.',
  unique: [
    'Verb-first (VSO) sentences, unusual among the languages here.',
    'A small sound system: ten consonants and five vowels (short and long).',
    'Small particles, not endings, mark tense and role.',
    'Macrons distinguish words — keke (cake) vs. kēkē (armpit).',
  ],
}

const jam: LanguageFacts = {
  tagline: 'An English-lexicon creole with West African grammar.',
  family: 'English-based creole (Atlantic)',
  speakers: '~3 million, plus a large diaspora.',
  whereSpoken: 'Jamaica and Jamaican communities worldwide.',
  writingSystem: 'Latin alphabet — written both in an English-based spelling and the phonetic Cassidy/JLU system. Left to right.',
  wordOrder: 'Subject–Verb–Object.',
  history:
    'Born on colonial-era plantations, where enslaved West Africans built a new language from an English vocabulary and the grammar of Akan, Igbo, and other tongues.',
  unique: [
    'Verbs don’t conjugate — tense comes from particles (mi did go, mi a go).',
    'Distinct pronouns: mi, yu, im, wi, unu, dem.',
    'Reduplication intensifies (chaka-chaka = messy).',
    'English words, but a grammar all its own.',
  ],
}

const en: LanguageFacts = {
  tagline: 'A Germanic language that borrowed from everyone.',
  family: 'Indo-European › Germanic (West Germanic)',
  speakers: '~380 million native, ~1.5 billion total — the world’s lingua franca.',
  whereSpoken: 'The UK, Ireland, North America, Australia, New Zealand, and as a second language almost everywhere.',
  writingSystem: 'Latin alphabet, 26 letters, no diacritics. Left to right.',
  wordOrder: 'Subject–Verb–Object, quite rigid — word order does the work cases used to.',
  history:
    'Began as Anglo-Saxon (Old English), was reshaped by Norse settlers and then a flood of Norman French after 1066, and spread globally through the British Empire and American influence.',
  unique: [
    'A huge vocabulary — a Germanic core layered with Latin, French, and Greek.',
    'Very little inflection: nouns barely change, and there is no grammatical gender.',
    'Notoriously irregular spelling, a fossil of older pronunciations.',
    'Phrasal verbs (give up, put off, run into) carry idiomatic meaning.',
  ],
}

const nl: LanguageFacts = {
  tagline: 'The West Germanic language between English and German.',
  family: 'Indo-European › Germanic (West Germanic)',
  speakers: '~25 million native.',
  whereSpoken: 'The Netherlands, Belgium (Flanders), Suriname, and the Dutch Caribbean.',
  writingSystem: 'Latin alphabet; the digraph "ij" behaves like a single letter. Left to right.',
  wordOrder: 'Verb-second in main clauses, verb-final in subordinate ones — like German.',
  history:
    'A Low Franconian language that never underwent German’s consonant shift, leaving it grammatically and lexically poised between English and German.',
  unique: [
    'Verb-second word order sends verbs to the end of subordinate clauses.',
    'Two genders — common (de) and neuter (het).',
    'A famously guttural "g".',
    'Diminutives in -je are everywhere and soften the tone.',
  ],
}

const ru: LanguageFacts = {
  tagline: 'A Slavic language of cases and verbal aspect.',
  family: 'Indo-European › Balto-Slavic › East Slavic',
  speakers: '~150 million native, and widely spoken as a second language.',
  whereSpoken: 'Russia and much of the former Soviet Union.',
  writingSystem: 'Cyrillic alphabet, adapted from Greek. Left to right.',
  wordOrder: 'Subject–Verb–Object officially, but word order is very free — cases show who does what.',
  history:
    'An East Slavic language written in Cyrillic since the Christianisation of the Rus, heavily shaped by Old Church Slavonic and standardised on the Moscow dialect.',
  unique: [
    'Six cases reshape nouns, adjectives, and pronouns.',
    'Every verb comes as an aspect pair — imperfective (process) vs. perfective (result).',
    'No words for "a" or "the".',
    'A hard/soft consonant distinction (palatalisation) runs through the sound system.',
  ],
}

const el: LanguageFacts = {
  tagline: 'A language 3,400 years deep, on its own branch.',
  family: 'Indo-European › Hellenic (its own branch)',
  speakers: '~13 million native.',
  whereSpoken: 'Greece and Cyprus.',
  writingSystem: 'The Greek alphabet — ancestor of both Latin and Cyrillic. Left to right.',
  wordOrder: 'Subject–Verb–Object, flexible thanks to case endings.',
  history:
    'The oldest recorded Indo-European language still spoken, with a continuous written record from Mycenaean Greek through Ancient and Koine Greek to today.',
  unique: [
    'Its own alphabet, from which Latin and Cyrillic descend.',
    'Four cases and three genders.',
    'A single Greek root underlies a huge share of scientific vocabulary.',
    'Modern stress accent replaced the ancient pitch accent.',
  ],
}

const ar: LanguageFacts = {
  tagline: 'A Semitic language built from three-letter roots.',
  family: 'Afro-Asiatic › Semitic',
  speakers: '~310 million native across its many varieties.',
  whereSpoken: 'The Middle East and North Africa, and liturgically across the Muslim world.',
  writingSystem: 'The Arabic script, written right to left and joined cursively.',
  wordOrder: 'Verb–Subject–Object in the classical language; many dialects prefer Subject–Verb–Object.',
  history:
    'A Semitic language whose classical form was fixed by the Qur’an. Today a formal standard (MSA) is shared across the region while everyone speaks a local dialect — a situation called diglossia.',
  unique: [
    'Words are built from three-consonant roots: k-t-b gives kitāb (book), kātib (writer), maktab (office).',
    'Written right to left, with letters that change shape by position.',
    'A dual number, distinct from singular and plural.',
    'Emphatic and pharyngeal consonants with no English equivalents.',
  ],
}

const hi: LanguageFacts = {
  tagline: 'An Indo-Aryan language that puts the verb last.',
  family: 'Indo-European › Indo-Iranian › Indo-Aryan',
  speakers: '~340 million native (nearly identical spoken form to Urdu).',
  whereSpoken: 'Northern and central India.',
  writingSystem: 'The Devanagari abugida — each consonant carries an inherent vowel. Left to right.',
  wordOrder: 'Subject–Object–Verb.',
  history:
    'Descended from Sanskrit through the Prakrits, it absorbed Persian and Arabic vocabulary under the Mughals — the shared spoken register with Urdu is often called Hindustani.',
  unique: [
    'Postpositions instead of prepositions (English "to the house" → "house-to").',
    'Split ergativity: the marker ne appears on the subject in past-tense transitives.',
    'Verbs agree in gender, so sentences shift with who is speaking or acting.',
    'Three levels of "you" (tū, tum, āp) tune the politeness.',
  ],
}

const th: LanguageFacts = {
  tagline: 'A tonal, isolating language written without spaces.',
  family: 'Kra-Dai › Tai',
  speakers: '~60 million native.',
  whereSpoken: 'Thailand.',
  writingSystem: 'The Thai abugida — an alphabet with tone marks and no spaces between words. Left to right.',
  wordOrder: 'Subject–Verb–Object.',
  history:
    'A Tai language whose speakers migrated south from what is now southern China, layering in Pali, Sanskrit, and Khmer vocabulary; its script descends from Khmer.',
  unique: [
    'Five tones — the same syllable means five different things.',
    'Isolating: words never change form; grammar rides on word order and particles.',
    'Counting requires a classifier for the kind of thing being counted.',
    'Polite particles (khráp for men, khâ for women) end sentences.',
  ],
}

const ko: LanguageFacts = {
  tagline: 'A language isolate with a scientifically designed alphabet.',
  family: 'Koreanic (a language isolate)',
  speakers: '~80 million native.',
  whereSpoken: 'South and North Korea, and a wide diaspora.',
  writingSystem: 'Hangul — a featural alphabet whose letters group into syllable blocks. Left to right.',
  wordOrder: 'Subject–Object–Verb.',
  history:
    'Korean stands alone, with no proven relatives. Long written in Chinese characters, it gained Hangul — commissioned by King Sejong in 1443 — a script deliberately designed to be easy to learn.',
  unique: [
    'Hangul letters are shaped to reflect how the mouth makes each sound.',
    'Elaborate honorific and speech levels reshape verbs by social context.',
    'Agglutinative: particles and endings attach to mark role and nuance.',
    'A topic marker (은/는) highlights what the sentence is about.',
  ],
}

export const LANGUAGE_FACTS: Record<string, LanguageFacts> = {
  es, fr, de, it, ca, pt, ro, tr, sw, yo, ha, xh, mi, jam, en, nl, ru, el, ar, hi, th, ko,
}

export function factsFor(code: string | undefined | null): LanguageFacts | null {
  return (code && LANGUAGE_FACTS[code]) || null
}

/**
 * A single interlinear example: the sentence, a word-by-word gloss, and a
 * natural translation — so a learner can SEE how the word order actually works,
 * not just read that it's "SOV". `note` calls out what the example demonstrates
 * (verb position, a case ending, a fused verb…). `rtl` renders the words
 * right-to-left (Arabic).
 */
export interface GlossedWord {
  /** The word as written in the language. */
  w: string
  /** Its word-by-word gloss (kept short). */
  g: string
}

export interface SyntaxExample {
  sentence: string
  words: GlossedWord[]
  translation: string
  note?: string
  rtl?: boolean
}

/** Glossed examples per language, chosen to show its characteristic word order
 * and a couple of distinctive constructions. Rendered under "How sentences are
 * built" on the About page. */
export const LANGUAGE_SYNTAX: Record<string, SyntaxExample[]> = {
  es: [
    {
      sentence: 'El niño come una manzana.',
      words: [
        { w: 'El', g: 'the' }, { w: 'niño', g: 'boy' }, { w: 'come', g: 'eats' },
        { w: 'una', g: 'a' }, { w: 'manzana', g: 'apple' },
      ],
      translation: 'The boy eats an apple.',
      note: 'Subject–Verb–Object; the article agrees with the noun.',
    },
    {
      sentence: '¿Hablas español?',
      words: [{ w: '¿Hablas', g: '(you)-speak' }, { w: 'español?', g: 'Spanish' }],
      translation: 'Do you speak Spanish?',
      note: "No word for 'you' — the ending -as already means it (pro-drop).",
    },
  ],
  fr: [
    {
      sentence: 'Le garçon mange une pomme.',
      words: [
        { w: 'Le', g: 'the' }, { w: 'garçon', g: 'boy' }, { w: 'mange', g: 'eats' },
        { w: 'une', g: 'a' }, { w: 'pomme', g: 'apple' },
      ],
      translation: 'The boy eats an apple.',
    },
    {
      sentence: 'Je ne mange pas de viande.',
      words: [
        { w: 'Je', g: 'I' }, { w: 'ne', g: '(not)' }, { w: 'mange', g: 'eat' },
        { w: 'pas', g: '(not)' }, { w: 'de', g: 'any' }, { w: 'viande', g: 'meat' },
      ],
      translation: "I don't eat meat.",
      note: 'Negation wraps the verb in two pieces: ne … pas.',
    },
  ],
  de: [
    {
      sentence: 'Heute esse ich einen Apfel.',
      words: [
        { w: 'Heute', g: 'today' }, { w: 'esse', g: 'eat' }, { w: 'ich', g: 'I' },
        { w: 'einen', g: 'an' }, { w: 'Apfel', g: 'apple' },
      ],
      translation: 'Today I eat an apple.',
      note: "The verb 'esse' sits SECOND, pushing the subject 'ich' after it.",
    },
    {
      sentence: 'Ich weiß, dass er heute kommt.',
      words: [
        { w: 'Ich', g: 'I' }, { w: 'weiß', g: 'know' }, { w: 'dass', g: 'that' },
        { w: 'er', g: 'he' }, { w: 'heute', g: 'today' }, { w: 'kommt', g: 'comes' },
      ],
      translation: 'I know that he is coming today.',
      note: "In a subordinate clause the verb 'kommt' jumps to the very end.",
    },
  ],
  it: [
    {
      sentence: 'Il ragazzo mangia una mela.',
      words: [
        { w: 'Il', g: 'the' }, { w: 'ragazzo', g: 'boy' }, { w: 'mangia', g: 'eats' },
        { w: 'una', g: 'a' }, { w: 'mela', g: 'apple' },
      ],
      translation: 'The boy eats an apple.',
    },
    {
      sentence: 'Lo vedo.',
      words: [{ w: 'Lo', g: 'him' }, { w: 'vedo', g: '(I)-see' }],
      translation: 'I see him.',
      note: "The object pronoun 'lo' comes before the verb; the subject is dropped.",
    },
  ],
  ca: [
    {
      sentence: 'El nen menja una poma.',
      words: [
        { w: 'El', g: 'the' }, { w: 'nen', g: 'boy' }, { w: 'menja', g: 'eats' },
        { w: 'una', g: 'a' }, { w: 'poma', g: 'apple' },
      ],
      translation: 'The boy eats an apple.',
    },
    {
      sentence: 'No en tinc.',
      words: [{ w: 'No', g: '(not)' }, { w: 'en', g: 'of-it' }, { w: 'tinc', g: '(I)-have' }],
      translation: "I don't have any.",
      note: "The weak pronoun 'en' stands in for 'of it' and clusters around the verb.",
    },
  ],
  pt: [
    {
      sentence: 'O menino come uma maçã.',
      words: [
        { w: 'O', g: 'the' }, { w: 'menino', g: 'boy' }, { w: 'come', g: 'eats' },
        { w: 'uma', g: 'a' }, { w: 'maçã', g: 'apple' },
      ],
      translation: 'The boy eats an apple.',
    },
    {
      sentence: 'É importante estudarmos.',
      words: [
        { w: 'É', g: '(it)-is' }, { w: 'importante', g: 'important' },
        { w: 'estudarmos', g: '(for-us)-to-study' },
      ],
      translation: "It's important for us to study.",
      note: "The infinitive takes a personal ending -mos — the personal infinitive, unique to Portuguese.",
    },
  ],
  ro: [
    {
      sentence: 'Băiatul mănâncă un măr.',
      words: [
        { w: 'Băiatul', g: 'boy-the' }, { w: 'mănâncă', g: 'eats' },
        { w: 'un', g: 'an' }, { w: 'măr', g: 'apple' },
      ],
      translation: 'The boy eats an apple.',
      note: "'Băiatul' = 'boy-the' — the article -ul is glued to the end of the noun.",
    },
    {
      sentence: 'Cartea este pe masă.',
      words: [
        { w: 'Cartea', g: 'book-the' }, { w: 'este', g: 'is' }, { w: 'pe', g: 'on' },
        { w: 'masă', g: 'table' },
      ],
      translation: 'The book is on the table.',
      note: "Again the article rides on the end: 'Cartea' = 'book-the'.",
    },
  ],
  tr: [
    {
      sentence: 'Çocuk elmayı yedi.',
      words: [
        { w: 'Çocuk', g: 'child' }, { w: 'elmayı', g: 'apple-(object)' },
        { w: 'yedi', g: 'ate' },
      ],
      translation: 'The child ate the apple.',
      note: "Verb last (SOV); the ending -yı marks 'apple' as the definite object.",
    },
    {
      sentence: 'Evlerimizde.',
      words: [
        { w: 'Ev', g: 'house' }, { w: '-ler', g: '(plural)' },
        { w: '-imiz', g: 'our' }, { w: '-de', g: 'in' },
      ],
      translation: 'In our houses.',
      note: 'One word = four English words, built by stacking suffixes (agglutination).',
    },
  ],
  sw: [
    {
      sentence: 'Mtoto anasoma kitabu.',
      words: [
        { w: 'Mtoto', g: 'child' }, { w: 'anasoma', g: 's/he-is-reading' },
        { w: 'kitabu', g: 'book' },
      ],
      translation: 'The child is reading a book.',
      note: "'a-na-soma' fuses subject + tense + verb into one word.",
    },
    {
      sentence: 'Vitabu vyangu viwili.',
      words: [
        { w: 'Vitabu', g: 'books' }, { w: 'vyangu', g: 'my' }, { w: 'viwili', g: 'two' },
      ],
      translation: 'my two books',
      note: "The class marker vi- repeats on every word that agrees with 'books'.",
    },
  ],
  yo: [
    {
      sentence: 'Adé ra bàtà.',
      words: [{ w: 'Adé', g: 'Ade' }, { w: 'ra', g: 'bought' }, { w: 'bàtà', g: 'shoes' }],
      translation: 'Ade bought shoes.',
      note: 'Word order is a fixed SVO; tone (not endings) does the grammatical work.',
    },
    {
      sentence: 'Ó mú ìwé wá.',
      words: [
        { w: 'Ó', g: 'he' }, { w: 'mú', g: 'took' }, { w: 'ìwé', g: 'book' },
        { w: 'wá', g: 'came' },
      ],
      translation: 'He brought the book.',
      note: "Two verbs in a row (mú … wá, 'take … come') together mean 'bring' — a serial verb.",
    },
  ],
  ha: [
    {
      sentence: 'Yaro ya sayi doya.',
      words: [
        { w: 'Yaro', g: 'boy' }, { w: 'ya', g: 'he-(did)' }, { w: 'sayi', g: 'buy' },
        { w: 'doya', g: 'yam' },
      ],
      translation: 'The boy bought a yam.',
      note: "'ya' carries 'he' + completed action, right before the verb.",
    },
    {
      sentence: 'Yarinya ta tafi.',
      words: [
        { w: 'Yarinya', g: 'girl' }, { w: 'ta', g: 'she-(did)' }, { w: 'tafi', g: 'go' },
      ],
      translation: 'The girl went.',
      note: "'ta' marks a feminine subject; 'ya' would be masculine.",
    },
  ],
  xh: [
    {
      sentence: 'Umntwana ufunda incwadi.',
      words: [
        { w: 'Umntwana', g: 'child' }, { w: 'ufunda', g: 's/he-reads' },
        { w: 'incwadi', g: 'book' },
      ],
      translation: 'The child reads a book.',
      note: 'Noun-class prefixes (um-, in-) thread agreement through the sentence.',
    },
    {
      sentence: 'Abantwana bafunda.',
      words: [{ w: 'Abantwana', g: 'children' }, { w: 'bafunda', g: 'they-read' }],
      translation: 'The children read.',
      note: 'Plural prefix aba- on the noun, echoed by ba- on the verb.',
    },
  ],
  mi: [
    {
      sentence: 'Kei te kai te tamaiti i te āporo.',
      words: [
        { w: 'Kei te kai', g: 'is-eating' }, { w: 'te', g: 'the' },
        { w: 'tamaiti', g: 'child' }, { w: 'i te', g: '(object) the' },
        { w: 'āporo', g: 'apple' },
      ],
      translation: 'The child is eating the apple.',
      note: "Verb-FIRST (VSO); the particle 'i' marks the object.",
    },
    {
      sentence: 'He tangata ia.',
      words: [{ w: 'He', g: 'a' }, { w: 'tangata', g: 'person' }, { w: 'ia', g: 'he' }],
      translation: 'He is a person.',
      note: "No verb 'to be' — the words simply sit together.",
    },
  ],
  jam: [
    {
      sentence: 'Mi a nyam di food.',
      words: [
        { w: 'Mi', g: 'I' }, { w: 'a', g: '(ongoing)' }, { w: 'nyam', g: 'eat' },
        { w: 'di', g: 'the' }, { w: 'food', g: 'food' },
      ],
      translation: "I'm eating the food.",
      note: "'a' is a particle for ongoing action — the verb itself never changes.",
    },
    {
      sentence: 'Mi did nyam di food.',
      words: [
        { w: 'Mi', g: 'I' }, { w: 'did', g: '(past)' }, { w: 'nyam', g: 'eat' },
        { w: 'di', g: 'the' }, { w: 'food', g: 'food' },
      ],
      translation: 'I ate the food.',
      note: "'did' sets the past — swap the particle, and the verb 'nyam' stays put.",
    },
  ],
  en: [
    {
      sentence: 'The dog chased the cat.',
      words: [
        { w: 'The', g: 'the' }, { w: 'dog', g: 'dog' }, { w: 'chased', g: 'chased' },
        { w: 'the', g: 'the' }, { w: 'cat', g: 'cat' },
      ],
      translation: 'The dog chased the cat.',
      note: 'Swap the nouns and the meaning flips — order alone marks who did what.',
    },
    {
      sentence: 'She looked after the kids.',
      words: [
        { w: 'She', g: 'she' }, { w: 'looked', g: 'looked' }, { w: 'after', g: 'after' },
        { w: 'the', g: 'the' }, { w: 'kids', g: 'kids' },
      ],
      translation: 'She cared for the kids.',
      note: "'look after' = care for — a phrasal verb whose parts add up to a new meaning.",
    },
  ],
  nl: [
    {
      sentence: 'Vandaag koop ik brood.',
      words: [
        { w: 'Vandaag', g: 'today' }, { w: 'koop', g: 'buy' }, { w: 'ik', g: 'I' },
        { w: 'brood', g: 'bread' },
      ],
      translation: 'Today I buy bread.',
      note: "Verb second, like German: 'koop' comes before the subject 'ik'.",
    },
    {
      sentence: 'Ik weet dat hij komt.',
      words: [
        { w: 'Ik', g: 'I' }, { w: 'weet', g: 'know' }, { w: 'dat', g: 'that' },
        { w: 'hij', g: 'he' }, { w: 'komt', g: 'comes' },
      ],
      translation: 'I know that he is coming.',
      note: "Also like German: 'komt' moves to the end of the subordinate clause.",
    },
  ],
  ru: [
    {
      sentence: 'Мальчик читает книгу.',
      words: [
        { w: 'Мальчик', g: 'boy' }, { w: 'читает', g: 'reads' },
        { w: 'книгу', g: 'book-(object)' },
      ],
      translation: 'The boy reads a book.',
      note: "'книгу' is the accusative of 'книга' — the case, not the position, marks the object, so the words can reorder freely.",
    },
    {
      sentence: 'Я прочитал письмо.',
      words: [
        { w: 'Я', g: 'I' }, { w: 'прочитал', g: 'read-(completed)' },
        { w: 'письмо', g: 'letter' },
      ],
      translation: 'I read the letter (and finished it).',
      note: "The perfective 'прочитал' says the action was completed; its imperfective pair 'читал' would describe the process.",
    },
  ],
  el: [
    {
      sentence: 'Ο άντρας διαβάζει το βιβλίο.',
      words: [
        { w: 'Ο', g: 'the' }, { w: 'άντρας', g: 'man' }, { w: 'διαβάζει', g: 'reads' },
        { w: 'το', g: 'the' }, { w: 'βιβλίο', g: 'book' },
      ],
      translation: 'The man reads the book.',
    },
    {
      sentence: 'Βλέπω τον άντρα.',
      words: [
        { w: 'Βλέπω', g: '(I)-see' }, { w: 'τον', g: 'the-(object)' },
        { w: 'άντρα', g: 'man' },
      ],
      translation: 'I see the man.',
      note: 'The article shifts for case: τον (accusative) vs. ο (nominative).',
    },
  ],
  ar: [
    {
      sentence: 'يقرأ الولد الكتاب.',
      words: [
        { w: 'يقرأ', g: 'reads' }, { w: 'الولد', g: 'the-boy' },
        { w: 'الكتاب', g: 'the-book' },
      ],
      translation: 'The boy reads the book.',
      note: 'Classical Arabic leads with the verb (VSO); read right to left.',
      rtl: true,
    },
    {
      sentence: 'الكتاب جديد.',
      words: [{ w: 'الكتاب', g: 'the-book' }, { w: 'جديد', g: 'new' }],
      translation: 'The book is new.',
      note: "No verb 'to be' in the present — just 'the book' + 'new'.",
      rtl: true,
    },
  ],
  hi: [
    {
      sentence: 'लड़का किताब पढ़ता है।',
      words: [
        { w: 'लड़का', g: 'boy' }, { w: 'किताब', g: 'book' }, { w: 'पढ़ता', g: 'reads' },
        { w: 'है', g: 'is' },
      ],
      translation: 'The boy reads a book.',
      note: "Verb last (SOV); the sentence closes with 'है' (is).",
    },
    {
      sentence: 'लड़का घर में है।',
      words: [
        { w: 'लड़का', g: 'boy' }, { w: 'घर', g: 'house' }, { w: 'में', g: 'in' },
        { w: 'है', g: 'is' },
      ],
      translation: 'The boy is in the house.',
      note: "'में' (in) comes AFTER the noun — a postposition, not a preposition.",
    },
  ],
  th: [
    {
      sentence: 'เด็กกินข้าว',
      words: [{ w: 'เด็ก', g: 'child' }, { w: 'กิน', g: 'eat' }, { w: 'ข้าว', g: 'rice' }],
      translation: 'The child eats rice.',
      note: 'Isolating: no word ever changes form; there are no spaces between words.',
    },
    {
      sentence: 'หนังสือสามเล่ม',
      words: [
        { w: 'หนังสือ', g: 'book' }, { w: 'สาม', g: 'three' }, { w: 'เล่ม', g: '(classifier)' },
      ],
      translation: 'three books',
      note: 'Counting needs a classifier — เล่ม for books and other flat, bound things.',
    },
  ],
  ko: [
    {
      sentence: '아이가 책을 읽어요.',
      words: [
        { w: '아이가', g: 'child-(subject)' }, { w: '책을', g: 'book-(object)' },
        { w: '읽어요', g: 'reads' },
      ],
      translation: 'The child reads a book.',
      note: "Verb last; '-가' marks the subject and '-을' the object.",
    },
    {
      sentence: '저는 학생이에요.',
      words: [
        { w: '저는', g: 'I-(topic)' }, { w: '학생이에요', g: 'am-a-student' },
      ],
      translation: 'I am a student.',
      note: "'-는' marks the topic; the verb 'to be' fuses onto the noun 학생 (student).",
    },
  ],
}

export function syntaxFor(code: string | undefined | null): SyntaxExample[] {
  return (code && LANGUAGE_SYNTAX[code]) || []
}
