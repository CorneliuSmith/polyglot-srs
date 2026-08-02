/**
 * Letters & Sounds, localized: per-UI-language overlays over the English
 * reference data. NOT word-for-word translations — the sound descriptions
 * are re-anchored for each audience (an English "'ah' as in father" is
 * useless to a Russian reader; Turkish ı is simply "как ы"). A language
 * pair with no overlay falls back to the English original in lettersData.
 *
 * Keyed [uiLanguage][courseCode]. Turkish first (the live test course);
 * further courses join pair by pair, quality over coverage.
 */
import type { LanguageLetters } from './lettersData'

const turkishEs: LanguageLetters = {
  intro:
    'La ortografía turca es perfectamente regular. El famoso par de la i con punto y la ı sin punto importa: son letras distintas.',
  sections: [
    {
      title: 'Las vocales — equipo anterior y equipo posterior',
      note: 'Armonía vocálica: cada palabra se queda en un solo equipo. Anteriores: e i ö ü. Posteriores: a ı o u.',
      rows: [
        { char: 'a', example: 'araba', sound: "como la a de 'casa'" },
        { char: 'e', example: 'ev', sound: "como la e de 'mesa'" },
        { char: 'ı (¡sin punto!)', example: 'ılık', sound: 'una «e» sorda y relajada, con los labios estirados — no existe en español' },
        { char: 'i (con punto)', example: 'bir', sound: "como la i de 'mil'" },
        { char: 'o', example: 'okul', sound: "como la o de 'poco'" },
        { char: 'ö', example: 'göz', sound: 'di «e» con los labios redondeados (la eu francesa)' },
        { char: 'u', example: 'su', sound: "como la u de 'luna'" },
        { char: 'ü', example: 'üzüm', sound: 'di «i» con los labios redondeados (la u francesa)' },
      ],
    },
    {
      title: 'Consonantes',
      rows: [
        { char: 'c', example: 'cam', sound: 'como una «y» fuerte rioplatense; la j del inglés jam' },
        { char: 'ç', example: 'çay', sound: "como la ch de 'chico'" },
        { char: 'ş', example: 'şeker', sound: 'como la sh inglesa de shop' },
        { char: 'j', example: 'jandarma', sound: 'como la j francesa de jour (zh suave)' },
        { char: 'ğ (g suave)', example: 'dağ', sound: 'muda — solo alarga la vocal anterior' },
        { char: 'v', example: 'var', sound: 'v suave, casi w' },
        { char: 'r', example: 'resim', sound: "r simple de 'pero'; al final de palabra suena susurrada" },
      ],
    },
  ],
}

const turkishAr: LanguageLetters = {
  intro:
    'الإملاء التركي منتظم تمامًا. الفرق بين الياء المنقوطة i وغير المنقوطة ı مهم — فهما حرفان مختلفان.',
  sections: [
    {
      title: 'حروف العلة — مجموعة أمامية ومجموعة خلفية',
      note: 'التناغم الصوتي: تلتزم الكلمة بمجموعة واحدة. الأمامية: e i ö ü. الخلفية: a ı o u.',
      rows: [
        { char: 'a', example: 'araba', sound: 'فتحة ممدودة قليلًا، مثل ألف «باب»' },
        { char: 'e', example: 'ev', sound: 'فتحة ممالة نحو الكسر' },
        { char: 'ı (بلا نقطة!)', example: 'ılık', sound: 'صوت مطموس بين الضمة والكسرة، بشفتين مبسوطتين' },
        { char: 'i (بنقطة)', example: 'bir', sound: 'كسرة صريحة، مثل ياء «بير»' },
        { char: 'o', example: 'okul', sound: 'مثل واو «لو» قصيرة' },
        { char: 'ö', example: 'göz', sound: 'انطق الكسرة بشفتين مدوّرتين' },
        { char: 'u', example: 'su', sound: 'ضمة صريحة، مثل واو «سو»' },
        { char: 'ü', example: 'üzüm', sound: 'انطق الياء بشفتين مدوّرتين' },
      ],
    },
    {
      title: 'الحروف الساكنة',
      rows: [
        { char: 'c', example: 'cam', sound: 'مثل الجيم الفصحى المعطّشة (ج)' },
        { char: 'ç', example: 'çay', sound: 'مثل «تش» في «تشاي»' },
        { char: 'ş', example: 'şeker', sound: 'مثل الشين (ش)' },
        { char: 'j', example: 'jandarma', sound: 'مثل الجيم الشامية غير المعطّشة (چ الفرنسية في jour)' },
        { char: 'ğ (الغين اللينة)', example: 'dağ', sound: 'صامت — يطيل الحركة التي قبله فقط' },
        { char: 'v', example: 'var', sound: 'بين الواو والـ v الخفيفة' },
        { char: 'r', example: 'resim', sound: 'راء بضربة واحدة؛ تُهمس في آخر الكلمة' },
      ],
    },
  ],
}

const turkishRu: LanguageLetters = {
  intro:
    'Турецкая орфография абсолютно регулярна. Знаменитая пара — i с точкой и ı без точки — важна: это разные буквы.',
  sections: [
    {
      title: 'Гласные — передняя и задняя команды',
      note: 'Гармония гласных: слово держится одной команды. Передние: e i ö ü. Задние: a ı o u.',
      rows: [
        { char: 'a', example: 'araba', sound: 'как а в «мама»' },
        { char: 'e', example: 'ev', sound: 'как э в «это»' },
        { char: 'ı (без точки!)', example: 'ılık', sound: 'почти как русская ы, короткая, с растянутыми губами' },
        { char: 'i (с точкой)', example: 'bir', sound: 'как и в «мир»' },
        { char: 'o', example: 'okul', sound: 'как о в «дом»' },
        { char: 'ö', example: 'göz', sound: 'э с округлёнными губами (немецкая ö)' },
        { char: 'u', example: 'su', sound: 'как у в «суп»' },
        { char: 'ü', example: 'üzüm', sound: 'и с округлёнными губами (немецкая ü, как в «тюль»)' },
      ],
    },
    {
      title: 'Согласные',
      rows: [
        { char: 'c', example: 'cam', sound: 'как дж в «джем»' },
        { char: 'ç', example: 'çay', sound: 'как ч' },
        { char: 'ş', example: 'şeker', sound: 'как ш' },
        { char: 'j', example: 'jandarma', sound: 'как ж' },
        { char: 'ğ (мягкая g)', example: 'dağ', sound: 'немая — лишь удлиняет предыдущий гласный' },
        { char: 'v', example: 'var', sound: 'мягкое в, близкое к английскому w' },
        { char: 'r', example: 'resim', sound: 'одноударное р; в конце слова приглушённое' },
      ],
    },
  ],
}

const turkishFr: LanguageLetters = {
  intro:
    'L’orthographe turque est parfaitement régulière. Le fameux duo i avec point / ı sans point compte : ce sont deux lettres différentes.',
  sections: [
    {
      title: 'Les voyelles — équipe antérieure et équipe postérieure',
      note: 'Harmonie vocalique : un mot reste dans une seule équipe. Antérieures : e i ö ü. Postérieures : a ı o u.',
      rows: [
        { char: 'a', example: 'araba', sound: 'comme le a de « papa »' },
        { char: 'e', example: 'ev', sound: 'comme le è de « mère »' },
        { char: 'ı (sans point !)', example: 'ılık', sound: 'proche du e muet de « le », lèvres étirées' },
        { char: 'i (avec point)', example: 'bir', sound: 'comme le i de « ici »' },
        { char: 'o', example: 'okul', sound: 'comme le o de « fort »' },
        { char: 'ö', example: 'göz', sound: 'comme eu dans « peur »' },
        { char: 'u', example: 'su', sound: 'comme ou dans « fou »' },
        { char: 'ü', example: 'üzüm', sound: 'comme le u français de « lune »' },
      ],
    },
    {
      title: 'Les consonnes',
      rows: [
        { char: 'c', example: 'cam', sound: 'comme dj dans « Djibouti »' },
        { char: 'ç', example: 'çay', sound: 'comme tch dans « tchèque »' },
        { char: 'ş', example: 'şeker', sound: 'comme ch dans « chat »' },
        { char: 'j', example: 'jandarma', sound: 'comme le j français de « jour »' },
        { char: 'ğ (g doux)', example: 'dağ', sound: 'muet — il allonge simplement la voyelle précédente' },
        { char: 'v', example: 'var', sound: 'v doux, proche du w' },
        { char: 'r', example: 'resim', sound: 'r battu bref ; chuchoté en fin de mot' },
      ],
    },
  ],
}

const turkishPt: LanguageLetters = {
  intro:
    'A ortografia turca é perfeitamente regular. O famoso par i com ponto / ı sem ponto importa: são letras diferentes.',
  sections: [
    {
      title: 'As vogais — time anterior e time posterior',
      note: 'Harmonia vocálica: a palavra fica em um só time. Anteriores: e i ö ü. Posteriores: a ı o u.',
      rows: [
        { char: 'a', example: 'araba', sound: "como o a de 'casa'" },
        { char: 'e', example: 'ev', sound: "como o é de 'pé'" },
        { char: 'ı (sem ponto!)', example: 'ılık', sound: "um 'e' mudo de lábios esticados — como o e final de 'nome' em Portugal" },
        { char: 'i (com ponto)', example: 'bir', sound: "como o i de 'ali'" },
        { char: 'o', example: 'okul', sound: "como o ó de 'avó'" },
        { char: 'ö', example: 'göz', sound: 'diga «ê» com os lábios arredondados (eu francês)' },
        { char: 'u', example: 'su', sound: "como o u de 'tudo'" },
        { char: 'ü', example: 'üzüm', sound: 'diga «i» com os lábios arredondados (u francês)' },
      ],
    },
    {
      title: 'Consoantes',
      rows: [
        { char: 'c', example: 'cam', sound: "como dj — o j do inglês 'jam'" },
        { char: 'ç', example: 'çay', sound: "como tch em 'tchau'" },
        { char: 'ş', example: 'şeker', sound: "como ch em 'chave'" },
        { char: 'j', example: 'jandarma', sound: "como o j de 'já'" },
        { char: 'ğ (g suave)', example: 'dağ', sound: 'mudo — só alonga a vogal anterior' },
        { char: 'v', example: 'var', sound: 'v suave, quase w' },
        { char: 'r', example: 'resim', sound: "r de vibração simples, como em 'caro'; sussurrado no fim da palavra" },
      ],
    },
  ],
}

export const LETTERS_L10N: Record<string, Record<string, LanguageLetters>> = {
  es: { tr: turkishEs },
  ar: { tr: turkishAr },
  ru: { tr: turkishRu },
  fr: { tr: turkishFr },
  pt: { tr: turkishPt },
}
