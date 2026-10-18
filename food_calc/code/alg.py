import basic_func, itertools

version = "0.3-pre-alpha"

# Load recipes, values, and food stats from files
RECIPES = basic_func.file_to_list("recipes.txt") # {"Meaty Stew": {"Content": {*Meat: (">=", 3),}, "Excludes": "Twigs",},}
VALUES = basic_func.file_to_list("value.txt") # {"Cactus": {"*Vegetables": 1, ...}, ...}
STATS = basic_func.file_to_list("food.txt") # {"Meaty Stew": {"Hunger": 150, ...}, ...}

def get_version():
    """Return the current version of the program."""
    return version

def get_food_stat(name, type):
    """Return the stat value for a given food item and type."""
    if type == "Hunger":
        return STATS[name][0]
    elif type == "Sanity":
        return STATS[name][1]
    elif type == "Health":
        return STATS[name][2]
    else:
        return 0

def can_comb(food_list):
    """Generate all combinations of 4 food items."""
    return {tuple(sorted(i)) for i in itertools.combinations(food_list, 4)}

def check_value(food_name):
    """Check the value of a food item and return a list of its value properties."""
    value = VALUES[food_name]
    return [(k, v) for k, v in value.items() if k.startswith('*')]

def crockpot(ingridients):
    """Cook a dish using the given ingredients."""
    i1, i2, i3, i4 = map(check_value, ingridients)
    dishes = []

    for recipe in RECIPES:
        name, conditions, excludes, priority = recipe

        # Check if conditions are met
        condition_met = True
        for cond in conditions.split(", "):
            condition_type, item, value = cond.split()
            if condition_type == '>=':
                if any(item in i and i[item] < float(value) for i in (i1, i2, i3, i4)):
                    condition_met = False
        # Check if excludes are met
        if any(exclude in i1 for exclude in excludes) or \
           any(exclude in i2 for exclude in excludes) or \
           any(exclude in i3 for exclude in excludes) or \
           any(exclude in i4 for exclude in excludes):
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

def can_cook(dish, food_list):
    """Check if a list of food items can be cooked."""
    if crockpot(food_list) == dish:
        return True
    else:
        return False
