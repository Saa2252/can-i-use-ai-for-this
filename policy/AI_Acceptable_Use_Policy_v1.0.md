# AI Acceptable Use Policy

**Policy ID:** AIG-POL-001  
**Version:** 1.0 (model policy)  
**Status:** Ready to adapt and approve  
**Owner:** Head of AI Governance  
**Approver:** Executive Committee  
**Review:** Policy yearly; standards quarterly  
**As of:** 22 Oct 2026  
**Prepared by:** Your Name, AI Governance Lead

## 1. Purpose

**1.1** This policy sets the rules for how everyone working for the organization uses artificial intelligence. It aims to make AI easy to use for legitimate work while keeping the organization within the law, protecting the people affected by its decisions, and protecting client and company data.  

**1.2** Where this policy and local law differ, the stricter requirement applies.  


## 2. Scope

**2.1** People: employees, contractors, temporary staff, interns, and third parties acting on the organization's behalf.  

**2.2** Systems: standalone AI tools, AI features inside other software, AI agents, open-weight or locally run models, and AI browser extensions or plugins, on company or personal devices when used for work.  

**2.3** Activities: any use of AI for work, including research, drafting, analysis, coding, customer interactions, decisions about people and automated actions.  

**2.4** Building AI products for sale is governed by the AI Development and Risk Management Policy. This policy still applies to the AI tools staff use while doing that work.  


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
| Tier A tool | Enterprise approved: contract in place, SSO, no training on our inputs, defined retention, audit logs. |
| Tier B tool | Limited approval: vetted, but with weaker contractual or technical controls. |
| Tier C tool | Anything not assessed, including personal accounts. This is shadow AI. |
| Consequential decision | A decision with legal or similarly significant effect on a person: employment, credit, insurance, housing, education, healthcare, or access to essential or public services. |
| Synthetic media | AI-generated or AI-altered images, audio or video that could be mistaken for real. |
| Data classes | Public, Internal, Confidential, Restricted (personal, health, payment and other special-category data), and Secrets (passwords, keys, tokens). |

## 5. Roles and responsibilities


| Role | Responsible for |
|---|---|
| Board or Executive Committee | Approves this policy and the organization's AI risk appetite; receives a twice-yearly AI risk report. |
| Executive sponsor | Accountable for the AI governance program; accepts residual risk on exceptions. |
| AI Governance Committee | Owns the standards; approves restricted use cases; reviews incidents quarterly. |
| Head of AI Governance | Policy owner; runs the AI register, intake and metrics. |
| IT and Security | Vets tools; runs SSO, DLP, logging, agent identities and kill switches. |
| Legal and Privacy | Interprets law; leads impact assessments involving personal data. |
| Use-case owner | Answers for a specific AI use and its outcomes; names the human reviewer. |
| Every user | Follows the data rules, checks outputs, reports problems. |

## 6. Prohibited uses

_These apply everywhere, with no exceptions and no approval route._

**6.1** Any practice prohibited by Article 5 of the EU AI Act, wherever it takes place. This includes manipulative or deceptive techniques that cause significant harm; exploiting vulnerabilities linked to age, disability or social or economic situation; social scoring; predicting criminal offending from profiling alone; untargeted scraping of facial images; emotion recognition of employees or students; and biometric categorisation to infer sensitive traits.  

**6.2** Creating or altering sexual or intimate imagery of a real person, or any child sexual abuse material.  

**6.3** Entering passwords, API keys, tokens, private keys or other secrets into any AI tool.  

**6.4** Using AI to deceive: impersonating a real person, fabricating records, evidence, reviews or testimonials, or hiding AI involvement where disclosure is required.  

**6.5** Using AI to bypass security controls, gain unauthorized access, or create malicious code.  

**6.6** Making a consequential decision about a person based solely on AI output, without meaningful human review.  

**6.7** Putting anything other than public data into a Tier C (unapproved) tool.  

**6.8** Uploading client data to any AI service, or using it to train or fine-tune a model, where the client contract does not allow it.  


## 7. Data rules

**7.1** The data class decides which tools may be used, as set out in the table below.  

**7.2** Personal data goes into an AI tool only with a lawful basis, for a compatible purpose, and in the minimum amount needed. De-identified data is preferred.  

**7.3** Health, biometric, children's, financial-account and other special-category data are Restricted.  

**7.4** Client data follows the client contract. If the contract is silent, it is Confidential and is never used to train or fine-tune a model.  

**7.5** A tool reaches Tier A only with: an enterprise contract, no training on our inputs, defined retention and deletion, stated data location, SSO, audit logs, a sub-processor list, and security-incident notice.  


| Data class | Tier A | Tier B | Tier C |
|---|---|---|---|
| Public | Yes | Yes | Yes |
| Internal | Yes | Yes, no client names | No |
| Confidential | Yes | No | No |
| Restricted | Approved use case only | No | No |
| Secrets | Never | Never | Never |

## 8. Restricted uses (approval required)

_Each needs a registered use case, an impact assessment sized to the risk, a named human reviewer and logging._

**8.1** R1. Consequential decisions about people: hiring, promotion, performance, termination, credit, insurance pricing or claims, housing, education, healthcare, or public benefits.  

**8.2** R2. Customer-facing or public-facing AI, such as chatbots and voice agents.  

**8.3** R3. Publishing AI-generated content externally under the organization's name.  

**8.4** R4. Synthetic images, audio or video of a real, identifiable person. Written consent and an AI label are required.  

**8.5** R5. AI agents with rights to write, send, pay, delete, or communicate externally.  

**8.6** R6. Processing Restricted data in a Tier A tool.  

**8.7** R7. Using AI to monitor or evaluate employees.  

**8.8** R8. AI in safety-critical, clinical or physical operations, in addition to sector rules.  

**8.9** R9. Connecting AI tools to new internal systems or data sources through plugins, connectors, MCP servers or APIs.  

**8.10** Everything else, such as drafting, summarizing, translating, research, analysis and coding help, is permitted in approved tools within the data rules, with the user checking the output.  


## 9. Human oversight and responsibility for outputs

**9.1** The person who uses AI owns the result, as if they had produced it themselves.  

**9.2** Facts, figures, citations, and legal, financial or medical statements are checked against a reliable source before anyone relies on them.  

**9.3** AI-written code goes through the same review, testing, security scanning and licence checks as any other code.  

**9.4** For consequential decisions, the reviewer has the authority and competence to overrule the AI, sees the main factors behind its output, and records the decision.  

**9.5** People affected by a consequential decision can ask for human review, get a plain-language explanation, and contest the outcome.  

**9.6** Reviewers get the time and information to disagree. Override rates are monitored; a sign-off rate near 100% triggers a review of the process.  


## 10. Transparency and disclosure

**10.1** People are told when they are dealing with an AI system, unless that is obvious.  

**10.2** Synthetic media is labelled as AI-generated, and AI-generated text published to inform the public on matters of public interest is disclosed, in line with local law.  

**10.3** Candidates, employees and customers are told before AI materially influences a consequential decision about them, and receive a plain-language explanation after an adverse outcome.  

**10.4** AI use is disclosed to clients where contracts or professional rules require it. Marketing never overstates what an AI product can do.  


## 11. AI agents

**11.1** Every agent is registered in the AI register with a named human owner.  

**11.2** Each agent has its own identity and the least privilege its task needs. It never runs on a person's full credentials.  

**11.3** Agents are read-only by default. Paying, deleting, sending external messages, changing records or changing production systems needs approval for each action, or a pre-approved scope with limits.  

**11.4** Anything an agent reads (emails, documents, web pages, tool outputs) is untrusted data, never an instruction.  

**11.5** All agent actions are logged in a form audit can review.  

**11.6** Every agent has a tested kill switch and a way to roll back its actions.  

**11.7** Agents are rolled out in stages and monitored. Users are told what the agent can do and who to contact when it misbehaves.  

**11.8** Connecting agents to each other, or to new tools, is a new use case and goes through approval.  


## 12. Intellectual property

**12.1** Third-party material (licensed reports, paywalled content, client IP) goes into an AI tool only where the licence allows it.  

**12.2** Before external use, outputs are checked for close copies of protected material, third-party trademarks, and open-source code under incompatible licences.  

**12.3** Material generated by AI alone may not be protected by copyright. Where ownership matters, such as brand assets or product code, meaningful human authorship is kept and recorded.  


## 13. Third parties and procurement

**13.1** Every AI tool, model or AI feature in purchased software is reviewed before it touches non-public data.  

**13.2** Contracts cover: no training on our data without consent, retention and deletion, data location, sub-processors, incident notice, advance notice of new AI features, audit rights and IP terms.  

**13.3** At renewal, existing vendors are asked about new AI features. Admins keep new AI features switched off until reviewed.  

**13.4** The organization remains accountable for outcomes produced by vendor AI.  


## 14. Approval and the AI register

**14.1** New tools and restricted uses are requested through the AI intake form.  

**14.2** Requests are triaged within 2 working days as Standard (security review, target 10 working days), Restricted (committee review, target 20 working days) or Prohibited (declined).  

**14.3** Approved uses are recorded in the AI register with owner, purpose, data, tool, risk tier, reviewer and next review date.  

**14.4** Each registered use is reviewed at least yearly; restricted uses at least every 6 months.  


## 15. Incidents

**15.1** Report within 24 hours: data put into the wrong tool; harmful, biased or false output used in a decision or sent outside; an agent acting outside its scope; suspected prompt injection; or a deepfake targeting the organization or its people.  

**15.2** Reports made within 24 hours are treated as learning, not discipline, unless prohibited use was deliberate.  

**15.3** Legal and Privacy decide on regulatory notification, such as personal-data breach reporting. Incidents feed the quarterly standards review.  


## 16. Training and AI literacy

**16.1** Everyone completes baseline training before getting access to AI tools, refreshed yearly.  

**16.2** Role add-ons: developers and agent builders; reviewers of consequential decisions (HR, lending, underwriting, clinical); managers who approve use cases; marketing and communications.  

**16.3** Training records are kept by role.  


## 17. Monitoring and enforcement

**17.1** AI use is monitored through approved means such as SSO, DLP and logs, only to enforce this policy, in line with privacy and employment law. Staff are told what is monitored.  

**17.2** Consequences are graduated: coaching for a first minor slip, a formal warning for repeats, and standard disciplinary process for deliberate breaches or any prohibited use.  

**17.3** Managers are responsible for their team's compliance.  


## 18. Exceptions, review and related documents

**18.1** Exceptions are written, time-limited (90 days, renewable once), risk-accepted by the executive sponsor and logged. There are no exceptions to Section 6.  

**18.2** The policy is reviewed yearly and the standards quarterly, with an out-of-cycle review within 30 days of a material legal change or serious incident.  

**18.3** Related documents: Information Security Policy, Data Classification Standard, Privacy Policy, AI Development and Risk Management Policy, Third-Party Risk Policy, Code of Conduct.  


# Sector annexes

## Annex: Financial services

**FS.1** Credit, underwriting, collections and fraud decisions are R1 uses and also fall under model risk management: inventory, independent validation and ongoing monitoring.  

**FS.2** The board approves the AI policy and receives the AI inventory and AI risk report at least twice a year.  

**FS.3** AI-generated investment or product advice to retail customers is reviewed by a licensed person before it is given, and suitability rules still apply.  

**FS.4** Trading or market-facing AI has human supervision and a tested kill switch.  

**FS.5** Customers get a specific, plain-language reason for AI-influenced adverse credit decisions.  

**FS.6** Concentration on single AI and cloud providers is assessed under third-party risk.  


## Annex: Employment and HR

**HR.1** AI in recruiting, promotion, performance, scheduling or termination is R1, with anti-bias testing before and after deployment.  

**HR.2** Candidates and employees are notified before AI is used; independent bias audits run yearly where the law requires them.  

**HR.3** AI decision records are kept for at least 4 years.  

**HR.4** Vendor contracts give access to audit data; vendors are treated as acting for the employer.  

**HR.5** AI assessments offer reasonable accommodation and never function as a medical inquiry.  


---
Model policy. Adapt with your legal counsel before adoption. Regulatory status as of 22 Oct 2026.