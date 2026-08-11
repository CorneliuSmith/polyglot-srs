/**
 * Letters & Sounds — Arabic (ar) UI overlay: the full course catalogue
 * re-anchored for Arabic readers. Sound descriptions lean on Arabic
 * phonology (حركات، مدود، مخارج الحروف) and real Arabic anchor words;
 * course-language example words are untouched.
 */
import type { LanguageLetters } from './lettersData'

const spanishAr: LanguageLetters = {
  intro: 'الإملاء الإسباني أمين: خمس حركات صافية، وكل حرف تقريبًا يُنطق بالطريقة نفسها في كل مرة.',
  sections: [
    {
      title: 'الحركات الخمس',
      note: 'قصيرة صافية لا تُمَط أبدًا. الشرطة (á é í ó ú) تحدد موضع النبر — والصوت لا يتغير.',
      rows: [
        { char: 'a / á', example: 'agua', sound: 'فتحة صريحة، مثل أول «باب» قصيرة' },
        { char: 'e / é', example: 'leche', sound: 'فتحة ممالة نحو الكسر' },
        { char: 'i / í', example: 'vivir', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'o / ó', example: 'poco', sound: 'مثل واو «لو» قصيرة' },
        { char: 'u / ú', example: 'luna', sound: 'ضمة صريحة، مثل واو «نور» (لا تُنطق في que/qui وgue/gui)' },
        { char: 'ü', example: 'pingüino', sound: 'النقطتان توقظان u: تُنطق gü جيمًا قاهرية (g) تليها واو' },
      ],
    },
    {
      title: 'حروف صامتة تخالف التوقع',
      rows: [
        { char: 'ñ', example: 'niño', sound: 'نون تليها ياء مدغمتان، مثل «دُنْيا» مسرعة' },
        { char: 'j', example: 'joven', sound: 'خاء عربية تمامًا' },
        { char: 'g (+e/i)', example: 'gente', sound: 'الخاء نفسها؛ وفي غير ذلك جيم قاهرية (g)' },
        { char: 'll / y', example: 'llamar', sound: 'ياء مثل ياء «يد» (وفي معظم أمريكا اللاتينية أقرب إلى جيم خفيفة)' },
        { char: 'h', example: 'hola', sound: 'صامتة دائمًا' },
        { char: 'rr / r-', example: 'perro', sound: 'راء مكررة مشددة؛ والراء المفردة بين حركتين ضربة واحدة خفيفة' },
        { char: 'z / c(+e,i)', example: 'zapato', sound: 'سين في أمريكا اللاتينية؛ ثاء عربية في إسبانيا' },
        { char: 'v', example: 'vaso', sound: 'مثل b تمامًا — باء خفيفة' },
        { char: 'qu', example: 'queso', sound: 'كاف — والحرف u صامت' },
      ],
    },
  ],
}

const frenchAr: LanguageLetters = {
  intro: 'أصوات الفرنسية تسكن في الحركات وفي انسياب الكلام بين الكلمات. الحروف الأخيرة صامتة غالبًا، والعلامات تغيّر نوعية الحركة لا موضع النبر.',
  sections: [
    {
      title: 'الحركات وعلاماتها',
      rows: [
        { char: 'a / à / â', example: 'chat', sound: 'فتحة مثل أول «باب»' },
        { char: 'é', example: 'été', sound: 'إمالة مشدودة بين الفتحة والكسرة، بلا انزلاق' },
        { char: 'è / ê / e(+2 cons.)', example: 'mère', sound: 'فتحة ممالة مفتوحة' },
        { char: 'e (بلا علامة)', example: 'le', sound: 'حركة مطموسة مختلسة بين الفتحة والضمة — وكثيرًا ما تسقط' },
        { char: 'i / î / y', example: 'ville', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'o / ô', example: 'mot', sound: 'مثل واو «لو»' },
        { char: 'u / û', example: 'tu', sound: 'انطق الياء بشفتين مدوّرتين — لا نظير له في العربية' },
        { char: 'ou', example: 'vous', sound: 'واو مد، مثل واو «نور»' },
        { char: 'eu / œu', example: 'peu', sound: 'انطق الإمالة بشفتين مدوّرتين' },
        { char: 'oi', example: 'moi', sound: 'مثل «وا» في «واحة»' },
        { char: 'au / eau', example: 'eau', sound: 'مثل واو «لو»' },
        { char: 'ai / ei', example: 'maison', sound: 'فتحة ممالة' },
      ],
    },
    {
      title: 'الحركات الأنفية',
      note: 'حركة + n/m في المقطع نفسه = يمر الهواء من الأنف، ولا يُنطق حرف n/m نفسه إطلاقًا.',
      rows: [
        { char: 'on / om', example: 'bon', sound: 'واو قصيرة أنفية — «أو» تخرج من الأنف' },
        { char: 'an / en', example: 'enfant', sound: 'فتحة ممدودة أنفية' },
        { char: 'in / ain / ein', example: 'vin', sound: 'فتحة ممالة أنفية' },
        { char: 'un', example: 'un', sound: 'حركة مطموسة أنفية (يدمجها كثيرون مع in)' },
      ],
    },
    {
      title: 'عادات الحروف الصامتة',
      rows: [
        { char: 'r', example: 'rouge', sound: 'غرغرة من أقصى الحلق — قريبة من الغين العربية' },
        { char: 'ç', example: 'garçon', sound: 'سين — الذيل يبقي c لينة قبل a/o/u' },
        { char: 'ch', example: 'chien', sound: 'شين عربية' },
        { char: 'gn', example: 'montagne', sound: 'نون تليها ياء مدغمتان، مثل «دُنْيا»' },
        { char: 'j / g(+e,i)', example: 'jour', sound: 'جيم شامية غير معطّشة' },
        { char: 'h', example: 'homme', sound: 'صامتة' },
        { char: 'final consonants', example: 'petit', sound: 'الحروف الأخيرة صامتة غالبًا — انتبه إلى s وt وd وx' },
      ],
    },
  ],
}

const germanAr: LanguageLetters = {
  intro: 'الألمانية تُنطق كما تُكتب متى عرفت حروف الأوملاوت وحفنة من الثنائيات.',
  sections: [
    {
      title: 'الحركات وحروف الأوملاوت',
      rows: [
        { char: 'a', example: 'Haus', sound: 'فتحة مثل أول «باب»' },
        { char: 'ä', example: 'Mädchen', sound: 'فتحة ممالة نحو الكسر' },
        { char: 'o', example: 'Brot', sound: 'مثل واو «لو»' },
        { char: 'ö', example: 'schön', sound: 'انطق الإمالة بشفتين مدوّرتين' },
        { char: 'u', example: 'gut', sound: 'واو مد، مثل واو «نور»' },
        { char: 'ü', example: 'über', sound: 'انطق الياء بشفتين مدوّرتين' },
        { char: 'ei', example: 'mein', sound: 'فتحة تليها ياء ساكنة، مثل «بَيْت»' },
        { char: 'ie', example: 'Liebe', sound: 'ياء مد، مثل ياء «فيل»' },
        { char: 'eu / äu', example: 'heute', sound: 'مثل «أُوي» — واو قصيرة تليها ياء' },
        { char: 'au', example: 'Auto', sound: 'فتحة تليها واو ساكنة، مثل «يَوْم»' },
      ],
    },
    {
      title: 'ثنائيات الحروف الصامتة',
      rows: [
        { char: 'w', example: 'Wasser', sound: 'صوت v: فاء مجهورة (يكتبها بعضهم ڤ)' },
        { char: 'v', example: 'Vater', sound: 'فاء عادية' },
        { char: 'z', example: 'Zeit', sound: '«تس» — تاء وسين ملتصقتان' },
        { char: 's (+ حركة)', example: 'Sonne', sound: 'زاي' },
        { char: 'ß / ss', example: 'Straße', sound: 'سين حادة' },
        { char: 'sch', example: 'Schule', sound: 'شين' },
        { char: 'st- / sp-', example: 'Straße', sound: '«شت» / «شب» في أول الكلمة' },
        { char: 'ch (بعد a/o/u)', example: 'Buch', sound: 'خاء عربية' },
        { char: 'ch (بعد e/i)', example: 'ich', sound: 'خاء خفيفة مهموسة من مقدمة الحنك — بين الشين والخاء' },
        { char: 'r', example: 'rot', sound: 'غين خفيفة من أقصى الحلق؛ في آخر الكلمة تكاد تصير حركة (‏-er = فتحة مطموسة)' },
        { char: 'final b/d/g', example: 'Tag', sound: 'في آخر الكلمة تقسو إلى p/t/k (باء مهموسة، تاء، كاف)' },
      ],
    },
  ],
}

const italianAr: LanguageLetters = {
  intro: 'سبعة أصوات للحركات، وحروف مضعّفة واضحة كأن عليها شدة، وحرفان (c وg) يلينان قبل e وi.',
  sections: [
    {
      title: 'الحركات',
      rows: [
        { char: 'a / à', example: 'casa', sound: 'فتحة مثل أول «باب»' },
        { char: 'e / è', example: 'bene', sound: 'فتحة ممالة (é أشد إمالة نحو الياء)' },
        { char: 'i / ì', example: 'vino', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'o / ò', example: 'otto', sound: 'مثل واو «لو»' },
        { char: 'u / ù', example: 'uno', sound: 'ضمة صريحة، مثل واو «نور»' },
      ],
    },
    {
      title: 'نظام c وg',
      rows: [
        { char: 'c (+a,o,u)', example: 'casa', sound: 'كاف' },
        { char: 'c (+e,i)', example: 'cena', sound: '«تش» مثل «تشاي»' },
        { char: 'ch', example: 'chiave', sound: 'كاف — الهاء تعيد الحرف صلبًا' },
        { char: 'g (+a,o,u)', example: 'gatto', sound: 'جيم قاهرية (g)' },
        { char: 'g (+e,i)', example: 'gelato', sound: 'جيم فصحى معطّشة' },
        { char: 'gh', example: 'spaghetti', sound: 'جيم قاهرية — أُعيدت صلبة' },
        { char: 'gn', example: 'gnocchi', sound: 'نون تليها ياء مدغمتان، مثل «دُنْيا»' },
        { char: 'gli', example: 'famiglia', sound: 'لام تليها ياء مدغمة: «لْي»' },
        { char: 'sc (+e,i)', example: 'pesce', sound: 'شين' },
      ],
    },
    {
      title: 'عادات',
      rows: [
        { char: 'double consonants', example: 'pizza', sound: 'مضعّف كأن عليه شدة — أمسكه ضعف المدة: pit-tsa لا pi-tsa' },
        { char: 'z', example: 'zio', sound: '«تس» أو «دز»' },
        { char: 'r', example: 'Roma', sound: 'راء عربية مكررة' },
        { char: 'h', example: 'hotel', sound: 'صامتة' },
      ],
    },
  ],
}

const catalanAr: LanguageLetters = {
  intro: 'حركات الكتالانية تنطمس حين لا تكون منبورة (سمة كتالانية)، ولها هجاءات لا تُرى في غيرها.',
  sections: [
    {
      title: 'الحركات',
      rows: [
        { char: 'a / à', example: 'casa', sound: 'فتحة عند النبر؛ حركة مطموسة بلا نبر' },
        { char: 'e / é / è', example: 'més', sound: 'إمالة أو فتحة ممالة عند النبر؛ مطموسة بلا نبر' },
        { char: 'i / í', example: 'nit', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'o / ó / ò', example: 'porta', sound: 'مثل واو «لو» عند النبر؛ ضمة «نور» بلا نبر' },
        { char: 'u / ú', example: 'butxaca', sound: 'ضمة صريحة، مثل واو «نور»' },
      ],
    },
    {
      title: 'خصوصيات كتالانية',
      rows: [
        { char: 'ny', example: 'Catalunya', sound: 'نون تليها ياء مدغمتان، مثل «دُنْيا»' },
        { char: 'l·l', example: 'il·lusió', sound: 'النقطة الطائرة: لام ممدودة' },
        { char: 'x', example: 'xocolata', sound: 'شين' },
        { char: 'tx', example: 'cotxe', sound: '«تش» مثل «تشاي»' },
        { char: 'ç', example: 'plaça', sound: 'سين' },
        { char: 'j / g(+e,i)', example: 'jugar', sound: 'جيم شامية غير معطّشة' },
        { char: 'r final', example: 'cantar', sound: 'صامتة غالبًا في آخر الكلمة' },
        { char: 'ig final', example: 'puig', sound: '«تش» في آخر الكلمة' },
      ],
    },
  ],
}

const portugueseAr: LanguageLetters = {
  intro: 'البرتغالية البرازيلية: حركات موسيقية، وأصوات أنفية شهيرة، وحروف صامتة تفاجئ حتى الناطقين بالإسبانية.',
  sections: [
    {
      title: 'الحركات وعلاماتها',
      rows: [
        { char: 'a / á', example: 'casa', sound: 'فتحة مثل أول «باب»' },
        { char: 'â', example: 'câmera', sound: 'حركة مطموسة مغلقة' },
        { char: 'e / é', example: 'ela', sound: 'فتحة ممالة' },
        { char: 'ê', example: 'você', sound: 'إمالة مشدودة بلا انزلاق' },
        { char: 'e final', example: 'nome', sound: 'تنكمش إلى كسرة قصيرة في البرازيل' },
        { char: 'o / ó', example: 'avó', sound: 'واو مفتوحة عريضة' },
        { char: 'ô', example: 'avô', sound: 'واو مغلقة — لا يفترق avó عن avô إلا هنا!' },
        { char: 'o final', example: 'gato', sound: 'تنكمش إلى ضمة' },
        { char: 'u', example: 'tudo', sound: 'واو مد، مثل واو «نور»' },
      ],
    },
    {
      title: 'العائلة الأنفية',
      note: 'علامة المد (~) أو حرف m/n بعد الحركة يُخرجانها من الأنف.',
      rows: [
        { char: 'ã', example: 'maçã', sound: 'فتحة أنفية' },
        { char: 'ão', example: 'pão', sound: 'مثل «أَوْ» أنفية — أكثر الأصوات برتغاليةً على الإطلاق' },
        { char: 'õe', example: 'ações', sound: 'مثل «ـوي» أنفية' },
        { char: 'em / en', example: 'bem', sound: 'إمالة أنفية' },
        { char: 'im / in', example: 'sim', sound: 'كسرة أنفية' },
      ],
    },
    {
      title: 'مفاجآت الحروف الصامتة',
      rows: [
        { char: 'ç', example: 'coração', sound: 'سين' },
        { char: 'ch', example: 'chuva', sound: 'شين' },
        { char: 'lh', example: 'filho', sound: 'لام تليها ياء مدغمة: «لْي»' },
        { char: 'nh', example: 'ninho', sound: 'نون تليها ياء مدغمتان، مثل «دُنْيا»' },
        { char: 'j / g(+e,i)', example: 'hoje', sound: 'جيم شامية غير معطّشة' },
        { char: 'r- / rr', example: 'rio', sound: 'هاء هوائية في البرازيل' },
        { char: 'ti / di', example: 'dia', sound: 'تُنطقان «تشي» / «جي» في معظم البرازيل' },
        { char: 'l final', example: 'Brasil', sound: 'تتحول إلى واو — Brasiw' },
      ],
    },
  ],
}

const romanianAr: LanguageLetters = {
  intro: 'الرومانية تُقرأ تقريبًا كالإيطالية مع خمسة أحرف زائدة — وكلها منتظمة.',
  sections: [
    {
      title: 'الأحرف الخمسة الخاصة',
      rows: [
        { char: 'ă', example: 'casă', sound: 'حركة مطموسة بين الفتحة والضمة' },
        { char: 'â / î', example: 'în', sound: 'كسرة عميقة مركزية — انطق الياء ولسانك مسحوب إلى الخلف' },
        { char: 'ș', example: 'și', sound: 'شين' },
        { char: 'ț', example: 'preț', sound: '«تس» — تاء وسين ملتصقتان' },
      ],
    },
    {
      title: 'جدير بالمعرفة',
      rows: [
        { char: 'c (+e,i)', example: 'ce', sound: '«تش» مثل «تشاي»' },
        { char: 'che / chi', example: 'chelner', sound: 'كاف' },
        { char: 'g (+e,i)', example: 'ger', sound: 'جيم فصحى معطّشة' },
        { char: 'ghe / ghi', example: 'ghid', sound: 'جيم قاهرية (g)' },
        { char: 'j', example: 'jos', sound: 'جيم شامية غير معطّشة' },
        { char: 'r', example: 'repede', sound: 'راء عربية مكررة' },
        { char: '-i final', example: 'lupi', sound: 'مهموسة — بالكاد ياء' },
      ],
    },
  ],
}

// Reused verbatim from lettersL10n.ts (turkishAr) — the reference register.
const turkishAr: LanguageLetters = {
  intro:
    'الإملاء التركي منتظم تمامًا. الفرق بين الياء المنقوطة i وغير المنقوطة ı مهم — فهما حرفان مختلفان.',
  sections: [
    {
      title: 'حروف العلة — مجموعة أمامية ومجموعة خلفية',
      note: 'التناغم الصوتي: تلتزم الكلمة بمجموعة واحدة. الأمامية: e i ö ü. الخلفية: a ı o u.',
      rows: [
        { char: 'a', example: 'araba', sound: 'فتحة ممدودة قليلًا، مثل ألف «باب»' },
        { char: 'e', example: 'ev', sound: 'فتحة ممالة نحو الكسر' },
        { char: 'ı (بلا نقطة!)', example: 'ılık', sound: 'صوت مطموس بين الضمة والكسرة، بشفتين مبسوطتين' },
        { char: 'i (بنقطة)', example: 'bir', sound: 'كسرة صريحة، مثل ياء «بير»' },
        { char: 'o', example: 'okul', sound: 'مثل واو «لو» قصيرة' },
        { char: 'ö', example: 'göz', sound: 'انطق الكسرة بشفتين مدوّرتين' },
        { char: 'u', example: 'su', sound: 'ضمة صريحة، مثل واو «سو»' },
        { char: 'ü', example: 'üzüm', sound: 'انطق الياء بشفتين مدوّرتين' },
      ],
    },
    {
      title: 'الحروف الساكنة',
      rows: [
        { char: 'c', example: 'cam', sound: 'مثل الجيم الفصحى المعطّشة (ج)' },
        { char: 'ç', example: 'çay', sound: 'مثل «تش» في «تشاي»' },
        { char: 'ş', example: 'şeker', sound: 'مثل الشين (ش)' },
        { char: 'j', example: 'jandarma', sound: 'مثل الجيم الشامية غير المعطّشة (چ الفرنسية في jour)' },
        { char: 'ğ (الغين اللينة)', example: 'dağ', sound: 'صامت — يطيل الحركة التي قبله فقط' },
        { char: 'v', example: 'var', sound: 'بين الواو والـ v الخفيفة' },
        { char: 'r', example: 'resim', sound: 'راء بضربة واحدة؛ تُهمس في آخر الكلمة' },
      ],
    },
  ],
}

const swahiliAr: LanguageLetters = {
  intro: 'السواحلية صوتية بامتياز: خمس حركات صافية، والنبر دائمًا على المقطع قبل الأخير.',
  sections: [
    {
      title: 'الحركات',
      rows: [
        { char: 'a', example: 'baba', sound: 'فتحة مثل أول «باب»' },
        { char: 'e', example: 'wewe', sound: 'فتحة ممالة' },
        { char: 'i', example: 'sisi', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'o', example: 'moto', sound: 'مثل واو «لو»' },
        { char: 'u', example: 'kuku', sound: 'ضمة صريحة، مثل واو «نور»' },
      ],
    },
    {
      title: 'ثنائيات الحروف',
      rows: [
        { char: 'ny', example: 'nyumba', sound: 'نون تليها ياء مدغمتان، مثل «دُنْيا»' },
        { char: "ng'", example: "ng'ombe", sound: 'نون خيشومية مثل النون المخفاة قبل الكاف في «مَن كان» — لكن في أول المقطع' },
        { char: 'ng (no apostrophe)', example: 'ngoma', sound: 'النون الخيشومية نفسها تليها جيم قاهرية: «نْ-غ»' },
        { char: 'dh', example: 'dhahabu', sound: 'ذال عربية (من الكلمات العربية الدخيلة)' },
        { char: 'th', example: 'thelathini', sound: 'ثاء عربية' },
        { char: 'gh', example: 'ghali', sound: 'غين عربية (من الكلمات العربية الدخيلة)' },
        { char: 'ch', example: 'chai', sound: '«تش» مثل «تشاي»' },
        { char: 'mb / nd / nj', example: 'mbwa', sound: 'همهم بالميم أو النون داخل الحرف التالي — نبضة واحدة' },
      ],
    },
  ],
}

const yorubaAr: LanguageLetters = {
  intro: 'اليوروبا لغة نغمية — علامات الشكل فيها طبقة صوت لا نبر. وحرفان منقوطان يدلان على حركتين مفتوحتين.',
  sections: [
    {
      title: 'الحركات (7) والنقاط',
      rows: [
        { char: 'a', example: 'ata', sound: 'فتحة مثل أول «باب»' },
        { char: 'e', example: 'ewé', sound: 'إمالة مشدودة' },
        { char: 'ẹ (منقوطة)', example: 'ẹja', sound: 'فتحة ممالة مفتوحة' },
        { char: 'i', example: 'ilé', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'o', example: 'owó', sound: 'واو مغلقة، مثل واو «لو»' },
        { char: 'ọ (منقوطة)', example: 'ọmọ', sound: 'واو مفتوحة عريضة' },
        { char: 'u', example: 'imu', sound: 'ضمة صريحة، مثل واو «نور»' },
      ],
    },
    {
      title: 'النغمات — الطبقات الثلاث',
      note: 'الحروف نفسها بطبقة مختلفة كلمة مختلفة. العلامات هي اللحن.',
      rows: [
        { char: 'á (عالية)', example: 'wá', sound: 'الطبقة تقفز صعودًا' },
        { char: 'a (وسطى)', example: 'wa', sound: 'طبقة مستوية عادية' },
        { char: 'à (منخفضة)', example: 'wà', sound: 'الطبقة تهبط نزولًا' },
      ],
    },
    {
      title: 'الحروف الصامتة',
      rows: [
        { char: 'ṣ (منقوطة)', example: 'ṣe', sound: 'شين' },
        { char: 'gb', example: 'gbogbo', sound: 'جيم قاهرية (g) وباء في اللحظة نفسها — لا نظير له' },
        { char: 'p', example: 'pápá', sound: 'في الحقيقة «كْب» تُطلقان معًا' },
        { char: 'j', example: 'jẹun', sound: 'جيم فصحى معطّشة' },
      ],
    },
  ],
}

const hausaAr: LanguageLetters = {
  intro: 'كتابة «بوكو» الهوسية تستعمل ثلاثة أحرف «معقوفة» لأصوات لا تنساب بل تفرقع أو تنقر.',
  sections: [
    {
      title: 'الحركات',
      note: 'خمس حركات، قصيرة أو طويلة — والطول يغيّر المعنى.',
      rows: [
        { char: 'a', example: 'ruwa', sound: 'فتحة (الطويلة: مُدَّها كألف «باب»)' },
        { char: 'e', example: 'gemu', sound: 'إمالة' },
        { char: 'i', example: 'kifi', sound: 'كسرة، مثل ياء «فيل»' },
        { char: 'o', example: 'doki', sound: 'مثل واو «لو»' },
        { char: 'u', example: 'kudi', sound: 'ضمة، مثل واو «نور»' },
      ],
    },
    {
      title: 'الأحرف المعقوفة',
      rows: [
        { char: 'ɓ', example: 'ɓera', sound: 'باء انفجارية إلى الداخل — الهواء يُشفط إلى الفم' },
        { char: 'ɗ', example: 'ɗaki', sound: 'دال انفجارية إلى الداخل' },
        { char: 'ƙ', example: 'ƙofa', sound: 'كاف مقترنة بهمزة قطع — قريبة من قاف مضغوطة' },
        { char: "'y", example: "'ya'ya", sound: 'ياء محشرجة مصرورة' },
      ],
    },
    {
      title: 'عادات أخرى',
      rows: [
        { char: 'ts', example: 'tsuntsu', sound: '«تس» مع نقرة حنجرية — روح الصاد مع همزة' },
        { char: 'sh', example: 'shekara', sound: 'شين' },
        { char: 'c', example: 'ci', sound: '«تش» مثل «تشاي»' },
        { char: 'r', example: 'rana', sound: 'راء مكررة أو بضربة واحدة' },
      ],
    },
  ],
}

const xhosaAr: LanguageLetters = {
  intro: 'إسيخوسا شهيرة بحروف الطقطقة — ثلاث طقطقات أساسية تُكتب c وx وq. وكل ما عداها قريب من المألوف.',
  sections: [
    {
      title: 'الطقطقات الثلاث',
      rows: [
        { char: 'c', example: 'cela', sound: 'طقطقة أسنانية — صوت التذمر «تسك تسك»، اللسان خلف الأسنان' },
        { char: 'x', example: 'ixesha', sound: 'طقطقة جانبية — صوت حث الخيل من جانب الفم' },
        { char: 'q', example: 'iqanda', sound: 'طقطقة حنكية — فرقعة كفتح قنينة من سقف الحنك' },
        { char: 'gc / gx / gq', example: 'gqiba', sound: 'الطقطقات نفسها مجهورة (همهم خلالها)' },
        { char: 'nc / nx / nq', example: 'inqola', sound: 'الطقطقات نفسها مع غنّة أنفية' },
      ],
    },
    {
      title: 'الحركات',
      rows: [
        { char: 'a', example: 'abantu', sound: 'فتحة مثل أول «باب»' },
        { char: 'e', example: 'ewe', sound: 'فتحة ممالة' },
        { char: 'i', example: 'siza', sound: 'كسرة، مثل ياء «فيل»' },
        { char: 'o', example: 'onke', sound: 'واو مفتوحة عريضة' },
        { char: 'u', example: 'ubuntu', sound: 'ضمة، مثل واو «نور»' },
      ],
    },
    {
      title: 'ثنائيات أخرى',
      rows: [
        { char: 'hl', example: 'hlala', sound: 'لام مهموسة — انفخ الهواء من جانبي اللسان بلا صوت' },
        { char: 'dl', example: 'indlela', sound: 'النسخة المجهورة من hl' },
        { char: 'tsh', example: 'utshaba', sound: '«تش» مثل «تشاي»' },
        { char: 'kh / th / ph', example: 'ukutya', sound: 'كاف وتاء وباء مهموسة مع نفخة هواء' },
      ],
    },
  ],
}

const maoriAr: LanguageLetters = {
  intro: 'الماورية: خمس حركات (قصيرة وطويلة)، وثمانية حروف صامتة، وثنائيان. كل مقطع ينتهي بحركة.',
  sections: [
    {
      title: 'الحركات — قصيرة وطويلة',
      note: 'الماكرون (ā ē ī ō ū) يضاعف طول الحركة، والطول يغيّر المعنى.',
      rows: [
        { char: 'a / ā', example: 'aroha', sound: 'فتحة مثل أول «باب» (‏ā تُمَد كألفها)' },
        { char: 'e / ē', example: 'kete', sound: 'فتحة ممالة' },
        { char: 'i / ī', example: 'kiwi', sound: 'كسرة، مثل ياء «فيل»' },
        { char: 'o / ō', example: 'moana', sound: 'واو مفتوحة، مثل واو «لو»' },
        { char: 'u / ū', example: 'utu', sound: 'ضمة، مثل واو «نور»' },
      ],
    },
    {
      title: 'الثنائيان',
      rows: [
        { char: 'wh', example: 'whānau', sound: 'فاء' },
        { char: 'ng', example: 'ngā', sound: 'نون خيشومية مثل النون المخفاة قبل الكاف — حتى في أول الكلمة' },
      ],
    },
    {
      title: 'الحروف الصامتة',
      rows: [
        { char: 'r', example: 'reo', sound: 'ضربة خفيفة بين الراء واللام' },
        { char: 't', example: 'te', sound: 'تاء ناعمة تكاد تخلو من النفخة' },
        { char: 'k, m, n, p, h, w', example: 'kapa haka', sound: 'كنظائرها المألوفة: كاف وميم ونون وهاء وواو — وp باء مهموسة' },
      ],
    },
  ],
}

const jamaicanAr: LanguageLetters = {
  intro: 'الباتوا بهجاء كاسيدي/JLU: صوت واحد لكل حرف، ولا حروف صامتة. إن استطعت قوله استطعت كتابته.',
  sections: [
    {
      title: 'الحركات',
      rows: [
        { char: 'a', example: 'bak', sound: 'فتحة مثل أول «باب»' },
        { char: 'aa', example: 'baal', sound: 'ألف مد طويلة' },
        { char: 'e', example: 'bel', sound: 'فتحة ممالة' },
        { char: 'i', example: 'sik', sound: 'كسرة قصيرة مرتخية' },
        { char: 'ii', example: 'siik', sound: 'ياء مد، مثل ياء «فيل»' },
        { char: 'o', example: 'pat', sound: 'واو قصيرة مفتوحة' },
        { char: 'u', example: 'buk', sound: 'ضمة قصيرة' },
        { char: 'uu', example: 'skuul', sound: 'واو مد، مثل واو «نور»' },
        { char: 'ie', example: 'kiek', sound: 'انزلاق من الياء إلى فتحة ممالة: «يِه»' },
        { char: 'uo', example: 'guo', sound: 'انزلاق من الواو إلى الفتحة: «وُوَه»' },
        { char: 'ai', example: 'taim', sound: 'فتحة تليها ياء ساكنة، مثل «بَيْت»' },
        { char: 'ou', example: 'bout', sound: 'فتحة تليها واو ساكنة، مثل «يَوْم»' },
      ],
    },
    {
      title: 'عادات الحروف الصامتة',
      rows: [
        { char: 'k / g (+ya)', example: 'kyaan', sound: 'كاف أو جيم قاهرية تنزلق إلى ياء: «كْيا» / «غْيا»' },
        { char: 'no th', example: 'tink / dis', sound: 'الثاء والذال الإنجليزيتان تصيران تاء أو دالًا' },
        { char: 'no h-drop rule', example: 'ouse / haks', sound: 'الهاء تأتي وتذهب بحرية — كلاهما صحيح' },
        { char: 'final clusters trim', example: 'las (last)', sound: 'يسقط آخر حرف من العنقود الختامي' },
      ],
    },
  ],
}

const englishAr: LanguageLetters = {
  intro: 'الإملاء الإنجليزي تاريخٌ لا صوتيات. هذه الأصوات التي يجاهد فيها المتعلمون — مع أنماط الهجاء الموثوقة حيث وُجدت.',
  sections: [
    {
      title: 'الأصوات الشهيرة',
      rows: [
        { char: 'th (مهموسة)', example: 'think', sound: 'ثاء عربية تمامًا — اللسان بين الأسنان مع نفخ الهواء بلا جهر' },
        { char: 'th (مجهورة)', example: 'this', sound: 'ذال عربية تمامًا — الوضع نفسه مع الجهر' },
        { char: 'w vs v', example: 'very wet', sound: 'w واو بشفتين مدوّرتين بلا أسنان؛ v فاء مجهورة بالأسنان على الشفة' },
        { char: 'r', example: 'red', sound: 'لا تكرار ولا غرغرة — اثنِ اللسان دون أن يلمس شيئًا' },
        { char: 'h', example: 'house', sound: 'هاء حقيقية — لا تصمت أبدًا (إلا في hour وhonest)' },
      ],
    },
    {
      title: 'حركات تُربك المتعلمين',
      rows: [
        { char: 'i (قصيرة)', example: 'ship', sound: 'كسرة قصيرة مرتخية — وليست ياء مد' },
        { char: 'ee', example: 'sheep', sound: 'ياء مد مشدودة طويلة، مثل ياء «فيل»' },
        { char: 'a (قصيرة)', example: 'cat', sound: 'فتحة مفتوحة جدًا بفك منخفض — بين الفتحة والإمالة' },
        { char: 'u (قصيرة)', example: 'cup', sound: 'فتحة مطموسة مركزية' },
        { char: 'er / unstressed', example: 'teacher', sound: 'حركة مطموسة مختلسة — أكسل الحركات؛ معظم المقاطع غير المنبورة تستعملها' },
      ],
    },
    {
      title: 'أنماط هجاء يمكن الوثوق بها',
      rows: [
        { char: 'magic e', example: 'hat → hate', sound: 'حرف e الصامت في الآخر يحوّل الحركة إلى مدّ باسم الحرف' },
        { char: '-tion', example: 'station', sound: 'تُنطق «شِن»' },
        { char: 'ough', example: 'though / tough', sound: 'عذرًا — ستة أصوات مختلفة؛ احفظ كل كلمة وحدها' },
      ],
    },
  ],
}

const dutchAr: LanguageLetters = {
  intro: 'الإملاء الهولندي ودود — بضع ثنائيات وحركة شهيرة واحدة (ui) تصنع كل المتاعب.',
  sections: [
    {
      title: 'ثنائيات الحركات',
      rows: [
        { char: 'aa / a', example: 'water', sound: 'ألف مد طويلة / حركة مطموسة قصيرة — التضعيف علامة الطول' },
        { char: 'ee / e', example: 'been', sound: 'إمالة طويلة / فتحة ممالة قصيرة؛ والـ -e الأخيرة مطموسة' },
        { char: 'oo / o', example: 'boom', sound: 'واو طويلة مثل «أوه» / واو قصيرة' },
        { char: 'uu / u', example: 'muur', sound: 'انطق الياء بشفتين مدوّرتين / حركة مطموسة قصيرة' },
        { char: 'ie', example: 'niet', sound: 'ياء مد، مثل ياء «فيل»' },
        { char: 'oe', example: 'boek', sound: 'واو مد، مثل واو «نور»' },
        { char: 'eu', example: 'leuk', sound: 'انطق الإمالة بشفتين مدوّرتين' },
        { char: 'ij / ei', example: 'ijs', sound: 'بين «أيْ» و«إيْ» — الصوت الهولندي الشهير بهجاءين' },
        { char: 'ui', example: 'huis', sound: 'لا نظير له: انطق «أَوْ» بشفتين مدوّرتين بشدة' },
        { char: 'ou / au', example: 'oud', sound: 'فتحة تليها واو ساكنة، مثل «يَوْم»' },
      ],
    },
    {
      title: 'عادات الحروف الصامتة',
      rows: [
        { char: 'g / ch', example: 'goed', sound: 'الحشرجة الهولندية — خاء عربية (أنعم في الجنوب)' },
        { char: 'sch', example: 'school', sound: 'سين تليها خاء: «سخول»' },
        { char: 'w', example: 'water', sound: 'بين الواو والـ v' },
        { char: 'v', example: 'vader', sound: 'بين الـ v والفاء' },
        { char: 'j', example: 'ja', sound: 'ياء مثل ياء «يد»' },
        { char: 'r', example: 'rood', sound: 'مكررة أو حلقية كالغين — كلاهما صحيح' },
        { char: '-en (في النهاية)', example: 'lopen', sound: 'النون الأخيرة كثيرًا ما تسقط: «لوبِه»' },
        { char: '-tje', example: 'kopje', sound: 'آلة التصغير — koppje وhuisje وmomentje' },
      ],
    },
  ],
}

const russianAr: LanguageLetters = {
  intro: 'الأبجدية السيريلية — 33 حرفًا. لمعظمها صوت واحد ثابت؛ والنظام الذي يجب تعلمه هو أزواج الحركات «القاسية/اللينة» الخمسة.',
  sections: [
    {
      title: 'الحركات — المجموعة القاسية',
      note: 'تُبقي الحرف الصامت قبلها على حاله.',
      rows: [
        { char: 'а', roman: 'a', example: 'мама', sound: 'فتحة مثل أول «باب»' },
        { char: 'э', roman: 'e', example: 'это', sound: 'فتحة ممالة نحو الكسر' },
        { char: 'ы', roman: 'y', example: 'мы', sound: 'كسرة عميقة — انطق الكسرة ولسانك مسحوب إلى الخلف' },
        { char: 'о', roman: 'o', example: 'дом', sound: 'مثل واو «لو» (عند النبر فقط)' },
        { char: 'у', roman: 'u', example: 'утро', sound: 'ضمة صريحة، مثل واو «نور»' },
      ],
    },
    {
      title: 'الحركات — المجموعة اللينة',
      note: 'الأصوات نفسها، لكنها تُليّن الصامت قبلها (تضيف ياء خفية).',
      rows: [
        { char: 'я', roman: 'ya', example: 'яблоко', sound: '«يا» — ياء تليها فتحة' },
        { char: 'е', roman: 'e/ye', example: 'нет', sound: '«يِه» — ياء تليها فتحة ممالة' },
        { char: 'и', roman: 'i', example: 'мир', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'ё', roman: 'yo', example: 'ёлка', sound: '«يو» — ياء تليها واو «لو» (منبورة دائمًا)' },
        { char: 'ю', roman: 'yu', example: 'юг', sound: '«يو» — ياء تليها ضمة، مثل أول «يونيو»' },
      ],
    },
    {
      title: 'حروف صامتة تبدو مألوفة (وليست كذلك)',
      rows: [
        { char: 'в', roman: 'v', example: 'вода', sound: 'صوت v — فاء مجهورة (وليست باء)' },
        { char: 'н', roman: 'n', example: 'нос', sound: 'نون — رغم شبهها بحرف H' },
        { char: 'р', roman: 'r', example: 'рука', sound: 'راء عربية مكررة' },
        { char: 'с', roman: 's', example: 'сок', sound: 'سين (وليست كافًا)' },
        { char: 'у', roman: 'u', example: 'ум', sound: 'واو «نور» — تشبه y لكنها ليست ياء' },
        { char: 'х', roman: 'h/x', example: 'хлеб', sound: 'خاء عربية' },
      ],
    },
    {
      title: 'بقية الحروف الصامتة',
      rows: [
        { char: 'б', roman: 'b', example: 'брат', sound: 'باء' },
        { char: 'г', roman: 'g', example: 'год', sound: 'جيم قاهرية (g)' },
        { char: 'д', roman: 'd', example: 'да', sound: 'دال' },
        { char: 'ж', roman: 'zh', example: 'жить', sound: 'جيم شامية غير معطّشة' },
        { char: 'з', roman: 'z', example: 'зима', sound: 'زاي' },
        { char: 'й', roman: 'j', example: 'мой', sound: 'ياء انزلاقية، مثل ياء «بَيْت»' },
        { char: 'к', roman: 'k', example: 'кот', sound: 'كاف' },
        { char: 'л', roman: 'l', example: 'лампа', sound: 'لام' },
        { char: 'м', roman: 'm', example: 'мост', sound: 'ميم' },
        { char: 'п', roman: 'p', example: 'папа', sound: 'باء مهموسة بنفخة هواء (صوت p)' },
        { char: 'т', roman: 't', example: 'там', sound: 'تاء' },
        { char: 'ф', roman: 'f', example: 'фото', sound: 'فاء' },
        { char: 'ц', roman: 'c/ts', example: 'цирк', sound: '«تس» — تاء وسين ملتصقتان' },
        { char: 'ч', roman: 'ch', example: 'чай', sound: '«تش» مثل «تشاي»' },
        { char: 'ш', roman: 'sh', example: 'школа', sound: 'شين مفخمة' },
        { char: 'щ', roman: 'shch', example: 'щи', sound: 'شين لينة طويلة — «ششّ» ناعمة' },
      ],
    },
    {
      title: 'العلامتان الصامتتان',
      rows: [
        { char: 'ь', roman: "'", example: 'день', sound: 'علامة التليين — تُليّن الصامت قبلها (تضيف لمسة ياء)' },
        { char: 'ъ', roman: "''", example: 'объект', sound: 'علامة التقسية — وقفة صغيرة كهمزة بين السابقة والجذر' },
      ],
    },
    {
      title: 'الطباعة مقابل المائل (وخط اليد)',
      note: 'للسيريلية المطبوعة وجهان. في المائل — وأكثر في خط اليد — تتحول حروف إلى أشكال تشبه حروفًا لاتينية مختلفة. الحرف نفسه والصوت نفسه: قارن كل زوج قائم/مائل.',
      italics: true,
      rows: [
        { char: 'т', roman: 't', example: 'там', sound: 'تصير т المائلة بشكل m — وتبقى تاء' },
        { char: 'и', roman: 'i', example: 'мир', sound: 'تصير и المائلة بشكل u — وتبقى كسرة' },
        { char: 'й', roman: 'j', example: 'мой', sound: 'حرف й المائل هو شكل u نفسه مع علامة القوس فوقه' },
        { char: 'п', roman: 'p', example: 'папа', sound: 'تصير п المائلة بشكل n — ويبقى صوتها p' },
        { char: 'д', roman: 'd', example: 'да', sound: 'تصير д المائلة بشكل g — وتبقى دالًا' },
        { char: 'г', roman: 'g', example: 'год', sound: 'تصير г المائلة بشكل s معكوسة — وتبقى جيمًا قاهرية' },
      ],
    },
  ],
}

const greekAr: LanguageLetters = {
  intro: 'الأبجدية اليونانية — 24 حرفًا. حروف كثيرة مألوفة الشكل جاءت من هنا، فنصف الطريق مقطوع سلفًا.',
  sections: [
    {
      title: 'الحركات',
      note: 'لليونانية الحديثة خمسة أصوات حركات فقط؛ وتتقاسمها عدة هجاءات.',
      rows: [
        { char: 'α', roman: 'a', example: 'αγάπη', sound: 'فتحة مثل أول «باب»' },
        { char: 'ε', roman: 'e', example: 'ένα', sound: 'فتحة ممالة نحو الكسر' },
        { char: 'η', roman: 'h/i', example: 'ημέρα', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'ι', roman: 'i', example: 'ιδέα', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'ο', roman: 'o', example: 'όχι', sound: 'واو قصيرة مفتوحة' },
        { char: 'υ', roman: 'u/y', example: 'ύπνος', sound: 'كسرة — نعم، كسرة أيضًا' },
        { char: 'ω', roman: 'w', example: 'ώρα', sound: 'مثل ο تمامًا' },
      ],
    },
    {
      title: 'الحروف الصامتة',
      rows: [
        { char: 'β', roman: 'v/b', example: 'βιβλίο', sound: 'صوت v — فاء مجهورة (وليست باء!)' },
        { char: 'γ', roman: 'g', example: 'γάλα', sound: 'غين عربية لينة؛ وقبل e/i تصير ياء' },
        { char: 'δ', roman: 'd', example: 'δέκα', sound: 'ذال عربية (وليست دالًا!)' },
        { char: 'ζ', roman: 'z', example: 'ζωή', sound: 'زاي' },
        { char: 'θ', roman: 'th', example: 'θάλασσα', sound: 'ثاء عربية' },
        { char: 'κ', roman: 'k', example: 'καλά', sound: 'كاف' },
        { char: 'λ', roman: 'l', example: 'λέξη', sound: 'لام' },
        { char: 'μ', roman: 'm', example: 'μητέρα', sound: 'ميم' },
        { char: 'ν', roman: 'n', example: 'νερό', sound: 'نون (رغم شبهها بحرف v!)' },
        { char: 'ξ', roman: 'x', example: 'ξένος', sound: '«كس» — كاف تليها سين' },
        { char: 'π', roman: 'p', example: 'πατέρας', sound: 'باء مهموسة بنفخة هواء (صوت p)' },
        { char: 'ρ', roman: 'r', example: 'ρολόι', sound: 'راء بضربة خفيفة (رغم شبهها بحرف p!)' },
        { char: 'σ/ς', roman: 's', example: 'σπίτι', sound: 'سين؛ وشكل ς في آخر الكلمة فقط' },
        { char: 'τ', roman: 't', example: 'τρία', sound: 'تاء' },
        { char: 'φ', roman: 'f', example: 'φίλος', sound: 'فاء' },
        { char: 'χ', roman: 'ch', example: 'χέρι', sound: 'خاء عربية' },
        { char: 'ψ', roman: 'ps', example: 'ψωμί', sound: '«بس» — حتى في أول الكلمة' },
      ],
    },
    {
      title: 'الثنائيات الشائعة',
      note: 'حرفان بصوت واحد — احفظها وحدات.',
      rows: [
        { char: 'ου', roman: 'ou', example: 'ουρανός', sound: 'واو مد، مثل واو «نور»' },
        { char: 'αι', roman: 'ai', example: 'παιδί', sound: 'فتحة ممالة' },
        { char: 'ει/οι', roman: 'ei/oi', example: 'είναι', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'μπ', roman: 'mp', example: 'μπανάνα', sound: 'باء في أول الكلمة؛ «مب» في وسطها' },
        { char: 'ντ', roman: 'nt', example: 'ντομάτα', sound: 'دال في أول الكلمة؛ «ند» في وسطها' },
        { char: 'γγ/γκ', roman: 'gg/gk', example: 'αγγλικά', sound: 'جيم قاهرية / «نْ-غ»' },
      ],
    },
  ],
}

const arabicAr: LanguageLetters = {
  intro: 'الأبجدية العربية — 28 حرفًا تُكتب من اليمين إلى اليسار. تتصل الحروف وتتبدل أشكالها بحسب موضعها، والحركات القصيرة لا تُكتب غالبًا.',
  sections: [
    {
      title: 'كيف تتصل الحروف',
      note: 'العربية متصلة بطبيعتها: لمعظم الحروف أربعة أشكال — منفصل، وفي أول الكلمة، ووسطها، وآخرها — وتلتحم بجاراتها.',
      rows: [
        { char: 'م ح م د → محمد', roman: 'm-H-m-d', example: 'محمد', sound: 'الحروف نفسها متصلة: يتبدل شكل كل حرف بحسب موضعه' },
        { char: 'ب ـبـ ـب', roman: 'b', example: 'باب', sound: 'حرف واحد بثلاثة أشكال موصولة: بداية ووسط ونهاية' },
        { char: 'ا د ر ز و', roman: '(non-joiners)', example: 'دار', sound: 'ستة حروف لا تتصل بما بعدها أبدًا — تفرض فجوة وسط الكلمة' },
        { char: 'ل + ا → لا', roman: 'laa', example: 'سلام', sound: 'اللام والألف تلتحمان في رمز «لا» الخاص' },
      ],
    },
    {
      title: 'حروف المد وأنصاف الحركات',
      positions: true,
      rows: [
        { char: 'ا', roman: 'aa', example: 'باب', sound: 'ألف المد: فتحة طويلة كما في «باب»' },
        { char: 'و', roman: 'w/uu', example: 'نور', sound: 'الواو: صامتة، أو واو مد كما في «نور»' },
        { char: 'ي', roman: 'y/ii', example: 'كبير', sound: 'الياء: صامتة، أو ياء مد كما في «كبير»' },
      ],
    },
    {
      title: 'الحروف الأساسية',
      note: 'كل حرف معروض بأشكاله الأربعة: منفصلًا، وموصولًا في أول الكلمة ووسطها وآخرها.',
      positions: true,
      rows: [
        { char: 'ب', roman: 'b', example: 'بيت', sound: 'الباء، كما في «بيت»' },
        { char: 'ت', roman: 't', example: 'تفاح', sound: 'التاء، كما في «تفاح»' },
        { char: 'ث', roman: 'th', example: 'ثلاثة', sound: 'الثاء، كما في «ثلاثة»' },
        { char: 'ج', roman: 'j', example: 'جمل', sound: 'الجيم الفصحى المعطّشة، كما في «جمل»' },
        { char: 'د', roman: 'd', example: 'دار', sound: 'الدال، كما في «دار»' },
        { char: 'ذ', roman: 'dh', example: 'هذا', sound: 'الذال، كما في «هذا»' },
        { char: 'ر', roman: 'r', example: 'رجل', sound: 'الراء المكررة، كما في «رجل»' },
        { char: 'ز', roman: 'z', example: 'زيت', sound: 'الزاي، كما في «زيت»' },
        { char: 'س', roman: 's', example: 'سلام', sound: 'السين، كما في «سلام»' },
        { char: 'ش', roman: 'sh', example: 'شمس', sound: 'الشين، كما في «شمس»' },
        { char: 'ف', roman: 'f', example: 'فيل', sound: 'الفاء، كما في «فيل»' },
        { char: 'ك', roman: 'k', example: 'كتاب', sound: 'الكاف، كما في «كتاب»' },
        { char: 'ل', roman: 'l', example: 'ليل', sound: 'اللام، كما في «ليل»' },
        { char: 'م', roman: 'm', example: 'ماء', sound: 'الميم، كما في «ماء»' },
        { char: 'ن', roman: 'n', example: 'نار', sound: 'النون، كما في «نار»' },
        { char: 'ه', roman: 'h', example: 'هنا', sound: 'الهاء، كما في «هنا»' },
      ],
    },
    {
      title: 'الحروف الحلقية',
      note: 'مخارجها من الحلق — وهي من أخص سمات العربية.',
      positions: true,
      rows: [
        { char: 'ح', roman: 'H / 7', example: 'حب', sound: 'الحاء: هاء مهموسة من وسط الحلق، كما في «حب»' },
        { char: 'خ', roman: 'kh / 5', example: 'خبز', sound: 'الخاء: احتكاكية من أقصى الحنك، كما في «خبز»' },
        { char: 'ع', roman: '3', example: 'عين', sound: 'العين: من وسط الحلق مع ضغطة، كما في «عين»' },
        { char: 'غ', roman: 'gh', example: 'غرب', sound: 'الغين: أخت الخاء المجهورة، كما في «غرب»' },
        { char: 'ق', roman: 'q', example: 'قلب', sound: 'القاف: من أقصى اللسان مع اللهاة، كما في «قلب»' },
        { char: 'ء', roman: "2 / '", example: 'سؤال', sound: 'الهمزة: وقفة حنجرية، كما في «سؤال»' },
      ],
    },
    {
      title: 'حروف الإطباق الأربعة',
      note: 'أخوات مفخمة للتاء والدال والسين والذال — يتقعر اللسان وتتفخم الكلمة كلها.',
      positions: true,
      rows: [
        { char: 'ص', roman: 'S', example: 'صباح', sound: 'الصاد: سين مفخمة مطبقة' },
        { char: 'ض', roman: 'D', example: 'ضوء', sound: 'الضاد: دال مفخمة مطبقة' },
        { char: 'ط', roman: 'T', example: 'طعام', sound: 'الطاء: تاء مفخمة مطبقة' },
        { char: 'ظ', roman: 'Z', example: 'ظهر', sound: 'الظاء: ذال مفخمة مطبقة' },
      ],
    },
    {
      title: 'الحركات القصيرة',
      note: 'علامات صغيرة فوق الحرف أو تحته — لا تُكتب عادة خارج نصوص التعليم.',
      rows: [
        { char: 'ـَ', roman: 'a', example: 'فَتَحَ', sound: 'الفتحة، كما في «فَتَحَ»' },
        { char: 'ـِ', roman: 'i', example: 'بِنت', sound: 'الكسرة، كما في «بِنت»' },
        { char: 'ـُ', roman: 'u', example: 'كُتُب', sound: 'الضمة، كما في «كُتُب»' },
        { char: 'ـّ', roman: '(double)', example: 'مُدَرِّس', sound: 'الشدة — يُضعَّف الحرف ويُمسك ضعف مدته' },
      ],
    },
  ],
}

const hindiAr: LanguageLetters = {
  intro: 'الديوناغرية — كل حرف صامت يحمل فتحة مدمجة؛ وعلامات الحركات (الماترا) تحل محلها. أبرز الأصوات: الحروف الالتوائية (اللسان مثنيّ إلى الخلف) مقابل الأسنانية (اللسان على الأسنان)، وأزواج بنفخة هواء زائدة.',
  sections: [
    {
      title: 'كيف تتركب الحروف',
      note: 'الديوناغرية تبني مقاطع: علامات الحركات تلتصق بالحروف، والفيراما (्) تلحم الحروف في عناقيد.',
      rows: [
        { char: 'क + ा → का', roman: 'k + aa', example: 'काम', sound: 'علامة الحركة (ماترا) تحل محل الفتحة المدمجة' },
        { char: 'क + ि → कि', roman: 'k + i', example: 'किताब', sound: 'علامة الكسرة تُكتب قبل حرفها لا بعده' },
        { char: 'स + ् + त → स्त', roman: 's+t', example: 'नमस्ते', sound: 'الفيراما تحذف الفتحة وتدمج الحرفين عنقودًا واحدًا' },
        { char: 'क + ् + ष → क्ष', roman: 'ksh', example: 'क्षमा', sound: 'بعض العناقيد لها شكل جديد كليًّا — احفظ الشائع منها بالنظر' },
        { char: 'र special', roman: 'r', example: 'कर्म / प्रेम', sound: 'الراء فوق العنقود إذا جاءت أولًا (कर्म)، وشرطة صغيرة تحته إذا جاءت ثانية (प्रेम)' },
      ],
    },
    {
      title: 'الحركات المستقلة',
      note: 'تُستعمل في أول الكلمة؛ وداخل الكلمات تصير ماترات (القسم التالي).',
      rows: [
        { char: 'अ', roman: 'a', example: 'अब', sound: 'فتحة مطموسة قصيرة' },
        { char: 'आ', roman: 'aa', example: 'आम', sound: 'ألف مد، كما في «باب»' },
        { char: 'इ', roman: 'i', example: 'इधर', sound: 'كسرة قصيرة' },
        { char: 'ई', roman: 'ii', example: 'ईद', sound: 'ياء مد، مثل ياء «فيل»' },
        { char: 'उ', roman: 'u', example: 'उधर', sound: 'ضمة قصيرة' },
        { char: 'ऊ', roman: 'uu', example: 'ऊपर', sound: 'واو مد، مثل واو «نور»' },
        { char: 'ए', roman: 'e', example: 'एक', sound: 'إمالة ممدودة بلا انزلاق' },
        { char: 'ऐ', roman: 'ai', example: 'ऐनक', sound: 'فتحة مفتوحة جدًا نحو الإمالة' },
        { char: 'ओ', roman: 'o', example: 'ओर', sound: 'مثل واو «لو» بلا انزلاق' },
        { char: 'औ', roman: 'au', example: 'औरत', sound: 'واو مفتوحة عريضة' },
      ],
    },
    {
      title: 'الحركات نفسها ماترات',
      note: 'الحرف क هو الحامل هنا. الفتحة المدمجة अ لا تحتاج إلى علامة.',
      rows: [
        { char: 'का', roman: 'kaa', example: 'काम', sound: 'كاف + ألف مد' },
        { char: 'कि', roman: 'ki', example: 'किताब', sound: 'كاف + كسرة (العلامة تُكتب قبل الحرف)' },
        { char: 'की', roman: 'kii', example: 'की', sound: 'كاف + ياء مد' },
        { char: 'कु', roman: 'ku', example: 'कुछ', sound: 'كاف + ضمة' },
        { char: 'कू', roman: 'kuu', example: 'कूद', sound: 'كاف + واو مد' },
        { char: 'के', roman: 'ke', example: 'के', sound: 'كاف + إمالة' },
        { char: 'कै', roman: 'kai', example: 'कैसा', sound: 'كاف + فتحة مفتوحة' },
        { char: 'को', roman: 'ko', example: 'को', sound: 'كاف + واو' },
        { char: 'कौ', roman: 'kau', example: 'कौन', sound: 'كاف + واو مفتوحة' },
        { char: 'कं', roman: 'kaM', example: 'कंघी', sound: 'غنّة بعد الحركة (أنوسفارا)' },
      ],
    },
    {
      title: 'الحروف الصامتة — أزواج النفخة',
      note: 'الثاني من كل زوج يضيف نفخة هواء (ارفع كفك أمام فمك — ستشعر بها).',
      rows: [
        { char: 'क / ख', roman: 'k / kh', example: 'खाना', sound: 'كاف بلا نفخة، ثم كاف + نَفَس' },
        { char: 'ग / घ', roman: 'g / gh', example: 'घर', sound: 'جيم قاهرية (g)، ثم بنَفَس' },
        { char: 'च / छ', roman: 'ch / chh', example: 'छह', sound: '«تش»، ثم بنَفَس' },
        { char: 'ज / झ', roman: 'j / jh', example: 'झील', sound: 'جيم معطّشة، ثم بنَفَس' },
        { char: 'प / फ', roman: 'p / ph', example: 'फल', sound: 'باء مهموسة (p)، ثم بنَفَس' },
        { char: 'ब / भ', roman: 'b / bh', example: 'भाई', sound: 'باء، ثم بنَفَس' },
      ],
    },
    {
      title: 'الالتوائية مقابل الأسنانية — الفرق الكبير',
      note: 'الالتوائية: اللسان مثنيّ إلى سقف الحنك. الأسنانية: اللسان يلمس الأسنان — كالتاء والدال العربيتين تمامًا.',
      rows: [
        { char: 'ट / ठ', roman: 'T / Th', example: 'टमाटर', sound: 'تاء التوائية (بلا نفخة / بنفخة)' },
        { char: 'ड / ढ', roman: 'D / Dh', example: 'डर', sound: 'دال التوائية (بلا نفخة / بنفخة)' },
        { char: 'ण', roman: 'N', example: 'बाण', sound: 'نون التوائية' },
        { char: 'त / थ', roman: 't / th', example: 'तीन', sound: 'تاء أسنانية كالتاء العربية (بلا نفخة / بنفخة)' },
        { char: 'द / ध', roman: 'd / dh', example: 'दो', sound: 'دال أسنانية كالدال العربية (بلا نفخة / بنفخة)' },
        { char: 'न', roman: 'n', example: 'नाम', sound: 'نون' },
        { char: 'ड़ / ढ़', roman: 'R / Rh', example: 'लड़का', sound: 'راء مخفوقة — اللسان يهبط صافعًا من وضع الالتواء' },
      ],
    },
    {
      title: 'البقية',
      rows: [
        { char: 'म', roman: 'm', example: 'माँ', sound: 'ميم' },
        { char: 'य', roman: 'y', example: 'यह', sound: 'ياء' },
        { char: 'र', roman: 'r', example: 'रात', sound: 'راء بضربة خفيفة' },
        { char: 'ल', roman: 'l', example: 'लाल', sound: 'لام' },
        { char: 'व', roman: 'v/w', example: 'वह', sound: 'بين الـ v والواو' },
        { char: 'श / ष', roman: 'sh / Sh', example: 'शहर', sound: 'شين' },
        { char: 'स', roman: 's', example: 'सात', sound: 'سين' },
        { char: 'ह', roman: 'h', example: 'हाँ', sound: 'هاء' },
      ],
    },
    {
      title: 'حروف النقطة (أصوات دخيلة)',
      note: 'نقطة تحت الحرف علامة على أصوات فارسية-عربية — وهي أصواتك أنت.',
      rows: [
        { char: 'ज़', roman: 'z', example: 'ज़रूर', sound: 'زاي عربية' },
        { char: 'फ़', roman: 'f', example: 'फ़ोन', sound: 'فاء عربية' },
        { char: 'क़', roman: 'q', example: 'क़लम', sound: 'قاف عربية' },
        { char: 'ख़ / ग़', roman: 'kh / gh', example: 'ख़बर', sound: 'خاء وغين عربيتان' },
      ],
    },
  ],
}

const thaiAr: LanguageLetters = {
  intro: 'الخط التايلندي: 44 حرفًا صامتًا في ثلاث فئات (الفئة + علامة النغمة تحددان النغمة)، وحركات تلتصق حول الحرف، ولا مسافات بين الكلمات.',
  sections: [
    {
      title: 'كيف تتركب الحروف',
      note: 'الحركات تلتف حول حرفها — قبله أو بعده أو فوقه أو تحته — وعلامات النغمة تتراكب في الأعلى.',
      rows: [
        { char: 'ก + า → กา', roman: 'k + aa', example: 'กาแฟ', sound: 'هذه الحركة تلي الحرف' },
        { char: 'ก + ิ → กิ', roman: 'k + i', example: 'กิน', sound: 'هذه الحركة تجلس فوق الحرف' },
        { char: 'ก + ุ → กุ', roman: 'k + u', example: 'กุ้ง', sound: 'هذه الحركة تتدلى تحت الحرف' },
        { char: 'เ + ก → เก', roman: 'k + e', example: 'เกาะ', sound: 'هذه الحركة تُكتب قبل الحرف الذي تُنطق بعده' },
        { char: 'เ-ีย, เ-ือ', roman: 'ia, uea', example: 'เมีย', sound: 'الحركات المركبة تحيط بالحرف من جهتين أو ثلاث' },
        { char: 'ก่ ก้ ก๊ ก๋', roman: 'tones', example: 'ไม่', sound: 'أربع علامات نغمة تتراكب فوق؛ وفئة الحرف تحدد معناها' },
      ],
    },
    {
      title: 'حروف الاستعمال اليومي (الفئة الوسطى)',
      rows: [
        { char: 'ก', roman: 'g/k', example: 'ไก่', sound: 'جيم قاهرية (كاف بلا نفخة)' },
        { char: 'จ', roman: 'j', example: 'จาน', sound: 'جيم معطّشة أكثر حدة' },
        { char: 'ด', roman: 'd', example: 'เด็ก', sound: 'دال' },
        { char: 'ต', roman: 'dt', example: 'ตา', sound: 'بين الدال والتاء — تاء بلا نفخة' },
        { char: 'บ', roman: 'b', example: 'บ้าน', sound: 'باء' },
        { char: 'ป', roman: 'bp', example: 'ปลา', sound: 'بين الباء والباء المهموسة — صوت p بلا نفخة' },
        { char: 'อ', roman: '(silent)', example: 'อาหาร', sound: 'الحرف الصامت الذي يحمل الحركات المنفردة' },
      ],
    },
    {
      title: 'الحروف المنفوسة (زوجا الفئتين العليا والدنيا)',
      note: 'الصوت نفسه بفئة مختلفة — والفئة تغيّر نغمة المقطع.',
      rows: [
        { char: 'ข / ค', roman: 'kh', example: 'ขาว / ควาย', sound: 'كاف + نفخة (فئة عليا / دنيا)' },
        { char: 'ถ / ท', roman: 'th', example: 'ถนน / ทำ', sound: 'تاء + نفخة (عليا / دنيا)' },
        { char: 'ผ / พ', roman: 'ph', example: 'ผม / พ่อ', sound: 'باء مهموسة (p) + نفخة — وليست فاء أبدًا! (عليا / دنيا)' },
        { char: 'ฝ / ฟ', roman: 'f', example: 'ฝน / ไฟ', sound: 'فاء (عليا / دنيا)' },
        { char: 'ส / ซ', roman: 's', example: 'สวย / ซ้าย', sound: 'سين (عليا / دنيا)' },
        { char: 'ห / ฮ', roman: 'h', example: 'หก / ฮา', sound: 'هاء (عليا / دنيا)؛ وحرف ห يرفع فئة الحرف التالي بصمت' },
      ],
    },
    {
      title: 'الرنينية والبقية',
      rows: [
        { char: 'ม', roman: 'm', example: 'แม่', sound: 'ميم' },
        { char: 'น / ณ', roman: 'n', example: 'น้ำ', sound: 'نون' },
        { char: 'ง', roman: 'ng', example: 'งู', sound: 'نون خيشومية مثل النون المخفاة قبل الكاف — حتى في أول الكلمة' },
        { char: 'ร', roman: 'r', example: 'รถ', sound: 'راء مكررة (تصير لامًا في الكلام العفوي غالبًا)' },
        { char: 'ล', roman: 'l', example: 'ลิง', sound: 'لام' },
        { char: 'ว', roman: 'w', example: 'วัน', sound: 'واو' },
        { char: 'ย / ญ', roman: 'y', example: 'ยา', sound: 'ياء' },
        { char: 'ช', roman: 'ch', example: 'ช้าง', sound: '«تش» + نفخة' },
      ],
    },
    {
      title: 'الحركات الأساسية (معروضة على ก)',
      note: 'القصير مقابل الطويل يغيّر المعنى — مُدَّ الطويلة بوضوح.',
      rows: [
        { char: 'กะ / กา', roman: 'a / aa', example: 'มา', sound: 'فتحة قصيرة / ألف مد كما في «باب»' },
        { char: 'กิ / กี', roman: 'i / ii', example: 'มี', sound: 'كسرة قصيرة / ياء مد' },
        { char: 'กุ / กู', roman: 'u / uu', example: 'ดู', sound: 'ضمة قصيرة / واو مد' },
        { char: 'เกะ / เก', roman: 'e', example: 'เย็น', sound: 'فتحة ممالة قصيرة / إمالة ممدودة' },
        { char: 'โกะ / โก', roman: 'o', example: 'โต', sound: 'واو قصيرة / ممدودة' },
        { char: 'ไก / ใก', roman: 'ai', example: 'ไป', sound: 'فتحة تليها ياء ساكنة، مثل «بَيْت» — هجاءان لصوت واحد' },
        { char: 'เกา', roman: 'ao', example: 'เก้า', sound: 'فتحة تليها واو ساكنة، مثل «يَوْم»' },
        { char: 'กือ', roman: 'ue', example: 'มือ', sound: 'ضمة بشفتين مبسوطتين — لا نظير لها' },
      ],
    },
    {
      title: 'النغمات الخمس',
      note: 'المقطع نفسه بخمسة معانٍ. النغمة تأتي من فئة الحرف + علامة النغمة + نوع المقطع.',
      rows: [
        { char: 'มา (وسطى)', roman: 'maa', example: 'มา', sound: 'طبقة مستوية — بمعنى «يأتي»' },
        { char: 'หม่า (منخفضة)', roman: 'màa', example: 'ไม่', sound: 'تبدأ منخفضة وتبقى منخفضة' },
        { char: 'ม้า (عالية… هابطة)', roman: 'máa', example: 'ม้า', sound: 'نغمة عالية — بمعنى «حصان»' },
        { char: 'หม้า (هابطة)', roman: 'mâa', example: 'บ้าน', sound: 'تهبط من عالٍ إلى منخفض' },
        { char: 'หมา (صاعدة)', roman: 'mǎa', example: 'หมา', sound: 'تنخفض ثم تصعد — بمعنى «كلب» (انتبه لزوج الحصان/الكلب!)' },
      ],
    },
  ],
}

const koreanAr: LanguageLetters = {
  intro: 'الهانغل — 24 حرفًا أساسيًا تتجمع في مكعبات مقطعية. اختُرع عام 1443 ليُتعلم في صباح واحد؛ بل إن أشكال الحروف ترسم الفم وهو يصنع الصوت.',
  sections: [
    {
      title: 'كيف تتجمع الحروف',
      note: 'الحروف تتراكب في مكعبات مقطعية: صامت + حركة، مع صامت ختامي اختياري (받침) في الأسفل. كلمة 한국 ستة حروف في مكعبين.',
      rows: [
        { char: 'ㅎ + ㅏ + ㄴ → 한', roman: 'h + a + n', example: '한국', sound: 'الصامت يسارًا، والحركة العمودية يمينًا، والحرف الختامي في الأسفل' },
        { char: 'ㄱ + ㅜ + ㄱ → 국', roman: 'g + u + k', example: '한국', sound: 'الحركات الأفقية تُكتب تحت الصامت الأول' },
        { char: 'ㅅ + ㅏ → 사', roman: 's + a', example: '사람', sound: 'بلا حرف ختامي — صامت + حركة فقط' },
        { char: 'ㅇ + ㅜ → 우', roman: '(silent) + u', example: '우유', sound: 'الحرف ㅇ حاملٌ صامت حين يبدأ المكعب بحركة' },
        { char: 'ㅂ + ㅏ + ㅂ → 밥', roman: 'b + a + p', example: '밥', sound: 'الحرف الختامي ㅂ (받침) يغلق المقطع' },
        { char: '받침 rule', roman: 'finals', example: '있다', sound: 'سبعة أصوات فقط تختم المكعب: k n t l m p ng — الهجاء يحفظ الحرف والفم يبسّطه' },
      ],
    },
    {
      title: 'الحروف الصامتة البسيطة',
      rows: [
        { char: 'ㄱ', roman: 'g/k', example: '가다', sound: 'بين الجيم القاهرية والكاف — أقرب إلى g في أول الكلمة' },
        { char: 'ㄴ', roman: 'n', example: '나', sound: 'نون' },
        { char: 'ㄷ', roman: 'd/t', example: '돈', sound: 'بين الدال والتاء' },
        { char: 'ㄹ', roman: 'r/l', example: '물', sound: 'راء بضربة خفيفة بين الحركات؛ لام في آخر المكعب' },
        { char: 'ㅁ', roman: 'm', example: '몸', sound: 'ميم' },
        { char: 'ㅂ', roman: 'b/p', example: '밥', sound: 'بين الباء والباء المهموسة (p)' },
        { char: 'ㅅ', roman: 's', example: '사람', sound: 'سين؛ وشين قبل ㅣ' },
        { char: 'ㅇ', roman: '-/ng', example: '강', sound: 'صامت في البداية؛ نون خيشومية (ng) في النهاية' },
        { char: 'ㅈ', roman: 'j', example: '집', sound: 'بين الجيم المعطّشة و«تش»' },
        { char: 'ㅎ', roman: 'h', example: '하다', sound: 'هاء' },
      ],
    },
    {
      title: 'الحروف المنفوسة (بنفخة هواء)',
      note: 'كل منها حرف بسيط بشطبة زائدة ونفخة زائدة.',
      rows: [
        { char: 'ㅋ', roman: 'k', example: '코', sound: 'كاف بنفخة قوية (ㄱ + هواء)' },
        { char: 'ㅌ', roman: 't', example: '토요일', sound: 'تاء بنفخة قوية (ㄷ + هواء)' },
        { char: 'ㅍ', roman: 'p', example: '팔', sound: 'باء مهموسة (p) بنفخة قوية (ㅂ + هواء)' },
        { char: 'ㅊ', roman: 'ch', example: '차', sound: '«تش» بنفخة قوية (ㅈ + هواء)' },
      ],
    },
    {
      title: 'الحروف المشدودة (مضعّفة بلا هواء)',
      note: 'انطقها بحلق مشدود وبلا أي نفخة — كأن على الحرف شدة.',
      rows: [
        { char: 'ㄲ', roman: 'kk', example: '까만', sound: 'كاف مشدودة بلا نفخة' },
        { char: 'ㄸ', roman: 'tt', example: '딸', sound: 'تاء مشدودة بلا نفخة' },
        { char: 'ㅃ', roman: 'pp', example: '빵', sound: 'باء مهموسة مشدودة بلا نفخة' },
        { char: 'ㅆ', roman: 'ss', example: '쌀', sound: 'سين مشدودة' },
        { char: 'ㅉ', roman: 'jj', example: '짜다', sound: 'جيم مشدودة بلا نفخة' },
      ],
    },
    {
      title: 'الحركات الأساسية',
      rows: [
        { char: 'ㅏ', roman: 'a', example: '아빠', sound: 'فتحة مثل أول «باب»' },
        { char: 'ㅓ', roman: 'eo', example: '어머니', sound: 'فتحة مطموسة مفخمة — بين الفتحة والواو المفتوحة' },
        { char: 'ㅗ', roman: 'o', example: '오늘', sound: 'مثل واو «لو» بشفتين مدوّرتين' },
        { char: 'ㅜ', roman: 'u', example: '우리', sound: 'واو مد، مثل واو «نور»' },
        { char: 'ㅡ', roman: 'eu', example: '그', sound: 'ضمة بشفتين مبسوطتين تمامًا — انطق الواو وأنت مبتسم' },
        { char: 'ㅣ', roman: 'i', example: '이름', sound: 'كسرة صريحة، مثل ياء «فيل»' },
        { char: 'ㅐ', roman: 'ae', example: '개', sound: 'فتحة ممالة (تطابق ㅔ في الكلام الحديث)' },
        { char: 'ㅔ', roman: 'e', example: '세 시', sound: 'فتحة ممالة' },
      ],
    },
    {
      title: 'حركات الياء والواو',
      note: 'شطبة زائدة تضيف ياءً في الأول؛ وجمع حركتين يصنع واوًا.',
      rows: [
        { char: 'ㅑ ㅕ ㅛ ㅠ', roman: 'ya yeo yo yu', example: '야구, 여자', sound: 'الحركات الأربع الأساسية مسبوقة بياء' },
        { char: 'ㅒ ㅖ', roman: 'yae ye', example: '예', sound: '«يِه» مثل أول «يد»' },
        { char: 'ㅘ ㅝ', roman: 'wa wo', example: '와요, 뭐', sound: '«وا» مثل «واحة»، و«وُه» مفتوحة' },
        { char: 'ㅙ ㅞ ㅚ', roman: 'wae we oe', example: '왜, 회사', sound: 'الثلاثة تُنطق «وِه» في الكلام الحديث' },
        { char: 'ㅟ', roman: 'wi', example: '귀', sound: '«وي» — واو تليها ياء' },
        { char: 'ㅢ', roman: 'ui', example: '의사', sound: 'ضمة مبسوطة تنزلق إلى ياء؛ وكثيرًا ما تُنطق ياءً فقط' },
      ],
    },
  ],
}

const hebrewAr: LanguageLetters = {
  intro: 'الأبجدية العبرية — 22 حرفًا من اليمين إلى اليسار، وهي قريبة جدًا من العربية: معظم الحروف لها نظير مباشر. للحرف شكل واحد (خمسة تتغير في آخر الكلمة)، والحركات لا تُكتب غالبًا.',
  sections: [
    {
      title: 'حروف لها نظير عربي مباشر',
      rows: [
        { char: 'ב', roman: 'b', example: 'בית', sound: 'مثل الباء (ب)؛ بلا نقطة داخلية تلفظ v' },
        { char: 'ג', roman: 'g', example: 'גדול', sound: 'مثل الجيم المصرية (g)' },
        { char: 'ד', roman: 'd', example: 'דג', sound: 'مثل الدال (د)' },
        { char: 'ה', roman: 'h', example: 'הר', sound: 'مثل الهاء (ه)؛ صامتة في آخر الكلمة' },
        { char: 'ו', roman: 'v', example: 'ורד', sound: 'حرف v؛ ويكتب أيضًا الواو الطويلة (و)' },
        { char: 'ז', roman: 'z', example: 'זמן', sound: 'مثل الزاي (ز)' },
        { char: 'י', roman: 'y', example: 'יד', sound: 'مثل الياء (ي)؛ ويكتب الكسرة الطويلة' },
        { char: 'כ', roman: 'k', example: 'כלב', sound: 'مثل الكاف (ك)؛ بلا نقطة داخلية مثل الخاء' },
        { char: 'ל', roman: 'l', example: 'לילה', sound: 'مثل اللام (ل)' },
        { char: 'מ', roman: 'm', example: 'מים', sound: 'مثل الميم (م)' },
        { char: 'נ', roman: 'n', example: 'נר', sound: 'مثل النون (ن)' },
        { char: 'ס', roman: 's', example: 'ספר', sound: 'مثل السين (س)' },
        { char: 'פ', roman: 'p', example: 'פרח', sound: 'حرف p؛ بلا نقطة داخلية مثل الفاء (ف)' },
        { char: 'ק', roman: 'q', example: 'קטן', sound: 'أصلها القاف (ق)؛ تلفظ اليوم كافًا مثل כ' },
        { char: 'ר', roman: 'r', example: 'ראש', sound: 'راء مُغَرغَرة مثل الراء الفرنسية — لا تُرَقرَق' },
        { char: 'ש', roman: 'sh', example: 'שלום', sound: 'مثل الشين (ش)؛ وبنقطة يسرى تلفظ سينًا' },
        { char: 'ת', roman: 't', example: 'תודה', sound: 'مثل التاء (ت)' },
      ],
    },
    {
      title: 'الأصوات التي تغيّرت عن نظيرها',
      rows: [
        { char: 'א', roman: 'a', example: 'אבא', sound: 'نظير الهمزة/الألف: صامتة، كرسي للحركة' },
        { char: 'ח', roman: 'ch', example: 'חלב', sound: 'أصلها الحاء، لكنها تلفظ اليوم خاءً (خ)' },
        { char: 'ט', roman: 'T', example: 'טוב', sound: 'أصلها الطاء (ط)؛ تلفظ اليوم تاءً عادية' },
        { char: 'ע', roman: "'", example: 'עין', sound: 'نظير العين (ع)؛ معظم المتكلمين اليوم يسقطونها' },
        { char: 'צ', roman: 'ts', example: 'ציפור', sound: 'أصلها الصاد (ص)؛ تلفظ اليوم «تس»' },
      ],
    },
    {
      title: 'الأشكال النهائية',
      note: 'خمسة حروف يتغير شكلها في آخر الكلمة — كالتاء المربوطة عندنا: الحرف نفسه والصوت نفسه. لوحة المفاتيح تتكفل بذلك.',
      rows: [
        { char: 'כ → ך', roman: 'k', example: 'מלך', sound: 'الكاف في آخر الكلمة' },
        { char: 'מ → ם', roman: 'm', example: 'מים', sound: 'الميم في آخر الكلمة' },
        { char: 'נ → ן', roman: 'n', example: 'בן', sound: 'النون في آخر الكلمة' },
        { char: 'פ → ף', roman: 'p/f', example: 'סוף', sound: 'الفاء/p في آخر الكلمة' },
        { char: 'צ → ץ', roman: 'ts', example: 'ארץ', sound: 'التسادي في آخر الكلمة' },
      ],
    },
    {
      title: 'أين ذهبت الحركات',
      note: 'كما في العربية تمامًا: الحركات القصيرة لا تُكتب في النص العادي، وحروف العلة الطويلة تُكتب بـ ו و־י. النقاط (نيقود) تظهر فقط في كتب الأطفال والشعر والمعاجم — مثل التشكيل عندنا.',
      rows: [
        { char: 'וֹ / וּ', roman: 'o / u', example: 'שלום', sound: 'الواو حين تعمل حرف علة: ضمة أو واو طويلة' },
        { char: 'י', roman: 'i', example: 'דין', sound: 'الياء حين تعمل حرف علة: كسرة طويلة' },
        { char: 'בַ בֶ בִ', roman: '(niqqud)', example: 'בַּיִת', sound: 'علامات الحركات تحت الحرف — تُهمل غالبًا كالتشكيل' },
      ],
    },
  ],
}

const persianAr: LanguageLetters = {
  intro: 'تكتب الفارسية بالحرف العربي نفسه — 32 حرفًا من اليمين إلى اليسار — لكن نطقها أبسط بكثير: لا إطباق ولا حلقيات ثقيلة، وعدة حروف عربية اندمجت أصواتها في س وز وت وهـ عادية.',
  sections: [
    {
      title: 'الحروف الأربعة الخاصة بالفارسية',
      note: 'أضيفت إلى الحرف العربي لأصوات لا توجد في العربية.',
      positions: true,
      rows: [
        { char: 'پ', roman: 'p', example: 'پدر', sound: 'باء مهموسة p — باء بثلاث نقاط' },
        { char: 'چ', roman: 'ch', example: 'چای', sound: 'مثل «تش» في تشاي — جيم بثلاث نقاط' },
        { char: 'ژ', roman: 'zh', example: 'ژاله', sound: 'مثل الجيم الشامية غير المعطشة (j الفرنسية) — زاي بثلاث نقاط' },
        { char: 'گ', roman: 'g', example: 'گل', sound: 'مثل الجيم المصرية g — كاف بخط إضافي' },
      ],
    },
    {
      title: 'حروف تنطق كما تعرفها',
      positions: true,
      rows: [
        { char: 'ب', roman: 'b', example: 'باب', sound: 'الباء كما هي' },
        { char: 'ت', roman: 't', example: 'تهران', sound: 'التاء كما هي' },
        { char: 'ج', roman: 'j', example: 'جان', sound: 'الجيم الفصحى المعطشة' },
        { char: 'د', roman: 'd', example: 'دست', sound: 'الدال كما هي' },
        { char: 'ر', roman: 'r', example: 'روز', sound: 'الراء كما هي' },
        { char: 'ز', roman: 'z', example: 'زبان', sound: 'الزاي كما هي' },
        { char: 'س', roman: 's', example: 'سلام', sound: 'السين كما هي' },
        { char: 'ش', roman: 'sh', example: 'شب', sound: 'الشين كما هي' },
        { char: 'ف', roman: 'f', example: 'فردا', sound: 'الفاء كما هي' },
        { char: 'ک', roman: 'k', example: 'کتاب', sound: 'الكاف — تكتب ک بلا همزة صغيرة' },
        { char: 'ل', roman: 'l', example: 'لب', sound: 'اللام كما هي' },
        { char: 'م', roman: 'm', example: 'مادر', sound: 'الميم كما هي' },
        { char: 'ن', roman: 'n', example: 'نان', sound: 'النون كما هي' },
        { char: 'ه', roman: 'h', example: 'هفت', sound: 'الهاء كما هي' },
        { char: 'و', roman: 'v', example: 'وقت', sound: 'تلفظ v لا w؛ وتكتب الواو الطويلة أيضًا' },
        { char: 'ی', roman: 'y', example: 'یک', sound: 'الياء — تكتب ی بلا نقطتين' },
      ],
    },
    {
      title: 'التوائم المستعارة',
      note: 'الكلمات العربية المستعارة حافظت على رسمها، لكن الفارسية وحّدت الأصوات — هذه الحروف تلفظ س أو ز أو ت أو هـ أو ق عادية تمامًا. الرسم يفرّق الكلمات؛ الفم لا يفعل شيئًا خاصًا.',
      positions: true,
      rows: [
        { char: 'ث', roman: 's', example: 'ثانیه', sound: 'سين عادية — لا ثاء في الفارسية' },
        { char: 'ص', roman: 's', example: 'صبح', sound: 'سين عادية — لا إطباق' },
        { char: 'ذ', roman: 'z', example: 'ذهن', sound: 'زاي عادية — لا ذال' },
        { char: 'ض', roman: 'z', example: 'ضعیف', sound: 'زاي عادية' },
        { char: 'ظ', roman: 'z', example: 'ظهر', sound: 'زاي عادية' },
        { char: 'ط', roman: 't', example: 'طلا', sound: 'تاء عادية — لا إطباق' },
        { char: 'ح', roman: 'h', example: 'حال', sound: 'هاء عادية — لا حاء حلقية' },
        { char: 'ع', roman: "'", example: 'عشق', sound: 'سكتة خفيفة أو لا شيء — أخف كثيرًا من العين العربية' },
        { char: 'غ', roman: 'gh', example: 'غذا', sound: 'غين مغرغرة — وتلتقي بالقاف في النطق' },
        { char: 'ق', roman: 'q / gh', example: 'قلب', sound: 'تلفظ غينًا عند معظم المتكلمين' },
      ],
    },
    {
      title: 'الحركات ونصف المسافة',
      rows: [
        { char: 'آ', roman: 'aa', example: 'آب', sound: 'ألف ممدودة داكنة تميل نحو الواو — ألف بمدّة' },
        { char: 'ا', roman: 'a', example: 'اسم', sound: 'كرسي الحركة في أول الكلمة' },
        { char: 'و / ی', roman: 'oo / ee', example: 'دور، شیر', sound: 'الواو والياء الطويلتان' },
        { char: 'ــِـ ــَـ ــُـ', roman: 'e a o', example: 'دَر', sound: 'الحركات القصيرة — لا تكتب غالبًا، كما في العربية' },
        { char: '‌ (نیم‌فاصله)', roman: '-', example: 'می‌روم', sound: 'نصف المسافة (ZWNJ): تُبقي می ملتصقة-منفصلة عن فعلها — تُكتب بالشرطة -' },
      ],
    },
  ],
}

export const LETTERS_AR: Record<string, LanguageLetters> = {
  he: hebrewAr,
  fa: persianAr,
  es: spanishAr,
  fr: frenchAr,
  de: germanAr,
  it: italianAr,
  ca: catalanAr,
  pt: portugueseAr,
  ro: romanianAr,
  tr: turkishAr,
  sw: swahiliAr,
  yo: yorubaAr,
  ha: hausaAr,
  xh: xhosaAr,
  mi: maoriAr,
  jam: jamaicanAr,
  en: englishAr,
  nl: dutchAr,
  ru: russianAr,
  el: greekAr,
  ar: arabicAr,
  hi: hindiAr,
  th: thaiAr,
  ko: koreanAr,
}
