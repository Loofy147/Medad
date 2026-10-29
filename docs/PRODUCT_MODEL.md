# Product model & evidence contract

## Scope

The engine is a decision-support model for Algerian COD-style commerce partnerships. It is deterministic and uses Python's standard library. It does not discover live products, verify supplier legitimacy, predict conversion, or connect to courier, advertising or order APIs.

## Unit economics

For P placed orders, delivery rate d, and customer-return rate r:

- Delivered = P × d
- Undelivered = P − Delivered
- Returned after delivery = Delivered × r
- Retained = Delivered − Returned
- Product sales revenue = retained × sale price
- Customer delivery fee revenue = retained × delivery fee collected (modeled only when the order is retained)
- Retained-product COGS = retained × purchase cost
- Unrecoverable return inventory loss = returned × purchase cost × (1 − recovery rate)

Other costs are explicitly separated: packaging per placed order, outbound courier cost per placed order, failed-delivery return logistics, return shipping and handling, ads, other retained-order variable costs, and fixed costs.

> This is a configurable simplifying model. If your courier charges only after dispatch, cancellations before dispatch must be modeled separately. Taxes, payment fees, storage, salaries, refund leakage, supplier minimum quantities and working-capital timing are not automatically inferred.

## Break-even

Contribution before ads is revenue and collected delivery fees minus the modeled variable costs other than ads and fixed costs. Break-even ad spend is `contribution_before_ads - other_fixed_costs` when this value is non-negative. If it is exactly zero, the model is at break-even with zero ad spend. If it is negative, break-even spend/CAC are `null` because no ad budget can repair a loss that exists before advertising. Break-even CAC is reported per placed order and per retained order only when break-even is possible and denominators exist. A zero-volume case returns `null` for undefined CAC rather than inventing a zero.

## Scenario analysis

Downside, base, and upside are deterministic stress cases, not probabilistic forecasts or calibrated confidence intervals. Downside reduces delivery, increases returns, ad spend, outbound delivery and failed-delivery cost. Upside assumes modestly better delivery, fewer returns and lower ad spend. Tune the shocks using observed historical cohort data before relying on them.

## Evidence labels

Every external input should carry a source, observation date, geography, sample size, and status:

- observed: measured from the business's real orders or completed campaigns.
- quoted: stated by a supplier or carrier and supported by a dated quote/document.
- estimated: estimated from disclosed comparisons or historical evidence.
- assumed: no adequate evidence yet.

The data_quality score is a heuristic completeness/freshness indicator, not a probability of making a profit. Labels alone do not verify claims. Any high-risk input should identify source URL/document, date, location/region, currency and owner.

## Traceability requirement

Input values can be numerically plausible and still be untrustworthy. For a source-backed evidence grade, attach `evidence_sources` metadata to named evidence groups (for example `unit_cost`, `selling_price`, `delivery_rate`, `return_rate`, `ad_cost`) with an HTTPS source URL, ISO date `observed_on`, and evidence label (`observed`, `quoted`, `estimated`, or `assumed`). Numeric confidence without source URLs/date/label is capped at `LOW`. A source URL alone is not an independent verification; the linked evidence must support the specific input it is attached to. The score remains a heuristic completeness/freshness signal, never a probability of profit.

## Machine-enforced stage-gate contract

The current readiness evaluator deliberately ignores old boolean-only assertions such as "supplier quotes verified" or "campaign tested". To pass research gates, candidate records must include traceable evidence:

- **SKU + sample:** `sku` and `product_spec_verified=true`, plus `sample_inspection` containing `artifact_ref`, `inspected_on`, `inspector_id`, `outcome=PASS`, and the same SKU.
- **Supplier quotes:** at least two quote objects from distinct `supplier_id` values, each with a unique `quote_id`, an evidence `artifact_ref`, quote date, unexpired `valid_until`, exact matching SKU, `seller_verified=true`, positive `unit_price_dzd`, a positive integer `minimum_quantity`, and `currency=DZD`.
- **Landed cost:** documented `component_costs_dzd` must include purchase, packaging and inbound transport. Their sum must reconcile to `unit_cost_dzd` (tolerance 0.02 DZD), be reviewed, and reference at least one of the valid quote IDs.
- **Courier terms:** seller account verified, origin wilaya, explicit destination coverage, outbound/failed-delivery/return fees, cash-remittance days, quote/contract ID, date and evidence reference.
- **Campaign:** evidence ref, platform, creative, attribution method, start/end dates, spend and integer placed/attributed order counts.
- **Order cohort:** evidence ref, SKU, date window, reviewer and reconciliation flag. The evaluator checks `delivered + failed = placed`, `returned <= delivered`, and `retained = delivered - returned`. Two distinct reconciled cohorts are required for `SCALE_REVIEW_CANDIDATE`.

`artifact_ref` is an opaque traceable reference (for example an internal document ID or private object reference); this repository does not implement upload/storage of those artifacts yet. A valid reference and well-formed record are necessary but do not independently prove authenticity. Human review is still required, and a scale-review stage is not investment approval.

Freshness limits in the current evaluator: sample inspection must be no older than 180 days; supplier quotes and courier terms must be no older than 90 days and unexpired; campaign evidence and order cohorts must be no older than 90 days. The quote record must match the candidate's exact SKU and come from a distinct verified seller. These are conservative implementation gates, not claims that older evidence becomes false; they require revalidation before a decision.

For a positive modeled result, the unit-economics engine returns `UNVERIFIED_ECONOMICS` when provenance/sample/freshness is unknown or low. `TEST_CANDIDATE` requires `HIGH` evidence quality and acceptable delivery/return thresholds, and only permits a bounded test. A negative result remains explicitly labeled as a loss under the current inputs, not as an absolute statement about the SKU.


## Decision gates

1. Research: capture product source, supplier quote, comparable sale prices and sample proof.
2. Model: run downside/base/upside and test return, delivery and ad-cost sensitivity.
3. Small test: cap budget and stock exposure; define stop conditions before launch.
4. Reconcile: compare orders placed, confirmed, dispatched, delivered, refused/returned, and retained. Recompute CAC per retained order.
5. Scale: only after cohort results and cash conversion cycle support the decision.

Never describe a modeled candidate as a guaranteed winner. Do not rank products from fabricated or illustrative demand data.

## Partnership proposal essentials

The partner typically funds purchase and stock and manages storage/fulfillment/courier handoff. Medad manages product research, creative/marketing, paid campaign operations, and order acquisition. Agreement must define profit after costs, who owns inventory, who funds returns and losses, ad-spend cap/approval, settlement cadence, customer support, data access, and exit/unsold stock terms. The engine does not choose a profit-sharing percentage.

## Tests

Run from the repository root:

    cd engine
    python -m unittest -v
    python engine.py

The test suite covers the base result, recoverable returned inventory, zero volume, input validation, stress scenarios and evidence metadata.
