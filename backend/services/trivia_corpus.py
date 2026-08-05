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
