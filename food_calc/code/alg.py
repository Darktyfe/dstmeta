import basic_func
import itertools

version = "0.1-pre-alpha"

RECIPES = basic_func.file_to_list("recipes.txt")
VALUES = basic_func.file_to_list("values.txt")
STATS = basic_func.file_to_list("food.txt")

def get_version():
    return version

def get_food_stat(type, name, stat):
    return 0

def can_comb():
    return 0

def check_value(food_name, value_name):
    return food_name[value_name][VALUES]

def can_cooked():
    return 0

def can_receipt():
    return 0