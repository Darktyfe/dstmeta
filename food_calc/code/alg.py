import basic_func
import itertools

version = "0.1-pre-alpha"

RECIPES = basic_func.file_to_list("recipes.txt")
# {"Meaty Stew": {"Content": {*Meat: (">=", 3),}, "Excludes": "Twigs",},}
VALUES = basic_func.file_to_list("values.txt")
# {"Cactus": {"*Vegetables": 1, ...}, ...}
STATS = basic_func.file_to_list("food.txt")
# {"Meaty Stew": {"Hunger": 150, ...}, ...}


def get_version():
    return version


def get_food_stat(name, type):
    return STATS[name][type]


def can_comb(food_list):
    return {tuple(sorted(i)) for i in itertools.combinations(food_list, 4)}


def check_value(food_name):
    return value # value = [("*Meat", 0.25), ("*Fish", 0.25)]


def canbe_cooked():
    return 0


def crockpot(ingridients):
    i1, i2, i3, i4 = list(map(check_value, ingridients))
    dishes = []
    for recipe in RECIPES:
        name, conditions, excludes, priority = recipe
        # check condition and excludes for i1 i2 i3 i4 -> dishes. then check priority -> dish (if more than one -> print each with chances)
        for cond in conditions: # conditions = [(">=", "Meat", "3.0"), ...]
            # i1 + i2 + i3 + i4
            # check i1 + i2 + i3 + i4 satisfies condition
            # check i1 + i2 + i3 + i4 satisfies exludes
            # if both True
            dishes.append(name, priority)
    # sort dishes
    # dish = dish with highest priority and chance (100%) (if more than one -> print each with chances)
    return dish
