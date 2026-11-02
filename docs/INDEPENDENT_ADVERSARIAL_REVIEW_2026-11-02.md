# Independent Adversarial Review — Medad

**Review date:** 2026-11-02  
**Scope:** Product strategy, market position, demand, differentiation, engineering readiness, unit economics, privacy/security, legal framing, and Startup.dz application readiness.  
**Posture:** Adversarial. A capability is not proven merely because code exists or documentation describes it.

## Executive decision

**Do not submit the Startup.dz application yet. Do not position Medad as a general e-commerce operating system or as a validated B2B SaaS product.**

Medad is a real, non-trivial local software prototype with a deterministic unit-economics engine, evidence/claim logic, candidate readiness gates, a run workflow, local persistence primitives, and a substantial automated test suite. The inspected development branch has 190 commits ahead of main; its GitHub Actions run #359 completed successfully.

That establishes engineering progress. It does **not** establish product-market fit, commercial uniqueness, production readiness, customer demand, or sustainable economics.

The strongest position to test is narrower: **pre-stock commercial underwriting and partnership-risk control for Algerian COD commerce** — deciding whether a proposed product deal deserves a bounded test before capital and advertising are committed, then reconciling evidence and retained-order economics afterwards.

This wedge is still a hypothesis. It must be compared directly against existing seller platforms, spreadsheets, and the actual working practices of merchants and capital partners.

## Decision matrix

| Dimension | Assessment | Why |
|---|---|---|
| Engineering feasibility | **EXPERIMENTALLY_SUPPORTED — local prototype** | Real Python engine, structured tests, frontend verification and passing CI. |
| Production readiness | **NOT READY** | No production identity, multi-tenant isolation, connected server API, live data sources or browser E2E evidence. |
| Originality | **HYPOTHESIS / PARTIAL DIFFERENTIATION** | Evidence-gated pre-stock decisioning is plausible; broad COD analytics and commerce operations already have competitors. |
| Customer problem | **HYPOTHESIS** | Logical problem statement, but no primary customer research or quantified pain evidence is in the repo. |
| Real demand | **UNKNOWN** | No Medad customer cohort, paying pilot, signed partner, revenue or repeated usage evidence was found in the inspected material. |
| Product economic viability | **UNKNOWN** | Merchant-side unit economics exist; Medad’s own payer, price, acquisition cost, support cost, gross margin and retention model do not. |
| Application readiness | **NOT READY** | Missing economic-growth evidence, founder/team qualifications and actual prototype photo; custom deck is not the official portal template. |
| Legal/privacy readiness | **NOT READY FOR REAL CUSTOMER DATA** | Role allocation, processing register, operational logbook, data hosting/transfer and security controls remain to be implemented and reviewed. |

## 1. Repository identity and engineering evidence

### Observed source state

- Repository: Loofy147/Medad.
- Default branch: main.
- Technical frontier inspected: feat/medad-commerce-os-foundation.
- Branch comparison: **190 commits ahead, 0 behind** relative to main at the time checked. The technical frontier remains non-default and unmerged.
- The application dossier branch is based on that development branch. It is not evidence that the implementation has been merged into main.

### Positive engineering evidence

The inspected branch contains:
- A local Arabic RTL interface in index.html.
- A deterministic Python unit-economics model.
- Evidence and claim assessment logic.
- Candidate readiness gates.
- Sensitivity analysis.
- A workflow producing a structured decision packet.
- Local SQLite persistence and local artifact-reference/storage primitives.
- Instant event generation from an evaluated snapshot.
- Eight test files containing **118 test_* methods** across engine, methodology, store, workflow, CLI, task-contract, journal and artifact-store behavior.
- GitHub Actions run **#359** for the dossier head completed with success. Both “Run deterministic engine tests” and “Verify UI syntax and evidence snapshot” completed successfully.

**What this proves:** the tested local contracts and frontend verification passed for that source revision.

**What it does not prove:** browser-level end-to-end behavior, real user outcomes, multi-tenant security, production deployment, carrier/supplier connections, data authenticity, or commercial demand. The tests are engineering evidence, not market validation.

### Production blockers

The README and code documentation leave these areas unestablished:
- trusted production authentication and actor identity;
- customer/partner tenant isolation and sharing;
- a production server API connected to the interface;
- artifact upload/retention for external quote and order evidence;
- live supplier, carrier, advertising, order or partner integrations;
- live event subscriptions or real-time market monitoring;
- production browser E2E and security-boundary tests.

The SQLite store is local and single-host. Its append-only/audit behavior is useful under the supported application API, but it is not a tamper-proof hosted ledger. Run/report hashes establish packet identity and integrity checks, not that source information is true or authentic. A locally supplied code revision string does not independently prove which source build produced a run.

**Architecture conclusion:** keep the current deterministic core. Do not add AI or live integrations to make the product look more complete. First validate the decision workflow manually and define the production trust boundary.

## 2. Market and competitive position

### The current market is not empty

A first-pass public competitor scan on 2026-11-02 identified at least three adjacent products:

| Product | Publicly described capabilities | Competitive implication |
|---|---|---|
| **KIO / KIOSTORE** | Store creation, CIB/Edahabia/COD, COD Shield, marketing pixels and Conversion API, analytics, Google Sheets sync, carrier APIs, POS, customer data and ERP. KIO publicly claims 10,000+ merchants and offers a free tier; its current page lists paid plans around DZD 2,030 and DZD 4,130/month when billed annually. | Competes strongly on merchant workflow, order operations, payments, advertising tracking, courier integration and broad analytics. Its merchant and uptime claims are self-published, not independently audited here. |
| **Storix DZ** | Orders, inventory, shipment status, COD returns and costs, net margin, exports, analytics, pricing by wilaya; public page lists a DZD 1,500/month Pro plan and a 30-day/30-order trial. It says it is not connected directly to carriers. | Directly overlaps the current Medad story about COD costs, returns, margins and operational visibility. Demonstrates that “see what you really earned after returns” is not a unique claim. Its demo metrics are explicitly marked as demonstration data. |
| **goStore DZ** | Store, orders, stock, Ecotrack shipping, sales statistics, net-profit calculation, team management and API access by plan. | Further overlap in merchant operations, order/stock/delivery and profit calculation. Public site claims are not independent product validation. |

Sources and retrieval date are recorded at the end. Competitor feature and pricing claims come from public vendor pages; no hands-on trial, customer reference, security audit or independent merchant-count verification was performed.

### The current differentiation claim is too broad

These claims are not defensible as unique by themselves:
- COD-aware profitability;
- returned-order cost calculation;
- order/stock/delivery tracking;
- basic seller analytics;
- local currency and Algerian merchant workflow;
- “all-in-one commerce OS”.

At least some competitors already advertise overlapping capabilities. Competing directly as another store builder, CRM, ERP, courier console or general analytics dashboard would put Medad against established products, free plans and low monthly prices.

### More defensible wedge to test

Test whether Medad can own the workflow **before stock is purchased**:

1. Build a deal file for one exact SKU and intended partnership.
2. Reconcile independently sourced supplier quotes for comparable specification and quantity.
3. Verify the sample and capture landed-cost and cash-timing assumptions.
4. Capture seller-specific courier terms by origin/destination and delivery mode.
5. Model downside exposure: stock cash at risk, failed delivery, recoverability, return losses, advertising cap and settlement delay.
6. Record who funds stock, who owns it, who approves spend, how losses are allocated and how retained profit is calculated.
7. Authorize only a bounded human-approved pilot.
8. Reconcile actual orders and cash after delivery/returns, then compare the result with the pre-stock decision.

This is a tighter and more valuable claim than “we calculate seller margins”. However, the current code does not yet provide the entire partnership-capital and cash-reconciliation workflow. It has useful foundations, but ownership, exposure, cash conversion, partner settlements and the buyer/payer are not fully implemented or validated.

**Discriminating test:** run the same pre-stock decision through Medad, a spreadsheet/manual process, KIO, Storix and goStore where their functions permit. Measure whether Medad changes a real decision, reduces time or error, reveals a risk the alternatives miss, or produces a materially better auditable partner decision. If it does not, do not build a large new platform around the current differentiation story.

## 3. Product and user strategy

The current dossier assumes a B2B subscription model. That is not established by repository evidence and may be premature.

The initial operating concept is better represented as a two-party commercial workflow:
- **Operator:** product research, evidence gathering, offer design, marketing/advertising and order acquisition.
- **Capital/fulfilment partner:** funds or acquires stock, stores/prepares it and coordinates delivery.
- **Shared decision record:** product specification, supplier evidence, full costs, stock ownership, permitted ad spend, responsibilities, return/loss allocation and settlement.

These are intended roles, not confirmed signed partners or completed operations.

Do not force a SaaS subscription as the first monetization model. Compare these hypotheses:
- a managed deal-evaluation / partnership service;
- a per-deal or operating fee;
- a SaaS workspace subscription for repeat users;
- a blended model only if buyers demonstrate willingness to pay.

The first payer must be identified. A merchant user, capital partner, e-commerce agency and fulfilment operator have different budgets, incentives and trust requirements. The person entering data is not necessarily the buyer.

**Recommended client-zero sequence:** first run the workflow in one real partnership under human control; learn the actual documents, roles, settlement rules and decisions; then decide which components must become multi-user software. A hosted SaaS architecture should follow an evidenced collaboration need, not precede it.

## 4. Unit-economics methodology — strengths and limitations

### Strengths

The current engine usefully separates placed, delivered, failed, returned and retained orders. It calculates contribution, modeled profit, CAC per placed and retained order, and a break-even ad threshold. It does not silently produce a zero break-even ad budget when the model is already loss-making before ads. It validates numeric inputs, exposes assumptions and supports deterministic stress scenarios.

The opportunity gates also demand exact SKU evidence, sample inspection, two supplier quote records, landed-cost reconciliation, courier terms, a campaign and reconciled cohorts. These are stronger than a simple profitability score.

### Material modeling limitations

1. **Order lifecycle is too compressed.** One delivery rate and one customer-return rate do not represent confirmation, pre-dispatch cancellation, dispatch, first attempt, refused parcel, repeated attempt, successful delivery, customer return and final retention separately.
2. **Cost-incurrence timing is assumed.** Packaging and outbound delivery are charged on every placed order. If costs are only incurred after confirmation or dispatch, the model can overstate costs; if other fees are incurred earlier, it may understate them.
3. **Delivery fee handling is simplified.** Delivery-fee revenue is modeled only for retained orders. Actual collection, refund and carrier settlement rules must be modeled from the relevant contract and cohort.
4. **Return recovery is simplified.** A single recovery percentage does not represent damaged goods, missing packaging, resale discounts, inspection, reverse logistics, refurbishment or loss of saleability.
5. **Other material costs are not automatically inferred.** Taxes, payment fees, storage, handling, salaries, supplier MOQs, stock-outs, obsolescence, cash conversion cycle and working-capital financing need explicit fields and timing.
6. **Supplier quote comparability is not fully established.** Unique supplier IDs and valid-looking quote records do not by themselves prove independent suppliers, authentic seller identity, comparable product grade, equal quantity tiers, current stock or equivalent delivery/incoterm terms.
7. **Artifact references are not authenticity checks.** The gate accepts structured references and fields, but the project does not yet provide a production evidence intake and provenance/authenticity service for the underlying documents.
8. **Campaign attribution can be wrong.** A campaign record with spend, creative and attributed orders does not independently verify attribution or deduplicate cross-channel orders.
9. **A high evidence-quality grade is not statistical confidence.** The score is a heuristic based on a small set of groups, freshness, coverage and sample-size thresholds. A sample size of 30 is not generally sufficient to establish precise delivery/return rates; the grade must not be described as probability, forecast reliability or proof of profit.

Before a live pilot, replace single rates with cohort-level counts and denominators, preserve stage timestamps and cost-incurrence rules, include uncertainty intervals for rates, and explicitly reconcile courier remittances and returned inventory.

### Missing economics: Medad itself

The engine estimates the merchant/partnership deal. It does not yet establish the economics of Medad as a business:
- who pays and for which measurable outcome;
- revenue per customer/deal/workspace;
- acquisition cost and sales-cycle length;
- onboarding and human-review time;
- support and data-collection cost;
- infrastructure and third-party API cost;
- gross margin and payback;
- repeat deal frequency and retention;
- payment collection and bad-debt exposure.

Do not treat profitable merchant orders as evidence that Medad is a profitable software company.

## 5. Data, security and legal scope

No production multi-tenant data boundary is established. The prototype should not be used as a hosted system for identifiable customer/order data until identity, authorization, isolation and operational security are implemented and tested.

The legal review must distinguish two roles:
- **Medad as a B2B software/service provider:** define controller/processor roles and whether Medad processes personal data on behalf of merchants.
- **Medad as an electronic supplier, intermediary or operator of transactions:** determine whether its actual conduct brings additional e-commerce registration, website/domain, disclosure, contract, delivery, consumer and return requirements into scope.

Do not decide applicability solely from the product label or marketing language. Obtain an Algerian legal review of the actual business flow and contract structure.

Law 25-11 (24 July 2025) amends Law 18-07. Among other provisions, it adds obligations around DPO designation for controllers in scope, registers of processing activities, automated logs of processing operations, pre-processing impact studies where high risks are likely, security measures, and breach notification. The current Medad prototype is not a compliance implementation. Map these requirements to the controller/processor roles actually applicable to the pilot. Also examine cross-border hosting and transfers where external cloud, model, analytics or file providers are used.

The e-commerce law 18-05 defines e-commerce in terms of an e-provider offering or supplying goods/services remotely by electronic communications and includes registration and site requirements. Whether it applies to Medad directly depends on whether Medad merely supplies business software or itself offers/arranges the transaction; that must be assessed rather than assumed.

## 6. Startup.dz — application readiness

The current Startup.dz form requires Latin-script fields, applicant identity/contact/CV, project name/sector, a description of no more than 400 characters, the portal's downloadable pitch-deck model, a detailed presentation, a prototype photo, advancement status, business-model type, website, incubation/ministerial-decision details and IP/awards where applicable.

The proposed short description currently has **332 characters**. It should be revised to avoid overclaiming that the software itself operationally blocks all risky business decisions; the present engine produces analysis and gate statuses, but the UI and production workflow are not fully integrated.

### Legal criteria

The original Decree 20-254 (2020), Article 17 requires:
- a presentation of the project and its innovative aspects;
- evidence of significant economic growth potential;
- scientific and/or technical qualifications and experience of the team;
- where applicable, IP documents and awards.

Decree 21-422 (2021) amends the application pathway and preserves the first three document items as unchanged, while listing conditional supporting evidence such as IP, awards, proof that at least half the project members hold doctorates, incubation attestation from a labelled incubator, and a proof-of-concept/prototype presentation.

Decree 25-311 (published in December 2025) later amends other parts of Decree 20-254, including the committee's remit, startup-label renewal and incubator provisions, and establishes a Scale-up label. Its published amendments do **not** rewrite Article 17's Projet innovant evidence list. The dossier should cite all three instruments and avoid describing Decree 25-311 as having changed Article 17.

### Current submission blockers

- **Growth potential:** not demonstrated. National e-commerce statistics and COD context are not evidence of Medad's reachable customers, demand, adoption or revenue potential.
- **Team:** founder CVs, qualifications, technical experience, role allocation and commitment have not been included or verified.
- **Prototype photo:** the deck uses authored diagrams, not an authentic screenshot/photo of the actual prototype. The form separately asks for a prototype photo.
- **Official pitch-deck template:** the portal explicitly requires its downloadable template. The supplied custom 13-slide PowerPoint has not been compared against that template and is not submission-compliant by default.
- **Business model:** B2B is selected in the dossier without evidence identifying the actual payer or validated willingness to pay.
- **Market positioning:** competitor analysis was missing from the first dossier; this review adds the first-pass scan but not a complete market study.
- **Commercial evidence:** no verified paid pilot, customer LOI, actual order dataset, revenue, repeat usage or signed partnership was found in the inspected material.
- **IP/incubation/awards:** status unknown; do not invent or imply availability.

**Application decision: NOT READY TO SUBMIT.** Continue dossier preparation, but do not upload it as a completed evidence package.

## 7. Required validation programme and kill criteria

### Stage A — problem and competitive validation (first 2 weeks)

Interview a deliberately varied discovery sample: e-commerce operators, people who finance or own stock, and partnership/fulfilment operators. Treat the sample as qualitative discovery, not a statistically representative survey.

For the same historical deal, compare:
- current spreadsheet/manual process;
- KIO;
- Storix;
- goStore;
- Medad's proposed workflow.

Record which source the user trusts, which decisions they make, which information is missing, time to decision, reconciliation errors, and whether any incumbent plus spreadsheet already solves the pre-stock job.

**Kill/pivot condition:** users cannot identify a repeated, costly decision that the alternatives fail to support, or they will not share the minimum supplier/courier evidence needed.

### Stage B — one real client-zero deal (weeks 3–6)

Run one exact SKU/partnership through a manual evidence pack. Use only consented, redacted records. Record supplier identity, exact product grade, quantity tier, quote date/validity, sample inspection, landed cost, courier terms, cash remittance and stock ownership. No inventory purchase or advertising commitment should occur without a separate human decision and written terms.

Measure:
- time and effort to prepare the decision;
- evidence completeness and reconciliation discrepancies;
- capital exposed and downside loss;
- what the partner/operator decided before and after;
- what the product predicted versus the real cohort outcome.

### Stage C — repeated execution and payer test (weeks 7–12)

Run separate non-overlapping cohorts where operations genuinely permit. Reconcile placed, confirmed, dispatched, delivered, failed, returned and retained orders; carrier settlement and customer refunds; ad spend and cash timing.

Then present a real paid offer to the identified payer. Record acceptance, rejection, reason, price, support effort and repeated usage. Stated interest is not equivalent to payment.

### Stop conditions

Stop or reposition if:
1. Medad cannot change a decision or produce a measurable time/error/risk improvement over incumbent tools and spreadsheets.
2. operators and capital partners will not supply the necessary evidence;
3. no identifiable buyer accepts a paid pilot or another defensible commercial arrangement;
4. actual data repeatedly invalidates the model assumptions and the engine cannot be calibrated without excessive data-collection cost;
5. partnership economics remain ambiguous enough that the workflow cannot safely represent ownership, losses, advertising authority and settlement.

## 8. Corrections required before resubmitting the application pack

1. Rewrite the business model as an **unresolved, testable choice**; explain the initial partnership workflow and separate a later SaaS option.
2. Add a competitor matrix and narrow the claimed innovation to pre-stock underwriting and partnership-risk control.
3. Replace the stale CI statement with the actual run #359 result, while preserving the production-readiness limitations.
4. Add the missing growth-potential evidence plan and founder/team evidence checklist required under Article 17.
5. Use an authentic prototype screenshot as the photo attachment.
6. Obtain the official Startup.dz pitch-deck template and transfer content into it; compare every mandatory section before submission.
7. Add a role-based privacy/legal implementation plan under amended Law 18-07 and clarify whether Medad is an e-provider or merely a B2B software service.
8. Keep all NIN, identity documents, home addresses, phone numbers, founder CVs and confidential evidence out of this public repository. Upload personal documents only through the verified official portal.

## Sources checked on 2026-11-02

### Official Algerian application and legal sources
- [Startup.dz — Label Projet innovant form](https://startup.dz/label-projet/) — live required fields and official deck-template instruction.
- [Journal officiel 2020, Decree 20-254](https://www.joradp.dz/FTP/jo-arabe/2020/A2020055.pdf) — Article 17, growth potential and team qualifications/experience.
- [Journal officiel 2021, Decree 21-422](https://www.joradp.dz/FTP/jo-francais/2021/F2021084.pdf) — amended Article 17 and conditional supporting evidence.
- [Journal officiel 2025, Decree 25-311](https://www.joradp.dz/FTP/jo-arabe/2025/A2025081.pdf) — later changes to the Decree 20-254 framework and the Scale-up label.
- [Law 25-11 amending Law 18-07](https://droit.mjustice.gov.dz/sites/default/files/loi_25-11-fr.pdf).
- [Ministry of Commerce — Law 18-05](https://commerce.gov.dz/fr/reglementation/loi-n-deg-18-05).
- [UNCTAD — Algeria eTrade Readiness Assessment (2025)](https://unctad.org/system/files/official-document/dtlecde2025d3_en.pdf) — national context only, not Medad demand or TAM.

### Competitor pages reviewed (vendor-published claims)
- [KIOSTORE](https://kio.dz/en/kiostore) and [KIO About](https://kio.dz/en/about).
- [Storix DZ](https://storix-dz.com/).
- [goStore DZ](https://gostoredz.com/fr).

### Project evidence
- [Medad development branch](https://github.com/Loofy147/Medad/tree/feat/medad-commerce-os-foundation).
- [Product model / evidence contract](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/docs/PRODUCT_MODEL.md).
- [Market research snapshot](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/docs/MARKET_RESEARCH.md).
- [Unit-economics engine](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/engine/engine.py).
- [Opportunity gates](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/engine/opportunity.py).
- [Decision workflow](https://github.com/Loofy147/Medad/blob/feat/medad-commerce-os-foundation/engine/workflow.py).
