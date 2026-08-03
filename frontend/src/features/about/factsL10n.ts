/**
 * "Things to know", localized: per-UI-language overlays over the English
 * reference in languageFacts.ts, authored (not machine-glossed) per
 * audience. A pair with no overlay falls back to English. Keyed
 * [uiLanguage][courseCode]; Turkish first, the live test course.
 */
import type { LanguageFacts } from './languageFacts'

const trEs: LanguageFacts = {
  tagline: 'Una lengua túrquica que se construye apilando sufijos.',
  family: 'Túrquica › Oguz',
  speakers: '~80 millones de hablantes nativos.',
  whereSpoken: 'Turquía y Chipre, con grandes comunidades por toda Europa.',
  writingSystem: 'Alfabeto latino adaptado (adoptado en 1928) con ç, ğ, ı, ö, ş, ü. De izquierda a derecha.',
  wordOrder: 'Sujeto–Objeto–Verbo: el verbo va al final.',
  history:
    'Una lengua túrquica oguz llevada hacia el oeste desde Asia Central. El turco otomano se escribía en alfabeto árabe, impregnado de persa y árabe; las reformas de Atatürk en los años veinte lo latinizaron y lo «purificaron».',
  unique: [
    'Aglutinante: frases enteras se construyen con una raíz más una cadena de sufijos.',
    'Armonía vocálica: las vocales de los sufijos cambian para ajustarse a las de la palabra.',
    'Sin género gramatical y sin artículo definido.',
    'Una forma evidencial propia (-miş) marca lo que se oyó decir o se infiere.',
  ],
}

const trAr: LanguageFacts = {
  tagline: 'لغة تركية تُبنى بتكديس اللواحق.',
  family: 'التركية › الأوغوزية',
  speakers: 'نحو ٨٠ مليون ناطق أصلي.',
  whereSpoken: 'تركيا وقبرص، مع جاليات كبيرة في أنحاء أوروبا.',
  writingSystem: 'أبجدية لاتينية معدّلة (اعتُمدت عام 1928) مع ç, ğ, ı, ö, ş, ü. تُكتب من اليسار إلى اليمين.',
  wordOrder: 'فاعل–مفعول–فعل: الفعل يأتي في آخر الجملة.',
  history:
    'لغة تركية أوغوزية حُملت غربًا من آسيا الوسطى. كانت التركية العثمانية تُكتب بالحرف العربي وهي مشبعة بالفارسية والعربية؛ ثم جاءت إصلاحات أتاتورك في العشرينيات فحوّلتها إلى الحرف اللاتيني و«نقّتها».',
  unique: [
    'إلصاقية: يمكن بناء جمل كاملة من جذر واحد وسلسلة لواحق.',
    'تناغم صوتي — حركات اللواحق تتغير لتوافق حركات الكلمة.',
    'لا جنس نحوي ولا أداة تعريف.',
    'صيغة نقلية خاصة (-miş) تدل على السماع أو الاستنتاج.',
  ],
}

const trRu: LanguageFacts = {
  tagline: 'Тюркский язык, который собирается из цепочек суффиксов.',
  family: 'Тюркские › огузские',
  speakers: '~80 млн носителей.',
  whereSpoken: 'Турция и Кипр, крупные общины по всей Европе.',
  writingSystem: 'Адаптированная латиница (принята в 1928 году) с ç, ğ, ı, ö, ş, ü. Слева направо.',
  wordOrder: 'Подлежащее–дополнение–сказуемое: глагол в конце.',
  history:
    'Огузский тюркский язык, принесённый на запад из Средней Азии. Османский турецкий писался арабским письмом и был насыщен персидским и арабским; реформы Ататюрка 1920-х перевели его на латиницу и «очистили».',
  unique: [
    'Агглютинация: целые предложения строятся из корня и цепочки суффиксов.',
    'Гармония гласных — гласные суффиксов подстраиваются под гласные слова.',
    'Нет грамматического рода и определённого артикля.',
    'Особая эвиденциальная форма (-miş) отмечает услышанное или выведенное.',
  ],
}

const trFr: LanguageFacts = {
  tagline: 'Une langue turcique bâtie en empilant des suffixes.',
  family: 'Turcique › oghouze',
  speakers: '~80 millions de locuteurs natifs.',
  whereSpoken: 'Turquie et Chypre, avec de grandes communautés dans toute l’Europe.',
  writingSystem: 'Alphabet latin adapté (adopté en 1928) avec ç, ğ, ı, ö, ş, ü. De gauche à droite.',
  wordOrder: 'Sujet–Objet–Verbe : le verbe vient en dernier.',
  history:
    'Langue turcique oghouze portée vers l’ouest depuis l’Asie centrale. Le turc ottoman s’écrivait en alphabet arabe, imprégné de persan et d’arabe ; les réformes d’Atatürk dans les années 1920 l’ont latinisé et « purifié ».',
  unique: [
    'Agglutinante : des phrases entières se construisent à partir d’une racine et d’une chaîne de suffixes.',
    'Harmonie vocalique — les voyelles des suffixes s’accordent à celles du mot.',
    'Pas de genre grammatical ni d’article défini.',
    'Une forme évidentielle dédiée (-miş) signale le ouï-dire ou l’inférence.',
  ],
}

const trPt: LanguageFacts = {
  tagline: 'Uma língua túrquica construída empilhando sufixos.',
  family: 'Túrquica › Oguz',
  speakers: '~80 milhões de falantes nativos.',
  whereSpoken: 'Turquia e Chipre, com grandes comunidades pela Europa.',
  writingSystem: 'Alfabeto latino adaptado (adotado em 1928) com ç, ğ, ı, ö, ş, ü. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Objeto–Verbo: o verbo vem por último.',
  history:
    'Língua túrquica oguz levada para o oeste a partir da Ásia Central. O turco otomano era escrito em alfabeto árabe, impregnado de persa e árabe; as reformas de Atatürk nos anos 1920 o latinizaram e o «purificaram».',
  unique: [
    'Aglutinante: frases inteiras se constroem de uma raiz mais uma cadeia de sufixos.',
    'Harmonia vocálica — as vogais dos sufixos mudam para combinar com as da palavra.',
    'Sem gênero gramatical e sem artigo definido.',
    'Uma forma evidencial própria (-miş) marca o que se ouviu dizer ou se inferiu.',
  ],
}

// Full per-locale overlays (all courses), authored in factsL10n.{locale}.ts.
// The tr* entries above were the originals and are reused verbatim inside
// those files; spreading them last keeps them authoritative should the two
// ever diverge.
import { FACTS_AR, SYNTAX_AR } from './factsL10n.ar'
import { FACTS_ES, SYNTAX_ES } from './factsL10n.es'
import { FACTS_FR, SYNTAX_FR } from './factsL10n.fr'
import { FACTS_PT, SYNTAX_PT } from './factsL10n.pt'
import { FACTS_RU, SYNTAX_RU } from './factsL10n.ru'
import type { SyntaxExample } from './languageFacts'

export const FACTS_L10N: Record<string, Record<string, LanguageFacts>> = {
  es: { ...FACTS_ES, tr: trEs },
  ar: { ...FACTS_AR, tr: trAr },
  ru: { ...FACTS_RU, tr: trRu },
  fr: { ...FACTS_FR, tr: trFr },
  pt: { ...FACTS_PT, tr: trPt },
}

/** Glossed word-order examples, localized: same sentences and words as the
 * base, with glosses/translations/notes in the reader's UI language. */
export const SYNTAX_L10N: Record<string, Record<string, SyntaxExample[]>> = {
  es: SYNTAX_ES,
  ar: SYNTAX_AR,
  ru: SYNTAX_RU,
  fr: SYNTAX_FR,
  pt: SYNTAX_PT,
}
