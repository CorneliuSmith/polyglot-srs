# The 65 committed-file defects, repaired — 7 September 2026

The judged twin pass (`2026-09-07-unmarked-twins.md`) found 65 rows where the COMMITTED file, not production, carried the worse form: the unaccented spelling, or a bare inflection stub where production had the lemma. A writer for each language drafted the exact row edit against that course's guide; a second reader refused any edit that would make the file worse.

| | rows |
|---|---:|
| drafted | 65 |
| **applied** | 56 |
| refused by the second reader | 9 |
| fields corrected before applying | 8 |

Every new spelling was already a production row (checked read-only, 56 of 56), so **no re-seed is needed**: the next `reconcile --apply` corrects each definition and retires the old spelling. 55 old spellings went to `vocab_exclusions.tsv`.

## What the second reader refused, and why it matters

Seven of the nine refusals are one Romanian fact. A feminine noun ending `-ă` and a first-conjugation verb infinitive ending `-a` fold to the same string once the mark is stripped, so `uzină` (works, plant) and `a uzina` (to machine) — likewise `violență`/`a violenta`, `eclipsă`/`a eclipsa`, `expertiză`/`a expertiza`, `perlă`/`a perla`, `ramă`/`a rama`, `însuți`/`a însuti` — cannot both be cards. The drafter proposed keeping the noun and retiring the verb. The reader refused: the verbs are real, several with full conjugation charts in `ro_morphology.json`. **The course can hold only one of each pair, and choosing is a Romanian editorial decision, not a sweep.** Left untouched.

The other two: German `Gange`, the dative singular that survives in the fixed idiom `im Gange`, and `reporter`, whose proposed spelling was not the course's variety.

| course | file word | refused because |
|---|---|---|
| ca | `reporter` | Fails check 1 (new_word is not the correct standard spelling for the course's variety) and check 3 (retiring a real, distinct word). Check 1: docs/quality/ca.md fixes the variety a |
| de | `gange` | Criterion 3 — the old spelling is a real, distinct word and retire_old is true. 'Gange' is the dative singular of Gang that survives in the fixed idiom 'in vollem Gange'; all three |
| ro | `însuti` | Criterion 3 — the old spelling is a real, distinct word and retire_old is true. data/raw/ro_kaikki.jsonl carries `a însuti` as an untagged Romanian 4th-conjugation verb ('to centup |
| ro | `uzina` | Criterion 3 — `a uzina` 'to machine' is a real, distinct verb (untagged transitive entry in ro_kaikki.jsonl, full conjugation chart in ro_morphology.json), the note concedes it, an |
| ro | `violenta` | Criterion 3 — `a violenta` 'to subject to violence, commit violence upon' is a real, distinct transitive verb (untagged in ro_kaikki.jsonl, full chart in ro_morphology.json) and th |
| ro | `eclipsa` | Criterion 3 — `a eclipsa` 'to eclipse' is a real, distinct verb (untagged in ro_kaikki.jsonl, full chart in ro_morphology.json), the note concedes it, and retire_old is true. r9867 |
| ro | `expertiza` | Criterion 3 — `a expertiza` 'to appraise, to value' is a real, distinct verb (untagged in ro_kaikki.jsonl, full chart in ro_morphology.json), the note concedes it, and retire_old i |
| ro | `perla` | Criterion 3 — `a perla` 'to bead' is a real, distinct verb (untagged 1st-conjugation entry in ro_kaikki.jsonl, full chart in ro_morphology.json), the note concedes it ('a real but  |
| ro | `rama` | Criterion 3 — `a rama` 'to row' is a real, distinct verb: ro_kaikki.jsonl lists it as an intransitive Romanian verb with no rare/regional/obsolete tag, and ro_morphology.json holds |

## What the second reader corrected before it landed

| file word | field | why |
|---|---|---|
| `detroit` | definition | Rename, pos and retirement are all right, but dropping the city sense breaks the card against its own sentence pool. data/fr_sentences.tsv keys sentences by headword and already ha |
| `junior` | definition | The rename to júnior is right (RAE-adapted spelling, Fundéu 'júnior, mejor que junior'; data/en_translations.tsv already renders English 'junior' as es 'júnior' for both the adj an |
| `ружье` | note | The retire as written strands the card's only sentence. seed_sentences.py joins on an exact lowercase word (id_by_word.get(row['word'].lower())), so an un-retagged row links to not |
| `втроем` | note | apply_gloss_overrides_to_records (backend/services/seeder/gloss_overrides.py:70-73) sets translations['en'] to the override text, overwriting the frequency file's column on every s |
| `втроем` | definition | Register only: 'as a threesome' carries a sexual reading in current English, and ru.md's translation standards require neutral standard register throughout. 'in a group of three' i |
| `fẹ` | definition | The rename to fẹ́ is right and I am not touching it. The definition contradicts its own note: the note says rank 204 fẹran 'must not be folded in', then the definition folds in tha |
| `eniyan` | definition | The rename to ènìyàn is right (11 attestations in data/yo_sentences.tsv, and rank 144 enia is already glossed 'archaic spelling of ènìyàn'), and enia is correctly left alone. But r |
| `navala` | definition | The edit itself is right — the old row is only the definite feminine of `naval`, which keeps its own row at r6358, so no word is deleted, and pos noun matches the gloss. But the pa |

## Every repair applied

| course | was | is now | pos | definition | old spelling retired |
|---|---|---|---|---|---|
| de | `strauss` | `strauß` | noun | Strauß (der) — bouquet, bunch of flowers (ein Strauß Rosen — a bunch of roses; pl. Sträuße); ostrich, the large flightless bird (pl. Strauße) | yes |
| es | `crió` | `crio` | verb | he/she raised, brought up, reared; you (formal) raised — third-person singular preterite of criar: crio a tres hijos sola, she raised three children o | yes |
| es | `diselo` | `díselo` | verb | tell him/her/them (it) — the tú imperative of decir with the clitics se + lo attached: díselo ahora, tell him now | yes |
| es | `guión` | `guion` | noun | script, screenplay (m.) — el guion de la película, the film's script; also the hyphen, the short dash written between or inside words | yes |
| es | `junior` | `júnior` | adj | junior — the younger of two people with the same name (Juan Pérez júnior); of the sports category immediately below sénior, roughly the late-teen/youn | yes |
| es | `manager` | `mánager` | noun | manager (m. and f.) — the person who runs a team, represents an artist, or heads a business: el/la mánager del equipo | yes |
| fr | `detroit` | `détroit` | noun | (m.) a strait — a narrow channel of sea joining two larger bodies of water (le détroit de Gibraltar, le détroit de Béring); also Détroit, the city in  | yes |
| fr | `egypte` | `égypte` | name | Egypt (f.) — the country in North Africa and West Asia (l'Égypte, en Égypte) | yes |
| fr | `eve` | `ève` | name | Eve (f.) — the first woman in Genesis, Adam's wife; also a French female given name, equivalent to English Eve | yes |
| pt | `bónus` | `bônus` | noun | bonus (m.) — extra money paid on top of a salary or fee (bônus de fim de ano = year-end bonus); an added perk or extra given free; invariable in the p | yes |
| pt | `cerimónia` | `cerimônia` | noun | ceremony (f.) — a formal ritual with religious, social or political significance (cerimônia de casamento = wedding ceremony); formality, standing on c | yes |
| pt | `cocó` | `cocô` | noun | poo, poop (m.) — the nursery word for excrement (fazer cocô = to poo; cocô de cachorro = dog poo); (figuratively, informal) crap, junk — something of  | no |
| pt | `colónia` | `colônia` | noun | colony (f.) — a territory held by a foreign power, or the settlers living in it (a colônia portuguesa); cologne, scented water (água de colônia, or ju | yes |
| pt | `dêem` | `deem` | verb | give; let them give — third-person plural present subjunctive and imperative of dar (espero que eles deem uma resposta = I hope they give an answer; d | yes |
| pt | `gémeos` | `gêmeos` | noun | twins (m. pl.) — two or more children born of the same pregnancy (irmãos gêmeos = twin brothers; ela teve gêmeos = she had twins); (capitalised, Gêmeo | yes |
| pt | `génio` | `gênio` | noun | genius (m.) — a person of exceptional ability (ele é um gênio da matemática); temper, disposition (tem um gênio difícil = he has a difficult temper);  | yes |
| pt | `havai` | `havaí` | name | Hawaii (m.) — the Pacific island state of the United States (o Havaí; as ilhas do Havaí = the Hawaiian islands) | yes |
| pt | `iris` | `íris` | noun | iris (f.) — the coloured ring of the eye around the pupil (a íris azul); the iris flower, of the genus Iris | yes |
| pt | `jóia` | `joia` | noun | jewel, gem (f.) — a piece of precious jewellery (loja de joias = jewellery shop); a treasure — anything or anyone precious (essa menina é uma joia); ( | yes |
| pt | `oxigénio` | `oxigênio` | noun | oxygen (m.) — the gas that makes up about a fifth of the air and that we breathe (máscara de oxigênio = oxygen mask); an atom of oxygen | yes |
| pt | `paranóia` | `paranoia` | noun | paranoia (f.) — a psychotic condition marked by delusions of persecution; (spoken Brazil) an irrational fear or obsessive worry (isso é paranoia sua = | yes |
| pt | `paranóico` | `paranoico` | adj | paranoid — irrationally suspicious or convinced of being persecuted (ele está paranoico com isso = he's paranoid about it); (used as a noun, m.) a per | yes |
| pt | `prémio` | `prêmio` | noun | prize, award (m.) — what you win in a contest, lottery or competition (ganhar um prêmio = to win a prize); premium — the sum paid for an insurance pol | yes |
| pt | `pénis` | `pênis` | noun | penis (m.) — the male sexual and urinary organ; invariable in the plural (os pênis) | yes |
| pt | `pólo` | `polo` | noun | pole (m.) — the geographic or magnetic pole (Polo Norte = the North Pole); a hub or centre (polo industrial = industrial hub); polo, the sport played  | yes |
| pt | `suite` | `suíte` | noun | suite (f.) — a set of connected rooms in a hotel (uma suíte de luxo); (Brazil) a bedroom with its own private bathroom (quarto com suíte = en-suite be | yes |
| pt | `ténis` | `tênis` | noun | tennis (m.) — the racket sport (jogar tênis = to play tennis; quadra de tênis = tennis court); a trainer, sneaker, athletic shoe (um par de tênis = a  | yes |
| ro | `amica` | `amică` | noun | female friend, lady friend; girlfriend — the feminine counterpart of amic (f., pl. amice) | yes |
| ro | `arca` | `arcă` | noun | ark — a large covered boat, met almost only in arca lui Noe “Noah's ark” (f., pl. arce) | yes |
| ro | `brat` | `braț` | noun | arm — the limb from shoulder to hand; by extension the arm of a chair, a river or a crane (n., pl. brațe) — la braț “arm in arm”, în brațe “in one's a | yes |
| ro | `buza` | `buză` | noun | lip — of the mouth (f., pl. buze); edge, rim, brink — buza prăpastiei “the brink of the precipice” | yes |
| ro | `catedrala` | `catedrală` | noun | cathedral — the principal church of a diocese, the bishop's seat (f., pl. catedrale) | yes |
| ro | `ceata` | `ceată` | noun | band, group, troop — a body of people acting together; flock, pack of animals (f., pl. cete) — în ceată “in a group” | yes |
| ro | `dorința` | `dorință` | noun | wish, desire; longing (f., pl. dorințe) — a-și pune o dorință “to make a wish”, ultima dorință “a last wish” | yes |
| ro | `freza` | `freză` | noun | milling cutter, router bit — a rotary cutting tool (f., pl. freze); (colloquial) haircut, hairdo | yes |
| ro | `gena` | `genă` | noun | gene — the unit of heredity carried on a chromosome (f., pl. gene) | yes |
| ro | `mos` | `moș` | noun | old man; (before a name) old fellow, uncle (m., pl. moși) — Moș Crăciun “Father Christmas, Santa Claus”, moși “forebears, ancestors” | yes |
| ro | `navala` | `năvală` | noun | onrush, rush, surge; invasion, assault, onslaught (f., pl. năvale) — a da năvală “to rush in, to storm in” | yes |
| ro | `otel` | `oțel` | noun | steel — the metal (n., pl. oțeluri) — oțel inoxidabil “stainless steel”, nervi de oțel “nerves of steel” | yes |
| ro | `pizda` | `pizdă` | noun | (vulgar) cunt, pussy — the female genitals; (of a person) wimp, coward (f., pl. pizde) | yes |
| ro | `poanta` | `poantă` | noun | punchline, the point of a joke; a gag, a witty turn (f., pl. poante) — a strica poanta “to spoil the punchline” | yes |
| ro | `print` | `prinț` | noun | prince — a monarch's son, or the ruler of a principality (m., pl. prinți) | yes |
| ro | `puma` | `pumă` | noun | puma, cougar, mountain lion — the large American wild cat (f., pl. pume) | yes |
| ro | `sir` | `șir` | noun | row, line, queue (of people or things); series, succession; range of mountains (n., pl. șiruri) — zile în șir “days on end”, un șir de munți “a mounta | yes |
| ro | `soacra` | `soacră` | noun | mother-in-law — the mother of one's husband or wife (f., pl. soacre) | yes |
| ro | `teza` | `teză` | noun | thesis — a proposition put forward and argued; (school) an end-of-term written examination paper (f., pl. teze) — teză de doctorat “doctoral thesis”,  | yes |
| ru | `актер` | `актёр` | noun | actor, performer (m., animate) — someone who acts on stage or screen (известный актёр — a famous actor; он хороший актёр — he's a good actor); the fem | yes |
| ru | `втроем` | `втроём` | adv | the three of them, the three of us, the three of you — three people doing something together, in a group of three (мы втроём — the three of us; они жи | yes |
| ru | `жилье` | `жильё` | noun | housing, accommodation, a place to live (n.) — somewhere to live rather than a building as an object (снимать жильё — to rent a place; своё жильё — a  | yes |
| ru | `ружье` | `ружьё` | noun | shotgun, rifle, hunting gun (n.) — a long-barrelled firearm carried by a hunter or soldier (охотничье ружьё — a hunting gun; чистить ружьё — to clean  | yes |
| ru | `четко` | `чётко` | adv | clearly, distinctly — said, written or done so that nothing is blurred or in doubt (говори чётко — speak clearly; он чётко дал понять — he made it per | yes |
| yo | `awa` | `àwa` | pron | we, us — emphatic first-person plural pronoun, used when the subject is focused or contrasted (Àwa ni: it is us), as against plain a for the ordinary  | yes |
| yo | `eniyan` | `ènìyàn` | noun | person, human being — the full written form; people, human beings in general (pluralised with àwọn when the count matters). Broader than ẹni, which na | yes |
| yo | `fẹ` | `fẹ́` | verb | to want, to desire — stands between the subject and the verb (mo fẹ́ jẹun: I want to eat); to want someone as a spouse, to marry; distinct from fẹ̀ (t | yes |
| yo | `nla` | `ńlá` | adj | big, large — follows the noun it describes (ilé ńlá: a big house); great, considerable, of weight or seriousness (ìṣòro ńlá: a big problem) | yes |
| yo | `ounjẹ` | `oúnjẹ` | noun | food, anything eaten; a meal, the cooked dish that is served (oúnjẹ alẹ́: the evening meal) | yes |
