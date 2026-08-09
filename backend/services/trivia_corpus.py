"""The baseline trivia corpus: written once, here, in every UI locale.

The wait screen's game had a bootstrapping problem. The bank starts empty,
the generator fills it — so the very first learner to reach a locale sees
nothing, which is the exact "first one here gets an empty screen" trap the
wait screen exists to soften. Filling it inline (routers/review._top_up_
trivia) narrowed that to a few seconds of API call, but only where a
provider key is configured and the budget allows. Where it isn't, the game
simply never exists.

So the baseline is written down rather than generated. These questions cost
nothing, need no key, and are the same for everybody — a question about why
some scripts run right-to-left is as good for a Turkish learner as a Greek
one. The generated corpus grows on top of this, and is handed these
questions as the "avoid" list so it widens the bank instead of restating it.

Every entry carries all six UI locales. That is deliberate rather than
tedious: a corpus that exists in English and gets machine-translated on
demand is the situation trivia was introduced to work around. The parity is
enforced by a test, so a question added in one locale and forgotten in
another fails the build rather than quietly shrinking someone's bank.

`answer` is one index shared across locales, which means the options must
stay in the same ORDER in every language. Translate them in place; do not
reorder them to read more naturally.
"""
from __future__ import annotations

import uuid

# The UI locales. A support locale outside this list gets no baseline and
# falls through to the generator, which is the pre-existing behaviour.
LOCALES = ("en", "es", "fr", "pt", "ru", "ar")

# Stable namespace for the in-memory ids below. Fixed forever: it is what
# makes a served question identify the same question across processes.
_NS = uuid.UUID("6f1c1d2e-0b7a-4a5f-9e3c-6d5b7a8c9d01")

_QUESTIONS: list[dict] = [
    {
        "answer": 1,
        "en": {
            "question": "Which of these scripts is written from right to left?",
            "options": ["Greek", "Arabic", "Thai", "Devanagari"],
            "fact": "Arabic and Hebrew both run right to left — but their "
                    "digits are written left to right, so a phone number "
                    "goes the other way.",
        },
        "es": {
            "question": "¿Cuál de estas escrituras se escribe de derecha a izquierda?",
            "options": ["Griega", "Árabe", "Tailandesa", "Devanagari"],
            "fact": "El árabe y el hebreo se escriben de derecha a izquierda, "
                    "pero sus cifras van de izquierda a derecha: un número de "
                    "teléfono se lee al revés.",
        },
        "fr": {
            "question": "Laquelle de ces écritures s'écrit de droite à gauche ?",
            "options": ["Le grec", "L'arabe", "Le thaï", "La devanagari"],
            "fact": "L'arabe et l'hébreu s'écrivent de droite à gauche, mais "
                    "leurs chiffres s'écrivent de gauche à droite : un numéro "
                    "de téléphone se lit dans l'autre sens.",
        },
        "pt": {
            "question": "Qual destas escritas se escreve da direita para a esquerda?",
            "options": ["Grega", "Árabe", "Tailandesa", "Devanágari"],
            "fact": "O árabe e o hebraico escrevem-se da direita para a "
                    "esquerda, mas os seus algarismos vão da esquerda para a "
                    "direita: um número de telefone lê-se ao contrário.",
        },
        "ru": {
            "question": "Какая из этих письменностей пишется справа налево?",
            "options": ["Греческая", "Арабская", "Тайская", "Деванагари"],
            "fact": "Арабское и еврейское письмо идут справа налево, а цифры "
                    "в них пишутся слева направо — номер телефона читается в "
                    "другую сторону.",
        },
        "ar": {
            "question": "أي من هذه الكتابات تُكتب من اليمين إلى اليسار؟",
            "options": ["اليونانية", "العربية", "التايلاندية", "الديفاناغارية"],
            "fact": "تُكتب العربية والعبرية من اليمين إلى اليسار، لكن أرقامهما "
                    "تُكتب من اليسار إلى اليمين، فرقم الهاتف يسير في الاتجاه "
                    "المعاكس.",
        },
    },
    {
        "answer": 2,
        "en": {
            "question": "About how many languages are spoken in the world today?",
            "options": ["About 200", "About 700", "About 7,000", "About 70,000"],
            "fact": "Ethnologue counts just over 7,000 — and rates roughly "
                    "40% of them as endangered.",
        },
        "es": {
            "question": "¿Cuántas lenguas se hablan hoy en el mundo, aproximadamente?",
            "options": ["Unas 200", "Unas 700", "Unas 7.000", "Unas 70.000"],
            "fact": "Ethnologue registra algo más de 7.000 y considera en "
                    "peligro cerca del 40%.",
        },
        "fr": {
            "question": "Combien de langues parle-t-on dans le monde aujourd'hui, environ ?",
            "options": ["Environ 200", "Environ 700", "Environ 7 000", "Environ 70 000"],
            "fact": "Ethnologue en recense un peu plus de 7 000 et en classe "
                    "près de 40 % comme menacées.",
        },
        "pt": {
            "question": "Quantas línguas se falam hoje no mundo, aproximadamente?",
            "options": ["Cerca de 200", "Cerca de 700", "Cerca de 7.000", "Cerca de 70.000"],
            "fact": "O Ethnologue regista pouco mais de 7.000 e classifica "
                    "cerca de 40% como ameaçadas.",
        },
        "ru": {
            "question": "Сколько примерно языков существует в мире сегодня?",
            "options": ["Около 200", "Около 700", "Около 7000", "Около 70 000"],
            "fact": "«Этнолог» насчитывает чуть более 7000 языков и относит "
                    "около 40 % из них к исчезающим.",
        },
        "ar": {
            "question": "كم لغة تقريبًا يُتحدَّث بها في العالم اليوم؟",
            "options": ["نحو 200", "نحو 700", "نحو 7000", "نحو 70000"],
            "fact": "يُحصي «إثنولوغ» ما يزيد قليلًا على 7000 لغة، ويصنّف نحو "
                    "40% منها بأنها مهدَّدة بالانقراض.",
        },
    },
    {
        "answer": 1,
        "en": {
            "question": "Which language has the most native speakers?",
            "options": ["English", "Mandarin Chinese", "Spanish", "Hindi"],
            "fact": "Mandarin has roughly 940 million native speakers. "
                    "English only takes the lead once second-language "
                    "speakers are counted.",
        },
        "es": {
            "question": "¿Qué lengua tiene más hablantes nativos?",
            "options": ["Inglés", "Chino mandarín", "Español", "Hindi"],
            "fact": "El mandarín tiene unos 940 millones de hablantes "
                    "nativos. El inglés solo encabeza la lista si se cuentan "
                    "los hablantes de segunda lengua.",
        },
        "fr": {
            "question": "Quelle langue compte le plus de locuteurs natifs ?",
            "options": ["L'anglais", "Le chinois mandarin", "L'espagnol", "Le hindi"],
            "fact": "Le mandarin compte environ 940 millions de locuteurs "
                    "natifs. L'anglais ne passe en tête que si l'on compte "
                    "les locuteurs en langue seconde.",
        },
        "pt": {
            "question": "Que língua tem mais falantes nativos?",
            "options": ["Inglês", "Chinês mandarim", "Espanhol", "Híndi"],
            "fact": "O mandarim tem cerca de 940 milhões de falantes nativos. "
                    "O inglês só fica em primeiro se contarmos os falantes de "
                    "segunda língua.",
        },
        "ru": {
            "question": "У какого языка больше всего носителей?",
            "options": ["Английский", "Китайский (путунхуа)", "Испанский", "Хинди"],
            "fact": "У путунхуа около 940 миллионов носителей. Английский "
                    "выходит вперёд, только если считать и тех, для кого он "
                    "второй язык.",
        },
        "ar": {
            "question": "أي لغة لديها أكبر عدد من المتحدثين الأصليين؟",
            "options": ["الإنجليزية", "الصينية (الماندرين)", "الإسبانية", "الهندية"],
            "fact": "للماندرين نحو 940 مليون متحدث أصلي، ولا تتصدر الإنجليزية "
                    "إلا عند احتساب من يتحدثونها لغةً ثانية.",
        },
    },
    {
        "answer": 2,
        "en": {
            "question": "What is a \"cognate\"?",
            "options": [
                "A word borrowed from another language last century",
                "A word with two unrelated meanings",
                "A word that shares an ancestor with a word in another language",
                "A word that imitates the sound of what it names",
            ],
            "fact": "English \"night\", German \"Nacht\" and Spanish \"noche\" "
                    "all come from the same Proto-Indo-European root.",
        },
        "es": {
            "question": "¿Qué es un «cognado»?",
            "options": [
                "Una palabra tomada de otra lengua el siglo pasado",
                "Una palabra con dos significados sin relación",
                "Una palabra que comparte un antepasado con otra de otra lengua",
                "Una palabra que imita el sonido de aquello que nombra",
            ],
            "fact": "El inglés «night», el alemán «Nacht» y el español "
                    "«noche» vienen de la misma raíz protoindoeuropea.",
        },
        "fr": {
            "question": "Qu'est-ce qu'un mot apparenté (un « cognat ») ?",
            "options": [
                "Un mot emprunté à une autre langue au siècle dernier",
                "Un mot ayant deux sens sans rapport",
                "Un mot qui partage un ancêtre avec un mot d'une autre langue",
                "Un mot qui imite le son de ce qu'il désigne",
            ],
            "fact": "L'anglais « night », l'allemand « Nacht » et l'espagnol "
                    "« noche » viennent de la même racine indo-européenne.",
        },
        "pt": {
            "question": "O que é um «cognato»?",
            "options": [
                "Uma palavra tomada de outra língua no século passado",
                "Uma palavra com dois sentidos sem relação",
                "Uma palavra que partilha um antepassado com outra de outra língua",
                "Uma palavra que imita o som daquilo que nomeia",
            ],
            "fact": "O inglês «night», o alemão «Nacht» e o espanhol «noche» "
                    "vêm da mesma raiz indo-europeia.",
        },
        "ru": {
            "question": "Что такое «когнат»?",
            "options": [
                "Слово, заимствованное из другого языка в прошлом веке",
                "Слово с двумя не связанными значениями",
                "Слово, у которого общий предок со словом другого языка",
                "Слово, подражающее звуку того, что оно называет",
            ],
            "fact": "Английское «night», немецкое «Nacht» и испанское «noche» "
                    "восходят к одному праиндоевропейскому корню.",
        },
        "ar": {
            "question": "ما المقصود بالكلمات المشتركة الأصل (cognates)؟",
            "options": [
                "كلمة اقتُرضت من لغة أخرى في القرن الماضي",
                "كلمة لها معنيان لا رابط بينهما",
                "كلمة تشترك مع كلمة في لغة أخرى في أصل واحد",
                "كلمة تحاكي صوت ما تسمّيه",
            ],
            "fact": "الإنجليزية «night» والألمانية «Nacht» والإسبانية «noche» "
                    "ترجع كلها إلى جذر هندي-أوروبي واحد.",
        },
    },
    {
        "answer": 1,
        "en": {
            "question": "What is a \"false friend\"?",
            "options": [
                "A word nobody uses any more",
                "A word that looks like one in another language but means something else",
                "A word with no direct translation",
                "A word invented for a single book",
            ],
            "fact": "Spanish \"embarazada\" looks like \"embarrassed\" and "
                    "means pregnant.",
        },
        "es": {
            "question": "¿Qué es un «falso amigo»?",
            "options": [
                "Una palabra que ya nadie usa",
                "Una palabra que se parece a otra de otra lengua pero significa algo distinto",
                "Una palabra sin traducción directa",
                "Una palabra inventada para un solo libro",
            ],
            "fact": "El inglés «actually» se parece a «actualmente», pero "
                    "significa «en realidad».",
        },
        "fr": {
            "question": "Qu'est-ce qu'un « faux ami » ?",
            "options": [
                "Un mot que plus personne n'utilise",
                "Un mot qui ressemble à un mot d'une autre langue mais signifie autre chose",
                "Un mot sans traduction directe",
                "Un mot inventé pour un seul livre",
            ],
            "fact": "L'anglais « library » ressemble à « librairie », mais "
                    "désigne une bibliothèque.",
        },
        "pt": {
            "question": "O que é um «falso amigo»?",
            "options": [
                "Uma palavra que já ninguém usa",
                "Uma palavra que se parece com outra de outra língua mas significa algo diferente",
                "Uma palavra sem tradução direta",
                "Uma palavra inventada para um único livro",
            ],
            "fact": "O inglês «pretend» parece «pretender», mas significa "
                    "fingir.",
        },
        "ru": {
            "question": "Что такое «ложный друг переводчика»?",
            "options": [
                "Слово, которым больше никто не пользуется",
                "Слово, похожее на слово другого языка, но значащее другое",
                "Слово, у которого нет прямого перевода",
                "Слово, придуманное для одной книги",
            ],
            "fact": "Английское «magazine» похоже на «магазин», но означает "
                    "журнал.",
        },
        "ar": {
            "question": "ما المقصود بـ«الصديق الكاذب» بين اللغات؟",
            "options": [
                "كلمة لم يعد أحد يستعملها",
                "كلمة تشبه كلمة في لغة أخرى لكن معناها مختلف",
                "كلمة لا ترجمة مباشرة لها",
                "كلمة اختُرعت من أجل كتاب واحد",
            ],
            "fact": "الكلمة الإسبانية «embarazada» تشبه الإنجليزية "
                    "«embarrassed» لكنها تعني «حامل».",
        },
    },
    {
        "answer": 1,
        "en": {
            "question": "Which of these languages is NOT Indo-European?",
            "options": ["Armenian", "Hungarian", "Persian", "Greek"],
            "fact": "Hungarian is Uralic — its closest relatives are Finnish "
                    "and Estonian, not its neighbours.",
        },
        "es": {
            "question": "¿Cuál de estas lenguas NO es indoeuropea?",
            "options": ["Armenio", "Húngaro", "Persa", "Griego"],
            "fact": "El húngaro es urálico: sus parientes más cercanos son el "
                    "finés y el estonio, no sus vecinos.",
        },
        "fr": {
            "question": "Laquelle de ces langues n'est PAS indo-européenne ?",
            "options": ["L'arménien", "Le hongrois", "Le persan", "Le grec"],
            "fact": "Le hongrois est une langue ouralienne : ses plus proches "
                    "parents sont le finnois et l'estonien, pas ses voisins.",
        },
        "pt": {
            "question": "Qual destas línguas NÃO é indo-europeia?",
            "options": ["Arménio", "Húngaro", "Persa", "Grego"],
            "fact": "O húngaro é urálico: os seus parentes mais próximos são "
                    "o finlandês e o estónio, não os vizinhos.",
        },
        "ru": {
            "question": "Какой из этих языков НЕ индоевропейский?",
            "options": ["Армянский", "Венгерский", "Персидский", "Греческий"],
            "fact": "Венгерский — уральский язык: его ближайшие родственники "
                    "финский и эстонский, а не языки соседей.",
        },
        "ar": {
            "question": "أي من هذه اللغات ليست هندية-أوروبية؟",
            "options": ["الأرمنية", "المجرية", "الفارسية", "اليونانية"],
            "fact": "المجرية لغة أورالية، وأقرب أقاربها الفنلندية والإستونية "
                    "لا لغات جيرانها.",
        },
    },
    {
        "answer": 0,
        "en": {
            "question": "What is the International Phonetic Alphabet for?",
            "options": [
                "Writing one symbol for each speech sound",
                "Ranking languages by difficulty",
                "Translating between alphabets",
                "Teaching children to read",
            ],
            "fact": "It was published in 1888 so the sounds of any language "
                    "could be written down without ambiguity.",
        },
        "es": {
            "question": "¿Para qué sirve el Alfabeto Fonético Internacional?",
            "options": [
                "Para escribir un símbolo por cada sonido del habla",
                "Para ordenar las lenguas por dificultad",
                "Para traducir entre alfabetos",
                "Para enseñar a leer a los niños",
            ],
            "fact": "Se publicó en 1888 para poder escribir sin ambigüedad "
                    "los sonidos de cualquier lengua.",
        },
        "fr": {
            "question": "À quoi sert l'alphabet phonétique international ?",
            "options": [
                "À noter un symbole par son de parole",
                "À classer les langues par difficulté",
                "À traduire d'un alphabet à un autre",
                "À apprendre à lire aux enfants",
            ],
            "fact": "Il a été publié en 1888 pour pouvoir noter sans "
                    "ambiguïté les sons de n'importe quelle langue.",
        },
        "pt": {
            "question": "Para que serve o Alfabeto Fonético Internacional?",
            "options": [
                "Para escrever um símbolo por cada som da fala",
                "Para ordenar as línguas por dificuldade",
                "Para traduzir entre alfabetos",
                "Para ensinar as crianças a ler",
            ],
            "fact": "Foi publicado em 1888 para se poderem escrever sem "
                    "ambiguidade os sons de qualquer língua.",
        },
        "ru": {
            "question": "Для чего нужен Международный фонетический алфавит?",
            "options": [
                "Чтобы записывать каждый звук речи отдельным знаком",
                "Чтобы ранжировать языки по сложности",
                "Чтобы переводить между алфавитами",
                "Чтобы учить детей читать",
            ],
            "fact": "Он был опубликован в 1888 году, чтобы звуки любого языка "
                    "можно было записать однозначно.",
        },
        "ar": {
            "question": "ما الغرض من الأبجدية الصوتية الدولية؟",
            "options": [
                "كتابة رمز واحد لكل صوت من أصوات الكلام",
                "ترتيب اللغات حسب صعوبتها",
                "الترجمة بين الأبجديات",
                "تعليم الأطفال القراءة",
            ],
            "fact": "نُشرت عام 1888 لتمكين تدوين أصوات أي لغة دون لبس.",
        },
    },
    {
        "answer": 2,
        "en": {
            "question": "What does grammatical gender do in a language?",
            "options": [
                "Marks whether the speaker is a man or a woman",
                "Marks how polite a sentence is",
                "Sorts nouns into classes that other words must agree with",
                "Marks whether an action is finished",
            ],
            "fact": "German has three genders; Swahili sorts its nouns into "
                    "more than a dozen classes.",
        },
        "es": {
            "question": "¿Qué hace el género gramatical en una lengua?",
            "options": [
                "Indica si quien habla es hombre o mujer",
                "Indica lo cortés que es una frase",
                "Agrupa los sustantivos en clases con las que otras palabras concuerdan",
                "Indica si una acción ha terminado",
            ],
            "fact": "El alemán tiene tres géneros; el suajili reparte sus "
                    "sustantivos en más de una docena de clases.",
        },
        "fr": {
            "question": "À quoi sert le genre grammatical dans une langue ?",
            "options": [
                "Il indique si la personne qui parle est un homme ou une femme",
                "Il indique le degré de politesse de la phrase",
                "Il range les noms en classes avec lesquelles les autres mots s'accordent",
                "Il indique si l'action est achevée",
            ],
            "fact": "L'allemand a trois genres ; le swahili répartit ses noms "
                    "en plus d'une douzaine de classes.",
        },
        "pt": {
            "question": "O que faz o género gramatical numa língua?",
            "options": [
                "Indica se quem fala é homem ou mulher",
                "Indica o grau de cortesia da frase",
                "Agrupa os substantivos em classes com que as outras palavras concordam",
                "Indica se a ação está terminada",
            ],
            "fact": "O alemão tem três géneros; o suaíli reparte os seus "
                    "substantivos por mais de uma dúzia de classes.",
        },
        "ru": {
            "question": "Для чего в языке нужен грамматический род?",
            "options": [
                "Он показывает, мужчина говорит или женщина",
                "Он показывает степень вежливости фразы",
                "Он делит существительные на классы, с которыми согласуются другие слова",
                "Он показывает, завершено ли действие",
            ],
            "fact": "В немецком три рода, а в суахили существительные "
                    "разделены более чем на десяток классов.",
        },
        "ar": {
            "question": "ما وظيفة الجنس النحوي في اللغة؟",
            "options": [
                "يبيّن إن كان المتكلّم رجلًا أم امرأة",
                "يبيّن درجة تأدُّب الجملة",
                "يصنّف الأسماء في فئات تطابقها بقية الكلمات",
                "يبيّن إن كان الفعل قد اكتمل",
            ],
            "fact": "في الألمانية ثلاثة أجناس، وفي السواحيلية أكثر من اثنتي "
                    "عشرة فئة للأسماء.",
        },
    },
    {
        "answer": 1,
        "en": {
            "question": "Where does the largest share of English vocabulary come from?",
            "options": ["Old English", "French and Latin", "Old Norse", "Greek"],
            "fact": "After the Norman conquest of 1066, French and Latin "
                    "supplied more than half the words in an English "
                    "dictionary.",
        },
        "es": {
            "question": "¿De dónde procede la mayor parte del vocabulario inglés?",
            "options": ["Del inglés antiguo", "Del francés y el latín", "Del nórdico antiguo", "Del griego"],
            "fact": "Tras la conquista normanda de 1066, el francés y el "
                    "latín aportaron más de la mitad de las palabras de un "
                    "diccionario inglés.",
        },
        "fr": {
            "question": "D'où vient la plus grande partie du vocabulaire anglais ?",
            "options": ["Du vieil anglais", "Du français et du latin", "Du vieux norrois", "Du grec"],
            "fact": "Après la conquête normande de 1066, le français et le "
                    "latin ont fourni plus de la moitié des mots d'un "
                    "dictionnaire anglais.",
        },
        "pt": {
            "question": "De onde vem a maior parte do vocabulário inglês?",
            "options": ["Do inglês antigo", "Do francês e do latim", "Do nórdico antigo", "Do grego"],
            "fact": "Depois da conquista normanda de 1066, o francês e o "
                    "latim deram mais de metade das palavras de um dicionário "
                    "inglês.",
        },
        "ru": {
            "question": "Откуда происходит бо́льшая часть английской лексики?",
            "options": ["Из древнеанглийского", "Из французского и латыни", "Из древнескандинавского", "Из греческого"],
            "fact": "После нормандского завоевания 1066 года французский и "
                    "латынь дали больше половины слов английского словаря.",
        },
        "ar": {
            "question": "من أين يأتي الجزء الأكبر من مفردات الإنجليزية؟",
            "options": ["من الإنجليزية القديمة", "من الفرنسية واللاتينية", "من الإسكندنافية القديمة", "من اليونانية"],
            "fact": "بعد الغزو النورماندي عام 1066 قدّمت الفرنسية واللاتينية "
                    "أكثر من نصف كلمات القاموس الإنجليزي.",
        },
    },
    {
        "answer": 0,
        "en": {
            "question": "What is an agglutinative language?",
            "options": [
                "One that builds words by stacking suffixes, each with one job",
                "One with no verb tenses",
                "One written without vowels",
                "One with a very small vocabulary",
            ],
            "fact": "Turkish, Finnish and Swahili work this way — a single "
                    "Turkish word can carry a whole English sentence.",
        },
        "es": {
            "question": "¿Qué es una lengua aglutinante?",
            "options": [
                "Una que forma palabras encadenando sufijos, cada uno con una función",
                "Una que no tiene tiempos verbales",
                "Una que se escribe sin vocales",
                "Una con un vocabulario muy reducido",
            ],
            "fact": "El turco, el finés y el suajili funcionan así: una sola "
                    "palabra turca puede equivaler a una frase entera.",
        },
        "fr": {
            "question": "Qu'est-ce qu'une langue agglutinante ?",
            "options": [
                "Une langue qui forme ses mots en empilant des suffixes ayant chacun un rôle",
                "Une langue sans temps verbaux",
                "Une langue écrite sans voyelles",
                "Une langue au vocabulaire très restreint",
            ],
            "fact": "Le turc, le finnois et le swahili fonctionnent ainsi : "
                    "un seul mot turc peut valoir une phrase entière.",
        },
        "pt": {
            "question": "O que é uma língua aglutinante?",
            "options": [
                "Uma que forma palavras encadeando sufixos, cada um com uma função",
                "Uma que não tem tempos verbais",
                "Uma que se escreve sem vogais",
                "Uma com um vocabulário muito reduzido",
            ],
            "fact": "O turco, o finlandês e o suaíli funcionam assim: uma só "
                    "palavra turca pode valer uma frase inteira.",
        },
        "ru": {
            "question": "Что такое агглютинативный язык?",
            "options": [
                "Язык, где слова строятся нанизыванием суффиксов, каждый со своей функцией",
                "Язык без глагольных времён",
                "Язык, который пишется без гласных",
                "Язык с очень маленьким словарём",
            ],
            "fact": "Так устроены турецкий, финский и суахили: одно турецкое "
                    "слово может заменить целое предложение.",
        },
        "ar": {
            "question": "ما اللغة الإلصاقية؟",
            "options": [
                "لغة تبني كلماتها برصّ لواحق لكلٍّ منها وظيفة واحدة",
                "لغة بلا أزمنة للفعل",
                "لغة تُكتب دون حروف علة",
                "لغة ذات مفردات قليلة جدًا",
            ],
            "fact": "هكذا تعمل التركية والفنلندية والسواحيلية، وقد تعادل كلمة "
                    "تركية واحدة جملة كاملة.",
        },
    },
    {
        "answer": 1,
        "en": {
            "question": "In which of these languages does the pitch of a syllable change the word?",
            "options": ["Russian", "Mandarin Chinese", "Turkish", "Portuguese"],
            "fact": "Mandarin has four tones — say \"ma\" four ways and you "
                    "get mother, hemp, horse and a scolding.",
        },
        "es": {
            "question": "¿En cuál de estas lenguas el tono de una sílaba cambia la palabra?",
            "options": ["Ruso", "Chino mandarín", "Turco", "Portugués"],
            "fact": "El mandarín tiene cuatro tonos: «ma» dicho de cuatro "
                    "maneras significa madre, cáñamo, caballo o regañar.",
        },
        "fr": {
            "question": "Dans laquelle de ces langues la hauteur d'une syllabe change-t-elle le mot ?",
            "options": ["Le russe", "Le chinois mandarin", "Le turc", "Le portugais"],
            "fact": "Le mandarin a quatre tons : « ma » prononcé de quatre "
                    "façons donne mère, chanvre, cheval ou gronder.",
        },
        "pt": {
            "question": "Em qual destas línguas o tom de uma sílaba muda a palavra?",
            "options": ["Russo", "Chinês mandarim", "Turco", "Português"],
            "fact": "O mandarim tem quatro tons: «ma» dito de quatro maneiras "
                    "significa mãe, cânhamo, cavalo ou repreender.",
        },
        "ru": {
            "question": "В каком из этих языков высота тона в слоге меняет слово?",
            "options": ["Русский", "Китайский (путунхуа)", "Турецкий", "Португальский"],
            "fact": "В путунхуа четыре тона: слог «ма», произнесённый "
                    "по-разному, значит «мать», «конопля», «лошадь» или "
                    "«ругать».",
        },
        "ar": {
            "question": "في أي من هذه اللغات تُغيّر نبرة المقطع الكلمة نفسها؟",
            "options": ["الروسية", "الصينية (الماندرين)", "التركية", "البرتغالية"],
            "fact": "للماندرين أربع نبرات: «ما» بأربع طرق تعني أمًّا وقنّبًا "
                    "وحصانًا وتوبيخًا.",
        },
    },
    {
        "answer": 2,
        "en": {
            "question": "Which writing system has been in continuous use the longest?",
            "options": ["Cuneiform", "Egyptian hieroglyphs", "Chinese characters", "Linear B"],
            "fact": "Chinese characters have been written for more than 3,000 "
                    "years; the other three all fell out of use.",
        },
        "es": {
            "question": "¿Qué sistema de escritura lleva más tiempo en uso continuo?",
            "options": ["La escritura cuneiforme", "Los jeroglíficos egipcios", "Los caracteres chinos", "El lineal B"],
            "fact": "Los caracteres chinos se escriben desde hace más de "
                    "3.000 años; los otros tres dejaron de usarse.",
        },
        "fr": {
            "question": "Quel système d'écriture est en usage continu depuis le plus longtemps ?",
            "options": ["Le cunéiforme", "Les hiéroglyphes égyptiens", "Les caractères chinois", "Le linéaire B"],
            "fact": "Les caractères chinois s'écrivent depuis plus de 3 000 "
                    "ans ; les trois autres ont cessé d'être utilisés.",
        },
        "pt": {
            "question": "Que sistema de escrita está em uso contínuo há mais tempo?",
            "options": ["A escrita cuneiforme", "Os hieróglifos egípcios", "Os caracteres chineses", "O linear B"],
            "fact": "Os caracteres chineses escrevem-se há mais de 3.000 "
                    "anos; os outros três deixaram de ser usados.",
        },
        "ru": {
            "question": "Какая система письма непрерывно используется дольше всех?",
            "options": ["Клинопись", "Египетские иероглифы", "Китайские иероглифы", "Линейное письмо Б"],
            "fact": "Китайскими иероглифами пишут более 3000 лет, а три "
                    "остальные системы вышли из употребления.",
        },
        "ar": {
            "question": "أي نظام كتابة ظلّ مستخدمًا دون انقطاع أطول مدة؟",
            "options": ["الكتابة المسمارية", "الهيروغليفية المصرية", "الحروف الصينية", "الخط الخطي ب"],
            "fact": "يُكتب بالحروف الصينية منذ أكثر من 3000 سنة، أما الأنظمة "
                    "الثلاثة الأخرى فقد اندثرت.",
        },
    },
    {
        "answer": 1,
        "en": {
            "question": "Latin, Greek, Cyrillic, Arabic and Hebrew letters all descend from which alphabet?",
            "options": ["Sumerian", "Phoenician", "Etruscan", "Coptic"],
            "fact": "Almost every alphabet in use today traces back to "
                    "Phoenician traders around 1050 BCE.",
        },
        "es": {
            "question": "Las letras latinas, griegas, cirílicas, árabes y hebreas descienden de un mismo alfabeto. ¿Cuál?",
            "options": ["El sumerio", "El fenicio", "El etrusco", "El copto"],
            "fact": "Casi todos los alfabetos actuales se remontan a los "
                    "comerciantes fenicios, hacia el año 1050 a. C.",
        },
        "fr": {
            "question": "Les lettres latines, grecques, cyrilliques, arabes et hébraïques descendent d'un même alphabet. Lequel ?",
            "options": ["Le sumérien", "Le phénicien", "L'étrusque", "Le copte"],
            "fact": "Presque tous les alphabets actuels remontent aux "
                    "marchands phéniciens, vers 1050 av. J.-C.",
        },
        "pt": {
            "question": "As letras latinas, gregas, cirílicas, árabes e hebraicas descendem de que alfabeto?",
            "options": ["Do sumério", "Do fenício", "Do etrusco", "Do copta"],
            "fact": "Quase todos os alfabetos de hoje remontam aos "
                    "comerciantes fenícios, por volta de 1050 a.C.",
        },
        "ru": {
            "question": "От какого алфавита произошли латинские, греческие, кириллические, арабские и еврейские буквы?",
            "options": ["От шумерского", "От финикийского", "От этрусского", "От коптского"],
            "fact": "Почти все современные алфавиты восходят к письму "
                    "финикийских купцов около 1050 года до н. э.",
        },
        "ar": {
            "question": "من أي أبجدية انحدرت الحروف اللاتينية واليونانية والسيريلية والعربية والعبرية؟",
            "options": ["السومرية", "الفينيقية", "الإتروسكية", "القبطية"],
            "fact": "تعود معظم أبجديات اليوم إلى كتابة التجار الفينيقيين نحو "
                    "عام 1050 قبل الميلاد.",
        },
    },
    {
        "answer": 2,
        "en": {
            "question": "What is a creole language?",
            "options": [
                "A regional accent of a larger language",
                "A language with no written form",
                "A full language that grew out of a contact pidgin and became a mother tongue",
                "A language used only in worship",
            ],
            "fact": "Haitian Creole began as a contact language and now has "
                    "millions of native speakers and official status.",
        },
        "es": {
            "question": "¿Qué es una lengua criolla?",
            "options": [
                "Un acento regional de una lengua mayor",
                "Una lengua sin forma escrita",
                "Una lengua plena que nació de un pidgin de contacto y pasó a ser lengua materna",
                "Una lengua que solo se usa en el culto",
            ],
            "fact": "El criollo haitiano nació como lengua de contacto y hoy "
                    "tiene millones de hablantes nativos y estatus oficial.",
        },
        "fr": {
            "question": "Qu'est-ce qu'une langue créole ?",
            "options": [
                "Un accent régional d'une grande langue",
                "Une langue sans forme écrite",
                "Une langue à part entière née d'un pidgin de contact et devenue langue maternelle",
                "Une langue réservée au culte",
            ],
            "fact": "Le créole haïtien est né comme langue de contact ; il "
                    "compte aujourd'hui des millions de locuteurs natifs et "
                    "un statut officiel.",
        },
        "pt": {
            "question": "O que é uma língua crioula?",
            "options": [
                "Um sotaque regional de uma língua maior",
                "Uma língua sem forma escrita",
                "Uma língua completa que nasceu de um pidgin de contacto e passou a língua materna",
                "Uma língua usada apenas no culto",
            ],
            "fact": "O crioulo haitiano nasceu como língua de contacto e tem "
                    "hoje milhões de falantes nativos e estatuto oficial.",
        },
        "ru": {
            "question": "Что такое креольский язык?",
            "options": [
                "Региональный акцент крупного языка",
                "Язык без письменности",
                "Полноценный язык, выросший из контактного пиджина и ставший родным",
                "Язык, используемый только в богослужении",
            ],
            "fact": "Гаитянский креольский возник как контактный язык, а "
                    "сегодня у него миллионы носителей и статус "
                    "государственного.",
        },
        "ar": {
            "question": "ما اللغة الكريولية؟",
            "options": [
                "لهجة محلية للغة كبرى",
                "لغة بلا صورة مكتوبة",
                "لغة كاملة نشأت من لغة تخاطب مبسّطة ثم صارت لغة أمّ",
                "لغة لا تُستعمل إلا في العبادة",
            ],
            "fact": "بدأت الكريولية الهايتية لغة تخاطب، ولها اليوم ملايين "
                    "الناطقين بها وصفة رسمية.",
        },
    },
    {
        "answer": 0,
        "en": {
            "question": "What is a phoneme?",
            "options": [
                "The smallest sound unit that can change a word's meaning",
                "A letter of the alphabet",
                "A syllable carrying stress",
                "A word with no meaning of its own",
            ],
            "fact": "\"Pat\" and \"bat\" differ by exactly one phoneme — and "
                    "that is enough to make them different words.",
        },
        "es": {
            "question": "¿Qué es un fonema?",
            "options": [
                "La unidad sonora más pequeña capaz de cambiar el significado de una palabra",
                "Una letra del alfabeto",
                "Una sílaba tónica",
                "Una palabra sin significado propio",
            ],
            "fact": "«Pata» y «bata» se diferencian en un solo fonema, y eso "
                    "basta para que sean palabras distintas.",
        },
        "fr": {
            "question": "Qu'est-ce qu'un phonème ?",
            "options": [
                "La plus petite unité sonore capable de changer le sens d'un mot",
                "Une lettre de l'alphabet",
                "Une syllabe accentuée",
                "Un mot sans signification propre",
            ],
            "fact": "« Pain » et « bain » ne diffèrent que par un phonème, et "
                    "cela suffit à en faire deux mots.",
        },
        "pt": {
            "question": "O que é um fonema?",
            "options": [
                "A menor unidade sonora capaz de mudar o significado de uma palavra",
                "Uma letra do alfabeto",
                "Uma sílaba tónica",
                "Uma palavra sem significado próprio",
            ],
            "fact": "«Pata» e «bata» distinguem-se por um único fonema, e "
                    "isso basta para serem palavras diferentes.",
        },
        "ru": {
            "question": "Что такое фонема?",
            "options": [
                "Наименьшая звуковая единица, способная изменить значение слова",
                "Буква алфавита",
                "Ударный слог",
                "Слово без собственного значения",
            ],
            "fact": "«Дом» и «том» различаются одной фонемой — и этого "
                    "достаточно, чтобы это были разные слова.",
        },
        "ar": {
            "question": "ما الفونيم (الوحدة الصوتية)؟",
            "options": [
                "أصغر وحدة صوتية قادرة على تغيير معنى الكلمة",
                "حرف من حروف الأبجدية",
                "مقطع يحمل النبر",
                "كلمة لا معنى لها بذاتها",
            ],
            "fact": "تختلف «سار» عن «صار» بفونيم واحد، ويكفي ذلك لتصبحا "
                    "كلمتين مختلفتين.",
        },
    },
    {
        "answer": 0,
        "en": {
            "question": "Which language normally leaves out \"to be\" in ordinary present-tense sentences?",
            "options": ["Russian", "German", "French", "Italian"],
            "fact": "Russian says \"on vrach\" — literally \"he doctor\". The "
                    "present-tense copula simply isn't there.",
        },
        "es": {
            "question": "¿Qué lengua suele omitir el verbo «ser» en las frases corrientes en presente?",
            "options": ["El ruso", "El alemán", "El francés", "El italiano"],
            "fact": "En ruso se dice «он врач», literalmente «él médico»: la "
                    "cópula en presente sencillamente no aparece.",
        },
        "fr": {
            "question": "Quelle langue omet normalement le verbe « être » dans les phrases ordinaires au présent ?",
            "options": ["Le russe", "L'allemand", "Le français", "L'italien"],
            "fact": "En russe on dit « он врач », littéralement « il médecin » : "
                    "la copule au présent n'existe tout simplement pas.",
        },
        "pt": {
            "question": "Que língua costuma omitir o verbo «ser» nas frases correntes no presente?",
            "options": ["O russo", "O alemão", "O francês", "O italiano"],
            "fact": "Em russo diz-se «он врач», literalmente «ele médico»: a "
                    "cópula no presente simplesmente não aparece.",
        },
        "ru": {
            "question": "В каком языке в обычных предложениях настоящего времени связка «быть» опускается?",
            "options": ["В русском", "В немецком", "Во французском", "В итальянском"],
            "fact": "По-русски говорят «он врач» без связки, тогда как "
                    "по-английски обязательно «he is a doctor».",
        },
        "ar": {
            "question": "أي لغة تحذف عادةً فعل الكينونة في جمل المضارع البسيطة؟",
            "options": ["الروسية", "الألمانية", "الفرنسية", "الإيطالية"],
            "fact": "تقول الروسية «он врач» أي «هو طبيب» بلا فعل رابط، تمامًا "
                    "كالجملة الاسمية في العربية.",
        },
    },
    {
        "answer": 1,
        "en": {
            "question": "What does \"SOV\" describe about a language?",
            "options": [
                "How many vowels it has",
                "The usual order of subject, object and verb",
                "How formal its writing is",
                "How many speakers it has",
            ],
            "fact": "Subject-object-verb is the world's most common order — "
                    "Japanese, Turkish and Hindi all use it. English is "
                    "subject-verb-object.",
        },
        "es": {
            "question": "¿Qué describe la sigla «SOV» sobre una lengua?",
            "options": [
                "Cuántas vocales tiene",
                "El orden habitual de sujeto, objeto y verbo",
                "Lo formal que es su escritura",
                "Cuántos hablantes tiene",
            ],
            "fact": "Sujeto-objeto-verbo es el orden más frecuente del mundo: "
                    "lo usan el japonés, el turco y el hindi. El español es "
                    "sujeto-verbo-objeto.",
        },
        "fr": {
            "question": "Que décrit le sigle « SOV » à propos d'une langue ?",
            "options": [
                "Le nombre de ses voyelles",
                "L'ordre habituel du sujet, de l'objet et du verbe",
                "Le degré de formalité de son écriture",
                "Son nombre de locuteurs",
            ],
            "fact": "Sujet-objet-verbe est l'ordre le plus répandu au monde : "
                    "le japonais, le turc et le hindi l'emploient. Le "
                    "français est sujet-verbe-objet.",
        },
        "pt": {
            "question": "O que descreve a sigla «SOV» sobre uma língua?",
            "options": [
                "Quantas vogais tem",
                "A ordem habitual de sujeito, objeto e verbo",
                "O grau de formalidade da sua escrita",
                "Quantos falantes tem",
            ],
            "fact": "Sujeito-objeto-verbo é a ordem mais comum do mundo: "
                    "usam-na o japonês, o turco e o híndi. O português é "
                    "sujeito-verbo-objeto.",
        },
        "ru": {
            "question": "Что описывает сокращение «SOV» применительно к языку?",
            "options": [
                "Количество гласных",
                "Обычный порядок подлежащего, дополнения и сказуемого",
                "Степень официальности письменной речи",
                "Число носителей",
            ],
            "fact": "Порядок «подлежащее — дополнение — сказуемое» самый "
                    "распространённый в мире: так строятся японский, турецкий "
                    "и хинди.",
        },
        "ar": {
            "question": "ماذا يصف الرمز «SOV» في اللغة؟",
            "options": [
                "عدد حروف العلة فيها",
                "الترتيب المعتاد للفاعل والمفعول والفعل",
                "درجة رسمية كتابتها",
                "عدد الناطقين بها",
            ],
            "fact": "ترتيب الفاعل ثم المفعول ثم الفعل هو الأكثر شيوعًا في "
                    "العالم، وتتبعه اليابانية والتركية والهندية.",
        },
    },
    {
        "answer": 1,
        "en": {
            "question": "Roughly how many class hours does an English speaker need to work professionally in Spanish or French?",
            "options": ["About 200", "About 700", "About 2,000", "About 5,000"],
            "fact": "The US Foreign Service Institute estimates 600-750 hours "
                    "— and roughly three times that for Arabic, Chinese, "
                    "Japanese or Korean.",
        },
        "es": {
            "question": "¿Cuántas horas de clase necesita aproximadamente un anglohablante para trabajar en español o francés?",
            "options": ["Unas 200", "Unas 700", "Unas 2.000", "Unas 5.000"],
            "fact": "El Foreign Service Institute estadounidense calcula "
                    "entre 600 y 750 horas, y unas tres veces más para el "
                    "árabe, el chino, el japonés o el coreano.",
        },
        "fr": {
            "question": "Combien d'heures de cours faut-il environ à un anglophone pour travailler en espagnol ou en français ?",
            "options": ["Environ 200", "Environ 700", "Environ 2 000", "Environ 5 000"],
            "fact": "Le Foreign Service Institute américain estime 600 à 750 "
                    "heures, et environ trois fois plus pour l'arabe, le "
                    "chinois, le japonais ou le coréen.",
        },
        "pt": {
            "question": "Quantas horas de aulas precisa, mais ou menos, um falante de inglês para trabalhar em espanhol ou francês?",
            "options": ["Cerca de 200", "Cerca de 700", "Cerca de 2.000", "Cerca de 5.000"],
            "fact": "O Foreign Service Institute norte-americano estima 600 a "
                    "750 horas, e cerca de três vezes mais para árabe, "
                    "chinês, japonês ou coreano.",
        },
        "ru": {
            "question": "Сколько примерно учебных часов нужно носителю английского, чтобы работать на испанском или французском?",
            "options": ["Около 200", "Около 700", "Около 2000", "Около 5000"],
            "fact": "Институт дипломатической службы США оценивает это в "
                    "600–750 часов, а для арабского, китайского, японского и "
                    "корейского — примерно втрое больше.",
        },
        "ar": {
            "question": "كم ساعة دراسية يحتاج تقريبًا متحدث الإنجليزية ليعمل مهنيًا بالإسبانية أو الفرنسية؟",
            "options": ["نحو 200", "نحو 700", "نحو 2000", "نحو 5000"],
            "fact": "يقدّر معهد الخدمة الخارجية الأمريكي ذلك بـ600 إلى 750 "
                    "ساعة، وثلاثة أضعافها تقريبًا للعربية والصينية واليابانية "
                    "والكورية.",
        },
    },
    {
        "answer": 2,
        "en": {
            "question": "What is code-switching?",
            "options": [
                "Writing one language in another's alphabet",
                "Learning two languages one after the other",
                "Moving between two languages within a single conversation",
                "Translating word by word",
            ],
            "fact": "It follows regular grammatical rules — bilingual "
                    "speakers switch at predictable points, not at random.",
        },
        "es": {
            "question": "¿Qué es la alternancia de códigos?",
            "options": [
                "Escribir una lengua con el alfabeto de otra",
                "Aprender dos lenguas una después de otra",
                "Pasar de una lengua a otra dentro de una misma conversación",
                "Traducir palabra por palabra",
            ],
            "fact": "Sigue reglas gramaticales regulares: los bilingües "
                    "cambian en puntos predecibles, no al azar.",
        },
        "fr": {
            "question": "Qu'est-ce que l'alternance codique ?",
            "options": [
                "Écrire une langue avec l'alphabet d'une autre",
                "Apprendre deux langues l'une après l'autre",
                "Passer d'une langue à l'autre au sein d'une même conversation",
                "Traduire mot à mot",
            ],
            "fact": "Elle obéit à des règles grammaticales régulières : les "
                    "bilingues changent de langue à des endroits prévisibles, "
                    "pas au hasard.",
        },
        "pt": {
            "question": "O que é a alternância de código?",
            "options": [
                "Escrever uma língua com o alfabeto de outra",
                "Aprender duas línguas uma a seguir à outra",
                "Passar de uma língua para outra dentro da mesma conversa",
                "Traduzir palavra a palavra",
            ],
            "fact": "Segue regras gramaticais regulares: os bilingues mudam "
                    "em pontos previsíveis, não ao acaso.",
        },
        "ru": {
            "question": "Что такое переключение кодов?",
            "options": [
                "Запись одного языка алфавитом другого",
                "Изучение двух языков один за другим",
                "Переход с одного языка на другой внутри одного разговора",
                "Дословный перевод",
            ],
            "fact": "Оно подчиняется грамматическим правилам: билингвы "
                    "переключаются в предсказуемых местах, а не случайно.",
        },
        "ar": {
            "question": "ما التناوب اللغوي (code-switching)؟",
            "options": [
                "كتابة لغة بأبجدية لغة أخرى",
                "تعلّم لغتين واحدة بعد الأخرى",
                "الانتقال بين لغتين داخل الحديث الواحد",
                "الترجمة كلمة بكلمة",
            ],
            "fact": "يخضع لقواعد نحوية منتظمة، فالمتحدثون بلغتين ينتقلون في "
                    "مواضع متوقَّعة لا عشوائية.",
        },
    },
    {
        "answer": 0,
        "en": {
            "question": "Why does spacing your reviews out beat cramming them together?",
            "options": [
                "Because recalling something just before you forget it strengthens the memory more",
                "Because short sessions are easier to fit into a day",
                "Because the brain can only hold seven words a day",
                "Because it lets you skip the hard words",
            ],
            "fact": "Hermann Ebbinghaus measured the forgetting curve on "
                    "himself in the 1880s; spaced repetition puts the review "
                    "just before the drop.",
        },
        "es": {
            "question": "¿Por qué es mejor espaciar los repasos que amontonarlos?",
            "options": [
                "Porque recordar algo justo antes de olvidarlo refuerza más la memoria",
                "Porque las sesiones cortas caben mejor en el día",
                "Porque el cerebro solo retiene siete palabras al día",
                "Porque permite saltarse las palabras difíciles",
            ],
            "fact": "Hermann Ebbinghaus midió la curva del olvido en sí mismo "
                    "en la década de 1880; la repetición espaciada coloca el "
                    "repaso justo antes de la caída.",
        },
        "fr": {
            "question": "Pourquoi vaut-il mieux espacer ses révisions que les entasser ?",
            "options": [
                "Parce que se souvenir juste avant d'oublier renforce davantage la mémoire",
                "Parce que les sessions courtes tiennent mieux dans une journée",
                "Parce que le cerveau ne retient que sept mots par jour",
                "Parce que cela permet d'éviter les mots difficiles",
            ],
            "fact": "Hermann Ebbinghaus a mesuré la courbe de l'oubli sur "
                    "lui-même dans les années 1880 ; la répétition espacée "
                    "place la révision juste avant la chute.",
        },
        "pt": {
            "question": "Porque é melhor espaçar as revisões do que amontoá-las?",
            "options": [
                "Porque recordar algo mesmo antes de o esquecer reforça mais a memória",
                "Porque as sessões curtas cabem melhor no dia",
                "Porque o cérebro só retém sete palavras por dia",
                "Porque permite saltar as palavras difíceis",
            ],
            "fact": "Hermann Ebbinghaus mediu a curva do esquecimento em si "
                    "próprio nos anos 1880; a repetição espaçada põe a "
                    "revisão mesmo antes da queda.",
        },
        "ru": {
            "question": "Почему повторять с интервалами лучше, чем зубрить всё сразу?",
            "options": [
                "Потому что припоминание перед самым забыванием укрепляет память сильнее",
                "Потому что короткие занятия проще вписать в день",
                "Потому что мозг удерживает только семь слов в день",
                "Потому что так можно пропускать трудные слова",
            ],
            "fact": "Герман Эббингауз измерил кривую забывания на себе в "
                    "1880-х годах; интервальное повторение ставит повтор "
                    "прямо перед спадом.",
        },
        "ar": {
            "question": "لماذا تتفوّق المراجعة المتباعدة على الحشو المتواصل؟",
            "options": [
                "لأن استدعاء المعلومة قبيل نسيانها يثبّتها في الذاكرة أكثر",
                "لأن الجلسات القصيرة أسهل في ترتيب اليوم",
                "لأن الدماغ لا يحفظ أكثر من سبع كلمات يوميًا",
                "لأنها تتيح تخطّي الكلمات الصعبة",
            ],
            "fact": "قاس هيرمان إبنغهاوس منحنى النسيان على نفسه في ثمانينيات "
                    "القرن التاسع عشر، والتكرار المتباعد يضع المراجعة قبيل "
                    "الهبوط مباشرة.",
        },
    },
    {
        "answer": 1,
        "en": {"question": "Which of these languages uses click consonants?",
               "options": ["Turkish", "Xhosa", "Russian", "Catalan"],
               "fact": "Xhosa has around eighteen click consonants, adopted "
                       "centuries ago from neighbouring Khoisan languages — "
                       "the X in “Xhosa” is itself a click."},
        "es": {"question": "¿Cuál de estas lenguas usa consonantes de chasquido (clics)?",
               "options": ["El turco", "El xhosa", "El ruso", "El catalán"],
               "fact": "El xhosa tiene unos dieciocho clics, adoptados hace "
                       "siglos de las lenguas joisanas vecinas: la X de "
                       "“xhosa” es en sí misma un clic."},
        "fr": {"question": "Laquelle de ces langues utilise des consonnes à clic ?",
               "options": ["Le turc", "Le xhosa", "Le russe", "Le catalan"],
               "fact": "Le xhosa compte environ dix-huit clics, empruntés il y "
                       "a des siècles aux langues khoïsanes voisines — le X de "
                       "« xhosa » est lui-même un clic."},
        "pt": {"question": "Qual destas línguas usa consoantes de clique?",
               "options": ["O turco", "O xhosa", "O russo", "O catalão"],
               "fact": "O xhosa tem cerca de dezoito cliques, adotados há "
                       "séculos das línguas khoisan vizinhas — o X de "
                       "“xhosa” é, ele próprio, um clique."},
        "ru": {"question": "В каком из этих языков есть щёлкающие согласные (клики)?",
               "options": ["В турецком", "В коса", "В русском", "В каталанском"],
               "fact": "В языке коса около восемнадцати щёлкающих согласных, "
                       "заимствованных столетия назад у соседних койсанских "
                       "языков — буква X в названии «Xhosa» сама "
                       "обозначает щелчок."},
        "ar": {"question": "أي من هذه اللغات تستخدم الأصوات الطقطقية (النقرية)؟",
               "options": ["التركية", "الكوسا", "الروسية", "الكتالانية"],
               "fact": "في لغة الكوسا نحو ثمانية عشر صوتًا طقطقيًا، اقتُبست قبل "
                       "قرون من لغات الخويسان المجاورة — وحرف X في اسم "
                       "“Xhosa” هو نفسه صوت طقطقة."},
    },
    {
        "answer": 2,
        "en": {"question": "Which alphabet was deliberately invented, rather than evolving over centuries?",
               "options": ["Latin", "Greek", "Korean Hangul", "Cyrillic"],
               "fact": "Hangul was published in 1446 under King Sejong so "
                       "ordinary people could learn to read; its letter shapes "
                       "sketch the position of the tongue and lips."},
        "es": {"question": "¿Qué alfabeto fue inventado deliberadamente, en lugar de evolucionar durante siglos?",
               "options": ["El latino", "El griego", "El hangul coreano", "El cirílico"],
               "fact": "El hangul se publicó en 1446 bajo el rey Sejong para "
                       "que la gente corriente pudiera aprender a leer; sus "
                       "letras dibujan la posición de la lengua y los labios."},
        "fr": {"question": "Quel alphabet a été inventé délibérément, au lieu d'évoluer au fil des siècles ?",
               "options": ["Le latin", "Le grec", "Le hangeul coréen", "Le cyrillique"],
               "fact": "Le hangeul a été publié en 1446 sous le roi Sejong "
                       "pour que le peuple puisse apprendre à lire ; la forme "
                       "des lettres esquisse la position de la langue et des "
                       "lèvres."},
        "pt": {"question": "Que alfabeto foi inventado deliberadamente, em vez de evoluir ao longo de séculos?",
               "options": ["O latino", "O grego", "O hangul coreano", "O cirílico"],
               "fact": "O hangul foi publicado em 1446 sob o rei Sejong para "
                       "que as pessoas comuns pudessem aprender a ler; as "
                       "letras desenham a posição da língua e dos lábios."},
        "ru": {"question": "Какой алфавит был создан намеренно, а не складывался веками?",
               "options": ["Латинский", "Греческий", "Корейский хангыль", "Кириллица"],
               "fact": "Хангыль обнародовали в 1446 году при короле Седжоне, "
                       "чтобы читать мог простой народ; форма букв "
                       "схематически изображает положение языка и губ."},
        "ar": {"question": "أي أبجدية اختُرعت اختراعًا مقصودًا بدل أن تتطور عبر القرون؟",
               "options": ["اللاتينية", "اليونانية", "الهانغل الكورية", "السيريلية"],
               "fact": "نُشرت الهانغل عام 1446 في عهد الملك سيجونغ ليتمكن عامة "
                       "الناس من تعلم القراءة؛ وأشكال حروفها ترسم وضع اللسان "
                       "والشفتين."},
    },
    {
        "answer": 2,
        "en": {"question": "What is true of sign languages like ASL?",
               "options": ["They are pantomime",
                           "They are signed versions of the local spoken language",
                           "They are full languages with their own grammar",
                           "They are the same all over the world"],
               "fact": "American Sign Language is closer to French Sign "
                       "Language than to British — its grammar travelled with "
                       "a school founded from Paris, not with English."},
        "es": {"question": "¿Qué es cierto sobre las lenguas de señas como la ASL?",
               "options": ["Son pantomima",
                           "Son versiones en señas de la lengua hablada local",
                           "Son lenguas completas con gramática propia",
                           "Son iguales en todo el mundo"],
               "fact": "La lengua de señas americana se parece más a la "
                       "francesa que a la británica: su gramática viajó con "
                       "una escuela fundada desde París, no con el inglés."},
        "fr": {"question": "Que peut-on dire des langues des signes comme l'ASL ?",
               "options": ["C'est de la pantomime",
                           "Ce sont des versions signées de la langue parlée locale",
                           "Ce sont des langues à part entière, avec leur propre grammaire",
                           "Elles sont identiques dans le monde entier"],
               "fact": "La langue des signes américaine est plus proche de la "
                       "française que de la britannique : sa grammaire a "
                       "voyagé avec une école fondée depuis Paris, pas avec "
                       "l'anglais."},
        "pt": {"question": "O que é verdade sobre as línguas de sinais como a ASL?",
               "options": ["São pantomima",
                           "São versões em sinais da língua falada local",
                           "São línguas completas, com gramática própria",
                           "São iguais no mundo inteiro"],
               "fact": "A língua de sinais americana é mais próxima da "
                       "francesa do que da britânica: a gramática viajou com "
                       "uma escola fundada a partir de Paris, não com o "
                       "inglês."},
        "ru": {"question": "Что верно о жестовых языках, таких как амслен (ASL)?",
               "options": ["Это пантомима",
                           "Это жестовые версии местного звучащего языка",
                           "Это полноценные языки со своей грамматикой",
                           "Они одинаковы во всём мире"],
               "fact": "Американский жестовый язык ближе к французскому, чем "
                       "к британскому: его грамматика пришла со школой, "
                       "основанной выходцами из Парижа, а не с английским."},
        "ar": {"question": "ما الصحيح بشأن لغات الإشارة مثل لغة الإشارة الأمريكية؟",
               "options": ["إنها تمثيل إيمائي",
                           "إنها نسخ بالإشارة من اللغة المنطوقة المحلية",
                           "إنها لغات كاملة لها قواعدها الخاصة",
                           "إنها واحدة في كل أنحاء العالم"],
               "fact": "لغة الإشارة الأمريكية أقرب إلى الفرنسية منها إلى "
                       "البريطانية: فقد جاءت قواعدها مع مدرسة أُسست من باريس، "
                       "لا مع الإنجليزية."},
    },
    {
        "answer": 0,
        "en": {"question": "On La Gomera in the Canary Islands, Spanish can be…",
               "options": ["whistled", "drummed", "hummed", "clapped"],
               "fact": "Silbo Gomero turns Spanish into whistles that carry "
                       "for kilometres across ravines — and it is taught in "
                       "the island's schools today."},
        "es": {"question": "En La Gomera, en las islas Canarias, el español se puede…",
               "options": ["silbar", "tocar con tambores", "tararear", "aplaudir"],
               "fact": "El silbo gomero convierte el español en silbidos que "
                       "cruzan barrancos a kilómetros de distancia, y hoy se "
                       "enseña en las escuelas de la isla."},
        "fr": {"question": "À La Gomera, aux îles Canaries, l'espagnol peut être…",
               "options": ["sifflé", "tambouriné", "fredonné", "frappé dans les mains"],
               "fact": "Le silbo gomero transforme l'espagnol en sifflements "
                       "qui portent à des kilomètres par-dessus les ravins — "
                       "et il s'enseigne aujourd'hui à l'école sur l'île."},
        "pt": {"question": "Em La Gomera, nas ilhas Canárias, o espanhol pode ser…",
               "options": ["assobiado", "tocado em tambores", "cantarolado", "batido com palmas"],
               "fact": "O silbo gomero converte o espanhol em assobios que "
                       "atravessam ravinas a quilómetros de distância — e hoje "
                       "é ensinado nas escolas da ilha."},
        "ru": {"question": "На острове Гомера (Канарские острова) на испанском можно…",
               "options": ["свистеть", "барабанить", "напевать", "хлопать"],
               "fact": "Сильбо гомеро превращает испанский в свист, слышный "
                       "за километры через ущелья, — и сегодня ему учат в "
                       "школах острова."},
        "ar": {"question": "في جزيرة لا غوميرا بجزر الكناري، يمكن للإسبانية أن…",
               "options": ["تُصفَّر", "تُقرَع بالطبول", "تُدندَن", "تُصفَّق"],
               "fact": "يحوّل “الصفير الغوميري” الإسبانية إلى صفير يُسمع "
                       "على بُعد كيلومترات عبر الوديان — وهو يُدرَّس اليوم في "
                       "مدارس الجزيرة."},
    },
    {
        "answer": 1,
        "en": {"question": "What is the most common basic word order in the world's languages?",
               "options": ["Subject–verb–object, like English",
                           "Subject–object–verb, like Turkish and Japanese",
                           "Verb first, like Welsh",
                           "Object first"],
               "fact": "Nearly half of all languages put the verb last. "
                       "Verb-first languages like Welsh and Māori are far "
                       "rarer, and object-first ones are vanishingly so."},
        "es": {"question": "¿Cuál es el orden de palabras básico más común entre las lenguas del mundo?",
               "options": ["Sujeto–verbo–objeto, como el inglés",
                           "Sujeto–objeto–verbo, como el turco y el japonés",
                           "El verbo primero, como el galés",
                           "El objeto primero"],
               "fact": "Casi la mitad de las lenguas ponen el verbo al final. "
                       "Las lenguas con verbo inicial, como el galés o el "
                       "maorí, son mucho más raras; las de objeto inicial, "
                       "rarísimas."},
        "fr": {"question": "Quel est l'ordre des mots de base le plus répandu parmi les langues du monde ?",
               "options": ["Sujet–verbe–objet, comme l'anglais",
                           "Sujet–objet–verbe, comme le turc et le japonais",
                           "Le verbe d'abord, comme le gallois",
                           "L'objet d'abord"],
               "fact": "Près de la moitié des langues placent le verbe en "
                       "dernier. Les langues à verbe initial comme le gallois "
                       "ou le māori sont bien plus rares, et celles à objet "
                       "initial, exceptionnelles."},
        "pt": {"question": "Qual é a ordem de palavras básica mais comum entre as línguas do mundo?",
               "options": ["Sujeito–verbo–objeto, como o inglês",
                           "Sujeito–objeto–verbo, como o turco e o japonês",
                           "O verbo primeiro, como o galês",
                           "O objeto primeiro"],
               "fact": "Quase metade das línguas põe o verbo no fim. Línguas "
                       "com verbo inicial, como o galês e o māori, são bem "
                       "mais raras; com objeto inicial, raríssimas."},
        "ru": {"question": "Какой базовый порядок слов встречается в языках мира чаще всего?",
               "options": ["Подлежащее–сказуемое–дополнение, как в английском",
                           "Подлежащее–дополнение–сказуемое, как в турецком и японском",
                           "Сначала глагол, как в валлийском",
                           "Сначала дополнение"],
               "fact": "Почти половина языков ставит глагол в конец. Языки, "
                       "начинающие с глагола, вроде валлийского и маори, "
                       "заметно реже, а начинающие с дополнения — единичны."},
        "ar": {"question": "ما ترتيب الكلمات الأساسي الأكثر شيوعًا بين لغات العالم؟",
               "options": ["فاعل–فعل–مفعول، كما في الإنجليزية",
                           "فاعل–مفعول–فعل، كما في التركية واليابانية",
                           "الفعل أولًا، كما في الويلزية",
                           "المفعول أولًا"],
               "fact": "نحو نصف اللغات يضع الفعل في آخر الجملة. أما اللغات "
                       "التي تبدأ بالفعل، كالويلزية والماورية، فأندر بكثير، "
                       "والتي تبدأ بالمفعول نادرة للغاية."},
    },
    {
        "answer": 0,
        "en": {"question": "Besides singular and plural, what third grammatical number does Arabic have?",
               "options": ["The dual, for exactly two",
                           "The trial, for exactly three",
                           "The paucal, for a few",
                           "It has no third number"],
               "fact": "In Arabic, kitābān means “two books” with no word "
                       "for “two” at all — the ending carries it. Slovene "
                       "and Ancient Greek kept a dual as well."},
        "es": {"question": "Además del singular y el plural, ¿qué tercer número gramatical tiene el árabe?",
               "options": ["El dual, para exactamente dos",
                           "El trial, para exactamente tres",
                           "El paucal, para unos pocos",
                           "No tiene un tercer número"],
               "fact": "En árabe, kitābān significa “dos libros” sin "
                       "ninguna palabra para “dos”: la terminación lo "
                       "dice todo. El esloveno y el griego antiguo también "
                       "conservaron un dual."},
        "fr": {"question": "Outre le singulier et le pluriel, quel troisième nombre grammatical possède l'arabe ?",
               "options": ["Le duel, pour exactement deux",
                           "Le triel, pour exactement trois",
                           "Le paucal, pour quelques-uns",
                           "Il n'a pas de troisième nombre"],
               "fact": "En arabe, kitābān signifie « deux livres » sans "
                       "aucun mot pour « deux » : c'est la terminaison "
                       "qui le dit. Le slovène et le grec ancien ont eux aussi "
                       "conservé un duel."},
        "pt": {"question": "Além do singular e do plural, que terceiro número gramatical tem o árabe?",
               "options": ["O dual, para exatamente dois",
                           "O trial, para exatamente três",
                           "O paucal, para uns poucos",
                           "Não tem um terceiro número"],
               "fact": "Em árabe, kitābān significa “dois livros” sem "
                       "palavra nenhuma para “dois”: a terminação diz "
                       "tudo. O esloveno e o grego antigo também conservaram "
                       "um dual."},
        "ru": {"question": "Кроме единственного и множественного, какое третье грамматическое число есть в арабском?",
               "options": ["Двойственное — ровно для двух",
                           "Тройственное — ровно для трёх",
                           "Паукальное — для нескольких",
                           "Третьего числа нет"],
               "fact": "По-арабски kitābān значит «две книги» — без "
                       "всякого слова «две»: всё делает окончание. "
                       "Двойственное число сохранили также словенский и "
                       "древнегреческий."},
        "ar": {"question": "إلى جانب المفرد والجمع، ما العدد النحوي الثالث في العربية؟",
               "options": ["المثنى، لاثنين بالضبط",
                           "الثلاثي، لثلاثة بالضبط",
                           "عدد القِلة، لبضعة أشياء",
                           "لا عدد ثالث فيها"],
               "fact": "“كتابان” تعني كتابين اثنين من دون ذكر كلمة "
                       "“اثنين” أصلًا — فالنهاية تحمل المعنى. وقد احتفظت "
                       "السلوفينية واليونانية القديمة بالمثنى أيضًا."},
    },
    {
        "answer": 0,
        "en": {"question": "In Turkish, the verb ending can change depending on…",
               "options": ["whether you saw it happen or only heard about it",
                           "how polite you are being",
                           "the size of the object",
                           "the day of the week"],
               "fact": "Gitti is “he went (I witnessed it)”; gitmiş is "
                       "“he apparently went”. Some Amazonian languages "
                       "mark five grades of evidence — and marking one is not "
                       "optional."},
        "es": {"question": "En turco, la terminación del verbo puede cambiar según…",
               "options": ["si lo viste tú mismo o solo te lo contaron",
                           "el grado de cortesía",
                           "el tamaño del objeto",
                           "el día de la semana"],
               "fact": "Gitti es “se fue (yo lo vi)”; gitmiş, “por lo "
                       "visto se fue”. Algunas lenguas amazónicas marcan "
                       "cinco grados de evidencia, y marcarla es obligatorio."},
        "fr": {"question": "En turc, la terminaison du verbe peut changer selon…",
               "options": ["que vous avez vu la chose ou qu'on vous l'a racontée",
                           "le degré de politesse",
                           "la taille de l'objet",
                           "le jour de la semaine"],
               "fact": "Gitti : « il est parti (je l'ai vu) » ; gitmiş : "
                       "« il serait parti, paraît-il ». Certaines "
                       "langues d'Amazonie distinguent cinq degrés de preuve — "
                       "et le marquage est obligatoire."},
        "pt": {"question": "Em turco, a terminação do verbo pode mudar conforme…",
               "options": ["você viu acontecer ou só ouviu contar",
                           "o grau de cortesia",
                           "o tamanho do objeto",
                           "o dia da semana"],
               "fact": "Gitti é “ele foi (eu vi)”; gitmiş é “ao que "
                       "parece, ele foi”. Algumas línguas amazónicas marcam "
                       "cinco graus de evidência — e marcar é obrigatório."},
        "ru": {"question": "В турецком окончание глагола может меняться в зависимости от того…",
               "options": ["видели ли вы событие сами или знаете о нём с чужих слов",
                           "насколько вежливо вы говорите",
                           "какого размера предмет",
                           "какой сегодня день недели"],
               "fact": "Gitti — «он ушёл (я видел)»; gitmiş — «он, "
                       "судя по всему, ушёл». В некоторых амазонских "
                       "языках различается пять степеней достоверности, и "
                       "выбрать одну из них обязательно."},
        "ar": {"question": "في التركية، قد تتغير نهاية الفعل بحسب…",
               "options": ["هل رأيتَ الحدث بنفسك أم سمعت عنه فقط",
                           "درجة التهذيب",
                           "حجم الشيء",
                           "يوم الأسبوع"],
               "fact": "Gitti تعني “ذهب (وقد رأيتُه)”، أما gitmiş فتعني "
                       "“يبدو أنه ذهب”. بعض لغات الأمازون تميّز خمس درجات "
                       "من الدليل — والتمييز إلزامي لا اختياري."},
    },
    {
        "answer": 0,
        "en": {"question": "If a language has only three colour words, which are they almost always?",
               "options": ["Black, white and red",
                           "Blue, green and yellow",
                           "Red, green and blue",
                           "Black, white and blue"],
               "fact": "Colour vocabularies grow in a near-universal order: "
                       "dark, light, then red — blue arrives late. Homer "
                       "famously calls the sea “wine-dark”, never blue."},
        "es": {"question": "Si una lengua tiene solo tres palabras para colores, ¿cuáles son casi siempre?",
               "options": ["Negro, blanco y rojo",
                           "Azul, verde y amarillo",
                           "Rojo, verde y azul",
                           "Negro, blanco y azul"],
               "fact": "Los vocabularios de color crecen en un orden casi "
                       "universal: oscuro, claro y luego rojo; el azul llega "
                       "tarde. Homero llama al mar “vinoso”, nunca "
                       "azul."},
        "fr": {"question": "Si une langue n'a que trois mots de couleur, lesquels sont-ce presque toujours ?",
               "options": ["Noir, blanc et rouge",
                           "Bleu, vert et jaune",
                           "Rouge, vert et bleu",
                           "Noir, blanc et bleu"],
               "fact": "Les vocabulaires des couleurs grandissent dans un "
                       "ordre quasi universel : sombre, clair, puis rouge — le "
                       "bleu vient tard. Homère dit la mer « couleur de "
                       "vin », jamais bleue."},
        "pt": {"question": "Se uma língua tem só três palavras para cores, quais são quase sempre?",
               "options": ["Preto, branco e vermelho",
                           "Azul, verde e amarelo",
                           "Vermelho, verde e azul",
                           "Preto, branco e azul"],
               "fact": "Os vocabulários de cor crescem numa ordem quase "
                       "universal: escuro, claro e depois vermelho — o azul "
                       "chega tarde. Homero chama ao mar “cor de vinho”, "
                       "nunca azul."},
        "ru": {"question": "Если в языке всего три слова для цветов, какие это почти всегда цвета?",
               "options": ["Чёрный, белый и красный",
                           "Синий, зелёный и жёлтый",
                           "Красный, зелёный и синий",
                           "Чёрный, белый и синий"],
               "fact": "Названия цветов появляются в языках почти в одном и "
                       "том же порядке: тёмный, светлый, затем красный — синий "
                       "приходит поздно. У Гомера море «винноцветное», "
                       "но не синее."},
        "ar": {"question": "إذا لم يكن في لغة إلا ثلاث كلمات للألوان، فما هي في الغالب؟",
               "options": ["الأسود والأبيض والأحمر",
                           "الأزرق والأخضر والأصفر",
                           "الأحمر والأخضر والأزرق",
                           "الأسود والأبيض والأزرق"],
               "fact": "تنمو مفردات الألوان بترتيب يكاد يكون واحدًا في كل "
                       "اللغات: الداكن ثم الفاتح ثم الأحمر — ويتأخر الأزرق. "
                       "هوميروس يصف البحر بأنه “بلون الخمر” ولا يقول "
                       "أزرق قط."},
    },
    {
        "answer": 1,
        "en": {"question": "Why do words like “mama” and “papa” sound similar in unrelated languages?",
               "options": ["They share one ancient ancestor",
                           "They come from babies' first babbling sounds",
                           "They were spread by Latin",
                           "It is pure coincidence"],
               "fact": "M, p, b and ah are the first sounds infants can make, "
                       "and parents everywhere hear their names in them. "
                       "Georgian flips it: mama is “dad” and deda is "
                       "“mum”."},
        "es": {"question": "¿Por qué palabras como “mamá” y “papá” suenan parecido en lenguas sin parentesco?",
               "options": ["Comparten un único ancestro antiguo",
                           "Vienen de los primeros balbuceos de los bebés",
                           "Las difundió el latín",
                           "Es pura coincidencia"],
               "fact": "M, p, b y a son los primeros sonidos que un bebé puede "
                       "producir, y los padres de todo el mundo oyen en ellos "
                       "sus nombres. El georgiano lo invierte: mama es "
                       "“papá” y deda, “mamá”."},
        "fr": {"question": "Pourquoi des mots comme « maman » et « papa » se ressemblent-ils dans des langues sans lien de parenté ?",
               "options": ["Ils partagent un unique ancêtre très ancien",
                           "Ils viennent des premiers babillages des bébés",
                           "Le latin les a répandus",
                           "C'est une pure coïncidence"],
               "fact": "M, p, b et a sont les premiers sons qu'un nourrisson "
                       "sait produire, et les parents du monde entier y "
                       "entendent leurs noms. Le géorgien inverse tout : mama "
                       "y veut dire « papa », et deda « maman »."},
        "pt": {"question": "Por que palavras como “mamã” e “papá” soam parecido em línguas sem parentesco?",
               "options": ["Partilham um único antepassado antigo",
                           "Vêm dos primeiros balbucios dos bebés",
                           "Foram espalhadas pelo latim",
                           "É pura coincidência"],
               "fact": "M, p, b e á são os primeiros sons que um bebé consegue "
                       "produzir, e os pais de todo o mundo ouvem neles os "
                       "seus nomes. O georgiano inverte: mama é “pai” e "
                       "deda é “mãe”."},
        "ru": {"question": "Почему слова вроде «мама» и «папа» похожи в неродственных языках?",
               "options": ["У них один древний общий предок",
                           "Они происходят из первого лепета младенцев",
                           "Их разнесла латынь",
                           "Это чистое совпадение"],
               "fact": "М, п, б и а — первые звуки, которые умеет произносить "
                       "младенец, и родители всего мира слышат в них свои "
                       "имена. Грузинский всё переворачивает: mama там — "
                       "«папа», а deda — «мама»."},
        "ar": {"question": "لماذا تتشابه كلمات مثل “ماما” و“بابا” في لغات لا قرابة بينها؟",
               "options": ["لأن لها سلفًا واحدًا قديمًا",
                           "لأنها من أولى مناغاة الرضّع",
                           "لأن اللاتينية نشرتها",
                           "إنها محض مصادفة"],
               "fact": "الميم والباء والألف أول ما يستطيع الرضيع نطقه، "
                       "والآباء في كل مكان يسمعون فيها أسماءهم. وتقلبها "
                       "الجورجية رأسًا على عقب: mama تعني الأب وdeda تعني "
                       "الأم."},
    },
    {
        "answer": 1,
        "en": {"question": "Portuguese “saudade” is famous as…",
               "options": ["a folk dance",
                           "a word for missing someone or something, hard to translate in one word",
                           "a kind of wine",
                           "a formal greeting"],
               "fact": "Every language has one-word gaps others envy: Danish "
                       "hygge (cosy togetherness), German Fernweh (an ache "
                       "for far-away places), Arabic ya'aburnee (“may you "
                       "outlive me”)."},
        "es": {"question": "La palabra portuguesa “saudade” es famosa por ser…",
               "options": ["una danza popular",
                           "una palabra para la añoranza de alguien o algo, difícil de traducir en una sola palabra",
                           "un tipo de vino",
                           "un saludo formal"],
               "fact": "Toda lengua tiene huecos de una sola palabra que otras "
                       "envidian: el danés hygge (calidez compartida), el "
                       "alemán Fernweh (anhelo de lugares lejanos), el árabe "
                       "ya'aburnee (“que me sobrevivas”)."},
        "fr": {"question": "Le mot portugais « saudade » est célèbre comme…",
               "options": ["une danse populaire",
                           "un mot disant le manque d'un être ou d'un lieu, difficile à traduire en un seul mot",
                           "un type de vin",
                           "une salutation formelle"],
               "fact": "Chaque langue a ses mots-trous que les autres lui "
                       "envient : le danois hygge (chaleur partagée), "
                       "l'allemand Fernweh (le mal du lointain), l'arabe "
                       "ya'aburnee (« puisses-tu me survivre »)."},
        "pt": {"question": "A palavra portuguesa “saudade” é famosa como…",
               "options": ["uma dança popular",
                           "uma palavra para a falta que alguém ou algo nos faz, difícil de traduzir numa só palavra",
                           "um tipo de vinho",
                           "uma saudação formal"],
               "fact": "Toda língua tem lacunas de uma palavra só que as "
                       "outras invejam: o dinamarquês hygge (aconchego "
                       "partilhado), o alemão Fernweh (saudade do longe), o "
                       "árabe ya'aburnee (“que me sobrevivas”)."},
        "ru": {"question": "Португальское слово «saudade» знаменито тем, что…",
               "options": ["это народный танец",
                           "это слово о тоске по кому-то или чему-то, которое трудно перевести одним словом",
                           "это сорт вина",
                           "это официальное приветствие"],
               "fact": "В каждом языке есть слова-лакуны, которым завидуют "
                       "другие: датское hygge (уютная близость), немецкое "
                       "Fernweh (тоска по дальним краям), арабское ya'aburnee "
                       "(«переживи меня»)."},
        "ar": {"question": "كلمة “ساوداده” البرتغالية مشهورة بوصفها…",
               "options": ["رقصة شعبية",
                           "كلمة عن الحنين إلى شخص أو شيء، يصعب نقلها بكلمة واحدة",
                           "نوعًا من النبيذ",
                           "تحية رسمية"],
               "fact": "في كل لغة كلمات لا تُترجم بكلمة واحدة وتحسدها عليها "
                       "اللغات الأخرى: الدنماركية hygge (دفء الصحبة)، "
                       "والألمانية Fernweh (الحنين إلى الأماكن البعيدة)، "
                       "والعربية “يعبرني”."},
    },
    {
        "answer": 1,
        "en": {"question": "In Indonesian, how do you usually make a plural?",
               "options": ["Add an -s",
                           "Say the word twice: orang “person”, orang-orang “people”",
                           "Change the vowel",
                           "Add a prefix"],
               "fact": "Doubling — reduplication — is everywhere in the "
                       "world's languages, marking plurals, intensity or "
                       "repetition. English uses it too: “is it a DATE-date "
                       "or just lunch?”"},
        "es": {"question": "En indonesio, ¿cómo se forma normalmente el plural?",
               "options": ["Añadiendo una -s",
                           "Repitiendo la palabra: orang “persona”, orang-orang “gente”",
                           "Cambiando la vocal",
                           "Añadiendo un prefijo"],
               "fact": "La reduplicación aparece en lenguas de todo el mundo "
                       "para marcar plural, intensidad o repetición. El "
                       "español coloquial también la usa: “era un café "
                       "café”."},
        "fr": {"question": "En indonésien, comment forme-t-on d'ordinaire le pluriel ?",
               "options": ["En ajoutant un -s",
                           "En répétant le mot : orang « personne », orang-orang « les gens »",
                           "En changeant la voyelle",
                           "En ajoutant un préfixe"],
               "fact": "Le redoublement existe dans les langues du monde "
                       "entier pour dire le pluriel, l'intensité ou la "
                       "répétition. Le français familier s'en sert aussi : "
                       "« c'est du café-café »."},
        "pt": {"question": "Em indonésio, como se faz normalmente o plural?",
               "options": ["Acrescenta-se um -s",
                           "Repete-se a palavra: orang “pessoa”, orang-orang “pessoas”",
                           "Muda-se a vogal",
                           "Acrescenta-se um prefixo"],
               "fact": "A reduplicação aparece em línguas do mundo inteiro "
                       "para marcar plural, intensidade ou repetição. O "
                       "português coloquial também a usa: “é um café "
                       "café”."},
        "ru": {"question": "Как в индонезийском обычно образуется множественное число?",
               "options": ["Добавлением -s",
                           "Повторением слова: orang — «человек», orang-orang — «люди»",
                           "Сменой гласной",
                           "Добавлением приставки"],
               "fact": "Редупликация встречается в языках всего мира и "
                       "означает множественность, усиление или повтор. Есть "
                       "она и в русском: «чуть-чуть», «еле-еле»."},
        "ar": {"question": "كيف يُصاغ الجمع عادةً في الإندونيسية؟",
               "options": ["بإضافة -s",
                           "بتكرار الكلمة: orang “شخص”، وorang-orang “أشخاص”",
                           "بتغيير الحركة",
                           "بإضافة سابقة"],
               "fact": "التكرار موجود في لغات العالم كلها للدلالة على الجمع "
                       "أو التوكيد أو المعاودة. وفي العربية شيء قريب منه: "
                       "“شيئًا فشيئًا” و“كثيرًا كثيرًا”."},
    },
    {
        "answer": 2,
        "en": {"question": "Roughly how many grammatical cases does Hungarian have?",
               "options": ["Two", "Around six", "Around eighteen", "None"],
               "fact": "Where English says “in the house”, Hungarian says "
                       "házban — one word. Finnish plays the same game with "
                       "about fifteen cases; Russian gets by with six."},
        "es": {"question": "¿Aproximadamente cuántos casos gramaticales tiene el húngaro?",
               "options": ["Dos", "Unos seis", "Unos dieciocho", "Ninguno"],
               "fact": "Donde el español dice “en la casa”, el húngaro "
                       "dice házban: una sola palabra. El finés juega igual "
                       "con unos quince casos; al ruso le bastan seis."},
        "fr": {"question": "Combien de cas grammaticaux le hongrois possède-t-il, environ ?",
               "options": ["Deux", "Environ six", "Environ dix-huit", "Aucun"],
               "fact": "Là où le français dit « dans la maison », le "
                       "hongrois dit házban — un seul mot. Le finnois joue au "
                       "même jeu avec une quinzaine de cas ; le russe s'en "
                       "tire avec six."},
        "pt": {"question": "Aproximadamente quantos casos gramaticais tem o húngaro?",
               "options": ["Dois", "Uns seis", "Uns dezoito", "Nenhum"],
               "fact": "Onde o português diz “na casa”, o húngaro diz "
                       "házban — uma palavra só. O finlandês joga o mesmo jogo "
                       "com uns quinze casos; ao russo bastam seis."},
        "ru": {"question": "Сколько примерно грамматических падежей в венгерском?",
               "options": ["Два", "Около шести", "Около восемнадцати", "Ни одного"],
               "fact": "Там, где по-русски говорят «в доме», венгр "
                       "скажет házban — одним словом. Финский играет в ту же "
                       "игру с примерно пятнадцатью падежами; русскому хватает "
                       "шести."},
        "ar": {"question": "كم عدد الحالات الإعرابية في المجرية تقريبًا؟",
               "options": ["اثنتان", "نحو ست", "نحو ثماني عشرة", "لا شيء"],
               "fact": "حيث تقول العربية “في البيت” بكلمتين، تقول المجرية "
                       "házban بكلمة واحدة. والفنلندية تلعب اللعبة نفسها بنحو "
                       "خمس عشرة حالة، بينما تكتفي الروسية بست."},
    },
    {
        "answer": 0,
        "en": {"question": "Some early Greek inscriptions are written “boustrophedon”. What does that mean?",
               "options": ["Alternating direction line by line, like an ox ploughing a field",
                           "Vertically, top to bottom",
                           "In a spiral toward the centre",
                           "In mirror writing throughout"],
               "fact": "The word means “as the ox turns”. One line runs "
                       "left to right, the next right to left — the reader's "
                       "eye never has to sweep back."},
        "es": {"question": "Algunas inscripciones griegas antiguas están escritas en “bustrofedon”. ¿Qué significa?",
               "options": ["Alternando la dirección línea a línea, como ara un buey",
                           "En vertical, de arriba abajo",
                           "En espiral hacia el centro",
                           "Todo en escritura especular"],
               "fact": "La palabra significa “como gira el buey”. Una "
                       "línea va de izquierda a derecha y la siguiente al "
                       "revés: el ojo del lector nunca tiene que volver atrás."},
        "fr": {"question": "Certaines inscriptions grecques archaïques sont écrites en « boustrophédon ». Qu'est-ce que cela signifie ?",
               "options": ["Le sens d'écriture alterne à chaque ligne, comme le bœuf qui laboure",
                           "À la verticale, de haut en bas",
                           "En spirale vers le centre",
                           "Entièrement en écriture miroir"],
               "fact": "Le mot signifie « comme tourne le bœuf ». Une "
                       "ligne va de gauche à droite, la suivante de droite à "
                       "gauche — l'œil du lecteur n'a jamais à revenir en "
                       "arrière."},
        "pt": {"question": "Algumas inscrições gregas antigas estão escritas em “bustrofédon”. O que significa isso?",
               "options": ["A direção alterna linha a linha, como um boi a lavrar",
                           "Na vertical, de cima para baixo",
                           "Em espiral até ao centro",
                           "Tudo em escrita espelhada"],
               "fact": "A palavra significa “como o boi vira”. Uma linha "
                       "corre da esquerda para a direita e a seguinte ao "
                       "contrário — o olho do leitor nunca precisa de voltar "
                       "atrás."},
        "ru": {"question": "Некоторые ранние греческие надписи написаны «бустрофедоном». Что это значит?",
               "options": ["Направление письма меняется с каждой строкой, как борозда за волом",
                           "Вертикально, сверху вниз",
                           "По спирали к центру",
                           "Целиком зеркальным письмом"],
               "fact": "Слово значит «как поворачивает вол». Одна "
                       "строка идёт слева направо, следующая — справа налево: "
                       "глазу читателя не приходится возвращаться к краю."},
        "ar": {"question": "بعض النقوش اليونانية المبكرة مكتوبة بأسلوب “بوسطروفيدون”. فما معناه؟",
               "options": ["يتناوب اتجاه الكتابة سطرًا بعد سطر، كما يحرث الثور الحقل",
                           "عموديًا من أعلى إلى أسفل",
                           "بشكل لولبي نحو المركز",
                           "بكتابة معكوسة كليًا"],
               "fact": "الكلمة تعني “كما يدور الثور”. سطر يمضي من اليسار "
                       "إلى اليمين والتالي بالعكس — فلا تحتاج عين القارئ إلى "
                       "الرجوع إلى أول السطر."},
    },
    {
        "answer": 0,
        "en": {"question": "Which pair of English words both come from Arabic?",
               "options": ["Algebra and coffee", "Piano and opera",
                           "Tea and typhoon", "Sauna and ski"],
               "fact": "Al-jabr names a 9th-century Baghdad mathematics book; "
                       "qahwa became kahve, caffè, coffee. Alcohol, cotton, "
                       "sugar and zero made the same journey."},
        "es": {"question": "¿Qué par de palabras vienen ambas del árabe?",
               "options": ["Álgebra y café", "Piano y ópera",
                           "Té y tifón", "Sauna y esquí"],
               "fact": "Al-jabr da nombre a un libro de matemáticas del "
                       "Bagdad del siglo IX; qahwa se volvió kahve, caffè, "
                       "café. Alcohol, algodón, azúcar y cero hicieron el "
                       "mismo viaje."},
        "fr": {"question": "Quelle paire de mots vient tout entière de l'arabe ?",
               "options": ["Algèbre et café", "Piano et opéra",
                           "Thé et typhon", "Sauna et ski"],
               "fact": "Al-jabr est le titre d'un traité de mathématiques du "
                       "Bagdad du IXe siècle ; qahwa est devenu kahve, caffè, "
                       "café. Alcool, coton, sucre et zéro ont fait le même "
                       "voyage."},
        "pt": {"question": "Que par de palavras vem, ambas, do árabe?",
               "options": ["Álgebra e café", "Piano e ópera",
                           "Chá e tufão", "Sauna e esqui"],
               "fact": "Al-jabr dá nome a um livro de matemática da Bagdade "
                       "do século IX; qahwa virou kahve, caffè, café. Álcool, "
                       "algodão, açúcar e zero fizeram a mesma viagem."},
        "ru": {"question": "Какая пара слов целиком пришла из арабского?",
               "options": ["Алгебра и кофе", "Пианино и опера",
                           "Чай и тайфун", "Сауна и лыжи"],
               "fact": "Аль-джабр — из названия багдадского учебника "
                       "математики IX века; qahwa стало kahve, caffè, кофе. "
                       "Тот же путь прошли алкоголь, хлопок (cotton), сахар и "
                       "цифра ноль."},
        "ar": {"question": "أي زوج من الكلمات الإنجليزية جاء كلاهما من العربية؟",
               "options": ["Algebra وcoffee", "Piano وopera",
                           "Tea وtyphoon", "Sauna وski"],
               "fact": "“الجبر” من عنوان كتاب رياضيات بغدادي من القرن "
                       "التاسع؛ و“قهوة” صارت kahve ثم caffè ثم coffee. "
                       "وسلكت “الكحول” و“القطن” و“السكر” "
                       "و“صفر” الطريق نفسه."},
    },
    {
        "answer": 1,
        "en": {"question": "Spanish “embarazada” looks like “embarrassed”, but means…",
               "options": ["embarrassed", "pregnant", "busy", "wealthy"],
               "fact": "Translators call these false friends. German “Gift” "
                       "is poison, Italian “camera” is a room, and Russian "
                       "“магазин” (magazin) is a shop, not a magazine."},
        "es": {"question": "La palabra inglesa “embarrassed” se parece a “embarazada”, pero significa…",
               "options": ["embarazada", "avergonzado", "ocupado", "rico"],
               "fact": "Los traductores los llaman falsos amigos. El alemán "
                       "“Gift” es veneno, el italiano “camera” es "
                       "una habitación y el ruso “магазин” es una "
                       "tienda, no una revista."},
        "fr": {"question": "L'espagnol « embarazada » ressemble à « embarrassée », mais signifie…",
               "options": ["embarrassée", "enceinte", "occupée", "riche"],
               "fact": "Les traducteurs appellent cela des faux amis. "
                       "L'allemand « Gift » est un poison, l'italien "
                       "« camera » une chambre, et le russe "
                       "« магазин » un magasin… c'est-à-dire une "
                       "boutique, pas une revue."},
        "pt": {"question": "O espanhol “embarazada” parece “embaraçada”, mas significa…",
               "options": ["embaraçada", "grávida", "ocupada", "rica"],
               "fact": "Os tradutores chamam-lhes falsos amigos. O alemão "
                       "“Gift” é veneno, o italiano “camera” é um "
                       "quarto e o russo “магазин” é uma loja, não uma "
                       "revista."},
        "ru": {"question": "Испанское «embarazada» похоже на «embarrassed» («смущённая»), но значит…",
               "options": ["смущённая", "беременная", "занятая", "богатая"],
               "fact": "Переводчики зовут такие пары ложными друзьями. "
                       "Немецкое «Gift» — яд, итальянское "
                       "«camera» — комната, а английское "
                       "«magazine» — журнал, вовсе не магазин."},
        "ar": {"question": "الكلمة الإسبانية “embarazada” تشبه الإنجليزية “embarrassed” (محرَج)، لكنها تعني…",
               "options": ["محرَجة", "حامل", "مشغولة", "ثرية"],
               "fact": "يسمي المترجمون هذه الأزواج “الأصدقاء الكاذبين”. "
                       "فالألمانية “Gift” تعني سمًّا، والإيطالية "
                       "“camera” غرفة، والروسية “магазин” متجرًا لا "
                       "مجلة."},
    },
    {
        "answer": 1,
        "en": {"question": "The most common vowel sound in English is…",
               "options": ["the “ee” in “see”",
                           "the schwa — the weak “uh” in “about”",
                           "the “a” in “cat”",
                           "the “o” in “go”"],
               "fact": "Unstressed English vowels collapse into the schwa, "
                       "which is one big reason spelling and sound drift so "
                       "far apart: the a, e, o in “about”, “taken”, "
                       "“lemon” are all the same sound."},
        "es": {"question": "El sonido vocálico más frecuente del inglés es…",
               "options": ["la “ee” de “see”",
                           "la schwa: la “uh” débil de “about”",
                           "la “a” de “cat”",
                           "la “o” de “go”"],
               "fact": "Las vocales átonas del inglés se reducen a la schwa, "
                       "y por eso ortografía y sonido se separan tanto: la a, "
                       "la e y la o de “about”, “taken” y "
                       "“lemon” suenan igual."},
        "fr": {"question": "Le son de voyelle le plus fréquent de l'anglais est…",
               "options": ["le « ee » de « see »",
                           "le schwa — le « euh » faible de « about »",
                           "le « a » de « cat »",
                           "le « o » de « go »"],
               "fact": "Les voyelles atones de l'anglais s'affaissent en "
                       "schwa — grande raison pour laquelle l'orthographe et "
                       "le son divergent tant : le a, le e et le o de "
                       "« about », « taken », « lemon » se "
                       "prononcent pareil."},
        "pt": {"question": "O som de vogal mais comum do inglês é…",
               "options": ["o “ee” de “see”",
                           "o schwa — o “ã” fraco de “about”",
                           "o “a” de “cat”",
                           "o “o” de “go”"],
               "fact": "As vogais átonas do inglês reduzem-se ao schwa, e é "
                       "em grande parte por isso que grafia e som se afastam "
                       "tanto: o a, o e e o o de “about”, “taken” e "
                       "“lemon” soam igual."},
        "ru": {"question": "Самый частый гласный звук английского языка — это…",
               "options": ["«и» в «see»",
                           "шва — слабое «э» в «about»",
                           "«э» в «cat»",
                           "«оу» в «go»"],
               "fact": "Безударные гласные английского сводятся к шва — "
                       "потому написание и звучание так расходятся: a, e и o "
                       "в «about», «taken», «lemon» звучат "
                       "одинаково. Похожая редукция есть и в русском: "
                       "«молоко» звучит как «мълако»."},
        "ar": {"question": "أكثر أصوات العلة شيوعًا في الإنجليزية هو…",
               "options": ["“ee” في “see”",
                           "الشوا — الصوت الضعيف في أول “about”",
                           "“a” في “cat”",
                           "“o” في “go”"],
               "fact": "تتقلص أصوات العلة غير المنبورة في الإنجليزية إلى "
                       "الشوا، وهذا سبب رئيسي لابتعاد الكتابة عن النطق: فحروف "
                       "a وe وo في “about” و“taken” و“lemon” "
                       "تُنطق كلها صوتًا واحدًا."},
    },
    {
        "answer": 0,
        "en": {"question": "According to a famous quip, what separates a “language” from a “dialect”?",
               "options": ["An army and a navy — politics, not linguistics",
                           "Grammar complexity",
                           "Having a writing system",
                           "Vocabulary size"],
               "fact": "Swedes and Norwegians chat across their “language” "
                       "border; many Chinese “dialects” cannot understand "
                       "each other at all. The border is drawn by states, not "
                       "by grammar."},
        "es": {"question": "Según una frase célebre, ¿qué separa una “lengua” de un “dialecto”?",
               "options": ["Un ejército y una armada: política, no lingüística",
                           "La complejidad de la gramática",
                           "Tener un sistema de escritura",
                           "El tamaño del vocabulario"],
               "fact": "Suecos y noruegos conversan a través de su frontera "
                       "“lingüística”; muchos “dialectos” chinos "
                       "no se entienden entre sí en absoluto. La frontera la "
                       "trazan los Estados, no la gramática."},
        "fr": {"question": "Selon un mot célèbre, qu'est-ce qui sépare une « langue » d'un « dialecte » ?",
               "options": ["Une armée et une marine — la politique, pas la linguistique",
                           "La complexité de la grammaire",
                           "Le fait d'avoir une écriture",
                           "La taille du vocabulaire"],
               "fact": "Suédois et Norvégiens bavardent par-dessus leur "
                       "frontière « linguistique » ; bien des "
                       "« dialectes » chinois ne se comprennent pas du "
                       "tout entre eux. La frontière est tracée par les États, "
                       "pas par la grammaire."},
        "pt": {"question": "Segundo um dito famoso, o que separa uma “língua” de um “dialeto”?",
               "options": ["Um exército e uma marinha — política, não linguística",
                           "A complexidade da gramática",
                           "Ter um sistema de escrita",
                           "O tamanho do vocabulário"],
               "fact": "Suecos e noruegueses conversam através da sua "
                       "fronteira “linguística”; muitos “dialetos” "
                       "chineses não se entendem uns aos outros. A fronteira é "
                       "traçada pelos Estados, não pela gramática."},
        "ru": {"question": "Согласно известной шутке, чем «язык» отличается от «диалекта»?",
               "options": ["Армией и флотом — то есть политикой, а не лингвистикой",
                           "Сложностью грамматики",
                           "Наличием письменности",
                           "Размером словаря"],
               "fact": "Шведы и норвежцы спокойно болтают через свою "
                       "«языковую» границу, а многие китайские "
                       "«диалекты» вовсе не понимают друг друга. "
                       "Границу проводят государства, а не грамматика."},
        "ar": {"question": "بحسب قول مأثور، ما الذي يفصل “اللغة” عن “اللهجة”؟",
               "options": ["جيش وأسطول — أي السياسة لا علم اللغة",
                           "تعقيد القواعد",
                           "امتلاك نظام كتابة",
                           "حجم المفردات"],
               "fact": "السويديون والنرويجيون يتحادثون عبر حدود "
                       "“لغتيهما”، بينما كثير من “اللهجات” الصينية "
                       "لا يفهم بعضها بعضًا إطلاقًا. الحدود ترسمها الدول لا "
                       "القواعد."},
    },
    {
        "answer": 0,
        "en": {"question": "About how many distinct sounds (phonemes) does Hawaiian use?",
               "options": ["About 13", "About 44", "About 80", "More than 100"],
               "fact": "Eight consonants and five vowels — among the world's "
                       "smallest inventories, which is why every Hawaiian "
                       "syllable ends in a vowel. English uses about 44; !Xóõ "
                       "in Botswana over 100. Māori runs small too."},
        "es": {"question": "¿Aproximadamente cuántos sonidos distintos (fonemas) usa el hawaiano?",
               "options": ["Unos 13", "Unos 44", "Unos 80", "Más de 100"],
               "fact": "Ocho consonantes y cinco vocales: uno de los "
                       "inventarios más pequeños del mundo, y por eso toda "
                       "sílaba hawaiana termina en vocal. El inglés usa unos "
                       "44; el !xóõ de Botsuana, más de 100. El maorí también "
                       "es pequeño."},
        "fr": {"question": "Environ combien de sons distincts (phonèmes) le hawaïen utilise-t-il ?",
               "options": ["Environ 13", "Environ 44", "Environ 80", "Plus de 100"],
               "fact": "Huit consonnes et cinq voyelles — l'un des plus "
                       "petits inventaires du monde, d'où le fait que toute "
                       "syllabe hawaïenne finit par une voyelle. L'anglais en "
                       "utilise environ 44 ; le !xóõ du Botswana, plus de 100. "
                       "Le māori aussi est tout petit."},
        "pt": {"question": "Aproximadamente quantos sons distintos (fonemas) usa o havaiano?",
               "options": ["Uns 13", "Uns 44", "Uns 80", "Mais de 100"],
               "fact": "Oito consoantes e cinco vogais — um dos inventários "
                       "mais pequenos do mundo, e por isso toda a sílaba "
                       "havaiana termina em vogal. O inglês usa uns 44; o "
                       "!xóõ do Botsuana, mais de 100. O māori também é "
                       "pequeno."},
        "ru": {"question": "Сколько примерно различных звуков (фонем) в гавайском языке?",
               "options": ["Около 13", "Около 44", "Около 80", "Больше 100"],
               "fact": "Восемь согласных и пять гласных — один из самых "
                       "маленьких наборов в мире; потому каждый гавайский "
                       "слог кончается гласным. В английском около 44 фонем, "
                       "в языке къхонг (!Xóõ) в Ботсване — больше ста. У маори "
                       "набор тоже крошечный."},
        "ar": {"question": "كم عدد الأصوات المميزة (الفونيمات) في اللغة الهاوايية تقريبًا؟",
               "options": ["نحو 13", "نحو 44", "نحو 80", "أكثر من 100"],
               "fact": "ثمانية صوامت وخمس صوائت — من أصغر المخزونات الصوتية "
                       "في العالم، ولهذا ينتهي كل مقطع هاوايي بصائت. "
                       "الإنجليزية فيها نحو 44، ولغة !Xóõ في بوتسوانا أكثر من "
                       "مئة. والماورية صغيرة المخزون أيضًا."},
    },
    {
        "answer": 0,
        "en": {"question": "Which language is written with one of the world's shortest alphabets — about 12 letters?",
               "options": ["Rotokas, in Papua New Guinea", "Russian", "Arabic", "Greek"],
               "fact": "Rotokas needs about a dozen letters; Khmer sits at "
                       "the other end with 74. Russian uses 33, Arabic 28, "
                       "Greek 24."},
        "es": {"question": "¿Qué lengua se escribe con uno de los alfabetos más cortos del mundo, de unas 12 letras?",
               "options": ["El rotokas, de Papúa Nueva Guinea", "El ruso", "El árabe", "El griego"],
               "fact": "Al rotokas le basta una docena de letras; el jemer "
                       "está en el otro extremo con 74. El ruso usa 33, el "
                       "árabe 28 y el griego 24."},
        "fr": {"question": "Quelle langue s'écrit avec l'un des alphabets les plus courts du monde — environ 12 lettres ?",
               "options": ["Le rotokas, en Papouasie-Nouvelle-Guinée", "Le russe", "L'arabe", "Le grec"],
               "fact": "Une douzaine de lettres suffisent au rotokas ; le "
                       "khmer occupe l'autre extrême avec 74. Le russe en "
                       "utilise 33, l'arabe 28, le grec 24."},
        "pt": {"question": "Que língua se escreve com um dos alfabetos mais curtos do mundo — cerca de 12 letras?",
               "options": ["O rotokas, da Papua-Nova Guiné", "O russo", "O árabe", "O grego"],
               "fact": "Ao rotokas basta-lhe uma dúzia de letras; o khmer "
                       "está no outro extremo, com 74. O russo usa 33, o "
                       "árabe 28, o grego 24."},
        "ru": {"question": "Какой язык записывается одним из самых коротких алфавитов в мире — около 12 букв?",
               "options": ["Ротокас в Папуа — Новой Гвинее", "Русский", "Арабский", "Греческий"],
               "fact": "Ротокасу хватает дюжины букв; на другом конце — "
                       "кхмерский с 74. В русском 33 буквы, в арабском 28, в "
                       "греческом 24."},
        "ar": {"question": "أي لغة تُكتب بواحدة من أقصر أبجديات العالم — نحو 12 حرفًا؟",
               "options": ["الروتوكاس في بابوا غينيا الجديدة", "الروسية", "العربية", "اليونانية"],
               "fact": "تكفي الروتوكاس اثنتا عشرة حرفًا تقريبًا؛ وفي الطرف "
                       "الآخر الخميرية بـ74 حرفًا. وللروسية 33 حرفًا، وللعربية "
                       "28، ولليونانية 24."},
    },
    {
        "answer": 0,
        "en": {"question": "Which European language is a “language isolate”, related to no other known language?",
               "options": ["Basque", "Hungarian", "Finnish", "Albanian"],
               "fact": "Hungarian and Finnish are distant cousins in the "
                       "Uralic family, and Albanian is Indo-European. Basque "
                       "stands alone — likely a survivor from before "
                       "Indo-European reached Europe."},
        "es": {"question": "¿Qué lengua europea es una “lengua aislada”, sin parentesco conocido con ninguna otra?",
               "options": ["El euskera", "El húngaro", "El finés", "El albanés"],
               "fact": "El húngaro y el finés son primos lejanos dentro de la "
                       "familia urálica, y el albanés es indoeuropeo. El "
                       "euskera está solo: probablemente sobrevive de antes "
                       "de que el indoeuropeo llegara a Europa."},
        "fr": {"question": "Quelle langue européenne est un « isolat », sans parenté connue avec aucune autre ?",
               "options": ["Le basque", "Le hongrois", "Le finnois", "L'albanais"],
               "fact": "Le hongrois et le finnois sont de lointains cousins "
                       "de la famille ouralienne, et l'albanais est "
                       "indo-européen. Le basque est seul — sans doute un "
                       "survivant d'avant l'arrivée de l'indo-européen en "
                       "Europe."},
        "pt": {"question": "Que língua europeia é uma “língua isolada”, sem parentesco conhecido com nenhuma outra?",
               "options": ["O basco", "O húngaro", "O finlandês", "O albanês"],
               "fact": "O húngaro e o finlandês são primos afastados na "
                       "família urálica, e o albanês é indo-europeu. O basco "
                       "está sozinho — provavelmente um sobrevivente de antes "
                       "de o indo-europeu chegar à Europa."},
        "ru": {"question": "Какой европейский язык — «язык-изолят», не родственный ни одному известному языку?",
               "options": ["Баскский", "Венгерский", "Финский", "Албанский"],
               "fact": "Венгерский и финский — дальние родственники в "
                       "уральской семье, албанский — индоевропейский. "
                       "Баскский стоит особняком: скорее всего, он уцелел с "
                       "времён до прихода индоевропейцев в Европу."},
        "ar": {"question": "أي لغة أوروبية “لغة معزولة” لا قرابة معروفة لها بأي لغة أخرى؟",
               "options": ["الباسكية", "المجرية", "الفنلندية", "الألبانية"],
               "fact": "المجرية والفنلندية قريبتان بعيدتان ضمن الأسرة "
                       "الأورالية، والألبانية هندوأوروبية. أما الباسكية فوحيدة "
                       "— ولعلها ناجية من عهد ما قبل وصول الهندوأوروبية إلى "
                       "أوروبا."},
    },
]


def seed_questions(locale: str) -> list[dict]:
    """The baseline corpus for *locale*, in the shape store_trivia expects.

    An unknown locale returns [] rather than falling back to English: a
    game in a language the learner didn't ask for is worse than no game,
    and the generator can still write one for them.
    """
    out: list[dict] = []
    for entry in _QUESTIONS:
        text = entry.get(locale)
        if not text:
            continue
        out.append({
            "question": text["question"],
            "options": list(text["options"]),
            "answer_index": entry["answer"],
            "fact": text["fact"],
        })
    return out


def offline_questions(locale: str, limit: int) -> list[dict]:
    """The corpus served straight from memory, with ids attached.

    The last line of defence: used when the bank cannot be read or written
    at all — most likely because the migration hasn't been applied yet.
    Nothing here touches the database, so the game still plays; the cost is
    that "already seen" can't be recorded, so questions may repeat.

    The ids are derived from the question text, so the same question is the
    same id in every process. That matters because the client posts them
    back to /trivia/seen, which filters to ids the bank actually holds.
    """
    items = seed_questions(locale)[: max(0, limit)]
    for it in items:
        it["id"] = str(uuid.uuid5(_NS, f"{locale}:{it['question']}"))
    return items
