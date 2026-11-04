"""Tests for the per-character eating rules.

Run with ``py food_calc/code/test_characters.py``.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import alg
import characters


def stats(name, mode="dst", character=None, over_time=True):
    return alg.get_food_stats(name, over_time, mode, character)


class FavouriteFoodTest(unittest.TestCase):
    def test_vanilla_favourite_adds_hunger(self):
        self.assertEqual(stats("Bacon and Eggs", character="wilson"), (90.0, 5.0, 20.0))
        self.assertEqual(stats("Ice Cream", character="webber"), (40.0, 50.0, 0.0))

    def test_wortox_halves_the_favourite_after_the_bonus(self):
        # Pomegranate gains the +15 Hunger favourite bonus, then Wortox
        # halves every stat.
        base = stats("Pomegranate")
        self.assertEqual(
            stats("Pomegranate", character="wortox"),
            (
                (base[0] + 15.0) / 2.0,
                base[1] / 2.0,
                base[2] / 2.0,
            ),
        )

    def test_uc_favourite_gives_sanity_instead_of_hunger(self):
        self.assertEqual(
            stats("Bacon and Eggs", mode="uc", character="wilson"),
            (75.0, 20.0, 20.0),
        )
        self.assertEqual(
            stats("Spicy Chili", mode="uc", character="willow"),
            (37.5, 10.0, 20.0),
        )

    def test_uc_favourite_is_gradual(self):
        # With over-time stats ignored, only Winky's immediate part remains.
        self.assertEqual(
            stats("Bacon and Eggs", mode="uc", character="wilson", over_time=False),
            (75.0, 5.0, 20.0),
        )
        self.assertEqual(
            stats("Powdercake", mode="uc", character="winky", over_time=False),
            (15.0, 15.0, 12.0),
        )
        self.assertEqual(
            stats("Powdercake", mode="uc", character="winky", over_time=True),
            (15.0, 30.0, 12.0),
        )

    def test_walter_uc_has_several_favourites(self):
        for name, bonus in (
            ("Trail Mix", 15.0),
            ("Jerky", 15.0),
            ("Small Jerky", 10.0),
            ("Small Fishy Jerky", 10.0),
            ("Dried Kelp Fronds", 5.0),
        ):
            base = stats(name, mode="uc")[1]
            self.assertEqual(
                stats(name, mode="uc", character="walter")[1],
                base + bonus,
            )


class DietTest(unittest.TestCase):
    def test_wigfrid_eats_meat_and_goodies_only(self):
        data = alg._dataset("dst")
        self.assertTrue(
            characters.can_eat("wigfrid", "Meatballs", data.food_types, True)
        )
        self.assertTrue(
            characters.can_eat("wigfrid", "Ice Cream", data.food_types, True)
        )
        self.assertFalse(
            characters.can_eat("wigfrid", "Carrot", data.food_types, False)
        )
        self.assertFalse(
            characters.can_eat("wigfrid", "Butter Muffin", data.food_types, True)
        )

    def test_warly_eats_only_crockpot_dishes(self):
        self.assertFalse(characters.can_eat("warly", "Meat", {}, False))
        self.assertTrue(characters.can_eat("warly", "Meatballs", {}, True))

    def test_wurt_cannot_eat_meat_but_can_eat_durian(self):
        data = alg._dataset("dst")
        self.assertFalse(
            characters.can_eat("wurt", "Meatballs", data.food_types, True)
        )
        self.assertFalse(
            characters.can_eat("wurt", "Monster Meat", data.food_types, False)
        )
        self.assertTrue(
            characters.can_eat("wurt", "Durian", data.food_types, False)
        )
        self.assertTrue(
            characters.can_eat("wurt", "Ice Cream", data.food_types, True)
        )

    def test_uc_type_changes_remove_some_goodies(self):
        uc = alg._dataset("uc")
        self.assertFalse(
            characters.can_eat("wigfrid", "Ice Cream", uc.food_types, True)
        )
        self.assertFalse(
            characters.can_eat("wigfrid", "Taffy", uc.food_types, True)
        )

    def test_wigfrid_plan_keeps_vegetables(self):
        total, actions = alg.find_best_plan(
            ["Carrot"] * 4, "Hunger", character="wigfrid"
        )
        self.assertEqual(total, 0.0)
        self.assertTrue(all(action[0] == "keep" for action in actions))


class SpecialRulesTest(unittest.TestCase):
    def test_webber_ignores_monster_penalties_but_not_durian(self):
        self.assertEqual(
            stats("Monster Meat", character="webber"), (18.75, 0.0, 0.0)
        )
        self.assertEqual(
            stats("Monster Lasagna", character="webber"), (37.5, 0.0, 0.0)
        )
        self.assertEqual(
            stats("Durian", character="webber"), (25.0, -5.0, -3.0)
        )

    def test_wormwood_and_wanda_health_rules(self):
        self.assertEqual(stats("Bacon and Eggs", character="wormwood")[2], 0.0)
        self.assertEqual(stats("Taffy", character="wanda")[2], 0.0)
        self.assertEqual(stats("Monster Meat", character="wanda")[2], -20.0)

    def test_wurt_favourite_removes_durian_penalties(self):
        self.assertEqual(
            stats("Durian", character="wurt"), (40.0, 0.0, 0.0)
        )
        self.assertEqual(
            stats("Durian", mode="uc", character="wurt"),
            (25.0, 15.0, 0.0),
        )

    def test_wathom_ignores_raw_meat_but_not_monster_meat(self):
        self.assertEqual(
            stats("Meat", mode="uc", character="wathom"), (25.0, 0.0, 1.0)
        )
        self.assertEqual(
            stats("Monster Meat", mode="uc", character="wathom")[1], -15.0
        )

    def test_max_hunger_caps_the_plan(self):
        inv = ["Meat"] * 4
        total, _ = alg.find_best_plan(inv, "Hunger", character="wes")
        self.assertEqual(total, 75.0)
        total, _ = alg.find_best_plan(inv, "Hunger", character="wigfrid")
        self.assertEqual(total, 120.0)
        total, _ = alg.find_best_plan(inv, "Hunger", character="walter")
        self.assertEqual(total, 110.0)


class WarlyTest(unittest.TestCase):
    def test_multiplier_schedule(self):
        self.assertEqual(characters.warly_multiplier(1, "dst"), 1.0)
        self.assertEqual(characters.warly_multiplier(2, "dst"), 0.9)
        self.assertEqual(characters.warly_multiplier(6, "dst"), 0.3)
        self.assertEqual(characters.warly_multiplier(1, "uc"), 1.2)
        self.assertEqual(characters.warly_multiplier(2, "uc"), 0.8)
        self.assertEqual(characters.warly_multiplier(6, "uc"), 0.3)

    def test_repeat_limit_controls_servings(self):
        inv = ["Meat"] * 8
        total, _ = alg.find_best_plan(
            inv, "Hunger", character="warly", warly_repeats=0
        )
        self.assertEqual(total, 150.0)
        total, _ = alg.find_best_plan(
            inv, "Hunger", character="warly", warly_repeats=1
        )
        self.assertEqual(total, 285.0)
        total, _ = alg.find_best_plan(
            inv, "Hunger", mode="uc", character="warly", warly_repeats=1
        )
        self.assertEqual(total, 300.0)

    def test_ignoring_repeats_gives_full_value(self):
        total, _ = alg.find_best_plan(
            ["Meat"] * 8, "Hunger", character="warly", warly_repeats=-1
        )
        self.assertEqual(total, 300.0)

    def test_warly_eats_no_raw_food(self):
        total, actions = alg.find_best_plan(
            ["Meat"], "Hunger", character="warly"
        )
        self.assertEqual(total, 0.0)
        self.assertTrue(all(action[0] == "keep" for action in actions))

    def test_warly_can_use_different_dishes(self):
        inv = ["Meat"] * 4 + ["Berries"] * 4
        total, actions = alg.find_best_plan(
            inv, "Hunger", character="warly", warly_repeats=0
        )
        self.assertEqual(total, 212.5)
        dishes = [action[2] for action in actions if action[0] == "cook"]
        self.assertEqual(sorted(dishes), ["Meatballs", "Meaty Stew"])


if __name__ == "__main__":
    unittest.main()
