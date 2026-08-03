/**
 * Letters & Sounds — French (fr) UI-language overlay, all 22 courses.
 * Sound descriptions are re-anchored for a French-speaking reader: every
 * anchor word is French, and sounds French lacks are described (or pointed
 * at English/Spanish) rather than left on an English anchor. The `fr`
 * course entry describes French natively. `char`/`roman`/`example` are
 * copied from the base data; only parenthetical asides are localized.
 */
import type { LanguageLetters } from './lettersData'

const spanishFr: LanguageLetters = {
  intro:
    'L’orthographe espagnole est honnête : cinq voyelles pures, et presque chaque lettre se prononce toujours de la même façon.',
  sections: [
    {
      title: 'Les cinq voyelles',
      note: 'Brèves, pures, jamais traînées. L’accent (á é í ó ú) marque la syllabe tonique — le son ne change pas.',
      rows: [
        { char: 'a / á', example: 'agua', sound: 'comme le a de « papa »' },
        { char: 'e / é', example: 'leche', sound: 'comme le è de « mère »' },
        { char: 'i / í', example: 'vivir', sound: 'comme le i de « ici »' },
        { char: 'o / ó', example: 'poco', sound: 'comme le o de « fort »' },
        { char: 'u / ú', example: 'luna', sound: 'comme ou dans « fou » (muet dans que/qui, gue/gui)' },
        { char: 'ü', example: 'pingüino', sound: 'les deux points réveillent le u : gü = « gou » bref (gw)' },
      ],
    },
    {
      title: 'Les consonnes qui diffèrent du français',
      rows: [
        { char: 'ñ', example: 'niño', sound: 'comme le gn de « montagne »' },
        { char: 'j', example: 'joven', sound: 'la jota — un raclement sourd du fond de la gorge, un r français sans la voix' },
        { char: 'g (+e/i)', example: 'gente', sound: 'la même jota raclée ; ailleurs, g dur' },
        { char: 'll / y', example: 'llamar', sound: 'comme le y de « yoga » (un j doux dans une grande partie de l’Amérique latine)' },
        { char: 'h', example: 'hola', sound: 'toujours muet' },
        { char: 'rr / r-', example: 'perro', sound: 'r roulé ; le r simple entre voyelles est une battue brève' },
        { char: 'z / c(+e,i)', example: 'zapato', sound: 's en Amérique latine ; en Espagne, le th anglais de think (langue entre les dents)' },
        { char: 'v', example: 'vaso', sound: 'comme b — un b relâché' },
        { char: 'qu', example: 'queso', sound: 'k — le u est muet' },
      ],
    },
  ],
}

const frenchFr: LanguageLetters = {
  intro:
    'Les sons du français vivent dans les voyelles et dans l’enchaînement des mots. Les consonnes finales sont le plus souvent muettes ; les accents changent le timbre de la voyelle, pas l’accent tonique.',
  sections: [
    {
      title: 'Les voyelles et leurs accents',
      rows: [
        { char: 'a / à / â', example: 'chat', sound: 'un a franc, comme dans « papa »' },
        { char: 'é', example: 'été', sound: 'é fermé, net, sans aucun glissement' },
        { char: 'è / ê / e(+2 cons.)', example: 'mère', sound: 'è ouvert, comme dans « père »' },
        { char: 'e (sans accent)', example: 'le', sound: 'le e muet — souvent escamoté à l’oral' },
        { char: 'i / î / y', example: 'ville', sound: 'un i net, comme dans « vie »' },
        { char: 'o / ô', example: 'mot', sound: 'o fermé, comme dans « eau »' },
        { char: 'u / û', example: 'tu', sound: 'u fermé, lèvres arrondies vers l’avant, comme dans « lune »' },
        { char: 'ou', example: 'vous', sound: 'ou profond, comme dans « fou »' },
        { char: 'eu / œu', example: 'peu', sound: 'eu fermé, comme dans « feu »' },
        { char: 'oi', example: 'moi', sound: '« oua », comme dans « roi »' },
        { char: 'au / eau', example: 'eau', sound: 'o fermé, comme dans « chaud »' },
        { char: 'ai / ei', example: 'maison', sound: 'è ouvert, comme dans « lait »' },
      ],
    },
    {
      title: 'Les voyelles nasales',
      note: 'Voyelle + n/m dans la même syllabe = l’air passe par le nez, et le n/m lui-même ne se prononce PAS.',
      rows: [
        { char: 'on / om', example: 'bon', sound: 'le on de « bon » — un o nasal' },
        { char: 'an / en', example: 'enfant', sound: 'le an de « maman » — un a nasal' },
        { char: 'in / ain / ein', example: 'vin', sound: 'le in de « pain » — un è nasal' },
        { char: 'un', example: 'un', sound: 'le un de « brun » (beaucoup de locuteurs le confondent avec in)' },
      ],
    },
    {
      title: 'Les habitudes des consonnes',
      rows: [
        { char: 'r', example: 'rouge', sound: 'frotté au fond de la gorge, jamais roulé de la pointe de la langue' },
        { char: 'ç', example: 'garçon', sound: 's — la cédille garde le c doux devant a/o/u' },
        { char: 'ch', example: 'chien', sound: 'comme dans « chat »' },
        { char: 'gn', example: 'montagne', sound: 'comme dans « agneau »' },
        { char: 'j / g(+e,i)', example: 'jour', sound: 'le j de « jour »' },
        { char: 'h', example: 'homme', sound: 'muet' },
        { char: 'final consonants', example: 'petit', sound: 'les consonnes finales sont le plus souvent muettes — attention à s, t, d, x' },
      ],
    },
  ],
}

const germanFr: LanguageLetters = {
  intro:
    'L’allemand se prononce comme il s’écrit, une fois qu’on connaît les umlauts et une poignée d’équipes de lettres.',
  sections: [
    {
      title: 'Voyelles et umlauts',
      rows: [
        { char: 'a', example: 'Haus', sound: 'comme le a de « papa »' },
        { char: 'ä', example: 'Mädchen', sound: 'comme le è de « mère »' },
        { char: 'o', example: 'Brot', sound: 'o fermé, comme dans « eau »' },
        { char: 'ö', example: 'schön', sound: 'comme eu dans « peu »' },
        { char: 'u', example: 'gut', sound: 'comme ou dans « fou »' },
        { char: 'ü', example: 'über', sound: 'comme le u français de « lune »' },
        { char: 'ei', example: 'mein', sound: 'comme « aï » dans « aïe ! »' },
        { char: 'ie', example: 'Liebe', sound: 'comme le i de « vie »' },
        { char: 'eu / äu', example: 'heute', sound: 'comme « oy » dans « cow-boy »' },
        { char: 'au', example: 'Auto', sound: 'comme « aou » dans « caoutchouc », en une seule syllabe' },
      ],
    },
    {
      title: 'Équipes de consonnes',
      rows: [
        { char: 'w', example: 'Wasser', sound: 'comme le v de « vache »' },
        { char: 'v', example: 'Vater', sound: 'comme le f de « feu »' },
        { char: 'z', example: 'Zeit', sound: 'ts, comme dans « tsar »' },
        { char: 's (+voyelle)', example: 'Sonne', sound: 'comme le z de « zoo »' },
        { char: 'ß / ss', example: 'Straße', sound: 's dur, comme dans « passe »' },
        { char: 'sch', example: 'Schule', sound: 'comme ch dans « chat »' },
        { char: 'st- / sp-', example: 'Straße', sound: '« cht » / « chp » en début de mot' },
        { char: 'ch (après a/o/u)', example: 'Buch', sound: 'raclé au fond de la gorge — la jota espagnole' },
        { char: 'ch (après e/i)', example: 'ich', sound: 'un h chuchoté contre le palais — soufflez un « y » sans la voix' },
        { char: 'r', example: 'rot', sound: 'proche du r français ; presque une voyelle en fin de mot (-er = « a » relâché)' },
        { char: 'final b/d/g', example: 'Tag', sound: 'en fin de mot, b/d/g se durcissent en p/t/k' },
      ],
    },
  ],
}

const italianFr: LanguageLetters = {
  intro:
    'Sept sons de voyelles, des consonnes doubles bien nettes, et deux lettres (c, g) qui s’adoucissent devant e et i.',
  sections: [
    {
      title: 'Voyelles',
      rows: [
        { char: 'a / à', example: 'casa', sound: 'comme le a de « papa »' },
        { char: 'e / è', example: 'bene', sound: 'comme le è de « mère » (é plus fermé, comme dans « été »)' },
        { char: 'i / ì', example: 'vino', sound: 'comme le i de « vie »' },
        { char: 'o / ò', example: 'otto', sound: 'comme le o de « fort »' },
        { char: 'u / ù', example: 'uno', sound: 'comme ou dans « fou »' },
      ],
    },
    {
      title: 'Le système c/g',
      rows: [
        { char: 'c (+a,o,u)', example: 'casa', sound: 'k' },
        { char: 'c (+e,i)', example: 'cena', sound: 'tch, comme dans « tchèque »' },
        { char: 'ch', example: 'chiave', sound: 'k — le h le redurcit' },
        { char: 'g (+a,o,u)', example: 'gatto', sound: 'comme le g de « gare »' },
        { char: 'g (+e,i)', example: 'gelato', sound: 'dj, comme dans « Djibouti »' },
        { char: 'gh', example: 'spaghetti', sound: 'g dur — redurci par le h' },
        { char: 'gn', example: 'gnocchi', sound: 'comme le gn de « montagne »' },
        { char: 'gli', example: 'famiglia', sound: 'un l mouillé — dites « li » en collant toute la langue au palais' },
        { char: 'sc (+e,i)', example: 'pesce', sound: 'comme ch dans « chat »' },
      ],
    },
    {
      title: 'Habitudes',
      rows: [
        { char: 'double consonants', example: 'pizza', sound: 'les doubles se tiennent deux fois plus longtemps — pit-tsa, pas pi-tsa' },
        { char: 'z', example: 'zio', sound: '« ts » ou « dz »' },
        { char: 'r', example: 'Roma', sound: 'roulé, comme en espagnol' },
        { char: 'h', example: 'hotel', sound: 'muet' },
      ],
    },
  ],
}

const catalanFr: LanguageLetters = {
  intro:
    'Les voyelles catalanes se réduisent hors accent (une signature du catalan), et quelques graphies n’appartiennent qu’à lui.',
  sections: [
    {
      title: 'Voyelles',
      rows: [
        { char: 'a / à', example: 'casa', sound: 'a franc sous l’accent ; e muet (schwa) ailleurs' },
        { char: 'e / é / è', example: 'més', sound: 'é ou è sous l’accent ; e muet ailleurs' },
        { char: 'i / í', example: 'nit', sound: 'comme le i de « vie »' },
        { char: 'o / ó / ò', example: 'porta', sound: 'o sous l’accent ; « ou » ailleurs' },
        { char: 'u / ú', example: 'butxaca', sound: 'comme ou dans « fou »' },
      ],
    },
    {
      title: 'Les spécialités catalanes',
      rows: [
        { char: 'ny', example: 'Catalunya', sound: 'comme le gn de « montagne »' },
        { char: 'l·l', example: 'il·lusió', sound: 'le point volant : un l long' },
        { char: 'x', example: 'xocolata', sound: 'comme ch dans « chat »' },
        { char: 'tx', example: 'cotxe', sound: 'tch, comme dans « tchèque »' },
        { char: 'ç', example: 'plaça', sound: 's' },
        { char: 'j / g(+e,i)', example: 'jugar', sound: 'comme le j français de « jour »' },
        { char: 'r final', example: 'cantar', sound: 'généralement muet' },
        { char: 'ig final', example: 'puig', sound: 'tch, comme dans « tchèque »' },
      ],
    },
  ],
}

const portugueseFr: LanguageLetters = {
  intro:
    'Le portugais du Brésil : des voyelles chantantes, les fameuses nasales, et quelques consonnes qui surprennent même les hispanophones.',
  sections: [
    {
      title: 'Voyelles et accents',
      rows: [
        { char: 'a / á', example: 'casa', sound: 'comme le a de « papa »' },
        { char: 'â', example: 'câmera', sound: 'un a sombre et fermé, qui tire vers le e muet' },
        { char: 'e / é', example: 'ela', sound: 'comme le è de « mère »' },
        { char: 'ê', example: 'você', sound: 'é fermé, comme dans « été », sans glissement' },
        { char: 'e final', example: 'nome', sound: 'se réduit en « i » au Brésil' },
        { char: 'o / ó', example: 'avó', sound: 'o ouvert, comme dans « fort »' },
        { char: 'ô', example: 'avô', sound: 'o fermé, comme dans « eau » — avó/avô ne diffèrent que là !' },
        { char: 'o final', example: 'gato', sound: 'se réduit en « ou »' },
        { char: 'u', example: 'tudo', sound: 'comme ou dans « fou »' },
      ],
    },
    {
      title: 'La famille nasale',
      note: 'Le tilde (~) ou un m/n qui suit envoie la voyelle par le nez.',
      rows: [
        { char: 'ã', example: 'maçã', sound: 'a nasal, proche du an de « maman »' },
        { char: 'ão', example: 'pão', sound: 'un « aou » nasal — le son le plus portugais qui soit' },
        { char: 'õe', example: 'ações', sound: 'un « oï » nasal' },
        { char: 'em / en', example: 'bem', sound: 'un « eïn » nasal, glissé' },
        { char: 'im / in', example: 'sim', sound: 'un i nasal' },
      ],
    },
    {
      title: 'Les surprises consonantiques',
      rows: [
        { char: 'ç', example: 'coração', sound: 's' },
        { char: 'ch', example: 'chuva', sound: 'comme ch dans « chat »' },
        { char: 'lh', example: 'filho', sound: 'un l mouillé — « li » collé au palais, comme le gli italien' },
        { char: 'nh', example: 'ninho', sound: 'comme le gn de « montagne »' },
        { char: 'j / g(+e,i)', example: 'hoje', sound: 'comme le j français de « jour »' },
        { char: 'r- / rr', example: 'rio', sound: 'un h soufflé au Brésil' },
        { char: 'ti / di', example: 'dia', sound: '« tchi » / « dji » dans la plus grande partie du Brésil' },
        { char: 'l final', example: 'Brasil', sound: 'devient un « ou » glissé (w) — Brasiw' },
      ],
    },
  ],
}

const romanianFr: LanguageLetters = {
  intro:
    'Le roumain se lit presque comme l’italien, avec cinq lettres en plus — et toutes les cinq sont régulières.',
  sections: [
    {
      title: 'Les cinq lettres spéciales',
      rows: [
        { char: 'ă', example: 'casă', sound: 'le e muet de « le »' },
        { char: 'â / î', example: 'în', sound: 'un « i » central et profond — dites « i » en reculant la langue ; n’existe pas en français' },
        { char: 'ș', example: 'și', sound: 'comme ch dans « chat »' },
        { char: 'ț', example: 'preț', sound: 'ts, comme dans « tsar »' },
      ],
    },
    {
      title: 'Bon à savoir',
      rows: [
        { char: 'c (+e,i)', example: 'ce', sound: 'tch, comme dans « tchèque »' },
        { char: 'che / chi', example: 'chelner', sound: 'k' },
        { char: 'g (+e,i)', example: 'ger', sound: 'dj, comme dans « Djibouti »' },
        { char: 'ghe / ghi', example: 'ghid', sound: 'comme le g de « gare »' },
        { char: 'j', example: 'jos', sound: 'comme le j français de « jour »' },
        { char: 'r', example: 'repede', sound: 'roulé, comme en espagnol' },
        { char: '-i final', example: 'lupi', sound: 'chuchoté — à peine un y' },
      ],
    },
  ],
}

/* Reused verbatim from lettersL10n.ts (turkishFr). */
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

const swahiliFr: LanguageLetters = {
  intro:
    'Le swahili est merveilleusement phonétique : cinq voyelles pures, accent toujours sur l’avant-dernière syllabe.',
  sections: [
    {
      title: 'Voyelles',
      rows: [
        { char: 'a', example: 'baba', sound: 'comme le a de « papa »' },
        { char: 'e', example: 'wewe', sound: 'comme le è de « mère »' },
        { char: 'i', example: 'sisi', sound: 'comme le i de « vie »' },
        { char: 'o', example: 'moto', sound: 'comme le o de « fort »' },
        { char: 'u', example: 'kuku', sound: 'comme ou dans « fou »' },
      ],
    },
    {
      title: 'Équipes de lettres',
      rows: [
        { char: 'ny', example: 'nyumba', sound: 'comme le gn de « montagne »' },
        { char: 'ng\'', example: 'ng\'ombe', sound: 'le ng de « parking », sans g — en DÉBUT de syllabe' },
        { char: 'ng (sans apostrophe)', example: 'ngoma', sound: '« ng » + g, comme dans « bingo »' },
        { char: 'dh', example: 'dhahabu', sound: 'le th anglais de this — langue entre les dents, avec la voix (emprunts arabes)' },
        { char: 'th', example: 'thelathini', sound: 'le th anglais de think — langue entre les dents, sans la voix' },
        { char: 'gh', example: 'ghali', sound: 'un g gargarisé, proche du r français (emprunts arabes)' },
        { char: 'ch', example: 'chai', sound: 'tch, comme dans « tchèque »' },
        { char: 'mb / nd / nj', example: 'mbwa', sound: 'fredonnez le m/n DANS la consonne suivante — un seul temps' },
      ],
    },
  ],
}

const yorubaFr: LanguageLetters = {
  intro:
    'Le yoruba est une langue à tons — les accents notent la hauteur, pas l’accent tonique. Deux lettres à point souscrit marquent les voyelles ouvertes.',
  sections: [
    {
      title: 'Voyelles (7) + les points',
      rows: [
        { char: 'a', example: 'ata', sound: 'comme le a de « papa »' },
        { char: 'e', example: 'ewé', sound: 'é fermé, comme dans « été »' },
        { char: 'ẹ (avec point)', example: 'ẹja', sound: 'è ouvert, comme dans « mère »' },
        { char: 'i', example: 'ilé', sound: 'comme le i de « vie »' },
        { char: 'o', example: 'owó', sound: 'o fermé, comme dans « eau »' },
        { char: 'ọ (avec point)', example: 'ọmọ', sound: 'o ouvert, comme dans « fort »' },
        { char: 'u', example: 'imu', sound: 'comme ou dans « fou »' },
      ],
    },
    {
      title: 'Les tons — les trois hauteurs',
      note: 'Mêmes lettres, autre hauteur, autre mot. Les accents sont la mélodie.',
      rows: [
        { char: 'á (haut)', example: 'wá', sound: 'la voix saute vers le haut' },
        { char: 'a (moyen)', example: 'wa', sound: 'hauteur ordinaire, stable' },
        { char: 'à (bas)', example: 'wà', sound: 'la voix descend' },
      ],
    },
    {
      title: 'Consonnes',
      rows: [
        { char: 'ṣ (avec point)', example: 'ṣe', sound: 'comme ch dans « chat »' },
        { char: 'gb', example: 'gbogbo', sound: 'g et b exactement au même instant — n’existe pas en français' },
        { char: 'p', example: 'pápá', sound: 'en réalité « kp », relâchés ensemble' },
        { char: 'j', example: 'jẹun', sound: 'dj, comme dans « Djibouti »' },
      ],
    },
  ],
}

const hausaFr: LanguageLetters = {
  intro:
    'Le hausa en boko utilise trois lettres « à crochet » pour des sons que le français n’a pas — ils claquent au lieu de couler.',
  sections: [
    {
      title: 'Voyelles',
      note: 'Cinq voyelles, longues ou brèves — la longueur change le sens.',
      rows: [
        { char: 'a', example: 'ruwa', sound: 'comme le a de « papa » (long : tenez-le)' },
        { char: 'e', example: 'gemu', sound: 'é fermé, comme dans « été »' },
        { char: 'i', example: 'kifi', sound: 'comme le i de « vie »' },
        { char: 'o', example: 'doki', sound: 'comme le o de « mot »' },
        { char: 'u', example: 'kudi', sound: 'comme ou dans « fou »' },
      ],
    },
    {
      title: 'Les lettres à crochet',
      rows: [
        { char: 'ɓ', example: 'ɓera', sound: 'un b implosif — l’air claque vers l’intérieur' },
        { char: 'ɗ', example: 'ɗaki', sound: 'un d implosif' },
        { char: 'ƙ', example: 'ƙofa', sound: 'un k avec un craquement de glotte' },
        { char: '\'y', example: '\'ya\'ya', sound: 'un y craquant, serré dans la gorge' },
      ],
    },
    {
      title: 'Autres habitudes',
      rows: [
        { char: 'ts', example: 'tsuntsu', sound: '« ts » avec un craquement' },
        { char: 'sh', example: 'shekara', sound: 'comme ch dans « chat »' },
        { char: 'c', example: 'ci', sound: 'tch, comme dans « tchèque »' },
        { char: 'r', example: 'rana', sound: 'roulé ou battu' },
      ],
    },
  ],
}

const xhosaFr: LanguageLetters = {
  intro:
    'L’isiXhosa est célèbre pour ses consonnes à clic — trois clics de base, écrits c, x, q. Tout le reste est proche de sons familiers.',
  sections: [
    {
      title: 'Les trois clics',
      rows: [
        { char: 'c', example: 'cela', sound: 'clic dental — le « tst tst » de la désapprobation, langue derrière les dents' },
        { char: 'x', example: 'ixesha', sound: 'clic latéral — le claquement qui fait avancer un cheval, sur le côté de la bouche' },
        { char: 'q', example: 'iqanda', sound: 'clic palatal — un « pop » de bouchon contre le palais' },
        { char: 'gc / gx / gq', example: 'gqiba', sound: 'les mêmes clics, avec la voix (fredonnez à travers)' },
        { char: 'nc / nx / nq', example: 'inqola', sound: 'les mêmes clics avec un bourdonnement nasal' },
      ],
    },
    {
      title: 'Voyelles',
      rows: [
        { char: 'a', example: 'abantu', sound: 'comme le a de « papa »' },
        { char: 'e', example: 'ewe', sound: 'comme le è de « mère »' },
        { char: 'i', example: 'siza', sound: 'comme le i de « vie »' },
        { char: 'o', example: 'onke', sound: 'comme le o de « fort »' },
        { char: 'u', example: 'ubuntu', sound: 'comme ou dans « fou »' },
      ],
    },
    {
      title: 'Autres équipes de lettres',
      rows: [
        { char: 'hl', example: 'hlala', sound: 'le ll gallois — soufflez l’air sur les côtés de la langue' },
        { char: 'dl', example: 'indlela', sound: 'la version voisée de hl' },
        { char: 'tsh', example: 'utshaba', sound: 'tch, comme dans « tchèque »' },
        { char: 'kh / th / ph', example: 'ukutya', sound: 'k/t/p suivis d’un souffle net' },
      ],
    },
  ],
}

const maoriFr: LanguageLetters = {
  intro:
    'Le te reo māori : cinq voyelles (brèves et longues), huit consonnes, deux digrammes. Chaque syllabe finit par une voyelle.',
  sections: [
    {
      title: 'Voyelles — brèves et longues',
      note: 'Le macron (ā ē ī ō ū) double la longueur, et la longueur change le sens.',
      rows: [
        { char: 'a / ā', example: 'aroha', sound: 'comme le a de « papa » (ā tenu plus longtemps)' },
        { char: 'e / ē', example: 'kete', sound: 'comme le è de « mère »' },
        { char: 'i / ī', example: 'kiwi', sound: 'comme le i de « vie »' },
        { char: 'o / ō', example: 'moana', sound: 'comme le o de « fort »' },
        { char: 'u / ū', example: 'utu', sound: 'comme ou dans « fou »' },
      ],
    },
    {
      title: 'Les deux digrammes',
      rows: [
        { char: 'wh', example: 'whānau', sound: 'comme le f de « feu »' },
        { char: 'ng', example: 'ngā', sound: 'le ng de « parking », sans g — même en début de mot' },
      ],
    },
    {
      title: 'Consonnes',
      rows: [
        { char: 'r', example: 'reo', sound: 'une battue douce, entre r et l' },
        { char: 't', example: 'te', sound: 't doux, à peine soufflé' },
        { char: 'k, m, n, p, h, w', example: 'kapa haka', sound: 'comme en français — mais le h se prononce vraiment, soufflé' },
      ],
    },
  ],
}

const jamaicanFr: LanguageLetters = {
  intro:
    'Le patois en orthographe Cassidy/JLU : un son par lettre, aucune lettre muette. Si vous savez le dire, vous savez l’écrire.',
  sections: [
    {
      title: 'Voyelles',
      rows: [
        { char: 'a', example: 'bak', sound: 'comme le a de « papa »' },
        { char: 'aa', example: 'baal', sound: 'a long, tenu' },
        { char: 'e', example: 'bel', sound: 'comme le è de « mère »' },
        { char: 'i', example: 'sik', sound: 'un i bref et relâché, entre i et é — le i anglais de bit' },
        { char: 'ii', example: 'siik', sound: 'comme le i de « vie », long' },
        { char: 'o', example: 'pat', sound: 'un o très ouvert qui tire vers le a — le o anglais de pot' },
        { char: 'u', example: 'buk', sound: 'un « ou » bref et relâché — l’anglais put' },
        { char: 'uu', example: 'skuul', sound: 'comme ou dans « fou », long' },
        { char: 'ie', example: 'kiek', sound: 'un glissé « yé-è » — cake à la jamaïcaine' },
        { char: 'uo', example: 'guo', sound: 'un glissé « ou-oa » — go à la jamaïcaine' },
        { char: 'ai', example: 'taim', sound: 'comme « aï » dans « aïe ! »' },
        { char: 'ou', example: 'bout', sound: 'comme « aou » dans « caoutchouc », en une syllabe' },
      ],
    },
    {
      title: 'Habitudes consonantiques',
      rows: [
        { char: 'k / g (+ya)', example: 'kyaan', sound: 'un glissé ky/gy — « kyan » pour can’t' },
        { char: 'no th', example: 'tink / dis', sound: 'le th anglais devient un simple t ou d' },
        { char: 'no h-drop rule', example: 'ouse / haks', sound: 'le h va et vient librement — les deux se disent' },
        { char: 'final clusters trim', example: 'las (last)', sound: 'la dernière consonne d’un groupe final tombe' },
      ],
    },
  ],
}

const englishFr: LanguageLetters = {
  intro:
    'L’orthographe anglaise est de l’histoire, pas de la phonétique. Voici les sons contre lesquels les apprenants se battent — avec les graphies fiables quand elles existent.',
  sections: [
    {
      title: 'Les célèbres',
      rows: [
        { char: 'th (sourd)', example: 'think', sound: 'langue entre les dents, soufflez — sans la voix ; n’existe pas en français' },
        { char: 'th (sonore)', example: 'this', sound: 'même position, ajoutez la voix' },
        { char: 'w vs v', example: 'very wet', sound: 'w = lèvres arrondies comme pour « oui », sans les dents ; v = dents sur la lèvre' },
        { char: 'r', example: 'red', sound: 'ni roulé ni raclé — recourbez la langue sans toucher nulle part ; rien à voir avec le r français' },
        { char: 'h', example: 'house', sound: 'un vrai souffle — jamais muet (sauf hour, honest), au contraire du h français' },
      ],
    },
    {
      title: 'Les voyelles qui piègent',
      rows: [
        { char: 'i (bref)', example: 'ship', sound: 'un i relâché, entre i et é — PAS le i de sheep' },
        { char: 'ee', example: 'sheep', sound: 'un i long et tendu — le i de « vie », tenu' },
        { char: 'a (bref)', example: 'cat', sound: 'mâchoire ouverte, entre le a de « patte » et le è de « mère »' },
        { char: 'u (bref)', example: 'cup', sound: 'un « a » sombre et bref, vers le e muet' },
        { char: 'er / unstressed', example: 'teacher', sound: 'le schwa — proche du e muet de « le » ; la voyelle la plus paresseuse, la plupart des syllabes atones l’utilisent' },
      ],
    },
    {
      title: 'Les graphies auxquelles on peut se fier',
      rows: [
        { char: 'magic e', example: 'hat → hate', sound: 'le e final muet fait dire à la voyelle son nom d’alphabet' },
        { char: '-tion', example: 'station', sound: 'se prononce « cheun » (ch + e muet + n)' },
        { char: 'ough', example: 'though / tough', sound: 'désolé — six sons différents ; apprenez chaque mot' },
      ],
    },
  ],
}

const dutchFr: LanguageLetters = {
  intro:
    'L’orthographe néerlandaise est accueillante — quelques équipes de lettres et une voyelle célèbre (ui) font tous les dégâts.',
  sections: [
    {
      title: 'Les équipes de voyelles',
      rows: [
        { char: 'aa / a', example: 'water', sound: 'a long de « pâte » / a bref et sombre — le doublement marque la longueur' },
        { char: 'ee / e', example: 'been', sound: 'é long fermé / è bref ; le -e final est un e muet' },
        { char: 'oo / o', example: 'boom', sound: 'o long fermé, comme dans « eau » / o bref ouvert' },
        { char: 'uu / u', example: 'muur', sound: 'le u français de « lune » / un « u » bref et relâché' },
        { char: 'ie', example: 'niet', sound: 'comme le i de « vie »' },
        { char: 'oe', example: 'boek', sound: 'comme ou dans « fou »' },
        { char: 'eu', example: 'leuk', sound: 'comme eu dans « peu »' },
        { char: 'ij / ei', example: 'ijs', sound: 'un « èï » glissé — la fameuse diphtongue néerlandaise, deux graphies' },
        { char: 'ui', example: 'huis', sound: 'n’existe pas en français : dites « aou » avec les lèvres serrées et arrondies' },
        { char: 'ou / au', example: 'oud', sound: 'comme « aou » dans « caoutchouc », en une syllabe' },
      ],
    },
    {
      title: 'Habitudes consonantiques',
      rows: [
        { char: 'g / ch', example: 'goed', sound: 'le raclement néerlandais — la jota espagnole, un r français durci et sans voix (plus doux dans le sud)' },
        { char: 'sch', example: 'school', sound: 's + le raclement : s-chool' },
        { char: 'w', example: 'water', sound: 'entre le w de « oui » et le v' },
        { char: 'v', example: 'vader', sound: 'entre v et f' },
        { char: 'j', example: 'ja', sound: 'comme le y de « yoga »' },
        { char: 'r', example: 'rood', sound: 'roulé ou raclé — les deux se disent' },
        { char: '-en (terminaison)', example: 'lopen', sound: 'le n final tombe souvent : « lope(n) »' },
        { char: '-tje', example: 'kopje', sound: 'la machine à diminutifs — koppje, huisje, momentje' },
      ],
    },
  ],
}

const russianFr: LanguageLetters = {
  intro:
    'L’alphabet cyrillique — 33 lettres. La plupart n’ont qu’un seul son stable ; les cinq paires de voyelles « dures/molles » sont le système à apprendre.',
  sections: [
    {
      title: 'Voyelles — la série dure',
      note: 'Elles laissent la consonne précédente telle quelle.',
      rows: [
        { char: 'а', roman: 'a', example: 'мама', sound: 'comme le a de « papa »' },
        { char: 'э', roman: 'e', example: 'это', sound: 'comme le è de « mère »' },
        { char: 'ы', roman: 'y', example: 'мы', sound: 'un i profond — dites « i » en reculant la langue ; n’existe pas en français' },
        { char: 'о', roman: 'o', example: 'дом', sound: 'comme le o de « fort » (seulement sous l’accent)' },
        { char: 'у', roman: 'u', example: 'утро', sound: 'comme ou dans « fou »' },
      ],
    },
    {
      title: 'Voyelles — la série molle',
      note: 'Mêmes sons de voyelles, mais elles mouillent la consonne précédente (un petit y caché).',
      rows: [
        { char: 'я', roman: 'ya', example: 'яблоко', sound: '« ya », comme dans « yaourt »' },
        { char: 'е', roman: 'e/ye', example: 'нет', sound: '« yé », comme dans « payé »' },
        { char: 'и', roman: 'i', example: 'мир', sound: 'comme le i de « vie »' },
        { char: 'ё', roman: 'yo', example: 'ёлка', sound: '« yo », comme dans « yoga » (toujours accentuée)' },
        { char: 'ю', roman: 'yu', example: 'юг', sound: '« you », comme dans « caillou »' },
      ],
    },
    {
      title: 'Des consonnes à l’air familier (mais non)',
      rows: [
        { char: 'в', roman: 'v', example: 'вода', sound: 'comme le v de « vache » (pas b)' },
        { char: 'н', roman: 'n', example: 'нос', sound: 'comme le n de « non » (pas h)' },
        { char: 'р', roman: 'r', example: 'рука', sound: 'r roulé, comme en espagnol' },
        { char: 'с', roman: 's', example: 'сок', sound: 'comme le s de « soleil » (pas k)' },
        { char: 'у', roman: 'u', example: 'ум', sound: '« ou » — elle ressemble à un y, mais jamais « i grec »' },
        { char: 'х', roman: 'h/x', example: 'хлеб', sound: 'un h raclé — la jota espagnole' },
      ],
    },
    {
      title: 'Le reste des consonnes',
      rows: [
        { char: 'б', roman: 'b', example: 'брат', sound: 'comme le b de « bon »' },
        { char: 'г', roman: 'g', example: 'год', sound: 'comme le g de « gare »' },
        { char: 'д', roman: 'd', example: 'да', sound: 'comme le d de « deux »' },
        { char: 'ж', roman: 'zh', example: 'жить', sound: 'comme le j de « jour »' },
        { char: 'з', roman: 'z', example: 'зима', sound: 'comme le z de « zoo »' },
        { char: 'й', roman: 'j', example: 'мой', sound: 'le y glissé de « travail »' },
        { char: 'к', roman: 'k', example: 'кот', sound: 'comme le k de « kilo »' },
        { char: 'л', roman: 'l', example: 'лампа', sound: 'comme le l de « lune »' },
        { char: 'м', roman: 'm', example: 'мост', sound: 'comme le m de « main »' },
        { char: 'п', roman: 'p', example: 'папа', sound: 'comme le p de « papa »' },
        { char: 'т', roman: 't', example: 'там', sound: 'comme le t de « table »' },
        { char: 'ф', roman: 'f', example: 'фото', sound: 'comme le f de « feu »' },
        { char: 'ц', roman: 'c/ts', example: 'цирк', sound: 'ts, comme dans « tsar »' },
        { char: 'ч', roman: 'ch', example: 'чай', sound: 'tch, comme dans « tchèque »' },
        { char: 'ш', roman: 'sh', example: 'школа', sound: 'un ch dur, comme dans « chat »' },
        { char: 'щ', roman: 'shch', example: 'щи', sound: 'un « ch » long et mouillé — chch, langue vers le palais' },
      ],
    },
    {
      title: 'Les deux signes muets',
      rows: [
        { char: 'ь', roman: '\'', example: 'день', sound: 'signe mou — mouille la consonne précédente (ajoute une pointe de y)' },
        { char: 'ъ', roman: '\'\'', example: 'объект', sound: 'signe dur — une minuscule pause entre préfixe et racine' },
      ],
    },
    {
      title: 'Imprimé vs italique (et écriture manuscrite)',
      note: 'Le cyrillique tapé a deux visages. En italique — et plus encore en manuscrit — plusieurs lettres prennent des formes qui ressemblent à d’AUTRES lettres latines. Même lettre, même son : comparez chaque paire droite/italique.',
      italics: true,
      rows: [
        { char: 'т', roman: 't', example: 'там', sound: 'le т italique devient une forme de m — toujours « t »' },
        { char: 'и', roman: 'i', example: 'мир', sound: 'le и italique devient une forme de u — toujours « i »' },
        { char: 'й', roman: 'j', example: 'мой', sound: 'le й italique est cette forme de u, avec la petite courbe au-dessus' },
        { char: 'п', roman: 'p', example: 'папа', sound: 'le п italique devient une forme de n — toujours « p »' },
        { char: 'д', roman: 'd', example: 'да', sound: 'le д italique devient une forme de g — toujours « d »' },
        { char: 'г', roman: 'g', example: 'год', sound: 'le г italique devient un s à l’envers — toujours « g »' },
      ],
    },
  ],
}

const greekFr: LanguageLetters = {
  intro:
    'L’alphabet grec — 24 lettres. Plusieurs de nos lettres latines en viennent, la moitié du travail est donc déjà faite.',
  sections: [
    {
      title: 'Voyelles',
      note: 'Le grec moderne n’a que cinq sons de voyelles ; plusieurs graphies se les partagent.',
      rows: [
        { char: 'α', roman: 'a', example: 'αγάπη', sound: 'comme le a de « papa »' },
        { char: 'ε', roman: 'e', example: 'ένα', sound: 'comme le è de « mère »' },
        { char: 'η', roman: 'h/i', example: 'ημέρα', sound: 'comme le i de « vie »' },
        { char: 'ι', roman: 'i', example: 'ιδέα', sound: 'comme le i de « vie »' },
        { char: 'ο', roman: 'o', example: 'όχι', sound: 'comme le o de « fort »' },
        { char: 'υ', roman: 'u/y', example: 'ύπνος', sound: '« i » — oui, encore un i' },
        { char: 'ω', roman: 'w', example: 'ώρα', sound: '« o » — le même que ο' },
      ],
    },
    {
      title: 'Consonnes',
      rows: [
        { char: 'β', roman: 'v/b', example: 'βιβλίο', sound: 'comme le v de « vache » (pas b !)' },
        { char: 'γ', roman: 'g', example: 'γάλα', sound: 'un g doux et gargarisé ; devant e/i, comme le y de « yoga »' },
        { char: 'δ', roman: 'd', example: 'δέκα', sound: 'le th anglais de this — langue entre les dents, avec la voix (pas d !)' },
        { char: 'ζ', roman: 'z', example: 'ζωή', sound: 'comme le z de « zoo »' },
        { char: 'θ', roman: 'th', example: 'θάλασσα', sound: 'le th anglais de think — langue entre les dents, sans la voix' },
        { char: 'κ', roman: 'k', example: 'καλά', sound: 'comme le k de « kilo »' },
        { char: 'λ', roman: 'l', example: 'λέξη', sound: 'comme le l de « lune »' },
        { char: 'μ', roman: 'm', example: 'μητέρα', sound: 'comme le m de « main »' },
        { char: 'ν', roman: 'n', example: 'νερό', sound: 'comme le n de « non » (elle ressemble à v !)' },
        { char: 'ξ', roman: 'x', example: 'ξένος', sound: '« ks », comme le x de « taxi »' },
        { char: 'π', roman: 'p', example: 'πατέρας', sound: 'comme le p de « papa »' },
        { char: 'ρ', roman: 'r', example: 'ρολόι', sound: 'r légèrement roulé (elle ressemble à p !)' },
        { char: 'σ/ς', roman: 's', example: 'σπίτι', sound: 'comme le s de « soleil » ; ς seulement en fin de mot' },
        { char: 'τ', roman: 't', example: 'τρία', sound: 'comme le t de « table »' },
        { char: 'φ', roman: 'f', example: 'φίλος', sound: 'comme le f de « feu »' },
        { char: 'χ', roman: 'ch', example: 'χέρι', sound: 'un h raclé — la jota espagnole' },
        { char: 'ψ', roman: 'ps', example: 'ψωμί', sound: '« ps », comme dans « psychologie » — même en début de mot' },
      ],
    },
    {
      title: 'Paires courantes',
      note: 'Deux lettres, un seul son — apprenez-les comme des unités.',
      rows: [
        { char: 'ου', roman: 'ou', example: 'ουρανός', sound: 'comme ou dans « fou »' },
        { char: 'αι', roman: 'ai', example: 'παιδί', sound: 'comme le è de « mère »' },
        { char: 'ει/οι', roman: 'ei/oi', example: 'είναι', sound: 'comme le i de « vie »' },
        { char: 'μπ', roman: 'mp', example: 'μπανάνα', sound: '« b » en début de mot ; « mb » à l’intérieur' },
        { char: 'ντ', roman: 'nt', example: 'ντομάτα', sound: '« d » en début de mot ; « nd » à l’intérieur' },
        { char: 'γγ/γκ', roman: 'gg/gk', example: 'αγγλικά', sound: '« g » / « ng-g »' },
      ],
    },
  ],
}

const arabicFr: LanguageLetters = {
  intro:
    'L’abjad arabe — 28 lettres, écrites de droite à gauche. Les lettres se lient et changent de forme selon leur position ; les voyelles brèves ne s’écrivent généralement pas.',
  sections: [
    {
      title: 'Comment les lettres s’assemblent',
      note: 'L’arabe est cursif par règle : la plupart des lettres ont quatre formes — isolée, initiale, médiane, finale — et se lient à leurs voisines.',
      rows: [
        { char: 'م ح م د → محمد', roman: 'm-H-m-d', example: 'محمد', sound: 'les mêmes lettres, liées : chacune change de forme selon sa position' },
        { char: 'ب ـبـ ـب', roman: 'b', example: 'باب', sound: 'une lettre, trois formes liées : initiale, médiane, finale' },
        { char: 'ا د ر ز و', roman: '(non-joiners)', example: 'دار', sound: 'six lettres ne se lient jamais VERS L’AVANT — elles imposent une coupure au milieu du mot' },
        { char: 'ل + ا → لا', roman: 'laa', example: 'سلام', sound: 'lam + alif fusionnent dans la ligature spéciale lam-alif' },
      ],
    },
    {
      title: 'Voyelles longues et semi-voyelles',
      positions: true,
      rows: [
        { char: 'ا', roman: 'aa', example: 'باب', sound: 'un a long — le a de « papa », tenu' },
        { char: 'و', roman: 'w/uu', example: 'نور', sound: 'le « ou » de « oui », ou un ou long comme dans « fou »' },
        { char: 'ي', roman: 'y/ii', example: 'كبير', sound: 'le y de « yoga », ou un i long comme dans « vie »' },
      ],
    },
    {
      title: 'Les lettres familières',
      note: 'Chaque lettre en quatre positions : isolée, puis liée au début, au milieu et à la fin d’un mot.',
      positions: true,
      rows: [
        { char: 'ب', roman: 'b', example: 'بيت', sound: 'comme le b de « bon »' },
        { char: 'ت', roman: 't', example: 'تفاح', sound: 'comme le t de « table »' },
        { char: 'ث', roman: 'th', example: 'ثلاثة', sound: 'le th anglais de think — langue entre les dents, sans la voix' },
        { char: 'ج', roman: 'j', example: 'جمل', sound: 'dj, comme dans « Djibouti »' },
        { char: 'د', roman: 'd', example: 'دار', sound: 'comme le d de « deux »' },
        { char: 'ذ', roman: 'dh', example: 'هذا', sound: 'le th anglais de this — la version avec la voix' },
        { char: 'ر', roman: 'r', example: 'رجل', sound: 'r roulé, comme en espagnol' },
        { char: 'ز', roman: 'z', example: 'زيت', sound: 'comme le z de « zoo »' },
        { char: 'س', roman: 's', example: 'سلام', sound: 'comme le s de « soleil »' },
        { char: 'ش', roman: 'sh', example: 'شمس', sound: 'comme ch dans « chat »' },
        { char: 'ف', roman: 'f', example: 'فيل', sound: 'comme le f de « feu »' },
        { char: 'ك', roman: 'k', example: 'كتاب', sound: 'comme le k de « kilo »' },
        { char: 'ل', roman: 'l', example: 'ليل', sound: 'comme le l de « lune »' },
        { char: 'م', roman: 'm', example: 'ماء', sound: 'comme le m de « main »' },
        { char: 'ن', roman: 'n', example: 'نار', sound: 'comme le n de « non »' },
        { char: 'ه', roman: 'h', example: 'هنا', sound: 'un h vraiment soufflé, comme dans l’anglais house — pas muet' },
      ],
    },
    {
      title: 'Les sons nouveaux',
      note: 'Produits plus bas dans la gorge que tout ce que le français possède — écoutez et imitez.',
      positions: true,
      rows: [
        { char: 'ح', roman: 'H / 7', example: 'حب', sound: 'un h soufflé du fond de la gorge — comme pour embuer un miroir, en plus appuyé' },
        { char: 'خ', roman: 'kh / 5', example: 'خبز', sound: 'un raclement sourd — la jota espagnole, un r français sans la voix' },
        { char: 'ع', roman: '3', example: 'عين', sound: 'une voyelle serrée dans la gorge — aucun équivalent ; écoutez bien' },
        { char: 'غ', roman: 'gh', example: 'غرب', sound: 'un g gargarisé — tout proche du r français de « rue »' },
        { char: 'ق', roman: 'q', example: 'قلب', sound: 'un « k » reculé tout au fond de la bouche' },
        { char: 'ء', roman: '2 / \'', example: 'سؤال', sound: 'le coup de glotte — la petite cassure entre les deux « oh » de « oh-oh ! »' },
      ],
    },
    {
      title: 'Les quatre emphatiques',
      note: 'Jumelles lourdes de t/d/s/z — la langue se creuse vers l’arrière et tout le mot s’assombrit.',
      positions: true,
      rows: [
        { char: 'ص', roman: 'S', example: 'صباح', sound: '« s » lourd' },
        { char: 'ض', roman: 'D', example: 'ضوء', sound: '« d » lourd' },
        { char: 'ط', roman: 'T', example: 'طعام', sound: '« t » lourd' },
        { char: 'ظ', roman: 'Z', example: 'ظهر', sound: '« th/z » lourd' },
      ],
    },
    {
      title: 'Voyelles brèves (harakat)',
      note: 'Petits signes au-dessus ou au-dessous de la lettre — généralement omis hors des textes pédagogiques.',
      rows: [
        { char: 'ـَ', roman: 'a', example: 'فَتَحَ', sound: 'a bref, comme dans « patte » (fatha)' },
        { char: 'ـِ', roman: 'i', example: 'بِنت', sound: 'i bref, comme dans « ici » (kasra)' },
        { char: 'ـُ', roman: 'u', example: 'كُتُب', sound: '« ou » bref, comme dans « tout » (damma)' },
        { char: 'ـّ', roman: '(double)', example: 'مُدَرِّس', sound: 'chadda — tenez la consonne deux fois plus longtemps' },
      ],
    },
  ],
}

const hindiFr: LanguageLetters = {
  intro:
    'La devanagari — chaque consonne porte un « a » intégré ; les signes vocaliques (matras) le remplacent. Les sons vedettes : les rétroflexes (langue recourbée en arrière) face aux dentales (langue sur les dents), et les paires aspirées, avec un souffle en plus.',
  sections: [
    {
      title: 'Comment les lettres s’assemblent',
      note: 'La devanagari construit des syllabes : les signes vocaliques s’accrochent aux consonnes, et le virama (्) soude les consonnes en groupes.',
      rows: [
        { char: 'क + ा → का', roman: 'k + aa', example: 'काम', sound: 'un signe vocalique (matra) remplace le a intégré' },
        { char: 'क + ि → कि', roman: 'k + i', example: 'किताब', sound: 'la matra du i s’écrit À GAUCHE de sa consonne' },
        { char: 'स + ् + त → स्त', roman: 's+t', example: 'नमस्ते', sound: 'le virama supprime le a et fond la paire en un seul groupe' },
        { char: 'क + ् + ष → क्ष', roman: 'ksh', example: 'क्षमा', sound: 'certains groupes prennent une forme toute neuve — apprenez les plus courants à vue' },
        { char: 'र special', roman: 'r', example: 'कर्म / प्रेम', sound: 'le r s’écrit AU-DESSUS du groupe quand il vient en premier (कर्म), en petit trait dessous quand il vient en second (प्रेम)' },
      ],
    },
    {
      title: 'Voyelles indépendantes',
      note: 'Employées en début de mot ; à l’intérieur, elles deviennent des matras (section suivante).',
      rows: [
        { char: 'अ', roman: 'a', example: 'अब', sound: 'un a bref et relâché, qui tire vers le e muet de « le »' },
        { char: 'आ', roman: 'aa', example: 'आम', sound: 'un a long — le a de « papa », tenu' },
        { char: 'इ', roman: 'i', example: 'इधर', sound: 'un i bref et relâché — le i anglais de bit' },
        { char: 'ई', roman: 'ii', example: 'ईद', sound: 'comme le i de « vie », long' },
        { char: 'उ', roman: 'u', example: 'उधर', sound: 'un « ou » bref et relâché — l’anglais put' },
        { char: 'ऊ', roman: 'uu', example: 'ऊपर', sound: 'comme ou dans « fou », long' },
        { char: 'ए', roman: 'e', example: 'एक', sound: 'é fermé, comme dans « été » (sans glissement)' },
        { char: 'ऐ', roman: 'ai', example: 'ऐनक', sound: 'entre le a de « patte » et le è de « mère » — le a anglais de cat' },
        { char: 'ओ', roman: 'o', example: 'ओर', sound: 'o fermé, comme dans « eau » (sans glissement)' },
        { char: 'औ', roman: 'au', example: 'औरत', sound: 'o ouvert, comme dans « fort »' },
      ],
    },
    {
      title: 'Les mêmes voyelles en matras',
      note: 'क sert de support. Le अ intégré n’a pas besoin de signe.',
      rows: [
        { char: 'का', roman: 'kaa', example: 'काम', sound: 'k + a long' },
        { char: 'कि', roman: 'ki', example: 'किताब', sound: 'k + i (le signe s’écrit AVANT la lettre)' },
        { char: 'की', roman: 'kii', example: 'की', sound: 'k + i long' },
        { char: 'कु', roman: 'ku', example: 'कुछ', sound: 'k + ou bref' },
        { char: 'कू', roman: 'kuu', example: 'कूद', sound: 'k + ou long' },
        { char: 'के', roman: 'ke', example: 'के', sound: 'k + é' },
        { char: 'कै', roman: 'kai', example: 'कैसा', sound: 'k + le a anglais de cat' },
        { char: 'को', roman: 'ko', example: 'को', sound: 'k + o fermé' },
        { char: 'कौ', roman: 'kau', example: 'कौन', sound: 'k + o ouvert' },
        { char: 'कं', roman: 'kaM', example: 'कंघी', sound: 'un bourdonnement nasal après la voyelle (anusvara)' },
      ],
    },
    {
      title: 'Consonnes — les paires aspirées',
      note: 'La seconde de chaque paire ajoute un souffle (paume devant la bouche — vous devez le sentir).',
      rows: [
        { char: 'क / ख', roman: 'k / kh', example: 'खाना', sound: '« k » simple, puis « k » + souffle' },
        { char: 'ग / घ', roman: 'g / gh', example: 'घर', sound: '« g » simple, puis « g » + souffle' },
        { char: 'च / छ', roman: 'ch / chh', example: 'छह', sound: '« tch » simple, puis « tch » + souffle' },
        { char: 'ज / झ', roman: 'j / jh', example: 'झील', sound: '« dj » simple, puis « dj » + souffle' },
        { char: 'प / फ', roman: 'p / ph', example: 'फल', sound: '« p » simple, puis « p » + souffle' },
        { char: 'ब / भ', roman: 'b / bh', example: 'भाई', sound: '« b » simple, puis « b » + souffle' },
      ],
    },
    {
      title: 'Rétroflexes vs dentales — le grand partage',
      note: 'Rétroflexe : langue recourbée vers le palais. Dentale : langue sur les dents. Les t/d français sont déjà dentaux — c’est la série rétroflexe qui demande du travail.',
      rows: [
        { char: 'ट / ठ', roman: 'T / Th', example: 'टमाटर', sound: 't rétroflexe (simple / + souffle)' },
        { char: 'ड / ढ', roman: 'D / Dh', example: 'डर', sound: 'd rétroflexe (simple / + souffle)' },
        { char: 'ण', roman: 'N', example: 'बाण', sound: 'n rétroflexe' },
        { char: 'त / थ', roman: 't / th', example: 'तीन', sound: 't dental — comme le t français (simple / + souffle)' },
        { char: 'द / ध', roman: 'd / dh', example: 'दो', sound: 'd dental (simple / + souffle)' },
        { char: 'न', roman: 'n', example: 'नाम', sound: 'comme le n de « non »' },
        { char: 'ड़ / ढ़', roman: 'R / Rh', example: 'लड़का', sound: 'r battu — la langue claque en redescendant de la position rétroflexe' },
      ],
    },
    {
      title: 'Le reste',
      rows: [
        { char: 'म', roman: 'm', example: 'माँ', sound: 'comme le m de « main »' },
        { char: 'य', roman: 'y', example: 'यह', sound: 'comme le y de « yoga »' },
        { char: 'र', roman: 'r', example: 'रात', sound: 'un r battu léger' },
        { char: 'ल', roman: 'l', example: 'लाल', sound: 'comme le l de « lune »' },
        { char: 'व', roman: 'v/w', example: 'वह', sound: 'entre le v et le « ou » de « oui »' },
        { char: 'श / ष', roman: 'sh / Sh', example: 'शहर', sound: 'comme ch dans « chat »' },
        { char: 'स', roman: 's', example: 'सात', sound: 'comme le s de « soleil »' },
        { char: 'ह', roman: 'h', example: 'हाँ', sound: 'un h vraiment soufflé, comme dans l’anglais house' },
      ],
    },
    {
      title: 'Lettres à nuqta (sons d’emprunt)',
      note: 'Un point sous la lettre marque les sons perso-arabes.',
      rows: [
        { char: 'ज़', roman: 'z', example: 'ज़रूर', sound: 'comme le z de « zoo »' },
        { char: 'फ़', roman: 'f', example: 'फ़ोन', sound: 'comme le f de « feu »' },
        { char: 'क़', roman: 'q', example: 'क़लम', sound: 'un « k » reculé au fond de la bouche' },
        { char: 'ख़ / ग़', roman: 'kh / gh', example: 'ख़बर', sound: 'raclement type jota / g gargarisé proche du r français' },
      ],
    },
  ],
}

const thaiFr: LanguageLetters = {
  intro:
    'L’écriture thaïe : 44 consonnes réparties en trois CLASSES (la classe + le signe de ton décident du ton), des voyelles qui s’accrochent autour de la consonne, et pas d’espaces entre les mots.',
  sections: [
    {
      title: 'Comment les lettres s’assemblent',
      note: 'Les voyelles enveloppent leur consonne — avant, après, dessus ou dessous — et les signes de ton s’empilent au sommet.',
      rows: [
        { char: 'ก + า → กา', roman: 'k + aa', example: 'กาแฟ', sound: 'cette voyelle suit la consonne' },
        { char: 'ก + ิ → กิ', roman: 'k + i', example: 'กิน', sound: 'cette voyelle se pose AU-DESSUS' },
        { char: 'ก + ุ → กุ', roman: 'k + u', example: 'กุ้ง', sound: 'cette voyelle pend EN DESSOUS' },
        { char: 'เ + ก → เก', roman: 'k + e', example: 'เกาะ', sound: 'cette voyelle s’écrit AVANT la consonne après laquelle on la prononce' },
        { char: 'เ-ีย, เ-ือ', roman: 'ia, uea', example: 'เมีย', sound: 'les voyelles composées entourent la consonne sur deux ou trois côtés' },
        { char: 'ก่ ก้ ก๊ ก๋', roman: 'tones', example: 'ไม่', sound: 'quatre signes de ton s’empilent au-dessus ; la classe de la consonne décide de leur valeur' },
      ],
    },
    {
      title: 'Consonnes de tous les jours (classe moyenne)',
      rows: [
        { char: 'ก', roman: 'g/k', example: 'ไก่', sound: 'comme le g de « gare » (un k sans souffle)' },
        { char: 'จ', roman: 'j', example: 'จาน', sound: 'dj, comme dans « Djibouti » (plus sec)' },
        { char: 'ด', roman: 'd', example: 'เด็ก', sound: 'comme le d de « deux »' },
        { char: 'ต', roman: 'dt', example: 'ตา', sound: 'entre d et t — un t sans souffle' },
        { char: 'บ', roman: 'b', example: 'บ้าน', sound: 'comme le b de « bon »' },
        { char: 'ป', roman: 'bp', example: 'ปลา', sound: 'entre b et p — un p sans souffle' },
        { char: 'อ', roman: '(silent)', example: 'อาหาร', sound: 'la consonne muette qui porte les voyelles isolées' },
      ],
    },
    {
      title: 'Consonnes soufflées (paires haute + basse)',
      note: 'Même son, autre classe — la classe change le TON de la syllabe.',
      rows: [
        { char: 'ข / ค', roman: 'kh', example: 'ขาว / ควาย', sound: '« k » + souffle (classe haute / classe basse)' },
        { char: 'ถ / ท', roman: 'th', example: 'ถนน / ทำ', sound: '« t » + souffle (haute / basse)' },
        { char: 'ผ / พ', roman: 'ph', example: 'ผม / พ่อ', sound: '« p » + souffle — jamais un f ! (haute / basse)' },
        { char: 'ฝ / ฟ', roman: 'f', example: 'ฝน / ไฟ', sound: 'comme le f de « feu » (haute / basse)' },
        { char: 'ส / ซ', roman: 's', example: 'สวย / ซ้าย', sound: '« s » (haute / basse)' },
        { char: 'ห / ฮ', roman: 'h', example: 'หก / ฮา', sound: 'un h soufflé (haute / basse) ; ห élève aussi en silence la classe de la lettre suivante' },
      ],
    },
    {
      title: 'Sonantes et le reste',
      rows: [
        { char: 'ม', roman: 'm', example: 'แม่', sound: 'comme le m de « main »' },
        { char: 'น / ณ', roman: 'n', example: 'น้ำ', sound: 'comme le n de « non »' },
        { char: 'ง', roman: 'ng', example: 'งู', sound: 'le ng de « parking », sans g — même en DÉBUT de mot' },
        { char: 'ร', roman: 'r', example: 'รถ', sound: 'r roulé (devient souvent l en parler relâché)' },
        { char: 'ล', roman: 'l', example: 'ลิง', sound: 'comme le l de « lune »' },
        { char: 'ว', roman: 'w', example: 'วัน', sound: 'comme le « ou » de « oui »' },
        { char: 'ย / ญ', roman: 'y', example: 'ยา', sound: 'comme le y de « yoga »' },
        { char: 'ช', roman: 'ch', example: 'ช้าง', sound: '« tch » + souffle' },
      ],
    },
    {
      title: 'Voyelles de base (montrées sur ก)',
      note: 'Brève ou longue, la voyelle change le sens — tenez nettement les longues.',
      rows: [
        { char: 'กะ / กา', roman: 'a / aa', example: 'มา', sound: 'a bref / long, comme le a de « papa »' },
        { char: 'กิ / กี', roman: 'i / ii', example: 'มี', sound: 'i bref / long, comme le i de « vie »' },
        { char: 'กุ / กู', roman: 'u / uu', example: 'ดู', sound: '« ou » bref / long, comme dans « fou »' },
        { char: 'เกะ / เก', roman: 'e', example: 'เย็น', sound: 'è bref, comme dans « mère » / é long' },
        { char: 'โกะ / โก', roman: 'o', example: 'โต', sound: 'o bref / long, comme dans « eau »' },
        { char: 'ไก / ใก', roman: 'ai', example: 'ไป', sound: 'comme « aï » dans « aïe ! » — deux graphies, un seul son' },
        { char: 'เกา', roman: 'ao', example: 'เก้า', sound: 'comme « aou » dans « caoutchouc », en une syllabe' },
        { char: 'กือ', roman: 'ue', example: 'มือ', sound: 'un « u » à lèvres étirées — n’existe pas en français' },
      ],
    },
    {
      title: 'Les cinq tons',
      note: 'Même syllabe, cinq sens. Le ton vient de la classe de la consonne + du signe de ton + du type de syllabe.',
      rows: [
        { char: 'มา (moyen)', roman: 'maa', example: 'มา', sound: 'hauteur stable — venir' },
        { char: 'หม่า (bas)', roman: 'màa', example: 'ไม่', sound: 'commence bas, reste bas' },
        { char: 'ม้า (haut… descendant)', roman: 'máa', example: 'ม้า', sound: 'ton haut — cheval' },
        { char: 'หม้า (descendant)', roman: 'mâa', example: 'บ้าน', sound: 'chute du haut vers le bas' },
        { char: 'หมา (montant)', roman: 'mǎa', example: 'หมา', sound: 'creuse puis remonte — chien (gare à la paire cheval/chien !)' },
      ],
    },
  ],
}

const koreanFr: LanguageLetters = {
  intro:
    'Le hangul — 24 lettres de base qui s’ASSEMBLENT en blocs syllabiques. Inventé en 1443 pour s’apprendre en une matinée ; les formes dessinent même la bouche qui fait le son.',
  sections: [
    {
      title: 'Comment les lettres s’assemblent',
      note: 'Les lettres s’empilent en blocs carrés : consonne + voyelle, plus une consonne finale facultative (받침) en dessous. 한국, c’est six lettres en deux blocs.',
      rows: [
        { char: 'ㅎ + ㅏ + ㄴ → 한', roman: 'h + a + n', example: '한국', sound: 'consonne à gauche, voyelle verticale à droite, lettre finale en dessous' },
        { char: 'ㄱ + ㅜ + ㄱ → 국', roman: 'g + u + k', example: '한국', sound: 'les voyelles horizontales vont SOUS la première consonne' },
        { char: 'ㅅ + ㅏ → 사', roman: 's + a', example: '사람', sound: 'pas de lettre finale — juste consonne + voyelle' },
        { char: 'ㅇ + ㅜ → 우', roman: '(silent) + u', example: '우유', sound: 'ㅇ est un support muet quand le bloc commence par une voyelle' },
        { char: 'ㅂ + ㅏ + ㅂ → 밥', roman: 'b + a + p', example: '밥', sound: 'le ㅂ final (받침) ferme la syllabe' },
        { char: '받침 rule', roman: 'finals', example: '있다', sound: 'seuls 7 sons peuvent clore un bloc : k, n, t, l, m, p, ng — l’orthographe garde la lettre, la bouche simplifie' },
      ],
    },
    {
      title: 'Consonnes simples',
      rows: [
        { char: 'ㄱ', roman: 'g/k', example: '가다', sound: 'entre g et k — plutôt « g » en début de groupe' },
        { char: 'ㄴ', roman: 'n', example: '나', sound: 'comme le n de « non »' },
        { char: 'ㄷ', roman: 'd/t', example: '돈', sound: 'entre d et t' },
        { char: 'ㄹ', roman: 'r/l', example: '물', sound: 'un r battu entre voyelles ; l en fin de bloc' },
        { char: 'ㅁ', roman: 'm', example: '몸', sound: 'comme le m de « main »' },
        { char: 'ㅂ', roman: 'b/p', example: '밥', sound: 'entre b et p' },
        { char: 'ㅅ', roman: 's', example: '사람', sound: 'comme le s de « soleil » ; « ch » devant ㅣ' },
        { char: 'ㅇ', roman: '-/ng', example: '강', sound: 'muet au début ; le ng de « parking » à la fin' },
        { char: 'ㅈ', roman: 'j', example: '집', sound: 'entre dj et tch' },
        { char: 'ㅎ', roman: 'h', example: '하다', sound: 'un h vraiment soufflé, comme dans l’anglais house' },
      ],
    },
    {
      title: 'Consonnes aspirées (un souffle en plus)',
      note: 'Chacune est une consonne simple avec un trait en plus et un souffle en plus.',
      rows: [
        { char: 'ㅋ', roman: 'k', example: '코', sound: '« k » avec un souffle net (ㄱ + air)' },
        { char: 'ㅌ', roman: 't', example: '토요일', sound: '« t » avec un souffle net (ㄷ + air)' },
        { char: 'ㅍ', roman: 'p', example: '팔', sound: '« p » avec un souffle net (ㅂ + air)' },
        { char: 'ㅊ', roman: 'ch', example: '차', sound: '« tch » avec un souffle net (ㅈ + air)' },
      ],
    },
    {
      title: 'Consonnes tendues (doublées, sans air)',
      note: 'Gorge serrée, zéro souffle — le p français de « papa » est déjà proche ; serrez encore un peu plus.',
      rows: [
        { char: 'ㄲ', roman: 'kk', example: '까만', sound: 'un « k » serré, sans aucun souffle' },
        { char: 'ㄸ', roman: 'tt', example: '딸', sound: 'un « t » serré, sans souffle' },
        { char: 'ㅃ', roman: 'pp', example: '빵', sound: 'un « p » serré, sans souffle' },
        { char: 'ㅆ', roman: 'ss', example: '쌀', sound: 'un « s » serré' },
        { char: 'ㅉ', roman: 'jj', example: '짜다', sound: 'un « tch » serré, sans souffle' },
      ],
    },
    {
      title: 'Voyelles de base',
      rows: [
        { char: 'ㅏ', roman: 'a', example: '아빠', sound: 'comme le a de « papa »' },
        { char: 'ㅓ', roman: 'eo', example: '어머니', sound: 'un o très ouvert, qui tire vers le a — l’anglais cut' },
        { char: 'ㅗ', roman: 'o', example: '오늘', sound: 'o fermé, comme dans « eau » (lèvres arrondies)' },
        { char: 'ㅜ', roman: 'u', example: '우리', sound: 'comme ou dans « fou »' },
        { char: 'ㅡ', roman: 'eu', example: '그', sound: 'un « ou » à lèvres PLATES — dites « ou » en souriant' },
        { char: 'ㅣ', roman: 'i', example: '이름', sound: 'comme le i de « vie »' },
        { char: 'ㅐ', roman: 'ae', example: '개', sound: 'comme le è de « mère » (identique à ㅔ aujourd’hui)' },
        { char: 'ㅔ', roman: 'e', example: '세 시', sound: 'comme le è de « mère »' },
      ],
    },
    {
      title: 'Voyelles en y- et en w-',
      note: 'Un trait en plus ajoute un y- ; deux voyelles combinées font un w-.',
      rows: [
        { char: 'ㅑ ㅕ ㅛ ㅠ', roman: 'ya yeo yo yu', example: '야구, 여자', sound: 'les quatre voyelles de base précédées d’un y' },
        { char: 'ㅒ ㅖ', roman: 'yae ye', example: '예', sound: '« yè », comme dans « hyène »' },
        { char: 'ㅘ ㅝ', roman: 'wa wo', example: '와요, 뭐', sound: '« oua », comme dans « quoi » ; « ouo » = ou + o très ouvert' },
        { char: 'ㅙ ㅞ ㅚ', roman: 'wae we oe', example: '왜, 회사', sound: 'les trois sonnent « ouè » aujourd’hui — comme dans « ouest »' },
        { char: 'ㅟ', roman: 'wi', example: '귀', sound: '« oui », comme le mot « oui »' },
        { char: 'ㅢ', roman: 'ui', example: '의사', sound: 'ㅡ + i glissés ensemble ; souvent juste « i » ou « è » à l’oral' },
      ],
    },
  ],
}

export const LETTERS_FR: Record<string, LanguageLetters> = {
  es: spanishFr,
  fr: frenchFr,
  de: germanFr,
  it: italianFr,
  ca: catalanFr,
  pt: portugueseFr,
  ro: romanianFr,
  tr: turkishFr,
  sw: swahiliFr,
  yo: yorubaFr,
  ha: hausaFr,
  xh: xhosaFr,
  mi: maoriFr,
  jam: jamaicanFr,
  en: englishFr,
  nl: dutchFr,
  ru: russianFr,
  el: greekFr,
  ar: arabicFr,
  hi: hindiFr,
  th: thaiFr,
  ko: koreanFr,
}
