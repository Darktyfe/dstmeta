"""Tests for the DSTMeta website API helpers.

Run with ``py site/test_site.py``.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import server


class SiteApiTest(unittest.TestCase):
    def test_plan_uses_raw_pot_ingredients(self):
        result = server.calculate(
            {
                "ingredients": "Meat\nMeat\nMeat\nIce\nMeat",
                "stat": "Hunger",
            }
        )

        self.assertEqual(result["total"], 175)
        self.assertEqual(
            result["totals"], {"Hunger": 175.0, "Sanity": 5.0, "Health": 15.0}
        )

        cook = next(action for action in result["plan"] if action["kind"] == "cook")
        self.assertNotIn("Cooked Meat", cook["ingredients"])
        self.assertEqual(sorted(cook["ingredients"]), ["Ice", "Meat", "Meat", "Meat"])

        self.assertEqual(result["bestDish"]["name"], "Meaty Stew")
        self.assertNotIn("Cooked Meat", result["bestDish"]["combination"])

    def test_permissible_losses_change_the_plan(self):
        payload = {
            "ingredients": "Monster Meat\nMonster Meat\nIce\nIce",
            "stat": "Hunger",
            "warly": True,
            "losses": {"Hunger": 0, "Sanity": 0, "Health": 0},
        }
        no_loss = server.calculate(payload)
        self.assertEqual(no_loss["total"], 4.6)
        self.assertFalse(any(step["kind"] == "cook" for step in no_loss["plan"]))

        payload["losses"] = {"Hunger": 0, "Sanity": 20, "Health": 20}
        allowed = server.calculate(payload)
        self.assertEqual(allowed["total"], 62.5)
        self.assertTrue(any(step["kind"] == "cook" for step in allowed["plan"]))

    def test_plan_works_with_fewer_than_four_ingredients(self):
        result = server.calculate({"ingredients": "Carrot", "stat": "Health"})
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["plan"][0]["kind"], "roast")

    def test_calculate_rejects_non_object_payloads(self):
        with self.assertRaises(ValueError):
            server.calculate(["Meat", "Ice"])

    def test_unknown_ingredients_are_reported(self):
        result = server.calculate(
            {
                "ingredients": "Meat\nMeat\nMystery Fruit\nIce",
                "stat": "Hunger",
            }
        )
        self.assertEqual(result["unknown"], ["Mystery Fruit"])


if __name__ == "__main__":
    unittest.main()
