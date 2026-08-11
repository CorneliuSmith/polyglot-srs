/**
 * Letters & Sounds — русская локализация: полный оверлей всех 22 курсов.
 * Не пословный перевод: каждое описание звука заякорено заново для
 * русскоязычного читателя («'ah' as in father» → «как а в „мама“»), с опорой
 * на русскую фонологию (ы, х, ж, щ, мягкость, оглушение конечных согласных).
 * char / roman / example скопированы из английского оригинала без изменений
 * (локализованы только пояснения в скобках); tr взят из lettersL10n.ts как есть.
 */
import type { LanguageLetters } from './lettersData'

const spanishRu: LanguageLetters = {
  intro: 'Испанская орфография честна: пять чистых гласных, и почти каждая буква всегда читается одинаково.',
  sections: [
    {
      title: 'Пять гласных',
      note: 'Краткие, чистые, без растягивания. Акцент (á é í ó ú) отмечает ударение — сам звук не меняется.',
      rows: [
        { char: 'a / á', example: 'agua', sound: 'как а в «мама»' },
        { char: 'e / é', example: 'leche', sound: 'как э в «это»' },
        { char: 'i / í', example: 'vivir', sound: 'как и в «мир»' },
        { char: 'o / ó', example: 'poco', sound: 'как о в «дом»' },
        { char: 'u / ú', example: 'luna', sound: 'как у в «утро» (немая в que/qui, gue/gui)' },
        { char: 'ü', example: 'pingüino', sound: 'точки «будят» u: gü = «гв», как в «пингвин»' },
      ],
    },
    {
      title: 'Согласные, которые читаются неожиданно',
      rows: [
        { char: 'ñ', example: 'niño', sound: 'как нь в «няня»' },
        { char: 'j', example: 'joven', sound: 'как русское х' },
        { char: 'g (+e/i)', example: 'gente', sound: 'то же х; в остальных позициях — обычное г' },
        { char: 'll / y', example: 'llamar', sound: 'как й в «йога» (в большей части Латинской Америки — мягкое дж/ж)' },
        { char: 'h', example: 'hola', sound: 'всегда немая' },
        { char: 'rr / r-', example: 'perro', sound: 'раскатистое рр; одиночная r между гласными — один быстрый удар языка' },
        { char: 'z / c(+e,i)', example: 'zapato', sound: 'с в Латинской Америке; в Испании — межзубное с (язык между зубами, в русском такого нет)' },
        { char: 'v', example: 'vaso', sound: 'то же, что b — мягкое расслабленное б' },
        { char: 'qu', example: 'queso', sound: 'как к — u не читается' },
      ],
    },
  ],
}

const frenchRu: LanguageLetters = {
  intro: 'Французский живёт в гласных и в слитности речи. Конечные согласные обычно немые; акценты меняют качество гласного, а не ударение.',
  sections: [
    {
      title: 'Гласные и их акценты',
      rows: [
        { char: 'a / à / â', example: 'chat', sound: 'как а в «мама»' },
        { char: 'é', example: 'été', sound: 'узкое закрытое э — между э и и, без й на конце' },
        { char: 'è / ê / e(+2 согл.)', example: 'mère', sound: 'открытое э, как в «это»' },
        { char: 'e (без акцента)', example: 'le', sound: 'беглый нейтральный звук — как первое о в «молоко»; часто вовсе выпадает' },
        { char: 'i / î / y', example: 'ville', sound: 'как и в «мир»' },
        { char: 'o / ô', example: 'mot', sound: 'как о в «дом»' },
        { char: 'u / û', example: 'tu', sound: 'и с округлёнными губами — как гласный в «тюль»' },
        { char: 'ou', example: 'vous', sound: 'как у в «суп»' },
        { char: 'eu / œu', example: 'peu', sound: 'э с округлёнными губами (немецкая ö)' },
        { char: 'oi', example: 'moi', sound: 'как уа, слитно в один слог: moi = «муа»' },
        { char: 'au / eau', example: 'eau', sound: 'как о' },
        { char: 'ai / ei', example: 'maison', sound: 'как э' },
      ],
    },
    {
      title: 'Носовые гласные',
      note: 'Гласный + n/m в одном слоге = воздух идёт через нос, а сама n/m НЕ произносится.',
      rows: [
        { char: 'on / om', example: 'bon', sound: 'носовое о' },
        { char: 'an / en', example: 'enfant', sound: 'носовое а' },
        { char: 'in / ain / ein', example: 'vin', sound: 'носовое э (ближе к а)' },
        { char: 'un', example: 'un', sound: 'носовое ə (у многих говорящих сливается с in)' },
      ],
    },
    {
      title: 'Повадки согласных',
      rows: [
        { char: 'r', example: 'rouge', sound: 'картавое, грассирующее — в глубине горла' },
        { char: 'ç', example: 'garçon', sound: 'как с — хвостик сохраняет мягкое чтение c перед a/o/u' },
        { char: 'ch', example: 'chien', sound: 'как ш' },
        { char: 'gn', example: 'montagne', sound: 'как нь в «няня»' },
        { char: 'j / g(+e,i)', example: 'jour', sound: 'как ж' },
        { char: 'h', example: 'homme', sound: 'немая' },
        { char: 'final consonants', example: 'petit', sound: 'конечные согласные обычно немые — осторожнее с s, t, d, x' },
      ],
    },
  ],
}

const germanRu: LanguageLetters = {
  intro: 'Немецкий читается так, как пишется, — стоит лишь выучить умлауты и несколько буквосочетаний.',
  sections: [
    {
      title: 'Гласные и умлауты',
      rows: [
        { char: 'a', example: 'Haus', sound: 'как а в «мама»' },
        { char: 'ä', example: 'Mädchen', sound: 'как э в «это»' },
        { char: 'o', example: 'Brot', sound: 'как о в «дом»' },
        { char: 'ö', example: 'schön', sound: 'э с округлёнными губами' },
        { char: 'u', example: 'gut', sound: 'как у в «утро»' },
        { char: 'ü', example: 'über', sound: 'и с округлёнными губами — как гласный в «тюль»' },
        { char: 'ei', example: 'mein', sound: 'как ай' },
        { char: 'ie', example: 'Liebe', sound: 'долгое и' },
        { char: 'eu / äu', example: 'heute', sound: 'как ой' },
        { char: 'au', example: 'Auto', sound: 'как ау' },
      ],
    },
    {
      title: 'Сочетания согласных',
      rows: [
        { char: 'w', example: 'Wasser', sound: 'как в' },
        { char: 'v', example: 'Vater', sound: 'как ф' },
        { char: 'z', example: 'Zeit', sound: 'как ц' },
        { char: 's (+гласная)', example: 'Sonne', sound: 'как з' },
        { char: 'ß / ss', example: 'Straße', sound: 'чёткое с' },
        { char: 'sch', example: 'Schule', sound: 'как ш' },
        { char: 'st- / sp-', example: 'Straße', sound: 'шт / шп в начале слова' },
        { char: 'ch (после a/o/u)', example: 'Buch', sound: 'как русское х' },
        { char: 'ch (после e/i)', example: 'ich', sound: 'мягкое хь, как в «хитрый»' },
        { char: 'r', example: 'rot', sound: 'картавое, в глубине горла; в конце слова почти гласный (-er = «а»)' },
        { char: 'final b/d/g', example: 'Tag', sound: 'на конце слова оглушаются до п/т/к — в точности как в русском («год» → «гот»)' },
      ],
    },
  ],
}

const italianRu: LanguageLetters = {
  intro: 'Семь гласных звуков, чёткие двойные согласные и две буквы (c, g), которые смягчаются перед e и i.',
  sections: [
    {
      title: 'Гласные',
      rows: [
        { char: 'a / à', example: 'casa', sound: 'как а в «мама»' },
        { char: 'e / è', example: 'bene', sound: 'как э в «это» (é — более закрытое, ближе к е)' },
        { char: 'i / ì', example: 'vino', sound: 'как и в «мир»' },
        { char: 'o / ò', example: 'otto', sound: 'как о в «дом»' },
        { char: 'u / ù', example: 'uno', sound: 'как у в «утро»' },
      ],
    },
    {
      title: 'Система c/g',
      rows: [
        { char: 'c (+a,o,u)', example: 'casa', sound: 'как к' },
        { char: 'c (+e,i)', example: 'cena', sound: 'как ч' },
        { char: 'ch', example: 'chiave', sound: 'как к — h возвращает твёрдое чтение' },
        { char: 'g (+a,o,u)', example: 'gatto', sound: 'как г' },
        { char: 'g (+e,i)', example: 'gelato', sound: 'как дж в «джем»' },
        { char: 'gh', example: 'spaghetti', sound: 'как г — снова твёрдое' },
        { char: 'gn', example: 'gnocchi', sound: 'как нь в «няня»' },
        { char: 'gli', example: 'famiglia', sound: 'мягкое ль, как в «льют»' },
        { char: 'sc (+e,i)', example: 'pesce', sound: 'как ш' },
      ],
    },
    {
      title: 'Привычки',
      rows: [
        { char: 'double consonants', example: 'pizza', sound: 'двойные согласные держатся вдвое дольше — «пит-тса», а не «пи-тса»' },
        { char: 'z', example: 'zio', sound: 'как ц или дз' },
        { char: 'r', example: 'Roma', sound: 'раскатистое, как русское' },
        { char: 'h', example: 'hotel', sound: 'немая' },
      ],
    },
  ],
}

const catalanRu: LanguageLetters = {
  intro: 'В каталанском безударные гласные редуцируются (фирменная черта языка), а несколько написаний не встречаются больше нигде.',
  sections: [
    {
      title: 'Гласные',
      rows: [
        { char: 'a / à', example: 'casa', sound: 'под ударением а; без ударения — нейтральное ə, как первое о в «молоко»' },
        { char: 'e / é / è', example: 'més', sound: 'под ударением е/э; без ударения — то же нейтральное ə' },
        { char: 'i / í', example: 'nit', sound: 'как и в «мир»' },
        { char: 'o / ó / ò', example: 'porta', sound: 'под ударением о; без ударения превращается в у' },
        { char: 'u / ú', example: 'butxaca', sound: 'как у в «утро»' },
      ],
    },
    {
      title: 'Каталанские особинки',
      rows: [
        { char: 'ny', example: 'Catalunya', sound: 'как нь в «няня»' },
        { char: 'l·l', example: 'il·lusió', sound: '«летящая точка»: долгое л' },
        { char: 'x', example: 'xocolata', sound: 'как ш' },
        { char: 'tx', example: 'cotxe', sound: 'как ч' },
        { char: 'ç', example: 'plaça', sound: 'как с' },
        { char: 'j / g(+e,i)', example: 'jugar', sound: 'как ж' },
        { char: 'r final', example: 'cantar', sound: 'конечная r обычно немая' },
        { char: 'ig final', example: 'puig', sound: 'на конце слова — как ч' },
      ],
    },
  ],
}

const portugueseRu: LanguageLetters = {
  intro: 'Бразильский португальский: певучие гласные, знаменитые носовые звуки и согласные, которые удивляют даже испаноговорящих.',
  sections: [
    {
      title: 'Гласные и акценты',
      rows: [
        { char: 'a / á', example: 'casa', sound: 'как а в «мама»' },
        { char: 'â', example: 'câmera', sound: 'закрытое приглушённое а, ближе к ə' },
        { char: 'e / é', example: 'ela', sound: 'открытое э, как в «это»' },
        { char: 'ê', example: 'você', sound: 'узкое закрытое э, без й на конце' },
        { char: 'e final', example: 'nome', sound: 'в Бразилии конечное e сжимается до и' },
        { char: 'o / ó', example: 'avó', sound: 'широкое открытое о' },
        { char: 'ô', example: 'avô', sound: 'закрытое о — avó/avô различаются только этим!' },
        { char: 'o final', example: 'gato', sound: 'конечное o сжимается до у' },
        { char: 'u', example: 'tudo', sound: 'как у в «утро»' },
      ],
    },
    {
      title: 'Носовое семейство',
      note: 'Тильда (~) или следующая m/n пускает гласный через нос.',
      rows: [
        { char: 'ã', example: 'maçã', sound: 'носовое а' },
        { char: 'ão', example: 'pão', sound: 'носовое ау — самый португальский звук на свете' },
        { char: 'õe', example: 'ações', sound: 'носовое ой' },
        { char: 'em / en', example: 'bem', sound: 'носовое эй' },
        { char: 'im / in', example: 'sim', sound: 'носовое и' },
      ],
    },
    {
      title: 'Сюрпризы согласных',
      rows: [
        { char: 'ç', example: 'coração', sound: 'как с' },
        { char: 'ch', example: 'chuva', sound: 'как ш' },
        { char: 'lh', example: 'filho', sound: 'мягкое ль, как в «льют»' },
        { char: 'nh', example: 'ninho', sound: 'как нь в «няня»' },
        { char: 'j / g(+e,i)', example: 'hoje', sound: 'как ж' },
        { char: 'r- / rr', example: 'rio', sound: 'в Бразилии — лёгкое х на выдохе' },
        { char: 'ti / di', example: 'dia', sound: 'в большей части Бразилии — «чи» / «джи»' },
        { char: 'l final', example: 'Brasil', sound: 'превращается в краткое у (как белорусское ў) — «Бразиу»' },
      ],
    },
  ],
}

const romanianRu: LanguageLetters = {
  intro: 'Румынский читается почти как итальянский плюс пять собственных букв — и все пять регулярны.',
  sections: [
    {
      title: 'Пять особых букв',
      rows: [
        { char: 'ă', example: 'casă', sound: 'нейтральное ə — как первое о в «молоко»' },
        { char: 'â / î', example: 'în', sound: 'практически русская ы' },
        { char: 'ș', example: 'și', sound: 'как ш' },
        { char: 'ț', example: 'preț', sound: 'как ц' },
      ],
    },
    {
      title: 'Полезно знать',
      rows: [
        { char: 'c (+e,i)', example: 'ce', sound: 'как ч' },
        { char: 'che / chi', example: 'chelner', sound: 'как к' },
        { char: 'g (+e,i)', example: 'ger', sound: 'как дж в «джем»' },
        { char: 'ghe / ghi', example: 'ghid', sound: 'как г' },
        { char: 'j', example: 'jos', sound: 'как ж' },
        { char: 'r', example: 'repede', sound: 'раскатистое, как русское' },
        { char: '-i final', example: 'lupi', sound: 'шёпотное — едва слышный й' },
      ],
    },
  ],
}

// Турецкий: содержимое turkishRu из lettersL10n.ts, без изменений.
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

const swahiliRu: LanguageLetters = {
  intro: 'Суахили чудесно фонетичен: пять чистых гласных, ударение всегда на предпоследнем слоге.',
  sections: [
    {
      title: 'Гласные',
      rows: [
        { char: 'a', example: 'baba', sound: 'как а в «мама»' },
        { char: 'e', example: 'wewe', sound: 'как э в «это»' },
        { char: 'i', example: 'sisi', sound: 'как и в «мир»' },
        { char: 'o', example: 'moto', sound: 'как о в «дом»' },
        { char: 'u', example: 'kuku', sound: 'как у в «утро»' },
      ],
    },
    {
      title: 'Буквосочетания',
      rows: [
        { char: 'ny', example: 'nyumba', sound: 'как нь в «няня»' },
        { char: 'ng\'', example: 'ng\'ombe', sound: 'заднеязычное носовое н (как английское -ng) — в НАЧАЛЕ слога; в русском такого нет' },
        { char: 'ng (без апострофа)', example: 'ngoma', sound: 'нг с явным г, как в «манго»' },
        { char: 'dh', example: 'dhahabu', sound: 'звонкое межзубное з — язык между зубами (арабские заимствования)' },
        { char: 'th', example: 'thelathini', sound: 'глухое межзубное с — язык между зубами' },
        { char: 'gh', example: 'ghali', sound: 'картавое г, как украинское г (арабские заимствования)' },
        { char: 'ch', example: 'chai', sound: 'как ч' },
        { char: 'mb / nd / nj', example: 'mbwa', sound: 'м/н гудит прямо в следующий согласный — один такт' },
      ],
    },
  ],
}

const yorubaRu: LanguageLetters = {
  intro: 'Йоруба — тоновый язык: значки над буквами обозначают высоту тона, а не ударение. Две буквы с точкой отмечают открытые гласные.',
  sections: [
    {
      title: 'Гласные (7) + точки',
      rows: [
        { char: 'a', example: 'ata', sound: 'как а в «мама»' },
        { char: 'e', example: 'ewé', sound: 'узкое закрытое э, ближе к е' },
        { char: 'ẹ (с точкой)', example: 'ẹja', sound: 'открытое э, как в «это»' },
        { char: 'i', example: 'ilé', sound: 'как и в «мир»' },
        { char: 'o', example: 'owó', sound: 'закрытое о' },
        { char: 'ọ (с точкой)', example: 'ọmọ', sound: 'широкое открытое о — рот открыт шире обычного' },
        { char: 'u', example: 'imu', sound: 'как у в «утро»' },
      ],
    },
    {
      title: 'Тоны — три высоты',
      note: 'Те же буквы, другая высота — другое слово. Значки — это мелодия.',
      rows: [
        { char: 'á (высокий)', example: 'wá', sound: 'тон прыгает вверх' },
        { char: 'a (средний)', example: 'wa', sound: 'ровный, обычный тон' },
        { char: 'à (низкий)', example: 'wà', sound: 'тон падает вниз' },
      ],
    },
    {
      title: 'Согласные',
      rows: [
        { char: 'ṣ (с точкой)', example: 'ṣe', sound: 'как ш' },
        { char: 'gb', example: 'gbogbo', sound: 'г и б в один и тот же миг — в русском такого нет' },
        { char: 'p', example: 'pápá', sound: 'на самом деле кп, произнесённые одновременно' },
        { char: 'j', example: 'jẹun', sound: 'как дж в «джем»' },
      ],
    },
  ],
}

const hausaRu: LanguageLetters = {
  intro: 'Хауса (латиница boko) использует три буквы «с крючком» для звуков, которых нет в русском, — они хлопают или поскрипывают, а не текут.',
  sections: [
    {
      title: 'Гласные',
      note: 'Пять гласных, долгих или кратких, — долгота меняет смысл.',
      rows: [
        { char: 'a', example: 'ruwa', sound: 'как а (долгое — тяните)' },
        { char: 'e', example: 'gemu', sound: 'узкое закрытое э' },
        { char: 'i', example: 'kifi', sound: 'как и' },
        { char: 'o', example: 'doki', sound: 'как о' },
        { char: 'u', example: 'kudi', sound: 'как у' },
      ],
    },
    {
      title: 'Буквы с крючком',
      rows: [
        { char: 'ɓ', example: 'ɓera', sound: 'б, «схлопывающееся» внутрь — воздух хлопает вовнутрь' },
        { char: 'ɗ', example: 'ɗaki', sound: 'д, «схлопывающееся» внутрь' },
        { char: 'ƙ', example: 'ƙofa', sound: 'к с гортанным щелчком' },
        { char: '\'y', example: '\'ya\'ya', sound: 'скрипучее й' },
      ],
    },
    {
      title: 'Другие привычки',
      rows: [
        { char: 'ts', example: 'tsuntsu', sound: 'ц с гортанным щелчком' },
        { char: 'sh', example: 'shekara', sound: 'как ш' },
        { char: 'c', example: 'ci', sound: 'как ч' },
        { char: 'r', example: 'rana', sound: 'раскатистое или одноударное' },
      ],
    },
  ],
}

const xhosaRu: LanguageLetters = {
  intro: 'Коса знаменит щёлкающими согласными — три базовых клика, записываемых c, x, q. Остальное близко к привычному.',
  sections: [
    {
      title: 'Три клика',
      rows: [
        { char: 'c', example: 'cela', sound: 'зубной клик — укоризненное «ц-ц-ц», язык за зубами' },
        { char: 'x', example: 'ixesha', sound: 'боковой клик — звук «но-о!», которым понукают лошадь, сбоку рта' },
        { char: 'q', example: 'iqanda', sound: 'нёбный клик — «хлопок пробки» от нёба' },
        { char: 'gc / gx / gq', example: 'gqiba', sound: 'те же клики, озвончённые (гудите сквозь них)' },
        { char: 'nc / nx / nq', example: 'inqola', sound: 'те же клики с носовым гудением' },
      ],
    },
    {
      title: 'Гласные',
      rows: [
        { char: 'a', example: 'abantu', sound: 'как а' },
        { char: 'e', example: 'ewe', sound: 'как э в «это»' },
        { char: 'i', example: 'siza', sound: 'как и' },
        { char: 'o', example: 'onke', sound: 'открытое о' },
        { char: 'u', example: 'ubuntu', sound: 'как у' },
      ],
    },
    {
      title: 'Другие буквосочетания',
      rows: [
        { char: 'hl', example: 'hlala', sound: 'валлийское ll — глухое «шепелявое л», воздух выдувается по бокам языка' },
        { char: 'dl', example: 'indlela', sound: 'звонкий вариант hl' },
        { char: 'tsh', example: 'utshaba', sound: 'как ч' },
        { char: 'kh / th / ph', example: 'ukutya', sound: 'к/т/п с придыханием — с заметным выдохом' },
      ],
    },
  ],
}

const maoriRu: LanguageLetters = {
  intro: 'Те рео маори: пять гласных (кратких и долгих), восемь согласных, два диграфа. Каждый слог оканчивается на гласный.',
  sections: [
    {
      title: 'Гласные — краткие и долгие',
      note: 'Макрон (ā ē ī ō ū) удваивает долготу, а долгота меняет смысл.',
      rows: [
        { char: 'a / ā', example: 'aroha', sound: 'как а в «мама» (ā держится дольше)' },
        { char: 'e / ē', example: 'kete', sound: 'как э в «это»' },
        { char: 'i / ī', example: 'kiwi', sound: 'как и в «мир»' },
        { char: 'o / ō', example: 'moana', sound: 'как о в «дом»' },
        { char: 'u / ū', example: 'utu', sound: 'как у в «утро»' },
      ],
    },
    {
      title: 'Два диграфа',
      rows: [
        { char: 'wh', example: 'whānau', sound: 'как ф' },
        { char: 'ng', example: 'ngā', sound: 'заднеязычное носовое н (английское -ng) — даже в начале слова' },
      ],
    },
    {
      title: 'Согласные',
      rows: [
        { char: 'r', example: 'reo', sound: 'мягкий одноударный звук между р и л' },
        { char: 't', example: 'te', sound: 'мягкое т, почти без придыхания' },
        { char: 'k, m, n, p, h, w', example: 'kapa haka', sound: 'без сюрпризов: к, м, н, п, лёгкий выдох h и у-образное w' },
      ],
    },
  ],
}

const jamaicanRu: LanguageLetters = {
  intro: 'Патуа в орфографии Кассиди/JLU: один звук — одна буква, немых букв нет. Можете произнести — сможете и написать.',
  sections: [
    {
      title: 'Гласные',
      rows: [
        { char: 'a', example: 'bak', sound: 'как а в «мама»' },
        { char: 'aa', example: 'baal', sound: 'долгое а' },
        { char: 'e', example: 'bel', sound: 'как э в «это»' },
        { char: 'i', example: 'sik', sound: 'краткое и' },
        { char: 'ii', example: 'siik', sound: 'долгое и' },
        { char: 'o', example: 'pat', sound: 'открытое о' },
        { char: 'u', example: 'buk', sound: 'краткое у' },
        { char: 'uu', example: 'skuul', sound: 'долгое у' },
        { char: 'ie', example: 'kiek', sound: 'скользящее «иэ» — cake на ямайский лад' },
        { char: 'uo', example: 'guo', sound: 'скользящее «уо» — go на ямайский лад' },
        { char: 'ai', example: 'taim', sound: 'как ай' },
        { char: 'ou', example: 'bout', sound: 'как ау' },
      ],
    },
    {
      title: 'Повадки согласных',
      rows: [
        { char: 'k / g (+ya)', example: 'kyaan', sound: 'скольжение кь/гь — «кьяан» вместо английского can\'t' },
        { char: 'no th', example: 'tink / dis', sound: 'английское th становится простым т или д' },
        { char: 'no h-drop rule', example: 'ouse / haks', sound: 'h свободно появляется и исчезает — верны оба варианта' },
        { char: 'final clusters trim', example: 'las (last)', sound: 'последний согласный в скоплении отпадает' },
      ],
    },
  ],
}

const englishRu: LanguageLetters = {
  intro: 'Английская орфография — это история, а не фонетика. Здесь звуки, с которыми воюют ученики, и надёжные написания там, где они есть.',
  sections: [
    {
      title: 'Знаменитые звуки',
      rows: [
        { char: 'th (глухое)', example: 'think', sound: 'язык между зубами, выдох без голоса — межзубное «с»; в русском такого нет' },
        { char: 'th (звонкое)', example: 'this', sound: 'то же положение языка, но с голосом — межзубное «з»' },
        { char: 'w vs v', example: 'very wet', sound: 'w — губы округлены, зубы не участвуют (у-образный звук); v — зубы на губе, как русское в' },
        { char: 'r', example: 'red', sound: 'без раската и без картавости — загните язык назад, ничего им не касаясь' },
        { char: 'h', example: 'house', sound: 'лёгкий выдох, слабее русского х — и никогда не немой (кроме hour, honest)' },
      ],
    },
    {
      title: 'Гласные-ловушки',
      rows: [
        { char: 'i (краткое)', example: 'ship', sound: 'расслабленное краткое и с призвуком ы — НЕ «шиип»' },
        { char: 'ee', example: 'sheep', sound: 'долгое напряжённое и' },
        { char: 'a (краткое)', example: 'cat', sound: 'широкое э с сильно открытой челюстью — между а и э' },
        { char: 'u (краткое)', example: 'cup', sound: 'краткое а, как безударное а в «сама»' },
        { char: 'er / unstressed', example: 'teacher', sound: 'шва — самый ленивый гласный, как первое о в «молоко»; в нём живёт большинство безударных слогов' },
      ],
    },
    {
      title: 'Написания, которым можно доверять',
      rows: [
        { char: 'magic e', example: 'hat → hate', sound: 'немая конечная e заставляет гласную читаться как в алфавите' },
        { char: '-tion', example: 'station', sound: '«шн»' },
        { char: 'ough', example: 'though / tough', sound: 'увы — шесть разных чтений; учите каждое слово отдельно' },
      ],
    },
  ],
}

const dutchRu: LanguageLetters = {
  intro: 'Голландская орфография дружелюбна — несколько буквосочетаний и один знаменитый гласный (ui) делают всю погоду.',
  sections: [
    {
      title: 'Команды гласных',
      rows: [
        { char: 'aa / a', example: 'water', sound: 'долгое а / краткое а — удвоение обозначает долготу' },
        { char: 'ee / e', example: 'been', sound: 'долгое закрытое э (почти «эй») / краткое э; конечная -e — беглое ə' },
        { char: 'oo / o', example: 'boom', sound: 'долгое о / краткое о' },
        { char: 'uu / u', example: 'muur', sound: 'и с округлёнными губами (как в «тюль») / краткое ə' },
        { char: 'ie', example: 'niet', sound: 'как и' },
        { char: 'oe', example: 'boek', sound: 'как у' },
        { char: 'eu', example: 'leuk', sound: 'э с округлёнными губами' },
        { char: 'ij / ei', example: 'ijs', sound: 'между ай и эй — знаменитый голландский дифтонг, два написания' },
        { char: 'ui', example: 'huis', sound: 'аналога нет: скажите «ау» с плотно округлёнными губами' },
        { char: 'ou / au', example: 'oud', sound: 'как ау' },
      ],
    },
    {
      title: 'Повадки согласных',
      rows: [
        { char: 'g / ch', example: 'goed', sound: 'голландский скрежет — жёсткое русское х (на юге мягче)' },
        { char: 'sch', example: 'school', sound: 'с + этот же х: «с-хол»' },
        { char: 'w', example: 'water', sound: 'между в и английским w' },
        { char: 'v', example: 'vader', sound: 'между в и ф' },
        { char: 'j', example: 'ja', sound: 'как й' },
        { char: 'r', example: 'rood', sound: 'раскатистое или картавое — годится любое' },
        { char: '-en (окончание)', example: 'lopen', sound: 'конечное n часто отпадает: «lope(n)»' },
        { char: '-tje', example: 'kopje', sound: 'машинка уменьшительных — koppje, huisje, momentje' },
      ],
    },
  ],
}

const russianRu: LanguageLetters = {
  intro: 'Кириллица — 33 буквы. Почти каждая читается одним и тем же звуком; главное — система из пяти пар гласных «твёрдый/мягкий ряд».',
  sections: [
    {
      title: 'Гласные — твёрдый ряд',
      note: 'Не смягчают согласный перед собой.',
      rows: [
        { char: 'а', roman: 'a', example: 'мама', sound: 'а, как в «мама»' },
        { char: 'э', roman: 'e', example: 'это', sound: 'э, как в «это»' },
        { char: 'ы', roman: 'y', example: 'мы', sound: 'ы, как в «мы» — язык оттянут назад' },
        { char: 'о', roman: 'o', example: 'дом', sound: 'о, как в «дом» (только под ударением)' },
        { char: 'у', roman: 'u', example: 'утро', sound: 'у, как в «утро»' },
      ],
    },
    {
      title: 'Гласные — мягкий ряд',
      note: 'Те же гласные звуки, но они смягчают согласный перед собой (прячут в себе й-призвук).',
      rows: [
        { char: 'я', roman: 'ya', example: 'яблоко', sound: 'йа, как в «яблоко»' },
        { char: 'е', roman: 'e/ye', example: 'нет', sound: 'йэ, как в «нет»' },
        { char: 'и', roman: 'i', example: 'мир', sound: 'и, как в «мир»' },
        { char: 'ё', roman: 'yo', example: 'ёлка', sound: 'йо, как в «ёлка» (всегда под ударением)' },
        { char: 'ю', roman: 'yu', example: 'юг', sound: 'йу, как в «юг»' },
      ],
    },
    {
      title: 'Согласные, похожие на латинские буквы (но это не они)',
      rows: [
        { char: 'в', roman: 'v', example: 'вода', sound: 'в, как в «вода» (не латинская b)' },
        { char: 'н', roman: 'n', example: 'нос', sound: 'н, как в «нос» (не латинская h)' },
        { char: 'р', roman: 'r', example: 'рука', sound: 'раскатистое р, как в «рука»' },
        { char: 'с', roman: 's', example: 'сок', sound: 'с, как в «сок» (не латинская c = к)' },
        { char: 'у', roman: 'u', example: 'ум', sound: 'у — выглядит как латинская y, но читается всегда «у»' },
        { char: 'х', roman: 'h/x', example: 'хлеб', sound: 'х, как в «хлеб»' },
      ],
    },
    {
      title: 'Остальные согласные',
      rows: [
        { char: 'б', roman: 'b', example: 'брат', sound: 'б, как в «брат»' },
        { char: 'г', roman: 'g', example: 'год', sound: 'г, как в «год»' },
        { char: 'д', roman: 'd', example: 'да', sound: 'д, как в «да»' },
        { char: 'ж', roman: 'zh', example: 'жить', sound: 'ж, как в «жить» — всегда твёрдое' },
        { char: 'з', roman: 'z', example: 'зима', sound: 'з, как в «зима»' },
        { char: 'й', roman: 'j', example: 'мой', sound: 'й, как в «мой»' },
        { char: 'к', roman: 'k', example: 'кот', sound: 'к, как в «кот»' },
        { char: 'л', roman: 'l', example: 'лампа', sound: 'л, как в «лампа»' },
        { char: 'м', roman: 'm', example: 'мост', sound: 'м, как в «мост»' },
        { char: 'п', roman: 'p', example: 'папа', sound: 'п, как в «папа»' },
        { char: 'т', roman: 't', example: 'там', sound: 'т, как в «там»' },
        { char: 'ф', roman: 'f', example: 'фото', sound: 'ф, как в «фото»' },
        { char: 'ц', roman: 'c/ts', example: 'цирк', sound: 'ц, как в «цирк»' },
        { char: 'ч', roman: 'ch', example: 'чай', sound: 'ч, как в «чай» — всегда мягкое' },
        { char: 'ш', roman: 'sh', example: 'школа', sound: 'ш, как в «школа» — всегда твёрдое' },
        { char: 'щ', roman: 'shch', example: 'щи', sound: 'долгое мягкое щ, как в «щи»' },
      ],
    },
    {
      title: 'Два немых знака',
      rows: [
        { char: 'ь', roman: '\'', example: 'день', sound: 'мягкий знак — смягчает согласный перед собой (добавляет намёк на й)' },
        { char: 'ъ', roman: '\'\'', example: 'объект', sound: 'твёрдый знак — крошечная пауза между приставкой и корнем' },
      ],
    },
    {
      title: 'Печать и курсив (и рукопись)',
      note: 'У печатной кириллицы два лица. В курсиве — и тем более в рукописи — несколько букв принимают форму ДРУГИХ, латинских на вид, букв. Буква и звук те же: сравните каждую пару «прямая/курсивная».',
      italics: true,
      rows: [
        { char: 'т', roman: 't', example: 'там', sound: 'курсивная т выглядит как m — но это всё та же т' },
        { char: 'и', roman: 'i', example: 'мир', sound: 'курсивная и выглядит как u — но это всё та же и' },
        { char: 'й', roman: 'j', example: 'мой', sound: 'курсивная й — та же u-форма с дужкой сверху' },
        { char: 'п', roman: 'p', example: 'папа', sound: 'курсивная п выглядит как n — но это всё та же п' },
        { char: 'д', roman: 'd', example: 'да', sound: 'курсивная д выглядит как g — но это всё та же д' },
        { char: 'г', roman: 'g', example: 'год', sound: 'курсивная г похожа на зеркальную s — но это всё та же г' },
      ],
    },
  ],
}

const greekRu: LanguageLetters = {
  intro: 'Греческий алфавит — 24 буквы. Кириллица выросла из греческого, так что половина работы уже сделана.',
  sections: [
    {
      title: 'Гласные',
      note: 'В новогреческом всего пять гласных звуков; несколько написаний делят их между собой.',
      rows: [
        { char: 'α', roman: 'a', example: 'αγάπη', sound: 'как а в «мама»' },
        { char: 'ε', roman: 'e', example: 'ένα', sound: 'как э в «это»' },
        { char: 'η', roman: 'h/i', example: 'ημέρα', sound: 'как и в «мир»' },
        { char: 'ι', roman: 'i', example: 'ιδέα', sound: 'как и в «мир»' },
        { char: 'ο', roman: 'o', example: 'όχι', sound: 'как о в «дом»' },
        { char: 'υ', roman: 'u/y', example: 'ύπνος', sound: 'как и — да, тоже и' },
        { char: 'ω', roman: 'w', example: 'ώρα', sound: 'как о — то же, что ο' },
      ],
    },
    {
      title: 'Согласные',
      rows: [
        { char: 'β', roman: 'v/b', example: 'βιβλίο', sound: 'как в (не б!)' },
        { char: 'γ', roman: 'g', example: 'γάλα', sound: 'картавое г, как украинское г; перед э/и — как й' },
        { char: 'δ', roman: 'd', example: 'δέκα', sound: 'звонкое межзубное з — язык между зубами (не д!)' },
        { char: 'ζ', roman: 'z', example: 'ζωή', sound: 'как з' },
        { char: 'θ', roman: 'th', example: 'θάλασσα', sound: 'глухое межзубное с — язык между зубами; в русском такого нет' },
        { char: 'κ', roman: 'k', example: 'καλά', sound: 'как к' },
        { char: 'λ', roman: 'l', example: 'λέξη', sound: 'как л' },
        { char: 'μ', roman: 'm', example: 'μητέρα', sound: 'как м' },
        { char: 'ν', roman: 'n', example: 'νερό', sound: 'как н (выглядит как v!)' },
        { char: 'ξ', roman: 'x', example: 'ξένος', sound: 'как кс' },
        { char: 'π', roman: 'p', example: 'πατέρας', sound: 'как п' },
        { char: 'ρ', roman: 'r', example: 'ρολόι', sound: 'слегка раскатистое р (выглядит как p!)' },
        { char: 'σ/ς', roman: 's', example: 'σπίτι', sound: 'как с; ς пишется только в конце слова' },
        { char: 'τ', roman: 't', example: 'τρία', sound: 'как т' },
        { char: 'φ', roman: 'f', example: 'φίλος', sound: 'как ф' },
        { char: 'χ', roman: 'ch', example: 'χέρι', sound: 'как русское х' },
        { char: 'ψ', roman: 'ps', example: 'ψωμί', sound: 'как пс — даже в начале слова' },
      ],
    },
    {
      title: 'Частые пары',
      note: 'Две буквы — один звук; учите их как единое целое.',
      rows: [
        { char: 'ου', roman: 'ou', example: 'ουρανός', sound: 'как у' },
        { char: 'αι', roman: 'ai', example: 'παιδί', sound: 'как э' },
        { char: 'ει/οι', roman: 'ei/oi', example: 'είναι', sound: 'как и' },
        { char: 'μπ', roman: 'mp', example: 'μπανάνα', sound: 'б в начале слова; мб внутри' },
        { char: 'ντ', roman: 'nt', example: 'ντομάτα', sound: 'д в начале слова; нд внутри' },
        { char: 'γγ/γκ', roman: 'gg/gk', example: 'αγγλικά', sound: 'г / нг-г' },
      ],
    },
  ],
}

const arabicRu: LanguageLetters = {
  intro: 'Арабский абджад — 28 букв, письмо справа налево. Буквы соединяются и меняют форму в зависимости от позиции; краткие гласные обычно не записываются.',
  sections: [
    {
      title: 'Как буквы соединяются',
      note: 'Арабское письмо связное по правилу: у большинства букв четыре формы — отдельная, начальная, срединная, конечная — и они цепляются к соседям.',
      rows: [
        { char: 'م ح م د → محمد', roman: 'm-H-m-d', example: 'محمد', sound: 'те же буквы, но соединённые: каждая меняет форму по позиции' },
        { char: 'ب ـبـ ـب', roman: 'b', example: 'باب', sound: 'одна буква, три соединённые формы: начальная, срединная, конечная' },
        { char: 'ا د ر ز و', roman: '(non-joiners)', example: 'دار', sound: 'шесть букв никогда не соединяются ВПЕРЁД — они создают разрыв внутри слова' },
        { char: 'ل + ا → لا', roman: 'laa', example: 'سلام', sound: 'лям + алиф сливаются в особую лигатуру лям-алиф' },
      ],
    },
    {
      title: 'Долгие гласные и глайды',
      positions: true,
      rows: [
        { char: 'ا', roman: 'aa', example: 'باب', sound: 'долгое а, как в «мама», но тяните' },
        { char: 'و', roman: 'w/uu', example: 'نور', sound: 'у-образный согласный (английское w) или долгое у' },
        { char: 'ي', roman: 'y/ii', example: 'كبير', sound: 'й или долгое и' },
      ],
    },
    {
      title: 'В основном знакомые звуки',
      note: 'Каждая буква показана во всех четырёх позициях: отдельно, а также в начале, середине и конце слова.',
      positions: true,
      rows: [
        { char: 'ب', roman: 'b', example: 'بيت', sound: 'б, как в «брат»' },
        { char: 'ت', roman: 't', example: 'تفاح', sound: 'т, как в «там»' },
        { char: 'ث', roman: 'th', example: 'ثلاثة', sound: 'глухое межзубное с — язык между зубами; в русском такого нет' },
        { char: 'ج', roman: 'j', example: 'جمل', sound: 'дж, как в «джем»' },
        { char: 'د', roman: 'd', example: 'دار', sound: 'д, как в «да»' },
        { char: 'ذ', roman: 'dh', example: 'هذا', sound: 'звонкое межзубное з — язык между зубами' },
        { char: 'ر', roman: 'r', example: 'رجل', sound: 'раскатистое р, как русское' },
        { char: 'ز', roman: 'z', example: 'زيت', sound: 'з, как в «зима»' },
        { char: 'س', roman: 's', example: 'سلام', sound: 'с, как в «сок»' },
        { char: 'ش', roman: 'sh', example: 'شمس', sound: 'ш, как в «школа»' },
        { char: 'ف', roman: 'f', example: 'فيل', sound: 'ф, как в «фото»' },
        { char: 'ك', roman: 'k', example: 'كتاب', sound: 'к, как в «кот»' },
        { char: 'ل', roman: 'l', example: 'ليل', sound: 'л, как в «лампа»' },
        { char: 'م', roman: 'm', example: 'ماء', sound: 'м, как в «мост»' },
        { char: 'ن', roman: 'n', example: 'نار', sound: 'н, как в «нос»' },
        { char: 'ه', roman: 'h', example: 'هنا', sound: 'лёгкий выдох-h, заметно слабее русского х' },
      ],
    },
    {
      title: 'Новые звуки',
      note: 'Рождаются глубже в горле, чем любой русский звук, — слушайте и повторяйте.',
      positions: true,
      rows: [
        { char: 'ح', roman: 'H / 7', example: 'حب', sound: 'сдавленный выдох из глубины горла — как будто дышите на замёрзшее стекло, только резче' },
        { char: 'خ', roman: 'kh / 5', example: 'خبز', sound: 'практически русское х, только жёстче' },
        { char: 'ع', roman: '3', example: 'عين', sound: 'сжатый горлом гласный — аналога нет; вслушивайтесь' },
        { char: 'غ', roman: 'gh', example: 'غرب', sound: 'картавое гортанное г — как французское р' },
        { char: 'ق', roman: 'q', example: 'قلب', sound: 'к, оттянутое в самую глубину рта' },
        { char: 'ء', roman: '2 / \'', example: 'سؤال', sound: 'гортанная смычка — запинка, как в «не-а»' },
      ],
    },
    {
      title: 'Эмфатическая четвёрка',
      note: 'Тяжёлые близнецы т/д/с/з: язык прогибается назад, и всё слово «темнеет».',
      positions: true,
      rows: [
        { char: 'ص', roman: 'S', example: 'صباح', sound: 'тяжёлое с' },
        { char: 'ض', roman: 'D', example: 'ضوء', sound: 'тяжёлое д' },
        { char: 'ط', roman: 'T', example: 'طعام', sound: 'тяжёлое т' },
        { char: 'ظ', roman: 'Z', example: 'ظهر', sound: 'тяжёлое з' },
      ],
    },
    {
      title: 'Краткие гласные (харакаты)',
      note: 'Маленькие значки над и под буквой — вне учебных текстов их обычно не пишут.',
      rows: [
        { char: 'ـَ', roman: 'a', example: 'فَتَحَ', sound: 'краткое а (фатха)' },
        { char: 'ـِ', roman: 'i', example: 'بِنت', sound: 'краткое и (кясра)' },
        { char: 'ـُ', roman: 'u', example: 'كُتُب', sound: 'краткое у (дамма)' },
        { char: 'ـّ', roman: '(double)', example: 'مُدَرِّس', sound: 'шадда — держите согласный вдвое дольше' },
      ],
    },
  ],
}

const hindiRu: LanguageLetters = {
  intro: 'Деванагари — каждый согласный несёт встроенное «а»; огласовки (матры) его заменяют. Главные звуки: ретрофлексные буквы (язык загнут назад) против зубных (язык у зубов, как в русском) и пары с придыханием — с лишним выдохом.',
  sections: [
    {
      title: 'Как буквы соединяются',
      note: 'Деванагари строит слоги: огласовки крепятся к согласным, а вирама (्) сваривает согласные в лигатуры.',
      rows: [
        { char: 'क + ा → का', roman: 'k + aa', example: 'काम', sound: 'огласовка (матра) заменяет встроенное а' },
        { char: 'क + ि → कि', roman: 'k + i', example: 'किताब', sound: 'матра для и пишется СЛЕВА от согласного' },
        { char: 'स + ् + त → स्त', roman: 's+t', example: 'नमस्ते', sound: 'вирама убирает а и сливает пару в один кластер' },
        { char: 'क + ् + ष → क्ष', roman: 'ksh', example: 'क्षमा', sound: 'некоторые кластеры получают совершенно новую форму — частые запоминайте на глаз' },
        { char: 'र special', roman: 'r', example: 'कर्म / प्रेम', sound: 'р пишется НАД кластером, если идёт первым (कर्म), и косым штрихом снизу, если вторым (प्रेम)' },
      ],
    },
    {
      title: 'Самостоятельные гласные',
      note: 'Используются в начале слова; внутри слов превращаются в матры (следующий раздел).',
      rows: [
        { char: 'अ', roman: 'a', example: 'अब', sound: 'краткое нейтральное а — как безударное а в «сама»' },
        { char: 'आ', roman: 'aa', example: 'आम', sound: 'долгое а, как в «мама», но тяните' },
        { char: 'इ', roman: 'i', example: 'इधर', sound: 'краткое и' },
        { char: 'ई', roman: 'ii', example: 'ईद', sound: 'долгое и' },
        { char: 'उ', roman: 'u', example: 'उधर', sound: 'краткое у' },
        { char: 'ऊ', roman: 'uu', example: 'ऊपर', sound: 'долгое у' },
        { char: 'ए', roman: 'e', example: 'एक', sound: 'закрытое э, без й на конце' },
        { char: 'ऐ', roman: 'ai', example: 'ऐनक', sound: 'широкое э, между а и э' },
        { char: 'ओ', roman: 'o', example: 'ओर', sound: 'чистое закрытое о' },
        { char: 'औ', roman: 'au', example: 'औरत', sound: 'широкое открытое о' },
      ],
    },
    {
      title: 'Те же гласные как матры',
      note: 'क показана как носитель. Встроенное अ значка не требует.',
      rows: [
        { char: 'का', roman: 'kaa', example: 'काम', sound: 'к + долгое а' },
        { char: 'कि', roman: 'ki', example: 'किताब', sound: 'к + и (значок идёт ПЕРЕД буквой)' },
        { char: 'की', roman: 'kii', example: 'की', sound: 'к + долгое и' },
        { char: 'कु', roman: 'ku', example: 'कुछ', sound: 'к + у' },
        { char: 'कू', roman: 'kuu', example: 'कूद', sound: 'к + долгое у' },
        { char: 'के', roman: 'ke', example: 'के', sound: 'к + закрытое э' },
        { char: 'कै', roman: 'kai', example: 'कैसा', sound: 'к + широкое э' },
        { char: 'को', roman: 'ko', example: 'को', sound: 'к + о' },
        { char: 'कौ', roman: 'kau', example: 'कौन', sound: 'к + открытое о' },
        { char: 'कं', roman: 'kaM', example: 'कंघी', sound: 'носовой призвук после гласного (анусвара)' },
      ],
    },
    {
      title: 'Согласные — пары с придыханием',
      note: 'Второй звук каждой пары добавляет выдох (поднесите ладонь ко рту — вы должны его почувствовать).',
      rows: [
        { char: 'क / ख', roman: 'k / kh', example: 'खाना', sound: 'к обычное, затем к + выдох' },
        { char: 'ग / घ', roman: 'g / gh', example: 'घर', sound: 'г обычное, затем г + выдох' },
        { char: 'च / छ', roman: 'ch / chh', example: 'छह', sound: 'ч обычное, затем ч + выдох' },
        { char: 'ज / झ', roman: 'j / jh', example: 'झील', sound: 'дж обычное, затем дж + выдох' },
        { char: 'प / फ', roman: 'p / ph', example: 'फल', sound: 'п обычное, затем п + выдох' },
        { char: 'ब / भ', roman: 'b / bh', example: 'भाई', sound: 'б обычное, затем б + выдох' },
      ],
    },
    {
      title: 'Ретрофлексные против зубных — главный водораздел',
      note: 'Ретрофлексные: кончик языка загнут назад к нёбу. Зубные: язык у зубов — то есть практически русские т/д.',
      rows: [
        { char: 'ट / ठ', roman: 'T / Th', example: 'टमाटर', sound: 'ретрофлексное т (обычное / + выдох)' },
        { char: 'ड / ढ', roman: 'D / Dh', example: 'डर', sound: 'ретрофлексное д (обычное / + выдох)' },
        { char: 'ण', roman: 'N', example: 'बाण', sound: 'ретрофлексное н' },
        { char: 'त / थ', roman: 't / th', example: 'तीन', sound: 'зубное т — как русское т (обычное / + выдох)' },
        { char: 'द / ध', roman: 'd / dh', example: 'दो', sound: 'зубное д — как русское д (обычное / + выдох)' },
        { char: 'न', roman: 'n', example: 'नाम', sound: 'н, как в «нос»' },
        { char: 'ड़ / ढ़', roman: 'R / Rh', example: 'लड़का', sound: 'р-шлепок: язык срывается вниз из ретрофлексного положения' },
      ],
    },
    {
      title: 'Остальные',
      rows: [
        { char: 'म', roman: 'm', example: 'माँ', sound: 'м, как в «мост»' },
        { char: 'य', roman: 'y', example: 'यह', sound: 'й, как в «йога»' },
        { char: 'र', roman: 'r', example: 'रात', sound: 'лёгкое одноударное р' },
        { char: 'ल', roman: 'l', example: 'लाल', sound: 'л, как в «лампа»' },
        { char: 'व', roman: 'v/w', example: 'वह', sound: 'между в и у-образным w' },
        { char: 'श / ष', roman: 'sh / Sh', example: 'शहर', sound: 'ш, чуть мягче русского — ближе к щ' },
        { char: 'स', roman: 's', example: 'सात', sound: 'с, как в «сок»' },
        { char: 'ह', roman: 'h', example: 'हाँ', sound: 'лёгкий выдох-h, слабее русского х' },
      ],
    },
    {
      title: 'Буквы с нуктой (заимствованные звуки)',
      note: 'Точка под буквой обозначает персидско-арабские звуки.',
      rows: [
        { char: 'ज़', roman: 'z', example: 'ज़रूर', sound: 'з, как в «зима»' },
        { char: 'फ़', roman: 'f', example: 'फ़ोन', sound: 'ф, как в «фото»' },
        { char: 'क़', roman: 'q', example: 'क़लम', sound: 'заднее к — из самой глубины рта' },
        { char: 'ख़ / ग़', roman: 'kh / gh', example: 'ख़बर', sound: 'русское х / картавое г' },
      ],
    },
  ],
}

const thaiRu: LanguageLetters = {
  intro: 'Тайское письмо: 44 согласных трёх КЛАССОВ (класс вместе с тоновым знаком задаёт тон), гласные, которые крепятся вокруг согласного, и никаких пробелов между словами.',
  sections: [
    {
      title: 'Как буквы соединяются',
      note: 'Гласные обвивают свой согласный — спереди, сзади, сверху или снизу, а тоновые знаки ставятся сверху.',
      rows: [
        { char: 'ก + า → กา', roman: 'k + aa', example: 'กาแฟ', sound: 'этот гласный идёт после согласного' },
        { char: 'ก + ิ → กิ', roman: 'k + i', example: 'กิน', sound: 'этот гласный сидит СВЕРХУ' },
        { char: 'ก + ุ → กุ', roman: 'k + u', example: 'กุ้ง', sound: 'этот гласный висит СНИЗУ' },
        { char: 'เ + ก → เก', roman: 'k + e', example: 'เกาะ', sound: 'этот гласный пишется ПЕРЕД согласным, после которого произносится' },
        { char: 'เ-ีย, เ-ือ', roman: 'ia, uea', example: 'เมีย', sound: 'составные гласные окружают согласный с двух-трёх сторон' },
        { char: 'ก่ ก้ ก๊ ก๋', roman: 'tones', example: 'ไม่', sound: 'четыре тоновых знака ставятся сверху; что они означают — решает класс согласного' },
      ],
    },
    {
      title: 'Повседневные согласные (средний класс)',
      rows: [
        { char: 'ก', roman: 'g/k', example: 'ไก่', sound: 'к без выдоха — на слух между г и к' },
        { char: 'จ', roman: 'j', example: 'จาน', sound: 'чёткое ч/дж без выдоха' },
        { char: 'ด', roman: 'd', example: 'เด็ก', sound: 'д, как в «да»' },
        { char: 'ต', roman: 'dt', example: 'ตา', sound: 'между д и т — т без выдоха' },
        { char: 'บ', roman: 'b', example: 'บ้าน', sound: 'б, как в «брат»' },
        { char: 'ป', roman: 'bp', example: 'ปลา', sound: 'между б и п — п без выдоха' },
        { char: 'อ', roman: '(silent)', example: 'อาหาร', sound: 'немой согласный-носитель для одиноких гласных' },
      ],
    },
    {
      title: 'Согласные с придыханием (пары высокого и низкого классов)',
      note: 'Звук тот же, класс другой — а класс меняет ТОН слога.',
      rows: [
        { char: 'ข / ค', roman: 'kh', example: 'ขาว / ควาย', sound: 'к + выдох (высокий класс / низкий класс)' },
        { char: 'ถ / ท', roman: 'th', example: 'ถนน / ทำ', sound: 'т + выдох (высокий / низкий)' },
        { char: 'ผ / พ', roman: 'ph', example: 'ผม / พ่อ', sound: 'п + выдох — никогда не ф! (высокий / низкий)' },
        { char: 'ฝ / ฟ', roman: 'f', example: 'ฝน / ไฟ', sound: 'ф, как в «фото» (высокий / низкий)' },
        { char: 'ส / ซ', roman: 's', example: 'สวย / ซ้าย', sound: 'с (высокий / низкий)' },
        { char: 'ห / ฮ', roman: 'h', example: 'หก / ฮา', sound: 'лёгкий выдох-h (высокий / низкий); ห к тому же беззвучно повышает класс следующей буквы' },
      ],
    },
    {
      title: 'Сонорные и остальные',
      rows: [
        { char: 'ม', roman: 'm', example: 'แม่', sound: 'м, как в «мост»' },
        { char: 'น / ณ', roman: 'n', example: 'น้ำ', sound: 'н, как в «нос»' },
        { char: 'ง', roman: 'ng', example: 'งู', sound: 'заднеязычное носовое н (английское -ng) — даже в НАЧАЛЕ слова' },
        { char: 'ร', roman: 'r', example: 'รถ', sound: 'раскатистое р (в беглой речи часто превращается в л)' },
        { char: 'ล', roman: 'l', example: 'ลิง', sound: 'л, как в «лампа»' },
        { char: 'ว', roman: 'w', example: 'วัน', sound: 'у-образный согласный, как английское w' },
        { char: 'ย / ญ', roman: 'y', example: 'ยา', sound: 'й, как в «йога»' },
        { char: 'ช', roman: 'ch', example: 'ช้าง', sound: 'ч + выдох' },
      ],
    },
    {
      title: 'Основные гласные (показаны на ก)',
      note: 'Краткость и долгота меняют смысл — долгие заметно тяните.',
      rows: [
        { char: 'กะ / กา', roman: 'a / aa', example: 'มา', sound: 'а краткое / долгое' },
        { char: 'กิ / กี', roman: 'i / ii', example: 'มี', sound: 'и краткое / долгое' },
        { char: 'กุ / กู', roman: 'u / uu', example: 'ดู', sound: 'у краткое / долгое' },
        { char: 'เกะ / เก', roman: 'e', example: 'เย็น', sound: 'э краткое / долгое закрытое' },
        { char: 'โกะ / โก', roman: 'o', example: 'โต', sound: 'о краткое / долгое' },
        { char: 'ไก / ใก', roman: 'ai', example: 'ไป', sound: 'ай — два написания, один звук' },
        { char: 'เกา', roman: 'ao', example: 'เก้า', sound: 'как ау' },
        { char: 'กือ', roman: 'ue', example: 'มือ', sound: 'почти русская ы — у с растянутыми губами' },
      ],
    },
    {
      title: 'Пять тонов',
      note: 'Один слог — пять смыслов. Тон складывается из класса согласного + тонового знака + типа слога.',
      rows: [
        { char: 'มา (средний)', roman: 'maa', example: 'มา', sound: 'ровный тон — «приходить»' },
        { char: 'หม่า (низкий)', roman: 'màa', example: 'ไม่', sound: 'начинается низко и остаётся низко' },
        { char: 'ม้า (высокий… нисходящий)', roman: 'máa', example: 'ม้า', sound: 'высокий тон — «лошадь»' },
        { char: 'หม้า (нисходящий)', roman: 'mâa', example: 'บ้าน', sound: 'падает с высокого к низкому' },
        { char: 'หมา (восходящий)', roman: 'mǎa', example: 'หมา', sound: 'проседает и поднимается — «собака» (не перепутайте лошадь с собакой!)' },
      ],
    },
  ],
}

const koreanRu: LanguageLetters = {
  intro: 'Хангыль — 24 базовые буквы, которые СОБИРАЮТСЯ в слоговые блоки. Изобретён в 1443 году, чтобы выучиваться за одно утро; формы букв даже рисуют положение рта.',
  sections: [
    {
      title: 'Как буквы соединяются',
      note: 'Буквы складываются в квадратные слоговые блоки: согласный + гласный и необязательный конечный согласный (받침) снизу. 한국 — шесть букв в двух блоках.',
      rows: [
        { char: 'ㅎ + ㅏ + ㄴ → 한', roman: 'h + a + n', example: '한국', sound: 'согласный слева, вертикальный гласный справа, конечная буква снизу' },
        { char: 'ㄱ + ㅜ + ㄱ → 국', roman: 'g + u + k', example: '한국', sound: 'горизонтальные гласные идут ПОД первым согласным' },
        { char: 'ㅅ + ㅏ → 사', roman: 's + a', example: '사람', sound: 'без конечной буквы — просто согласный + гласный' },
        { char: 'ㅇ + ㅜ → 우', roman: '(silent) + u', example: '우유', sound: 'ㅇ — немая заглушка, когда блок начинается с гласного' },
        { char: 'ㅂ + ㅏ + ㅂ → 밥', roman: 'b + a + p', example: '밥', sound: 'конечный ㅂ (받침) закрывает слог' },
        { char: '받침 rule', roman: 'finals', example: '있다', sound: 'закрывать блок могут лишь 7 звуков: к, н, т, ль, м, п, нг — написание хранит букву, рот упрощает' },
      ],
    },
    {
      title: 'Простые согласные',
      rows: [
        { char: 'ㄱ', roman: 'g/k', example: '가다', sound: 'между г и к' },
        { char: 'ㄴ', roman: 'n', example: '나', sound: 'н, как в «нос»' },
        { char: 'ㄷ', roman: 'd/t', example: '돈', sound: 'между д и т' },
        { char: 'ㄹ', roman: 'r/l', example: '물', sound: 'одноударное р между гласными; ль в конце блока' },
        { char: 'ㅁ', roman: 'm', example: '몸', sound: 'м, как в «мама»' },
        { char: 'ㅂ', roman: 'b/p', example: '밥', sound: 'между б и п' },
        { char: 'ㅅ', roman: 's', example: '사람', sound: 'с, как в «сок»; перед ㅣ — щ-образное' },
        { char: 'ㅇ', roman: '-/ng', example: '강', sound: 'немой в начале блока; в конце — заднеязычное носовое н (английское -ng)' },
        { char: 'ㅈ', roman: 'j', example: '집', sound: 'между дж и ч' },
        { char: 'ㅎ', roman: 'h', example: '하다', sound: 'лёгкий выдох-h, слабее русского х' },
      ],
    },
    {
      title: 'Придыхательные согласные (добавьте выдох)',
      note: 'Каждый — простой согласный с лишней чертой и лишним выдохом.',
      rows: [
        { char: 'ㅋ', roman: 'k', example: '코', sound: 'к с сильным выдохом (ㄱ + воздух)' },
        { char: 'ㅌ', roman: 't', example: '토요일', sound: 'т с сильным выдохом (ㄷ + воздух)' },
        { char: 'ㅍ', roman: 'p', example: '팔', sound: 'п с сильным выдохом (ㅂ + воздух)' },
        { char: 'ㅊ', roman: 'ch', example: '차', sound: 'ч с сильным выдохом (ㅈ + воздух)' },
      ],
    },
    {
      title: 'Напряжённые согласные (двойные, без воздуха)',
      note: 'Произносите со сжатым горлом и без малейшего выдоха — коротко и туго.',
      rows: [
        { char: 'ㄲ', roman: 'kk', example: '까만', sound: 'тугое к без выдоха' },
        { char: 'ㄸ', roman: 'tt', example: '딸', sound: 'тугое т без выдоха' },
        { char: 'ㅃ', roman: 'pp', example: '빵', sound: 'тугое п без выдоха' },
        { char: 'ㅆ', roman: 'ss', example: '쌀', sound: 'тугое с' },
        { char: 'ㅉ', roman: 'jj', example: '짜다', sound: 'тугое ч без выдоха' },
      ],
    },
    {
      title: 'Базовые гласные',
      rows: [
        { char: 'ㅏ', roman: 'a', example: '아빠', sound: 'как а в «мама»' },
        { char: 'ㅓ', roman: 'eo', example: '어머니', sound: 'открытое о без округления губ — между а и о' },
        { char: 'ㅗ', roman: 'o', example: '오늘', sound: 'как о (губы округлены)' },
        { char: 'ㅜ', roman: 'u', example: '우리', sound: 'как у в «утро»' },
        { char: 'ㅡ', roman: 'eu', example: '그', sound: 'практически русская ы — скажите у, растянув губы в улыбке' },
        { char: 'ㅣ', roman: 'i', example: '이름', sound: 'как и в «мир»' },
        { char: 'ㅐ', roman: 'ae', example: '개', sound: 'как э (в современной речи совпадает с ㅔ)' },
        { char: 'ㅔ', roman: 'e', example: '세 시', sound: 'как э в «это»' },
      ],
    },
    {
      title: 'Гласные с й- и у̯-',
      note: 'Дополнительная черта добавляет й- впереди; соединение двух гласных даёт у̯- (как английское w).',
      rows: [
        { char: 'ㅑ ㅕ ㅛ ㅠ', roman: 'ya yeo yo yu', example: '야구, 여자', sound: 'те же четыре базовых гласных с й- впереди (я, йо, ё, ю)' },
        { char: 'ㅒ ㅖ', roman: 'yae ye', example: '예', sound: 'йэ — как е в «ель»' },
        { char: 'ㅘ ㅝ', roman: 'wa wo', example: '와요, 뭐', sound: 'уа / уо — слитно, одним слогом' },
        { char: 'ㅙ ㅞ ㅚ', roman: 'wae we oe', example: '왜, 회사', sound: 'в современной речи все три звучат как уэ' },
        { char: 'ㅟ', roman: 'wi', example: '귀', sound: 'уи одним слогом' },
        { char: 'ㅢ', roman: 'ui', example: '의사', sound: 'ы + и слитно; в речи часто просто и или э' },
      ],
    },
  ],
}

const hebrewRu: LanguageLetters = {
  intro: 'Еврейский алфавит — 22 буквы, справа налево. У каждой буквы одна форма (пять меняются в конце слова); гласные почти никогда не пишутся.',
  sections: [
    {
      title: 'Буквы, которые есть в русском',
      rows: [
        { char: 'ב', roman: 'b', example: 'בית', sound: 'как б («в» без точки внутри)' },
        { char: 'ג', roman: 'g', example: 'גדול', sound: 'как г в «год»' },
        { char: 'ד', roman: 'd', example: 'דג', sound: 'как д в «дом»' },
        { char: 'ה', roman: 'h', example: 'הר', sound: 'лёгкое придыхание, как английское h; в конце слова немая' },
        { char: 'ו', roman: 'v', example: 'ורד', sound: 'как в; также пишет долгие «о»/«у»' },
        { char: 'ז', roman: 'z', example: 'זמן', sound: 'как з в «зуб»' },
        { char: 'י', roman: 'y', example: 'יד', sound: 'как й; также пишет долгую «и»' },
        { char: 'כ', roman: 'k', example: 'כלב', sound: 'как к; без точки внутри — как х' },
        { char: 'ל', roman: 'l', example: 'לילה', sound: 'как л в «лампа»' },
        { char: 'מ', roman: 'm', example: 'מים', sound: 'как м в «мама»' },
        { char: 'נ', roman: 'n', example: 'נר', sound: 'как н в «нет»' },
        { char: 'ס', roman: 's', example: 'ספר', sound: 'как с в «сон»' },
        { char: 'פ', roman: 'p', example: 'פרח', sound: 'как п; без точки внутри — ф' },
        { char: 'ק', roman: 'q', example: 'קטן', sound: 'ещё одно к (сегодня звучит как כ)' },
        { char: 'ר', roman: 'r', example: 'ראש', sound: 'картавое р, как французское' },
        { char: 'ש', roman: 'sh', example: 'שלום', sound: 'как ш; с точкой слева — с' },
        { char: 'ת', roman: 't', example: 'תודה', sound: 'как т в «там»' },
      ],
    },
    {
      title: 'Новые звуки',
      rows: [
        { char: 'א', roman: 'a', example: 'אבא', sound: 'немая — опора для гласной' },
        { char: 'ח', roman: 'ch', example: 'חלב', sound: 'жёсткое х из глубины горла' },
        { char: 'ט', roman: 'T', example: 'טוב', sound: 'ещё одно т (сегодня звучит как ת); различие только в написании' },
        { char: 'ע', roman: "'", example: 'עין', sound: 'сжатие в горле; у большинства сегодня немая' },
        { char: 'צ', roman: 'ts', example: 'ציפור', sound: 'как ц в «цирк»' },
      ],
    },
    {
      title: 'Конечные формы',
      note: 'Пять букв меняют форму в конце слова — та же буква, тот же звук. Клавиатура делает это сама.',
      rows: [
        { char: 'כ → ך', roman: 'k', example: 'מלך', sound: 'каф в конце слова' },
        { char: 'מ → ם', roman: 'm', example: 'מים', sound: 'мем в конце слова' },
        { char: 'נ → ן', roman: 'n', example: 'בן', sound: 'нун в конце слова' },
        { char: 'פ → ף', roman: 'p/f', example: 'סוף', sound: 'пей в конце слова' },
        { char: 'צ → ץ', roman: 'ts', example: 'ארץ', sound: 'цади в конце слова' },
      ],
    },
    {
      title: 'Куда делись гласные',
      note: 'В обычном иврите большинство гласных не пишется (полное письмо передаёт долгие о/у через ו, и через י). Огласовки (никуд) встречаются только в детских книгах, поэзии и словарях.',
      rows: [
        { char: 'וֹ / וּ', roman: 'o / u', example: 'שלום', sound: 'вав в роли гласной: долгие «о» или «у»' },
        { char: 'י', roman: 'i', example: 'דין', sound: 'йод в роли гласной: долгая «и»' },
        { char: 'בַ בֶ בִ', roman: '(niqqud)', example: 'בַּיִת', sound: 'огласовки под буквой — почти всегда опускаются' },
      ],
    },
  ],
}

const persianRu: LanguageLetters = {
  intro: 'Персидский пишется арабским письмом — 32 буквы, справа налево, обязательная вязь — но фонетика намного проще: без эмфатических и жёстких гортанных, а несколько заимствованных букв слились в обычные с, з, т и х.',
  sections: [
    {
      title: 'Четыре чисто персидские буквы',
      note: 'Добавлены к арабскому письму для звуков, которых в арабском нет.',
      positions: true,
      rows: [
        { char: 'پ', roman: 'p', example: 'پدر', sound: 'как п в «папа»' },
        { char: 'چ', roman: 'ch', example: 'چای', sound: 'как ч в «чай»' },
        { char: 'ژ', roman: 'zh', example: 'ژاله', sound: 'как ж в «жар»' },
        { char: 'گ', roman: 'g', example: 'گل', sound: 'как г в «год»' },
      ],
    },
    {
      title: 'Буквы, которые есть в русском',
      positions: true,
      rows: [
        { char: 'ب', roman: 'b', example: 'باب', sound: 'как б в «брат»' },
        { char: 'ت', roman: 't', example: 'تهران', sound: 'как т в «там»' },
        { char: 'ج', roman: 'j', example: 'جان', sound: 'как дж в «джем»' },
        { char: 'د', roman: 'd', example: 'دست', sound: 'как д в «дом»' },
        { char: 'ر', roman: 'r', example: 'روز', sound: 'одноударное р, как испанское' },
        { char: 'ز', roman: 'z', example: 'زبان', sound: 'как з в «зуб»' },
        { char: 'س', roman: 's', example: 'سلام', sound: 'как с в «сон»' },
        { char: 'ش', roman: 'sh', example: 'شب', sound: 'как ш в «шум»' },
        { char: 'ف', roman: 'f', example: 'فردا', sound: 'как ф в «флаг»' },
        { char: 'ک', roman: 'k', example: 'کتاب', sound: 'как к в «кот»' },
        { char: 'ل', roman: 'l', example: 'لب', sound: 'как л в «лампа»' },
        { char: 'م', roman: 'm', example: 'مادر', sound: 'как м в «мама»' },
        { char: 'ن', roman: 'n', example: 'نان', sound: 'как н в «нет»' },
        { char: 'ه', roman: 'h', example: 'هفت', sound: 'лёгкое придыхание, как английское h' },
        { char: 'و', roman: 'v', example: 'وقت', sound: 'как в; также пишет долгие «у»/«о»' },
        { char: 'ی', roman: 'y', example: 'یک', sound: 'как й; также пишет долгую «и»' },
      ],
    },
    {
      title: 'Заимствованные двойники',
      note: 'Арабские заимствования сохранили написание, но персидский слил звуки — эти буквы звучат ровно как с, з, т, х или к. Орфография различает слова; рот ничего особенного не делает.',
      positions: true,
      rows: [
        { char: 'ث', roman: 's', example: 'ثانیه', sound: 'обычное с (арабское th)' },
        { char: 'ص', roman: 's', example: 'صبح', sound: 'обычное с' },
        { char: 'ذ', roman: 'z', example: 'ذهن', sound: 'обычное з (арабское dh)' },
        { char: 'ض', roman: 'z', example: 'ضعیف', sound: 'обычное з' },
        { char: 'ظ', roman: 'z', example: 'ظهر', sound: 'обычное з' },
        { char: 'ط', roman: 't', example: 'طلا', sound: 'обычное т' },
        { char: 'ح', roman: 'h', example: 'حال', sound: 'обычное х-придыхание' },
        { char: 'ع', roman: "'", example: 'عشق', sound: 'лёгкая смычка, или вообще ничего — куда мягче арабского' },
        { char: 'غ', roman: 'gh', example: 'غذا', sound: 'картавое г, как французское р' },
        { char: 'ق', roman: 'q / gh', example: 'قلب', sound: 'то же картавое г у большинства говорящих' },
      ],
    },
    {
      title: 'Гласные и полупробел',
      rows: [
        { char: 'آ', roman: 'aa', example: 'آب', sound: 'долгое тёмное «а», ближе к «о» — алеф с шапочкой (мадда)' },
        { char: 'ا', roman: 'a', example: 'اسم', sound: 'опора гласной в начале слова' },
        { char: 'و / ی', roman: 'oo / ee', example: 'دور، شیر', sound: 'долгие у и и, пишутся через вав и йе' },
        { char: 'ــِـ ــَـ ــُـ', roman: 'e a o', example: 'دَر', sound: 'краткие гласные — почти никогда не пишутся' },
        { char: '‌ (نیم‌فاصله)', roman: '-', example: 'می‌روم', sound: 'полупробел (ZWNJ): держит می при глаголе, но раздельно — набирается через -' },
      ],
    },
  ],
}

export const LETTERS_RU: Record<string, LanguageLetters> = {
  he: hebrewRu,
  fa: persianRu,
  es: spanishRu,
  fr: frenchRu,
  de: germanRu,
  it: italianRu,
  ca: catalanRu,
  pt: portugueseRu,
  ro: romanianRu,
  tr: turkishRu,
  sw: swahiliRu,
  yo: yorubaRu,
  ha: hausaRu,
  xh: xhosaRu,
  mi: maoriRu,
  jam: jamaicanRu,
  en: englishRu,
  nl: dutchRu,
  ru: russianRu,
  el: greekRu,
  ar: arabicRu,
  hi: hindiRu,
  th: thaiRu,
  ko: koreanRu,
}
