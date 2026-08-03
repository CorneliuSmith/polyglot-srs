/**
 * Letters & Sounds — Portuguese (pt) overlay: every course's guide rewritten
 * for a Portuguese-speaking reader. Not word-for-word translations — each
 * sound is re-anchored in a real Portuguese word (Brazilian-leaning, matching
 * turkishPt); where Portuguese lacks the sound, it is described, with French
 * or English as reference. char/roman/example are copied verbatim from the
 * base data; only parenthetical asides inside char are localized.
 */
import type { LanguageLetters } from './lettersData'

const spanishPt: LanguageLetters = {
  intro:
    'A ortografia espanhola é honesta: cinco vogais puras, e quase toda letra soa sempre igual.',
  sections: [
    {
      title: 'As cinco vogais',
      note: 'Curtas, puras, nunca arrastadas. O acento (á é í ó ú) marca a sílaba tônica — o som não muda.',
      rows: [
        { char: 'a / á', example: 'agua', sound: "como o a de 'casa'" },
        { char: 'e / é', example: 'leche', sound: "entre o é de 'pé' e o ê de 'você'" },
        { char: 'i / í', example: 'vivir', sound: "como o i de 'ali'" },
        { char: 'o / ó', example: 'poco', sound: "como o ó de 'avó'" },
        { char: 'u / ú', example: 'luna', sound: "como o u de 'tudo' (mudo em que/qui, gue/gui)" },
        { char: 'ü', example: 'pingüino', sound: "o trema acorda o u: gü soa como o gu de 'aguentar'" },
      ],
    },
    {
      title: 'Consoantes que diferem do português',
      rows: [
        { char: 'ñ', example: 'niño', sound: "como o nh de 'ninho'" },
        { char: 'j', example: 'joven', sound: "raspado no fundo da boca — como o rr carioca de 'carro'" },
        { char: 'g (+e/i)', example: 'gente', sound: "o mesmo raspado; nas outras posições, g de 'gato'" },
        { char: 'll / y', example: 'llamar', sound: "como o i de 'ioga' (um 'dj' leve em boa parte da América Latina)" },
        { char: 'h', example: 'hola', sound: 'sempre muda, como a nossa' },
        { char: 'rr / r-', example: 'perro', sound: "rr vibrante, com a ponta da língua tremulando; o r simples entre vogais é o r de 'caro'" },
        { char: 'z / c(+e,i)', example: 'zapato', sound: "'s' na América Latina; na Espanha, o th do inglês 'think' (língua entre os dentes)" },
        { char: 'v', example: 'vaso', sound: "igual ao b espanhol — um 'b' suave, nunca o nosso v" },
        { char: 'qu', example: 'queso', sound: "como o c de 'casa' — o u é mudo" },
      ],
    },
  ],
}

const frenchPt: LanguageLetters = {
  intro:
    'Os sons do francês vivem nas vogais e na ligação entre as palavras. As consoantes finais em geral são mudas; os acentos mudam a qualidade da vogal, não a sílaba tônica.',
  sections: [
    {
      title: 'As vogais e seus acentos',
      rows: [
        { char: 'a / à / â', example: 'chat', sound: "como o a de 'casa'" },
        { char: 'é', example: 'été', sound: "como o ê de 'você', sem deslize" },
        { char: 'è / ê / e(+2 cons.)', example: 'mère', sound: "é aberto, como o é de 'pé'" },
        { char: 'e (sem acento)', example: 'le', sound: "um 'e' apagado e átono — muitas vezes nem se pronuncia" },
        { char: 'i / î / y', example: 'ville', sound: "como o i de 'ali'" },
        { char: 'o / ô', example: 'mot', sound: "como o ô de 'avô'" },
        { char: 'u / û', example: 'tu', sound: "diga 'i' e arredonde os lábios — não existe em português" },
        { char: 'ou', example: 'vous', sound: "como o u de 'tudo'" },
        { char: 'eu / œu', example: 'peu', sound: "diga 'ê' com os lábios arredondados" },
        { char: 'oi', example: 'moi', sound: "como o ua de 'quadro'" },
        { char: 'au / eau', example: 'eau', sound: "como o ô de 'avô'" },
        { char: 'ai / ei', example: 'maison', sound: "como o é de 'pé'" },
      ],
    },
    {
      title: 'As vogais nasais',
      note: 'Vogal + n/m na mesma sílaba = ar pelo nariz, como nas nossas nasais — e o n/m NÃO se pronuncia.',
      rows: [
        { char: 'on / om', example: 'bon', sound: "como o om de 'bom'" },
        { char: 'an / en', example: 'enfant', sound: "parecido com o ã de 'maçã', porém mais aberto" },
        { char: 'in / ain / ein', example: 'vin', sound: "um 'é' nasal — comece no é de 'pé' e solte o ar pelo nariz" },
        { char: 'un', example: 'un', sound: 'um «eu» nasal (para muitos falantes, igual a in)' },
      ],
    },
    {
      title: 'Hábitos das consoantes',
      rows: [
        { char: 'r', example: 'rouge', sound: "raspado no fundo da garganta — como o rr carioca de 'carro'" },
        { char: 'ç', example: 'garçon', sound: "'s' — a cedilha funciona como a nossa, mantendo o c suave antes de a/o/u" },
        { char: 'ch', example: 'chien', sound: "como o ch de 'chuva'" },
        { char: 'gn', example: 'montagne', sound: "como o nh de 'ninho'" },
        { char: 'j / g(+e,i)', example: 'jour', sound: "como o j de 'já'" },
        { char: 'h', example: 'homme', sound: 'mudo' },
        { char: 'final consonants', example: 'petit', sound: 'em geral mudas — atenção com s, t, d, x' },
      ],
    },
  ],
}

const germanPt: LanguageLetters = {
  intro:
    'O alemão se fala como se escreve, depois que você aprende os tremas (umlauts) e meia dúzia de grupos de letras.',
  sections: [
    {
      title: 'Vogais e umlauts',
      rows: [
        { char: 'a', example: 'Haus', sound: "como o a de 'casa'" },
        { char: 'ä', example: 'Mädchen', sound: "como o é de 'pé'" },
        { char: 'o', example: 'Brot', sound: "como o ô de 'avô'" },
        { char: 'ö', example: 'schön', sound: "diga 'ê' com os lábios arredondados (o eu francês)" },
        { char: 'u', example: 'gut', sound: "como o u de 'tudo'" },
        { char: 'ü', example: 'über', sound: "diga 'i' com os lábios arredondados (o u francês)" },
        { char: 'ei', example: 'mein', sound: "como o ai de 'pai'" },
        { char: 'ie', example: 'Liebe', sound: "como o i de 'ali'" },
        { char: 'eu / äu', example: 'heute', sound: "como o ói de 'dói'" },
        { char: 'au', example: 'Auto', sound: "como o au de 'mau'" },
      ],
    },
    {
      title: 'Grupos de consoantes',
      rows: [
        { char: 'w', example: 'Wasser', sound: "como o v de 'vida'" },
        { char: 'v', example: 'Vater', sound: "como o f de 'faca'" },
        { char: 'z', example: 'Zeit', sound: "como o ts de 'tsunami'" },
        { char: 's (+vogal)', example: 'Sonne', sound: "como o z de 'zebra'" },
        { char: 'ß / ss', example: 'Straße', sound: "'s' forte, como o ss de 'passo'" },
        { char: 'sch', example: 'Schule', sound: "como o ch de 'chuva'" },
        { char: 'st- / sp-', example: 'Straße', sound: "'cht' / 'chp' no início da palavra — ch de 'chuva' + t/p" },
        { char: 'ch (depois de a/o/u)', example: 'Buch', sound: "raspado, como o rr carioca de 'carro'" },
        { char: 'ch (depois de e/i)', example: 'ich', sound: "um sopro sussurrado — diga o ch de 'chuva' sorrindo, bem à frente da boca" },
        { char: 'r', example: 'rot', sound: 'raspado no fundo da garganta; quase vogal no fim da palavra (-er = um a átono)' },
        { char: 'final b/d/g', example: 'Tag', sound: 'endurecem para p/t/k' },
      ],
    },
  ],
}

const italianPt: LanguageLetters = {
  intro:
    'Sete sons de vogal, consoantes duplas bem marcadas e duas letras (c, g) que amolecem antes de e e i.',
  sections: [
    {
      title: 'Vogais',
      rows: [
        { char: 'a / à', example: 'casa', sound: "como o a de 'casa'" },
        { char: 'e / è', example: 'bene', sound: "é aberto de 'pé' (o é agudo é fechado, como o ê de 'você')" },
        { char: 'i / ì', example: 'vino', sound: "como o i de 'ali'" },
        { char: 'o / ò', example: 'otto', sound: "como o ó de 'avó'" },
        { char: 'u / ù', example: 'uno', sound: "como o u de 'tudo'" },
      ],
    },
    {
      title: 'O sistema c/g',
      rows: [
        { char: 'c (+a,o,u)', example: 'casa', sound: "como o c de 'casa'" },
        { char: 'c (+e,i)', example: 'cena', sound: "como o tch de 'tchau'" },
        { char: 'ch', example: 'chiave', sound: "c de 'casa' — o h endurece o som de volta" },
        { char: 'g (+a,o,u)', example: 'gatto', sound: "como o g de 'gato'" },
        { char: 'g (+e,i)', example: 'gelato', sound: "como dj — o j do inglês 'jam'" },
        { char: 'gh', example: 'spaghetti', sound: "g de 'gato' — endurecido de volta" },
        { char: 'gn', example: 'gnocchi', sound: "como o nh de 'ninho'" },
        { char: 'gli', example: 'famiglia', sound: "como o lh de 'filho'" },
        { char: 'sc (+e,i)', example: 'pesce', sound: "como o ch de 'chuva'" },
      ],
    },
    {
      title: 'Hábitos',
      rows: [
        { char: 'double consonants', example: 'pizza', sound: 'seguradas pelo dobro do tempo — pit-tsa, não pi-tsa' },
        { char: 'z', example: 'zio', sound: "'ts' ou 'dz'" },
        { char: 'r', example: 'Roma', sound: 'vibrante, como o rr do espanhol' },
        { char: 'h', example: 'hotel', sound: 'mudo' },
      ],
    },
  ],
}

const catalanPt: LanguageLetters = {
  intro:
    'As vogais do catalão se reduzem quando átonas (uma assinatura da língua), e algumas grafias são só dela.',
  sections: [
    {
      title: 'Vogais',
      rows: [
        { char: 'a / à', example: 'casa', sound: "a de 'casa' quando tônico; átono, um 'e' apagado (schwa)" },
        { char: 'e / é / è', example: 'més', sound: "'ê'/'é' quando tônico; átono, o mesmo 'e' apagado" },
        { char: 'i / í', example: 'nit', sound: "como o i de 'ali'" },
        { char: 'o / ó / ò', example: 'porta', sound: "'ô'/'ó' quando tônico; átono, u de 'tudo'" },
        { char: 'u / ú', example: 'butxaca', sound: "como o u de 'tudo'" },
      ],
    },
    {
      title: 'Especialidades catalãs',
      rows: [
        { char: 'ny', example: 'Catalunya', sound: "como o nh de 'ninho'" },
        { char: 'l·l', example: 'il·lusió', sound: 'o ponto voador: um l longo' },
        { char: 'x', example: 'xocolata', sound: "como o ch de 'chuva'" },
        { char: 'tx', example: 'cotxe', sound: "como o tch de 'tchau'" },
        { char: 'ç', example: 'plaça', sound: "'s', como a nossa cedilha" },
        { char: 'j / g(+e,i)', example: 'jugar', sound: "como o j de 'já'" },
        { char: 'r final', example: 'cantar', sound: 'em geral mudo' },
        { char: 'ig final', example: 'puig', sound: "como o tch de 'tchau'" },
      ],
    },
  ],
}

const portuguesePt: LanguageLetters = {
  intro:
    'O português brasileiro por dentro: vogais abertas e fechadas, a famosa família nasal e consoantes com regras bem nossas.',
  sections: [
    {
      title: 'Vogais e acentos',
      rows: [
        { char: 'a / á', example: 'casa', sound: "a aberto, como em 'casa'" },
        { char: 'â', example: 'câmera', sound: 'a fechado, mais abafado' },
        { char: 'e / é', example: 'ela', sound: "é aberto, como em 'ela'" },
        { char: 'ê', example: 'você', sound: "ê fechado, como em 'você'" },
        { char: 'e final', example: 'nome', sound: "átono, no Brasil reduz-se a um i: 'nomi'" },
        { char: 'o / ó', example: 'avó', sound: 'ó aberto' },
        { char: 'ô', example: 'avô', sound: 'ô fechado — avó e avô diferem só nisso!' },
        { char: 'o final', example: 'gato', sound: "átono, reduz-se a um u: 'gatu'" },
        { char: 'u', example: 'tudo', sound: 'u pleno' },
      ],
    },
    {
      title: 'A família nasal',
      note: 'O til (~) ou um m/n seguinte manda a vogal pelo nariz.',
      rows: [
        { char: 'ã', example: 'maçã', sound: 'a nasal' },
        { char: 'ão', example: 'pão', sound: 'ditongo nasal — o som mais português que existe' },
        { char: 'õe', example: 'ações', sound: "ditongo nasal de 'ações', 'põe'" },
        { char: 'em / en', example: 'bem', sound: "ditongo nasal — 'bem' soa quase 'beim'" },
        { char: 'im / in', example: 'sim', sound: 'i nasal' },
      ],
    },
    {
      title: 'Consoantes com regra própria',
      rows: [
        { char: 'ç', example: 'coração', sound: "sempre 's'" },
        { char: 'ch', example: 'chuva', sound: "o mesmo som do x de 'xícara'" },
        { char: 'lh', example: 'filho', sound: 'a lateral palatal — língua espalmada no céu da boca' },
        { char: 'nh', example: 'ninho', sound: 'o n palatal — irmão nasal do lh' },
        { char: 'j / g(+e,i)', example: 'hoje', sound: "um único som: o j de 'hoje' e o g de 'gente'" },
        { char: 'r- / rr', example: 'rio', sound: "no Brasil, um 'h' aspirado: 'rio', 'carro'" },
        { char: 'ti / di', example: 'dia', sound: "na maior parte do Brasil, 'tchi' e 'dji': 'dia' soa 'djia'" },
        { char: 'l final', example: 'Brasil', sound: "vira 'u': Brasil soa 'Brasiu'" },
      ],
    },
  ],
}

const romanianPt: LanguageLetters = {
  intro:
    'O romeno se lê quase como o italiano, com cinco letras a mais — e as cinco são regulares.',
  sections: [
    {
      title: 'As cinco letras especiais',
      rows: [
        { char: 'ă', example: 'casă', sound: "um 'e' apagado e relaxado, como o a final átono de 'casa'" },
        { char: 'â / î', example: 'în', sound: "um 'i' grave e central — diga 'i' com a língua puxada para trás; não existe em português" },
        { char: 'ș', example: 'și', sound: "como o ch de 'chuva'" },
        { char: 'ț', example: 'preț', sound: "como o ts de 'tsunami'" },
      ],
    },
    {
      title: 'Vale saber',
      rows: [
        { char: 'c (+e,i)', example: 'ce', sound: "como o tch de 'tchau'" },
        { char: 'che / chi', example: 'chelner', sound: "como o c de 'casa'" },
        { char: 'g (+e,i)', example: 'ger', sound: "como dj — o j do inglês 'jam'" },
        { char: 'ghe / ghi', example: 'ghid', sound: "como o g de 'gato'" },
        { char: 'j', example: 'jos', sound: "como o j de 'já'" },
        { char: 'r', example: 'repede', sound: 'vibrante, como o rr do espanhol' },
        { char: '-i final', example: 'lupi', sound: 'sussurrado — mal chega a ser um i' },
      ],
    },
  ],
}

// tr — reused verbatim from lettersL10n.ts (turkishPt).
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

const swahiliPt: LanguageLetters = {
  intro:
    'O suaíli é maravilhosamente fonético: cinco vogais puras, sílaba tônica sempre na penúltima.',
  sections: [
    {
      title: 'Vogais',
      rows: [
        { char: 'a', example: 'baba', sound: "como o a de 'casa'" },
        { char: 'e', example: 'wewe', sound: "como o é de 'pé'" },
        { char: 'i', example: 'sisi', sound: "como o i de 'ali'" },
        { char: 'o', example: 'moto', sound: "como o ó de 'avó'" },
        { char: 'u', example: 'kuku', sound: "como o u de 'tudo'" },
      ],
    },
    {
      title: 'Grupos de letras',
      rows: [
        { char: 'ny', example: 'nyumba', sound: "como o nh de 'ninho'" },
        { char: "ng'", example: "ng'ombe", sound: "o n de fundo de boca de 'manga' (sem soltar o g) — no COMEÇO da sílaba" },
        { char: 'ng (sem apóstrofo)', example: 'ngoma', sound: "o mesmo n de fundo de boca + g de 'gato' bem solto: 'ng-g'" },
        { char: 'dh', example: 'dhahabu', sound: "o th sonoro do inglês 'this' — língua entre os dentes, com voz (empréstimos árabes)" },
        { char: 'th', example: 'thelathini', sound: "o th surdo do inglês 'think' — língua entre os dentes, sem voz" },
        { char: 'gh', example: 'ghali', sound: 'g gargarejado (empréstimos árabes)' },
        { char: 'ch', example: 'chai', sound: "como o tch de 'tchau'" },
        { char: 'mb / nd / nj', example: 'mbwa', sound: 'cantarole o m/n JUNTO com a consoante seguinte — uma batida só' },
      ],
    },
  ],
}

const yorubaPt: LanguageLetters = {
  intro:
    'O iorubá é uma língua tonal — os acentos marcam altura, não sílaba tônica. Duas letras com ponto marcam vogais abertas.',
  sections: [
    {
      title: 'Vogais (7) + os pontos',
      rows: [
        { char: 'a', example: 'ata', sound: "como o a de 'casa'" },
        { char: 'e', example: 'ewé', sound: "ê fechado, como em 'você'" },
        { char: 'ẹ (com ponto)', example: 'ẹja', sound: "é aberto, como em 'pé'" },
        { char: 'i', example: 'ilé', sound: "como o i de 'ali'" },
        { char: 'o', example: 'owó', sound: "ô fechado, como em 'avô'" },
        { char: 'ọ (com ponto)', example: 'ọmọ', sound: "ó aberto, como em 'avó'" },
        { char: 'u', example: 'imu', sound: "como o u de 'tudo'" },
      ],
    },
    {
      title: 'Os tons — as três alturas',
      note: 'As mesmas letras, outra altura, outra palavra. Os acentos são a melodia.',
      rows: [
        { char: 'á (alto)', example: 'wá', sound: 'o tom salta para cima' },
        { char: 'a (médio)', example: 'wa', sound: 'altura normal, nivelada' },
        { char: 'à (baixo)', example: 'wà', sound: 'o tom cai para baixo' },
      ],
    },
    {
      title: 'Consoantes',
      rows: [
        { char: 'ṣ (com ponto)', example: 'ṣe', sound: "como o ch de 'chuva'" },
        { char: 'gb', example: 'gbogbo', sound: "'g' e 'b' no mesmo instante exato — não existe em português" },
        { char: 'p', example: 'pápá', sound: "na verdade 'kp' soltos juntos" },
        { char: 'j', example: 'jẹun', sound: "como dj — o j do inglês 'jam'" },
      ],
    },
  ],
}

const hausaPt: LanguageLetters = {
  intro:
    'O hausa em boko usa três letras «com gancho» para sons que o português não tem — eles estalam em vez de fluir.',
  sections: [
    {
      title: 'Vogais',
      note: 'Cinco vogais, longas ou curtas — a duração muda o sentido.',
      rows: [
        { char: 'a', example: 'ruwa', sound: "a de 'casa' (longo: segure-o)" },
        { char: 'e', example: 'gemu', sound: "como o ê de 'você'" },
        { char: 'i', example: 'kifi', sound: "como o i de 'ali'" },
        { char: 'o', example: 'doki', sound: "como o ô de 'avô'" },
        { char: 'u', example: 'kudi', sound: "como o u de 'tudo'" },
      ],
    },
    {
      title: 'As letras com gancho',
      rows: [
        { char: 'ɓ', example: 'ɓera', sound: "um 'b' implosivo — o ar estala para dentro" },
        { char: 'ɗ', example: 'ɗaki', sound: "um 'd' implosivo" },
        { char: 'ƙ', example: 'ƙofa', sound: "um c de 'casa' com um estalo na glote" },
        { char: "'y", example: "'ya'ya", sound: "um i de 'ioga' rangido, com a garganta apertada" },
      ],
    },
    {
      title: 'Outros hábitos',
      rows: [
        { char: 'ts', example: 'tsuntsu', sound: "'ts' com um estalo" },
        { char: 'sh', example: 'shekara', sound: "como o ch de 'chuva'" },
        { char: 'c', example: 'ci', sound: "como o tch de 'tchau'" },
        { char: 'r', example: 'rana', sound: "vibrante, ou de batida única como em 'caro'" },
      ],
    },
  ],
}

const xhosaPt: LanguageLetters = {
  intro:
    'O isiXhosa é famoso pelos cliques — três cliques básicos, escritos c, x, q. O resto fica perto do que já conhecemos.',
  sections: [
    {
      title: 'Os três cliques',
      rows: [
        { char: 'c', example: 'cela', sound: "clique dental — o 'tsc-tsc' de reprovação, língua atrás dos dentes" },
        { char: 'x', example: 'ixesha', sound: 'clique lateral — o estalo de apressar o cavalo, pela lateral da boca' },
        { char: 'q', example: 'iqanda', sound: 'clique palatal — um estalo de rolha no céu da boca' },
        { char: 'gc / gx / gq', example: 'gqiba', sound: 'os mesmos cliques, sonoros (cantarole através deles)' },
        { char: 'nc / nx / nq', example: 'inqola', sound: 'os mesmos cliques com um zumbido nasal' },
      ],
    },
    {
      title: 'Vogais',
      rows: [
        { char: 'a', example: 'abantu', sound: "como o a de 'casa'" },
        { char: 'e', example: 'ewe', sound: "como o é de 'pé'" },
        { char: 'i', example: 'siza', sound: "como o i de 'ali'" },
        { char: 'o', example: 'onke', sound: "como o ó de 'avó'" },
        { char: 'u', example: 'ubuntu', sound: "como o u de 'tudo'" },
      ],
    },
    {
      title: 'Outros grupos de letras',
      rows: [
        { char: 'hl', example: 'hlala', sound: 'o ll galês — sopre o ar pelas laterais da língua' },
        { char: 'dl', example: 'indlela', sound: 'a versão sonora do hl' },
        { char: 'tsh', example: 'utshaba', sound: "como o tch de 'tchau'" },
        { char: 'kh / th / ph', example: 'ukutya', sound: 'k/t/p com um sopro de ar' },
      ],
    },
  ],
}

const maoriPt: LanguageLetters = {
  intro:
    'Te reo Māori: cinco vogais (curtas e longas), oito consoantes, dois dígrafos. Toda sílaba termina em vogal.',
  sections: [
    {
      title: 'Vogais — curtas e longas',
      note: 'O mácron (ā ē ī ō ū) dobra a duração, e a duração muda o sentido.',
      rows: [
        { char: 'a / ā', example: 'aroha', sound: "como o a de 'casa' (ā segurado mais tempo)" },
        { char: 'e / ē', example: 'kete', sound: "como o é de 'pé'" },
        { char: 'i / ī', example: 'kiwi', sound: "como o i de 'ali'" },
        { char: 'o / ō', example: 'moana', sound: "como o ó de 'avó'" },
        { char: 'u / ū', example: 'utu', sound: "como o u de 'tudo'" },
      ],
    },
    {
      title: 'Os dois dígrafos',
      rows: [
        { char: 'wh', example: 'whānau', sound: "como o f de 'faca'" },
        { char: 'ng', example: 'ngā', sound: "o n de fundo de boca de 'manga' — até no começo da palavra" },
      ],
    },
    {
      title: 'Consoantes',
      rows: [
        { char: 'r', example: 'reo', sound: "batida leve entre r e l, como o r de 'caro'" },
        { char: 't', example: 'te', sound: "'t' suave, quase sem sopro — como o nosso" },
        { char: 'k, m, n, p, h, w', example: 'kapa haka', sound: "como em português (o h é soprado, como o r inicial de 'rato' no Brasil)" },
      ],
    },
  ],
}

const jamaicanPt: LanguageLetters = {
  intro:
    'O patoá na grafia Cassidy/JLU: um som por letra, nenhuma letra muda. Se você sabe dizer, sabe escrever.',
  sections: [
    {
      title: 'Vogais',
      rows: [
        { char: 'a', example: 'bak', sound: "como o a de 'casa'" },
        { char: 'aa', example: 'baal', sound: "'a' longo, segurado" },
        { char: 'e', example: 'bel', sound: "como o é de 'pé'" },
        { char: 'i', example: 'sik', sound: "'i' curto e relaxado, puxado para o ê — não existe em português" },
        { char: 'ii', example: 'siik', sound: "como o i de 'ali'" },
        { char: 'o', example: 'pat', sound: "ó aberto, como em 'avó'" },
        { char: 'u', example: 'buk', sound: "'u' curto e relaxado" },
        { char: 'uu', example: 'skuul', sound: "u longo de 'tudo'" },
        { char: 'ie', example: 'kiek', sound: "deslize 'iê' — cake dito à moda jamaicana" },
        { char: 'uo', example: 'guo', sound: "deslize 'uô' — go dito à moda jamaicana" },
        { char: 'ai', example: 'taim', sound: "como o ai de 'pai'" },
        { char: 'ou', example: 'bout', sound: "como o au de 'mau'" },
      ],
    },
    {
      title: 'Hábitos das consoantes',
      rows: [
        { char: 'k / g (+ya)', example: 'kyaan', sound: "deslize ky/gy — 'kiã' para can't" },
        { char: 'no th', example: 'tink / dis', sound: "o th inglês vira 't' ou 'd' simples" },
        { char: 'no h-drop rule', example: 'ouse / haks', sound: 'o h vai e vem à vontade — as duas formas valem' },
        { char: 'final clusters trim', example: 'las (last)', sound: 'a última consoante de um amontoado cai' },
      ],
    },
  ],
}

const englishPt: LanguageLetters = {
  intro:
    'A ortografia inglesa é história, não fonética. Estes são os sons em que os alunos penam — com as grafias confiáveis, quando existem.',
  sections: [
    {
      title: 'Os famosos',
      rows: [
        { char: 'th (surdo)', example: 'think', sound: 'língua entre os dentes, sopre o ar — sem voz; não existe em português' },
        { char: 'th (sonoro)', example: 'this', sound: 'mesma posição, acrescente a voz' },
        { char: 'w vs v', example: 'very wet', sound: "w = lábios arredondados, sem dentes (o u de 'água'); v = dentes no lábio (o v de 'vida')" },
        { char: 'r', example: 'red', sound: 'não vibra nem raspa — curve a língua para trás sem tocar em nada' },
        { char: 'h', example: 'house', sound: "um sopro de verdade, como o r inicial de 'rato' no Brasil — nunca mudo (exceto hour, honest)" },
      ],
    },
    {
      title: 'Vogais que derrubam os alunos',
      rows: [
        { char: 'i (curto)', example: 'ship', sound: "'i' relaxado, puxado para o ê — ship NÃO é sheep" },
        { char: 'ee', example: 'sheep', sound: "i longo e tenso, como o i de 'ali' esticado" },
        { char: 'a (curto)', example: 'cat', sound: "um 'é' de boca bem aberta, quase um a" },
        { char: 'u (curto)', example: 'cup', sound: "um 'a' curto e abafado, dito no meio da boca" },
        { char: 'er / unstressed', example: 'teacher', sound: "o schwa — a vogal mais preguiçosa, como o a final átono de 'casa'; quase toda sílaba átona usa ele" },
      ],
    },
    {
      title: 'Padrões de grafia confiáveis',
      rows: [
        { char: 'magic e', example: 'hat → hate', sound: "o e final mudo muda a vogal para o nome inglês da letra: hat ('rét') vira hate ('rêit')" },
        { char: '-tion', example: 'station', sound: "soa 'xân'" },
        { char: 'ough', example: 'though / tough', sound: 'desculpe — seis sons diferentes; aprenda palavra por palavra' },
      ],
    },
  ],
}

const dutchPt: LanguageLetters = {
  intro:
    'A ortografia holandesa é amigável — alguns grupos de letras e uma vogal famosa (ui) fazem todo o estrago.',
  sections: [
    {
      title: 'Os times de vogais',
      rows: [
        { char: 'aa / a', example: 'water', sound: "'a' longo de 'casa' / 'a' curto e abafado — dobrar a letra marca a duração" },
        { char: 'ee / e', example: 'been', sound: "'ê' longo de 'você' / 'é' curto; o -e final é um schwa (a final átono de 'casa')" },
        { char: 'oo / o', example: 'boom', sound: "'ô' longo de 'avô' / 'ó' curto" },
        { char: 'uu / u', example: 'muur', sound: "diga 'i' com os lábios arredondados / 'e' curto e abafado" },
        { char: 'ie', example: 'niet', sound: "como o i de 'ali'" },
        { char: 'oe', example: 'boek', sound: "como o u de 'tudo'" },
        { char: 'eu', example: 'leuk', sound: "diga 'ê' com os lábios arredondados (o eu francês)" },
        { char: 'ij / ei', example: 'ijs', sound: "entre o 'ai' de 'pai' e 'éi' — o famoso ditongo holandês, com duas grafias" },
        { char: 'ui', example: 'huis', sound: "não existe em português: diga o 'au' de 'mau' com os lábios bem arredondados e fechados" },
        { char: 'ou / au', example: 'oud', sound: "como o au de 'mau'" },
      ],
    },
    {
      title: 'Hábitos das consoantes',
      rows: [
        { char: 'g / ch', example: 'goed', sound: "o raspado holandês — um rr carioca de 'carro' bem forte (mais suave no sul)" },
        { char: 'sch', example: 'school', sound: "'s' + o raspado: s-chool" },
        { char: 'w', example: 'water', sound: "entre o u de 'água' e o v" },
        { char: 'v', example: 'vader', sound: 'entre v e f' },
        { char: 'j', example: 'ja', sound: "como o i de 'ioga'" },
        { char: 'r', example: 'rood', sound: 'vibrante ou raspado — os dois valem' },
        { char: '-en (terminação)', example: 'lopen', sound: "o n final costuma cair: 'lope(n)'" },
        { char: '-tje', example: 'kopje', sound: 'a máquina de diminutivos — koppje, huisje, momentje' },
      ],
    },
  ],
}

const russianPt: LanguageLetters = {
  intro:
    'O alfabeto cirílico — 33 letras. A maioria tem um som fixo; o sistema a aprender são os cinco pares de vogais «duras/moles».',
  sections: [
    {
      title: 'Vogais — série dura',
      note: 'Estas mantêm simples a consoante anterior.',
      rows: [
        { char: 'а', roman: 'a', example: 'мама', sound: "como o a de 'casa'" },
        { char: 'э', roman: 'e', example: 'это', sound: "como o é de 'pé'" },
        { char: 'ы', roman: 'y', example: 'мы', sound: "um 'i' grave — diga 'i' com a língua puxada para trás; não existe em português" },
        { char: 'о', roman: 'o', example: 'дом', sound: "como o ó de 'avó' (só quando tônico)" },
        { char: 'у', roman: 'u', example: 'утро', sound: "como o u de 'tudo'" },
      ],
    },
    {
      title: 'Vogais — série mole',
      note: 'Os mesmos sons de vogal, mas amolecem a consoante anterior (acrescentam um deslize de i escondido).',
      rows: [
        { char: 'я', roman: 'ya', example: 'яблоко', sound: "'iá', como em 'piada'" },
        { char: 'е', roman: 'e/ye', example: 'нет', sound: "'iê', como em 'fiel'" },
        { char: 'и', roman: 'i', example: 'мир', sound: "como o i de 'ali'" },
        { char: 'ё', roman: 'yo', example: 'ёлка', sound: "'iô', como em 'ioiô' (sempre tônica)" },
        { char: 'ю', roman: 'yu', example: 'юг', sound: "'iú', como em 'ciúme'" },
      ],
    },
    {
      title: 'Consoantes que parecem conhecidas (mas não são)',
      rows: [
        { char: 'в', roman: 'v', example: 'вода', sound: "como o v de 'vida' (não é b)" },
        { char: 'н', roman: 'n', example: 'нос', sound: "como o n de 'não' (não é h)" },
        { char: 'р', roman: 'r', example: 'рука', sound: 'r vibrante, como o rr do espanhol' },
        { char: 'с', roman: 's', example: 'сок', sound: "como o s de 'sapo' (não é k)" },
        { char: 'у', roman: 'u', example: 'ум', sound: "parece um y, mas é sempre o u de 'tudo'" },
        { char: 'х', roman: 'h/x', example: 'хлеб', sound: "raspado, como o rr carioca de 'carro'" },
      ],
    },
    {
      title: 'O resto das consoantes',
      rows: [
        { char: 'б', roman: 'b', example: 'брат', sound: "como o b de 'bola'" },
        { char: 'г', roman: 'g', example: 'год', sound: "como o g de 'gato'" },
        { char: 'д', roman: 'd', example: 'да', sound: "como o d de 'dado'" },
        { char: 'ж', roman: 'zh', example: 'жить', sound: "como o j de 'já'" },
        { char: 'з', roman: 'z', example: 'зима', sound: "como o z de 'zebra'" },
        { char: 'й', roman: 'j', example: 'мой', sound: "o deslize de i no fim de 'pai'" },
        { char: 'к', roman: 'k', example: 'кот', sound: "como o c de 'casa'" },
        { char: 'л', roman: 'l', example: 'лампа', sound: "como o l de 'lata'" },
        { char: 'м', roman: 'm', example: 'мост', sound: "como o m de 'mapa'" },
        { char: 'п', roman: 'p', example: 'папа', sound: "como o p de 'pato'" },
        { char: 'т', roman: 't', example: 'там', sound: "como o t de 'tatu'" },
        { char: 'ф', roman: 'f', example: 'фото', sound: "como o f de 'faca'" },
        { char: 'ц', roman: 'c/ts', example: 'цирк', sound: "como o ts de 'tsunami'" },
        { char: 'ч', roman: 'ch', example: 'чай', sound: "como o tch de 'tchau'" },
        { char: 'ш', roman: 'sh', example: 'школа', sound: "ch duro de 'chuva', com a língua mais para trás" },
        { char: 'щ', roman: 'shch', example: 'щи', sound: "um 'ch' longo e mole — diga o ch de 'chuva' sorrindo e segure" },
      ],
    },
    {
      title: 'Os dois sinais mudos',
      rows: [
        { char: 'ь', roman: "'", example: 'день', sound: 'sinal mole — amolece a consoante anterior (acrescenta um toque de i)' },
        { char: 'ъ', roman: "''", example: 'объект', sound: 'sinal duro — uma pausa minúscula entre prefixo e raiz' },
      ],
    },
    {
      title: 'Imprensa vs itálico (e letra de mão)',
      note: 'O cirílico digitado tem duas caras. No itálico — e mais ainda na letra de mão — várias letras viram formas que parecem OUTRAS letras latinas. Mesma letra, mesmo som: compare cada par.',
      italics: true,
      rows: [
        { char: 'т', roman: 't', example: 'там', sound: "o т itálico vira um m — continua sendo 't'" },
        { char: 'и', roman: 'i', example: 'мир', sound: "o и itálico vira um u — continua sendo 'i'" },
        { char: 'й', roman: 'j', example: 'мой', sound: 'o й itálico é esse u com o arquinho em cima' },
        { char: 'п', roman: 'p', example: 'папа', sound: "o п itálico vira um n — continua sendo 'p'" },
        { char: 'д', roman: 'd', example: 'да', sound: "o д itálico vira um g — continua sendo 'd'" },
        { char: 'г', roman: 'g', example: 'год', sound: "o г itálico vira um s invertido — continua sendo 'g'" },
      ],
    },
  ],
}

const greekPt: LanguageLetters = {
  intro:
    'O alfabeto grego — 24 letras. Várias letras do nosso alfabeto vieram daqui, então metade do trabalho já está feita.',
  sections: [
    {
      title: 'Vogais',
      note: 'O grego moderno tem só cinco sons de vogal; várias grafias os compartilham.',
      rows: [
        { char: 'α', roman: 'a', example: 'αγάπη', sound: "como o a de 'casa'" },
        { char: 'ε', roman: 'e', example: 'ένα', sound: "como o é de 'pé'" },
        { char: 'η', roman: 'h/i', example: 'ημέρα', sound: "como o i de 'ali'" },
        { char: 'ι', roman: 'i', example: 'ιδέα', sound: "como o i de 'ali'" },
        { char: 'ο', roman: 'o', example: 'όχι', sound: "como o ó de 'avó'" },
        { char: 'υ', roman: 'u/y', example: 'ύπνος', sound: "'i' — sim, também i" },
        { char: 'ω', roman: 'w', example: 'ώρα', sound: "'ó' — igual ao ο" },
      ],
    },
    {
      title: 'Consoantes',
      rows: [
        { char: 'β', roman: 'v/b', example: 'βιβλίο', sound: "como o v de 'vida' (não é b!)" },
        { char: 'γ', roman: 'g', example: 'γάλα', sound: "'g' gargarejado suave; antes de e/i soa como o i de 'ioga'" },
        { char: 'δ', roman: 'd', example: 'δέκα', sound: "o th sonoro do inglês 'this' — língua entre os dentes, com voz (não é d!)" },
        { char: 'ζ', roman: 'z', example: 'ζωή', sound: "como o z de 'zebra'" },
        { char: 'θ', roman: 'th', example: 'θάλασσα', sound: "o th surdo do inglês 'think' — língua entre os dentes, sem voz" },
        { char: 'κ', roman: 'k', example: 'καλά', sound: "como o c de 'casa'" },
        { char: 'λ', roman: 'l', example: 'λέξη', sound: "como o l de 'lata'" },
        { char: 'μ', roman: 'm', example: 'μητέρα', sound: "como o m de 'mapa'" },
        { char: 'ν', roman: 'n', example: 'νερό', sound: "como o n de 'não' (parece um v!)" },
        { char: 'ξ', roman: 'x', example: 'ξένος', sound: "'ks', como o x de 'táxi'" },
        { char: 'π', roman: 'p', example: 'πατέρας', sound: "como o p de 'pato'" },
        { char: 'ρ', roman: 'r', example: 'ρολόι', sound: "r de batida leve, como em 'caro' (parece um p!)" },
        { char: 'σ/ς', roman: 's', example: 'σπίτι', sound: "como o s de 'sapo'; ς só no fim da palavra" },
        { char: 'τ', roman: 't', example: 'τρία', sound: "como o t de 'tatu'" },
        { char: 'φ', roman: 'f', example: 'φίλος', sound: "como o f de 'faca'" },
        { char: 'χ', roman: 'ch', example: 'χέρι', sound: "raspado, como o rr carioca de 'carro'" },
        { char: 'ψ', roman: 'ps', example: 'ψωμί', sound: "'ps' como em 'psicologia' (com o p soando) — até no começo da palavra" },
      ],
    },
    {
      title: 'Pares comuns',
      note: 'Duas letras, um som — aprenda cada par como uma unidade.',
      rows: [
        { char: 'ου', roman: 'ou', example: 'ουρανός', sound: "como o u de 'tudo'" },
        { char: 'αι', roman: 'ai', example: 'παιδί', sound: "como o é de 'pé'" },
        { char: 'ει/οι', roman: 'ei/oi', example: 'είναι', sound: "como o i de 'ali'" },
        { char: 'μπ', roman: 'mp', example: 'μπανάνα', sound: "'b' no começo da palavra; 'mb' no meio" },
        { char: 'ντ', roman: 'nt', example: 'ντομάτα', sound: "'d' no começo da palavra; 'nd' no meio" },
        { char: 'γγ/γκ', roman: 'gg/gk', example: 'αγγλικά', sound: "'g' / 'ng-g'" },
      ],
    },
  ],
}

const arabicPt: LanguageLetters = {
  intro:
    'O abjad árabe — 28 letras, escritas da direita para a esquerda. As letras se ligam e mudam de forma conforme a posição; as vogais curtas em geral não se escrevem.',
  sections: [
    {
      title: 'Como as letras se juntam',
      note: 'O árabe é cursivo por regra: a maioria das letras tem quatro formas — isolada, inicial, medial, final — e se liga às vizinhas.',
      rows: [
        { char: 'م ح م د → محمد', roman: 'm-H-m-d', example: 'محمد', sound: 'as mesmas letras, ligadas: cada uma muda de forma conforme a posição' },
        { char: 'ب ـبـ ـب', roman: 'b', example: 'باب', sound: 'uma letra, três formas ligadas: inicial, medial, final' },
        { char: 'ا د ر ز و', roman: '(non-joiners)', example: 'دار', sound: 'seis letras nunca se ligam PARA A FRENTE — forçam um espaço no meio da palavra' },
        { char: 'ل + ا → لا', roman: 'laa', example: 'سلام', sound: 'lam + alif se fundem na ligatura especial lam-alif' },
      ],
    },
    {
      title: 'Vogais longas e semivogais',
      positions: true,
      rows: [
        { char: 'ا', roman: 'aa', example: 'باب', sound: "'a' longo, como o a de 'casa' segurado" },
        { char: 'و', roman: 'w/uu', example: 'نور', sound: "o u de 'água', ou o u longo de 'tudo'" },
        { char: 'ي', roman: 'y/ii', example: 'كبير', sound: "o i de 'ioga', ou o i longo de 'ali'" },
      ],
    },
    {
      title: 'As letras familiares',
      note: 'Cada letra nas quatro posições: isolada e ligada no início, no meio e no fim da palavra.',
      positions: true,
      rows: [
        { char: 'ب', roman: 'b', example: 'بيت', sound: "como o b de 'bola'" },
        { char: 'ت', roman: 't', example: 'تفاح', sound: "como o t de 'tatu'" },
        { char: 'ث', roman: 'th', example: 'ثلاثة', sound: "o th surdo do inglês 'think' — língua entre os dentes, sem voz" },
        { char: 'ج', roman: 'j', example: 'جمل', sound: "como dj — o j do inglês 'jam'" },
        { char: 'د', roman: 'd', example: 'دار', sound: "como o d de 'dado'" },
        { char: 'ذ', roman: 'dh', example: 'هذا', sound: "o th sonoro do inglês 'this' — língua entre os dentes, com voz" },
        { char: 'ر', roman: 'r', example: 'رجل', sound: 'r vibrante, como o rr do espanhol' },
        { char: 'ز', roman: 'z', example: 'زيت', sound: "como o z de 'zebra'" },
        { char: 'س', roman: 's', example: 'سلام', sound: "como o s de 'sapo'" },
        { char: 'ش', roman: 'sh', example: 'شمس', sound: "como o ch de 'chuva'" },
        { char: 'ف', roman: 'f', example: 'فيل', sound: "como o f de 'faca'" },
        { char: 'ك', roman: 'k', example: 'كتاب', sound: "como o c de 'casa'" },
        { char: 'ل', roman: 'l', example: 'ليل', sound: "como o l de 'lata'" },
        { char: 'م', roman: 'm', example: 'ماء', sound: "como o m de 'mapa'" },
        { char: 'ن', roman: 'n', example: 'نار', sound: "como o n de 'não'" },
        { char: 'ه', roman: 'h', example: 'هنا', sound: "h soprado, como o r inicial de 'rato' no Brasil" },
      ],
    },
    {
      title: 'Os sons novos',
      note: 'Produzidos mais fundo na garganta do que qualquer som do português — ouça e imite.',
      positions: true,
      rows: [
        { char: 'ح', roman: 'H / 7', example: 'حب', sound: "'h' soprado do fundo da garganta — como embaçar um espelho, com mais força" },
        { char: 'خ', roman: 'kh / 5', example: 'خبز', sound: "raspado, como o rr carioca de 'carro'" },
        { char: 'ع', roman: '3', example: 'عين', sound: 'uma vogal apertada na garganta — não existe em português; ouça com atenção' },
        { char: 'غ', roman: 'gh', example: 'غرب', sound: 'g gargarejado — um r francês' },
        { char: 'ق', roman: 'q', example: 'قلب', sound: "um c de 'casa' puxado para o fundo da boca" },
        { char: 'ء', roman: "2 / '", example: 'سؤال', sound: "oclusão glotal — o cortezinho de ar no meio do 'ã-ã' de negação" },
      ],
    },
    {
      title: 'As quatro enfáticas',
      note: 'Gêmeas pesadas de t/d/s/z — a língua se arqueia para trás e a palavra inteira escurece.',
      positions: true,
      rows: [
        { char: 'ص', roman: 'S', example: 'صباح', sound: "'s' pesado" },
        { char: 'ض', roman: 'D', example: 'ضوء', sound: "'d' pesado" },
        { char: 'ط', roman: 'T', example: 'طعام', sound: "'t' pesado" },
        { char: 'ظ', roman: 'Z', example: 'ظهر', sound: "'th/z' pesado" },
      ],
    },
    {
      title: 'Vogais curtas (harakat)',
      note: 'Sinais pequenos acima/abaixo da letra — em geral omitidos fora dos textos didáticos.',
      rows: [
        { char: 'ـَ', roman: 'a', example: 'فَتَحَ', sound: "'a' curto, aberto (fatha)" },
        { char: 'ـِ', roman: 'i', example: 'بِنت', sound: "'i' curto e relaxado (kasra)" },
        { char: 'ـُ', roman: 'u', example: 'كُتُب', sound: "'u' curto (damma)" },
        { char: 'ـّ', roman: '(double)', example: 'مُدَرِّس', sound: 'shadda — segure a consoante pelo dobro do tempo' },
      ],
    },
  ],
}

const hindiPt: LanguageLetters = {
  intro:
    'O devanágari — cada consoante carrega um «a» embutido; sinais de vogal (matras) o substituem. Os sons de destaque: letras retroflexas (língua curvada para trás) vs dentais (língua nos dentes), e pares aspirados com um sopro extra de ar.',
  sections: [
    {
      title: 'Como as letras se juntam',
      note: 'O devanágari monta sílabas: os sinais de vogal se prendem às consoantes, e o virama (्) solda consoantes em pilhas.',
      rows: [
        { char: 'क + ा → का', roman: 'k + aa', example: 'काम', sound: 'um sinal de vogal (matra) substitui o a embutido' },
        { char: 'क + ि → कि', roman: 'k + i', example: 'किताब', sound: 'a matra do i se escreve à ESQUERDA da consoante' },
        { char: 'स + ् + त → स्त', roman: 's+t', example: 'नमस्ते', sound: 'o virama apaga o a e funde o par em um só grupo' },
        { char: 'क + ् + ष → क्ष', roman: 'ksh', example: 'क्षमा', sound: 'alguns grupos ganham uma forma totalmente nova — aprenda os comuns de vista' },
        { char: 'र special', roman: 'r', example: 'कर्म / प्रेम', sound: 'o r vai ACIMA do grupo quando vem primeiro (कर्म) e vira um tracinho abaixo quando vem depois (प्रेम)' },
      ],
    },
    {
      title: 'Vogais independentes',
      note: 'Usadas no início da palavra; dentro dela viram matras (próxima seção).',
      rows: [
        { char: 'अ', roman: 'a', example: 'अब', sound: "'a' curto e abafado, como o a final átono de 'casa'" },
        { char: 'आ', roman: 'aa', example: 'आम', sound: "'a' longo, como o a de 'casa' segurado" },
        { char: 'इ', roman: 'i', example: 'इधर', sound: "'i' curto e relaxado" },
        { char: 'ई', roman: 'ii', example: 'ईद', sound: "'i' longo, como o i de 'ali'" },
        { char: 'उ', roman: 'u', example: 'उधर', sound: "'u' curto" },
        { char: 'ऊ', roman: 'uu', example: 'ऊपर', sound: "'u' longo, como o u de 'tudo'" },
        { char: 'ए', roman: 'e', example: 'एक', sound: "como o ê de 'você' (sem deslize)" },
        { char: 'ऐ', roman: 'ai', example: 'ऐनक', sound: "um 'é' bem aberto, puxado para o a (o a do inglês 'cat')" },
        { char: 'ओ', roman: 'o', example: 'ओर', sound: "como o ô de 'avô' (sem deslize)" },
        { char: 'औ', roman: 'au', example: 'औरत', sound: "como o ó de 'avó'" },
      ],
    },
    {
      title: 'As mesmas vogais como matras',
      note: 'क mostrado como portador. O अ embutido não precisa de sinal.',
      rows: [
        { char: 'का', roman: 'kaa', example: 'काम', sound: 'k + a longo' },
        { char: 'कि', roman: 'ki', example: 'किताब', sound: 'k + i curto (o sinal vai ANTES da letra)' },
        { char: 'की', roman: 'kii', example: 'की', sound: 'k + i longo' },
        { char: 'कु', roman: 'ku', example: 'कुछ', sound: 'k + u curto' },
        { char: 'कू', roman: 'kuu', example: 'कूद', sound: 'k + u longo' },
        { char: 'के', roman: 'ke', example: 'के', sound: 'k + ê' },
        { char: 'कै', roman: 'kai', example: 'कैसा', sound: 'k + esse é bem aberto' },
        { char: 'को', roman: 'ko', example: 'को', sound: 'k + ô' },
        { char: 'कौ', roman: 'kau', example: 'कौन', sound: 'k + ó' },
        { char: 'कं', roman: 'kaM', example: 'कंघी', sound: 'zumbido nasal depois da vogal (anusvara)' },
      ],
    },
    {
      title: 'Consoantes — os pares aspirados',
      note: 'O segundo de cada par acrescenta um sopro de ar (ponha a palma da mão à frente da boca — dá para sentir).',
      rows: [
        { char: 'क / ख', roman: 'k / kh', example: 'खाना', sound: "c de 'casa' simples, depois com sopro" },
        { char: 'ग / घ', roman: 'g / gh', example: 'घर', sound: "g de 'gato' simples, depois com sopro" },
        { char: 'च / छ', roman: 'ch / chh', example: 'छह', sound: "'tch' simples, depois com sopro" },
        { char: 'ज / झ', roman: 'j / jh', example: 'झील', sound: "'dj' simples, depois com sopro" },
        { char: 'प / फ', roman: 'p / ph', example: 'फल', sound: "'p' simples, depois com sopro" },
        { char: 'ब / भ', roman: 'b / bh', example: 'भाई', sound: "'b' simples, depois com sopro" },
      ],
    },
    {
      title: 'Retroflexas vs dentais — a grande divisão',
      note: 'Retroflexa: língua curvada para trás no céu da boca. Dental: língua encostada nos dentes. O t/d do português já é dental — a novidade para nós são as retroflexas.',
      rows: [
        { char: 'ट / ठ', roman: 'T / Th', example: 'टमाटर', sound: 't retroflexo (simples / +sopro)' },
        { char: 'ड / ढ', roman: 'D / Dh', example: 'डर', sound: 'd retroflexo (simples / +sopro)' },
        { char: 'ण', roman: 'N', example: 'बाण', sound: 'n retroflexo' },
        { char: 'त / थ', roman: 't / th', example: 'तीन', sound: "t dental — como o nosso t de 'tatu' (simples / +sopro)" },
        { char: 'द / ध', roman: 'd / dh', example: 'दो', sound: 'd dental, como o nosso (simples / +sopro)' },
        { char: 'न', roman: 'n', example: 'नाम', sound: "como o n de 'não'" },
        { char: 'ड़ / ढ़', roman: 'R / Rh', example: 'लड़का', sound: 'r de batida — a língua desce estalando da posição retroflexa' },
      ],
    },
    {
      title: 'O resto',
      rows: [
        { char: 'म', roman: 'm', example: 'माँ', sound: "como o m de 'mapa'" },
        { char: 'य', roman: 'y', example: 'यह', sound: "como o i de 'ioga'" },
        { char: 'र', roman: 'r', example: 'रात', sound: "r leve de batida, como em 'caro'" },
        { char: 'ल', roman: 'l', example: 'लाल', sound: "como o l de 'lata'" },
        { char: 'व', roman: 'v/w', example: 'वह', sound: "entre o v de 'vida' e o u de 'água'" },
        { char: 'श / ष', roman: 'sh / Sh', example: 'शहर', sound: "como o ch de 'chuva'" },
        { char: 'स', roman: 's', example: 'सात', sound: "como o s de 'sapo'" },
        { char: 'ह', roman: 'h', example: 'हाँ', sound: "h soprado, como o r inicial de 'rato' no Brasil" },
      ],
    },
    {
      title: 'Letras com nuqta (sons de empréstimo)',
      note: 'Um ponto sob a letra marca sons perso-árabes.',
      rows: [
        { char: 'ज़', roman: 'z', example: 'ज़रूर', sound: "como o z de 'zebra'" },
        { char: 'फ़', roman: 'f', example: 'फ़ोन', sound: "como o f de 'faca'" },
        { char: 'क़', roman: 'q', example: 'क़लम', sound: "'c' do fundo da boca" },
        { char: 'ख़ / ग़', roman: 'kh / gh', example: 'ख़बर', sound: 'rr raspado / g gargarejado' },
      ],
    },
  ],
}

const thaiPt: LanguageLetters = {
  intro:
    'A escrita tailandesa: 44 consoantes em três CLASSES (a classe + o sinal de tom decide o tom), vogais que se prendem em volta da consoante e nenhum espaço entre as palavras.',
  sections: [
    {
      title: 'Como as letras se juntam',
      note: 'As vogais envolvem a consoante — antes, depois, acima ou abaixo — e os sinais de tom empilham em cima.',
      rows: [
        { char: 'ก + า → กา', roman: 'k + aa', example: 'กาแฟ', sound: 'esta vogal vem depois da consoante' },
        { char: 'ก + ิ → กิ', roman: 'k + i', example: 'กิน', sound: 'esta vogal senta EM CIMA' },
        { char: 'ก + ุ → กุ', roman: 'k + u', example: 'กุ้ง', sound: 'esta vogal pendura EMBAIXO' },
        { char: 'เ + ก → เก', roman: 'k + e', example: 'เกาะ', sound: 'esta vogal se escreve ANTES da consoante, mas se diz depois' },
        { char: 'เ-ีย, เ-ือ', roman: 'ia, uea', example: 'เมีย', sound: 'vogais compostas cercam a consoante por dois ou três lados' },
        { char: 'ก่ ก้ ก๊ ก๋', roman: 'tones', example: 'ไม่', sound: 'quatro sinais de tom empilham acima; a classe da consoante decide o que significam' },
      ],
    },
    {
      title: 'Consoantes do dia a dia (classe média)',
      rows: [
        { char: 'ก', roman: 'g/k', example: 'ไก่', sound: "como o g de 'gato' (um k sem sopro)" },
        { char: 'จ', roman: 'j', example: 'จาน', sound: "'dj' bem seco" },
        { char: 'ด', roman: 'd', example: 'เด็ก', sound: "como o d de 'dado'" },
        { char: 'ต', roman: 'dt', example: 'ตา', sound: 'entre d e t — um t sem sopro' },
        { char: 'บ', roman: 'b', example: 'บ้าน', sound: "como o b de 'bola'" },
        { char: 'ป', roman: 'bp', example: 'ปลา', sound: 'entre b e p — um p sem sopro' },
        { char: 'อ', roman: '(silent)', example: 'อาหาร', sound: 'a consoante muda que carrega vogais sozinhas' },
      ],
    },
    {
      title: 'Consoantes sopradas (pares classe alta + baixa)',
      note: 'Mesmo som, classe diferente — a classe muda o TOM da sílaba.',
      rows: [
        { char: 'ข / ค', roman: 'kh', example: 'ขาว / ควาย', sound: "c de 'casa' + sopro (classe alta / classe baixa)" },
        { char: 'ถ / ท', roman: 'th', example: 'ถนน / ทำ', sound: "'t' + sopro (alta / baixa)" },
        { char: 'ผ / พ', roman: 'ph', example: 'ผม / พ่อ', sound: "'p' + sopro — nunca é f! (alta / baixa)" },
        { char: 'ฝ / ฟ', roman: 'f', example: 'ฝน / ไฟ', sound: "como o f de 'faca' (alta / baixa)" },
        { char: 'ส / ซ', roman: 's', example: 'สวย / ซ้าย', sound: "como o s de 'sapo' (alta / baixa)" },
        { char: 'ห / ฮ', roman: 'h', example: 'หก / ฮา', sound: "h soprado, como o r de 'rato' (alta / baixa); ห também eleva em silêncio a classe da letra seguinte" },
      ],
    },
    {
      title: 'Sonorantes e o resto',
      rows: [
        { char: 'ม', roman: 'm', example: 'แม่', sound: "como o m de 'mapa'" },
        { char: 'น / ณ', roman: 'n', example: 'น้ำ', sound: "como o n de 'não'" },
        { char: 'ง', roman: 'ng', example: 'งู', sound: "o n de fundo de boca de 'manga' — até no COMEÇO da palavra" },
        { char: 'ร', roman: 'r', example: 'รถ', sound: 'r vibrante (na fala corrente muitas vezes vira l)' },
        { char: 'ล', roman: 'l', example: 'ลิง', sound: "como o l de 'lata'" },
        { char: 'ว', roman: 'w', example: 'วัน', sound: "como o u de 'água'" },
        { char: 'ย / ญ', roman: 'y', example: 'ยา', sound: "como o i de 'ioga'" },
        { char: 'ช', roman: 'ch', example: 'ช้าง', sound: "'tch' + sopro" },
      ],
    },
    {
      title: 'Vogais centrais (mostradas em ก)',
      note: 'Curta vs longa muda o sentido — segure bem as longas.',
      rows: [
        { char: 'กะ / กา', roman: 'a / aa', example: 'มา', sound: "'a' curto / longo, como o a de 'casa' segurado" },
        { char: 'กิ / กี', roman: 'i / ii', example: 'มี', sound: "'i' curto / 'i' longo de 'ali'" },
        { char: 'กุ / กู', roman: 'u / uu', example: 'ดู', sound: "'u' curto / 'u' longo de 'tudo'" },
        { char: 'เกะ / เก', roman: 'e', example: 'เย็น', sound: "'é' de 'pé' / 'ê' longo de 'você'" },
        { char: 'โกะ / โก', roman: 'o', example: 'โต', sound: "'ô' curto / longo, como em 'avô'" },
        { char: 'ไก / ใก', roman: 'ai', example: 'ไป', sound: "como o ai de 'pai' — duas grafias, o mesmo som" },
        { char: 'เกา', roman: 'ao', example: 'เก้า', sound: "como o au de 'mau'" },
        { char: 'กือ', roman: 'ue', example: 'มือ', sound: "'u' com os lábios esticados — não existe em português" },
      ],
    },
    {
      title: 'Os cinco tons',
      note: 'A mesma sílaba, cinco sentidos. O tom vem da classe da consoante + sinal de tom + tipo de sílaba.',
      rows: [
        { char: 'มา (médio)', roman: 'maa', example: 'มา', sound: 'altura nivelada — vir' },
        { char: 'หม่า (baixo)', roman: 'màa', example: 'ไม่', sound: 'começa baixo, fica baixo' },
        { char: 'ม้า (alto… descendente)', roman: 'máa', example: 'ม้า', sound: 'tom alto — cavalo' },
        { char: 'หม้า (descendente)', roman: 'mâa', example: 'บ้าน', sound: 'cai do alto para o baixo' },
        { char: 'หมา (ascendente)', roman: 'mǎa', example: 'หมา', sound: 'desce e sobe — cachorro (cuidado com o par cavalo/cachorro!)' },
      ],
    },
  ],
}

const koreanPt: LanguageLetters = {
  intro:
    'O hangul — 24 letras básicas que se MONTAM em blocos silábicos. Inventado em 1443 para ser aprendido em uma manhã; as formas até desenham a boca fazendo o som.',
  sections: [
    {
      title: 'Como as letras se juntam',
      note: 'As letras empilham em blocos quadrados: consoante + vogal, mais uma consoante final opcional (받침) embaixo. 한국 são seis letras em dois blocos.',
      rows: [
        { char: 'ㅎ + ㅏ + ㄴ → 한', roman: 'h + a + n', example: '한국', sound: 'consoante à esquerda, vogal vertical à direita, letra final embaixo' },
        { char: 'ㄱ + ㅜ + ㄱ → 국', roman: 'g + u + k', example: '한국', sound: 'as vogais horizontais vão EMBAIXO da primeira consoante' },
        { char: 'ㅅ + ㅏ → 사', roman: 's + a', example: '사람', sound: 'sem letra final — só consoante + vogal' },
        { char: 'ㅇ + ㅜ → 우', roman: '(silent) + u', example: '우유', sound: 'ㅇ é um marcador mudo quando o bloco começa com vogal' },
        { char: 'ㅂ + ㅏ + ㅂ → 밥', roman: 'b + a + p', example: '밥', sound: 'o ㅂ final (받침) fecha a sílaba' },
        { char: '받침 rule', roman: 'finals', example: '있다', sound: 'só 7 sons podem fechar um bloco: k, n, t, l, m, p, ng — a grafia guarda a letra, a boca simplifica' },
      ],
    },
    {
      title: 'Consoantes simples',
      rows: [
        { char: 'ㄱ', roman: 'g/k', example: '가다', sound: "entre o g de 'gato' e o c de 'casa' — 'g' no começo da palavra" },
        { char: 'ㄴ', roman: 'n', example: '나', sound: "como o n de 'não'" },
        { char: 'ㄷ', roman: 'd/t', example: '돈', sound: "entre 'd' e 't'" },
        { char: 'ㄹ', roman: 'r/l', example: '물', sound: "r de batida entre vogais, como em 'caro'; 'l' no fim do bloco" },
        { char: 'ㅁ', roman: 'm', example: '몸', sound: "como o m de 'mapa'" },
        { char: 'ㅂ', roman: 'b/p', example: '밥', sound: "entre 'b' e 'p'" },
        { char: 'ㅅ', roman: 's', example: '사람', sound: "como o s de 'sapo'; ch de 'chuva' antes de ㅣ" },
        { char: 'ㅇ', roman: '-/ng', example: '강', sound: "mudo no início; no fim, o n de fundo de boca de 'manga'" },
        { char: 'ㅈ', roman: 'j', example: '집', sound: "entre 'dj' e 'tch'" },
        { char: 'ㅎ', roman: 'h', example: '하다', sound: "h soprado, como o r inicial de 'rato' no Brasil" },
      ],
    },
    {
      title: 'Consoantes aspiradas (com sopro de ar)',
      note: 'Cada uma é uma consoante simples com um traço a mais e um sopro a mais.',
      rows: [
        { char: 'ㅋ', roman: 'k', example: '코', sound: "c de 'casa' com sopro forte (ㄱ + ar)" },
        { char: 'ㅌ', roman: 't', example: '토요일', sound: "'t' com sopro forte (ㄷ + ar)" },
        { char: 'ㅍ', roman: 'p', example: '팔', sound: "'p' com sopro forte (ㅂ + ar)" },
        { char: 'ㅊ', roman: 'ch', example: '차', sound: "'tch' com sopro forte (ㅈ + ar)" },
      ],
    },
    {
      title: 'Consoantes tensas (dobradas, sem ar)',
      note: 'Com a garganta apertada e nenhum sopro — parta do nosso p/t/c, que já saem sem sopro, e aperte mais.',
      rows: [
        { char: 'ㄲ', roman: 'kk', example: '까만', sound: "um 'c' tenso, sem nenhum sopro" },
        { char: 'ㄸ', roman: 'tt', example: '딸', sound: "um 't' tenso, sem nenhum sopro" },
        { char: 'ㅃ', roman: 'pp', example: '빵', sound: "um 'p' tenso, sem nenhum sopro" },
        { char: 'ㅆ', roman: 'ss', example: '쌀', sound: "um 's' tenso" },
        { char: 'ㅉ', roman: 'jj', example: '짜다', sound: "um 'tch' tenso, sem nenhum sopro" },
      ],
    },
    {
      title: 'Vogais básicas',
      rows: [
        { char: 'ㅏ', roman: 'a', example: '아빠', sound: "como o a de 'casa'" },
        { char: 'ㅓ', roman: 'eo', example: '어머니', sound: "um 'ó' bem aberto, sem arredondar os lábios — entre o a e o ô" },
        { char: 'ㅗ', roman: 'o', example: '오늘', sound: "como o ô de 'avô' (lábios arredondados)" },
        { char: 'ㅜ', roman: 'u', example: '우리', sound: "como o u de 'tudo'" },
        { char: 'ㅡ', roman: 'eu', example: '그', sound: "'u' com os lábios ESTICADOS — diga 'u' sorrindo" },
        { char: 'ㅣ', roman: 'i', example: '이름', sound: "como o i de 'ali'" },
        { char: 'ㅐ', roman: 'ae', example: '개', sound: "como o é de 'pé' (igual a ㅔ na fala moderna)" },
        { char: 'ㅔ', roman: 'e', example: '세 시', sound: "como o é de 'pé'" },
      ],
    },
    {
      title: 'Vogais com y- e w-',
      note: 'Um traço extra acrescenta o deslize de i (y-); combinar duas vogais faz o w-.',
      rows: [
        { char: 'ㅑ ㅕ ㅛ ㅠ', roman: 'ya yeo yo yu', example: '야구, 여자', sound: 'as quatro vogais básicas com um i- na frente' },
        { char: 'ㅒ ㅖ', roman: 'yae ye', example: '예', sound: "'iê', como em 'fiel'" },
        { char: 'ㅘ ㅝ', roman: 'wa wo', example: '와요, 뭐', sound: "'ua' de 'quadro', 'uó' — u + ó emendados" },
        { char: 'ㅙ ㅞ ㅚ', roman: 'wae we oe', example: '왜, 회사', sound: "as três soam como o nosso 'ué' na fala moderna" },
        { char: 'ㅟ', roman: 'wi', example: '귀', sound: "'ui', como em 'uísque'" },
        { char: 'ㅢ', roman: 'ui', example: '의사', sound: "o 'u' esticado + 'i' emendados; na fala, muitas vezes só 'i' ou 'ê'" },
      ],
    },
  ],
}

export const LETTERS_PT: Record<string, LanguageLetters> = {
  es: spanishPt,
  fr: frenchPt,
  de: germanPt,
  it: italianPt,
  ca: catalanPt,
  pt: portuguesePt,
  ro: romanianPt,
  tr: turkishPt,
  sw: swahiliPt,
  yo: yorubaPt,
  ha: hausaPt,
  xh: xhosaPt,
  mi: maoriPt,
  jam: jamaicanPt,
  en: englishPt,
  nl: dutchPt,
  ru: russianPt,
  el: greekPt,
  ar: arabicPt,
  hi: hindiPt,
  th: thaiPt,
  ko: koreanPt,
}
