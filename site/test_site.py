"""Tests for the DSTMeta website API helpers.

Run with ``py site/test_site.py``.
"""

import json
import re
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

    def test_every_food_has_a_russian_name(self):
        missing = sorted(
            set(server.alg.known_foods()) - set(server.RU_NAMES)
        )
        self.assertEqual(missing, [])

    def test_every_uc_food_has_a_russian_name(self):
        missing = sorted(
            set(server.alg.known_foods("uc")) - set(server.RU_NAMES)
        )
        self.assertEqual(missing, [])

    def test_russian_names_follow_the_wiki(self):
        self.assertEqual(server.RU_NAMES["Fish"], "Рыба")
        self.assertEqual(server.RU_NAMES["Morsel"], "Кусочек мяса")
        self.assertEqual(server.RU_NAMES["Fish Morsel"], "Кусочек рыбы")
        self.assertEqual(server.RU_NAMES["Grim Galette"], "Зловещий пирог")
        self.assertEqual(server.RU_NAMES["Ice"], "Лёд")
        self.assertEqual(server.RU_NAMES["Forget-Me-Lots"], "Позабудка")
        self.assertEqual(server.RU_NAMES["Tillweeds"], "Сорняк")
        self.assertEqual(server.RU_NAMES["Heat Gland"], "Тепловая железа")
        self.assertEqual(server.RU_NAMES["Meaty Stew"], "Мясная похлёбка")
        self.assertEqual(server.RU_NAMES["Cooked Morsel"], "Приготовленный кусочек мяса")
        self.assertEqual(server.RU_NAMES["Beefalo Horn"], "Рог бифало")
        self.assertEqual(server.RU_NAMES["Rabbit"], "Кролик")

    def test_russian_input_matches_english(self):
        english = server.calculate(
            {"ingredients": "Meat\nMeat\nMeat\nIce", "stat": "Hunger"}
        )
        russian = server.calculate(
            {
                "ingredients": "Мясо\nМясо\nМясо\nЛёд",
                "stat": "Hunger",
                "lang": "ru",
            }
        )

        self.assertEqual(russian["lang"], "ru")
        self.assertEqual(russian["total"], english["total"])
        self.assertEqual(russian["plan"], english["plan"])
        self.assertEqual(russian["ingredients"], english["ingredients"])

    def test_russian_input_ignores_the_yo_diaeresis(self):
        with_yo = server.calculate(
            {"ingredients": "Мясо\nМясо\nМясо\nЛёд", "stat": "Hunger"}
        )
        without_yo = server.calculate(
            {"ingredients": "Мясо\nМясо\nМясо\nЛед", "stat": "Hunger"}
        )
        self.assertEqual(with_yo["total"], without_yo["total"])

    def test_russian_unknown_ingredient_error_is_localized(self):
        with self.assertRaises(ValueError) as caught:
            server.calculate(
                {
                    "ingredients": "Мясо\nТайный фрукт",
                    "stat": "Hunger",
                    "lang": "ru",
                }
            )
        message = str(caught.exception)
        self.assertIn("Тайный фрукт", message)
        self.assertIn("не еда", message)
        self.assertIn("Уберите", message)

    def test_russian_limit_error_is_localized(self):
        payload = "\n".join(["Мясо"] * (server.MAX_INGREDIENTS + 1))
        with self.assertRaises(ValueError) as caught:
            server.calculate(
                {"ingredients": payload, "stat": "Hunger", "lang": "ru"}
            )
        self.assertIn("Слишком много ингредиентов", str(caught.exception))

    def test_mode_defaults_to_dst(self):
        result = server.calculate({"ingredients": "Meat\nMeat\nMeat\nMeat"})
        self.assertEqual(result["mode"], "dst")
        self.assertEqual(result["bestDish"]["name"], "Meaty Stew")

    def test_uc_mode_uses_uc_data(self):
        result = server.calculate(
            {
                "ingredients": "Boomberry\nBoomberry\nEgg\nEgg",
                "mode": "uc",
            }
        )
        self.assertEqual(result["mode"], "uc")
        self.assertEqual(result["bestDish"]["name"], "Boomberry Pancakes")
        self.assertEqual(result["bestDish"]["stats"]["Hunger"], 75.0)
        self.assertEqual(result["plan"][0]["food"], "Boomberry Pancakes")

    def test_uc_ingredients_are_rejected_in_dst(self):
        with self.assertRaises(ValueError):
            server.calculate(
                {"ingredients": "Boomberry\nBoomberry\nEgg\nEgg"}
            )

    def test_russian_uc_ingredient_is_accepted(self):
        result = server.calculate(
            {
                "ingredients": "Бумберри\nБумберри\nЯйцо\nЯйцо",
                "mode": "uc",
                "lang": "ru",
            }
        )
        self.assertEqual(result["bestDish"]["name"], "Boomberry Pancakes")

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            server.calculate(
                {"ingredients": "Meat\nMeat\nMeat\nMeat", "mode": "hardcore"}
            )
        self.assertIn("mode", str(caught.exception))


class PickerTest(unittest.TestCase):
    """The ingredient picker, its order and its icon set."""

    # Items that are not crockpot ingredients and cannot be cooked, dried or
    # roasted; they stay out of the menu.
    TRINKETS = (
        "Dead Wobster",
        "Delicious Wobster",
        "Gears",
        "Hatching Tallbird Egg",
        "Lune Tree Blossom",
        "Phlegm",
        "Rotten Egg",
        "Succulent",
        "Wet Goop",
    )

    @staticmethod
    def slug(name):
        return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    def test_picker_only_offers_crockpot_ingredients(self):
        for name in server.alg.picker_foods():
            self.assertIn(name, server.alg.VALUES, name)
            self.assertNotIn(name, server.alg._RECIPE_DISHES)
            self.assertNotIn(name, server.alg._HAT_DISHES)

    def test_picker_skips_dishes_and_trinkets(self):
        picker = set(server.alg.picker_foods())
        for name in self.TRINKETS:
            self.assertNotIn(name, picker)
        for dish in ("Meatballs", "Meaty Stew", "Butter Muffin", "Trail Mix"):
            self.assertNotIn(dish, picker)

    def test_picker_offers_every_value_ingredient_once(self):
        foods = server.alg.picker_foods()
        self.assertEqual(len(foods), len(set(foods)))
        expected = set(server.alg.VALUES) - server.alg._RECIPE_DISHES - server.alg._HAT_DISHES
        self.assertEqual(set(foods), expected)

    def test_picker_follows_the_wiki_food_value_order(self):
        foods = server.alg.picker_foods()
        self.assertEqual(
            foods[:5],
            ["Barnacles", "Cooked Barnacles", "Morsel", "Cooked Morsel", "Drumstick"],
        )
        self.assertLess(foods.index("Morsel"), foods.index("Meat"))
        self.assertLess(foods.index("Meat"), foods.index("Berries"))
        self.assertLess(foods.index("Berries"), foods.index("Carrot"))
        self.assertLess(foods.index("Carrot"), foods.index("Ice"))
        self.assertLess(foods.index("Ice"), foods.index("Birchnut"))
        # Extras that the wiki page does not list sit next to their relatives.
        self.assertEqual(
            foods[foods.index("Banana") : foods.index("Banana") + 4],
            ["Banana", "Cooked Banana", "Cave Banana", "Cooked Cave Banana"],
        )
        self.assertEqual(
            foods[foods.index("Mandrake") : foods.index("Mandrake") + 2],
            ["Mandrake", "Cooked Mandrake"],
        )

    def test_group_names_have_no_duplicate_slugs(self):
        slugs = {}
        for name in server.alg.known_foods():
            key = self.slug(name)
            self.assertNotIn(key, slugs, f"{name} collides with {slugs.get(key)}")
            slugs[key] = name

    def test_every_food_has_an_icon_file(self):
        icons = server.ROOT / "icons"
        self.assertTrue(icons.is_dir(), "site/icons is missing")
        missing = [
            name
            for name in server.alg.known_foods()
            if not (icons / f"{self.slug(name)}.png").is_file()
        ]
        self.assertEqual(missing, [])

    def test_uc_picker_offers_every_uc_ingredient_once(self):
        data = server.alg._dataset("uc")
        foods = server.alg.picker_foods("uc")
        self.assertEqual(len(foods), len(set(foods)))
        expected = set(data.values) - data.recipe_dishes - server.alg._HAT_DISHES
        self.assertEqual(set(foods), expected)
        for name in (
            "Boomberry",
            "Gloom Berry",
            "Zaspberry",
            "Rice Grains",
            "Monster Morsel",
            "Monster Egg",
            "Scorpion Carapace",
            "Green Foliage",
        ):
            self.assertIn(name, foods)

    def test_uc_rebalanced_ingredients_are_pickable(self):
        foods = server.alg.picker_foods("uc")
        for name in ("Beefalo Horn", "Rabbit", "Fire Nettle Fronds"):
            with self.subTest(name=name):
                self.assertIn(name, foods)

    def test_uc_dishes_are_not_pot_ingredients(self):
        foods = set(server.alg.picker_foods("uc"))
        for dish in server.alg._dataset("uc").recipe_dishes:
            self.assertNotIn(dish, foods)

    def test_uc_picker_ingredients_have_icons(self):
        icons = server.ROOT / "icons"
        missing = [
            name
            for name in server.alg.picker_foods("uc")
            if not (icons / f"{self.slug(name)}.png").is_file()
        ]
        self.assertEqual(missing, [])

    def test_uc_group_names_have_no_duplicate_slugs(self):
        slugs = {}
        for name in server.alg.known_foods("uc"):
            key = self.slug(name)
            self.assertNotIn(key, slugs, f"{name} collides with {slugs.get(key)}")
            slugs[key] = name

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

    def test_russian_names_file_is_served(self):
        with urllib.request.urlopen(self.base + "/names_ru.json", timeout=5) as response:
            self.assertEqual(response.status, 200)
            names = json.load(response)
        self.assertEqual(names["Fish"], "Рыба")

    def test_foods_endpoint_returns_the_picker_list(self):
        with urllib.request.urlopen(self.base + "/api/foods", timeout=5) as response:
            self.assertEqual(response.status, 200)
            payload = json.load(response)
        self.assertEqual(payload["foods"], server.alg.picker_foods())
        self.assertNotIn("categories", payload)
        self.assertEqual(payload["foods"][0], "Barnacles")
        self.assertNotIn("Meatballs", payload["foods"])
        self.assertEqual(payload["maxIngredients"], server.MAX_INGREDIENTS)
        self.assertEqual(payload["maxIngredientTypes"], server.MAX_INGREDIENT_TYPES)

    def test_foods_endpoint_can_select_uc_mode(self):
        with urllib.request.urlopen(
            self.base + "/api/foods?mode=uc", timeout=5
        ) as response:
            self.assertEqual(response.status, 200)
            payload = json.load(response)
        self.assertEqual(payload["mode"], "uc")
        self.assertEqual(payload["foods"], server.alg.picker_foods("uc"))
        self.assertIn("Boomberry", payload["foods"])
        self.assertNotIn("Boomberry", server.alg.picker_foods())

    def test_foods_endpoint_rejects_an_unknown_mode(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(
                self.base + "/api/foods?mode=hardcore", timeout=5
            )
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()

    def test_icons_are_served(self):
        with urllib.request.urlopen(self.base + "/icons/meat.png", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
    def test_calculate_endpoint_localizes_errors(self):
        body = json.dumps(
            {
                "ingredients": "Мясо\nТайный фрукт",
                "stat": "Hunger",
                "lang": "ru",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base + "/api/calculate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 400)
        payload = json.load(caught.exception)
        caught.exception.close()
        self.assertIn("не еда", payload["error"])


if __name__ == "__main__":
    unittest.main()
