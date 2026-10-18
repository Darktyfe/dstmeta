def read_file(file):
    """Reads a file and returns its content as a string."""
    with open(f"food_calc/data/{file}", 'r') as file:
        return file.read()

def parse_food_line(line):
    """Parses a line from food.txt and returns a tuple of name and stats."""
    name, rest = line.split(": ")
    hunger, sanity, health = list(map(float, rest.split(", ")))
    return name, (float(hunger), float(sanity), float(health))

def parse_recipe_line(line):
    """Parses a line from recipes.txt and returns a tuple of name, content, excludes, and priority."""
    name, content, excludes, priority = line.split("; ")
    return name, content, excludes, int(priority)

def parse_value_line(line):
    """Parses a line from value.txt and returns a tuple of name and values."""
    name, rest = line.split(": ")
    vals = {}
    for i in rest.split(", "):
        k, number = i.split(" - ")
        vals[k] = float(number)
    return name, vals

def file_to_list(file_name):
    """Converts a file to a list based on the file name."""
    if file_name == "food.txt":
        return {name: stats for name, stats in map(parse_food_line, read_file(file_name).split("\n"))}
    elif file_name == "recipes.txt":
        return [parse_recipe_line(line) for line in read_file(file_name).split("\n")]
    elif file_name == "value.txt":
        return {name: values for name, values in map(parse_value_line, read_file(file_name).split("\n"))}
    else:
        raise ValueError("Unsupported file type")

