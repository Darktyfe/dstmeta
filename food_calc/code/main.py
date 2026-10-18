import alg


LANGUAGE = "en" # default


def get_user_food():
    food = []
    while True:
        print("Enter a food item or 'done' to finish:")
        if (i := input()) != "done":
            food.append(i)
            continue
        else:
            break
    return food

def find_best_dish_combination(user_ingredients, stat_lookup):
    """
    Find the best sequence or combination of dishes a user can make using their available ingredients.
    """
    # Generate possible dishes using the current user ingredients
    possible_dishes = alg.can_comb(user_ingredients)

    # Initialize variables to track the best path or combination of dishes
    best_path = []
    best_score = 0

    # Recursive function to explore all possible dish combinations
    def explore(path, remaining_ingredients):
        nonlocal best_path, best_score

        # Evaluate the current path based on the optimization criteria
        current_score = evaluate_path(path, remaining_ingredients, stat_lookup)
        if current_score > best_score:
            best_path = path[:]
            best_score = current_score

        # Recursively explore further sequential dishes
        for dish in possible_dishes:
            if alg.can_cook(dish, remaining_ingredients):
                new_path = path + [dish]
                new_remaining_ingredients = alg.crockpot(remaining_ingredients, dish)
                explore(new_path, new_remaining_ingredients)

    # Start exploring from an empty path and full user ingredients
    explore([], user_ingredients)

    # Return the best path or combination of dishes
    return best_path

def evaluate_path(path, remaining_ingredients, stat_lookup):
    """
    Evaluate the current path based on the optimization criteria.
    """
    # Example: maximize the number of dishes made
    return len(path)


print(alg.get_version())

print(find_best_dish_combination(get_user_food(), 'Hunger'))