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

import random
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
    # ---------------------------------------------------------- typology
    {
        "answer": 1,
        "en": {"question": "Spanish and Portuguese can say “fell asleep” as one word (dormí, dormi). Why doesn't the sentence need “I”?",
               "options": ["The pronoun is implied by context alone",
                           "The verb ending already says who did it — “pro-drop”",
                           "It is considered rude to say “I”",
                           "It is a poetic shortcut"],
               "fact": "Most Romance and Slavic languages drop subject "
                       "pronouns because the verb carries the person. English "
                       "and French can't: their verb endings collapsed, so "
                       "the pronoun does the work."},
        "es": {"question": "En español basta “dormí”, sin “yo”. ¿Por qué la frase no necesita el pronombre?",
               "options": ["El pronombre se sobreentiende solo por el contexto",
                           "La terminación del verbo ya dice quién lo hizo: es una lengua “pro-drop”",
                           "Decir “yo” se considera descortés",
                           "Es una licencia poética"],
               "fact": "La mayoría de las lenguas romances y eslavas omiten "
                       "el pronombre sujeto porque el verbo lleva la persona. "
                       "El inglés y el francés no pueden: sus terminaciones "
                       "se desgastaron y el pronombre hace el trabajo."},
        "fr": {"question": "L'espagnol dit « dormí » (« j'ai dormi ») sans « je ». Pourquoi la phrase n'a-t-elle pas besoin du pronom ?",
               "options": ["Le pronom se déduit du seul contexte",
                           "La terminaison du verbe dit déjà qui a agi — une langue « pro-drop »",
                           "Dire « je » serait impoli",
                           "C'est un raccourci poétique"],
               "fact": "La plupart des langues romanes et slaves omettent le "
                       "pronom sujet : le verbe porte la personne. L'anglais "
                       "et le français ne le peuvent pas — leurs terminaisons "
                       "se sont effacées, alors le pronom fait le travail."},
        "pt": {"question": "Em português basta “dormi”, sem “eu”. Porque é que a frase não precisa do pronome?",
               "options": ["O pronome deduz-se só pelo contexto",
                           "A terminação do verbo já diz quem foi: uma língua “pro-drop”",
                           "Dizer “eu” seria indelicado",
                           "É um atalho poético"],
               "fact": "A maioria das línguas românicas e eslavas omite o "
                       "pronome sujeito porque o verbo carrega a pessoa. O "
                       "inglês e o francês não podem: as terminações "
                       "desgastaram-se e o pronome faz o trabalho."},
        "ru": {"question": "По-испански можно сказать «dormí» («я поспал») без «я». Почему предложению не нужно местоимение?",
               "options": ["Местоимение понятно только из контекста",
                           "Окончание глагола уже говорит, кто это сделал, — «pro-drop»-язык",
                           "Говорить «я» невежливо",
                           "Это поэтическая вольность"],
               "fact": "Большинство романских и славянских языков опускают "
                       "местоимение-подлежащее: лицо несёт глагол. "
                       "Английский и французский так не могут — их окончания "
                       "стёрлись, и работу делает местоимение."},
        "ar": {"question": "بالإسبانية تكفي كلمة “dormí” (نمتُ) دون ضمير. لماذا لا تحتاج الجملة إلى “أنا”؟",
               "options": ["الضمير مفهوم من السياق وحده",
                           "نهاية الفعل تدل على الفاعل — لغة “تُسقِط الضمير”",
                           "قول “أنا” يُعد قلة تهذيب",
                           "إنه اختصار شعري"],
               "fact": "معظم اللغات الرومانسية والسلافية تُسقط ضمير الفاعل "
                       "لأن الفعل يحمل الدلالة — والعربية كذلك: “نمتُ” "
                       "تغني عن “أنا”. أما الإنجليزية والفرنسية فقد تآكلت "
                       "نهايات أفعالهما فصار الضمير ضروريًا."},
    },
    {
        "answer": 0,
        "en": {"question": "Tagalog and Māori have two words for “we”. What do they distinguish?",
               "options": ["Whether “we” includes the person you're talking to",
                           "Whether “we” is two people or more",
                           "Whether “we” is male or female",
                           "Whether “we” is formal or casual"],
               "fact": "“Shall we go?” is ambiguous in English — coming or "
                       "not? Tagalog tayo includes you, kami excludes you; "
                       "Māori, Quechua and Indonesian make the same cut."},
        "es": {"question": "El tagalo y el maorí tienen dos palabras para “nosotros”. ¿Qué distinguen?",
               "options": ["Si “nosotros” incluye a la persona con quien hablas",
                           "Si “nosotros” son dos personas o más",
                           "Si “nosotros” es masculino o femenino",
                           "Si “nosotros” es formal o informal"],
               "fact": "“¿Nos vamos?” es ambiguo: ¿vienes o no? En tagalo, "
                       "tayo te incluye y kami te excluye; el maorí, el "
                       "quechua y el indonesio hacen el mismo corte."},
        "fr": {"question": "Le tagalog et le māori ont deux mots pour « nous ». Que distinguent-ils ?",
               "options": ["Si « nous » inclut la personne à qui l'on parle",
                           "Si « nous » désigne deux personnes ou davantage",
                           "Si « nous » est masculin ou féminin",
                           "Si « nous » est formel ou familier"],
               "fact": "« On y va ? » est ambigu : viens-tu ou non ? En "
                       "tagalog, tayo t'inclut, kami t'exclut ; le māori, le "
                       "quechua et l'indonésien font la même distinction."},
        "pt": {"question": "O tagalo e o māori têm duas palavras para “nós”. O que distinguem?",
               "options": ["Se “nós” inclui a pessoa com quem falas",
                           "Se “nós” são duas pessoas ou mais",
                           "Se “nós” é masculino ou feminino",
                           "Se “nós” é formal ou informal"],
               "fact": "“Vamos?” é ambíguo: vens ou não? Em tagalo, tayo "
                       "inclui-te e kami exclui-te; o māori, o quéchua e o "
                       "indonésio fazem o mesmo corte."},
        "ru": {"question": "В тагальском и маори есть два слова для «мы». Что они различают?",
               "options": ["Входит ли в «мы» собеседник",
                           "Двое это или больше",
                           "Мужское это «мы» или женское",
                           "Формальное оно или разговорное"],
               "fact": "«Пойдём?» двусмысленно: ты идёшь или нет? В "
                       "тагальском tayo включает собеседника, kami — "
                       "исключает; так же устроены маори, кечуа и "
                       "индонезийский."},
        "ar": {"question": "في التاغالوغية والماورية كلمتان لـ“نحن”. ما الفرق بينهما؟",
               "options": ["هل تشمل “نحن” من تخاطبه أم لا",
                           "هل “نحن” اثنان أم أكثر",
                           "هل “نحن” للمذكر أم للمؤنث",
                           "هل “نحن” رسمية أم عامية"],
               "fact": "“هيا بنا؟” عبارة ملتبسة: هل أنت معنا أم لا؟ في "
                       "التاغالوغية tayo تشملك وkami تستثنيك؛ وتفعل الماورية "
                       "والكيتشوا والإندونيسية الشيء نفسه."},
    },
    {
        "answer": 2,
        "en": {"question": "To say “three books” in Japanese you must add a small extra word. What is it?",
               "options": ["An article, like “the”",
                           "A politeness marker",
                           "A classifier that matches the shape of the thing counted",
                           "A plural ending"],
               "fact": "Japanese counts flat things with -mai, long thin "
                       "things with -hon, small animals with -hiki. Chinese, "
                       "Korean, Thai and Vietnamese all count through "
                       "classifiers too — English does it only in traces: "
                       "“three head of cattle”."},
        "es": {"question": "Para decir “tres libros” en japonés hay que añadir una palabrita extra. ¿Cuál?",
               "options": ["Un artículo, como “los”",
                           "Una marca de cortesía",
                           "Un clasificador que concuerda con la forma del objeto contado",
                           "Una terminación de plural"],
               "fact": "El japonés cuenta cosas planas con -mai, cosas largas "
                       "y finas con -hon, animales pequeños con -hiki. El "
                       "chino, el coreano, el tailandés y el vietnamita "
                       "también cuentan con clasificadores; en español quedan "
                       "restos: “tres cabezas de ganado”."},
        "fr": {"question": "Pour dire « trois livres » en japonais, il faut ajouter un petit mot. Lequel ?",
               "options": ["Un article, comme « les »",
                           "Une marque de politesse",
                           "Un classificateur accordé à la forme de la chose comptée",
                           "Une terminaison de pluriel"],
               "fact": "Le japonais compte les choses plates avec -mai, les "
                       "choses longues et fines avec -hon, les petits animaux "
                       "avec -hiki. Chinois, coréen, thaï et vietnamien "
                       "comptent aussi par classificateurs — le français en "
                       "garde des traces : « trois têtes de bétail »."},
        "pt": {"question": "Para dizer “três livros” em japonês é preciso acrescentar uma palavrinha. Qual?",
               "options": ["Um artigo, como “os”",
                           "Uma marca de cortesia",
                           "Um classificador que combina com a forma da coisa contada",
                           "Uma terminação de plural"],
               "fact": "O japonês conta coisas planas com -mai, coisas "
                       "compridas e finas com -hon, animais pequenos com "
                       "-hiki. Chinês, coreano, tailandês e vietnamita também "
                       "contam por classificadores — o português guarda "
                       "vestígios: “três cabeças de gado”."},
        "ru": {"question": "Чтобы сказать по-японски «три книги», нужно добавить особое словечко. Какое?",
               "options": ["Артикль, вроде «the»",
                           "Показатель вежливости",
                           "Счётное слово, подходящее к форме предмета",
                           "Окончание множественного числа"],
               "fact": "Плоское японец считает с -mai, длинное и тонкое — с "
                       "-hon, мелких животных — с -hiki. Китайский, "
                       "корейский, тайский и вьетнамский тоже считают через "
                       "счётные слова; в русском есть след той же логики: "
                       "«три головы скота»."},
        "ar": {"question": "لقول “ثلاثة كتب” باليابانية لا بد من إضافة كلمة صغيرة. ما هي؟",
               "options": ["أداة تعريف مثل “الـ”",
                           "علامة تهذيب",
                           "كلمة عدٍّ تناسب شكل الشيء المعدود",
                           "لاحقة جمع"],
               "fact": "تَعُدُّ اليابانية الأشياء المسطحة بـ-mai والطويلة "
                       "الرفيعة بـ-hon وصغار الحيوانات بـ-hiki. وتَعُدُّ "
                       "الصينية والكورية والتايلاندية والفيتنامية بكلمات عدٍّ "
                       "أيضًا — وفي العربية أثر منها: “ثلاثة رؤوس من "
                       "الماشية”."},
    },
    {
        "answer": 1,
        "en": {"question": "How does Turkish turn a statement into a yes-no question?",
               "options": ["By flipping the word order, as English does",
                           "With a little question particle: geldi “came” → geldi mi? “did it come?”",
                           "Only by tone of voice",
                           "With a special question verb"],
               "fact": "Question particles are everywhere: Japanese ka, "
                       "Mandarin ma, Polish czy, Arabic hal. English is the "
                       "odd one out, reshuffling its verbs instead."},
        "es": {"question": "¿Cómo convierte el turco una afirmación en pregunta de sí o no?",
               "options": ["Invirtiendo el orden de las palabras, como el inglés",
                           "Con una partícula interrogativa: geldi “vino” → geldi mi? “¿vino?”",
                           "Solo con la entonación",
                           "Con un verbo interrogativo especial"],
               "fact": "Las partículas interrogativas están por todas partes: "
                       "ka en japonés, ma en chino, czy en polaco, hal en "
                       "árabe. El raro es el inglés, que reordena sus verbos."},
        "fr": {"question": "Comment le turc transforme-t-il une affirmation en question fermée ?",
               "options": ["En inversant l'ordre des mots, comme l'anglais",
                           "Avec une petite particule interrogative : geldi « il est venu » → geldi mi ? « est-il venu ? »",
                           "Seulement par l'intonation",
                           "Avec un verbe interrogatif spécial"],
               "fact": "Les particules interrogatives sont partout : ka en "
                       "japonais, ma en mandarin, czy en polonais, hal en "
                       "arabe. L'exception, c'est l'anglais, qui remanie ses "
                       "verbes."},
        "pt": {"question": "Como é que o turco transforma uma afirmação numa pergunta de sim ou não?",
               "options": ["Invertendo a ordem das palavras, como o inglês",
                           "Com uma partícula interrogativa: geldi “veio” → geldi mi? “veio?”",
                           "Só com a entoação",
                           "Com um verbo interrogativo especial"],
               "fact": "As partículas interrogativas estão por todo o lado: "
                       "ka em japonês, ma em mandarim, czy em polaco, hal em "
                       "árabe. O estranho é o inglês, que baralha os verbos."},
        "ru": {"question": "Как турецкий превращает утверждение в вопрос «да или нет»?",
               "options": ["Меняет порядок слов, как английский",
                           "Добавляет вопросительную частицу: geldi «пришёл» → geldi mi? «пришёл ли?»",
                           "Только интонацией",
                           "Особым вопросительным глаголом"],
               "fact": "Вопросительные частицы есть повсюду: японское ka, "
                       "китайское ma, польское czy, арабское hal — и русское "
                       "«ли». Странный здесь английский, который вместо "
                       "этого тасует глаголы."},
        "ar": {"question": "كيف تحوّل التركية الجملة الخبرية إلى سؤال بنعم أو لا؟",
               "options": ["بقلب ترتيب الكلمات كما تفعل الإنجليزية",
                           "بأداة استفهام صغيرة: geldi “جاء” ← geldi mi؟ “هل جاء؟”",
                           "بنبرة الصوت فقط",
                           "بفعل استفهامي خاص"],
               "fact": "أدوات الاستفهام منتشرة في اللغات: ka اليابانية وma "
                       "الصينية وczy البولندية و“هل” العربية. الشاذ هو "
                       "الإنجليزية التي تعيد ترتيب أفعالها بدلًا من ذلك."},
    },
    {
        "answer": 0,
        "en": {"question": "Latin and Russian can shuffle their word order freely. What makes that possible?",
               "options": ["Case endings mark who does what to whom, wherever the words stand",
                           "Listeners simply guess from context",
                           "Their sentences are shorter",
                           "Strict rules about intonation"],
               "fact": "Canem homo mordet and homo canem mordet both mean "
                       "“the man bites the dog” — the -em says who gets "
                       "bitten. The freed-up order then carries emphasis, "
                       "which is why Latin poetry can scatter a phrase "
                       "across a whole line."},
        "es": {"question": "El latín y el ruso pueden barajar el orden de las palabras con libertad. ¿Qué lo hace posible?",
               "options": ["Los casos marcan quién hace qué a quién, estén donde estén las palabras",
                           "El oyente simplemente lo adivina por el contexto",
                           "Sus frases son más cortas",
                           "Reglas estrictas de entonación"],
               "fact": "Canem homo mordet y homo canem mordet significan lo "
                       "mismo: “el hombre muerde al perro” — la -em dice "
                       "quién recibe el mordisco. El orden libre pasa a "
                       "marcar el énfasis, y por eso la poesía latina puede "
                       "esparcir una frase por todo un verso."},
        "fr": {"question": "Le latin et le russe peuvent mélanger librement l'ordre des mots. Qu'est-ce qui le permet ?",
               "options": ["Les cas marquent qui fait quoi à qui, où que soient les mots",
                           "L'auditeur devine simplement d'après le contexte",
                           "Leurs phrases sont plus courtes",
                           "Des règles strictes d'intonation"],
               "fact": "Canem homo mordet et homo canem mordet disent la "
                       "même chose : « l'homme mord le chien » — le -em "
                       "désigne le mordu. L'ordre libéré porte alors "
                       "l'emphase, et la poésie latine peut éparpiller un "
                       "groupe sur tout un vers."},
        "pt": {"question": "O latim e o russo podem baralhar a ordem das palavras à vontade. O que torna isso possível?",
               "options": ["Os casos marcam quem faz o quê a quem, estejam as palavras onde estiverem",
                           "O ouvinte simplesmente adivinha pelo contexto",
                           "As frases deles são mais curtas",
                           "Regras estritas de entoação"],
               "fact": "Canem homo mordet e homo canem mordet significam o "
                       "mesmo: “o homem morde o cão” — o -em diz quem é "
                       "mordido. A ordem livre passa a carregar a ênfase, e "
                       "por isso a poesia latina espalha uma frase por um "
                       "verso inteiro."},
        "ru": {"question": "Латынь и русский свободно переставляют слова в предложении. Что это позволяет?",
               "options": ["Падежные окончания показывают, кто что с кем делает, где бы слова ни стояли",
                           "Слушатель просто догадывается по контексту",
                           "Предложения в них короче",
                           "Строгие правила интонации"],
               "fact": "«Человек кусает собаку» и «собаку кусает "
                       "человек» — смысл тот же: винительный падеж говорит, "
                       "кого укусили. Освободившийся порядок слов начинает "
                       "передавать акцент — потому латинская поэзия может "
                       "рассыпать словосочетание по всей строке."},
        "ar": {"question": "تستطيع اللاتينية والروسية خلط ترتيب الكلمات بحرية. ما الذي يتيح ذلك؟",
               "options": ["علامات الإعراب تبيّن مَن فعل ماذا بمن أينما وقعت الكلمات",
                           "السامع يخمّن من السياق فحسب",
                           "جملهما أقصر",
                           "قواعد صارمة للتنغيم"],
               "fact": "في اللاتينية canem homo mordet وhomo canem mordet "
                       "بمعنى واحد: “الرجل يعضّ الكلب” — فالنهاية -em "
                       "تحدد المعضوض. والعربية تعرف هذا جيدًا: فالفتحة "
                       "والضمة تؤديان الدور نفسه."},
    },
    {
        "answer": 1,
        "en": {"question": "What is striking about Vietnamese words?",
               "options": ["They are extremely long",
                           "They never change form — no endings for tense, number or case at all",
                           "They are all borrowed from Chinese",
                           "They must start with a consonant"],
               "fact": "Vietnamese is a near-perfectly “isolating” "
                       "language: grammar is done by word order and little "
                       "helper words, not endings. Greenlandic sits at the "
                       "other pole, packing a whole sentence into one word."},
        "es": {"question": "¿Qué llama la atención de las palabras vietnamitas?",
               "options": ["Son larguísimas",
                           "Nunca cambian de forma: sin terminaciones de tiempo, número ni caso",
                           "Todas vienen del chino",
                           "Deben empezar por consonante"],
               "fact": "El vietnamita es una lengua casi perfectamente "
                       "“aislante”: la gramática se hace con el orden y "
                       "con palabritas auxiliares, no con terminaciones. El "
                       "groenlandés está en el polo opuesto: mete una frase "
                       "entera en una sola palabra."},
        "fr": {"question": "Qu'est-ce qui frappe dans les mots vietnamiens ?",
               "options": ["Ils sont extrêmement longs",
                           "Ils ne changent jamais de forme — aucune terminaison de temps, de nombre ou de cas",
                           "Ils sont tous empruntés au chinois",
                           "Ils doivent commencer par une consonne"],
               "fact": "Le vietnamien est une langue presque parfaitement "
                       "« isolante » : la grammaire passe par l'ordre des "
                       "mots et de petits mots-outils, pas par des "
                       "terminaisons. Le groenlandais occupe le pôle opposé "
                       "et loge une phrase entière dans un seul mot."},
        "pt": {"question": "O que é notável nas palavras vietnamitas?",
               "options": ["São compridíssimas",
                           "Nunca mudam de forma — sem terminações de tempo, número ou caso",
                           "Vêm todas do chinês",
                           "Têm de começar por consoante"],
               "fact": "O vietnamita é uma língua quase perfeitamente "
                       "“isolante”: a gramática faz-se com a ordem e com "
                       "palavrinhas auxiliares, não com terminações. O "
                       "gronelandês está no polo oposto: cabe uma frase "
                       "inteira numa só palavra."},
        "ru": {"question": "Чем примечательны вьетнамские слова?",
               "options": ["Они очень длинные",
                           "Они никогда не меняют форму — никаких окончаний времени, числа или падежа",
                           "Все они заимствованы из китайского",
                           "Они обязаны начинаться с согласного"],
               "fact": "Вьетнамский — почти идеально «изолирующий» язык: "
                       "грамматика делается порядком слов и служебными "
                       "словечками, а не окончаниями. Гренландский — "
                       "противоположный полюс: целое предложение в одном "
                       "слове."},
        "ar": {"question": "ما اللافت في كلمات اللغة الفيتنامية؟",
               "options": ["أنها طويلة جدًا",
                           "أنها لا تتغير أبدًا — لا لواحق للزمن ولا للعدد ولا للإعراب",
                           "أنها كلها مستعارة من الصينية",
                           "أنها تبدأ بحرف ساكن دائمًا"],
               "fact": "الفيتنامية لغة “عازلة” تكاد تكون مثالية: قواعدها "
                       "في ترتيب الكلمات وكليمات مساعدة لا في اللواحق. وعلى "
                       "الطرف الآخر الغرينلاندية التي تحشر جملة كاملة في "
                       "كلمة واحدة."},
    },
    {
        "answer": 2,
        "en": {"question": "Korean and Javanese are famous for building politeness into…",
               "options": ["their alphabets",
                           "handwriting styles",
                           "the grammar itself — different verb endings for different social settings",
                           "loudness of speech"],
               "fact": "A Korean verb ends differently to a friend, a "
                       "stranger, or a grandparent — choosing no level is "
                       "not an option. Javanese goes further, with largely "
                       "different vocabulary per level."},
        "es": {"question": "El coreano y el javanés son famosos por incorporar la cortesía en…",
               "options": ["sus alfabetos",
                           "los estilos de caligrafía",
                           "la propia gramática: terminaciones verbales distintas según la situación social",
                           "el volumen de la voz"],
               "fact": "Un verbo coreano termina distinto ante un amigo, un "
                       "desconocido o un abuelo — y no elegir nivel no es "
                       "una opción. El javanés va más lejos: cambia gran "
                       "parte del vocabulario según el nivel."},
        "fr": {"question": "Le coréen et le javanais sont célèbres pour intégrer la politesse dans…",
               "options": ["leurs alphabets",
                           "les styles d'écriture manuscrite",
                           "la grammaire elle-même — des terminaisons verbales différentes selon la situation sociale",
                           "le volume de la voix"],
               "fact": "Un verbe coréen ne se termine pas pareil devant un "
                       "ami, un inconnu ou un grand-parent — et ne pas "
                       "choisir de niveau n'est pas possible. Le javanais va "
                       "plus loin : le vocabulaire change en grande partie "
                       "selon le niveau."},
        "pt": {"question": "O coreano e o javanês são famosos por embutirem a cortesia…",
               "options": ["nos alfabetos",
                           "nos estilos de caligrafia",
                           "na própria gramática: terminações verbais diferentes conforme a situação social",
                           "no volume da voz"],
               "fact": "Um verbo coreano termina de forma diferente para um "
                       "amigo, um desconhecido ou um avô — e não escolher "
                       "nível não é opção. O javanês vai mais longe: muda "
                       "grande parte do vocabulário conforme o nível."},
        "ru": {"question": "Корейский и яванский знамениты тем, что вежливость встроена…",
               "options": ["в их алфавиты",
                           "в стили письма от руки",
                           "в саму грамматику — разные глагольные окончания для разных социальных ситуаций",
                           "в громкость речи"],
               "fact": "Корейский глагол кончается по-разному в разговоре с "
                       "другом, незнакомцем и дедушкой — не выбрать уровень "
                       "нельзя. Яванский идёт дальше: от уровня зависит и "
                       "заметная часть словаря."},
        "ar": {"question": "تشتهر الكورية والجاوية بأن التهذيب مدمج في…",
               "options": ["أبجديتيهما",
                           "أساليب الخط اليدوي",
                           "القواعد نفسها — نهايات أفعال مختلفة بحسب المقام الاجتماعي",
                           "علو الصوت"],
               "fact": "ينتهي الفعل الكوري نهاية مختلفة مع الصديق والغريب "
                       "والجد — وعدمُ اختيار مستوى ليس خيارًا. وتذهب الجاوية "
                       "أبعد: يتغير قسم كبير من المفردات نفسها بحسب "
                       "المستوى."},
    },
    # ---------------------------------------------------------- phonology
    {
        "answer": 0,
        "en": {"question": "In Yoruba, saying a syllable on a high, mid or low pitch can…",
               "options": ["change it into a completely different word",
                           "only add emphasis",
                           "signal a question",
                           "mark politeness"],
               "fact": "Yoruba has three level tones; ọkọ can be husband, "
                       "hoe, spear or vehicle depending on pitch. By many "
                       "counts more of the world's languages are tonal than "
                       "not — Mandarin, Thai, Hausa, Zulu, Punjabi."},
        "es": {"question": "En yoruba, pronunciar una sílaba con tono alto, medio o bajo puede…",
               "options": ["convertirla en una palabra completamente distinta",
                           "solo añadir énfasis",
                           "señalar una pregunta",
                           "marcar cortesía"],
               "fact": "El yoruba tiene tres tonos; ọkọ puede ser marido, "
                       "azada, lanza o vehículo según la altura. Según muchos "
                       "recuentos, más de la mitad de las lenguas del mundo "
                       "son tonales: chino, tailandés, hausa, zulú, panyabí."},
        "fr": {"question": "En yoruba, prononcer une syllabe sur un ton haut, moyen ou bas peut…",
               "options": ["en faire un mot complètement différent",
                           "seulement ajouter de l'emphase",
                           "signaler une question",
                           "marquer la politesse"],
               "fact": "Le yoruba a trois tons ; ọkọ peut signifier mari, "
                       "houe, lance ou véhicule selon la hauteur. Selon bien "
                       "des décomptes, plus de la moitié des langues du monde "
                       "sont tonales : mandarin, thaï, haoussa, zoulou, "
                       "pendjabi."},
        "pt": {"question": "Em iorubá, dizer uma sílaba em tom alto, médio ou baixo pode…",
               "options": ["transformá-la numa palavra completamente diferente",
                           "apenas acrescentar ênfase",
                           "sinalizar uma pergunta",
                           "marcar cortesia"],
               "fact": "O iorubá tem três tons; ọkọ pode ser marido, enxada, "
                       "lança ou veículo conforme a altura. Por muitas "
                       "contagens, mais de metade das línguas do mundo são "
                       "tonais: mandarim, tailandês, hauçá, zulu, panjabi."},
        "ru": {"question": "В йоруба произнести слог высоким, средним или низким тоном значит…",
               "options": ["получить совершенно другое слово",
                           "лишь добавить выразительности",
                           "обозначить вопрос",
                           "выразить вежливость"],
               "fact": "В йоруба три ровных тона; ọkọ — это муж, мотыга, "
                       "копьё или повозка в зависимости от высоты. По многим "
                       "подсчётам тональных языков в мире больше, чем "
                       "нетональных: китайский, тайский, хауса, зулу, "
                       "панджаби."},
        "ar": {"question": "في اليوروبا، نطق المقطع بنغمة عالية أو وسطى أو منخفضة قد…",
               "options": ["يحوّله إلى كلمة مختلفة تمامًا",
                           "يضيف توكيدًا فقط",
                           "يدل على سؤال",
                           "يعبّر عن التهذيب"],
               "fact": "في اليوروبا ثلاث نغمات؛ فكلمة ọkọ تعني الزوج أو "
                       "الفأس أو الرمح أو المركبة بحسب النغمة. وبحسب إحصاءات "
                       "كثيرة، اللغات النغمية في العالم أكثر من غيرها: "
                       "الصينية والتايلاندية والهوسا والزولو والبنجابية."},
    },
    {
        "answer": 1,
        "en": {"question": "Why is the Turkish plural sometimes -lar and sometimes -ler (evler “houses”, kızlar “girls”)?",
               "options": ["It is irregular and must be memorised",
                           "Vowel harmony: the suffix vowel matches the vowels of the word",
                           "One is formal, one casual",
                           "One is old-fashioned"],
               "fact": "Turkish suffixes come in matched sets and take the "
                       "colour of the word they attach to. Hungarian, "
                       "Finnish and Mongolian run on the same principle — "
                       "one reason those languages sound so internally "
                       "consistent."},
        "es": {"question": "¿Por qué el plural turco es a veces -lar y a veces -ler (evler “casas”, kızlar “chicas”)?",
               "options": ["Es irregular y hay que memorizarlo",
                           "Armonía vocálica: la vocal del sufijo se acomoda a las vocales de la palabra",
                           "Uno es formal y otro coloquial",
                           "Uno es anticuado"],
               "fact": "Los sufijos turcos vienen en juegos emparejados y "
                       "toman el color de la palabra a la que se pegan. El "
                       "húngaro, el finés y el mongol funcionan igual — por "
                       "eso suenan tan internamente consistentes."},
        "fr": {"question": "Pourquoi le pluriel turc est-il tantôt -lar, tantôt -ler (evler « maisons », kızlar « filles ») ?",
               "options": ["C'est irrégulier, il faut mémoriser",
                           "Harmonie vocalique : la voyelle du suffixe s'accorde aux voyelles du mot",
                           "L'un est formel, l'autre familier",
                           "L'un est vieilli"],
               "fact": "Les suffixes turcs vont par paires assorties et "
                       "prennent la couleur du mot qui les porte. Le "
                       "hongrois, le finnois et le mongol suivent le même "
                       "principe — d'où leur sonorité si cohérente."},
        "pt": {"question": "Porque é que o plural turco é umas vezes -lar e outras -ler (evler “casas”, kızlar “raparigas”)?",
               "options": ["É irregular e tem de se decorar",
                           "Harmonia vocálica: a vogal do sufixo combina com as vogais da palavra",
                           "Um é formal, o outro coloquial",
                           "Um é antiquado"],
               "fact": "Os sufixos turcos vêm em pares combinados e tomam a "
                       "cor da palavra a que se colam. O húngaro, o "
                       "finlandês e o mongol seguem o mesmo princípio — daí "
                       "soarem tão internamente consistentes."},
        "ru": {"question": "Почему турецкое множественное число — то -lar, то -ler (evler «дома», kızlar «девушки»)?",
               "options": ["Это исключения, их надо заучивать",
                           "Гармония гласных: гласный суффикса подстраивается под гласные слова",
                           "Одно формальное, другое разговорное",
                           "Одно устарело"],
               "fact": "Турецкие суффиксы ходят парными наборами и "
                       "принимают окраску слова, к которому крепятся. Так же "
                       "устроены венгерский, финский и монгольский — оттого "
                       "они и звучат так цельно."},
        "ar": {"question": "لماذا يكون الجمع التركي أحيانًا -lar وأحيانًا -ler (evler “بيوت”، kızlar “بنات”)؟",
               "options": ["إنه شاذ ويجب حفظه",
                           "انسجام الصوائت: صائت اللاحقة يوافق صوائت الكلمة",
                           "أحدهما رسمي والآخر عامي",
                           "أحدهما قديم مهجور"],
               "fact": "تأتي اللواحق التركية أطقمًا متناسبة وتأخذ لون الكلمة "
                       "التي تلتصق بها. وعلى المبدأ نفسه تقوم المجرية "
                       "والفنلندية والمنغولية — ولهذا تبدو أصواتها منسجمة "
                       "إلى هذا الحد."},
    },
    {
        "answer": 2,
        "en": {"question": "Japanese turned “ice cream” into aisukurīmu. Why the extra vowels?",
               "options": ["To make it cuter",
                           "Spelling rules require it",
                           "Japanese syllables can't end in most consonants, so borrowed clusters get vowels inserted",
                           "It copies the American pronunciation"],
               "fact": "Languages differ sharply in what a syllable may "
                       "look like: Hawaiian and Māori bar almost all final "
                       "consonants, while Georgian happily opens a word "
                       "with six — mts'vrtneli, “trainer”."},
        "es": {"question": "El japonés convirtió “ice cream” en aisukurīmu. ¿Por qué esas vocales de más?",
               "options": ["Para que suene más simpático",
                           "Lo exige la ortografía",
                           "Las sílabas japonesas no pueden acabar en casi ninguna consonante, así que se insertan vocales en los grupos prestados",
                           "Copia la pronunciación americana"],
               "fact": "Las lenguas difieren mucho en cómo puede ser una "
                       "sílaba: el hawaiano y el maorí vetan casi toda "
                       "consonante final, mientras el georgiano abre "
                       "tranquilamente una palabra con seis: mts'vrtneli, "
                       "“entrenador”."},
        "fr": {"question": "Le japonais a fait de « ice cream » aisukurīmu. Pourquoi ces voyelles en plus ?",
               "options": ["Pour faire plus mignon",
                           "L'orthographe l'exige",
                           "Les syllabes japonaises ne peuvent finir par presque aucune consonne : les groupes empruntés reçoivent des voyelles",
                           "Cela copie la prononciation américaine"],
               "fact": "Les langues diffèrent fort sur la forme d'une "
                       "syllabe : le hawaïen et le māori interdisent presque "
                       "toute consonne finale, quand le géorgien ouvre sans "
                       "peine un mot par six — mts'vrtneli, « entraîneur »."},
        "pt": {"question": "O japonês transformou “ice cream” em aisukurīmu. Porquê as vogais a mais?",
               "options": ["Para soar mais simpático",
                           "A ortografia obriga",
                           "As sílabas japonesas não podem acabar em quase nenhuma consoante, por isso os grupos emprestados recebem vogais",
                           "Copia a pronúncia americana"],
               "fact": "As línguas diferem muito no formato da sílaba: o "
                       "havaiano e o māori proíbem quase toda a consoante "
                       "final, enquanto o georgiano abre uma palavra com "
                       "seis: mts'vrtneli, “treinador”."},
        "ru": {"question": "Японский превратил «ice cream» в aisukurīmu. Откуда лишние гласные?",
               "options": ["Так милее звучит",
                           "Этого требует орфография",
                           "Японский слог почти не может кончаться согласным, и в заимствованные скопления вставляются гласные",
                           "Это копия американского произношения"],
               "fact": "Языки резко расходятся в том, каким может быть "
                       "слог: гавайский и маори запрещают почти любые "
                       "конечные согласные, а грузинский спокойно начинает "
                       "слово с шести — мцвртнели, «тренер»."},
        "ar": {"question": "حوّلت اليابانية “ice cream” إلى aisukurīmu. لماذا هذه الصوائت الزائدة؟",
               "options": ["ليبدو ألطف",
                           "الإملاء يفرض ذلك",
                           "المقطع الياباني لا ينتهي بمعظم الصوامت، فتُحشر صوائت في التجمعات المستعارة",
                           "تقليدًا للنطق الأمريكي"],
               "fact": "تختلف اللغات كثيرًا في شكل المقطع: الهاوايية "
                       "والماورية تمنعان معظم الصوامت في آخر المقطع، بينما "
                       "تفتتح الجورجية كلمة بستة صوامت — mts'vrtneli أي "
                       "“مدرِّب”."},
    },
    {
        "answer": 1,
        "en": {"question": "Where does word stress fall in French?",
               "options": ["It moves word by word and must be learned",
                           "Always at the end of the word or phrase",
                           "Always on the first syllable",
                           "French has no stress at all"],
               "fact": "French stress is fixed phrase-finally; Polish fixes "
                       "it on the second-to-last syllable, Czech on the "
                       "first. Russian and Spanish let it move — which is "
                       "why their stress can distinguish words, like Spanish "
                       "hablo “I speak” vs habló “he spoke”."},
        "es": {"question": "¿Dónde cae el acento en francés?",
               "options": ["Cambia de palabra en palabra y hay que aprenderlo",
                           "Siempre al final de la palabra o de la frase",
                           "Siempre en la primera sílaba",
                           "El francés no tiene acento"],
               "fact": "El acento francés es fijo al final; el polaco lo "
                       "fija en la penúltima y el checo en la primera. El "
                       "ruso y el español lo dejan moverse — por eso puede "
                       "distinguir palabras: hablo frente a habló."},
        "fr": {"question": "Où tombe l'accent tonique en français ?",
               "options": ["Il change selon les mots et doit s'apprendre",
                           "Toujours en fin de mot ou de groupe",
                           "Toujours sur la première syllabe",
                           "Le français n'a pas d'accent tonique"],
               "fact": "L'accent français est fixe en finale ; le polonais "
                       "le fixe sur l'avant-dernière syllabe, le tchèque sur "
                       "la première. Le russe et l'espagnol le laissent "
                       "bouger — il peut alors distinguer des mots : hablo "
                       "« je parle » contre habló « il a parlé »."},
        "pt": {"question": "Onde cai o acento tónico em francês?",
               "options": ["Muda de palavra para palavra e tem de se aprender",
                           "Sempre no fim da palavra ou do grupo",
                           "Sempre na primeira sílaba",
                           "O francês não tem acento tónico"],
               "fact": "O acento francês é fixo no final; o polaco fixa-o na "
                       "penúltima sílaba, o checo na primeira. O russo e o "
                       "espanhol deixam-no mover-se — e aí distingue "
                       "palavras: hablo “falo” contra habló “falou”."},
        "ru": {"question": "Куда падает ударение во французском?",
               "options": ["Оно разное в разных словах, его надо учить",
                           "Всегда на конец слова или фразы",
                           "Всегда на первый слог",
                           "Во французском ударения нет"],
               "fact": "Французское ударение закреплено на конце; польское — "
                       "на предпоследнем слоге, чешское — на первом. В "
                       "русском и испанском оно подвижно, потому и различает "
                       "слова: за́мок и замо́к."},
        "ar": {"question": "أين يقع النبر في الكلمة الفرنسية؟",
               "options": ["يتنقل من كلمة إلى أخرى ويجب تعلمه",
                           "دائمًا في آخر الكلمة أو العبارة",
                           "دائمًا على المقطع الأول",
                           "لا نبر في الفرنسية إطلاقًا"],
               "fact": "النبر الفرنسي ثابت في النهاية؛ والبولندية تثبّته على "
                       "المقطع قبل الأخير، والتشيكية على الأول. أما الروسية "
                       "والإسبانية فيتحرك فيهما النبر حتى إنه يفرّق بين "
                       "الكلمات: hablo “أتكلم” وhabló “تكلَّم”."},
    },
    {
        "answer": 0,
        "en": {"question": "In Italian, pala means “shovel” and palla means “ball”. What distinguishes them in speech?",
               "options": ["The l is held longer — a double (geminate) consonant",
                           "Nothing; only spelling",
                           "The stress moves",
                           "The first a changes"],
               "fact": "Consonant length is meaningful in Italian, Finnish, "
                       "Japanese and Arabic — Arabic even has a diacritic "
                       "for it, the shadda. English speakers hear the "
                       "difference easily across words: “bus stop” vs "
                       "“bus top”."},
        "es": {"question": "En italiano, pala es “pala” y palla es “pelota”. ¿Qué las distingue al hablar?",
               "options": ["La l se sostiene más: una consonante doble (geminada)",
                           "Nada; solo la ortografía",
                           "Se mueve el acento",
                           "Cambia la primera a"],
               "fact": "La duración de la consonante importa en italiano, "
                       "finés, japonés y árabe — el árabe hasta tiene un "
                       "diacrítico para eso, la shadda. En español se oye "
                       "entre palabras: “las salas” frente a “la "
                       "sala”."},
        "fr": {"question": "En italien, pala veut dire « pelle » et palla « balle ». Qu'est-ce qui les distingue à l'oral ?",
               "options": ["Le l est tenu plus longtemps — une consonne double (géminée)",
                           "Rien ; seulement l'orthographe",
                           "L'accent se déplace",
                           "Le premier a change"],
               "fact": "La longueur des consonnes est distinctive en "
                       "italien, en finnois, en japonais et en arabe — "
                       "l'arabe a même un signe pour cela, la chadda. En "
                       "français on l'entend entre les mots : « il l'a "
                       "dit » contre « il a dit »."},
        "pt": {"question": "Em italiano, pala é “pá” e palla é “bola”. O que as distingue na fala?",
               "options": ["O l é segurado mais tempo — uma consoante dupla (geminada)",
                           "Nada; só a ortografia",
                           "O acento muda de lugar",
                           "O primeiro a muda"],
               "fact": "A duração da consoante é distintiva em italiano, "
                       "finlandês, japonês e árabe — o árabe até tem um "
                       "diacrítico para isso, a chadda. Entre palavras "
                       "ouve-se em português: “às salas” contra “à "
                       "sala”."},
        "ru": {"question": "По-итальянски pala — «лопата», palla — «мяч». Чем они различаются в речи?",
               "options": ["Звук l тянется дольше — двойной (геминированный) согласный",
                           "Ничем, только написанием",
                           "Смещается ударение",
                           "Меняется первая a"],
               "fact": "Долгота согласного различает слова в итальянском, "
                       "финском, японском и арабском — в арабском для неё "
                       "есть даже значок, шадда. В русском это слышно на "
                       "стыках: «введение» против «ведение»."},
        "ar": {"question": "بالإيطالية pala تعني “مجرفة” وpalla تعني “كرة”. ما الفرق بينهما في النطق؟",
               "options": ["حرف اللام يُمَدُّ أطول — صامت مضعَّف",
                           "لا شيء؛ الفرق في الكتابة فقط",
                           "ينتقل النبر",
                           "تتغير الألف الأولى"],
               "fact": "طول الصامت يفرّق بين الكلمات في الإيطالية والفنلندية "
                       "واليابانية والعربية — بل إن للعربية علامة خاصة به هي "
                       "الشدة: فرِّق بين “درس” و“درَّس”."},
    },
    {
        "answer": 2,
        "en": {"question": "French bon and Portuguese bom end in a vowel with a special quality. Which?",
               "options": ["It is whispered",
                           "It is doubled",
                           "It is nasal — air flows through the nose as you say it",
                           "It is silent"],
               "fact": "Portuguese pão, mãe and João all carry nasal "
                       "vowels, marked by the tilde. Polish and Yoruba have "
                       "them too. French once had more; spelling still "
                       "remembers them in -on, -an, -in."},
        "es": {"question": "El francés bon y el portugués bom terminan en una vocal con una cualidad especial. ¿Cuál?",
               "options": ["Es susurrada",
                           "Es doble",
                           "Es nasal: el aire sale por la nariz al pronunciarla",
                           "Es muda"],
               "fact": "El portugués pão, mãe y João llevan vocales "
                       "nasales, marcadas con la tilde de la eñe portuguesa. "
                       "El polaco y el yoruba también las tienen. El español "
                       "las perdió; el francés las conserva en -on, -an, "
                       "-in."},
        "fr": {"question": "Le français « bon » et le portugais « bom » finissent par une voyelle d'une qualité particulière. Laquelle ?",
               "options": ["Elle est chuchotée",
                           "Elle est doublée",
                           "Elle est nasale — l'air passe par le nez quand on la prononce",
                           "Elle est muette"],
               "fact": "Le portugais pão, mãe et João portent des voyelles "
                       "nasales, marquées par le tilde. Le polonais et le "
                       "yoruba en ont aussi. Le français en est riche : bon, "
                       "blanc, brin, brun."},
        "pt": {"question": "O francês bon e o português bom terminam numa vogal com uma qualidade especial. Qual?",
               "options": ["É sussurrada",
                           "É dobrada",
                           "É nasal — o ar sai pelo nariz ao dizê-la",
                           "É muda"],
               "fact": "Pão, mãe e João levam vogais nasais, marcadas pelo "
                       "til. O polaco e o iorubá também as têm. O espanhol "
                       "perdeu-as — por isso um espanhol diz “pan” onde "
                       "nós dizemos “pão”."},
        "ru": {"question": "Французское bon и португальское bom кончаются гласным с особым свойством. Каким?",
               "options": ["Он произносится шёпотом",
                           "Он удвоен",
                           "Он носовой — воздух при произнесении идёт через нос",
                           "Он немой"],
               "fact": "Португальские pão, mãe и João несут носовые "
                       "гласные, отмеченные тильдой. Они есть и в польском, "
                       "и в йоруба. Были и в древнерусском — «юсы» "
                       "старой кириллицы писали именно их."},
        "ar": {"question": "تنتهي الفرنسية bon والبرتغالية bom بصائت له صفة خاصة. ما هي؟",
               "options": ["يُهمَس همسًا",
                           "يُضاعَف",
                           "أنفيّ — يمر الهواء من الأنف عند نطقه",
                           "صامت لا يُنطق"],
               "fact": "تحمل الكلمات البرتغالية pão وmãe وJoão صوائت أنفية "
                       "تُكتب فوقها علامة التلدة. وتوجد في البولندية "
                       "واليوروبا أيضًا. والفرنسية غنية بها: bon وblanc "
                       "وbrin."},
    },
    {
        "answer": 1,
        "en": {"question": "Xhosa k', t' and p' are “ejectives”. What makes an ejective different?",
               "options": ["It is pronounced while breathing in",
                           "The air is pushed out by the closed glottis, giving a sharp popping sound",
                           "It is always whispered",
                           "It is twice as long"],
               "fact": "Ejectives ride on air compressed above the closed "
                       "vocal folds rather than air from the lungs. Georgian, "
                       "Amharic, Quechua and many languages of the Caucasus "
                       "and the Americas use them as everyday consonants."},
        "es": {"question": "Las k', t' y p' del xhosa son “eyectivas”. ¿Qué hace distinta a una eyectiva?",
               "options": ["Se pronuncia inspirando",
                           "El aire lo empuja la glotis cerrada, con un chasquido seco",
                           "Siempre se susurra",
                           "Dura el doble"],
               "fact": "Las eyectivas usan aire comprimido sobre las cuerdas "
                       "vocales cerradas, no aire de los pulmones. El "
                       "georgiano, el amárico, el quechua y muchas lenguas "
                       "del Cáucaso y de América las usan como consonantes "
                       "de diario."},
        "fr": {"question": "Les k', t' et p' du xhosa sont des « éjectives ». Qu'est-ce qui rend une éjective différente ?",
               "options": ["On la prononce en inspirant",
                           "L'air est chassé par la glotte fermée, avec un petit claquement sec",
                           "Elle est toujours chuchotée",
                           "Elle dure deux fois plus longtemps"],
               "fact": "Les éjectives utilisent l'air comprimé au-dessus des "
                       "cordes vocales fermées, pas l'air des poumons. Le "
                       "géorgien, l'amharique, le quechua et bien des langues "
                       "du Caucase et des Amériques en font des consonnes de "
                       "tous les jours."},
        "pt": {"question": "Os k', t' e p' do xhosa são “ejetivas”. O que torna uma ejetiva diferente?",
               "options": ["Pronuncia-se a inspirar",
                           "O ar é empurrado pela glote fechada, com um estalo seco",
                           "É sempre sussurrada",
                           "Dura o dobro"],
               "fact": "As ejetivas usam ar comprimido acima das cordas "
                       "vocais fechadas, não ar dos pulmões. O georgiano, o "
                       "amárico, o quéchua e muitas línguas do Cáucaso e das "
                       "Américas usam-nas como consoantes do dia a dia."},
        "ru": {"question": "Звуки k', t' и p' в коса — «абруптивы» (эйективы). Чем они особенны?",
               "options": ["Их произносят на вдохе",
                           "Воздух выталкивается сомкнутой гортанью, с резким щелчком",
                           "Их всегда шепчут",
                           "Они вдвое длиннее"],
               "fact": "Абруптивы работают на воздухе, сжатом над сомкнутыми "
                       "голосовыми связками, а не на лёгочном. В грузинском, "
                       "амхарском, кечуа и многих языках Кавказа и Америки "
                       "это самые обычные согласные."},
        "ar": {"question": "أصوات k' وt' وp' في الكوسا “قذفية”. ما الذي يميز الصوت القذفي؟",
               "options": ["يُنطق أثناء الشهيق",
                           "يدفع الهواءَ انغلاقُ المزمار فيخرج بفرقعة حادة",
                           "يُهمس دائمًا",
                           "يدوم ضعف المدة"],
               "fact": "تعتمد الأصوات القذفية على هواء مضغوط فوق الوترين "
                       "الصوتيين المغلقين لا على هواء الرئتين. وهي صوامت "
                       "يومية في الجورجية والأمهرية والكيتشوا ولغات كثيرة في "
                       "القوقاز والأمريكتين."},
    },
    {
        "answer": 0,
        "en": {"question": "Finnish tuli, tuuli and tulli are three different words. What separates them?",
               "options": ["Vowel and consonant LENGTH: fire, wind, customs",
                           "Tone",
                           "Stress",
                           "Nothing — they are spelling variants"],
               "fact": "Length alone does the work: tuli “fire”, tuuli "
                       "“wind”, tulli “customs office”. Japanese and "
                       "Arabic also build meaning on length — Arabic even "
                       "writes long vowels with their own letters."},
        "es": {"question": "En finés, tuli, tuuli y tulli son tres palabras distintas. ¿Qué las separa?",
               "options": ["La DURACIÓN de vocales y consonantes: fuego, viento, aduana",
                           "El tono",
                           "El acento",
                           "Nada: son variantes ortográficas"],
               "fact": "La pura duración hace el trabajo: tuli “fuego”, "
                       "tuuli “viento”, tulli “aduana”. El japonés y "
                       "el árabe también apoyan significado en la duración — "
                       "el árabe escribe las vocales largas con letras "
                       "propias."},
        "fr": {"question": "En finnois, tuli, tuuli et tulli sont trois mots différents. Qu'est-ce qui les sépare ?",
               "options": ["La DURÉE des voyelles et consonnes : feu, vent, douane",
                           "Le ton",
                           "L'accent",
                           "Rien — ce sont des variantes d'orthographe"],
               "fact": "La durée seule fait le travail : tuli « feu », "
                       "tuuli « vent », tulli « douane ». Le japonais "
                       "et l'arabe bâtissent aussi du sens sur la durée — "
                       "l'arabe écrit ses voyelles longues avec des lettres "
                       "à part entière."},
        "pt": {"question": "Em finlandês, tuli, tuuli e tulli são três palavras diferentes. O que as separa?",
               "options": ["A DURAÇÃO de vogais e consoantes: fogo, vento, alfândega",
                           "O tom",
                           "O acento",
                           "Nada — são variantes ortográficas"],
               "fact": "Só a duração faz o trabalho: tuli “fogo”, tuuli "
                       "“vento”, tulli “alfândega”. O japonês e o "
                       "árabe também constroem sentido sobre a duração — o "
                       "árabe escreve as vogais longas com letras próprias."},
        "ru": {"question": "Финские tuli, tuuli и tulli — три разных слова. Чем они различаются?",
               "options": ["ДОЛГОТОЙ гласных и согласных: огонь, ветер, таможня",
                           "Тоном",
                           "Ударением",
                           "Ничем — это варианты написания"],
               "fact": "Работу делает одна долгота: tuli «огонь», tuuli "
                       "«ветер», tulli «таможня». Японский и арабский "
                       "тоже строят смысл на долготе — в арабском долгие "
                       "гласные пишутся отдельными буквами."},
        "ar": {"question": "بالفنلندية tuli وtuuli وtulli ثلاث كلمات مختلفة. ما الذي يفصل بينها؟",
               "options": ["طول الصوائت والصوامت: نار، ريح، جمارك",
                           "النغمة",
                           "النبر",
                           "لا شيء — إنها اختلافات إملائية"],
               "fact": "الطول وحده يقوم بالعمل: tuli “نار” وtuuli “ريح” "
                       "وtulli “جمارك”. واليابانية والعربية تبنيان المعنى "
                       "على الطول أيضًا — فالعربية تفرّق بين “جمل” "
                       "و“جميل” و“جمال” بمدّ واحد."},
    },
    {
        "answer": 1,
        "en": {"question": "Russian brat (“brother”) and brat' (“to take”) differ only in the final t. How?",
               "options": ["One t is longer",
                           "One t is “soft” — said with the tongue raised toward the palate",
                           "One t is silent",
                           "One t is stressed"],
               "fact": "Russian pairs nearly every consonant into hard and "
                       "soft versions, doubling the inventory — the soft "
                       "sign ь writes the difference. Irish runs its whole "
                       "grammar on a similar broad/slender split."},
        "es": {"question": "En ruso, brat (“hermano”) y brat' (“tomar”) se distinguen solo en la t final. ¿Cómo?",
               "options": ["Una t es más larga",
                           "Una t es “blanda”: se dice con la lengua alzada hacia el paladar",
                           "Una t es muda",
                           "Una t lleva el acento"],
               "fact": "El ruso empareja casi todas sus consonantes en "
                       "versión dura y blanda, duplicando el inventario — el "
                       "signo blando ь escribe la diferencia. El irlandés "
                       "monta su gramática entera sobre un corte parecido."},
        "fr": {"question": "En russe, brat (« frère ») et brat' (« prendre ») ne diffèrent que par le t final. Comment ?",
               "options": ["L'un des t est plus long",
                           "L'un des t est « mou » — prononcé la langue relevée vers le palais",
                           "L'un des t est muet",
                           "L'un des t porte l'accent"],
               "fact": "Le russe apparie presque toutes ses consonnes en "
                       "version dure et molle, doublant l'inventaire — le "
                       "signe mou ь écrit la différence. L'irlandais fait "
                       "tourner toute sa grammaire sur un partage voisin."},
        "pt": {"question": "Em russo, brat (“irmão”) e brat' (“tomar”) diferem só no t final. Como?",
               "options": ["Um t é mais longo",
                           "Um t é “brando” — diz-se com a língua erguida para o palato",
                           "Um t é mudo",
                           "Um t leva o acento"],
               "fact": "O russo emparelha quase todas as consoantes em "
                       "versão dura e branda, duplicando o inventário — o "
                       "sinal brando ь escreve a diferença. O irlandês "
                       "assenta a gramática inteira num corte parecido."},
        "ru": {"question": "«Брат» и «брать» различаются только последним звуком. Чем именно?",
               "options": ["Один т длиннее",
                           "Один т мягкий — произносится с поднятой к нёбу спинкой языка",
                           "Один т немой",
                           "Один т ударный"],
               "fact": "Почти каждый русский согласный существует в твёрдой "
                       "и мягкой паре — инвентарь звуков от этого почти "
                       "удваивается, а на письме разницу несёт мягкий знак. "
                       "Ирландский строит на похожем разделении всю свою "
                       "грамматику."},
        "ar": {"question": "بالروسية brat (“أخ”) وbrat' (“يأخذ”) لا تختلفان إلا في التاء الأخيرة. كيف؟",
               "options": ["إحدى التاءين أطول",
                           "إحداهما “ليّنة” — تُنطق واللسان مرفوع نحو الحنك",
                           "إحداهما لا تُنطق",
                           "إحداهما منبورة"],
               "fact": "يُزاوج الروسي كل صامت تقريبًا بنسخة قاسية وأخرى "
                       "ليّنة فيتضاعف مخزون الأصوات — وعلامة اللين ь تكتب "
                       "الفرق. وتُدير الأيرلندية قواعدها كلها على انقسام "
                       "مشابه."},
    },
    # ---------------------------------------------------------- phonetics
    {
        "answer": 2,
        "en": {"question": "Hindi has FOUR different t-like stops where English has one. What are the extra distinctions?",
               "options": ["Loudness and pitch",
                           "Length and tone",
                           "Aspiration (a puff of air) and voicing, in every combination",
                           "They are dialect variants"],
               "fact": "ta, tha, da, dha — plain, breathy, voiced, and "
                       "breathy-voiced. English has aspiration too, but "
                       "never uses it to tell words apart: hold a hand "
                       "before your mouth and feel “pin” puff where "
                       "“spin” doesn't."},
        "es": {"question": "El hindi tiene CUATRO oclusivas parecidas a la t donde el español tiene una. ¿Qué distingue a las demás?",
               "options": ["El volumen y el tono",
                           "La duración y el tono",
                           "La aspiración (un soplo de aire) y la sonoridad, en todas las combinaciones",
                           "Son variantes dialectales"],
               "fact": "ta, tha, da, dha: simple, aspirada, sonora y sonora "
                       "aspirada. El inglés también aspira, pero nunca para "
                       "distinguir palabras: pon la mano ante la boca y "
                       "siente el soplo de “pin” que “spin” no tiene."},
        "fr": {"question": "Le hindi a QUATRE occlusives proches du t là où le français en a une. Quelles distinctions s'ajoutent ?",
               "options": ["Le volume et la hauteur",
                           "La durée et le ton",
                           "L'aspiration (un souffle d'air) et le voisement, dans toutes les combinaisons",
                           "Ce sont des variantes dialectales"],
               "fact": "ta, tha, da, dha : simple, aspirée, sonore, sonore "
                       "aspirée. L'anglais aspire aussi, mais jamais pour "
                       "distinguer des mots : la main devant la bouche, on "
                       "sent le souffle de « pin » que « spin » n'a "
                       "pas."},
        "pt": {"question": "O hindi tem QUATRO oclusivas parecidas com o t onde o português tem uma. Que distinções acrescenta?",
               "options": ["O volume e a altura",
                           "A duração e o tom",
                           "A aspiração (um sopro de ar) e o vozeamento, em todas as combinações",
                           "São variantes dialetais"],
               "fact": "ta, tha, da, dha: simples, aspirada, sonora e sonora "
                       "aspirada. O inglês também aspira, mas nunca para "
                       "distinguir palavras: com a mão diante da boca "
                       "sente-se o sopro de “pin” que “spin” não "
                       "tem."},
        "ru": {"question": "В хинди ЧЕТЫРЕ разных смычных вроде «т» там, где в русском один. Какие признаки добавляются?",
               "options": ["Громкость и высота",
                           "Долгота и тон",
                           "Придыхание (выдох воздуха) и звонкость — во всех сочетаниях",
                           "Это диалектные варианты"],
               "fact": "ta, tha, da, dha: простой, придыхательный, звонкий и "
                       "звонкий придыхательный. В английском придыхание тоже "
                       "есть, но слова оно не различает: поднесите ладонь ко "
                       "рту — «pin» дует, «spin» нет."},
        "ar": {"question": "في الهندية أربعة أصوات انفجارية شبيهة بالتاء حيث للعربية واحد. ما التمييزات الإضافية؟",
               "options": ["علو الصوت وطبقته",
                           "الطول والنغمة",
                           "الهمس النَّفَسي (نفخة هواء) والجهر، بكل التوليفات",
                           "إنها فروق لهجات"],
               "fact": "ta وtha وda وdha: عادي ومنفوس ومجهور ومجهور منفوس. "
                       "وفي الإنجليزية نفخة مماثلة لكنها لا تفرّق بين "
                       "الكلمات: ضع يدك أمام فمك تشعر بنفخة “pin” التي "
                       "تغيب عن “spin”."},
    },
    {
        "answer": 1,
        "en": {"question": "The Hindi sounds written ṭ and ḍ are “retroflex”. What does the tongue do?",
               "options": ["It touches the teeth",
                           "Its tip curls up and back toward the roof of the mouth",
                           "It vibrates",
                           "It doesn't move at all"],
               "fact": "Retroflexes colour the sound of most languages of "
                       "India, and they're why an Indian accent renders "
                       "English t and d the way it does — English t sits "
                       "just behind the teeth, ṭ much further back."},
        "es": {"question": "Los sonidos hindis escritos ṭ y ḍ son “retroflejos”. ¿Qué hace la lengua?",
               "options": ["Toca los dientes",
                           "La punta se curva hacia arriba y atrás, hacia el paladar",
                           "Vibra",
                           "No se mueve en absoluto"],
               "fact": "Las retroflejas dan color a la mayoría de las "
                       "lenguas de la India, y explican cómo suena la t "
                       "inglesa con acento indio: la t del español está en "
                       "los dientes; la ṭ, mucho más atrás."},
        "fr": {"question": "Les sons hindis notés ṭ et ḍ sont « rétroflexes ». Que fait la langue ?",
               "options": ["Elle touche les dents",
                           "Sa pointe se recourbe vers l'arrière du palais",
                           "Elle vibre",
                           "Elle ne bouge pas du tout"],
               "fact": "Les rétroflexes colorent la plupart des langues de "
                       "l'Inde, et c'est par elles que passe l'accent indien "
                       "en anglais : le t français se fait aux dents, le ṭ "
                       "bien plus en arrière."},
        "pt": {"question": "Os sons hindis escritos ṭ e ḍ são “retroflexos”. O que faz a língua?",
               "options": ["Toca nos dentes",
                           "A ponta curva-se para cima e para trás, contra o palato",
                           "Vibra",
                           "Não se move de todo"],
               "fact": "As retroflexas dão cor à maioria das línguas da "
                       "Índia, e são elas que moldam o t inglês no sotaque "
                       "indiano: o t português faz-se nos dentes; o ṭ, muito "
                       "mais atrás."},
        "ru": {"question": "Звуки хинди, записываемые ṭ и ḍ, — «ретрофлексные». Что делает язык?",
               "options": ["Касается зубов",
                           "Кончик загибается вверх и назад, к нёбу",
                           "Вибрирует",
                           "Вообще не движется"],
               "fact": "Ретрофлексные звуки окрашивают большинство языков "
                       "Индии — из-за них так звучат t и d в индийском "
                       "английском: русское «т» упирается в зубы, ṭ — "
                       "гораздо глубже."},
        "ar": {"question": "الصوتان الهنديان المكتوبان ṭ وḍ “التوائيان”. ماذا يفعل اللسان؟",
               "options": ["يلمس الأسنان",
                           "ينثني طرفه إلى أعلى وإلى الخلف نحو سقف الحلق",
                           "يهتز",
                           "لا يتحرك إطلاقًا"],
               "fact": "الأصوات الالتوائية تصبغ معظم لغات الهند، وهي سر نطق "
                       "التاء والدال في الإنجليزية بلكنة هندية: تاء العربية "
                       "عند الأسنان، أما ṭ فأعمق بكثير."},
    },
    {
        "answer": 0,
        "en": {"question": "The catch in the middle of English “uh-oh” is a real consonant in Arabic and Hawaiian. Which one?",
               "options": ["The glottal stop — Arabic hamza, Hawaiian ʻokina",
                           "A click",
                           "A rolled r",
                           "A nasal"],
               "fact": "In Hawaiʻi the ʻokina is a full letter: Hawaiʻi "
                       "itself contains one. Arabic hamza distinguishes "
                       "words, and German quietly inserts a glottal stop "
                       "before most vowel-initial words."},
        "es": {"question": "El corte en medio del inglés “uh-oh” es una consonante de pleno derecho en árabe y hawaiano. ¿Cuál?",
               "options": ["La oclusiva glotal: la hamza árabe, la ʻokina hawaiana",
                           "Un clic",
                           "Una erre vibrante",
                           "Una nasal"],
               "fact": "En Hawái la ʻokina es una letra plena: el propio "
                       "nombre Hawaiʻi lleva una. La hamza árabe distingue "
                       "palabras, y el alemán inserta sin ruido una oclusiva "
                       "glotal ante casi toda palabra que empieza por "
                       "vocal."},
        "fr": {"question": "Le petit arrêt au milieu de « uh-oh » en anglais est une vraie consonne en arabe et en hawaïen. Laquelle ?",
               "options": ["Le coup de glotte — hamza arabe, ʻokina hawaïenne",
                           "Un clic",
                           "Un r roulé",
                           "Une nasale"],
               "fact": "À Hawaï, la ʻokina est une lettre à part entière : "
                       "le nom Hawaiʻi en contient une. La hamza arabe "
                       "distingue des mots, et l'allemand glisse sans bruit "
                       "un coup de glotte devant presque tout mot commençant "
                       "par une voyelle."},
        "pt": {"question": "O corte no meio do inglês “uh-oh” é uma consoante de pleno direito em árabe e havaiano. Qual?",
               "options": ["A oclusiva glotal — a hamza árabe, a ʻokina havaiana",
                           "Um clique",
                           "Um r vibrante",
                           "Uma nasal"],
               "fact": "No Havai, a ʻokina é uma letra plena: o próprio nome "
                       "Hawaiʻi contém uma. A hamza árabe distingue "
                       "palavras, e o alemão insere discretamente uma "
                       "oclusiva glotal antes de quase toda a palavra "
                       "iniciada por vogal."},
        "ru": {"question": "Заминка в середине английского «uh-oh» — полноправный согласный в арабском и гавайском. Какой?",
               "options": ["Гортанная смычка — арабская хамза, гавайская окина",
                           "Щелчок",
                           "Раскатистое р",
                           "Носовой"],
               "fact": "На Гавайях окина — полноценная буква: она есть в "
                       "самом слове Hawaiʻi. Арабская хамза различает слова, "
                       "а немецкий незаметно вставляет гортанную смычку "
                       "почти перед каждым словом на гласный."},
        "ar": {"question": "التوقف الخاطف وسط “uh-oh” الإنجليزية صامتٌ كامل الحقوق في العربية والهاوايية. ما هو؟",
               "options": ["الوقفة الحنجرية — الهمزة العربية والعُكينة الهاوايية",
                           "صوت طقطقة",
                           "راء مكررة",
                           "صوت أنفي"],
               "fact": "في هاواي، العُكينة حرف كامل: اسم Hawaiʻi نفسه يحويها. "
                       "والهمزة العربية تفرّق بين الكلمات — “سأل” غير "
                       "“سال” — والألمانية تدسّ وقفة حنجرية قبل معظم "
                       "الكلمات المبدوءة بصائت."},
    },
    {
        "answer": 2,
        "en": {"question": "The two th-sounds of English (“think”, “this”) are…",
               "options": ["found in nearly every language",
                           "unique to English",
                           "rare worldwide — shared with Greek, Icelandic, Castilian Spanish and Arabic",
                           "recent inventions"],
               "fact": "Arabic has both, as ث and ذ. Most learners of "
                       "English substitute s/z, t/d or f/v — and entire "
                       "English dialects do the same: “fink” in London, "
                       "“tink” in Dublin."},
        "es": {"question": "Los dos sonidos th del inglés (“think”, “this”) son…",
               "options": ["comunes en casi todas las lenguas",
                           "exclusivos del inglés",
                           "raros en el mundo: los comparten el griego, el islandés, el español castellano y el árabe",
                           "invenciones recientes"],
               "fact": "El árabe tiene ambos, como ث y ذ — y el castellano "
                       "tiene el primero: es la z de “zapato”. Muchos "
                       "aprendices sustituyen s/z o t/d, y dialectos "
                       "enteros del inglés hacen igual: “fink” en "
                       "Londres, “tink” en Dublín."},
        "fr": {"question": "Les deux sons th de l'anglais (« think », « this ») sont…",
               "options": ["présents dans presque toutes les langues",
                           "propres à l'anglais",
                           "rares dans le monde — partagés avec le grec, l'islandais, l'espagnol castillan et l'arabe",
                           "des inventions récentes"],
               "fact": "L'arabe a les deux, ث et ذ. La plupart des "
                       "apprenants substituent s/z, t/d ou f/v — et des "
                       "dialectes anglais entiers font pareil : « fink » "
                       "à Londres, « tink » à Dublin."},
        "pt": {"question": "Os dois sons th do inglês (“think”, “this”) são…",
               "options": ["comuns em quase todas as línguas",
                           "exclusivos do inglês",
                           "raros no mundo — partilhados com o grego, o islandês, o castelhano e o árabe",
                           "invenções recentes"],
               "fact": "O árabe tem os dois, ث e ذ. A maioria dos "
                       "aprendentes substitui s/z, t/d ou f/v — e dialetos "
                       "ingleses inteiros fazem o mesmo: “fink” em "
                       "Londres, “tink” em Dublim."},
        "ru": {"question": "Два английских звука th («think», «this») — это…",
               "options": ["звуки, которые есть почти во всех языках",
                           "уникальная особенность английского",
                           "редкость в мире — их разделяют греческий, исландский, кастильский испанский и арабский",
                           "недавние новшества"],
               "fact": "В арабском есть оба — ث и ذ. Большинство изучающих "
                       "подставляют с/з, т/д или ф/в, и целые диалекты "
                       "английского делают то же: «fink» в Лондоне, "
                       "«tink» в Дублине."},
        "ar": {"question": "صوتا th في الإنجليزية (“think” و“this”) هما…",
               "options": ["موجودان في كل اللغات تقريبًا",
                           "خاصان بالإنجليزية وحدها",
                           "نادران عالميًا — تشارك فيهما اليونانية والآيسلندية وإسبانية قشتالة والعربية",
                           "ابتكاران حديثان"],
               "fact": "في العربية كلاهما: الثاء والذال. معظم متعلمي "
                       "الإنجليزية يستبدلون بهما s/z أو t/d أو f/v — ولهجات "
                       "إنجليزية بأكملها تفعل ذلك: “fink” في لندن "
                       "و“tink” في دبلن."},
    },
    # ---------------------------------------------------------- morphology
    {
        "answer": 1,
        "en": {"question": "Arabic kitāb (book), kātib (writer), maktab (office) all share k-t-b. What is this system called?",
               "options": ["Compounding",
                           "Root-and-pattern morphology: three consonants carry the idea, vowel patterns shape the word",
                           "Reduplication",
                           "Suffix chains"],
               "fact": "The root k-t-b holds “writing”; templates pour "
                       "meaning around it — kataba “he wrote”, maktaba "
                       "“library”, mukātaba “correspondence”. Hebrew "
                       "and the other Semitic languages are built the same "
                       "way."},
        "es": {"question": "El árabe kitāb (libro), kātib (escritor) y maktab (oficina) comparten k-t-b. ¿Cómo se llama este sistema?",
               "options": ["Composición",
                           "Morfología de raíz y esquema: tres consonantes llevan la idea y los patrones vocálicos moldean la palabra",
                           "Reduplicación",
                           "Cadenas de sufijos"],
               "fact": "La raíz k-t-b guarda la idea de escribir; los "
                       "esquemas vierten el significado alrededor: kataba "
                       "“escribió”, maktaba “biblioteca”, mukātaba "
                       "“correspondencia”. El hebreo y las demás lenguas "
                       "semíticas se construyen igual."},
        "fr": {"question": "L'arabe kitāb (livre), kātib (écrivain), maktab (bureau) partagent k-t-b. Comment s'appelle ce système ?",
               "options": ["La composition",
                           "La morphologie à racines et schèmes : trois consonnes portent l'idée, les gabarits vocaliques façonnent le mot",
                           "Le redoublement",
                           "Les chaînes de suffixes"],
               "fact": "La racine k-t-b porte « écrire » ; les schèmes "
                       "coulent le sens autour : kataba « il a écrit », "
                       "maktaba « bibliothèque », mukātaba "
                       "« correspondance ». L'hébreu et les autres "
                       "langues sémitiques sont bâtis pareil."},
        "pt": {"question": "O árabe kitāb (livro), kātib (escritor) e maktab (escritório) partilham k-t-b. Como se chama este sistema?",
               "options": ["Composição",
                           "Morfologia de raiz e padrão: três consoantes carregam a ideia, padrões vocálicos moldam a palavra",
                           "Reduplicação",
                           "Cadeias de sufixos"],
               "fact": "A raiz k-t-b guarda “escrever”; os padrões vertem "
                       "o sentido à volta: kataba “escreveu”, maktaba "
                       "“biblioteca”, mukātaba “correspondência”. O "
                       "hebraico e as demais línguas semíticas "
                       "constroem-se assim."},
        "ru": {"question": "Арабские kitāb (книга), kātib (писец), maktab (контора) делят корень k-t-b. Как называется эта система?",
               "options": ["Словосложение",
                           "Корне-шаблонная морфология: три согласных несут идею, огласовочные схемы лепят слово",
                           "Редупликация",
                           "Цепочки суффиксов"],
               "fact": "Корень k-t-b хранит «письмо»; шаблоны обливают "
                       "его смыслом: kataba «он написал», maktaba "
                       "«библиотека», mukātaba «переписка». Иврит и "
                       "остальные семитские языки устроены так же."},
        "ar": {"question": "“كتاب” و“كاتب” و“مكتب” تشترك في الجذر ك-ت-ب. ماذا يسمى هذا النظام؟",
               "options": ["التركيب",
                           "صرف الجذر والوزن: ثلاثة صوامت تحمل الفكرة والأوزان تصوغ الكلمة",
                           "التكرار",
                           "سلاسل اللواحق"],
               "fact": "الجذر ك-ت-ب يحمل معنى الكتابة، والأوزان تصبّ المعنى "
                       "حوله: كَتَبَ ومَكتبة ومُكاتبة واستكتاب. وعلى هذا "
                       "البناء نفسه تقوم العبرية وسائر اللغات السامية."},
    },
    {
        "answer": 0,
        "en": {"question": "Turkish evlerinizden means “from your houses”. How is it built?",
               "options": ["ev-ler-iniz-den: house + plural + your + from, each suffix doing one job",
                           "It is one unanalysable word",
                           "Four separate words written together",
                           "An abbreviation"],
               "fact": "Agglutination: suffixes snap on like beads, each "
                       "with exactly one meaning, and the chains can grow "
                       "absurdly long. Finnish, Hungarian, Swahili and "
                       "Quechua build words the same way."},
        "es": {"question": "El turco evlerinizden significa “desde vuestras casas”. ¿Cómo está construida?",
               "options": ["ev-ler-iniz-den: casa + plural + vuestro + desde, cada sufijo con una sola función",
                           "Es una palabra inanalizable",
                           "Cuatro palabras separadas escritas juntas",
                           "Una abreviatura"],
               "fact": "Aglutinación: los sufijos se enganchan como cuentas, "
                       "cada uno con exactamente un significado, y las "
                       "cadenas pueden alargarse hasta lo absurdo. El finés, "
                       "el húngaro, el suajili y el quechua construyen igual."},
        "fr": {"question": "Le turc evlerinizden signifie « depuis vos maisons ». Comment est-il construit ?",
               "options": ["ev-ler-iniz-den : maison + pluriel + votre + depuis, chaque suffixe ayant un seul rôle",
                           "C'est un mot inanalysable",
                           "Quatre mots séparés écrits ensemble",
                           "Une abréviation"],
               "fact": "L'agglutination : les suffixes s'enfilent comme des "
                       "perles, chacun avec exactement un sens, et les "
                       "chaînes peuvent devenir absurdement longues. Le "
                       "finnois, le hongrois, le swahili et le quechua "
                       "construisent pareil."},
        "pt": {"question": "O turco evlerinizden significa “das vossas casas”. Como se constrói?",
               "options": ["ev-ler-iniz-den: casa + plural + vosso + de, cada sufixo com uma só função",
                           "É uma palavra inanalisável",
                           "Quatro palavras separadas escritas juntas",
                           "Uma abreviatura"],
               "fact": "Aglutinação: os sufixos encaixam como contas, cada "
                       "um com exatamente um significado, e as cadeias podem "
                       "crescer até ao absurdo. O finlandês, o húngaro, o "
                       "suaíli e o quéchua constroem assim."},
        "ru": {"question": "Турецкое evlerinizden значит «из ваших домов». Как оно устроено?",
               "options": ["ev-ler-iniz-den: дом + множ. число + ваш + из, у каждого суффикса ровно одна работа",
                           "Это неразложимое слово",
                           "Четыре отдельных слова, записанные слитно",
                           "Сокращение"],
               "fact": "Агглютинация: суффиксы нанизываются, как бусины, "
                       "каждый ровно с одним значением, и цепочки растут до "
                       "абсурда. Так же строят слова финский, венгерский, "
                       "суахили и кечуа."},
        "ar": {"question": "الكلمة التركية evlerinizden تعني “من بيوتكم”. كيف بُنيت؟",
               "options": ["ev-ler-iniz-den: بيت + جمع + كُم + مِن، لكل لاحقة وظيفة واحدة",
                           "كلمة لا تقبل التحليل",
                           "أربع كلمات منفصلة كُتبت معًا",
                           "اختصار"],
               "fact": "الإلصاق: تنتظم اللواحق كالخرز، لكل واحدة معنى واحد "
                       "بالضبط، وقد تطول السلاسل طولًا عجيبًا. وتبني "
                       "الفنلندية والمجرية والسواحلية والكيتشوا كلماتها "
                       "بالطريقة نفسها."},
    },
    {
        "answer": 1,
        "en": {"question": "Why is the past of “go” the completely unrelated “went”?",
               "options": ["Sound change disguised the connection",
                           "Suppletion: two different old verbs fused into one paradigm",
                           "A printing error that stuck",
                           "It was borrowed from French"],
               "fact": "“Went” belonged to “wend”. Paradigms love to "
                       "patch themselves with strangers: good/better, "
                       "French va/ira, Spanish voy/fui, Russian "
                       "chelovek/lyudi — always in the commonest words, "
                       "where usage protects the irregularity."},
        "es": {"question": "¿Por qué el pasado de “ir” es el ajeno “fui”?",
               "options": ["Un cambio fonético disfrazó la conexión",
                           "Supleción: dos verbos antiguos distintos se fundieron en un solo paradigma",
                           "Una errata que se consolidó",
                           "Se tomó del francés"],
               "fact": "“Fui” pertenece históricamente a SER: dos verbos "
                       "latinos (ire, esse) parchearon un solo paradigma. "
                       "Pasa siempre en las palabras más usadas, donde el "
                       "uso protege la irregularidad: bueno/mejor, inglés "
                       "go/went, ruso chelovek/lyudi."},
        "fr": {"question": "Pourquoi « aller » fait-il « je vais, j'irai » — des formes sans aucun rapport ?",
               "options": ["Un changement phonétique a masqué le lien",
                           "La supplétion : plusieurs anciens verbes ont fusionné en un seul paradigme",
                           "Une coquille d'imprimerie qui a pris",
                           "C'est un emprunt à l'anglais"],
               "fact": "« Aller » recolle trois verbes latins : ambulare "
                       "(vais), ire (irai), et l'origine de « aller » "
                       "elle-même. Toujours dans les mots les plus courants, "
                       "où l'usage protège l'irrégularité : bon/meilleur, "
                       "anglais go/went, espagnol voy/fui."},
        "pt": {"question": "Porque é que o passado de “ir” é o estranhíssimo “fui”?",
               "options": ["Uma mudança de som disfarçou a ligação",
                           "Supleção: dois verbos antigos diferentes fundiram-se num só paradigma",
                           "Uma gralha que pegou",
                           "Foi emprestado do francês"],
               "fact": "“Fui” pertence historicamente a SER: dois verbos "
                       "latinos (ire, esse) remendaram um só paradigma. "
                       "Acontece sempre nas palavras mais usadas, onde o uso "
                       "protege a irregularidade: bom/melhor, inglês "
                       "go/went, russo tchelovek/liudi."},
        "ru": {"question": "Почему прошедшее от «идти» — совсем непохожее «шёл»?",
               "options": ["Звуковые изменения замаскировали связь",
                           "Супплетивизм: два разных древних глагола срослись в одну парадигму",
                           "Закрепившаяся опечатка",
                           "Заимствование из французского"],
               "fact": "«Идти» и «шёл» — исторически разные корни, "
                       "сросшиеся в одно спряжение. Так бывает в самых "
                       "частотных словах, где употребление хранит "
                       "нерегулярность: человек/люди, хорошо/лучше, "
                       "английские go/went."},
        "ar": {"question": "لماذا ماضي الفعل الإنجليزي “go” هو “went” الذي لا صلة له به؟",
               "options": ["تغيّر صوتي أخفى الصلة",
                           "الاستبدال الصرفي: فعلان قديمان مختلفان التحما في تصريف واحد",
                           "خطأ مطبعي رسخ",
                           "استعارة من الفرنسية"],
               "fact": "“went” كانت ماضي الفعل “wend”. والتصاريف تحب "
                       "الترقيع بالغرباء: good/better بالإنجليزية، voy/fui "
                       "بالإسبانية، человек/люди بالروسية — ودائمًا في "
                       "أكثر الكلمات استعمالًا، حيث يحمي الاستعمالُ الشذوذَ."},
    },
    {
        "answer": 0,
        "en": {"question": "Swahili mtu is “person”, watu is “people”. Where does the change happen?",
               "options": ["At the FRONT: Bantu noun classes swap prefixes, and agreement echoes them across the sentence",
                           "At the end, like most languages",
                           "In the middle vowel",
                           "Only in writing"],
               "fact": "Swahili sorts every noun into one of ~15 classes — "
                       "people, trees, tools, abstracts — each with its own "
                       "prefix pair, and verbs and adjectives repeat the "
                       "class marker: watu wazuri wale, “those good "
                       "people”, chimes wa- three times."},
        "es": {"question": "En suajili, mtu es “persona” y watu, “gente”. ¿Dónde ocurre el cambio?",
               "options": ["Al PRINCIPIO: las clases nominales bantúes cambian prefijos, y la concordancia los repite por toda la frase",
                           "Al final, como en la mayoría de las lenguas",
                           "En la vocal central",
                           "Solo en la escritura"],
               "fact": "El suajili reparte cada sustantivo en una de unas 15 "
                       "clases — personas, árboles, herramientas, "
                       "abstractos — cada una con su par de prefijos, y "
                       "verbos y adjetivos repiten la marca: watu wazuri "
                       "wale, “aquella buena gente”, hace sonar wa- tres "
                       "veces."},
        "fr": {"question": "En swahili, mtu veut dire « personne » et watu « les gens ». Où se produit le changement ?",
               "options": ["AU DÉBUT : les classes nominales bantoues échangent leurs préfixes, et l'accord les répète dans toute la phrase",
                           "À la fin, comme dans la plupart des langues",
                           "Dans la voyelle du milieu",
                           "Seulement à l'écrit"],
               "fact": "Le swahili range chaque nom dans l'une d'environ 15 "
                       "classes — personnes, arbres, outils, abstraits — "
                       "chacune avec sa paire de préfixes, et verbes et "
                       "adjectifs répètent la marque : watu wazuri wale, "
                       "« ces bonnes gens », fait sonner wa- trois fois."},
        "pt": {"question": "Em suaíli, mtu é “pessoa” e watu é “gente”. Onde acontece a mudança?",
               "options": ["No INÍCIO: as classes nominais bantas trocam prefixos, e a concordância repete-os pela frase fora",
                           "No fim, como na maioria das línguas",
                           "Na vogal do meio",
                           "Só na escrita"],
               "fact": "O suaíli arruma cada substantivo numa de ~15 classes "
                       "— pessoas, árvores, ferramentas, abstratos — cada "
                       "qual com o seu par de prefixos, e verbos e adjetivos "
                       "repetem a marca: watu wazuri wale, “aquela boa "
                       "gente”, faz soar wa- três vezes."},
        "ru": {"question": "В суахили mtu — «человек», watu — «люди». Где происходит изменение?",
               "options": ["В НАЧАЛЕ слова: именные классы банту меняют префиксы, и согласование разносит их по всему предложению",
                           "В конце, как в большинстве языков",
                           "В средней гласной",
                           "Только на письме"],
               "fact": "Суахили раскладывает существительные примерно по 15 "
                       "классам — люди, деревья, орудия, абстракции — у "
                       "каждого своя пара префиксов, и глаголы с "
                       "прилагательными повторяют показатель: watu wazuri "
                       "wale, «те добрые люди», трижды отзывается wa-."},
        "ar": {"question": "في السواحلية mtu تعني “إنسان” وwatu تعني “ناس”. أين يقع التغيير؟",
               "options": ["في أول الكلمة: أصناف الأسماء البانتوية تبدّل السوابق، والمطابقة ترددها في الجملة كلها",
                           "في آخرها كما في معظم اللغات",
                           "في الصائت الأوسط",
                           "في الكتابة فقط"],
               "fact": "توزّع السواحلية أسماءها على نحو 15 صنفًا — الناس "
                       "والأشجار والأدوات والمجردات — لكل صنف زوج سوابق، "
                       "وتردد الأفعالُ والصفاتُ العلامةَ: watu wazuri wale، "
                       "“أولئك الناس الطيبون”، تُسمِع wa- ثلاث مرات."},
    },
    {
        "answer": 1,
        "en": {"question": "What is German famous for doing with nouns?",
               "options": ["Dropping them wherever possible",
                           "Welding them into long compounds, written as one word",
                           "Repeating them for emphasis",
                           "Never borrowing any"],
               "fact": "Streichholzschächtelchen — “little matchbox” — is "
                       "an everyday tongue-twister. The record-setters get "
                       "retired: a 63-letter beef-labelling law lost its "
                       "title when the law was repealed in 2013."},
        "es": {"question": "¿Por qué es famoso el alemán en cuanto a los sustantivos?",
               "options": ["Por omitirlos siempre que puede",
                           "Por soldarlos en compuestos larguísimos, escritos como una sola palabra",
                           "Por repetirlos para dar énfasis",
                           "Por no tomar ninguno prestado"],
               "fact": "Streichholzschächtelchen — “cajita de "
                       "cerillas” — es un trabalenguas cotidiano. Los "
                       "récords acaban jubilados: una ley del etiquetado "
                       "de la carne de 63 letras perdió el título al "
                       "derogarse en 2013."},
        "fr": {"question": "Pour quoi l'allemand est-il célèbre en matière de noms ?",
               "options": ["Il les omet dès que possible",
                           "Il les soude en longs composés, écrits en un seul mot",
                           "Il les répète pour insister",
                           "Il n'en emprunte jamais"],
               "fact": "Streichholzschächtelchen — « petite boîte "
                       "d'allumettes » — est un virelangue du quotidien. "
                       "Les recordmen finissent à la retraite : une loi de "
                       "63 lettres sur l'étiquetage du bœuf a perdu son "
                       "titre à son abrogation, en 2013."},
        "pt": {"question": "Pelo que é famoso o alemão no que toca aos substantivos?",
               "options": ["Por omiti-los sempre que possível",
                           "Por soldá-los em compostos compridos, escritos numa só palavra",
                           "Por repeti-los para dar ênfase",
                           "Por nunca pedir nenhum emprestado"],
               "fact": "Streichholzschächtelchen — “caixinha de "
                       "fósforos” — é um trava-línguas do quotidiano. Os "
                       "recordistas reformam-se: uma lei de 63 letras sobre "
                       "rotulagem de carne perdeu o título quando foi "
                       "revogada, em 2013."},
        "ru": {"question": "Чем знаменит немецкий в обращении с существительными?",
               "options": ["Опускает их при любой возможности",
                           "Сваривает их в длинные композиты, записываемые одним словом",
                           "Повторяет их для выразительности",
                           "Никогда их не заимствует"],
               "fact": "Streichholzschächtelchen — «спичечная "
                       "коробочка» — обычная бытовая скороговорка. "
                       "Рекордсмены уходят на пенсию: 63-буквенный закон о "
                       "маркировке говядины лишился титула, когда его "
                       "отменили в 2013 году."},
        "ar": {"question": "بمَ تشتهر الألمانية في تعاملها مع الأسماء؟",
               "options": ["بحذفها كلما أمكن",
                           "بلحمها في مركّبات طويلة تُكتب كلمة واحدة",
                           "بتكرارها للتوكيد",
                           "بأنها لا تستعير اسمًا قط"],
               "fact": "كلمة Streichholzschächtelchen — “علبة كبريت "
                       "صغيرة” — لعبة لسان يومية. وأصحاب الأرقام القياسية "
                       "يتقاعدون: قانونُ وسمِ لحوم البقر ذو الـ63 حرفًا فقد "
                       "لقبه حين أُلغي عام 2013."},
    },
    # ------------------------------------------------- historical linguistics
    {
        "answer": 2,
        "en": {"question": "Latin pater, piscis, tres — English father, fish, three. What explains the neat p→f, t→th matches?",
               "options": ["English borrowed the words and mangled them",
                           "Pure coincidence",
                           "Grimm's law: a regular sound shift that swept the Germanic languages",
                           "Latin copied Germanic"],
               "fact": "Sound change is regular enough to state as law — "
                       "the discovery that founded historical linguistics. "
                       "The same correspondences repeat everywhere you "
                       "look: pes/foot, cordem/heart, canis/hound."},
        "es": {"question": "Latín pater, piscis, tres — inglés father, fish, three. ¿Qué explica esas parejas tan limpias p→f, t→th?",
               "options": ["El inglés tomó las palabras y las deformó",
                           "Pura coincidencia",
                           "La ley de Grimm: un cambio fonético regular que barrió las lenguas germánicas",
                           "El latín copió del germánico"],
               "fact": "El cambio fonético es tan regular que puede "
                       "enunciarse como ley — el descubrimiento que fundó "
                       "la lingüística histórica. Las correspondencias se "
                       "repiten donde mires: pes/foot, cordem/heart, "
                       "canis/hound."},
        "fr": {"question": "Latin pater, piscis, tres — anglais father, fish, three. Qu'est-ce qui explique ces correspondances nettes p→f, t→th ?",
               "options": ["L'anglais a emprunté les mots en les déformant",
                           "Pure coïncidence",
                           "La loi de Grimm : une mutation phonétique régulière qui a balayé les langues germaniques",
                           "Le latin a copié le germanique"],
               "fact": "Le changement phonétique est assez régulier pour "
                       "s'énoncer en loi — la découverte qui a fondé la "
                       "linguistique historique. Les correspondances se "
                       "répètent partout : pes/foot, cordem/heart, "
                       "canis/hound."},
        "pt": {"question": "Latim pater, piscis, tres — inglês father, fish, three. O que explica os pares tão certinhos p→f, t→th?",
               "options": ["O inglês pediu as palavras emprestadas e estropiou-as",
                           "Pura coincidência",
                           "A lei de Grimm: uma mudança fonética regular que varreu as línguas germânicas",
                           "O latim copiou do germânico"],
               "fact": "A mudança fonética é regular ao ponto de se enunciar "
                       "como lei — a descoberta que fundou a linguística "
                       "histórica. As correspondências repetem-se onde quer "
                       "que se olhe: pes/foot, cordem/heart, canis/hound."},
        "ru": {"question": "Латинские pater, piscis, tres — английские father, fish, three. Что объясняет такие ровные пары p→f, t→th?",
               "options": ["Английский заимствовал эти слова и исказил",
                           "Чистое совпадение",
                           "Закон Гримма: регулярный сдвиг звуков, прокатившийся по германским языкам",
                           "Латынь скопировала германское"],
               "fact": "Звуковые изменения настолько регулярны, что их можно "
                       "записать как закон, — открытие, основавшее "
                       "историческую лингвистику. Соответствия повторяются "
                       "всюду: pes/foot, cordem/heart, canis/hound."},
        "ar": {"question": "اللاتينية pater وpiscis وtres تقابل الإنجليزية father وfish وthree. ما تفسير هذا التقابل المنتظم p→f وt→th؟",
               "options": ["استعارت الإنجليزية الكلمات وشوّهتها",
                           "محض مصادفة",
                           "قانون غريم: تحوّل صوتي منتظم اجتاح اللغات الجرمانية",
                           "اللاتينية نقلت عن الجرمانية"],
               "fact": "التغيّر الصوتي من الانتظام بحيث يُصاغ قانونًا — وهو "
                       "الاكتشاف الذي أسس علم اللغة التاريخي. والتقابلات "
                       "تتكرر أينما نظرت: pes/foot وcordem/heart "
                       "وcanis/hound."},
    },
    {
        "answer": 1,
        "en": {"question": "In 1786 a British judge in Calcutta noticed Sanskrit, Greek and Latin were too alike for chance. What did that found?",
               "options": ["Modern translation theory",
                           "Comparative linguistics — and the Indo-European family hypothesis",
                           "The first dictionary",
                           "Phonetic spelling reform"],
               "fact": "William Jones concluded all three had “sprung "
                       "from some common source, which perhaps no longer "
                       "exists”. That source — Proto-Indo-European — was "
                       "never written down, yet much of it has been "
                       "reconstructed sound by sound."},
        "es": {"question": "En 1786, un juez británico en Calcuta notó que el sánscrito, el griego y el latín se parecían demasiado para ser casualidad. ¿Qué fundó eso?",
               "options": ["La teoría moderna de la traducción",
                           "La lingüística comparada — y la hipótesis de la familia indoeuropea",
                           "El primer diccionario",
                           "La reforma ortográfica fonética"],
               "fact": "William Jones concluyó que las tres habían "
                       "“brotado de alguna fuente común que quizá ya no "
                       "existe”. Esa fuente — el protoindoeuropeo — nunca "
                       "se escribió, y sin embargo gran parte se ha "
                       "reconstruido sonido a sonido."},
        "fr": {"question": "En 1786, un juge britannique à Calcutta remarqua que sanskrit, grec et latin se ressemblaient trop pour le hasard. Qu'est-ce que cela a fondé ?",
               "options": ["La théorie moderne de la traduction",
                           "La linguistique comparée — et l'hypothèse de la famille indo-européenne",
                           "Le premier dictionnaire",
                           "La réforme phonétique de l'orthographe"],
               "fact": "William Jones conclut que les trois avaient "
                       "« jailli d'une source commune qui peut-être "
                       "n'existe plus ». Cette source — le "
                       "proto-indo-européen — ne fut jamais écrite ; on en a "
                       "pourtant reconstruit une grande part, son par son."},
        "pt": {"question": "Em 1786, um juiz britânico em Calcutá reparou que sânscrito, grego e latim eram parecidos demais para ser acaso. O que fundou isso?",
               "options": ["A teoria moderna da tradução",
                           "A linguística comparada — e a hipótese da família indo-europeia",
                           "O primeiro dicionário",
                           "A reforma ortográfica fonética"],
               "fact": "William Jones concluiu que as três tinham "
                       "“brotado de alguma fonte comum que talvez já não "
                       "exista”. Essa fonte — o proto-indo-europeu — nunca "
                       "foi escrita; ainda assim, grande parte foi "
                       "reconstruída som a som."},
        "ru": {"question": "В 1786 году британский судья в Калькутте заметил: санскрит, греческий и латынь слишком похожи для случайности. Что это основало?",
               "options": ["Современную теорию перевода",
                           "Сравнительное языкознание — и гипотезу индоевропейской семьи",
                           "Первый словарь",
                           "Фонетическую реформу орфографии"],
               "fact": "Уильям Джонс заключил, что все три «выросли из "
                       "общего источника, которого, возможно, уже нет». "
                       "Этот источник — праиндоевропейский — никогда не "
                       "записывался, и всё же немалая его часть "
                       "восстановлена звук за звуком."},
        "ar": {"question": "عام 1786 لاحظ قاضٍ بريطاني في كلكتا أن السنسكريتية واليونانية واللاتينية أشبه من أن تكون مصادفة. ماذا أسّست ملاحظته؟",
               "options": ["نظرية الترجمة الحديثة",
                           "علم اللغة المقارن — وفرضية الأسرة الهندوأوروبية",
                           "أول معجم",
                           "إصلاح الإملاء الصوتي"],
               "fact": "خلص ويليام جونز إلى أن الثلاث “انبثقت من مصدر "
                       "مشترك ربما لم يعد موجودًا”. ذلك المصدر — "
                       "الهندوأوروبية الأم — لم يُكتب قط، ومع ذلك أُعيد بناء "
                       "قسم كبير منه صوتًا صوتًا."},
    },
    {
        "answer": 0,
        "en": {"question": "Why does English keep animal/meat pairs like cow/beef, sheep/mutton, pig/pork?",
               "options": ["After 1066, farmers spoke English and the dining hall spoke Norman French",
                           "Butchers invented trade terms",
                           "The meat words are older",
                           "Religious food laws required it"],
               "fact": "The animal in the field kept its English name; the "
                       "dish served upstairs took the French one — boeuf, "
                       "mouton, porc. A class divide, fossilised in the "
                       "menu for a thousand years."},
        "es": {"question": "¿Por qué el inglés mantiene pares animal/carne como cow/beef, sheep/mutton, pig/pork?",
               "options": ["Tras 1066, el campo hablaba inglés y el comedor señorial, francés normando",
                           "Los carniceros inventaron términos del oficio",
                           "Las palabras de la carne son más antiguas",
                           "Lo exigían leyes religiosas sobre la comida"],
               "fact": "El animal en el prado conservó su nombre inglés; el "
                       "plato servido arriba tomó el francés: boeuf, mouton, "
                       "porc. Una división de clases fosilizada en el menú "
                       "durante mil años."},
        "fr": {"question": "Pourquoi l'anglais garde-t-il des paires animal/viande comme cow/beef, sheep/mutton, pig/pork ?",
               "options": ["Après 1066, la ferme parlait anglais et la table seigneuriale parlait français normand",
                           "Les bouchers ont inventé des termes de métier",
                           "Les mots de viande sont plus anciens",
                           "Des lois religieuses l'exigeaient"],
               "fact": "L'animal au pré garda son nom anglais ; le plat "
                       "servi en haut prit le nom français — bœuf, mouton, "
                       "porc. Une frontière de classe, fossilisée dans le "
                       "menu depuis mille ans."},
        "pt": {"question": "Porque é que o inglês guarda pares animal/carne como cow/beef, sheep/mutton, pig/pork?",
               "options": ["Depois de 1066, o campo falava inglês e a mesa senhorial falava francês normando",
                           "Os talhantes inventaram termos do ofício",
                           "As palavras da carne são mais antigas",
                           "Leis religiosas da alimentação exigiam-no"],
               "fact": "O animal no campo ficou com o nome inglês; o prato "
                       "servido lá em cima tomou o francês — boeuf, mouton, "
                       "porc. Uma divisão de classes fossilizada no menu há "
                       "mil anos."},
        "ru": {"question": "Почему в английском пары животное/мясо: cow/beef, sheep/mutton, pig/pork?",
               "options": ["После 1066 года крестьяне говорили по-английски, а господская столовая — по-нормандски",
                           "Мясники придумали цеховые термины",
                           "Слова для мяса древнее",
                           "Так требовали религиозные пищевые законы"],
               "fact": "Животное в поле сохранило английское имя; блюдо "
                       "наверху получило французское — boeuf, mouton, porc. "
                       "Классовая граница, застывшая в меню на тысячу лет."},
        "ar": {"question": "لماذا تحتفظ الإنجليزية بأزواج الحيوان/اللحم مثل cow/beef وsheep/mutton وpig/pork؟",
               "options": ["بعد 1066 كان الفلاحون يتكلمون الإنجليزية ومائدةُ السادة تتكلم الفرنسية النورمانية",
                           "اخترع الجزارون مصطلحات مهنة",
                           "كلمات اللحم أقدم عهدًا",
                           "فرضتها شرائع الطعام الدينية"],
               "fact": "احتفظ الحيوان في الحقل باسمه الإنجليزي، وأخذ الطبقُ "
                       "المقدَّم في الأعلى الاسمَ الفرنسي — boeuf وmouton "
                       "وporc. حدٌّ طبقي تحجّر في قائمة الطعام ألف سنة."},
    },
    {
        "answer": 1,
        "en": {"question": "Swahili safari, and English “safari” after it, trace back to which source?",
               "options": ["A Portuguese sailing term",
                           "Arabic safar, “journey” — one of Swahili's many Arabic loans",
                           "A Zulu hunting word",
                           "A colonial-era invention"],
               "fact": "Centuries of Indian-Ocean trade filled Swahili with "
                       "Arabic: the very name comes from sawāḥil, "
                       "“coasts”. Loans travel in chains — English took "
                       "safari from Swahili, which took safar from Arabic."},
        "es": {"question": "El suajili safari — y de ahí el “safari” de todos — ¿a qué fuente remonta?",
               "options": ["A un término náutico portugués",
                           "Al árabe safar, “viaje”: uno de los muchos préstamos árabes del suajili",
                           "A una palabra zulú de caza",
                           "A una invención de la época colonial"],
               "fact": "Siglos de comercio en el Índico llenaron el suajili "
                       "de árabe: hasta su nombre viene de sawāḥil, "
                       "“costas”. Los préstamos viajan en cadena: el "
                       "español tomó safari del inglés, este del suajili, y "
                       "este del árabe."},
        "fr": {"question": "Le swahili safari — et notre « safari » à sa suite — remonte à quelle source ?",
               "options": ["Un terme de marine portugais",
                           "L'arabe safar, « voyage » — l'un des nombreux emprunts arabes du swahili",
                           "Un mot de chasse zoulou",
                           "Une invention de l'époque coloniale"],
               "fact": "Des siècles de commerce dans l'océan Indien ont "
                       "rempli le swahili d'arabe : son nom même vient de "
                       "sawāḥil, « côtes ». Les emprunts voyagent en "
                       "chaîne — le français a pris safari à l'anglais, qui "
                       "l'a pris au swahili, qui a pris safar à l'arabe."},
        "pt": {"question": "O suaíli safari — e o nosso “safari” a seguir — remonta a que fonte?",
               "options": ["A um termo náutico português",
                           "Ao árabe safar, “viagem” — um dos muitos empréstimos árabes do suaíli",
                           "A uma palavra zulu de caça",
                           "A uma invenção da era colonial"],
               "fact": "Séculos de comércio no Índico encheram o suaíli de "
                       "árabe: o próprio nome vem de sawāḥil, "
                       "“costas”. Os empréstimos viajam em cadeia — o "
                       "português tomou safari do inglês, que o tomou do "
                       "suaíli, que tomou safar do árabe."},
        "ru": {"question": "Суахилийское safari — а следом и всеобщее «сафари» — к какому источнику восходит?",
               "options": ["К португальскому морскому термину",
                           "К арабскому safar, «путешествие», — одному из множества арабских заимствований суахили",
                           "К зулусскому охотничьему слову",
                           "К выдумке колониальной эпохи"],
               "fact": "Века торговли в Индийском океане наполнили суахили "
                       "арабским: само его имя — от sawāḥil, «берега». "
                       "Заимствования ходят цепочками: русский взял "
                       "«сафари» из английского, тот — из суахили, а тот "
                       "— safar из арабского."},
        "ar": {"question": "كلمة safari السواحلية — ومنها “سفاري” العالمية — إلى أي أصل تعود؟",
               "options": ["إلى مصطلح بحري برتغالي",
                           "إلى العربية “سَفَر” — واحدة من قروض السواحلية العربية الكثيرة",
                           "إلى كلمة صيد زولوية",
                           "إلى ابتكار من الحقبة الاستعمارية"],
               "fact": "قرون من تجارة المحيط الهندي ملأت السواحلية بالعربية: "
                       "حتى اسمها من “سواحل”. والقروض تسافر في سلاسل — "
                       "أخذت الإنجليزية safari من السواحلية، التي أخذت "
                       "“سفر” من العربية."},
    },
    {
        "answer": 2,
        "en": {"question": "English “silly” once meant “blessed”; “nice” meant “ignorant”. What is this drift called?",
               "options": ["Corruption",
                           "Slang",
                           "Semantic change — meanings wander while the form stays",
                           "Mistranslation"],
               "fact": "Meanings walk in patterns: they widen, narrow, "
                       "sour or sweeten. “Awful” once meant awe-inspiring; "
                       "Spanish bizarro drifted from “brave”; French "
                       "travail “work” descends from an instrument of "
                       "torture."},
        "es": {"question": "El inglés “silly” significó “bendito”; “nice”, “ignorante”. ¿Cómo se llama esta deriva?",
               "options": ["Corrupción",
                           "Jerga",
                           "Cambio semántico: los significados vagan mientras la forma se queda",
                           "Error de traducción"],
               "fact": "Los significados caminan con patrones: se "
                       "ensanchan, se estrechan, se agrian o se endulzan. "
                       "“Awful” fue “imponente”; bizarro derivó de "
                       "“valiente”; y “trabajo” desciende del "
                       "tripalium, un instrumento de tortura."},
        "fr": {"question": "L'anglais « silly » a signifié « béni » ; « nice », « ignorant ». Comment nomme-t-on cette dérive ?",
               "options": ["La corruption",
                           "L'argot",
                           "Le changement sémantique — les sens voyagent, la forme reste",
                           "Une erreur de traduction"],
               "fact": "Les sens marchent selon des motifs : ils "
                       "s'élargissent, se rétrécissent, s'aigrissent ou "
                       "s'adoucissent. « Awful » fut « imposant » ; et "
                       "le français « travail » descend du tripalium, un "
                       "instrument de torture."},
        "pt": {"question": "O inglês “silly” já significou “abençoado”; “nice”, “ignorante”. Como se chama esta deriva?",
               "options": ["Corrupção",
                           "Gíria",
                           "Mudança semântica — os sentidos vagueiam enquanto a forma fica",
                           "Erro de tradução"],
               "fact": "Os sentidos caminham com padrões: alargam, "
                       "estreitam, azedam ou adoçam. “Awful” já foi "
                       "“imponente”; e “trabalho” desce do tripalium, "
                       "um instrumento de tortura."},
        "ru": {"question": "Английское «silly» когда-то значило «блаженный», «nice» — «невежественный». Как называется этот дрейф?",
               "options": ["Порча языка",
                           "Сленг",
                           "Семантический сдвиг — значения странствуют, форма остаётся",
                           "Ошибка перевода"],
               "fact": "Значения ходят по узнаваемым тропам: расширяются, "
                       "сужаются, портятся и облагораживаются. «Awful» "
                       "значило «внушающий трепет»; русское «врач» "
                       "родственно «врать» в старом смысле «говорить, "
                       "заговаривать»."},
        "ar": {"question": "كانت “silly” الإنجليزية تعني “مبارَك” و“nice” تعني “جاهل”. ماذا يسمى هذا الانزياح؟",
               "options": ["فساد اللغة",
                           "عامية",
                           "التغيّر الدلالي — تتجول المعاني ويبقى المبنى",
                           "خطأ ترجمة"],
               "fact": "تسير المعاني في مسالك معروفة: تتسع وتضيق وتسوء "
                       "وتَحسُن. كانت “awful” تعني “مهيبًا”؛ وفي "
                       "العربية كانت “العقيلة” للمرأة الكريمة ثم خُصّت "
                       "بالزوجة."},
    },
    {
        "answer": 0,
        "en": {"question": "Which of these is a Romance language — a direct descendant of Latin?",
               "options": ["Romanian", "Albanian", "Hungarian", "Bulgarian"],
               "fact": "Romanian grew from the Latin of Roman Dacia and "
                       "kept its case endings longer than its western "
                       "cousins — while absorbing Slavic vocabulary from "
                       "every neighbour. Its neighbours are Slavic "
                       "(Bulgarian), Uralic (Hungarian) and a family of one "
                       "(Albanian)."},
        "es": {"question": "¿Cuál de estas es una lengua romance, descendiente directa del latín?",
               "options": ["El rumano", "El albanés", "El húngaro", "El búlgaro"],
               "fact": "El rumano creció del latín de la Dacia romana y "
                       "conservó los casos más tiempo que sus primos "
                       "occidentales, mientras absorbía vocabulario eslavo "
                       "de cada vecino. Sus vecinos son eslavos (búlgaro), "
                       "urálicos (húngaro) o familia de uno (albanés)."},
        "fr": {"question": "Laquelle de ces langues est une langue romane, descendante directe du latin ?",
               "options": ["Le roumain", "L'albanais", "Le hongrois", "Le bulgare"],
               "fact": "Le roumain a poussé sur le latin de la Dacie "
                       "romaine et a gardé ses cas plus longtemps que ses "
                       "cousins d'occident, tout en absorbant du vocabulaire "
                       "slave de chaque voisin. Ses voisins sont slaves "
                       "(bulgare), ouralien (hongrois) ou famille à un seul "
                       "membre (albanais)."},
        "pt": {"question": "Qual destas é uma língua românica — descendente direta do latim?",
               "options": ["O romeno", "O albanês", "O húngaro", "O búlgaro"],
               "fact": "O romeno cresceu do latim da Dácia romana e guardou "
                       "os casos mais tempo do que os primos ocidentais, "
                       "enquanto absorvia vocabulário eslavo de cada "
                       "vizinho. Os vizinhos são eslavos (búlgaro), urálicos "
                       "(húngaro) ou família de um só (albanês)."},
        "ru": {"question": "Какой из этих языков — романский, прямой потомок латыни?",
               "options": ["Румынский", "Албанский", "Венгерский", "Болгарский"],
               "fact": "Румынский вырос из латыни римской Дакии и дольше "
                       "западных родственников хранил падежи, впитывая при "
                       "этом славянскую лексику от всех соседей. Соседи же — "
                       "славяне (болгарский), уральцы (венгерский) и семья "
                       "из одного языка (албанский)."},
        "ar": {"question": "أي من هذه اللغات لغة رومانسية منحدرة مباشرة من اللاتينية؟",
               "options": ["الرومانية", "الألبانية", "المجرية", "البلغارية"],
               "fact": "نمت الرومانية من لاتينية داقية الرومانية وحافظت على "
                       "الإعراب أطول من قريباتها الغربيات، وهي تمتص مفردات "
                       "سلافية من كل جيرانها. أما الجيران فسلاف (البلغارية) "
                       "وأوراليون (المجرية) وأسرة من عضو واحد (الألبانية)."},
    },
    {
        "answer": 1,
        "en": {"question": "Where does the Cyrillic alphabet of Russian and Bulgarian come from?",
               "options": ["It evolved from runes",
                           "Created in the 9th–10th centuries for Slavic, building on Greek letters",
                           "Adapted from Latin",
                           "Invented by Peter the Great"],
               "fact": "Disciples of Cyril and Methodius shaped it in the "
                       "first Bulgarian empire, extending Greek with new "
                       "letters for Slavic sounds — ш, ч, ж. Peter the "
                       "Great only slimmed the letterforms eight centuries "
                       "later."},
        "es": {"question": "¿De dónde viene el alfabeto cirílico del ruso y el búlgaro?",
               "options": ["Evolucionó de las runas",
                           "Se creó en los siglos IX–X para el eslavo, sobre la base de las letras griegas",
                           "Se adaptó del latino",
                           "Lo inventó Pedro el Grande"],
               "fact": "Discípulos de Cirilo y Metodio le dieron forma en "
                       "el primer imperio búlgaro, ampliando el griego con "
                       "letras nuevas para los sonidos eslavos: ш, ч, ж. "
                       "Pedro el Grande solo estilizó los trazos ocho "
                       "siglos después."},
        "fr": {"question": "D'où vient l'alphabet cyrillique du russe et du bulgare ?",
               "options": ["Il a évolué à partir des runes",
                           "Créé aux IXe–Xe siècles pour le slave, sur la base des lettres grecques",
                           "Adapté du latin",
                           "Inventé par Pierre le Grand"],
               "fact": "Des disciples de Cyrille et Méthode l'ont façonné "
                       "dans le premier empire bulgare, prolongeant le grec "
                       "de lettres nouvelles pour les sons slaves — ш, ч, ж. "
                       "Pierre le Grand n'a fait qu'affiner les formes huit "
                       "siècles plus tard."},
        "pt": {"question": "De onde vem o alfabeto cirílico do russo e do búlgaro?",
               "options": ["Evoluiu das runas",
                           "Foi criado nos séculos IX–X para o eslavo, sobre a base das letras gregas",
                           "Foi adaptado do latino",
                           "Inventou-o Pedro, o Grande"],
               "fact": "Discípulos de Cirilo e Metódio moldaram-no no "
                       "primeiro império búlgaro, estendendo o grego com "
                       "letras novas para os sons eslavos — ш, ч, ж. Pedro, "
                       "o Grande, só afinou os traços oito séculos depois."},
        "ru": {"question": "Откуда происходит кириллица, которой пишут русский и болгарский?",
               "options": ["Развилась из рун",
                           "Создана в IX–X веках для славянской речи на основе греческих букв",
                           "Приспособлена из латиницы",
                           "Её изобрёл Пётр Первый"],
               "fact": "Её оформили ученики Кирилла и Мефодия в Первом "
                       "Болгарском царстве, дополнив греческое письмо "
                       "буквами для славянских звуков — ш, ч, ж. Пётр лишь "
                       "упростил начертания восемь веков спустя, введя "
                       "гражданский шрифт."},
        "ar": {"question": "من أين جاءت الأبجدية السيريلية التي تُكتب بها الروسية والبلغارية؟",
               "options": ["تطورت من الرونية",
                           "أُنشئت في القرنين التاسع والعاشر للسلافية على أساس الحروف اليونانية",
                           "كُيّفت من اللاتينية",
                           "اخترعها بطرس الأكبر"],
               "fact": "صاغها تلاميذ كيرلس وميثوديوس في الإمبراطورية "
                       "البلغارية الأولى، فمدّوا اليونانية بحروف جديدة "
                       "للأصوات السلافية — ш وч وж. ولم يفعل بطرس الأكبر بعد "
                       "ثمانية قرون سوى ترشيق أشكال الحروف."},
    },
    # ------------------------------------------- writing systems & scripts
    {
        "answer": 1,
        "en": {"question": "An Arabic speaker writes news in one form of the language and jokes with family in another. What is this called?",
               "options": ["Bilingualism", "Diglossia — a high and a low variety living side by side", "Code error", "Dialect death"],
               "fact": "Modern Standard Arabic serves print, school and "
                       "speeches; the spoken darija of Morocco or Egypt "
                       "serves life. Swiss German and standard German split "
                       "the same way — and no one speaks the high variety "
                       "at the dinner table."},
        "es": {"question": "Un hablante de árabe escribe las noticias en una forma de la lengua y bromea con su familia en otra. ¿Cómo se llama esto?",
               "options": ["Bilingüismo", "Diglosia: una variedad alta y una baja conviviendo", "Error de código", "Muerte dialectal"],
               "fact": "El árabe estándar moderno sirve para la prensa, la "
                       "escuela y los discursos; la dariya hablada de "
                       "Marruecos o Egipto sirve para la vida. El alemán de "
                       "Suiza y el estándar se reparten igual — y nadie "
                       "habla la variedad alta en la mesa."},
        "fr": {"question": "Un arabophone écrit les nouvelles dans une forme de la langue et plaisante en famille dans une autre. Comment cela s'appelle-t-il ?",
               "options": ["Le bilinguisme", "La diglossie — une variété haute et une basse qui cohabitent", "Une erreur de code", "La mort dialectale"],
               "fact": "L'arabe standard moderne sert à la presse, à l'école "
                       "et aux discours ; la darija parlée du Maroc ou "
                       "d'Égypte sert à la vie. Le suisse allemand et "
                       "l'allemand standard se partagent de la même façon — "
                       "et personne ne parle la variété haute à table."},
        "pt": {"question": "Um falante de árabe escreve as notícias numa forma da língua e brinca com a família noutra. Como se chama isto?",
               "options": ["Bilinguismo", "Diglossia — uma variedade alta e uma baixa a conviver", "Erro de código", "Morte dialetal"],
               "fact": "O árabe padrão moderno serve a imprensa, a escola e "
                       "os discursos; a darija falada de Marrocos ou do "
                       "Egito serve a vida. O alemão da Suíça e o padrão "
                       "dividem-se da mesma maneira — e ninguém fala a "
                       "variedade alta à mesa."},
        "ru": {"question": "Арабоговорящий пишет новости на одной форме языка, а шутит с семьёй на другой. Как это называется?",
               "options": ["Двуязычие", "Диглоссия — «высокая» и «низкая» разновидности бок о бок", "Ошибка кода", "Смерть диалекта"],
               "fact": "Современный стандартный арабский обслуживает печать, "
                       "школу и речи; разговорная дарижа Марокко или Египта — "
                       "жизнь. Так же делят труд швейцарский и литературный "
                       "немецкий, и «высокой» разновидностью за ужином не "
                       "говорит никто."},
        "ar": {"question": "يكتب الناطق بالعربية الأخبار بصيغة من اللغة ويمازح أهله بأخرى. ماذا تسمى هذه الظاهرة؟",
               "options": ["ثنائية اللغة", "الازدواج اللغوي — صيغة فصحى وأخرى دارجة تتعايشان", "خطأ في الترميز", "موت اللهجة"],
               "fact": "الفصحى للصحافة والمدرسة والخُطب، والدارجة المغربية أو "
                       "المصرية للحياة اليومية. وينقسم الألمانيّ السويسري "
                       "والألمانيّ الفصيح على النحو نفسه — ولا أحد يتكلم "
                       "الصيغة العليا على مائدة العشاء."},
    },
    {
        "answer": 2,
        "en": {"question": "How many writing systems does an ordinary Japanese sentence mix?",
               "options": ["One", "Two", "Three — kanji, hiragana and katakana, each with its own job", "Five"],
               "fact": "Kanji carry word roots, hiragana the grammar, "
                       "katakana the loanwords — so a reader can see at a "
                       "glance which part of the sentence is which. Rōmaji "
                       "makes an occasional fourth."},
        "es": {"question": "¿Cuántos sistemas de escritura mezcla una frase japonesa corriente?",
               "options": ["Uno", "Dos", "Tres: kanji, hiragana y katakana, cada uno con su función", "Cinco"],
               "fact": "Los kanji llevan las raíces, el hiragana la "
                       "gramática, el katakana los préstamos — así el lector "
                       "ve de un vistazo qué parte de la frase es cada cosa. "
                       "El rōmaji hace de cuarto ocasional."},
        "fr": {"question": "Combien de systèmes d'écriture une phrase japonaise ordinaire mélange-t-elle ?",
               "options": ["Un", "Deux", "Trois — kanji, hiragana et katakana, chacun avec son rôle", "Cinq"],
               "fact": "Les kanji portent les racines, les hiragana la "
                       "grammaire, les katakana les emprunts — le lecteur "
                       "voit d'un coup d'œil quelle partie de la phrase est "
                       "quoi. Le rōmaji fait un quatrième occasionnel."},
        "pt": {"question": "Quantos sistemas de escrita mistura uma frase japonesa corrente?",
               "options": ["Um", "Dois", "Três — kanji, hiragana e katakana, cada um com a sua função", "Cinco"],
               "fact": "Os kanji levam as raízes, o hiragana a gramática, o "
                       "katakana os empréstimos — o leitor vê num relance "
                       "que parte da frase é o quê. O rōmaji faz de quarto "
                       "ocasional."},
        "ru": {"question": "Сколько систем письма смешивает обычное японское предложение?",
               "options": ["Одну", "Две", "Три — кандзи, хирагану и катакану, у каждой своя работа", "Пять"],
               "fact": "Кандзи несут корни слов, хирагана — грамматику, "
                       "катакана — заимствования, так что читатель с одного "
                       "взгляда видит, где что. Ромадзи бывает четвёртой."},
        "ar": {"question": "كم نظام كتابة تخلط الجملة اليابانية العادية؟",
               "options": ["واحدًا", "اثنين", "ثلاثة — الكانجي والهيراغانا والكاتاكانا، لكلٍّ وظيفته", "خمسة"],
               "fact": "الكانجي تحمل جذور الكلمات، والهيراغانا القواعد، "
                       "والكاتاكانا الكلمات المستعارة — فيرى القارئ بلمحة أي "
                       "جزء من الجملة هو ماذا. والروماجي رابعٌ يظهر أحيانًا."},
    },
    {
        "answer": 0,
        "en": {"question": "In Devanagari, the script of Hindi, the letter क alone reads “ka”. What does that make it?",
               "options": ["An abugida: every consonant carries a built-in vowel unless marked otherwise",
                           "An alphabet like Greek",
                           "A set of word-pictures",
                           "A syllable lottery"],
               "fact": "Abugidas dress a consonant with vowel marks: क ka, "
                       "कि ki, कु ku. Ethiopia's Ge'ez script and the "
                       "scripts of Thai, Burmese, Khmer and most of India "
                       "work this way — a third answer to the "
                       "alphabet-or-syllabary question."},
        "es": {"question": "En devanagari, la escritura del hindi, la letra क sola se lee “ka”. ¿Qué la convierte eso?",
               "options": ["En un abugida: cada consonante lleva una vocal incorporada salvo marca en contra",
                           "En un alfabeto como el griego",
                           "En un juego de pictogramas",
                           "En una lotería de sílabas"],
               "fact": "Los abugidas visten la consonante con marcas "
                       "vocálicas: क ka, कि ki, कु ku. Así funcionan el "
                       "ge'ez de Etiopía y las escrituras del tailandés, el "
                       "birmano, el jemer y casi toda la India — una tercera "
                       "respuesta a la pregunta alfabeto-o-silabario."},
        "fr": {"question": "En devanagari, l'écriture du hindi, la lettre क seule se lit « ka ». Qu'est-ce que cela en fait ?",
               "options": ["Un abugida : chaque consonne porte une voyelle incorporée, sauf marque contraire",
                           "Un alphabet comme le grec",
                           "Un jeu de pictogrammes",
                           "Une loterie de syllabes"],
               "fact": "Les abugidas habillent la consonne de marques "
                       "vocaliques : क ka, कि ki, कु ku. Le guèze "
                       "d'Éthiopie et les écritures du thaï, du birman, du "
                       "khmer et de presque toute l'Inde fonctionnent "
                       "ainsi — une troisième réponse à la question "
                       "alphabet-ou-syllabaire."},
        "pt": {"question": "Em devanágari, a escrita do hindi, a letra क sozinha lê-se “ka”. O que faz dela isso?",
               "options": ["Um abugida: cada consoante traz uma vogal embutida, salvo marca em contrário",
                           "Um alfabeto como o grego",
                           "Um conjunto de pictogramas",
                           "Uma lotaria de sílabas"],
               "fact": "Os abugidas vestem a consoante com marcas vocálicas: "
                       "क ka, कि ki, कु ku. O ge'ez da Etiópia e as "
                       "escritas do tailandês, do birmanês, do khmer e de "
                       "quase toda a Índia funcionam assim — uma terceira "
                       "resposta à pergunta alfabeto-ou-silabário."},
        "ru": {"question": "В деванагари, письме хинди, буква क сама по себе читается «ка». Что это за тип письма?",
               "options": ["Абугида: каждый согласный несёт встроенный гласный, пока не отмечено иное",
                           "Алфавит вроде греческого",
                           "Набор рисунков-слов",
                           "Слоговая лотерея"],
               "fact": "Абугиды одевают согласный огласовками: क ка, कि "
                       "ки, कु ку. Так работают эфиопский геэз и письмена "
                       "тайского, бирманского, кхмерского и почти всей "
                       "Индии — третий ответ на вопрос «алфавит или "
                       "слоговое письмо»."},
        "ar": {"question": "في الديفاناغارية، خط الهندية، الحرف क وحده يُقرأ “كَا”. ماذا يجعلها ذلك؟",
               "options": ["أبوجيدا: كل صامت يحمل صائتًا مدمجًا ما لم يُوسم بغيره",
                           "أبجدية كاليونانية",
                           "مجموعة صور للكلمات",
                           "يانصيب مقاطع"],
               "fact": "الأبوجيدا تُلبس الصامتَ علاماتِ صوائت: क كَا، कि "
                       "كِي، कु كُو. وهكذا يعمل الجعزية الإثيوبي وخطوط "
                       "التايلاندية والبورمية والخميرية ومعظم الهند — جواب "
                       "ثالث عن سؤال أبجدية أم مقطعية. والحركات العربية "
                       "قريبة من الفكرة."},
    },
    {
        "answer": 1,
        "en": {"question": "In 1928 Turkey switched alphabets. How fast did the country move from Arabic to Latin script?",
               "options": ["Over about thirty years", "Within months — newspapers, schools and signs", "It never fully finished", "Only after 1950"],
               "fact": "The new 29-letter alphabet was tailored to Turkish "
                       "sounds — ç, ş, ğ, ı — and the old script vanished "
                       "from public life within a year. Few languages have "
                       "ever changed their writing so completely, so fast."},
        "es": {"question": "En 1928 Turquía cambió de alfabeto. ¿Con qué rapidez pasó el país de la escritura árabe a la latina?",
               "options": ["A lo largo de unos treinta años", "En cuestión de meses: prensa, escuelas y rótulos", "Nunca terminó del todo", "Solo después de 1950"],
               "fact": "El nuevo alfabeto de 29 letras se ajustó a los "
                       "sonidos turcos — ç, ş, ğ, ı — y la escritura vieja "
                       "desapareció de la vida pública en un año. Pocas "
                       "lenguas han cambiado su escritura tan completa y "
                       "rápidamente."},
        "fr": {"question": "En 1928, la Turquie a changé d'alphabet. À quelle vitesse le pays est-il passé de l'écriture arabe à la latine ?",
               "options": ["Sur une trentaine d'années", "En quelques mois — journaux, écoles et enseignes", "Cela ne s'est jamais tout à fait achevé", "Seulement après 1950"],
               "fact": "Le nouvel alphabet de 29 lettres était taillé pour "
                       "les sons turcs — ç, ş, ğ, ı — et l'ancienne écriture "
                       "a quitté la vie publique en un an. Peu de langues "
                       "ont changé d'écriture aussi complètement, aussi "
                       "vite."},
        "pt": {"question": "Em 1928 a Turquia trocou de alfabeto. Com que rapidez passou o país da escrita árabe à latina?",
               "options": ["Ao longo de uns trinta anos", "Em meses — jornais, escolas e tabuletas", "Nunca terminou de todo", "Só depois de 1950"],
               "fact": "O novo alfabeto de 29 letras foi talhado para os "
                       "sons turcos — ç, ş, ğ, ı — e a escrita antiga "
                       "desapareceu da vida pública num ano. Poucas línguas "
                       "mudaram a sua escrita tão completa e depressa."},
        "ru": {"question": "В 1928 году Турция сменила алфавит. Как быстро страна перешла с арабского письма на латиницу?",
               "options": ["Лет за тридцать", "За считанные месяцы — газеты, школы, вывески", "Полностью так и не перешла", "Только после 1950 года"],
               "fact": "Новый алфавит из 29 букв скроили под турецкие звуки "
                       "— ç, ş, ğ, ı — и старое письмо исчезло из публичной "
                       "жизни за год. Мало какой язык менял письменность "
                       "настолько полно и быстро."},
        "ar": {"question": "عام 1928 بدّلت تركيا أبجديتها. بأي سرعة انتقلت البلاد من الخط العربي إلى اللاتيني؟",
               "options": ["على مدى ثلاثين عامًا تقريبًا", "خلال أشهر — الصحف والمدارس واللافتات", "لم يكتمل الانتقال قط", "بعد 1950 فقط"],
               "fact": "فُصِّلت الأبجدية الجديدة ذات 29 حرفًا على أصوات "
                       "التركية — ç وş وğ وı — واختفى الخط القديم من الحياة "
                       "العامة خلال سنة. قلّما بدّلت لغةٌ كتابتها بهذا "
                       "الاكتمال وبهذه السرعة."},
    },
    {
        "answer": 2,
        "en": {"question": "How did the earliest writing manage to record abstract words like names?",
               "options": ["It couldn't, so names went unwritten",
                           "With special name-symbols",
                           "The rebus principle: use the picture of a thing that SOUNDS like what you mean",
                           "By inventing an alphabet immediately"],
               "fact": "Like writing “belief” with a bee and a leaf. "
                       "Sumerian scribes wrote the syllable ti (“life”) "
                       "with the arrow sign, also ti — the moment pictures "
                       "started recording sounds, and writing became able "
                       "to say anything."},
        "es": {"question": "¿Cómo logró la escritura más antigua registrar palabras abstractas, como los nombres?",
               "options": ["No podía, así que los nombres quedaban sin escribir",
                           "Con símbolos especiales para nombres",
                           "Con el principio del jeroglífico-jeroglífico (rebus): usar el dibujo de algo que SUENA como lo que quieres decir",
                           "Inventando un alfabeto de inmediato"],
               "fact": "Como escribir “soldado” con un sol y un dado. "
                       "Los escribas sumerios anotaban la sílaba ti "
                       "(“vida”) con el signo de la flecha, también ti — "
                       "el momento en que los dibujos empezaron a registrar "
                       "sonidos, y la escritura pudo decirlo todo."},
        "fr": {"question": "Comment la toute première écriture a-t-elle réussi à noter des mots abstraits, comme les noms propres ?",
               "options": ["Elle ne le pouvait pas : les noms restaient non écrits",
                           "Avec des symboles spéciaux pour les noms",
                           "Par le principe du rébus : utiliser l'image d'une chose qui SONNE comme ce qu'on veut dire",
                           "En inventant tout de suite un alphabet"],
               "fact": "Comme écrire « chagrin » avec un chat et un "
                       "grain. Les scribes sumériens notaient la syllabe ti "
                       "(« vie ») avec le signe de la flèche, ti aussi — "
                       "l'instant où les images se mirent à noter des sons, "
                       "et où l'écriture put tout dire."},
        "pt": {"question": "Como conseguiu a escrita mais antiga registar palavras abstratas, como os nomes?",
               "options": ["Não conseguia, e os nomes ficavam por escrever",
                           "Com símbolos especiais para nomes",
                           "Pelo princípio do rébus: usar a imagem de algo que SOA como o que se quer dizer",
                           "Inventando logo um alfabeto"],
               "fact": "Como escrever “soldado” com um sol e um dado. Os "
                       "escribas sumérios notavam a sílaba ti (“vida”) "
                       "com o sinal da flecha, também ti — o momento em que "
                       "as imagens passaram a registar sons, e a escrita "
                       "pôde dizer tudo."},
        "ru": {"question": "Как самая ранняя письменность ухитрялась записывать отвлечённые слова — например, имена?",
               "options": ["Никак — имена оставались незаписанными",
                           "Особыми знаками для имён",
                           "По принципу ребуса: рисунком вещи, которая ЗВУЧИТ как то, что нужно сказать",
                           "Сразу изобрели алфавит"],
               "fact": "Как записать «столица» через стол и лица. "
                       "Шумерские писцы обозначали слог ti («жизнь») "
                       "знаком стрелы — тоже ti. В этот момент картинки "
                       "начали записывать звуки, и письмо смогло сказать "
                       "что угодно."},
        "ar": {"question": "كيف استطاعت أقدم كتابة تدوين الكلمات المجردة كالأسماء؟",
               "options": ["لم تستطع، فبقيت الأسماء غير مكتوبة",
                           "برموز خاصة بالأسماء",
                           "بمبدأ الأحجية الصوتية: استخدام صورة شيء يُشبه صوتُه ما تريد قوله",
                           "باختراع أبجدية فورًا"],
               "fact": "كمن يكتب “سلسبيل” بصور سلسلة وبئر. دوّن الكتبة "
                       "السومريون المقطع ti (“حياة”) بعلامة السهم، وهو ti "
                       "أيضًا — تلك هي اللحظة التي بدأت فيها الصور تسجل "
                       "الأصوات فصارت الكتابة قادرة على قول أي شيء."},
    },
    {
        "answer": 1,
        "en": {"question": "What made the Rosetta Stone the key to Egyptian hieroglyphs?",
               "options": ["It listed every hieroglyph with its meaning",
                           "It carried the SAME decree in hieroglyphs, Demotic and Greek — and Greek could be read",
                           "It was written by a Greek tourist",
                           "It contained a pronunciation guide"],
               "fact": "Champollion cracked it in 1822 by chasing royal "
                       "names — Ptolemy, Cleopatra — through the cartouches, "
                       "proving hieroglyphs wrote sounds, not just ideas. "
                       "Every undeciphered script hunts for its own Rosetta."},
        "es": {"question": "¿Qué hizo de la piedra de Rosetta la llave de los jeroglíficos egipcios?",
               "options": ["Enumeraba cada jeroglífico con su significado",
                           "Llevaba el MISMO decreto en jeroglífico, demótico y griego — y el griego se podía leer",
                           "La escribió un turista griego",
                           "Contenía una guía de pronunciación"],
               "fact": "Champollion la descifró en 1822 persiguiendo "
                       "nombres reales — Ptolomeo, Cleopatra — por los "
                       "cartuchos, y demostró que los jeroglíficos escribían "
                       "sonidos, no solo ideas. Toda escritura sin descifrar "
                       "busca su propia Rosetta."},
        "fr": {"question": "Qu'est-ce qui a fait de la pierre de Rosette la clef des hiéroglyphes égyptiens ?",
               "options": ["Elle listait chaque hiéroglyphe avec son sens",
                           "Elle portait le MÊME décret en hiéroglyphes, en démotique et en grec — et le grec, on savait le lire",
                           "Un touriste grec l'avait écrite",
                           "Elle contenait un guide de prononciation"],
               "fact": "Champollion la déchiffra en 1822 en traquant les "
                       "noms royaux — Ptolémée, Cléopâtre — dans les "
                       "cartouches, prouvant que les hiéroglyphes notaient "
                       "des sons, pas seulement des idées. Toute écriture "
                       "non déchiffrée cherche sa Rosette."},
        "pt": {"question": "O que fez da pedra de Roseta a chave dos hieróglifos egípcios?",
               "options": ["Listava cada hieróglifo com o seu significado",
                           "Trazia o MESMO decreto em hieróglifos, demótico e grego — e o grego sabia-se ler",
                           "Foi escrita por um turista grego",
                           "Continha um guia de pronúncia"],
               "fact": "Champollion decifrou-a em 1822 perseguindo nomes "
                       "reais — Ptolomeu, Cleópatra — pelos cartuchos, "
                       "provando que os hieróglifos escreviam sons, não só "
                       "ideias. Toda a escrita por decifrar procura a sua "
                       "própria Roseta."},
        "ru": {"question": "Что сделало Розеттский камень ключом к египетским иероглифам?",
               "options": ["На нём был список иероглифов со значениями",
                           "Он нёс ОДИН И ТОТ ЖЕ указ иероглифами, демотикой и по-гречески — а греческий читать умели",
                           "Его написал греческий путешественник",
                           "На нём было руководство по произношению"],
               "fact": "Шампольон расшифровал его в 1822 году, выслеживая "
                       "царские имена — Птолемей, Клеопатра — в картушах, и "
                       "доказал, что иероглифы записывают звуки, а не только "
                       "идеи. Каждое нерасшифрованное письмо ищет свою "
                       "Розетту."},
        "ar": {"question": "ما الذي جعل حجر رشيد مفتاحَ الهيروغليفية المصرية؟",
               "options": ["أنه يسرد كل رمز هيروغليفي بمعناه",
                           "أنه حمل المرسوم نفسه بالهيروغليفية والديموطيقية واليونانية — واليونانية كانت مقروءة",
                           "أن سائحًا يونانيًا كتبه",
                           "أنه تضمّن دليل نطق"],
               "fact": "فكّ شامبليون رموزه عام 1822 بتتبّع الأسماء الملكية — "
                       "بطليموس وكليوباترا — داخل الخراطيش، فأثبت أن "
                       "الهيروغليفية تكتب أصواتًا لا أفكارًا فحسب. وكل خطٍّ "
                       "لم يُفك بعدُ يبحث عن حجر رشيد خاص به."},
    },
    {
        "answer": 0,
        "en": {"question": "Linear B, scratched on clay tablets in Bronze Age Crete, turned out to record…",
               "options": ["an early form of Greek — deciphered only in 1952",
                           "Egyptian",
                           "Phoenician",
                           "a language still unknown"],
               "fact": "Michael Ventris, an architect working from wartime "
                       "code-breaking methods, showed the tablets were "
                       "Greek five centuries older than Homer — mostly "
                       "palace inventories of sheep, oil and chariot "
                       "wheels. Its cousin Linear A remains unread."},
        "es": {"question": "El lineal B, grabado en tablillas de arcilla en la Creta de la Edad del Bronce, resultó registrar…",
               "options": ["una forma temprana de griego, descifrada recién en 1952",
                           "egipcio",
                           "fenicio",
                           "una lengua aún desconocida"],
               "fact": "Michael Ventris, un arquitecto que aplicó métodos "
                       "del criptoanálisis de guerra, mostró que las "
                       "tablillas eran griego cinco siglos anterior a "
                       "Homero — sobre todo inventarios palaciegos de "
                       "ovejas, aceite y ruedas de carro. Su primo, el "
                       "lineal A, sigue sin leerse."},
        "fr": {"question": "Le linéaire B, gravé sur des tablettes d'argile dans la Crète de l'âge du bronze, s'est révélé noter…",
               "options": ["une forme ancienne de grec — déchiffrée seulement en 1952",
                           "de l'égyptien",
                           "du phénicien",
                           "une langue toujours inconnue"],
               "fact": "Michael Ventris, architecte formé aux méthodes du "
                       "décryptage de guerre, montra que les tablettes "
                       "étaient du grec antérieur de cinq siècles à Homère — "
                       "surtout des inventaires palatiaux de moutons, "
                       "d'huile et de roues de char. Son cousin le linéaire "
                       "A reste illisible."},
        "pt": {"question": "O linear B, gravado em tabuinhas de argila na Creta da Idade do Bronze, revelou-se registar…",
               "options": ["uma forma antiga de grego — decifrada só em 1952",
                           "egípcio",
                           "fenício",
                           "uma língua ainda desconhecida"],
               "fact": "Michael Ventris, um arquiteto a aplicar métodos da "
                       "criptoanálise de guerra, mostrou que as tabuinhas "
                       "eram grego cinco séculos anterior a Homero — "
                       "sobretudo inventários palacianos de ovelhas, azeite "
                       "e rodas de carro. O primo linear A continua por "
                       "ler."},
        "ru": {"question": "Линейное письмо Б, процарапанное на глиняных табличках Крита бронзового века, оказалось записью…",
               "options": ["ранней формы греческого — расшифровано лишь в 1952 году",
                           "египетского",
                           "финикийского",
                           "языка, неизвестного до сих пор"],
               "fact": "Майкл Вентрис, архитектор с методами военных "
                       "дешифровщиков, показал: таблички — греческий на "
                       "пять веков старше Гомера, в основном дворцовые "
                       "описи овец, масла и колёс колесниц. Его родич, "
                       "линейное письмо А, не прочитан до сих пор."},
        "ar": {"question": "الخط الخطي “ب” المحفور على ألواح طينية في كريت العصر البرونزي تبيّن أنه يسجّل…",
               "options": ["صيغة مبكرة من اليونانية — لم تُفك إلا عام 1952",
                           "المصرية",
                           "الفينيقية",
                           "لغة ما تزال مجهولة"],
               "fact": "أثبت مايكل فنتريس، وهو معماري استعان بأساليب فك "
                       "الشفرات الحربية، أن الألواح يونانيةٌ أقدم من هوميروس "
                       "بخمسة قرون — ومعظمها جرودُ قصورٍ للأغنام والزيت "
                       "وعجلات المركبات. أما قريبه الخطي “أ” فلم يُقرأ "
                       "بعد."},
    },
    {
        "answer": 1,
        "en": {"question": "Why are Norse runes all straight lines and sharp angles?",
               "options": ["Religious rules required it",
                           "They were made to be CARVED — curves are hard to cut across wood grain",
                           "Their creators couldn't draw curves",
                           "To save space"],
               "fact": "Writing tools shape letters everywhere: cuneiform "
                       "is wedge-shaped from pressing reeds into clay, "
                       "Chinese strokes follow the brush, and roman "
                       "serifs echo the chisel."},
        "es": {"question": "¿Por qué las runas nórdicas son todo líneas rectas y ángulos afilados?",
               "options": ["Lo exigían reglas religiosas",
                           "Se hicieron para TALLARSE: las curvas son difíciles de cortar a contraveta",
                           "Sus creadores no sabían trazar curvas",
                           "Para ahorrar espacio"],
               "fact": "Las herramientas moldean las letras en todas "
                       "partes: la cuneiforme es de cuñas por presionar "
                       "cañas en arcilla, los trazos chinos siguen el "
                       "pincel y las serifas romanas recuerdan el cincel."},
        "fr": {"question": "Pourquoi les runes nordiques ne sont-elles que lignes droites et angles vifs ?",
               "options": ["Des règles religieuses l'exigeaient",
                           "Elles étaient faites pour être GRAVÉES — les courbes se taillent mal à travers le fil du bois",
                           "Leurs créateurs ne savaient pas tracer de courbes",
                           "Pour gagner de la place"],
               "fact": "Partout, l'outil façonne la lettre : le cunéiforme "
                       "est fait de coins pressés dans l'argile, les traits "
                       "chinois suivent le pinceau, et les empattements "
                       "romains gardent la mémoire du ciseau."},
        "pt": {"question": "Porque é que as runas nórdicas são só linhas retas e ângulos vivos?",
               "options": ["Regras religiosas exigiam-no",
                           "Foram feitas para TALHAR — curvas cortam-se mal contra o veio da madeira",
                           "Os criadores não sabiam traçar curvas",
                           "Para poupar espaço"],
               "fact": "A ferramenta molda a letra em todo o lado: o "
                       "cuneiforme é de cunhas prensadas na argila, os "
                       "traços chineses seguem o pincel, e as serifas "
                       "romanas ecoam o cinzel."},
        "ru": {"question": "Почему скандинавские руны — сплошь прямые линии и острые углы?",
               "options": ["Так требовали религиозные правила",
                           "Их создавали для РЕЗЬБЫ: кривые плохо режутся поперёк волокон дерева",
                           "Их создатели не умели чертить кривые",
                           "Для экономии места"],
               "fact": "Инструмент лепит букву повсюду: клинопись — из "
                       "клиньев тростника, вдавленных в глину, китайские "
                       "черты следуют кисти, а римские засечки помнят "
                       "резец."},
        "ar": {"question": "لماذا الرونية الإسكندنافية كلها خطوط مستقيمة وزوايا حادة؟",
               "options": ["فرضتها قواعد دينية",
                           "صُنعت لتُحفَر — والمنحنيات عسيرة القطع عبر ألياف الخشب",
                           "لم يعرف صانعوها رسم المنحنيات",
                           "توفيرًا للمساحة"],
               "fact": "الأداة تصوغ الحرف في كل مكان: المسمارية أسافين قصبٍ "
                       "مضغوطة في الطين، وضربات الصينية تتبع الفرشاة، "
                       "والخط العربي نفسه وليد القلم القصبي المائل."},
    },
    {
        "answer": 2,
        "en": {"question": "The digits 1, 2, 3 are called “Arabic numerals” in the West. Where were they actually born?",
               "options": ["Arabia", "Greece", "India — Arabic scholars carried them west", "Rome"],
               "fact": "Indian mathematicians invented the place-value "
                       "system and zero; al-Khwarizmi's books spread them, "
                       "so Europe named them after the messenger. Arabic "
                       "itself calls them “Indian numerals” — and uses "
                       "different digit shapes."},
        "es": {"question": "A las cifras 1, 2, 3 en Occidente se les llama “números arábigos”. ¿Dónde nacieron en realidad?",
               "options": ["En Arabia", "En Grecia", "En la India: los sabios árabes las llevaron al oeste", "En Roma"],
               "fact": "Los matemáticos indios inventaron el valor "
                       "posicional y el cero; los libros de Al-Juarismi los "
                       "difundieron, y Europa los bautizó por el mensajero. "
                       "El propio árabe los llama “números indios” — y "
                       "usa otras formas para las cifras."},
        "fr": {"question": "Les chiffres 1, 2, 3 sont dits « chiffres arabes » en Occident. Où sont-ils réellement nés ?",
               "options": ["En Arabie", "En Grèce", "En Inde — les savants arabes les ont portés vers l'ouest", "À Rome"],
               "fact": "Les mathématiciens indiens ont inventé la notation "
                       "de position et le zéro ; les livres d'Al-Khwarizmi "
                       "les ont diffusés, et l'Europe les a nommés d'après "
                       "le messager. L'arabe lui-même les appelle "
                       "« chiffres indiens » — avec d'autres formes."},
        "pt": {"question": "Os algarismos 1, 2, 3 chamam-se “arábicos” no Ocidente. Onde nasceram realmente?",
               "options": ["Na Arábia", "Na Grécia", "Na Índia — os sábios árabes levaram-nos para ocidente", "Em Roma"],
               "fact": "Os matemáticos indianos inventaram o valor de "
                       "posição e o zero; os livros de Al-Khwarizmi "
                       "espalharam-nos, e a Europa deu-lhes o nome do "
                       "mensageiro. O próprio árabe chama-lhes “algarismos "
                       "indianos” — e usa outras formas."},
        "ru": {"question": "Цифры 1, 2, 3 на Западе зовут «арабскими». Где они родились на самом деле?",
               "options": ["В Аравии", "В Греции", "В Индии — арабские учёные принесли их на запад", "В Риме"],
               "fact": "Индийские математики изобрели позиционную запись и "
                       "ноль; книги аль-Хорезми разнесли их, и Европа "
                       "назвала цифры именем посредника. Сам арабский зовёт "
                       "их «индийскими» — и пишет другими знаками. Да и "
                       "слово «цифра» — от арабского sifr, «ноль»."},
        "ar": {"question": "الأرقام 1 و2 و3 تسمى في الغرب “أرقامًا عربية”. أين وُلدت في الحقيقة؟",
               "options": ["في الجزيرة العربية", "في اليونان", "في الهند — وحملها العلماء العرب غربًا", "في روما"],
               "fact": "اخترع رياضيو الهند نظام الخانات والصفر؛ ونشرتها كتب "
                       "الخوارزمي، فسمّاها الأوروبيون باسم الرسول لا "
                       "المُرسِل. والعربية نفسها تسميها “الأرقام الهندية” "
                       "— ومن “صِفر” جاءت كلمة chiffre الفرنسية وcipher "
                       "الإنجليزية."},
    },
    {
        "answer": 0,
        "en": {"question": "Why does English write “knight” with a k and gh nobody says?",
               "options": ["Spelling froze while pronunciation kept moving — those letters were once all heard",
                           "Printers added decorative letters",
                           "To distinguish it from “night” in speech",
                           "French influence"],
               "fact": "Chaucer's knight was “k-n-i-ch-t”, every letter "
                       "sounded. French keeps whole silent syllables — "
                       "parlent — and Danish spelling drifts from speech "
                       "further still. Spelling is a museum; speech is a "
                       "street."},
        "es": {"question": "¿Por qué el inglés escribe “knight” con una k y una gh que nadie pronuncia?",
               "options": ["La ortografía se congeló mientras la pronunciación seguía andando: esas letras se oían todas",
                           "Los impresores añadieron letras decorativas",
                           "Para distinguirlo de “night” al hablar",
                           "Influencia francesa"],
               "fact": "El caballero de Chaucer era “k-n-i-ch-t”, con "
                       "cada letra sonando. El francés guarda sílabas mudas "
                       "enteras — parlent — y el danés se aleja aún más de "
                       "su habla. La ortografía es un museo; el habla, una "
                       "calle."},
        "fr": {"question": "Pourquoi l'anglais écrit-il « knight » avec un k et un gh que personne ne prononce ?",
               "options": ["L'orthographe a gelé pendant que la prononciation continuait d'avancer — toutes ces lettres s'entendaient jadis",
                           "Les imprimeurs ont ajouté des lettres décoratives",
                           "Pour le distinguer de « night » à l'oral",
                           "Influence française"],
               "fact": "Le chevalier de Chaucer se disait « k-n-i-ch-t », "
                       "chaque lettre sonnant. Le français garde des "
                       "syllabes muettes entières — « parlent » — et le "
                       "danois s'éloigne plus encore de sa parole. "
                       "L'orthographe est un musée ; la parole, une rue."},
        "pt": {"question": "Porque é que o inglês escreve “knight” com um k e um gh que ninguém diz?",
               "options": ["A ortografia congelou enquanto a pronúncia continuou a andar — essas letras já se ouviram todas",
                           "Os impressores acrescentaram letras decorativas",
                           "Para o distinguir de “night” na fala",
                           "Influência francesa"],
               "fact": "O cavaleiro de Chaucer era “k-n-i-ch-t”, cada "
                       "letra soando. O francês guarda sílabas mudas "
                       "inteiras — parlent — e o dinamarquês afasta-se ainda "
                       "mais da fala. A ortografia é um museu; a fala, uma "
                       "rua."},
        "ru": {"question": "Почему английский пишет «knight» с k и gh, которых никто не произносит?",
               "options": ["Орфография застыла, а произношение ушло вперёд — когда-то звучала каждая буква",
                           "Печатники добавили буквы для красоты",
                           "Чтобы в речи отличать от «night»",
                           "Французское влияние"],
               "fact": "Рыцарь у Чосера звучал «к-н-и-х-т», каждой "
                       "буквой. Французский хранит целые немые слоги — "
                       "parlent, — а датское письмо ушло от речи ещё дальше. "
                       "Орфография — музей; речь — улица."},
        "ar": {"question": "لماذا تكتب الإنجليزية “knight” بحرفي k وgh لا ينطقهما أحد؟",
               "options": ["تجمّد الإملاء بينما واصل النطق مسيره — كانت تلك الحروف كلها مسموعة يومًا",
                           "أضاف الطابعون حروفًا للزينة",
                           "للتفريق عن “night” في الكلام",
                           "تأثير فرنسي"],
               "fact": "كان فارس تشوسر يُنطق “ك-ن-ي-خ-ت” بكل حروفه. "
                       "والفرنسية تحتفظ بمقاطع صامتة كاملة — parlent — "
                       "والدنماركية أبعد من ذلك عن نطقها. الإملاء متحفٌ، "
                       "والكلام شارع."},
    },
    {
        "answer": 1,
        "en": {"question": "Which language opens questions and exclamations with upside-down marks — ¿ and ¡?",
               "options": ["Portuguese", "Spanish", "Italian", "Romanian"],
               "fact": "Adopted by the Spanish Royal Academy in 1754 so a "
                       "reader knows the sentence's tune before starting "
                       "it — Spanish word order often doesn't signal a "
                       "question. No other major language followed."},
        "es": {"question": "¿Qué lengua abre preguntas y exclamaciones con signos invertidos — ¿ y ¡?",
               "options": ["El portugués", "El español", "El italiano", "El rumano"],
               "fact": "Los adoptó la Real Academia en 1754 para que el "
                       "lector conozca la melodía de la frase antes de "
                       "empezarla — el orden de palabras español muchas "
                       "veces no delata la pregunta. Ninguna otra gran "
                       "lengua lo siguió."},
        "fr": {"question": "Quelle langue ouvre questions et exclamations par des signes renversés — ¿ et ¡ ?",
               "options": ["Le portugais", "L'espagnol", "L'italien", "Le roumain"],
               "fact": "Adoptés par l'Académie royale espagnole en 1754 "
                       "pour que le lecteur connaisse la mélodie de la "
                       "phrase avant de la commencer — l'ordre des mots "
                       "espagnol ne signale souvent pas la question. "
                       "Aucune autre grande langue n'a suivi."},
        "pt": {"question": "Que língua abre perguntas e exclamações com sinais invertidos — ¿ e ¡?",
               "options": ["O português", "O espanhol", "O italiano", "O romeno"],
               "fact": "Adotados pela Real Academia Espanhola em 1754 para "
                       "o leitor conhecer a melodia da frase antes de a "
                       "começar — a ordem das palavras em espanhol muitas "
                       "vezes não denuncia a pergunta. Nenhuma outra grande "
                       "língua seguiu o exemplo."},
        "ru": {"question": "Какой язык открывает вопросы и восклицания перевёрнутыми знаками — ¿ и ¡?",
               "options": ["Португальский", "Испанский", "Итальянский", "Румынский"],
               "fact": "Их ввела Испанская королевская академия в 1754 "
                       "году, чтобы читатель знал мелодию фразы до её "
                       "начала: испанский порядок слов часто не выдаёт "
                       "вопроса. Ни один другой крупный язык не "
                       "последовал."},
        "ar": {"question": "أي لغة تفتتح الأسئلة والتعجب بعلامتين مقلوبتين — ¿ و¡؟",
               "options": ["البرتغالية", "الإسبانية", "الإيطالية", "الرومانية"],
               "fact": "أقرّتهما الأكاديمية الملكية الإسبانية عام 1754 ليعرف "
                       "القارئ لحن الجملة قبل أن يبدأها — فترتيب الكلمات "
                       "الإسباني كثيرًا ما لا يكشف السؤال. ولم تحذُ حذوَها "
                       "لغة كبيرة أخرى."},
    },
    {
        "answer": 2,
        "en": {"question": "Which language still capitalizes Every Single Noun?",
               "options": ["Dutch", "Swedish", "German", "Icelandic"],
               "fact": "English did it too in the 18th century — read the "
                       "US Constitution — and Danish kept it until 1948. "
                       "German held on: Leben “life” wears its capital, "
                       "leben “to live” doesn't, and sometimes that's "
                       "the only visible difference."},
        "es": {"question": "¿Qué lengua sigue escribiendo con mayúscula Todos Los Sustantivos?",
               "options": ["El neerlandés", "El sueco", "El alemán", "El islandés"],
               "fact": "El inglés también lo hacía en el siglo XVIII — "
                       "léase la Constitución de EE. UU. — y el danés lo "
                       "mantuvo hasta 1948. El alemán resistió: Leben "
                       "“vida” lleva su mayúscula, leben “vivir” no, "
                       "y a veces esa es la única diferencia visible."},
        "fr": {"question": "Quelle langue met encore la majuscule à Chaque Nom Commun ?",
               "options": ["Le néerlandais", "Le suédois", "L'allemand", "L'islandais"],
               "fact": "L'anglais le faisait aussi au XVIIIe siècle — "
                       "lisez la Constitution américaine — et le danois "
                       "l'a gardé jusqu'en 1948. L'allemand a tenu bon : "
                       "Leben « la vie » porte sa majuscule, leben "
                       "« vivre » non, et c'est parfois la seule "
                       "différence visible."},
        "pt": {"question": "Que língua ainda escreve com maiúscula Todos Os Substantivos?",
               "options": ["O neerlandês", "O sueco", "O alemão", "O islandês"],
               "fact": "O inglês também o fazia no século XVIII — leia-se a "
                       "Constituição dos EUA — e o dinamarquês manteve-o "
                       "até 1948. O alemão resistiu: Leben “vida” leva "
                       "maiúscula, leben “viver” não, e às vezes essa é "
                       "a única diferença visível."},
        "ru": {"question": "Какой язык до сих пор пишет С Большой Буквы Каждое Существительное?",
               "options": ["Нидерландский", "Шведский", "Немецкий", "Исландский"],
               "fact": "Английский делал так же в XVIII веке — почитайте "
                       "конституцию США, — а датский держался до 1948 года. "
                       "Немецкий устоял: Leben «жизнь» носит заглавную, "
                       "leben «жить» — нет, и порой это единственная "
                       "видимая разница."},
        "ar": {"question": "أي لغة ما تزال تكتب كل اسم بحرف كبير في أوله؟",
               "options": ["الهولندية", "السويدية", "الألمانية", "الآيسلندية"],
               "fact": "فعلت الإنجليزية ذلك أيضًا في القرن الثامن عشر — "
                       "اقرأ الدستور الأمريكي — وأبقته الدنماركية حتى 1948. "
                       "وصمدت الألمانية: Leben “الحياة” بحرف كبير، وleben "
                       "“يعيش” من دونه، وقد يكون ذلك الفرق المرئي "
                       "الوحيد."},
    },
    {
        "answer": 0,
        "en": {"question": "Spoken Hindi and Urdu speakers chat with no interpreter. What separates the two on paper?",
               "options": ["Script and formal vocabulary: Devanagari and Sanskrit borrowings vs Perso-Arabic script and Persian borrowings",
                           "Completely different grammar",
                           "Different word order",
                           "Nothing at all"],
               "fact": "One spoken continuum, two writing systems, two "
                       "borrowing traditions, two national standards — the "
                       "clearest case of politics drawing the language "
                       "border. Serbian and Croatian repeat the pattern "
                       "with Cyrillic and Latin."},
        "es": {"question": "Hablantes de hindi y de urdu conversan sin intérprete. ¿Qué separa a las dos sobre el papel?",
               "options": ["La escritura y el vocabulario culto: devanagari y préstamos sánscritos frente a escritura persoárabe y préstamos persas",
                           "Gramáticas completamente distintas",
                           "Otro orden de palabras",
                           "Nada en absoluto"],
               "fact": "Un continuo hablado, dos escrituras, dos "
                       "tradiciones de préstamo, dos estándares "
                       "nacionales: el caso más claro de frontera "
                       "lingüística trazada por la política. El serbio y el "
                       "croata repiten el patrón con cirílico y latino."},
        "fr": {"question": "Les locuteurs du hindi et de l'ourdou bavardent sans interprète. Qu'est-ce qui sépare les deux sur le papier ?",
               "options": ["L'écriture et le vocabulaire soutenu : devanagari et emprunts sanskrits contre écriture perso-arabe et emprunts persans",
                           "Des grammaires complètement différentes",
                           "Un autre ordre des mots",
                           "Rien du tout"],
               "fact": "Un même continuum parlé, deux écritures, deux "
                       "traditions d'emprunt, deux standards nationaux — le "
                       "cas le plus net de frontière linguistique tracée "
                       "par la politique. Le serbe et le croate répètent le "
                       "schéma avec cyrillique et latin."},
        "pt": {"question": "Falantes de hindi e urdu conversam sem intérprete. O que separa as duas no papel?",
               "options": ["A escrita e o vocabulário culto: devanágari e empréstimos sânscritos contra escrita perso-árabe e empréstimos persas",
                           "Gramáticas completamente diferentes",
                           "Outra ordem de palavras",
                           "Nada de nada"],
               "fact": "Um contínuo falado, duas escritas, duas tradições "
                       "de empréstimo, dois padrões nacionais — o caso mais "
                       "claro de fronteira linguística traçada pela "
                       "política. O sérvio e o croata repetem o padrão com "
                       "cirílico e latino."},
        "ru": {"question": "Говорящие на хинди и урду болтают без переводчика. Что разделяет их на бумаге?",
               "options": ["Письмо и книжная лексика: деванагари с санскритскими заимствованиями против персо-арабского письма с персидскими",
                           "Совершенно разная грамматика",
                           "Другой порядок слов",
                           "Вообще ничего"],
               "fact": "Один разговорный континуум, две письменности, две "
                       "традиции заимствований, два государственных "
                       "стандарта — самый наглядный случай языковой "
                       "границы, проведённой политикой. Сербский и "
                       "хорватский повторяют узор кириллицей и латиницей."},
        "ar": {"question": "يتحادث متكلمو الهندية والأردية بلا مترجم. فما الذي يفصل بينهما على الورق؟",
               "options": ["الخط والمعجم الرسمي: ديفاناغارية واقتراض سنسكريتي مقابل خط فارسي-عربي واقتراض فارسي",
                           "قواعد مختلفة تمامًا",
                           "ترتيب كلمات آخر",
                           "لا شيء إطلاقًا"],
               "fact": "متصلٌ منطوق واحد وخطّان وتقليدا اقتراض ومعياران "
                       "وطنيان — أوضح حالة لحدود لغوية رسمتها السياسة. "
                       "وتكرر الصربية والكرواتية النمط بالسيريلية "
                       "واللاتينية."},
    },
    {
        "answer": 1,
        "en": {"question": "Persian is written in the Arabic script. What family does the language itself belong to?",
               "options": ["Semitic, like Arabic",
                           "Indo-European — a distant cousin of English, French and Hindi",
                           "Turkic",
                           "It is an isolate"],
               "fact": "Script and family are independent: Persian mādar "
                       "is sister to “mother” and Latin mater. Turkish "
                       "wore the Arabic script for centuries while being "
                       "Turkic; Swahili wore it too while being Bantu."},
        "es": {"question": "El persa se escribe con el alfabeto árabe. ¿A qué familia pertenece la lengua en sí?",
               "options": ["A la semítica, como el árabe",
                           "A la indoeuropea: prima lejana del inglés, el francés y el hindi",
                           "A la túrquica",
                           "Es una lengua aislada"],
               "fact": "Escritura y familia son independientes: el persa "
                       "mādar es hermana de “madre” y del latín mater. "
                       "El turco vistió siglos la escritura árabe siendo "
                       "túrquico; el suajili también, siendo bantú."},
        "fr": {"question": "Le persan s'écrit avec l'alphabet arabe. À quelle famille la langue elle-même appartient-elle ?",
               "options": ["Sémitique, comme l'arabe",
                           "Indo-européenne — cousine lointaine de l'anglais, du français et du hindi",
                           "Turcique",
                           "C'est un isolat"],
               "fact": "Écriture et famille sont indépendantes : le persan "
                       "mādar est sœur de « mère » et du latin mater. "
                       "Le turc a porté des siècles l'écriture arabe tout "
                       "en étant turcique ; le swahili aussi, tout en étant "
                       "bantou."},
        "pt": {"question": "O persa escreve-se com o alfabeto árabe. A que família pertence a língua em si?",
               "options": ["À semítica, como o árabe",
                           "À indo-europeia — prima afastada do inglês, do francês e do hindi",
                           "À turcomana",
                           "É um isolado"],
               "fact": "Escrita e família são independentes: o persa mādar "
                       "é irmã de “mãe” e do latim mater. O turco vestiu "
                       "séculos a escrita árabe sendo túrquico; o suaíli "
                       "também, sendo banto."},
        "ru": {"question": "Персидский пишется арабским письмом. К какой семье принадлежит сам язык?",
               "options": ["К семитской, как арабский",
                           "К индоевропейской — дальний родич английского, французского и хинди",
                           "К тюркской",
                           "Это изолят"],
               "fact": "Письмо и родство независимы: персидское mādar — "
                       "сестра русского «мать» и латинского mater. "
                       "Турецкий веками носил арабское письмо, оставаясь "
                       "тюркским; суахили тоже — оставаясь банту."},
        "ar": {"question": "تُكتب الفارسية بالخط العربي. فإلى أي أسرة تنتمي اللغة نفسها؟",
               "options": ["السامية كالعربية",
                           "الهندوأوروبية — قريبة بعيدة للإنجليزية والفرنسية والهندية",
                           "التركية",
                           "إنها لغة معزولة"],
               "fact": "الخط والنسب مستقلان: الفارسية mādar أخت الإنجليزية "
                       "mother واللاتينية mater. لبست التركية الخط العربي "
                       "قرونًا وهي تركية النسب؛ ولبسته السواحلية وهي "
                       "بانتوية."},
    },
    {
        "answer": 2,
        "en": {"question": "What is braille, linguistically speaking?",
               "options": ["A language of its own",
                           "A simplified code for short messages",
                           "A writing system — it can write French, Arabic, Chinese, music or mathematics",
                           "A kind of shorthand for English only"],
               "fact": "Louis Braille adapted a soldiers' night-writing "
                       "code at fifteen. Each language maps the six-dot "
                       "cells its own way — and contracted braille packs "
                       "frequent words into single cells, like a tactile "
                       "shorthand."},
        "es": {"question": "¿Qué es el braille, lingüísticamente hablando?",
               "options": ["Una lengua propia",
                           "Un código simplificado para mensajes cortos",
                           "Un sistema de escritura: puede escribir francés, árabe, chino, música o matemáticas",
                           "Una taquigrafía solo para inglés"],
               "fact": "Louis Braille adaptó a los quince años un código "
                       "militar de escritura nocturna. Cada lengua asigna "
                       "las celdas de seis puntos a su manera — y el "
                       "braille contraído comprime palabras frecuentes en "
                       "una sola celda, como una taquigrafía táctil."},
        "fr": {"question": "Qu'est-ce que le braille, linguistiquement parlant ?",
               "options": ["Une langue à part entière",
                           "Un code simplifié pour messages courts",
                           "Un système d'écriture — il peut écrire le français, l'arabe, le chinois, la musique ou les mathématiques",
                           "Une sténographie réservée à l'anglais"],
               "fact": "Louis Braille adapta à quinze ans un code militaire "
                       "d'écriture nocturne. Chaque langue distribue à sa "
                       "façon les cellules de six points — et le braille "
                       "abrégé condense les mots fréquents en une seule "
                       "cellule, comme une sténo tactile."},
        "pt": {"question": "O que é o braille, linguisticamente falando?",
               "options": ["Uma língua própria",
                           "Um código simplificado para mensagens curtas",
                           "Um sistema de escrita — pode escrever francês, árabe, chinês, música ou matemática",
                           "Uma estenografia só para inglês"],
               "fact": "Louis Braille adaptou aos quinze anos um código "
                       "militar de escrita noturna. Cada língua distribui "
                       "as células de seis pontos à sua maneira — e o "
                       "braille contraído comprime palavras frequentes numa "
                       "só célula, como uma estenografia táctil."},
        "ru": {"question": "Что такое брайль с лингвистической точки зрения?",
               "options": ["Отдельный язык",
                           "Упрощённый код для коротких сообщений",
                           "Система письма — ею можно записать французский, арабский, китайский, ноты и математику",
                           "Стенография только для английского"],
               "fact": "Луи Брайль в пятнадцать лет приспособил военный "
                       "код «ночного письма». Каждый язык раскладывает "
                       "шеститочечные ячейки по-своему, а краткопись "
                       "Брайля сжимает частые слова в одну ячейку — "
                       "осязательная стенография."},
        "ar": {"question": "ما البرايل من وجهة نظر لغوية؟",
               "options": ["لغة قائمة بذاتها",
                           "شفرة مبسطة للرسائل القصيرة",
                           "نظام كتابة — يكتب الفرنسية والعربية والصينية والموسيقى والرياضيات",
                           "اختزال للإنجليزية وحدها"],
               "fact": "كيّف لويس برايل في الخامسة عشرة شفرةً عسكرية "
                       "لـ“الكتابة الليلية”. وكل لغة توزّع خلايا النقاط "
                       "الست على طريقتها — وللعربية برايلها الخاص، وثمة "
                       "برايل مختزل يضغط الكلمات الشائعة في خلية واحدة."},
    },
    {
        "answer": 1,
        "en": {"question": "Icelandic schoolchildren can read sagas written around 800 years ago. Why?",
               "options": ["The sagas are modernised for them",
                           "Icelandic has changed unusually little — isolation and deliberate purism kept it archaic",
                           "All Icelanders study Old Norse for years",
                           "The sagas were written recently"],
               "fact": "The spelling standard leans archaic, and new ideas "
                       "get native coinages instead of loans: tölva "
                       "“computer” welds tala (number) to völva "
                       "(prophetess) — a number-prophetess. Pronunciation "
                       "has moved more than the page shows."},
        "es": {"question": "Los escolares islandeses pueden leer sagas escritas hace unos 800 años. ¿Por qué?",
               "options": ["Las sagas se les modernizan",
                           "El islandés ha cambiado inusualmente poco: el aislamiento y un purismo deliberado lo mantuvieron arcaico",
                           "Todos los islandeses estudian nórdico antiguo durante años",
                           "Las sagas se escribieron hace poco"],
               "fact": "La norma ortográfica tira a arcaica y las ideas "
                       "nuevas reciben acuñaciones propias en vez de "
                       "préstamos: tölva “ordenador” suelda tala "
                       "(número) con völva (profetisa) — una profetisa de "
                       "números. La pronunciación ha andado más de lo que "
                       "la página muestra."},
        "fr": {"question": "Les écoliers islandais peuvent lire des sagas écrites il y a environ 800 ans. Pourquoi ?",
               "options": ["On leur modernise les sagas",
                           "L'islandais a exceptionnellement peu changé — l'isolement et un purisme délibéré l'ont gardé archaïque",
                           "Tous les Islandais étudient le vieux norrois pendant des années",
                           "Les sagas ont été écrites récemment"],
               "fact": "La norme orthographique penche vers l'archaïque, et "
                       "les idées neuves reçoivent des créations locales "
                       "plutôt que des emprunts : tölva « ordinateur » "
                       "soude tala (nombre) à völva (prophétesse) — une "
                       "prophétesse des nombres. La prononciation a bougé "
                       "plus que la page ne le montre."},
        "pt": {"question": "As crianças islandesas conseguem ler sagas escritas há cerca de 800 anos. Porquê?",
               "options": ["As sagas são-lhes modernizadas",
                           "O islandês mudou invulgarmente pouco — o isolamento e um purismo deliberado mantiveram-no arcaico",
                           "Todos os islandeses estudam nórdico antigo durante anos",
                           "As sagas foram escritas há pouco"],
               "fact": "A norma ortográfica pende para o arcaico, e as "
                       "ideias novas recebem cunhagens próprias em vez de "
                       "empréstimos: tölva “computador” solda tala "
                       "(número) a völva (profetisa) — uma profetisa dos "
                       "números. A pronúncia andou mais do que a página "
                       "mostra."},
        "ru": {"question": "Исландские школьники могут читать саги, записанные около 800 лет назад. Почему?",
               "options": ["Саги для них осовременивают",
                           "Исландский изменился необычайно мало — изоляция и сознательный пуризм сохранили его архаичным",
                           "Все исландцы годами учат древнескандинавский",
                           "Саги написаны недавно"],
               "fact": "Орфографическая норма тяготеет к архаике, а новые "
                       "понятия получают свои слова вместо заимствований: "
                       "tölva «компьютер» сваривает tala (число) с völva "
                       "(пророчица) — числовая пророчица. Произношение "
                       "ушло дальше, чем видно со страницы."},
        "ar": {"question": "يستطيع تلاميذ آيسلندا قراءة ملاحم كُتبت قبل نحو 800 سنة. لماذا؟",
               "options": ["تُحدَّث الملاحم لهم",
                           "تغيّرت الآيسلندية قليلًا على نحو استثنائي — حفظتها العزلة والتزمّت اللغوي المتعمد",
                           "يدرس الآيسلنديون جميعًا النوردية القديمة سنوات",
                           "كُتبت الملاحم حديثًا"],
               "fact": "معيار الإملاء يميل إلى القديم، والمفاهيم الجديدة "
                       "تُنحت نحتًا محليًا بدل الاستعارة: tölva "
                       "“حاسوب” تلحم tala (عدد) بـvölva (عرّافة) — "
                       "عرّافة أعداد. أما النطق فقد تحرك أكثر مما تُظهر "
                       "الصفحة."},
    },
    # -------------------------- acquisition, psycholinguistics, use
    {
        "answer": 0,
        "en": {"question": "What can a six-month-old baby do that its parents no longer can?",
               "options": ["Hear the difference between speech sounds of ANY language",
                           "Understand grammar",
                           "Read facial expressions",
                           "Remember melodies"],
               "fact": "Infants start as universal listeners; by about "
                       "their first birthday they specialise in their own "
                       "language's sounds — which is why Japanese adults "
                       "struggle with r/l and English speakers with Hindi's "
                       "retroflexes. The categories close early."},
        "es": {"question": "¿Qué puede hacer un bebé de seis meses que sus padres ya no pueden?",
               "options": ["Distinguir de oído los sonidos de CUALQUIER lengua",
                           "Entender la gramática",
                           "Leer las expresiones de la cara",
                           "Recordar melodías"],
               "fact": "Los bebés empiezan como oyentes universales; hacia "
                       "su primer cumpleaños se especializan en los sonidos "
                       "de su lengua — por eso a los japoneses adultos les "
                       "cuestan r/l y a los hispanohablantes las "
                       "retroflejas del hindi. Las categorías se cierran "
                       "pronto."},
        "fr": {"question": "Que sait faire un bébé de six mois que ses parents ne savent plus faire ?",
               "options": ["Entendre la différence entre les sons de N'IMPORTE QUELLE langue",
                           "Comprendre la grammaire",
                           "Lire les expressions du visage",
                           "Retenir des mélodies"],
               "fact": "Les nourrissons commencent en auditeurs "
                       "universels ; vers leur premier anniversaire, ils se "
                       "spécialisent dans les sons de leur langue — voilà "
                       "pourquoi les adultes japonais peinent sur r/l et "
                       "les francophones sur les rétroflexes du hindi. Les "
                       "catégories se ferment tôt."},
        "pt": {"question": "O que consegue fazer um bebé de seis meses que os pais já não conseguem?",
               "options": ["Ouvir a diferença entre os sons de QUALQUER língua",
                           "Entender a gramática",
                           "Ler expressões faciais",
                           "Lembrar melodias"],
               "fact": "Os bebés começam como ouvintes universais; por "
                       "volta do primeiro aniversário especializam-se nos "
                       "sons da sua língua — por isso os japoneses adultos "
                       "sofrem com r/l e os lusófonos com as retroflexas do "
                       "hindi. As categorias fecham cedo."},
        "ru": {"question": "Что умеет полугодовалый младенец, чего уже не умеют его родители?",
               "options": ["Слышать разницу между звуками ЛЮБОГО языка",
                           "Понимать грамматику",
                           "Читать выражения лиц",
                           "Запоминать мелодии"],
               "fact": "Младенцы начинают как универсальные слушатели; к "
                       "первому дню рождения они специализируются на звуках "
                       "родного языка — потому взрослым японцам трудно с "
                       "r/l, а русскоговорящим — с ретрофлексными хинди. "
                       "Категории закрываются рано."},
        "ar": {"question": "ما الذي يستطيعه رضيع في شهره السادس ولم يعد والداه يستطيعانه؟",
               "options": ["تمييز أصوات أي لغة كانت بأذنه",
                           "فهم القواعد",
                           "قراءة تعابير الوجوه",
                           "حفظ الألحان"],
               "fact": "يبدأ الرضّع مستمعين كونيين؛ وقرب عيد ميلادهم الأول "
                       "يتخصصون في أصوات لغتهم — ولهذا يعاني اليابانيون "
                       "الكبار من r/l ويعاني الناطقون بالعربية من p/b. "
                       "فالفئات الصوتية تُغلق مبكرًا."},
    },
    {
        "answer": 1,
        "en": {"question": "Why do adults who master a language's grammar perfectly still keep an accent?",
               "options": ["Laziness",
                           "The sound categories and motor habits of the first language are set deep — grammar is learnable for life, new phonemes far less so",
                           "Accents are genetic",
                           "They secretly translate everything"],
               "fact": "Joseph Conrad wrote English prose among the "
                       "century's finest and spoke it, by all accounts, "
                       "with a heavy Polish accent his whole life. The pen "
                       "has no accent."},
        "es": {"question": "¿Por qué los adultos que dominan a la perfección la gramática de una lengua conservan el acento?",
               "options": ["Pereza",
                           "Las categorías de sonido y los hábitos motores de la primera lengua quedan grabados: la gramática se aprende toda la vida; los fonemas nuevos, mucho menos",
                           "El acento es genético",
                           "Traducen todo en secreto"],
               "fact": "Joseph Conrad escribió una prosa inglesa de las "
                       "mejores de su siglo y la habló, según todos los "
                       "testimonios, con un fuerte acento polaco toda su "
                       "vida. La pluma no tiene acento."},
        "fr": {"question": "Pourquoi des adultes qui maîtrisent parfaitement la grammaire d'une langue gardent-ils un accent ?",
               "options": ["Par paresse",
                           "Les catégories sonores et les habitudes motrices de la première langue sont ancrées — la grammaire s'apprend toute la vie, les phonèmes nouveaux beaucoup moins",
                           "L'accent est génétique",
                           "Ils traduisent tout en secret"],
               "fact": "Joseph Conrad écrivit une prose anglaise parmi les "
                       "plus belles de son siècle et la parla, de l'avis "
                       "général, avec un fort accent polonais toute sa vie. "
                       "La plume n'a pas d'accent."},
        "pt": {"question": "Porque é que adultos que dominam perfeitamente a gramática de uma língua mantêm o sotaque?",
               "options": ["Preguiça",
                           "As categorias de som e os hábitos motores da primeira língua ficam gravados — a gramática aprende-se a vida toda; fonemas novos, muito menos",
                           "O sotaque é genético",
                           "Traduzem tudo em segredo"],
               "fact": "Joseph Conrad escreveu prosa inglesa das melhores "
                       "do seu século e falou-a, por todos os relatos, com "
                       "forte sotaque polaco a vida inteira. A caneta não "
                       "tem sotaque."},
        "ru": {"question": "Почему взрослые, в совершенстве освоившие грамматику языка, всё равно сохраняют акцент?",
               "options": ["Из лени",
                           "Звуковые категории и моторика первого языка врезаны глубоко: грамматика учится всю жизнь, новые фонемы — куда хуже",
                           "Акцент передаётся генетически",
                           "Они втайне всё переводят"],
               "fact": "Джозеф Конрад писал английскую прозу из лучших в "
                       "своём веке, а говорил по-английски, по всем "
                       "свидетельствам, с сильным польским акцентом до "
                       "конца жизни. У пера акцента нет."},
        "ar": {"question": "لماذا يحتفظ الكبار الذين أتقنوا قواعد لغةٍ إتقانًا تامًا بلكنتهم؟",
               "options": ["كسلًا",
                           "فئات الأصوات وعادات النطق الحركية للغة الأولى راسخة عميقًا — فالقواعد تُتعلم مدى الحياة أما الأصوات الجديدة فأعسر بكثير",
                           "اللكنة وراثية",
                           "إنهم يترجمون كل شيء سرًّا"],
               "fact": "كتب جوزيف كونراد نثرًا إنجليزيًا من أرقى نثر قرنه، "
                       "وظل بحسب كل الشهادات يتكلمها بلكنة بولندية ثقيلة "
                       "طوال حياته. القلم لا لكنة له."},
    },
    {
        "answer": 2,
        "en": {"question": "How much of ordinary written English is just the word “the”?",
               "options": ["About 0.1%", "About 1%", "About 6–7% — the most common word is startlingly dominant", "About 20%"],
               "fact": "Word frequencies follow Zipf's law: the second "
                       "word is about half as common as the first, the "
                       "third a third, and a long tail of words occurs "
                       "once. It holds in every language tested — nobody "
                       "fully knows why."},
        "es": {"question": "¿Qué parte del español escrito corriente es solo la palabra “de”?",
               "options": ["Cerca del 0,1%", "Cerca del 1%", "Cerca del 5–7%: la palabra más común domina de forma asombrosa", "Cerca del 20%"],
               "fact": "Las frecuencias siguen la ley de Zipf: la segunda "
                       "palabra es la mitad de común que la primera, la "
                       "tercera un tercio, y una larga cola aparece una "
                       "sola vez. Se cumple en todas las lenguas "
                       "estudiadas — nadie sabe del todo por qué."},
        "fr": {"question": "Quelle part du français écrit ordinaire revient au seul mot « de » ?",
               "options": ["Environ 0,1 %", "Environ 1 %", "Environ 5–7 % — le mot le plus fréquent domine de façon saisissante", "Environ 20 %"],
               "fact": "Les fréquences suivent la loi de Zipf : le "
                       "deuxième mot est deux fois moins fréquent que le "
                       "premier, le troisième trois fois moins, et une "
                       "longue traîne n'apparaît qu'une fois. Cela vaut "
                       "pour toutes les langues testées — nul ne sait tout "
                       "à fait pourquoi."},
        "pt": {"question": "Que parte do português escrito corrente é só a palavra “de”?",
               "options": ["Cerca de 0,1%", "Cerca de 1%", "Cerca de 5–7% — a palavra mais comum domina de forma espantosa", "Cerca de 20%"],
               "fact": "As frequências seguem a lei de Zipf: a segunda "
                       "palavra é metade tão comum como a primeira, a "
                       "terceira um terço, e uma longa cauda aparece uma só "
                       "vez. Vale em todas as línguas testadas — ninguém "
                       "sabe bem porquê."},
        "ru": {"question": "Какую долю обычного русского текста занимает один только предлог «в»?",
               "options": ["Около 0,1%", "Около 1%", "Около 4–6% — самое частое слово поразительно доминирует", "Около 20%"],
               "fact": "Частоты слов подчиняются закону Ципфа: второе слово "
                       "вдвое реже первого, третье — втрое, а длинный хвост "
                       "встречается по одному разу. Это верно для всех "
                       "проверенных языков — и никто до конца не знает "
                       "почему."},
        "ar": {"question": "كم تبلغ حصة كلمة “في” وحدها من النص العربي العادي تقريبًا؟",
               "options": ["نحو 0.1%", "نحو 1%", "نحو 3–6% — الكلمة الأكثر شيوعًا تهيمن هيمنة مدهشة", "نحو 20%"],
               "fact": "تخضع تواترات الكلمات لقانون زيف: الكلمة الثانية "
                       "نصف شيوع الأولى، والثالثة ثلثها، وذيل طويل من "
                       "الكلمات لا يرد إلا مرة. ويصدق هذا على كل لغة "
                       "اختُبرت — ولا أحد يعلم السبب تمام العلم."},
    },
    {
        "answer": 0,
        "en": {"question": "Spanish is spoken with more syllables per second than English. Does it deliver information faster?",
               "options": ["No — faster languages pack less into each syllable, and the information rate comes out similar",
                           "Yes, much faster",
                           "No, much slower",
                           "It delivers no information"],
               "fact": "Cross-language studies keep landing on the same "
                       "trade-off: Japanese and Spanish sprint through "
                       "light syllables, English and Mandarin walk with "
                       "heavy ones, and the bits per second converge. "
                       "Languages find the same channel capacity by "
                       "different routes."},
        "es": {"question": "El español se habla con más sílabas por segundo que el inglés. ¿Transmite la información más rápido?",
               "options": ["No: las lenguas rápidas meten menos en cada sílaba, y la tasa de información acaba pareja",
                           "Sí, mucho más rápido",
                           "No, mucho más lento",
                           "No transmite información"],
               "fact": "Los estudios comparados topan una y otra vez con "
                       "el mismo canje: el japonés y el español corren con "
                       "sílabas ligeras, el inglés y el chino caminan con "
                       "sílabas densas, y los bits por segundo convergen. "
                       "Las lenguas llegan a la misma capacidad por rutas "
                       "distintas."},
        "fr": {"question": "L'espagnol se parle avec plus de syllabes par seconde que l'anglais. Livre-t-il l'information plus vite ?",
               "options": ["Non — les langues rapides mettent moins dans chaque syllabe, et le débit d'information s'équilibre",
                           "Oui, bien plus vite",
                           "Non, bien plus lentement",
                           "Il ne livre aucune information"],
               "fact": "Les études comparées retombent toujours sur le "
                       "même troc : le japonais et l'espagnol sprintent en "
                       "syllabes légères, l'anglais et le mandarin marchent "
                       "en syllabes denses, et les bits par seconde "
                       "convergent. Les langues trouvent la même capacité "
                       "de canal par des chemins différents."},
        "pt": {"question": "O espanhol fala-se com mais sílabas por segundo do que o inglês. Entrega a informação mais depressa?",
               "options": ["Não — as línguas rápidas põem menos em cada sílaba, e a taxa de informação sai parecida",
                           "Sim, muito mais depressa",
                           "Não, muito mais devagar",
                           "Não entrega informação nenhuma"],
               "fact": "Os estudos comparados batem sempre na mesma troca: "
                       "o japonês e o espanhol correm em sílabas leves, o "
                       "inglês e o mandarim caminham em sílabas densas, e "
                       "os bits por segundo convergem. As línguas chegam à "
                       "mesma capacidade por rotas diferentes."},
        "ru": {"question": "В испанском больше слогов в секунду, чем в английском. Значит ли это, что он передаёт информацию быстрее?",
               "options": ["Нет — быстрые языки кладут в каждый слог меньше, и скорость информации выходит сходной",
                           "Да, гораздо быстрее",
                           "Нет, гораздо медленнее",
                           "Он не передаёт информации"],
               "fact": "Сравнительные исследования упираются в один и тот "
                       "же размен: японский и испанский бегут лёгкими "
                       "слогами, английский и китайский шагают тяжёлыми, а "
                       "биты в секунду сходятся. Языки выходят на одну "
                       "пропускную способность разными путями."},
        "ar": {"question": "تُنطق الإسبانية بمقاطع في الثانية أكثر من الإنجليزية. فهل تنقل المعلومات أسرع؟",
               "options": ["لا — اللغات السريعة تضع في كل مقطع أقل، فيتقارب معدل المعلومات",
                           "نعم، أسرع بكثير",
                           "لا، أبطأ بكثير",
                           "لا تنقل معلومات"],
               "fact": "تصل الدراسات المقارنة دومًا إلى المقايضة نفسها: "
                       "اليابانية والإسبانية تعدوان بمقاطع خفيفة، "
                       "والإنجليزية والصينية تمشيان بمقاطع كثيفة، ويتقارب "
                       "عدد البتات في الثانية. تبلغ اللغات سعة القناة "
                       "ذاتها من طرق شتى."},
    },
    {
        "answer": 1,
        "en": {"question": "In the McGurk effect, watching lips say “ga” while the audio plays “ba” makes most people hear…",
               "options": ["“ba”, as the audio says", "“da” — the brain splits the difference between eye and ear", "silence", "both sounds at once"],
               "fact": "Speech perception is audiovisual: the brain fuses "
                       "what it sees with what it hears without asking "
                       "permission. It's part of why phone calls in a "
                       "second language are so much harder than "
                       "face-to-face talk."},
        "es": {"question": "En el efecto McGurk, ver unos labios decir “ga” mientras el audio reproduce “ba” hace que la mayoría oiga…",
               "options": ["“ba”, como dice el audio", "“da”: el cerebro parte la diferencia entre ojo y oído", "silencio", "los dos sonidos a la vez"],
               "fact": "Percibir el habla es audiovisual: el cerebro "
                       "fusiona lo que ve con lo que oye sin pedir permiso. "
                       "En parte por eso las llamadas en una segunda lengua "
                       "cuestan tanto más que la conversación cara a cara."},
        "fr": {"question": "Dans l'effet McGurk, regarder des lèvres dire « ga » pendant que l'audio joue « ba » fait entendre à la plupart des gens…",
               "options": ["« ba », comme le dit l'audio", "« da » — le cerveau coupe la poire en deux entre l'œil et l'oreille", "le silence", "les deux sons à la fois"],
               "fact": "La perception de la parole est audiovisuelle : le "
                       "cerveau fusionne ce qu'il voit et ce qu'il entend "
                       "sans demander la permission. C'est en partie "
                       "pourquoi téléphoner dans une langue seconde est "
                       "tellement plus dur que parler face à face."},
        "pt": {"question": "No efeito McGurk, ver lábios a dizer “ga” enquanto o áudio toca “ba” faz a maioria ouvir…",
               "options": ["“ba”, como diz o áudio", "“da” — o cérebro divide a diferença entre olho e ouvido", "silêncio", "os dois sons ao mesmo tempo"],
               "fact": "A perceção da fala é audiovisual: o cérebro funde o "
                       "que vê com o que ouve sem pedir licença. É em parte "
                       "por isso que os telefonemas numa segunda língua "
                       "custam tanto mais do que a conversa cara a cara."},
        "ru": {"question": "В эффекте Мак-Гурка, когда губы на видео говорят «га», а звук — «ба», большинство слышит…",
               "options": ["«ба», как в записи", "«да» — мозг делит разницу между глазом и ухом", "тишину", "оба звука сразу"],
               "fact": "Восприятие речи аудиовизуально: мозг сплавляет "
                       "увиденное с услышанным, не спрашивая разрешения. "
                       "Отчасти поэтому телефонный разговор на чужом языке "
                       "настолько труднее беседы лицом к лицу."},
        "ar": {"question": "في تأثير مكغورك، مشاهدة شفتين تقولان “غا” بينما الصوت يقول “با” تجعل معظم الناس يسمعون…",
               "options": ["“با” كما في التسجيل", "“دا” — يقسم الدماغ الفرق بين العين والأذن", "صمتًا", "الصوتين معًا"],
               "fact": "إدراك الكلام سمعي-بصري: يدمج الدماغ ما يراه بما "
                       "يسمعه دون استئذان. وهذا بعض سبب كون المكالمات "
                       "الهاتفية بلغة ثانية أشق كثيرًا من الحديث وجهًا "
                       "لوجه."},
    },
    {
        "answer": 2,
        "en": {"question": "Users of sign languages report a version of “tip of the tongue”. What is it called?",
               "options": ["Tip of the eye", "Hand freeze", "“Tip of the fingers” — knowing the sign but failing to retrieve it", "Sign block"],
               "fact": "Signers even get partial retrieval — recalling the "
                       "handshape but not the movement — exactly parallel "
                       "to remembering a word's first letter. The mental "
                       "dictionary works alike whether words are spoken or "
                       "signed."},
        "es": {"question": "Quienes usan lenguas de señas describen una versión del “en la punta de la lengua”. ¿Cómo se llama?",
               "options": ["En la punta del ojo", "Congelación de manos", "“En la punta de los dedos”: sabes el signo pero no logras recuperarlo", "Bloqueo de señas"],
               "fact": "Los señantes incluso recuperan a medias — recuerdan "
                       "la forma de la mano pero no el movimiento — en "
                       "paralelo exacto a recordar la primera letra de una "
                       "palabra. El diccionario mental funciona igual, "
                       "hablado o señado."},
        "fr": {"question": "Les locuteurs des langues des signes décrivent une version du « mot sur le bout de la langue ». Comment l'appelle-t-on ?",
               "options": ["Sur le bout de l'œil", "Le gel des mains", "« Sur le bout des doigts » — connaître le signe sans parvenir à le retrouver", "Le blocage du signe"],
               "fact": "Les signeurs récupèrent même partiellement — la "
                       "configuration de la main mais pas le mouvement — en "
                       "parallèle exact du souvenir de la première lettre "
                       "d'un mot. Le dictionnaire mental fonctionne pareil, "
                       "parlé ou signé."},
        "pt": {"question": "Os utilizadores de línguas de sinais relatam uma versão do “debaixo da língua”. Como se chama?",
               "options": ["Na ponta do olho", "Congelamento das mãos", "“Na ponta dos dedos” — saber o sinal mas não conseguir recuperá-lo", "Bloqueio de sinal"],
               "fact": "Os sinalizantes até recuperam parcialmente — "
                       "lembram a forma da mão mas não o movimento — em "
                       "paralelo exato a lembrar a primeira letra de uma "
                       "palavra. O dicionário mental funciona igual, falado "
                       "ou sinalizado."},
        "ru": {"question": "Носители жестовых языков описывают свою версию «вертится на языке». Как она называется?",
               "options": ["«Вертится на глазу»", "Замирание рук", "«Вертится на пальцах» — жест знаком, но не извлекается", "Жестовый блок"],
               "fact": "У жестикулирующих бывает даже частичное "
                       "припоминание — форма кисти без движения — в точной "
                       "параллели к «помню первую букву». Ментальный "
                       "словарь устроен одинаково, звучит слово или "
                       "показывается."},
        "ar": {"question": "يصف مستخدمو لغات الإشارة نسختهم من “على طرف اللسان”. ماذا تسمى؟",
               "options": ["على طرف العين", "تجمّد اليدين", "“على أطراف الأصابع” — تعرف الإشارة ولا تستطيع استحضارها", "انسداد الإشارة"],
               "fact": "بل يحدث لهم استرجاع جزئي — يتذكرون شكل الكف دون "
                       "الحركة — في موازاة تامة لتذكر أول حرف من الكلمة. "
                       "فالمعجم الذهني يعمل بالطريقة نفسها، نُطقت الكلمة أو "
                       "أُشيرت."},
    },
    {
        "answer": 0,
        "en": {"question": "Shown a spiky shape and a round blob and the names “kiki” and “bouba”, what do people everywhere do?",
               "options": ["Call the spiky one kiki and the round one bouba — sound carries a feel of shape",
                           "Choose at random",
                           "Refuse to answer",
                           "Reverse it in most cultures"],
               "fact": "The match holds across continents and in toddlers. "
                       "Sound symbolism is real but soft — it bends "
                       "vocabulary gently, it doesn't dictate it, which is "
                       "why words for “knife” still differ everywhere."},
        "es": {"question": "Ante una forma puntiaguda y una redondeada, y los nombres “kiki” y “bouba”, ¿qué hace la gente en todas partes?",
               "options": ["Llama kiki a la puntiaguda y bouba a la redonda: el sonido lleva una sensación de forma",
                           "Elige al azar",
                           "Se niega a contestar",
                           "Lo invierte en la mayoría de las culturas"],
               "fact": "La correspondencia se mantiene entre continentes y "
                       "en niños pequeños. El simbolismo fónico es real "
                       "pero suave: inclina el vocabulario, no lo dicta — "
                       "por eso “cuchillo” sigue diciéndose distinto en "
                       "cada lengua."},
        "fr": {"question": "Devant une forme piquante et une forme ronde, et les noms « kiki » et « bouba », que font les gens partout ?",
               "options": ["Ils appellent kiki la piquante et bouba la ronde — le son porte une sensation de forme",
                           "Ils choisissent au hasard",
                           "Ils refusent de répondre",
                           "Ils inversent dans la plupart des cultures"],
               "fact": "L'appariement tient d'un continent à l'autre et "
                       "chez les tout-petits. Le symbolisme sonore est réel "
                       "mais doux — il incline le vocabulaire sans le "
                       "dicter, et c'est pourquoi « couteau » se dit "
                       "encore autrement partout."},
        "pt": {"question": "Perante uma forma bicuda e uma redonda, e os nomes “kiki” e “bouba”, o que fazem as pessoas em todo o lado?",
               "options": ["Chamam kiki à bicuda e bouba à redonda — o som carrega uma sensação de forma",
                           "Escolhem ao acaso",
                           "Recusam-se a responder",
                           "Invertem na maioria das culturas"],
               "fact": "A correspondência mantém-se entre continentes e em "
                       "crianças pequenas. O simbolismo sonoro é real mas "
                       "suave — inclina o vocabulário, não o dita, e por "
                       "isso “faca” continua a dizer-se diferente em "
                       "cada língua."},
        "ru": {"question": "Показав людям колючую фигуру и округлую кляксу и имена «кики» и «буба», что обнаруживают повсюду?",
               "options": ["Колючую зовут кики, округлую — буба: звук несёт ощущение формы",
                           "Выбирают наугад",
                           "Отказываются отвечать",
                           "В большинстве культур наоборот"],
               "fact": "Соответствие держится на всех континентах и у "
                       "малышей. Звукосимволизм реален, но мягок — он "
                       "подталкивает словарь, а не диктует его, потому "
                       "«нож» всё равно всюду звучит по-разному."},
        "ar": {"question": "أمام شكل مدبب وآخر مستدير وباسمي “كيكي” و“بوبا”، ماذا يفعل الناس في كل مكان؟",
               "options": ["يسمّون المدبب كيكي والمستدير بوبا — فالصوت يحمل إحساسًا بالشكل",
                           "يختارون عشوائيًا",
                           "يرفضون الإجابة",
                           "يعكسون في معظم الثقافات"],
               "fact": "يثبت هذا التوافق عبر القارات وعند الأطفال الصغار. "
                       "الرمزية الصوتية حقيقية لكنها لطيفة — تُميل المعجم "
                       "ولا تمليه، ولهذا ما زالت كلمة “سكين” تختلف من "
                       "لغة إلى لغة."},
    },
    {
        "answer": 1,
        "en": {"question": "It pours in English as “cats and dogs”. What falls in French and Spanish?",
               "options": ["Also cats and dogs — the image is universal",
                           "Ropes in French (des cordes), pitchers in Spanish (a cántaros)",
                           "Frogs in both",
                           "Nothing — the idiom can't be said"],
               "fact": "Idioms almost never survive word-for-word travel: "
                       "Russians pour “as from a bucket”, Germans get "
                       "“string rain”, and in Yoruba heavy rain simply "
                       "gets its own verb. Translate the image, not the "
                       "words."},
        "es": {"question": "En inglés llueve “a gatos y perros”. ¿Qué cae en francés y en español?",
               "options": ["También gatos y perros: la imagen es universal",
                           "Cuerdas en francés (des cordes), cántaros en español",
                           "Ranas en ambos",
                           "Nada: el modismo no puede decirse"],
               "fact": "Los modismos casi nunca sobreviven al viaje "
                       "palabra por palabra: los rusos vierten “como de "
                       "un cubo”, los alemanes reciben “lluvia de "
                       "cuerdas”, y en yoruba la lluvia fuerte tiene "
                       "sencillamente su propio verbo. Traduce la imagen, "
                       "no las palabras."},
        "fr": {"question": "En anglais, il pleut « des chats et des chiens ». Que tombe-t-il en français et en espagnol ?",
               "options": ["Aussi des chats et des chiens — l'image est universelle",
                           "Des cordes en français, des cruches en espagnol (a cántaros)",
                           "Des grenouilles dans les deux",
                           "Rien — l'idiome ne peut pas se dire"],
               "fact": "Les idiomes survivent rarement au voyage mot à "
                       "mot : les Russes versent « comme d'un seau », "
                       "les Allemands reçoivent une « pluie de "
                       "ficelles », et en yoruba la grosse pluie a "
                       "simplement son propre verbe. Traduisez l'image, pas "
                       "les mots."},
        "pt": {"question": "Em inglês chove “gatos e cães”. O que cai em francês e em espanhol?",
               "options": ["Também gatos e cães — a imagem é universal",
                           "Cordas em francês (des cordes), cântaros em espanhol",
                           "Rãs em ambos",
                           "Nada — o idiomatismo não se pode dizer"],
               "fact": "Os idiomatismos quase nunca sobrevivem à viagem "
                       "palavra a palavra: os russos despejam “como de um "
                       "balde”, os alemães apanham “chuva de cordéis”, "
                       "e em iorubá a chuva forte tem simplesmente o seu "
                       "próprio verbo. Traduz-se a imagem, não as palavras."},
        "ru": {"question": "По-английски льёт «кошками и собаками». Что льётся по-французски и по-испански?",
               "options": ["Тоже кошки и собаки — образ универсален",
                           "Верёвки во французском (des cordes), кувшины в испанском (a cántaros)",
                           "Лягушки в обоих",
                           "Никак — идиому нельзя сказать"],
               "fact": "Идиомы почти никогда не переживают дословного "
                       "переезда: по-русски льёт «как из ведра», у "
                       "немцев «дождь верёвками», а в йоруба у ливня "
                       "просто свой глагол. Переводите образ, а не слова."},
        "ar": {"question": "بالإنجليزية تمطر “قططًا وكلابًا”. فماذا يسقط بالفرنسية والإسبانية؟",
               "options": ["قطط وكلاب أيضًا — الصورة كونية",
                           "حبال بالفرنسية (des cordes) وجِرار بالإسبانية (a cántaros)",
                           "ضفادع في كلتيهما",
                           "لا شيء — التعبير لا يقال"],
               "fact": "قلّما تنجو التعابير من السفر كلمةً كلمة: الروس "
                       "يسكبون “كما من دلو”، والألمان يتلقون “مطر "
                       "خيوط”، والعربية تقول “تمطر كأفواه القِرَب”. "
                       "ترجِم الصورةَ لا الكلمات."},
    },
    {
        "answer": 2,
        "en": {"question": "French vous, Spanish usted, Russian вы — what did English do with its polite “you”?",
               "options": ["Never had one",
                           "Still uses it daily",
                           "Kept ONLY the polite form — “thou” was the informal one, and it died",
                           "Merged it into “y'all”"],
               "fact": "So English politeness went underground: it now "
                       "lives in phrasing — “could you possibly” — "
                       "instead of pronouns. Quakers kept “thee” for "
                       "centuries precisely to refuse the social ladder."},
        "es": {"question": "El francés vous, el español usted, el ruso вы… ¿qué hizo el inglés con su “tú/usted”?",
               "options": ["Nunca tuvo distinción",
                           "Todavía la usa a diario",
                           "Conservó SOLO la forma cortés: “thou” era el tuteo, y murió",
                           "La fundió en “y'all”"],
               "fact": "La cortesía inglesa se volvió subterránea: ahora "
                       "vive en el fraseo — “could you possibly” — en "
                       "vez de en los pronombres. Los cuáqueros mantuvieron "
                       "“thee” durante siglos precisamente para rechazar "
                       "la escalera social. Curioso: usted nació de "
                       "“vuestra merced”."},
        "fr": {"question": "Français vous, espagnol usted, russe вы — qu'a fait l'anglais de son vouvoiement ?",
               "options": ["Il n'en a jamais eu",
                           "Il s'en sert encore tous les jours",
                           "Il n'a gardé QUE la forme polie — « thou » était le tutoiement, et il est mort",
                           "Il l'a fondu dans « y'all »"],
               "fact": "La politesse anglaise est passée sous terre : elle "
                       "vit désormais dans la tournure — « could you "
                       "possibly » — plutôt que dans les pronoms. Les "
                       "quakers ont gardé « thee » des siècles, "
                       "précisément pour refuser l'échelle sociale."},
        "pt": {"question": "O francês vous, o espanhol usted, o russo вы — o que fez o inglês ao seu “tu/você”?",
               "options": ["Nunca teve distinção",
                           "Ainda a usa todos os dias",
                           "Guardou SÓ a forma de cortesia — “thou” era o tratamento íntimo, e morreu",
                           "Fundiu-a em “y'all”"],
               "fact": "A cortesia inglesa passou à clandestinidade: vive "
                       "agora na frase — “could you possibly” — em vez "
                       "de nos pronomes. Os quakers guardaram “thee” "
                       "séculos, precisamente para recusar a escada social. "
                       "Curioso: você nasceu de “vossa mercê”."},
        "ru": {"question": "Французское vous, испанское usted, русское «вы» — а что сделал английский со своим вежливым «вы»?",
               "options": ["У него его никогда не было",
                           "До сих пор пользуется каждый день",
                           "Оставил ТОЛЬКО вежливую форму: «thou» было «ты» — и умерло",
                           "Слил его в «y'all»"],
               "fact": "Английская вежливость ушла в подполье: теперь она "
                       "живёт в оборотах — «could you possibly» — а не в "
                       "местоимениях. Квакеры веками держались за "
                       "«thee» именно затем, чтобы отвергнуть социальную "
                       "лестницу."},
        "ar": {"question": "الفرنسية vous والإسبانية usted والروسية вы — فماذا فعلت الإنجليزية بضمير التبجيل عندها؟",
               "options": ["لم يكن عندها قط",
                           "ما زالت تستعمله يوميًا",
                           "أبقت صيغة التبجيل وحدها — كانت “thou” للمخاطبة الحميمة فماتت",
                           "أذابته في “y'all”"],
               "fact": "فذهب التهذيب الإنجليزي إلى السر: يسكن اليوم في "
                       "الصياغة — “could you possibly” — لا في "
                       "الضمائر. وتمسّك الكويكرز بـ“thee” قرونًا رفضًا "
                       "للسلّم الاجتماعي بالذات."},
    },
    {
        "answer": 1,
        "en": {"question": "Speakers of Guugu Yimithirr in Australia don't say “left” or “right”. How do they give directions?",
               "options": ["By pointing only",
                           "By compass points, always: “your north hand”, “move the cup south”",
                           "By naming landmarks",
                           "They avoid talking about space"],
               "fact": "Speaking it requires knowing where north is at all "
                       "times, indoors or out — and speakers do, running a "
                       "constant mental compass that stuns researchers. "
                       "Several Aboriginal and Mayan languages work the "
                       "same way."},
        "es": {"question": "Los hablantes de guugu yimithirr, en Australia, no dicen “izquierda” ni “derecha”. ¿Cómo dan indicaciones?",
               "options": ["Solo señalando",
                           "Con puntos cardinales, siempre: “tu mano norte”, “mueve la taza al sur”",
                           "Nombrando puntos de referencia",
                           "Evitan hablar del espacio"],
               "fact": "Hablarlo exige saber dónde está el norte en todo "
                       "momento, bajo techo o al aire libre — y los "
                       "hablantes lo saben, con una brújula mental continua "
                       "que asombra a los investigadores. Varias lenguas "
                       "aborígenes y mayas funcionan igual."},
        "fr": {"question": "Les locuteurs du guugu yimithirr, en Australie, ne disent ni « gauche » ni « droite ». Comment donnent-ils des directions ?",
               "options": ["Uniquement en pointant",
                           "Par les points cardinaux, toujours : « ta main nord », « pousse la tasse vers le sud »",
                           "En nommant des repères",
                           "Ils évitent de parler de l'espace"],
               "fact": "Le parler exige de savoir où est le nord à tout "
                       "instant, dedans comme dehors — et les locuteurs le "
                       "savent, boussole mentale toujours allumée, à la "
                       "stupeur des chercheurs. Plusieurs langues "
                       "aborigènes et mayas font pareil."},
        "pt": {"question": "Os falantes de guugu yimithirr, na Austrália, não dizem “esquerda” nem “direita”. Como dão indicações?",
               "options": ["Só apontando",
                           "Por pontos cardeais, sempre: “a tua mão norte”, “empurra a chávena para sul”",
                           "Nomeando pontos de referência",
                           "Evitam falar do espaço"],
               "fact": "Falá-lo exige saber onde fica o norte a toda a "
                       "hora, dentro ou fora de casa — e os falantes sabem, "
                       "com uma bússola mental contínua que espanta os "
                       "investigadores. Várias línguas aborígenes e maias "
                       "funcionam assim."},
        "ru": {"question": "Носители языка гуугу-йимитир в Австралии не говорят «слева» и «справа». Как они объясняют дорогу?",
               "options": ["Только жестами",
                           "Всегда по сторонам света: «твоя северная рука», «подвинь чашку к югу»",
                           "Называя ориентиры",
                           "Избегают говорить о пространстве"],
               "fact": "Чтобы говорить на нём, нужно всегда знать, где "
                       "север — в помещении и снаружи, — и носители знают, "
                       "нося в голове постоянный компас, поражающий "
                       "исследователей. Так же устроены несколько "
                       "австралийских и майяских языков."},
        "ar": {"question": "متكلمو لغة غوغو ييميثير في أستراليا لا يقولون “يمين” ولا “يسار”. فكيف يدلّون على الاتجاهات؟",
               "options": ["بالإشارة فقط",
                           "بالجهات الأصلية دائمًا: “يدك الشمالية”، “حرّك الكوب جنوبًا”",
                           "بذكر المعالم",
                           "يتجنبون الحديث عن المكان"],
               "fact": "التكلم بها يستلزم معرفة جهة الشمال في كل لحظة، في "
                       "الداخل والخارج — والمتكلمون يعرفونها فعلًا، "
                       "ببوصلة ذهنية دائمة تُدهش الباحثين. وعلى هذا النحو "
                       "تعمل لغات أسترالية ومايانية عدة."},
    },
    {
        "answer": 2,
        "en": {"question": "How does French say 97?",
               "options": ["Simply “ninety-seven”",
                           "“Ninety and seven”",
                           "“Four-twenty-seventeen” (quatre-vingt-dix-sept) — a leftover of counting by twenties",
                           "It borrows the English word"],
               "fact": "Twenty-counting survives at the edges of Europe: "
                       "Danish halvfems packs it tighter still, Basque and "
                       "Georgian count by twenties throughout — and "
                       "Belgian and Swiss French quietly say "
                       "nonante-sept instead."},
        "es": {"question": "¿Cómo dice el francés 97?",
               "options": ["Simplemente “noventa y siete”",
                           "“Noventa con siete”",
                           "“Cuatro-veintes-diecisiete” (quatre-vingt-dix-sept): un resto de contar de veinte en veinte",
                           "Toma prestada la palabra inglesa"],
               "fact": "El conteo por veintenas sobrevive en los bordes de "
                       "Europa: el danés halvfems lo comprime aún más, el "
                       "vasco y el georgiano cuentan por veintes de "
                       "principio a fin — y el francés de Bélgica y Suiza "
                       "dice tranquilamente nonante-sept."},
        "fr": {"question": "Comment le français de France dit-il 97 ?",
               "options": ["Simplement « nonante-sept », partout",
                           "« Nonante et sept »",
                           "« Quatre-vingt-dix-sept » — un vestige du compte par vingtaines",
                           "Il emprunte le mot anglais"],
               "fact": "Le compte par vingt survit aux marges de "
                       "l'Europe : le danois halvfems le compresse plus "
                       "fort encore, le basque et le géorgien comptent par "
                       "vingtaines de bout en bout — et les français de "
                       "Belgique et de Suisse disent tranquillement "
                       "nonante-sept."},
        "pt": {"question": "Como diz o francês 97?",
               "options": ["Simplesmente “noventa e sete”",
                           "“Noventa com sete”",
                           "“Quatro-vintes-dezassete” (quatre-vingt-dix-sept) — um resto da contagem de vinte em vinte",
                           "Pede emprestada a palavra inglesa"],
               "fact": "A contagem por vintenas sobrevive nas margens da "
                       "Europa: o dinamarquês halvfems comprime-a ainda "
                       "mais, o basco e o georgiano contam por vintes do "
                       "princípio ao fim — e o francês da Bélgica e da "
                       "Suíça diz tranquilamente nonante-sept."},
        "ru": {"question": "Как французский говорит «97»?",
               "options": ["Просто «девяносто семь»",
                           "«Девяносто и семь»",
                           "«Четырежды-двадцать-семнадцать» (quatre-vingt-dix-sept) — след счёта двадцатками",
                           "Заимствует английское слово"],
               "fact": "Счёт двадцатками выжил по краям Европы: датское "
                       "halvfems сжимает его ещё туже, баскский и "
                       "грузинский считают двадцатками насквозь — а "
                       "бельгийские и швейцарские французы спокойно говорят "
                       "nonante-sept."},
        "ar": {"question": "كيف تقول الفرنسية 97؟",
               "options": ["ببساطة “سبعة وتسعون”",
                           "“تسعون وسبعة”",
                           "“أربع-عشرينات-وسبع-عشرة” (quatre-vingt-dix-sept) — بقيةٌ من العد بالعشرينات",
                           "تستعير الكلمة الإنجليزية"],
               "fact": "يعيش العد بالعشرينات على أطراف أوروبا: الدنماركية "
                       "halvfems تضغطه أشد، والباسكية والجورجية تعدان "
                       "بالعشرينات من أولها إلى آخرها — وفرنسيةُ بلجيكا "
                       "وسويسرا تقول بهدوء nonante-sept."},
    },
    {
        "answer": 0,
        "en": {"question": "When a pronunciation starts changing, who does sociolinguistics consistently find leading it?",
               "options": ["Young women, generation after generation",
                           "Elderly men",
                           "Radio announcers",
                           "Teachers"],
               "fact": "From Labov's department-store vowels on, study "
                       "after study finds women about a generation ahead "
                       "on changes that later become the standard. "
                       "Yesterday's “sloppy speech” complaint is "
                       "tomorrow's dictionary entry."},
        "es": {"question": "Cuando una pronunciación empieza a cambiar, ¿quién encabeza el cambio según la sociolingüística, una y otra vez?",
               "options": ["Las mujeres jóvenes, generación tras generación",
                           "Los hombres mayores",
                           "Los locutores de radio",
                           "Los maestros"],
               "fact": "Desde las vocales de los grandes almacenes de "
                       "Labov, estudio tras estudio encuentra a las mujeres "
                       "una generación por delante en los cambios que luego "
                       "serán la norma. La queja de hoy por “hablar "
                       "descuidado” es la entrada de diccionario de "
                       "mañana."},
        "fr": {"question": "Quand une prononciation commence à changer, qui la sociolinguistique trouve-t-elle systématiquement en tête ?",
               "options": ["Les jeunes femmes, génération après génération",
                           "Les hommes âgés",
                           "Les présentateurs de radio",
                           "Les enseignants"],
               "fact": "Depuis les voyelles de grands magasins de Labov, "
                       "étude après étude trouve les femmes une génération "
                       "en avance sur les changements qui deviendront la "
                       "norme. La plainte d'hier sur le « parler "
                       "relâché » est l'entrée de dictionnaire de "
                       "demain."},
        "pt": {"question": "Quando uma pronúncia começa a mudar, quem é que a sociolinguística encontra sempre à frente?",
               "options": ["As mulheres jovens, geração após geração",
                           "Os homens idosos",
                           "Os locutores de rádio",
                           "Os professores"],
               "fact": "Desde as vogais de armazém de Labov, estudo após "
                       "estudo encontra as mulheres uma geração à frente "
                       "nas mudanças que depois viram norma. A queixa de "
                       "ontem sobre “fala desleixada” é a entrada de "
                       "dicionário de amanhã."},
        "ru": {"question": "Когда произношение начинает меняться, кого социолингвистика раз за разом находит во главе перемен?",
               "options": ["Молодых женщин, поколение за поколением",
                           "Пожилых мужчин",
                           "Радиоведущих",
                           "Учителей"],
               "fact": "Начиная с лабовских гласных в универмагах, "
                       "исследование за исследованием находит женщин на "
                       "поколение впереди в изменениях, которые потом "
                       "станут нормой. Вчерашняя жалоба на «небрежную "
                       "речь» — завтрашняя словарная статья."},
        "ar": {"question": "حين يبدأ نطقٌ ما بالتغير، من الذي يجده علم اللغة الاجتماعي في طليعته مرة بعد مرة؟",
               "options": ["الشابات، جيلًا بعد جيل",
                           "كبار السن من الرجال",
                           "مذيعو الراديو",
                           "المعلمون"],
               "fact": "منذ دراسة لابوف لصوائت المتاجر الكبرى، تجد الدراسات "
                       "المرأةَ متقدمةً جيلًا كاملًا في التغيرات التي تصير "
                       "لاحقًا هي المعيار. شكوى الأمس من “الكلام "
                       "المتراخي” هي مدخل معجم الغد."},
    },
    {
        "answer": 1,
        "en": {"question": "“Toilet” replaced ruder words, then needed replacing by “bathroom”, then “restroom”. What is this cycle called?",
               "options": ["Spelling reform",
                           "The euphemism treadmill — the polite word absorbs the taboo and needs replacing again",
                           "Semantic bleaching",
                           "Word inflation"],
               "fact": "The taboo outruns every new label, because it "
                       "sticks to the THING, not the word. “Toilet” "
                       "itself began as delicate French for a little cloth. "
                       "Job titles and medical terms ride the same "
                       "treadmill."},
        "es": {"question": "“Retrete” cedió a “váter”, luego a “baño”, luego a “aseo”. ¿Cómo se llama este ciclo?",
               "options": ["Reforma ortográfica",
                           "La noria del eufemismo: la palabra fina absorbe el tabú y hay que reemplazarla otra vez",
                           "Desgaste semántico",
                           "Inflación léxica"],
               "fact": "El tabú alcanza a cada etiqueta nueva, porque se "
                       "pega a la COSA, no a la palabra. “Retrete” "
                       "empezó siendo un delicado galicismo para un "
                       "cuartito apartado. Los títulos laborales y los "
                       "términos médicos giran en la misma noria."},
        "fr": {"question": "« Lieux d'aisances » a cédé à « cabinets », puis à « toilettes ». Comment s'appelle ce cycle ?",
               "options": ["La réforme orthographique",
                           "Le tapis roulant de l'euphémisme — le mot poli absorbe le tabou et doit être remplacé à son tour",
                           "Le blanchiment sémantique",
                           "L'inflation lexicale"],
               "fact": "Le tabou rattrape chaque étiquette neuve, parce "
                       "qu'il colle à la CHOSE, pas au mot. "
                       "« Toilette » a commencé en délicat diminutif de "
                       "toile. Les intitulés de métiers et les termes "
                       "médicaux tournent sur le même tapis."},
        "pt": {"question": "“Retrete” cedeu a “casa de banho”, depois a “lavabo”, depois a “WC”. Como se chama este ciclo?",
               "options": ["Reforma ortográfica",
                           "A passadeira do eufemismo — a palavra educada absorve o tabu e precisa de ser substituída outra vez",
                           "Desbotamento semântico",
                           "Inflação lexical"],
               "fact": "O tabu apanha cada rótulo novo, porque se cola à "
                       "COISA, não à palavra. “Toilette” começou por "
                       "ser um delicado diminutivo francês de tecido. Os "
                       "títulos profissionais e os termos médicos andam na "
                       "mesma passadeira."},
        "ru": {"question": "«Нужник» сменился «уборной», та — «туалетом», тот — «санузлом». Как называется этот цикл?",
               "options": ["Орфографическая реформа",
                           "Беговая дорожка эвфемизмов: вежливое слово впитывает табу, и его снова надо менять",
                           "Семантическое выцветание",
                           "Словесная инфляция"],
               "fact": "Табу догоняет каждый новый ярлык, потому что "
                       "липнет к ВЕЩИ, а не к слову: «туалет» начинался "
                       "как изящное французское словцо о наряде. По той же "
                       "дорожке бегут названия профессий и медицинские "
                       "термины."},
        "ar": {"question": "“بيت الخلاء” أفسح لـ“المرحاض”، ثم “دورة المياه”، ثم “الحمّام”. ماذا تسمى هذه الدورة؟",
               "options": ["إصلاح إملائي",
                           "دولاب التلطيف — تمتص الكلمة المهذبة الوصمة فتحتاج بدورها إلى بديل",
                           "بهتان دلالي",
                           "تضخم لفظي"],
               "fact": "تلحق الوصمة بكل تسمية جديدة لأنها تلتصق بالشيء لا "
                       "بالكلمة. و“toilette” نفسها بدأت تصغيرًا فرنسيًا "
                       "رقيقًا لقطعة قماش. وتدور ألقاب المهن والمصطلحات "
                       "الطبية في الدولاب نفسه."},
    },
    {
        "answer": 2,
        "en": {"question": "In Dyirbal, an Australian language, speakers traditionally switched to a special vocabulary when…",
               "options": ["hunting",
                           "singing",
                           "certain in-laws were within earshot — an “avoidance register” with different words for everything",
                           "it rained"],
               "fact": "The “mother-in-law language” kept the same "
                       "grammar but swapped the entire vocabulary — one "
                       "grammar wearing two lexicons. Politeness can run "
                       "deeper than pronouns: whole parallel word-stocks."},
        "es": {"question": "En dyirbal, una lengua australiana, los hablantes cambiaban tradicionalmente a un vocabulario especial cuando…",
               "options": ["cazaban",
                           "cantaban",
                           "ciertos parientes políticos estaban al alcance del oído: un “registro de evitación” con otras palabras para todo",
                           "llovía"],
               "fact": "La “lengua de la suegra” conservaba la misma "
                       "gramática pero cambiaba el vocabulario entero — una "
                       "gramática vistiendo dos léxicos. La cortesía puede "
                       "calar más hondo que los pronombres: vocabularios "
                       "paralelos completos."},
        "fr": {"question": "En dyirbal, langue d'Australie, les locuteurs passaient traditionnellement à un vocabulaire spécial quand…",
               "options": ["ils chassaient",
                           "ils chantaient",
                           "certains beaux-parents étaient à portée d'oreille — un « registre d'évitement » aux mots tous différents",
                           "il pleuvait"],
               "fact": "La « langue de la belle-mère » gardait la même "
                       "grammaire mais changeait tout le lexique — une "
                       "grammaire portant deux vocabulaires. La politesse "
                       "peut aller plus profond que les pronoms : des "
                       "stocks de mots parallèles entiers."},
        "pt": {"question": "Em dyirbal, uma língua australiana, os falantes mudavam tradicionalmente para um vocabulário especial quando…",
               "options": ["caçavam",
                           "cantavam",
                           "certos sogros estavam ao alcance do ouvido — um “registo de evitação” com palavras diferentes para tudo",
                           "chovia"],
               "fact": "A “língua da sogra” mantinha a mesma gramática "
                       "mas trocava o vocabulário inteiro — uma gramática a "
                       "vestir dois léxicos. A cortesia pode ir mais fundo "
                       "do que os pronomes: acervos de palavras paralelos "
                       "completos."},
        "ru": {"question": "В дьирбале, языке Австралии, говорящие по традиции переходили на особый словарь, когда…",
               "options": ["охотились",
                           "пели",
                           "поблизости были определённые свойственники — «регистр избегания» с другими словами для всего",
                           "шёл дождь"],
               "fact": "«Язык тёщи» сохранял ту же грамматику, но менял "
                       "весь словарь — одна грамматика в двух лексиконах. "
                       "Вежливость может уходить глубже местоимений: в "
                       "целые параллельные запасы слов."},
        "ar": {"question": "في الديربالية، وهي لغة أسترالية, كان المتكلمون تقليديًا ينتقلون إلى معجم خاص عندما…",
               "options": ["يصطادون",
                           "يغنّون",
                           "يكون بعض الأصهار على مسمع منهم — “سجل تجنّب” بكلمات مختلفة لكل شيء",
                           "تمطر"],
               "fact": "حافظت “لغة الحماة” على القواعد نفسها لكنها "
                       "بدّلت المعجم كله — قواعد واحدة تلبس معجمين. قد يذهب "
                       "التهذيب أعمق من الضمائر: إلى مخزونات كلمات موازية "
                       "بأكملها."},
    },
    {
        "answer": 1,
        "en": {"question": "In 1980s Nicaragua, deaf children brought together in new schools did something linguists had never watched happen. What?",
               "options": ["They learned Spanish unusually fast",
                           "They CREATED a brand-new language — Nicaraguan Sign Language — in a generation",
                           "They stayed without language",
                           "They adopted American signs wholesale"],
               "fact": "The first cohort built a rough contact code; the "
                       "younger children who received it made it "
                       "grammatical — agreement, verb classes, spatial "
                       "syntax. The strongest live evidence that language "
                       "capacity is born, not taught."},
        "es": {"question": "En la Nicaragua de los años 80, niños sordos reunidos en escuelas nuevas hicieron algo que los lingüistas nunca habían visto ocurrir. ¿Qué?",
               "options": ["Aprendieron español inusualmente rápido",
                           "CREARON una lengua nueva — la lengua de señas nicaragüense — en una generación",
                           "Se quedaron sin lengua",
                           "Adoptaron en bloque las señas americanas"],
               "fact": "La primera cohorte armó un código de contacto "
                       "tosco; los niños menores que lo recibieron lo "
                       "volvieron gramatical — concordancia, clases "
                       "verbales, sintaxis espacial. La prueba viva más "
                       "fuerte de que la capacidad de lenguaje nace, no se "
                       "enseña."},
        "fr": {"question": "Dans le Nicaragua des années 1980, des enfants sourds réunis dans de nouvelles écoles ont fait une chose que les linguistes n'avaient jamais vue se produire. Laquelle ?",
               "options": ["Ils ont appris l'espagnol exceptionnellement vite",
                           "Ils ont CRÉÉ une langue toute neuve — la langue des signes nicaraguayenne — en une génération",
                           "Ils sont restés sans langue",
                           "Ils ont adopté en bloc les signes américains"],
               "fact": "La première cohorte bâtit un code de contact "
                       "fruste ; les plus jeunes qui le reçurent le "
                       "rendirent grammatical — accords, classes verbales, "
                       "syntaxe spatiale. La plus forte preuve vivante que "
                       "la capacité de langage naît au lieu de "
                       "s'enseigner."},
        "pt": {"question": "Na Nicarágua dos anos 1980, crianças surdas reunidas em escolas novas fizeram algo que os linguistas nunca tinham visto acontecer. O quê?",
               "options": ["Aprenderam espanhol invulgarmente depressa",
                           "CRIARAM uma língua nova em folha — a língua gestual nicaraguense — numa geração",
                           "Ficaram sem língua",
                           "Adotaram em bloco os gestos americanos"],
               "fact": "A primeira leva construiu um código de contacto "
                       "tosco; as crianças mais novas que o receberam "
                       "tornaram-no gramatical — concordância, classes "
                       "verbais, sintaxe espacial. A prova viva mais forte "
                       "de que a capacidade de linguagem nasce, não se "
                       "ensina."},
        "ru": {"question": "В Никарагуа 1980-х глухие дети, собранные в новых школах, сделали то, чего лингвисты никогда не наблюдали вживую. Что именно?",
               "options": ["Необычно быстро выучили испанский",
                           "СОЗДАЛИ совершенно новый язык — никарагуанский жестовый — за одно поколение",
                           "Остались без языка",
                           "Целиком переняли американские жесты"],
               "fact": "Первый набор построил грубый контактный код; "
                       "младшие, получив его, сделали его грамматичным — "
                       "согласование, глагольные классы, пространственный "
                       "синтаксис. Сильнейшее живое свидетельство, что "
                       "языковая способность рождается, а не преподаётся."},
        "ar": {"question": "في نيكاراغوا الثمانينيات، فعل أطفال صُمّ جُمعوا في مدارس جديدة شيئًا لم يشهد اللغويون حدوثه قط. ما هو؟",
               "options": ["تعلموا الإسبانية بسرعة غير عادية",
                           "أنشأوا لغة جديدة كليًا — لغة الإشارة النيكاراغوية — في جيل واحد",
                           "بقوا بلا لغة",
                           "تبنّوا الإشارات الأمريكية جملةً"],
               "fact": "بنت الدفعة الأولى شفرة تواصل خشنة؛ فلما تلقاها "
                       "الأصغر سنًا جعلوها نحوية — مطابقةً وأصنافَ أفعال "
                       "وتركيبًا مكانيًا. أقوى دليل حي على أن ملكة اللغة "
                       "تولد ولا تُلقَّن."},
    },
    {
        "answer": 0,
        "en": {"question": "Every healthy human community speaks. How does writing compare?",
               "options": ["An invention, made from scratch only a handful of times in history — most languages have never been written",
                           "Equally universal",
                           "Older than speech",
                           "Universal since ancient times"],
               "fact": "Writing was independently invented in "
                       "Mesopotamia, China and Mesoamerica — nearly "
                       "everything else is borrowing and adaptation. "
                       "Speech is the species trait; writing is "
                       "technology, which is why it must be taught."},
        "es": {"question": "Toda comunidad humana sana habla. ¿Cómo se compara la escritura?",
               "options": ["Es un invento, creado de cero solo un puñado de veces en la historia: la mayoría de las lenguas nunca se han escrito",
                           "Es igual de universal",
                           "Es más antigua que el habla",
                           "Es universal desde la antigüedad"],
               "fact": "La escritura se inventó de forma independiente en "
                       "Mesopotamia, China y Mesoamérica — casi todo lo "
                       "demás es préstamo y adaptación. El habla es rasgo "
                       "de la especie; la escritura es tecnología, y por "
                       "eso hay que enseñarla."},
        "fr": {"question": "Toute communauté humaine en bonne santé parle. Et l'écriture, en comparaison ?",
               "options": ["Une invention, créée de zéro une poignée de fois dans l'histoire — la plupart des langues n'ont jamais été écrites",
                           "Tout aussi universelle",
                           "Plus ancienne que la parole",
                           "Universelle depuis l'Antiquité"],
               "fact": "L'écriture fut inventée indépendamment en "
                       "Mésopotamie, en Chine et en Mésoamérique — presque "
                       "tout le reste est emprunt et adaptation. La parole "
                       "est un trait de l'espèce ; l'écriture est une "
                       "technologie, et c'est pourquoi il faut "
                       "l'enseigner."},
        "pt": {"question": "Toda a comunidade humana saudável fala. E a escrita, em comparação?",
               "options": ["É uma invenção, criada do zero só umas poucas vezes na história — a maioria das línguas nunca foi escrita",
                           "É igualmente universal",
                           "É mais antiga do que a fala",
                           "É universal desde a antiguidade"],
               "fact": "A escrita foi inventada de forma independente na "
                       "Mesopotâmia, na China e na Mesoamérica — quase tudo "
                       "o resto é empréstimo e adaptação. A fala é traço da "
                       "espécie; a escrita é tecnologia, e por isso tem de "
                       "se ensinar."},
        "ru": {"question": "Всякое здоровое человеческое сообщество говорит. А как с письмом?",
               "options": ["Письмо — изобретение, созданное с нуля считанные разы в истории; большинство языков никогда не записывались",
                           "Оно так же универсально",
                           "Оно древнее речи",
                           "Оно универсально с древности"],
               "fact": "Письменность независимо изобрели в Месопотамии, "
                       "Китае и Мезоамерике — почти всё остальное "
                       "заимствование и приспособление. Речь — свойство "
                       "вида; письмо — технология, потому ему и приходится "
                       "учить."},
        "ar": {"question": "كل جماعة بشرية سليمة تتكلم. فماذا عن الكتابة مقارنةً بذلك؟",
               "options": ["اختراعٌ ابتُكر من الصفر مرات معدودة في التاريخ — ومعظم اللغات لم تُكتب قط",
                           "كونية بالقدر نفسه",
                           "أقدم من الكلام",
                           "كونية منذ القدم"],
               "fact": "اختُرعت الكتابة استقلالًا في بلاد الرافدين والصين "
                       "وأمريكا الوسطى — وكل ما عداها تقريبًا اقتراض "
                       "وتكييف. الكلام سمةُ النوع البشري؛ أما الكتابة "
                       "فتقنية، ولهذا لا بد من تعليمها."},
    },
    # ---------------------- families, diversity, grammar around the world
    {
        "answer": 1,
        "en": {"question": "Which country is the most linguistically dense place on Earth?",
               "options": ["India", "Papua New Guinea — around 840 languages among some ten million people", "Brazil", "Nigeria"],
               "fact": "Mountain valleys, islands and ten millennia of "
                       "settlement each kept communities apart. Neighbouring "
                       "villages can speak languages as different as English "
                       "and Japanese; Tok Pisin bridges them."},
        "es": {"question": "¿Qué país es el lugar lingüísticamente más denso de la Tierra?",
               "options": ["La India", "Papúa Nueva Guinea: unas 840 lenguas entre unos diez millones de personas", "Brasil", "Nigeria"],
               "fact": "Valles montañosos, islas y diez milenios de "
                       "poblamiento mantuvieron separadas a las "
                       "comunidades. Aldeas vecinas pueden hablar lenguas "
                       "tan distintas como el español y el japonés; el tok "
                       "pisin les sirve de puente."},
        "fr": {"question": "Quel pays est l'endroit le plus dense en langues de la Terre ?",
               "options": ["L'Inde", "La Papouasie-Nouvelle-Guinée — environ 840 langues pour quelque dix millions d'habitants", "Le Brésil", "Le Nigeria"],
               "fact": "Vallées de montagne, îles et dix millénaires de "
                       "peuplement ont tenu les communautés à l'écart les "
                       "unes des autres. Des villages voisins peuvent "
                       "parler des langues aussi différentes que le "
                       "français et le japonais ; le tok pisin fait le "
                       "pont."},
        "pt": {"question": "Que país é o lugar linguisticamente mais denso da Terra?",
               "options": ["A Índia", "A Papua-Nova Guiné — cerca de 840 línguas entre uns dez milhões de pessoas", "O Brasil", "A Nigéria"],
               "fact": "Vales de montanha, ilhas e dez milénios de "
                       "povoamento mantiveram as comunidades separadas. "
                       "Aldeias vizinhas podem falar línguas tão diferentes "
                       "como o português e o japonês; o tok pisin faz a "
                       "ponte."},
        "ru": {"question": "Какая страна — самое языково плотное место на Земле?",
               "options": ["Индия", "Папуа — Новая Гвинея: около 840 языков на примерно десять миллионов человек", "Бразилия", "Нигерия"],
               "fact": "Горные долины, острова и десять тысячелетий "
                       "заселения держали общины порознь. Соседние деревни "
                       "могут говорить на языках, различных как русский и "
                       "японский; мостом служит ток-писин."},
        "ar": {"question": "أي بلد هو أكثف بقعة لغويًا على وجه الأرض؟",
               "options": ["الهند", "بابوا غينيا الجديدة — نحو 840 لغة بين نحو عشرة ملايين نسمة", "البرازيل", "نيجيريا"],
               "fact": "الوديان الجبلية والجزر وعشرة آلاف سنة من الاستيطان "
                       "أبقت الجماعات متباعدة. قد تتكلم قريتان متجاورتان "
                       "لغتين تختلفان اختلاف العربية عن اليابانية؛ "
                       "وتجسر بينهما التوك-بيسين."},
    },
    {
        "answer": 2,
        "en": {"question": "Of the world's roughly 7,000 languages, how many are considered endangered?",
               "options": ["A few dozen", "About one in twenty", "Around HALF — many with no child speakers left", "Almost none"],
               "fact": "When no children learn a language, its clock is "
                       "set. But the road runs both ways: Hebrew returned "
                       "from no native speakers to millions, and Māori and "
                       "Hawaiian are climbing back through immersion "
                       "schools."},
        "es": {"question": "De las cerca de 7.000 lenguas del mundo, ¿cuántas se consideran amenazadas?",
               "options": ["Unas pocas docenas", "Aproximadamente una de cada veinte", "Cerca de la MITAD, muchas ya sin hablantes niños", "Casi ninguna"],
               "fact": "Cuando ningún niño aprende una lengua, su reloj "
                       "queda en marcha. Pero el camino tiene dos "
                       "sentidos: el hebreo volvió de cero hablantes "
                       "nativos a millones, y el maorí y el hawaiano "
                       "remontan mediante escuelas de inmersión."},
        "fr": {"question": "Sur les quelque 7 000 langues du monde, combien sont considérées comme menacées ?",
               "options": ["Quelques dizaines", "Environ une sur vingt", "Près de la MOITIÉ — beaucoup sans plus aucun enfant locuteur", "Presque aucune"],
               "fact": "Quand plus aucun enfant n'apprend une langue, son "
                       "horloge est lancée. Mais la route va dans les deux "
                       "sens : l'hébreu est revenu de zéro locuteur natif à "
                       "des millions, et le māori et le hawaïen remontent "
                       "par les écoles d'immersion."},
        "pt": {"question": "Das cerca de 7.000 línguas do mundo, quantas se consideram ameaçadas?",
               "options": ["Umas poucas dezenas", "Cerca de uma em vinte", "Perto de METADE — muitas já sem falantes crianças", "Quase nenhuma"],
               "fact": "Quando nenhuma criança aprende uma língua, o "
                       "relógio dela fica a contar. Mas a estrada tem dois "
                       "sentidos: o hebraico voltou de zero falantes "
                       "nativos a milhões, e o māori e o havaiano sobem de "
                       "volta pelas escolas de imersão."},
        "ru": {"question": "Из примерно 7000 языков мира сколько считаются под угрозой исчезновения?",
               "options": ["Несколько десятков", "Примерно один из двадцати", "Около ПОЛОВИНЫ — у многих не осталось детей-носителей", "Почти ни одного"],
               "fact": "Когда язык не учат дети, его часы запущены. Но "
                       "дорога двусторонняя: иврит вернулся от нуля "
                       "носителей к миллионам, а маори и гавайский "
                       "выбираются обратно через школы погружения."},
        "ar": {"question": "من بين نحو سبعة آلاف لغة في العالم، كم لغة تُعد مهددة بالاندثار؟",
               "options": ["بضع عشرات", "واحدة من كل عشرين تقريبًا", "نحو النصف — وكثير منها لم يعد يتعلمه الأطفال", "لا تكاد توجد"],
               "fact": "حين لا يتعلم الأطفال لغةً، تبدأ ساعتها بالعد. لكن "
                       "الطريق ذو اتجاهين: عادت العبرية من صفر متكلم أصلي "
                       "إلى الملايين، والماورية والهاوايية تصعدان من جديد "
                       "عبر مدارس الانغماس."},
    },
    {
        "answer": 0,
        "en": {"question": "What makes the revival of Hebrew unique in language history?",
               "options": ["A language with NO native speakers became the mother tongue of millions",
                           "It was the fastest spelling reform ever",
                           "It borrowed no words at all",
                           "It was decreed by a single law"],
               "fact": "For centuries Hebrew lived in books and liturgy "
                       "only. From the 1880s, families in Ottoman "
                       "Palestine — Ben-Yehuda's famously first — raised "
                       "children in it, coining daily words as they went. "
                       "No other full revival has succeeded on that "
                       "scale."},
        "es": {"question": "¿Qué hace único al renacimiento del hebreo en la historia de las lenguas?",
               "options": ["Una lengua SIN hablantes nativos se volvió lengua materna de millones",
                           "Fue la reforma ortográfica más rápida de la historia",
                           "No tomó prestada ninguna palabra",
                           "Se decretó con una sola ley"],
               "fact": "Durante siglos el hebreo vivió solo en libros y "
                       "liturgia. Desde la década de 1880, familias de la "
                       "Palestina otomana — la de Ben-Yehuda, célebremente "
                       "la primera — criaron hijos en él, acuñando palabras "
                       "cotidianas sobre la marcha. Ningún otro "
                       "renacimiento pleno ha triunfado a esa escala."},
        "fr": {"question": "Qu'est-ce qui rend la renaissance de l'hébreu unique dans l'histoire des langues ?",
               "options": ["Une langue SANS locuteurs natifs est devenue la langue maternelle de millions de gens",
                           "Ce fut la réforme orthographique la plus rapide de l'histoire",
                           "Elle n'a emprunté aucun mot",
                           "Un seul décret l'a ordonnée"],
               "fact": "Des siècles durant, l'hébreu ne vécut que dans les "
                       "livres et la liturgie. À partir des années 1880, "
                       "des familles de Palestine ottomane — celle de "
                       "Ben-Yehuda, fameusement la première — y élevèrent "
                       "leurs enfants, forgeant les mots du quotidien en "
                       "chemin. Aucune autre renaissance complète n'a "
                       "réussi à cette échelle."},
        "pt": {"question": "O que torna o renascimento do hebraico único na história das línguas?",
               "options": ["Uma língua SEM falantes nativos tornou-se língua materna de milhões",
                           "Foi a reforma ortográfica mais rápida de sempre",
                           "Não pediu emprestada palavra nenhuma",
                           "Foi decretado por uma única lei"],
               "fact": "Durante séculos o hebraico viveu só nos livros e "
                       "na liturgia. A partir da década de 1880, famílias "
                       "da Palestina otomana — a de Ben-Yehuda, "
                       "celebremente a primeira — criaram filhos nele, "
                       "cunhando palavras do dia a dia pelo caminho. Nenhum "
                       "outro renascimento pleno triunfou a essa escala."},
        "ru": {"question": "Чем возрождение иврита уникально в истории языков?",
               "options": ["Язык БЕЗ носителей стал родным для миллионов",
                           "Это была самая быстрая реформа орфографии",
                           "Он не заимствовал ни одного слова",
                           "Его предписали одним законом"],
               "fact": "Веками иврит жил только в книгах и литургии. С "
                       "1880-х семьи в османской Палестине — семья "
                       "Бен-Иехуды, как известно, первой — растили на нём "
                       "детей, на ходу чеканя бытовые слова. Ни одно другое "
                       "полное возрождение не удалось в таком масштабе."},
        "ar": {"question": "ما الذي يجعل إحياء العبرية فريدًا في تاريخ اللغات؟",
               "options": ["لغة بلا متكلمين أصليين صارت لغةً أمًّا لملايين",
                           "كانت أسرع إصلاح إملائي في التاريخ",
                           "لم تستعر كلمة واحدة",
                           "صدر بها مرسوم واحد"],
               "fact": "عاشت العبرية قرونًا في الكتب والطقوس وحدها. ومنذ "
                       "ثمانينيات القرن التاسع عشر أخذت أسرٌ في فلسطين "
                       "العثمانية — وأشهرها أسرة بن يهودا الأولى — تربي "
                       "أطفالها بها وتسكّ كلمات الحياة اليومية في الطريق. "
                       "ولم ينجح إحياء كامل آخر بهذا الحجم."},
    },
    {
        "answer": 1,
        "en": {"question": "What are Māori “kōhanga reo”, founded from 1982?",
               "options": ["Traditional song contests",
                           "“Language nests” — preschools run entirely in Māori, elders passing the language straight to toddlers",
                           "Radio stations",
                           "Dictionary projects"],
               "fact": "The nest model — skip the lost generation, connect "
                       "grandparents to toddlers — was copied by Hawaiian, "
                       "Welsh, Sámi and many others. It reframed revival: "
                       "not a school subject but a home."},
        "es": {"question": "¿Qué son los “kōhanga reo” maoríes, fundados desde 1982?",
               "options": ["Concursos de canto tradicionales",
                           "“Nidos de lengua”: preescolares enteramente en maorí, con los mayores pasando la lengua directo a los pequeños",
                           "Emisoras de radio",
                           "Proyectos de diccionario"],
               "fact": "El modelo del nido — saltarse la generación "
                       "perdida y conectar a los abuelos con los niños "
                       "pequeños — fue copiado por el hawaiano, el galés, "
                       "el sami y muchos más. Replanteó el renacimiento: "
                       "no una asignatura, sino un hogar."},
        "fr": {"question": "Que sont les « kōhanga reo » māoris, fondés à partir de 1982 ?",
               "options": ["Des concours de chant traditionnels",
                           "Des « nids de langue » — des maternelles entièrement en māori, où les anciens passent la langue directement aux tout-petits",
                           "Des stations de radio",
                           "Des projets de dictionnaires"],
               "fact": "Le modèle du nid — sauter la génération perdue, "
                       "relier les grands-parents aux tout-petits — fut "
                       "copié par le hawaïen, le gallois, le same et bien "
                       "d'autres. Il a recadré la renaissance : non pas une "
                       "matière scolaire, mais un foyer."},
        "pt": {"question": "O que são os “kōhanga reo” māori, fundados a partir de 1982?",
               "options": ["Concursos de canto tradicionais",
                           "“Ninhos de língua” — pré-escolas inteiramente em māori, com os mais velhos a passar a língua direto aos pequenos",
                           "Estações de rádio",
                           "Projetos de dicionário"],
               "fact": "O modelo do ninho — saltar a geração perdida, "
                       "ligar os avós aos mais pequenos — foi copiado pelo "
                       "havaiano, pelo galês, pelo sámi e muitos outros. "
                       "Reenquadrou o renascimento: não uma disciplina, mas "
                       "um lar."},
        "ru": {"question": "Что такое маорийские «kōhanga reo», основанные с 1982 года?",
               "options": ["Конкурсы традиционного пения",
                           "«Языковые гнёзда» — детские сады целиком на маори, где старики передают язык прямо малышам",
                           "Радиостанции",
                           "Словарные проекты"],
               "fact": "Модель гнезда — перешагнуть потерянное поколение, "
                       "соединить дедов с малышами — переняли гавайский, "
                       "валлийский, саамские и многие другие. Она "
                       "переосмыслила возрождение: не школьный предмет, а "
                       "дом."},
        "ar": {"question": "ما “كوهانغا ريو” الماورية التي أُسست منذ 1982؟",
               "options": ["مسابقات غناء تقليدية",
                           "“أعشاش لغة” — رياض أطفال بالماورية وحدها، يمرر فيها الكبارُ اللغةَ إلى الصغار مباشرة",
                           "محطات إذاعية",
                           "مشاريع معاجم"],
               "fact": "نموذج العش — تجاوز الجيل الضائع ووصل الأجداد "
                       "بالأطفال — نسخته الهاوايية والويلزية والصامية "
                       "وغيرها كثير. لقد أعاد صياغة الإحياء: لا مادةً "
                       "مدرسية بل بيتًا."},
    },
    {
        "answer": 2,
        "en": {"question": "Indonesian unites a country of 700+ languages. What was it based on?",
               "options": ["Javanese, the biggest language",
                           "Dutch",
                           "Malay — for centuries the TRADE language of the archipelago, native to relatively few",
                           "An invented language"],
               "fact": "Choosing giant Javanese would have crowned one "
                       "ethnic group; little Malay belonged to everyone's "
                       "market. Swahili plays the same role across East "
                       "Africa — lingua francas win by being nobody's "
                       "prize."},
        "es": {"question": "El indonesio une un país de más de 700 lenguas. ¿En qué se basó?",
               "options": ["En el javanés, la lengua mayor",
                           "En el neerlandés",
                           "En el malayo: durante siglos la lengua COMERCIAL del archipiélago, materna de relativamente pocos",
                           "En una lengua inventada"],
               "fact": "Elegir el gigantesco javanés habría coronado a una "
                       "etnia; el pequeño malayo era el mercado de todos. "
                       "El suajili juega el mismo papel en África "
                       "oriental — las linguas francas ganan por no ser el "
                       "trofeo de nadie."},
        "fr": {"question": "L'indonésien unit un pays de plus de 700 langues. Sur quoi fut-il fondé ?",
               "options": ["Sur le javanais, la plus grande langue",
                           "Sur le néerlandais",
                           "Sur le malais — des siècles durant la langue de COMMERCE de l'archipel, maternelle pour assez peu de gens",
                           "Sur une langue inventée"],
               "fact": "Choisir le géant javanais aurait couronné une "
                       "ethnie ; le petit malais appartenait au marché de "
                       "tous. Le swahili joue le même rôle en Afrique de "
                       "l'Est — les langues véhiculaires gagnent en "
                       "n'étant le trophée de personne."},
        "pt": {"question": "O indonésio une um país de mais de 700 línguas. Em que se baseou?",
               "options": ["No javanês, a língua maior",
                           "No neerlandês",
                           "No malaio — durante séculos a língua de COMÉRCIO do arquipélago, materna de relativamente poucos",
                           "Numa língua inventada"],
               "fact": "Escolher o gigante javanês teria coroado uma "
                       "etnia; o pequeno malaio pertencia ao mercado de "
                       "todos. O suaíli faz o mesmo papel na África "
                       "Oriental — as línguas francas ganham por não serem "
                       "o troféu de ninguém."},
        "ru": {"question": "Индонезийский объединяет страну с 700+ языками. На чём он основан?",
               "options": ["На яванском, крупнейшем языке",
                           "На нидерландском",
                           "На малайском — веками ТОРГОВОМ языке архипелага, родном для сравнительно немногих",
                           "На искусственном языке"],
               "fact": "Выбор гигантского яванского короновал бы один "
                       "народ; маленький малайский был рынком для всех. Ту "
                       "же роль в Восточной Африке играет суахили: "
                       "лингва-франка побеждает тем, что она — ничей "
                       "трофей."},
        "ar": {"question": "توحّد الإندونيسية بلدًا فيه أكثر من 700 لغة. فعلامَ بُنيت؟",
               "options": ["على الجاوية، اللغة الكبرى",
                           "على الهولندية",
                           "على الملايوية — لغة التجارة في الأرخبيل قرونًا، وهي أم لقلة نسبيًا",
                           "على لغة مخترعة"],
               "fact": "اختيار الجاوية العملاقة كان سيتوّج قومية واحدة؛ "
                       "أما الملايوية الصغيرة فكانت سوقَ الجميع. وتلعب "
                       "السواحلية الدور نفسه في شرق أفريقيا — تفوز اللغات "
                       "الوسيطة لأنها غنيمة لا يملكها أحد."},
    },
    {
        "answer": 1,
        "en": {"question": "Which family contains the most languages of any on Earth — Swahili, Yoruba, Xhosa and Zulu among them?",
               "options": ["Indo-European", "Niger-Congo, with roughly 1,500 languages", "Afro-Asiatic", "Austronesian"],
               "fact": "Most of it is the Bantu expansion: farming "
                       "communities spreading from around the "
                       "Nigeria–Cameroon border across half of Africa in "
                       "3,000 years — which is why noun-class prefixes echo "
                       "from Douala to Durban."},
        "es": {"question": "¿Qué familia contiene más lenguas que ninguna otra en la Tierra — entre ellas el suajili, el yoruba, el xhosa y el zulú?",
               "options": ["La indoeuropea", "La Níger-Congo, con aproximadamente 1.500 lenguas", "La afroasiática", "La austronesia"],
               "fact": "Casi todo es la expansión bantú: comunidades "
                       "agrícolas extendiéndose desde la frontera "
                       "Nigeria-Camerún por media África en 3.000 años — "
                       "por eso los prefijos de clase nominal resuenan de "
                       "Duala a Durban."},
        "fr": {"question": "Quelle famille contient plus de langues qu'aucune autre sur Terre — dont le swahili, le yoruba, le xhosa et le zoulou ?",
               "options": ["L'indo-européenne", "Le Niger-Congo, avec environ 1 500 langues", "L'afro-asiatique", "L'austronésienne"],
               "fact": "L'essentiel en est l'expansion bantoue : des "
                       "communautés agricoles s'étendant depuis la "
                       "frontière Nigeria-Cameroun sur la moitié de "
                       "l'Afrique en 3 000 ans — d'où les préfixes de "
                       "classe nominale qui résonnent de Douala à Durban."},
        "pt": {"question": "Que família contém mais línguas do que qualquer outra na Terra — entre elas o suaíli, o iorubá, o xhosa e o zulu?",
               "options": ["A indo-europeia", "A Níger-Congo, com cerca de 1.500 línguas", "A afro-asiática", "A austronésia"],
               "fact": "Quase tudo é a expansão bantu: comunidades "
                       "agrícolas a espalhar-se da fronteira "
                       "Nigéria-Camarões por metade da África em 3.000 "
                       "anos — por isso os prefixos de classe nominal ecoam "
                       "de Duala a Durban."},
        "ru": {"question": "Какая семья содержит больше языков, чем любая другая на Земле, — среди них суахили, йоруба, коса и зулу?",
               "options": ["Индоевропейская", "Нигеро-конголезская, примерно 1500 языков", "Афразийская", "Австронезийская"],
               "fact": "Основная её часть — экспансия банту: земледельцы, "
                       "расселившиеся от границы Нигерии и Камеруна на "
                       "пол-Африки за 3000 лет, — потому префиксы именных "
                       "классов и перекликаются от Дуалы до Дурбана."},
        "ar": {"question": "أي أسرة لغوية تضم لغات أكثر من أي أسرة أخرى على الأرض — ومنها السواحلية واليوروبا والكوسا والزولو؟",
               "options": ["الهندوأوروبية", "النيجرية-الكونغولية، بنحو 1500 لغة", "الأفروآسيوية", "الأسترونيزية"],
               "fact": "جُلّها توسع البانتو: جماعات زراعية انتشرت من حدود "
                       "نيجيريا والكاميرون عبر نصف أفريقيا في ثلاثة آلاف "
                       "سنة — ولهذا تتردد سوابق أصناف الأسماء من دوالا إلى "
                       "ديربان."},
    },
    {
        "answer": 0,
        "en": {"question": "Malagasy, the language of Madagascar off the African coast, is most closely related to…",
               "options": ["languages of BORNEO, an ocean away in Indonesia",
                           "Swahili, across the channel",
                           "Arabic",
                           "Zulu"],
               "fact": "Austronesian sailors crossed the Indian Ocean "
                       "around the mid-first millennium. Their family had "
                       "already spread from Taiwan through the Philippines "
                       "and Indonesia to, eventually, Hawaiʻi, Easter "
                       "Island and Aotearoa — Māori is a member — the "
                       "widest-flung family of the pre-modern world."},
        "es": {"question": "El malgache, la lengua de Madagascar, frente a la costa africana, está emparentado sobre todo con…",
               "options": ["lenguas de BORNEO, a un océano de distancia, en Indonesia",
                           "el suajili, al otro lado del canal",
                           "el árabe",
                           "el zulú"],
               "fact": "Navegantes austronesios cruzaron el Índico hacia "
                       "mediados del primer milenio. Su familia ya se había "
                       "extendido de Taiwán por Filipinas e Indonesia "
                       "hasta llegar con el tiempo a Hawái, la isla de "
                       "Pascua y Aotearoa — el maorí es miembro — la "
                       "familia más desparramada del mundo premoderno."},
        "fr": {"question": "Le malgache, langue de Madagascar au large de l'Afrique, est le plus étroitement apparenté à…",
               "options": ["des langues de BORNÉO, à un océan de là, en Indonésie",
                           "au swahili, de l'autre côté du canal",
                           "à l'arabe",
                           "au zoulou"],
               "fact": "Des navigateurs austronésiens traversèrent l'océan "
                       "Indien vers le milieu du premier millénaire. Leur "
                       "famille s'étendait déjà de Taïwan aux Philippines "
                       "et à l'Indonésie, pour atteindre à terme Hawaï, "
                       "l'île de Pâques et Aotearoa — le māori en est "
                       "membre — la famille la plus étalée du monde "
                       "prémoderne."},
        "pt": {"question": "O malgaxe, a língua de Madagáscar, ao largo da costa africana, é mais aparentado com…",
               "options": ["línguas do BORNÉU, a um oceano de distância, na Indonésia",
                           "o suaíli, do outro lado do canal",
                           "o árabe",
                           "o zulu"],
               "fact": "Navegadores austronésios cruzaram o Índico por "
                       "meados do primeiro milénio. A família deles já se "
                       "estendia de Taiwan pelas Filipinas e Indonésia até "
                       "chegar, com o tempo, ao Havai, à ilha de Páscoa e a "
                       "Aotearoa — o māori é membro — a família mais "
                       "espalhada do mundo pré-moderno."},
        "ru": {"question": "Малагасийский — язык Мадагаскара у берегов Африки — ближе всего в родстве с…",
               "options": ["языками БОРНЕО, за океаном, в Индонезии",
                           "суахили, через пролив",
                           "арабским",
                           "зулу"],
               "fact": "Австронезийские мореходы пересекли Индийский океан "
                       "около середины первого тысячелетия. Их семья уже "
                       "растянулась от Тайваня через Филиппины и Индонезию "
                       "— и дотянулась потом до Гавайев, острова Пасхи и "
                       "Аотеароа: маори — её член. Самая раскинутая семья "
                       "домодерного мира."},
        "ar": {"question": "الملغاشية، لغة مدغشقر قبالة الساحل الأفريقي، أقرب قرابةً إلى…",
               "options": ["لغات بورنيو في إندونيسيا، على بُعد محيط كامل",
                           "السواحلية عبر القناة",
                           "العربية",
                           "الزولو"],
               "fact": "عبر بحّارة أسترونيزيون المحيطَ الهندي نحو منتصف "
                       "الألفية الأولى. وكانت أسرتهم قد امتدت من تايوان "
                       "عبر الفلبين وإندونيسيا لتبلغ لاحقًا هاواي وجزيرة "
                       "القيامة وأوتياروا — والماورية من أعضائها — أوسع "
                       "أسرة انتشارًا في العالم قبل الحديث."},
    },
    {
        "answer": 1,
        "en": {"question": "How far does the Turkic language family stretch?",
               "options": ["Only Turkey",
                           "From the Balkans to Siberia — Turkish, Azerbaijani, Uzbek, Kazakh, Uyghur, Yakut…",
                           "Turkey and Iran only",
                           "It has no living relatives"],
               "fact": "A Turk and an Uzbek can partly follow each other "
                       "across 3,000 kilometres. The family's shared "
                       "skeleton — vowel harmony, suffix chains, verb "
                       "last — survives from the Mediterranean to the "
                       "Arctic Circle."},
        "es": {"question": "¿Hasta dónde se extiende la familia de lenguas túrquicas?",
               "options": ["Solo Turquía",
                           "De los Balcanes a Siberia: turco, azerí, uzbeko, kazajo, uigur, yakuto…",
                           "Solo Turquía e Irán",
                           "No tiene parientes vivos"],
               "fact": "Un turco y un uzbeko pueden seguirse a medias a "
                       "3.000 kilómetros de distancia. El esqueleto común "
                       "de la familia — armonía vocálica, cadenas de "
                       "sufijos, verbo al final — sobrevive del "
                       "Mediterráneo al círculo polar."},
        "fr": {"question": "Jusqu'où s'étend la famille des langues turciques ?",
               "options": ["La Turquie seulement",
                           "Des Balkans à la Sibérie — turc, azéri, ouzbek, kazakh, ouïghour, iakoute…",
                           "La Turquie et l'Iran seulement",
                           "Elle n'a pas de parents vivants"],
               "fact": "Un Turc et un Ouzbek peuvent en partie se suivre à "
                       "3 000 kilomètres de distance. Le squelette commun "
                       "de la famille — harmonie vocalique, chaînes de "
                       "suffixes, verbe en dernier — survit de la "
                       "Méditerranée au cercle polaire."},
        "pt": {"question": "Até onde se estende a família de línguas turcomanas?",
               "options": ["Só a Turquia",
                           "Dos Balcãs à Sibéria — turco, azeri, usbeque, cazaque, uigur, iacuto…",
                           "Só a Turquia e o Irão",
                           "Não tem parentes vivos"],
               "fact": "Um turco e um usbeque conseguem seguir-se em parte "
                       "a 3.000 quilómetros de distância. O esqueleto comum "
                       "da família — harmonia vocálica, cadeias de sufixos, "
                       "verbo no fim — sobrevive do Mediterrâneo ao círculo "
                       "polar."},
        "ru": {"question": "Как далеко простирается тюркская языковая семья?",
               "options": ["Только Турция",
                           "От Балкан до Сибири: турецкий, азербайджанский, узбекский, казахский, уйгурский, якутский…",
                           "Только Турция и Иран",
                           "У неё нет живых родственников"],
               "fact": "Турок и узбек могут отчасти понимать друг друга "
                       "через 3000 километров. Общий скелет семьи — "
                       "гармония гласных, цепочки суффиксов, глагол в "
                       "конце — выживает от Средиземного моря до "
                       "полярного круга."},
        "ar": {"question": "إلى أي مدى تمتد أسرة اللغات التركية؟",
               "options": ["تركيا وحدها",
                           "من البلقان إلى سيبيريا — التركية والأذرية والأوزبكية والكازاخية والأويغورية والياقوتية…",
                           "تركيا وإيران فقط",
                           "لا أقارب أحياء لها"],
               "fact": "يستطيع تركي وأوزبكي أن يفهم كلٌّ الآخرَ جزئيًا عبر "
                       "ثلاثة آلاف كيلومتر. والهيكل المشترك للأسرة — "
                       "انسجام الصوائت وسلاسل اللواحق والفعل في الآخر — "
                       "باقٍ من المتوسط إلى الدائرة القطبية."},
    },
    {
        "answer": 2,
        "en": {"question": "The plural of Arabic kitāb (book) is kutub. What happened?",
               "options": ["A suffix was added",
                           "The word was doubled",
                           "The VOWELS changed inside the fixed consonants — a “broken plural”",
                           "Nothing; context decides"],
               "fact": "Arabic has dozens of broken-plural patterns — "
                       "walad/awlād, madīna/mudun — and learners simply "
                       "must learn each noun's. English keeps a Germanic "
                       "miniature of the idea: foot/feet, mouse/mice."},
        "es": {"question": "El plural del árabe kitāb (libro) es kutub. ¿Qué ha pasado?",
               "options": ["Se añadió un sufijo",
                           "Se duplicó la palabra",
                           "Cambiaron las VOCALES dentro de las consonantes fijas: un “plural fracto”",
                           "Nada; decide el contexto"],
               "fact": "El árabe tiene docenas de patrones de plural "
                       "fracto — walad/awlād, madīna/mudun — y el aprendiz "
                       "simplemente debe saberse el de cada sustantivo. El "
                       "inglés guarda una miniatura germánica de la idea: "
                       "foot/feet, mouse/mice."},
        "fr": {"question": "Le pluriel de l'arabe kitāb (livre) est kutub. Que s'est-il passé ?",
               "options": ["On a ajouté un suffixe",
                           "On a doublé le mot",
                           "Les VOYELLES ont changé à l'intérieur des consonnes fixes — un « pluriel brisé »",
                           "Rien ; le contexte décide"],
               "fact": "L'arabe a des dizaines de schèmes de pluriel "
                       "brisé — walad/awlād, madīna/mudun — et l'apprenant "
                       "doit simplement connaître celui de chaque nom. "
                       "L'anglais garde une miniature germanique de "
                       "l'idée : foot/feet, mouse/mice."},
        "pt": {"question": "O plural do árabe kitāb (livro) é kutub. O que aconteceu?",
               "options": ["Acrescentou-se um sufixo",
                           "Duplicou-se a palavra",
                           "As VOGAIS mudaram dentro das consoantes fixas — um “plural fraturado”",
                           "Nada; o contexto decide"],
               "fact": "O árabe tem dezenas de padrões de plural "
                       "fraturado — walad/awlād, madīna/mudun — e o "
                       "aprendente tem simplesmente de saber o de cada "
                       "substantivo. O inglês guarda uma miniatura "
                       "germânica da ideia: foot/feet, mouse/mice."},
        "ru": {"question": "Множественное число арабского kitāb (книга) — kutub. Что произошло?",
               "options": ["Добавился суффикс",
                           "Слово удвоилось",
                           "Внутри неизменных согласных сменились ГЛАСНЫЕ — «ломаное множественное»",
                           "Ничего; решает контекст"],
               "fact": "В арабском десятки моделей ломаного множественного "
                       "— walad/awlād, madīna/mudun, — и учащемуся просто "
                       "надо знать модель каждого слова. Английский хранит "
                       "германскую миниатюру той же идеи: foot/feet, "
                       "mouse/mice."},
        "ar": {"question": "جمع “كتاب” هو “كُتُب”. ماذا حدث للكلمة؟",
               "options": ["أُضيفت لاحقة",
                           "ضوعفت الكلمة",
                           "تغيّرت الحركات داخل الصوامت الثابتة — إنه “جمع التكسير”",
                           "لا شيء؛ السياق يقرر"],
               "fact": "في العربية عشرات أوزان جمع التكسير — ولد/أولاد، "
                       "مدينة/مُدُن — وما على المتعلم إلا حفظ وزن كل اسم. "
                       "وتحفظ الإنجليزية مصغّرًا جرمانيًا للفكرة نفسها: "
                       "foot/feet وmouse/mice."},
    },
    {
        "answer": 1,
        "en": {"question": "Mandarin Chinese has no past tense. How does it say that something already happened?",
               "options": ["It can't express time",
                           "With particles and time words: le after the verb, “yesterday” up front",
                           "By changing tone",
                           "By word order alone"],
               "fact": "Chinese marks ASPECT — complete, ongoing, "
                       "experienced — rather than tense. Indonesian works "
                       "with time words alone: sudah “already”, akan "
                       "“going to”. A language can skip any category, "
                       "and route the meaning another way."},
        "es": {"question": "El chino mandarín no tiene tiempo pasado. ¿Cómo dice que algo ya ocurrió?",
               "options": ["No puede expresar el tiempo",
                           "Con partículas y palabras temporales: le tras el verbo, “ayer” delante",
                           "Cambiando el tono",
                           "Solo con el orden de palabras"],
               "fact": "El chino marca el ASPECTO — completo, en curso, "
                       "experimentado — y no el tiempo. El indonesio se "
                       "arregla solo con palabras temporales: sudah "
                       "“ya”, akan “va a”. Una lengua puede saltarse "
                       "cualquier categoría y encaminar el significado por "
                       "otra vía."},
        "fr": {"question": "Le chinois mandarin n'a pas de passé. Comment dit-il qu'une chose a déjà eu lieu ?",
               "options": ["Il ne peut pas exprimer le temps",
                           "Par des particules et des mots de temps : le après le verbe, « hier » en tête",
                           "En changeant de ton",
                           "Par le seul ordre des mots"],
               "fact": "Le chinois marque l'ASPECT — accompli, en cours, "
                       "vécu — plutôt que le temps. L'indonésien s'en tire "
                       "avec les seuls mots de temps : sudah « déjà », "
                       "akan « va ». Une langue peut sauter n'importe "
                       "quelle catégorie et faire passer le sens par un "
                       "autre chemin."},
        "pt": {"question": "O chinês mandarim não tem pretérito. Como diz que algo já aconteceu?",
               "options": ["Não consegue exprimir o tempo",
                           "Com partículas e palavras de tempo: le depois do verbo, “ontem” à frente",
                           "Mudando o tom",
                           "Só pela ordem das palavras"],
               "fact": "O chinês marca o ASPETO — completo, em curso, "
                       "vivido — em vez do tempo. O indonésio governa-se só "
                       "com palavras de tempo: sudah “já”, akan “vai”. "
                       "Uma língua pode saltar qualquer categoria e "
                       "encaminhar o sentido por outra via."},
        "ru": {"question": "В китайском нет прошедшего времени. Как он говорит, что нечто уже случилось?",
               "options": ["Он не может выразить время",
                           "Частицами и словами времени: le после глагола, «вчера» в начале",
                           "Сменой тона",
                           "Одним порядком слов"],
               "fact": "Китайский маркирует ВИД — завершённое, длящееся, "
                       "пережитое, — а не время. Индонезийский обходится "
                       "одними словами времени: sudah «уже», akan "
                       "«собирается». Язык может пропустить любую "
                       "категорию и провести смысл другим путём — русскому "
                       "ли с его видовыми парами этого не знать."},
        "ar": {"question": "لا زمن ماضيًا في الصينية. فكيف تقول إن أمرًا قد وقع؟",
               "options": ["لا تستطيع التعبير عن الزمن",
                           "بأدوات وكلمات زمن: le بعد الفعل و“أمس” في الصدارة",
                           "بتغيير النغمة",
                           "بترتيب الكلمات وحده"],
               "fact": "تَسِمُ الصينية الجهةَ — مكتمل، جارٍ، مُجرَّب — لا "
                       "الزمن. وتكتفي الإندونيسية بكلمات الزمن وحدها: sudah "
                       "“قد/فعلًا” وakan “سوف”. تستطيع اللغة إسقاط أي "
                       "مقولة وتمرير المعنى من طريق آخر."},
    },
    {
        "answer": 0,
        "en": {"question": "English leans hard on “the” and “a”. How unusual are articles, globally?",
               "options": ["Most languages do WITHOUT them — Russian, Turkish, Japanese, Swahili, Hindi…",
                           "Nearly every language has them",
                           "Only English has them",
                           "All languages once had them and lost them"],
               "fact": "Definiteness gets routed elsewhere: word order, "
                       "case, demonstratives, or simply context. Meanwhile "
                       "article languages disagree profoundly about where "
                       "articles go — Romanian and the Scandinavian "
                       "languages glue them onto the END of the noun."},
        "es": {"question": "El español se apoya en “el” y “un”. ¿Qué tan comunes son los artículos en el mundo?",
               "options": ["La mayoría de las lenguas se las arregla SIN ellos: ruso, turco, japonés, suajili, hindi…",
                           "Casi todas las lenguas los tienen",
                           "Solo las lenguas romances los tienen",
                           "Todas los tuvieron y los perdieron"],
               "fact": "La definitud se encamina por otra parte: orden de "
                       "palabras, casos, demostrativos o simple contexto. Y "
                       "las lenguas con artículo discrepan a fondo sobre "
                       "dónde va: el rumano y las lenguas escandinavas lo "
                       "pegan al FINAL del sustantivo."},
        "fr": {"question": "Le français s'appuie fort sur « le » et « un ». Les articles sont-ils si répandus dans le monde ?",
               "options": ["La plupart des langues s'en passent — russe, turc, japonais, swahili, hindi…",
                           "Presque toutes les langues en ont",
                           "Seules les langues romanes en ont",
                           "Toutes en ont eu puis les ont perdus"],
               "fact": "La définitude passe par d'autres canaux : ordre "
                       "des mots, cas, démonstratifs ou simple contexte. Et "
                       "les langues à articles divergent profondément sur "
                       "leur place — le roumain et les langues "
                       "scandinaves le collent à la FIN du nom."},
        "pt": {"question": "O português apoia-se em “o” e “um”. Quão comuns são os artigos no mundo?",
               "options": ["A maioria das línguas passa SEM eles — russo, turco, japonês, suaíli, hindi…",
                           "Quase todas as línguas os têm",
                           "Só as línguas românicas os têm",
                           "Todas os tiveram e perderam"],
               "fact": "A definitude segue por outros canais: ordem das "
                       "palavras, casos, demonstrativos ou simples "
                       "contexto. E as línguas com artigo divergem "
                       "profundamente sobre onde ele vai — o romeno e as "
                       "línguas escandinavas colam-no ao FIM do "
                       "substantivo."},
        "ru": {"question": "Английский держится за «the» и «a». Насколько вообще обычны артикли в языках мира?",
               "options": ["Большинство языков обходится БЕЗ них — русский, турецкий, японский, суахили, хинди…",
                           "Они есть почти во всех языках",
                           "Они есть только в английском",
                           "Все языки их имели и потеряли"],
               "fact": "Определённость идёт другими путями: порядком слов, "
                       "падежами, указательными словами или просто "
                       "контекстом. А языки с артиклями глубоко расходятся "
                       "в том, где ему стоять: румынский и скандинавские "
                       "клеят его к КОНЦУ существительного."},
        "ar": {"question": "تتكئ الإنجليزية على “the” و“a”. فما مدى شيوع أدوات التعريف في لغات العالم؟",
               "options": ["معظم اللغات تستغني عنها — الروسية والتركية واليابانية والسواحلية والهندية…",
                           "تكاد توجد في كل لغة",
                           "لا توجد إلا في الإنجليزية",
                           "كانت في كل اللغات ثم ضاعت"],
               "fact": "يمر التعريف من قنوات أخرى: ترتيب الكلمات أو "
                       "الإعراب أو أسماء الإشارة أو السياق وحده — والعربية "
                       "تعرفه بأداة واحدة “ال”. وتختلف لغات الأدوات "
                       "اختلافًا عميقًا في موضعها: الرومانية والإسكندنافية "
                       "تلصقانها بآخر الاسم."},
    },
    {
        "answer": 1,
        "en": {"question": "Spanish says “no vi nada” — literally “I didn't see nothing”. What is this?",
               "options": ["A logical error Spanish tolerates",
                           "Negative concord: negatives AGREE with each other, standard in most Romance and Slavic languages",
                           "Slang",
                           "Emphasis only"],
               "fact": "Russian piles up three in a row — nikto nikogda "
                       "nichego — and it's textbook grammar. English "
                       "banned double negatives in the 1700s by analogy "
                       "with mathematics; Chaucer and Shakespeare used "
                       "them freely."},
        "es": {"question": "El español dice “no vi nada”, dos negaciones seguidas. ¿Qué es esto?",
               "options": ["Un error lógico que el español tolera",
                           "Concordancia negativa: las negaciones CONCUERDAN entre sí, lo normal en las lenguas romances y eslavas",
                           "Jerga",
                           "Solo énfasis"],
               "fact": "El ruso apila tres seguidas — nikto nikogda "
                       "nichego — y es gramática de manual. El inglés "
                       "prohibió la doble negación en el siglo XVIII por "
                       "analogía con las matemáticas; Chaucer y Shakespeare "
                       "las usaban con toda libertad."},
        "fr": {"question": "L'espagnol dit « no vi nada » — mot à mot « je n'ai pas vu rien ». Qu'est-ce que c'est ?",
               "options": ["Une erreur logique que l'espagnol tolère",
                           "La concordance négative : les négations S'ACCORDENT entre elles, la norme dans les langues romanes et slaves",
                           "De l'argot",
                           "De l'emphase seulement"],
               "fact": "Le russe en empile trois — nikto nikogda "
                       "nichego — et c'est la grammaire du manuel. "
                       "L'anglais a banni la double négation au XVIIIe "
                       "siècle par analogie avec les mathématiques ; "
                       "Chaucer et Shakespeare en usaient librement. Le "
                       "français « ne… rien » en garde la structure."},
        "pt": {"question": "O português diz “não vi nada” — duas negações seguidas. O que é isto?",
               "options": ["Um erro lógico que a língua tolera",
                           "Concordância negativa: as negações CONCORDAM entre si, o normal nas línguas românicas e eslavas",
                           "Gíria",
                           "Só ênfase"],
               "fact": "O russo empilha três seguidas — nikto nikogda "
                       "nichego — e é gramática de manual. O inglês baniu a "
                       "dupla negação no século XVIII por analogia com a "
                       "matemática; Chaucer e Shakespeare usavam-na à "
                       "vontade."},
        "ru": {"question": "По-испански «no vi nada» — буквально «не видел ничего». Что это?",
               "options": ["Логическая ошибка, которую испанский терпит",
                           "Отрицательное согласование: отрицания СОГЛАСУЮТСЯ друг с другом — норма романских и славянских языков",
                           "Сленг",
                           "Только усиление"],
               "fact": "Русский нанизывает три подряд — «никто никогда "
                       "ничего» — и это хрестоматийная грамматика. "
                       "Английский запретил двойное отрицание в XVIII веке "
                       "по аналогии с математикой; Чосер и Шекспир "
                       "пользовались им свободно."},
        "ar": {"question": "تقول الإسبانية “no vi nada” — حرفيًا “لم أرَ لا شيء”. ما هذا؟",
               "options": ["خطأ منطقي تتسامح فيه الإسبانية",
                           "التطابق السلبي: أدوات النفي تتوافق بعضها مع بعض — وهو المعيار في الرومانسية والسلافية",
                           "عامية",
                           "توكيد فقط"],
               "fact": "تكدّس الروسية ثلاثًا متتالية — nikto nikogda "
                       "nichego — وهي قواعد الكتاب المدرسي. حظرت "
                       "الإنجليزية النفي المزدوج في القرن الثامن عشر قياسًا "
                       "على الرياضيات؛ وكان تشوسر وشكسبير يستعملانه "
                       "بحرية."},
    },
    {
        "answer": 2,
        "en": {"question": "Which living language do historical linguists prize as closest to ancient Indo-European in sound?",
               "options": ["Modern Greek", "Icelandic", "Lithuanian — its endings and accent preserve startling archaisms", "Welsh"],
               "fact": "Lithuanian dievas “god” sits beside Sanskrit "
                       "devas; whole case endings match forms "
                       "reconstructed for five thousand years ago. The "
                       "saying goes that a linguist wanting to hear "
                       "Proto-Indo-European should listen to a Lithuanian "
                       "farmer."},
        "es": {"question": "¿Qué lengua viva aprecian los lingüistas históricos como la más cercana en sonido al indoeuropeo antiguo?",
               "options": ["El griego moderno", "El islandés", "El lituano: sus terminaciones y su acento conservan arcaísmos asombrosos", "El galés"],
               "fact": "El lituano dievas “dios” se sienta junto al "
                       "sánscrito devas; terminaciones enteras coinciden "
                       "con formas reconstruidas de hace cinco mil años. "
                       "Dice el dicho que el lingüista que quiera oír "
                       "protoindoeuropeo escuche a un campesino lituano."},
        "fr": {"question": "Quelle langue vivante les linguistes historiques prisent-ils comme la plus proche, par ses sons, du vieil indo-européen ?",
               "options": ["Le grec moderne", "L'islandais", "Le lituanien — ses désinences et son accent conservent des archaïsmes saisissants", "Le gallois"],
               "fact": "Le lituanien dievas « dieu » siège à côté du "
                       "sanskrit devas ; des désinences entières coïncident "
                       "avec des formes reconstruites d'il y a cinq mille "
                       "ans. Le dicton veut qu'un linguiste désireux "
                       "d'entendre du proto-indo-européen écoute un paysan "
                       "lituanien."},
        "pt": {"question": "Que língua viva os linguistas históricos prezam como a mais próxima, no som, do indo-europeu antigo?",
               "options": ["O grego moderno", "O islandês", "O lituano — as terminações e o acento preservam arcaísmos espantosos", "O galês"],
               "fact": "O lituano dievas “deus” senta-se ao lado do "
                       "sânscrito devas; terminações inteiras coincidem com "
                       "formas reconstruídas de há cinco mil anos. Diz o "
                       "ditado que um linguista que queira ouvir "
                       "proto-indo-europeu escute um lavrador lituano."},
        "ru": {"question": "Какой живой язык историческая лингвистика ценит как ближайший по звучанию к древнему индоевропейскому?",
               "options": ["Новогреческий", "Исландский", "Литовский — его окончания и ударение хранят поразительные архаизмы", "Валлийский"],
               "fact": "Литовское dievas «бог» стоит рядом с "
                       "санскритским devas; целые падежные окончания "
                       "совпадают с формами, восстановленными для "
                       "пятитысячелетней давности. Поговорка велит "
                       "лингвисту, желающему услышать праиндоевропейский, "
                       "слушать литовского крестьянина."},
        "ar": {"question": "أي لغة حية يُجلّها اللغويون التاريخيون بوصفها الأقرب صوتًا إلى الهندوأوروبية القديمة؟",
               "options": ["اليونانية الحديثة", "الآيسلندية", "الليتوانية — نهاياتها ونبرها يحفظان عتائق مذهلة", "الويلزية"],
               "fact": "الليتوانية dievas “إله” تجلس بجوار السنسكريتية "
                       "devas؛ ونهايات إعراب كاملة تطابق صيغًا أُعيد "
                       "بناؤها لما قبل خمسة آلاف سنة. ويقول المثل: من أراد "
                       "من اللغويين سماع الهندوأوروبية الأم فليُنصت إلى "
                       "فلاح ليتواني."},
    },
    {
        "answer": 1,
        "en": {"question": "Portuguese can conjugate an INFINITIVE: “para sairmos” — “for us-to-leave”. How rare is that?",
               "options": ["Every Romance language does it",
                           "Very rare — the “personal infinitive” is a signature of Portuguese and Galician",
                           "Borrowed from Arabic",
                           "It's a spelling convention"],
               "fact": "The personal infinitive lets Portuguese pack "
                       "“in order for us to leave” into two words while "
                       "staying an infinitive — a construction grammarians "
                       "cross oceans to admire. Hungarian, unrelated, "
                       "arrived at a similar trick independently."},
        "es": {"question": "El portugués puede conjugar un INFINITIVO: “para sairmos”, “para salir-nosotros”. ¿Qué tan raro es eso?",
               "options": ["Todas las lenguas romances lo hacen",
                           "Rarísimo: el “infinitivo personal” es seña de identidad del portugués y el gallego",
                           "Se tomó del árabe",
                           "Es una convención ortográfica"],
               "fact": "El infinitivo personal permite al portugués meter "
                       "“para que salgamos” en dos palabras sin dejar "
                       "de ser infinitivo — una construcción que los "
                       "gramáticos cruzan océanos para admirar. El húngaro, "
                       "sin parentesco, llegó por su cuenta a un truco "
                       "parecido."},
        "fr": {"question": "Le portugais peut conjuguer un INFINITIF : « para sairmos » — « pour nous-partir ». À quel point est-ce rare ?",
               "options": ["Toutes les langues romanes le font",
                           "Très rare — l'« infinitif personnel » est une signature du portugais et du galicien",
                           "C'est emprunté à l'arabe",
                           "C'est une convention d'orthographe"],
               "fact": "L'infinitif personnel permet au portugais de "
                       "loger « pour que nous partions » en deux mots "
                       "tout en restant à l'infinitif — une construction "
                       "que les grammairiens traversent les océans pour "
                       "admirer. Le hongrois, sans parenté, est arrivé "
                       "seul à un tour semblable."},
        "pt": {"question": "O português consegue conjugar um INFINITIVO: “para sairmos”. Quão raro é isso?",
               "options": ["Todas as línguas românicas o fazem",
                           "Raríssimo — o “infinitivo pessoal” é assinatura do português e do galego",
                           "Foi emprestado do árabe",
                           "É uma convenção ortográfica"],
               "fact": "O infinitivo pessoal deixa o português meter "
                       "“para que saiamos” em duas palavras sem deixar "
                       "de ser infinitivo — uma construção que os "
                       "gramáticos atravessam oceanos para admirar. O "
                       "húngaro, sem parentesco nenhum, chegou sozinho a "
                       "um truque parecido."},
        "ru": {"question": "Португальский умеет спрягать ИНФИНИТИВ: «para sairmos» — «чтобы нам-уйти». Насколько это редкость?",
               "options": ["Так делают все романские языки",
                           "Большая редкость: «личный инфинитив» — фирменный знак португальского и галисийского",
                           "Это заимствовано из арабского",
                           "Это условность орфографии"],
               "fact": "Личный инфинитив позволяет португальскому уложить "
                       "«чтобы мы ушли» в два слова, оставаясь "
                       "инфинитивом, — конструкция, ради которой грамматисты "
                       "пересекают океаны. Венгерский, вовсе не родственный, "
                       "самостоятельно пришёл к похожему фокусу."},
        "ar": {"question": "تستطيع البرتغالية تصريف المصدر: “para sairmos” أي “لكي نغادر-نحن”. فما ندرة ذلك؟",
               "options": ["كل اللغات الرومانسية تفعله",
                           "نادر جدًا — “المصدر الشخصي” علامة مميزة للبرتغالية والجاليقية",
                           "مستعار من العربية",
                           "مجرد عرف إملائي"],
               "fact": "يتيح المصدر الشخصي للبرتغالية حشر “لكي نغادر” "
                       "في كلمتين مع بقائه مصدرًا — تركيبٌ يقطع النحاة "
                       "المحيطات لإعجابهم به. والمجرية، ولا قرابة بينهما، "
                       "بلغت حيلة مشابهة على حدة."},
    },
    {
        "answer": 0,
        "en": {"question": "In French, “les amis” sounds a z between the words that “les copains” doesn't. What is this?",
               "options": ["Liaison: a normally silent final consonant surfaces before a vowel",
                           "A spelling mistake in speech",
                           "An accent feature of Paris only",
                           "Random variation"],
               "fact": "The z of les was always there in writing, silent "
                       "until a vowel wakes it. Liaison even carries "
                       "grammar: petit ami with the t sounded is "
                       "“boyfriend”, not just any small friend."},
        "es": {"question": "En francés, “les amis” hace sonar una z entre las palabras que “les copains” no tiene. ¿Qué es esto?",
               "options": ["La liaison: una consonante final normalmente muda aflora ante vocal",
                           "Un error ortográfico al hablar",
                           "Un rasgo del acento de París solamente",
                           "Variación aleatoria"],
               "fact": "La z de les siempre estuvo en la escritura, muda "
                       "hasta que una vocal la despierta. La liaison hasta "
                       "acarrea gramática: petit ami con la t sonada es "
                       "“novio”, no cualquier amigo pequeño."},
        "fr": {"question": "En français, « les amis » fait sonner un z entre les mots que « les copains » n'a pas. Qu'est-ce que c'est ?",
               "options": ["La liaison : une consonne finale normalement muette refait surface devant une voyelle",
                           "Une faute d'orthographe à l'oral",
                           "Un trait de l'accent parisien seulement",
                           "Une variation aléatoire"],
               "fact": "Le z de « les » a toujours été là à l'écrit, "
                       "muet jusqu'à ce qu'une voyelle le réveille. La "
                       "liaison porte même de la grammaire : « petit "
                       "ami » avec le t sonné, c'est l'amoureux — pas "
                       "n'importe quel petit copain."},
        "pt": {"question": "Em francês, “les amis” faz soar um z entre as palavras que “les copains” não tem. O que é isto?",
               "options": ["A liaison: uma consoante final normalmente muda vem à tona antes de vogal",
                           "Um erro ortográfico na fala",
                           "Um traço do sotaque de Paris apenas",
                           "Variação aleatória"],
               "fact": "O z de les sempre esteve na escrita, mudo até uma "
                       "vogal o acordar. A liaison até carrega gramática: "
                       "petit ami com o t soado é “namorado”, não um "
                       "amigo pequeno qualquer."},
        "ru": {"question": "Во французском в «les amis» между словами звучит z, которого нет в «les copains». Что это?",
               "options": ["Лиэзон: обычно немой конечный согласный всплывает перед гласным",
                           "Орфографическая ошибка в речи",
                           "Черта только парижского выговора",
                           "Случайное колебание"],
               "fact": "Буква z в les всегда была на письме — немая, пока "
                       "её не разбудит гласный. Лиэзон несёт даже "
                       "грамматику: petit ami с озвученным t — это "
                       "«возлюбленный», а не просто маленький друг."},
        "ar": {"question": "في الفرنسية تُسمَع زاي بين كلمتي “les amis” لا وجود لها في “les copains”. ما هذا؟",
               "options": ["الوصل: صامت أخير صامتٌ عادةً يطفو قبل الصائت",
                           "خطأ إملائي في الكلام",
                           "سمة لهجة باريس وحدها",
                           "تنوع عشوائي"],
               "fact": "زاي les كانت في الكتابة دومًا، صامتةً حتى يوقظها "
                       "صائت. بل يحمل الوصل قواعدَ: petit ami بتاء مسموعة "
                       "تعني “الحبيب” لا أيَّ صديق صغير."},
    },
    {
        "answer": 2,
        "en": {"question": "“Do you like it?” — what is odd, cross-linguistically, about that little “do”?",
               "options": ["Nothing; most languages have one",
                           "It is a politeness marker",
                           "Almost NO other language needs a dummy verb to ask or negate — English do-support is a genuine rarity",
                           "It was borrowed from Latin"],
               "fact": "Other Germanic languages just flip: "
                       "“Magst du…?”. Learners' “Like you it?” is "
                       "perfectly good German, Dutch and Old English "
                       "grammar — the odd one out here is modern English "
                       "itself."},
        "es": {"question": "“Do you like it?” — ¿qué tiene de raro, entre las lenguas, ese pequeño “do”?",
               "options": ["Nada; casi todas las lenguas tienen uno",
                           "Es una marca de cortesía",
                           "Casi NINGUNA otra lengua necesita un verbo comodín para preguntar o negar: el do inglés es una verdadera rareza",
                           "Se tomó del latín"],
               "fact": "Las demás lenguas germánicas simplemente "
                       "invierten: “Magst du…?”. El “Like you "
                       "it?” del aprendiz es gramática perfecta en "
                       "alemán, neerlandés e inglés antiguo — aquí el raro "
                       "es el inglés moderno."},
        "fr": {"question": "« Do you like it? » — qu'a-t-il d'étrange, entre les langues, ce petit « do » ?",
               "options": ["Rien ; la plupart des langues en ont un",
                           "C'est une marque de politesse",
                           "Presque AUCUNE autre langue n'a besoin d'un verbe béquille pour interroger ou nier — le do anglais est une vraie rareté",
                           "Il fut emprunté au latin"],
               "fact": "Les autres langues germaniques se contentent "
                       "d'inverser : « Magst du…? ». Le « Like you "
                       "it? » de l'apprenant est une grammaire parfaite "
                       "en allemand, en néerlandais et en vieil anglais — "
                       "l'étrange, ici, c'est l'anglais moderne lui-même."},
        "pt": {"question": "“Do you like it?” — o que tem de estranho, entre as línguas, aquele pequeno “do”?",
               "options": ["Nada; a maioria das línguas tem um",
                           "É uma marca de cortesia",
                           "Quase NENHUMA outra língua precisa de um verbo fantoche para perguntar ou negar — o do inglês é uma raridade genuína",
                           "Foi emprestado do latim"],
               "fact": "As outras línguas germânicas simplesmente "
                       "invertem: “Magst du…?”. O “Like you it?” "
                       "do aprendente é gramática perfeita em alemão, "
                       "neerlandês e inglês antigo — o esquisito aqui é o "
                       "próprio inglês moderno."},
        "ru": {"question": "«Do you like it?» — что странного, по меркам языков мира, в этом маленьком «do»?",
               "options": ["Ничего, такой есть почти везде",
                           "Это показатель вежливости",
                           "Почти НИ одному другому языку не нужен глагол-пустышка для вопроса и отрицания — английское do-support настоящая редкость",
                           "Оно заимствовано из латыни"],
               "fact": "Другие германские языки просто переставляют: "
                       "«Magst du…?». Ученическое «Like you it?» — "
                       "безупречная грамматика немецкого, нидерландского и "
                       "древнеанглийского. Странный здесь — сам "
                       "современный английский."},
        "ar": {"question": "“Do you like it?” — ما الغريب، بمقياس اللغات، في كلمة “do” الصغيرة هذه؟",
               "options": ["لا شيء؛ لمعظم اللغات مثلها",
                           "إنها علامة تهذيب",
                           "لا تكاد لغة أخرى تحتاج فعلًا زائفًا للسؤال والنفي — فـdo الإنجليزية ندرة حقيقية",
                           "استُعيرت من اللاتينية"],
               "fact": "سائر الجرمانية تكتفي بالقلب: “Magst du…?”. "
                       "وجملة المتعلم “Like you it?” قواعدُ سليمة تمامًا "
                       "في الألمانية والهولندية والإنجليزية القديمة — الشاذ "
                       "هنا هو الإنجليزية الحديثة نفسها."},
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
    # A random draw, not the first N: with no seen-record, a fixed slice
    # would make every visit to this path the same handful of questions in
    # the same order — the loudest possible "same stuff over and over".
    pool = seed_questions(locale)
    n = max(0, min(limit, len(pool)))
    items = random.sample(pool, n) if n else []
    for it in items:
        it["id"] = str(uuid.uuid5(_NS, f"{locale}:{it['question']}"))
    return items
