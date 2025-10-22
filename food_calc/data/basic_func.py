def read_file(file):
    file = open(f"food_calc/data/{file}")
    content = file.read()
    file.close()
    return content


def file_to_list(file_name):
    if file_name == "food.txt":
        def ff(line):
            name, rest = line.split(": ")
            hunger, sanity, health = list(map(float, rest.split(", ")))
            return name, {
                "Hunger": hunger,
                "Sanity": sanity,
                "Health": health
            }
        stats = {}
        for line in read_file("food.txt").split("\n"):
            name, s = ff(line)
            stats[name] = s
        return stats
    if file_name == "recipes.txt":
        def rr(line):
            name, rest = line.split(": ")
            rest, *excludes = rest.split("; ")
            content = {}
            for el in rest.split(", "):
                ell = el.split(maxsplit=3)
                content[ell[2]] = ell[0], float(ell[1])
            return name, {
                "Content": content,
                "Excludes": excludes
            }
        recipes = {}
        for line in read_file("recipes.txt").split("\n"):
            name, r = rr(line)
            recipes[name] = r
        return recipes
    if file_name == "value.txt":
        values = {}
        for i in read_file("value.txt").split("\n\n"):
            value_name, *foods = i.split("\n")
            for line in foods:
                food_name, val = line.split(" - ")
                if food_name not in values:
                    values[food_name] = {value_name: val}
                else:
                    values[food_name][value_name] = val
        return values


