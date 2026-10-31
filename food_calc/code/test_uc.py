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
