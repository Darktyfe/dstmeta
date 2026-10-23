"""Tests for the crockpot engine.  Run with ``py food_calc/code/test_alg.py``."""

import unittest

import alg


class CrockpotTest(unittest.TestCase):
    def test_four_meat_cooks_meaty_stew(self):
        self.assertEqual(alg.crockpot(("Meat",) * 4), "Meaty Stew")

    def test_meatballs_with_fruit(self):
        self.assertEqual(
            alg.crockpot(("Meat", "Berries", "Berries", "Berries")),
            "Meatballs",
        )

    def test_inedible_exclusion_blocks_meatballs(self):
        self.assertEqual(
            alg.crockpot(("Meat", "Twigs", "Twigs", "Twigs")),
            "Wet Goop",
        )

    def test_all_twigs_steams_twigs(self):
        self.assertEqual(alg.crockpot(("Twigs",) * 4), "Steamed Twigs")

    def test_priority_beats_meaty_stew(self):
        self.assertEqual(
            alg.crockpot(("Honey", "Meat", "Meat", "Meat")),
            "Honey Ham",
        )

    def test_dairy_tag(self):
        # Regression: recipes.txt used to say "*Diary", so dairy never matched.
        self.assertEqual(
            alg.crockpot(("Ice", "Butter", "Honey", "Berries")),
            "Ice Cream",
        )

    def test_fish_tag(self):
        # Fish morsels carry half meat and half fish: not enough meat for
        # Surf 'n' Turf, but enough fish for Seafood Gumbo.
        self.assertEqual(alg.crockpot(("Fish Morsel",) * 4), "Seafood Gumbo")
        # Big fish carry a full meat and fish point each.
        self.assertEqual(alg.crockpot(("Fish",) * 4), "Surf 'n' Turf")

    def test_egg_threshold(self):
        self.assertEqual(alg.crockpot(("Egg",) * 4), "Plain Omelette")

    def test_processed_names_keep_their_tags(self):
        self.assertEqual(alg.crockpot(("Cooked Meat",) * 4), "Meaty Stew")
        self.assertEqual(
            alg.crockpot(("Moleworm", "Ripe Stone Fruit", "Twigs", "Twigs")),
            "Guacamole",
        )

    def test_named_ingredient_tag(self):
        self.assertEqual(
            alg.crockpot(("Banana", "Ice", "Twigs", "Twigs")),
            "Banana Pop",
        )

    def test_unknown_ingredient_is_harmless(self):
        self.assertEqual(alg.crockpot(("Rot",) * 4), "Wet Goop")

    def test_requires_four_slots(self):
        with self.assertRaises(ValueError):
            alg.crockpot(("Meat", "Meat"))

    def test_dead_and_delicious_wobster_are_not_pot_ingredients(self):
        # The game only accepts a living Wobster in the Crock Pot.
        self.assertIsNone(
            alg.crockpot(("Dead Wobster", "Ice", "Twigs", "Meat"))
        )
        self.assertIsNone(
            alg.crockpot(("Delicious Wobster", "Ice", "Twigs", "Meat"))
        )

    def test_prepared_dishes_are_not_pot_ingredients(self):
        self.assertIsNone(
            alg.crockpot(("Meatballs", "Ice", "Twigs", "Meat"))
        )

    def test_cooked_mandrake_is_not_a_pot_ingredient(self):
        # Mandrake Soup needs a raw Mandrake; roasting it first is one-way.
        self.assertIsNone(
            alg.crockpot(("Cooked Mandrake", "Ice", "Twigs", "Meat"))
        )


class InventoryTest(unittest.TestCase):
    def test_cookable_dishes(self):
        dishes = alg.cookable_dishes(["Meat"] * 4 + ["Berries"] * 4)
        self.assertIn("Meaty Stew", dishes)
        self.assertIn("Meatballs", dishes)

    def test_best_single_dish(self):
        score, dish, combo = alg.best_single_dish(["Meat"] * 4, "Hunger")
        self.assertEqual(dish, "Meaty Stew")
        self.assertEqual(score, 150)
        self.assertEqual(len(combo), 4)

    def test_best_single_dish_prefers_raw_ingredients(self):
        # Cooking meat before putting it in the pot is unnecessary.
        score, dish, combo = alg.best_single_dish(
            ["Meat", "Meat", "Meat", "Ice"], "Hunger"
        )
        self.assertEqual(dish, "Meaty Stew")
        self.assertEqual(sorted(combo), ["Ice", "Meat", "Meat", "Meat"])

    def test_plan_does_not_cook_meat_for_the_pot(self):
        total, actions = alg.find_best_plan(
            ["Meat", "Meat", "Meat", "Meat", "Ice"], "Hunger"
        )
        self.assertEqual(total, 175)
        cook = next(action for action in actions if action[0] == "cook")
        self.assertEqual(sorted(cook[1]), ["Ice", "Meat", "Meat", "Meat"])
        self.assertEqual(alg.plan_totals(actions), {"Hunger": 175, "Sanity": 5, "Health": 15})

    def test_plan_can_leave_the_first_item_out_of_the_pot(self):
        # Regression: the search used to skip every plan where the first
        # (sorted) inventory item was eaten individually while later items were
        # still cooked.  Roasting the berries leaves the ice for the pot and
        # produces one more health point than the old 44.5 plan.
        total, actions = alg.find_best_plan(
            ["Honey", "Ice", "Fish", "Ice", "Twigs", "Fig", "Berries"],
            "Health",
            warly=True,
            losses={"Hunger": 5, "Sanity": 20, "Health": 0},
        )
        self.assertEqual(total, 45)
        self.assertAlmostEqual(alg.plan_totals(actions)["Health"], 45)

    def test_plan_lists_campfire_prep_for_pot_ingredients(self):
        # Roasting the fish morsel removes its meat tag, which lets the soup
        # recipe win; the plan has to show that campfire step.
        total, actions = alg.find_best_plan(
            ["Fish Morsel", "Onion", "Toma Root", "Roasted Potato", "Nightberry"],
            "Sanity",
        )
        self.assertEqual(total, 33)
        kinds = [action[0] for action in actions]
        self.assertIn("prep", kinds)
        self.assertLess(kinds.index("prep"), kinds.index("cook"))
        self.assertAlmostEqual(alg.plan_totals(actions)["Sanity"], 33)

    def test_permissible_losses(self):
        ingredients = ["Monster Meat", "Monster Meat", "Ice", "Ice"]
        # With no losses allowed, the negative Monster Tartare is rejected.
        total, actions = alg.find_best_plan(
            ingredients, "Hunger", warly=True
        )
        self.assertEqual(total, 4.6)
        self.assertFalse(any(action[0] == "cook" for action in actions))

        total, actions = alg.find_best_plan(
            ingredients,
            "Hunger",
            warly=True,
            losses={"Hunger": 0, "Sanity": 20, "Health": 20},
        )
        self.assertEqual(total, 62.5)
        self.assertTrue(any(action[0] == "cook" for action in actions))

    def test_losses_can_be_given_as_a_sequence(self):
        allowed = alg.normalize_losses([1, 2, 3])
        self.assertEqual(allowed, {"Hunger": 1.0, "Sanity": 2.0, "Health": 3.0})
        with self.assertRaises(ValueError):
            alg.normalize_losses([0, -1, 0])
        with self.assertRaises(ValueError):
            alg.normalize_losses({"Hunger": float("inf"), "Sanity": 0, "Health": 0})

    def test_best_sequence_uses_two_groups(self):
        total, actions = alg.find_best_plan(["Meat"] * 8, "Hunger")
        cooks = [action for action in actions if action[0] == "cook"]
        self.assertEqual(len(cooks), 2)
        self.assertEqual(total, 300)


class CookingTest(unittest.TestCase):
    def test_cooked_variant_lookup(self):
        self.assertEqual(alg.get_cooked_variant("Carrot"), "Roasted Carrot")
        self.assertIsNone(alg.get_cooked_variant("Cooked Carrot"))

    def test_roasting_when_it_is_better(self):
        # Carrot health: raw 1, roasted 3.
        total, actions = alg.find_best_plan(["Carrot"] * 4, "Health")
        self.assertEqual(total, 12)
        self.assertTrue(all(action[0] == "roast" for action in actions))

    def test_raw_food_when_it_is_better(self):
        # Corn gives 25 hunger, Popcorn only 12.5.
        total, actions = alg.find_best_plan(["Corn"] * 4, "Hunger")
        self.assertEqual(total, 100)
        self.assertTrue(all(action[0] == "eat" for action in actions))

    def test_kept_food_does_not_count_toward_totals(self):
        # Monster Meat costs sanity, so it should be kept rather than eaten.
        total, actions = alg.find_best_plan(["Monster Meat"] * 4, "Sanity")
        self.assertEqual(total, 0)
        self.assertTrue(all(action[0] == "keep" for action in actions))
        self.assertEqual(alg.plan_totals(actions)["Sanity"], 0)

    def test_roasted_ingredients_still_work_in_the_pot(self):
        self.assertEqual(
            alg.crockpot(("Roasted Potato",) * 4),
            "Ratatouille",
        )

    def test_warly_recipes_are_opt_in(self):
        ingredients = ("Asparagus", "Asparagus", "Ice", "Ice")
        self.assertEqual(alg.crockpot(ingredients), "Ratatouille")
        self.assertEqual(alg.crockpot(ingredients, warly=True), "Asparagazpacho")

    def test_warly_grim_galette(self):
        ingredients = ("Potato", "Onion", "Nightmare Fuel", "Nightmare Fuel")
        self.assertEqual(alg.crockpot(ingredients), "Wet Goop")
        self.assertEqual(alg.crockpot(ingredients, warly=True), "Grim Galette")


class DryingTest(unittest.TestCase):
    def test_dried_variant_lookup(self):
        self.assertEqual(alg.get_dried_variant("Meat"), "Jerky")
        self.assertEqual(alg.get_dried_variant("Raw Fish"), "Fishy Jerky")
        self.assertIsNone(alg.get_dried_variant("Jerky"))

    def test_drying_is_opt_in(self):
        # Meat has no sanity raw, and Meaty Stew only gives 5; four Jerky give 60.
        total, actions = alg.find_best_plan(["Meat"] * 4, "Sanity")
        self.assertEqual(total, 5)

        total, actions = alg.find_best_plan(["Meat"] * 4, "Sanity", dried=True)
        self.assertEqual(total, 60)
        self.assertEqual([action[0] for action in actions], ["dry"] * 4)
        self.assertTrue(all(action[2] == "Jerky" for action in actions))
        self.assertEqual(alg.plan_totals(actions), {"Hunger": 100, "Sanity": 60, "Health": 80})

    def test_dried_fish_variants(self):
        total, actions = alg.find_best_plan(["Raw Fish"] * 4, "Sanity", dried=True)
        self.assertEqual(total, 60)
        self.assertTrue(all(action[0] == "dry" for action in actions))
        self.assertTrue(all(action[2] == "Fishy Jerky" for action in actions))

        total, actions = alg.find_best_plan(
            ["Fish Morsel"] * 4, "Sanity", dried=True
        )
        self.assertEqual(total, 80)
        self.assertTrue(all(action[2] == "Small Fishy Jerky" for action in actions))

    def test_dried_kelp_boosts_sanity(self):
        total, actions = alg.find_best_plan(
            ["Kelp Fronds"] * 4, "Sanity", dried=True
        )
        self.assertEqual(total, 40)
        self.assertTrue(all(action[2] == "Dried Kelp Fronds" for action in actions))

    def test_drying_a_harmful_item_is_skipped(self):
        # Monster Jerky is less harmful than raw Monster Meat but still negative,
        # so keeping it is better than either.
        total, actions = alg.find_best_plan(
            ["Monster Meat"] * 4, "Sanity", dried=True
        )
        self.assertEqual(total, 0)
        self.assertTrue(all(action[0] == "keep" for action in actions))

    def test_dried_food_stats(self):
        self.assertEqual(alg.get_food_stats("Jerky"), (25.0, 15.0, 20.0))
        self.assertEqual(alg.get_food_stats("Small Jerky"), (12.5, 10.0, 8.0))
        self.assertEqual(alg.get_food_stats("Fishy Jerky"), (25.0, 15.0, 30.0))
        self.assertEqual(
            alg.get_food_stats("Small Fishy Jerky"), (12.5, 20.0, 15.0)
        )
        self.assertEqual(alg.get_food_stats("Raw Fish"), (25.0, 0.0, 8.0))

    def test_dried_pot_still_uses_raw_meat(self):
        dishes = alg.cookable_dishes(["Meat"] * 4, dried=True)
        self.assertEqual(dishes["Meaty Stew"][0], ("Meat",) * 4)

        total, actions = alg.find_best_plan(["Meat"] * 4, "Hunger", dried=True)
        self.assertEqual(total, 150)
        self.assertEqual(actions[0][0], "cook")
        self.assertEqual(sorted(actions[0][1]), ["Meat"] * 4)

    def test_pot_equivalent_variants_are_not_enumerated(self):
        # Drying does not change crockpot values, so Jerky is not tried in the pot.
        self.assertEqual(alg._pot_signature("Meat"), alg._pot_signature("Jerky"))
        self.assertEqual(alg._variant_options("Meat", True), ("Meat",))
        self.assertEqual(alg._variant_options("Monster Meat", True), ("Monster Meat",))

        # A cooked form that really is different is still kept.
        self.assertNotEqual(alg._pot_signature("Corn"), alg._pot_signature("Popcorn"))
        self.assertEqual(alg._variant_options("Corn"), ("Corn", "Popcorn"))

        # Unreferenced name tags do not matter, but a name a recipe uses does.
        self.assertEqual(alg._variant_options("Dead Wobster"), ("Dead Wobster",))
        self.assertIn("Charred Nostrils", alg._variant_options("Naked Nostrils"))

        # Dried forms that really change a recipe-relevant tag stay available.
        self.assertNotIn("Dried Kelp Fronds", alg._variant_options("Kelp Fronds"))
        self.assertIn(
            "Dried Kelp Fronds", alg._variant_options("Kelp Fronds", True)
        )
        self.assertIn("Small Fishy Jerky", alg._variant_options("Eel", True))

    def test_best_item_action_and_description(self):
        self.assertEqual(
            alg.best_item_action("Meat", "Sanity", dried=True),
            ("dry", "Meat", "Jerky"),
        )
        self.assertEqual(
            alg.describe_action(("dry", "Meat", "Jerky")), "dry Meat -> Jerky"
        )


class LookupTest(unittest.TestCase):
    def test_stats_are_tuples(self):
        self.assertEqual(alg.get_food_stats("Meatballs"), (62.5, 5.0, 3.0))

    def test_missing_stats_read_as_zero(self):
        self.assertEqual(alg.get_food_stat("Not A Food", "Hunger"), 0)

    def test_unknown_stat_raises(self):
        with self.assertRaises(ValueError):
            alg.get_food_stat("Meatballs", "Mana")

    def test_name_resolution_is_case_and_plural_insensitive(self):
        self.assertEqual(alg.resolve_food_name("meat"), "Meat")
        self.assertEqual(alg.resolve_food_name("Berry"), "Berries")
        self.assertEqual(alg.resolve_food_name("roasted potato"), "Roasted Potato")
        self.assertIsNone(alg.resolve_food_name("Unobtainium"))

    def test_unknown_food_message(self):
        self.assertIsNone(alg.resolve_food_name("Tomato"))
        self.assertEqual(
            alg.unknown_food_message(["Tomato"]),
            "'Tomato' is not a food and should be removed from the ingredient list.",
        )
        self.assertEqual(
            alg.unknown_food_message(["Tomato", "Tomato", "Mystery Fruit"]),
            "'Tomato', 'Mystery Fruit' are not foods and should be removed "
            "from the ingredient list.",
        )

    def test_jelly_salad_fields(self):
        rows = [row for row in alg.RECIPES if row[0] == "Jelly Salad"]
        self.assertEqual(len(rows), 1)
        name, conditions, excludes, priority = rows[0]
        self.assertIn("*Sweetener", conditions)
        self.assertEqual(excludes, "")
        self.assertEqual(priority, 50)


class NativeParityTest(unittest.TestCase):
    """The compiled engine must produce the same plans as the Python engine."""

    CASES = [
        ["Meat", "Meat", "Meat", "Ice"],
        ["Meat"] * 8,
        ["Monster Meat", "Monster Meat", "Ice", "Ice"],
        ["Carrot", "Carrot", "Corn", "Corn", "Meat", "Twigs"],
        ["Fish Morsel"] * 6 + ["Twigs"] * 4,
        ["Berries", "Berries", "Berries", "Butter", "Honey", "Ice",
         "Meat", "Meat", "Monster Meat", "Twigs", "Twigs", "Twigs"],
    ]

    def _run_plan(self, ingredients, **kwargs):
        import cpp_engine

        if not cpp_engine.available():
            self.skipTest("native engine not available")

        alg._USE_NATIVE = False
        try:
            python_plan = alg.find_best_plan(ingredients, **kwargs)
        finally:
            alg._USE_NATIVE = True
        native_plan = alg.find_best_plan(ingredients, **kwargs)
        return python_plan, native_plan

    @staticmethod
    def _cook_groups(actions):
        return sorted((action[2], sorted(action[1]))
                      for action in actions if action[0] == "cook")

    def test_hunger_plans_match(self):
        for ingredients in self.CASES:
            with self.subTest(inventory=ingredients):
                (py_total, py_actions), (cpp_total, cpp_actions) = self._run_plan(ingredients)
                self.assertEqual(cpp_total, py_total)
                self.assertEqual(alg.plan_totals(cpp_actions), alg.plan_totals(py_actions))
                self.assertEqual(self._cook_groups(cpp_actions), self._cook_groups(py_actions))

    def test_warly_and_losses_match(self):
        ingredients = ["Monster Meat", "Monster Meat", "Ice", "Ice"]
        for losses in (None, {"Hunger": 0, "Sanity": 20, "Health": 20}):
            with self.subTest(losses=losses):
                (py_total, py_actions), (cpp_total, cpp_actions) = self._run_plan(
                    ingredients, warly=True, losses=losses
                )
                self.assertEqual(cpp_total, py_total)
                self.assertEqual(alg.plan_totals(cpp_actions), alg.plan_totals(py_actions))
                self.assertEqual(self._cook_groups(cpp_actions), self._cook_groups(py_actions))

    def test_other_stats_match(self):
        for ingredients, stat in (
            (["Carrot"] * 4, "Health"),
            (["Corn"] * 4, "Hunger"),
            (["Meat"] * 4 + ["Ice"] * 4, "Sanity"),
        ):
            with self.subTest(inventory=ingredients, stat=stat):
                (py_total, py_actions), (cpp_total, cpp_actions) = self._run_plan(ingredients, stat=stat)
                self.assertEqual(cpp_total, py_total)
                self.assertEqual(alg.plan_totals(cpp_actions), alg.plan_totals(py_actions))
                self.assertEqual(self._cook_groups(cpp_actions), self._cook_groups(py_actions))

    def test_dried_plans_match(self):
        for ingredients, stat in (
            (["Meat"] * 4, "Sanity"),
            (["Meat"] * 8, "Health"),
            (["Raw Fish"] * 4, "Sanity"),
            (["Fish Morsel"] * 4, "Sanity"),
            (["Kelp Fronds", "Meat", "Morsel", "Raw Fish"], "Health"),
            (["Carrot", "Carrot", "Meat", "Meat"], "Health"),
        ):
            with self.subTest(inventory=ingredients, stat=stat):
                (py_total, py_actions), (cpp_total, cpp_actions) = self._run_plan(
                    ingredients, stat=stat, dried=True
                )
                self.assertEqual(cpp_total, py_total)
                self.assertEqual(alg.plan_totals(cpp_actions), alg.plan_totals(py_actions))
                self.assertEqual(self._cook_groups(cpp_actions), self._cook_groups(py_actions))
                self.assertEqual(
                    sorted(action[0] for action in cpp_actions),
                    sorted(action[0] for action in py_actions),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
