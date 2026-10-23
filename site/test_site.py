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

    def test_unknown_ingredients_are_rejected(self):
        with self.assertRaises(ValueError) as caught:
            server.calculate(
                {
                    "ingredients": "Meat\nMeat\nMystery Fruit\nIce",
                    "stat": "Hunger",
                }
            )
        message = str(caught.exception)
        self.assertIn("Mystery Fruit", message)
        self.assertIn("is not a food", message)
        self.assertIn("removed", message)

    def test_tomato_is_rejected_with_a_hint(self):
        with self.assertRaises(ValueError) as caught:
            server.calculate(
                {
                    "ingredients": "Tomato\nTomato\nTomato\nTomato",
                    "stat": "Hunger",
                }
            )
        self.assertEqual(
            str(caught.exception),
            "'Tomato' is not a food and should be removed from the ingredient list.",
        )

    def test_multiple_unknown_ingredients_are_listed_once(self):
        with self.assertRaises(ValueError) as caught:
            server.calculate(
                {
                    "ingredients": "Tomato\nMystery Fruit\nTomato\nMeat",
                    "stat": "Hunger",
                }
            )
        message = str(caught.exception)
        self.assertIn("'Tomato'", message)
        self.assertIn("'Mystery Fruit'", message)
        self.assertIn("are not foods", message)

    def test_too_many_ingredients_is_rejected(self):
        payload = "\n".join(["Meat"] * (server.MAX_INGREDIENTS + 1))
        with self.assertRaises(ValueError):
            server.calculate({"ingredients": payload, "stat": "Hunger"})

    def test_engine_is_reported(self):
        result = server.calculate({"ingredients": "Meat\nMeat\nMeat\nIce", "stat": "Hunger"})
        self.assertIn(result["engine"], ("C++", "Python"))

    def test_dried_variants_are_ignored_by_default(self):
        result = server.calculate(
            {"ingredients": "Meat\nMeat\nMeat\nMeat", "stat": "Sanity"}
        )
        self.assertFalse(result["dried"])
        self.assertEqual(result["total"], 5)
        self.assertFalse(any(step["kind"] == "dry" for step in result["plan"]))

    def test_dried_variants_can_be_enabled(self):
        result = server.calculate(
            {
                "ingredients": "Meat\nMeat\nMeat\nMeat",
                "stat": "Sanity",
                "ignoreDried": False,
            }
        )
        self.assertTrue(result["dried"])
        self.assertEqual(result["total"], 60)
        dry = [step for step in result["plan"] if step["kind"] == "dry"]
        self.assertEqual(len(dry), 4)
        self.assertTrue(all(step["source"] == "Meat" for step in dry))
        self.assertTrue(all(step["food"] == "Jerky" for step in dry))


if __name__ == "__main__":
    unittest.main()
