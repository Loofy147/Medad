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

Contribution before ads is revenue and collected delivery fees minus the modeled variable costs other than ads and fixed costs. Break-even ad spend is max(0, contribution_before_ads - other_fixed_costs). Break-even CAC is reported per placed order and per retained order when denominators exist. A zero-volume case returns null for undefined CAC rather than inventing a zero.

## Scenario analysis

Downside, base, and upside are deterministic stress cases, not probabilistic forecasts or calibrated confidence intervals. Downside reduces delivery, increases returns, ad spend, outbound delivery and failed-delivery cost. Upside assumes modestly better delivery, fewer returns and lower ad spend. Tune the shocks using observed historical cohort data before relying on them.

## Evidence labels

Every external input should carry a source, observation date, geography, sample size, and status:

- observed: measured from the business's real orders or completed campaigns.
- quoted: stated by a supplier or carrier and supported by a dated quote/document.
- estimated: estimated from disclosed comparisons or historical evidence.
- assumed: no adequate evidence yet.

The data_quality score is a heuristic completeness/freshness indicator, not a probability of making a profit. Labels alone do not verify claims. Any high-risk input should identify source URL/document, date, location/region, currency and owner.

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
