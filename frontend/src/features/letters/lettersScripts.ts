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
    {
      title: 'Print vs italics (and handwriting)',
      note: 'Typed Cyrillic has two faces. In italics — and even more in handwriting — several letters turn into shapes that look like DIFFERENT Latin letters. Same letter, same sound: compare each upright/italic pair.',
      italics: true,
      rows: [
        { char: 'т', roman: 't', example: 'там', sound: "italic т becomes an m-shape — still 't'" },
        { char: 'и', roman: 'i', example: 'мир', sound: "italic и becomes a u-shape — still 'ee'" },
        { char: 'й', roman: 'j', example: 'мой', sound: 'italic й is that u-shape with the curve mark on top' },
        { char: 'п', roman: 'p', example: 'папа', sound: "italic п becomes an n-shape — still 'p'" },
        { char: 'д', roman: 'd', example: 'да', sound: "italic д becomes a g-shape — still 'd'" },
        { char: 'г', roman: 'g', example: 'год', sound: "italic г becomes a backwards s — still 'g'" },
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
      title: 'How letters come together',
      note: 'Arabic is cursive by rule: most letters take four shapes — alone, initial, medial, final — and join to their neighbours.',
      rows: [
        { char: 'م ح م د → محمد', roman: 'm-H-m-d', example: 'محمد', sound: 'the same letters, connected: each changes shape by position' },
        { char: 'ب ـبـ ـب', roman: 'b', example: 'باب', sound: 'one letter, three joined shapes: initial, medial, final' },
        { char: 'ا د ر ز و', roman: '(non-joiners)', example: 'دار', sound: 'six letters never connect FORWARD — they force a gap mid-word' },
        { char: 'ل + ا → لا', roman: 'laa', example: 'سلام', sound: 'lam + alif fuse into the special lam-alif ligature' },
      ],
    },
    {
      title: 'Long vowels and glides',
      positions: true,
      rows: [
        { char: 'ا', roman: 'aa', example: 'باب', sound: "long 'aa' as in father" },
        { char: 'و', roman: 'w/uu', example: 'نور', sound: "'w', or long 'oo' as in boot" },
        { char: 'ي', roman: 'y/ii', example: 'كبير', sound: "'y', or long 'ee' as in see" },
      ],
    },
    {
      title: 'Letters English has',
      note: 'Each letter shown in all four positions: alone, and joined at the start, middle, and end of a word.',
      positions: true,
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
      positions: true,
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
      positions: true,
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
      title: 'How letters come together',
      note: 'Devanagari builds syllables: vowel signs attach to consonants, and the virama (्) welds consonants into stacks.',
      rows: [
        { char: 'क + ा → का', roman: 'k + aa', example: 'काम', sound: 'a vowel sign (matra) replaces the built-in a' },
        { char: 'क + ि → कि', roman: 'k + i', example: 'किताब', sound: 'the i-matra writes to the LEFT of its consonant' },
        { char: 'स + ् + त → स्त', roman: 's+t', example: 'नमस्ते', sound: 'the virama deletes the a and fuses the pair into one cluster' },
        { char: 'क + ् + ष → क्ष', roman: 'ksh', example: 'क्षमा', sound: 'some clusters get a whole new shape — learn the common ones by sight' },
        { char: 'र special', roman: 'r', example: 'कर्म / प्रेम', sound: 'r ABOVE a cluster when first (कर्म), a small slash below when second (प्रेम)' },
      ],
    },
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

export const thaiLetters: LanguageLetters = {
  intro: 'Thai script: 44 consonants in three CLASSES (the class + tone mark decides the tone), vowels that attach around the consonant, and no spaces between words.',
  sections: [
    {
      title: 'How letters come together',
      note: 'Vowels wrap their consonant — before, after, above, or below it — and tone marks stack on top.',
      rows: [
        { char: 'ก + า → กา', roman: 'k + aa', example: 'กาแฟ', sound: 'this vowel follows the consonant' },
        { char: 'ก + ิ → กิ', roman: 'k + i', example: 'กิน', sound: 'this vowel sits ON TOP' },
        { char: 'ก + ุ → กุ', roman: 'k + u', example: 'กุ้ง', sound: 'this vowel hangs BELOW' },
        { char: 'เ + ก → เก', roman: 'k + e', example: 'เกาะ', sound: 'this vowel writes BEFORE the consonant you say it after' },
        { char: 'เ-ีย, เ-ือ', roman: 'ia, uea', example: 'เมีย', sound: 'compound vowels surround the consonant on two or three sides' },
        { char: 'ก่ ก้ ก๊ ก๋', roman: 'tones', example: 'ไม่', sound: 'four tone marks stack above; the consonant class decides what they mean' },
      ],
    },
    {
      title: 'Everyday consonants (mid class)',
      rows: [
        { char: 'ก', roman: 'g/k', example: 'ไก่', sound: "'g' as in go (unaspirated k)" },
        { char: 'จ', roman: 'j', example: 'จาน', sound: "'j' as in jar (crisper)" },
        { char: 'ด', roman: 'd', example: 'เด็ก', sound: "'d' as in dog" },
        { char: 'ต', roman: 'dt', example: 'ตา', sound: "between d and t — an unaspirated t" },
        { char: 'บ', roman: 'b', example: 'บ้าน', sound: "'b' as in bat" },
        { char: 'ป', roman: 'bp', example: 'ปลา', sound: 'between b and p — an unaspirated p' },
        { char: 'อ', roman: '(silent)', example: 'อาหาร', sound: 'the silent consonant that carries lone vowels' },
      ],
    },
    {
      title: 'Breathy consonants (high + low pairs)',
      note: 'Same sound, different class — the class changes the TONE of the syllable.',
      rows: [
        { char: 'ข / ค', roman: 'kh', example: 'ขาว / ควาย', sound: "'k'+breath (high class / low class)" },
        { char: 'ถ / ท', roman: 'th', example: 'ถนน / ทำ', sound: "'t'+breath (high / low)" },
        { char: 'ผ / พ', roman: 'ph', example: 'ผม / พ่อ', sound: "'p'+breath — never an f! (high / low)" },
        { char: 'ฝ / ฟ', roman: 'f', example: 'ฝน / ไฟ', sound: "'f' as in fun (high / low)" },
        { char: 'ส / ซ', roman: 's', example: 'สวย / ซ้าย', sound: "'s' (high / low)" },
        { char: 'ห / ฮ', roman: 'h', example: 'หก / ฮา', sound: "'h' (high / low); ห also silently raises the class of the next letter" },
      ],
    },
    {
      title: 'Sonorants and the rest',
      rows: [
        { char: 'ม', roman: 'm', example:'แม่', sound: "'m' as in map" },
        { char: 'น / ณ', roman: 'n', example: 'น้ำ', sound: "'n' as in no" },
        { char: 'ง', roman: 'ng', example: 'งู', sound: "'ng' of singer — at word START too" },
        { char: 'ร', roman: 'r', example: 'รถ', sound: 'rolled r (often becomes l in casual speech)' },
        { char: 'ล', roman: 'l', example: 'ลิง', sound: "'l' as in lamp" },
        { char: 'ว', roman: 'w', example: 'วัน', sound: "'w' as in way" },
        { char: 'ย / ญ', roman: 'y', example: 'ยา', sound: "'y' as in yes" },
        { char: 'ช', roman: 'ch', example: 'ช้าง', sound: "'ch'+breath as in chat" },
      ],
    },
    {
      title: 'Core vowels (shown on ก)',
      note: 'Short vs long changes meaning — hold the long ones noticeably.',
      rows: [
        { char: 'กะ / กา', roman: 'a / aa', example: 'มา', sound: "'a' short / long as in father" },
        { char: 'กิ / กี', roman: 'i / ii', example: 'มี', sound: "'i' short / 'ee' long" },
        { char: 'กุ / กู', roman: 'u / uu', example: 'ดู', sound: "'u' short / 'oo' long" },
        { char: 'เกะ / เก', roman: 'e', example: 'เย็น', sound: "'e' as in met / 'ay' long" },
        { char: 'โกะ / โก', roman: 'o', example: 'โต', sound: "'o' short / long as in go" },
        { char: 'ไก / ใก', roman: 'ai', example: 'ไป', sound: "'eye' — two spellings, same sound" },
        { char: 'เกา', roman: 'ao', example: 'เก้า', sound: "'ow' as in cow" },
        { char: 'กือ', roman: 'ue', example: 'มือ', sound: "'u' with spread lips — no English match" },
      ],
    },
    {
      title: 'The five tones',
      note: 'Same syllable, five meanings. Tone comes from consonant class + tone mark + syllable type.',
      rows: [
        { char: 'มา (mid)', roman: 'maa', example: 'มา', sound: 'level pitch — to come' },
        { char: 'หม่า (low)', roman: 'màa', example: 'ไม่', sound: 'starts low, stays low' },
        { char: 'ม้า (high… falling)', roman: 'máa', example: 'ม้า', sound: 'high tone — horse' },
        { char: 'หม้า (falling)', roman: 'mâa', example: 'บ้าน', sound: 'drops from high to low' },
        { char: 'หมา (rising)', roman: 'mǎa', example: 'หมา', sound: 'dips then rises — dog (mind the horse/dog pair!)' },
      ],
    },
  ],
}


export const koreanLetters: LanguageLetters = {
  intro: 'Hangul — 24 basic letters that ASSEMBLE into syllable blocks. Invented in 1443 to be learnable in a morning; the shapes even draw the mouth making the sound.',
  sections: [
    {
      title: 'How letters come together',
      note: 'Letters stack into square syllable blocks: consonant + vowel, plus an optional final consonant (받침) underneath. 한국 is six letters in two blocks.',
      rows: [
        { char: 'ㅎ + ㅏ + ㄴ → 한', roman: 'h + a + n', example: '한국', sound: 'consonant left, vertical vowel right, final letter below' },
        { char: 'ㄱ + ㅜ + ㄱ → 국', roman: 'g + u + k', example: '한국', sound: 'horizontal vowels go UNDER the first consonant' },
        { char: 'ㅅ + ㅏ → 사', roman: 's + a', example: '사람', sound: 'no final letter — just consonant + vowel' },
        { char: 'ㅇ + ㅜ → 우', roman: '(silent) + u', example: '우유', sound: 'ㅇ is a silent placeholder when a block starts with a vowel' },
        { char: 'ㅂ + ㅏ + ㅂ → 밥', roman: 'b + a + p', example: '밥', sound: 'the final ㅂ (받침) closes the syllable' },
        { char: '받침 rule', roman: 'finals', example: '있다', sound: 'only 7 sounds can end a block: k, n, t, l, m, p, ng — spelling keeps the letter, the mouth simplifies' },
      ],
    },
    {
      title: 'Plain consonants',
      rows: [
        { char: 'ㄱ', roman: 'g/k', example: '가다', sound: "between 'g' and 'k' — 'g' at the start of a word cluster" },
        { char: 'ㄴ', roman: 'n', example: '나', sound: "'n' as in no" },
        { char: 'ㄷ', roman: 'd/t', example: '돈', sound: "between 'd' and 't'" },
        { char: 'ㄹ', roman: 'r/l', example: '물', sound: "a tap 'r' between vowels; 'l' at the end of a block" },
        { char: 'ㅁ', roman: 'm', example: '몸', sound: "'m' as in mom" },
        { char: 'ㅂ', roman: 'b/p', example: '밥', sound: "between 'b' and 'p'" },
        { char: 'ㅅ', roman: 's', example: '사람', sound: "'s' as in see; 'sh' before ㅣ" },
        { char: 'ㅇ', roman: '-/ng', example: '강', sound: "silent at the start; 'ng' as in song at the end" },
        { char: 'ㅈ', roman: 'j', example: '집', sound: "between 'j' and 'ch'" },
        { char: 'ㅎ', roman: 'h', example: '하다', sound: "'h' as in hat" },
      ],
    },
    {
      title: 'Aspirated consonants (add a puff of air)',
      note: 'Each is a plain consonant with an extra stroke and an extra puff.',
      rows: [
        { char: 'ㅋ', roman: 'k', example: '코', sound: "'k' with a strong puff (ㄱ + air)" },
        { char: 'ㅌ', roman: 't', example: '토요일', sound: "'t' with a strong puff (ㄷ + air)" },
        { char: 'ㅍ', roman: 'p', example: '팔', sound: "'p' with a strong puff (ㅂ + air)" },
        { char: 'ㅊ', roman: 'ch', example: '차', sound: "'ch' with a strong puff (ㅈ + air)" },
      ],
    },
    {
      title: 'Tense consonants (doubled, no air)',
      note: 'Say them with a tight throat and zero puff — like the second p in "happy".',
      rows: [
        { char: 'ㄲ', roman: 'kk', example: '까만', sound: "a tight, unaspirated 'k'" },
        { char: 'ㄸ', roman: 'tt', example: '딸', sound: "a tight, unaspirated 't'" },
        { char: 'ㅃ', roman: 'pp', example: '빵', sound: "a tight, unaspirated 'p'" },
        { char: 'ㅆ', roman: 'ss', example: '쌀', sound: "a tight 's'" },
        { char: 'ㅉ', roman: 'jj', example: '짜다', sound: "a tight, unaspirated 'j'" },
      ],
    },
    {
      title: 'Basic vowels',
      rows: [
        { char: 'ㅏ', roman: 'a', example: '아빠', sound: "'ah' as in father" },
        { char: 'ㅓ', roman: 'eo', example: '어머니', sound: "'u' as in cut — an open 'aw'" },
        { char: 'ㅗ', roman: 'o', example: '오늘', sound: "'o' as in go (lips rounded)" },
        { char: 'ㅜ', roman: 'u', example: '우리', sound: "'oo' as in moon" },
        { char: 'ㅡ', roman: 'eu', example: '그', sound: "'u' with lips FLAT — say 'oo' while smiling" },
        { char: 'ㅣ', roman: 'i', example: '이름', sound: "'ee' as in see" },
        { char: 'ㅐ', roman: 'ae', example: '개', sound: "'e' as in bed (same as ㅔ in modern speech)" },
        { char: 'ㅔ', roman: 'e', example: '세 시', sound: "'e' as in bed" },
      ],
    },
    {
      title: 'Y- and W- vowels',
      note: 'An extra stroke adds y-; combining two vowels makes w-.',
      rows: [
        { char: 'ㅑ ㅕ ㅛ ㅠ', roman: 'ya yeo yo yu', example: '야구, 여자', sound: 'the four basic vowels with a y- on front' },
        { char: 'ㅒ ㅖ', roman: 'yae ye', example: '예', sound: "'ye' as in yes" },
        { char: 'ㅘ ㅝ', roman: 'wa wo', example: '와요, 뭐', sound: "'wa' as in water, 'wo' as in wonder" },
        { char: 'ㅙ ㅞ ㅚ', roman: 'wae we oe', example: '왜, 회사', sound: "all three sound like 'we' in modern speech" },
        { char: 'ㅟ', roman: 'wi', example: '귀', sound: "'wee' as in week" },
        { char: 'ㅢ', roman: 'ui', example: '의사', sound: "'u' + 'i' glided together; often just 'i' or 'e' in speech" },
      ],
    },
  ],
}

export const hebrewLetters: LanguageLetters = {
  intro: 'The Hebrew alef-bet — 22 letters, written right to left. Letters keep one shape (five change at the end of a word); vowels are usually unwritten.',
  sections: [
    {
      title: 'Letters English has',
      rows: [
        { char: 'ב', roman: 'b', example: 'בית', sound: "'b' as in bat (softens to 'v' without its dot)" },
        { char: 'ג', roman: 'g', example: 'גדול', sound: "'g' as in go" },
        { char: 'ד', roman: 'd', example: 'דג', sound: "'d' as in dog" },
        { char: 'ה', roman: 'h', example: 'הר', sound: "'h' as in hat; silent at the end of a word" },
        { char: 'ו', roman: 'v', example: 'ורד', sound: "'v'; as a vowel letter it spells long 'o' or 'u'" },
        { char: 'ז', roman: 'z', example: 'זמן', sound: "'z' as in zoo" },
        { char: 'י', roman: 'y', example: 'יד', sound: "'y' as in yes; as a vowel letter, long 'ee'" },
        { char: 'כ', roman: 'k', example: 'כלב', sound: "'k'; softens to 'ch' (loch) without its dot" },
        { char: 'ל', roman: 'l', example: 'לילה', sound: "'l' as in lamp" },
        { char: 'מ', roman: 'm', example: 'מים', sound: "'m' as in map" },
        { char: 'נ', roman: 'n', example: 'נר', sound: "'n' as in no" },
        { char: 'ס', roman: 's', example: 'ספר', sound: "'s' as in sun" },
        { char: 'פ', roman: 'p', example: 'פרח', sound: "'p'; softens to 'f' without its dot" },
        { char: 'ק', roman: 'q', example: 'קטן', sound: "'k' as in kite (no English difference from כ today)" },
        { char: 'ר', roman: 'r', example: 'ראש', sound: 'a gargled r at the back of the throat' },
        { char: 'ש', roman: 'sh', example: 'שלום', sound: "'sh' as in shop; with a left-side dot it reads 's'" },
        { char: 'ת', roman: 't', example: 'תודה', sound: "'t' as in top" },
      ],
    },
    {
      title: 'The new sounds',
      rows: [
        { char: 'א', roman: 'a', example: 'אבא', sound: "silent — a seat for a vowel, like the catch in 'uh-oh'" },
        { char: 'ח', roman: 'ch', example: 'חלב', sound: "'ch' of Scottish loch, from the throat" },
        { char: 'ט', roman: 'T', example: 'טוב', sound: "'t' — sounds like ת today; the spelling keeps them apart" },
        { char: 'ע', roman: "'", example: 'עין', sound: 'a squeezed throat vowel; most speakers today make it silent' },
        { char: 'צ', roman: 'ts', example: 'ציפור', sound: "'ts' as in cats" },
      ],
    },
    {
      title: 'Final forms',
      note: 'Five letters change shape at the end of a word — same letter, same sound. The keyboard does it automatically.',
      rows: [
        { char: 'כ → ך', roman: 'k', example: 'מלך', sound: 'kaf at the end of a word' },
        { char: 'מ → ם', roman: 'm', example: 'מים', sound: 'mem at the end of a word' },
        { char: 'נ → ן', roman: 'n', example: 'בן', sound: 'nun at the end of a word' },
        { char: 'פ → ף', roman: 'p/f', example: 'סוף', sound: 'pe at the end of a word' },
        { char: 'צ → ץ', roman: 'ts', example: 'ארץ', sound: 'tsadi at the end of a word' },
      ],
    },
    {
      title: 'Where the vowels went',
      note: 'Everyday Hebrew leaves most vowels unwritten (ktiv male spells long o/u with ו and ee with י). The dots and dashes (niqqud) appear only in children’s books, poetry and dictionaries.',
      rows: [
        { char: 'וֹ / וּ', roman: 'o / u', example: 'שלום', sound: "vav doing vowel duty: long 'o' or 'oo'" },
        { char: 'י', roman: 'i', example: 'דין', sound: "yod doing vowel duty: long 'ee'" },
        { char: 'בַ בֶ בִ', roman: '(niqqud)', example: 'בַּיִת', sound: 'the vowel points — small marks under the letter, usually omitted' },
      ],
    },
  ],
}

export const persianLetters: LanguageLetters = {
  intro: 'Persian uses the Arabic script — 32 letters, right to left, cursive by rule — but the sound system is far simpler: no emphatics, no throat-heavy consonants, and several borrowed letters that all merged into plain s, z, t and h.',
  sections: [
    {
      title: 'The four Persian-only letters',
      note: 'Added to the Arabic script for sounds Arabic lacks.',
      positions: true,
      rows: [
        { char: 'پ', roman: 'p', example: 'پدر', sound: "'p' as in pen" },
        { char: 'چ', roman: 'ch', example: 'چای', sound: "'ch' as in chair" },
        { char: 'ژ', roman: 'zh', example: 'ژاله', sound: "'zh' — the s in pleasure" },
        { char: 'گ', roman: 'g', example: 'گل', sound: "'g' as in go" },
      ],
    },
    {
      title: 'Letters English has',
      positions: true,
      rows: [
        { char: 'ب', roman: 'b', example: 'باب', sound: "'b' as in bat" },
        { char: 'ت', roman: 't', example: 'تهران', sound: "'t' as in top" },
        { char: 'ج', roman: 'j', example: 'جان', sound: "'j' as in jam" },
        { char: 'د', roman: 'd', example: 'دست', sound: "'d' as in dog" },
        { char: 'ر', roman: 'r', example: 'روز', sound: 'a tapped r, like Spanish' },
        { char: 'ز', roman: 'z', example: 'زبان', sound: "'z' as in zoo" },
        { char: 'س', roman: 's', example: 'سلام', sound: "'s' as in sun" },
        { char: 'ش', roman: 'sh', example: 'شب', sound: "'sh' as in shop" },
        { char: 'ف', roman: 'f', example: 'فردا', sound: "'f' as in fun" },
        { char: 'ک', roman: 'k', example: 'کتاب', sound: "'k' as in kite" },
        { char: 'ل', roman: 'l', example: 'لب', sound: "'l' as in lamp" },
        { char: 'م', roman: 'm', example: 'مادر', sound: "'m' as in map" },
        { char: 'ن', roman: 'n', example: 'نان', sound: "'n' as in no" },
        { char: 'ه', roman: 'h', example: 'هفت', sound: "'h' as in hat" },
        { char: 'و', roman: 'v', example: 'وقت', sound: "'v'; as a vowel letter, long 'oo' or 'o'" },
        { char: 'ی', roman: 'y', example: 'یک', sound: "'y'; as a vowel letter, long 'ee'" },
      ],
    },
    {
      title: 'The borrowed twins',
      note: 'Arabic loanwords kept their spelling, but Persian merged the sounds — these letters sound exactly like s, z, t, h or q. Spelling tells words apart; your mouth does nothing special.',
      positions: true,
      rows: [
        { char: 'ث', roman: 's', example: 'ثانیه', sound: "plain 's' (Arabic th)" },
        { char: 'ص', roman: 's', example: 'صبح', sound: "plain 's'" },
        { char: 'ذ', roman: 'z', example: 'ذهن', sound: "plain 'z' (Arabic dh)" },
        { char: 'ض', roman: 'z', example: 'ضعیف', sound: "plain 'z'" },
        { char: 'ظ', roman: 'z', example: 'ظهر', sound: "plain 'z'" },
        { char: 'ط', roman: 't', example: 'طلا', sound: "plain 't'" },
        { char: 'ح', roman: 'h', example: 'حال', sound: "plain 'h'" },
        { char: 'ع', roman: "'", example: 'عشق', sound: "a slight catch, or nothing at all — far softer than Arabic's" },
        { char: 'غ', roman: 'gh', example: 'غذا', sound: 'a gargled g — a French r' },
        { char: 'ق', roman: 'q / gh', example: 'قلب', sound: 'the same gargled g for most speakers' },
      ],
    },
    {
      title: 'Vowels and the little space',
      rows: [
        { char: 'آ', roman: 'aa', example: 'آب', sound: "long 'aw' as in law — alef with a hat (madda)" },
        { char: 'ا', roman: 'a', example: 'اسم', sound: 'a seat for a vowel at the start of a word' },
        { char: 'و / ی', roman: 'oo / ee', example: 'دور، شیر', sound: 'the long u and i, written with vav and ye' },
        { char: 'ــِـ ــَـ ــُـ', roman: 'e a o', example: 'دَر', sound: 'the short vowels — almost never written' },
        { char: '‌ (نیم‌فاصله)', roman: '-', example: 'می‌روم', sound: 'the half-space (ZWNJ): keeps می attached-but-separate from its verb — type it as -' },
      ],
    },
  ],
}
