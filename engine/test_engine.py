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

if __name__ == "__main__":
    unittest.main()
