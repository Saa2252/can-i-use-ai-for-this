# OPEN_QUESTIONS.md

Ambiguities found while reading the policy and BUILD_SPEC. Per BUILD_SPEC §0.3 and
§0.4, nothing here is resolved by guessing: each entry gives the clause and both
readings. None of these has been silently decided in code.

Status key: **needs your call** · **following BUILD_SPEC** (proceeding on the
spec's stated expectation, flagged because the policy text alone is ambiguous) ·
**resolved**

---

## Q1 — v1.0 has no Part B, C or D clauses, so some v1.0 rules have nothing to cite

**Status:** resolved in Phase 4 — see "How this was settled" at the end of this entry

**Where:** `policy/AI_Acceptable_Use_Policy_v1.0.md` vs BUILD_SPEC §6, §10.4

v1.0 predates the Part A–D restructure introduced in v1.1. It has sections 1–18
and two annexes ("Annex: Financial services", "Annex: Employment and HR"), and
**zero** `B.*` or `C.*` clause IDs. Several golden scenarios cite clauses that
simply do not exist in v1.0:

| Scenario | Cites in v1.5 | Exists in v1.0? |
|---|---|---|
| 10, 11 (agent pay / add payee) | `C.2` | no |
| 15 (client name, Tier B) | `B.2.3` | no |
| 18, 19 (notetakers) | `B.6.1`, `B.6.2`, `B.6.3` | no — v1.0 has no notetaker rules at all |
| 20 (self-hosted) | `B.1.3` | no |

**Reading A:** the v1.0 ruleset cites only the Part A clause that does exist
(e.g. scenario 15 → `7.1` alone, dropping `B.2.3`). The scenario still returns a
verdict, and the Review page shows the citation getting more specific over time.

**Reading B:** the scenario is marked "not covered in v1.0" and the Review page
reports the *absence* as the change. Arguably the more honest result for
notetakers (18, 19), where v1.0 is silent rather than differently worded — a
verdict computed from silence would invent policy, which §0.3 forbids.

**My inclination at the time:** B for scenarios 18 and 19 (genuine silence),
A elsewhere.

### How this was settled

**Reading A, everywhere. My inclination above was wrong, and reading v1.0
properly is what corrected it.**

v1.0 is *not* silent on notetakers. Its 8.10 is a catch-all in the same words
v1.5 uses:

> Everything else, such as drafting, summarizing, translating, research,
> analysis and coding help, is permitted in approved tools within the data
> rules, with the user checking the output.

So v1.0 does answer the notetaker question: permitted, wherever the data rules
allow the tool. Marking it "not covered" would have hidden the most interesting
finding on the Review page — that **under v1.0 an AI notetaker was permitted in
a meeting with legal counsel**, and B.6.3 is what changed that. A verdict read
off 8.10 is reading v1.0's text, not inventing policy from silence.

Everywhere else the rule exists in v1.0 under a different number, so the v1.0
ruleset cites v1.0's own numbering. No scenario needed a "not covered" state,
and none was built.

**One inference remains, and it is worth your eye.** v1.0 has no self-hosted or
open-weight criteria at all, and its only Tier A test (7.5) is vendor-contract
shaped ("an enterprise contract, no training on our inputs..."), which a locally
run model cannot meet. I therefore resolve any self-hosted model to Tier C under
v1.0, on the strength of v1.0's own definition of Tier C as "anything not
assessed". That makes scenario 20 PROHIBITED under v1.0 against NOT_PERMITTED
under v1.5 — one of the four changed verdicts. The inference is the step from
"cannot meet the Tier A criteria" to "is therefore Tier C"; v1.0 never says it
outright. It is recorded in `resolve_effective_tier` in `engine/models.py`.

---

## Q2 — Does the "no R1–R9" test read clause text or the whole file?

**Status:** following BUILD_SPEC

**Where:** BUILD_SPEC §4, final bullet: "no clause text in v1.5 contains the codes
`R1`–`R9`"

The R-codes are gone from every clause in v1.5, but the string survives once, at
line 34, inside the **v1.4 changelog table**:

> | Approval codes | The R1 to R9 labels are removed. Clauses 8.1 to 8.9 are cited by number everywhere…

**Reading A:** the test scopes itself to parsed `Clause.text`. Passes. A changelog
row describing the removal is not clause text, and deleting the row would destroy
the version history the Review page (§9.5) is built from.

**Reading B:** the test greps the whole file. Fails today, and the only fix is to
reword the changelog.

**Proceeding with A.** Flagging it because a reviewer running a naive `grep R1`
will see a hit and think the edit was missed.

---

## Q3 — `Verdict` needs a field to distinguish one-time from per-action approval

**Status:** following BUILD_SPEC

**Where:** BUILD_SPEC §5 (`Verdict` fields) vs §6 (expected results)

§5 lists `status, reasons, clauses, requirements, try_instead, basis`. But §6
expects three different NEEDS_APPROVAL results:

| Scenario | Expected |
|---|---|
| 8 Agent emails the approved list | NEEDS_APPROVAL **(one-time)** |
| 9 Agent emails an address not on the list | NEEDS_APPROVAL **(per message)** |
| 10 Agent pays an allowlisted supplier in cap | NEEDS_APPROVAL **(one-time)** |

Nothing in the §5 field list carries that distinction, so it cannot be asserted in
a test or rendered on the card.

**Adding** `approval_kind: one_time_use_case | per_action | none` to `Verdict`.
It is the smallest addition that makes §6 testable, and it is derivable straight
from 11.3 (the two exceptions are one-time; everything else is per action). Noted
here because it is a field BUILD_SPEC does not name.

---

## Q4 — Is a self-hosted model on a personal device Tier C? (changes scenario 20 from NOT_PERMITTED to PROHIBITED)

**Status:** following BUILD_SPEC — **but please read this one**

**Where:** 2.3, 6.7, B.1.3, Section 4 definition of Tier C, vs BUILD_SPEC §6 row 20

Scenario 20 is "open-weight model on a personal laptop, with internal docs",
expected **NOT_PERMITTED**, citing 2.3 and B.1.3.

The tension:

- **Section 4** defines Tier C as "anything not assessed, including personal
  accounts."
- **6.7** prohibits "putting anything other than public information into a Tier C
  tool" — and 6.7 is in Section 6, where 18.1 allows **no exceptions** and
  BUILD_SPEC §5 maps Section 6 to `PROHIBITED`.
- **2.3** and **B.1.3** say a model on a personal or unmanaged device "may be used
  with public data only" — the language of a boundary, not of a prohibition, and
  B.1.3 sits in a Part B standard rather than Section 6.

**Reading A (BUILD_SPEC's):** the personal-device self-hosted case is its own
branch, governed by 2.3/B.1.3, and is NOT_PERMITTED with a compliant route
(`try_instead`: run it on org infrastructure, or use a Tier A tool). Internal data
on a personal device is a device-control failure, not one of Section 6's hard
lines.

**Reading B:** an unassessed model on an unmanaged device is the definition of
"not assessed", therefore Tier C, therefore 6.7 fires and the verdict is
PROHIBITED with no route.

**Why it matters beyond one row:** under Reading B, scenario 20's card would show
"no route, no exceptions" — and `try_instead` would be wrong to offer. The two
readings give the user opposite advice about whether there is a way to proceed.

**Proceeding with Reading A**, per §6, and the engine gives
`personal_selfhosted` its own `effective_tier` value rather than folding it into
Tier C. I have **not** changed the test (§6: "never change a test just to make it
pass"). If you prefer Reading B, the policy needs a word in 2.3 or B.1.3 saying
whether such a host is Tier C — right now it is inferable either way.

---

## Q5 — "Physical state, not emotion" is BUILD_SPEC's distinction, not the policy's

**Status:** needs your call (cosmetic, but it is a legal line)

**Where:** 6.1, 8.7, 8.8, vs BUILD_SPEC §5 activity table

BUILD_SPEC draws the line between scenario 13 (webcam emotion detection →
PROHIBITED, 6.1) and scenario 14 (driver-fatigue detection → NEEDS_APPROVAL,
8.7 + 8.8) with the gloss "physical state, not emotion".

That phrase appears nowhere in the policy. 6.1 bans "emotion recognition in the
workplace" by reference to EU AI Act Article 5 and defers to "the legal text and
its stated exclusions"; 8.8 covers "any use that relies on an exclusion in
Article 5".

The verdicts are not in question — the spec states them and they follow from 6.1
and 8.8. The question is **presentation**: the Check page must not render
"physical state, not emotion" inside a clause drawer as though it were policy
text, because §0.3 and §0.5 forbid paraphrasing clauses in code.

**Proposal:** the engine cites 6.1/8.7/8.8 verbatim from the parsed policy, and
the distinction appears as an explicitly labelled interpretation note
("how we read this", visually separated from clause text), or not at all.
Tell me which you want.

---

## Q6 — Clause 6.3's backing type is "standard + our_choice", which the schema has no value for

**Status:** following BUILD_SPEC

**Where:** BUILD_SPEC 7, crosswalk row for 6.3, vs the `type` field in the same section

The `basis.yaml` example in BUILD_SPEC 7 gives `type` one value from
`law | standard | our_choice`. The crosswalk row for 6.3 reads
`standard + our_choice`, and names a source only for the standard half
("ISO/IEC 27001 access control").

**Encoded as two entries** for clause 6.3: one `standard` with the ISO source,
one `our_choice` with source "Internal governance choice" — the wording the
last crosswalk row uses for exactly that idea. The verdict card then shows both
badges, which is the honest reading: the ban on entering secrets rests partly
on a standard and partly on our own stricter choice.

The small inference is the `our_choice` **source string**, since the crosswalk
does not give one for that half. Say the word and I will leave it blank
instead.

---

## Q7 — BUILD_SPEC asks the Review page to show a review history this project has no record of

**Status:** needs your call (the page ships, but check how it is framed)

**Where:** BUILD_SPEC 9.5

The spec asks the Review page to include "the **disputed points**: where the
reviewer was overruled (fatigue detection, the absolute secrets ban, platform
labelling, the R-codes) and where the author accepted fixes. Show both sides
briefly."

Two problems with taking that literally:

1. **There is no transcript.** The only record in this repository is the policy
   text and its five change-log tables. Writing "the reviewer argued X and was
   overruled" would be inventing an exchange I cannot see, which 0.3 forbids as
   firmly for history as for policy.

2. **One of the four does not look overruled.** The spec groups platform
   labelling with the overruled points, but 10.2 in v1.1 reads "unless a
   contract or law requires one", and by v1.5 it reads "unless a contract,
   **law or platform rule** requires one", with change log 1.2 recording the
   edit. On the face of the text that point was *accepted*, not overruled.

**What the page does instead:** it gives each of the four as a question the
policy could have settled either way, sets out both readings, says how it was
settled, and names the change-log row or clause where that decision is
recorded. It states plainly that the app holds no transcript of the review, so
the readings are reconstructed from the text.

Three of the four have direct change-log evidence (1.1 Secrets, 1.2 Small
edits, 1.3/1.4 Approval codes). **Fatigue detection has none** — no change-log
row mentions it. Its resolution comes from BUILD_SPEC 5's own ruling plus the
1.1 row making 6.1 defer to the legal text and its exclusions.

**If you have the actual review correspondence**, send it and I will replace the
reconstruction with what was really argued. Otherwise, confirm that the "two
readings, and where it is recorded" framing is what you want, or tell me to
assert the overruled/accepted framing as the spec words it.
