"""Tests for the DSTMeta website API helpers.

Run with ``py site/test_site.py``.
"""

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
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

    def test_ingredient_limit_can_be_raised(self):
        original = server.MAX_INGREDIENTS
        try:
            server.MAX_INGREDIENTS = 24
            names = server.parse_ingredients("\n".join(["Meat"] * 24))
            self.assertEqual(len(names), 24)
            with self.assertRaises(ValueError):
                server.parse_ingredients("\n".join(["Meat"] * 25))
        finally:
            server.MAX_INGREDIENTS = original

    def test_too_many_ingredient_types_is_rejected(self):
        foods = server.alg.known_foods()[: server.MAX_INGREDIENT_TYPES + 1]
        with self.assertRaises(ValueError) as caught:
            server.calculate({"ingredients": "\n".join(foods), "stat": "Hunger"})
        self.assertIn("different ingredients", str(caught.exception))

    def test_type_limit_can_be_raised(self):
        original = server.MAX_INGREDIENT_TYPES
        try:
            server.MAX_INGREDIENT_TYPES = 2
            server.check_ingredient_types(["Meat", "Meat", "Ice"])
            with self.assertRaises(ValueError):
                server.check_ingredient_types(["Meat", "Ice", "Berries"])
        finally:
            server.MAX_INGREDIENT_TYPES = original

    def test_large_inventory_uses_the_fast_plan(self):
        backpack = (
            ["Berries"] * 12
            + ["Monster Meat"] * 5
            + ["Blue Cap"] * 3
            + ["Red Cap"] * 3
            + ["Green Cap"] * 2
            + ["Carrot"] * 4
            + ["Butterfly Wings"] * 20
            + ["Drumstick"] * 4
            + ["Meat"] * 2
            + ["Twigs"] * 20
        )
        result = server.calculate(
            {"ingredients": "\n".join(backpack), "stat": "Hunger"}
        )
        self.assertFalse(result["exact"])
        self.assertEqual(result["engine"], "Python")
        self.assertGreaterEqual(result["total"], 1000)
        self.assertAlmostEqual(result["totals"]["Hunger"], result["total"])
        self.assertEqual(len(result["ingredients"]), len(backpack))

    def test_engine_is_reported(self):
        result = server.calculate({"ingredients": "Meat\nMeat\nMeat\nIce", "stat": "Hunger"})
        self.assertIn(result["engine"], ("C++", "Python"))
        self.assertTrue(result["exact"])

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

    def test_over_time_stats_are_ignored_by_default(self):
        result = server.calculate(
            {"ingredients": "Forget-Me-Lots\nHoney\nIce\nIce", "stat": "Sanity"}
        )
        self.assertFalse(result["overTime"])
        self.assertEqual(result["total"], 15)
        self.assertEqual(result["totals"], {"Hunger": 0.0, "Sanity": 15.0, "Health": 3.0})

    def test_over_time_stats_can_be_counted(self):
        result = server.calculate(
            {
                "ingredients": "Forget-Me-Lots\nHoney\nIce\nIce",
                "stat": "Sanity",
                "ignoreOverTime": False,
            }
        )
        self.assertTrue(result["overTime"])
        self.assertEqual(result["total"], 45)
        self.assertEqual(result["totals"]["Sanity"], 45)

    def test_milkmade_hat_is_ignored_by_default(self):
        ingredients = "Naked Nostrils\nKelp Fronds\nButter\nTwigs"
        result = server.calculate({"ingredients": ingredients, "stat": "Hunger"})
        self.assertFalse(result["milkmade"])
        names = [dish["name"] for dish in result["dishes"]]
        self.assertNotIn("Milkmade Hat", names)
        self.assertFalse(
            any(step["food"] == "Milkmade Hat" for step in result["plan"])
        )

    def test_milkmade_hat_can_be_allowed(self):
        ingredients = "Naked Nostrils\nKelp Fronds\nButter\nTwigs"
        result = server.calculate(
            {
                "ingredients": ingredients,
                "stat": "Hunger",
                "ignoreMilkmade": False,
            }
        )
        self.assertTrue(result["milkmade"])
        names = [dish["name"] for dish in result["dishes"]]
        self.assertIn("Milkmade Hat", names)


class HttpEndpointTest(unittest.TestCase):
    """The HTTP surface the browser and simple health probes use."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(
            target=cls.httpd.serve_forever, daemon=True
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def test_health_endpoint_returns_ok(self):
        with urllib.request.urlopen(
            self.base + "/health", timeout=5
        ) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response), {"status": "ok"})

    def test_unknown_path_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.base + "/does-not-exist", timeout=5)
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
