# PLAN.md — "Can I Use AI For This?"

Implementation plan for BUILD_SPEC.md. Awaiting approval before Phase 1.

Policy versions in `policy/`: `v1.0` (baseline), `v1.4` (input), `v1.5` (generated in Phase 0 — diff reviewed).

---

## 1. File layout

Mostly as BUILD_SPEC §3, with the refinements marked **[new]**.

```
app/
  main.py                   # st.navigation entry point
  pages/
    1_check.py              # hero: "Can I use AI for this?"
    2_matrix.py             # data class × tool tier grid
    3_agent_builder.py      # agent permission builder
    4_scenarios.py          # quiz
    5_review.py             # v1.0 → v1.5 comparison
    6_policy.py             # searchable full policy
  components/
    verdict_card.py  clause_drawer.py  basis_badges.py  footer.py
    inputs.py               # [new] the conditional-flag logic, shared by
                            #       Check / Agent builder / Quiz
  styles/
    tokens.py               # colour + spacing tokens
    app.css                 # [new] the one CSS file BUILD_SPEC §8 asks for
engine/
  models.py                 # Inputs, Verdict, Clause, Basis, Status
  policy_parser.py
  rules.py                  # evaluate(inputs, version) -> Verdict
  conditions.py             # [new] the `when:` matcher (no eval(), see §3)
  rules_v1_0.yaml
  rules_v1_5.yaml
  basis.yaml
  scenarios.yaml            # [new] the 21 golden scenarios as data, so the
                            #       tests, quiz and Review page share one source
policy/
  AI_Acceptable_Use_Policy_v1.0.md
  AI_Acceptable_Use_Policy_v1.4.md    # kept: the input to Phase 0
  AI_Acceptable_Use_Policy_v1.5.md
tests/
  test_parser.py  test_rules.py  test_clause_integrity.py
  test_basis.py   test_app_smoke.py
  test_scenarios.py           # [new] drives engine/scenarios.yaml
.streamlit/config.toml
PLAN.md  OPEN_QUESTIONS.md  README.md  pyproject.toml
```

**Why `scenarios.yaml`:** BUILD_SPEC §6 says the golden scenarios "double as the quiz
and the tests", and §9.5 wants the Review page to compute which verdicts changed
between versions. Three consumers of one table means it should be data, not a
literal repeated in `test_rules.py` and `4_scenarios.py`. It also enforces §6's
"never change a test just to make it pass" — the expectations live in one
reviewable file.

---

## 2. Parser design

The two policy versions are **structurally different documents**, so the parser
detects shape rather than assuming one:

| | v1.0 | v1.5 |
|---|---|---|
| Part headers | none | `# Part A:` … `# Part D:` |
| Sections | `## 7. Data rules` | same, plus `## B.1 Tool tiers`, `## C.2 Action limits` |
| Annexes | `# Sector annexes` + `## Annex: Financial services` | `# Part D` + `## D.1 Financial services` |
| Clause IDs | `7.4` only | `7.4`, `B.1.3`, `C.2`, `FS.1` |
| Front matter | bold key/value lines | a markdown table |
| R-codes | present (11 uses) | gone from clause text |

### Clause extraction

`Clause(id, part, section, section_title, text)`.

Two kinds of citable ID, both required by BUILD_SPEC §4:

1. **Numbered clauses** — lines starting `**<id>**`. Covers Part A (`6.3`, `11.3`),
   Part B/C sub-clauses (`B.1.3`, `B.6.5`, `C.4.2`) and Part D (`FS.1`, `ED.4`).
2. **Leaf sections** — a `## B.3 …` / `## C.2 …` heading with *no* `**B.3.n**`
   sub-clauses underneath. Its body (prose or a table) becomes the clause text.
   Verified against v1.5:
   - leaf, cited by section ID: **B.3, B.4, B.8, B.9, B.10, C.2, C.3**
   - container, cite sub-clauses: B.1, B.2, B.5, B.6, B.7, C.1, C.4, C.5, C.6

   This matters because BUILD_SPEC cites `C.2` and `B.3` directly, and five golden
   scenarios (8–11) depend on `C.2` resolving.

### Table extraction

Returned as structured data, keyed by the owning clause/section:
Section 4 definitions (incl. "Irreversible action"), 7.1 (5 data classes × 3 tiers),
B.3 (rubric: 5 factors × 3 levels, plus the level/approver table), B.4, C.2 (6 rows).

### Staff summary

Parsed into `{always: [...], ask_first: [...], never: [...]}` from the
"Staff summary" section. Absent in v1.0 — returns empty, and the Review page
reports that as a v1.1 addition.

Both documents are loaded once and cached with `st.cache_data`.

---

## 3. Rules engine design

### Shape

Rules are **data**, evaluated by a small pure-Python matcher. No `if/elif` ladder
of policy logic, and no `eval()` — the `when:` block is a declarative tree, which
keeps the engine deterministic and the YAML reviewable by a non-programmer.

```yaml
- id: secrets_any_tool
  when: { data_class: [Secrets] }
  then:
    status: PROHIBITED
    reason: "Secrets never go into any AI tool, in any tier."
    clauses: ["6.3"]

- id: agent_pay_in_cap_allowlisted
  when:
    all_of:
      - { activity: [agent] }
      - { agent_action: [pay] }
      - { payee_on_allowlist: [true] }
      - { within_caps: [true] }
  then:
    status: NEEDS_APPROVAL
    approval_kind: one_time_use_case
    reason: >
      An in-cap payment to an allowlisted payee is one of the two exceptions
      that do not need approval for each action.
    clauses: ["8.5", "11.3", "C.2"]
    requirements:
      - "Committee risk acceptance"
      - "caps / allowlist set in C.2"
```

`when:` supports a mapping (field → accepted values; all keys must match) and the
combinators `all_of`, `any_of`, `none_of`. That is the whole grammar.

### Derived inputs

Computed before matching, so the YAML stays flat:

- **`effective_tier`** — resolves `tool` + `host` per B.1.3 and 2.3:
  org servers/cloud → `A` (B.1.3 assumed met, criteria shown in the UI);
  managed company laptop → `B`; personal/unmanaged device → `personal_selfhosted`,
  a distinct value, **not** Tier C (see OPEN_QUESTIONS Q4).
- **`is_agent`**, **`is_irreversible`** — `is_irreversible` is read from the
  Section 4 definition table, not hardcoded.

### Output

`Verdict(status, reasons[], clauses[], requirements[], try_instead, basis[], approval_kind)`.

**`approval_kind`** is an addition to BUILD_SPEC §5's field list:
`one_time_use_case | per_action | none`. §6 distinguishes "NEEDS_APPROVAL
(one-time)" from "NEEDS_APPROVAL (per message)" for scenarios 8/9/10, which needs
a machine-readable field to test and to render. Logged as Q3.

### Precedence

Evaluate **every** rule. Collect each fired rule's clauses, reasons and
requirements. Status = max severity over all fired rules:
`PROHIBITED > NOT_PERMITTED > NEEDS_APPROVAL > ALLOWED`.

This is why scenario 13 (emotion recognition, Restricted data, Tier A) returns
PROHIBITED on 6.1 even though 8.6 also fires — and both clauses still appear on
the card, which is the behaviour BUILD_SPEC §5 asks for.

`ALLOWED` is a floor, not a rule: if nothing more severe fires, the activity rule
supplies 8.10/9.2 and the status stays ALLOWED.

---

## 4. Backing layer

`engine/basis.yaml` holds only the 13 rows of BUILD_SPEC §7, every entry
`checked: 2026-10-22`. A `Basis` has `clause, type, source, jurisdiction, status,
checked, note`. Lookup is by clause ID, with prefix matching for the two wildcard
rows (`11.x / Part C`, "Whole policy").

`test_basis.py` asserts: no source outside the §7 crosswalk, every entry has a
`checked` date, and — per BUILD_SPEC §1 — emits a **warning, not a failure**, when
a `law` entry is older than 90 days. Against today (9 Nov 2026) `2026-10-22` is
18 days old, so the "needs re-check" tag is dormant but tested.

---

## 5. Phase order

Each phase ends with `pytest`, `ruff`, a 5-line summary, then a stop for review.

| Phase | Deliverable | Gate |
|---|---|---|
| **0 ✅** | v1.5 from v1.4 + Appendix A | diff reviewed — done |
| **1 ✅** | `models.py`, `policy_parser.py`, `rules_v1_5.yaml`, `basis.yaml`, `evaluate()`, `scenarios.yaml` | all 21 golden scenarios pass; clause-integrity and basis tests green; no UI — done |
| **2 ✅** | Check page, verdict card, Backed-by badges, tokens + CSS, query-param sync, footer | AppTest smoke test; verdict reproduces from URL — done |
| **3 ✅** | Matrix, Agent builder, Quiz, Policy browser | quiz always includes scenarios 4, 8, 9, 14 — done |
| **4 ✅** | `rules_v1_0.yaml` + Review page | "verdict changed" list computed, not written by hand — done |
| **5 ✅** | 375px pass, README + screenshots, deploy notes, `?demo=1` | no horizontal scroll at 375px — done |

Phase 1 carries the risk, so it lands before any pixel is styled: if the engine
can't reproduce §6 from the policy text, the UI is wasted work.

---

## 6. Testing strategy

| File | Asserts |
|---|---|
| `test_parser.py` | known clause texts match the file byte-for-byte; 7.1 is 5×3; C.2 has 6 rows; leaf-vs-container sections resolve; **no parsed clause text in v1.5 contains R1–R9** (scoped to clauses — see Q2) |
| `test_rules.py` | all 21 golden scenarios, status **and** the "must cite" clause set |
| `test_clause_integrity.py` | every clause ID in `rules_v1_5.yaml` + `basis.yaml` + components exists in parsed v1.5; every ID in `rules_v1_0.yaml` exists in parsed v1.0 |
| `test_basis.py` | sources confined to the §7 crosswalk; dates present; staleness warns |
| `test_scenarios.py` | `scenarios.yaml` matches BUILD_SPEC §6 row for row (guards against a scenario being quietly edited to pass) |
| `test_app_smoke.py` | each page renders via `AppTest`; query params round-trip |

---

## 7. Open questions

Four are logged in `OPEN_QUESTIONS.md`. **Q4 affects Phase 1 directly** —
scenario 20's expected status depends on whether a self-hosted model on a personal
device counts as Tier C. I follow BUILD_SPEC §6 (`NOT_PERMITTED`) and have not
changed the test, but the reading is worth your eye before I build on it.
