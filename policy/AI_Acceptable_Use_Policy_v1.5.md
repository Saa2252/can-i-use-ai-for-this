# AI Acceptable Use Policy

**Model policy template. Replace bracketed fields before adoption.**

| Field | Value |
|---|---|
| Policy ID | AIG-POL-001 |
| Version | 1.5 (model policy) |
| Organization | [Organization name] |
| Prepared by | [Your name], [Your role] |
| Owner | Head of AI Governance |
| Approver | Executive Committee (Part A only) |
| Companion documents | AI Use Standard (Part B), AI Agent Standard (Part C), Sector Annexes (Part D), all owned by the AI Governance Committee |
| Review | Part A yearly; Parts B to D quarterly |
| Version date | 9 Nov 2026 |
| Regulatory status checked | 22 Oct 2026 |

This document has four parts. **Part A** is the policy: principles, hard lines and accountability, approved by the Executive Committee. **Parts B and C** are standards that hold the operational detail (numbers, criteria, limits), so the AI Governance Committee can update them without re-approving the policy. **Part D** adds sector rules.

---

## Changes in version 1.5

| Area | Change |
|---|---|
| External messages | 11.3 adds a second narrow exception: messages to allowlisted recipients within rate limits, where the Committee accepts the risk. C.2 matches, and adding a recipient follows the same rules as adding a payee. |

## Changes in version 1.4

| Area | Change |
|---|---|
| Irreversible actions | The definition moves from Part C into Section 4, so only the Executive Committee can change what 11.3 means. The payment exception stays in 11.3; Part C sets only the caps and the allowlist. |
| Payee allowlist | Adding a payee needs human approval, is logged, and can never be done by an agent (C.2). |
| Approval codes | The R1 to R9 labels are removed. Clauses 8.1 to 8.9 are cited by number everywhere, so "Restricted" only names the data class. |
| HR records with health data | Sick-leave notes, medical accommodations and similar records stay Restricted (7.5). |

## Changes in version 1.3

| Area | Change |
|---|---|
| Approval authority | Section 8 uses are approved by the AI Governance Committee, or by an approver it delegates to in writing. B.3 sets how deep the assessment goes, not who approves. |
| Two meanings of "Restricted" | Section 8 is renamed "Uses that need approval", so "Restricted" now refers only to the data class. |
| Personal data | HR files and performance records are Confidential individually, not only in bulk (7.5). |
| Irreversible actions | Defined once in C.0. A payment counts as irreversible even if a refund or chargeback might be possible. |
| Self-hosted models | Three plain hosting rules replace the laptop wording in B.1.3. |
| Staff summary | Approved notetakers move to "Always"; only the meetings excluded in B.6.3 stay under "Ask first". |

## Changes in version 1.2

| Area | Change |
|---|---|
| Personal data | Restricted now means sensitive personal data only (7.4). Ordinary personal data, such as a colleague's name in an email, is Internal or Confidential. Bulk personal data is at least Confidential. |
| Agent payments | 11.3 and C.2 now agree: in-cap payments to allowlisted payees are the only irreversible action an agent may take without per-action approval, and only where the Committee accepts that risk. |
| Enforcement | 17.2 covers a first breach found by monitoring that the person did not know they had made. |
| Self-hosted models | B.1.3 matches 2.3: unmanaged or personal device means Tier C; managed laptop outside managed infrastructure means Tier B at most. |
| Legal hold | A legal hold overrides every deletion rule in Parts B and C (B.9). |
| Small edits | Platform labelling rules (10.2), "where one exists" (PS.1), cross-references to Section 6 in RC.3 and ED.4. |

## Changes in version 1.1

| Area | Change |
|---|---|
| Enforcement | 17.2 now applies discipline to deliberate or concealed prohibited use only, consistent with the no-blame rule in 15.2. |
| Structure | Operational numbers moved into a new AI Use Standard (Part B) and AI Agent Standard (Part C). The 24-hour reporting window stays in the policy (see 15.1). |
| Self-hosted models | Separate Tier A criteria for self-hosted and open-weight models (B.1.3). |
| Secrets | The ban on entering secrets stays absolute. New clauses cover AI tools reading repositories and agents needing credentials (6.3, C.1). |
| Classifying data | The prompt, context and attachments all count when classifying data (7.2). |
| Article 5 | 6.1 now defers to the legal text and its exclusions. Lawful uses near the line need approval (8.8). |
| Output checks | 9.2 scales verification to how the output will be used. |
| Data table | Removed the "no client names" patch; client information is Confidential for AI use (B.2.3). |
| Devices | Personal devices covered through a managed-app rule (2.2, 2.3). |
| Disclosure | Organizational default where local law is silent (10.2). |
| New content | Risk rubric (B.3), AI notetakers (B.6), vendor model changes and decommissioning (B.7), metrics (B.10), Internal Audit role (Section 5), agent limits and memory (Part C), staff summary (below). |

---

## Staff summary: AI at work on one page

**Always**
- Use approved AI tools with your work account.
- Classify the whole interaction before you start: what you type, what you paste, what you attach. A question can be confidential on its own.
- Check AI output before you rely on it. The more it matters, the harder you check.
- Tell people when they are dealing with AI, and label realistic AI images, audio and video.
- Report AI mistakes, leaks or strange agent behaviour within 24 hours. Reporting quickly protects you.
- Use only approved AI notetakers, and tell everyone in the meeting at the start.

**Ask first** (submit the AI intake form)
- AI that helps decide anything about a person: hiring, performance, credit, insurance, healthcare, benefits.
- Customer-facing chatbots, and content published under the organization's name.
- AI images, audio or video of a real person.
- Agents that send, pay, delete or change things.
- Health, biometric, children's, ID-number or payment data, or other sensitive personal data, in any AI tool.
- A new AI tool, plugin or connector.
- A notetaker in a meeting with lawyers, HR casework, a board executive session or an undisclosed deal.

**Never**
- Put passwords, API keys or other secrets into any AI tool.
- Put anything except public information into an unapproved or personal AI account.
- Create intimate imagery of a real person, or fake reviews, records or identities.
- Let AI make a decision about a person with no real human review.
- Use AI to get around security controls.

Questions: [AI governance contact]. Full rules: Parts A to D below.

---

# Part A: Policy

*Approved by the Executive Committee. Changes to Part A need Executive Committee approval.*

## 1. Purpose

**1.1** This policy sets the rules for how everyone working for the organization uses artificial intelligence. It aims to make AI easy to use for legitimate work while keeping the organization within the law, protecting the people affected by its decisions, and protecting client and company data.

**1.2** Where this policy and local law differ, the stricter requirement applies.

## 2. Scope

**2.1** People: employees, contractors, temporary staff, interns, and third parties acting on the organization's behalf.

**2.2** Systems: standalone AI tools, AI features inside other software, AI agents, self-hosted and open-weight models, and AI browser extensions, plugins and connectors, on any device where work data or work accounts are involved.

**2.3** On personal devices, AI may be used with non-public work data only through approved apps running in a managed work profile. Otherwise, personal devices may be used with public information only.

**2.4** Activities: any use of AI for work, including research, drafting, analysis, coding, meetings, customer interactions, decisions about people and automated actions.

**2.5** Building AI products for sale is governed by the AI Development and Risk Management Policy. This policy still applies to the AI tools staff use while doing that work.

## 3. Principles

**3.1** Human accountability: a named person answers for every AI output used and every AI-assisted decision made.

**3.2** Lawful and fair: AI is not used in ways that break the law or treat people unfairly, including through proxies for protected characteristics.

**3.3** Transparent: people know when AI plays a significant part in content they receive or decisions about them.

**3.4** Private and confidential: data goes into AI tools only when the data rules in Section 7 allow it.

**3.5** Secure: AI tools and agents are treated as part of the attack surface.

**3.6** Proportionate: controls scale with risk, so low-risk use stays quick and simple.

## 4. Definitions

| Term | Meaning in this policy |
|---|---|
| AI system | Software that infers from inputs how to generate outputs such as text, images, predictions, recommendations or decisions. |
| AI agent | An AI system that can take actions in other systems, such as sending, buying, editing, deleting or calling tools, with limited step-by-step human direction. |
| Tier A, B, C tool | Tool tiers defined in the AI Use Standard (B.1). Tier C means anything not assessed, including personal accounts. |
| Consequential decision | A decision with legal or similarly significant effect on a person: employment, credit, insurance, housing, education, healthcare, or access to essential or public services. |
| Synthetic media | AI-generated or AI-altered images, audio or video that could be mistaken for real. |
| Irreversible action | An action the organization cannot undo promptly on its own. This includes payments, even where a refund or chargeback might later be possible, because recovery depends on someone else. It also includes deletion without a tested backup, messages sent outside the organization, commitments to third parties, and production changes without a tested rollback. |
| Data classes | Public, Internal, Confidential, Restricted (sensitive personal data, as listed in 7.4), and Secrets (passwords, keys, tokens, private keys). Defined in the Data Classification Standard. |

## 5. Roles and responsibilities

| Role | Responsible for |
|---|---|
| Executive Committee | Approves Part A and the organization's AI risk appetite; receives the AI risk report twice a year. |
| Executive sponsor | Accountable for the AI governance program; accepts residual risk on exceptions; decides disagreements about risk appetite. |
| AI Governance Committee | Owns Parts B to D; approves uses under Section 8, and may delegate approval of Low and Medium uses in writing; approves Tier A status for tools that will hold Restricted data; reviews incidents and metrics quarterly. |
| Head of AI Governance | Policy owner; runs the AI register, intake and metrics. |
| IT and Security | Assesses tools and assigns their tier against the criteria in B.1; runs SSO, DLP, logging, agent identities and kill switches. |
| Legal and Privacy | Interprets the law; leads impact assessments involving personal data. Legal's view of what the law requires is binding on the Committee. |
| Internal Audit | Gives independent assurance, at least yearly, that this policy and its standards are followed and work as intended. |
| Use-case owner | Answers for a specific AI use and its outcomes; names the human reviewer. |
| Every user | Follows the data rules, checks outputs, reports problems. |

## 6. Prohibited uses

*These apply everywhere, with no approval route and no exceptions.*

**6.1** Any practice prohibited by Article 5 of the EU AI Act (Regulation (EU) 2024/1689, as amended), wherever in the world it takes place. The legal text and its stated exclusions govern this clause. Examples include manipulative or deceptive techniques that cause significant harm, social scoring, predicting criminal offending from profiling alone, untargeted scraping of facial images, emotion recognition in the workplace or education, and biometric categorisation to infer sensitive traits.

**6.2** Creating or altering sexual or intimate imagery of a real person, or any child sexual abuse material.

**6.3** Typing, pasting or uploading passwords, API keys, tokens, private keys or other secrets into any AI tool. AI tools are configured so that secret files are kept out of their context, and agents get credentials only as set out in the AI Agent Standard (C.1). Accidental exposure of a secret to an AI tool is an incident under Section 15: report it and rotate the secret.

**6.4** Using AI to deceive: impersonating a real person, fabricating records, evidence, reviews or testimonials, or hiding AI involvement where disclosure is required.

**6.5** Using AI to bypass security controls, gain unauthorized access, or create malicious code.

**6.6** Making a consequential decision about a person based solely on AI output, without meaningful human review.

**6.7** Putting anything other than public information into a Tier C tool.

**6.8** Uploading client data to any AI service, or using it to train or fine-tune a model, where the client contract does not allow it.

## 7. Data rules

**7.1** The data class decides which tools may be used:

| Data class | Tier A | Tier B | Tier C |
|---|---|---|---|
| Public | Yes | Yes | Yes |
| Internal | Yes | Yes | No |
| Confidential | Yes | No | No |
| Restricted | Approved use case only | No | No |
| Secrets | Never | Never | Never |

**7.2** Classification covers the whole interaction: the prompt, any context the tool can see, and any attached files. The highest class present decides the tool. A prompt can be confidential even when no confidential document is attached.

**7.3** Personal data goes into an AI tool only with a lawful basis, for a compatible purpose, and in the minimum amount needed. De-identified data is preferred.

**7.4** Restricted means sensitive personal data: health, genetic and biometric data; data revealing racial or ethnic origin, religious or political beliefs, trade union membership, or sex life or sexual orientation; children's data; criminal records; government ID numbers; and payment card and financial-account numbers.

**7.5** Other personal data is Internal or Confidential under the Data Classification Standard. A colleague's name or work email in a document does not make it Restricted. HR files, performance records and bulk personal data such as customer lists are at least Confidential. HR records that contain health data, such as sick-leave notes or medical accommodations, stay Restricted under 7.4. 7.3 still applies to all personal data.

**7.6** Client data follows the client contract. If the contract is silent, it is Confidential and is never used to train or fine-tune a model.

## 8. Uses that need approval

*Each needs a registered use case, an impact assessment sized using the risk rubric in B.3, a named human reviewer, and logging.*

**8.1** Consequential decisions about people: hiring, promotion, performance, termination, credit, insurance pricing or claims, housing, education, healthcare, or public benefits.

**8.2** Customer-facing or public-facing AI, such as chatbots and voice agents.

**8.3** Publishing AI-generated content externally under the organization's name.

**8.4** Synthetic images, audio or video of a real, identifiable person. Written consent and an AI label are required.

**8.5** AI agents with rights to write, send, pay, delete, or communicate externally.

**8.6** Processing Restricted data in a Tier A tool.

**8.7** Using AI to monitor or evaluate employees.

**8.8** AI in safety-critical, clinical or physical operations, and any use that relies on an exclusion in Article 5 (for example emotion recognition for medical or safety reasons). Sector rules apply as well.

**8.9** Connecting AI tools to new internal systems or data sources through plugins, connectors, MCP servers or APIs.

**8.10** Everything else, such as drafting, summarizing, translating, research, analysis and coding help, is permitted in approved tools within the data rules, with the user checking the output under Section 9.

**8.11** AI meeting notetakers and transcription are permitted only through approved tools and under the rules in B.6.

## 9. Human oversight and responsibility for outputs

**9.1** The person who uses AI owns the result, as if they had produced it themselves.

**9.2** Checking scales with use. Facts, figures, citations, and legal, financial, medical or technical claims are verified against a reliable source before they appear in external content, legal or financial documents, or any decision. Internal drafts get a reasonable review by the person who sends them.

**9.3** AI-written code goes through the same review, testing, security scanning and licence checks as any other code.

**9.4** For consequential decisions, the reviewer has the authority and competence to overrule the AI, sees the main factors behind its output, and records the decision.

**9.5** People affected by a consequential decision can ask for human review, get a plain-language explanation, and contest the outcome.

**9.6** Reviewers get the time and information to disagree. Override rates are monitored; a sign-off rate near 100% triggers a review of the process.

## 10. Transparency and disclosure

**10.1** People are told when they are dealing with an AI system, unless that is obvious.

**10.2** Where local law is stricter, it applies. Otherwise the organization's default is:
- Realistic synthetic images, audio and video are always labelled as AI-generated.
- Text generated by AI and published without human editorial review is disclosed as AI-generated.
- AI-assisted content that a named person has reviewed and takes editorial responsibility for needs no label, unless a contract, law or platform rule requires one.

**10.3** Candidates, employees and customers are told before AI materially influences a consequential decision about them, and receive a plain-language explanation after an adverse outcome.

**10.4** AI use is disclosed to clients where contracts or professional rules require it. Marketing never overstates what an AI product can do.

## 11. AI agents

**11.1** Every agent is registered in the AI register with a named human owner.

**11.2** Each agent has its own identity and the least privilege its task needs. It never runs on a person's full credentials.

**11.3** Agents are read-only by default. Actions that move money, delete, send externally, change records or change production systems need human approval for each action, or a pre-approved scope within the limits set in C.2. Irreversible actions (defined in Section 4) need human approval for each action, with two exceptions. Each applies only where the AI Governance Committee has accepted that risk for the use case: (a) payments within the per-action and daily caps, to payees on the allowlist; and (b) messages sent outside the organization to recipients on the allowlist, within the rate limits. Both are set in C.2. Part C may tighten these exceptions but never widen them.

**11.4** Anything an agent reads (emails, documents, web pages, tool outputs) is untrusted data, never an instruction.

**11.5** All agent actions are logged in a form audit can review.

**11.6** Every agent has a tested kill switch and a way to roll back its actions.

**11.7** Agent memory that persists between tasks is a data store under Section 7 and the rules in C.4.

**11.8** Agents are rolled out in stages and monitored. Users are told what the agent can do and who to contact when it misbehaves.

**11.9** Connecting agents to each other, or to new tools, is a new use case and goes through approval.

## 12. Intellectual property

**12.1** Third-party material (licensed reports, paywalled content, client IP) goes into an AI tool only where the licence allows it.

**12.2** Before external use, outputs are checked for close copies of protected material, third-party trademarks, and open-source code under incompatible licences.

**12.3** Material generated by AI alone may not be protected by copyright. Where ownership matters, such as brand assets or product code, meaningful human authorship is kept and recorded.

## 13. Third parties and procurement

**13.1** Every AI tool, model or AI feature in purchased software is reviewed before it touches non-public data.

**13.2** Contracts cover: no training on our data without consent, retention and deletion, data location, sub-processors, incident notice, advance notice of model and feature changes, audit rights and IP terms.

**13.3** At renewal, existing vendors are asked about new AI features. Admins keep new AI features switched off until reviewed.

**13.4** The organization remains accountable for outcomes produced by vendor AI.

**13.5** Changes to a vendor's model or AI features trigger re-validation, and retired AI tools are decommissioned, as set out in B.7.

## 14. Approval and the AI register

**14.1** New tools and uses under Section 8 are requested through the AI intake form.

**14.2** Requests are triaged as Standard (security review), Approval (a Section 8 use, decided under 5 and B.3) or Prohibited (declined). Service targets for each route are set in B.4, published to staff, and reported with the metrics in B.10.

**14.3** Approved uses are recorded in the AI register with owner, purpose, data, tool, risk level, reviewer and next review date.

**14.4** Each registered use is reviewed on the cycle its risk level sets in B.3.

## 15. Incidents

**15.1** Report within 24 hours of noticing: data put into the wrong tool; a secret exposed to an AI tool; harmful, biased or false output used in a decision or sent outside; an agent acting outside its scope; suspected prompt injection; or a deepfake targeting the organization or its people.

**15.2** A report made within 24 hours is treated as learning, not discipline, unless the prohibited use was deliberate.

**15.3** Legal and Privacy decide on regulatory notification, such as personal-data breach reporting. Incidents feed the quarterly standards review.

## 16. Training and AI literacy

**16.1** Everyone completes baseline training before getting access to AI tools, refreshed yearly.

**16.2** Role add-ons: developers and agent builders; reviewers of consequential decisions (HR, lending, underwriting, clinical); managers who approve use cases; marketing and communications.

**16.3** Training records are kept by role.

## 17. Monitoring and enforcement

**17.1** AI use is monitored through approved means such as SSO, DLP and logs, only to enforce this policy, in line with privacy and employment law. Staff are told what is monitored.

**17.2** Consequences are graduated. Accidental breaches reported under 15.2 are handled as learning, and so is a first breach that monitoring finds and the person did not know they had made. Repeated careless breaches lead to coaching and then a formal warning. Deliberate prohibited use, or concealing a breach (including failing to report one you know about), goes through the standard disciplinary process.

**17.3** Managers are responsible for their team's compliance.

## 18. Exceptions, review and related documents

**18.1** Exceptions are written, time-limited as set in B.8, risk-accepted by the executive sponsor and logged. There are no exceptions to Section 6.

**18.2** Part A is reviewed yearly and Parts B to D quarterly, with an out-of-cycle review within 30 days of a material legal change or serious incident.

**18.3** Related documents: AI Use Standard (Part B), AI Agent Standard (Part C), Sector Annexes (Part D), Data Classification Standard, Information Security Policy, Mobile Device and BYOD Policy, Privacy Policy, Records Retention Schedule, AI Development and Risk Management Policy, Third-Party Risk Policy, Code of Conduct.

---

# Part B: AI Use Standard

*Owned by the AI Governance Committee. Reviewed quarterly. Implements Part A.*

## B.1 Tool tiers

**B.1.1** IT and Security assess each tool and assign its tier against the criteria below. Tier A for any tool that will hold Restricted data also needs AI Governance Committee approval.

**B.1.2** Vendor-hosted tools reach Tier A only with all of: an enterprise contract; no training on our inputs; defined retention and deletion; stated data location; SSO; audit logs; a sub-processor list; security-incident notice; and advance notice of model changes. Tier B tools are vetted but miss one or more of these.

**B.1.3** Self-hosted and open-weight models reach Tier A only with all of:
- A model from an approved source, with its integrity checked (hash or signature).
- A licence that permits the intended commercial use.
- Hosting on organizational servers or the organization's cloud tenancy. Those are the only hosts eligible for Tier A. A model on a managed company laptop is Tier B at most. A model on a personal or unmanaged device may be used with public data only (2.3).
- No outbound data or telemetry from the model environment.
- Access control tied to SSO, and logging of use.
- A named owner responsible for patching and updates.
- An evaluation showing the model is fit for its intended use, including basic safety and prompt-injection testing.

Self-hosting removes vendor risk but adds supply-chain, patching and safety-tuning risk. It is not automatically safer.

## B.2 Classifying data for AI use

**B.2.1** Classify the whole interaction (7.2): prompt, context, attachments, and anything the tool can read through connectors.

**B.2.2** AI output inherits the highest class of its inputs until someone reclassifies it.

**B.2.3** For AI use, the identity of a client and any non-public information about a client are Confidential. If the Data Classification Standard says otherwise, align it with this rule rather than patching individual tools.

## B.3 Risk rubric for registered uses

| Factor | Low | Medium | High |
|---|---|---|---|
| Effect on people | None or trivial | Indirect or reversible | Consequential decision (8.1) or physical safety |
| Data | Public or Internal | Confidential | Restricted |
| Autonomy | Human acts on every output | Human approves in batches | Agent acts within a pre-approved scope |
| Audience | Internal only | Clients or partners | Public or customers at scale |
| Reversibility | Easily undone | Undone with effort | Hard or impossible to undo |

The highest factor sets the level.

| Level | Assessment | Default approver | Review cycle |
|---|---|---|---|
| Low | Intake form only | IT and Security | At the tool's yearly review |
| Medium | Short impact assessment | Head of AI Governance | Yearly |
| High | Full impact assessment, testing for bias and failure modes, named reviewer | AI Governance Committee | Every 6 months, and after any change under B.7 |

The level sets how deep the assessment goes. For new tools and other uses outside Section 8, the default approver applies. Uses under Section 8 are approved by the AI Governance Committee at every level, unless the Committee has delegated Low or Medium approvals in writing; any delegation is recorded in the AI register.

## B.4 Service targets

| Step | Target |
|---|---|
| Triage of any request | 2 working days |
| Standard route (security review) | 10 working days |
| Approval route (Section 8 uses) | 20 working days |

Median performance against these targets is reported monthly.

## B.5 Configuring AI tools

**B.5.1** Coding assistants and other tools that read files are configured to exclude secret files (such as `.env` files, key stores and credential files) from their context.

**B.5.2** Repositories used with AI tools have secret scanning before every commit. A secret found in a repository is an incident in its own right.

**B.5.3** New AI features in approved software stay off until reviewed (13.3).

## B.6 AI meeting notetakers and transcription

**B.6.1** Only approved notetaker tools may join or record meetings. Personal notetaker bots are Tier C.

**B.6.2** The host announces recording and AI notes at the start, and includes notice in the invite for external participants. Where local law requires every participant's consent, the host gets it before recording; anyone who objects is respected, and the notetaker is switched off.

**B.6.3** Notetakers are not used, unless the Committee approves a specific case, in: meetings with legal counsel; HR disciplinary, grievance or medical discussions; board executive sessions; or meetings about undisclosed transactions.

**B.6.4** Transcripts and summaries take the data class of the meeting. The host reviews the summary before it is shared.

**B.6.5** Recordings and transcripts are deleted after 90 days unless the Records Retention Schedule requires longer or a legal hold applies (B.9).

## B.7 Vendor model changes and decommissioning

**B.7.1** Any of the following triggers re-validation of the registered uses that depend on the tool:
- A new model version, or a model change announced or detected.
- A new AI feature, data source or connector.
- A change in hosting location, sub-processors or contract terms.
- Performance or error rates moving beyond the limits set at approval.
- An incident involving the tool.

**B.7.2** For High-risk uses, model versions are pinned where the vendor allows it, and a regression test runs before switching versions.

**B.7.3** Decommissioning a tool or use: revoke access and credentials; have the vendor delete or return data as the contract requires and confirm it in writing; archive records and logs under the Records Retention Schedule; clear agent memory, subject to any legal hold (B.9); update the AI register; and tell affected users.

## B.8 Exceptions

Exceptions last at most 90 days and can be renewed once. Each has compensating controls, an owner and an end date in the register.

## B.9 Records

AI register entries, impact assessments, approvals and logs are kept under the Records Retention Schedule. Records of consequential decisions are kept for at least 4 years, or longer where local law requires. Legal confirms the period for each jurisdiction.

A legal hold issued by Legal overrides every deletion and retention limit in Parts B and C, including B.6.5, B.7.3 and C.4.2, until Legal lifts it.

## B.10 Metrics

Reported quarterly to the AI Governance Committee and twice a year to the Executive Committee.

| Metric | What it tells you |
|---|---|
| Register coverage: share of detected AI tools and uses that are registered | How much AI use governance can actually see |
| Shadow AI detections per month, and trend | Whether approved tools meet real demand |
| Median approval time against B.4 targets | Whether the approved route is faster than the workaround |
| Median time from incident to report, and share self-reported | Whether the no-blame rule works |
| Reviewer override rate per 8.1 use | Whether human oversight is real (9.6) |
| Training completion by role | Evidence of AI literacy measures |
| Open exceptions and overdue reviews | Whether controls are slipping |

---

# Part C: AI Agent Standard

*Owned by the AI Governance Committee. Reviewed quarterly. These rules are interim: they follow Singapore's Model AI Governance Framework for Agentic AI and the OWASP Top 10 for Agentic Applications, and will be revised when NIST publishes its agent control overlays.*

## C.1 Identity and credentials

**C.1.1** Each agent runs under its own service identity.

**C.1.2** Agents get credentials only from the approved secrets manager, as short-lived tokens scoped to the task. Credentials never appear in prompts, agent memory or logs.

## C.2 Action limits

Each agent's register entry sets its limits. As a minimum:

| Limit | Rule |
|---|---|
| Spend | Payments without per-action approval only where the Committee has accepted the risk (11.3), within a cap per action and per day, and only to allowlisted payees. Anything above the cap, or to a payee not on the allowlist, needs human approval. Adding a payee to the allowlist needs human approval, is logged, and is never done by an agent. |
| Rate | A maximum number of actions per hour, with alerts when it is reached. |
| Recipients | Messages go outside the organization without per-action approval only where the Committee has accepted the risk (11.3), within the rate limit, and only to allowlisted domains or addresses. A message to anyone not on the allowlist needs human approval. Adding a recipient to the allowlist needs human approval, is logged, and is never done by an agent. |
| Data scope | An allowlist of systems and data the agent can read or write. |
| Tools | An allowlist of tools and connectors. |
| Irreversible actions | Deletion, any payment outside the in-cap allowance, any external message outside the recipient allowance, commitments to third parties, and production changes always need human approval for each action. |

## C.3 Untrusted content

Content an agent reads is data, not instructions (11.4). Agents that read external content (email, web, shared documents) are tested for prompt injection before release and after each significant change.

## C.4 Memory and persistence

**C.4.1** Persistent agent memory follows the data rules in Section 7. It never holds Secrets, and holds Restricted data only where the approved use case allows it.

**C.4.2** The owner can inspect and purge an agent's memory. Memory older than the retention period set at approval is deleted automatically, unless a legal hold applies (B.9).

**C.4.3** Memory is cleared when an agent is decommissioned (B.7.3).

## C.5 Monitoring and kill switch

**C.5.1** Agent actions are logged with enough detail to reconstruct what happened and why.

**C.5.2** Kill switches are tested before release and at least every quarter.

**C.5.3** Alerts fire on unusual volume, new destinations, repeated failures or limit breaches.

## C.6 Multi-agent systems and rollout

**C.6.1** Agents connected to other agents are assessed as one system. Each agent's limits apply on its own; no agent gains rights through another.

**C.6.2** Rollout is staged: a pilot with named users, then wider release after the owner reviews logs and incidents.

---

# Part D: Sector annexes

*Owned by the AI Governance Committee. Apply the annexes relevant to your organization on top of Parts A to C.*

## D.1 Financial services

**FS.1** Credit, underwriting, collections and fraud decisions are uses under 8.1 and also fall under model risk management: inventory, independent validation and ongoing monitoring, following the frameworks your supervisors use (for example the US Revised Guidance on Model Risk Management of April 2026, PRA SS1/23 in the UK, and the MAS Guidelines on AI Risk Management in Singapore). Generative and agentic AI, which the 2026 US guidance leaves out of scope, are governed through Sections 8 and 11 and Part C.

**FS.2** The board approves the AI policy and receives the AI inventory and AI risk report at least twice a year.

**FS.3** AI-generated investment or product advice to retail customers is reviewed by a licensed person before it is given, and suitability rules still apply.

**FS.4** Trading or market-facing AI has human supervision and a tested kill switch.

**FS.5** Customers get a specific, plain-language reason for AI-influenced adverse credit decisions.

**FS.6** Concentration on single AI and cloud providers is assessed under third-party risk.

## D.2 Insurance

**INS.1** Underwriting, pricing and claims decisions are uses under 8.1, tested for unfair discrimination (including proxies) before and after deployment.

**INS.2** A written AI systems program covering selection, validation, monitoring and retirement is kept ready for regulators.

**INS.3** AI-recommended claim denials are confirmed by a qualified person before notice is sent.

**INS.4** Vendor models come with documentation and testing rights; the insurer stays accountable.

## D.3 Healthcare and life sciences

**HC.1** Patient health information is Restricted and goes only into tools covered by a business associate agreement (US) or an equivalent data processing agreement.

**HC.2** Clinical decision support and diagnostic AI are governed by clinical governance and, where they qualify, medical device rules. This policy alone is not enough to approve them.

**HC.3** AI scribes and summaries are checked by the clinician before anything enters the record. Patients are told when an AI scribe is used.

**HC.4** General-purpose AI does not give patients medical advice.

**HC.5** Research use of patient data needs ethics approval in addition to an approved use case.

## D.4 Public sector

**PS.1** Any AI in eligibility, benefits, enforcement, licensing or immigration is a use under 8.1, with a public impact assessment and an entry in the public algorithm register where one exists.

**PS.2** Citizens always have a human review and appeal route.

**PS.3** Contracts bar vendors from training on non-public government data without explicit consent.

**PS.4** Citizen-facing chatbots disclose that they are AI and hand over to a person on request.

## D.5 Retail and consumer

**RC.1** Legal reviews every marketing claim about AI capability before publication.

**RC.2** Synthetic media is labelled; any real person's likeness needs written consent.

**RC.3** No AI-generated reviews, testimonials or personas posing as customers (restates 6.4).

**RC.4** Personalization and dynamic pricing are reviewed so they do not exploit vulnerable customers or discriminate.

**RC.5** Customer chatbots disclose they are AI and offer a person on request.

## D.6 Technology and software

**TS.1** Proprietary code goes only into Tier A coding assistants, configured under B.5.

**TS.2** AI-suggested code is scanned for licence conflicts before merge.

**TS.3** Agents in build and deployment pipelines use separate credentials and never write to production without approval.

**TS.4** Open-weight models meet B.1.3 before use with non-public data.

**TS.5** AI features built for customers follow the AI Development Policy, including OWASP LLM and agentic controls.

## D.7 Employment and HR (applies in every sector)

**HR.1** AI in recruiting, promotion, performance, scheduling or termination is a use under 8.1, with anti-bias testing before and after deployment.

**HR.2** Candidates and employees are notified before AI is used; independent bias audits run yearly where the law requires them.

**HR.3** AI decision records are kept for at least 4 years, or longer where local law requires. Legal confirms the period for each jurisdiction.

**HR.4** Vendor contracts give access to audit data; vendors are treated as acting for the employer.

**HR.5** AI assessments offer reasonable accommodation and never function as a medical inquiry.

## D.8 Education

**ED.1** AI in admissions, grading, placement or proctoring is a use under 8.1.

**ED.2** Student records go only into tools with education privacy terms.

**ED.3** Permitted AI use in assessed work is stated in advance and must be disclosed by students.

**ED.4** Tools used by minors have age-appropriate safeguards and no emotion recognition (restates 6.1).

---

*Model policy. Adapt with your legal counsel before adoption. Regulatory status checked 22 Oct 2026.*
