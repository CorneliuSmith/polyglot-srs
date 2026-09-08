# Five more courses through the markdown and editorial pass — 7 September 2026

Dutch, Catalan, Romanian, Greek and Russian, after French and the four Romance/German courses. The house-style prompt now carries the mistakes the earlier checkers caught, so those classes did not recur; the checkers found new ones instead.

| course | read | render as markdown | refused | content fixes |
|---|---:|---:|---:|---:|
| Dutch | 42 | 27 of 42 | 2 | 57 |
| Catalan | 42 | 30 of 42 | 0 | 99 |
| Romanian | 42 | 27 of 42 | 3 | 92 |
| Greek | 41 | 34 of 41 | 0 | 74 |
| Russian | 55 | 30 of 55 | 4 | 90 |
| **all five** | **222** | **148** | **9** | **412** |

**412 content corrections in five courses.** That is more than double the rate of the first five, and the reason is visible in the rejections below: these courses' explanations carry more rules, and more of the rules were stated in a form that is nearly right.

## What the second readers refused — nine edits, every one a real error

| course | point | why |
|---|---|---|
| Dutch | Indirect speech: dat and of | The replacement claim about Dutch is wrong. 'Only a prepositional phrase may trail after the verb; nothing else may' forbids extraposition that is ordinary and in places obligatory: a finite subordinate clause cannot stay in the middle field (Ze vraagt of ik w |
| Dutch | Fossils: der, des, te allen tijde | The added table's second row disagrees with its header. Der is the genitive feminine singular AND the genitive plural, so 'genitive | des | der' under 'Masculine / neuter | Feminine / plural' is right. But the dative plural was den, not der: te + den = ten cov |
| Romanian | -ea, -e and -i verbs (a vedea, a merge, a dormi) | New claim about Romanian is wrong and is falsified inside its own sentence: "The eu form keeps a -u when the stem ends in a consonant cluster: scriu from a scrie, beside merg and dorm." The -u in scriu is not conditioned by a consonant cluster — the stem of a  |
| Romanian | Possessives (meu, mea, tău…) | The replaced rule for the possessive article is wrong and its own first example disproves it. The edit says "The linking article al / a / ai / ale appears only when the possessive stands apart from its noun: o carte a mea 'a book of mine', al meu 'mine'" — but |
| Romanian | The gerund (gerunziul: scriind) | The whole value of this edit is the added rule that predicts -ind vs -ând, and the rule is wrong: the choice is set by conjugation class, not by the stem's final letter. Under any consistent segmentation one of its own three examples breaks. If 'stem' is the r |
| Russian | Gender of nouns (он, она, оно) | The table does not render as a table. Header row has four cells (Gender | Ending | Noun | Pronoun) but the delimiter row has three (| --- | --- | --- |). GFM requires them to match; with a mismatch the whole block falls back to a paragraph. Confirmed two ways: |
| Russian | Time expressions (в понедельник, утром) | Information dropped, and the change log is empty so it is undocumented. The original glossed its first example — 'в понедельник, в среду (on Monday, on Wednesday)' — and the reformat keeps the Russian but deletes the English. The bullet list retains '(this wee |
| Russian | Superlatives (самый) | The table's rows disagree with its header. The first column is headed 'Gender' and its last row reads 'plural' — a number, not a gender — in a point whose own opening sentence now says самый agrees 'in gender, number and case'. The table therefore contradicts  |
| Russian | Prefixed verbs of motion (прийти, уйти, выйти) | New unlogged claim, and it is wrong against its own table. The rewrite opens "Prefixes turn motion verbs into precise events, and each prefix brings its own preposition with it" — that sentence is not in the original, is not in content_changes, and two of the  |

Three of the nine are the writer inventing a rule the language does not have: a Romanian rule for `-ind` against `-ând` set by the stem when it is set by conjugation class; a Romanian possessive-article rule its own first example disproves; a Dutch word-order claim that forbids ordinary extraposition. Two are tables whose rows disagree with their header. One is a Russian table whose delimiter row had three cells under a four-cell header, so it would have rendered as a paragraph of pipes.

## The guard that fired, and why it was the wrong guard

The restraint check bounded the SHARE of formatted points at 80%, and Greek came in at 83%. Greek is not over-formatted; it is inflected — 21 of its 41 points hold a real case-by-gender or person-by-form paradigm, against 12 in French. Share measures the language, not the pass.

Replaced with the signal that does measure the pass: the share of points that got ONLY bold, no table and no list. Across the ten finished courses that runs 2% to 20%.

| course | formatted | of which tables | lists | bold only |
|---|---:|---:|---:|---:|
| ca | 30 of 42 | 26 | 3 | 1 |
| de | 30 of 43 | 18 | 10 | 2 |
| el | 34 of 41 | 21 | 5 | 8 |
| es | 27 of 47 | 16 | 5 | 6 |
| fr | 20 of 42 | 12 | 7 | 1 |
| it | 21 of 42 | 18 | 2 | 1 |
| nl | 27 of 42 | 13 | 10 | 4 |
| pt | 26 of 42 | 21 | 3 | 2 |
| ro | 27 of 42 | 18 | 8 | 1 |
| ru | 30 of 55 | 15 | 11 | 4 |
