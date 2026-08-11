/**
 * Letters & Sounds — Spanish (es) UI overlay for ALL 22 courses.
 * Not word-for-word translations: every sound description is re-anchored
 * for a Spanish-speaking reader (Spanish example words where the sound
 * exists; French/English references or an articulation recipe where it
 * does not). Examples stay in the course language — they are playable.
 */
import type { LanguageLetters } from './lettersData'

const spanishEs: LanguageLetters = {
  intro: 'La ortografía española es honesta: cinco vocales puras, y casi cada letra suena igual todas las veces.',
  sections: [
    {
      title: 'Las cinco vocales',
      note: 'Breves, puras, nunca arrastradas. La tilde (á é í ó ú) marca la sílaba tónica — el sonido no cambia.',
      rows: [
        { char: 'a / á', example: 'agua', sound: "la a de 'agua': abierta y pura" },
        { char: 'e / é', example: 'leche', sound: "la e de 'leche'" },
        { char: 'i / í', example: 'vivir', sound: "la i de 'vivir'" },
        { char: 'o / ó', example: 'poco', sound: "la o de 'poco'" },
        { char: 'u / ú', example: 'luna', sound: "la u de 'luna' (muda en que/qui, gue/gui)" },
        { char: 'ü', example: 'pingüino', sound: 'la diéresis despierta la u: gü suena «gu», como en pingüino' },
      ],
    },
    {
      title: 'Las consonantes con truco',
      rows: [
        { char: 'ñ', example: 'niño', sound: "la ñ de 'niño' — la nasal palatal, marca de la casa" },
        { char: 'j', example: 'joven', sound: "la jota de 'joven': fricción al fondo de la boca" },
        { char: 'g (+e/i)', example: 'gente', sound: 'ante e/i suena como la jota; en el resto, g dura' },
        { char: 'll / y', example: 'llamar', sound: "como la y de 'yema' (una «sh» suave en gran parte del Río de la Plata)" },
        { char: 'h', example: 'hola', sound: 'siempre muda' },
        { char: 'rr / r-', example: 'perro', sound: 'vibrante múltiple; la r simple entre vocales es un solo toque' },
        { char: 'z / c(+e,i)', example: 'zapato', sound: "'s' en América; en España, la zeta interdental de 'zapato'" },
        { char: 'v', example: 'vaso', sound: 'suena exactamente igual que la b' },
        { char: 'qu', example: 'queso', sound: "'k' — la u es muda" },
      ],
    },
  ],
}

const frenchEs: LanguageLetters = {
  intro: 'Los sonidos del francés viven en las vocales y en el enlace entre palabras. Las consonantes finales suelen ser mudas; los acentos cambian el timbre de la vocal, no la sílaba tónica.',
  sections: [
    {
      title: 'Las vocales y sus acentos',
      rows: [
        { char: 'a / à / â', example: 'chat', sound: "como la a de 'agua'" },
        { char: 'é', example: 'été', sound: "e cerrada y tensa, como la e de 'bebé'" },
        { char: 'è / ê / e(+2 cons.)', example: 'mère', sound: "e abierta, como la e de 'perro'" },
        { char: 'e (sin acento)', example: 'le', sound: 'una «e» neutra y relajada (schwa) — a menudo ni se pronuncia' },
        { char: 'i / î / y', example: 'ville', sound: "como la i de 'sí'" },
        { char: 'o / ô', example: 'mot', sound: "o cerrada, como la o de 'poco'" },
        { char: 'u / û', example: 'tu', sound: 'di «i» con los labios redondeados — no existe en español' },
        { char: 'ou', example: 'vous', sound: "como la u de 'luna'" },
        { char: 'eu / œu', example: 'peu', sound: 'di «e» con los labios redondeados' },
        { char: 'oi', example: 'moi', sound: "'ua', como en 'cuatro'" },
        { char: 'au / eau', example: 'eau', sound: 'o cerrada' },
        { char: 'ai / ei', example: 'maison', sound: "como la e de 'mesa'" },
      ],
    },
    {
      title: 'Las vocales nasales',
      note: 'Vocal + n/m en la misma sílaba = el aire sale por la nariz, y la n/m NO se pronuncia.',
      rows: [
        { char: 'on / om', example: 'bon', sound: "'o' nasal" },
        { char: 'an / en', example: 'enfant', sound: "'a' nasal" },
        { char: 'in / ain / ein', example: 'vin', sound: "'e' nasal muy abierta, hacia la a" },
        { char: 'un', example: 'un', sound: '«e» redondeada nasal (muchos hablantes la funden con in)' },
      ],
    },
    {
      title: 'Costumbres consonánticas',
      rows: [
        { char: 'r', example: 'rouge', sound: 'gargarizada al fondo de la garganta — prima de nuestra jota, pero sonora' },
        { char: 'ç', example: 'garçon', sound: "'s' — la cedilla mantiene la c suave ante a/o/u" },
        { char: 'ch', example: 'chien', sound: 'como la sh inglesa de shop' },
        { char: 'gn', example: 'montagne', sound: "como la ñ de 'niño'" },
        { char: 'j / g(+e,i)', example: 'jour', sound: 'como la y/ll rioplatense sonora — una ch suave y zumbada' },
        { char: 'h', example: 'homme', sound: 'muda' },
        { char: 'final consonants', example: 'petit', sound: 'casi siempre mudas — ojo con s, t, d, x' },
      ],
    },
  ],
}

const germanEs: LanguageLetters = {
  intro: 'El alemán se pronuncia como se escribe una vez que dominas las diéresis (umlauts) y un puñado de equipos de letras.',
  sections: [
    {
      title: 'Vocales y umlauts',
      rows: [
        { char: 'a', example: 'Haus', sound: "como la a de 'agua'" },
        { char: 'ä', example: 'Mädchen', sound: "como la e de 'mesa'" },
        { char: 'o', example: 'Brot', sound: "o cerrada, como la o de 'poco'" },
        { char: 'ö', example: 'schön', sound: 'di «e» con los labios redondeados (la eu francesa)' },
        { char: 'u', example: 'gut', sound: "como la u de 'luna'" },
        { char: 'ü', example: 'über', sound: 'di «i» con los labios redondeados (la u francesa)' },
        { char: 'ei', example: 'mein', sound: "como ay en 'hay'" },
        { char: 'ie', example: 'Liebe', sound: "como la i de 'sí'" },
        { char: 'eu / äu', example: 'heute', sound: "como oy en 'hoy'" },
        { char: 'au', example: 'Auto', sound: "como au en 'auto'" },
      ],
    },
    {
      title: 'Equipos de consonantes',
      rows: [
        { char: 'w', example: 'Wasser', sound: 'una v con los dientes sobre el labio (v francesa/inglesa) — no la b española' },
        { char: 'v', example: 'Vater', sound: "como la f de 'foca'" },
        { char: 'z', example: 'Zeit', sound: "'ts', como en 'tsunami'" },
        { char: 's (+vocal)', example: 'Sonne', sound: 's sonora, con zumbido de abeja — no existe en español' },
        { char: 'ß / ss', example: 'Straße', sound: "s sorda y tensa, como la s de 'sol'" },
        { char: 'sch', example: 'Schule', sound: 'como la sh inglesa de shop' },
        { char: 'st- / sp-', example: 'Straße', sound: "'sht' / 'shp' a principio de palabra" },
        { char: 'ch (tras a/o/u)', example: 'Buch', sound: "como la jota de 'joven'" },
        { char: 'ch (tras e/i)', example: 'ich', sound: 'una jota muy suave y silbada, dicha con la lengua en posición de i' },
        { char: 'r', example: 'rot', sound: 'gargarizada al fondo; casi una vocal a final de palabra (-er = «a» relajada)' },
        { char: 'final b/d/g', example: 'Tag', sound: 'a final de palabra se endurecen a p/t/k' },
      ],
    },
  ],
}

const italianEs: LanguageLetters = {
  intro: 'Siete sonidos vocálicos, consonantes dobles nítidas y dos letras (c, g) que se ablandan ante e e i.',
  sections: [
    {
      title: 'Vocales',
      rows: [
        { char: 'a / à', example: 'casa', sound: "como la a de 'agua'" },
        { char: 'e / è', example: 'bene', sound: "como la e de 'mesa' (é más cerrada, como en 'bebé')" },
        { char: 'i / ì', example: 'vino', sound: "como la i de 'sí'" },
        { char: 'o / ò', example: 'otto', sound: "como la o de 'poco'" },
        { char: 'u / ù', example: 'uno', sound: "como la u de 'luna'" },
      ],
    },
    {
      title: 'El sistema c/g',
      rows: [
        { char: 'c (+a,o,u)', example: 'casa', sound: "'k', como la c de 'casa'" },
        { char: 'c (+e,i)', example: 'cena', sound: "como la ch de 'chico'" },
        { char: 'ch', example: 'chiave', sound: "'k' — la h la vuelve dura otra vez" },
        { char: 'g (+a,o,u)', example: 'gatto', sound: "como la g de 'gato'" },
        { char: 'g (+e,i)', example: 'gelato', sound: 'como una «y» fuerte rioplatense; la j del inglés jam' },
        { char: 'gh', example: 'spaghetti', sound: "'g' dura de nuevo" },
        { char: 'gn', example: 'gnocchi', sound: "como la ñ de 'niño'" },
        { char: 'gli', example: 'famiglia', sound: "como la ll tradicional castellana — un 'li' dicho muy rápido" },
        { char: 'sc (+e,i)', example: 'pesce', sound: 'como la sh inglesa de shop' },
      ],
    },
    {
      title: 'Costumbres',
      rows: [
        { char: 'double consonants', example: 'pizza', sound: 'se sostienen el doble de tiempo — pit-tsa, no pi-tsa' },
        { char: 'z', example: 'zio', sound: "'ts' o 'ds'" },
        { char: 'r', example: 'Roma', sound: 'vibrante, como en español' },
        { char: 'h', example: 'hotel', sound: 'muda' },
      ],
    },
  ],
}

const catalanEs: LanguageLetters = {
  intro: 'Las vocales catalanas se reducen cuando son átonas (la firma del catalán), y unas cuantas grafías son solo suyas.',
  sections: [
    {
      title: 'Vocales',
      rows: [
        { char: 'a / à', example: 'casa', sound: "'a' tónica; átona, una «e» neutra y relajada (schwa)" },
        { char: 'e / é / è', example: 'més', sound: "'e' cerrada o abierta tónica; átona, la misma «e» neutra" },
        { char: 'i / í', example: 'nit', sound: "como la i de 'sí'" },
        { char: 'o / ó / ò', example: 'porta', sound: "'o' tónica; átona suena 'u'" },
        { char: 'u / ú', example: 'butxaca', sound: "como la u de 'luna'" },
      ],
    },
    {
      title: 'Especialidades catalanas',
      rows: [
        { char: 'ny', example: 'Catalunya', sound: "como la ñ de 'niño'" },
        { char: 'l·l', example: 'il·lusió', sound: 'el punto volado: una ele larga' },
        { char: 'x', example: 'xocolata', sound: 'como la sh inglesa de shop' },
        { char: 'tx', example: 'cotxe', sound: "como la ch de 'chico'" },
        { char: 'ç', example: 'plaça', sound: "'s'" },
        { char: 'j / g(+e,i)', example: 'jugar', sound: 'como la y/ll rioplatense sonora (la j francesa)' },
        { char: 'r final', example: 'cantar', sound: 'generalmente muda' },
        { char: 'ig final', example: 'puig', sound: "como la ch de 'chico'" },
      ],
    },
  ],
}

const portugueseEs: LanguageLetters = {
  intro: 'Portugués de Brasil: vocales musicales, los famosos sonidos nasales y unas consonantes que también sorprenden a los hispanohablantes.',
  sections: [
    {
      title: 'Vocales y acentos',
      rows: [
        { char: 'a / á', example: 'casa', sound: "como la a de 'agua'" },
        { char: 'â', example: 'câmera', sound: "'a' cerrada y apagada, hacia la «e» neutra" },
        { char: 'e / é', example: 'ela', sound: "e abierta, como la e de 'perro'" },
        { char: 'ê', example: 'você', sound: "e cerrada y tensa, como la e de 'bebé'" },
        { char: 'e final', example: 'nome', sound: "en Brasil se encoge a 'i'" },
        { char: 'o / ó', example: 'avó', sound: 'o muy abierta, tirando a la a' },
        { char: 'ô', example: 'avô', sound: 'o cerrada — ¡avó y avô solo se distinguen aquí!' },
        { char: 'o final', example: 'gato', sound: "se encoge a 'u'" },
        { char: 'u', example: 'tudo', sound: "como la u de 'luna'" },
      ],
    },
    {
      title: 'La familia nasal',
      note: 'La virgulilla (~) o una m/n siguiente mandan la vocal por la nariz.',
      rows: [
        { char: 'ã', example: 'maçã', sound: "'a' nasal" },
        { char: 'ão', example: 'pão', sound: "'au' nasal — el sonido más portugués que existe" },
        { char: 'õe', example: 'ações', sound: "'oi' nasal" },
        { char: 'em / en', example: 'bem', sound: "'ei' nasal" },
        { char: 'im / in', example: 'sim', sound: "'i' nasal" },
      ],
    },
    {
      title: 'Sorpresas consonánticas',
      rows: [
        { char: 'ç', example: 'coração', sound: "'s'" },
        { char: 'ch', example: 'chuva', sound: 'como la sh inglesa de shop' },
        { char: 'lh', example: 'filho', sound: "como la ll tradicional castellana — un 'li' rápido" },
        { char: 'nh', example: 'ninho', sound: "como la ñ de 'niño'" },
        { char: 'j / g(+e,i)', example: 'hoje', sound: 'como la y/ll rioplatense sonora (la j francesa)' },
        { char: 'r- / rr', example: 'rio', sound: 'en Brasil, una jota suave y aspirada — no una erre' },
        { char: 'ti / di', example: 'dia', sound: "'chi' / 'yi' en casi todo Brasil" },
        { char: 'l final', example: 'Brasil', sound: "se convierte en 'u': Brasiu" },
      ],
    },
  ],
}

const romanianEs: LanguageLetters = {
  intro: 'El rumano se lee casi como el italiano con cinco letras extra — y las cinco son regulares.',
  sections: [
    {
      title: 'Las cinco letras especiales',
      rows: [
        { char: 'ă', example: 'casă', sound: 'una «e» neutra y relajada (schwa) — no existe en español' },
        { char: 'â / î', example: 'în', sound: "una 'i' profunda y central — di «i» con la lengua retraída" },
        { char: 'ș', example: 'și', sound: 'como la sh inglesa de shop' },
        { char: 'ț', example: 'preț', sound: "'ts', como en 'tsunami'" },
      ],
    },
    {
      title: 'Conviene saber',
      rows: [
        { char: 'c (+e,i)', example: 'ce', sound: "como la ch de 'chico'" },
        { char: 'che / chi', example: 'chelner', sound: "'k'" },
        { char: 'g (+e,i)', example: 'ger', sound: 'como una «y» fuerte rioplatense; la j del inglés jam' },
        { char: 'ghe / ghi', example: 'ghid', sound: "como la g de 'gato'" },
        { char: 'j', example: 'jos', sound: 'como la j francesa de jour (y rioplatense sonora)' },
        { char: 'r', example: 'repede', sound: 'vibrante, como en español' },
        { char: '-i final', example: 'lupi', sound: 'susurrada — apenas una i insinuada' },
      ],
    },
  ],
}

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

const swahiliEs: LanguageLetters = {
  intro: 'El suajili es maravillosamente fonético: cinco vocales puras — como las del español — y el acento siempre en la penúltima sílaba.',
  sections: [
    {
      title: 'Vocales',
      rows: [
        { char: 'a', example: 'baba', sound: "como la a de 'agua'" },
        { char: 'e', example: 'wewe', sound: "como la e de 'mesa'" },
        { char: 'i', example: 'sisi', sound: "como la i de 'sí'" },
        { char: 'o', example: 'moto', sound: "como la o de 'poco'" },
        { char: 'u', example: 'kuku', sound: "como la u de 'luna'" },
      ],
    },
    {
      title: 'Equipos de letras',
      rows: [
        { char: 'ny', example: 'nyumba', sound: "como la ñ de 'niño'" },
        { char: "ng'", example: "ng'ombe", sound: "como la n de 'banco', sola y sin g — pero a PRINCIPIO de sílaba" },
        { char: 'ng (sin apóstrofo)', example: 'ngoma', sound: "'ng-g', como en 'tengo' — aquí la g sí suena" },
        { char: 'dh', example: 'dhahabu', sound: "como la d suave de 'nada' (préstamos del árabe)" },
        { char: 'th', example: 'thelathini', sound: "como la z de España en 'zapato'" },
        { char: 'gh', example: 'ghali', sound: 'g gargarizada — una jota sonora (préstamos del árabe)' },
        { char: 'ch', example: 'chai', sound: "como la ch de 'chico'" },
        { char: 'mb / nd / nj', example: 'mbwa', sound: 'tararea la m/n DENTRO de la consonante siguiente — un solo golpe' },
      ],
    },
  ],
}

const yorubaEs: LanguageLetters = {
  intro: 'El yoruba es una lengua tonal: las tildes marcan altura musical, no acento. Dos letras con punto marcan vocales abiertas.',
  sections: [
    {
      title: 'Vocales (7) + los puntos',
      rows: [
        { char: 'a', example: 'ata', sound: "como la a de 'agua'" },
        { char: 'e', example: 'ewé', sound: "e cerrada y tensa, como la e de 'bebé'" },
        { char: 'ẹ (con punto)', example: 'ẹja', sound: "e abierta, como la e de 'perro'" },
        { char: 'i', example: 'ilé', sound: "como la i de 'sí'" },
        { char: 'o', example: 'owó', sound: "o cerrada, como la o de 'poco'" },
        { char: 'ọ (con punto)', example: 'ọmọ', sound: 'o muy abierta, tirando a la a' },
        { char: 'u', example: 'imu', sound: "como la u de 'luna'" },
      ],
    },
    {
      title: 'Tonos — las tres alturas',
      note: 'Mismas letras, distinta altura, distinta palabra. Las tildes son la melodía.',
      rows: [
        { char: 'á (alto)', example: 'wá', sound: 'el tono salta hacia arriba' },
        { char: 'a (medio)', example: 'wa', sound: 'llano, altura normal' },
        { char: 'à (bajo)', example: 'wà', sound: 'el tono cae hacia abajo' },
      ],
    },
    {
      title: 'Consonantes',
      rows: [
        { char: 'ṣ (con punto)', example: 'ṣe', sound: 'como la sh inglesa de shop' },
        { char: 'gb', example: 'gbogbo', sound: "'g' y 'b' exactamente al mismo tiempo — no existe en español" },
        { char: 'p', example: 'pápá', sound: "en realidad es 'kp', soltadas a la vez" },
        { char: 'j', example: 'jẹun', sound: 'como una «y» fuerte rioplatense; la j del inglés jam' },
      ],
    },
  ],
}

const hausaEs: LanguageLetters = {
  intro: 'El hausa (boko) usa tres letras «con gancho» para sonidos que el español no tiene: estallan o crujen en vez de fluir.',
  sections: [
    {
      title: 'Vocales',
      note: 'Cinco vocales, largas o breves — la duración cambia el significado.',
      rows: [
        { char: 'a', example: 'ruwa', sound: "como la a de 'agua' (larga: sostenla)" },
        { char: 'e', example: 'gemu', sound: "como la e de 'mesa'" },
        { char: 'i', example: 'kifi', sound: "como la i de 'sí'" },
        { char: 'o', example: 'doki', sound: "como la o de 'poco'" },
        { char: 'u', example: 'kudi', sound: "como la u de 'luna'" },
      ],
    },
    {
      title: 'Las letras con gancho',
      rows: [
        { char: 'ɓ', example: 'ɓera', sound: "una 'b' implosiva — el aire estalla hacia dentro" },
        { char: 'ɗ', example: 'ɗaki', sound: "una 'd' implosiva" },
        { char: 'ƙ', example: 'ƙofa', sound: "una 'k' con golpe de glotis" },
        { char: "'y", example: "'ya'ya", sound: "una 'y' crujiente, con la voz rechinada" },
      ],
    },
    {
      title: 'Otras costumbres',
      rows: [
        { char: 'ts', example: 'tsuntsu', sound: "'ts' con un golpe de glotis" },
        { char: 'sh', example: 'shekara', sound: 'como la sh inglesa de shop' },
        { char: 'c', example: 'ci', sound: "como la ch de 'chico'" },
        { char: 'r', example: 'rana', sound: 'vibrante o de un toque, como en español' },
      ],
    },
  ],
}

const xhosaEs: LanguageLetters = {
  intro: 'El isiXhosa es famoso por sus clics — tres clics básicos, escritos c, x, q. Todo lo demás queda cerca del español.',
  sections: [
    {
      title: 'Los tres clics',
      rows: [
        { char: 'c', example: 'cela', sound: 'clic dental — el chasquido de desaprobación «ts-ts», con la lengua tras los dientes' },
        { char: 'x', example: 'ixesha', sound: 'clic lateral — el chasquido de arrear al caballo, por el lado de la boca' },
        { char: 'q', example: 'iqanda', sound: 'clic palatal — un taponazo de botella contra el paladar' },
        { char: 'gc / gx / gq', example: 'gqiba', sound: 'los mismos clics, sonoros (tararea a través de ellos)' },
        { char: 'nc / nx / nq', example: 'inqola', sound: 'los mismos clics con zumbido nasal' },
      ],
    },
    {
      title: 'Vocales',
      rows: [
        { char: 'a', example: 'abantu', sound: "como la a de 'agua'" },
        { char: 'e', example: 'ewe', sound: "como la e de 'mesa'" },
        { char: 'i', example: 'siza', sound: "como la i de 'sí'" },
        { char: 'o', example: 'onke', sound: 'o abierta, tirando a la a' },
        { char: 'u', example: 'ubuntu', sound: "como la u de 'luna'" },
      ],
    },
    {
      title: 'Otros equipos de letras',
      rows: [
        { char: 'hl', example: 'hlala', sound: 'la ll galesa — sopla el aire por los lados de la lengua' },
        { char: 'dl', example: 'indlela', sound: 'la versión sonora de hl' },
        { char: 'tsh', example: 'utshaba', sound: "como la ch de 'chico'" },
        { char: 'kh / th / ph', example: 'ukutya', sound: 'k/t/p con un soplo de aire extra' },
      ],
    },
  ],
}

const maoriEs: LanguageLetters = {
  intro: 'Te reo maorí: cinco vocales (breves y largas), ocho consonantes, dos dígrafos. Toda sílaba termina en vocal.',
  sections: [
    {
      title: 'Vocales — breves y largas',
      note: 'El macrón (ā ē ī ō ū) duplica la duración, y la duración cambia el significado.',
      rows: [
        { char: 'a / ā', example: 'aroha', sound: "como la a de 'agua' (ā, sostenida)" },
        { char: 'e / ē', example: 'kete', sound: "como la e de 'mesa'" },
        { char: 'i / ī', example: 'kiwi', sound: "como la i de 'sí'" },
        { char: 'o / ō', example: 'moana', sound: "o abierta, como la o de 'poco' tirando a la a" },
        { char: 'u / ū', example: 'utu', sound: "como la u de 'luna'" },
      ],
    },
    {
      title: 'Los dos dígrafos',
      rows: [
        { char: 'wh', example: 'whānau', sound: "como la f de 'foca'" },
        { char: 'ng', example: 'ngā', sound: "como la n de 'banco', sin g — incluso a principio de palabra" },
      ],
    },
    {
      title: 'Consonantes',
      rows: [
        { char: 'r', example: 'reo', sound: "un toque suave entre r y l, como la r de 'pero'" },
        { char: 't', example: 'te', sound: "t suave, casi sin soplo — como la t española" },
        { char: 'k, m, n, p, h, w', example: 'kapa haka', sound: 'como en español — pero la h SÍ se pronuncia (aspirada), no es muda' },
      ],
    },
  ],
}

const jamaicanEs: LanguageLetters = {
  intro: 'El patois en la ortografía Cassidy/JLU: un sonido por letra, sin letras mudas. Si sabes decirlo, sabes escribirlo.',
  sections: [
    {
      title: 'Vocales',
      rows: [
        { char: 'a', example: 'bak', sound: "como la a de 'agua'" },
        { char: 'aa', example: 'baal', sound: "'a' larga, sostenida" },
        { char: 'e', example: 'bel', sound: "como la e de 'mesa'" },
        { char: 'i', example: 'sik', sound: "'i' breve y relajada, entre i y e — no existe en español" },
        { char: 'ii', example: 'siik', sound: "como la i de 'sí'" },
        { char: 'o', example: 'pat', sound: 'o abierta, tirando a la a' },
        { char: 'u', example: 'buk', sound: "'u' breve y relajada" },
        { char: 'uu', example: 'skuul', sound: "como la u de 'luna'" },
        { char: 'ie', example: 'kiek', sound: 'deslizamiento «ie» — cake dicho a la jamaicana' },
        { char: 'uo', example: 'guo', sound: 'deslizamiento «uo» — go dicho a la jamaicana' },
        { char: 'ai', example: 'taim', sound: "como ay en 'hay'" },
        { char: 'ou', example: 'bout', sound: "como au en 'auto'" },
      ],
    },
    {
      title: 'Costumbres consonánticas',
      rows: [
        { char: 'k / g (+ya)', example: 'kyaan', sound: "deslizamiento ky/gy — 'kiaan' por can't" },
        { char: 'no th', example: 'tink / dis', sound: "la th inglesa se vuelve una simple 't' o 'd'" },
        { char: 'no h-drop rule', example: 'ouse / haks', sound: 'la h va y viene con libertad — ambas formas valen' },
        { char: 'final clusters trim', example: 'las (last)', sound: 'la última consonante del grupo final se cae' },
      ],
    },
  ],
}

const englishEs: LanguageLetters = {
  intro: 'La ortografía inglesa es historia, no fonética. Estos son los sonidos con los que se pelea todo estudiante — con las grafías fiables donde las hay.',
  sections: [
    {
      title: 'Los famosos',
      rows: [
        { char: 'th (soft)', example: 'think', sound: "lengua entre los dientes, solo aire — la z de España en 'zapato'" },
        { char: 'th (hard)', example: 'this', sound: "misma posición, con voz — la d suave de 'nada'" },
        { char: 'w vs v', example: 'very wet', sound: "w = labios redondeados, sin dientes (la u de 'hueso'); v = dientes sobre el labio — el español funde ambas en b, el inglés no" },
        { char: 'r', example: 'red', sound: 'ni vibrante ni gutural — curva la lengua hacia atrás sin tocar nada' },
        { char: 'h', example: 'house', sound: 'una aspiración real, como la j caribeña suave — nunca muda (salvo hour, honest)' },
      ],
    },
    {
      title: 'Vocales que hacen tropezar',
      rows: [
        { char: 'i (breve)', example: 'ship', sound: "'i' relajada tirando a e — ship NO suena como sheep" },
        { char: 'ee', example: 'sheep', sound: "i larga y tensa, como la i de 'sí' sostenida" },
        { char: 'a (breve)', example: 'cat', sound: 'entre a y e, con la mandíbula bien abierta' },
        { char: 'u (breve)', example: 'cup', sound: "una 'a' central y relajada, más cerrada que la a española" },
        { char: 'er / unstressed', example: 'teacher', sound: 'la schwa — la vocal más perezosa, una «e» neutra que no existe en español; casi toda sílaba átona la usa' },
      ],
    },
    {
      title: 'Patrones de ortografía fiables',
      rows: [
        { char: 'magic e', example: 'hat → hate', sound: 'la e final muda hace que la vocal «diga su nombre»' },
        { char: '-tion', example: 'station', sound: "'shon', con sh inglesa" },
        { char: 'ough', example: 'though / tough', sound: 'lo sentimos — seis sonidos distintos; apréndete cada palabra' },
      ],
    },
  ],
}

const dutchEs: LanguageLetters = {
  intro: 'La ortografía neerlandesa es amable: unos pocos equipos de letras y una vocal famosa (ui) hacen todo el daño.',
  sections: [
    {
      title: 'Los equipos de vocales',
      rows: [
        { char: 'aa / a', example: 'water', sound: "'a' larga / 'a' breve y apagada — doblar la letra marca la duración" },
        { char: 'ee / e', example: 'been', sound: "'e' cerrada larga / 'e' breve; la -e final es una «e» neutra (schwa)" },
        { char: 'oo / o', example: 'boom', sound: "'o' cerrada larga / 'o' breve" },
        { char: 'uu / u', example: 'muur', sound: 'di «i» con los labios redondeados (u francesa) / breve y relajada' },
        { char: 'ie', example: 'niet', sound: "como la i de 'sí'" },
        { char: 'oe', example: 'boek', sound: "como la u de 'luna'" },
        { char: 'eu', example: 'leuk', sound: 'di «e» con los labios redondeados (eu francesa)' },
        { char: 'ij / ei', example: 'ijs', sound: "entre 'ei' y 'ai' — el famoso diptongo neerlandés, con dos grafías" },
        { char: 'ui', example: 'huis', sound: 'no existe en español: di «au» con los labios muy redondeados y tensos' },
        { char: 'ou / au', example: 'oud', sound: "como au en 'auto'" },
      ],
    },
    {
      title: 'Costumbres consonánticas',
      rows: [
        { char: 'g / ch', example: 'goed', sound: "la raspadura neerlandesa — nuestra jota de 'joven' (más suave en el sur)" },
        { char: 'sch', example: 'school', sound: "'s' + esa jota: s-jool" },
        { char: 'w', example: 'water', sound: "entre la u de 'hueso' y una v suave" },
        { char: 'v', example: 'vader', sound: 'entre una v labiodental y una f' },
        { char: 'j', example: 'ja', sound: "como la y de 'ya' (nunca jota)" },
        { char: 'r', example: 'rood', sound: 'vibrante o gutural — ambas valen' },
        { char: '-en (final)', example: 'lopen', sound: "la n final suele caerse: 'lope(n)'" },
        { char: '-tje', example: 'kopje', sound: 'la máquina de diminutivos — koppje, huisje, momentje' },
      ],
    },
  ],
}

const russianEs: LanguageLetters = {
  intro: 'El alfabeto cirílico — 33 letras. Casi todas tienen un solo sonido estable; el sistema que hay que aprender son los cinco pares de vocales «duras/blandas».',
  sections: [
    {
      title: 'Vocales — juego duro',
      note: 'Estas dejan la consonante anterior tal cual.',
      rows: [
        { char: 'а', roman: 'a', example: 'мама', sound: "como la a de 'agua'" },
        { char: 'э', roman: 'e', example: 'это', sound: "como la e de 'mesa'" },
        { char: 'ы', roman: 'y', example: 'мы', sound: "una 'i' profunda y gutural — di «i» con la lengua retraída; no existe en español" },
        { char: 'о', roman: 'o', example: 'дом', sound: "como la o de 'poco' (solo cuando es tónica)" },
        { char: 'у', roman: 'u', example: 'утро', sound: "como la u de 'luna'" },
      ],
    },
    {
      title: 'Vocales — juego blando',
      note: 'Los mismos sonidos vocálicos, pero ablandan la consonante anterior (le añaden un deslizamiento de y oculto).',
      rows: [
        { char: 'я', roman: 'ya', example: 'яблоко', sound: "'ya', como en 'yate'" },
        { char: 'е', roman: 'e/ye', example: 'нет', sound: "'ye', como en 'yerba'" },
        { char: 'и', roman: 'i', example: 'мир', sound: "como la i de 'sí'" },
        { char: 'ё', roman: 'yo', example: 'ёлка', sound: "'yo', como en 'yoga' (siempre tónica)" },
        { char: 'ю', roman: 'yu', example: 'юг', sound: "'yu', como en 'yudo'" },
      ],
    },
    {
      title: 'Consonantes que parecen conocidas (pero no lo son)',
      rows: [
        { char: 'в', roman: 'v', example: 'вода', sound: 'v con los dientes sobre el labio (v francesa) — no es una b' },
        { char: 'н', roman: 'n', example: 'нос', sound: "como la n de 'no' (no es una h)" },
        { char: 'р', roman: 'r', example: 'рука', sound: 'vibrante, como la erre española' },
        { char: 'с', roman: 's', example: 'сок', sound: "como la s de 'sol' (no es una k)" },
        { char: 'у', roman: 'u', example: 'ум', sound: "'u' — parece una y, pero nunca suena así" },
        { char: 'х', roman: 'h/x', example: 'хлеб', sound: "como la jota de 'joven'" },
      ],
    },
    {
      title: 'El resto de las consonantes',
      rows: [
        { char: 'б', roman: 'b', example: 'брат', sound: "como la b de 'barco'" },
        { char: 'г', roman: 'g', example: 'год', sound: "como la g de 'gato'" },
        { char: 'д', roman: 'd', example: 'да', sound: "como la d de 'dedo'" },
        { char: 'ж', roman: 'zh', example: 'жить', sound: 'como la j francesa de jour (y rioplatense sonora)' },
        { char: 'з', roman: 'z', example: 'зима', sound: 's sonora, con zumbido — no existe en español' },
        { char: 'й', roman: 'j', example: 'мой', sound: "'y' de cierre, como en 'hoy'" },
        { char: 'к', roman: 'k', example: 'кот', sound: "como la c de 'casa'" },
        { char: 'л', roman: 'l', example: 'лампа', sound: "como la l de 'luna'" },
        { char: 'м', roman: 'm', example: 'мост', sound: "como la m de 'mano'" },
        { char: 'п', roman: 'p', example: 'папа', sound: "como la p de 'papá'" },
        { char: 'т', roman: 't', example: 'там', sound: "como la t de 'tren'" },
        { char: 'ф', roman: 'f', example: 'фото', sound: "como la f de 'foca'" },
        { char: 'ц', roman: 'c/ts', example: 'цирк', sound: "'ts', como en 'tsunami'" },
        { char: 'ч', roman: 'ch', example: 'чай', sound: "como la ch de 'chico'" },
        { char: 'ш', roman: 'sh', example: 'школа', sound: 'sh dura, como la sh inglesa de shop' },
        { char: 'щ', roman: 'shch', example: 'щи', sound: "un 'shsh' largo y suave, más silbado" },
      ],
    },
    {
      title: 'Los dos signos mudos',
      rows: [
        { char: 'ь', roman: "'", example: 'день', sound: 'signo blando — ablanda la consonante anterior (le añade un matiz de y)' },
        { char: 'ъ', roman: "''", example: 'объект', sound: 'signo duro — una pequeña pausa entre prefijo y raíz' },
      ],
    },
    {
      title: 'Imprenta frente a cursiva (y manuscrita)',
      note: 'El cirílico tipografiado tiene dos caras. En cursiva — y aún más en la letra manuscrita — varias letras adoptan formas que parecen letras latinas DISTINTAS. Misma letra, mismo sonido: compara cada par recto/cursiva.',
      italics: true,
      rows: [
        { char: 'т', roman: 't', example: 'там', sound: "la т cursiva se vuelve una m — sigue siendo 't'" },
        { char: 'и', roman: 'i', example: 'мир', sound: "la и cursiva se vuelve una u — sigue siendo 'i'" },
        { char: 'й', roman: 'j', example: 'мой', sound: 'la й cursiva es esa u con la marca curva encima' },
        { char: 'п', roman: 'p', example: 'папа', sound: "la п cursiva se vuelve una n — sigue siendo 'p'" },
        { char: 'д', roman: 'd', example: 'да', sound: "la д cursiva se vuelve una g — sigue siendo 'd'" },
        { char: 'г', roman: 'g', example: 'год', sound: "la г cursiva parece una s invertida — sigue siendo 'g'" },
      ],
    },
  ],
}

const greekEs: LanguageLetters = {
  intro: 'El alfabeto griego — 24 letras. Varias letras latinas salieron de aquí, así que la mitad del trabajo ya está hecho.',
  sections: [
    {
      title: 'Vocales',
      note: 'El griego moderno tiene solo cinco sonidos vocálicos; varias grafías los comparten.',
      rows: [
        { char: 'α', roman: 'a', example: 'αγάπη', sound: "como la a de 'agua'" },
        { char: 'ε', roman: 'e', example: 'ένα', sound: "como la e de 'mesa'" },
        { char: 'η', roman: 'h/i', example: 'ημέρα', sound: "como la i de 'sí'" },
        { char: 'ι', roman: 'i', example: 'ιδέα', sound: "como la i de 'sí'" },
        { char: 'ο', roman: 'o', example: 'όχι', sound: "como la o de 'poco'" },
        { char: 'υ', roman: 'u/y', example: 'ύπνος', sound: "'i' — sí, también es i" },
        { char: 'ω', roman: 'w', example: 'ώρα', sound: "'o' — igual que ο" },
      ],
    },
    {
      title: 'Consonantes',
      rows: [
        { char: 'β', roman: 'v/b', example: 'βιβλίο', sound: 'v con los dientes sobre el labio (v francesa) — ¡no es b!' },
        { char: 'γ', roman: 'g', example: 'γάλα', sound: "una 'g' suave gargarizada; ante e/i suena como la y de 'ya'" },
        { char: 'δ', roman: 'd', example: 'δέκα', sound: "como la d suave de 'nada' (¡nunca una d dura!)" },
        { char: 'ζ', roman: 'z', example: 'ζωή', sound: 's sonora, con zumbido — no existe en español' },
        { char: 'θ', roman: 'th', example: 'θάλασσα', sound: "como la z de España en 'zapato'" },
        { char: 'κ', roman: 'k', example: 'καλά', sound: "como la c de 'casa'" },
        { char: 'λ', roman: 'l', example: 'λέξη', sound: "como la l de 'luna'" },
        { char: 'μ', roman: 'm', example: 'μητέρα', sound: "como la m de 'mano'" },
        { char: 'ν', roman: 'n', example: 'νερό', sound: "como la n de 'no' (¡parece una v!)" },
        { char: 'ξ', roman: 'x', example: 'ξένος', sound: "'ks', como la x de 'taxi'" },
        { char: 'π', roman: 'p', example: 'πατέρας', sound: "como la p de 'papá'" },
        { char: 'ρ', roman: 'r', example: 'ρολόι', sound: "r de un toque, como en 'pero' (¡parece una p!)" },
        { char: 'σ/ς', roman: 's', example: 'σπίτι', sound: "como la s de 'sol'; ς solo a final de palabra" },
        { char: 'τ', roman: 't', example: 'τρία', sound: "como la t de 'tren'" },
        { char: 'φ', roman: 'f', example: 'φίλος', sound: "como la f de 'foca'" },
        { char: 'χ', roman: 'ch', example: 'χέρι', sound: "como la jota de 'joven'" },
        { char: 'ψ', roman: 'ps', example: 'ψωμί', sound: "'ps', como en 'pepsi' — incluso a principio de palabra" },
      ],
    },
    {
      title: 'Parejas frecuentes',
      note: 'Dos letras, un sonido — apréndelas como unidades.',
      rows: [
        { char: 'ου', roman: 'ou', example: 'ουρανός', sound: "como la u de 'luna'" },
        { char: 'αι', roman: 'ai', example: 'παιδί', sound: "como la e de 'mesa'" },
        { char: 'ει/οι', roman: 'ei/oi', example: 'είναι', sound: "como la i de 'sí'" },
        { char: 'μπ', roman: 'mp', example: 'μπανάνα', sound: "'b' a principio de palabra; 'mb' en el interior" },
        { char: 'ντ', roman: 'nt', example: 'ντομάτα', sound: "'d' a principio de palabra; 'nd' en el interior" },
        { char: 'γγ/γκ', roman: 'gg/gk', example: 'αγγλικά', sound: "'g' / 'ng-g'" },
      ],
    },
  ],
}

const arabicEs: LanguageLetters = {
  intro: 'El abyad árabe — 28 letras, escritas de derecha a izquierda. Las letras se conectan y cambian de forma según su posición; las vocales breves normalmente no se escriben.',
  sections: [
    {
      title: 'Cómo se unen las letras',
      note: 'El árabe es cursivo por norma: la mayoría de las letras tienen cuatro formas — aislada, inicial, media, final — y se unen a sus vecinas.',
      rows: [
        { char: 'م ح م د → محمد', roman: 'm-H-m-d', example: 'محمد', sound: 'las mismas letras, conectadas: cada una cambia de forma según su posición' },
        { char: 'ب ـبـ ـب', roman: 'b', example: 'باب', sound: 'una letra, tres formas unidas: inicial, media, final' },
        { char: 'ا د ر ز و', roman: '(non-joiners)', example: 'دار', sound: 'seis letras nunca se conectan HACIA DELANTE — fuerzan un hueco en mitad de la palabra' },
        { char: 'ل + ا → لا', roman: 'laa', example: 'سلام', sound: 'lam + alif se funden en la ligadura especial lam-alif' },
      ],
    },
    {
      title: 'Vocales largas y semivocales',
      positions: true,
      rows: [
        { char: 'ا', roman: 'aa', example: 'باب', sound: "'a' larga, como la a de 'agua' sostenida" },
        { char: 'و', roman: 'w/uu', example: 'نور', sound: "la u de 'hueso' (w), o una 'u' larga de 'luna'" },
        { char: 'ي', roman: 'y/ii', example: 'كبير', sound: "la y de 'ya', o una 'i' larga de 'sí'" },
      ],
    },
    {
      title: 'Letras que el español (casi) ya tiene',
      note: 'Cada letra se muestra en sus cuatro posiciones: aislada, y unida al principio, en medio y al final de la palabra.',
      positions: true,
      rows: [
        { char: 'ب', roman: 'b', example: 'بيت', sound: "como la b de 'barco'" },
        { char: 'ت', roman: 't', example: 'تفاح', sound: "como la t de 'tren'" },
        { char: 'ث', roman: 'th', example: 'ثلاثة', sound: "como la z de España en 'zapato'" },
        { char: 'ج', roman: 'j', example: 'جمل', sound: 'como una «y» fuerte rioplatense; la j del inglés jam' },
        { char: 'د', roman: 'd', example: 'دار', sound: "como la d de 'dedo'" },
        { char: 'ذ', roman: 'dh', example: 'هذا', sound: "como la d suave de 'nada'" },
        { char: 'ر', roman: 'r', example: 'رجل', sound: 'vibrante, como la r española' },
        { char: 'ز', roman: 'z', example: 'زيت', sound: 's sonora, con zumbido — no existe en español' },
        { char: 'س', roman: 's', example: 'سلام', sound: "como la s de 'sol'" },
        { char: 'ش', roman: 'sh', example: 'شمس', sound: 'como la sh inglesa de shop' },
        { char: 'ف', roman: 'f', example: 'فيل', sound: "como la f de 'foca'" },
        { char: 'ك', roman: 'k', example: 'كتاب', sound: "como la c de 'casa'" },
        { char: 'ل', roman: 'l', example: 'ليل', sound: "como la l de 'luna'" },
        { char: 'م', roman: 'm', example: 'ماء', sound: "como la m de 'mano'" },
        { char: 'ن', roman: 'n', example: 'نار', sound: "como la n de 'no'" },
        { char: 'ه', roman: 'h', example: 'هنا', sound: 'h aspirada suave, como la j caribeña' },
      ],
    },
    {
      title: 'Los sonidos nuevos',
      note: 'Nacen más al fondo de la garganta que casi todo lo español — y uno ya lo tienes: escucha y copia.',
      positions: true,
      rows: [
        { char: 'ح', roman: 'H / 7', example: 'حب', sound: "una 'h' soplada desde lo hondo de la garganta — como empañar un espejo, más fuerte" },
        { char: 'خ', roman: 'kh / 5', example: 'خبز', sound: "exactamente la jota española de 'joven' — esta ya la tienes" },
        { char: 'ع', roman: '3', example: 'عين', sound: 'una vocal apretada en la garganta — no existe en español; escucha con atención' },
        { char: 'غ', roman: 'gh', example: 'غرب', sound: 'g gargarizada — la r francesa' },
        { char: 'ق', roman: 'q', example: 'قلب', sound: "una 'k' pronunciada en lo más profundo de la boca" },
        { char: 'ء', roman: "2 / '", example: 'سؤال', sound: 'golpe de glotis — el corte de voz entre las vocales de «¡ah-ah!»' },
      ],
    },
    {
      title: 'Las cuatro enfáticas',
      note: 'Gemelas pesadas de t/d/s/z — la lengua se ahueca hacia atrás y toda la palabra se oscurece.',
      positions: true,
      rows: [
        { char: 'ص', roman: 'S', example: 'صباح', sound: "'s' pesada" },
        { char: 'ض', roman: 'D', example: 'ضوء', sound: "'d' pesada" },
        { char: 'ط', roman: 'T', example: 'طعام', sound: "'t' pesada" },
        { char: 'ظ', roman: 'Z', example: 'ظهر', sound: "'d/z' pesada" },
      ],
    },
    {
      title: 'Vocales breves (harakat)',
      note: 'Marcas pequeñas encima o debajo de la letra — fuera de los textos didácticos no suelen escribirse.',
      rows: [
        { char: 'ـَ', roman: 'a', example: 'فَتَحَ', sound: "'a' breve, tirando a la e (fatha)" },
        { char: 'ـِ', roman: 'i', example: 'بِنت', sound: "'i' breve y relajada (kasra)" },
        { char: 'ـُ', roman: 'u', example: 'كُتُب', sound: "'u' breve y relajada (damma)" },
        { char: 'ـّ', roman: '(double)', example: 'مُدَرِّس', sound: 'shadda — sostén la consonante el doble de tiempo' },
      ],
    },
  ],
}

const hindiEs: LanguageLetters = {
  intro: 'El devanagari: cada consonante lleva una «a» incorporada; los signos vocálicos (matras) la sustituyen. Los sonidos estrella: letras retroflejas (lengua curvada hacia atrás) frente a dentales (lengua en los dientes — como la t y la d españolas), y parejas aspiradas con un soplo extra de aire.',
  sections: [
    {
      title: 'Cómo se unen las letras',
      note: 'El devanagari construye sílabas: los signos vocálicos se acoplan a las consonantes, y el virama (्) suelda consonantes en grupos.',
      rows: [
        { char: 'क + ा → का', roman: 'k + aa', example: 'काम', sound: 'un signo vocálico (matra) sustituye la a incorporada' },
        { char: 'क + ि → कि', roman: 'k + i', example: 'किताब', sound: 'la matra de i se escribe a la IZQUIERDA de su consonante' },
        { char: 'स + ् + त → स्त', roman: 's+t', example: 'नमस्ते', sound: 'el virama borra la a y funde el par en un solo grupo' },
        { char: 'क + ् + ष → क्ष', roman: 'ksh', example: 'क्षमा', sound: 'algunos grupos reciben una forma completamente nueva — aprende de vista los más comunes' },
        { char: 'र special', roman: 'r', example: 'कर्म / प्रेम', sound: 'la r va ENCIMA del grupo cuando es la primera (कर्म) y como un trazo pequeño debajo cuando es la segunda (प्रेम)' },
      ],
    },
    {
      title: 'Vocales independientes',
      note: 'Se usan a principio de palabra; dentro de la palabra se convierten en matras (sección siguiente).',
      rows: [
        { char: 'अ', roman: 'a', example: 'अब', sound: "'a' breve y apagada, hacia la «e» neutra" },
        { char: 'आ', roman: 'aa', example: 'आम', sound: "'a' larga, como la a de 'agua' sostenida" },
        { char: 'इ', roman: 'i', example: 'इधर', sound: "'i' breve y relajada" },
        { char: 'ई', roman: 'ii', example: 'ईद', sound: "'i' larga, como la i de 'sí'" },
        { char: 'उ', roman: 'u', example: 'उधर', sound: "'u' breve y relajada" },
        { char: 'ऊ', roman: 'uu', example: 'ऊपर', sound: "'u' larga, como la u de 'luna'" },
        { char: 'ए', roman: 'e', example: 'एक', sound: "e cerrada, como la e de 'bebé' (sin deslizamiento)" },
        { char: 'ऐ', roman: 'ai', example: 'ऐनक', sound: 'entre a y e, con la boca abierta (la a inglesa de cat)' },
        { char: 'ओ', roman: 'o', example: 'ओर', sound: "o cerrada, como la o de 'poco' (sin deslizamiento)" },
        { char: 'औ', roman: 'au', example: 'औरत', sound: 'o muy abierta, tirando a la a' },
      ],
    },
    {
      title: 'Las mismas vocales como matras',
      note: 'Se muestra क como portadora. La अ incorporada no necesita marca.',
      rows: [
        { char: 'का', roman: 'kaa', example: 'काम', sound: 'k + a larga' },
        { char: 'कि', roman: 'ki', example: 'किताब', sound: 'k + i (la marca va DELANTE de la letra)' },
        { char: 'की', roman: 'kii', example: 'की', sound: 'k + i larga' },
        { char: 'कु', roman: 'ku', example: 'कुछ', sound: 'k + u breve' },
        { char: 'कू', roman: 'kuu', example: 'कूद', sound: 'k + u larga' },
        { char: 'के', roman: 'ke', example: 'के', sound: 'k + e cerrada' },
        { char: 'कै', roman: 'kai', example: 'कैसा', sound: 'k + a abierta (hacia la e)' },
        { char: 'को', roman: 'ko', example: 'को', sound: 'k + o' },
        { char: 'कौ', roman: 'kau', example: 'कौन', sound: 'k + o abierta' },
        { char: 'कं', roman: 'kaM', example: 'कंघी', sound: 'zumbido nasal tras la vocal (anusvara)' },
      ],
    },
    {
      title: 'Consonantes — las parejas aspiradas',
      note: 'La segunda de cada pareja añade un soplo de aire (pon la palma delante de la boca — deberías sentirlo).',
      rows: [
        { char: 'क / ख', roman: 'k / kh', example: 'खाना', sound: "'k' simple, luego 'k' + soplo" },
        { char: 'ग / घ', roman: 'g / gh', example: 'घर', sound: "'g' simple, luego 'g' + soplo" },
        { char: 'च / छ', roman: 'ch / chh', example: 'छह', sound: "'ch' de 'chico' simple, luego 'ch' + soplo" },
        { char: 'ज / झ', roman: 'j / jh', example: 'झील', sound: '«y» fuerte rioplatense simple, luego con soplo' },
        { char: 'प / फ', roman: 'p / ph', example: 'फल', sound: "'p' simple, luego 'p' + soplo" },
        { char: 'ब / भ', roman: 'b / bh', example: 'भाई', sound: "'b' simple, luego 'b' + soplo" },
      ],
    },
    {
      title: 'Retroflejas frente a dentales — la gran división',
      note: 'Retroflejas: lengua curvada hacia el paladar. Dentales: lengua en los dientes — justo donde ya están la t y la d españolas. Las retroflejas son las nuevas para ti.',
      rows: [
        { char: 'ट / ठ', roman: 'T / Th', example: 'टमाटर', sound: 't retrofleja (simple / + soplo)' },
        { char: 'ड / ढ', roman: 'D / Dh', example: 'डर', sound: 'd retrofleja (simple / + soplo)' },
        { char: 'ण', roman: 'N', example: 'बाण', sound: 'n retrofleja' },
        { char: 'त / थ', roman: 't / th', example: 'तीन', sound: 't dental — como la t española (simple / + soplo)' },
        { char: 'द / ध', roman: 'd / dh', example: 'दो', sound: 'd dental, como la española (simple / + soplo)' },
        { char: 'न', roman: 'n', example: 'नाम', sound: "como la n de 'no'" },
        { char: 'ड़ / ढ़', roman: 'R / Rh', example: 'लड़का', sound: 'r de golpe — la lengua baja azotando desde la posición retrofleja' },
      ],
    },
    {
      title: 'El resto',
      rows: [
        { char: 'म', roman: 'm', example: 'माँ', sound: "como la m de 'mano'" },
        { char: 'य', roman: 'y', example: 'यह', sound: "como la y de 'ya'" },
        { char: 'र', roman: 'r', example: 'रात', sound: "r suave de un toque, como en 'pero'" },
        { char: 'ल', roman: 'l', example: 'लाल', sound: "como la l de 'luna'" },
        { char: 'व', roman: 'v/w', example: 'वह', sound: "entre una v labiodental y la u de 'hueso'" },
        { char: 'श / ष', roman: 'sh / Sh', example: 'शहर', sound: 'como la sh inglesa de shop' },
        { char: 'स', roman: 's', example: 'सात', sound: "como la s de 'sol'" },
        { char: 'ह', roman: 'h', example: 'हाँ', sound: 'h aspirada, como una jota muy suave' },
      ],
    },
    {
      title: 'Letras con nuqta (sonidos prestados)',
      note: 'Un punto bajo la letra marca sonidos persa-árabes.',
      rows: [
        { char: 'ज़', roman: 'z', example: 'ज़रूर', sound: 's sonora, con zumbido — no existe en español' },
        { char: 'फ़', roman: 'f', example: 'फ़ोन', sound: "como la f de 'foca'" },
        { char: 'क़', roman: 'q', example: 'क़लम', sound: "'k' al fondo de la boca" },
        { char: 'ख़ / ग़', roman: 'kh / gh', example: 'ख़बर', sound: "la jota de 'joven' / g gargarizada" },
      ],
    },
  ],
}

const thaiEs: LanguageLetters = {
  intro: 'La escritura tailandesa: 44 consonantes en tres CLASES (la clase + el signo de tono deciden el tono), vocales que se acoplan alrededor de la consonante y ningún espacio entre palabras.',
  sections: [
    {
      title: 'Cómo se unen las letras',
      note: 'Las vocales envuelven su consonante — delante, detrás, encima o debajo — y los signos de tono se apilan encima.',
      rows: [
        { char: 'ก + า → กา', roman: 'k + aa', example: 'กาแฟ', sound: 'esta vocal va detrás de la consonante' },
        { char: 'ก + ิ → กิ', roman: 'k + i', example: 'กิน', sound: 'esta vocal se coloca ENCIMA' },
        { char: 'ก + ุ → กุ', roman: 'k + u', example: 'กุ้ง', sound: 'esta vocal cuelga DEBAJO' },
        { char: 'เ + ก → เก', roman: 'k + e', example: 'เกาะ', sound: 'esta vocal se escribe ANTES de la consonante tras la que se pronuncia' },
        { char: 'เ-ีย, เ-ือ', roman: 'ia, uea', example: 'เมีย', sound: 'las vocales compuestas rodean la consonante por dos o tres lados' },
        { char: 'ก่ ก้ ก๊ ก๋', roman: 'tones', example: 'ไม่', sound: 'cuatro signos de tono se apilan encima; la clase de la consonante decide qué significan' },
      ],
    },
    {
      title: 'Consonantes de diario (clase media)',
      rows: [
        { char: 'ก', roman: 'g/k', example: 'ไก่', sound: "entre g y k — como la c de 'casa' sin ni un soplo de aire" },
        { char: 'จ', roman: 'j', example: 'จาน', sound: "una ch seca y tensa, sin soplo — más nítida que la de 'chico'" },
        { char: 'ด', roman: 'd', example: 'เด็ก', sound: "como la d de 'dedo'" },
        { char: 'ต', roman: 'dt', example: 'ตา', sound: 'entre d y t — prácticamente la t española, sin soplo' },
        { char: 'บ', roman: 'b', example: 'บ้าน', sound: "como la b de 'barco'" },
        { char: 'ป', roman: 'bp', example: 'ปลา', sound: 'entre b y p — prácticamente la p española, sin soplo' },
        { char: 'อ', roman: '(silent)', example: 'อาหาร', sound: 'la consonante muda que sirve de soporte a las vocales solas' },
      ],
    },
    {
      title: 'Consonantes con soplo (parejas alta + baja)',
      note: 'Mismo sonido, distinta clase — la clase cambia el TONO de la sílaba.',
      rows: [
        { char: 'ข / ค', roman: 'kh', example: 'ขาว / ควาย', sound: "'k' + soplo de aire (clase alta / clase baja)" },
        { char: 'ถ / ท', roman: 'th', example: 'ถนน / ทำ', sound: "'t' + soplo (alta / baja)" },
        { char: 'ผ / พ', roman: 'ph', example: 'ผม / พ่อ', sound: "'p' + soplo — ¡nunca una f! (alta / baja)" },
        { char: 'ฝ / ฟ', roman: 'f', example: 'ฝน / ไฟ', sound: "como la f de 'foca' (alta / baja)" },
        { char: 'ส / ซ', roman: 's', example: 'สวย / ซ้าย', sound: "'s' (alta / baja)" },
        { char: 'ห / ฮ', roman: 'h', example: 'หก / ฮา', sound: "'h' aspirada (alta / baja); ห además sube en silencio la clase de la letra siguiente" },
      ],
    },
    {
      title: 'Sonorantes y el resto',
      rows: [
        { char: 'ม', roman: 'm', example: 'แม่', sound: "como la m de 'mano'" },
        { char: 'น / ณ', roman: 'n', example: 'น้ำ', sound: "como la n de 'no'" },
        { char: 'ง', roman: 'ng', example: 'งู', sound: "como la n de 'banco' (ng) — también a PRINCIPIO de palabra" },
        { char: 'ร', roman: 'r', example: 'รถ', sound: 'r vibrante, como en español (en el habla coloquial suele volverse l)' },
        { char: 'ล', roman: 'l', example: 'ลิง', sound: "como la l de 'luna'" },
        { char: 'ว', roman: 'w', example: 'วัน', sound: "como la u de 'hueso' (w)" },
        { char: 'ย / ญ', roman: 'y', example: 'ยา', sound: "como la y de 'ya'" },
        { char: 'ช', roman: 'ch', example: 'ช้าง', sound: "'ch' de 'chico' + soplo de aire" },
      ],
    },
    {
      title: 'Vocales básicas (mostradas sobre ก)',
      note: 'Breve o larga cambia el significado — sostén las largas de forma notoria.',
      rows: [
        { char: 'กะ / กา', roman: 'a / aa', example: 'มา', sound: "'a' breve / larga, como la a de 'agua'" },
        { char: 'กิ / กี', roman: 'i / ii', example: 'มี', sound: "'i' breve / larga, como la i de 'sí'" },
        { char: 'กุ / กู', roman: 'u / uu', example: 'ดู', sound: "'u' breve / larga, como la u de 'luna'" },
        { char: 'เกะ / เก', roman: 'e', example: 'เย็น', sound: "'e' de 'mesa' breve / e cerrada larga" },
        { char: 'โกะ / โก', roman: 'o', example: 'โต', sound: "'o' breve / larga y cerrada" },
        { char: 'ไก / ใก', roman: 'ai', example: 'ไป', sound: "como ay en 'hay' — dos grafías, el mismo sonido" },
        { char: 'เกา', roman: 'ao', example: 'เก้า', sound: "como au en 'auto'" },
        { char: 'กือ', roman: 'ue', example: 'มือ', sound: "una 'u' con los labios estirados — no existe en español" },
      ],
    },
    {
      title: 'Los cinco tonos',
      note: 'La misma sílaba, cinco significados. El tono sale de: clase de la consonante + signo de tono + tipo de sílaba.',
      rows: [
        { char: 'มา (medio)', roman: 'maa', example: 'มา', sound: 'tono llano — venir' },
        { char: 'หม่า (bajo)', roman: 'màa', example: 'ไม่', sound: 'empieza bajo y se queda bajo' },
        { char: 'ม้า (alto… descendente)', roman: 'máa', example: 'ม้า', sound: 'tono alto — caballo' },
        { char: 'หม้า (descendente)', roman: 'mâa', example: 'บ้าน', sound: 'cae de alto a bajo' },
        { char: 'หมา (ascendente)', roman: 'mǎa', example: 'หมา', sound: 'baja y luego sube — perro (¡ojo con el par caballo/perro!)' },
      ],
    },
  ],
}

const koreanEs: LanguageLetters = {
  intro: 'El hangul — 24 letras básicas que se ENSAMBLAN en bloques silábicos. Inventado en 1443 para aprenderse en una mañana; las formas hasta dibujan la boca haciendo el sonido.',
  sections: [
    {
      title: 'Cómo se unen las letras',
      note: 'Las letras se apilan en bloques silábicos cuadrados: consonante + vocal, más una consonante final opcional (받침) debajo. 한국 son seis letras en dos bloques.',
      rows: [
        { char: 'ㅎ + ㅏ + ㄴ → 한', roman: 'h + a + n', example: '한국', sound: 'consonante a la izquierda, vocal vertical a la derecha, letra final debajo' },
        { char: 'ㄱ + ㅜ + ㄱ → 국', roman: 'g + u + k', example: '한국', sound: 'las vocales horizontales van DEBAJO de la primera consonante' },
        { char: 'ㅅ + ㅏ → 사', roman: 's + a', example: '사람', sound: 'sin letra final — solo consonante + vocal' },
        { char: 'ㅇ + ㅜ → 우', roman: '(silent) + u', example: '우유', sound: 'ㅇ es un soporte mudo cuando el bloque empieza por vocal' },
        { char: 'ㅂ + ㅏ + ㅂ → 밥', roman: 'b + a + p', example: '밥', sound: 'la ㅂ final (받침) cierra la sílaba' },
        { char: '받침 rule', roman: 'finals', example: '있다', sound: 'solo 7 sonidos pueden cerrar un bloque: k, n, t, l, m, p, ng — la ortografía conserva la letra, la boca la simplifica' },
      ],
    },
    {
      title: 'Consonantes simples',
      rows: [
        { char: 'ㄱ', roman: 'g/k', example: '가다', sound: "entre 'g' y 'k' — 'g' a principio de palabra" },
        { char: 'ㄴ', roman: 'n', example: '나', sound: "como la n de 'no'" },
        { char: 'ㄷ', roman: 'd/t', example: '돈', sound: "entre 'd' y 't'" },
        { char: 'ㄹ', roman: 'r/l', example: '물', sound: "r de un toque ('pero') entre vocales; 'l' al final del bloque" },
        { char: 'ㅁ', roman: 'm', example: '몸', sound: "como la m de 'mano'" },
        { char: 'ㅂ', roman: 'b/p', example: '밥', sound: "entre 'b' y 'p'" },
        { char: 'ㅅ', roman: 's', example: '사람', sound: "como la s de 'sol'; 'sh' ante ㅣ" },
        { char: 'ㅇ', roman: '-/ng', example: '강', sound: "muda al principio; al final, la n de 'banco' (ng)" },
        { char: 'ㅈ', roman: 'j', example: '집', sound: 'entre la «y» fuerte rioplatense y la ch' },
        { char: 'ㅎ', roman: 'h', example: '하다', sound: 'h aspirada suave, como la j caribeña' },
      ],
    },
    {
      title: 'Consonantes aspiradas (añaden un soplo de aire)',
      note: 'Cada una es la consonante simple con un trazo extra y un soplo extra.',
      rows: [
        { char: 'ㅋ', roman: 'k', example: '코', sound: "'k' con un soplo fuerte (ㄱ + aire)" },
        { char: 'ㅌ', roman: 't', example: '토요일', sound: "'t' con un soplo fuerte (ㄷ + aire)" },
        { char: 'ㅍ', roman: 'p', example: '팔', sound: "'p' con un soplo fuerte (ㅂ + aire)" },
        { char: 'ㅊ', roman: 'ch', example: '차', sound: "'ch' con un soplo fuerte (ㅈ + aire)" },
      ],
    },
    {
      title: 'Consonantes tensas (dobladas, sin aire)',
      note: "Dilas con la garganta apretada y cero soplo — como la p española de 'papá', pero aún más tensa.",
      rows: [
        { char: 'ㄲ', roman: 'kk', example: '까만', sound: "una 'k' tensa, sin nada de soplo" },
        { char: 'ㄸ', roman: 'tt', example: '딸', sound: "una 't' tensa, sin soplo" },
        { char: 'ㅃ', roman: 'pp', example: '빵', sound: "una 'p' tensa, sin soplo" },
        { char: 'ㅆ', roman: 'ss', example: '쌀', sound: "una 's' tensa" },
        { char: 'ㅉ', roman: 'jj', example: '짜다', sound: "una 'ch' tensa, sin soplo" },
      ],
    },
    {
      title: 'Vocales básicas',
      rows: [
        { char: 'ㅏ', roman: 'a', example: '아빠', sound: "como la a de 'agua'" },
        { char: 'ㅓ', roman: 'eo', example: '어머니', sound: "una 'o' abierta y relajada, tirando a la a" },
        { char: 'ㅗ', roman: 'o', example: '오늘', sound: "o cerrada, como la o de 'poco' (labios redondeados)" },
        { char: 'ㅜ', roman: 'u', example: '우리', sound: "como la u de 'luna'" },
        { char: 'ㅡ', roman: 'eu', example: '그', sound: "una 'u' con los labios PLANOS — di «u» mientras sonríes" },
        { char: 'ㅣ', roman: 'i', example: '이름', sound: "como la i de 'sí'" },
        { char: 'ㅐ', roman: 'ae', example: '개', sound: "como la e de 'mesa' (igual que ㅔ en el habla moderna)" },
        { char: 'ㅔ', roman: 'e', example: '세 시', sound: "como la e de 'mesa'" },
      ],
    },
    {
      title: 'Vocales con y- y con w-',
      note: 'Un trazo extra añade y-; combinar dos vocales crea w-.',
      rows: [
        { char: 'ㅑ ㅕ ㅛ ㅠ', roman: 'ya yeo yo yu', example: '야구, 여자', sound: 'las cuatro vocales básicas con una y- delante' },
        { char: 'ㅒ ㅖ', roman: 'yae ye', example: '예', sound: "'ye', como en 'yerba'" },
        { char: 'ㅘ ㅝ', roman: 'wa wo', example: '와요, 뭐', sound: "'ua' como en 'cuatro', 'uo' como en 'cuota'" },
        { char: 'ㅙ ㅞ ㅚ', roman: 'wae we oe', example: '왜, 회사', sound: "en el habla moderna las tres suenan 'ue', como en 'bueno'" },
        { char: 'ㅟ', roman: 'wi', example: '귀', sound: "'ui', como en 'fui'" },
        { char: 'ㅢ', roman: 'ui', example: '의사', sound: "'u' plana + 'i' deslizadas; al hablar, a menudo solo 'i' o 'e'" },
      ],
    },
  ],
}

const hebrewEs: LanguageLetters = {
  intro: 'El alefato hebreo — 22 letras, de derecha a izquierda. Cada letra mantiene una sola forma (cinco cambian al final de la palabra); las vocales casi nunca se escriben.',
  sections: [
    {
      title: 'Letras que el español ya tiene',
      rows: [
        { char: 'ב', roman: 'b', example: 'בית', sound: "como la b de 'barco' ('v' sin su punto)" },
        { char: 'ג', roman: 'g', example: 'גדול', sound: "como la g de 'gato'" },
        { char: 'ד', roman: 'd', example: 'דג', sound: "como la d de 'dedo'" },
        { char: 'ה', roman: 'h', example: 'הר', sound: 'h aspirada suave (como en inglés); muda a final de palabra' },
        { char: 'ו', roman: 'v', example: 'ורד', sound: "v labiodental; también escribe la 'o'/'u' larga" },
        { char: 'ז', roman: 'z', example: 'זמן', sound: 'z sonora, un zumbido — la z inglesa de zoo' },
        { char: 'י', roman: 'y', example: 'יד', sound: "como la y de 'yo'; también escribe la 'i' larga" },
        { char: 'כ', roman: 'k', example: 'כלב', sound: "como la c de 'casa'; sin su punto suena como la j" },
        { char: 'ל', roman: 'l', example: 'לילה', sound: "como la l de 'luna'" },
        { char: 'מ', roman: 'm', example: 'מים', sound: "como la m de 'mano'" },
        { char: 'נ', roman: 'n', example: 'נר', sound: "como la n de 'noche'" },
        { char: 'ס', roman: 's', example: 'ספר', sound: "como la s de 'sol'" },
        { char: 'פ', roman: 'p', example: 'פרח', sound: "como la p de 'pan'; sin su punto, f" },
        { char: 'ק', roman: 'q', example: 'קטן', sound: 'otra c de casa (hoy igual que כ)' },
        { char: 'ר', roman: 'r', example: 'ראש', sound: 'r gutural, como la r francesa' },
        { char: 'ש', roman: 'sh', example: 'שלום', sound: 'la sh inglesa de shop; con punto a la izquierda, s' },
        { char: 'ת', roman: 't', example: 'תודה', sound: "como la t de 'tú'" },
      ],
    },
    {
      title: 'Los sonidos nuevos',
      rows: [
        { char: 'א', roman: 'a', example: 'אבא', sound: 'muda — un asiento para la vocal' },
        { char: 'ח', roman: 'ch', example: 'חלב', sound: 'como la j española, desde la garganta' },
        { char: 'ט', roman: 'T', example: 'טוב', sound: 'otra t (hoy igual que ת); la ortografía las distingue' },
        { char: 'ע', roman: "'", example: 'עין', sound: 'un apretón en la garganta; hoy casi siempre muda' },
        { char: 'צ', roman: 'ts', example: 'ציפור', sound: "'ts' como en 'tsunami'" },
      ],
    },
    {
      title: 'Formas finales',
      note: 'Cinco letras cambian de forma al final de la palabra — misma letra, mismo sonido. El teclado lo hace solo.',
      rows: [
        { char: 'כ → ך', roman: 'k', example: 'מלך', sound: 'kaf a final de palabra' },
        { char: 'מ → ם', roman: 'm', example: 'מים', sound: 'mem a final de palabra' },
        { char: 'נ → ן', roman: 'n', example: 'בן', sound: 'nun a final de palabra' },
        { char: 'פ → ף', roman: 'p/f', example: 'סוף', sound: 'pe a final de palabra' },
        { char: 'צ → ץ', roman: 'ts', example: 'ארץ', sound: 'tsadi a final de palabra' },
      ],
    },
    {
      title: 'A dónde fueron las vocales',
      note: 'El hebreo cotidiano deja la mayoría de las vocales sin escribir (el ktiv malé escribe la o/u larga con ו y la i con י). Los puntos (nikud) solo aparecen en libros infantiles, poesía y diccionarios.',
      rows: [
        { char: 'וֹ / וּ', roman: 'o / u', example: 'שלום', sound: "vav haciendo de vocal: 'o' o 'u' larga" },
        { char: 'י', roman: 'i', example: 'דין', sound: "yod haciendo de vocal: 'i' larga" },
        { char: 'בַ בֶ בִ', roman: '(niqqud)', example: 'בַּיִת', sound: 'los puntos vocálicos bajo la letra — casi siempre omitidos' },
      ],
    },
  ],
}

const persianEs: LanguageLetters = {
  intro: 'El persa usa la escritura árabe — 32 letras, de derecha a izquierda, cursiva por regla — pero su fonética es mucho más simple: sin enfáticas ni guturales fuertes, y varias letras prestadas que se fundieron en s, z, t y h simples.',
  sections: [
    {
      title: 'Las cuatro letras exclusivas del persa',
      note: 'Añadidas a la escritura árabe para sonidos que el árabe no tiene.',
      positions: true,
      rows: [
        { char: 'پ', roman: 'p', example: 'پدر', sound: "como la p de 'pan'" },
        { char: 'چ', roman: 'ch', example: 'چای', sound: "como la ch de 'chico'" },
        { char: 'ژ', roman: 'zh', example: 'ژاله', sound: 'como la j francesa de jour' },
        { char: 'گ', roman: 'g', example: 'گل', sound: "como la g de 'gato'" },
      ],
    },
    {
      title: 'Letras que el español ya tiene',
      positions: true,
      rows: [
        { char: 'ب', roman: 'b', example: 'باب', sound: "como la b de 'barco'" },
        { char: 'ت', roman: 't', example: 'تهران', sound: "como la t de 'tú'" },
        { char: 'ج', roman: 'j', example: 'جان', sound: "como la y fuerte rioplatense; el j inglés de jam" },
        { char: 'د', roman: 'd', example: 'دست', sound: "como la d de 'dedo'" },
        { char: 'ر', roman: 'r', example: 'روز', sound: "r simple de 'pero'" },
        { char: 'ز', roman: 'z', example: 'زبان', sound: 'z sonora — la z inglesa de zoo' },
        { char: 'س', roman: 's', example: 'سلام', sound: "como la s de 'sol'" },
        { char: 'ش', roman: 'sh', example: 'شب', sound: 'la sh inglesa de shop' },
        { char: 'ف', roman: 'f', example: 'فردا', sound: "como la f de 'flor'" },
        { char: 'ک', roman: 'k', example: 'کتاب', sound: "como la c de 'casa'" },
        { char: 'ل', roman: 'l', example: 'لب', sound: "como la l de 'luna'" },
        { char: 'م', roman: 'm', example: 'مادر', sound: "como la m de 'mano'" },
        { char: 'ن', roman: 'n', example: 'نان', sound: "como la n de 'noche'" },
        { char: 'ه', roman: 'h', example: 'هفت', sound: 'h aspirada suave, como en inglés' },
        { char: 'و', roman: 'v', example: 'وقت', sound: "v labiodental; también escribe la 'u'/'o' larga" },
        { char: 'ی', roman: 'y', example: 'یک', sound: "como la y de 'yo'; también escribe la 'i' larga" },
      ],
    },
    {
      title: 'Las gemelas prestadas',
      note: 'Los préstamos árabes conservaron su ortografía, pero el persa fundió los sonidos — estas letras suenan exactamente como s, z, t, h o q. La ortografía distingue las palabras; tu boca no hace nada especial.',
      positions: true,
      rows: [
        { char: 'ث', roman: 's', example: 'ثانیه', sound: "s simple (el th árabe)" },
        { char: 'ص', roman: 's', example: 'صبح', sound: 's simple' },
        { char: 'ذ', roman: 'z', example: 'ذهن', sound: 'z sonora simple (el dh árabe)' },
        { char: 'ض', roman: 'z', example: 'ضعیف', sound: 'z sonora simple' },
        { char: 'ظ', roman: 'z', example: 'ظهر', sound: 'z sonora simple' },
        { char: 'ط', roman: 't', example: 'طلا', sound: 't simple' },
        { char: 'ح', roman: 'h', example: 'حال', sound: 'h simple' },
        { char: 'ع', roman: "'", example: 'عشق', sound: 'un pequeño corte, o nada — mucho más suave que en árabe' },
        { char: 'غ', roman: 'gh', example: 'غذا', sound: 'g gargarizada — una r francesa' },
        { char: 'ق', roman: 'q / gh', example: 'قلب', sound: 'la misma g gargarizada para la mayoría de los hablantes' },
      ],
    },
    {
      title: 'Las vocales y el medio espacio',
      rows: [
        { char: 'آ', roman: 'aa', example: 'آب', sound: "una 'a' larga y oscura, hacia la o — alef con sombrero (madda)" },
        { char: 'ا', roman: 'a', example: 'اسم', sound: 'asiento de la vocal al principio de la palabra' },
        { char: 'و / ی', roman: 'oo / ee', example: 'دور، شیر', sound: 'la u y la i largas, escritas con vav y ye' },
        { char: 'ــِـ ــَـ ــُـ', roman: 'e a o', example: 'دَر', sound: 'las vocales breves — casi nunca se escriben' },
        { char: '‌ (نیم‌فاصله)', roman: '-', example: 'می‌روم', sound: 'el medio espacio (ZWNJ): mantiene می unido-pero-separado de su verbo — se teclea con -' },
      ],
    },
  ],
}

export const LETTERS_ES: Record<string, LanguageLetters> = {
  he: hebrewEs,
  fa: persianEs,
  es: spanishEs,
  fr: frenchEs,
  de: germanEs,
  it: italianEs,
  ca: catalanEs,
  pt: portugueseEs,
  ro: romanianEs,
  tr: turkishEs,
  sw: swahiliEs,
  yo: yorubaEs,
  ha: hausaEs,
  xh: xhosaEs,
  mi: maoriEs,
  jam: jamaicanEs,
  en: englishEs,
  nl: dutchEs,
  ru: russianEs,
  el: greekEs,
  ar: arabicEs,
  hi: hindiEs,
  th: thaiEs,
  ko: koreanEs,
}
