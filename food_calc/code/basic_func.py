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
            return name, (float(hunger), float(sanity), float(health))
        stats = {}
        for line in read_file("food.txt").split("\n"):
            name, s = ff(line)
            stats[name] = s
        return stats
    if file_name == "recipes.txt":
        def rr(line):
            name, content, excludes, priority = line.split("; ")
            return name, content, excludes, int(priority)
        recipes = []
        for line in read_file("recipes.txt").split("\n"):
            r = rr(line)
            recipes.append(r)
        return recipes
    if file_name == "value.txt":
        def vv(line):
            name, rest = line.split(": ")
            vals = {}
            for i in rest.split(", "):
                k, number = i.split(" - ")
                vals[k] = float(number)
            return name, vals
        values = {}
        for i in read_file("value.txt").split("\n"):
            name, v = vv(line)
            values[name] = v
        return values
