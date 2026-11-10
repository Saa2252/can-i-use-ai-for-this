# BUILD_SPEC.md — "Can I Use AI For This?" (policy v1.5)

An interactive Streamlit app that turns the AI Acceptable Use Policy (AIG-POL-001, version 1.5) into a decision tool.
Audience: LinkedIn visitors (mostly on phones), hiring managers in AI governance, and staff at companies like theirs.

You are building a portfolio piece that has to look polished and also be **correct**. A verdict that misstates the policy is worse than no app. Read this whole file before writing any code.

---

## 0. How to work (read first)

1. **Plan first.** Before coding, write `PLAN.md` with your file layout, the rules-engine design, and the order of phases. Stop and wait for my approval.
2. **Work in phases** (Section 10). At the end of each phase, run the tests and `ruff`, give me a 5-line summary, then **stop** for review.
3. **Never invent policy.** Every rule in the engine must map to a clause ID in the policy. If the policy is ambiguous or silent, do **not** guess. Add the case to `OPEN_QUESTIONS.md` with the clause and both readings.
4. **Never invent law.** The only legal and standards citations allowed are those in Section 7. If you think one is missing, add it to `OPEN_QUESTIONS.md`. Do not add it to the app.
5. **The policy text is the source of truth.** Load clause text from the parsed policy files; never paraphrase clauses inside code.
6. Keep dependencies minimal. Ask before adding anything not listed in Section 2.

---

## 1. Product goals

- **Hero interaction above the fold.** A visitor picks three things and gets a verdict in under 10 seconds, without scrolling first.
- **Every verdict cites its clauses**, showing the clause ID plus the exact text, which expands on tap.
- **Every verdict shows its backing:** ⚖️ Law, 📘 Standard or 🏢 Our choice (Section 7).
- **Shareable.** Every verdict has a URL that reproduces it.
- **Deterministic.** The rules engine is pure Python, with no LLM anywhere in the decision path.
- **Privacy by design.** Nothing the visitor enters is stored or logged. Say so in the footer.
- **Mobile first.** Single column at phone width, with large tap targets.

### Success criteria
- All golden scenarios in Section 6 pass.
- Every clause ID used anywhere exists in the parsed policy (enforced by a test).
- Every ⚖️ Law entry has a `checked` date within 90 days, or the app shows "needs re-check" (enforced by a test that warns rather than fails).
- Works at 375px width with no horizontal scroll.

---

## 2. Stack

- Python 3.12, managed with `uv`
- Streamlit (latest stable): `st.navigation`/`st.Page`, `st.segmented_control`, `st.pills`, `st.query_params`
- `pydantic` v2, `PyYAML`, `pytest`, Streamlit `AppTest` (`streamlit.testing.v1`), `ruff`

Check the installed Streamlit version's docs before using any newer API.

---

## 3. Repo layout (proposed; refine in PLAN.md)

```
app/
  main.py
  pages/
    1_check.py          # hero: "Can I use AI for this?"
    2_matrix.py         # data class × tool tier grid
    3_agent_builder.py  # agent permission builder
    4_scenarios.py      # quiz
    5_review.py         # v1.0 → v1.5: how the policy changed, and why
    6_policy.py         # searchable full policy
  components/           # verdict_card, clause_drawer, basis_badges, footer
  styles/tokens.py
engine/
  models.py             # Inputs, Verdict, Clause, Basis
  policy_parser.py
  rules.py              # evaluate(inputs, version) -> Verdict
  rules_v1_0.yaml
  rules_v1_5.yaml
  basis.yaml            # regulatory crosswalk (Section 7)
policy/
  AI_Acceptable_Use_Policy_v1.0.md
  AI_Acceptable_Use_Policy_v1.5.md   # v1.4 + the edits in Appendix A
tests/
  test_parser.py  test_rules.py  test_clause_integrity.py
  test_basis.py   test_app_smoke.py
.streamlit/config.toml
PLAN.md  OPEN_QUESTIONS.md  README.md
```

**Before Phase 1:** I will put `AI_Acceptable_Use_Policy_v1.0.md` and `AI_Acceptable_Use_Policy_v1.4.md` in `policy/`. Create `v1.5.md` by copying v1.4 and applying **exactly** the edits in Appendix A. Show me the diff before continuing.

---

## 4. Policy parser

- Parse every numbered clause into `Clause(id, part, section, section_title, text)`. Clause IDs come in these forms:
  - Part A: `6.3`, `11.3`
  - Parts B and C: `B.1.3`, `B.6.5`, `C.2`, `C.4.2`
  - Part D: `FS.1`, `INS.1`, `HC.3`, `PS.1`, `RC.3`, `TS.4`, `HR.1`, `ED.4`
- Parse tables as structured data: Section 4 (definitions, including "Irreversible action"), 7.1 (data × tier), B.3 (risk rubric), B.4 (service targets), and C.2 (action limits).
- Parse the staff summary (Always / Ask first / Never) for the policy page.
- Cache with `st.cache_data`.
- Tests: known clause texts; the 7.1 table is 5×3; C.2 has 6 rows; and **no clause text in v1.5 contains the codes `R1`–`R9`**.

---

## 5. Rules engine

### Inputs
- `data_class`: Public | Internal | Confidential | Restricted | Secrets
  - Show helper text from 7.4 and 7.5. Examples: "a colleague's name in an email → Internal", "sick-leave note → Restricted", "client's name → Confidential (B.2.3)".
- `tool`: Tier A | Tier B | Tier C (personal/unknown) | Self-hosted, plus a `host` sub-choice: org servers/cloud, managed company laptop, or personal/unmanaged device (B.1.3, 2.3)
- `activity`: see the table below
- Conditional flags, shown only when relevant:
  - `human_review`
  - `client_contract_allows`
  - `sexual_or_intimate`
  - `agent_action` (read | write | pay | delete | message_external | production_change | add_payee | add_recipient)
  - `recipient_on_allowlist`, `payee_on_allowlist`, `within_caps`
  - `meeting_type` (ordinary | legal_counsel | hr_casework | board_exec | undisclosed_deal)

### Output — `Verdict`
- `status`, one of four values:
  - `ALLOWED`: go ahead and check the output (9.1, 9.2)
  - `NEEDS_APPROVAL`: a Section 8 use, or a per-action human approval. List what's required.
  - `NOT_PERMITTED`: blocked as described, **but a compliant route exists**. Fill in `try_instead`.
  - `PROHIBITED`: Section 6, with no route and no exceptions (18.1)
- `reasons` (plain English), `clauses` (IDs), `requirements` (checklist), `try_instead`, and `basis` (from Section 7, for each cited clause)

### Precedence
`PROHIBITED` > `NOT_PERMITTED` > `NEEDS_APPROVAL` > `ALLOWED`. Evaluate **all** rules, collect **every** clause that fires, then pick the most severe status.

### Rules (store in YAML, not if/else)

**Data rules (always applied):**
- 7.1 table lookup, using the classification from 7.2, 7.4, 7.5 and B.2.3
- Secrets in any tool → PROHIBITED (6.3)
- Non-public data in Tier C → PROHIBITED (6.7)
- Restricted data in Tier A → NEEDS_APPROVAL (8.6, 7.1)
- Self-hosted model: org servers/cloud → treat as Tier A only if B.1.3 is met (assume met, but show the criteria); managed laptop → Tier B at most; personal/unmanaged device → public data only (2.3, B.1.3)
- Client data used for training or fine-tuning with no contract permission → PROHIBITED (6.8, 7.6)

**Activities:**

| Activity | Clauses |
|---|---|
| Drafting / summarizing / translating / research / analysis | 8.10, 9.2 |
| Coding help | 8.10, 9.3, B.5.1 |
| Decision about a person | 8.1, 9.4, 10.3; with no human review → 6.6; add HR.1 for hiring |
| Customer- or public-facing chatbot | 8.2, 10.1 |
| Publishing AI content externally | 8.3, 10.2, 12.2 |
| Synthetic media of a real person | 8.4; if sexual or intimate → 6.2 |
| Monitoring or evaluating employees | 8.7 |
| Emotion recognition of employees or students | 6.1 |
| Fatigue or safety detection (physical state, not emotion) | 8.7 and 8.8, **not** 6.1 |
| Safety-critical or clinical operations | 8.8 |
| Connecting AI to internal systems (plugins, MCP, APIs) | 8.9, 11.9 |
| AI notetaker | Ordinary meeting → ALLOWED (8.11, B.6.1, B.6.2). Legal counsel / HR casework / board executive session / undisclosed deal → NEEDS_APPROVAL (B.6.3) |
| AI agent | See below |

**Agent rules (11.3 and C.2, as amended in v1.5):**
- Read-only → ALLOWED with registration (11.1–11.8)
- Any write rights → NEEDS_APPROVAL (8.5)
- Irreversible actions are defined in **Section 4**. Each needs a human **per action**, except:
  - (a) in-cap payments to allowlisted payees, and
  - (b) external messages to allowlisted recipients within rate limits.
  - Both apply only where the Committee has accepted the risk.
  - In those two cases the verdict is NEEDS_APPROVAL as a **one-time use-case approval**. The requirements list must say "Committee risk acceptance" and "caps / allowlist set in C.2".
- A payment or message outside the allowance → NEEDS_APPROVAL as a **per-action human approval** (11.3, C.2)
- An agent adding a payee or recipient itself → NOT_PERMITTED, with try_instead "a human adds it, and it is logged" (C.2)
- Deletion, commitments to third parties, and production changes → per-action human approval, always (C.2)

---

## 6. Golden scenarios (they double as the quiz and the tests)

| # | Scenario | Data | Tool | Expected | Must cite |
|---|---|---|---|---|---|
| 1 | Summarize a public news article in personal ChatGPT | Public | C | ALLOWED | 7.1, 8.10 |
| 2 | Paste a client contract into personal ChatGPT | Confidential | C | PROHIBITED | 6.7 |
| 3 | Draft an internal memo in the approved enterprise tool | Internal | A | ALLOWED | 8.10 |
| 4 | Summarize an email thread that names colleagues | Internal | A | ALLOWED | 7.5, 8.10 |
| 5 | AI auto-rejects CVs, no human review | Confidential | A | PROHIBITED | 6.6, 8.1 |
| 6 | AI ranks CVs, a recruiter decides | Confidential | A | NEEDS_APPROVAL | 8.1, HR.1 |
| 7 | Upload sick-leave notes to the approved tool | Restricted | A | NEEDS_APPROVAL | 7.4, 7.5, 8.6 |
| 8 | Agent emails customers on the approved list | Internal | A | NEEDS_APPROVAL (one-time) | 8.5, 11.3, C.2 |
| 9 | Agent emails an address not on the list | Internal | A | NEEDS_APPROVAL (per message) | 11.3, C.2 |
| 10 | Agent pays an allowlisted supplier within its cap | Confidential | A | NEEDS_APPROVAL (one-time) | 8.5, 11.3, C.2 |
| 11 | Agent adds a new payee to its own allowlist | Confidential | A | NOT_PERMITTED | C.2 |
| 12 | Paste an API key to debug an error | Secrets | A | PROHIBITED | 6.3 |
| 13 | Webcam emotion detection of employees in meetings | Restricted | A | PROHIBITED | 6.1 |
| 14 | Driver-fatigue detection for the delivery fleet | Restricted | A | NEEDS_APPROVAL | 8.7, 8.8 |
| 15 | Document naming a client in a Tier B tool | Confidential | B | NOT_PERMITTED | B.2.3, 7.1 |
| 16 | Customer-support chatbot on the website | Internal | A | NEEDS_APPROVAL | 8.2, 10.1 |
| 17 | Connect the AI assistant to the CRM via MCP | Confidential | A | NEEDS_APPROVAL | 8.9 |
| 18 | Approved notetaker in a team meeting | Internal | A | ALLOWED | 8.11, B.6.2 |
| 19 | Notetaker in a meeting with legal counsel | Confidential | A | NEEDS_APPROVAL | B.6.3 |
| 20 | Open-weight model on a personal laptop, with internal docs | Internal | Self-hosted, personal device | NOT_PERMITTED | 2.3, B.1.3 |
| 21 | AI-generated intimate image of a real person | Restricted | A | PROHIBITED | 6.2 |

The quiz uses a shuffled set of 10, and must always include 4, 8, 9 and 14. Those four show the policy's most interesting lines.

If any expected result conflicts with your reading of the policy text, **stop and log it in OPEN_QUESTIONS.md**. Never change a test just to make it pass.

---

## 7. Regulatory backing layer ("Backed by")

The **policy decides** the verdict. This layer only explains **why the rule exists**. The verdict never changes based on jurisdiction, because 1.2 already applies the stricter rule.

`engine/basis.yaml` entries look like this:
```yaml
- clause: "6.1"
  type: law            # law | standard | our_choice
  source: "EU AI Act, Article 5"
  jurisdiction: EU
  status: "In force"
  checked: 2026-10-22
  note: "Prohibited practices; legal text and its exclusions govern."
```

**Seed crosswalk. Use only these, and mark every entry `checked: 2026-10-22`. I will re-verify before launch.**

| Clause | Type | Source | Jurisdiction | Status |
|---|---|---|---|---|
| 6.1 | law | EU AI Act Art. 5 | EU | In force |
| 6.2 | law | EU AI Act Art. 5, as amended by the 2026 AI omnibus (non-consensual intimate imagery and CSAM) | EU | Agreed 2026; confirm final text |
| 6.3 | standard + our_choice | ISO/IEC 27001 access control | Global | — |
| 6.6 | law | GDPR Art. 22 | EU/UK | In force |
| 7.3 | law | GDPR Arts. 5–6; India DPDP Act 2023 and Rules 2025 | EU; India | DPDP phased to May 2027 |
| 8.1 / HR.1 | law | EU AI Act Annex III (high-risk); Colorado SB 26-189 | EU; US-CO | Dec 2027; Jan 2027 |
| 10.1 | law | EU AI Act Art. 50 | EU | Applies 2026 |
| 11.x / Part C | standard | OWASP Top 10 for Agentic Applications; Singapore Model AI Governance Framework for Agentic AI | Global; SG | — |
| 16.1 | law | EU AI Act Art. 4 (AI literacy) | EU | Confirm after omnibus |
| FS.1 | standard | US Revised Guidance on Model Risk Management (Apr 2026); MAS Guidelines on AI Risk Management (Oct 2026) | US; SG | Issued |
| Whole policy | standard | ISO/IEC 42001 (AI policy); NIST AI RMF GOVERN | Global | — |
| 15.1, 17.2, B.4, C.2 caps | our_choice | Internal governance choice | — | — |

**UI:**
- Verdict card: a "Backed by" row of badges (⚖️ / 📘 / 🏢). Tapping one shows the source, status and date checked.
- A jurisdiction lens (Global / EU / US / India) on the policy page highlights which laws apply where.
- An entry older than 90 days shows a muted "needs re-check" tag.
- Footer: "Legal references are for context, not legal advice. Status checked [date]."

---

## 8. Design system

**Tone:** a calm, credible "governance" look, like a well-run public-sector service rather than a startup landing page.

- **Tokens:**
  - Background `#FAFAF7`, surface `#FFFFFF`, text `#1C2430`, muted `#5B6573`, accent teal `#0F5E66`
  - Verdicts: ALLOWED green `#1E7B4A`, NEEDS_APPROVAL amber `#B26B00`, NOT_PERMITTED orange-brown `#9A4A12`, PROHIBITED red `#B42318`
  - All at AA contrast
- **Never color alone:** every verdict has an icon, a word and a color.
- **Verdict card:** status line, one-sentence reason, clause chips, "Backed by" badges, requirements or try-instead, and "Copy link."
- Single column, max width about 720px. No balloons or confetti.
- Hide Streamlit's default chrome. Custom footer: "Model policy, not legal advice" · "Nothing you enter is stored" · version and dates.
- Keep all custom CSS in one small file.

---

## 9. Pages

1. **Check (hero):** "Can I use AI for this?" Inputs in the order Data → Tool → Activity, with conditional flags. The verdict renders below. Two-way sync with `st.query_params`. A "Try an example" chip row (scenarios 2, 4, 8).
2. **Matrix:** the 7.1 grid. Tapping a cell shows the rule and a realistic example.
3. **Agent builder:** toggles for read / write / pay / delete / message externally / production change / call other agents. Shows live required controls from 11.x and C.x, plus the two irreversible-action exceptions and their conditions.
4. **Scenarios quiz:** 10 questions, a reveal with clauses and backing, a score, and "Share your score."
5. **Review (v1.0 → v1.5):**
   - A version toggle: run any scenario through `rules_v1_0.yaml` vs `rules_v1_5.yaml`.
   - A "Scenarios whose verdict changed" list, computed automatically.
   - "How the policy changed" cards built from the change logs in v1.5. Include the **disputed points**: where the reviewer was overruled (fatigue detection, the absolute secrets ban, platform labelling, the R-codes) and where the author accepted fixes. Show both sides briefly.
6. **Policy browser:** the staff summary first, then the full text with search, clause anchors and the jurisdiction lens.

---

## 10. Phases (stop for review after each)

0. **Policy files:** create v1.5 from v1.4 plus Appendix A, and show me the diff.
1. **Engine:** parser, models, `rules_v1_5.yaml`, `basis.yaml`, `evaluate()`. All Section 6 tests pass. No UI yet.
2. **Hero page:** Check page, verdict card with Backed-by badges, design tokens, query params, footer, AppTest smoke test.
3. **Matrix, Agent builder, Quiz, Policy browser.**
4. **`rules_v1_0.yaml` and the Review page**, including the "verdict changed" diff.
5. **Polish:** a 375px pass, README with screenshots, Streamlit Community Cloud deploy notes, and a `?demo=1` mode that preloads scenario 2 for screen recording.

---

## 11. Definition of done

- `pytest` is green and `ruff` is clean.
- Every clause ID in the YAML and code exists in the parsed v1.5 policy (or v1.0, for v1.0 rules).
- Every basis entry uses only the Section 7 crosswalk, and each has a date checked.
- `OPEN_QUESTIONS.md` lists every ambiguity found, with none silently resolved.
- Works at 375px with no horizontal scroll.
- The README explains: what it is, rules as data, clause citation, the backing layer, how to run it, and the disclaimer.

---

## Appendix A — v1.5 edits to apply to v1.4

**A.1 In Section 11.3, replace everything from "Irreversible actions (defined in Section 4)" to the end of the clause with:**

> Irreversible actions (defined in Section 4) need human approval for each action, with two exceptions. Each applies only where the AI Governance Committee has accepted that risk for the use case: (a) payments within the per-action and daily caps, to payees on the allowlist; and (b) messages sent outside the organization to recipients on the allowlist, within the rate limits. Both are set in C.2. Part C may tighten these exceptions but never widen them.

**A.2 In C.2, replace the Recipients row text with:**

> Messages go outside the organization without per-action approval only where the Committee has accepted the risk (11.3), within the rate limit, and only to allowlisted domains or addresses. A message to anyone not on the allowlist needs human approval. Adding a recipient to the allowlist needs human approval, is logged, and is never done by an agent.

**A.3 In C.2, replace the Irreversible actions row text with:**

> Deletion, any payment outside the in-cap allowance, any external message outside the recipient allowance, commitments to third parties, and production changes always need human approval for each action.

**A.4 Set Version to `1.5 (model policy)` and add this table above "Changes in version 1.4":**

> ## Changes in version 1.5
>
> | Area | Change |
> |---|---|
> | External messages | 11.3 adds a second narrow exception: messages to allowlisted recipients within rate limits, where the Committee accepts the risk. C.2 matches, and adding a recipient follows the same rules as adding a payee. |
