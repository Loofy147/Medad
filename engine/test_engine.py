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

    def test_non_finite_monetary_inputs_are_rejected(self):
        import math
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    evaluate(Inputs(purchase_cost=value))

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

    def test_positive_model_without_traceable_evidence_is_not_a_test_candidate(self):
        result = evaluate(Inputs())
        self.assertGreater(result["economics_dzd"]["estimated_profit"], 0)
        self.assertEqual(result["data_quality"]["grade"], "UNKNOWN")
        self.assertEqual(result["decision"]["status"], "UNVERIFIED_ECONOMICS")

    def test_test_candidate_status_requires_complete_recent_traceable_evidence(self):
        from datetime import date
        groups = ["unit_cost", "selling_price", "delivery_rate", "return_rate", "ad_cost"]
        evidence_sources = {
            key: {"url": f"https://evidence.example/{key}", "observed_on": date.today().isoformat(), "label": "observed"}
            for key in groups
        }
        result = evaluate(Inputs(
            confidence={key: .95 for key in groups},
            evidence={key: "observed" for key in groups},
            evidence_sources=evidence_sources,
            sample_size=100,
            data_age_days=0,
        ))
        self.assertEqual(result["data_quality"]["grade"], "HIGH")
        self.assertEqual(result["decision"]["status"], "TEST_CANDIDATE")

    def test_exact_break_even_before_ads_has_zero_budget(self):
        result = evaluate(Inputs(
            selling_price=1000, purchase_cost=500, packaging_cost=0,
            outbound_delivery_cost=0, delivery_fee_collected=0,
            failed_delivery_return_cost=0, return_shipping_cost=0,
            return_handling_cost=0, ad_spend=0, placed_orders=1,
            delivery_rate=1, customer_return_rate=0,
            inventory_recovery_rate=1, other_fixed_costs=500,
        ))
        economics = result["economics_dzd"]
        self.assertEqual(economics["contribution_before_ads"], 500)
        self.assertEqual(economics["break_even_ad_spend"], 0)
        self.assertTrue(economics["break_even_possible_before_ads"])

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

    def test_provenance_only_labels_contribute_coverage_but_do_not_create_high_confidence(self):
        result = evaluate(Inputs(
            evidence_sources={
                "unit_cost": {"url": "https://example.com/cost", "observed_on": "2026-10-29", "label": "quoted"},
                "selling_price": {"url": "https://example.com/price", "observed_on": "2026-10-29", "label": "observed"},
            },
        ))
        self.assertEqual(result["data_quality"]["coverage"], 0.4)
        self.assertEqual(result["data_quality"]["provenance_coverage"], 0.4)
        self.assertEqual(result["data_quality"]["grade"], "LOW")
        self.assertEqual(result["data_quality"]["components"]["unit_cost"], 0.8)
        self.assertIn("selling_price", result["data_quality"]["evidence_labels"])

    def test_confidence_and_label_for_same_group_are_blended_once(self):
        result = evaluate(Inputs(
            confidence={"unit_cost": 0.9},
            evidence={"unit_cost": "quoted"},
            evidence_sources={"unit_cost": {"url": "https://example.com/cost", "observed_on": "2026-10-29", "label": "quoted"}},
            sample_size=5,
            data_age_days=0,
        ))
        self.assertEqual(result["data_quality"]["components"], {"unit_cost": 0.85})
        self.assertEqual(result["data_quality"]["coverage"], 0.2)
        self.assertEqual(result["data_quality"]["provenance_coverage"], 0.2)

    def test_source_metadata_requires_valid_url_date_and_label(self):
        with self.assertRaises(ValueError):
            evaluate(Inputs(evidence_sources={"unit_cost": {"url": "not-a-url", "observed_on": "2026-10-29", "label": "quoted"}}))

    def test_evidence_source_label_must_match_input_label(self):
        with self.assertRaises(ValueError):
            evaluate(Inputs(
                evidence={"unit_cost": "assumed"},
                evidence_sources={"unit_cost": {"url": "https://example.com/quote", "observed_on": "2026-10-29", "label": "quoted"}},
            ))

    def test_stale_source_dates_override_falsely_fresh_user_age(self):
        groups = ["unit_cost", "selling_price", "delivery_rate", "return_rate", "ad_cost"]
        result = evaluate(Inputs(
            confidence={key: .95 for key in groups},
            evidence={key: "observed" for key in groups},
            evidence_sources={key: {"url": "https://example.com/" + key, "observed_on": "2020-01-01", "label": "observed"} for key in groups},
            sample_size=500, data_age_days=1,
        ))
        self.assertGreater(result["data_quality"]["data_age_days"], 90)
        self.assertEqual(result["data_quality"]["grade"], "LOW")

    def test_traceable_source_metadata_is_reported(self):
        result = evaluate(Inputs(
            confidence={"unit_cost": .9}, evidence={"unit_cost": "quoted"},
            evidence_sources={"unit_cost": {"url": "https://example.com/quote", "observed_on": "2026-10-29", "label": "quoted"}},
            sample_size=5, data_age_days=0,
        ))
        self.assertEqual(result["data_quality"]["provenance_coverage"], .2)
        self.assertEqual(result["data_quality"]["grade"], "LOW")


class OpportunityGateTests(unittest.TestCase):
    @staticmethod
    def research_ready_candidate():
        from datetime import date, timedelta
        today = date.today()
        later = (today + timedelta(days=30)).isoformat()
        recent = today.isoformat()
        quotes = [
            {"quote_id": "quote-1", "artifact_ref": "private://evidence/quote-1", "quoted_on": recent,
             "valid_until": later, "supplier_id": "supplier-a", "seller_verified": True, "sku": "SKU-1",
             "minimum_quantity": 10, "unit_price_dzd": 500, "currency": "DZD"},
            {"quote_id": "quote-2", "artifact_ref": "private://evidence/quote-2", "quoted_on": recent,
             "valid_until": later, "supplier_id": "supplier-b", "seller_verified": True, "sku": "SKU-1",
             "minimum_quantity": 20, "unit_price_dzd": 470, "currency": "DZD"},
        ]
        return {
            "id": "test-candidate", "sku": "SKU-1", "product_spec_verified": True,
            "sample_inspection": {"artifact_ref": "private://evidence/sample", "inspected_on": recent,
                                  "inspector_id": "reviewer-a", "outcome": "PASS", "sku": "SKU-1"},
            "supplier_quotes": quotes,
            "landed_cost": {"artifact_ref": "private://evidence/landed-cost", "calculated_on": recent,
                            "verified": True, "reviewed_by": "reviewer-a",
                            "component_costs_dzd": {"purchase": 470, "packaging": 30, "inbound_transport": 20},
                            "unit_cost_dzd": 520, "source_quote_ids": ["quote-2"]},
            "courier_quote": {"artifact_ref": "private://evidence/courier", "quoted_on": recent,
                              "valid_until": later, "seller_account_verified": True, "origin_wilaya": "Blida",
                              "coverage_wilayas": ["Blida", "Alger"], "outbound_dzd": 450,
                              "failed_delivery_dzd": 250, "return_dzd": 200, "cod_remittance_days": 5,
                              "contract_or_quote_id": "carrier-quote-1"},
        }

    @staticmethod
    def add_test_evidence(candidate, cohort_count=1):
        from datetime import date, timedelta
        today = date.today()
        recent = today.isoformat()
        candidate["pilot_campaign"] = {
            "artifact_ref": "private://evidence/campaign-1",
            "started_on": (today - timedelta(days=7)).isoformat(), "ended_on": recent,
            "platform": "Meta Ads", "creative_id": "creative-001", "attribution_method": "tracked form + CRM",
            "spend_dzd": 15000, "placed_orders": 50, "attributed_orders": 40,
        }
        candidate["order_cohorts"] = []
        for i in range(cohort_count):
            end = today - timedelta(days=(cohort_count - i - 1) * 7)
            start = end - timedelta(days=6)
            candidate["order_cohorts"].append({
                "artifact_ref": f"private://evidence/cohort-{i+1}",
                "started_on": start.isoformat(), "ended_on": end.isoformat(),
                "cohort_id": f"cohort-{i+1}", "sku": candidate["sku"], "reconciled": True,
                "reconciled_by": "operations-reviewer", "placed_orders": 50, "delivered_orders": 35,
                "failed_orders": 15, "returned_orders": 2, "retained_orders": 33,
            })
        return candidate

    def test_listing_without_supplier_quote_stays_research_only(self):
        from opportunity import assess_candidate
        result = assess_candidate({"id": "listing-only", "market_price_observed_dzd": {"low": 100, "high": 200}})
        self.assertEqual(result["stage"], "RESEARCH_ONLY")
        self.assertFalse(result["is_profitability_score"])
        self.assertFalse(result["is_investment_approval"])

    def test_research_evidence_must_not_skip_the_pilot_gate(self):
        from opportunity import assess_candidate
        candidate = self.research_ready_candidate()
        result = assess_candidate(candidate)
        self.assertEqual(result["stage"], "PRETEST_READY")
        self.assertEqual(result["valid_supplier_quote_count"], 2)
        self.assertTrue(result["missing_test_gates"])

    def test_supplier_quotes_must_be_current_and_for_two_verified_sellers(self):
        from datetime import date, timedelta
        from opportunity import assess_candidate
        candidate = self.research_ready_candidate()
        candidate["supplier_quotes"][1]["supplier_id"] = "supplier-a"
        result = assess_candidate(candidate)
        self.assertEqual(result["stage"], "RESEARCH_ONLY")
        self.assertEqual(result["valid_supplier_quote_count"], 1)

        candidate = self.research_ready_candidate()
        candidate["supplier_quotes"][1]["valid_until"] = (date.today() - timedelta(days=1)).isoformat()
        result = assess_candidate(candidate)
        self.assertEqual(result["stage"], "RESEARCH_ONLY")

    def test_expired_courier_quote_blocks_research_gate(self):
        from datetime import date, timedelta
        from opportunity import assess_candidate
        candidate = self.research_ready_candidate()
        candidate["courier_quote"]["valid_until"] = (date.today() - timedelta(days=1)).isoformat()
        self.assertEqual(assess_candidate(candidate)["stage"], "RESEARCH_ONLY")

    def test_stale_supplier_quote_does_not_count(self):
        from datetime import date, timedelta
        from opportunity import assess_candidate
        candidate = self.research_ready_candidate()
        candidate["supplier_quotes"][1]["quoted_on"] = (date.today() - timedelta(days=120)).isoformat()
        candidate["supplier_quotes"][1]["valid_until"] = (date.today() + timedelta(days=30)).isoformat()
        self.assertEqual(assess_candidate(candidate)["stage"], "RESEARCH_ONLY")
        self.assertEqual(assess_candidate(candidate)["valid_supplier_quote_count"], 1)

    def test_landed_cost_must_reconcile_with_its_components(self):
        from opportunity import assess_candidate
        candidate = self.research_ready_candidate()
        candidate["landed_cost"]["unit_cost_dzd"] = 900
        self.assertEqual(assess_candidate(candidate)["stage"], "RESEARCH_ONLY")

    def test_single_cohort_needs_repeatability_before_scale_review(self):
        from opportunity import assess_candidate
        candidate = self.add_test_evidence(self.research_ready_candidate(), cohort_count=1)
        result = assess_candidate(candidate)
        self.assertEqual(result["stage"], "TESTED_SINGLE_COHORT")
        self.assertEqual(result["valid_reconciled_cohort_count"], 1)

    def test_scale_review_requires_two_distinct_reconciled_cohorts(self):
        from opportunity import assess_candidate
        candidate = self.add_test_evidence(self.research_ready_candidate(), cohort_count=2)
        result = assess_candidate(candidate)
        self.assertEqual(result["stage"], "SCALE_REVIEW_CANDIDATE")
        self.assertFalse(result["is_investment_approval"])

    def test_inconsistent_order_cohort_counts_do_not_pass_test_gate(self):
        from opportunity import assess_candidate
        candidate = self.add_test_evidence(self.research_ready_candidate(), cohort_count=1)
        candidate["order_cohorts"][0]["retained_orders"] = 50
        result = assess_candidate(candidate)
        self.assertEqual(result["stage"], "PRETEST_READY")
        self.assertEqual(result["valid_reconciled_cohort_count"], 0)

    def test_wholesale_discovery_platforms_are_not_supplier_quotes(self):
        from pathlib import Path
        from opportunity import load_snapshot
        snapshot = load_snapshot(Path(__file__).resolve().parent.parent / "data" / "research_snapshot_2026-10-29.json")
        self.assertEqual(len(snapshot["sourcing_leads"]), 5)
        self.assertTrue(all(lead["status"] in {"DISCOVERY_LEAD_ONLY", "CONTACT_REQUIRED_NOT_VERIFIED"} for lead in snapshot["sourcing_leads"]))
        self.assertTrue(all(lead["quote_verified"] is False for lead in snapshot["sourcing_leads"]))
        self.assertEqual(snapshot["verified_supplier_quote_count"], 0)

    def test_registry_rejects_sourcing_lead_with_unknown_source(self):
        from pathlib import Path
        import json
        import tempfile
        from opportunity import load_snapshot
        path = Path(__file__).resolve().parent.parent / "data" / "research_snapshot_2026-10-29.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        source["sourcing_leads"][0]["platform_source_id"] = "missing-source"
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
