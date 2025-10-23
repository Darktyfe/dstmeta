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

def check_value(food_name, value_name):
    return food_name[value_name][VALUES]

def canbe_cooked():
    return 0

def can_receipt():
    return 0
