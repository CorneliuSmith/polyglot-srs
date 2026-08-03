/**
 * French (fr) overlay for the "About this language" reference: all 27 course
 * facts entries plus glossed syntax examples. Course-language text (sentence,
 * words[].w, rtl) is copied verbatim from languageFacts.ts — only glosses,
 * translations, and notes are in French. Register follows trFr in factsL10n.ts.
 */
import type { LanguageFacts, SyntaxExample } from './languageFacts'

export const FACTS_FR: Record<string, LanguageFacts> = {
  es: {
    tagline: 'Une langue romane à la portée remarquable et à l’orthographe fidèle.',
    family: 'Indo-européenne › italique › romane (ibéro-romane)',
    speakers: '~485 millions de locuteurs natifs — juste derrière le mandarin.',
    whereSpoken: 'Espagne, presque toute l’Amérique latine, Guinée équatoriale, et largement aux États-Unis.',
    writingSystem: 'Alphabet latin, plus ñ et les signes á é í ó ú ü. S’écrit de gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet, mais souple — les terminaisons en disent tant que le sujet est le plus souvent omis.',
    history:
      'Issu du latin parlé de l’Hispanie romaine, il a pris forme comme castillan dans les royaumes médiévaux du nord de l’Espagne. L’empire l’a ensuite porté au-delà de l’Atlantique, où vit aujourd’hui la majorité de ses locuteurs.',
    unique: [
      'Les verbes font le gros du travail : un seul mot marque la personne, le temps et le mode, si bien que les pronoms sont généralement omis.',
      'Chaque nom est masculin ou féminin, et les adjectifs s’accordent avec lui.',
      'Deux verbes « être » — ser (permanent) et estar (temporaire ou lieu).',
      'Les signes inversés ¿ et ¡ ouvrent questions et exclamations.',
    ],
  },
  fr: {
    tagline: 'Une langue romane où beaucoup s’écrit sans se prononcer.',
    family: 'Indo-européenne › italique › romane (gallo-romane)',
    speakers: '~80 millions de locuteurs natifs, ~300 millions au total sur cinq continents.',
    whereSpoken: 'France, Belgique, Suisse, Québec, et une grande partie de l’Afrique de l’Ouest et centrale.',
    writingSystem: 'Alphabet latin avec accents (é è ê ë), cédille (ç) et ligatures (œ). De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet, assez rigide — le pronom sujet reste en place.',
    history:
      'Issu du latin vulgaire de Gaule, il a émergé comme langue d’oïl au nord. Des siècles de prestige de cour et l’Académie française ont façonné le standard soigné d’aujourd’hui.',
    unique: [
      'Bien des lettres finales sont muettes — mais ressurgissent en liaison devant une voyelle.',
      'Les voyelles nasales (on, an, in) n’ont pas d’équivalent direct dans la plupart des autres langues.',
      'Les noms portent un genre ; articles et adjectifs s’accordent.',
      'Le vous formel face au tu familier marque le registre social de chaque échange.',
    ],
  },
  de: {
    tagline: 'Une langue germanique qui garde le verbe pour la fin.',
    family: 'Indo-européenne › germanique (germanique occidental)',
    speakers: '~95 millions de locuteurs natifs — la première langue maternelle de l’UE.',
    whereSpoken: 'Allemagne, Autriche, Suisse, Liechtenstein, et des poches en Belgique, en Italie et au-delà.',
    writingSystem: 'Alphabet latin plus ä ö ü et ß. Les noms prennent toujours la majuscule. De gauche à droite.',
    wordOrder: 'Verbe en deuxième position dans les principales, en fin de subordonnée — le fameux « verbe à la fin ».',
    history:
      'Issu de dialectes germaniques occidentaux remodelés par la mutation consonantique du haut allemand. La traduction de la Bible par Luther a beaucoup fait pour forger un standard écrit commun.',
    unique: [
      'Quatre cas (nominatif, accusatif, datif, génitif) modifient articles et terminaisons.',
      'Trois genres — et der/die/das suivent rarement le sens.',
      'Les mots s’empilent en longs composés (Handschuh = « chaussure de main » = gant).',
      'Les verbes séparables se scindent : « ich stehe früh auf » (je me lève tôt).',
    ],
  },
  it: {
    tagline: 'La langue romane la plus proche de son parent latin.',
    family: 'Indo-européenne › italique › romane (italo-dalmate)',
    speakers: '~65 millions de locuteurs natifs.',
    whereSpoken: 'Italie, Saint-Marin, Vatican et Tessin suisse.',
    writingSystem: 'Alphabet latin avec accents graves et aigus (à, é). De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet, souple — le sujet est souvent omis.',
    history:
      'L’italien standard est né du toscan de Florence, élevé par Dante, Pétrarque et Boccace, et n’est devenu une langue parlée commune à tout le pays qu’après l’unification des années 1860.',
    unique: [
      'Les consonnes doubles se prononcent longues et peuvent changer le sens (pala vs palla).',
      'Grammaticalement la plus conservatrice des grandes langues romanes — très proche du latin.',
      'Noms et adjectifs s’accordent en genre et en nombre.',
      'Une intonation riche et musicale, des voyelles ouvertes et nettes.',
    ],
  },
  ca: {
    tagline: 'Une langue romane, pont entre l’Espagne et la France.',
    family: 'Indo-européenne › italique › romane (occitano-romane)',
    speakers: '~9 millions de locuteurs natifs.',
    whereSpoken: 'Catalogne, Pays valencien, îles Baléares, Andorre (où il est la seule langue officielle) et Alghero en Sardaigne.',
    writingSystem: 'Alphabet latin avec le point médian (l·l) et des accents. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet, souple, avec omission du sujet.',
    history:
      'Formé à partir du latin vulgaire, il a fleuri comme langue littéraire et juridique au Moyen Âge. Réprimé sous Franco, il a été relancé et se trouve aujourd’hui au cœur de l’identité catalane.',
    unique: [
      'À mi-chemin entre l’espagnol et le français — familier aux deux, identique à aucun.',
      'Les pronoms objets faibles (em, et, es, hi, en) se greffent autour du verbe.',
      'Une voyelle neutre (schwa) caractéristique dans les dialectes orientaux.',
      'Une langue littéraire et officielle à part entière, pas un dialecte de l’espagnol.',
    ],
  },
  pt: {
    tagline: 'Une langue romane du monde atlantique.',
    family: 'Indo-européenne › italique › romane (ibéro-romane)',
    speakers: '~230 millions de locuteurs natifs — la plupart au Brésil.',
    whereSpoken: 'Brésil, Portugal, Angola, Mozambique, Cap-Vert et d’autres anciennes colonies maritimes.',
    writingSystem: 'Alphabet latin avec ã õ, ç et des accents. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet, souple, avec omission du sujet.',
    history:
      'Né du galaïco-portugais au nord-ouest de la péninsule Ibérique, il s’est répandu dans le monde par les routes maritimes du Portugal, se scindant en deux standards distincts, européen et brésilien.',
    unique: [
      'Voyelles et diphtongues nasales (pão, mãe, coração).',
      'Un infinitif personnel — l’infinitif peut prendre des terminaisons pour chaque personne.',
      'Un subjonctif futur bien vivant, perdu dans la plupart des langues romanes.',
      'Les variétés européenne et brésilienne diffèrent nettement par les sons et le rythme.',
    ],
  },
  ro: {
    tagline: 'La langue romane de l’Est, façonnée par ses voisins.',
    family: 'Indo-européenne › italique › romane (romane orientale)',
    speakers: '~24 millions de locuteurs natifs.',
    whereSpoken: 'Roumanie et Moldavie.',
    writingSystem: 'Alphabet latin avec ă, â, î, ș, ț. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet, souple grâce au marquage des cas.',
    history:
      'Descend du latin de la Dacie romaine et a évolué des siècles durant coupé du reste du monde roman, profondément marqué par ses voisins slaves et balkaniques.',
    unique: [
      'La seule grande langue romane à avoir conservé des cas grammaticaux.',
      'L’article défini se colle à la fin du nom : lup → lupul (le loup).',
      'Un genre neutre conservé aux côtés du masculin et du féminin.',
      'Partage des traits balkaniques (comme l’article postposé) avec des voisins sans parenté.',
    ],
  },
  tr: {
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
  },
  sw: {
    tagline: 'Le grand trait d’union de l’Afrique de l’Est, bantou de cœur.',
    family: 'Nigéro-congolaise › atlantique-congolaise › bantoue',
    speakers: '~5 millions de locuteurs natifs, mais plus de 80 millions en langue seconde partagée.',
    whereSpoken: 'Tanzanie, Kenya, Ouganda, RDC et toute la région des Grands Lacs africains.',
    writingSystem: 'Alphabet latin (jadis aussi l’écriture arabe). De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet.',
    history:
      'Langue bantoue de la côte est-africaine, façonnée par mille ans de commerce dans l’océan Indien — d’où ses nombreux emprunts arabes — puis répandue vers l’intérieur comme langue véhiculaire.',
    unique: [
      'Les noms se répartissent en ~15 classes ; la classe commande l’accord dans toute la phrase.',
      'Les verbes agglutinent sujet, temps, objet et plus encore en un seul mot.',
      'Fait rare pour une langue bantoue, il n’est pas tonal.',
      'Une riche couche de vocabulaire arabe (safari, kitabu, asante) repose sur la base bantoue.',
    ],
  },
  yo: {
    tagline: 'Une langue ouest-africaine où la hauteur de la voix porte le sens.',
    family: 'Nigéro-congolaise › atlantique-congolaise › volta-nigérienne',
    speakers: '~45 millions.',
    whereSpoken: 'Sud-ouest du Nigeria, Bénin et Togo — plus une profonde diaspora dans les Amériques.',
    writingSystem: 'Alphabet latin avec points souscrits (ẹ, ọ, ṣ) et marques de ton. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet.',
    history:
      'La langue des civilisations d’Ifẹ̀ et d’Ọ̀yọ́, portée à travers l’Atlantique par la traite esclavagiste et préservée dans les traditions religieuses cubaines et brésiliennes.',
    unique: [
      'Trois tons (haut, moyen, bas) distinguent des mots par ailleurs identiques.',
      'Les constructions à verbes sériels enchaînent plusieurs verbes dans une même proposition.',
      'Les lettres à point souscrit notent des voyelles et des consonnes distinctes.',
      'Une riche tradition de proverbes tissée dans la parole de tous les jours.',
    ],
  },
  ha: {
    tagline: 'Une langue tchadique, langue d’échange du Sahel.',
    family: 'Afro-asiatique › tchadique',
    speakers: 'Plus de 50 millions, et langue véhiculaire pour bien davantage.',
    whereSpoken: 'Nord du Nigeria et Niger, et à travers l’Afrique de l’Ouest et le Sahel.',
    writingSystem: 'Alphabet latin (boko) avec lettres crochetées (ɓ, ɗ, ƙ) ; s’écrit aussi en caractères arabes (ajami). De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet.',
    history:
      'Une langue tchadique — cousine lointaine de l’arabe et de l’hébreu — répandue bien au-delà de son berceau par des siècles de commerce transsaharien et d’érudition islamique.',
    unique: [
      'Deux tons et la longueur des voyelles façonnent le sens des mots.',
      'Des consonnes glottalisées « crochetées » : ɓ, ɗ, ƙ.',
      'Le genre grammatical apparaît au singulier mais disparaît au pluriel.',
      'Un système de « degrés » verbaux encode la direction et l’accomplissement.',
    ],
  },
  xh: {
    tagline: 'Une langue nguni célèbre pour ses clics.',
    family: 'Nigéro-congolaise › atlantique-congolaise › bantoue (nguni)',
    speakers: '~8 millions de locuteurs natifs.',
    whereSpoken: 'Afrique du Sud, surtout le Cap-Oriental — l’une de ses 11 langues officielles.',
    writingSystem: 'Alphabet latin ; les lettres c, x, q notent trois clics différents. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet.',
    history:
      'Langue bantoue du groupe nguni, proche parente du zoulou. Le contact avec les peuples khoïsan lui a donné les consonnes à clic qui la rendent immédiatement reconnaissable.',
    unique: [
      'Trois consonnes à clic — dentale (c), latérale (x) et palatale (q) — empruntées au khoïsan.',
      'Un système de classes nominales qui tisse l’accord à travers la phrase.',
      'Une langue tonale, même si le ton ne s’écrit pas.',
      'Des préfixes d’accord relient chaque mot à la classe du nom.',
    ],
  },
  mi: {
    tagline: 'La langue polynésienne d’Aotearoa, verbe en tête.',
    family: 'Austronésienne › malayo-polynésienne › polynésienne',
    speakers: '~150 000 à 190 000, en renouveau constant.',
    whereSpoken: 'Nouvelle-Zélande (Aotearoa).',
    writingSystem: 'Alphabet latin ; les macrons (ā, ē, ī, ō, ū) notent les voyelles longues. De gauche à droite.',
    wordOrder: 'Verbe–Sujet–Objet — le verbe vient en premier.',
    history:
      'Langue polynésienne orientale arrivée en Nouvelle-Zélande vers les années 1300. Poussée au bord de l’extinction au XXe siècle, elle a été revitalisée par les kōhanga reo (« nids de langue ») et l’enseignement par immersion.',
    unique: [
      'Des phrases à verbe initial (VSO), rares parmi les langues présentées ici.',
      'Un petit système de sons : dix consonnes et cinq voyelles (brèves et longues).',
      'De petites particules, et non des terminaisons, marquent le temps et le rôle.',
      'Les macrons distinguent les mots — keke (gâteau) vs kēkē (aisselle).',
    ],
  },
  jam: {
    tagline: 'Un créole à lexique anglais et à grammaire ouest-africaine.',
    family: 'Créole à base anglaise (atlantique)',
    speakers: '~3 millions, plus une large diaspora.',
    whereSpoken: 'Jamaïque et communautés jamaïcaines du monde entier.',
    writingSystem: 'Alphabet latin — écrit tantôt dans une orthographe d’inspiration anglaise, tantôt dans le système phonétique Cassidy/JLU. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet.',
    history:
      'Né dans les plantations de l’ère coloniale, où des Africains de l’Ouest réduits en esclavage ont bâti une langue nouvelle à partir d’un vocabulaire anglais et de la grammaire de l’akan, de l’igbo et d’autres langues.',
    unique: [
      'Les verbes ne se conjuguent pas — le temps vient de particules (mi did go, mi a go).',
      'Des pronoms bien à lui : mi, yu, im, wi, unu, dem.',
      'Le redoublement intensifie (chaka-chaka = en désordre).',
      'Des mots anglais, mais une grammaire qui n’appartient qu’à lui.',
    ],
  },
  en: {
    tagline: 'Une langue germanique qui a emprunté à tout le monde.',
    family: 'Indo-européenne › germanique (germanique occidental)',
    speakers: '~380 millions de locuteurs natifs, ~1,5 milliard au total — la lingua franca du monde.',
    whereSpoken: 'Royaume-Uni, Irlande, Amérique du Nord, Australie, Nouvelle-Zélande, et comme langue seconde presque partout.',
    writingSystem: 'Alphabet latin, 26 lettres, sans diacritiques. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet, assez rigide — l’ordre des mots fait le travail que faisaient jadis les cas.',
    history:
      'Né comme anglo-saxon (vieil anglais), remodelé par les colons scandinaves puis par un flot de français normand après 1066, il s’est répandu dans le monde par l’Empire britannique et l’influence américaine.',
    unique: [
      'Un vocabulaire immense — un noyau germanique recouvert de couches latines, françaises et grecques.',
      'Très peu de flexion : les noms changent à peine, et il n’y a pas de genre grammatical.',
      'Une orthographe notoirement irrégulière, fossile de prononciations anciennes.',
      'Les verbes à particule (give up, put off, run into) portent le sens idiomatique.',
    ],
  },
  nl: {
    tagline: 'La langue germanique occidentale entre l’anglais et l’allemand.',
    family: 'Indo-européenne › germanique (germanique occidental)',
    speakers: '~25 millions de locuteurs natifs.',
    whereSpoken: 'Pays-Bas, Belgique (Flandre), Suriname et Caraïbes néerlandaises.',
    writingSystem: 'Alphabet latin ; le digramme « ij » se comporte comme une seule lettre. De gauche à droite.',
    wordOrder: 'Verbe en deuxième position dans les principales, en fin de subordonnée — comme en allemand.',
    history:
      'Langue bas-francique qui n’a jamais subi la mutation consonantique de l’allemand, ce qui la laisse, par la grammaire et le lexique, en équilibre entre l’anglais et l’allemand.',
    unique: [
      'L’ordre « verbe second » envoie les verbes en fin de subordonnée.',
      'Deux genres — commun (de) et neutre (het).',
      'Un « g » guttural resté fameux.',
      'Les diminutifs en -je sont partout et adoucissent le ton.',
    ],
  },
  ru: {
    tagline: 'Une langue slave, faite de cas et d’aspect verbal.',
    family: 'Indo-européenne › balto-slave › slave orientale',
    speakers: '~150 millions de locuteurs natifs, et largement parlé en langue seconde.',
    whereSpoken: 'Russie et une grande partie de l’ex-Union soviétique.',
    writingSystem: 'Alphabet cyrillique, adapté du grec. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet en principe, mais l’ordre est très libre — les cas disent qui fait quoi.',
    history:
      'Langue slave orientale écrite en cyrillique depuis la christianisation de la Rus’, profondément façonnée par le vieux slave d’église et standardisée sur le dialecte de Moscou.',
    unique: [
      'Six cas remodèlent noms, adjectifs et pronoms.',
      'Chaque verbe vient en paire d’aspects — imperfectif (le processus) vs perfectif (le résultat).',
      'Aucun mot pour « un » ni pour « le ».',
      'Une distinction consonnes dures/molles (palatalisation) traverse tout le système sonore.',
    ],
  },
  el: {
    tagline: 'Une langue profonde de 3 400 ans, sur sa propre branche.',
    family: 'Indo-européenne › hellénique (une branche à elle seule)',
    speakers: '~13 millions de locuteurs natifs.',
    whereSpoken: 'Grèce et Chypre.',
    writingSystem: 'L’alphabet grec — ancêtre du latin comme du cyrillique. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet, souple grâce aux terminaisons casuelles.',
    history:
      'La plus ancienne langue indo-européenne attestée encore parlée, avec une tradition écrite continue du grec mycénien au grec d’aujourd’hui, en passant par le grec ancien et la koinè.',
    unique: [
      'Son propre alphabet, dont descendent le latin et le cyrillique.',
      'Quatre cas et trois genres.',
      'Une part immense du vocabulaire scientifique repose sur des racines grecques.',
      'L’accent d’intensité moderne a remplacé l’ancien accent de hauteur.',
    ],
  },
  ar: {
    tagline: 'Une langue sémitique bâtie sur des racines de trois lettres.',
    family: 'Afro-asiatique › sémitique',
    speakers: '~310 millions de locuteurs natifs à travers ses nombreuses variétés.',
    whereSpoken: 'Le Moyen-Orient et l’Afrique du Nord, et liturgiquement dans tout le monde musulman.',
    writingSystem: 'L’écriture arabe, tracée de droite à gauche et liée en cursive.',
    wordOrder: 'Verbe–Sujet–Objet dans la langue classique ; beaucoup de dialectes préfèrent Sujet–Verbe–Objet.',
    history:
      'Langue sémitique dont la forme classique a été fixée par le Coran. Aujourd’hui, un standard formel (l’arabe standard moderne) est partagé dans toute la région tandis que chacun parle un dialecte local — une situation appelée diglossie.',
    unique: [
      'Les mots se construisent sur des racines de trois consonnes : k-t-b donne kitāb (livre), kātib (écrivain), maktab (bureau).',
      'S’écrit de droite à gauche, avec des lettres qui changent de forme selon leur position.',
      'Un duel, distinct du singulier et du pluriel.',
      'Des consonnes emphatiques et pharyngales sans équivalent en français.',
    ],
  },
  hi: {
    tagline: 'Une langue indo-aryenne qui place le verbe en dernier.',
    family: 'Indo-européenne › indo-iranienne › indo-aryenne',
    speakers: '~340 millions de locuteurs natifs (forme parlée quasi identique à l’ourdou).',
    whereSpoken: 'Inde du Nord et du Centre.',
    writingSystem: 'L’abugida devanagari — chaque consonne porte une voyelle inhérente. De gauche à droite.',
    wordOrder: 'Sujet–Objet–Verbe.',
    history:
      'Descendu du sanskrit à travers les prakrits, il a absorbé un vocabulaire persan et arabe sous les Moghols — le registre parlé partagé avec l’ourdou est souvent appelé hindoustani.',
    unique: [
      'Des postpositions au lieu de prépositions (« vers la maison » → « maison-vers »).',
      'Ergativité scindée : la marque ne apparaît sur le sujet des verbes transitifs au passé.',
      'Les verbes s’accordent en genre, si bien que les phrases changent selon qui parle ou agit.',
      'Trois niveaux de « tu/vous » (tū, tum, āp) règlent la politesse.',
    ],
  },
  th: {
    tagline: 'Une langue tonale et isolante, écrite sans espaces.',
    family: 'Kra-daï › taï',
    speakers: '~60 millions de locuteurs natifs.',
    whereSpoken: 'Thaïlande.',
    writingSystem: 'L’abugida thaï — un alphabet avec marques de ton et sans espaces entre les mots. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet.',
    history:
      'Langue taï dont les locuteurs ont migré vers le sud depuis l’actuelle Chine méridionale, absorbant du vocabulaire pali, sanskrit et khmer ; son écriture descend du khmer.',
    unique: [
      'Cinq tons — la même syllabe peut vouloir dire cinq choses différentes.',
      'Isolante : les mots ne changent jamais de forme ; la grammaire repose sur l’ordre des mots et les particules.',
      'Compter exige un classificateur selon la nature de ce que l’on compte.',
      'Des particules de politesse (khráp pour les hommes, khâ pour les femmes) closent les phrases.',
    ],
  },
  ko: {
    tagline: 'Un isolat linguistique doté d’un alphabet conçu scientifiquement.',
    family: 'Coréanique (un isolat linguistique)',
    speakers: '~80 millions de locuteurs natifs.',
    whereSpoken: 'Corée du Sud et du Nord, et une vaste diaspora.',
    writingSystem: 'Le hangul — un alphabet dont les lettres se groupent en blocs syllabiques. De gauche à droite.',
    wordOrder: 'Sujet–Objet–Verbe.',
    history:
      'Le coréen est seul de son espèce, sans parenté prouvée. Longtemps écrit en caractères chinois, il a reçu le hangul — commandé par le roi Sejong en 1443 — une écriture délibérément conçue pour être facile à apprendre.',
    unique: [
      'Les lettres du hangul épousent la forme que prend la bouche pour chaque son.',
      'Des niveaux de langue et d’honorifiques élaborés remodèlent les verbes selon le contexte social.',
      'Agglutinant : particules et terminaisons s’attachent pour marquer le rôle et la nuance.',
      'Une particule de thème (은/는) met en avant ce dont parle la phrase.',
    ],
  },
  he: {
    tagline: 'Une langue sémitique ressuscitée, de la page à la parole quotidienne.',
    family: 'Afro-asiatique › sémitique (sémitique du Nord-Ouest, cananéenne)',
    speakers: '~9 millions de locuteurs natifs, presque tous en Israël.',
    whereSpoken: 'Israël, et les communautés juives du monde entier (liturgiquement depuis l’Antiquité).',
    writingSystem: 'L’abjad hébreu, écrit de droite à gauche. Les voyelles ne sont normalement pas notées ; les points du niqqoud les indiquent dans les textes pédagogiques, la poésie et les livres de prière.',
    wordOrder: 'Sujet–Verbe–Objet aujourd’hui (l’hébreu biblique préférait Verbe–Sujet–Objet).',
    history:
      'Langue cananéenne de la Bible hébraïque, elle a survécu comme langue du droit, de la liturgie et de l’érudition juives pendant près de deux millénaires après avoir cessé d’être la langue quotidienne de quiconque. Relancée comme langue parlée à partir de la fin du XIXe siècle, elle est devenue la langue officielle d’Israël — l’une des seules renaissances linguistiques complètes de l’histoire.',
    unique: [
      'Morphologie à racines et schèmes : trois consonnes portent le sens central, et le schème du mot le façonne — k-t-b donne katav (il a écrit) et mikhtav (lettre).',
      'L’écriture ordinaire ne note aucune voyelle — le lecteur aguerri les restitue d’après le contexte.',
      'Les verbes marquent le genre autant que la personne et le nombre, même au présent.',
      'Une langue ressuscitée : un véritable écart sépare l’hébreu biblique ancien de l’hébreu moderne vivant parlé aujourd’hui.',
    ],
  },
  la: {
    tagline: 'La langue classique dont toutes les langues romanes sont issues.',
    family: 'Indo-européenne › italique',
    speakers: 'Plus aucun locuteur natif — étudié dans le monde entier, et toujours en usage liturgique.',
    whereSpoken:
      'Aucune communauté vivante ; il conserve un statut cérémoniel et officiel au Vatican et dans la liturgie de l’Église catholique.',
    writingSystem: 'L’alphabet latin — l’ancêtre direct de celui du français. De gauche à droite.',
    wordOrder:
      'Souple : les terminaisons casuelles marquent le rôle grammatical de chaque mot, si bien que l’ordre sert l’emphase plutôt qu’il n’est fixé par la grammaire.',
    history:
      'Langue de la Rome antique, il s’est répandu autour de la Méditerranée et en Europe occidentale avec l’Empire romain, puis a évolué localement en langues romanes — espagnol, français, italien, portugais, roumain et d’autres — tout en demeurant la langue de l’érudition médiévale, de l’Église et des sciences pendant des siècles après la chute de Rome.',
    unique: [
      'Les noms se déclinent en cas (nominatif, génitif, datif, accusatif, ablatif, et un vocatif résiduel) qui marquent leur rôle dans la phrase.',
      'Aucun article — puella seul peut signifier « fille », « une fille » ou « la fille ».',
      'Les verbes se conjuguent en personne, nombre, temps, mode et voix, rendant souvent le pronom inutile.',
      'L’ancêtre direct des langues romanes — une grande part de son vocabulaire et de sa grammaire survit, transformée, en espagnol, français, italien, portugais et roumain.',
    ],
  },
  fa: {
    tagline: 'Une langue indo-européenne écrite dans une écriture sémitique d’emprunt.',
    family: 'Indo-européenne › indo-iranienne (iranienne occidentale)',
    speakers: '~70 millions de locuteurs natifs, plus les locuteurs du dari et du tadjik, très proches.',
    whereSpoken: 'Iran (farsi/persan), Afghanistan (dari) et Tadjikistan (tadjik).',
    writingSystem: 'Une écriture arabe modifiée, de droite à gauche ; les voyelles brèves restent le plus souvent non écrites, comme en arabe.',
    wordOrder: 'Sujet–Objet–Verbe — à la différence de l’arabe, qui ouvre par le verbe.',
    history:
      'Langue iranienne descendue du vieux perse, langue de l’Empire achéménide, via le moyen perse (pehlevi). Après la conquête islamique, elle a adopté l’écriture arabe et absorbé un large vocabulaire arabe, tout en gardant de bout en bout sa grammaire indo-européenne — génétiquement, elle n’a rien à voir avec l’arabe malgré l’alphabet partagé.',
    unique: [
      'Une grammaire indo-européenne sous une écriture dérivée de l’arabe — les deux langues ne sont pas parentes, quoi qu’en suggère l’alphabet.',
      'Ni genre grammatical ni système casuel — une morphologie étonnamment régulière pour une langue indo-européenne.',
      'L’ezāfe : un -e atone, généralement non écrit, qui relie un nom à ce qui le suit — un adjectif, un possesseur, un autre nom.',
      'Le verbe vient en dernier, et « être » est souvent un suffixe léger soudé au prédicat plutôt qu’un mot à part.',
    ],
  },
  id: {
    tagline: 'Une langue nationale choisie à dessein pour appartenir à tous.',
    family: 'Austronésienne › malayo-polynésienne (malaïque)',
    speakers: '~270 millions de locuteurs en Indonésie, la plupart en langue seconde parlée très couramment.',
    whereSpoken: 'Indonésie, dont elle est la langue nationale et officielle, sur un archipel aux centaines de langues locales.',
    writingSystem: 'L’alphabet latin, orthographe phonétique sans diacritiques dans l’usage standard. De gauche à droite.',
    wordOrder: 'Sujet–Verbe–Objet.',
    history:
      'Forme standardisée du malais, adoptée à l’indépendance comme langue nationale unificatrice de l’Indonésie précisément parce qu’elle n’était la langue maternelle dominante d’aucune ethnie — un acte délibéré d’aménagement linguistique, et l’un des plus réussis de l’histoire, dans un pays aux centaines de langues locales.',
    unique: [
      'Aucune conjugaison — une seule forme verbale couvre toute personne, tout nombre et tout temps ; des mots séparés comme sudah (« déjà ») et akan (« va ») portent le temps.',
      'Le pluriel se forme souvent en doublant simplement le mot : buku (livre) → buku-buku (livres).',
      'Des couches de préfixes et de suffixes remodèlent le sens et le rôle d’une racine : ajar (enseigner) → belajar (étudier) → mengajar (enseigner) → pelajaran (leçon).',
      'Pas de genre grammatical, pas d’articles, et des pronoms qui ne changent pas de forme selon leur fonction.',
    ],
  },
  tl: {
    tagline: 'Une langue austronésienne qui place le verbe en premier.',
    family: 'Austronésienne › malayo-polynésienne (philippine)',
    speakers: '~28 millions de locuteurs natifs ; compris comme filipino par la plupart des 110 millions d’habitants des Philippines.',
    whereSpoken: 'Les Philippines, autour de Manille et de Luçon — et dans tout le pays comme filipino, l’une des deux langues officielles.',
    writingSystem: 'L’alphabet latin, orthographe phonétique. De gauche à droite. (Écrit dans le syllabaire baybayin avant la colonisation espagnole.)',
    wordOrder: 'Verbe initial — le prédicat ouvre la phrase, avant l’agent et ce qui subit l’action.',
    history:
      'Langue austronésienne de l’archipel philippin, elle est devenue à l’indépendance la base du filipino, la langue nationale — l’une des deux langues officielles aux côtés de l’anglais, enseignée dans tout le pays parmi des dizaines d’autres langues vivantes de l’archipel.',
    unique: [
      'Des phrases à verbe initial : le verbe ouvre généralement la proposition, de petites particules (ang, ng, sa) marquant qui fait quoi à quoi.',
      'Un système de « focus » : l’affixe du verbe change selon que le sujet est l’agent, la chose affectée, le lieu ou autre chose — une marque des langues philippines.',
      'Un redoublement très productif, comme en indonésien : araw (jour) → araw-araw (chaque jour).',
      'Des siècles d’emprunts espagnols puis, plus récemment, anglais côtoient son noyau austronésien.',
    ],
  },
}

export const SYNTAX_FR: Record<string, SyntaxExample[]> = {
  es: [
    {
      sentence: 'El niño come una manzana.',
      words: [
        { w: 'El', g: 'le' }, { w: 'niño', g: 'garçon' }, { w: 'come', g: 'mange' },
        { w: 'una', g: 'une' }, { w: 'manzana', g: 'pomme' },
      ],
      translation: 'Le garçon mange une pomme.',
      note: 'Sujet–Verbe–Objet ; l’article s’accorde avec le nom.',
    },
    {
      sentence: '¿Hablas español?',
      words: [{ w: '¿Hablas', g: '(tu)-parles' }, { w: 'español?', g: 'espagnol' }],
      translation: 'Parles-tu espagnol ?',
      note: 'Aucun mot pour « tu » — la terminaison -as le dit déjà (sujet omis).',
    },
  ],
  fr: [
    {
      sentence: 'Le garçon mange une pomme.',
      words: [
        { w: 'Le', g: 'le' }, { w: 'garçon', g: 'garçon' }, { w: 'mange', g: 'mange' },
        { w: 'une', g: 'une' }, { w: 'pomme', g: 'pomme' },
      ],
      translation: 'Le garçon mange une pomme.',
    },
    {
      sentence: 'Je ne mange pas de viande.',
      words: [
        { w: 'Je', g: 'je' }, { w: 'ne', g: '(ne)' }, { w: 'mange', g: 'mange' },
        { w: 'pas', g: '(pas)' }, { w: 'de', g: 'de' }, { w: 'viande', g: 'viande' },
      ],
      translation: 'Je ne mange pas de viande.',
      note: 'La négation encadre le verbe en deux morceaux : ne … pas.',
    },
  ],
  de: [
    {
      sentence: 'Heute esse ich einen Apfel.',
      words: [
        { w: 'Heute', g: 'aujourd’hui' }, { w: 'esse', g: 'mange' }, { w: 'ich', g: 'je' },
        { w: 'einen', g: 'une' }, { w: 'Apfel', g: 'pomme' },
      ],
      translation: 'Aujourd’hui je mange une pomme.',
      note: 'Le verbe « esse » occupe la DEUXIÈME place, repoussant le sujet « ich » derrière lui.',
    },
    {
      sentence: 'Ich weiß, dass er heute kommt.',
      words: [
        { w: 'Ich', g: 'je' }, { w: 'weiß', g: 'sais' }, { w: 'dass', g: 'que' },
        { w: 'er', g: 'il' }, { w: 'heute', g: 'aujourd’hui' }, { w: 'kommt', g: 'vient' },
      ],
      translation: 'Je sais qu’il vient aujourd’hui.',
      note: 'Dans la subordonnée, le verbe « kommt » saute tout à la fin.',
    },
  ],
  it: [
    {
      sentence: 'Il ragazzo mangia una mela.',
      words: [
        { w: 'Il', g: 'le' }, { w: 'ragazzo', g: 'garçon' }, { w: 'mangia', g: 'mange' },
        { w: 'una', g: 'une' }, { w: 'mela', g: 'pomme' },
      ],
      translation: 'Le garçon mange une pomme.',
    },
    {
      sentence: 'Lo vedo.',
      words: [{ w: 'Lo', g: 'le' }, { w: 'vedo', g: '(je)-vois' }],
      translation: 'Je le vois.',
      note: 'Le pronom objet « lo » précède le verbe ; le sujet est omis.',
    },
  ],
  ca: [
    {
      sentence: 'El nen menja una poma.',
      words: [
        { w: 'El', g: 'le' }, { w: 'nen', g: 'garçon' }, { w: 'menja', g: 'mange' },
        { w: 'una', g: 'une' }, { w: 'poma', g: 'pomme' },
      ],
      translation: 'Le garçon mange une pomme.',
    },
    {
      sentence: 'No en tinc.',
      words: [{ w: 'No', g: '(pas)' }, { w: 'en', g: 'en' }, { w: 'tinc', g: '(j’)-ai' }],
      translation: 'Je n’en ai pas.',
      note: 'Le pronom faible « en » — comme le « en » français — se groupe autour du verbe.',
    },
  ],
  pt: [
    {
      sentence: 'O menino come uma maçã.',
      words: [
        { w: 'O', g: 'le' }, { w: 'menino', g: 'garçon' }, { w: 'come', g: 'mange' },
        { w: 'uma', g: 'une' }, { w: 'maçã', g: 'pomme' },
      ],
      translation: 'Le garçon mange une pomme.',
    },
    {
      sentence: 'É importante estudarmos.',
      words: [
        { w: 'É', g: '(c’)-est' }, { w: 'importante', g: 'important' },
        { w: 'estudarmos', g: '(pour-nous)-étudier' },
      ],
      translation: 'Il est important que nous étudiions.',
      note: 'L’infinitif prend une terminaison personnelle -mos — l’infinitif personnel, propre au portugais.',
    },
  ],
  ro: [
    {
      sentence: 'Băiatul mănâncă un măr.',
      words: [
        { w: 'Băiatul', g: 'garçon-le' }, { w: 'mănâncă', g: 'mange' },
        { w: 'un', g: 'une' }, { w: 'măr', g: 'pomme' },
      ],
      translation: 'Le garçon mange une pomme.',
      note: '« Băiatul » = « garçon-le » — l’article -ul est collé à la fin du nom.',
    },
    {
      sentence: 'Cartea este pe masă.',
      words: [
        { w: 'Cartea', g: 'livre-le' }, { w: 'este', g: 'est' }, { w: 'pe', g: 'sur' },
        { w: 'masă', g: 'table' },
      ],
      translation: 'Le livre est sur la table.',
      note: 'Là encore, l’article se greffe à la fin : « Cartea » = « livre-le ».',
    },
  ],
  tr: [
    {
      sentence: 'Çocuk elmayı yedi.',
      words: [
        { w: 'Çocuk', g: 'enfant' }, { w: 'elmayı', g: 'pomme-(objet)' },
        { w: 'yedi', g: 'a-mangé' },
      ],
      translation: 'L’enfant a mangé la pomme.',
      note: 'Verbe en dernier (SOV) ; la terminaison -yı marque « pomme » comme objet défini.',
    },
    {
      sentence: 'Evlerimizde.',
      words: [
        { w: 'Ev', g: 'maison' }, { w: '-ler', g: '(pluriel)' },
        { w: '-imiz', g: 'notre' }, { w: '-de', g: 'dans' },
      ],
      translation: 'Dans nos maisons.',
      note: 'Un seul mot = quatre mots français, bâti en empilant des suffixes (agglutination).',
    },
  ],
  sw: [
    {
      sentence: 'Mtoto anasoma kitabu.',
      words: [
        { w: 'Mtoto', g: 'enfant' }, { w: 'anasoma', g: 'il/elle-lit' },
        { w: 'kitabu', g: 'livre' },
      ],
      translation: 'L’enfant est en train de lire un livre.',
      note: '« a-na-soma » fond sujet + temps + verbe en un seul mot.',
    },
    {
      sentence: 'Vitabu vyangu viwili.',
      words: [
        { w: 'Vitabu', g: 'livres' }, { w: 'vyangu', g: 'mes' }, { w: 'viwili', g: 'deux' },
      ],
      translation: 'mes deux livres',
      note: 'La marque de classe vi- se répète sur chaque mot qui s’accorde avec « livres ».',
    },
  ],
  yo: [
    {
      sentence: 'Adé ra bàtà.',
      words: [{ w: 'Adé', g: 'Adé' }, { w: 'ra', g: 'a-acheté' }, { w: 'bàtà', g: 'chaussures' }],
      translation: 'Adé a acheté des chaussures.',
      note: 'L’ordre des mots est un SVO fixe ; c’est le ton (et non des terminaisons) qui fait le travail grammatical.',
    },
    {
      sentence: 'Ó mú ìwé wá.',
      words: [
        { w: 'Ó', g: 'il' }, { w: 'mú', g: 'a-pris' }, { w: 'ìwé', g: 'livre' },
        { w: 'wá', g: 'est-venu' },
      ],
      translation: 'Il a apporté le livre.',
      note: 'Deux verbes à la suite (mú … wá, « prendre … venir ») signifient ensemble « apporter » — un verbe sériel.',
    },
  ],
  ha: [
    {
      sentence: 'Yaro ya sayi doya.',
      words: [
        { w: 'Yaro', g: 'garçon' }, { w: 'ya', g: 'il-(accompli)' }, { w: 'sayi', g: 'acheter' },
        { w: 'doya', g: 'igname' },
      ],
      translation: 'Le garçon a acheté une igname.',
      note: '« ya » porte « il » + action accomplie, juste avant le verbe.',
    },
    {
      sentence: 'Yarinya ta tafi.',
      words: [
        { w: 'Yarinya', g: 'fille' }, { w: 'ta', g: 'elle-(accompli)' }, { w: 'tafi', g: 'partir' },
      ],
      translation: 'La fille est partie.',
      note: '« ta » marque un sujet féminin ; « ya » serait masculin.',
    },
  ],
  xh: [
    {
      sentence: 'Umntwana ufunda incwadi.',
      words: [
        { w: 'Umntwana', g: 'enfant' }, { w: 'ufunda', g: 'il/elle-lit' },
        { w: 'incwadi', g: 'livre' },
      ],
      translation: 'L’enfant lit un livre.',
      note: 'Les préfixes de classe (um-, in-) tissent l’accord à travers la phrase.',
    },
    {
      sentence: 'Abantwana bafunda.',
      words: [{ w: 'Abantwana', g: 'enfants' }, { w: 'bafunda', g: 'ils-lisent' }],
      translation: 'Les enfants lisent.',
      note: 'Préfixe pluriel aba- sur le nom, repris par ba- sur le verbe.',
    },
  ],
  mi: [
    {
      sentence: 'Kei te kai te tamaiti i te āporo.',
      words: [
        { w: 'Kei te kai', g: 'est-en-train-de-manger' }, { w: 'te', g: 'le' },
        { w: 'tamaiti', g: 'enfant' }, { w: 'i te', g: '(objet) la' },
        { w: 'āporo', g: 'pomme' },
      ],
      translation: 'L’enfant est en train de manger la pomme.',
      note: 'Verbe en PREMIER (VSO) ; la particule « i » marque l’objet.',
    },
    {
      sentence: 'He tangata ia.',
      words: [{ w: 'He', g: 'une' }, { w: 'tangata', g: 'personne' }, { w: 'ia', g: 'il' }],
      translation: 'C’est une personne.',
      note: 'Pas de verbe « être » — les mots sont simplement juxtaposés.',
    },
  ],
  jam: [
    {
      sentence: 'Mi a nyam di food.',
      words: [
        { w: 'Mi', g: 'je' }, { w: 'a', g: '(en-cours)' }, { w: 'nyam', g: 'manger' },
        { w: 'di', g: 'la' }, { w: 'food', g: 'nourriture' },
      ],
      translation: 'Je suis en train de manger la nourriture.',
      note: '« a » est une particule d’action en cours — le verbe lui-même ne change jamais.',
    },
    {
      sentence: 'Mi did nyam di food.',
      words: [
        { w: 'Mi', g: 'je' }, { w: 'did', g: '(passé)' }, { w: 'nyam', g: 'manger' },
        { w: 'di', g: 'la' }, { w: 'food', g: 'nourriture' },
      ],
      translation: 'J’ai mangé la nourriture.',
      note: '« did » pose le passé — on change la particule, et le verbe « nyam » ne bouge pas.',
    },
  ],
  en: [
    {
      sentence: 'The dog chased the cat.',
      words: [
        { w: 'The', g: 'le' }, { w: 'dog', g: 'chien' }, { w: 'chased', g: 'a-poursuivi' },
        { w: 'the', g: 'le' }, { w: 'cat', g: 'chat' },
      ],
      translation: 'Le chien a poursuivi le chat.',
      note: 'Échangez les noms et le sens s’inverse — l’ordre seul marque qui a fait quoi.',
    },
    {
      sentence: 'She looked after the kids.',
      words: [
        { w: 'She', g: 'elle' }, { w: 'looked', g: 'a-regardé' }, { w: 'after', g: 'après' },
        { w: 'the', g: 'les' }, { w: 'kids', g: 'enfants' },
      ],
      translation: 'Elle s’est occupée des enfants.',
      note: '« look after » = s’occuper de — un verbe à particule dont les parties composent un sens nouveau.',
    },
  ],
  nl: [
    {
      sentence: 'Vandaag koop ik brood.',
      words: [
        { w: 'Vandaag', g: 'aujourd’hui' }, { w: 'koop', g: 'achète' }, { w: 'ik', g: 'je' },
        { w: 'brood', g: 'pain' },
      ],
      translation: 'Aujourd’hui j’achète du pain.',
      note: 'Verbe en deuxième position, comme en allemand : « koop » précède le sujet « ik ».',
    },
    {
      sentence: 'Ik weet dat hij komt.',
      words: [
        { w: 'Ik', g: 'je' }, { w: 'weet', g: 'sais' }, { w: 'dat', g: 'que' },
        { w: 'hij', g: 'il' }, { w: 'komt', g: 'vient' },
      ],
      translation: 'Je sais qu’il vient.',
      note: 'Comme en allemand encore : « komt » file en fin de subordonnée.',
    },
  ],
  ru: [
    {
      sentence: 'Мальчик читает книгу.',
      words: [
        { w: 'Мальчик', g: 'garçon' }, { w: 'читает', g: 'lit' },
        { w: 'книгу', g: 'livre-(objet)' },
      ],
      translation: 'Le garçon lit un livre.',
      note: '« книгу » est l’accusatif de « книга » — c’est le cas, et non la position, qui marque l’objet, si bien que les mots peuvent se réordonner librement.',
    },
    {
      sentence: 'Я прочитал письмо.',
      words: [
        { w: 'Я', g: 'je' }, { w: 'прочитал', g: 'ai-lu-(achevé)' },
        { w: 'письмо', g: 'lettre' },
      ],
      translation: 'J’ai lu la lettre (jusqu’au bout).',
      note: 'Le perfectif « прочитал » dit que l’action a été menée à terme ; son pendant imperfectif « читал » décrirait le processus.',
    },
  ],
  el: [
    {
      sentence: 'Ο άντρας διαβάζει το βιβλίο.',
      words: [
        { w: 'Ο', g: 'le' }, { w: 'άντρας', g: 'homme' }, { w: 'διαβάζει', g: 'lit' },
        { w: 'το', g: 'le' }, { w: 'βιβλίο', g: 'livre' },
      ],
      translation: 'L’homme lit le livre.',
    },
    {
      sentence: 'Βλέπω τον άντρα.',
      words: [
        { w: 'Βλέπω', g: '(je)-vois' }, { w: 'τον', g: 'le-(objet)' },
        { w: 'άντρα', g: 'homme' },
      ],
      translation: 'Je vois l’homme.',
      note: 'L’article change selon le cas : τον (accusatif) vs ο (nominatif).',
    },
  ],
  ar: [
    {
      sentence: 'يقرأ الولد الكتاب.',
      words: [
        { w: 'يقرأ', g: 'lit' }, { w: 'الولد', g: 'le-garçon' },
        { w: 'الكتاب', g: 'le-livre' },
      ],
      translation: 'Le garçon lit le livre.',
      note: 'L’arabe classique ouvre par le verbe (VSO) ; se lit de droite à gauche.',
      rtl: true,
    },
    {
      sentence: 'الكتاب جديد.',
      words: [{ w: 'الكتاب', g: 'le-livre' }, { w: 'جديد', g: 'nouveau' }],
      translation: 'Le livre est nouveau.',
      note: 'Pas de verbe « être » au présent — juste « le livre » + « nouveau ».',
      rtl: true,
    },
  ],
  hi: [
    {
      sentence: 'लड़का किताब पढ़ता है।',
      words: [
        { w: 'लड़का', g: 'garçon' }, { w: 'किताब', g: 'livre' }, { w: 'पढ़ता', g: 'lit' },
        { w: 'है', g: 'est' },
      ],
      translation: 'Le garçon lit un livre.',
      note: 'Verbe en dernier (SOV) ; la phrase se clôt sur « है » (est).',
    },
    {
      sentence: 'लड़का घर में है।',
      words: [
        { w: 'लड़का', g: 'garçon' }, { w: 'घर', g: 'maison' }, { w: 'में', g: 'dans' },
        { w: 'है', g: 'est' },
      ],
      translation: 'Le garçon est dans la maison.',
      note: '« में » (dans) vient APRÈS le nom — une postposition, pas une préposition.',
    },
  ],
  th: [
    {
      sentence: 'เด็กกินข้าว',
      words: [{ w: 'เด็ก', g: 'enfant' }, { w: 'กิน', g: 'manger' }, { w: 'ข้าว', g: 'riz' }],
      translation: 'L’enfant mange du riz.',
      note: 'Isolante : aucun mot ne change jamais de forme ; il n’y a pas d’espaces entre les mots.',
    },
    {
      sentence: 'หนังสือสามเล่ม',
      words: [
        { w: 'หนังสือ', g: 'livre' }, { w: 'สาม', g: 'trois' }, { w: 'เล่ม', g: '(classificateur)' },
      ],
      translation: 'trois livres',
      note: 'Compter demande un classificateur — เล่ม pour les livres et autres objets plats et reliés.',
    },
  ],
  ko: [
    {
      sentence: '아이가 책을 읽어요.',
      words: [
        { w: '아이가', g: 'enfant-(sujet)' }, { w: '책을', g: 'livre-(objet)' },
        { w: '읽어요', g: 'lit' },
      ],
      translation: 'L’enfant lit un livre.',
      note: 'Verbe en dernier ; « -가 » marque le sujet et « -을 » l’objet.',
    },
    {
      sentence: '저는 학생이에요.',
      words: [
        { w: '저는', g: 'je-(thème)' }, { w: '학생이에요', g: 'suis-étudiant' },
      ],
      translation: 'Je suis étudiant.',
      note: '« -는 » marque le thème ; le verbe « être » se soude au nom 학생 (étudiant).',
    },
  ],
  he: [
    {
      sentence: 'הילד קורא ספר.',
      words: [
        { w: 'הילד', g: 'le-garçon' }, { w: 'קורא', g: 'lit' }, { w: 'ספר', g: 'un-livre' },
      ],
      translation: 'Le garçon lit un livre.',
      note: 'Sujet–Verbe–Objet ; se lit de droite à gauche.',
      rtl: true,
    },
    {
      sentence: 'הספר חדש.',
      words: [{ w: 'הספר', g: 'le-livre' }, { w: 'חדש', g: 'nouveau' }],
      translation: 'Le livre est nouveau.',
      note: 'Pas de verbe « être » au présent — juste « le-livre » + « nouveau ».',
      rtl: true,
    },
  ],
  la: [
    {
      sentence: 'Puella librum legit.',
      words: [
        { w: 'Puella', g: 'fille' }, { w: 'librum', g: 'livre-(objet)' }, { w: 'legit', g: 'lit' },
      ],
      translation: 'La fille lit le livre.',
      note: 'Un ordre neutre courant (Sujet–Objet–Verbe), mais les terminaisons casuelles autoriseraient tous les réagencements.',
    },
    {
      sentence: 'Liber novus est.',
      words: [{ w: 'Liber', g: 'livre' }, { w: 'novus', g: 'nouveau' }, { w: 'est', g: 'est' }],
      translation: 'Le livre est nouveau.',
      note: 'Aucun mot pour « le » — liber seul peut signifier « livre », « un livre » ou « le livre ».',
    },
  ],
  fa: [
    {
      sentence: 'پسر کتاب می‌خواند.',
      words: [
        { w: 'پسر', g: 'garçon' }, { w: 'کتاب', g: 'livre' }, { w: 'می‌خواند', g: 'lit' },
      ],
      translation: 'Le garçon lit le livre.',
      note: 'Sujet–Objet–Verbe — le verbe vient en dernier, à la différence de l’arabe.',
      rtl: true,
    },
    {
      sentence: 'این کتاب خوب است.',
      words: [
        { w: 'این', g: 'ce' }, { w: 'کتاب', g: 'livre' }, { w: 'خوب', g: 'bon' }, { w: 'است', g: 'est' },
      ],
      translation: 'Ce livre est bon.',
      rtl: true,
    },
  ],
  id: [
    {
      sentence: 'Anak itu membaca buku.',
      words: [
        { w: 'Anak', g: 'enfant' }, { w: 'itu', g: 'ce/le' }, { w: 'membaca', g: 'lit' }, { w: 'buku', g: 'livre' },
      ],
      translation: 'L’enfant lit un livre.',
      note: '« Itu » (« ce ») suit le nom et fait office de « le ».',
    },
    {
      sentence: 'Saya membeli buku-buku itu.',
      words: [
        { w: 'Saya', g: 'je' }, { w: 'membeli', g: 'ai-acheté' }, { w: 'buku-buku', g: 'livres-(doublé)' }, { w: 'itu', g: 'ces' },
      ],
      translation: 'J’ai acheté ces livres.',
      note: 'Le pluriel, c’est le mot dit deux fois : buku (livre) → buku-buku (livres). Pas de marque de temps non plus — le contexte s’en charge.',
    },
  ],
  tl: [
    {
      sentence: 'Kumain ang bata ng mansanas.',
      words: [
        { w: 'Kumain', g: 'a-mangé' }, { w: 'ang bata', g: 'l’enfant' }, { w: 'ng mansanas', g: 'une-pomme' },
      ],
      translation: 'L’enfant a mangé une pomme.',
      note: 'Verbe d’abord — l’agent et la chose affectée suivent, marqués par ang et ng.',
    },
    {
      sentence: 'Naglalakad siya araw-araw.',
      words: [
        { w: 'Naglalakad', g: 'marche' }, { w: 'siya', g: 'il/elle' }, { w: 'araw-araw', g: 'jour-jour' },
      ],
      translation: 'Il/elle marche chaque jour.',
      note: 'Redoublement encore : araw (jour) doublé signifie « chaque jour ».',
    },
  ],
}
