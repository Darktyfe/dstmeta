"""Uncompromising Mode tests.  Run with ``py food_calc/code/test_uc.py``.

The examples come from the wiki's Crock Pot recipe table and its Uncompromising
Mode dish pages.  Every rule is checked against the DST data as well, because
selecting the mode must not leak into the default behaviour.
"""

import unittest

import alg


UC_ONLY = {
    "Boomberry Pancakes": ("Boomberry", "Boomberry", "Egg", "Egg"),
    "California King": ("Wobster", "Barnacles", "Pepper", "Ice"),
    "Deviled Eggs": ("Monster Egg", "Monster Egg", "Egg", "Egg"),
    "Devils Fruit Cake": ("Pomegranate", "Egg", "Egg", "Honey"),
    "Gloomberry Jam": ("Gloom Berry", "Boomberry", "Carrot", "Carrot"),
    "Hard Shell Tacos": (
        "Scorpion Carapace",
        "Scorpion Carapace",
        "Carrot",
        "Twigs",
    ),
    "Liceloaf": ("Rice Grains", "Rice Grains", "Carrot", "Carrot"),
    "Seafood Paella": ("Rice Grains", "Carrot", "Wobster", "Blue Cap"),
    "Simple Salad": ("Foliage", "Foliage", "Carrot", "Carrot"),
    "Snot Roast": ("Koalefant Trunk", "Carrot", "Potato", "Onion"),
    "Snowcone": ("Ice", "Ice", "Twigs", "Twigs"),
    "Steamed Hams": ("Meat", "Foliage", "Carrot", "Carrot"),
    "Stuffed Peeper Poppers": (
        "Durian",
        "Milky Whites",
        "Monster Meat",
        "Monster Meat",
    ),
    "Zazpberry Parfait": ("Zaspberry", "Honey", "Butter", "Carrot"),
}

# Vanilla foods and dishes the mod rebalances (wiki Balance Changes/Food).
REBALANCED_STATS = {
    "Asparagus Soup": (25.0, 20.0, 30.0),
    "Barnacle Nigiri": (37.5, 15.0, 40.0),
    "Barnacle Pita": (37.5, 15.0, 8.0),
    "Creamy Potato Purée": (75.0, 15.0, 20.0),
    "Fancy Spiralled Tubers": (25.0, 15.0, 3.0),
    "Figgy Frogwich": (37.5, 33.0, 3.0),
    "Figkabab": (37.5, 10.0, 20.0),
    "Fish Tacos": (75.0, 5.0, 20.0),
    "Flower Salad": (12.5, 5.0, 60.0),
    "Ice Cream": (25.0, 100.0, 0.0),
    "Meatballs": (50.0, 5.0, 3.0),
    "Powdercake": (0.0, 0.0, -3.0),
    "Puffed Potato Soufflé": (50.0, 5.0, 60.0),
    "Pumpkin Cookies": (50.0, 33.0, 15.0),
    "Salsa Fresca": (25.0, 50.0, 3.0),
    "Seafood Gumbo": (100.0, 5.0, 5.0),
    "Stuffed Eggplant": (50.0, 5.0, 20.0),
    "Stuffed Pepper Poppers": (25.0, -5.0, 40.0),
    "Veggie Burger": (100.0, 5.0, 3.0),
}

REBALANCED_BASIC_STATS = {
    "Butterfly Wings": (2.5, 0.0, 1.0),
    "Cactus Flesh": (12.5, -5.0, -8.0),
    "Cooked Cactus Flesh": (12.5, 5.0, 1.0),
    "Eggplant": (18.75, 0.0, 8.0),
    "Braised Eggplant": (18.75, 0.0, 12.0),
    "Fire Nettle Fronds": (0.0, -5.0, -15.0),
    "Cooked Green Cap": (0.0, 15.0, -5.0),
    "Winter Koalefant Trunk": (37.5, 0.0, 30.0),
    "Cooked Monster Meat": (18.75, -10.0, -8.0),
    "Roasted Potato": (18.75, 0.0, 8.0),
    "Roasted Toma Root": (12.5, 0.0, 8.0),
    "Rot": (-10.0, -5.0, -5.0),
    "Seeds": (1.5, 0.0, 0.0),
    "Toasted Seeds": (1.5, 0.0, 1.0),
    "Honey": (2.5, 0.0, 1.0),
}


class UCRecipesTest(unittest.TestCase):
    def test_uc_only_dishes(self):
        for dish, ingredients in UC_ONLY.items():
            with self.subTest(dish=dish):
                self.assertEqual(alg.cook(ingredients, mode="uc"), dish)

    def test_deviled_eggs_beats_monster_lasagna(self):
        # Both tests match; the mod gives Deviled Eggs priority 52 and Monster
        # Lasagna priority 51.
        self.assertEqual(
            alg.cook(("Monster Egg", "Monster Egg", "Egg", "Egg"), mode="uc"),
            "Deviled Eggs",
        )

    def test_hard_shell_tacos_beat_monster_lasagna(self):
        # Two carapaces carry a full insectoid point, which the mod's Monster
        # Lasagna test rejects.
        self.assertEqual(
            alg.cook(
                ("Scorpion Carapace", "Scorpion Carapace", "Carrot", "Twigs"),
                mode="uc",
            ),
            "Hard Shell Tacos",
        )

    def test_monster_lasagna_needs_dilution(self):
        # Two monster meats are enough in DST; in UC both carry two monster
        # points, so they still make Lasagna.  One monster meat diluted with
        # normal meat does not.
        self.assertEqual(
            alg.cook(("Monster Meat", "Monster Meat", "Meat", "Meat"),
                     mode="uc"),
            "Monster Lasagna",
        )
        self.assertEqual(
            alg.cook(("Monster Meat", "Meat", "Meat", "Meat"), mode="uc"),
            "Meaty Stew",
        )

    def test_replaced_monster_lasagna_respects_ice_limit(self):
        # DST makes Lasagna here.  UC's Lasagna rejects more than one point of
        # ice, so the two ice cubes fall through to Snowcone instead of keeping
        # the old Lasagna row alive.
        self.assertEqual(
            alg.cook(("Monster Meat", "Monster Meat", "Ice", "Ice")),
            "Monster Lasagna",
        )
        self.assertEqual(
            alg.cook(("Monster Meat", "Monster Meat", "Ice", "Ice"),
                     mode="uc"),
            "Snowcone",
        )

    def test_replaced_kabobs_reject_ice(self):
        self.assertEqual(
            alg.cook(("Meat", "Twigs", "Ice", "Ice")),
            "Kabobs",
        )
        self.assertEqual(
            alg.cook(("Meat", "Twigs", "Ice", "Ice"), mode="uc"),
            "Snowcone",
        )

    def test_kabobs_still_allow_monster(self):
        self.assertEqual(
            alg.cook(("Monster Meat", "Twigs", "Carrot", "Carrot"),
                     mode="uc"),
            "Kabobs",
        )

    def test_liceloaf_filler_limit(self):
        self.assertEqual(
            alg.cook(("Rice Grains", "Rice Grains", "Carrot", "Ice"),
                     mode="uc"),
            "Liceloaf",
        )
        self.assertEqual(
            alg.cook(("Rice Grains", "Rice Grains", "Ice", "Ice"),
                     mode="uc"),
            "Snowcone",
        )

    def test_steamed_hams_accepts_green_foliage(self):
        self.assertEqual(
            alg.cook(("Meat", "Green Foliage", "Carrot", "Carrot"), mode="uc"),
            "Steamed Hams",
        )

    def test_cooked_rice_cannot_make_liceloaf(self):
        # rice_cooked only carries the vegetable tag in the mod.
        self.assertNotEqual(
            alg.cook(("Burnt Rice", "Burnt Rice", "Carrot", "Carrot"),
                     mode="uc"),
            "Liceloaf",
        )

    def test_simple_salad_rejects_ice_and_sweetener(self):
        self.assertNotEqual(
            alg.cook(("Foliage", "Foliage", "Ice", "Honey"), mode="uc"),
            "Simple Salad",
        )

    def test_snowcone_needs_ice(self):
        self.assertEqual(
            alg.cook(("Ice", "Twigs", "Carrot", "Berry"), mode="uc"),
            "Snowcone",
        )
        self.assertNotEqual(
            alg.cook(("Twigs", "Twigs", "Carrot", "Berry"), mode="uc"),
            "Snowcone",
        )


class UCRebalanceTest(unittest.TestCase):
    def test_rebalanced_dish_stats(self):
        for dish, stats in REBALANCED_STATS.items():
            with self.subTest(dish=dish):
                self.assertEqual(alg.get_food_stats(dish, mode="uc"), stats)

    def test_rebalanced_basic_food_stats(self):
        for food, stats in REBALANCED_BASIC_STATS.items():
            with self.subTest(food=food):
                self.assertEqual(alg.get_food_stats(food, mode="uc"), stats)

    def test_rebalanced_stats_do_not_leak_into_dst(self):
        # Barnacle Nigiri, Figkabab and Powdercake already disagree with the
        # wiki in the base files; the overlay only corrects them in UC mode.
        self.assertEqual(alg.get_food_stats("Barnacle Nigiri"), (37.5, 5.0, 40.0))
        self.assertEqual(alg.get_food_stats("Figkabab"), (25.0, 15.0, 20.0))
        self.assertEqual(alg.get_food_stats("Powdercake"), (0.0, 0.0, 3.0))
        self.assertEqual(alg.get_food_stat("Seeds", "Hunger"), 4.6875)

    def test_barnacle_nigiri_no_longer_needs_eggs(self):
        ingredients = ("Barnacles", "Kelp Fronds", "Carrot", "Carrot")
        self.assertEqual(alg.cook(ingredients), "Barnacle Pita")
        self.assertEqual(alg.cook(ingredients, mode="uc"), "Barnacle Nigiri")

    def test_bunny_stew_needs_rabbit_and_two_frozen_items(self):
        self.assertEqual(
            alg.cook(("Rabbit", "Ice", "Ice", "Carrot"), mode="uc"),
            "Bunny Stew",
        )
        self.assertNotEqual(
            alg.cook(("Rabbit", "Ice", "Carrot", "Carrot"), mode="uc"),
            "Bunny Stew",
        )
        # DST only looks at the meat and ice values, so a morsel works.
        self.assertEqual(alg.cook(("Morsel", "Ice", "Ice", "Carrot")), "Bunny Stew")
        self.assertNotEqual(
            alg.cook(("Morsel", "Ice", "Ice", "Carrot"), mode="uc"),
            "Bunny Stew",
        )

    def test_meaty_stew_needs_three_and_a_half_meat(self):
        self.assertEqual(alg.cook(("Meat", "Meat", "Meat", "Carrot")), "Meaty Stew")
        self.assertEqual(
            alg.cook(("Meat", "Meat", "Meat", "Carrot"), mode="uc"),
            "Meatballs",
        )
        self.assertEqual(
            alg.cook(("Meat", "Meat", "Meat", "Morsel"), mode="uc"),
            "Meaty Stew",
        )

    def test_pierogi_needs_one_and_a_half_vegetables(self):
        self.assertEqual(alg.cook(("Egg", "Meat", "Carrot", "Ice")), "Pierogi")
        self.assertNotEqual(
            alg.cook(("Egg", "Meat", "Carrot", "Ice"), mode="uc"),
            "Pierogi",
        )
        self.assertEqual(
            alg.cook(("Egg", "Meat", "Carrot", "Carrot"), mode="uc"),
            "Pierogi",
        )

    def test_seafood_gumbo_needs_three_fish_and_three_meat(self):
        self.assertEqual(
            alg.cook(("Fish", "Fish", "Fish", "Meat"), mode="uc"),
            "Seafood Gumbo",
        )
        self.assertEqual(
            alg.cook(("Fish", "Fish", "Meat", "Meat"), mode="uc"),
            "Surf 'n' Turf",
        )

    def test_surf_and_turf_needs_two_fish(self):
        ingredients = ("Meat", "Meat", "Fish Morsel", "Fish")
        self.assertEqual(alg.cook(ingredients), "Surf 'n' Turf")
        self.assertNotEqual(
            alg.cook(ingredients, mode="uc"),
            "Surf 'n' Turf",
        )

    def test_figkabab_rejects_ice(self):
        ingredients = ("Fig", "Meat", "Twigs", "Ice")
        self.assertEqual(alg.cook(ingredients), "Figkabab")
        self.assertNotEqual(alg.cook(ingredients, mode="uc"), "Figkabab")

    def test_tall_scotch_eggs_need_three_vegetables(self):
        two_vegetables = ("Tallbird Egg", "Carrot", "Carrot", "Ice")
        self.assertEqual(alg.cook(two_vegetables), "Tall Scotch Eggs")
        self.assertNotEqual(
            alg.cook(two_vegetables, mode="uc"),
            "Tall Scotch Eggs",
        )
        self.assertEqual(
            alg.cook(("Tallbird Egg", "Carrot", "Carrot", "Carrot"),
                     mode="uc"),
            "Tall Scotch Eggs",
        )

    def test_unagi_priority_beats_surf_and_turf(self):
        ingredients = ("Eel", "Kelp Fronds", "Fish", "Meat")
        self.assertEqual(alg.cook(ingredients), "Surf 'n' Turf")
        self.assertEqual(alg.cook(ingredients, mode="uc"), "Unagi")

    def test_monster_tartare_needs_four_monster(self):
        self.assertEqual(
            alg.cook(("Monster Meat", "Monster Meat", "Carrot", "Carrot"),
                     warly=True, mode="uc"),
            "Monster Tartare",
        )
        self.assertNotEqual(
            alg.cook(("Monster Meat", "Meat", "Meat", "Carrot"),
                     warly=True, mode="uc"),
            "Monster Tartare",
        )

    def test_overlay_priorities(self):
        priorities = {}
        data = alg._dataset("uc")
        for name, _, _, priority in data.recipes + data.warly_recipes:
            priorities.setdefault(name, set()).add(priority)
        self.assertEqual(priorities["Bacon and Eggs"], {9})
        self.assertEqual(priorities["Seafood Gumbo"], {31})
        self.assertEqual(priorities["Unagi"], {52})
        self.assertEqual(priorities["Monster Tartare"], {52})

    def test_uc_ingredient_values(self):
        self.assertEqual(alg.ingredient_tags("Beefalo Horn", "uc")["meat"], 1.0)
        self.assertEqual(alg.ingredient_tags("Rabbit", "uc")["meat"], 0.5)
        self.assertEqual(
            alg.ingredient_tags("Fire Nettle Fronds", "uc")["foliage"], 1.0
        )
        for trunk in (
            "Koalefant Trunk",
            "Winter Koalefant Trunk",
            "Koalefant Trunk Steak",
        ):
            with self.subTest(trunk=trunk):
                self.assertEqual(alg.ingredient_tags(trunk, "uc")["meat"], 2.0)

    def test_new_uc_ingredients_are_pickable(self):
        picker = alg.picker_foods("uc")
        for name in ("Beefalo Horn", "Rabbit", "Fire Nettle Fronds"):
            with self.subTest(name=name):
                self.assertIn(name, picker)
        self.assertNotIn("Beefalo Horn", alg.picker_foods())
        self.assertNotIn("Rabbit", alg.picker_foods())
        self.assertNotIn("Fire Nettle Fronds", alg.picker_foods())


class UCModeTest(unittest.TestCase):
    def test_dst_does_not_know_uc_dishes(self):
        for dish in UC_ONLY:
            with self.subTest(dish=dish):
                self.assertIsNone(alg.get_food_stats(dish))
                self.assertNotIn(dish, alg.picker_foods())

    def test_uc_stats(self):
        expected = {
            "Boomberry Pancakes": (75.0, 20.0, 5.0),
            "California King": (62.5, -15.0, 3.0),
            "Deviled Eggs": (18.75, -20.0, -15.0),
            "Devils Fruit Cake": (62.5, -0.6, 60.0),
            "Gloomberry Jam": (37.5, 15.0, 40.0),
            "Hard Shell Tacos": (37.5, 5.0, 20.0),
            "Liceloaf": (62.5, 0.0, 0.0),
            "Seafood Paella": (75.0, 60.0, 20.0),
            "Simple Salad": (6.25, 5.0, 3.0),
            "Snot Roast": (150.0, 5.0, 3.0),
            "Snowcone": (9.375, 5.0, 3.0),
            "Steamed Hams": (37.5, 15.0, 40.0),
            "Stuffed Peeper Poppers": (37.5, -15.0, -3.0),
            "Zazpberry Parfait": (37.5, 15.0, 40.0),
        }
        for dish, stats in expected.items():
            with self.subTest(dish=dish):
                self.assertEqual(alg.get_food_stats(dish, mode="uc"), stats)

    def test_uc_ingredients_are_pickable(self):
        picker = alg.picker_foods("uc")
        for name in (
            "Boomberry",
            "Gloom Berry",
            "Zaspberry",
            "Rice Grains",
            "Monster Morsel",
            "Monster Egg",
            "Scorpion Carapace",
            "Foliage",
            "Forget-Me-Lots",
        ):
            with self.subTest(name=name):
                self.assertIn(name, picker)

    def test_uc_dishes_are_not_pot_ingredients(self):
        for dish in UC_ONLY:
            with self.subTest(dish=dish):
                self.assertNotIn(dish, alg.picker_foods("uc"))

    def test_resolve_food_name_is_mode_aware(self):
        self.assertIsNone(alg.resolve_food_name("Boomberry"))
        self.assertEqual(alg.resolve_food_name("Boomberry", "uc"), "Boomberry")
        self.assertEqual(
            alg.resolve_food_name("boomberries", "uc"), "Boomberry"
        )

    def test_uc_plan_uses_uc_data(self):
        inventory = ("Boomberry", "Boomberry", "Egg", "Egg")
        total, actions = alg.find_best_plan(inventory, mode="uc")
        self.assertEqual(total, 75.0)
        self.assertEqual(actions, [("cook", ("Boomberry", "Boomberry", "Egg", "Egg"),
                                    "Boomberry Pancakes")])
        dst_total, _ = alg.find_best_plan(inventory)
        self.assertNotEqual(dst_total, 75.0)

    def test_uc_data_files_have_no_warnings(self):
        self.assertEqual(alg.data_warnings("uc"), [])

    def test_default_mode_is_dst(self):
        self.assertEqual(alg.cook(("Meat",) * 4), "Meaty Stew")
        self.assertEqual(alg.cook(("Meat",) * 4, mode="dst"), "Meaty Stew")
        with self.assertRaises(ValueError):
            alg.cook(("Meat",) * 4, mode="unknown")


if __name__ == "__main__":
    unittest.main()
