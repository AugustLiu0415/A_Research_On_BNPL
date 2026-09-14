# BNPL Partnership Announcements: Shareholder Value Creation and Value Allocation

Canonical active research-question document. Framing revision: **2026-09-14**.

This document governs the current research description, not the frozen
estimation protocol. It summarizes the README's questions in more detail,
connects them to evidence and preserves earlier frameworks as history.
The [README](../README.md) is the project entry point, and its
[Latest Checkpoint](../README.md#latest-checkpoint) remains the reference for
verified progress counts. No new results table is added here.

## Primary Research Question

> Do BNPL platform–merchant partnership announcements create shareholder value, how are the associated gains and losses distributed between platforms and merchants, and how do these valuation responses vary with firm and partnership characteristics?

This project examines announcement-associated equity-market responses to
BNPL platform–merchant partnerships. The primary design connects dated
partnership information, event-date securities, exchange-local reaction
sessions, market benchmarks and contemporaneous-news audits. Observed returns
refer to the traded issuer or public parent. Where a platform is observed
through a listed parent, the measured response is the parent's valuation
response, not a separately measured BNPL subsidiary return.

The current focus develops the intermediate proposal's **H2—Partnership
Surplus Allocation** component. Percentage CAR diagnostics are a first step
toward this question, not a completed measurement of contractual surplus.
Joint abnormal shareholder wealth and heterogeneity are planned extensions.

## Research Evolution

### Stage A — Original merchant-accounting design

The original question was:

> What are the short-run and long-run effects of BNPL adoption on merchants'
> revenue growth, gross margins, and operating margins, and are these effects
> heterogeneous across firms with different size and bargaining power?

The original README at historical commit `54fb93c` records the following
hypotheses. They are preserved as **Stage A hypotheses about accounting
outcomes**, not current CAR hypotheses:

1. **Stage A H1 — Industry Heterogeneity Hypothesis:** The BNPL effect is
   stronger in discretionary, high-ticket, high-margin, and e-commerce-intensive
   industries.
2. **Stage A H2 — Scale/Exposure Hypothesis:** BNPL adoption generates larger
   proportional revenue effects for smaller and more focused merchants
   because BNPL-enabled sales represent a larger share of firm-level sales.
3. **Stage A H3 — Bargaining Power Hypothesis:** Conditional on BNPL exposure,
   larger merchants may experience smaller margin penalties because stronger
   bargaining power allows them to negotiate more favorable BNPL economics.

The researcher's supplied account of earlier exploratory work reported:

- Placebo standard deviation: approximately **3.06%**.
- Implied minimum detectable revenue effect: approximately **8.6%**.
- Reasoned plausible consolidated-revenue effect: **1–6%**.

The 1–6% range was a **plausibility assessment, not an estimated treatment
effect**. These reported considerations motivated concerns about consolidated
outcome aggregation and statistical power. They do not prove that BNPL has
no merchant effect. This framing task does not independently re-estimate the
placebo distribution, minimum detectable effect or accounting outcomes.

### Stage B — Intermediate platform-focused proposal

The researcher's proposal asked:

> How do merchant-network composition and regulatory shocks shape value creation, surplus allocation, and risk incidence in Buy Now, Pay Later platforms?

Its proposed H1–H3 framework is retained separately:

1. **Stage B H1 — Merchant Portfolio Economics:** Merchant composition,
   concentration and multi-homing in relation to platform performance and risk.
2. **Stage B H2 — Partnership Surplus Allocation:** Partnerships may create
   value for both sides, but bargaining power, outside options and relative
   importance may affect its allocation.
3. **Stage B H3 — Regulatory Incidence:** Platforms and merchants may respond
   differently to regulatory changes.

This was the researcher's proposal and request for advice. It is not evidence
that Professor Chernoff approved the exact current wording. The sending date
of the private email is not established here, and the full correspondence
is neither reproduced nor distributed.

The Stage A and Stage B H1–H3 labels identify different historical frameworks.
They are not merged or silently relabelled as finalized current hypotheses.

### Stage C — Current primary empirical focus

The partnership-announcement event study is primary and develops **Stage B
H2—Partnership Surplus Allocation**. The agenda is prioritized as follows:

| Priority | Scope | Role and completion boundary |
| --- | --- | --- |
| Primary | Partnership announcements, bilateral valuation responses, planned abnormal dollar wealth and heterogeneity | Initial AR/CAR diagnostics exist; wealth, mechanisms and formal inference remain unestablished |
| Supporting | Merchant-network composition and platform-quarter economics | Context, mechanism or robustness work if historical data permit; not all completed |
| Secondary | Regulatory-event feasibility and robustness | Earlier tests were reported as mixed/noisy; not a coequal current main design |
| Legacy/exploratory | Merchant accounting DiD and private-company financial recovery | Prior outcomes and data-recovery work are preserved; not the current primary analysis |

The broader agenda has not been abandoned. Existing historical plans,
module-specific decision logs and private correspondence are unchanged.
Sequence labels A/B/C do not invent dates for the earlier proposal or
retroactively describe it as an approved pre-analysis plan.

## Units, Eligible Samples and Observable Scope

| Layer | Unit of observation | Eligibility and interpretation |
| --- | --- | --- |
| Event evidence | Distinct partnership-information announcement/bundle, with merchant links | Distinguish first information from operational rollout and later announcement stages |
| Market observation | Event × security/side × local reaction session/window, retaining specification and timing scenario | Historical identity/tradability, audited interval, valid return basis, appropriate benchmark, estimation coverage and complete event returns must pass |
| Paired comparison | The same event with both securities observable and eligible | Retain both local reaction intervals; do not compare unrelated platform-only and merchant-only samples as allocation evidence |
| Planned wealth comparison | Eligible same-event pair with aligned pre-event capitalization and FX inputs | Match share-class, ownership and currency scope before interpreting combined amounts |

The current eligible diagnostic subset comes from the unchanged fixed pilot.
A clean main-anchor observation requires accepted timing and the relevant
side/window audit. Bounded timing sensitivities remain separate from accepted
anchors. A source-quality grade or MAIN sample label does not establish a
clean information shock.

The Zip–Fanatics/Fiserv multi-merchant announcement is one platform shock
with two links. Do not count its platform reaction repeatedly, or allocate
its full platform wealth change independently to each merchant. Repeated
platforms, bundles and overlapping windows create dependence.

A private merchant's unobservable return is **missing, not zero**. Listed
parent responses can include other businesses; they are not pure merchant-brand
or BNPL-subsidiary valuations.

## Four Research Questions

### RQ1 — Do BNPL partnership announcements create value?

**Operational question:** Are partnership announcements associated with positive or negative abnormal shareholder returns for BNPL platforms and their merchant partners?

- **Outcome/evidence:** Platform CAR and merchant/public-parent CAR. Eventually,
  suitable inference about average responses and uncertainty in explicitly
  defined eligible samples.
- **Unit of observation:** Event × security/side × local reaction
  session/window.
- **Eligible sample:** Independently eligible sides of the fixed pilot,
  separated by specification, market, window and timing status. Both sides
  need not be available to retain an eligible single-side diagnostic.
- **Current status:** Initial event-level diagnostics exist. An industry-wide
  effect and formal inference are not established.
- **What remains:** A documented inferential population, dependence-aware
  measurement and inference choices, and data/benchmark validation.
- **Key interpretation limit:** Do not assume every announcement benefits
  both sides. Missing or imprecise responses are not proof of no value.
  Announcement-associated returns are not realized operating gains or causal
  proof of partnership effects.

### RQ2 — Who captures the value, or bears the loss?

**Operational question:** How are announcement-associated gains and losses distributed between the platform and the merchant in the same partnership event?

- **Outcome/evidence:** Same-event platform and merchant CAR; planned abnormal
  dollar wealth using pre-event capitalization; independent evidence on
  bargaining power, outside options and relative dependence.
- **Unit of observation:** The same partnership event with an eligible
  bilateral pair, retaining each security's local reaction window.
- **Eligible sample:** Both legs observable and eligible. Comparable
  specifications are required for like-for-like paired summaries; timing
  sensitivities and cross-market comparisons remain explicitly separate.
- **Current status:** Paired percentage-return diagnostics exist for some
  events. Dollar-wealth allocation and bargaining mechanisms are unestablished.
- **What remains:** Historical capitalization, comparable currency amounts,
  measurement decisions and mechanism evidence that is not inferred from
  subsequent CAR signs.
- **Key interpretation limit:** A larger percentage CAR does not imply a
  larger dollar gain or a larger share of contractual surplus. Comparing
  different platform-only and merchant-only samples is not allocation
  evidence. Missing private-counterparty returns are never set to zero.

### RQ3 — Net combined value or redistribution?

“Does the partnership create total economic value, or merely redistribute it?”

In this design, the measurable object is combined abnormal shareholder wealth
for the observed participating firms, not total economy-wide value or welfare.

**Operational question:** Are the partners’ combined abnormal wealth changes consistent with net gains, net losses, or offsetting gains and losses between their shareholders?

- **Outcome/evidence:** Combined abnormal shareholder wealth for the observed
  participating firms.
- **Unit of observation:** An eligible same-event pair or explicitly specified
  multi-merchant bundle with aligned valuation scope.
- **Eligible sample:** Both required returns observable and eligible, with
  valid pre-event capitalization and a documented FX convention. No completed
  wealth-analysis sample is claimed at this checkpoint.
- **Current status:** **Planned**, pending capitalization/FX inputs and
  measurement/inference decisions.
- **What remains:** Define the pre-information baseline, share-class/ownership
  coverage, currency convention, error treatment and bundle aggregation
  before producing dollar estimates.

**Planned short-window measurement — not completed results:**

```text
AW_platform,e ≈ PreEventMarketCap_platform,e × CAR_platform,e
AW_merchant,e ≈ PreEventMarketCap_merchant,e × CAR_merchant,e
JointAW_e = AW_platform,e + AW_merchant,e
```

The last sum requires both abnormal amounts in the **same currency**. For
different currencies, convert the abnormal amounts using a documented
**pre-event FX convention before summing**. The capitalization baseline must
precede the relevant information/event window and respect the security's
share-class and ownership scope. Do not use today's capitalization or a
post-announcement baseline.

**Key interpretation limits:**

- Opposite-signed CARs do not prove a transfer between the firms.
- A near-zero estimate or failure to reject zero does not establish pure
  redistribution.
- Positive combined shareholder wealth does not prove newly created
  economy-wide surplus. Rival firms, consumers and creditors are outside
  this sum.
- Dollar scaling can magnify return-estimation error for large firms.
- Do not mechanically define surplus shares when total abnormal wealth
  is near zero or negative.
- Do not count a bundle's platform value repeatedly, and do not sum overlapping
  ownership claims without resolving scope.

No joint-wealth calculation is performed or authorized by this framing update.

### RQ4 — When is value creation strongest?

**Operational question:** How do the direction and magnitude of individual and joint valuation responses vary with firm and partnership characteristics?

- **Outcome/evidence:** Individual CARs, planned joint abnormal wealth and
  historical firm/partnership characteristics.
- **Unit of observation:** Eligible event-security observations for individual
  responses, or eligible same-event pairs/bundles for planned joint responses.
- **Eligible sample:** The relevant eligible outcome sample with verified
  characteristics known before or at the announcement. Availability and
  missingness must be documented; no new sample selection is made here.
- **Current status:** **Planned heterogeneity analysis.** Some characteristics
  exist, but not all historical covariates are complete and the seven
  dimensions have not all been tested.
- **What remains:** Historical covariate completion, construct definitions,
  planned comparisons/tests and appropriate treatment of dependence,
  multiple comparisons and limited sample size.

The seven dimensions, in order, are:

1. **Industry.**
2. **BNPL platform.**
3. **Merchant size.**
4. **Exclusivity.**
5. **Multi-homing:** use of multiple BNPL providers.
6. **Partnership type:** distinguish direct merchants, marketplaces,
   distribution platforms and payment processors.
7. **Competitive importance:** observable scope, network reach, outside
   options or relative dependence, not subsequent stock returns.

**Key interpretation limits:** Current directory membership is not
automatically historical membership. Do not infer exclusivity from silence.
Do not impose an unsupported sign for size, exclusivity or multi-homing.
Size can combine exposure/dilution and bargaining-power channels. Historical
accounting hypotheses do not establish directional CAR predictions.
No new heterogeneity regressions are run in this documentation task.

## Working Mechanisms and Planned Tests

These propositions organize future evidence. They are not established
findings or finalized directional hypotheses.

| Working mechanism | Questions | Evidence needed | Planned test or interpretation |
| --- | --- | --- | --- |
| Incremental demand and network benefits may generate value when they outweigh fees, integration/financing costs and risks | RQ1, RQ3 | Audited event-side CAR; planned same-event dollar wealth; independent information on partnership scope, benefits and costs where observable | Assess responses with uncertainty once the inferential design is settled; CAR alone does not identify demand or realized profit |
| Bargaining power, outside options and relative dependence may shape asymmetric gains and losses | RQ2, RQ4 | Eligible bilateral observations; capitalization/FX; pre-event dependence, outside-option and contractual evidence where available | Compare the same event's sides and documented characteristics; percentage differences alone do not establish bargaining power or surplus shares |
| Exposure, merchant economics and partnership characteristics may condition valuation responses | RQ4 | Event-time characteristics across all seven dimensions, with documented missingness | Plan comparisons only after measurement and sample rules are explicit; do not infer moderators from observed CAR signs |

This question–proposition–evidence mapping follows the organizational structure
of the local *PhD Research Analysis Plan Guide*, especially sections 1.3–1.4,
6.3 and 6.5. The guide is an organizing aid, not empirical evidence, a source
of approved hypotheses or proof of a literature gap.

Diagnostics have already been observed. These formulations are recorded
on **2026-09-14**, not backdated or described as preregistered before the
pilot. They are not derived from whether Walmart or Shopify had a positive
CAR. Where a directional hypothesis remains unsettled, retain an explicit
question rather than fabricate a prediction.

## Completed Diagnostics and Planned Objectives

The verified existing
[README checkpoint](../README.md#latest-checkpoint) reports the unchanged
20 platform-shock units and 21 links, 29 OLS models, 133 daily AR records,
80 CAR estimates and 16 paired window/scenario records. Three bilateral
events have accepted-anchor, main-window paired diagnostics.

The 80 CARs comprise 12 primary-anchor/main-window records, 24
window-robustness records and 44 timing-sensitivity records. They are not
80 independent events; the 16 paired rows are not 16 independent partnerships.

Completed work provides local event-level diagnostics and an auditable
separation of eligible, blocked and not-applicable records. Formal inference,
industry-wide claims, mechanism identification, joint abnormal wealth and
heterogeneity remain planned or unestablished.

The current adjusted-stock/market-price-index diagnostics are not the final
matched-total-return specification. Initial information can precede rollout,
historical tradability and local sessions matter, and source quality is not
a confounder audit. Small samples, repeated platforms, bundles and overlapping
windows limit inference.

The previously documented workbook-hash discrepancy remains open:
current workbook values were reconciled to saved canonical outputs in the
preceding documentation review, but the current XLSX bytes differ from the
original run-manifest hashes. No workbook or manifest is changed here.

The existing disclosure boundary is unchanged. Specific CAR magnitudes,
raw and derived market data, workbooks and private correspondence remain
local and are not added to this documentation release.

## Documentation Decision Log

### 2026-09-14 — Current framing alignment

**Decision:** Research framing aligned with the partnership-announcement shareholder-valuation design; no sample, estimation or numerical outputs changed.

**Alternatives distinguished:** the original merchant-accounting design,
the intermediate three-module platform proposal, and the current focus on
the proposal's Partnership Surplus Allocation component.

**Reason:** Make the primary question, four subquestions, measured outcomes,
working mechanisms and completed-versus-planned objectives consistent across
the README and this canonical document.

**Impact and scope:** Documentation only. No changes to event dates, security
mapping, sample selection, exclusions, audit decisions, windows, thresholds,
benchmarks, models, frozen manifests, numerical results or existing code.
No estimation, joint-wealth calculation, new regression or research-test
rerun. Existing archived plans and private correspondence are preserved.
This is not a record of supervisor approval or preregistration.
