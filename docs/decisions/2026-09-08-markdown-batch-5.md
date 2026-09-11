# The last nine courses through the markdown pass — 8 September 2026

English, Hausa, Indonesian, Jamaican Patois, Latin, Māori, Tagalog, Xhosa and Yoruba. Korean is held for its duplicate-point decision, so **26 of 27 courses have now had this pass**.

| course | read | render as markdown | refused | content fixes |
|---|---:|---:|---:|---:|
| English | 43 | 27 of 43 | 2 | 42 |
| Hausa | 42 | 28 of 42 | 5 | 80 |
| Indonesian | 40 | 35 of 40 | 3 | 67 |
| Jamaican Patois | 32 | 29 of 32 | 1 | 29 |
| Latin | 41 | 36 of 41 | 2 | 30 |
| Māori | 40 | 29 of 40 | 2 | 53 |
| Tagalog | 40 | 36 of 40 | 3 | 60 |
| Xhosa | 40 | 20 of 40 | 7 | 100 |
| Yoruba | 40 | 28 of 40 | 2 | 47 |
| **all nine** | **358** | **268** | **27** | **508** |

## Twenty-seven refusals, and one new class

**Four Hausa edits would have broken the card, not the grammar.** The writer moved an example run into its own paragraph and dropped the colon that had been holding it together. `ExplanationView`'s typesetter peels an introduction off a paragraph that has one; without the colon it peels the first two words instead, so the card shows a stray `Ina da` line above a table whose first row has lost its subject. The checker knew the renderer better than the applier's gate did — the gate checks what markdown the card can render, not what the plain-text typesetter does with a paragraph that has no markdown at all.

The rest are the classes the earlier batches established: a rule the writer invented that the point's own drills falsify (Tagalog aspect reduplication, Xhosa `-na-` merging, Xhosa when-clauses, Yoruba tone pairs), information dropped without declaring it, and bold on one item of a list where the point teaches all of them.

| course | point | why |
|---|---|---|
| English | Question tags and indirect questions | Bold on **aren't you** is not the taught form and is bold on one item where all are taught. The paragraph shows three tags — aren't you, does she, didn't he — as parallel illustrations of one rule (and of both directions of the po |
| English | Formal connectors (notwithstanding, albeit) | New and wrong claim about English: 'albeit and though take a reduced phrase rather than a clause'. That is true of albeit and false of though, which is an ordinary clause subordinator (though it was raining, we went out; it's expe |
| Hausa | Object pronouns | Invented claim, wrong, and contradicted by the edit's own table. The new sentence reads "Two of them differ from the independent pronouns: ka and ta here, not kai and ita." Three differ, not two: the independent set taught in poin |
| Hausa | Subjunctive (ka tafi, mu je…) | Breaks on the card. Moving the example run into its own paragraph strips the colon that used to protect it, so ExplanationView falls to the TERM_GLOSS path and fires the intro-peel heuristic (frontend/src/components/ExplanationVie |
| Hausa | Relative continuous -ke | Same renderer break. The trailing example paragraph has no colon, so the intro-peel fires: the card shows a stray 'Ina kake' line, then a table whose first row is 'zaune? | Where do you live?' — pairing zaune ('residing', per the  |
| Hausa | To have: da (ina da, ba ni da) | Same renderer break, and the worst of the four. The colon-less example paragraph peels to a stray 'Ina da' line above a table whose first row reads 'mota | I have a car' — the card would teach that mota means 'I have a car'. The o |
| Hausa | Impersonal an / ana (passive sense) | Same renderer break. 'An gina gida (A house was built — 'one built'), …' as a colon-less paragraph peels to a stray 'An gina' line plus a first row 'gida | A house was built — 'one built'' — gida ('house') glossed as the whole Eng |
| Indonesian | Negation: tidak vs. bukan | Information dropped, and content_changes is empty so the loss is undeclared. The original glossed both examples — "tidak besar = 'not big'" and "bukan guru = 'not a teacher'". The table's Example column carries them bare, so nowhe |
| Indonesian | Time markers before the verb: sudah, belum, akan | Same defect: the compression into the table silently drops the three example translations the original carried — 'Saya sudah makan = I've already eaten', 'Saya belum makan = I haven't eaten yet', 'Saya akan makan = I will eat' — a |
| Indonesian | Modality: bisa, boleh, harus, mau | Formatting: the only bold in the point falls on **tidak**, which is not this point's taught form — the point teaches bisa/boleh/harus/mau/perlu (all unbolded, in the table), and tidak is the headline form of point 2, 'Negation: ti |
| Jamaican Patois | Negation: no and duon | Undeclared content change: content_changes is empty, but the rewrite adds a grammatical claim the original point never made — naa is now scoped "for the progressive and the going-to future" where the original said only "no + a fus |
| Latin | Imperfect tense (-bam): what used to happen | Malformed table: the header and all six body rows have three cells (`| Person | -are verbs | sum |`), but the delimiter row has two (`| --- | --- |`). GFM does not recognise a table whose delimiter row disagrees with its header, s |
| Latin | Conditionals: the three types of si-clause | Silent deletion of a term of art, unlisted in content_changes. The original named the second type "Future-less-vivid (\"should ... would\")"; the edit reduces it to "should-would" and drops the technical name entirely. "Future les |
| Māori | Passive verbs (kua kainga) | The suffix list lost the original's "and others" hedge and now reads as a closed inventory of eight, and the deletion is not in content_changes. It omits -na, which the course's own sentence bank uses: data/mi_sentences.tsv line 3 |
| Māori | Nō and Mō — 'of/from' and 'for' | mo lost its future-possession sense with no content_changes entry. The original read "mo marks a benefactive or future belonging 'for/about'"; the edit leaves "who something is for, or what it is about", and the table row is only  |
| Tagalog | The linker na | The three-row table is right; the sentence after it is a new and wrong claim about Tagalog. Linker allomorphy is obligatory, not a preference, so -ng/-g are not merely "the one you will usually hear and read", and separately-writt |
| Tagalog | Aspect: completed, incompleted, contemplated | "The incompleted and the contemplated both double the first syllable of the root" is falsified by this point's own drill Naghihintay. hintay syllabifies hin-tay, so doubling the first syllable gives *naghinhintay; Tagalog copies t |
| Tagalog | Locative focus with -an | The added stem-change rule is wrong for its own leading example and for this point's first drill. "A few roots drop the vowel before their last consonant (bili → bilhan, bigay → bigyan)": bili's last consonant is l and the vowel b |
| Xhosa | Subject concords and the present (ndi-, u-, ba-…) | The new hedge does not fix the counter-example its own changelog names. "Every verb in a statement starts with a subject concord" is still falsified by the infinitives: "Ndiza kufunda" (point 11, drill 1) is a statement and kufund |
| Xhosa | Questions (ntoni, bani, phi) | Formatting adds nothing: `ngubani` is a whole word in code, and the four other question words taught in the same point (ntoni, phi, nini, bani) are plain — including bani in the very same sentence ("`ngu-` plus bani"). Code is use |
| Xhosa | To have: -na- | The invented merge rule is falsified by the point's own drill 3. "An i- noun gives -ne-" applied to iincwadi predicts Ndinencwadi, but the drill's answer is Ndineencwadi (hint "ndi + na + iincwadi", translation "I have two books") |
| Xhosa | Recent past (-ile) | The added mechanism is wrong for one of the two examples it is attached to. "The stem's final -la and the -ile merge into -le" predicts ulale from lala, but the drill's answer is ulele (and the Xhosa data has elele); lala raises t |
| Xhosa | Demonstratives (lo, le, eli…) | Formatting adds nothing: **lo** is bolded in "**lo** mntu (this person), le ncwadi (this book), aba bantwana (these children)" while `le` and `aba` — equally taught demonstratives in the same run — are plain. Bold on one item wher |
| Xhosa | Causative (-isa) | A changed claim about Xhosa that is now wrong, and not listed in content_changes: the original glossed `Ndisebenzisa ifowuni` as "(I use a phone)"; the edit changes it to "(I am using my phone)". The possessive is unlicensed — `if |
| Xhosa | When-clauses: xa + participial | Invented rule falsified by the point's own drill and by the writer's own table. The edit adds "Only the third person moves, so the two u- forms are the ones to watch" — but the table directly above it has the row `| it | ku- | ku- |
| Yoruba | Tones change meaning | The added sentence makes a wrong claim about the pair it cites. "owó (money) and ọwọ́ (hand) differ by the dot as well as by the marks" says the two differ tonally as well as by the underdot. They do not: both are mid-high (o + wó |
| Yoruba | Adjectives are verbs (dára, tóbi) | The rewrite replaces a wrong rule with a different wrong rule. Removing "Before a noun they become participles" is correct — ńlá is a separate adjective, not a form of tóbi. But the replacement, "To modify a noun, a quality verb n |

## The restraint guard, calibrated twice and then rebuilt

It first bounded the SHARE of formatted points at 80%. **Greek** tripped it at 83% — and Greek is not over-formatted, it is inflected: 21 of its 41 points hold a real paradigm against 12 in French.

It then bounded the share of points that got ONLY bold. **Jamaican** tripped it at 38% and **Yoruba** at 38% — and their bolds are all correct. Both languages teach particles, so a point is often one sentence naming one form: `**dem**` after the noun for the plural, `**Kò**` before the verb for negation. There is no paradigm to table.

Both thresholds were measuring the LANGUAGE. What measures the PASS is whether a bold names the form the point actually teaches, which is checkable: across the 26 finished courses **208 of 238 bolds (87%)** match a string in the point's title or one of its drill answers. That is the guard now.

