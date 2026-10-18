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
        # Check if conditions are met
        condition_met = True
        for cond in conditions:
            condition_type, item, value = cond
            if condition_type == '>=':
                if item in i1 and i1[item] < float(value):
                    condition_met = False
                if item in i2 and i2[item] < float(value):
                    condition_met = False
                if item in i3 and i3[item] < float(value):
                    condition_met = False
                if item in i4 and i4[item] < float(value):
                    condition_met = False
            # Add more condition types if needed
        # Check if excludes are met
        if any(exclude in i1 for exclude in excludes):
            condition_met = False
        if any(exclude in i2 for exclude in excludes):
            condition_met = False
        if any(exclude in i3 for exclude in excludes):
            condition_met = False
        if any(exclude in i4 for exclude in excludes):
            condition_met = False
        # If conditions are met, add dish to list
        if condition_met:
            dishes.append((name, priority))
    # Sort dishes by priority (descending)
    dishes.sort(key=lambda x: x[1], reverse=True)
    # Return dish with the highest priority
    if dishes:
        return dishes[0][0]
    else:
        return None

