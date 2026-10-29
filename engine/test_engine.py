import unittest
from engine import Inputs, assess_data_quality, evaluate, scenarios

class UnitEconomicsTests(unittest.TestCase):
    def test_base_case_accounts_for_delivered_retained_orders_and_costs(self):
        result = evaluate(Inputs())
        self.assertEqual(result["funnel"]["placed_orders"], 100)
        self.assertEqual(result["funnel"]["delivered_orders_expected"], 70.0)
        self.assertEqual(result["funnel"]["returned_orders_expected"], 3.5)
        self.assertEqual(result["funnel"]["retained_orders_expected"], 66.5)
        self.assertEqual(result["economics_dzd"]["estimated_profit"], 32855.0)

    def test_recovered_return_inventory_is_not_fully_written_off(self):
        full_recovery = evaluate(Inputs(customer_return_rate=0.1, inventory_recovery_rate=1.0))
        no_recovery = evaluate(Inputs(customer_return_rate=0.1, inventory_recovery_rate=0.0))
        loss_full = full_recovery["economics_dzd"]["unrecoverable_return_inventory"]
        loss_none = no_recovery["economics_dzd"]["unrecoverable_return_inventory"]
        self.assertEqual(loss_full, 0)
        self.assertGreater(loss_none, loss_full)

    def test_zero_orders_has_no_division_error_or_fake_cac(self):
        result = evaluate(Inputs(placed_orders=0, ad_spend=0))
        self.assertEqual(result["decision"]["status"], "NO_VOLUME")
        self.assertIsNone(result["economics_dzd"]["ad_cost_per_placed_order"])
        self.assertIsNone(result["economics_dzd"]["profit_per_retained_order"])

    def test_invalid_rates_and_negative_costs_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(Inputs(delivery_rate=1.2))
        with self.assertRaises(ValueError):
            evaluate(Inputs(purchase_cost=-1))
        with self.assertRaises(ValueError):
            evaluate(Inputs(placed_orders=1.5))

    def test_downside_scenario_is_worse_than_base_for_default_case(self):
        cases = scenarios(Inputs())
        base = cases["base"]["economics_dzd"]["estimated_profit"]
        downside = cases["downside"]["economics_dzd"]["estimated_profit"]
        upside = cases["upside"]["economics_dzd"]["estimated_profit"]
        self.assertLess(downside, base)
        self.assertGreater(upside, base)

    def test_data_quality_without_metadata_is_unknown(self):
        quality = assess_data_quality(Inputs())
        self.assertIsNone(quality["score"])
        self.assertEqual(quality["grade"], "UNKNOWN")

    def test_data_quality_rejects_unknown_evidence_labels(self):
        with self.assertRaises(ValueError):
            evaluate(Inputs(evidence={"unit_cost": "guaranteed"}))

    def test_no_break_even_when_product_loses_money_before_ad_spend(self):
        result = evaluate(Inputs(selling_price=100, purchase_cost=1000, ad_spend=0))
        econ = result["economics_dzd"]
        self.assertFalse(econ["break_even_possible_before_ads"])
        self.assertIsNone(econ["break_even_ad_spend"])
        self.assertIsNone(econ["break_even_ad_cost_per_retained_order"])

    def test_untraceable_numeric_scores_cannot_receive_high_evidence_grade(self):
        result = evaluate(Inputs(
            confidence={"unit_cost": 1, "selling_price": 1, "delivery_rate": 1, "return_rate": 1, "ad_cost": 1},
            evidence={"unit_cost": "observed", "selling_price": "observed", "delivery_rate": "observed", "return_rate": "observed", "ad_cost": "observed"},
            sample_size=1000, data_age_days=1,
        ))
        self.assertEqual(result["data_quality"]["grade"], "LOW")
        self.assertEqual(result["data_quality"]["provenance_coverage"], 0)
        self.assertTrue(any("Source URL" in item for item in result["data_quality"]["warnings"]))

    def test_source_metadata_requires_valid_url_date_and_label(self):
        with self.assertRaises(ValueError):
            evaluate(Inputs(evidence_sources={"unit_cost": {"url": "not-a-url", "observed_on": "2026-10-29", "label": "quoted"}}))

    def test_traceable_source_metadata_is_reported(self):
        result = evaluate(Inputs(
            confidence={"unit_cost": .9}, evidence={"unit_cost": "quoted"},
            evidence_sources={"unit_cost": {"url": "https://example.com/quote", "observed_on": "2026-10-29", "label": "quoted"}},
            sample_size=5, data_age_days=0,
        ))
        self.assertEqual(result["data_quality"]["provenance_coverage"], .2)
        self.assertEqual(result["data_quality"]["grade"], "LOW")


class OpportunityGateTests(unittest.TestCase):
    def test_listing_without_supplier_quote_stays_research_only(self):
        from opportunity import assess_candidate
        result = assess_candidate({"id": "listing-only", "market_price_observed_dzd": {"low": 100, "high": 200}})
        self.assertEqual(result["stage"], "RESEARCH_ONLY")
        self.assertFalse(result["is_profitability_score"])
        self.assertFalse(result["is_investment_approval"])

    def test_supplier_and_courier_quotes_do_not_skip_pilot_gate(self):
        from opportunity import assess_candidate
        candidate = {"id": "quoted", "product_spec_verified": True, "supplier_quotes_count": 2,
                     "landed_cost_verified": True, "courier_quote_verified": True}
        self.assertEqual(assess_candidate(candidate)["stage"], "PRETEST_READY")

    def test_single_cohort_needs_repeatability_before_scale_review(self):
        from opportunity import assess_candidate
        candidate = {"id": "tested", "product_spec_verified": True, "supplier_quotes_count": 2,
                     "landed_cost_verified": True, "courier_quote_verified": True,
                     "pilot_campaign_evidence": True, "delivered_order_cohort_evidence": True,
                     "repeatable_cohorts": 1}
        self.assertEqual(assess_candidate(candidate)["stage"], "TESTED_SINGLE_COHORT")

    def test_wholesale_discovery_platforms_are_not_supplier_quotes(self):
        from pathlib import Path
        from opportunity import load_snapshot
        snapshot = load_snapshot(Path(__file__).resolve().parent.parent / "data" / "research_snapshot_2026-10-29.json")
        self.assertEqual(len(snapshot["sourcing_leads"]), 3)
        self.assertTrue(all(lead["status"] == "DISCOVERY_LEAD_ONLY" for lead in snapshot["sourcing_leads"]))
        self.assertTrue(all(lead["quote_verified"] is False for lead in snapshot["sourcing_leads"]))

    def test_registry_rejects_sourcing_lead_with_unknown_source(self):
        from pathlib import Path
        import json
        from opportunity import load_snapshot
        path = Path(__file__).resolve().parent.parent / "data" / "research_snapshot_2026-10-29.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        source["sourcing_leads"][0]["platform_source_id"] = "missing-source"
        # Keep the corrupt snapshot isolated in a temporary file.
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as file:
            json.dump(source, file)
            temp_path = Path(file.name)
        try:
            with self.assertRaises(ValueError):
                load_snapshot(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_registry_has_no_investment_ready_candidate(self):
        from pathlib import Path
        from opportunity import load_snapshot
        snapshot = load_snapshot(Path(__file__).resolve().parent.parent / "data" / "research_snapshot_2026-10-29.json")
        self.assertEqual(len(snapshot["candidates"]), 4)
        self.assertTrue(all(x["stage"] == "RESEARCH_ONLY" for x in snapshot["readiness"]))


if __name__ == "__main__":
    unittest.main()
