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

    def test_jelly_salad_fields(self):
        rows = [row for row in alg.RECIPES if row[0] == "Jelly Salad"]
        self.assertEqual(len(rows), 1)
        name, conditions, excludes, priority = rows[0]
        self.assertIn("*Sweetener", conditions)
        self.assertEqual(excludes, "")
        self.assertEqual(priority, 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
