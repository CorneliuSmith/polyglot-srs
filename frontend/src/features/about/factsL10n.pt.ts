/**
 * Portuguese (pt) overlay for the "About this language" reference:
 * hand-authored translations of LANGUAGE_FACTS (all 27 courses) and of the
 * gloss/translation/note layer of LANGUAGE_SYNTAX. Course-language text
 * (sentence, words[].w, rtl) is copied verbatim from languageFacts.ts.
 * Register follows trPt in factsL10n.ts, reused verbatim here for 'tr'.
 */
import type { LanguageFacts, SyntaxExample } from './languageFacts'

const es: LanguageFacts = {
  tagline: 'Uma língua românica de alcance notável e ortografia honesta.',
  family: 'Indo-europeia › Itálica › Românica (ibero-românica)',
  speakers: '~485 milhões de falantes nativos — atrás apenas do mandarim.',
  whereSpoken: 'Espanha, quase toda a América Latina, Guiné Equatorial e amplamente pelos Estados Unidos.',
  writingSystem: 'Alfabeto latino, mais o ñ e os sinais á é í ó ú ü. Escrita da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto, mas flexível — as terminações dizem tanto que o sujeito costuma ser omitido.',
  history:
    'Nasceu do latim falado da Hispânia romana, tomando forma como castelhano nos reinos medievais do norte da Espanha. O império depois o levou através do Atlântico, onde hoje vive a maioria dos seus falantes.',
  unique: [
    'Os verbos fazem o trabalho pesado: uma só palavra marca pessoa, tempo e modo, e por isso os pronomes costumam ficar de fora.',
    'Todo substantivo é masculino ou feminino, e os adjetivos concordam com ele.',
    'Dois verbos para «ser»: ser (permanente) vs. estar (temporário ou localização).',
    'Os sinais invertidos ¿ e ¡ abrem perguntas e exclamações.',
  ],
}

const fr: LanguageFacts = {
  tagline: 'Uma língua românica em que muito se escreve mas pouco se pronuncia.',
  family: 'Indo-europeia › Itálica › Românica (galo-românica)',
  speakers: '~80 milhões de falantes nativos, ~300 milhões no total em cinco continentes.',
  whereSpoken: 'França, Bélgica, Suíça, Québec e boa parte da África Ocidental e Central.',
  writingSystem: 'Alfabeto latino com acentos (é è ê ë), a cedilha (ç) e ligaturas (œ). Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto, bastante rígida — o pronome sujeito não sai do lugar.',
  history:
    'Descende do latim vulgar da Gália, surgindo como a langue d’oïl do norte. Séculos de prestígio da corte e a Académie française moldaram o padrão arrumado de hoje.',
  unique: [
    'Muitas letras finais são mudas — mas reaparecem como liaisons antes de vogal.',
    'Vogais nasais (on, an, in) — próximas das do português, mas não idênticas.',
    'Os substantivos têm gênero, e artigos e adjetivos concordam.',
    'O vous formal vs. o tu familiar marca o registro social de cada «você».',
  ],
}

const de: LanguageFacts = {
  tagline: 'Uma língua germânica que guarda o verbo para o fim.',
  family: 'Indo-europeia › Germânica (germânica ocidental)',
  speakers: '~95 milhões de falantes nativos — a primeira língua mais falada da UE.',
  whereSpoken: 'Alemanha, Áustria, Suíça, Liechtenstein e bolsões na Bélgica, na Itália e além.',
  writingSystem: 'Alfabeto latino mais ä ö ü e ß. Os substantivos são sempre escritos com maiúscula. Da esquerda para a direita.',
  wordOrder: 'Verbo em segunda posição nas orações principais, no fim nas subordinadas — o famoso «verbo no fim».',
  history:
    'Surgiu de dialetos germânicos ocidentais remodelados pela mutação consonântica do alto-alemão. A tradução da Bíblia por Lutero fez muito para forjar um padrão escrito único.',
  unique: [
    'Quatro casos (nominativo, acusativo, dativo, genitivo) mudam artigos e terminações.',
    'Três gêneros — e der/die/das raramente seguem o sentido.',
    'As palavras se empilham em compostos longos (Handschuh = «sapato-de-mão» = luva).',
    'Os verbos separáveis se dividem: «ich stehe früh auf» (levanto-me cedo).',
  ],
}

const it: LanguageFacts = {
  tagline: 'A língua românica mais próxima do seu latim de origem.',
  family: 'Indo-europeia › Itálica › Românica (ítalo-dálmata)',
  speakers: '~65 milhões de falantes nativos.',
  whereSpoken: 'Itália, San Marino, Cidade do Vaticano e o Ticino suíço.',
  writingSystem: 'Alfabeto latino com acentos graves e agudos (à, é). Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto, flexível — o sujeito é muitas vezes omitido.',
  history:
    'O italiano padrão nasceu do toscano de Florença, elevado por Dante, Petrarca e Boccaccio, e só se tornou língua falada em todo o país depois da unificação nos anos 1860.',
  unique: [
    'As consoantes duplas se pronunciam longas e podem mudar o sentido (pala vs. palla).',
    'Gramaticalmente a mais conservadora das grandes línguas românicas — muito próxima do latim.',
    'Substantivos e adjetivos concordam em gênero e número.',
    'Entonação rica e musical, com vogais abertas e claras.',
  ],
}

const ca: LanguageFacts = {
  tagline: 'Uma língua românica que faz ponte entre a Espanha e a França.',
  family: 'Indo-europeia › Itálica › Românica (occitano-românica)',
  speakers: '~9 milhões de falantes nativos.',
  whereSpoken: 'Catalunha, Valência, Ilhas Baleares, Andorra (onde é a única língua oficial) e Alghero, na Sardenha.',
  writingSystem: 'Alfabeto latino com o ponto médio (l·l) e acentos. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto, flexível, com omissão do sujeito.',
  history:
    'Formou-se do latim vulgar e floresceu como língua literária e jurídica medieval. Reprimido sob Franco, foi revitalizado e é hoje central para a identidade catalã.',
  unique: [
    'Fica entre o espanhol e o francês — familiar aos dois, idêntico a nenhum.',
    'Pronomes átonos (em, et, es, hi, en) se prendem em volta do verbo.',
    'Vogal neutra (schwa) característica nos dialetos orientais.',
    'Uma língua literária e oficial completa, não um dialeto do espanhol.',
  ],
}

const pt: LanguageFacts = {
  tagline: 'Uma língua românica do mundo atlântico.',
  family: 'Indo-europeia › Itálica › Românica (ibero-românica)',
  speakers: '~230 milhões de falantes nativos — a maioria no Brasil.',
  whereSpoken: 'Brasil, Portugal, Angola, Moçambique, Cabo Verde e outras antigas colônias marítimas.',
  writingSystem: 'Alfabeto latino com ã õ, ç e acentos. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto, flexível, com omissão do sujeito.',
  history:
    'Nasceu do galego-português no noroeste da Península Ibérica e espalhou-se pelo mundo nas rotas marítimas de Portugal, dividindo-se em padrões europeu e brasileiro distintos.',
  unique: [
    'Vogais e ditongos nasais (pão, mãe, coração).',
    'Um infinitivo pessoal — o infinitivo pode receber terminações para cada pessoa.',
    'Um futuro do subjuntivo vivo, perdido na maioria das línguas românicas.',
    'As variedades europeia e brasileira diferem visivelmente no som e no ritmo.',
  ],
}

const ro: LanguageFacts = {
  tagline: 'A língua românica do Leste, moldada pelos vizinhos.',
  family: 'Indo-europeia › Itálica › Românica (românica oriental)',
  speakers: '~24 milhões de falantes nativos.',
  whereSpoken: 'Romênia e Moldávia.',
  writingSystem: 'Alfabeto latino com ă, â, î, ș, ț. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto, flexível graças à marcação de casos.',
  history:
    'Descende do latim da Dácia romana e evoluiu durante séculos isolado do resto do mundo românico, profundamente marcado pelos vizinhos eslavos e balcânicos.',
  unique: [
    'A única grande língua românica que conservou os casos gramaticais.',
    'O artigo definido se prende ao fim do substantivo: lup → lupul (o lobo).',
    'Manteve um gênero neutro ao lado do masculino e do feminino.',
    'Partilha traços balcânicos (como o artigo posposto) com vizinhos sem parentesco.',
  ],
}

// Reused verbatim from factsL10n.ts (trPt), the register reference.
const tr: LanguageFacts = {
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

const sw: LanguageFacts = {
  tagline: 'O grande elo da África Oriental, bantu de coração.',
  family: 'Nígero-congolesa › Atlântico-congolesa › Bantu',
  speakers: '~5 milhões de falantes nativos, mas mais de 80 milhões como segunda língua comum.',
  whereSpoken: 'Tanzânia, Quênia, Uganda, RDC e por toda a região dos Grandes Lagos africanos.',
  writingSystem: 'Alfabeto latino (historicamente também escrita árabe). Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto.',
  history:
    'Uma língua bantu da costa da África Oriental, moldada por mil anos de comércio no Índico — daí os muitos empréstimos árabes — e depois espalhada para o interior como língua franca.',
  unique: [
    'Os substantivos se dividem em ~15 classes; a classe comanda a concordância na frase inteira.',
    'Os verbos aglutinam sujeito, tempo, objeto e mais numa só palavra.',
    'Coisa rara numa língua bantu: não é tonal.',
    'Uma camada rica de vocabulário árabe (safari, kitabu, asante) assenta sobre a base bantu.',
  ],
}

const yo: LanguageFacts = {
  tagline: 'Uma língua da África Ocidental em que o tom carrega o sentido.',
  family: 'Nígero-congolesa › Atlântico-congolesa › Volta-Níger',
  speakers: '~45 milhões.',
  whereSpoken: 'Sudoeste da Nigéria, Benim e Togo — além de uma profunda diáspora nas Américas.',
  writingSystem: 'Alfabeto latino com pontos subscritos (ẹ, ọ, ṣ) e marcas de tom. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto.',
  history:
    'A língua das civilizações de Ifẹ̀ e Ọ̀yọ́, levada através do Atlântico pelo tráfico de escravizados e preservada nas tradições religiosas cubanas e brasileiras.',
  unique: [
    'Três tons (alto, médio, baixo) distinguem palavras de resto idênticas.',
    'Construções de verbos em série encadeiam vários verbos numa só oração.',
    'Letras com ponto subscrito marcam vogais e consoantes distintas.',
    'Uma rica tradição de provérbios entretecida na fala cotidiana.',
  ],
}

const ha: LanguageFacts = {
  tagline: 'Uma língua chádica e o idioma de comércio do Sahel.',
  family: 'Afro-asiática › Chádica',
  speakers: 'Mais de ~50 milhões, e língua franca para muitos mais.',
  whereSpoken: 'Norte da Nigéria e Níger, e por toda a África Ocidental e o Sahel.',
  writingSystem: 'Alfabeto latino (Boko) com letras de gancho (ɓ, ɗ, ƙ); também escrita em alfabeto árabe (Ajami). Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto.',
  history:
    'Uma língua chádica — prima distante do árabe e do hebraico — espalhada muito além da sua terra natal por séculos de comércio transaariano e erudição islâmica.',
  unique: [
    'Dois tons mais a duração das vogais moldam o sentido das palavras.',
    'Consoantes glotalizadas «de gancho»: ɓ, ɗ, ƙ.',
    'O gênero gramatical aparece no singular mas desaparece no plural.',
    'Um sistema de «graus» verbais codifica direção e conclusão.',
  ],
}

const xh: LanguageFacts = {
  tagline: 'Uma língua nguni famosa pelos seus cliques.',
  family: 'Nígero-congolesa › Atlântico-congolesa › Bantu (Nguni)',
  speakers: '~8 milhões de falantes nativos.',
  whereSpoken: 'África do Sul, sobretudo o Cabo Oriental — uma das suas 11 línguas oficiais.',
  writingSystem: 'Alfabeto latino; as letras c, x, q grafam três cliques diferentes. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto.',
  history:
    'Uma língua bantu do grupo nguni, aparentada de perto com o zulu. O contato com os povos khoisan lhe deu os cliques que a tornam inconfundível.',
  unique: [
    'Três consoantes de clique — dental (c), lateral (x) e palatal (q) — emprestadas do khoisan.',
    'Um sistema de classes nominais que costura a concordância pela frase.',
    'É tonal, embora o tom não seja escrito.',
    'Prefixos de concordância ligam cada palavra de volta à classe do substantivo.',
  ],
}

const mi: LanguageFacts = {
  tagline: 'A língua polinésia de Aotearoa, com o verbo primeiro.',
  family: 'Austronésia › Malaio-polinésia › Polinésia',
  speakers: '~150.000–190.000, em firme revitalização.',
  whereSpoken: 'Nova Zelândia (Aotearoa).',
  writingSystem: 'Alfabeto latino; os mácrons (ā, ē, ī, ō, ū) marcam vogais longas. Da esquerda para a direita.',
  wordOrder: 'Verbo–Sujeito–Objeto — o verbo vem primeiro.',
  history:
    'Uma língua polinésia oriental levada à Nova Zelândia por volta do século XIV. Empurrada à beira do desaparecimento no século XX, foi revitalizada pelos kōhanga reo («ninhos de língua») e pelo ensino por imersão.',
  unique: [
    'Frases com o verbo primeiro (VSO), raras entre as línguas daqui.',
    'Um sistema de sons pequeno: dez consoantes e cinco vogais (curtas e longas).',
    'Partículas pequenas, e não terminações, marcam tempo e função.',
    'Os mácrons distinguem palavras — keke (bolo) vs. kēkē (axila).',
  ],
}

const jam: LanguageFacts = {
  tagline: 'Um crioulo de léxico inglês com gramática da África Ocidental.',
  family: 'Crioulo de base inglesa (atlântico)',
  speakers: '~3 milhões, mais uma grande diáspora.',
  whereSpoken: 'Jamaica e comunidades jamaicanas pelo mundo.',
  writingSystem: 'Alfabeto latino — escrito tanto numa grafia baseada no inglês quanto no sistema fonético Cassidy/JLU. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto.',
  history:
    'Nasceu nas plantações da era colonial, onde africanos ocidentais escravizados construíram uma língua nova com o vocabulário do inglês e a gramática do acã, do igbo e de outras línguas.',
  unique: [
    'Os verbos não se conjugam — o tempo vem de partículas (mi did go, mi a go).',
    'Pronomes próprios: mi, yu, im, wi, unu, dem.',
    'A reduplicação intensifica (chaka-chaka = bagunçado).',
    'Palavras inglesas, mas uma gramática toda sua.',
  ],
}

const en: LanguageFacts = {
  tagline: 'Uma língua germânica que tomou emprestado de todo mundo.',
  family: 'Indo-europeia › Germânica (germânica ocidental)',
  speakers: '~380 milhões de falantes nativos, ~1,5 bilhão no total — a língua franca do mundo.',
  whereSpoken: 'Reino Unido, Irlanda, América do Norte, Austrália, Nova Zelândia e, como segunda língua, quase toda parte.',
  writingSystem: 'Alfabeto latino, 26 letras, sem diacríticos. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto, bastante rígida — a ordem das palavras faz o trabalho que os casos faziam.',
  history:
    'Começou como anglo-saxão (inglês antigo), foi remodelado pelos colonos nórdicos e depois por uma enxurrada de francês normando após 1066, e espalhou-se pelo mundo com o Império Britânico e a influência americana.',
  unique: [
    'Um vocabulário enorme — um núcleo germânico coberto por camadas de latim, francês e grego.',
    'Pouquíssima flexão: os substantivos mal mudam, e não há gênero gramatical.',
    'Ortografia notoriamente irregular, fóssil de pronúncias antigas.',
    'Os phrasal verbs (give up, put off, run into) carregam sentido idiomático.',
  ],
}

const nl: LanguageFacts = {
  tagline: 'A língua germânica ocidental entre o inglês e o alemão.',
  family: 'Indo-europeia › Germânica (germânica ocidental)',
  speakers: '~25 milhões de falantes nativos.',
  whereSpoken: 'Países Baixos, Bélgica (Flandres), Suriname e o Caribe Neerlandês.',
  writingSystem: 'Alfabeto latino; o dígrafo «ij» se comporta como uma letra só. Da esquerda para a direita.',
  wordOrder: 'Verbo em segunda posição nas orações principais, no fim nas subordinadas — como no alemão.',
  history:
    'Uma língua baixo-frâncica que nunca passou pela mutação consonântica do alemão, o que a deixou, na gramática e no léxico, a meio caminho entre o inglês e o alemão.',
  unique: [
    'A ordem «verbo em segundo lugar» manda os verbos para o fim das subordinadas.',
    'Dois gêneros — comum (de) e neutro (het).',
    'Um «g» gutural famoso.',
    'Diminutivos em -je estão por toda parte e suavizam o tom.',
  ],
}

const ru: LanguageFacts = {
  tagline: 'Uma língua eslava de casos e aspecto verbal.',
  family: 'Indo-europeia › Balto-eslava › Eslava oriental',
  speakers: '~150 milhões de falantes nativos, e muito falada como segunda língua.',
  whereSpoken: 'Rússia e boa parte da antiga União Soviética.',
  writingSystem: 'Alfabeto cirílico, adaptado do grego. Da esquerda para a direita.',
  wordOrder: 'Oficialmente Sujeito–Verbo–Objeto, mas a ordem é muito livre — os casos mostram quem faz o quê.',
  history:
    'Uma língua eslava oriental escrita em cirílico desde a cristianização da Rus, fortemente moldada pelo eslavo eclesiástico antigo e padronizada sobre o dialeto de Moscou.',
  unique: [
    'Seis casos remodelam substantivos, adjetivos e pronomes.',
    'Cada verbo vem num par de aspecto — imperfectivo (processo) vs. perfectivo (resultado).',
    'Não há palavras para «um» ou «o».',
    'Uma distinção entre consoantes duras e moles (palatalização) atravessa todo o sistema de sons.',
  ],
}

const el: LanguageFacts = {
  tagline: 'Uma língua com 3.400 anos de profundidade, num ramo só seu.',
  family: 'Indo-europeia › Helênica (um ramo próprio)',
  speakers: '~13 milhões de falantes nativos.',
  whereSpoken: 'Grécia e Chipre.',
  writingSystem: 'O alfabeto grego — ancestral tanto do latino quanto do cirílico. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto, flexível graças às terminações de caso.',
  history:
    'A mais antiga língua indo-europeia registrada ainda falada, com um registro escrito contínuo do grego micênico, passando pelo antigo e pelo koiné, até hoje.',
  unique: [
    'Um alfabeto próprio, do qual descendem o latino e o cirílico.',
    'Quatro casos e três gêneros.',
    'Uma única raiz grega sustenta uma parcela enorme do vocabulário científico.',
    'O acento de intensidade moderno substituiu o antigo acento tonal.',
  ],
}

const ar: LanguageFacts = {
  tagline: 'Uma língua semítica construída de raízes de três letras.',
  family: 'Afro-asiática › Semítica',
  speakers: '~310 milhões de falantes nativos nas suas muitas variedades.',
  whereSpoken: 'Oriente Médio e Norte da África, e liturgicamente por todo o mundo muçulmano.',
  writingSystem: 'A escrita árabe, da direita para a esquerda e ligada em cursivo.',
  wordOrder: 'Verbo–Sujeito–Objeto na língua clássica; muitos dialetos preferem Sujeito–Verbo–Objeto.',
  history:
    'Uma língua semítica cuja forma clássica foi fixada pelo Alcorão. Hoje um padrão formal (o árabe moderno padrão) é compartilhado por toda a região, enquanto cada um fala um dialeto local — situação chamada diglossia.',
  unique: [
    'As palavras se constroem de raízes de três consoantes: k-t-b dá kitāb (livro), kātib (escritor), maktab (escritório).',
    'Escrita da direita para a esquerda, com letras que mudam de forma conforme a posição.',
    'Um número dual, distinto do singular e do plural.',
    'Consoantes enfáticas e faríngeas sem equivalente em português.',
  ],
}

const hi: LanguageFacts = {
  tagline: 'Uma língua indo-ariana que deixa o verbo para o fim.',
  family: 'Indo-europeia › Indo-iraniana › Indo-ariana',
  speakers: '~340 milhões de falantes nativos (a forma falada é quase idêntica à do urdu).',
  whereSpoken: 'Norte e centro da Índia.',
  writingSystem: 'O abugida devanágari — cada consoante carrega uma vogal inerente. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Objeto–Verbo.',
  history:
    'Descende do sânscrito através dos prácritos e absorveu vocabulário persa e árabe sob os mogóis — o registro falado compartilhado com o urdu é muitas vezes chamado hindustâni.',
  unique: [
    'Posposições em vez de preposições («para a casa» → «casa-para»).',
    'Ergatividade cindida: a marca ne aparece no sujeito dos transitivos no passado.',
    'Os verbos concordam em gênero, então as frases mudam conforme quem fala ou age.',
    'Três níveis de «você» (tū, tum, āp) afinam a polidez.',
  ],
}

const th: LanguageFacts = {
  tagline: 'Uma língua tonal e isolante escrita sem espaços.',
  family: 'Kra-Dai › Tai',
  speakers: '~60 milhões de falantes nativos.',
  whereSpoken: 'Tailândia.',
  writingSystem: 'O abugida tailandês — um alfabeto com marcas de tom e sem espaços entre as palavras. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto.',
  history:
    'Uma língua tai cujos falantes migraram para o sul a partir do que hoje é o sul da China, acumulando vocabulário páli, sânscrito e khmer; sua escrita descende da khmer.',
  unique: [
    'Cinco tons — a mesma sílaba significa cinco coisas diferentes.',
    'Isolante: as palavras nunca mudam de forma; a gramática corre por conta da ordem e das partículas.',
    'Contar exige um classificador para o tipo de coisa contada.',
    'Partículas de polidez (khráp para homens, khâ para mulheres) fecham as frases.',
  ],
}

const ko: LanguageFacts = {
  tagline: 'Uma língua isolada com um alfabeto de desenho científico.',
  family: 'Coreânica (uma língua isolada)',
  speakers: '~80 milhões de falantes nativos.',
  whereSpoken: 'Coreia do Sul e Coreia do Norte, e uma ampla diáspora.',
  writingSystem: 'O hangul — um alfabeto featural cujas letras se agrupam em blocos silábicos. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Objeto–Verbo.',
  history:
    'O coreano está sozinho, sem parentes comprovados. Longamente escrito em caracteres chineses, ganhou o hangul — encomendado pelo rei Sejong em 1443 — uma escrita deliberadamente desenhada para ser fácil de aprender.',
  unique: [
    'As letras do hangul têm formas que refletem como a boca produz cada som.',
    'Elaborados níveis honoríficos e de fala remodelam os verbos conforme o contexto social.',
    'Aglutinante: partículas e terminações se prendem para marcar função e nuance.',
    'Um marcador de tópico (은/는) destaca aquilo de que a frase trata.',
  ],
}

const he: LanguageFacts = {
  tagline: 'Uma língua semítica ressuscitada da página para a fala cotidiana.',
  family: 'Afro-asiática › Semítica (semítica do noroeste, cananeia)',
  speakers: '~9 milhões de falantes nativos, quase todos em Israel.',
  whereSpoken: 'Israel, e comunidades judaicas pelo mundo (liturgicamente desde a Antiguidade).',
  writingSystem: 'O abjad hebraico, escrito da direita para a esquerda. As vogais normalmente não se marcam; os pontos de niqqud as mostram em textos didáticos, poesia e livros de oração.',
  wordOrder: 'Sujeito–Verbo–Objeto hoje (o hebraico bíblico preferia Verbo–Sujeito–Objeto).',
  history:
    'A língua cananeia da Bíblia hebraica sobreviveu como língua da lei, da liturgia e da erudição judaicas por quase dois milênios depois de deixar de ser o idioma cotidiano de alguém. Revivida como vernáculo falado a partir do fim do século XIX, tornou-se a língua oficial de Israel — um dos únicos renascimentos linguísticos completos e bem-sucedidos da história.',
  unique: [
    'Morfologia de raiz e padrão: três consoantes carregam o sentido central, e o padrão da palavra a molda — k-t-b dá katav (ele escreveu) e mikhtav (carta).',
    'A escrita corrente não traz vogal nenhuma — o leitor fluente as supre pelo contexto.',
    'Os verbos marcam gênero além de pessoa e número, até no presente.',
    'Uma língua revivida: um hiato real separa o hebraico bíblico antigo do hebraico moderno vivo de hoje.',
  ],
}

const la: LanguageFacts = {
  tagline: 'A língua clássica de que toda língua românica nasceu.',
  family: 'Indo-europeia › Itálica',
  speakers: 'Sem falantes nativos hoje — estudada no mundo todo e ainda usada na liturgia.',
  whereSpoken:
    'Nenhuma comunidade viva; conserva status cerimonial e oficial na Cidade do Vaticano e na liturgia da Igreja Católica.',
  writingSystem: 'O alfabeto latino — o ancestral direto do que o português usa. Da esquerda para a direita.',
  wordOrder:
    'Flexível: as terminações de caso marcam a função gramatical de cada palavra, então a ordem fica livre para a ênfase, em vez de fixada pela gramática.',
  history:
    'A língua da Roma antiga espalhou-se pelo Mediterrâneo e pela Europa Ocidental com o Império Romano e depois evoluiu localmente para as línguas românicas — espanhol, francês, italiano, português, romeno e mais — enquanto seguia como língua da erudição medieval, da Igreja e da ciência por séculos após a queda de Roma.',
  unique: [
    'Os substantivos se declinam por casos (nominativo, genitivo, dativo, acusativo, ablativo e um vocativo residual) que marcam sua função na frase.',
    'Nenhum artigo: puella sozinha pode significar «menina», «uma menina» ou «a menina».',
    'Os verbos se conjugam em pessoa, número, tempo, modo e voz, muitas vezes dispensando o pronome.',
    'O ancestral direto das línguas românicas — muito do seu vocabulário e da sua gramática sobrevive, transformado, no espanhol, no francês, no italiano, no português e no romeno.',
  ],
}

const fa: LanguageFacts = {
  tagline: 'Uma língua indo-europeia escrita numa escrita semítica emprestada.',
  family: 'Indo-europeia › Indo-iraniana (irânica ocidental)',
  speakers: '~70 milhões de falantes nativos, mais os falantes do dári e do tadjique, intimamente aparentados.',
  whereSpoken: 'Irã (farsi/persa), Afeganistão (dári) e Tadjiquistão (tadjique).',
  writingSystem: 'Uma escrita árabe modificada, da direita para a esquerda; as vogais curtas em geral não se escrevem, como no árabe.',
  wordOrder: 'Sujeito–Objeto–Verbo — ao contrário da ordem com verbo primeiro do árabe.',
  history:
    'Uma língua irânica descendente do persa antigo, a língua do Império Aquemênida, através do persa médio (pahlavi). Depois da conquista islâmica adotou a escrita árabe e absorveu um grande vocabulário árabe, mantendo porém a sua própria gramática indo-europeia — geneticamente nada tem a ver com o árabe, apesar do alfabeto compartilhado.',
  unique: [
    'Gramática indo-europeia vestindo uma escrita derivada do árabe — as duas línguas não são aparentadas, diga o que disser o alfabeto.',
    'Sem gênero gramatical e sem sistema de casos — morfologia invulgarmente regular para uma língua indo-europeia.',
    'O ezāfe: um -e átono, geralmente não escrito, que liga um substantivo ao que o segue — um adjetivo, um possuidor, outro substantivo.',
    'O verbo vem por último, e «ser» é muitas vezes um sufixo leve fundido ao predicado, e não uma palavra à parte.',
  ],
}

const id: LanguageFacts = {
  tagline: 'Uma língua nacional escolhida de propósito para pertencer a todos.',
  family: 'Austronésia › Malaio-polinésia (Maláica)',
  speakers: '~270 milhões de falantes na Indonésia, a maioria como segunda língua muito fluente.',
  whereSpoken: 'Indonésia — sua língua nacional e oficial num arquipélago de centenas de línguas locais.',
  writingSystem: 'O alfabeto latino, com grafia fonética e sem diacríticos no uso padrão. Da esquerda para a direita.',
  wordOrder: 'Sujeito–Verbo–Objeto.',
  history:
    'Uma forma padronizada do malaio, adotada como língua nacional unificadora da Indonésia na independência justamente por não ser a língua materna étnica dominante de ninguém — um ato deliberado de planejamento linguístico, e um dos mais bem-sucedidos da história, num país de centenas de línguas locais.',
  unique: [
    'Nenhuma conjugação verbal — uma só forma cobre toda pessoa, número e tempo; palavras à parte como sudah («já») e akan («vai») carregam o tempo.',
    'O plural muitas vezes se faz simplesmente dobrando a palavra: buku (livro) → buku-buku (livros).',
    'Camadas de prefixos e sufixos remodelam o sentido e a função de uma raiz: ajar (ensinar) → belajar (estudar) → mengajar (dar aula) → pelajaran (lição).',
    'Sem gênero gramatical, sem artigos, e pronomes que não mudam de forma entre sujeito e objeto.',
  ],
}

const tl: LanguageFacts = {
  tagline: 'Uma língua austronésia que põe o verbo primeiro.',
  family: 'Austronésia › Malaio-polinésia (Filipina)',
  speakers: '~28 milhões de falantes nativos; entendida, como filipino, pela maioria dos 110 milhões de habitantes das Filipinas.',
  whereSpoken: 'As Filipinas, com centro em Manila e Luzon — em todo o país como filipino, uma das duas línguas oficiais.',
  writingSystem: 'O alfabeto latino, com grafia fonética. Da esquerda para a direita. (Antes da colonização espanhola, escrevia-se no silabário baybayin.)',
  wordOrder: 'Verbo no início — o predicado abre a frase, antes do agente e do que sofre a ação.',
  history:
    'Uma língua austronésia das ilhas Filipinas, tornou-se a base do filipino, a língua nacional, na independência — uma das duas línguas oficiais ao lado do inglês, ensinada em todo o país junto a dezenas das outras línguas vivas do arquipélago.',
  unique: [
    'Frases com o verbo primeiro: o verbo costuma abrir a oração, com partículas pequenas (ang, ng, sa) marcando quem fez o quê a quê.',
    'Um sistema de «foco»: o afixo do verbo muda conforme o sujeito seja o agente, a coisa afetada, o lugar ou outra coisa — marca registrada das línguas filipinas.',
    'Reduplicação extensa, como no indonésio: araw (dia) → araw-araw (todo dia).',
    'Séculos de empréstimos do espanhol e, mais recentemente, do inglês convivem com o seu núcleo austronésio nativo.',
  ],
}

export const FACTS_PT: Record<string, LanguageFacts> = {
  es, fr, de, it, ca, pt, ro, tr, sw, yo, ha, xh, mi, jam, en, nl, ru, el, ar, hi, th, ko,
  he, la, fa, id, tl,
}

export const SYNTAX_PT: Record<string, SyntaxExample[]> = {
  es: [
    {
      sentence: 'El niño come una manzana.',
      words: [
        { w: 'El', g: 'o' }, { w: 'niño', g: 'menino' }, { w: 'come', g: 'come' },
        { w: 'una', g: 'uma' }, { w: 'manzana', g: 'maçã' },
      ],
      translation: 'O menino come uma maçã.',
      note: 'Sujeito–Verbo–Objeto; o artigo concorda com o substantivo.',
    },
    {
      sentence: '¿Hablas español?',
      words: [{ w: '¿Hablas', g: '(tu)-falas' }, { w: 'español?', g: 'espanhol' }],
      translation: 'Você fala espanhol?',
      note: 'Nenhuma palavra para «você» — a terminação -as já o diz (sujeito omitido).',
    },
  ],
  fr: [
    {
      sentence: 'Le garçon mange une pomme.',
      words: [
        { w: 'Le', g: 'o' }, { w: 'garçon', g: 'menino' }, { w: 'mange', g: 'come' },
        { w: 'une', g: 'uma' }, { w: 'pomme', g: 'maçã' },
      ],
      translation: 'O menino come uma maçã.',
    },
    {
      sentence: 'Je ne mange pas de viande.',
      words: [
        { w: 'Je', g: 'eu' }, { w: 'ne', g: '(não)' }, { w: 'mange', g: 'como' },
        { w: 'pas', g: '(não)' }, { w: 'de', g: 'de' }, { w: 'viande', g: 'carne' },
      ],
      translation: 'Eu não como carne.',
      note: 'A negação envolve o verbo em duas partes: ne … pas.',
    },
  ],
  de: [
    {
      sentence: 'Heute esse ich einen Apfel.',
      words: [
        { w: 'Heute', g: 'hoje' }, { w: 'esse', g: 'como' }, { w: 'ich', g: 'eu' },
        { w: 'einen', g: 'uma' }, { w: 'Apfel', g: 'maçã' },
      ],
      translation: 'Hoje eu como uma maçã.',
      note: 'O verbo «esse» fica em SEGUNDO lugar, empurrando o sujeito «ich» para depois dele.',
    },
    {
      sentence: 'Ich weiß, dass er heute kommt.',
      words: [
        { w: 'Ich', g: 'eu' }, { w: 'weiß', g: 'sei' }, { w: 'dass', g: 'que' },
        { w: 'er', g: 'ele' }, { w: 'heute', g: 'hoje' }, { w: 'kommt', g: 'vem' },
      ],
      translation: 'Eu sei que ele vem hoje.',
      note: 'Na oração subordinada o verbo «kommt» salta para o fim.',
    },
  ],
  it: [
    {
      sentence: 'Il ragazzo mangia una mela.',
      words: [
        { w: 'Il', g: 'o' }, { w: 'ragazzo', g: 'menino' }, { w: 'mangia', g: 'come' },
        { w: 'una', g: 'uma' }, { w: 'mela', g: 'maçã' },
      ],
      translation: 'O menino come uma maçã.',
    },
    {
      sentence: 'Lo vedo.',
      words: [{ w: 'Lo', g: 'o-(ele)' }, { w: 'vedo', g: '(eu)-vejo' }],
      translation: 'Eu o vejo.',
      note: 'O pronome objeto «lo» vem antes do verbo; o sujeito é omitido.',
    },
  ],
  ca: [
    {
      sentence: 'El nen menja una poma.',
      words: [
        { w: 'El', g: 'o' }, { w: 'nen', g: 'menino' }, { w: 'menja', g: 'come' },
        { w: 'una', g: 'uma' }, { w: 'poma', g: 'maçã' },
      ],
      translation: 'O menino come uma maçã.',
    },
    {
      sentence: 'No en tinc.',
      words: [{ w: 'No', g: '(não)' }, { w: 'en', g: 'disso' }, { w: 'tinc', g: '(eu)-tenho' }],
      translation: 'Não tenho nenhum.',
      note: 'O pronome átono «en» substitui «disso» e se agrupa em volta do verbo.',
    },
  ],
  pt: [
    {
      sentence: 'O menino come uma maçã.',
      words: [
        { w: 'O', g: 'o' }, { w: 'menino', g: 'menino' }, { w: 'come', g: 'come' },
        { w: 'uma', g: 'uma' }, { w: 'maçã', g: 'maçã' },
      ],
      translation: 'O menino come uma maçã.',
    },
    {
      sentence: 'É importante estudarmos.',
      words: [
        { w: 'É', g: '(isso)-é' }, { w: 'importante', g: 'importante' },
        { w: 'estudarmos', g: '(nós)-estudarmos' },
      ],
      translation: 'É importante estudarmos.',
      note: 'O infinitivo recebe a terminação pessoal -mos — o infinitivo pessoal, exclusivo do português.',
    },
  ],
  ro: [
    {
      sentence: 'Băiatul mănâncă un măr.',
      words: [
        { w: 'Băiatul', g: 'menino-o' }, { w: 'mănâncă', g: 'come' },
        { w: 'un', g: 'uma' }, { w: 'măr', g: 'maçã' },
      ],
      translation: 'O menino come uma maçã.',
      note: '«Băiatul» = «menino-o»: o artigo -ul está colado ao fim do substantivo.',
    },
    {
      sentence: 'Cartea este pe masă.',
      words: [
        { w: 'Cartea', g: 'livro-o' }, { w: 'este', g: 'está' }, { w: 'pe', g: 'sobre' },
        { w: 'masă', g: 'mesa' },
      ],
      translation: 'O livro está sobre a mesa.',
      note: 'De novo o artigo viaja no fim: «Cartea» = «livro-o».',
    },
  ],
  tr: [
    {
      sentence: 'Çocuk elmayı yedi.',
      words: [
        { w: 'Çocuk', g: 'criança' }, { w: 'elmayı', g: 'maçã-(objeto)' },
        { w: 'yedi', g: 'comeu' },
      ],
      translation: 'A criança comeu a maçã.',
      note: 'Verbo no fim (SOV); a terminação -yı marca «maçã» como objeto definido.',
    },
    {
      sentence: 'Evlerimizde.',
      words: [
        { w: 'Ev', g: 'casa' }, { w: '-ler', g: '(plural)' },
        { w: '-imiz', g: 'nossas' }, { w: '-de', g: 'em' },
      ],
      translation: 'Nas nossas casas.',
      note: 'Uma palavra = quatro palavras em português, construída empilhando sufixos (aglutinação).',
    },
  ],
  sw: [
    {
      sentence: 'Mtoto anasoma kitabu.',
      words: [
        { w: 'Mtoto', g: 'criança' }, { w: 'anasoma', g: 'ele/ela-está-lendo' },
        { w: 'kitabu', g: 'livro' },
      ],
      translation: 'A criança está lendo um livro.',
      note: '«a-na-soma» funde sujeito + tempo + verbo numa só palavra.',
    },
    {
      sentence: 'Vitabu vyangu viwili.',
      words: [
        { w: 'Vitabu', g: 'livros' }, { w: 'vyangu', g: 'meus' }, { w: 'viwili', g: 'dois' },
      ],
      translation: 'meus dois livros',
      note: 'O marcador de classe vi- se repete em cada palavra que concorda com «livros».',
    },
  ],
  yo: [
    {
      sentence: 'Adé ra bàtà.',
      words: [{ w: 'Adé', g: 'Ade' }, { w: 'ra', g: 'comprou' }, { w: 'bàtà', g: 'sapatos' }],
      translation: 'Ade comprou sapatos.',
      note: 'A ordem é um SVO fixo; o tom (e não terminações) faz o trabalho gramatical.',
    },
    {
      sentence: 'Ó mú ìwé wá.',
      words: [
        { w: 'Ó', g: 'ele' }, { w: 'mú', g: 'pegou' }, { w: 'ìwé', g: 'livro' },
        { w: 'wá', g: 'veio' },
      ],
      translation: 'Ele trouxe o livro.',
      note: 'Dois verbos seguidos (mú … wá, «pegar … vir») juntos significam «trazer» — um verbo em série.',
    },
  ],
  ha: [
    {
      sentence: 'Yaro ya sayi doya.',
      words: [
        { w: 'Yaro', g: 'menino' }, { w: 'ya', g: 'ele-(fez)' }, { w: 'sayi', g: 'comprar' },
        { w: 'doya', g: 'inhame' },
      ],
      translation: 'O menino comprou um inhame.',
      note: '«ya» carrega «ele» + ação concluída, logo antes do verbo.',
    },
    {
      sentence: 'Yarinya ta tafi.',
      words: [
        { w: 'Yarinya', g: 'menina' }, { w: 'ta', g: 'ela-(fez)' }, { w: 'tafi', g: 'ir' },
      ],
      translation: 'A menina foi.',
      note: '«ta» marca sujeito feminino; «ya» seria masculino.',
    },
  ],
  xh: [
    {
      sentence: 'Umntwana ufunda incwadi.',
      words: [
        { w: 'Umntwana', g: 'criança' }, { w: 'ufunda', g: 'ele/ela-lê' },
        { w: 'incwadi', g: 'livro' },
      ],
      translation: 'A criança lê um livro.',
      note: 'Prefixos de classe nominal (um-, in-) costuram a concordância pela frase.',
    },
    {
      sentence: 'Abantwana bafunda.',
      words: [{ w: 'Abantwana', g: 'crianças' }, { w: 'bafunda', g: 'elas-leem' }],
      translation: 'As crianças leem.',
      note: 'Prefixo plural aba- no substantivo, ecoado por ba- no verbo.',
    },
  ],
  mi: [
    {
      sentence: 'Kei te kai te tamaiti i te āporo.',
      words: [
        { w: 'Kei te kai', g: 'está-comendo' }, { w: 'te', g: 'a' },
        { w: 'tamaiti', g: 'criança' }, { w: 'i te', g: '(objeto) a' },
        { w: 'āporo', g: 'maçã' },
      ],
      translation: 'A criança está comendo a maçã.',
      note: 'Verbo PRIMEIRO (VSO); a partícula «i» marca o objeto.',
    },
    {
      sentence: 'He tangata ia.',
      words: [{ w: 'He', g: 'uma' }, { w: 'tangata', g: 'pessoa' }, { w: 'ia', g: 'ele' }],
      translation: 'Ele é uma pessoa.',
      note: 'Sem verbo «ser» — as palavras simplesmente ficam lado a lado.',
    },
  ],
  jam: [
    {
      sentence: 'Mi a nyam di food.',
      words: [
        { w: 'Mi', g: 'eu' }, { w: 'a', g: '(em-curso)' }, { w: 'nyam', g: 'comer' },
        { w: 'di', g: 'a' }, { w: 'food', g: 'comida' },
      ],
      translation: 'Estou comendo a comida.',
      note: '«a» é uma partícula de ação em curso — o verbo em si nunca muda.',
    },
    {
      sentence: 'Mi did nyam di food.',
      words: [
        { w: 'Mi', g: 'eu' }, { w: 'did', g: '(passado)' }, { w: 'nyam', g: 'comer' },
        { w: 'di', g: 'a' }, { w: 'food', g: 'comida' },
      ],
      translation: 'Comi a comida.',
      note: '«did» põe a frase no passado — troca-se a partícula, e o verbo «nyam» não se move.',
    },
  ],
  en: [
    {
      sentence: 'The dog chased the cat.',
      words: [
        { w: 'The', g: 'o' }, { w: 'dog', g: 'cachorro' }, { w: 'chased', g: 'perseguiu' },
        { w: 'the', g: 'o' }, { w: 'cat', g: 'gato' },
      ],
      translation: 'O cachorro perseguiu o gato.',
      note: 'Troque os substantivos e o sentido se inverte — só a ordem marca quem fez o quê.',
    },
    {
      sentence: 'She looked after the kids.',
      words: [
        { w: 'She', g: 'ela' }, { w: 'looked', g: 'olhou' }, { w: 'after', g: 'após' },
        { w: 'the', g: 'as' }, { w: 'kids', g: 'crianças' },
      ],
      translation: 'Ela cuidou das crianças.',
      note: '«look after» = cuidar de — um phrasal verb cujas partes somam um sentido novo.',
    },
  ],
  nl: [
    {
      sentence: 'Vandaag koop ik brood.',
      words: [
        { w: 'Vandaag', g: 'hoje' }, { w: 'koop', g: 'compro' }, { w: 'ik', g: 'eu' },
        { w: 'brood', g: 'pão' },
      ],
      translation: 'Hoje eu compro pão.',
      note: 'Verbo em segundo lugar, como no alemão: «koop» vem antes do sujeito «ik».',
    },
    {
      sentence: 'Ik weet dat hij komt.',
      words: [
        { w: 'Ik', g: 'eu' }, { w: 'weet', g: 'sei' }, { w: 'dat', g: 'que' },
        { w: 'hij', g: 'ele' }, { w: 'komt', g: 'vem' },
      ],
      translation: 'Eu sei que ele vem.',
      note: 'Também como no alemão: «komt» vai para o fim da subordinada.',
    },
  ],
  ru: [
    {
      sentence: 'Мальчик читает книгу.',
      words: [
        { w: 'Мальчик', g: 'menino' }, { w: 'читает', g: 'lê' },
        { w: 'книгу', g: 'livro-(objeto)' },
      ],
      translation: 'O menino lê um livro.',
      note: '«книгу» é o acusativo de «книга» — o caso, e não a posição, marca o objeto, então as palavras podem se reordenar livremente.',
    },
    {
      sentence: 'Я прочитал письмо.',
      words: [
        { w: 'Я', g: 'eu' }, { w: 'прочитал', g: 'li-(concluído)' },
        { w: 'письмо', g: 'carta' },
      ],
      translation: 'Li a carta (até o fim).',
      note: 'O perfectivo «прочитал» diz que a ação foi concluída; seu par imperfectivo «читал» descreveria o processo.',
    },
  ],
  el: [
    {
      sentence: 'Ο άντρας διαβάζει το βιβλίο.',
      words: [
        { w: 'Ο', g: 'o' }, { w: 'άντρας', g: 'homem' }, { w: 'διαβάζει', g: 'lê' },
        { w: 'το', g: 'o' }, { w: 'βιβλίο', g: 'livro' },
      ],
      translation: 'O homem lê o livro.',
    },
    {
      sentence: 'Βλέπω τον άντρα.',
      words: [
        { w: 'Βλέπω', g: '(eu)-vejo' }, { w: 'τον', g: 'o-(objeto)' },
        { w: 'άντρα', g: 'homem' },
      ],
      translation: 'Eu vejo o homem.',
      note: 'O artigo muda com o caso: τον (acusativo) vs. ο (nominativo).',
    },
  ],
  ar: [
    {
      sentence: 'يقرأ الولد الكتاب.',
      words: [
        { w: 'يقرأ', g: 'lê' }, { w: 'الولد', g: 'o-menino' },
        { w: 'الكتاب', g: 'o-livro' },
      ],
      translation: 'O menino lê o livro.',
      note: 'O árabe clássico começa pelo verbo (VSO); lê-se da direita para a esquerda.',
      rtl: true,
    },
    {
      sentence: 'الكتاب جديد.',
      words: [{ w: 'الكتاب', g: 'o-livro' }, { w: 'جديد', g: 'novo' }],
      translation: 'O livro é novo.',
      note: 'Sem verbo «ser» no presente — apenas «o livro» + «novo».',
      rtl: true,
    },
  ],
  hi: [
    {
      sentence: 'लड़का किताब पढ़ता है।',
      words: [
        { w: 'लड़का', g: 'menino' }, { w: 'किताब', g: 'livro' }, { w: 'पढ़ता', g: 'lê' },
        { w: 'है', g: 'está' },
      ],
      translation: 'O menino lê um livro.',
      note: 'Verbo no fim (SOV); a frase fecha com «है» (está).',
    },
    {
      sentence: 'लड़का घर में है।',
      words: [
        { w: 'लड़का', g: 'menino' }, { w: 'घर', g: 'casa' }, { w: 'में', g: 'em' },
        { w: 'है', g: 'está' },
      ],
      translation: 'O menino está em casa.',
      note: '«में» (em) vem DEPOIS do substantivo — uma posposição, não uma preposição.',
    },
  ],
  th: [
    {
      sentence: 'เด็กกินข้าว',
      words: [{ w: 'เด็ก', g: 'criança' }, { w: 'กิน', g: 'comer' }, { w: 'ข้าว', g: 'arroz' }],
      translation: 'A criança come arroz.',
      note: 'Isolante: nenhuma palavra muda de forma; não há espaços entre as palavras.',
    },
    {
      sentence: 'หนังสือสามเล่ม',
      words: [
        { w: 'หนังสือ', g: 'livro' }, { w: 'สาม', g: 'três' }, { w: 'เล่ม', g: '(classificador)' },
      ],
      translation: 'três livros',
      note: 'Contar exige um classificador — เล่ม para livros e outras coisas planas e encadernadas.',
    },
  ],
  ko: [
    {
      sentence: '아이가 책을 읽어요.',
      words: [
        { w: '아이가', g: 'criança-(sujeito)' }, { w: '책을', g: 'livro-(objeto)' },
        { w: '읽어요', g: 'lê' },
      ],
      translation: 'A criança lê um livro.',
      note: 'Verbo no fim; «-가» marca o sujeito e «-을» o objeto.',
    },
    {
      sentence: '저는 학생이에요.',
      words: [
        { w: '저는', g: 'eu-(tópico)' }, { w: '학생이에요', g: 'sou-estudante' },
      ],
      translation: 'Eu sou estudante.',
      note: '«-는» marca o tópico; o verbo «ser» se funde ao substantivo 학생 (estudante).',
    },
  ],
  he: [
    {
      sentence: 'הילד קורא ספר.',
      words: [
        { w: 'הילד', g: 'o-menino' }, { w: 'קורא', g: 'lê' }, { w: 'ספר', g: 'um-livro' },
      ],
      translation: 'O menino lê um livro.',
      note: 'Sujeito–Verbo–Objeto; lê-se da direita para a esquerda.',
      rtl: true,
    },
    {
      sentence: 'הספר חדש.',
      words: [{ w: 'הספר', g: 'o-livro' }, { w: 'חדש', g: 'novo' }],
      translation: 'O livro é novo.',
      note: 'Sem verbo «ser» no presente — apenas «o-livro» + «novo».',
      rtl: true,
    },
  ],
  la: [
    {
      sentence: 'Puella librum legit.',
      words: [
        { w: 'Puella', g: 'menina' }, { w: 'librum', g: 'livro-(objeto)' }, { w: 'legit', g: 'lê' },
      ],
      translation: 'A menina lê o livro.',
      note: 'Uma ordem neutra comum (Sujeito–Objeto–Verbo), mas as terminações de caso permitiriam reordenar tudo livremente.',
    },
    {
      sentence: 'Liber novus est.',
      words: [{ w: 'Liber', g: 'livro' }, { w: 'novus', g: 'novo' }, { w: 'est', g: 'é' }],
      translation: 'O livro é novo.',
      note: 'Nenhuma palavra para «o» — liber sozinho pode significar «livro», «um livro» ou «o livro».',
    },
  ],
  fa: [
    {
      sentence: 'پسر کتاب می‌خواند.',
      words: [
        { w: 'پسر', g: 'menino' }, { w: 'کتاب', g: 'livro' }, { w: 'می‌خواند', g: 'lê' },
      ],
      translation: 'O menino lê o livro.',
      note: 'Sujeito–Objeto–Verbo — o verbo vem por último, ao contrário do árabe.',
      rtl: true,
    },
    {
      sentence: 'این کتاب خوب است.',
      words: [
        { w: 'این', g: 'este' }, { w: 'کتاب', g: 'livro' }, { w: 'خوب', g: 'bom' }, { w: 'است', g: 'é' },
      ],
      translation: 'Este livro é bom.',
      rtl: true,
    },
  ],
  id: [
    {
      sentence: 'Anak itu membaca buku.',
      words: [
        { w: 'Anak', g: 'criança' }, { w: 'itu', g: 'aquela/a' }, { w: 'membaca', g: 'lê' }, { w: 'buku', g: 'livro' },
      ],
      translation: 'A criança lê um livro.',
      note: '«Itu» («aquele») vem depois do substantivo, fazendo o papel de «o».',
    },
    {
      sentence: 'Saya membeli buku-buku itu.',
      words: [
        { w: 'Saya', g: 'eu' }, { w: 'membeli', g: 'comprei' }, { w: 'buku-buku', g: 'livros-(dobrado)' }, { w: 'itu', g: 'aqueles' },
      ],
      translation: 'Comprei aqueles livros.',
      note: 'O plural é a palavra dita duas vezes: buku (livro) → buku-buku (livros). Também não há marcação de tempo no verbo — o contexto se encarrega.',
    },
  ],
  tl: [
    {
      sentence: 'Kumain ang bata ng mansanas.',
      words: [
        { w: 'Kumain', g: 'comeu' }, { w: 'ang bata', g: 'a-criança' }, { w: 'ng mansanas', g: 'uma-maçã' },
      ],
      translation: 'A criança comeu uma maçã.',
      note: 'Verbo primeiro — o agente e a coisa afetada vêm depois, marcados por ang e ng.',
    },
    {
      sentence: 'Naglalakad siya araw-araw.',
      words: [
        { w: 'Naglalakad', g: 'está-andando' }, { w: 'siya', g: 'ele/ela' }, { w: 'araw-araw', g: 'dia-dia' },
      ],
      translation: 'Ele/ela anda todos os dias.',
      note: 'Reduplicação de novo: araw (dia) dobrado significa «todo dia».',
    },
  ],
}
