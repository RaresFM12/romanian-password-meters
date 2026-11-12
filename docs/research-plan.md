# How Well Do Password Strength Meters Work for Romanian Passwords?

## An Empirical Evaluation of zxcvbn on Romanian Passwords, a Romanian-Aware Extension, and a Study of Cross-Language Transfer Within the Romance Family

**Type:** Semester research project, 3rd year, Computer Science
**Version:** 2.4 (2026-10-25). History: **v2.4** (2026-10-25, with the full Lab 3–4 submission): scope set to the Romanian study (RQ1–RQ5), the Romance-family study (RQ6) kept as future work; RO-cognate / RO-noncognate moved with it (dataset now ~29,500); weeks 9–10 reassigned to the real-world validation and deployment cost; NIST reference updated to SP 800-63B-4 (July 2025), which recommends NFC normalisation (not NFKC/NFKD as the withdrawn edition did) and forbids composition rules; Bonneau (2012) added as a counterpoint on language-specific dictionaries. **v2.3** (2026-10-19, together with the Lab 3–4 outline): diacritics treated as a whole problem rather than as two encodings: a new section 2.5 lists the sources of spelling variation (two encodings of ș/ț, the pre-1993 î-spelling, composed vs decomposed Unicode, ASCII substitutes including the `sh`/`tz` digraphs, diacritics created by inflection, keyboard layouts); RQ5 and H5 widened accordingly; three synthetic categories added or changed (RO-diacritic as variant families, RO-translit, RO-inflected); chat abbreviations considered and left out of scope (section 14); a spelling-variant stage in the Romanian attackers; a digraph matcher and Romanian keyboard graphs in M-ZX-RO+; new measured gaps in `language-ro` (section 2.3); reuse-frequency groups for the real-world set (borrowed from Doucek et al.). Earlier: v2 (2026-10-11), changes from v1: corrected the claim that no Romanian zxcvbn package exists; added the existing `@zxcvbn-ts/language-ro` package as a baseline; added the closest prior work (Doucek et al. 2020); corrected the Bonneau & Xu citation; switched the engine to zxcvbn-ts; added the Romance-family transfer study (RQ6) requested by the supervisor. **v2.1** (same day, after a full reading of the seven core papers): added the structural scoring floor (section 2.4) and the floor/knowledge-gap attribution; made the attacker set algorithmically diverse (A-JTR, A-PCFG in the core); defined the weights for weighted Spearman (section 9.2); corrected the description of the Ciobanu & Dinu cognate dataset and the source of the Romance intelligibility scores; corrected the description of zxcvbn's brute-force fallback. **v2.2** (2026-10-12, after an independent verification pass of the papers, the plan and the tooling): every meter now loads `language-en` so English knowledge is held constant; added the original zxcvbn 4.4.2 as a reference meter; per-attacker budgets and staged rule ordering (hashcat is word-major); `best66.rule` (hashcat 7) and the external OneRule file pinned in the repo; A-PCFG budget capped at 10^9 because of generation speed; a `grep`-based consumer instead of a Python loop; cognate / non-cognate labels taken from CogNet and the Ciobanu & Dinu pairs rather than parsed from dexonline; licence notes (dexonline GPL, CogNet CC BY-NC-SA); M-ZX-RO+-D built from a patched copy of the core; a combinator / PRINCE stage so the attackers can produce multi-word passwords; a three-way split of the Romanian breach sample; seed exclusion between the cognate training pairs and the RO-cognate seeds; M-POLICY's score mapping; the safe-underestimation metric defined relative to the budget; smaller consistency fixes. Audit reports: `papers/verification-report.md`.
**Scope (decided 2026-10-25):** the project is the Romanian study, RQ1–RQ5. The Romance-family transfer study (RQ6, section 8) is **future work**: its design is kept in this plan so it can be picked up later with the same datasets, attackers and metrics, but it is not part of the current schedule, deliverables or Lab 3–4 submission. Sections that serve only RQ6 are marked *(future work)*.

**ACM CCS 2012 classification:**
- Primary: Security and privacy → Security services → Authentication
- Secondary: Security and privacy → Human and societal aspects of security and privacy → Usability in security and privacy
- Tertiary: Computing methodologies → Artificial intelligence → Natural language processing → Lexical semantics

---

## 1. One-paragraph summary

Password strength meters such as zxcvbn estimate how many guesses an attacker would need to find a password. They do this by matching the password against ranked dictionaries of words, names and common passwords, and by recognising patterns such as dates, keyboard walks and leetspeak. The accuracy of such a meter depends entirely on what it knows. The original zxcvbn knows English; the maintained successor, zxcvbn-ts, ships community language packages, including a Romanian one, but no published work has measured whether any of them actually make the meter accurate for that language. This project measures that for Romanian. It builds a controlled Romanian password dataset, establishes an **independent ground truth** for guessability by running real cracking attacks with English and Romanian wordlists, evaluates a composition policy, English-only zxcvbn and zxcvbn with the Romanian package against that ground truth, then extends the Romanian package with the things it lacks (handling of the many ways Romanian diacritics are typed: two Unicode encodings, two spelling norms, ASCII substitutes such as `sh`/`tz`; places, cultural terms, expressions, Romanian pattern matchers, a Romanian common-password list) and measures how much each addition helps. Finally, it asks a more general question: how much of the Romanian-specific improvement can be obtained **without any Romanian data**, using only the resources of Romanian's sister languages (Italian, Spanish, Portuguese, French) plus the regular lexical correspondences between them. The deliverables are a reproducible evaluation framework, improved Romanian resources contributed upstream, a quantified answer to the cross-language transfer question, and a written report.

---

## 2. Motivation and problem statement

### 2.1 Background

Password composition rules (minimum length, mixed case, digits, symbols) are a poor proxy for real strength. NIST SP 800-63B-4 (July 2025, superseding the 2017 edition) forbids imposing them (§3.1.1.2: verifiers "SHALL NOT impose other composition rules") and requires checking new passwords against a blocklist of commonly used, expected or compromised values instead. The state of the art for client-side meters is **zxcvbn** (Wheeler, USENIX Security 2016), which estimates the number of guesses an attacker needs by decomposing the password into matched patterns and multiplying their estimated guess counts. The original JavaScript implementation is no longer maintained; the actively maintained successor is **zxcvbn-ts**, which keeps the same algorithm and adds a plugin system: `@zxcvbn-ts/language-common` (49,233 leaked passwords, keyboard graphs, diceware), per-language packages, and a `customMatchers` API.

For a segment that matches no dictionary or pattern, zxcvbn (since the 2016 version) falls back to a flat brute-force estimate of 10 guesses per character, whatever the characters are. An unknown 7-letter Romanian word therefore costs about 10^7 guesses, the same as a random 7-letter string. English-only zxcvbn-ts sees `vacanta` as the English word `vacant` plus one character (about 10^5 guesses) and `vacanță` as pure brute force (10^7). The meter therefore **overestimates** the strength of any password built from words it does not know.

### 2.2 The problem

A Romanian user who chooses `VacantaLaMare1!` gets a 15-character password with mixed case, a digit and a symbol. A composition policy calls it strong. An English-only meter, seeing no dictionary hits, calls it strong too. A Romanian attacker who combines a few thousand common Romanian words (two or three at a time, with a year or symbol appended) finds it within a modest budget; section 4.2 includes exactly such a combinator stage so that this claim is tested, not assumed.

This matters because:
- Users trust meters when choosing passwords. A meter that says "strong" for a weak password actively harms the user.
- Romanian has roughly 24 million speakers, and Romanian-language services, banks and public institutions deploy meters that are either English-only or use an unvalidated community language package.
- The problem generalises to every language with weak or no meter support. Romanian is a concrete, measurable instance, and its position inside the Romance family makes it a good test case for whether language support can be *shared* across related languages instead of being rebuilt for each one.

### 2.3 What already exists, and what does not (verified 2026-10-11)

**Prior work on meters and language.** Published meter evaluations (de Carné de Carnavalet & Mannan 2014; Golla & Dürmuth 2018; Wang et al. 2023) use English and, in some cases, Chinese password sets, and the cracking-based ground truth they rely on was established on English sets (Ur et al. 2015). Language-specific password studies exist for Chinese (Li et al. 2014; Wang et al. 2019), Czech (Doucek et al. 2020), Lithuanian (Darbutaitė et al. 2023) and Swedish (Jensen et al. 2024). A counterpoint comes from Bonneau (2012): on 70 million Yahoo! passwords, guessing the 1,000 most common passwords of one language group with another group's list cost an attacker at most a factor of 4.8 in efficiency, and the global list performed well everywhere. That result concerns the head of the distribution (online guessing); a meter must also rank the long tail correctly (10^6–10^10 guesses), where vocabulary matters more, which is what this project measures. AlSabah et al. (2018) showed that zxcvbn overrates the passwords of users from non-English backgrounds and that localised training data improves its estimates. **The closest prior work is Doucek et al. (2020)**, who adapted zxcvbn to Czech and Slovak and evaluated it on 3.1 million leaked Czech passwords; they present their method as a template for other smaller European languages. No published work studies Romanian passwords, and no published work asks whether language support for meters transfers across related languages.

**The existing Romanian package.** `@zxcvbn-ts/language-ro` exists in the zxcvbn-ts repository. Its contents as of 2026-10-11:

| List | Entries | Source | Gap |
|------|---------|--------|-----|
| `commonWords` | 48,511 | OpenSubtitles 2024 via OPUS (subtitle corpus, so conversational vocabulary) | Contains **2,425 pairs of the same word in both diacritic encodings** (cedilla `ş ţ` and comma-below `ș ț`) at different ranks, and in total 7,604 entries that fold onto an earlier entry (the 2,425 cedilla/comma pairs plus diacritic/ASCII pairs; the two categories overlap), leaving 40,907 distinct entries with the fold table of `scripts/preliminary/audit_language_ro.py` (a full NFD fold gives 40,910). Example: `vacanţă` at list position 2,896, `vacanță` at 7,691, `vacanta` at 11,901 (zxcvbn-ts uses position + 1 as the rank and guess count: 2,897 / 7,692 / 11,902). The core library does no Unicode normalisation, so the same word receives three different guess estimates depending on how it is typed. The cedilla form often ranks far better than the correct comma-below form (`şefu` 2,821 vs `șefu` 10,132; `fetiţă` 2,920 vs `fetiță` 9,028), probably because much of the subtitle corpus uses the legacy encoding. 317 entries carry invisible formatting characters from subtitle files (for example U+200E before `în`). |
| `firstnames` | 857 | not documented | Small. No diminutives (`Andu` absent; `Mihăiță` present). |
| `lastnames` | 63,236 | not documented | Large; rank quality unknown. |
| `wikipedia` | 14,493 | Romanian Wikipedia titles | — |
| `wordSequences` | 14 sequences | hand-built (numbers, days, months, seasons, colours, zodiac, planets, …) | ASCII only. |
| Localities, counties, regions | — | — | **Absent.** |
| Cultural terms (clubs, brands, slang, endearments) | — | — | **Absent.** |
| Common Romanian expressions (`teiubesc`, `lamultiani`) | — | — | **Absent.** |
| Romanian leaked-password list | — | — | **Absent.** The common package's 49,233 passwords come from Mark Burnett's 10M corpus (English-speaking sites). |
| Romanian pattern matchers (phone numbers, CNP, plates, local date formats) | — | — | **Absent.** |
| Other spellings of diacritic letters | — | — | **Mostly absent.** No `sh`/`tz` spelling (`shefu`, `fetitza`, `ionutz`, `pisicutza`, `dragutza`); pre-1993 î-spellings only for frequent words (`cînd` 3,936, `sînt` 2,411, `mîine` 18,196, but no `pîine` although `pâine` is 2,866); `ionuţ` (cedilla) missing from `firstnames` while `ionuț` is present. |
| Romanian keyboard layouts | — | — | **Absent** (the keyboard graphs are in `language-common`: QWERTY, Dvorak, keypads). |

(Spelling probes: `scripts/preliminary/check_diacritic_spellings.py`, run 2026-10-19 on `language-ro` 4.1.2.)

Nobody has measured whether this package makes zxcvbn accurate for Romanian passwords. That measurement is the first contribution of this project; the gaps in the table are the second.

**Sister-language packages.** zxcvbn-ts also ships `it` (29,303 common words, 9,215 first names), `es-es` (39,799 / 1,279), `fr` (28,095 / 10,521) and `pt-br` (40,242 / 3,164), each with Wikipedia lists and word sequences. These are the raw material for the transfer study in section 8.

**Preliminary overlap measurement** (script to be committed under `scripts/preliminary/`): after folding diacritics to ASCII, the union of the IT, ES, FR and PT common-word lists contains **2,625 of the top 10,000 Romanian common-word entries (26% of entries; the 10,000 entries fold to 8,782 distinct strings, so 30% of distinct words)** as exact strings; the English list contains 2,045 (20%); 5,982 are in neither. For first names, 278 of the 857 Romanian name entries (767 distinct after folding) appear in the Italian list, 154 in Portuguese, 98 in Spanish, 51 in French. Exact counts shift by one or two with the choice of fold table; the script reproduces them. Exact-string overlap is a floor: cognates with regular spelling changes (*lapte / latte / leche / leite / lait*) are not counted and are the target of cognate projection (section 8.3).

### 2.4 A structural floor in zxcvbn's scoring (measured 2026-10-11)

Missing vocabulary is not the only limit. zxcvbn estimates a password's guesses as |S|! × ∏ guesses(match) + D^(|S|−1), where |S| is the number of segments in the chosen decomposition and D = 10,000 (Wheeler 2016, section 4.1, Eq. 1, proceedings p. 162 / PDF p. 7, which says 1,000 to 10,000 "work well in practice"; `MIN_GUESSES_BEFORE_GROWING_SEQUENCE = 10000` in `@zxcvbn-ts/core`, `src/data/const.ts`). Score thresholds are 10^3, 10^6, 10^8 and 10^10 (plus 5), configurable in zxcvbn-ts through `timeEstimationValues.scoring`. The additive term is a floor: any password decomposed into 3 segments gets at least 10^8 guesses (score ≥ 3), and any password decomposed into 4 or more segments gets at least 10^12 (score 4), however common each segment is. Measured with zxcvbn-ts 4.2.0, `language-common`, `language-en` and `language-ro` 4.1.2 (the configurations M-ZX-EN and M-ZX-RO-PKG of section 6.2):

| Password | M-ZX-EN (English only) | M-ZX-RO-PKG (English + Romanian) | Segments under M-ZX-RO-PKG | Why the score |
|----------|------------------------|----------------------------------|----------------------------|---------------|
| `vacanta` | 1.0×10^5, score 1 | 1.2×10^4, score 1 | vacanta | dictionary rank |
| `Andrei1999!` | 1.0×10^8, score 3 | 1.0×10^8, score 3 | Andrei · 1999! | 2 segments: product term, not the floor |
| `TeIubescMult` | 1.4×10^10, score 4 | 1.2×10^8, score 3 | Te · Iubesc · Mult | 3 segments: the 10^8 floor dominates (all three words are in the top 300) |
| `VacantaLaMare1!` | 1.1×10^13, score 4 | 1.1×10^12, score 4 | Vacanta · La · Mare · 1! | 4 segments: the 10^12 floor dominates |

(Scripts and raw output: `scripts/preliminary/`.)

Consequences for the design:

1. For multi-segment categories (RO-name-sym, RO-phrase, RO-passphrase, RO-place with suffixes), adding Romanian vocabulary cannot bring the score below the floor. Part of the dangerous overestimation (RQ2) will survive any dictionary extension, and this is expected, not a failure of the extension.
2. The analysis separates two causes. For every dangerously overestimated password, record whether the meter's estimate is dominated by the D^(|S|−1) term (**floor**) or by an unmatched or poorly ranked segment (**knowledge gap**), and report the split per category and meter (RQ4).
3. Multi-word expressions that users type as one unit (`teiubesc`, `lamultiani`) enter the dictionaries as single tokens. Without changing the algorithm, this is the only way to avoid the floor.
4. An exploratory variant, M-ZX-RO+-D (section 6.2), recomputes M-ZX-RO+ with smaller values of D (1,000, 100, 10) to measure how much error the floor causes. D is a hard-coded constant, not an option, so this variant is built from a patched copy of `@zxcvbn-ts/core` in which that single constant is changed (`bridge/patches/`). It changes the algorithm, so it is reported separately from the main comparison. The Czech adaptation of zxcvbn changed this constant to 1,000 (Doucek et al. 2020, per their public repository), which is a further reason to quantify its effect.

### 2.5 Romanian diacritics: one word, many strings

Romanian has five diacritic letters, three vowels (`ă â î`) and two consonants (`ș ț`), and about a third of the `language-ro` common words (16,554 of 48,511) contain at least one. Users rarely type them in passwords, but the ways of leaving them out, or putting them in, are not uniform. For a dictionary meter every variant is a different string, and an unknown variant is scored as brute force. The sources of variation are:

1. **Two Unicode encodings of ș and ț.** Comma-below (`ș` U+0219, `ț` U+021B) is correct; cedilla (`ş` U+015F, `ţ` U+0163) is the legacy form, still produced by the Windows "Romanian (Legacy)" layout. Unicode normalisation does not merge them: they are different characters, not canonical or compatibility equivalents, so the NFC normalisation that NIST SP 800-63B-4 (§3.1.1.2) recommends applying to passwords before hashing leaves the problem in place (and so would NFKC or NFKD).
2. **Two spelling norms for î/â.** Before the 1993 decision of the Romanian Academy, `î` was written inside words (`pîine`, `cînd`, `sînt`); since then it is `â` (`pâine`, `când`, `sunt`). After removing diacritics the two norms give different ASCII strings (`piine` / `paine`, `cind` / `cand`), so even folding does not merge them.
3. **Composed and decomposed forms.** `ă` can be one code point (U+0103) or `a` + combining breve (U+0306). `language-ro` is entirely in composed form (NFC), but a password that arrives decomposed matches nothing, and the brute-force fallback, which counts characters, should count each decomposed letter twice (to be checked in week 1).
4. **ASCII substitutes.** Dropping the sign (`fetita`, `ionut`) is the usual choice; `ș` and `ț` are also written as the digraphs `sh` and `tz` (`shefu`, `fetitza`, `Ionutz`). Digraphs change the length of the word, so a one-to-one fold cannot undo them (section 7.4).
5. **Diacritics created by inflection.** Plurals, definite and vocative forms and diminutives change `t → ț`, `s → ș`, `a → ă` (`frate → frați`, `urs → urși`, `carte → cărți`, `Ion → Ionuț`), so the same problem appears for words whose dictionary form has no diacritics.
6. **Keyboard layouts.** The Romanian Standard layout (SR 13392:2004) is QWERTY with the diacritic letters on the keys to the right of `P` and `L`; the Programmers layout is the US layout with AltGr; the Legacy layout is QWERTZ and types cedilla forms. The layout decides both which encoding appears and which keyboard walks are natural (the Czech adaptation added QWERTZ graphs for the same reason).

A word with two diacritic letters can therefore appear as five or more strings (`fetiță`, `fetiţă`, `fetita`, `fetitza`, and a capitalised or inflected form of each). RQ5 measures what this costs a meter, and section 7.4 describes how the extension handles it.

---

## 3. Research questions and hypotheses

| ID | Research question | Hypothesis | How it is answered |
|----|-------------------|------------|--------------------|
| RQ1 | How accurately does English-only zxcvbn rank the guessability of Romanian-based passwords, compared to English-based passwords of the same structure? | H1: Correlation between the meter's estimate and attacker guess numbers is significantly lower for Romanian passwords than for English ones. | Spearman and weighted Spearman between meter estimate and ground-truth guess number, per language group, with bootstrap confidence intervals. |
| RQ2 | Do English-only zxcvbn and zxcvbn with the existing Romanian package overestimate Romanian passwords in the dangerous direction (weak rated as strong)? | H2a: The dangerous-overestimation rate is higher for Romanian than for English passwords under the English-only meter. H2b: The existing Romanian package reduces but does not remove the gap, because of the missing lists in section 2.3 and the structural floor in section 2.4. | Dangerous-overestimation rate per group and per meter with chi-square tests. |
| RQ3 | Does the extended Romanian package improve accuracy on Romanian passwords over the existing package, without harming accuracy on English or random passwords? | H3a: Correlation improves on Romanian groups. H3b: No significant degradation on English and random control groups. | Same metrics, paired comparison of the three zxcvbn variants on the same passwords. |
| RQ4 | Which Romanian password structures are most misjudged, and which added resource (places, cultural terms, expressions, inflected forms, Romanian leaked passwords, matchers, keyboard graphs, spelling normalisation) accounts for the most improvement? | Exploratory, no fixed hypothesis. | Per-category analysis, ablation study (add resources one at a time), and attribution of each misjudgement to the structural floor or a knowledge gap (section 2.4). |
| RQ5 | How do the different ways of writing Romanian diacritics (two Unicode encodings, the pre-1993 î-spelling, composed vs decomposed forms, the sign dropped, `sh`/`tz` digraphs) affect meter behaviour? | H5a: Because the core does no normalisation and the Romanian word list holds some variants at very different ranks and lacks others, the variants of one word (`fetiță` / `fetiţă` / `fetita` / `fetitza`) receive inconsistent scores, and the `sh`/`tz` and old-norm variants are overestimated most. H5b: Folding plus the digraph matcher and variant entries (section 7.4) removes most of the inconsistency without raising scores of English or random controls. | Variant families (RO-diacritic) for consistency, RO-translit and RO-inflected for accuracy against the ground truth, before and after normalisation (section 2.5). |
| **RQ6** *(future work)* | **How much of the Romanian-specific improvement can be obtained with no Romanian data, using only the resources of Italian, Spanish, Portuguese and French plus the regular lexical correspondences between them and Romanian?** | H6a: A pooled Romance meter with diacritic folding recovers a substantial fraction of the Romanian-specific gain on word- and name-based categories, and almost none on cultural categories. H6b: Adding cognate projection (a few hundred correspondence rules, no Romanian word list) recovers more than pooling alone. H6c: The pooled meter does not degrade accuracy on English and random controls. | Leave-one-language-out design (section 8), "gain recovered" metric (section 9), per-category breakdown. |

A traditional composition policy (length ≥ 8, three of four character classes) is included as a **baseline**, not a research question. Its weakness is established in the literature; it serves to show the magnitude of the problem in a way that is immediately intuitive to a reader.

RQ1–RQ5 form the project. RQ6 is the generalisation suggested by the supervisor and is kept as **future work**: it would reuse the same datasets, attackers and metrics, so its marginal cost is building one additional meter family (section 8).

---

## 4. Methodological core: independent ground truth

### 4.1 Why it is necessary

A naive design would generate passwords from Romanian templates, build a meter that knows those templates, and observe that the new meter scores them lower. That result is guaranteed by construction and proves nothing. The project must answer "weaker according to whom?" with something that is **not** built by the same person who built the meter.

### 4.2 The attacker models

Ground truth is the **guess number**: the position at which a password appears in the candidate stream of a realistic attack. Ur et al. (2015) showed that any single cracking configuration gives biased guess numbers and that taking the minimum over several approaches approximates a professional attacker; the project therefore runs several attackers that use different algorithms, and reports the minimum as well as each individually.

| Attacker | Wordlist | Rules | Models |
|----------|----------|-------|--------|
| A-EN | RockYou (public, 14M entries) + English dictionary | hashcat, staged: `best66.rule` (shipped with hashcat 7.x; it replaced `best64.rule`) over the whole wordlist, then `OneRuleToRuleThemAll.rule` (an external community file of about 52,000 rules, not part of hashcat; pinned in the repository) | An attacker with no knowledge of the target's language. This is the attacker an English-only meter implicitly models. |
| A-RO | Romanian dictionary (dexonline lexemes) + Romanian first names + surnames + localities + expressions + the attacker share of the Romanian breach sample (section 5.3) | Same staged rules, then a **combinator stage**: hashcat `-a 1` over the top 5,000 Romanian words (two-word candidates, 2.5×10^7) and John the Ripper PRINCE mode (`--prince`) over the same list for 3–4 word chains, each followed by the light rules (capitalisation, separator, appended year / digits / symbol), then a **spelling-variant stage**: the Romanian wordlist expanded with the variants of section 2.5 (sign dropped, cedilla, `sh`/`tz`, pre-1993 î) before the rules are applied. This is done by expanding the wordlist, not with hashcat rules, because rules work on bytes and `ș` is two bytes in UTF-8. | An attacker who knows the target is Romanian, including that Romanians build passwords from several words. Without the combinator stage no attacker could produce `VacantaLaMare1!`, `TeIubescMult` or any RO-phrase / RO-passphrase password, and those categories would be censored by construction. |
| A-ALL | Union of both wordlists | Same stages as A-RO, including the combinator stage over the union's top 5,000 words | A well-resourced attacker. |
| A-JTR | Same as A-ALL | John the Ripper `--rules=Jumbo`, then PRINCE mode, then incremental mode | A different tool with a different candidate order. Adds the algorithmic diversity that makes the minimum meaningful. |
| A-PCFG | PCFG model (Weir et al. 2009, `pcfg_cracker`) trained on RockYou plus, if permitted, the attacker share of the Romanian-filtered breach sample (section 5.3) | n/a (probability order) | A probabilistic model that learns password structure rather than applying fixed rules. Budget 10^9, not 10^10: `pcfg_guesser` generates about 50,000–100,000 guesses per second, so 10^9 takes 3–6 hours and 10^10 would take days. |
| A-MIN | — | — | Per password, the minimum guess number over all attackers above. Following Ur et al. (2015), and the primary ground truth. |

The minimum is meaningful only if the attackers differ. Ur et al.'s Min_auto combines different algorithms (PCFG, Markov, John the Ripper, hashcat). A minimum over hashcat runs that differ only in wordlist would not inherit their result, so A-JTR and A-PCFG are part of the core design, not optional.

Guess budgets and ordering. hashcat's straight mode is **word-major**: it emits each base word under all rules before moving to the next word, so the first 10^10 candidates of RockYou × OneRule (about 7×10^11 in total) would cover only the first ~190,000 words, each fully mangled, and never reach the rest of the list. The staged order above fixes this: `best66.rule` × 14.3M words (about 9×10^8 candidates) covers every word shallowly first, then OneRule adds depth until the budget. John the Ripper is **rule-major** (each rule across the whole wordlist), so A-JTR's order is genuinely different, which is what makes A-MIN meaningful. Budgets: 10^10 for the hashcat and John attackers, 10^9 for A-PCFG. Passwords not found are right-censored at their attacker's budget, and censoring is reported per attacker.

### 4.3 Computing guess numbers without storing the stream

Candidate streams of 10^10 entries cannot be stored. Instead:

1. Load the evaluation dataset into a hash set (tens of thousands of entries, trivial memory).
2. Generate the candidate stream with `hashcat --stdout <wordlist> -r <rules>` (or John the Ripper `--stdout`, or `pcfg_guesser`).
3. Cut the stream at the budget and find the first line number of every target: `... | head -n <budget> | grep -n -x -F -f targets.txt`. `grep -F` matches a set of fixed strings at tens of millions of lines per second; a pure-Python loop manages only 1–3 million lines per second and would make each 10^10 run take hours. The line number of a target's first match is its guess number.
4. Every target that never appears gets guess number = budget, flagged as censored.

This is linear in the stream and constant in memory. At grep speed a 10^10 stream takes well under an hour per attacker on the development machine (Apple M5, 10 cores, 24 GB). Two things to verify in week 1: hashcat `--stdout` initialises a compute backend even though it does no hashing (on Apple Silicon the Metal backend should satisfy it; if not, John's `--stdout`, which needs no backend, generates the same wordlist × rules stream), and the exact rule-file versions, which are vendored into the repository for reproducibility. Neither hashcat nor John is installed yet; both are available via Homebrew (hashcat 7.1.2, john-jumbo 1.9.0).

### 4.4 Guards against leakage and circularity

Two kinds of sharing would make the results circular, and are forbidden:

1. **Generator ↔ meter.** If the extension's dictionaries were built from the same lists that generate the synthetic passwords, the extension would "know" the test set. The generator therefore draws from **independently sourced seed lists** (dexonline lexemes ranked by CoRoLa frequencies, a Wikipedia-derived name list, GeoNames), never from the zxcvbn-ts language packages, `wordfreq`, `language-ro`, or any list that goes into a meter. Overlap between the seeds and each meter's dictionary is measured and reported.
2. **Meter ↔ attacker.** If the meter's dictionary and the attacker's wordlist were the same file, the attacker would crack exactly what the meter knows, by construction. Attacker wordlists are therefore separate builds from separate sources (dexonline and the attacker share of the breach sample for A-RO; `language-ro`, INS/Wikipedia names and the meter share of the breach sample for the meter), the files are distinct and versioned, and their overlap of unique strings is reported.

Sharing between the **generator and the attackers** is allowed and inevitable: a wordlist attack can only find a word that is in its wordlist, so dexonline serves both as the generator's lexicon and as A-RO's dictionary. This is the realism the ground truth needs, not a circularity, and the overlap is reported.

For the transfer study (section 8): the sister-language packages are used only by the Romance meters. The cognate pairs are used by the level-1 meter (to learn rules) and by the generator (to label RO-cognate / RO-noncognate seeds, section 5.2); to keep these apart, **rules are learned only from pairs whose Romanian side is not a synthetic seed word** (seed exclusion), and the number of excluded pairs is reported. The level-0 meter reads no Romanian-specific file, which a test checks by listing the meter's build inputs; note that the shared `language-common` password list, present in every meter including M-ZX-EN, contains a few Romanian items (`teiubesc`, `andrei`, `steaua`, `romania`), and the fold table knows Romanian letters. Because these are in M-ZX-EN too, they cancel out of gain recovered.
- Note that `language-ro` common words come from OpenSubtitles and `wordfreq` also includes OpenSubtitles among its sources; this is a reason not to use `wordfreq` as the generator's seed list.
- The real-world validation set (section 5.3) is not generated by anyone, which removes the circularity entirely for that part of the evaluation.
- The spelling-variant rules (section 2.5) are shared by the generator, the attackers and the meter. They are facts about Romanian orthography, not data, so sharing them is not circular in the sense above; but to show how much the attackers depend on them, A-RO is also reported without its spelling-variant stage.

---

## 5. Datasets

### 5.1 Lexical resources (inputs to the meters and attackers)

| Resource | Source | Format | In `language-ro` today? | Notes |
|----------|--------|--------|------------------------|-------|
| Romanian common words | `language-ro` `commonWords` (48,511, OpenSubtitles) re-ranked after folding; `wordfreq` (`ro`) and CoRoLa frequency lists as a cross-check | ranked list | yes, but with encoding duplicates | Deduplicate after folding; rank = best rank among variants. |
| Romanian dictionary (full lexicon) | dexonline database dump (about 380 MB; data under GPL, code under AGPL); CoRoLa frequency list for ranking | word list (lexeme table) | no | Generator seed list and A-RO wordlist (allowed to share, section 4.4); never a meter dictionary. Etymology is not a structured field in the dump (it sits inside definition text from many source dictionaries), so it is not used for labelling; see section 5.2. |
| Romanian first names | `language-ro` `firstnames` (857) extended with INS / public registry statistics where available, Wikipedia category lists, ro.wiktionary; diminutives added by hand | ranked list | partially | Include diminutives (`Andu`, `Mihăiță`, `Alex`, `Ionuț`). |
| Romanian surnames | `language-ro` `lastnames` (63,236); public frequency lists as a cross-check | ranked list | yes | Verify the ranking is by frequency. |
| Localities and counties | GeoNames (RO), county names and two-letter codes | list | **no** | City, county and region names; folded and unfolded. |
| Calendar terms | `language-ro` `wordSequences` plus holidays | list | partially | Add `Crăciun`, `Paște`, `Revelion`, `Mărțișor`. |
| Cultural terms | hand-built, documented | list | **no** | Football clubs, brands, TV shows, political terms, slang, endearments (`iubire`, `puiule`). |
| Common Romanian expressions | hand-built from phrase lists | list | **no** | `teiubesc`, `tepup`, `noroc`, `lamultiani`, `hairomania`, etc. |
| Spelling-variant table | hand-built from orthography rules (DOOM3 2021; 1993 Academy decision), documented | table | **no** | Cedilla ↔ comma-below, sign dropped, `ș → sh`, `ț → tz`, interior `â ↔ î`. Used by the meter (7.4), the attackers' variant stage (4.2) and the generator. |
| Inflected and diminutive forms | meter: the forms already in `commonWords` (subtitles contain many: `puiule`, `iubito`, `frați`) plus hand-built diminutives and vocatives of the top first names; generator and A-RO: dexonline's inflected-form table | ranked list | partially | Separate sources for meter and generator (section 4.4). |
| Romanian keyboard graphs | built from the SR 13392:2004 Standard layout and the Windows Legacy (QWERTZ) layout | adjacency graphs | **no** | Same format as zxcvbn's QWERTY graph. |
| Romanian leaked passwords | Filtered from public breach corpora (section 5.3) | ranked list | **no** | The single most valuable resource; split three ways by occurrence into a meter dictionary, an attacker / PCFG-training share, and a validation share (section 5.3). |
| Sister-language packages | `@zxcvbn-ts/language-it`, `-es-es`, `-fr`, `-pt-br` (common words, names, Wikipedia) | ranked lists | n/a | Inputs to the Romance meters only (section 8). |
| Romance cognate data | Ciobanu & Dinu (LREC 2014) dataset: Romanian-centred word–etymon and word–cognate pairs for FR, IT, ES, PT (and TR), extracted from dexonline and foreign etymological dictionaries; 4,124 Romanian words have a partner in all four Romance languages. Available from the authors on request. CogNet v2.0 (Batsuren et al. 2019; TSV download; covers `ron`, `ita`, `spa`, `por`, `fra`; licence CC BY-NC-SA, so anything derived from it stays in the research artefacts and is not contributed upstream) for broader, downloadable coverage | word pairs per language | n/a | Section 8.3. |
| Multilingual frequency ranks | `wordfreq` 3.x (`ro`, `it`, `es`, `pt`, `fr`; the data is frozen at about 2021 and Romanian has only the "small" list) | ranked lists | n/a | Used to re-rank pooled Romance dictionaries on a common scale. |

Every Romanian resource is stored in NFC, with invisible formatting characters removed, in three forms: original with comma-below diacritics, legacy-cedilla form, and ASCII-folded (section 7.4); the `sh`/`tz` and pre-1993 variants are generated from these by the spelling-variant table. Every hand-built list is documented with its construction method so it can be criticised and reproduced.

### 5.2 Synthetic evaluation dataset (controlled)

Generated by templates with a fixed random seed. Each password carries its generating category, so misclassification can be analysed by structure. Target size: about 29,500 passwords (26,000 in the fixed-size categories plus 1,000 RO-diacritic families of 3–5 variants each); the RO-cognate and RO-noncognate groups (2,000 more) are added only for the future RQ6.

| Category | Template | Example | Count |
|----------|----------|---------|-------|
| RO-word | Romanian word, optional capitalisation | `vacanta`, `Dragoste` | 2000 |
| RO-word-num | Romanian word + 1–4 digits | `vacanta123` | 2000 |
| RO-word-year | Romanian word + year 1950–2026 | `Dragoste2001` | 2000 |
| RO-name-num | First name + digits / year | `Andrei1999` | 2000 |
| RO-name-sym | Name + year + symbol | `Andrei2026!` | 1500 |
| RO-place | Locality or county + suffix | `Bucuresti123!`, `Cluj2020` | 1500 |
| RO-phrase | Multi-word Romanian phrase | `TeIubescMult`, `VacantaLaMare1!` | 2000 |
| RO-leet | Any of the above with substitutions | `Dr@g0ste`, `V@canta1` | 1500 |
| RO-diacritic | Variant family: the same word in all its spellings (comma-below, cedilla, sign dropped, and where they apply `sh`/`tz` and the pre-1993 î-form) | `fetiță`, `fetiţă`, `fetita`, `fetitza`; `pâine`, `pîine`, `paine`, `piine` | 1000 families |
| RO-translit | Word or name containing ș/ț written with `sh`/`tz`, + optional suffix | `Ionutz99`, `fetitza2005`, `shefu1` | 1000 |
| RO-inflected | Inflected, vocative or diminutive form (including `t → ț`, `s → ș` changes), any spelling, + optional suffix | `puiule1`, `fratii2010`, `pisicuta!` | 1000 |
| RO-cultural | Clubs, brands, slang + suffix | `Steaua1986`, `Dinamo!` | 1000 |
| RO-passphrase | 3–4 Romanian words, space or no space | `casa mare verde` | 1000 |
| RO-cognate | Romanian words that have a Latin-derived cognate in ≥ 2 sister languages, + optional suffix | `lapte2020`, `noapte!` | 1000 |
| RO-noncognate | Romanian words of Slavic or other non-Latin origin, + optional suffix | `iubire123`, `prieten!` | 1000 |
| EN-word-num | English word + digits (control) | `summer123` | 2000 |
| EN-name-year | English name + year (control) | `Michael1999` | 2000 |
| EN-phrase | English phrase (control) | `ILoveYou2!` | 1500 |
| RANDOM | Uniform random over printable ASCII, lengths 8–16 (control) | `xQ7#pL9@vR2!` | 2000 |

The EN groups are the critical control: they share **structure** with the RO groups and differ only in **language**. Any accuracy difference between matched RO and EN groups is attributable to language coverage, not to password structure.

RO-diacritic is used for consistency (one score spread per family, RQ5); RO-translit and RO-inflected measure accuracy against the ground truth like every other category. RO-translit and RO-inflected are new in v2.3.

*(Future work.)* The RO-cognate and RO-noncognate groups are generated only when RQ6 is taken up; they are not part of the current dataset. They are new in v2 and exist for RQ6: they separate the part of Romanian vocabulary that sister languages can in principle cover from the part they cannot. Labels: a seed word is RO-cognate if CogNet or the Ciobanu & Dinu pairs give it a cognate in at least two of IT/ES/PT/FR, and RO-noncognate if it has no cognate or etymon in any of the four in either resource; words in neither class are not used for these two groups. A 200-word sample of each label is hand-checked against dexonline's etymology notes and the agreement rate is reported. Because the Ciobanu & Dinu pairs and CogNet are also level-1 training data (section 8.3), pairs whose Romanian side is a seed word are excluded from rule learning (seed exclusion, section 4.4), and the guard test confirms that the seed lists themselves are never read by any meter.

### 5.3 Real-world validation set

A sample of genuine Romanian passwords, drawn from publicly available breach corpora that are routinely used in academic password research (RockYou and similar). Romanian entries are identified by matching against the Romanian lexical resources with a precision check (e.g. contains a Romanian word of ≥ 5 letters that is not also an English word, or a Romanian name, or Romanian diacritics). Because many Romanian-looking strings are also English or Romance words, the filter's precision is estimated on a hand-labelled sample of 300 entries and reported.

- Target: 5,000–20,000 passwords.
- Purpose: confirm that findings on the synthetic set hold on passwords nobody in this project generated.
- The Romanian-filtered breach passwords are split three ways **by occurrence** (each occurrence is assigned at random to one share, so a frequent password appears in all three with proportional counts, as in Golla & Dürmuth's reference split): 40% meter dictionary ("Romanian common passwords", section 7.2), 30% attacker share (A-RO wordlist and A-PCFG training), 30% validation. The validation share is never used as a dictionary or for training; the overlap of unique strings between shares is reported.
- Results on the validation share are also reported by **reuse-frequency group** (passwords used by ≥ 1,000, 100–999, 10–99, 2–9 accounts, and unique ones), following Doucek et al. (2020): a meter error on a password reused thousands of times matters more than one on a unique password.
- A descriptive **profile** of the sample is reported: length and character classes; the share of passwords that contain a Romanian word with diacritics, and how that word is spelled (with diacritics, cedilla vs comma-below, sign dropped, `sh`/`tz`, pre-1993 î); and the most frequent base words. This tells how much each source of variation in section 2.5 matters in practice.

**Ethics.** Breach corpora contain no usernames in the form used here, are already public, and are standard in the field (Ur et al. 2015; Golla & Dürmuth 2018; Doucek et al. 2020; Wang et al. 2023). The supervisor's and faculty's position on their use must be confirmed in writing before use. The same decision covers RockYou, which the attackers use as a wordlist (A-EN, A-ALL, A-JTR) and as PCFG training data. If use of the Romanian sample is not permitted, everything derived from it is dropped: the validation set, the "Romanian common passwords" meter dictionary (7.2), the empirical leet table (7.3, replaced by the default table), the attacker share in A-RO, and the Romanian share of A-PCFG's training data. If no breach data at all is permitted, RockYou is also dropped: the attackers use dictionary-only wordlists, A-PCFG is dropped, and all of this is stated as limitations. The synthetic set with the independent attacker ground truth still supports the main conclusions.

---

## 6. Meters under evaluation

### 6.1 Engine choice

All zxcvbn variants run on **zxcvbn-ts** (`@zxcvbn-ts/core`), not on the Python port used in v1 of this plan. Reasons: (1) the baseline that matters is what a Romanian deployment would actually use today, which is zxcvbn-ts with `language-ro`; (2) the sister-language packages for RQ6 are zxcvbn-ts packages; (3) zxcvbn-ts has an official `customMatchers` API for the Romanian matchers and the folding layer, so no fork is needed for any of the main meters (only the exploratory M-ZX-RO+-D uses a one-constant patch of the pinned core); (4) the improved resources can be contributed upstream as-is. The Python framework calls the engine through a 50-line Node bridge (`bridge/zx.js`) that reads passwords from stdin and writes one JSON result per line. All variants share the same core version, pinned.

### 6.2 Meter list

| Meter | Composition | Role |
|-------|-------------|------|
| M-POLICY | Length ≥ 8 and ≥ 3 of {lower, upper, digit, symbol}; stricter variant: length ≥ 12, all four classes. Output: pass → score 4, fail → score 0; no guess estimate | Intuitive baseline. Enters the rate metrics and the confusion matrix only; excluded from correlations, which it cannot produce |
| M-ZX-ORIG | original `zxcvbn` 4.4.2 (JavaScript, unmaintained) | Reference point only: same algorithm as zxcvbn-ts but different word lists (e.g. `teiubesc` is rank 11,577 in zxcvbn 4.4.2 and about 18,900 in zxcvbn-ts). Shows how much of any difference is due to the port. |
| M-ZX-EN | core + `language-common` + `language-en` | English-only zxcvbn-ts: what an unlocalised deployment uses. |
| M-ZX-RO-PKG | core + `language-common` + `language-en` + `language-ro` as published | The existing Romanian support, loaded the way a Romanian deployment would load it (English and Romanian together; Romanian users also use English words). **The baseline to beat.** |
| M-ZX-RO+ | M-ZX-RO-PKG + the extension of section 7 (spelling normalisation and digraph matcher, deduplicated re-ranked words, extended names, places, calendar, cultural, expressions, inflected forms, Romanian leaked passwords, Romanian matchers, Romanian keyboard graphs, Romanian leet table) | Full Romanian-aware meter |
| M-ZX-RO+ ablations | M-ZX-RO-PKG plus one addition at a time | RQ4 |
| M-ZX-ROM-0 | core + `language-common` + `language-en` + `it` + `es-es` + `fr` + `pt-br` + folding, **no Romanian file** | Transfer level 0: pooling only (section 8) |
| M-ZX-ROM-1 | M-ZX-ROM-0 + cognate projection rules | Transfer level 1: pooling + correspondence rules |
| M-ZX-ROM+RO | M-ZX-ROM-1 + everything in M-ZX-RO+ | Upper bound: does pooling help on top of Romanian data? |
| M-ZX-RO+-D (exploratory) | M-ZX-RO+ on a patched copy of the core with the multi-segment constant D lowered to 1,000, 100 and 10 | Measures the effect of the structural floor (section 2.4). Changes the algorithm, so it is reported separately. |

English knowledge (`language-common` + `language-en`) is held constant across every zxcvbn-ts meter, so the only thing that varies between them is Romanian or Romance knowledge, and the EN control groups stay meaningful for H3b and H6c.

All meters are called through a single interface in the framework so adding a meter later (e.g. a neural estimator) is a one-file change. Output per password: log10(guesses), score 0–4, matched pattern sequence.

---

## 7. The Romanian-aware extension (M-ZX-RO+)

### 7.1 Design principle

Keep zxcvbn's scoring algorithm untouched in every main meter. Change only what it knows. (The exploratory M-ZX-RO+-D is the single, declared exception.) This makes the comparison clean: any difference between M-ZX-RO-PKG and M-ZX-RO+ is due to added knowledge, not to a different algorithm. All additions go through the public extension points of zxcvbn-ts (`dictionary` option, `customMatchers`, `l33tTable`).

### 7.2 Ranked dictionaries

- **Deduplicate and re-rank `commonWords`.** Fold every entry; where several entries fold to the same string, keep one entry at the best (lowest) rank. This alone removes 2,425 encoding duplicates and ~6,500 ASCII/diacritic duplicates (48,511 → 40,907 entries) and is a self-contained upstream fix. Entries with invisible formatting characters (317) are cleaned before folding.
- **Add** the missing lists from section 5.1: localities, calendar/holiday terms, cultural terms, expressions, extended first names with diminutives and vocatives, Romanian leaked passwords. Each is a separate ranked dictionary with its own name so the ablation can switch it on and off.

### 7.3 Romanian leetspeak table

Extend the substitution table with usages observed in the Romanian leaked-password sample. Expected additions beyond the default English table are limited (`a→4/@`, `e→3`, `i→1/!`, `o→0`, `s→5/$`, `t→7`) but the empirical check is part of RQ4.

### 7.4 Diacritic and encoding normalisation

Romanian uses five diacritic letters: `ă â î ș ț`. Two of them have two Unicode encodings each: comma-below (`ș` U+0219, `ț` U+021B, correct) and cedilla (`ş` U+015F, `ţ` U+0163, legacy but widespread on Windows). Users type all of `vacanță`, `vacanţă` and `vacanta`.

The other sources of variation are listed in section 2.5. The normalisation is applied in this order:

1. **NFC.** The password is converted to composed form, so decomposed letters match the dictionaries.
2. **Folding** (below), which merges the two encodings and the sign-dropped spelling.
3. **Pre-1993 î.** Folded dictionaries also contain the old-norm spelling of every entry with interior `â` (`piine` next to `paine`), at the same rank. The rule is not applied after prefixes (`neînțeles`), where `î` is correct in both norms.
4. **Digraphs.** A `digraphDictionary` custom matcher rewrites `sh → s` and `tz → t` with an explicit index map back to the original password and looks the result up in the folded Romanian dictionaries. A match is accepted only if the rewritten word is a Romanian entry, so English words containing `sh` (`ashley`) are not affected. Like zxcvbn's l33t matcher, it multiplies the word's guesses by a small factor for the substitution.

Implementation of folding: a `foldedDictionary` custom matcher that (1) maps the input to canonical ASCII through a 1:1 character table (so match indices need no remapping), (2) runs the standard dictionary matcher over the folded string against folded dictionaries, and (3) reports the fold as a match property. This lets the meter recognise the three variants as the same dictionary word, while still giving a small credit for extra character-set entropy if the user actually typed diacritics (mirroring zxcvbn's existing treatment of uppercase). The same folding table is extended to the sister languages' diacritics (`à á â ã ç é è ê í ì ï ñ ó ò ô õ ú ù ü`) so one layer serves section 8. Ligatures that would break the 1:1 property (`œ`, `æ`, `ß`) are left unchanged; they are rare in passwords and this is noted as a limitation.

### 7.5 Romanian-specific pattern matchers

Added through `customMatchers`, each with a documented guess estimate and unit tests:

- Romanian mobile phone numbers: `07` followed by 8 digits.
- Romanian date formats: `dd.mm.yyyy`, `ddmmyyyy`, `dd-mm-yy` (check first whether the core date matcher already covers these; extend only if not).
- Personal numeric code (CNP) structure: 13 digits beginning with 1–8, valid date in positions 2–7.
- County codes and licence-plate shapes: `B123ABC`, `CJ12ABC`.
- Keyboard walks on the Romanian Standard and Legacy (QWERTZ) layouts, added as extra adjacency graphs for the existing spatial matcher (as the Czech adaptation did for its QWERTZ layout).
- Multi-word Romanian phrases with camel-case or no separator (`TeIubesc`), handled by the dictionary matcher once expressions are present, verified in tests.

### 7.6 Deliverable form

- A package `zxcvbn-ro-extended` (TypeScript, same layout as the zxcvbn-ts language packages) containing the deduplicated and extended dictionaries plus the matchers.
- Upstream contributions to zxcvbn-ts, in increasing size: (a) the deduplication fix for `language-ro`; (b) the added lists; (c) the folding matcher, which benefits every language package with diacritics.

---

## 8. The Romance-family transfer study (RQ6) — future work

*Not in the current scope (see Scope at the top). The design below is kept so the study can be run later on the same infrastructure. The meters M-ZX-ROM-0, M-ZX-ROM-1 and M-ZX-ROM+RO in section 6.2, the gain-recovered metric in section 9 and figures 8–9 in section 10 belong to it.*

### 8.1 Question and reasoning

Building a language package is manual work that every language community must repeat. Romanian, Italian, Spanish, Portuguese and French descend from Latin and share a large part of their core vocabulary, often with regular spelling correspondences (Latin *-ct-* → Romanian *-pt-*, Italian *-tt-*, Spanish *-ch-*: *lapte / latte / leche*). Ciobanu & Dinu ("On the Romance Languages Mutual Intelligibility", LREC 2014) quantify this: Romanian is the least intelligible Romance language for speakers of the others. On their Europarl matrix (Table 4; the value in row X, column Y is how comprehensible text in language X is to a speaker of Y), Portuguese text scores 86.4 for a Spanish speaker while Romanian text scores 60.0 for a Spanish speaker; the Romanian row, i.e. how well speakers of the other languages understand Romanian, is IT 66.0, FR 65.1, PT 64.5, ES 60.0. The row direction is the right analogue for this project: a meter equipped with an Italian dictionary "reads" Romanian passwords the way an Italian speaker reads Romanian text. (The column direction, Romanian speakers reading the others, gives ES 70.2 > IT 69.2 > PT 65.6 > FR 62.3; the authors call these differences not very significant.) This makes Romanian a conservative test case: if transfer works for Romanian, it should work at least as well among the others.

The question is **how much of the accuracy gain from a hand-built Romanian package can be obtained for free from the sister languages**, and whether a small amount of linguistic knowledge (correspondence rules) buys more than brute pooling.

### 8.2 Design: leave-one-language-out with knowledge levels

Romanian is the held-out language. Three levels of "Romanian knowledge" are defined, and a meter is built at each:

| Level | Meter | What it knows about Romanian | Cost to produce |
|-------|-------|------------------------------|-----------------|
| 0 | M-ZX-ROM-0 | No Romanian-specific resource (the shared `language-common` list and fold table, present in every meter, are the only exceptions; section 4.4). Pooled IT/ES/FR/PT dictionaries, folded. Shared names and identical word forms transfer by accident of history. | Zero: reuses existing packages. |
| 1 | M-ZX-ROM-1 | Only how Romanian spelling relates to the sister languages: a few hundred correspondence rules and the cognate dataset. No Romanian frequency list, no Romanian passwords. | Hours: rules are learned from the cognate dataset. |
| 2 | M-ZX-RO+ | Everything (section 7). | Weeks of manual resource building. |

All are evaluated on the same Romanian groups against the same attackers, together with M-ZX-EN as the floor. The headline metric is the **gain recovered**:

gain recovered(level ℓ) = (accuracy(level ℓ) − accuracy(M-ZX-EN)) / (accuracy(M-ZX-RO+) − accuracy(M-ZX-EN))

computed per accuracy metric (Spearman on the synthetic set, weighted Spearman on the real-world set, and the dangerous-overestimation rate, for which lower is better, so both differences are negative and the ratio stays positive) and per category. A value near 1 means sister languages substitute for a hand-built package; a value near 0 means they do not.

### 8.3 Building the Romance meters

**Level 0: pooling.** Keep `language-common` and `language-en` as in every meter. Merge the `commonWords`, `firstnames`, `lastnames` and `wikipedia` lists of the four sister packages. Fold diacritics. For each folded string, rank = best rank among the source lists, with ranks first put on a common scale using `wordfreq` frequencies (the packages have different sizes and sources, so raw ranks are not comparable). Add the common folding layer and the sister languages' word sequences.

**Level 1: cognate projection.** Using the Ciobanu & Dinu (LREC 2014) word pairs as training data (Romanian word ↔ its etymon or cognate in each sister language; the dataset covers 53,347 Romanian words with a French partner, 13,377 Italian, 7,780 Spanish and 10,972 Portuguese, of which 4,124 have a partner in all four languages; the pairs with a learnable spelling change, after identical forms are removed, are 445 French, 3,477 Italian, 5,113 Spanish and 7,858 Portuguese strict-cognate pairs (ACL 2014), plus the many French word–etymon pairs, which are mostly near-identical 19th-century borrowings), learn orthographic correspondence rules from each sister language to Romanian: align each pair with Needleman–Wunsch as Ciobanu & Dinu (ACL 2014) do, extract the mismatch n-grams, and keep the frequent ones as substitution rules. The ACL paper itself only *detects* cognates (a classifier); generating Romanian forms is cognate *production* (Beinborn, Zesch & Gurevych 2013), which is what this step adds. After seed exclusion (section 4.4). Apply the rules to the pooled list to produce candidate Romanian forms; keep candidates that are produced by ≥ 2 source languages or confirmed by CogNet, and assign them the rank of their source word. Important: the **rules** are learned from the cognate dataset, which contains Romanian forms; this is the deliberate "small linguistic knowledge" of level 1 and is declared as such. The Romanian frequency list and Romanian passwords remain unused. The test in section 4.4 verifies that no `language-ro` file and no Romanian leaked-password file is read.

**Name pooling** is handled the same way at both levels; shared given names (Maria, Ana, Andrei/Andrea, Ion/Juan/João) are a visible component and are reported separately.

### 8.4 Analyses

1. Gain recovered at levels 0 and 1, overall and per category. The RO-cognate vs RO-noncognate split is the direct test of the mechanism: transfer should work on the former and fail on the latter.
2. Contribution of each pooling source: ablate one sister language at a time, and relate the drop to Ciobanu & Dinu's RO–X intelligibility scores (Europarl: IT 66.0, FR 65.1, PT 64.5, ES 60.0, so expected order IT ≥ FR ≈ PT > ES). French deserves particular attention: 52,868 Romanian words have a French etymon (Ciobanu & Dinu, LREC 2014, Table 1), so French may transfer better than its cognate count suggests.
3. Does pooling hurt? Compare M-ZX-ROM+RO with M-ZX-RO+ on Romanian groups and on EN/RANDOM controls. Bigger dictionaries risk over-penalising (false dictionary hits) and larger bundle size; both are measured.
4. Bundle size and evaluation speed of every meter, since zxcvbn is client-side and size is a deployment constraint (Doucek et al. report this for Czech).
5. (Stretch) Rotate the held-out language once: build the pooled meter from RO/ES/FR/PT and test on an Italian synthetic set generated with the same templates and an A-IT attacker. Synthetic only; no Italian breach data.

### 8.5 What would make this a general result

If level 0 or 1 recovers a large part of the gain on word- and name-based categories, the practical recommendation is concrete: a deployment serving a Romance-language population without a dedicated package should load the pooled Romance dictionaries plus folding, which costs nothing to build. If it recovers little, the result says that password vocabulary is dominated by language-specific and cultural items that etymology does not predict, which is also useful and bounds what any cross-language approach can do. Either way, the method (knowledge levels, gain recovered, cognate/non-cognate split) is reusable for other families (Slavic: Czech/Slovak/Polish; Germanic: Dutch/German/Danish), all of which have zxcvbn-ts packages.

---

## 9. Evaluation metrics

For each (meter, dataset group) pair:

| Metric | Definition | Answers |
|--------|------------|---------|
| Spearman ρ | Rank correlation between meter log10(guesses) and attacker log10(guess number) | RQ1, RQ3, RQ6: does the meter order passwords correctly? |
| Kendall τ | Same, more robust to ties | cross-check |
| Weighted Spearman (Golla & Dürmuth 2018; recommended for online guessing by Wang et al. 2023) | Spearman computed with a weight per password: its frequency in the reference data (section 9.2) | primary accuracy metric on the real-world set; emphasises the common passwords that matter most |
| Dangerous overestimation rate | Fraction of passwords with attacker guess number ≤ 10^6 that the meter scores ≥ 3 | RQ2: the harmful failure mode |
| Safe underestimation rate | Fraction of passwords not cracked within the budget B by any attacker (i.e. censored under A-MIN) that the meter scores ≤ 1; B is reported and must be ≥ 10^10 for this metric to be meaningful | cost of being too conservative |
| Bucket confusion matrix | 5×5 matrix of meter score vs. attacker guess-number bucket | overall picture per group |
| Reclassification rate | Fraction of passwords whose score changed between two meters, by direction | RQ3, RQ4 |
| Mean absolute log error | Mean of \|meter log10 guesses − attacker log10 guess number\| on non-censored passwords | magnitude of misestimation |
| Spelling consistency | For each RO-diacritic variant family, max minus min score, and the spread of log10 guesses | RQ5 |
| Gain recovered | (acc(level ℓ) − acc(M-ZX-EN)) / (acc(M-ZX-RO+) − acc(M-ZX-EN)), per metric and category | RQ6 |
| Bundle size, ms per password | Size of the dictionary payload; median evaluation time | deployment cost of every variant |

A-MIN is the primary ground truth for all groups. A-EN and A-RO are also reported separately to show how conclusions depend on what the attacker knows about the target's language, and every result table is reported against each attacker.

### 9.1 Statistical treatment

- All correlation estimates carry 95% bootstrap confidence intervals (1000 resamples, stratified by category).
- Differences between meters on the same passwords are paired; use a paired bootstrap on the difference in ρ. Gain recovered is a ratio of two paired differences; its CI comes from the same bootstrap resamples.
- Rate comparisons (overestimation rate across groups or meters) use chi-square tests with effect size (Cramér's V), with Holm correction across the family of tests.
- Censored guess numbers are handled by rank-based methods, which are insensitive to the exact censoring value, and reported separately where they would dominate.
- Gain recovered is reported only where the 95% CI of its denominator (the M-ZX-RO+ minus M-ZX-EN difference) excludes zero; otherwise the category is reported as having no gain to recover.

### 9.2 Weights for weighted Spearman

Golla & Dürmuth weight each password by its count in the reference distribution, so common passwords count more. Every synthetic password occurs exactly once, so on the synthetic set weighted Spearman with frequency weights reduces to plain Spearman. Therefore:

- On the synthetic set, the primary accuracy metric is plain Spearman, together with the dangerous-overestimation rate. Weighted Spearman cannot replace that rate, because it does not tell the two error directions apart.
- On the real-world validation set, the weights are the passwords' occurrence counts in the held-out half, following Golla & Dürmuth's online setup.
- A documented proxy weight on the synthetic set (proportional to 1 / A-MIN guess number) is reported only as a sensitivity analysis.
- Implementation: Golla & Dürmuth compute weighted Spearman with the R package wCorr. `scipy.stats.weightedtau` is a different metric. `metrics.py` implements the wCorr formulas and is unit-tested against R's wCorr output on random data, and against the qualitative behaviour of Golla & Dürmuth's Table 2 test cases (LOG, Q4-equi, INV-WEAK-5, …) reproduced on a synthetic reference (their exact values depend on their non-public LinkedIn halves).

---

## 10. Analysis and visualisations

Planned figures, each tied to a research question:

1. Scatter of meter estimate vs. attacker guess number, one panel per meter, coloured by RO/EN/RANDOM. (RQ1)
2. Bar chart of Spearman (weighted Spearman on the real-world set) with CIs, grouped by language, one bar per meter: M-POLICY, M-ZX-EN, M-ZX-RO-PKG, M-ZX-RO+. (RQ1, RQ2, RQ3)
3. Dangerous-overestimation rate per category for the same four meters. (RQ2, RQ3)
4. Heatmap confusion matrices, M-ZX-EN / M-ZX-RO-PKG / M-ZX-RO+, Romanian groups only. (RQ2)
5. Ablation chart: ρ on Romanian groups as resources are added one at a time to M-ZX-RO-PKG. (RQ4)
6. Top-20 most-misjudged password structures with example, scores under each meter, A-RO guess number. (RQ4)
7. Spelling-consistency distribution, before and after normalisation, with one panel per source of variation (encoding, sign dropped, `sh`/`tz`, pre-1993 î), and the rank example from section 2.3. (RQ5)
8. Gain recovered at levels 0 and 1, per category, with the RO-cognate / RO-noncognate contrast highlighted. (RQ6)
9. Per-sister-language ablation drop plotted against Ciobanu & Dinu's intelligibility score of Romanian for that language. (RQ6)
10. Bundle size vs. accuracy for every meter. (deployment trade-off)
11. Real-world validation set: figures 2, 3 and 8 repeated. (external validity)
12. Guessing curves (fraction of passwords cracked vs. log10 guesses) for RO, EN and RANDOM groups, one panel per attacker including A-MIN, following Ur et al. (2015). (RQ1, ground-truth sanity check)
13. Floor vs. knowledge-gap attribution of dangerous overestimations, per category and meter, including M-ZX-RO+-D. (RQ2, RQ4)

All figures generated by scripts from the result tables; no manual editing.

---

## 11. Software framework

```
ro-password-meter/
├── README.md
├── pyproject.toml              # Python >= 3.12 in a venv (system python is 3.9); pinned deps: pandas, numpy, scipy, matplotlib, wordfreq
├── Makefile                    # make data / make attack / make evaluate / make figures
├── bridge/                     # Node package: @zxcvbn-ts/core + language packages, pinned
│   ├── package.json
│   ├── zx.js                   # stdin passwords -> stdout JSONL, one meter config per run
│   ├── configs/                # one JSON per meter: which dictionaries, matchers, options
│   ├── patches/                # core copy with D changed, for M-ZX-RO+-D only
│   └── rules/                  # vendored best66.rule and OneRuleToRuleThemAll.rule with checksums
├── packages/
│   └── zxcvbn-ro-extended/     # the deliverable TS package: dictionaries + matchers + folding
├── data/
│   ├── lexicon/ro/             # ranked Romanian lists, build scripts, provenance notes
│   ├── lexicon/romance/        # pooled IT/ES/FR/PT lists, cognate sets, learned rules
│   ├── synthetic/              # generated dataset + generator seed + category labels
│   └── validation/             # Romanian-filtered breach sample (not committed; build script only)
├── scripts/preliminary/        # overlap measurement and language-ro audit (section 2.3)
├── src/ropw/
│   ├── generate.py             # synthetic dataset generator (independent seed lists)
│   ├── lexicon.py              # builds and normalises Romanian lexical resources
│   ├── normalize.py            # NFC, folding table, spelling-variant table (sh/tz, î/â); shared with bridge/
│   ├── romance/
│   │   ├── pool.py             # level-0 pooling and common-scale re-ranking
│   │   ├── cognates.py         # loads Ciobanu-Dinu sets and CogNet
│   │   └── project.py          # learns correspondence rules, projects candidates (level 1)
│   ├── meters/
│   │   ├── base.py             # Meter interface: evaluate(passwords) -> MeterResult
│   │   ├── policy.py           # M-POLICY
│   │   └── zx_bridge.py        # every zxcvbn-ts variant, selected by config name
│   ├── attack/
│   │   ├── stream.py           # runs hashcat/john/pcfg --stdout | head | grep -n -x -F -f, records guess numbers
│   │   └── pcfg.py             # PCFG attacker (pcfg_cracker wrapper)
│   ├── evaluate.py             # runs all meters over all datasets, writes results.parquet
│   ├── metrics.py              # correlations, rates, confusion, gain recovered, bootstrap
│   └── figures.py              # all plots
├── tests/                      # normalisation, matchers, generator, metrics, no-Romanian-input guard
├── notebooks/                  # exploratory analysis only; nothing in the report depends on them
├── results/                    # generated tables and figures
├── demo/                       # optional web page: enter password, see verdicts from each meter
└── report/                     # LaTeX or Markdown source of the written report
```

Reproducibility rules: fixed seeds, pinned versions of both Python and Node dependencies, `make all` regenerates every table and figure from raw inputs, and the report cites result files by name.

---

## 12. Work plan (14 weeks)

| Week | Work | Output |
|------|------|--------|
| 1 | Literature review (reading list in section 16). Confirm ethics position on breach data with supervisor. Audit `language-ro` and commit the preliminary measurement scripts. Set up repo, Node bridge, CI. Install hashcat 7.x and John, verify `hashcat --stdout` on this machine, vendor the rule files. Email the Ciobanu & Dinu authors; download CogNet. | Annotated bibliography, go/no-go on section 5.3, bridge running M-ZX-EN and M-ZX-RO-PKG, attack tools verified |
| 2 | Build Romanian lexical resources (section 5.1) with provenance notes; time-box the hand-built lists (cultural, expressions, diminutives) to two days. Write the spelling-variant table. Implement NFC + folding and their tests. | `data/lexicon/ro/`, `normalize.py` |
| 3 | Synthetic dataset generator (all categories incl. RO-cognate / RO-noncognate, RO-translit, RO-inflected, RO-diacritic families) and v1 dataset. M-POLICY through the common interface. First evaluation run of the three baseline meters. | `data/synthetic/`, first result tables |
| 4 | Attack stream consumer. Train the PCFG model. Run all attackers (A-EN, A-RO, A-ALL, A-JTR, A-PCFG) at a small budget (10^8) to validate the pipeline. | Guess numbers for the full synthetic set |
| 5 | Full-budget attacks, A-MIN. Metrics and bootstrap. First results for RQ1 and RQ2. | Preliminary tables for RQ1, RQ2 |
| 6 | M-ZX-RO+: deduplicated dictionaries, added lists, folding matcher, old-norm variants, digraph matcher. Spelling experiment for RQ5. | `zxcvbn-ro-extended` v1, RQ5 results |
| 7 | Romanian pattern matchers, Romanian keyboard graphs and leet table. Unit tests. Ablation variants. Patched-core build for M-ZX-RO+-D. | `zxcvbn-ro-extended` v2, `bridge/patches/` |
| 8 | Full evaluation run of all Romanian meters. Results for RQ3, RQ4. **Core project complete.** | Results for RQ3, RQ4 |
| 9 | Real-world validation set (section 5.3) if permitted: filter, precision check, three-way split, profile and reuse-frequency groups. | `data/validation/` build script, profile tables |
| 10 | Evaluate all meters on the validation share (weighted Spearman, reuse groups). Bundle size and speed of every meter. | Results for external validity and deployment cost |
| 11 | Buffer week. Re-run anything that changed. Freeze results. | Frozen `results/` |
| 12 | Figures and tables. Report: method and results sections. | Draft figures, draft sections |
| 13 | Report: introduction, related work, discussion, limitations. Supervisor review. Open the upstream pull requests (dedup fix first). | Full draft, PRs |
| 14 | Revisions, proofreading, presentation slides. Optional demo page. Optional Italian rotation (section 8.4, item 5). | Final report, slides |

The minimum viable project is weeks 1–8 plus 11–14 (RQ1–RQ5 on the synthetic set). Weeks 9–10 add the real-world validation and the deployment cost. RQ6 is future work and is not scheduled; if the project finishes early, level 0 of section 8 (a one-day build) is the first piece to add. The riskiest weeks at 12–15 hours per week are 2 (resource building is open-ended), 4 (five attackers plus the PCFG model) and 6–7 (TypeScript matchers and ablations). Cut order if the schedule slips: first the real-world validation set (section 5.3), then the attacker set (keep A-EN, A-RO, A-JTR; lower the A-PCFG budget further).

---

## 13. Expected outcomes and what counts as success

Likely findings, stated so they can be falsified:

- M-ZX-EN's rank correlation with A-MIN on Romanian groups will be noticeably lower than its correlation with A-MIN on English groups (A-EN and A-RO reported as sensitivity analyses).
- M-ZX-RO-PKG will close a large part of that gap on RO-word and RO-name categories and little of it on RO-place, RO-cultural and RO-phrase, which its lists do not cover.
- Dangerous overestimation will be highest on RO-name-num, RO-word-year, RO-place and RO-phrase; lowest on RO-leet and RANDOM.
- M-ZX-RO+ will recover most of the remaining gap with no measurable change on RANDOM and a small or no change on EN groups. The Romanian leaked-password list and names will contribute more than the general dictionary (ablation).
- Because of the structural floor (section 2.4), M-ZX-RO+ will leave dangerous overestimation on multi-segment categories (RO-name-sym, RO-phrase, RO-passphrase) that no dictionary removes; most remaining errors there will be attributed to the floor, and M-ZX-RO+-D will show how much a smaller D removes.
- The spelling variants of the same word will receive inconsistent scores from M-ZX-RO-PKG, and consistent ones after normalisation. Among the variants, `sh`/`tz` and pre-1993 spellings will be overestimated most, because `language-ro` lacks them.
- *(Future work, RQ6.)* M-ZX-ROM-0 would recover a moderate fraction of the gain on RO-cognate and name categories and close to zero on RO-noncognate and RO-cultural; M-ZX-ROM-1 will recover more on RO-cognate; neither will degrade controls. Italian will contribute the most and Spanish the least, following the intelligibility scores; French may contribute more than expected because of the large number of French borrowings in Romanian.

**A null or partial result is still a success.** If the Romance meters recover little, that is a finding about the limits of cross-language transfer for password vocabulary and is worth reporting. The project succeeds if every research question is answered with a measured, reproducible result and an honest discussion of why.

---

## 14. Limitations to acknowledge in the report

- The attacker models are specific (hashcat rules, particular wordlists). A different attacker produces different guess numbers. Reporting against several attackers and their minimum mitigates but does not remove this.
- Synthetic passwords are drawn from templates that a researcher imagined. The real-world set addresses this, but only if ethics permit its use.
- Romanian lexical resources are assembled by the author and are not exhaustive. Resource quality bounds the meter's improvement.
- Guess numbers are censored at the budget. Conclusions about very strong passwords are weaker than conclusions about weak ones.
- Romanian vocabulary includes a substantial Slavic, Hungarian, Turkish and Greek layer that no Romance sister language can supply; the RO-noncognate group makes this visible, but the proportion of such words in real passwords is unknown and is itself a result.
- The sister-language packages are of uneven quality (e.g. 566 Italian and 362 Portuguese surnames vs. 63,236 Romanian). Pooled name lists inherit this unevenness.
- Level-1 rules are learned from a cognate dataset that contains Romanian forms, so level 1 is not Romanian-free; this is declared and quantified (number of rules vs. number of dictionary entries).
- The Romanian-filter for breach data cannot perfectly separate Romanian from English or other Romance passwords; its precision is estimated and reported.
- A-PCFG runs with a smaller budget (10^9) than the other attackers because of generation speed, so its censoring rate is higher; A-MIN is unaffected for passwords found by any attacker.
- CogNet is licensed CC BY-NC-SA, so level-1 artefacts derived from it are research outputs only and are not part of the upstream contribution.
- The spelling-variant table covers the conventions listed in section 2.5; other informal spellings (for example `x` for `cs`) are not modelled. The digraph matcher may occasionally accept a non-Romanian word whose rewritten form happens to be a Romanian entry.
- Chat abbreviations (`pt`, `bn`, `nmk`, `pwp`, …) are out of scope. They are a closed class of a few dozen items, so any list used to generate test passwords and any list given to the meter would be almost the same, and the meter would recognise the test passwords by construction.
- No user study: the project measures meter accuracy, not whether users change behaviour in response to better feedback.

---

## 15. Original contribution

1. The first empirical measurement, to our knowledge, of password-meter accuracy on Romanian passwords, and the first evaluation of a zxcvbn-ts community language package against an independent cracking-based ground truth.
2. A documented defect analysis of `@zxcvbn-ts/language-ro` (encoding duplicates, missing resource types, no normalisation) with a fix and extended resources contributed upstream.
3. A diacritic normalisation layer for zxcvbn-ts (NFC, encoding folding, spelling-norm variants, digraph matcher) that is reusable by every language package with diacritics, and a measurement of how each way of writing Romanian diacritics affects the meter.
4. *(Future work.)* A method and the first measurement of **cross-language transfer** for password strength meters: knowledge levels, the gain-recovered metric, the cognate/non-cognate split, applied to the Romance family with Romanian held out.
5. A reproducible evaluation framework that can be rerun for any other language, or language family, by swapping the lexical resources.

---

## 16. References and reading list

Verified against the original sources on 2026-10-11. Add any new 2025–2026 work found during the week-1 review.

### Password meters and their evaluation
- D. L. Wheeler. "zxcvbn: Low-Budget Password Strength Estimation." USENIX Security 2016, pp. 157–173. https://www.usenix.org/system/files/conference/usenixsecurity16/sec16_paper_wheeler.pdf
- M. Golla, M. Dürmuth. "On the Accuracy of Password Strength Meters." ACM CCS 2018, pp. 1567–1582. doi:10.1145/3243734.3243769. https://password-meter-comparison.org/files/ccsf285-finalv3.pdf
- D. Wang, X. Shan, Q. Dong, Y. Shen, C. Jia. "No Single Silver Bullet: Measuring the Accuracy of Password Strength Meters." USENIX Security 2023, pp. 947–964. https://www.usenix.org/system/files/usenixsecurity23-wang-ding-silver-bullet.pdf
- X. de Carné de Carnavalet, M. Mannan. "From Very Weak to Very Strong: Analyzing Password-Strength Meters." NDSS 2014. doi:10.14722/ndss.2014.23268
- B. Ur et al. "Design and Evaluation of a Data-Driven Password Meter." ACM CHI 2017, pp. 3775–3786. doi:10.1145/3025453.3026050
- D. Temoshok et al. NIST SP 800-63B-4. "Digital Identity Guidelines: Authentication and Authenticator Management." NIST, July 2025. doi:10.6028/NIST.SP.800-63b-4 (supersedes SP 800-63B, 2017/2020)

### Guessability ground truth
- B. Ur, S. M. Segreti, L. Bauer, N. Christin, L. F. Cranor, S. Komanduri, D. Kurilova, M. L. Mazurek, W. Melicher, R. Shay. "Measuring Real-World Accuracies and Biases in Modeling Password Guessability." USENIX Security 2015, pp. 463–481. https://www.usenix.org/system/files/conference/usenixsecurity15/sec15-paper-ur.pdf
- M. Weir, S. Aggarwal, B. de Medeiros, B. Glodek. "Password Cracking Using Probabilistic Context-Free Grammars." IEEE S&P 2009, pp. 391–405. doi:10.1109/SP.2009.8
- J. Bonneau. "The Science of Guessing: Analyzing an Anonymized Corpus of 70 Million Passwords." IEEE S&P 2012, pp. 538–552. doi:10.1109/SP.2012.49
- W. Melicher, B. Ur, S. M. Segreti, S. Komanduri, L. Bauer, N. Christin, L. F. Cranor. "Fast, Lean, and Accurate: Modeling Password Guessability Using Neural Networks." USENIX Security 2016, pp. 175–191.

### Language, culture and passwords
- P. Doucek, L. Pavlíček, J. Sedláček, L. Nedomová. "Adaptation of password strength estimators to a non-English environment—the Czech experience." Computers & Security 95 (2020) 101757. doi:10.1016/j.cose.2020.101757. Code: https://github.com/lpavlicek/zxcvbn-czech. **Closest prior work.**
- M. AlSabah, G. Oligeri, R. Riley. "Your Culture is in Your Password: An Analysis of a Demographically-diverse Password Dataset." Computers & Security 77 (2018) 427–441. doi:10.1016/j.cose.2018.03.014. https://eprint.iacr.org/2018/1063
- D. Wang, P. Wang, D. He, Y. Tian. "Birthday, Name and Bifacial-security: Understanding Passwords of Chinese Web Users." USENIX Security 2019, pp. 1537–1555.
- Z. Li, W. Han, W. Xu. "A Large-Scale Empirical Analysis of Chinese Web Passwords." USENIX Security 2014, pp. 559–574.
- J. Bonneau, R. Xu. "Of contraseñas, סיסמאות, and 密码: Character encoding issues for web passwords." W2SP 2012. https://jbonneau.com/doc/BX12-W2SP-passwords_character_encoding.pdf
- R. Veras, C. Collins, J. Thorpe. "On the Semantic Patterns of Passwords and their Security Impact." NDSS 2014. doi:10.14722/ndss.2014.23103. Extended: "A Large-Scale Analysis of the Semantic Password Model and Linguistic Patterns in Passwords." ACM TOPS 24(3), 2021. doi:10.1145/3448608
- C. A. Tai, U. Hengartner, A. Wong. "Evaluating the Strength and Availability of Multilingual Passphrase Authentication." NDSS MADWeb 2025. https://www.ndss-symposium.org/wp-content/uploads/madweb25-4.pdf
- C. Jensen, M. Karresand, G. S. Gaba, E. Öhrn. "Are Swedish Passwords Tougher Than the Rest?" NordSec 2024, LNCS, pp. 3–21. doi:10.1007/978-3-031-79007-2_1
- E. Darbutaitė, P. Stefanovič, S. Ramanauskaitė. "Machine-Learning-Based Password-Strength-Estimation Approach for Passwords of Lithuanian Context." Applied Sciences 13(13):7811, 2023. doi:10.3390/app13137811
- D. Pasquini, G. Ateniese, C. Troncoso. "Universal Neural-Cracking-Machines: Self-Configurable Password Models from Auxiliary Data." IEEE S&P 2024. https://arxiv.org/abs/2301.07628 (related work: one model adapting to many populations)

### Cross-language lexical resources (RQ6)
- A. M. Ciobanu, L. P. Dinu. "Building a Dataset of Multilingual Cognates for the Romanian Lexicon." LREC 2014, pp. 1038–1043. https://aclanthology.org/L14-1184/
- A. M. Ciobanu, L. P. Dinu. "Automatic Detection of Cognates Using Orthographic Alignment." ACL 2014, pp. 99–105. doi:10.3115/v1/P14-2017
- A. M. Ciobanu, L. P. Dinu. "On the Romance Languages Mutual Intelligibility." LREC 2014, pp. 3313–3318. https://aclanthology.org/L14-1127/
- A. M. Ciobanu, L. P. Dinu. "An Etymological Approach to Cross-Language Orthographic Similarity. Application on Romanian." EMNLP 2014, pp. 1047–1058. doi:10.3115/v1/D14-1112
- L. Beinborn, T. Zesch, I. Gurevych. "Cognate Production using Character-based Machine Translation." IJCNLP 2013. https://aclanthology.org/I13-1112/
- K. Batsuren, G. Bella, F. Giunchiglia. "CogNet: A Large-Scale Cognate Database." ACL 2019, pp. 3136–3145. doi:10.18653/v1/P19-1302. Data: https://github.com/kbatsuren/CogNet
- A. Conneau, G. Lample, M. Ranzato, L. Denoyer, H. Jégou. "Word Translation Without Parallel Data." ICLR 2018. https://arxiv.org/abs/1710.04087 (MUSE bilingual dictionaries; optional, for non-cognate translation equivalents)
- R. Speer. wordfreq (v3.0.2, 2022). doi:10.5281/zenodo.7199437. https://github.com/rspeer/wordfreq

### Standards and Romanian orthography
- Unicode Standard Annex #15. "Unicode Normalization Forms." https://unicode.org/reports/tr15/
- ASRO. SR 13392:2004. Romanian keyboard layout standard (Standard and Programmers layouts).
- Academia Română, Institutul de Lingvistică "Iorgu Iordan – Al. Rosetti". *Dicționarul ortografic, ortoepic și morfologic al limbii române* (DOOM3), 3rd edition, 2021.
- Academia Română. Decision of 17 February 1993 on writing `â` inside words and the forms `sunt`, `suntem`, `sunteți`.

### Software
- zxcvbn-ts: https://github.com/zxcvbn-ts/zxcvbn (core, `language-common`, `language-ro`, `language-it`, `language-es-es`, `language-fr`, `language-pt-br`; pin the commit used)
- hashcat 7.x (`best66.rule`, combinator mode `-a 1`); John the Ripper jumbo (`--rules=Jumbo`, PRINCE mode `--prince`, incremental mode); `OneRuleToRuleThemAll.rule` (NotSoSecure, external; vendored with checksum)
- `pcfg_cracker` (Weir)
- dexonline database dump; GeoNames RO; CoRoLa frequency lists

---

## 17. Immediate next steps

1. Send this plan to the supervisor; get the ethics decision on breach data; tell them that the Romance-family generalisation (RQ6) is planned as future work.
2. Commit the preliminary `language-ro` audit and overlap-measurement scripts under `scripts/preliminary/` so the numbers in section 2.3 are reproducible.
3. Create the repository with the layout in section 11; get the Node bridge running M-ZX-EN and M-ZX-RO-PKG; install hashcat 7.x and John via Homebrew, confirm `hashcat --stdout` works on this machine, and vendor `best66.rule` and `OneRuleToRuleThemAll.rule` with checksums.
4. Run M-ZX-EN and M-ZX-RO-PKG on twenty hand-picked Romanian passwords (including the `vacanță` / `vacanţă` / `vacanta` triple, a `fetitza` / `Ionutz` pair and a pre-1993 spelling such as `piine`) to confirm the problem exists before investing further.
5. Email the authors (University of Bucharest) to request the Ciobanu & Dinu cognate lists, which are available on request only; ask about licence and format. Start with CogNet, which is downloadable, so level 1 is not blocked while waiting.
