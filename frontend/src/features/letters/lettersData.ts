/**
 * Letters & Sounds (beta request): a per-language pronunciation reference.
 *
 * Non-Latin scripts (ru, el, ar, hi) list their full inventories in
 * lettersScripts.ts. Latin-script languages list what an English speaker
 * actually needs: the vowels with their accent/diacritic variants, plus the
 * consonants that do NOT behave like English. Sound descriptions are written
 * for an average English speaker; the example word is playable through the
 * language's neural voice.
 */

export interface LetterRow {
  /** The letter/character (or pair) being described. */
  char: string
  /** Romanization / typing key, for the non-Latin scripts. */
  roman?: string
  /** A word to hear it in. */
  example: string
  /** Plain-English description of the sound. */
  sound: string
}

export interface LetterSection {
  title: string
  note?: string
  rows: LetterRow[]
}

export interface LanguageLetters {
  intro?: string
  sections: LetterSection[]
}

import { arabicLetters, greekLetters, hindiLetters, russianLetters, thaiLetters } from './lettersScripts'

const spanish: LanguageLetters = {
  intro: 'Spanish spelling is honest: five pure vowels, and almost every letter says the same thing every time.',
  sections: [
    {
      title: 'The five vowels',
      note: 'Short, pure, never drawled. An accent (á é í ó ú) marks stress — the sound does not change.',
      rows: [
        { char: 'a / á', example: 'agua', sound: "'ah' as in father" },
        { char: 'e / é', example: 'leche', sound: "'e' as in met" },
        { char: 'i / í', example: 'vivir', sound: "'ee' as in see" },
        { char: 'o / ó', example: 'poco', sound: "'o' as in more" },
        { char: 'u / ú', example: 'luna', sound: "'oo' as in boot (silent in que/qui, gue/gui)" },
        { char: 'ü', example: 'pingüino', sound: 'the dots wake the u up: gü = "gw"' },
      ],
    },
    {
      title: 'Consonants that differ from English',
      rows: [
        { char: 'ñ', example: 'niño', sound: "'ny' as in canyon" },
        { char: 'j', example: 'joven', sound: "throaty 'h' — Scottish loch" },
        { char: 'g (+e/i)', example: 'gente', sound: "same throaty 'h'; elsewhere hard g" },
        { char: 'll / y', example: 'llamar', sound: "'y' as in yes (a soft 'j' in much of Latin America)" },
        { char: 'h', example: 'hola', sound: 'always silent' },
        { char: 'rr / r-', example: 'perro', sound: 'rolled r; single r between vowels is a quick tap' },
        { char: 'z / c(+e,i)', example: 'zapato', sound: "'s' in Latin America; 'th' (think) in Spain" },
        { char: 'v', example: 'vaso', sound: "same as b — a soft 'b'" },
        { char: 'qu', example: 'queso', sound: "'k' — the u is silent" },
      ],
    },
  ],
}

const french: LanguageLetters = {
  intro: 'French sounds live in the vowels and the flow between words. Final consonants are usually silent; accents change vowel quality, not stress.',
  sections: [
    {
      title: 'Vowels and their accents',
      rows: [
        { char: 'a / à / â', example: 'chat', sound: "'ah' as in father" },
        { char: 'é', example: 'été', sound: "tight 'ay' as in day, no glide" },
        { char: 'è / ê / e(+2 cons.)', example: 'mère', sound: "open 'e' as in met" },
        { char: 'e (unaccented)', example: 'le', sound: "'uh' — the little schwa; often dropped" },
        { char: 'i / î / y', example: 'ville', sound: "'ee' as in see" },
        { char: 'o / ô', example: 'mot', sound: "'o' as in go" },
        { char: 'u / û', example: 'tu', sound: "say 'ee' and round your lips — no English match" },
        { char: 'ou', example: 'vous', sound: "'oo' as in boot" },
        { char: 'eu / œu', example: 'peu', sound: "say 'ay' with rounded lips" },
        { char: 'oi', example: 'moi', sound: "'wa' as in watt" },
        { char: 'au / eau', example: 'eau', sound: "'o' as in go" },
        { char: 'ai / ei', example: 'maison', sound: "'e' as in met" },
      ],
    },
    {
      title: 'The nasal vowels',
      note: 'Vowel + n/m in the same syllable = air through the nose, and the n/m itself is NOT pronounced.',
      rows: [
        { char: 'on / om', example: 'bon', sound: "nasal 'oh'" },
        { char: 'an / en', example: 'enfant', sound: "nasal 'ah'" },
        { char: 'in / ain / ein', example: 'vin', sound: "nasal 'a' (cat)" },
        { char: 'un', example: 'un', sound: 'nasal “uh” (merging with in for many speakers)' },
      ],
    },
    {
      title: 'Consonant habits',
      rows: [
        { char: 'r', example: 'rouge', sound: 'gargled at the back of the throat' },
        { char: 'ç', example: 'garçon', sound: "'s' — the tail keeps c soft before a/o/u" },
        { char: 'ch', example: 'chien', sound: "'sh' as in shop" },
        { char: 'gn', example: 'montagne', sound: "'ny' as in canyon" },
        { char: 'j / g(+e,i)', example: 'jour', sound: "'zh' — the s in pleasure" },
        { char: 'h', example: 'homme', sound: 'silent' },
        { char: 'final consonants', example: 'petit', sound: 'usually silent — careful with s, t, d, x' },
      ],
    },
  ],
}

const german: LanguageLetters = {
  intro: 'German is spoken as written once you know the umlauts and a handful of letter teams.',
  sections: [
    {
      title: 'Vowels and umlauts',
      rows: [
        { char: 'a', example: 'Haus', sound: "'ah' as in father" },
        { char: 'ä', example: 'Mädchen', sound: "'e' as in met" },
        { char: 'o', example: 'Brot', sound: "'o' as in go" },
        { char: 'ö', example: 'schön', sound: "say 'ay' with rounded lips" },
        { char: 'u', example: 'gut', sound: "'oo' as in boot" },
        { char: 'ü', example: 'über', sound: "say 'ee' with rounded lips" },
        { char: 'ei', example: 'mein', sound: "'eye'" },
        { char: 'ie', example: 'Liebe', sound: "'ee' as in see" },
        { char: 'eu / äu', example: 'heute', sound: "'oy' as in boy" },
        { char: 'au', example: 'Auto', sound: "'ow' as in cow" },
      ],
    },
    {
      title: 'Consonant teams',
      rows: [
        { char: 'w', example: 'Wasser', sound: "'v' as in van" },
        { char: 'v', example: 'Vater', sound: "'f' as in fun" },
        { char: 'z', example: 'Zeit', sound: "'ts' as in cats" },
        { char: 's (+vowel)', example: 'Sonne', sound: "'z' as in zoo" },
        { char: 'ß / ss', example: 'Straße', sound: "sharp 's'" },
        { char: 'sch', example: 'Schule', sound: "'sh' as in shop" },
        { char: 'st- / sp-', example: 'Straße', sound: "'sht' / 'shp' at word start" },
        { char: 'ch (after a/o/u)', example: 'Buch', sound: 'Scottish loch' },
        { char: 'ch (after e/i)', example: 'ich', sound: "whispered 'h' — a hissy 'hyu'" },
        { char: 'r', example: 'rot', sound: 'gargled at the back; almost a vowel at word end (-er = "uh")' },
        { char: 'final b/d/g', example: 'Tag', sound: 'harden to p/t/k' },
      ],
    },
  ],
}

const italian: LanguageLetters = {
  intro: 'Seven vowel sounds, crisp double consonants, and two letters (c, g) that soften before e and i.',
  sections: [
    {
      title: 'Vowels',
      rows: [
        { char: 'a / à', example: 'casa', sound: "'ah' as in father" },
        { char: 'e / è', example: 'bene', sound: "'e' as in met (é tighter, as in day)" },
        { char: 'i / ì', example: 'vino', sound: "'ee' as in see" },
        { char: 'o / ò', example: 'otto', sound: "'o' as in more" },
        { char: 'u / ù', example: 'uno', sound: "'oo' as in boot" },
      ],
    },
    {
      title: 'The c/g system',
      rows: [
        { char: 'c (+a,o,u)', example: 'casa', sound: "'k'" },
        { char: 'c (+e,i)', example: 'cena', sound: "'ch' as in chat" },
        { char: 'ch', example: 'chiave', sound: "'k' — the h hardens it back" },
        { char: 'g (+a,o,u)', example: 'gatto', sound: "'g' as in go" },
        { char: 'g (+e,i)', example: 'gelato', sound: "'j' as in jam" },
        { char: 'gh', example: 'spaghetti', sound: "'g' — hardened back" },
        { char: 'gn', example: 'gnocchi', sound: "'ny' as in canyon" },
        { char: 'gli', example: 'famiglia', sound: "'lli' as in million" },
        { char: 'sc (+e,i)', example: 'pesce', sound: "'sh' as in shop" },
      ],
    },
    {
      title: 'Habits',
      rows: [
        { char: 'double consonants', example: 'pizza', sound: 'held twice as long — pit-tsa, not pi-tsa' },
        { char: 'z', example: 'zio', sound: "'ts' or 'dz'" },
        { char: 'r', example: 'Roma', sound: 'rolled' },
        { char: 'h', example: 'hotel', sound: 'silent' },
      ],
    },
  ],
}

const catalan: LanguageLetters = {
  intro: 'Catalan vowels reduce when unstressed (a Catalan signature), and a few spellings are all its own.',
  sections: [
    {
      title: 'Vowels',
      rows: [
        { char: 'a / à', example: 'casa', sound: "'ah' stressed; 'uh' (schwa) unstressed" },
        { char: 'e / é / è', example: 'més', sound: "'ay'/'e' stressed; 'uh' unstressed" },
        { char: 'i / í', example: 'nit', sound: "'ee' as in see" },
        { char: 'o / ó / ò', example: 'porta', sound: "'o' stressed; 'oo' unstressed" },
        { char: 'u / ú', example: 'butxaca', sound: "'oo' as in boot" },
      ],
    },
    {
      title: 'Catalan specials',
      rows: [
        { char: 'ny', example: 'Catalunya', sound: "'ny' as in canyon" },
        { char: 'l·l', example: 'il·lusió', sound: 'the flying dot: a long l' },
        { char: 'x', example: 'xocolata', sound: "'sh' as in shop" },
        { char: 'tx', example: 'cotxe', sound: "'ch' as in chat" },
        { char: 'ç', example: 'plaça', sound: "'s'" },
        { char: 'j / g(+e,i)', example: 'jugar', sound: "'zh' — the s in pleasure" },
        { char: 'r final', example: 'cantar', sound: 'usually silent' },
        { char: 'ig final', example: 'puig', sound: "'ch' as in chat" },
      ],
    },
  ],
}

const portuguese: LanguageLetters = {
  intro: 'Brazilian Portuguese: musical vowels, famous nasal sounds, and a few consonants that surprise Spanish speakers too.',
  sections: [
    {
      title: 'Vowels and accents',
      rows: [
        { char: 'a / á', example: 'casa', sound: "'ah' as in father" },
        { char: 'â', example: 'câmera', sound: "closed 'uh'" },
        { char: 'e / é', example: 'ela', sound: "'e' as in met" },
        { char: 'ê', example: 'você', sound: "tight 'ay', no glide" },
        { char: 'e final', example: 'nome', sound: "shrinks to 'ee' in Brazil" },
        { char: 'o / ó', example: 'avó', sound: "open 'aw'" },
        { char: 'ô', example: 'avô', sound: "closed 'o' — avó/avô differ only here!" },
        { char: 'o final', example: 'gato', sound: "shrinks to 'oo'" },
        { char: 'u', example: 'tudo', sound: "'oo' as in boot" },
      ],
    },
    {
      title: 'The nasal family',
      note: 'The tilde (~) or a following m/n sends the vowel through the nose.',
      rows: [
        { char: 'ã', example: 'maçã', sound: "nasal 'ah'" },
        { char: 'ão', example: 'pão', sound: "nasal 'ow' — the most Portuguese sound there is" },
        { char: 'õe', example: 'ações', sound: "nasal 'oy'" },
        { char: 'em / en', example: 'bem', sound: "nasal 'ay'" },
        { char: 'im / in', example: 'sim', sound: "nasal 'ee'" },
      ],
    },
    {
      title: 'Consonant surprises',
      rows: [
        { char: 'ç', example: 'coração', sound: "'s'" },
        { char: 'ch', example: 'chuva', sound: "'sh' as in shop" },
        { char: 'lh', example: 'filho', sound: "'lli' as in million" },
        { char: 'nh', example: 'ninho', sound: "'ny' as in canyon" },
        { char: 'j / g(+e,i)', example: 'hoje', sound: "'zh' — the s in pleasure" },
        { char: 'r- / rr', example: 'rio', sound: "breathy 'h' in Brazil" },
        { char: 'ti / di', example: 'dia', sound: "'chee' / 'jee' in most of Brazil" },
        { char: 'l final', example: 'Brasil', sound: "turns into 'w' — Brasiw" },
      ],
    },
  ],
}

const romanian: LanguageLetters = {
  intro: 'Romanian reads almost like Italian with five extra letters — and all five are regular.',
  sections: [
    {
      title: 'The five special letters',
      rows: [
        { char: 'ă', example: 'casă', sound: "'uh' — the a in about" },
        { char: 'â / î', example: 'în', sound: "deep central 'ih' — say 'ee' with your tongue pulled back" },
        { char: 'ș', example: 'și', sound: "'sh' as in shop" },
        { char: 'ț', example: 'preț', sound: "'ts' as in cats" },
      ],
    },
    {
      title: 'Worth knowing',
      rows: [
        { char: 'c (+e,i)', example: 'ce', sound: "'ch' as in chat" },
        { char: 'che / chi', example: 'chelner', sound: "'k'" },
        { char: 'g (+e,i)', example: 'ger', sound: "'j' as in jam" },
        { char: 'ghe / ghi', example: 'ghid', sound: "'g' as in go" },
        { char: 'j', example: 'jos', sound: "'zh' — the s in pleasure" },
        { char: 'r', example: 'repede', sound: 'rolled' },
        { char: '-i final', example: 'lupi', sound: 'whispered — barely a y' },
      ],
    },
  ],
}

const turkish: LanguageLetters = {
  intro: 'Turkish spelling is perfectly regular. The famous dotted/dotless i pair matters — they are different letters.',
  sections: [
    {
      title: 'The vowels — front and back teams',
      note: 'Vowel harmony: a word sticks to one team. Front: e i ö ü. Back: a ı o u.',
      rows: [
        { char: 'a', example: 'araba', sound: "'ah' as in father" },
        { char: 'e', example: 'ev', sound: "'e' as in met" },
        { char: 'ı (dotless!)', example: 'ılık', sound: "'uh' with spread lips — the a in about" },
        { char: 'i (dotted)', example: 'bir', sound: "'i' as in bit" },
        { char: 'o', example: 'okul', sound: "'o' as in more" },
        { char: 'ö', example: 'göz', sound: "say 'ay' with rounded lips" },
        { char: 'u', example: 'su', sound: "'oo' as in boot" },
        { char: 'ü', example: 'üzüm', sound: "say 'ee' with rounded lips" },
      ],
    },
    {
      title: 'Consonants',
      rows: [
        { char: 'c', example: 'cam', sound: "'j' as in jam" },
        { char: 'ç', example: 'çay', sound: "'ch' as in chat" },
        { char: 'ş', example: 'şeker', sound: "'sh' as in shop" },
        { char: 'j', example: 'jandarma', sound: "'zh' — the s in pleasure" },
        { char: 'ğ (soft g)', example: 'dağ', sound: 'silent — it just lengthens the vowel before it' },
        { char: 'v', example: 'var', sound: "soft 'v', close to w" },
        { char: 'r', example: 'resim', sound: 'tapped; whispery at word end' },
      ],
    },
  ],
}

const swahili: LanguageLetters = {
  intro: 'Swahili is wonderfully phonetic: five pure vowels, stress always on the second-to-last syllable.',
  sections: [
    {
      title: 'Vowels',
      rows: [
        { char: 'a', example: 'baba', sound: "'ah' as in father" },
        { char: 'e', example: 'wewe', sound: "'e' as in met" },
        { char: 'i', example: 'sisi', sound: "'ee' as in see" },
        { char: 'o', example: 'moto', sound: "'o' as in more" },
        { char: 'u', example: 'kuku', sound: "'oo' as in boot" },
      ],
    },
    {
      title: 'Letter teams',
      rows: [
        { char: 'ny', example: 'nyumba', sound: "'ny' as in canyon" },
        { char: "ng'", example: "ng'ombe", sound: "'ng' of singer — at the START of the syllable" },
        { char: 'ng (no apostrophe)', example: 'ngoma', sound: "'ng-g' of finger" },
        { char: 'dh', example: 'dhahabu', sound: "'th' as in this (Arabic loans)" },
        { char: 'th', example: 'thelathini', sound: "'th' as in think" },
        { char: 'gh', example: 'ghali', sound: 'gargled g (Arabic loans)' },
        { char: 'ch', example: 'chai', sound: "'ch' as in chat" },
        { char: 'mb / nd / nj', example: 'mbwa', sound: 'hum the m/n INTO the next consonant — one beat' },
      ],
    },
  ],
}

const yoruba: LanguageLetters = {
  intro: 'Yoruba is a tone language — the accent marks are pitch, not stress. Two dotted letters mark open vowels.',
  sections: [
    {
      title: 'Vowels (7) + the dots',
      rows: [
        { char: 'a', example: 'ata', sound: "'ah' as in father" },
        { char: 'e', example: 'ewé', sound: "tight 'ay'" },
        { char: 'ẹ (dotted)', example: 'ẹja', sound: "open 'e' as in met" },
        { char: 'i', example: 'ilé', sound: "'ee' as in see" },
        { char: 'o', example: 'owó', sound: "tight 'o' as in go" },
        { char: 'ọ (dotted)', example: 'ọmọ', sound: "open 'aw' as in law" },
        { char: 'u', example: 'imu', sound: "'oo' as in boot" },
      ],
    },
    {
      title: 'Tones — the three pitches',
      note: 'Same letters, different pitch, different word. The marks are the melody.',
      rows: [
        { char: 'á (high)', example: 'wá', sound: 'pitch jumps up' },
        { char: 'a (mid)', example: 'wa', sound: 'level, ordinary pitch' },
        { char: 'à (low)', example: 'wà', sound: 'pitch drops down' },
      ],
    },
    {
      title: 'Consonants',
      rows: [
        { char: 'ṣ (dotted)', example: 'ṣe', sound: "'sh' as in shop" },
        { char: 'gb', example: 'gbogbo', sound: "'g' and 'b' at the exact same instant — no English match" },
        { char: 'p', example: 'pápá', sound: "actually 'kp' released together" },
        { char: 'j', example: 'jẹun', sound: "'j' as in jam" },
      ],
    },
  ],
}

const hausa: LanguageLetters = {
  intro: 'Hausa boko uses three "hooked" letters for sounds English does not have — they pop or crack instead of flowing.',
  sections: [
    {
      title: 'Vowels',
      note: 'Five vowels, long or short — length changes meaning.',
      rows: [
        { char: 'a', example: 'ruwa', sound: "'ah' (long: hold it)" },
        { char: 'e', example: 'gemu', sound: "'ay'" },
        { char: 'i', example: 'kifi', sound: "'ee'" },
        { char: 'o', example: 'doki', sound: "'o'" },
        { char: 'u', example: 'kudi', sound: "'oo'" },
      ],
    },
    {
      title: 'The hooked letters',
      rows: [
        { char: 'ɓ', example: 'ɓera', sound: "a 'b' that implodes — air pops inward" },
        { char: 'ɗ', example: 'ɗaki', sound: "a 'd' that implodes" },
        { char: 'ƙ', example: 'ƙofa', sound: "a 'k' with a glottal crack" },
        { char: "'y", example: "'ya'ya", sound: "a creaky 'y'" },
      ],
    },
    {
      title: 'Other habits',
      rows: [
        { char: 'ts', example: 'tsuntsu', sound: "'ts' with a crack" },
        { char: 'sh', example: 'shekara', sound: "'sh' as in shop" },
        { char: 'c', example: 'ci', sound: "'ch' as in chat" },
        { char: 'r', example: 'rana', sound: 'rolled or flapped' },
      ],
    },
  ],
}

const xhosa: LanguageLetters = {
  intro: 'isiXhosa is famous for its click consonants — three basic clicks, written c, x, q. Everything else is close to English.',
  sections: [
    {
      title: 'The three clicks',
      rows: [
        { char: 'c', example: 'cela', sound: "dental click — the 'tsk-tsk' sound, tongue behind the teeth" },
        { char: 'x', example: 'ixesha', sound: 'lateral click — the giddy-up sound from the side of the mouth' },
        { char: 'q', example: 'iqanda', sound: 'palatal click — a bottle-pop from the roof of the mouth' },
        { char: 'gc / gx / gq', example: 'gqiba', sound: 'the same clicks, voiced (hum through them)' },
        { char: 'nc / nx / nq', example: 'inqola', sound: 'the same clicks with a nasal hum' },
      ],
    },
    {
      title: 'Vowels',
      rows: [
        { char: 'a', example: 'abantu', sound: "'ah'" },
        { char: 'e', example: 'ewe', sound: "'e' as in met" },
        { char: 'i', example: 'siza', sound: "'ee'" },
        { char: 'o', example: 'onke', sound: "'aw'" },
        { char: 'u', example: 'ubuntu', sound: "'oo'" },
      ],
    },
    {
      title: 'Other letter teams',
      rows: [
        { char: 'hl', example: 'hlala', sound: 'the Welsh ll — blow air past the sides of the tongue' },
        { char: 'dl', example: 'indlela', sound: 'voiced version of hl' },
        { char: 'tsh', example: 'utshaba', sound: "'ch' as in chat" },
        { char: 'kh / th / ph', example: 'ukutya', sound: 'k/t/p with a puff of air' },
      ],
    },
  ],
}

const maori: LanguageLetters = {
  intro: 'Te reo Māori: five vowels (short and long), eight consonants, two digraphs. Every syllable ends in a vowel.',
  sections: [
    {
      title: 'Vowels — short and long',
      note: 'The macron (ā ē ī ō ū) doubles the length, and length changes meaning.',
      rows: [
        { char: 'a / ā', example: 'aroha', sound: "'ah' as in father (ā held longer)" },
        { char: 'e / ē', example: 'kete', sound: "'e' as in met" },
        { char: 'i / ī', example: 'kiwi', sound: "'ee' as in see" },
        { char: 'o / ō', example: 'moana', sound: "'aw' as in more" },
        { char: 'u / ū', example: 'utu', sound: "'oo' as in boot" },
      ],
    },
    {
      title: 'The two digraphs',
      rows: [
        { char: 'wh', example: 'whānau', sound: "'f' as in fun" },
        { char: 'ng', example: 'ngā', sound: "'ng' of singer — even at word start" },
      ],
    },
    {
      title: 'Consonants',
      rows: [
        { char: 'r', example: 'reo', sound: 'soft tap between r and l' },
        { char: 't', example: 'te', sound: "soft 't', barely aspirated" },
        { char: 'k, m, n, p, h, w', example: 'kapa haka', sound: 'as in English' },
      ],
    },
  ],
}

const jamaican: LanguageLetters = {
  intro: 'Patois in Cassidy/JLU spelling: one sound per letter, no silent letters. If you can say it, you can spell it.',
  sections: [
    {
      title: 'Vowels',
      rows: [
        { char: 'a', example: 'bak', sound: "'ah' as in father" },
        { char: 'aa', example: 'baal', sound: "long 'ah'" },
        { char: 'e', example: 'bel', sound: "'e' as in met" },
        { char: 'i', example: 'sik', sound: "'i' as in bit" },
        { char: 'ii', example: 'siik', sound: "'ee' as in see" },
        { char: 'o', example: 'pat', sound: "'o' as in pot" },
        { char: 'u', example: 'buk', sound: "'u' as in put" },
        { char: 'uu', example: 'skuul', sound: "'oo' as in boot" },
        { char: 'ie', example: 'kiek', sound: "'ye-eh' glide — cake said the Jamaican way" },
        { char: 'uo', example: 'guo', sound: "'wo-ah' glide — go said the Jamaican way" },
        { char: 'ai', example: 'taim', sound: "'eye'" },
        { char: 'ou', example: 'bout', sound: "'ow' as in cow" },
      ],
    },
    {
      title: 'Consonant habits',
      rows: [
        { char: 'k / g (+ya)', example: 'kyaan', sound: "ky/gy glide — 'cyah' for can't" },
        { char: 'no th', example: 'tink / dis', sound: "English th becomes plain 't' or 'd'" },
        { char: 'no h-drop rule', example: 'ouse / haks', sound: 'h comes and goes freely — both fine' },
        { char: 'final clusters trim', example: 'las (last)', sound: 'last consonant of a pile drops' },
      ],
    },
  ],
}


const dutch: LanguageLetters = {
  intro: 'Dutch spelling is friendly — a few letter teams and one famous vowel (ui) do all the damage.',
  sections: [
    {
      title: 'The vowel teams',
      rows: [
        { char: 'aa / a', example: 'water', sound: "long 'ah' / short 'uh' — doubling marks length" },
        { char: 'ee / e', example: 'been', sound: "long 'ay' / short 'e'; final -e is a schwa" },
        { char: 'oo / o', example: 'boom', sound: "long 'oh' / short 'o'" },
        { char: 'uu / u', example: 'muur', sound: "say 'ee' with rounded lips / short 'uh'" },
        { char: 'ie', example: 'niet', sound: "'ee' as in see" },
        { char: 'oe', example: 'boek', sound: "'oo' as in boot" },
        { char: 'eu', example: 'leuk', sound: "say 'ay' with rounded lips" },
        { char: 'ij / ei', example: 'ijs', sound: "'ay-ish eye' — the famous Dutch diphthong, two spellings" },
        { char: 'ui', example: 'huis', sound: "no English match: say 'ow' with tightly rounded lips" },
        { char: 'ou / au', example: 'oud', sound: "'ow' as in cow" },
      ],
    },
    {
      title: 'Consonant habits',
      rows: [
        { char: 'g / ch', example: 'goed', sound: 'the Dutch rasp — Scottish loch (softer in the south)' },
        { char: 'sch', example: 'school', sound: "'s' + the rasp: s-chool" },
        { char: 'w', example: 'water', sound: "between English w and v" },
        { char: 'v', example: 'vader', sound: "between v and f" },
        { char: 'j', example: 'ja', sound: "'y' as in yes" },
        { char: 'r', example: 'rood', sound: 'rolled or throaty — both fine' },
        { char: '-en (ending)', example: 'lopen', sound: "the final n often drops: 'lope(n)'" },
        { char: '-tje', example: 'kopje', sound: 'the diminutive machine — koppje, huisje, momentje' },
      ],
    },
  ],
}

const english: LanguageLetters = {
  intro: 'English spelling is history, not phonetics. These are the sounds learners fight — with reliable spellings where they exist.',
  sections: [
    {
      title: 'The famous ones',
      rows: [
        { char: 'th (soft)', example: 'think', sound: 'tongue between teeth, blow air — no voice' },
        { char: 'th (hard)', example: 'this', sound: 'same position, add voice' },
        { char: 'w vs v', example: 'very wet', sound: 'w = rounded lips no teeth; v = teeth on lip' },
        { char: 'r', example: 'red', sound: 'no roll, no gargle — curl the tongue, touch nothing' },
        { char: 'h', example: 'house', sound: 'a real breath — never silent (except hour, honest)' },
      ],
    },
    {
      title: 'Vowels that trip learners',
      rows: [
        { char: 'i (short)', example: 'ship', sound: "relaxed 'ih' — NOT sheep" },
        { char: 'ee', example: 'sheep', sound: "long tense 'ee'" },
        { char: 'a (short)', example: 'cat', sound: "open jaw 'aa'" },
        { char: 'u (short)', example: 'cup', sound: "central 'uh'" },
        { char: 'er / unstressed', example: 'teacher', sound: 'the schwa — the laziest vowel; most unstressed syllables use it' },
      ],
    },
    {
      title: 'Spelling patterns you can trust',
      rows: [
        { char: 'magic e', example: 'hat → hate', sound: 'final silent e makes the vowel say its name' },
        { char: '-tion', example: 'station', sound: "'shun'" },
        { char: 'ough', example: 'though / tough', sound: 'sorry — six different sounds; learn each word' },
      ],
    },
  ],
}

export const LETTERS: Record<string, LanguageLetters> = {
  es: spanish,
  fr: french,
  de: german,
  it: italian,
  ca: catalan,
  pt: portuguese,
  ro: romanian,
  tr: turkish,
  sw: swahili,
  yo: yoruba,
  ha: hausa,
  xh: xhosa,
  mi: maori,
  jam: jamaican,
  en: english,
  nl: dutch,
  ru: russianLetters,
  el: greekLetters,
  ar: arabicLetters,
  hi: hindiLetters,
  th: thaiLetters,
}

export function lettersFor(code: string | undefined | null): LanguageLetters | null {
  return (code && LETTERS[code]) || null
}
