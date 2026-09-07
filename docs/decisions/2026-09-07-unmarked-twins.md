# The 678 unmarked twins, judged — 7 September 2026

Decision D option 3. Every production vocabulary row that becomes identical to a committed-file word once its combining marks are stripped, read by a reader of that language against the course's own orthography policy, then re-read by a second reader told to overturn what was wrong. 31 verdicts were overturned, in both directions.

| verdict | rows | what happens |
|---|---:|---|
| unmarked duplicate | 386 | **shipped**: in `vocab_exclusions.tsv`, retired on your next `reconcile --apply` |
| the file has the worse form | 65 | **not shipped** — each needs a file edit and a re-seed; listed below |
| two different words | 223 | **nothing done** — both deserve cards; the production row needs a file row of its own (supply work) |

Only 2 of the retirements have a learner card, both Latin (`non`, `de`), both unmacronised twins of `nōn` and `dē` that `la.md`'s all-or-nothing macron policy does not allow.

## The file has the worse form — 65 rows for a follow-up pass

These are defects in the committed files, not in production: the file's row is an inflection stub or an unaccented spelling while the production row carries the right form. Each needs the file's headword edited AND a `seeder.run -l <code>`, because changing a headword makes the old spelling ungoverned and the new one absent. Not done tonight; that is a bigger change than an exclusion.

| course | file has | production has | proposed fix |
|---|---|---|---|
| ca | `reporter` | `repòrter` | replace `reporter` (r6586) with `repòrter`, keeping the gloss 'reporter (a journalist who investigates and reports)'; also rename the `reporter` entry |
| de | `gange` | `gänge` | replace gange ('dative singular of Gang', rank 8979) with gänge, gloss 'corridors, hallways; gears; courses of a meal (plural of Gang, der)' — the lem |
| de | `strauss` | `strauß` | replace strauss with strauß, gloss 'Strauß (der) — bouquet, bunch of flowers (pl. Sträuße); also ostrich (pl. Strauße)' — the gender-carrying, two-sen |
| es | `crió` | `crio` | replace crió (r9775) with crio, gloss 'he/she raised, brought up, reared — third-person singular preterite of criar; written without an accent since t |
| es | `diselo` | `díselo` | replace diselo (r3628) with díselo, gloss 'tell him/her/them (it) — the tú imperative of decir with the clitics se + lo (díselo ahora, tell him now)'; |
| es | `guión` | `guion` | Replace guión with guion (m.), gloss "script, screenplay (el guion de la película); hyphen (the punctuation mark)" — the RAE 2010 spelling — and delet |
| es | `junior` | `júnior` | replace junior (r4324) with júnior, gloss 'junior; novice — the younger of two of the same name; a junior-category player (pl. júniores)'; pos adj (al |
| es | `manager` | `mánager` | Replace manager with mánager (m. and f.), gloss "manager (of a team, artist or business) — el/la mánager". |
| fr | `detroit` | `détroit` | Replace the detroit name row with détroit, noun, '(m.) strait, narrow channel of water (le détroit de Gibraltar)'. |
| fr | `eve` | `ève` | Replace eve with ève (Ève), gloss "Eve (the biblical first woman); a female given name". |
| fr | `egypte` | `égypte` | Replace egypte with the accented, capitalised Égypte, gloss 'Egypt (a country in North Africa and West Asia)'. |
| pt | `bónus` | `bônus` | replace bónus with bônus and write the real gloss 'bonus (m.)' — the production row currently only points at the European spelling, so neither row sta |
| pt | `cerimónia` | `cerimônia` | replace cerimónia with cerimônia, gloss 'ceremony (f.) — a ritual with religious, social or political significance; excessive formality (fazer cerimôn |
| pt | `cocó` | `cocô` | cocô needs its own row — noun (m.), 'poo, poop (nursery word); crap (something of low quality)' — and must not be folded into cocó |
| pt | `colónia` | `colônia` | replace colónia with colônia, gloss 'colony (f.) — a territory under a foreign power, or the settlers in it; (água de) colônia = cologne' |
| pt | `dêem` | `deem` | replace dêem with deem, gloss 'give; let them give — third-person plural present subjunctive and imperative of dar (que eles deem, deem-me isso)' |
| pt | `gémeos` | `gêmeos` | replace gémeos with gêmeos, gloss 'twins (m. pl.); (capitalised) Gemini, the zodiac sign' |
| pt | `génio` | `gênio` | replace génio with gênio, gloss 'genius (m.); temper, disposition (tem um gênio difícil); genie, guardian spirit' |
| pt | `havai` | `havaí` | replace havai with havaí, gloss 'Hawaii (m.) — an insular state of the United States'. |
| pt | `jóia` | `joia` | replace jóia with joia, gloss 'jewel, gem (f.); a treasure (anything precious or valuable)'. |
| pt | `oxigénio` | `oxigênio` | replace oxigénio with oxigênio, gloss 'oxygen (m.); an atom of oxygen' |
| pt | `paranóia` | `paranoia` | replace paranóia with paranoia, gloss 'paranoia (f.) — a psychotic disorder characterised by delusions of persecution'. |
| pt | `paranóico` | `paranoico` | replace paranóico with paranoico, gloss 'paranoid' |
| pt | `pólo` | `polo` | replace pólo with polo, gloss 'pole (m.) — geographic or magnetic; hub, centre; polo (the sport)' |
| pt | `prémio` | `prêmio` | replace prémio with prêmio, gloss 'prize, award (m.); premium (insurance)' |
| pt | `pénis` | `pênis` | replace pénis with pênis, gloss 'penis (m.)' |
| pt | `suite` | `suíte` | replace suite with suíte, gloss 'suite (f.) — a set of connected rooms, a bedroom with en-suite bathroom (BR); a musical suite' |
| pt | `ténis` | `tênis` | replace ténis with tênis, keeping the gloss 'tennis (m.); a trainer, sneaker' |
| pt | `iris` | `íris` | replace iris with íris, gloss 'iris (f.) — the flower of the genus Iris; the coloured part of the eye' |
| ro | `amica` | `amică` | replace amica (stub, r8933) with amică (f.) 'female friend, girlfriend' |
| ro | `arca` | `arcă` | Replace arca 'backer, protector' with arcă (f.) 'ark (arca lui Noe)'. |
| ro | `brat` | `braț` | Replace brat 'brother; monk' with braț (n., pl. brațe) 'arm', and reglose brațul as 'the arm (definite form of braț)'. |
| ro | `buza` | `buză` | replace buza (stub, r7207) with buză, gloss 'lip (f.); edge, brink' |
| ro | `catedrala` | `catedrală` | Replace catedrala with catedrală (f.) 'cathedral'. |
| ro | `ceata` | `ceată` | Replace ceata with ceată (f.) 'group, band, troop, flock'. |
| ro | `dorința` | `dorință` | replace dorința (stub, r9332) with dorință, gloss 'wish, desire (f.)' |
| ro | `eclipsa` | `eclipsă` | Replace eclipsa 'to eclipse' with eclipsă (f.) 'eclipse'. |
| ro | `expertiza` | `expertiză` | Replace expertiza 'to appraise, to value' with expertiză (f.) 'expert appraisal, expert report; expertise'. |
| ro | `freza` | `freză` | replace freza (stub, r9249) with freză, gloss 'milling cutter, router bit; (colloquial) haircut (f.)' |
| ro | `gena` | `genă` | replace gena (stub, r7477) with genă (f.) 'gene' |
| ro | `mos` | `moș` | replace mos 'a cup' (r2137) with moș (m.) 'old man; Moș Crăciun — Santa Claus' |
| ro | `navala` | `năvală` | replace navala (stub, r9094) with năvală (f.) 'onrush, rush, invasion; a da năvală — to rush in' |
| ro | `otel` | `oțel` | replace otel 'hotel' (r3064) with oțel (n.) 'steel' |
| ro | `perla` | `perlă` | replace perla 'to bead' (r7963) with perlă, gloss 'pearl (f.)' |
| ro | `pizda` | `pizdă` | Replace pizda with pizdă (f.), gloss 'cunt, pussy (vulgar); (of a person) bitch' — or drop both if the course keeps vulgar register out of the list. |
| ro | `poanta` | `poantă` | Replace poanta 'alternative form of ponta' with poantă (f.) 'punchline, gag; the point of a joke'. |
| ro | `print` | `prinț` | replace print 'print' (r2577) with prinț (m.) 'prince' |
| ro | `puma` | `pumă` | replace `puma` (r9839, noun, 'puma') with `pumă`, noun (f.), 'puma, cougar, mountain lion' |
| ro | `rama` | `ramă` | Replace rama 'to row' with ramă (f.) 'frame (picture frame, spectacle frame); (rare, nautical) oar'. |
| ro | `soacra` | `soacră` | replace soacra (stub, r7834) with soacră (f.) 'mother-in-law' |
| ro | `teza` | `teză` | replace teza (stub, r8010) with teză (f.) 'thesis; (school) end-of-term paper' |
| ro | `uzina` | `uzină` | Replace uzina 'to machine' with uzină, gloss 'works, industrial plant (f.)'. |
| ro | `violenta` | `violență` | Replace violenta 'to subject to violence' with violență (f.) 'violence'. |
| ro | `însuti` | `însuți` | replace `însuti` (r8849, verb, 'to centuple') with `însuți`, pron, 'yourself (emphatic, masculine sg.: tu însuți "you yourself")' |
| ro | `sir` | `șir` | replace `sir` (r1256, noun, 'sir') with `șir`, noun (n.), 'row, line, string; series, succession; range (of mountains)'; if the English title is wante |
| ru | `актер` | `актёр` | replace актер with актёр at rank 7857, gloss 'actor, performer (m., animate)' |
| ru | `втроем` | `втроём` | replace втроем with втроём at rank 8976 and drop the apology from the gloss: 'the three of them (or us) together, as a threesome' |
| ru | `жилье` | `жильё` | replace жилье with жильё at rank 8113, gloss 'housing, accommodation, dwelling (n.)' |
| ru | `ружье` | `ружьё` | replace ружье with ружьё at rank 8007, gloss 'shotgun, rifle (n.)' |
| ru | `четко` | `чётко` | replace четко with чётко at rank 7288, keeping the gloss 'distinctly, clearly, audibly, legibly' |
| yo | `fẹ` | `fẹ́` | At rank 61 replace fẹ with fẹ́, gloss "to want, to desire". |
| yo | `ounjẹ` | `oúnjẹ` | At rank 106 replace ounjẹ with oúnjẹ, gloss "food". |
| yo | `awa` | `àwa` | At rank 468 replace awa with àwa, gloss "we — emphatic first-person plural pronoun". |
| yo | `eniyan` | `ènìyàn` | At rank 80 replace eniyan with ènìyàn, keeping the fuller gloss "person, people, human being". |
| yo | `nla` | `ńlá` | At rank 149 replace nla with ńlá, gloss "big, large". |

## Two different words — 223 rows

The mark is the lexeme: Spanish `cayo` (islet) against `cayó` (he fell), Latin `mālum` against `malum`, Catalan `caça` (hunting) against `caca`. Retiring these would delete a real word. Most need a row of their own in the frequency file, which is Phase 8 supply work rather than a maintenance sweep.

| course | production word | file word | reader's note |
|---|---|---|---|
| ar | `إيا` | `أيا` | The two differ by hamza seat (إ vs أ), which fold_lookalikes merges, but they are different real MSA words: إيّا is the particle that carries an objec |
| ca | `africà` | `àfrica` | Two words, not one mark: Àfrica is the continent and africà the derived adjective/noun 'African', with the accent on a different syllable. |
| ca | `capella` | `capellà` | The final grave moves the stress and the meaning — la capella 'chapel' (f.) against el capellà 'chaplain, priest' (m.); neither is missing a mark. |
| ca | `comes` | `comés` | The acute is the whole difference: comés is the past participle of cometre, while comes is the plural of coma — 'commas' is everyday vocabulary. |
| ca | `coreà` | `corea` | coreà 'Korean' is a derived adjective/noun, a different word from the file's corea, and the grave is not a dropped accent. |
| ca | `coça` | `coca` | ç is a letter: coça 'a kick (from an animal)' (f.) against coca, the flat Catalan pastry — no mark is missing from either form. |
| ca | `crèiem` | `creiem` | The grave marks the tense — creiem 'we believe' (present, r1798) against crèiem 'we believed' (imperfect of creure) — so the grader must not fold them |
| ca | `dotzè` | `dotze` | Cardinal against ordinal: dotze 'twelve' and dotzè 'twelfth', and the grave is exactly what marks the ordinal. |
| ca | `dòmino` | `domino` | dòmino (m.) 'domino, dominoes' is stressed on the first syllable and requires the grave, while domino is 'I dominate' (first-person singular of domina |
| ca | `esquerrà` | `esquerra` | The final grave makes a different word — esquerra 'left (f. of esquerre); the left hand or side' against esquerrà 'left-handed, left-wing'. |
| ca | `formula` | `fórmula` | fórmula (f.) 'formula' is stressed on the first syllable and needs the acute, while unaccented formula is a real form, 'he/she formulates' (of formula |
| ca | `guardó` | `guardo` | The acute turns a verb form into a noun: guardo 'I keep, I put away' (of guardar) against guardó (m.) 'award, prize'. |
| ca | `gustós` | `gustos` | The acute makes the adjective: gustós 'tasty' against gustos 'tastes, flavours' (plural of gust). |
| ca | `jamaicà` | `jamaica` | Jamaica is the country and jamaicà the adjective 'Jamaican'; the grave marks the derivation, not a dropped accent. |
| ca | `llaç` | `llac` | ç against c is a letter change, not an accent: llaç (m.) 'ribbon, bow, knot' and llac (m.) 'lake' are both everyday nouns. |
| ca | `llenca` | `llença` | The cedilla belongs to llençar: llença 'he/she throws' against llenca (f.) 'a strip, a slice' — two words, and neither lacks a required mark. |
| ca | `mari` | `marí` | marí 'marine, sea-' takes the acute while Mari is the Catalan form of the Roman name Marius (Gai Mari), so it is not the same word written badly — but |
| ca | `marquès` | `marques` | The grave separates marquès (m.) 'marquis, margrave' from marques 'marks, brands' (plural of marca). |
| ca | `pagà` | `paga` | pagà is the adjective/noun 'pagan' (and, at C1 only, the passat simple 'he paid'), while unaccented paga at r1592 is 'he/she pays' — the accent is the |
| ca | `patí` | `pati` | Final stress marked by the acute makes a different noun — pati (m.) 'courtyard, playground' against patí (m.) 'skate, pedalo' — and both are ordinary  |
| ca | `sicilià` | `sicília` | Sicília is the island and sicilià 'Sicilian' the derived noun/adjective, with the accent on a different syllable. |
| ca | `tardà` | `tarda` | tarda 'afternoon' (f., r817) and tardà 'late, belated' are separate words; the accent shifts the stress to the final syllable. |
| ca | `tènia` | `tenia` | The grave separates two real words — tènia 'tapeworm' (f.) and tenia 'I/he had' (imperfect of tenir, r202) — so it can never be retired as a mark-only |
| ca | `victorià` | `victòria` | victòria 'victory' (f.) and victorià 'Victorian' carry their accents on different syllables and are unrelated as words a learner would type. |
| ca | `xilè` | `xile` | Xile is the country and xilè the adjective 'Chilean'; the grave marks a derivation, not a dropped accent. |
| de | `blatter` | `blätter` | die Blatter (pock; pox) is a distinct noun, not Blätter (leaves) with the umlaut stripped, but it survives only in Blattern/Windpocken and has no sent |
| de | `dröhnen` | `drohnen` | The file already carries the lemma drohne at rank 8661 with a real gloss ('drone (male bee)'), so 'drohnen — plural of Drohne' is redundant extraction |
| de | `erhalt` | `erhält` | der Erhalt (receipt of something; preservation — 'nach Erhalt der Rechnung') is a noun in its own right, not erhält (he receives) with the ä flattened |
| de | `fuhre` | `führe` | die Fuhre (cartload, wagonload) is a genuine noun distinct from führe (I lead) — the ü is a letter, not a decoration — but a cartload is not vocabular |
| de | `futtern` | `füttern` | futtern is a real colloquial verb meaning 'to eat heartily, scoff' — the production gloss is its own meaning, not füttern's 'to feed' — so the missing |
| de | `fälschen` | `falschen` | 'Inflected form of falsch' is a definition that teaches nothing the rank-609 falsch row does not already teach, whereas fälschen 'to forge, counterfei |
| de | `färben` | `farben` | farbe is already in the file at rank 1797 with a real gloss, so 'farben — plural of Farbe' is a redundant inflection stub, whereas färben 'to dye, to  |
| de | `fördern` | `fordern` | The umlaut separates two common, unrelated verbs — fordern 'to demand, call for' vs fördern 'to promote, support, subsidise (also: to extract, of coal |
| de | `glaser` | `gläser` | der Glaser (glazier) is an occupation noun distinct from Gläser (glasses, plural of Glas) — a bare a is never a written ä — and it is worth its own ro |
| de | `hang` | `häng` | der Hang (slope, hillside; inclination, tendency) is a common noun, not häng with the umlaut dropped, and it is the better card of the two — the file' |
| de | `hauser` | `häuser` | Hauser (householder/housekeeper; also a surname) is a separate word from Häuser (plural of Haus), since a bare a never stands for ä, but it is archaic |
| de | `horst` | `hörst` | Horst is the eyrie of a bird of prey (and a common given name), a different word from hörst rather than an unaccented one, but the eyrie sense cannot  |
| de | `hort` | `hört` | der Hort (refuge, haven; hoard; after-school care centre) is a real noun and not hört with the umlaut dropped — a bare o is never a written ö (the key |
| de | `horten` | `hörten` | horten 'to hoard, to stockpile' is its own infinitive, not hörten (they heard) with the umlaut dropped, and it is ordinary upper-intermediate vocabula |
| de | `härte` | `harte` | The file row is a bare agreement stub ('strong/mixed nominative/accusative feminine singular') of hart, present at rank 802, while Härte is an indepen |
| de | `kampfer` | `kämpfer` | Kampfer (camphor) is a distinct noun, not Kämpfer (fighter) with the umlaut lost, but it is a chemical term with no sentences sitting on a rank borrow |
| de | `kränken` | `kranken` | The file row is both a bare inflection stub and a wrong-lexeme pick of CHECKS §3b's exact shape — the string 'kranken' in running text is the inflecte |
| de | `kürzen` | `kurzen` | Same shape: the file row is a case-inflection stub of kurz (rank 438, already present), and the umlauted production row is the real verb kürzen 'to sh |
| de | `locher` | `löcher` | der Locher (hole punch) is an everyday object noun and not Löcher (holes) with the umlaut dropped; both forms deserve cards, and the collision guard h |
| de | `lug` | `lüg` | der Lug (falsehood) is a real word rather than lüg 'lie!' with the ü flattened, but it survives only in the fixed pair 'Lug und Trug', so it is not so |
| de | `marz` | `märz` | Marz is a municipality in Burgenland, not März with the umlaut dropped — German's only sanctioned substitution is ä→ae ('maerz'), never bare a — but a |
| de | `rachen` | `rächen` | Der Rachen 'throat, pharynx' is a real noun, not a de-umlauted rächen 'to avenge' — the two share nothing but their consonants, so the file's rank-329 |
| de | `ruck` | `rück` | der Ruck (jerk, jolt — 'ruck, zuck', 'ein Ruck geht durch das Land') is an ordinary noun, not rück with the umlaut dropped, and the file's twin is a r |
| de | `ruhr` | `rühr` | Ruhr is the Rhine tributary (and die Ruhr, dysentery), a different word from rühr 'stir!' rather than an unaccented spelling of it, but a river name w |
| de | `schlosser` | `schlösser` | der Schlosser (locksmith, metalworker) is a trade noun distinct from Schlösser (castles; locks) — the ö is a letter, not an accent — and it deserves a |
| de | `schoß` | `schoss` | der Schoß (lap) keeps its ß after 1996 because the o is long, so this row is NOT the pre-reform spelling of schoss (preterite of schießen, rank 4573)  |
| de | `spurt` | `spürt` | der Spurt (a burst of speed, sprint finish) is a real sports noun, not spürt (he senses) unaccented; it is niche, and rank 3705 is spürt's count, so i |
| de | `store` | `störe` | der Store (net curtain, roller blind) is a French loan unrelated to Störe (sturgeons) rather than an unaccented spelling of it, but with no sentences  |
| de | `säge` | `sage` | Säge (die) 'saw, the tool' and sage 'I say' (1sg of sagen, rank 355) are different words that merely fold together when ä is stripped, so the rank-355 |
| de | `verbünden` | `verbunden` | Unlike the stub cases, verbunden is worth its own card — it outranks its own lemma (2313 vs verbinden 3340) and is lexicalised as an adjective ('conne |
| de | `verhalt` | `verhält` | der Verhalt (circumstance, state of affairs) is a separate deverbal noun from verhält (he behaves), but it is archaic outside the compound Sachverhalt |
| de | `wärmen` | `warmen` | The file row is a bare adjective-inflection stub ('strong genitive masculine/neuter singular') of warm, which is already in the file at rank 1978, whi |
| el | `άπλα` | `απλά` | η άπλα is a noun meaning 'open space, roominess'; απλά at r84 is the adverb 'simply' — a real stress pair, but the noun is uncommon enough in everyday |
| el | `έκτος` | `εκτός` | Moving the tonos changes both word and part of speech: έκτος is the ordinal 'sixth' (adj), εκτός the adverb/preposition 'outside, except' at r265 — a  |
| el | `αθηνά` | `αθήνα` | Αθηνά (stress final) is the goddess Athena and one of the commonest Greek female given names; Αθήνα (stress penult) is the city Athens — two different |
| el | `γερός` | `γέρος` | Stress alone separates the adjective γερός 'strong, sturdy, in good health' from the noun ο γέρος 'old man' — near-opposites in sense and different pa |
| el | `γυναικάς` | `γυναίκας` | ο γυναικάς is a separate masculine noun in -άς meaning 'womanizer', not the genitive γυναίκας 'of the woman' — the final stress marks a derivational s |
| el | `επιστήμων` | `επιστημών` | ο επιστήμων is the learned (Katharévousa) nominative 'scientist' beside demotic ο επιστήμονας, while επιστημών is the genitive plural of η επιστήμη 's |
| el | `ευλογιά` | `ευλογία` | A stress pair whose senses diverged long ago — η ευλογιά is 'smallpox' (the demotic euphemism), η ευλογία is 'blessing'; never a mark error, though at |
| el | `ζαριά` | `ζάρια` | η ζαριά is the derived noun 'a throw of the dice, the roll you get' (suffix -ιά, hence the final stress); τα ζάρια is simply the plural 'dice' — two w |
| el | `κάλος` | `καλός` | ο κάλος is a corn or callus on the foot; καλός at r373 is the adjective 'good' — noun against adjective, told apart only by which syllable takes the t |
| el | `κεφαλαίο` | `κεφάλαιο` | το κεφαλαίο (final-syllable stress) is a capital/uppercase letter, το κεφάλαιο (antepenult) is a chapter — and also 'capital' in the money sense, so b |
| el | `κοιλία` | `κοιλιά` | The closest call in this batch: κοιλία/κοιλιά is a learned/demotic doublet, but the learned member carries an anatomical sense the everyday one does n |
| el | `λάος` | `λαός` | το Λάος (stress on the first syllable) is the country Laos, a proper name; ο λαός (final stress) is 'the people' — the tonos placement is the only thi |
| el | `μονός` | `μόνος` | μονός is 'single, one-part' and 'odd' of numbers (opposite ζυγός); μόνος at r278 is 'alone' — two adjectives, and the final stress is the only signal, |
| el | `μπούνια` | `μπουνιά` | τα μπούνια are a ship's scuppers and η μπουνιά is a punch with the fist — different words, though the nautical term survives almost only in the idiom  |
| el | `πισινά` | `πισίνα` | τα πισινά is 'backside, buttocks' (neuter plural of ο πισινός), η πισίνα is 'swimming pool' — a stress pair whose accidental collision under mark-stri |
| el | `σύνοδος` | `συνοδός` | η σύνοδος is 'session, summit, (church) synod'; ο/η συνοδός is 'escort, attendant' (as in αεροσυνοδός, flight attendant) — a standard Greek stress pai |
| el | `τζαμί` | `τζάμι` | Two different Turkish loans split only by stress position — το τζαμί (cami) 'mosque' against το τζάμι (cam) 'pane of glass', so the tonos here is carr |
| el | `υπεροχή` | `υπέροχη` | A textbook Greek stress minimal pair: η υπεροχή (final stress) is the noun 'superiority, the edge over', υπέροχη (antepenult) is the feminine of the a |
| el | `ψαριά` | `ψάρια` | η ψαριά is 'a catch, a haul' — a derived noun in -ιά, not the plural τα ψάρια 'fish'; the stress marks the derivation, so this is not a missing-mark d |
| es | `canon` | `cañón` | ñ separates two real words: canon "canon (rule, body of works, musical round); levy, fee (canon digital)" versus cañón "canyon, cannon, barrel" — unre |
| es | `carné` | `carne` | carné (m.) "ID/membership card" is final-stressed and takes the acute; carne "meat, flesh" is a different word entirely, so both deserve rows. |
| es | `cerro` | `cerró` | cerro (m.) "hill" is an ordinary, frequent noun; cerró is the preterite of cerrar — the acute is the entire difference between them, so this is not a  |
| es | `cono` | `coño` | ñ is a letter: cono "cone" (cono de helado, el Cono Sur) is an ordinary noun and not a bowdlerised spelling of coño. |
| es | `cortés` | `cortes` | The acute marks final stress and a different word: cortés "polite, courteous" (adj.) versus cortes "cuts" / las Cortes, the Spanish parliament — both  |
| es | `cuando` | `cuándo` | The most consequential pair in this slice and the opposite of a duplicate: unaccented cuando is the conjunction/relative ('cuando llegues', 'de vez en |
| es | `cuanta` | `cuánta` | The tilde diacrítica separates two real words here: unaccented cuanta is the relative quantifier ('bebe cuanta agua quieras', 'unas cuantas'), cuánta  |
| es | `dona` | `doña` | Stripping the ñ from doña does not give this row: dona is 3sg of donar "he/she donates" — a real word — while the stored "doughnut" is the Mexican spe |
| es | `esperó` | `espero` | The acute is the lexeme — espero 'I wait, I hope' (r373) against esperó (m.) 'spur' — so it is not a misspelling, though the spur sense is rare at r88 |
| es | `inició` | `inicio` | The accent separates a verb from a noun: inició is 'he/she began' (preterite of iniciar), while the file's inicio is the noun 'start, initiation' — tw |
| es | `lloró` | `lloro` | lloró is the 3sg preterite of llorar and the file's lloro is the 1sg / deverbal noun — different forms whose only distinguisher is the acute, so the a |
| es | `moño` | `mono` | ñ is a letter: moño "bun, topknot; bow" is a different word from mono "monkey; cute", and here the production row carries the correct spelling while t |
| es | `paré` | `pare` | paré "I stopped" (1sg preterite of parar) and pare "stop / that he stop" (subjunctive-imperative, and the LatAm stop-sign noun) are separated by the a |
| es | `peña` | `pena` | ñ makes peña "crag, rock; club, circle of regulars (peña flamenca)" a different word from pena "sorrow; punishment", so the accented production row is |
| es | `picó` | `pico` | picó is the preterite of picar "stung, pecked, chopped" — a different word from pico "beak, peak" — so the accented row is not a duplicate; its stored |
| es | `plató` | `plato` | plató "studio set, sound stage" is a final-stressed French loan that must keep its acute; plato "plate, dish" is a different word, so the accented pro |
| es | `revolver` | `revólver` | The classic Spanish minimal pair: the accent moves stress and part of speech — revolver (v.) "to stir, to rummage through" versus revólver (n.) "revol |
| es | `secretaría` | `secretaria` | The acute shifts the stress and the meaning: la secretaría "secretariat, secretary's office" versus la secretaria "the (female) secretary" — a standar |
| es | `sonado` | `soñado` | ñ separates two lemmas: sonado "much talked-about, sensational (un caso sonado)" from sonar, and soñado "dreamed of" from soñar — neither is the other |
| es | `suena` | `sueña` | ñ is a letter, not a mark: suena is sonar "it sounds" (suena bien) and sueña is soñar "he/she dreams" — two different lemmas, both common, and the pro |
| es | `uña` | `una` | The ñ makes uña "fingernail, claw" a completely different word from the article una "a, one"; here the production row carries the correct spelling and |
| fr | `accéléré` | `accélère` | The two carry different accents on the same stem, not one a stripped mark: il accélère (grave, present) against accéléré (acute, participle and the no |
| fr | `aisé` | `aise` | The é gives the adjective aisé "easy, effortless; (of a person) well-off", a different word from the noun l'aise "ease, comfort" (être à l'aise). |
| fr | `appliqué` | `applique` | The é gives the adjective/participle appliqué "diligent, hard-working; applied" (appliquer), while applique is the verb form "(he) applies" or the nou |
| fr | `aveuglé` | `aveugle` | The é marks the participle of the verb aveugler "blinded, dazzled (momentarily)", which is not the adjective/noun aveugle "blind, a blind person". |
| fr | `botté` | `botte` | botte (f.) 'boot' and botté 'booted, wearing boots' (le Chat botté) are different words — the acute is the participle of botter, not a dropped accent  |
| fr | `bouché` | `bouche` | bouche (f.) 'mouth' at rank 1012 and bouché 'blocked up' are different words — the acute is the participle of boucher, not a mark dropped from the nou |
| fr | `bourre` | `bourré` | bourre lacks no required accent — it is the present of bourrer and the noun la bourre, against the participle/adjective bourré. |
| fr | `braque` | `braqué` | braque carries no dropped accent — it is the present of braquer plus a real noun, and stands against the participle braqué. |
| fr | `calé` | `cale` | The é is the participle/adjective calé "clued-up, good at (il est calé en maths)", not the noun une cale "wedge, chock; ship's hold" — and the product |
| fr | `camé` | `came` | The acute separates slang camé "high, junkie" (past participle of se camer) from the mechanical noun came "cam"; two words, one folded spelling. |
| fr | `claqué` | `claque` | claque (f.) 'slap' and the present il claque are different words from claqué 'knackered, dead'; the acute marks the participle, it is not a missing ma |
| fr | `comblé` | `comble` | The é is the past-participle ending of combler — comblé "filled to overflowing, overjoyed" — not the noun le comble "height, roof space" the file glos |
| fr | `demeuré` | `demeure` | The é is the participle of demeurer ("remained, stayed"), lexicalised as the pejorative noun "halfwit"; la demeure "dwelling, residence" is a differen |
| fr | `disputé` | `dispute` | The é is the past participle of disputer — "contested, hard-fought (un match très disputé); told off" — not the noun une dispute "argument, quarrel",  |
| fr | `dé` | `de` | CHECKS §3b names de/dé as one of the legitimate contrastive pairs the collision guard exists to protect: de is the rank-1 preposition, dé (m.) is a di |
| fr | `débute` | `débuté` | The é is the past participle of débuter; débute is the present (le film débute à 20 h) — two forms of one verb that the accent distinguishes, and neit |
| fr | `déchargé` | `décharge` | The é is the participle of décharger "unloaded, discharged", not the noun une décharge "landfill; discharge; release". |
| fr | `déconné` | `déconne` | Both belong to déconner and the é is the participle: j'ai déconné "I messed up" against il déconne "he's messing about" — the mark is the tense, so th |
| fr | `désiré` | `désire` | désire is the present of désirer, désiré the participle 'desired, wanted' — two real forms, so the acute is not a missing mark; the production row's g |
| fr | `emmenés` | `emmènes` | The grave in emmènes is the stem-vowel alternation of emmener (tu emmènes "you take along"), while emmenés is the masculine-plural past participle — d |
| fr | `enfoncé` | `enfonce` | Final -e vs -é separates two real forms: enfonce is the present of enfoncer (il enfonce), enfoncé the participle/adjective 'driven in, sunken, deep-se |
| fr | `enveloppé` | `enveloppe` | The é is the past participle of envelopper "wrapped (up)", not the noun une enveloppe "envelope". |
| fr | `fiché` | `fiche` | The é is the participle of ficher — "on file, on record (être fiché par la police)" — genuinely distinct from la fiche "card, record slip", but the st |
| fr | `foret` | `forêt` | The circumflex is the lexeme — un foret "drill bit" against une forêt "forest" — so this can never be retired as a missing mark, though at rank 9888 m |
| fr | `fourre` | `fourré` | The é marks the participle fourré "stuffed, filled", and fourre is the 3sg present of fourrer — but the production row's only gloss ("cover, slipcover |
| fr | `fréquenté` | `fréquente` | The final acute is grammatical: fréquente is the present of fréquenter (and the feminine of fréquent), fréquenté the participle/adjective 'busy, much  |
| fr | `félicité` | `félicite` | The final acute is morphology, not a dropped mark: la félicité "bliss" (and the past participle of féliciter, "congratulated") against félicite "(he)  |
| fr | `gênes` | `gènes` | These differ by which accent, not by a missing one: Gênes with the circumflex is Genoa, gènes with the grave is the plural of gène 'gene'. |
| fr | `imposé` | `impose` | impose is the present of imposer, imposé the participle/adjective 'imposed, taxed, compulsory' — the final acute separates two real forms. |
| fr | `influencé` | `influence` | influence (f.) is the noun 'influence' at rank 3267; influencé is the participle 'influenced' — different words, the acute being the participle ending |
| fr | `inversé` | `inverse` | inverse 'inverse, the other way round' is its own adjective and noun; inversé 'inverted, reversed' is the participle of inverser — the acute is not a  |
| fr | `invites` | `invités` | Different words, not a dropped mark: tu invites "you invite" against les invités "the guests" — the é is the participle turned noun. |
| fr | `justifié` | `justifie` | justifie is the present of justifier, justifié the participle/adjective 'justified' — the acute distinguishes two real forms rather than being absent  |
| fr | `largue` | `largué` | largue is the present of larguer (and a nautical adjective), a different form from the participle largué; the final -e is not a stripped acute. |
| fr | `loupe` | `loupé` | No mark is missing — loupe is a real lexical noun (la loupe, magnifying glass) and the present of louper, against the past participle loupé. |
| fr | `lé` | `le` | lé (m.) "width, strip of fabric or wallpaper" is a real and different word from the article le, but it is rank 9823 with no cards or sentences and fol |
| fr | `manifesté` | `manifeste` | The é is the past participle of manifester — "shown, expressed", and in the everyday sense "demonstrated, protested" (ils ont manifesté) — against the |
| fr | `manipule` | `manipulé` | manipule is the present of manipuler (il manipule), a different form from the participle manipulé; no required accent is missing from it. |
| fr | `mesuré` | `mesure` | The é is the participle/adjective mesuré "measured, moderate (un ton mesuré)", not the noun la mesure "measure, measurement". |
| fr | `mouille` | `mouillé` | The é in mouillé is the participle/adjective marker "wet", while mouille is the real 3sg present of mouiller ("il mouille") — but the production row's |
| fr | `musclé` | `muscle` | le muscle (the body tissue) and musclé 'muscular, beefy' are different words; the acute is the participle/adjective ending of muscler. |
| fr | `mât` | `mat` | The circumflex is the lexeme: mât "mast, flagpole" (m.) against mat "matt, dull; olive (of a complexion)" — CHECKS §25's rule that a mark can be the w |
| fr | `mûr` | `mur` | A genuine minimal pair the circumflex exists to keep apart — mur (m.) 'wall' against mûr 'ripe'; the 1990 reform deliberately kept û here for exactly  |
| fr | `nécessite` | `nécessité` | The final acute is the noun-forming ending: la nécessité "necessity, need" against il nécessite "requires, calls for" — two words, and the production  |
| fr | `offense` | `offensé` | offense is the lexical noun 'offence, affront' (and the present il offense), not offensé minus an accent — the final -e/-é contrast separates the pres |
| fr | `paume` | `paumé` | paume (f.) 'palm of the hand' is a plain lexical noun with no accent to lose, quite separate from paumé 'lost, clueless'. |
| fr | `présumé` | `présume` | Final -e/-é again separates present from participle: présume is 'presumes' (il présume), présumé the adjective 'presumed, alleged'. |
| fr | `pécheur` | `pêcheur` | Acute vs circumflex is the textbook French minimal pair — pécheur "sinner" (pécher, to sin) against pêcheur "fisherman" (pêcher, to fish) — so folding |
| fr | `reculé` | `recule` | The é gives the lexicalised adjective reculé "remote, far-off (une région reculée)", not recule "(he) moves back" — the mark is the grammatical conten |
| fr | `regretté` | `regrette` | regrette (je regrette = I'm sorry) and regretté (the participle, and 'le regretté X' = the late X) are different forms, not one word with a dropped ac |
| fr | `remercié` | `remercie` | Both are forms of remercier and the é is the grammatical content — remercié "thanked" (je t'ai remercié) against remercie "thank(s)" (je vous remercie |
| fr | `retraité` | `retraite` | la retraite 'retirement, pension' and un retraité 'a pensioner' are two different nouns, so the acute cannot be a missing mark — though the file's row |
| fr | `ré` | `re` | The file's row is extraction debris — a pos "name" glossed "abbreviation of Renaissance" cannot carry rank 2257 — while the production row is a real F |
| fr | `sacres` | `sacrés` | sacres is a real different word (plural of le sacre "coronation, consecration"), so it is not a missing-accent misspelling of sacrés "sacred; damned ( |
| fr | `salé` | `sale` | sale 'dirty' and salé 'salty, salted' are two different French adjectives; the acute is the only thing between them and dropping it produces the other |
| fr | `suspecté` | `suspecte` | The acute here is grammatical, not decorative: suspecté is the participle/adjective 'suspected', while suspecte is the present of suspecter and the fe |
| fr | `taillé` | `taille` | taille (f.) 'size, waist, cutting' at rank 1377 is a different word from taillé 'cut, carved, built for'; the acute marks the participle of tailler. |
| fr | `tranché` | `tranche` | tranche (f.) 'slice' and il tranche are real forms distinct from tranché 'clear-cut, sharply marked'; the final acute is the participle ending, not a  |
| fr | `trempe` | `trempé` | As glossed the row is trempé minus its acute: 'wet, soaked' as an adjective spelled trempe is the Québécois form, and fr.md puts Québécois lexicon exp |
| fr | `viole` | `violé` | French final -e vs -é is not a missing accent: viole is the third-person present of violer (il viole) and the instrument la viole, a different written |
| it | `ché` | `che` | The acute here is Italian's accento distintivo, not a dropped mark: `ché` is the causal conjunction "for, since" (short for perché, as in non c'è di c |
| pt | `caca` | `caça` | The cedilla changes the word outright — caça is 'hunting; fighter jet' and caca is the nursery word for excrement — so this is never a spelling fold,  |
| pt | `caracas` | `caraças` | The cedilla separates two unrelated words — caraças is the Portuguese interjection, caracas the Venezuelan capital — so the unmarked form is not a mis |
| pt | `contínuo` | `continuo` | The acute separates two real words a learner meets: contínuo 'continuous' (stress on the í) against continuo 'I continue' from continuar — the product |
| pt | `cortês` | `cortes` | The circumflex marks a genuinely different word: cortês is the final-stressed adjective 'polite, courteous', while cortes is the plural of corte 'cour |
| pt | `crista` | `cristã` | The tilde makes a different real word: crista is 'crest, ridge' while cristã is the feminine of cristão 'Christian' — no mark was dropped. |
| pt | `doído` | `doido` | The acute makes a different real word: doído is 'sore, aching' (past participle of doer, everyday Brazilian 'tô doído'), doido is 'crazy' — two lexeme |
| pt | `dó` | `do` | The acute is the whole difference between two unrelated words — dó 'pity' (and the musical note C) against the contraction do 'of the' at rank 15 — th |
| pt | `franca` | `frança` | The cedilla is meaning-bearing: França is the country, while franca is the feminine of franco — and the stored 'municipality of São Paulo' gloss is it |
| pt | `louça` | `louca` | The cedilla makes a different real word: louça is 'crockery, dishes' while louca is the feminine of louco 'crazy'. |
| pt | `manha` | `manhã` | The tilde is the whole difference between two live words — manhã 'morning' and manha 'cunning; whining, tantrum' — so this is not a dropped-mark dupli |
| pt | `moca` | `moça` | The cedilla separates two real words: moça 'young woman' and moca 'mocha (coffee)'. |
| pt | `mágoa` | `magoa` | The acute marks a different word, not a lost mark: mágoa is the noun 'grief, hurt' while magoa is the third-person present of magoar 'hurts'. |
| pt | `pró` | `pro` | The acute distinguishes two live items: pró 'in favour of, pro' against the colloquial contraction pro = pra + o. |
| pt | `pós` | `pôs` | Acute against circumflex, two different words: pôs is 'he/she put' (preterite of pôr) while pós is the plural of pó and the prefix pós- 'post-'. |
| pt | `secretaria` | `secretária` | A textbook Portuguese minimal pair: secretaria (no acute) is 'the secretariat/office', secretária (acute) is 'secretary (f.); desk' — the accent shift |
| pt | `tomás` | `tomas` | Not a dropped mark in either direction — Tomás is the given name Thomas and tomas is the second-person singular of tomar — but a proper name is not vo |
| pt | `vovô` | `vovó` | Circumflex against acute, not a dropped mark: vovô is 'grandpa' and vovó is 'grandma', and the production form is the commoner of the two. |
| ro | `ancoră` | `ancora` | Noun ancoră (f.) 'anchor' and verb a ancora 'to anchor' are separate lexemes — the final ă is the feminine noun ending, not a dropped diacritic. |
| ro | `asistență` | `asistentă` | ț against t separates asistență 'assistance, attendance, audience' from asistentă '(female) assistant, nurse'. |
| ro | `boxă` | `boxa` | boxă (f.) is a noun and a boxa 'to box' a verb; they collide only once the breve is folded away. |
| ro | `băț` | `bat` | Both marks are lexical: băț 'stick, rod' is a noun, bat 'I beat' is the first person of a bate (r1003) — unrelated words. |
| ro | `carat` | `cărat` | The breve separates the loan noun carat 'carat, karat' from cărat 'carried, hauled' (past participle of a căra, r6412). |
| ro | `catar` | `catâr` | â is a letter: catar 'catarrh' is a different word from catâr 'mule', so the two must never be merged — but catarrh at rank 9334 is rare, a learner ne |
| ro | `ceață` | `ceata` | ț against t separates two real words: ceață 'fog, mist' and ceată 'band, group, troop' — the file's ceata row is the definite of ceată, not an inflect |
| ro | `consolă` | `consola` | Noun consolă 'console' and verb a consola 'to console, comfort' are separate lexemes; the final ă is the feminine ending, not a dropped mark. |
| ro | `cotă` | `cota` | cotă (f.) 'quota, level, rating' is a noun while a cota 'to rate, quote' is a verb; the final ă is the noun's ending, not a missing mark. |
| ro | `coș` | `cos` | Comma-below ș is a letter: coș (n.) 'basket; chimney; pimple' is a common word with no card in the file (only baschet 'basketball'), while cos is 'I s |
| ro | `cretă` | `creta` | cretă (f.) 'chalk' and Creta 'Crete' are unrelated words separated by the breve, so the chalk card must not be folded into the island's row. |
| ro | `curenta` | `curentă` | a curenta 'to give an electric shock' (colloquial, m-a curentat) is a different word from curentă, the feminine of curent, and the file has electrocut |
| ro | `deriva` | `derivă` | The `ă` separates two dictionary entries, not two spellings of one: `derivă` is the feminine noun "drift" (and the 3sg present), while `deriva` is the |
| ro | `deșert` | `desert` | ș is a letter: deșert 'desert; empty, deserted' is not desert 'dessert', and both are ordinary vocabulary. |
| ro | `externa` | `externă` | a externa 'to discharge (a patient) from hospital' is an everyday verb — the file has only the adjective externat 'discharged' — and externă is the fe |
| ro | `furnica` | `furnică` | The unmarked form is a different real word — the verb `a furnica` "to tingle, prickle, feel pins and needles" (mă furnică pielea) — as well as being t |
| ro | `intriga` | `intrigă` | a intriga 'to intrigue, to puzzle' is a verb and intrigă (f.) 'plot, intrigue' a noun, but the unmarked intriga is also the definite 'the plot', so a  |
| ro | `laș` | `las` | Comma-below ș is a letter: laș is 'coward, cowardly' while las is 'I leave, I let' (a lăsa, 499), and the course has no card for 'coward' beyond frico |
| ro | `majora` | `majoră` | a majora 'to raise, to increase (prices, wages)' is current standard Romanian and absent from the file, while the breve-marked majoră is the feminine  |
| ro | `manie` | `mânie` | â is a letter: manie 'mania, obsession' is a different word from mânie 'rage, wrath', and the file's mânie gloss has already leaked the other word's s |
| ro | `mană` | `mână` | â is the word here — mână 'hand' at rank 740 is core vocabulary and mană 'manna, abundance; (of plants) mildew' is a separate lexeme, so folding them  |
| ro | `mușcat` | `muscat` | ș is a letter: mușcat 'bitten' (past participle of a mușca) is not muscat, the grape/wine adjective, so the two cannot share a row. |
| ro | `păstor` | `pastor` | The breve is the word: păstor 'shepherd' and pastor 'Protestant minister, priest' are two lexemes, not one spelling that lost a mark. |
| ro | `rad` | `râd` | The circumflex is the lexeme: rad is 'I shave' (a rade, file rank 2417) and râd is 'I laugh' (a râde, 1753), so folding them would launder one verb in |
| ro | `rață` | `rată` | ț is a letter: rață 'duck' is not rată 'instalment, rate' — and the file already has both rată (r6301) and a rata 'to miss' (r1941) but no word for du |
| ro | `salvă` | `salva` | Two different real words separated by the `ă`: `salva` is the verb infinitive "to save, rescue" (r1021), `salvă` is the feminine noun "salvo, volley"  |
| ro | `sarma` | `sârmă` | â is a letter: sarma 'stuffed cabbage roll' (a Turkish loan, usually plural sarmale) is unrelated to sârmă 'wire'. |
| ro | `simț` | `simt` | ț is a letter: simț (n.) 'sense' (cele cinci simțuri, bun-simț) is not simt 'I feel', the first person of a simți at rank 263. |
| ro | `specifica` | `specifică` | a specifica 'to specify' is an everyday verb the file has no card for anywhere, while specifică is the feminine of the adjective specific — the breve  |
| ro | `stimă` | `stima` | stimă (f.) 'esteem' (cu stimă = yours sincerely) is a noun and a stima 'to esteem' a verb — two lexemes, and the production row already has two senten |
| ro | `vânăt` | `vânat` | `ă` versus `a` gives two different real words: `vânat` is the noun/past participle "game, quarry, hunted animal", `vânăt` is the adjective "livid, bru |
| ro | `văi` | `vai` | The breve makes a different real word — văi 'valleys' (plural of vale, r3186) against the interjection vai 'alas' — so the two must never be graded as |
| ro | `văl` | `val` | The `ă` is the whole word here: `val` is "wave" (r2038) and `văl` is "veil, shroud, cover" — two unrelated common nouns, so the unmarked spelling is a |
| ro | `școli` | `scoli` | ș is a letter: școli 'schools' (plural of școală, r2696) is not scoli 'you get up' (a scula, r3547) — they must never be graded as one, though as a pl |
| ro | `țipa` | `tipă` | Both the ț and the final vowel are lexical here: a țipa 'to scream, yell' is a different word from tipă 'chick, woman', and the file has no verb for ' |
| ru | `лёт` | `лет` | The ё is the lexeme: лёт is 'flight (of birds, insects)' while лет at rank 150 is the genitive plural counted after numerals (пять лет), so retiring i |
| ru | `покои` | `покой` | No mark is involved — й is a letter, and the pair collides only because NFD decomposes й into и + combining breve; покои 'chambers, living quarters' i |
| yo | `elu` | `ẹlu` | e and ẹ are distinct phonemes and the glosses are unrelated — the file's `ẹlu` is the indigo plant while the production row is only a dialectal altern |
| yo | `kọ́` | `kọ` | Tone alone separates them: kọ́ is 'to learn, to teach' while the file's kọ (r54) is glossed 'to refuse, reject', which is kọ̀ — a different verb, and  |
| yo | `mọ̀` | `mo` | The underdot plus grave give a different real word — mọ̀ 'to know' versus the subject pronoun mo 'I' (r183) — so this is not a mark-loss duplicate of  |
| yo | `sọ̀rọ̀` | `ṣòro` | Two marks separate them — the ṣ and the underdots — so sọ̀rọ̀ 'to speak' and ṣòro 'to be difficult' are different words, not one spelling with a lost  |
| yo | `yé` | `ye` | The acute makes a different real word: yé is the verb 'to be clear to' (ó yé mi = I understand), while the file's ye (r370) is a noun of address for a |
| yo | `ìwọ` | `iwo` | The underdot is phonemic: ìwọ is the emphatic 2sg pronoun 'you', while iwo (rank 508) is 'horn' — a different real word, so this is never a mark-loss  |
| yo | `ṣe` | `sẹ` | The gloss is verbatim the yes-no question particle, which the file holds correctly toned as ṣé at rank 11 — so this row is ṣé missing its acute, not t |
| yo | `ṣun` | `sùn` | ṣ and s are different letters in Yoruba, and the glosses are unrelated ("to save, conserve" vs "to sleep"), so retiring this into `sùn` would launder  |
| yo | `ọjọ́` | `òjò` | The underdots are phonemic — ọjọ́ 'day' and òjò 'rain' are two different words, and the pairing is only an artefact of stripping dots and tones togeth |
| yo | `ọni` | `oni` | The underdot is the whole difference between `ọ̀ni` "crocodile" and `òní` "today" — two real words, exactly the `ọkọ`/`oko` case yo.md names, so foldi |
| yo | `ọọ` | `oo` | ọ and o are different letters and the meanings are unrelated ("hand" vs "business, trade"), so this is not an undotted `oo`; the production row is onl |

## Every retirement, by course

| course | word | twin in the file | why |
|---|---|---|---|
| ar | `ابريل` | `إبريل` | Bare alef for a hamza-seated alef, gloss "alternative spelling of أَبْرِيل", and another of the 11 twins deleted on 20 Aug 2026 — the canonical أبريل  |
| ar | `استوديو` | `إستوديو` | Bare alef against the hamza-seated headword both the file (rank 4402, "studio") and ar_morphology.json use (إستوديو, Gender m.), and the production ro |
| ar | `اقوياء` | `أقوياء` | Bare alef for the hamza seat أ in أقوياء; the production gloss "alternative spelling of أَقْوِيَاء" adds nothing, so the file's form is the one that s |
| ar | `الإثنين` | `الاثنين` | Same word with the wrong mark in the other direction: the alef of اثنين is hamzat wasl and is written bare, so الإثنين adds a hamza seat MSA does not  |
| ar | `الاحد` | `الأحد` | Bare alef where أحد takes the hamza seat أ (ال + أحد); the row's own gloss reads "alternative form of اَلْأَحَد (al-ʔaḥad, "Sunday")", and the file's  |
| ar | `انا` | `أنا` | Bare alef where the policy requires the hamza seat أ — ar.md names this exact word ("never bare ا for أنا, أنت"), the row's own gloss is "alternative  |
| ar | `انواع` | `أنواع` | Bare alef for the required hamza seat أ in أنواع (plural of نَوْع); the production gloss is literally "alternative spelling of أَنْوَاع", so it carrie |
| ca | `arteria` | `artèria` | No Catalan corpus writes 'craftiness' more often than 'artery', but the unaccented row sits at r7384 above artèria at r9059, so the rank belongs to ar |
| ca | `estàn` | `estan` | The row's own gloss says 'misspelling of estan' — the pointer-gloss class already excluded for ca (cóm, fóra) — and standard Catalan writes estan (r18 |
| ca | `forcat` | `forçat` | 'Forked/a plough' is far rarer than 'forced', yet the cedilla-less row outranks its twin (r3580 against forçat r6564), so the frequency is cedilla-les |
| ca | `francés` | `francès` | francés is the Valencian spelling of francès, and ca.md puts Valencian explicitly out of scope; the 'François' gloss is a wrong-lexeme pick on top of  |
| ca | `maría` | `maria` | Catalan writes the name Maria with no accent — the acute is Spanish orthography, out of scope the same way ca.md puts Valencian out of scope — and a v |
| ca | `pèr` | `per` | Standard Catalan has no `pèr` — the r10 preposition per takes no accent and DIEC lists no such noun — so the 'cauldron' gloss at r9839 is a leak from  |
| de | `ausser` | `außer` | The row self-identifies as obsolete-and-Swiss spelling of außer (rank 616) — both halves of that gloss are out of scope. |
| de | `bißchen` | `bisschen` | bißchen is named in de.md's nine pre-1996 removals; bisschen sits at rank 396 with the real gloss. |
| de | `bloss` | `bloß` | Self-identified Swiss ss spelling of bloß (rank 566), with no sentences; Swiss orthography is out of scope as a production target. |
| de | `bucher` | `bücher` | The production row's whole gloss is "a surname" with no English equivalent named — verbatim the class CHECKS §10 retired by owner decision (645 rows;  |
| de | `busse` | `buße` | Same §10 retired class — the row says only "a surname", and the string is additionally the Swiss ss spelling of Buße (Parkbusse), so both grounds poin |
| de | `daß` | `dass` | daß is named in de.md's own list of nine pre-1996 ß spellings removed; dass sits at rank 24, so nothing is lost. |
| de | `draussen` | `draußen` | Self-identified Swiss ss spelling of draußen (rank 406), with no sentences of its own; Swiss orthography is out of scope as a production target. |
| de | `gross` | `groß` | The string is the Swiss spelling of groß (rank 710) and the 'a surname' gloss is exactly the rare-twin-of-a-common-word debris de.md removed; leaving  |
| de | `grosse` | `größe` | grosse is the Swiss ss spelling of große (rank 458), out of scope as a production target; it only pairs with größe because the fold strips both ö and  |
| de | `grossen` | `großen` | grossen is the Swiss ss spelling of großen, and Swiss orthography is explicitly out of scope as a production target; großen carries the identical infl |
| de | `heisst` | `heißt` | 'inflection of heissen' is the Swiss ss spelling of heißt (rank 298) — the same out-of-scope class, and the German course drills heißen with ß. |
| de | `laß` | `lass` | laß is the pre-reform ß spelling of the imperative lass (rank 172) — the short a takes ss after 1996 — and is the same class as the laßt already remov |
| de | `laßt` | `lasst` | laßt is named outright in de.md's nine pre-1996 removals; the post-reform lasst sits at rank 530. |
| de | `läßt` | `lasst` | läßt is the pre-1996 spelling of lässt, which the file already has at rank 488; the paired lasst (2nd plural, rank 530) is a third form dragged in by  |
| de | `muß` | `muss` | muß is one of the nine pre-1996 spellings listed in de.md; the post-reform muss sits at rank 77. |
| de | `mußt` | `müsst` | mußt is a listed pre-1996 spelling of musst, which is already in the file at rank 202; note the row it was paired with, müsst (2nd person plural), is  |
| de | `mußte` | `müsste` | mußte is on the pre-1996 list and its modern form musste is in the file at rank 485; the paired müsste is Konjunktiv II, a different form the fold col |
| de | `paß` | `pass` | paß is one of the nine pre-1996 ß spellings de.md lists as already removed; the post-reform string pass sits at rank 639, so this is deprecated orthog |
| de | `scheisse` | `scheiße` | Self-identified 'Switzerland and Liechtenstein standard spelling of Scheiße'; the ß form is at rank 284 and Swiss ss is out of scope. |
| de | `spass` | `spaß` | Self-identified 'Switzerland and Liechtenstein standard spelling of Spaß'; the ß form is at rank 513. |
| de | `strassen` | `straßen` | strassen is the Swiss ss plural of Straßen (rank 2269) wearing a place-name gloss — the identical case to strasse, which is already in vocab_exclusion |
| de | `weiss` | `weiß` | The row self-identifies as 'Switzerland and Liechtenstein standard spelling of weiß' — the exact class de.md deleted — and weiß at rank 70 already car |
| de | `weisst` | `weißt` | Self-identified Swiss ss spelling of weißt (rank 148), which is out of scope as a production target. |
| de | `wußte` | `wüsste` | wußte is on de.md's pre-1996 list and its modern form wusste is in the file at rank 333; the paired wüsste is the Konjunktiv II, a different form the  |
| el | `άγια` | `αγία` | άγια and αγία are two inflections of ONE lemma, not two words — data/el_frequency.tsv already carries άγιος r4205 'holy, saintly; Saint' plus αγίου r3 |
| el | `αμερικανικά` | `αμερικάνικα` | Not a missing tonos but the same adjective 'American' in its two accepted stress variants (formal αμερικανικός / colloquial αμερικάνικος) — identical  |
| el | `αρά` | `άρα` | The recorded verdict contradicts both the reader's own file_fix ('needs no file row') and el.md's scope line ('Out of scope: Ancient and Koine Greek') |
| es | `ahi` | `ahí` | Self-identifying 'misspelling of ahí'; ahí is oxytone ending in a vowel and the acute also marks the í hiatus, so the unaccented spelling is never cor |
| es | `ahogo` | `ahogó` | ahogó (preterite of ahogar) requires the acute; accentless ahogo is 1sg of the same lemma, and the noun "breathlessness, suffocation" cannot carry ran |
| es | `aja` | `ajá` | ajá is final-stressed and must carry the acute; "adze" is not current Spanish (the tool is azuela), so the gloss is extraction debris and rank 9113 is |
| es | `alli` | `allí` | Stored as 'misspelling of allí'; oxytone ending in a vowel requires the acute, 0 sentences and 0 cards against allí r189. |
| es | `ano` | `año` | The verdict contradicts its own file_fix, which says retire on the montana/montaña precedent; ñ is a letter, but rank 5542 against año r331 is ñ-dropp |
| es | `aqui` | `aquí` | The row's own stored definition is 'misspelling of aquí' — aquí is oxytone ending in a vowel, so the acute is obligatory; 0 sentences and 0 cards, and |
| es | `arrojo` | `arrojó` | The acute separates 1sg arrojo from 3sg preterite arrojó inside one lemma (arrojar); the literary noun arrojo "daring" is real but cannot carry rank 4 |
| es | `asi` | `así` | Self-identifying pointer row ('misspelling of así; obsolete spelling of así'): así is oxytone ending in a vowel and requires the acute; no meaning of  |
| es | `bebe` | `bebé` | The row glosses "baby", which peninsular Spanish writes bebé with the acute; the genuinely different homograph bebe "he/she drinks" (from beber) is no |
| es | `capitan` | `capitán` | Stored as 'obsolete spelling of capitán'; an oxytone ending in -n requires the acute under the current norm, and the row carries no meaning of its own |
| es | `cayo` | `cayó` | The reader concedes rank 946 is inflated by accentless cayó, which is exactly CHECKS.md's rank-impossible row ("the meaning is real but cannot carry t |
| es | `compañia` | `compañía` | Stored as 'misspelling of compañía' — the acute marks the í hiatus and is obligatory; 0 sentences, 0 cards, against compañía r785. |
| es | `confeso` | `confesó` | confesó needs its acute; the adjective confeso survives essentially only in the legal formula reo confeso and cannot carry rank 4092 — the frequency i |
| es | `despues` | `después` | Stored as 'misspelling of después'; oxytone ending in -s requires the acute, and despues is not a separate Spanish word. |
| es | `dia` | `día` | Rank-impossible gloss, the exact class already in data/vocab_exclusions.tsv for es (tenia, numero, linea, ultimo): rank 1991 is carried by unaccented  |
| es | `dificil` | `difícil` | Stored as 'misspelling of difícil' — a paroxytone ending in -l is always written with the acute; no distinct meaning, 0 sentences, 0 cards. |
| es | `eligio` | `eligió` | Eligio is a capitalised given name, and elegir's 1sg is elijo, so lowercase eligio is not a Spanish word at all — rank 2660 is eligió typed without it |
| es | `escapo` | `escapó` | escapó requires the acute; accentless escapo is only 1sg of the same verb escapar, and the stored "scape" is the botanical term for a flower stalk, wh |
| es | `estan` | `están` | Stored definition is 'misspelling of están'; están is a paroxytone ending in -n, so the acute is obligatory, and the accentless form is not another Sp |
| es | `frances` | `francés` | Stored as 'obsolete spelling of francés; misspelling of francés' — oxytone in -s takes the acute, and the accentless form is not a separate Spanish wo |
| es | `golpeo` | `golpeó` | The acute only moves the same lemma from 1sg present (golpeo "I hit") to 3sg preterite (golpeó) — not a different word — and the deverbal noun "hittin |
| es | `habia` | `había` | Stored as 'misspelling of había; obsolete spelling of había' — the acute breaks the ía hiatus and is obligatory; the file's había r172 carries the rea |
| es | `incomodo` | `incómodo` | The adjective is written incómodo; this row glosses the same idea ("uncomfortableness") minus the required tilde, and the only real accentless incomod |
| es | `invite` | `invité` | invité "I invited" carries the acute; accentless invite is only the present subjunctive of the same lemma invitar, and the noun "invite" is a card-gam |
| es | `limite` | `límite` | The noun is esdrújula and written límite; this row glosses exactly that noun ("limitation; limit") without its required tilde — the only genuine accen |
| es | `lucho` | `luchó` | Lucho as a nickname for Luis is a capitalised proper name (excluded by the 25 Aug personal-name decision), and lowercase lucho is just 1sg of luchar — |
| es | `metete` | `métete` | Imperative + clitic is esdrújula and written métete; "metete" meaning nosy is Chilean/Andean colloquial, out of the peninsular scope, so rank 2840 is  |
| es | `mostro` | `mostró` | mostró (preterite of mostrar) must carry the acute; "mostro" as "excellent" is Peruvian slang (and an archaic variant of monstruo), outside the penins |
| es | `parate` | `párate` | párate "stand up / stop" is esdrújula (imperative of parar + te) and must be written with the acute; the noun parate "halt, stoppage" is River Plate u |
| es | `pego` | `pegó` | pegó carries the acute; accentless pego is at most 1sg of the same lemma pegar, and the stored card-sharping sense is obsolete jargon that cannot hold |
| es | `podre` | `podré` | podré "I will be able" needs the acute; the noun podre "pus, rot" is archaic-literary and cannot carry rank 1105 — the frequency is accentless podré. |
| es | `practicamente` | `prácticamente` | Adverbs in -mente keep the base adjective's written accent (práctico → prácticamente), and both rows carry the identical gloss "practically" — this is |
| es | `prometio` | `prometió` | prometió (preterite of prometer) needs its acute; "promethium" is a chemical element nobody meets in a course and cannot carry rank 2389 — the textboo |
| es | `razon` | `razón` | razón (rank 233) is a final-stressed word that must carry the acute; a surname gloss cannot hold rank 5443 — this is the same unaccented-twin shape as |
| es | `salio` | `salió` | salió is the preterite of salir and must carry the acute; the stored "Salian" is an obscure Latinism no learner meets and cannot carry rank 585 — that |
| es | `sandwich` | `sándwich` | Stored as 'misspelling of sándwich'; the DLE lemma is the adapted sándwich (paroxytone ending in a consonant takes the acute), so the bare English spe |
| es | `sientate` | `siéntate` | Stored as 'misspelling of siéntate' — the enclitic makes the form proparoxytone, so the acute is obligatory; 0 sentences and 0 cards against siéntate  |
| es | `tambien` | `también` | Stored as 'misspelling of también; obsolete spelling of también' — oxytone ending in -n requires the acute; the row carries no meaning of its own, 0 s |
| es | `tí` | `ti` | Spurious mark in the other direction — RAE writes ti with no accent (no homograph to separate, so the tilde diacrítica has no job), and the production |
| es | `unete` | `únete` | únete "join" (unir + te) is esdrújula and written with the acute; "an Internet currency established in Spain in 2013" is extraction debris, not a Span |
| es | `venia` | `venía` | The stored sense is real (venia "leave, permission — con su venia; a bow") but is formal-legal register and cannot carry rank 1424; that mass is venía |
| es | `video` | `vídeo` | Identical glosses and one word in two regional spellings, not two words — es.md makes peninsular standard authoritative and puts the Latin American pr |
| es | `éso` | `eso` | Spurious accent on a neuter demonstrative, which never takes one; the row's own gloss reads 'misspelling of eso' and the file's eso r27 carries the re |
| es | `ésto` | `esto` | Spurious accent: the neuter demonstratives esto/eso/aquello never carry one (they cannot be determiners, so there is no homograph to separate), and th |
| fr | `alle` | `allé` | alle is allé with the acute stripped; the 'she' gloss is the popular/regional spelling of elle that fr.md puts out of scope ('Québécois morphology and |
| fr | `arreter` | `arrêter` | Pointer gloss "obsolete spelling of arrêter" — the dropped circumflex fr.md names, with rank-387 arrêter holding the meaning. |
| fr | `chaine` | `chaîne` | chaine is the post-1990 rectified spelling of chaîne and its gloss says so outright ('post-1990 spelling of chaîne') — a pointer with no meaning of it |
| fr | `chloe` | `chloé` | The row says it: "alternative form of Chloé" — the French name carries the acute, and the unaccented row carries no meaning of its own. |
| fr | `derniere` | `dernière` | "archaic spelling of dernière" is a pointer gloss; the grave is the modern French spelling, and rank-314 dernière is the card. |
| fr | `dégoutant` | `dégoûtant` | dégoutant is the post-1990 rectified spelling of dégoûtant and carries only the pointer gloss saying so; note the file's own row is a weak stub ('pres |
| fr | `entrainer` | `entraîner` | entrainer is the post-1990 rectified spelling of entraîner and its gloss is the bare pointer 'post-1990 spelling of entraîner' — one word, one card, a |
| fr | `entraineur` | `entraîneur` | Pointer gloss "post-1990 spelling of entraîneur" — the 1990 rectification of î, one word with two official spellings (CHECKS §3), and entraîneur is th |
| fr | `entrainé` | `entraîné` | Same word, same participle: entrainé is entraîné with the circumflex dropped by the post-1990 rectification, so it is one card with the file's form, n |
| fr | `etait` | `était` | Pointer gloss "obsolete spelling of était": the missing acute is the dropped mark, and the rank is unaccented typing of rank-56 était. |
| fr | `etat` | `état` | "alternative spelling of État" is a pointer with no meaning of its own; French writes the acute, and the file's état "state, condition" at rank 563 is |
| fr | `etats` | `états` | "alternative spelling of États" — the same accent-stripped pointer as etat, one rank deeper. |
| fr | `etats-unis` | `états-unis` | Pointer gloss "alternative spelling of États-Unis" — the accents are dropped, not a different name, so it is the same country twice. |
| fr | `etre` | `être` | The row's whole gloss is "obsolete spelling of être" — the unaccented form fr.md's profile names as the dropped-circumflex defect, carrying no meaning |
| fr | `gout` | `goût` | The row's whole gloss is the pointer "post-1990 spelling of goût" — it carries no meaning of its own, and CHECKS §3 rules the French rectification pai |
| fr | `ile` | `île` | ile is the post-1990 rectified spelling of île and its gloss is the pointer 'post-1990 spelling of île' — CHECKS §3's boite/maitre/connaitre class exa |
| fr | `kévin` | `kevin` | The production row's own gloss calls it "a less common spelling of Kevin" — the self-identifying pointer class CHECKS §3 deletes — and §30 gives the r |
| fr | `maitresse` | `maîtresse` | Pointer gloss "post-1990 spelling of maîtresse" with no meaning of its own; the 1990 rectifications are variants of one word (CHECKS §3), and maîtress |
| fr | `maitrise` | `maîtrise` | maitrise is the post-1990 rectified spelling of maîtrise, glossed only as a pointer to it — CHECKS §3's maitre class; the circumflex form at rank 5439 |
| fr | `metal` | `métal` | The acute is required on métal, and the music-genre borrowing cannot carry rank 7629 — this is CHECKS §3's rank-impossible shape (es tenia/tenía, pt n |
| fr | `paraitre` | `paraître` | Self-identifying pointer gloss "post-1990 spelling of paraître", the same rectification class CHECKS §3 names (boite, maitre, connaitre) — official va |
| fr | `reconnaitre` | `reconnaître` | reconnaitre is the post-1990 rectified spelling of reconnaître with only the pointer gloss saying so — the same family CHECKS §3 already excluded as c |
| fr | `soul` | `soûl` | The gloss is a double pointer, "post-1990 spelling of soûl, itself an alternative form of saoul" — the rectification class CHECKS §3 rules one card, n |
| fr | `traine` | `traîné` | The pairing showed only traîné, but the file also holds traîne itself at rank 3668 ("anything that trails") — the production row is the post-1990 rect |
| fr | `trainée` | `traînée` | The production headword is a post-1990 rectified spelling, not a better lemma, and the first reader's own fix keeps the circumflex headword and retire |
| fr | `traitre` | `traître` | traitre is the post-1990 rectified spelling of traître, glossed only as the pointer 'post-1990 spelling of traître' — one word, one card, and the circ |
| fr | `égo` | `ego` | Same word twice with a character-identical gloss ("ego, the ego"): standard French writes the Latin borrowing unaccented, so the extra acute — the rev |
| it | `finchè` | `finché` | Same grave-for-acute error as perchè — standard Italian writes `finché` with the acute — and the row's stored definition is "misspelling of finché", s |
| it | `nè` | `né` | Grave for the required acute on `né` "nor"; the row's own gloss says "misspelling of né". The accentless `ne` IS a different real word (the partitive  |
| it | `perchè` | `perché` | Grave accent where the course's own profile line requires the acute (`perché` is named explicitly as the acute case), and the production row self-iden |
| it | `pieta` | `pietà` | The final grave on the oxytone `pietà` is obligatory in standard Italian; bare `pieta` is not a modern word (the row itself only claims "alternative f |
| it | `quì` | `qui` | The mark runs the other way here — a spurious grave added to the monosyllable `qui`, which standard Italian (and the file, rank 35) writes bare — but  |
| la | `amicus` | `amīcus` | Missing the long ī of amīcus 'friend'; the noun and its adjectival use share the same length, so nothing is lost by retiring the plain row. |
| la | `amo` | `amō` | Missing the long final ō of the first-person singular amō; every Latin 1sg active ends in long -ō, so no distinct word is created. |
| la | `audio` | `audiō` | Missing the long final ō of audiō; the file gloss adds 'I listen'. |
| la | `cur` | `cūr` | Missing the long ū of cūr 'why'; there is no short-u 'cur' in Classical Latin. |
| la | `de` **(has a learner card)** | `dē` | The preposition is always dē with a long ē — no short-e twin exists — and the file gloss 'down from; about; concerning' is strictly richer than the pr |
| la | `dico` | `dīcō` | Missing the long ī of dīcō 'I say'; a folded homograph dicō, dicāre 'I dedicate' does exist but is rare outside compounds and is not what this row glo |
| la | `dies` | `diēs` | Nominative singular is diēs with a long ē — the dies/diē contrast la.md names is nominative vs ablative inflection, not this pair — so the plain row i |
| la | `do` | `dō` | Missing the long ō of dō 'I give'; no short-o 'do' exists as a headword. |
| la | `eo` | `eō` | Missing the long ō of eō 'I go'; the adverb eō and the ablative eō are also long, so the macron separates nothing here and the plain row is pure dupli |
| la | `facio` | `faciō` | Missing the long final ō of faciō 'I do; I make'; identical gloss on both rows. |
| la | `femina` | `fēmina` | Missing the long ē of fēmina 'woman'; no short-e homograph exists. |
| la | `filia` | `fīlia` | Missing the long ī of fīlia 'daughter'; identical lemma and gloss. |
| la | `filius` | `fīlius` | Missing the long ī of fīlius 'son'; identical lemma and gloss. |
| la | `frater` | `frāter` | Missing the long ā of frāter 'brother'; no short-a twin. |
| la | `habeo` | `habeō` | Missing the long final ō of habeō; the file gloss additionally carries the everyday second sense 'I hold'. |
| la | `insula` | `īnsula` | Missing the long ī of īnsula 'island'; the file gloss also adds the second sense 'apartment block', so the file row is better on both spelling and def |
| la | `lego` | `legō` | The production row glosses 'I read', which is exactly the file's legō (short e, long final ō); the separate verb lēgō 'I bequeath' would need a long ē |
| la | `mater` | `māter` | Missing the long ā of māter 'mother'; no short-a twin. |
| la | `nomen` | `nōmen` | Same noun missing the long ō the all-or-nothing macron policy requires; nōmen is the only Latin word with this skeleton, and the file row carries the  |
| la | `non` **(has a learner card)** | `nōn` | The negator is nōn with a long ō and there is no short-o 'non'; the one learner card here is already covered by the macronised row, which AccentFoldin |
| la | `nos` | `nōs` | Missing the long ō of nōs 'we'; no distinct short-o word collides with it. |
| la | `pax` | `pāx` | Missing the long ā of pāx (pācis) 'peace'; no short-a homograph. |
| la | `quando` | `quandō` | Missing the final long ō of quandō 'when'; same adverb, same gloss. |
| la | `qui` | `quī` | Both the relative nominative and the archaic ablative are quī with a long ī, so dropping the macron produces no second word; the file gloss adds 'that |
| la | `rex` | `rēx` | Missing the long ē of rēx (rēgis) 'king'; no short-e twin exists. |
| la | `scio` | `sciō` | Missing the long final ō of sciō 'I know'; identical lemma and gloss. |
| la | `scribo` | `scrībō` | Missing the long ī of scrībō 'I write'; no short-i homograph. |
| la | `sedeo` | `sedeō` | Missing the long final ō of sedeō 'I sit'; same lemma, same gloss. |
| la | `si` | `sī` | The conditional conjunction is sī with a long ī; the unmacronised spelling is a misspelling, not another word. |
| la | `sto` | `stō` | Missing the long ō of stō 'I stand'; no competing form. |
| la | `tres` | `trēs` | Missing the long ē of trēs 'three'; no short-e twin. |
| la | `tu` | `tū` | Second-person nominative is tū with a long ū; the unmacronised row is the same pronoun with the mark dropped. |
| la | `unus` | `ūnus` | Missing the long ū of ūnus 'one'; no short-u twin. |
| la | `venio` | `veniō` | Missing the long final ō of veniō; the venit/vēnit contrast la.md warns about lives in the third-person forms, not in this 1sg headword. |
| la | `video` | `videō` | Missing the long final ō of videō 'I see'; same lemma, same gloss. |
| la | `vita` | `vīta` | Missing the macron on ī; vīta 'life' has no short-i homograph, and the production row's gloss is the file row's own. |
| la | `voco` | `vocō` | Missing the long final ō of vocō 'I call'; identical lemma and gloss. |
| la | `volo` | `volō` | Missing the long final ō of volō 'I want'; the homograph volō 'I fly' is spelled identically even with macrons, so length is not what would separate t |
| la | `vos` | `vōs` | Missing the long ō of vōs 'you (plural)'; same lemma, same gloss, no homograph. |
| mi | `hakari` | `hākari` | The verdict label contradicts its own reason text and file_fix (both say "retire instead" and refuse a new row), and the evidence backs the prose, not |
| mi | `morehu` | `mōrehu` | Same lexeme with the macron on the first vowel dropped — kaikki carries `morehu` and `mōrehu` as parallel entries with overlapping senses ("remnants o |
| mi | `nga` | `ngā` | The production row is the missing-macron spelling of the plural article and its own gloss admits it — "macronless spelling of ngā" — which is the exac |
| mi | `wikitoria` | `wikitōria` | Identical definitions on both rows and kaikki lists `Wikitoria` and `Wikitōria` as the same given name; the unmacronised spelling is 19th-century miss |
| nl | `mais` | `maïs` | Same noun with the same gloss ('corn, maize'), differing only by the trema Dutch orthography requires on maïs to force the ma-ïs syllable break — 'mai |
| pt | `alcool` | `álcool` | Drops the acute of álcool (file rank 2265); pre-reform pointer gloss naming another spelling and carrying no meaning of its own. |
| pt | `alem` | `além` | Self-labelled pre-reform spelling of além — the acute on the final syllable is required. |
| pt | `amen` | `ámen` | The production row is a self-identified obsolete spelling of amém and carries no meaning, so it must stop being drawn — but note the file's form is no |
| pt | `açucar` | `açúcar` | Keeps the cedilla but drops the acute of açúcar (file rank 2718); a pre-reform pointer row with no meaning of its own. |
| pt | `camara` | `câmara` | Drops the circumflex of câmara (file rank 849); pre-reform pointer gloss with no meaning of its own. |
| pt | `ciumes` | `ciúmes` | The row labels itself the pre-1943 spelling of ciúmes, and the authoritative variety here is post-Acordo Brazilian, which writes the acute. |
| pt | `cú` | `cu` | Here the mark is spurious rather than missing: a monosyllable ending in -u takes no accent, the stored gloss admits 'misspelling of cu', and the file' |
| pt | `deviamos` | `devíamos` | Drops the acute of devíamos and the stored gloss literally reads 'misspelling of devíamos' — the self-identifying misspelling class CHECKS §3 deletes  |
| pt | `distancia` | `distância` | Self-labelled pre-reform spelling of distância — the circumflex on â is required, and the rare verb form distancia is not what this row glosses. |
| pt | `electrico` | `eléctrico` | electrico is the fully unaccented pre-reform form and a pointer gloss, so it retires — though the file's eléctrico is itself a pre-Acordo spelling who |
| pt | `espectaculo` | `espectáculo` | espectaculo is the unaccented pre-reform form with a pointer gloss and must stop being drawn; note the file's espectáculo is also pre-Acordo and its g |
| pt | `esperavamos` | `esperávamos` | Self-labelled pre-reform spelling of esperávamos — the acute on the antepenult is required by the current orthography. |
| pt | `espirito` | `espírito` | Self-labelled pre-reform spelling of espírito — the acute is required by the current orthography. |
| pt | `facil` | `fácil` | Drops the acute of fácil (file rank 497); a pre-reform pointer gloss that names another spelling and carries no meaning of its own. |
| pt | `familia` | `família` | Self-identified obsolete spelling of família (file rank 247) with the acute dropped; its 2 sentences should be re-tagged to the accented headword rath |
| pt | `frequencia` | `frequência` | Drops the circumflex of frequência; the row's own gloss is a self-identified pre-reform pointer with no meaning, and rank 9183 is unaccented typing of |
| pt | `fácilmente` | `facilmente` | The acute on a -mente adverb is pre-1971 orthography (and the correct Spanish spelling, which likely inflated the rank); post-Acordo Brazilian writes  |
| pt | `fôr` | `for` | The differential circumflex on fôr was abolished by the 1971 Brazilian reform; the modern written form is for, and the production row is a pointer wit |
| pt | `india` | `índia` | india is the acute-less spelling (its own gloss says pre-reform, of Índia), and the file already holds the accented form that serves both the country  |
| pt | `industria` | `indústria` | Drops the acute of indústria (file rank 3689); the stored row is a pre-reform pointer, so retiring it loses no sense, and the frequency is unaccented  |
| pt | `ja` | `já` | Drops the acute of já (file rank 40); the row's own gloss says 'obsolete spelling of já' and carries no meaning. |
| pt | `lingua` | `língua` | Self-labelled pre-reform spelling of língua — the acute is required. |
| pt | `mao` | `mão` | mao is mão with the tilde dropped — the first mark the profile names — and 'Mao Zedong' is a foreign proper name, not a Portuguese lexeme competing fo |
| pt | `maça` | `maca` | The row's only usage evidence in the committed bank is "A maça foi comida por mim." / "The apple was eaten by me.", so rank 8922 is carried by tilde-d |
| pt | `obvio` | `óbvio` | The first reader's own reason and file_fix both conclude "retire" — obvio is a real 1sg of obviar but nobody writes it at rank 9908, so the frequency  |
| pt | `opera` | `ópera` | As glossed the row is simply ópera with the acute dropped (it says so itself); the homographic verb form opera 'he/she operates' would need its own di |
| pt | `optimo` | `óptimo` | optimo is óptimo with the acute dropped, and its own gloss says pre-reform — retiring it is right under any reading, since neither form is the modern  |
| pt | `ouca` | `ouça` | ouca is ouça with the cedilla dropped — the cedilla is one of the marks the profile names as routinely lost — and the 'parish of Vagos' gloss is a CHE |
| pt | `pes` | `pés` | pes is pés with the acute dropped; there is no Portuguese word pes, and the stored gloss 'ESP' is extraction debris rather than a competing sense. |
| pt | `possivel` | `possível` | Drops the acute of possível (file rank 473); self-identified obsolete spelling, pointer gloss, no meaning of its own. |
| pt | `principe` | `príncipe` | Self-labelled pre-reform spelling of príncipe — the acute is required on the proparoxytone. |
| pt | `principio` | `princípio` | The row's own gloss calls it the pre-reform spelling of princípio, i.e. the acute dropped; the homographic verb form principio 'I begin' (principiar)  |
| pt | `qué` | `quê` | A duck-quack interjection cannot carry rank 5686 while quê (r108) holds 'what' with three real sentences, which is the exact shape of the course's own |
| pt | `taxi` | `táxi` | Self-labelled pre-reform spelling of táxi — the acute is required in the current orthography. |
| pt | `tinhamos` | `tínhamos` | Drops the acute of tínhamos (imperfect of ter, file rank 893); a self-identified obsolete spelling, so its one sentence belongs on the accented card. |
| pt | `transito` | `trânsito` | Drops the circumflex of trânsito (file rank 3088); the stored gloss is a pre-reform pointer, so the row teaches nothing the accented card does not. |
| pt | `tres` | `três` | Self-labelled pre-reform spelling of três; the circumflex is required and rank 216 belongs to the numeral. |
| pt | `unico` | `único` | Self-labelled pre-reform spelling of único — the acute on the proparoxytone is required by the current orthography. |
| pt | `ve` | `vê` | Not a distinct word: the Norse god is itself written Vé with an accent, so the headword 've' spells neither word, and rank 9923 is unaccented typing o |
| ro | `adăugă` | `adaugă` | These are two cells of one verb — adăugă is the perfect simplu against the file's present adaugă — and ro.md quarantines the perfectul simplu at C2 as |
| ro | `albina` | `albină` | Two village names (Brăila, Timiș) folding onto albina 'the bee'; the lemma albină is in the file at 7513. |
| ro | `amara` | `amară` | A Buzău village and an Ialomița town; the unmarked string is otherwise the breve-less amară, feminine of amar 'bitter'. |
| ro | `arsura` | `arsură` | arsura is the definite form of arsură 'burn' with the breve lost, glossed as a Vaslui commune; the file's marked lemma is the card to draw. |
| ro | `bucla` | `buclă` | The verdict contradicts its own reasoning — the reader concluded 'rare: retire instead' because rank 9692 on that string is the definite bucla 'the cu |
| ro | `buda` | `budă` | A Călărași village name; the breve-less string is otherwise just the definite buda of budă 'toilet, outhouse', already in the file at 8484. |
| ro | `cianura` | `cianură` | The `ă`→`a` is the definite-article suffix, so `cianura` is "the cyanide" — the same lexeme as the file's `cianură` — and the stored verb gloss "to cy |
| ro | `ciuperca` | `ciupercă` | Breve-less/definite twin of ciupercă 'mushroom' glossed as a Vaslui village — the ă is a letter and the gloss is proper-noun debris. |
| ro | `comuna` | `comună` | comuna is the definite singular of comună ('the commune') and its gloss is a bare inflection stub — one card per lexeme, and the file already carries  |
| ro | `cârciuma` | `cârciumă` | cârciuma is the definite form of the file's cârciumă 'pub, tavern' with the final breve dropped, glossed as a Sibiu river — debris, not a lexeme. |
| ro | `căprioara` | `căprioară` | The final `ă`→`a` here is the suffixed definite article (ro.md: "The definite article is a suffix — casă → casa"), so `căprioara` is simply "the roe d |
| ro | `eleva` | `elevă` | Same self-contradiction — the reason ends 'rare, retire instead', and bookish a eleva 'to elevate' cannot carry rank 4290, which is the definite eleva |
| ro | `fetița` | `fetiță` | fetița is the suffixed-definite form of the file's fetiță 'little girl' with the final breve lost, and its gloss is a Cimișlia village — proper-noun e |
| ro | `formata` | `formată` | The reader's own finding is that rank 4543 belongs to unaccented formată, so by the course's stated removal class ('rare twins of common words', docs/ |
| ro | `frunza` | `frunză` | A Gorj village name harvested as a homograph of frunza 'the leaf'; frunză is already in the file at 7447. |
| ro | `galbena` | `galbenă` | An Alba County village name folding onto galbenă, the feminine of galben 'yellow' (file 4593); the toponym cannot carry the rank the colour word earns |
| ro | `greaca` | `greacă` | greaca is the breve-less spelling of greacă glossed as a Giurgiu commune; the language/adjective belongs to the file's greacă row, whose own stub ('fe |
| ro | `gâsca` | `gâscă` | Same shape: an inflection-stub row for the definite form of gâscă 'goose', which the file holds at 7738 with the real gloss. |
| ro | `indura` | `îndura` | Romanian writes word-initial /ɨ/ with î, so indura is îndura minus the required circumflex, and the 'to indurate' gloss is Latinate extraction debris  |
| ro | `larga` | `largă` | Two village names (Bacău, Gorj) harvested as a homograph of largă, the feminine of larg 'wide' (file 5278). |
| ro | `lebăda` | `lebădă` | Same definite-article suffix (`lebădă` → `lebăda` "the swan"), so this is the file lexeme's inflected form, and its stored gloss is the bare proper-no |
| ro | `mania` | `mânia` | The circumflex is a letter, but 'a mania — to handle' is not standard Romanian (the handling verb is a mânui); the string's frequency is the definite  |
| ro | `mândra` | `mândră` | A Bârla village name whose spelling is also just the definite form of mândră (rank 2192), so the row teaches a place instead of the word the breve mar |
| ro | `mânăstire` | `mănăstire` | mânăstire is the older â-variant of the standard mănăstire 'monastery', which ro.md's Academy/dexonline scope rules out, and the row's gloss is a Timi |
| ro | `nobila` | `nobilă` | The Romanian verb for 'to ennoble' is a înnobila; nobila is the breve-less spelling (and definite form) of nobilă 'noblewoman' at 5386, so the verb ro |
| ro | `oarba` | `oarbă` | A Galați river name; oarba is otherwise only the definite of oarbă, the feminine of orb 'blind' (file 4506). |
| ro | `priza` | `priză` | Without the breve, priza is the definite form of the file's priză 'socket'; the row's 'to snuff' is the marginal homograph verb a priza, not a second  |
| ro | `pupă` | `pupa` | The reason itself says 'rare, retire instead': the nautical noun pupă is spelled identically to the far commoner 3sg pupă of a pupa (file 6079), so it |
| ro | `rara` | `rară` | There is no standard Romanian adverb rara: the string is the breve-less spelling (and definite form) of rară, feminine of rar (file 4480 / 2319), and  |
| ro | `romana` | `română` | A village in Uda; the unmarked string folds onto two file rows at once (romană 8293, română 8862), so a toponym row here can only muddy words the file |
| ro | `rotunda` | `rotundă` | The row is an Argeș village name harvested as a homograph; the string's frequency is the breve-marked rotundă and its definite form rotunda, and the t |
| ro | `rupta` | `ruptă` | Definite feminine form of rupt carrying an inflection-stub gloss; ruptă 'torn' is in the file at 4581 and rupt at 1081. |
| ro | `sarata` | `sărată` | A Botoșani village name folding onto sărată, the feminine of sărat 'salty' (file 7172); the breve-less spelling is not a second word. |
| ro | `spânzură` | `spânzura` | spânzură is the third-person singular of the file's a spânzura 'to hang'; the final breve is the tense ending, and the noun gloss 'pendulum' is an ext |
| ro | `stanca` | `stânca` | stanca is the â-less typing of stânca 'the rock' (lemma stâncă, r4133) carrying a Brăila village gloss; separately the file's stânca row is a bare inf |
| ro | `sârma` | `sârmă` | A river in Neamț harvested as a homograph of sârma 'the wire'; the lemma sârmă is in the file at 5524. |
| ro | `tava` | `tavă` | The row's own gloss calls it an 'alternative form of tavă' — a pointer with no meaning of its own, and the breve-less spelling is also the definite ta |
| ro | `unealta` | `unealtă` | Inflection-stub row for the definite form of unealtă 'tool, instrument' (file 7039); the -a is the suffixed article, not a dropped breve, and either w |
| ro | `vama` | `vamă` | A village in Iași and a Satu Mare commune, harvested as a homograph of vama 'the customs post'; the lemma vamă is in the file at 7944. |
| ro | `îndemâna` | `îndemână` | In running text îndemâna is the definite/genitive of the file's adverbial îndemână ('la îndemâna cuiva'), so the final ă is inflection rather than a s |
| ru | `вертолет` | `вертолёт` | вертолёт without ё; the row has no sentences and only the pointer gloss. |
| ru | `возьмем` | `возьмём` | возьмём minus ё; the row carries only 'alternative spelling of возьмём'. |
| ru | `возьмешь` | `возьмёшь` | возьмёшь minus ё; self-identifying pointer gloss. |
| ru | `времен` | `времён` | The genitive plural is времён; времен is the ё-less typing and glosses itself so. |
| ru | `дает` | `даёт` | даёт without its ё; the row glosses itself as an alternative spelling. |
| ru | `днем` | `днём` | The adverb is днём; the ё-less spelling is a typing variant, not another word. |
| ru | `ее` | `её` | ё dropped from её; the gloss is the self-identifying pointer 'alternative spelling of её' and no separate word ее exists. |
| ru | `еще` | `ещё` | The ё-less typing of ещё, and the row says so itself: its only gloss is the pointer 'alternative spelling of ещё', no meaning of its own. |
| ru | `зеленый` | `зелёный` | зелёный without ё; the file holds зелёный at rank 2695 with the real gloss. |
| ru | `зовет` | `зовёт` | зовёт minus its ё, glossed 'alternative spelling of зовёт'. |
| ru | `идем` | `идём` | ё-less typing of идём; the gloss is the pointer only. |
| ru | `идет` | `идёт` | The ё-less typing of идёт — ru.md records the file's discipline here explicitly (75 идёт / 0 идет). |
| ru | `идете` | `идёте` | идёте minus its ё; pointer gloss only. |
| ru | `идешь` | `идёшь` | ё dropped from идёшь; pointer gloss only. |
| ru | `легкий` | `лёгкий` | лёгкий 'light' written without ё; pointer gloss only, and the file teaches лёгкий at rank 1189. |
| ru | `лед` | `лёд` | лёд 'ice' spelt without ё; unlike лёт/лет there is no е-spelled word лед to protect. |
| ru | `мое` | `моё` | моё written without its ё; the row's whole gloss is 'alternative spelling of моё'. |
| ru | `насчет` | `насчёт` | The preposition is насчёт; this row is the ё-less typing and glosses itself as such. |
| ru | `нее` | `неё` | The ё-less spelling of неё, carrying only 'alternative spelling of неё' — a pointer, not a sense. |
| ru | `остается` | `остаётся` | остаётся minus its ё, glossed 'alternative spelling of остаётся'. |
| ru | `отчет` | `отчёт` | отчёт 'report' without its ё; a self-identifying alternative-spelling row. |
| ru | `партнер` | `партнёр` | партнёр without its ё; the file already teaches партнёр at rank 2029. |
| ru | `пес` | `пёс` | пёс 'dog' written without ё; pointer gloss and no rival lexeme. |
| ru | `прием` | `приём` | приём 'reception' spelt without ё; pointer gloss, no rival word. |
| ru | `ребенок` | `ребёнок` | ребёнок written without ё; self-identifying pointer gloss and no rival lexeme. |
| ru | `самолет` | `самолёт` | самолёт written without ё; no lexeme самолет, and the file already holds самолёт at rank 1523. |
| ru | `свое` | `своё` | своё minus its ё, glossed 'alternative spelling of своё'. |
| ru | `своем` | `своём` | своём minus its ё, glossed 'alternative spelling of своём'. |
| ru | `семьей` | `семьёй` | The instrumental семьёй spelt without ё; pointer gloss only. |
| ru | `серьезно` | `серьёзно` | ё dropped from серьёзно; pointer gloss only, and no word серьезно exists. |
| ru | `серьезный` | `серьёзный` | серьёзный minus its ё; the file's серьёзный at rank 861 is the card to keep. |
| ru | `счет` | `счёт` | счёт 'bill, count' spelt without ё; there is no separate word счет. |
| ru | `твое` | `твоё` | твоё minus its ё, glossed 'alternative spelling of твоё'. |
| ru | `твоем` | `твоём` | твоём minus its ё, glossed 'alternative spelling of твоём'. |
| ru | `тетя` | `тётя` | тётя 'aunt' spelt тетя; no such separate word, pointer gloss only. |
| ru | `черная` | `чёрная` | чёрная without ё, glossed 'alternative spelling of чёрная'. |
| ru | `черный` | `чёрный` | чёрный without ё; the file's чёрный (rank 1147) is the form the course teaches. |
| ru | `шел` | `шёл` | The past шёл written without ё; pointer gloss, no competing lexeme. |
| tr | `dükkan` | `dükkân` | The production row's own gloss is the pointer "misspelling of dükkân" and carries no meaning of its own; TDK writes the circumflex after k (dükkân, li |
| tr | `mahçup` | `mahcup` | Here the mark runs the other way — TDK writes mahcup with plain `c` (Arabic maḥcūb) and `mahçup` is the common ç-hypercorrection, self-identified by i |
| tr | `zeka` | `zekâ` | Same pointer-gloss shape — the production row reads "misspelling of zekâ" and holds no sense of its own; TDK spells the word zekâ with the circumflex  |
| yo | `ade` | `adé` | adé 'crown' with the acute stripped; the name-prefix remark is the same entry's usage note. |
| yo | `agba` | `àgbà` | The gloss 'adult, elder; senior institution' matches àgbà exactly, so this is àgbà with both graves stripped, not agbá 'barrel'. |
| yo | `agbalagba` | `àgbàlagbà` | Three graves missing from àgbàlagbà 'elder, adult'; the gloss is word-for-word the file's. |
| yo | `awọn` | `àwọn` | Missing the grave on à-; yo.md names rank 8 awọn→àwọn as an attested top-band repair, and the "tongue" gloss is a wrong-lexeme extraction artefact (to |
| yo | `aye` | `ayé` | Identical gloss 'world; life'; the production row is ayé with the acute stripped, and ayé is the only member of this fold group. |
| yo | `baba` | `bàbá` | Same noun and gloss 'father, dad; term of respect for an older man'; the production row drops the grave and acute of bàbá. |
| yo | `bata` | `bàtà` | Both glossed "shoe", so the row is `bàtà` with its graves stripped — the tone-distinct `bàtá` (the drum) is a third word neither row claims. |
| yo | `bawo` | `báwo` | Same question word "how" missing the acute of `báwo`; yo.md's hint standard 4 already treats `Báwo` as the course form. |
| yo | `bayii` | `báyìí` | Same adverb, same POS, same gloss; the production row simply drops the acute and both graves of báyìí, and it is the only member of this fold group. |
| yo | `bi` | `bí` | "The name of the Latin script letter B/b" is extraction debris folding onto the real conjunction bí (r12), which already carries the acute the product |
| yo | `daadaa` | `dáadáa` | Same adverb "well; gladly" with both acutes of `dáadáa` stripped. |
| yo | `dara` | `dára` | dára 'to be good' missing its acute; same pos, same gloss. |
| yo | `dokita` | `dókítà` | Same loan noun "doctor" with the three tone marks of `dókítà` stripped. |
| yo | `dudu` | `dúdú` | dúdú 'black' with both high tones stripped; the added 'dark-skinned' sense is the same adjective. |
| yo | `dun` | `dùn` | Identical gloss; the production row drops the grave on dùn 'to be sweet' (dún 'to sound' is a different word and is not what this gloss names). |
| yo | `duro` | `dúró` | dúró 'to wait, to stay' with both acutes stripped; 'to stand' is the same verb's third sense. |
| yo | `ede` | `èdè` | The gloss 'language; speech' matches èdè (r53), so the production row is èdè with both graves stripped, not the separate word edé 'shrimp'. |
| yo | `eeyan` | `èèyàn` | All three graves of èèyàn 'person' are absent; same noun, same gloss. |
| yo | `ejo` | `ejò` | 'Snake' is ejò and this is that noun without its grave; the underdotted ẹjọ 'eight' (rank 281) is unaffected. |
| yo | `eko` | `ẹkọ` | Mis-paired by the fold: this row is the proper name Èkó 'Lagos' (file rank 116, same pos and gloss) with both tones stripped — the underdotted ẹkọ 'le |
| yo | `emi` | `èmi` | Identical gloss for the emphatic 1sg pronoun; only the grave of `èmi` is missing — the genuinely different `ẹ̀mí` "spirit" differs by the underdot and |
| yo | `erekuṣu` | `erékùṣù` | The underdots are present on both rows and only the tone marks of `erékùṣù` are missing, so this is a pure tone twin; the bank carries the island sent |
| yo | `eyi` | `èyí` | Same demonstrative pronoun and gloss; the production row drops the grave and acute of èyí, the only real word in this fold group. |
| yo | `fa` | `fà` | Same verb and gloss 'to pull; to suck'; the production row is fà with the grave stripped, and fà is the only real word in this fold group. |
| yo | `fila` | `fìlà` | Character-for-character the same definition ("hat, cap…"); only the two graves of `fìlà` are missing, and the bank has one sentence tagged both ways ( |
| yo | `fun` | `fún` | Same verb and near-identical sense list (give / squeeze / strangle); the production row is fún with the acute stripped, and fún is the only real word  |
| yo | `gbadura` | `gbàdúrà` | Same verb "to pray" with all three tone marks of `gbàdúrà` stripped. |
| yo | `gbagbe` | `gbàgbé` | gbàgbé 'to forget' with its grave and acute stripped; same verb. |
| yo | `gbe` | `gbẹ` | The gloss 'to carry; to lift' is the file's gbé at rank 47 with its acute stripped; the paired gbẹ 'to plant' differs by the underdot and is a differe |
| yo | `gbo` | `gbó` | Both rows gloss 'to bark (like a dog)', which is gbó — the acute is the only thing missing, and the dotted gbọ 'to hear' (rank 160) is a separate row  |
| yo | `gbolohun` | `gbólóhùn` | Same noun with the three tone marks of `gbólóhùn` stripped; the bank carries one sentence tagged both ways (lines 63 and 112). |
| yo | `gbona` | `gbóná` | Same word "to be hot" with both acutes of `gbóná` stripped; the mis-tagged pos ("noun" for a verb) is shared by both rows and is a separate defect. |
| yo | `ge` | `gẹ` | Mis-paired: 'to cut something; especially using a tool' is the file's gé at rank 549, verbatim — this row is gé without its acute, not the underdotted |
| yo | `ibeere` | `ìbéèrè` | Same noun "question" with all four tone marks of `ìbéèrè` stripped. |
| yo | `ile` | `ilẹ` | The gloss is the file's ilé 'home, house' at rank 24 with its tone stripped — yo.md states outright that after the toning pass "ile is no longer a wor |
| yo | `ina` | `iná` | iná 'fire, light' with the final acute stripped; glosses match exactly. |
| yo | `inu` | `inú` | Same lemma missing only the high tone on the final vowel (inú 'inside, stomach'); the production row's extra sense 'mind, heart' is a fuller kaikki gl |
| yo | `iroyin` | `ìròyìn` | All three graves of ìròyìn 'news' are missing; the gloss is identical to the file row. |
| yo | `iwaju` | `iwájú` | iwájú 'front' with both acutes stripped; identical gloss and pos. |
| yo | `iwe` | `iwẹ` | The gloss 'paper; document; book' is the file's ìwé at rank 59 with its tones stripped; the paired iwẹ 'bathing, swimming' differs by the underdot and |
| yo | `iya` | `ìyá` | The gloss 'mother, mom' fixes this as ìyá with its grave and acute stripped, not the separate word ìyà 'suffering'. |
| yo | `iyawo` | `ìyàwó` | Same noun and sense set (wife, junior wife); the production row drops the two graves and the acute of ìyàwó. |
| yo | `ja` | `jà` | 'To fight, to wrestle' is jà; the production row is that word with the grave stripped, and its extra 'break out (as in a war)' sense belongs to the sa |
| yo | `jade` | `jáde` | Missing the acute on jáde 'to go out'; glosses are identical. |
| yo | `ji` | `jí` | The written form is jí with the acute stripped, and its gloss is the alphabet letter-name sense (extraction debris a learner never meets), so retiring |
| yo | `jijẹ` | `jíjẹ` | jíjẹ 'eating' with the acute on the reduplicated syllable stripped; 'food' is an extra sense of the same nominalisation. |
| yo | `jinna` | `jìnnà` | Both glossed "to be far", so the row is `jìnnà` with its graves dropped — the tone-distinct `jinná` ("to be cooked") is a third word neither row claim |
| yo | `jokoo` | `jókòó` | Same verb "to sit (down)" with all three tone marks of `jókòó` stripped. |
| yo | `ka` | `kà` | Identical verb gloss 'to count; to read'; the production row is kà with the grave stripped. |
| yo | `kere` | `kéré` | Same verb "to be small" with both acutes stripped; `kéré` is the only word this skeleton spells at this gloss. |
| yo | `ki` | `kí` | "The name of the Latin script letter K/k" is extraction debris, not a Yoruba word, and it folds straight onto the real particle kí (r6); yo.md's headw |
| yo | `ko` | `kọ` | The production row's gloss is verbatim the negator, which the file already carries correctly as kò at rank 7 — this is kò missing its grave, not the p |
| yo | `kutukutu` | `kùtùkùtù` | Same word "early" with all four graves of `kùtùkùtù` stripped. |
| yo | `lanaa` | `lánàá` | Same adverb "yesterday" with all three tone marks of `lánàá` stripped. |
| yo | `lati` | `láti` | Same preposition and one of the file row's own senses ('from — a place'); the production row is láti with the acute stripped. |
| yo | `le` | `lẹ` | The gloss matches the file's lè 'to be able, can' at rank 21 word for word, so this is lè with the grave stripped; the paired lẹ 'to glue' differs by  |
| yo | `lonii` | `lónìí` | Same adverb "today" with the three tone marks of `lónìí` (ní + òní) stripped. |
| yo | `lori` | `lórí` | Both acutes are missing from lórí 'on top of'; same part of speech, same gloss. |
| yo | `maa` | `máa` | Both rows are the same pre-verbal future/anticipative particle; the production row is máa with the acute stripped. |
| yo | `meje` | `méje` | Same numeral "seven"; the production row simply drops the acute on `mé-`, and there is no distinct `meje` lexeme. |
| yo | `meji` | `méjì` | Numeral 'two' méjì with both tone marks stripped; identical gloss. |
| yo | `meloo` | `mélòó` | Same determiner "how many"; `mélòó` written bare is the untoned skeleton, not another word. |
| yo | `na` | `nà` | Same verb and gloss ('to beat; to hit; to smack'); the production row is nà with the grave stripped, and nà is the only real word in this fold group. |
| yo | `naa` | `náà` | Same determiner and gloss ('that, the'); the production row drops the acute and grave of náà. |
| yo | `nibo` | `níbo` | Same question word "where" missing the acute of `níbo`, the form yo.md's hint standards already cite as `Níbo`. |
| yo | `obinrin` | `obìnrin` | Same noun and gloss 'woman, female; wife'; the production row is obìnrin with the grave on -bì- stripped. |
| yo | `ojo` | `òjò` | 'Rain' is òjò and the production row is it with both graves stripped; the dotted ọjọ 'day' (rank 46) is untouched by this retire. |
| yo | `ole` | `ọlẹ` | Mis-paired: 'thief' is olè, already in the file at rank 174 with that exact gloss, so this row is olè without its grave — not the doubly underdotted ọ |
| yo | `ologbo` | `ológbò` | Identical gloss "cat"; the production row is `ológbò` with both tone marks stripped, and the sentence bank already carries the same sentence under the |
| yo | `olu` | `olú` | olú 'leader, chief' missing its acute; the trailing name-prefix note is the same entry's usage remark. |
| yo | `ori` | `orí` | The gloss 'head; top; leader' fixes this as orí with its acute stripped, not the separate word òrí 'shea butter'. |
| yo | `orukọ` | `orúkọ` | The underdot survived but the acute on orúkọ 'name' did not; one word, one card. |
| yo | `oun` | `òun` | Same emphatic third-person singular pronoun and gloss; the production row is òun with the grave stripped (ohun 'thing' is spelled with h and does not  |
| yo | `owe` | `ọwẹ` | The fold mis-paired this: the production gloss 'proverb, adage, saying' is word-for-word the file's òwe at rank 102, so the row is òwe with its grave  |
| yo | `owo` | `ọwọ` | The gloss 'money, cash; cowrie' is the file's owó at rank 39 with its acute stripped; the paired ọwọ 'broom' differs by two underdots and is a differe |
| yo | `pada` | `padà` | padà 'to return' missing its final grave; 'to transform' is a further sense of the same verb, not a second word. |
| yo | `pari` | `parí` | parí 'to finish' missing its acute; glosses identical. |
| yo | `pataki` | `pàtàkì` | Same noun and gloss 'importance'; the production row drops all three graves of pàtàkì, the only real word in this fold group. |
| yo | `pe` | `pẹ` | The gloss 'to call, to pronounce, to summon' is verbatim the file's pè at rank 17 — the row is pè missing its grave — while the paired pẹ 'to be late' |
| yo | `ri` | `rí` | "The name of the Latin script letter R/r" is extraction debris folding onto the real verb rí 'to see' (r38), which already carries the acute. |
| yo | `rin` | `rìn` | rìn 'to walk; to associate with' missing its grave; gloss copied verbatim. |
| yo | `ro` | `rọ` | Mis-paired: 'to think' is rò, which the file already carries at rank 156 — the production row is rò without its grave, not the underdotted rọ 'to para |
| yo | `sa` | `sà` | Same one-word gloss 'Sir' on both rows; the production form simply lacks the grave of sà. |
| yo | `sare` | `sáré` | Same verb "to run" with both acutes missing — `sáré` (from sá + eré) is the Standard Yoruba spelling and no untoned `sare` is a separate word. |
| yo | `se` | `sẹ` | Mis-paired: 'to cook; to boil' is sè, in the file at rank 210 with that exact gloss — the production row is sè without its grave, and the underdotted  |
| yo | `si` | `sì` | A letter-name gloss ("The name of the Latin script letter S/s") is extraction debris that folds onto the three real words in this group — sí (r9), ṣí  |
| yo | `sun` | `sùn` | 'To sleep' is sùn; the production row is that verb without its grave (sun 'to roast' and sún 'to move closer' are other words, and neither is glossed  |
| yo | `tobi` | `tóbi` | tóbi 'to be big' missing its acute; the added 'great, mighty' senses are the same verb. |
| yo | `tutu` | `tutù` | Same verb, the production row missing the grave on the second syllable; the extra senses it carries are a gloss difference, not a different word. |
| yo | `waa` | `wàá` | Identical definition ("contraction of ìwọ + á"); `wàá` written `waa` is the same contraction with grave and acute stripped. |
| yo | `wahala` | `wàhálà` | Identical gloss "trouble, problem, difficulty"; only the grave-acute-grave pattern of `wàhálà` is missing. |
| yo | `wọle` | `wọlé` | Underdot present, acute on wọlé 'to enter' missing; glosses identical. |
| yo | `yii` | `yìí` | Determiner 'this' written without its grave-plus-acute pattern (yìí); identical gloss and pos. |
| yo | `yin` | `yín` | 2pl/honorific possessive yín with the acute stripped; the gloss is copied verbatim from the file row. |
| yo | `yoo` | `yóò` | Future/intentional marker yóò with its acute and grave stripped; the longer production gloss is the same kaikki entry, unabridged. |
| yo | `yoruba` | `yorùbá` | Same proper noun and gloss; the production row drops the grave and acute of yorùbá, the only real word in this fold group. |
| yo | `ṣalaye` | `ṣàlàyé` | Same verb "to explain", ṣ intact on both, only the three tone marks of `ṣàlàyé` stripped. |
| yo | `ṣere` | `ṣeré` | ṣeré 'to play' missing the acute on the second syllable; same gloss and pos. |
| yo | `ṣi` | `sì` | Mis-paired — the underdotted ṣ is not the file's plain-s sì; this row is the untoned ṣí whose gloss is the letter-name of Ṣ/ṣ, pure extraction debris, |
| yo | `ṣokoto` | `sokoto` | The file already carries `ṣòkòtò` at rank 572 with the identical gloss "pants, trousers" and the sentence bank tags the same sentence `Mo fẹ́ ṣòkòtò.` |
| yo | `ṣoro` | `ṣòro` | ṣòro 'to be difficult' missing its grave; the similarly folding sọrọ 'to talk' (rank 261) is a different word and is not this row. |
| yo | `ṣubu` | `ṣubú` | The underdot on ṣ is present in both — only the final acute of `ṣubú` "to fall" is missing, so this is a tone-stripped twin. |
| yo | `ọja` | `ọjà` | Dots already match; only the grave on ọjà 'market' is absent, and the shared market/merchandise senses show it is the same noun. |
| yo | `ọkunrin` | `ọkùnrin` | Same noun and gloss 'man, male; manliness, bravery'; the production row is ọkùnrin with the grave on -kù- stripped. |
| yo | `ọmọde` | `ọmọdé` | Both underdots survived, the acute on ọmọdé 'child' did not; identical gloss. |
| yo | `ọti` | `oti` | Mis-paired: the production row already has the underdot and matches the file's ọtí 'alcohol, liquor' (rank 326) exactly — only the high tone is missin |
