/**
 * Spanish (es) overlay for the "About this language" reference: every course's
 * facts and glossed word-order examples, hand-authored in Spanish. Sentences
 * and per-word forms stay in the course language; only glosses/notes translate.
 */
import type { LanguageFacts, SyntaxExample } from './languageFacts'

const esEs: LanguageFacts = {
  tagline: 'Una lengua romance de alcance extraordinario y ortografía honesta.',
  family: 'Indoeuropea › Itálica › Romance (iberorromance)',
  speakers: '~485 millones de hablantes nativos: solo el chino mandarín la supera.',
  whereSpoken: 'España, casi toda América Latina, Guinea Ecuatorial y amplias zonas de Estados Unidos.',
  writingSystem: 'Alfabeto latino, más la ñ y las marcas á é í ó ú ü. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto, pero flexible: las terminaciones dicen tanto que el sujeto suele omitirse.',
  history:
    'Surgió del latín hablado de la Hispania romana y tomó forma como castellano en los reinos medievales del norte de España. Después el imperio lo llevó al otro lado del Atlántico, donde hoy vive la mayoría de sus hablantes.',
  unique: [
    'Los verbos cargan con el peso: una sola palabra marca persona, tiempo y modo, así que los pronombres suelen omitirse.',
    'Todo sustantivo es masculino o femenino, y los adjetivos concuerdan con él.',
    'Dos verbos para «to be» del inglés: ser (permanente) frente a estar (temporal o de lugar).',
    'Los signos invertidos ¿ y ¡ abren preguntas y exclamaciones.',
  ],
}

const frEs: LanguageFacts = {
  tagline: 'Una lengua romance donde mucho se escribe pero no se pronuncia.',
  family: 'Indoeuropea › Itálica › Romance (galorromance)',
  speakers: '~80 millones de hablantes nativos, ~300 millones en total en cinco continentes.',
  whereSpoken: 'Francia, Bélgica, Suiza, Quebec y buena parte de África Occidental y Central.',
  writingSystem: 'Alfabeto latino con acentos (é è ê ë), la cedilla (ç) y ligaduras (œ). De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto, bastante rígido: el pronombre sujeto no se mueve.',
  history:
    'Desciende del latín vulgar de la Galia y emergió como la langue d’oïl del norte. Siglos de prestigio cortesano y la Académie française moldearon el pulcro estándar actual.',
  unique: [
    'Muchas letras finales son mudas, pero reaparecen como liaisons ante una vocal.',
    'Las vocales nasales (on, an, in) no tienen equivalente directo en español.',
    'Los sustantivos llevan género, y artículos y adjetivos concuerdan.',
    'El vous formal frente al tu familiar marca el registro social de cada «tú».',
  ],
}

const deEs: LanguageFacts = {
  tagline: 'Una lengua germánica que guarda el verbo para el final.',
  family: 'Indoeuropea › Germánica (germánica occidental)',
  speakers: '~95 millones de hablantes nativos: la primera lengua más hablada de la UE.',
  whereSpoken: 'Alemania, Austria, Suiza, Liechtenstein y enclaves en Bélgica, Italia y más allá.',
  writingSystem: 'Alfabeto latino más ä ö ü y ß. Los sustantivos siempre se escriben con mayúscula. De izquierda a derecha.',
  wordOrder: 'Verbo en segunda posición en las oraciones principales, al final en las subordinadas: el famoso «verbo al final».',
  history:
    'Surgió de dialectos germánicos occidentales transformados por la mutación consonántica del alto alemán. La traducción de la Biblia de Lutero hizo mucho por forjar un estándar escrito único.',
  unique: [
    'Cuatro casos (nominativo, acusativo, dativo, genitivo) cambian artículos y terminaciones.',
    'Tres géneros, y der/die/das rara vez siguen el significado.',
    'Las palabras se apilan en largos compuestos (Handschuh = zapato de mano = guante).',
    'Los verbos separables se parten en dos: «ich stehe früh auf» (me levanto temprano).',
  ],
}

const itEs: LanguageFacts = {
  tagline: 'La lengua romance más cercana a su madre latina.',
  family: 'Indoeuropea › Itálica › Romance (italodálmata)',
  speakers: '~65 millones de hablantes nativos.',
  whereSpoken: 'Italia, San Marino, Ciudad del Vaticano y el Tesino suizo.',
  writingSystem: 'Alfabeto latino con acentos graves y agudos (à, é). De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto, flexible: el sujeto se omite a menudo.',
  history:
    'El italiano estándar nació del toscano de Florencia, elevado por Dante, Petrarca y Boccaccio, y solo se convirtió en lengua hablada compartida en todo el país tras la unificación de la década de 1860.',
  unique: [
    'Las consonantes dobles se pronuncian largas y pueden cambiar el significado (pala frente a palla).',
    'Gramaticalmente, la gran lengua romance más conservadora: muy cercana al latín.',
    'Sustantivos y adjetivos concuerdan en género y número.',
    'Una entonación rica y musical, con vocales abiertas y claras.',
  ],
}

const caEs: LanguageFacts = {
  tagline: 'Una lengua romance que tiende un puente entre España y Francia.',
  family: 'Indoeuropea › Itálica › Romance (occitanorromance)',
  speakers: '~9 millones de hablantes nativos.',
  whereSpoken: 'Cataluña, Valencia, las Islas Baleares, Andorra (donde es la única lengua oficial) y Alguer, en Cerdeña.',
  writingSystem: 'Alfabeto latino con el punto volado (l·l) y acentos. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto, flexible y con omisión del sujeto.',
  history:
    'Se formó a partir del latín vulgar y floreció como lengua literaria y jurídica medieval. Reprimido bajo Franco, resurgió y hoy es central en la identidad catalana.',
  unique: [
    'Se sitúa entre el español y el francés: familiar para ambos, idéntico a ninguno.',
    'Los pronombres débiles de objeto (em, et, es, hi, en) se adhieren alrededor del verbo.',
    'Una vocal neutra (schwa) característica en los dialectos orientales.',
    'Una lengua literaria y oficial de pleno derecho, no un dialecto del español.',
  ],
}

const ptEs: LanguageFacts = {
  tagline: 'Una lengua romance del mundo atlántico.',
  family: 'Indoeuropea › Itálica › Romance (iberorromance)',
  speakers: '~230 millones de hablantes nativos, la mayoría en Brasil.',
  whereSpoken: 'Brasil, Portugal, Angola, Mozambique, Cabo Verde y otras antiguas colonias marítimas.',
  writingSystem: 'Alfabeto latino con ã õ, ç y acentos. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto, flexible y con omisión del sujeto.',
  history:
    'Nació del gallegoportugués en el noroeste de la península ibérica y se extendió por el mundo con las rutas marítimas de Portugal, dividiéndose en dos estándares diferenciados, el europeo y el brasileño.',
  unique: [
    'Vocales y diptongos nasales (pão, mãe, coração).',
    'Un infinitivo personal: el infinitivo puede llevar terminaciones para cada persona.',
    'Un futuro de subjuntivo vivo, perdido en la mayoría de las lenguas romances.',
    'Las variedades europea y brasileña difieren notablemente en sonido y ritmo.',
  ],
}

const roEs: LanguageFacts = {
  tagline: 'La lengua romance de Oriente, moldeada por sus vecinos.',
  family: 'Indoeuropea › Itálica › Romance (romance oriental)',
  speakers: '~24 millones de hablantes nativos.',
  whereSpoken: 'Rumanía y Moldavia.',
  writingSystem: 'Alfabeto latino con ă, â, î, ș, ț. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto, flexible gracias a la marcación de casos.',
  history:
    'Desciende del latín de la Dacia romana y evolucionó durante siglos aislado del resto del mundo romance, profundamente marcado por sus vecinos eslavos y balcánicos.',
  unique: [
    'La única gran lengua romance que conservó los casos gramaticales.',
    'El artículo definido se pega al final del sustantivo: lup → lupul (el lobo).',
    'Conservó un género neutro junto al masculino y el femenino.',
    'Comparte rasgos balcánicos (como el artículo pospuesto) con vecinos no emparentados.',
  ],
}

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

const swEs: LanguageFacts = {
  tagline: 'El gran conector de África Oriental, bantú de corazón.',
  family: 'Níger-Congo › Atlántico-Congo › Bantú',
  speakers: '~5 millones de hablantes nativos, pero más de 80 millones la comparten como segunda lengua.',
  whereSpoken: 'Tanzania, Kenia, Uganda, la RDC y toda la región de los Grandes Lagos africanos.',
  writingSystem: 'Alfabeto latino (históricamente también escritura árabe). De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto.',
  history:
    'Una lengua bantú de la costa de África Oriental, moldeada por mil años de comercio en el Índico —de ahí sus muchos préstamos árabes— y extendida después hacia el interior como lengua franca.',
  unique: [
    'Los sustantivos se reparten en ~15 clases; la clase gobierna la concordancia de toda la oración.',
    'Los verbos aglutinan sujeto, tiempo, objeto y más en una sola palabra.',
    'Algo inusual para una lengua bantú: no es tonal.',
    'Una rica capa de vocabulario árabe (safari, kitabu, asante) descansa sobre la base bantú.',
  ],
}

const yoEs: LanguageFacts = {
  tagline: 'Una lengua de África Occidental donde el tono lleva el significado.',
  family: 'Níger-Congo › Atlántico-Congo › Volta-Níger',
  speakers: '~45 millones.',
  whereSpoken: 'El suroeste de Nigeria, Benín y Togo, además de una profunda diáspora en las Américas.',
  writingSystem: 'Alfabeto latino con puntos suscritos (ẹ, ọ, ṣ) y marcas de tono. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto.',
  history:
    'La lengua de las civilizaciones de Ifẹ̀ y Ọ̀yọ́, llevada al otro lado del Atlántico durante la trata de esclavos y preservada en las tradiciones religiosas de Cuba y Brasil.',
  unique: [
    'Tres tonos (alto, medio, bajo) distinguen palabras por lo demás idénticas.',
    'Las construcciones de verbos seriales encadenan varios verbos en una sola cláusula.',
    'Las letras con punto suscrito marcan vocales y consonantes distintas.',
    'Una rica tradición de proverbios entretejida en el habla cotidiana.',
  ],
}

const haEs: LanguageFacts = {
  tagline: 'Una lengua chádica y el idioma comercial del Sahel.',
  family: 'Afroasiática › Chádica',
  speakers: 'Más de ~50 millones, y lengua franca para muchos más.',
  whereSpoken: 'El norte de Nigeria y Níger, y por toda África Occidental y el Sahel.',
  writingSystem: 'Alfabeto latino (boko) con letras ganchudas (ɓ, ɗ, ƙ); también se escribe en alfabeto árabe (ajami). De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto.',
  history:
    'Una lengua chádica —prima lejana del árabe y el hebreo— difundida mucho más allá de su tierra natal por siglos de comercio transahariano y erudición islámica.',
  unique: [
    'Dos tonos más la duración vocálica dan forma al significado de las palabras.',
    'Consonantes glotalizadas «ganchudas»: ɓ, ɗ, ƙ.',
    'El género gramatical aparece en singular pero desaparece en plural.',
    'Un sistema de «grados» verbales codifica dirección y compleción.',
  ],
}

const xhEs: LanguageFacts = {
  tagline: 'Una lengua nguni famosa por sus clics.',
  family: 'Níger-Congo › Atlántico-Congo › Bantú (nguni)',
  speakers: '~8 millones de hablantes nativos.',
  whereSpoken: 'Sudáfrica, sobre todo el Cabo Oriental; es una de sus 11 lenguas oficiales.',
  writingSystem: 'Alfabeto latino; las letras c, x, q representan tres clics distintos. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto.',
  history:
    'Una lengua bantú del grupo nguni, estrechamente emparentada con el zulú. El contacto con los pueblos joisanos le dio las consonantes de clic que la hacen inconfundible.',
  unique: [
    'Tres consonantes de clic —dental (c), lateral (x) y palatal (q)— tomadas de las lenguas joisanas.',
    'Un sistema de clases nominales que enhebra la concordancia por toda la oración.',
    'Es tonal, aunque el tono no se escribe.',
    'Prefijos de concordancia enlazan cada palabra con la clase de su sustantivo.',
  ],
}

const miEs: LanguageFacts = {
  tagline: 'La lengua polinesia de Aotearoa, con el verbo primero.',
  family: 'Austronesia › Malayo-polinesia › Polinesia',
  speakers: '~150 000–190 000, y en constante recuperación.',
  whereSpoken: 'Nueva Zelanda (Aotearoa).',
  writingSystem: 'Alfabeto latino; los macrones (ā, ē, ī, ō, ū) marcan las vocales largas. De izquierda a derecha.',
  wordOrder: 'Verbo–Sujeto–Objeto: el verbo va primero.',
  history:
    'Una lengua polinesia oriental llevada a Nueva Zelanda hacia el siglo XIV. Al borde de la desaparición en el siglo XX, ha sido revitalizada mediante los kōhanga reo (nidos de lengua) y la enseñanza por inmersión.',
  unique: [
    'Oraciones con el verbo primero (VSO), algo inusual entre las lenguas de esta lista.',
    'Un sistema de sonidos pequeño: diez consonantes y cinco vocales (breves y largas).',
    'Pequeñas partículas, no terminaciones, marcan el tiempo y la función.',
    'Los macrones distinguen palabras: keke (pastel) frente a kēkē (axila).',
  ],
}

const jamEs: LanguageFacts = {
  tagline: 'Un criollo de léxico inglés con gramática de África Occidental.',
  family: 'Criollo de base inglesa (atlántico)',
  speakers: '~3 millones, más una gran diáspora.',
  whereSpoken: 'Jamaica y las comunidades jamaicanas de todo el mundo.',
  writingSystem: 'Alfabeto latino, escrito tanto con una ortografía de base inglesa como con el sistema fonético Cassidy/JLU. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto.',
  history:
    'Nació en las plantaciones de la época colonial, donde africanos occidentales esclavizados construyeron una lengua nueva con vocabulario inglés y la gramática del akan, el igbo y otras lenguas.',
  unique: [
    'Los verbos no se conjugan: el tiempo lo dan partículas (mi did go, mi a go).',
    'Pronombres propios: mi, yu, im, wi, unu, dem.',
    'La reduplicación intensifica (chaka-chaka = desordenado).',
    'Palabras inglesas, pero una gramática enteramente propia.',
  ],
}

const enEs: LanguageFacts = {
  tagline: 'Una lengua germánica que tomó prestado de todo el mundo.',
  family: 'Indoeuropea › Germánica (germánica occidental)',
  speakers: '~380 millones de hablantes nativos, ~1500 millones en total: la lengua franca mundial.',
  whereSpoken: 'El Reino Unido, Irlanda, Norteamérica, Australia, Nueva Zelanda y, como segunda lengua, casi todas partes.',
  writingSystem: 'Alfabeto latino, 26 letras, sin diacríticos. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto, bastante rígido: el orden de palabras hace el trabajo que antes hacían los casos.',
  history:
    'Empezó como anglosajón (inglés antiguo), fue transformado por los colonos nórdicos y luego por una avalancha de francés normando tras 1066, y se extendió por el mundo con el Imperio británico y la influencia estadounidense.',
  unique: [
    'Un vocabulario enorme: un núcleo germánico con capas de latín, francés y griego.',
    'Muy poca flexión: los sustantivos apenas cambian y no hay género gramatical.',
    'Una ortografía notoriamente irregular, fósil de pronunciaciones antiguas.',
    'Los verbos frasales (give up, put off, run into) llevan significado idiomático.',
  ],
}

const nlEs: LanguageFacts = {
  tagline: 'La lengua germánica occidental entre el inglés y el alemán.',
  family: 'Indoeuropea › Germánica (germánica occidental)',
  speakers: '~25 millones de hablantes nativos.',
  whereSpoken: 'Países Bajos, Bélgica (Flandes), Surinam y el Caribe neerlandés.',
  writingSystem: 'Alfabeto latino; el dígrafo «ij» se comporta como una sola letra. De izquierda a derecha.',
  wordOrder: 'Verbo en segunda posición en las oraciones principales, al final en las subordinadas, como en alemán.',
  history:
    'Una lengua franconia baja que nunca pasó por la mutación consonántica del alemán, lo que la deja gramatical y léxicamente a medio camino entre el inglés y el alemán.',
  unique: [
    'El orden de verbo en segunda posición manda los verbos al final de las subordinadas.',
    'Dos géneros: común (de) y neutro (het).',
    'Una «g» célebremente gutural.',
    'Los diminutivos en -je están por todas partes y suavizan el tono.',
  ],
}

const ruEs: LanguageFacts = {
  tagline: 'Una lengua eslava de casos y aspecto verbal.',
  family: 'Indoeuropea › Baltoeslava › Eslava oriental',
  speakers: '~150 millones de hablantes nativos, y muy hablada como segunda lengua.',
  whereSpoken: 'Rusia y buena parte de la antigua Unión Soviética.',
  writingSystem: 'Alfabeto cirílico, adaptado del griego. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto oficialmente, pero el orden es muy libre: los casos muestran quién hace qué.',
  history:
    'Una lengua eslava oriental escrita en cirílico desde la cristianización de la Rus, muy influida por el antiguo eslavo eclesiástico y estandarizada sobre el dialecto de Moscú.',
  unique: [
    'Seis casos remodelan sustantivos, adjetivos y pronombres.',
    'Cada verbo viene en pareja aspectual: imperfectivo (proceso) frente a perfectivo (resultado).',
    'No hay palabras para «un» ni «el».',
    'La distinción entre consonantes duras y blandas (palatalización) recorre todo el sistema de sonidos.',
  ],
}

const elEs: LanguageFacts = {
  tagline: 'Una lengua con 3400 años de profundidad, en su propia rama.',
  family: 'Indoeuropea › Helénica (una rama propia)',
  speakers: '~13 millones de hablantes nativos.',
  whereSpoken: 'Grecia y Chipre.',
  writingSystem: 'El alfabeto griego, antepasado del latino y del cirílico. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto, flexible gracias a las terminaciones de caso.',
  history:
    'La lengua indoeuropea documentada más antigua que aún se habla, con un registro escrito continuo desde el griego micénico, pasando por el antiguo y la koiné, hasta hoy.',
  unique: [
    'Un alfabeto propio, del que descienden el latino y el cirílico.',
    'Cuatro casos y tres géneros.',
    'Una sola raíz griega sustenta una parte enorme del vocabulario científico.',
    'El acento de intensidad moderno sustituyó al antiguo acento tonal.',
  ],
}

const arEs: LanguageFacts = {
  tagline: 'Una lengua semítica construida sobre raíces de tres letras.',
  family: 'Afroasiática › Semítica',
  speakers: '~310 millones de hablantes nativos entre sus muchas variedades.',
  whereSpoken: 'Oriente Medio y el norte de África, y litúrgicamente en todo el mundo musulmán.',
  writingSystem: 'La escritura árabe, de derecha a izquierda y ligada en cursiva.',
  wordOrder: 'Verbo–Sujeto–Objeto en la lengua clásica; muchos dialectos prefieren Sujeto–Verbo–Objeto.',
  history:
    'Una lengua semítica cuya forma clásica quedó fijada por el Corán. Hoy un estándar formal (el árabe estándar moderno) se comparte en toda la región mientras cada cual habla un dialecto local: una situación llamada diglosia.',
  unique: [
    'Las palabras se construyen sobre raíces de tres consonantes: k-t-b da kitāb (libro), kātib (escritor), maktab (oficina).',
    'Se escribe de derecha a izquierda, con letras que cambian de forma según su posición.',
    'Un número dual, distinto del singular y del plural.',
    'Consonantes enfáticas y faríngeas sin equivalente en español.',
  ],
}

const hiEs: LanguageFacts = {
  tagline: 'Una lengua indoaria que pone el verbo al final.',
  family: 'Indoeuropea › Indoirania › Indoaria',
  speakers: '~340 millones de hablantes nativos (su forma hablada es casi idéntica al urdu).',
  whereSpoken: 'El norte y el centro de la India.',
  writingSystem: 'El abugida devanagari: cada consonante lleva una vocal inherente. De izquierda a derecha.',
  wordOrder: 'Sujeto–Objeto–Verbo.',
  history:
    'Descendiente del sánscrito a través de los prácritos, absorbió vocabulario persa y árabe bajo los mogoles; el registro hablado que comparte con el urdu suele llamarse indostaní.',
  unique: [
    'Posposiciones en lugar de preposiciones («a la casa» → «casa-a»).',
    'Ergatividad escindida: la marca ne aparece en el sujeto de los transitivos en pasado.',
    'Los verbos concuerdan en género, así que las frases cambian según quién habla o actúa.',
    'Tres niveles de «tú» (tū, tum, āp) gradúan la cortesía.',
  ],
}

const thEs: LanguageFacts = {
  tagline: 'Una lengua tonal y aislante que se escribe sin espacios.',
  family: 'Kra-dai › Tai',
  speakers: '~60 millones de hablantes nativos.',
  whereSpoken: 'Tailandia.',
  writingSystem: 'El abugida tailandés: un alfabeto con marcas de tono y sin espacios entre palabras. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto.',
  history:
    'Una lengua tai cuyos hablantes migraron hacia el sur desde lo que hoy es el sur de China, incorporando por capas vocabulario pali, sánscrito y jemer; su escritura desciende de la jemer.',
  unique: [
    'Cinco tonos: la misma sílaba significa cinco cosas distintas.',
    'Aislante: las palabras nunca cambian de forma; la gramática descansa en el orden y las partículas.',
    'Contar exige un clasificador según el tipo de cosa que se cuenta.',
    'Partículas de cortesía (khráp para hombres, khâ para mujeres) cierran las frases.',
  ],
}

const koEs: LanguageFacts = {
  tagline: 'Una lengua aislada con un alfabeto diseñado científicamente.',
  family: 'Coreánica (una lengua aislada)',
  speakers: '~80 millones de hablantes nativos.',
  whereSpoken: 'Corea del Sur y del Norte, y una amplia diáspora.',
  writingSystem: 'El hangul: un alfabeto de rasgos cuyas letras se agrupan en bloques silábicos. De izquierda a derecha.',
  wordOrder: 'Sujeto–Objeto–Verbo.',
  history:
    'El coreano está solo, sin parientes probados. Escrito durante siglos con caracteres chinos, recibió el hangul —encargado por el rey Sejong en 1443—, una escritura diseñada deliberadamente para ser fácil de aprender.',
  unique: [
    'Las letras del hangul reflejan en su forma cómo la boca produce cada sonido.',
    'Elaborados niveles honoríficos y de habla remodelan los verbos según el contexto social.',
    'Aglutinante: partículas y terminaciones se adhieren para marcar función y matiz.',
    'Un marcador de tema (은/는) destaca de qué trata la frase.',
  ],
}

const heEs: LanguageFacts = {
  tagline: 'Una lengua semítica revivida del papel al habla cotidiana.',
  family: 'Afroasiática › Semítica (semítica noroccidental, cananea)',
  speakers: '~9 millones de hablantes nativos, casi todos en Israel.',
  whereSpoken: 'Israel, y comunidades judías de todo el mundo (litúrgicamente desde la Antigüedad).',
  writingSystem: 'El abyad hebreo, escrito de derecha a izquierda. Las vocales normalmente no se marcan; los puntos del niqud las muestran en textos didácticos, poesía y libros de oración.',
  wordOrder: 'Sujeto–Verbo–Objeto hoy (el hebreo bíblico prefería Verbo–Sujeto–Objeto).',
  history:
    'La lengua cananea de la Biblia hebrea sobrevivió como lengua de la ley, la liturgia y la erudición judías durante casi dos milenios después de dejar de ser el habla diaria de nadie. Revivida como lengua vernácula desde finales del siglo XIX, se convirtió en la lengua oficial de Israel: una de las únicas revitalizaciones lingüísticas plenas y exitosas de la historia.',
  unique: [
    'Morfología de raíz y patrón: tres consonantes llevan el significado central y el patrón moldea la palabra — k-t-b da katav (él escribió) y mikhtav (carta).',
    'La escritura corriente no lleva vocal alguna: el lector fluido las repone por contexto.',
    'Los verbos marcan género además de persona y número, incluso en presente.',
    'Una lengua revivida: una brecha real separa el antiguo hebreo bíblico del hebreo moderno vivo que se habla hoy.',
  ],
}

const laEs: LanguageFacts = {
  tagline: 'La lengua clásica de la que nacieron todas las romances.',
  family: 'Indoeuropea › Itálica',
  speakers: 'Hoy sin hablantes nativos: se estudia en todo el mundo y sigue usándose en la liturgia.',
  whereSpoken:
    'Sin comunidad viva; conserva estatus ceremonial y oficial en la Ciudad del Vaticano y en la liturgia de la Iglesia católica.',
  writingSystem: 'El alfabeto latino, antepasado directo del que usa el español. De izquierda a derecha.',
  wordOrder:
    'Flexible: las terminaciones de caso marcan la función gramatical de cada palabra, así que el orden queda libre para el énfasis en vez de fijado por la gramática.',
  history:
    'La lengua de la antigua Roma se extendió por el Mediterráneo y Europa occidental con el Imperio romano, y luego evolucionó localmente hasta convertirse en las lenguas romances —español, francés, italiano, portugués, rumano y más—, mientras seguía siendo la lengua de la erudición medieval, la Iglesia y la ciencia durante siglos tras la caída de Roma.',
  unique: [
    'Los sustantivos se declinan en casos (nominativo, genitivo, dativo, acusativo, ablativo y un vocativo residual) que marcan su función en la frase.',
    'Sin artículo alguno: puella por sí sola puede significar «niña», «una niña» o «la niña».',
    'Los verbos se conjugan en persona, número, tiempo, modo y voz, y a menudo hacen innecesario el pronombre.',
    'El antepasado directo de las lenguas romances: buena parte de su vocabulario y su gramática pervive, transformada, en español, francés, italiano, portugués y rumano.',
  ],
}

const faEs: LanguageFacts = {
  tagline: 'Una lengua indoeuropea escrita en una escritura semítica prestada.',
  family: 'Indoeuropea › Indoirania (irania occidental)',
  speakers: '~70 millones de hablantes nativos, más los de sus parientes cercanos, el darí y el tayiko.',
  whereSpoken: 'Irán (farsi/persa), Afganistán (darí) y Tayikistán (tayiko).',
  writingSystem: 'Una escritura árabe modificada, de derecha a izquierda; las vocales breves suelen quedar sin escribir, como en árabe.',
  wordOrder: 'Sujeto–Objeto–Verbo, a diferencia del orden con verbo inicial del árabe.',
  history:
    'Una lengua irania descendiente del persa antiguo, la lengua del Imperio aqueménida, a través del persa medio (pahlavi). Tras la conquista islámica adoptó la escritura árabe y absorbió un amplio vocabulario árabe, conservando siempre su gramática indoeuropea: genéticamente no tiene nada que ver con el árabe, por mucho que compartan alfabeto.',
  unique: [
    'Gramática indoeuropea vestida con una escritura de origen árabe: las dos lenguas no están emparentadas, sugiera lo que sugiera el alfabeto.',
    'Sin género gramatical y sin sistema de casos: una morfología inusualmente regular para una lengua indoeuropea.',
    'El ezāfe: una -e átona, normalmente no escrita, que une un sustantivo con lo que le sigue — un adjetivo, un poseedor, otro sustantivo.',
    'El verbo va al final, y «ser» es a menudo un sufijo ligero fundido al predicado más que una palabra aparte.',
  ],
}

const idEs: LanguageFacts = {
  tagline: 'Una lengua nacional elegida a propósito para pertenecer a todos.',
  family: 'Austronesia › Malayo-polinesia (maláyica)',
  speakers: '~270 millones de hablantes en Indonesia, la mayoría como segunda lengua muy fluida.',
  whereSpoken: 'Indonesia; su lengua nacional y oficial en un archipiélago con cientos de lenguas locales.',
  writingSystem: 'El alfabeto latino, con ortografía fonética y sin diacríticos en el uso estándar. De izquierda a derecha.',
  wordOrder: 'Sujeto–Verbo–Objeto.',
  history:
    'Una forma estandarizada del malayo, adoptada como lengua nacional unificadora de Indonesia en la independencia precisamente porque no era la lengua materna dominante de ninguna etnia: una pieza deliberada de planificación lingüística, y una de las más exitosas de la historia, en un país con cientos de lenguas locales.',
  unique: [
    'Sin conjugación verbal alguna: una sola forma cubre toda persona, número y tiempo; el tiempo lo llevan palabras aparte como sudah («ya») y akan (futuro).',
    'El plural se forma a menudo simplemente doblando la palabra: buku (libro) → buku-buku (libros).',
    'Capas de prefijos y sufijos remodelan el significado y la función de una raíz: ajar (enseñar) → belajar (estudiar) → mengajar (dar clase) → pelajaran (lección).',
    'Sin género gramatical, sin artículos y con pronombres que no cambian de forma entre sujeto y objeto.',
  ],
}

const tlEs: LanguageFacts = {
  tagline: 'Una lengua austronesia que pone el verbo primero.',
  family: 'Austronesia › Malayo-polinesia (filipina)',
  speakers: '~28 millones de hablantes nativos; la entiende, como filipino, la mayoría de los 110 millones de habitantes de Filipinas.',
  whereSpoken: 'Filipinas, con centro en Manila y Luzón; en todo el país como filipino, una de las dos lenguas oficiales.',
  writingSystem: 'El alfabeto latino, con ortografía fonética. De izquierda a derecha. (Antes de la colonización española se escribía en el silabario baybayin.)',
  wordOrder: 'Verbo inicial: el predicado abre la frase, por delante del agente y de lo que recibe la acción.',
  history:
    'Una lengua austronesia de las islas filipinas que se convirtió en la base del filipino, la lengua nacional, con la independencia: una de las dos lenguas oficiales junto al inglés, enseñada en todo el país junto a decenas de las demás lenguas vivas del archipiélago.',
  unique: [
    'Frases con el verbo primero: el verbo suele abrir la cláusula, y pequeñas partículas (ang, ng, sa) marcan quién hizo qué a qué.',
    'Un sistema de «foco»: el afijo del verbo cambia según si el sujeto es el agente, lo afectado, el lugar u otra cosa — un sello de las lenguas filipinas.',
    'Reduplicación extensa, como en indonesio: araw (día) → araw-araw (cada día).',
    'Siglos de préstamos del español y, más recientemente, del inglés conviven con su núcleo austronesio nativo.',
  ],
}

export const FACTS_ES: Record<string, LanguageFacts> = {
  es: esEs, fr: frEs, de: deEs, it: itEs, ca: caEs, pt: ptEs, ro: roEs, tr: trEs,
  sw: swEs, yo: yoEs, ha: haEs, xh: xhEs, mi: miEs, jam: jamEs, en: enEs, nl: nlEs,
  ru: ruEs, el: elEs, ar: arEs, hi: hiEs, th: thEs, ko: koEs, he: heEs, la: laEs,
  fa: faEs, id: idEs, tl: tlEs,
}

export const SYNTAX_ES: Record<string, SyntaxExample[]> = {
  es: [
    {
      sentence: 'El niño come una manzana.',
      words: [
        { w: 'El', g: 'el' }, { w: 'niño', g: 'niño' }, { w: 'come', g: 'come' },
        { w: 'una', g: 'una' }, { w: 'manzana', g: 'manzana' },
      ],
      translation: 'El niño come una manzana.',
      note: 'Sujeto–Verbo–Objeto; el artículo concuerda con el sustantivo.',
    },
    {
      sentence: '¿Hablas español?',
      words: [{ w: '¿Hablas', g: '(tú)-hablas' }, { w: 'español?', g: 'español' }],
      translation: '¿Hablas español?',
      note: 'No hace falta decir «tú»: la terminación -as ya lo expresa (omisión del sujeto).',
    },
  ],
  fr: [
    {
      sentence: 'Le garçon mange une pomme.',
      words: [
        { w: 'Le', g: 'el' }, { w: 'garçon', g: 'niño' }, { w: 'mange', g: 'come' },
        { w: 'une', g: 'una' }, { w: 'pomme', g: 'manzana' },
      ],
      translation: 'El niño come una manzana.',
    },
    {
      sentence: 'Je ne mange pas de viande.',
      words: [
        { w: 'Je', g: 'yo' }, { w: 'ne', g: '(no)' }, { w: 'mange', g: 'como' },
        { w: 'pas', g: '(no)' }, { w: 'de', g: 'de' }, { w: 'viande', g: 'carne' },
      ],
      translation: 'No como carne.',
      note: 'La negación envuelve al verbo en dos piezas: ne … pas.',
    },
  ],
  de: [
    {
      sentence: 'Heute esse ich einen Apfel.',
      words: [
        { w: 'Heute', g: 'hoy' }, { w: 'esse', g: 'como' }, { w: 'ich', g: 'yo' },
        { w: 'einen', g: 'una' }, { w: 'Apfel', g: 'manzana' },
      ],
      translation: 'Hoy como una manzana.',
      note: 'El verbo «esse» ocupa el SEGUNDO lugar y empuja al sujeto «ich» detrás de él.',
    },
    {
      sentence: 'Ich weiß, dass er heute kommt.',
      words: [
        { w: 'Ich', g: 'yo' }, { w: 'weiß', g: 'sé' }, { w: 'dass', g: 'que' },
        { w: 'er', g: 'él' }, { w: 'heute', g: 'hoy' }, { w: 'kommt', g: 'viene' },
      ],
      translation: 'Sé que él viene hoy.',
      note: 'En la subordinada, el verbo «kommt» salta al final de todo.',
    },
  ],
  it: [
    {
      sentence: 'Il ragazzo mangia una mela.',
      words: [
        { w: 'Il', g: 'el' }, { w: 'ragazzo', g: 'chico' }, { w: 'mangia', g: 'come' },
        { w: 'una', g: 'una' }, { w: 'mela', g: 'manzana' },
      ],
      translation: 'El chico come una manzana.',
    },
    {
      sentence: 'Lo vedo.',
      words: [{ w: 'Lo', g: 'lo' }, { w: 'vedo', g: '(yo)-veo' }],
      translation: 'Lo veo.',
      note: 'El pronombre objeto «lo» va antes del verbo; el sujeto se omite.',
    },
  ],
  ca: [
    {
      sentence: 'El nen menja una poma.',
      words: [
        { w: 'El', g: 'el' }, { w: 'nen', g: 'niño' }, { w: 'menja', g: 'come' },
        { w: 'una', g: 'una' }, { w: 'poma', g: 'manzana' },
      ],
      translation: 'El niño come una manzana.',
    },
    {
      sentence: 'No en tinc.',
      words: [{ w: 'No', g: '(no)' }, { w: 'en', g: 'de-ello' }, { w: 'tinc', g: '(yo)-tengo' }],
      translation: 'No tengo (de eso).',
      note: 'El pronombre débil «en» equivale a «de ello» y se agrupa junto al verbo.',
    },
  ],
  pt: [
    {
      sentence: 'O menino come uma maçã.',
      words: [
        { w: 'O', g: 'el' }, { w: 'menino', g: 'niño' }, { w: 'come', g: 'come' },
        { w: 'uma', g: 'una' }, { w: 'maçã', g: 'manzana' },
      ],
      translation: 'El niño come una manzana.',
    },
    {
      sentence: 'É importante estudarmos.',
      words: [
        { w: 'É', g: '(ello)-es' }, { w: 'importante', g: 'importante' },
        { w: 'estudarmos', g: '(nosotros)-estudiar' },
      ],
      translation: 'Es importante que estudiemos.',
      note: 'El infinitivo lleva la terminación personal -mos: el infinitivo personal, exclusivo del portugués.',
    },
  ],
  ro: [
    {
      sentence: 'Băiatul mănâncă un măr.',
      words: [
        { w: 'Băiatul', g: 'niño-el' }, { w: 'mănâncă', g: 'come' },
        { w: 'un', g: 'una' }, { w: 'măr', g: 'manzana' },
      ],
      translation: 'El niño come una manzana.',
      note: '«Băiatul» = «niño-el»: el artículo -ul va pegado al final del sustantivo.',
    },
    {
      sentence: 'Cartea este pe masă.',
      words: [
        { w: 'Cartea', g: 'libro-el' }, { w: 'este', g: 'está' }, { w: 'pe', g: 'sobre' },
        { w: 'masă', g: 'mesa' },
      ],
      translation: 'El libro está sobre la mesa.',
      note: 'De nuevo el artículo viaja al final: «Cartea» = «libro-el».',
    },
  ],
  tr: [
    {
      sentence: 'Çocuk elmayı yedi.',
      words: [
        { w: 'Çocuk', g: 'niño' }, { w: 'elmayı', g: 'manzana-(objeto)' },
        { w: 'yedi', g: 'comió' },
      ],
      translation: 'El niño se comió la manzana.',
      note: 'Verbo al final (SOV); la terminación -yı marca «manzana» como objeto definido.',
    },
    {
      sentence: 'Evlerimizde.',
      words: [
        { w: 'Ev', g: 'casa' }, { w: '-ler', g: '(plural)' },
        { w: '-imiz', g: 'nuestras' }, { w: '-de', g: 'en' },
      ],
      translation: 'En nuestras casas.',
      note: 'Una sola palabra equivale a toda una frase, construida apilando sufijos (aglutinación).',
    },
  ],
  sw: [
    {
      sentence: 'Mtoto anasoma kitabu.',
      words: [
        { w: 'Mtoto', g: 'niño' }, { w: 'anasoma', g: 'él/ella-está-leyendo' },
        { w: 'kitabu', g: 'libro' },
      ],
      translation: 'El niño está leyendo un libro.',
      note: '«a-na-soma» funde sujeto + tiempo + verbo en una sola palabra.',
    },
    {
      sentence: 'Vitabu vyangu viwili.',
      words: [
        { w: 'Vitabu', g: 'libros' }, { w: 'vyangu', g: 'míos' }, { w: 'viwili', g: 'dos' },
      ],
      translation: 'mis dos libros',
      note: 'El marcador de clase vi- se repite en cada palabra que concuerda con «libros».',
    },
  ],
  yo: [
    {
      sentence: 'Adé ra bàtà.',
      words: [{ w: 'Adé', g: 'Adé' }, { w: 'ra', g: 'compró' }, { w: 'bàtà', g: 'zapatos' }],
      translation: 'Adé compró zapatos.',
      note: 'El orden SVO es fijo; el tono (no las terminaciones) hace el trabajo gramatical.',
    },
    {
      sentence: 'Ó mú ìwé wá.',
      words: [
        { w: 'Ó', g: 'él' }, { w: 'mú', g: 'tomó' }, { w: 'ìwé', g: 'libro' },
        { w: 'wá', g: 'vino' },
      ],
      translation: 'Él trajo el libro.',
      note: 'Dos verbos seguidos (mú … wá, «tomar … venir») significan juntos «traer»: un verbo serial.',
    },
  ],
  ha: [
    {
      sentence: 'Yaro ya sayi doya.',
      words: [
        { w: 'Yaro', g: 'niño' }, { w: 'ya', g: 'él-(hizo)' }, { w: 'sayi', g: 'comprar' },
        { w: 'doya', g: 'ñame' },
      ],
      translation: 'El niño compró un ñame.',
      note: '«ya» lleva «él» + acción acabada, justo antes del verbo.',
    },
    {
      sentence: 'Yarinya ta tafi.',
      words: [
        { w: 'Yarinya', g: 'niña' }, { w: 'ta', g: 'ella-(hizo)' }, { w: 'tafi', g: 'ir' },
      ],
      translation: 'La niña se fue.',
      note: '«ta» marca un sujeto femenino; «ya» sería masculino.',
    },
  ],
  xh: [
    {
      sentence: 'Umntwana ufunda incwadi.',
      words: [
        { w: 'Umntwana', g: 'niño' }, { w: 'ufunda', g: 'él/ella-lee' },
        { w: 'incwadi', g: 'libro' },
      ],
      translation: 'El niño lee un libro.',
      note: 'Los prefijos de clase nominal (um-, in-) enhebran la concordancia por toda la frase.',
    },
    {
      sentence: 'Abantwana bafunda.',
      words: [{ w: 'Abantwana', g: 'niños' }, { w: 'bafunda', g: 'ellos-leen' }],
      translation: 'Los niños leen.',
      note: 'Prefijo plural aba- en el sustantivo, con eco de ba- en el verbo.',
    },
  ],
  mi: [
    {
      sentence: 'Kei te kai te tamaiti i te āporo.',
      words: [
        { w: 'Kei te kai', g: 'está-comiendo' }, { w: 'te', g: 'el' },
        { w: 'tamaiti', g: 'niño' }, { w: 'i te', g: '(objeto) la' },
        { w: 'āporo', g: 'manzana' },
      ],
      translation: 'El niño está comiendo la manzana.',
      note: 'El verbo va PRIMERO (VSO); la partícula «i» marca el objeto.',
    },
    {
      sentence: 'He tangata ia.',
      words: [{ w: 'He', g: 'una' }, { w: 'tangata', g: 'persona' }, { w: 'ia', g: 'él' }],
      translation: 'Él es una persona.',
      note: 'No hay verbo «ser»: las palabras simplemente van juntas.',
    },
  ],
  jam: [
    {
      sentence: 'Mi a nyam di food.',
      words: [
        { w: 'Mi', g: 'yo' }, { w: 'a', g: '(en-curso)' }, { w: 'nyam', g: 'comer' },
        { w: 'di', g: 'la' }, { w: 'food', g: 'comida' },
      ],
      translation: 'Me estoy comiendo la comida.',
      note: '«a» es una partícula de acción en curso: el verbo en sí nunca cambia.',
    },
    {
      sentence: 'Mi did nyam di food.',
      words: [
        { w: 'Mi', g: 'yo' }, { w: 'did', g: '(pasado)' }, { w: 'nyam', g: 'comer' },
        { w: 'di', g: 'la' }, { w: 'food', g: 'comida' },
      ],
      translation: 'Me comí la comida.',
      note: '«did» sitúa el pasado: se cambia la partícula y el verbo «nyam» no se mueve.',
    },
  ],
  en: [
    {
      sentence: 'The dog chased the cat.',
      words: [
        { w: 'The', g: 'el' }, { w: 'dog', g: 'perro' }, { w: 'chased', g: 'persiguió' },
        { w: 'the', g: 'el' }, { w: 'cat', g: 'gato' },
      ],
      translation: 'El perro persiguió al gato.',
      note: 'Intercambia los sustantivos y el significado se invierte: solo el orden marca quién hizo qué.',
    },
    {
      sentence: 'She looked after the kids.',
      words: [
        { w: 'She', g: 'ella' }, { w: 'looked', g: 'miró' }, { w: 'after', g: 'tras' },
        { w: 'the', g: 'los' }, { w: 'kids', g: 'niños' },
      ],
      translation: 'Ella cuidó de los niños.',
      note: '«look after» = cuidar de: un verbo frasal cuyas partes suman un significado nuevo.',
    },
  ],
  nl: [
    {
      sentence: 'Vandaag koop ik brood.',
      words: [
        { w: 'Vandaag', g: 'hoy' }, { w: 'koop', g: 'compro' }, { w: 'ik', g: 'yo' },
        { w: 'brood', g: 'pan' },
      ],
      translation: 'Hoy compro pan.',
      note: 'Verbo en segunda posición, como en alemán: «koop» va antes del sujeto «ik».',
    },
    {
      sentence: 'Ik weet dat hij komt.',
      words: [
        { w: 'Ik', g: 'yo' }, { w: 'weet', g: 'sé' }, { w: 'dat', g: 'que' },
        { w: 'hij', g: 'él' }, { w: 'komt', g: 'viene' },
      ],
      translation: 'Sé que él viene.',
      note: 'También como en alemán: «komt» se desplaza al final de la subordinada.',
    },
  ],
  ru: [
    {
      sentence: 'Мальчик читает книгу.',
      words: [
        { w: 'Мальчик', g: 'niño' }, { w: 'читает', g: 'lee' },
        { w: 'книгу', g: 'libro-(objeto)' },
      ],
      translation: 'El niño lee un libro.',
      note: '«книгу» es el acusativo de «книга»: el caso, no la posición, marca el objeto, así que las palabras pueden reordenarse libremente.',
    },
    {
      sentence: 'Я прочитал письмо.',
      words: [
        { w: 'Я', g: 'yo' }, { w: 'прочитал', g: 'leí-(completado)' },
        { w: 'письмо', g: 'carta' },
      ],
      translation: 'Leí la carta (y la terminé).',
      note: 'El perfectivo «прочитал» dice que la acción se completó; su pareja imperfectiva «читал» describiría el proceso.',
    },
  ],
  el: [
    {
      sentence: 'Ο άντρας διαβάζει το βιβλίο.',
      words: [
        { w: 'Ο', g: 'el' }, { w: 'άντρας', g: 'hombre' }, { w: 'διαβάζει', g: 'lee' },
        { w: 'το', g: 'el' }, { w: 'βιβλίο', g: 'libro' },
      ],
      translation: 'El hombre lee el libro.',
    },
    {
      sentence: 'Βλέπω τον άντρα.',
      words: [
        { w: 'Βλέπω', g: '(yo)-veo' }, { w: 'τον', g: 'al-(objeto)' },
        { w: 'άντρα', g: 'hombre' },
      ],
      translation: 'Veo al hombre.',
      note: 'El artículo cambia con el caso: τον (acusativo) frente a ο (nominativo).',
    },
  ],
  ar: [
    {
      sentence: 'يقرأ الولد الكتاب.',
      words: [
        { w: 'يقرأ', g: 'lee' }, { w: 'الولد', g: 'el-niño' },
        { w: 'الكتاب', g: 'el-libro' },
      ],
      translation: 'El niño lee el libro.',
      note: 'El árabe clásico empieza por el verbo (VSO); se lee de derecha a izquierda.',
      rtl: true,
    },
    {
      sentence: 'الكتاب جديد.',
      words: [{ w: 'الكتاب', g: 'el-libro' }, { w: 'جديد', g: 'nuevo' }],
      translation: 'El libro es nuevo.',
      note: 'No hay verbo «ser» en presente: solo «el libro» + «nuevo».',
      rtl: true,
    },
  ],
  hi: [
    {
      sentence: 'लड़का किताब पढ़ता है।',
      words: [
        { w: 'लड़का', g: 'niño' }, { w: 'किताब', g: 'libro' }, { w: 'पढ़ता', g: 'lee' },
        { w: 'है', g: 'está' },
      ],
      translation: 'El niño lee un libro.',
      note: 'Verbo al final (SOV); la frase se cierra con «है» (está).',
    },
    {
      sentence: 'लड़का घर में है।',
      words: [
        { w: 'लड़का', g: 'niño' }, { w: 'घर', g: 'casa' }, { w: 'में', g: 'en' },
        { w: 'है', g: 'está' },
      ],
      translation: 'El niño está en la casa.',
      note: '«में» (en) va DESPUÉS del sustantivo: una posposición, no una preposición.',
    },
  ],
  th: [
    {
      sentence: 'เด็กกินข้าว',
      words: [{ w: 'เด็ก', g: 'niño' }, { w: 'กิน', g: 'comer' }, { w: 'ข้าว', g: 'arroz' }],
      translation: 'El niño come arroz.',
      note: 'Aislante: ninguna palabra cambia de forma; no hay espacios entre palabras.',
    },
    {
      sentence: 'หนังสือสามเล่ม',
      words: [
        { w: 'หนังสือ', g: 'libro' }, { w: 'สาม', g: 'tres' }, { w: 'เล่ม', g: '(clasificador)' },
      ],
      translation: 'tres libros',
      note: 'Contar exige un clasificador: เล่ม para libros y otras cosas planas y encuadernadas.',
    },
  ],
  ko: [
    {
      sentence: '아이가 책을 읽어요.',
      words: [
        { w: '아이가', g: 'niño-(sujeto)' }, { w: '책을', g: 'libro-(objeto)' },
        { w: '읽어요', g: 'lee' },
      ],
      translation: 'El niño lee un libro.',
      note: 'Verbo al final; «-가» marca el sujeto y «-을» el objeto.',
    },
    {
      sentence: '저는 학생이에요.',
      words: [
        { w: '저는', g: 'yo-(tema)' }, { w: '학생이에요', g: 'soy-estudiante' },
      ],
      translation: 'Soy estudiante.',
      note: '«-는» marca el tema; el verbo «ser» se funde con el sustantivo 학생 (estudiante).',
    },
  ],
  he: [
    {
      sentence: 'הילד קורא ספר.',
      words: [
        { w: 'הילד', g: 'el-niño' }, { w: 'קורא', g: 'lee' }, { w: 'ספר', g: 'un-libro' },
      ],
      translation: 'El niño lee un libro.',
      note: 'Sujeto–Verbo–Objeto; se lee de derecha a izquierda.',
      rtl: true,
    },
    {
      sentence: 'הספר חדש.',
      words: [{ w: 'הספר', g: 'el-libro' }, { w: 'חדש', g: 'nuevo' }],
      translation: 'El libro es nuevo.',
      note: 'No hay verbo «ser» en presente: solo «el-libro» + «nuevo».',
      rtl: true,
    },
  ],
  la: [
    {
      sentence: 'Puella librum legit.',
      words: [
        { w: 'Puella', g: 'niña' }, { w: 'librum', g: 'libro-(objeto)' }, { w: 'legit', g: 'lee' },
      ],
      translation: 'La niña lee el libro.',
      note: 'Un orden neutro habitual (Sujeto–Objeto–Verbo), pero las terminaciones de caso permitirían reordenarlo libremente.',
    },
    {
      sentence: 'Liber novus est.',
      words: [{ w: 'Liber', g: 'libro' }, { w: 'novus', g: 'nuevo' }, { w: 'est', g: 'es' }],
      translation: 'El libro es nuevo.',
      note: 'No hay palabra para «el»: liber por sí solo puede significar «libro», «un libro» o «el libro».',
    },
  ],
  fa: [
    {
      sentence: 'پسر کتاب می‌خواند.',
      words: [
        { w: 'پسر', g: 'niño' }, { w: 'کتاب', g: 'libro' }, { w: 'می‌خواند', g: 'lee' },
      ],
      translation: 'El niño lee el libro.',
      note: 'Sujeto–Objeto–Verbo: el verbo va al final, a diferencia del árabe.',
      rtl: true,
    },
    {
      sentence: 'این کتاب خوب است.',
      words: [
        { w: 'این', g: 'este' }, { w: 'کتاب', g: 'libro' }, { w: 'خوب', g: 'bueno' }, { w: 'است', g: 'es' },
      ],
      translation: 'Este libro es bueno.',
      rtl: true,
    },
  ],
  id: [
    {
      sentence: 'Anak itu membaca buku.',
      words: [
        { w: 'Anak', g: 'niño' }, { w: 'itu', g: 'ese/el' }, { w: 'membaca', g: 'lee' }, { w: 'buku', g: 'libro' },
      ],
      translation: 'El niño lee un libro.',
      note: '«Itu» («ese») sigue al sustantivo y hace el trabajo de «el».',
    },
    {
      sentence: 'Saya membeli buku-buku itu.',
      words: [
        { w: 'Saya', g: 'yo' }, { w: 'membeli', g: 'compré' }, { w: 'buku-buku', g: 'libros-(doblado)' }, { w: 'itu', g: 'esos' },
      ],
      translation: 'Compré esos libros.',
      note: 'El plural es la palabra dicha dos veces: buku (libro) → buku-buku (libros). Tampoco hay marca de tiempo verbal: la aporta el contexto.',
    },
  ],
  tl: [
    {
      sentence: 'Kumain ang bata ng mansanas.',
      words: [
        { w: 'Kumain', g: 'comió' }, { w: 'ang bata', g: 'el-niño' }, { w: 'ng mansanas', g: 'una-manzana' },
      ],
      translation: 'El niño comió una manzana.',
      note: 'Verbo primero: el agente y lo actuado vienen después, marcados por ang y ng.',
    },
    {
      sentence: 'Naglalakad siya araw-araw.',
      words: [
        { w: 'Naglalakad', g: 'está-caminando' }, { w: 'siya', g: 'él/ella' }, { w: 'araw-araw', g: 'día-día' },
      ],
      translation: 'Él/ella camina todos los días.',
      note: 'Reduplicación otra vez: araw (día) doblado significa «todos los días».',
    },
  ],
}
