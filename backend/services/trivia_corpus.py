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
