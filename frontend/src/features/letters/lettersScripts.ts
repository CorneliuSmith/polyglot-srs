import type { LanguageLetters } from './lettersData'

/** Full script inventories for the non-Latin alphabets (ru, el, ar, hi).
 * Sound descriptions are aimed at an average English speaker; romanizations
 * match the app's QWERTY input schemes so the guide doubles as a typing key. */

export const russianLetters: LanguageLetters = {
  intro: 'The Cyrillic alphabet — 33 letters. Most are one steady sound each; the five "hard/soft" vowel pairs are the system to learn.',
  sections: [
    {
      title: 'Vowels — hard set',
      note: 'These keep the consonant before them plain.',
      rows: [
        { char: 'а', roman: 'a', example: 'мама', sound: "'ah' as in father" },
        { char: 'э', roman: 'e', example: 'это', sound: "'e' as in met" },
        { char: 'ы', roman: 'y', example: 'мы', sound: "a deep 'i' — say 'bit' with your tongue pulled back" },
        { char: 'о', roman: 'o', example: 'дом', sound: "'o' as in more (only when stressed)" },
        { char: 'у', roman: 'u', example: 'утро', sound: "'oo' as in boot" },
      ],
    },
    {
      title: 'Vowels — soft set',
      note: 'Same vowel sounds, but they soften the consonant before them (add a hidden y-glide).',
      rows: [
        { char: 'я', roman: 'ya', example: 'яблоко', sound: "'ya' as in yard" },
        { char: 'е', roman: 'e/ye', example: 'нет', sound: "'ye' as in yes" },
        { char: 'и', roman: 'i', example: 'мир', sound: "'ee' as in see" },
        { char: 'ё', roman: 'yo', example: 'ёлка', sound: "'yo' as in yolk (always stressed)" },
        { char: 'ю', roman: 'yu', example: 'юг', sound: "'yu' as in universe" },
      ],
    },
    {
      title: 'Consonants that look familiar (but are not)',
      rows: [
        { char: 'в', roman: 'v', example: 'вода', sound: "'v' as in van (not b)" },
        { char: 'н', roman: 'n', example: 'нос', sound: "'n' as in no (not h)" },
        { char: 'р', roman: 'r', example: 'рука', sound: 'rolled r, like Spanish' },
        { char: 'с', roman: 's', example: 'сок', sound: "'s' as in sun (not k)" },
        { char: 'у', roman: 'u', example: 'ум', sound: "'oo' — looks like y, never 'why'" },
        { char: 'х', roman: 'h/x', example: 'хлеб', sound: "throaty 'h', like Scottish loch" },
      ],
    },
    {
      title: 'The rest of the consonants',
      rows: [
        { char: 'б', roman: 'b', example: 'брат', sound: "'b' as in bat" },
        { char: 'г', roman: 'g', example:'год', sound: "'g' as in go" },
        { char: 'д', roman: 'd', example: 'да', sound: "'d' as in dog" },
        { char: 'ж', roman: 'zh', example: 'жить', sound: "'zh' — the s in pleasure" },
        { char: 'з', roman: 'z', example: 'зима', sound: "'z' as in zoo" },
        { char: 'й', roman: 'j', example: 'мой', sound: "'y' glide as in boy" },
        { char: 'к', roman: 'k', example: 'кот', sound: "'k' as in kite" },
        { char: 'л', roman: 'l', example: 'лампа', sound: "'l' as in lamp" },
        { char: 'м', roman: 'm', example: 'мост', sound: "'m' as in map" },
        { char: 'п', roman: 'p', example: 'папа', sound: "'p' as in pen" },
        { char: 'т', roman: 't', example: 'там', sound: "'t' as in top" },
        { char: 'ф', roman: 'f', example: 'фото', sound: "'f' as in fun" },
        { char: 'ц', roman: 'c/ts', example: 'цирк', sound: "'ts' as in cats" },
        { char: 'ч', roman: 'ch', example: 'чай', sound: "'ch' as in chat" },
        { char: 'ш', roman: 'sh', example: 'школа', sound: "hard 'sh' as in shop" },
        { char: 'щ', roman: 'shch', example: 'щи', sound: "long soft 'shsh' — fresh sheets" },
      ],
    },
    {
      title: 'The two silent signs',
      rows: [
        { char: 'ь', roman: "'", example: 'день', sound: 'soft sign — softens the consonant before it (adds a hint of y)' },
        { char: 'ъ', roman: "''", example: 'объект', sound: 'hard sign — a tiny break between prefix and root' },
      ],
    },
  ],
}

export const greekLetters: LanguageLetters = {
  intro: 'The Greek alphabet — 24 letters. Several English letters came from here, so half the work is already done.',
  sections: [
    {
      title: 'Vowels',
      note: 'Modern Greek has just five vowel sounds; several spellings share them.',
      rows: [
        { char: 'α', roman: 'a', example: 'αγάπη', sound: "'ah' as in father" },
        { char: 'ε', roman: 'e', example: 'ένα', sound: "'e' as in met" },
        { char: 'η', roman: 'h/i', example: 'ημέρα', sound: "'ee' as in see" },
        { char: 'ι', roman: 'i', example: 'ιδέα', sound: "'ee' as in see" },
        { char: 'ο', roman: 'o', example: 'όχι', sound: "'o' as in gone" },
        { char: 'υ', roman: 'u/y', example: 'ύπνος', sound: "'ee' — yes, also ee" },
        { char: 'ω', roman: 'w', example: 'ώρα', sound: "'o' — same as ο" },
      ],
    },
    {
      title: 'Consonants',
      rows: [
        { char: 'β', roman: 'v/b', example: 'βιβλίο', sound: "'v' as in van (not b!)" },
        { char: 'γ', roman: 'g', example: 'γάλα', sound: "soft gargled 'gh'; before e/i sounds like y in yes" },
        { char: 'δ', roman: 'd', example: 'δέκα', sound: "'th' as in this (not d!)" },
        { char: 'ζ', roman: 'z', example: 'ζωή', sound: "'z' as in zoo" },
        { char: 'θ', roman: 'th', example: 'θάλασσα', sound: "'th' as in think" },
        { char: 'κ', roman: 'k', example: 'καλά', sound: "'k' as in kite" },
        { char: 'λ', roman: 'l', example: 'λέξη', sound: "'l' as in lamp" },
        { char: 'μ', roman: 'm', example: 'μητέρα', sound: "'m' as in map" },
        { char: 'ν', roman: 'n', example: 'νερό', sound: "'n' as in no (looks like v!)" },
        { char: 'ξ', roman: 'x', example: 'ξένος', sound: "'x' as in box" },
        { char: 'π', roman: 'p', example: 'πατέρας', sound: "'p' as in pen" },
        { char: 'ρ', roman: 'r', example: 'ρολόι', sound: 'lightly rolled r (looks like p!)' },
        { char: 'σ/ς', roman: 's', example: 'σπίτι', sound: "'s' as in sun; ς only at word end" },
        { char: 'τ', roman: 't', example: 'τρία', sound: "'t' as in top" },
        { char: 'φ', roman: 'f', example: 'φίλος', sound: "'f' as in fun" },
        { char: 'χ', roman: 'ch', example: 'χέρι', sound: "throaty 'h' — Scottish loch" },
        { char: 'ψ', roman: 'ps', example: 'ψωμί', sound: "'ps' as in lapse — even at word start" },
      ],
    },
    {
      title: 'Common pairs',
      note: 'Two letters, one sound — learn these as units.',
      rows: [
        { char: 'ου', roman: 'ou', example: 'ουρανός', sound: "'oo' as in boot" },
        { char: 'αι', roman: 'ai', example: 'παιδί', sound: "'e' as in met" },
        { char: 'ει/οι', roman: 'ei/oi', example: 'είναι', sound: "'ee' as in see" },
        { char: 'μπ', roman: 'mp', example: 'μπανάνα', sound: "'b' at word start; 'mb' inside" },
        { char: 'ντ', roman: 'nt', example: 'ντομάτα', sound: "'d' at word start; 'nd' inside" },
        { char: 'γγ/γκ', roman: 'gg/gk', example: 'αγγλικά', sound: "'g'/'ng-g'" },
      ],
    },
  ],
}

export const arabicLetters: LanguageLetters = {
  intro: 'The Arabic abjad — 28 letters, written right to left. Letters connect and change shape by position; short vowels are usually unwritten.',
  sections: [
    {
      title: 'Long vowels and glides',
      rows: [
        { char: 'ا', roman: 'aa', example: 'باب', sound: "long 'aa' as in father" },
        { char: 'و', roman: 'w/uu', example: 'نور', sound: "'w', or long 'oo' as in boot" },
        { char: 'ي', roman: 'y/ii', example: 'كبير', sound: "'y', or long 'ee' as in see" },
      ],
    },
    {
      title: 'Letters English has',
      rows: [
        { char: 'ب', roman: 'b', example: 'بيت', sound: "'b' as in bat" },
        { char: 'ت', roman: 't', example: 'تفاح', sound: "'t' as in top" },
        { char: 'ث', roman: 'th', example: 'ثلاثة', sound: "'th' as in think" },
        { char: 'ج', roman: 'j', example: 'جمل', sound: "'j' as in jam" },
        { char: 'د', roman: 'd', example: 'دار', sound: "'d' as in dog" },
        { char: 'ذ', roman: 'dh', example: 'هذا', sound: "'th' as in this" },
        { char: 'ر', roman: 'r', example: 'رجل', sound: 'rolled r, like Spanish' },
        { char: 'ز', roman: 'z', example: 'زيت', sound: "'z' as in zoo" },
        { char: 'س', roman: 's', example: 'سلام', sound: "'s' as in sun" },
        { char: 'ش', roman: 'sh', example: 'شمس', sound: "'sh' as in shop" },
        { char: 'ف', roman: 'f', example: 'فيل', sound: "'f' as in fun" },
        { char: 'ك', roman: 'k', example: 'كتاب', sound: "'k' as in kite" },
        { char: 'ل', roman: 'l', example: 'ليل', sound: "'l' as in lamp" },
        { char: 'م', roman: 'm', example: 'ماء', sound: "'m' as in map" },
        { char: 'ن', roman: 'n', example: 'نار', sound: "'n' as in no" },
        { char: 'ه', roman: 'h', example: 'هنا', sound: "'h' as in hat" },
      ],
    },
    {
      title: 'The new sounds',
      note: 'Made deeper in the throat than anything in English — listen and copy.',
      rows: [
        { char: 'ح', roman: 'H / 7', example: 'حب', sound: "breathy 'h' from deep in the throat — fogging a mirror, harder" },
        { char: 'خ', roman: 'kh / 5', example: 'خبز', sound: "'ch' of Scottish loch" },
        { char: 'ع', roman: '3', example: 'عين', sound: 'a squeezed throat vowel — no English match; listen closely' },
        { char: 'غ', roman: 'gh', example: 'غرب', sound: 'gargled g — a French r' },
        { char: 'ق', roman: 'q', example: 'قلب', sound: "'k' pulled to the very back of the mouth" },
        { char: 'ء', roman: "2 / '", example: 'سؤال', sound: "glottal stop — the catch in 'uh-oh'" },
      ],
    },
    {
      title: 'The emphatic four',
      note: "Heavier twins of t/d/s/z — the tongue cups back and the whole word darkens.",
      rows: [
        { char: 'ص', roman: 'S', example: 'صباح', sound: "heavy 's'" },
        { char: 'ض', roman: 'D', example: 'ضوء', sound: "heavy 'd'" },
        { char: 'ط', roman: 'T', example: 'طعام', sound: "heavy 't'" },
        { char: 'ظ', roman: 'Z', example: 'ظهر', sound: "heavy 'th/z'" },
      ],
    },
    {
      title: 'Short vowels (harakat)',
      note: 'Small marks above/below the letter — usually left unwritten outside teaching texts.',
      rows: [
        { char: 'ـَ', roman: 'a', example: 'فَتَحَ', sound: "short 'a' as in cat (fatha)" },
        { char: 'ـِ', roman: 'i', example: 'بِنت', sound: "short 'i' as in bit (kasra)" },
        { char: 'ـُ', roman: 'u', example: 'كُتُب', sound: "short 'u' as in put (damma)" },
        { char: 'ـّ', roman: '(double)', example: 'مُدَرِّس', sound: 'shadda — hold the consonant twice as long' },
      ],
    },
  ],
}

export const hindiLetters: LanguageLetters = {
  intro: 'Devanagari — each consonant carries a built-in "a"; vowel signs (matras) replace it. The headline sounds: retroflex letters (tongue curled back) vs dental letters (tongue on the teeth), and aspirated pairs with an extra puff of air.',
  sections: [
    {
      title: 'Independent vowels',
      note: 'Used at the start of a word; inside words they become matras (next section).',
      rows: [
        { char: 'अ', roman: 'a', example: 'अब', sound: "short 'u' as in about" },
        { char: 'आ', roman: 'aa', example: 'आम', sound: "long 'aa' as in father" },
        { char: 'इ', roman: 'i', example: 'इधर', sound: "short 'i' as in bit" },
        { char: 'ई', roman: 'ii', example: 'ईद', sound: "long 'ee' as in see" },
        { char: 'उ', roman: 'u', example: 'उधर', sound: "short 'u' as in put" },
        { char: 'ऊ', roman: 'uu', example: 'ऊपर', sound: "long 'oo' as in boot" },
        { char: 'ए', roman: 'e', example: 'एक', sound: "'ay' as in day (no glide)" },
        { char: 'ऐ', roman: 'ai', example: 'ऐनक', sound: "'a' as in cat/bank" },
        { char: 'ओ', roman: 'o', example: 'ओर', sound: "'o' as in go (no glide)" },
        { char: 'औ', roman: 'au', example: 'औरत', sound: "'aw' as in law" },
      ],
    },
    {
      title: 'The same vowels as matras',
      note: 'क shown as the carrier. The inherent अ needs no mark.',
      rows: [
        { char: 'का', roman: 'kaa', example: 'काम', sound: 'k + aa' },
        { char: 'कि', roman: 'ki', example: 'किताब', sound: 'k + i (mark goes BEFORE the letter)' },
        { char: 'की', roman: 'kii', example: 'की', sound: 'k + ee' },
        { char: 'कु', roman: 'ku', example: 'कुछ', sound: 'k + u' },
        { char: 'कू', roman: 'kuu', example: 'कूद', sound: 'k + oo' },
        { char: 'के', roman: 'ke', example: 'के', sound: 'k + ay' },
        { char: 'कै', roman: 'kai', example: 'कैसा', sound: 'k + a (cat)' },
        { char: 'को', roman: 'ko', example: 'को', sound: 'k + o' },
        { char: 'कौ', roman: 'kau', example: 'कौन', sound: 'k + aw' },
        { char: 'कं', roman: 'kaM', example: 'कंघी', sound: 'nasal hum after the vowel (anusvara)' },
      ],
    },
    {
      title: 'Consonants — the aspirated pairs',
      note: 'Second of each pair adds a puff of air (hold your palm up — you should feel it).',
      rows: [
        { char: 'क / ख', roman: 'k / kh', example: 'खाना', sound: "'k' plain, then 'k'+breath" },
        { char: 'ग / घ', roman: 'g / gh', example: 'घर', sound: "'g' plain, then 'g'+breath" },
        { char: 'च / छ', roman: 'ch / chh', example: 'छह', sound: "'ch' plain, then 'ch'+breath" },
        { char: 'ज / झ', roman: 'j / jh', example: 'झील', sound: "'j' plain, then 'j'+breath" },
        { char: 'प / फ', roman: 'p / ph', example: 'फल', sound: "'p' plain, then 'p'+breath" },
        { char: 'ब / भ', roman: 'b / bh', example: 'भाई', sound: "'b' plain, then 'b'+breath" },
      ],
    },
    {
      title: 'Retroflex vs dental — the big split',
      note: 'Retroflex: tongue curled back to the roof. Dental: tongue touching the teeth. English t/d sit in between — Hindi hears them as retroflex.',
      rows: [
        { char: 'ट / ठ', roman: 'T / Th', example: 'टमाटर', sound: 'retroflex t (plain / +breath)' },
        { char: 'ड / ढ', roman: 'D / Dh', example: 'डर', sound: 'retroflex d (plain / +breath)' },
        { char: 'ण', roman: 'N', example: 'बाण', sound: 'retroflex n' },
        { char: 'त / थ', roman: 't / th', example: 'तीन', sound: 'dental t — softer than English (plain / +breath)' },
        { char: 'द / ध', roman: 'd / dh', example: 'दो', sound: 'dental d (plain / +breath)' },
        { char: 'न', roman: 'n', example: 'नाम', sound: "'n' as in no" },
        { char: 'ड़ / ढ़', roman: 'R / Rh', example: 'लड़का', sound: 'flapped r — tongue slaps down from retroflex' },
      ],
    },
    {
      title: 'The rest',
      rows: [
        { char: 'म', roman: 'm', example: 'माँ', sound: "'m' as in map" },
        { char: 'य', roman: 'y', example: 'यह', sound: "'y' as in yes" },
        { char: 'र', roman: 'r', example: 'रात', sound: 'light tapped r' },
        { char: 'ल', roman: 'l', example: 'लाल', sound: "'l' as in lamp" },
        { char: 'व', roman: 'v/w', example: 'वह', sound: "between 'v' and 'w'" },
        { char: 'श / ष', roman: 'sh / Sh', example: 'शहर', sound: "'sh' as in shop" },
        { char: 'स', roman: 's', example: 'सात', sound: "'s' as in sun" },
        { char: 'ह', roman: 'h', example: 'हाँ', sound: "'h' as in hat" },
      ],
    },
    {
      title: 'Nuqta letters (loan sounds)',
      note: 'A dot under a letter marks Perso-Arabic sounds.',
      rows: [
        { char: 'ज़', roman: 'z', example: 'ज़रूर', sound: "'z' as in zoo" },
        { char: 'फ़', roman: 'f', example: 'फ़ोन', sound: "'f' as in fun" },
        { char: 'क़', roman: 'q', example: 'क़लम', sound: "back-of-mouth 'k'" },
        { char: 'ख़ / ग़', roman: 'kh / gh', example: 'ख़बर', sound: 'loch-ch / gargled g' },
      ],
    },
  ],
}
