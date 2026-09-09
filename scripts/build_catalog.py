#!/usr/bin/env python3
"""Склеивает три файла каталога в data/dishes.json и проверяет их.

Запуск:  python3 scripts/build_catalog.py
Выход:   data/dishes.json + отчёт проверки в терминал.
"""
import json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = ["breakfast", "lunch", "dinner"]
AISLES = {"овощи", "мясо-рыба", "молочка", "бакалея", "заморозка", "специи", "прочее"}
MAX_ACTIVE = 20

def norm(t):
    return t.lower().replace("ё", "е")


def mentioned(name, steps):
    """Продукт считается упомянутым, если в шагах есть корень любого его слова.

    Русские окончания режем грубо: берём слово без двух последних букв,
    но не короче трёх. «яйца» -> «яйц» находит «яйцом», «хлопья» -> «хлопь».
    """
    for word in norm(name).split():
        if len(word) < 3:
            continue
        if word[:max(3, len(word) - 2)] in steps:
            return True
    return False


def main():
    dishes, errors = [], []
    for part in PARTS:
        path = os.path.join(ROOT, "data", f"{part}.json")
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
        if len(items) != 30:
            errors.append(f"{part}: {len(items)} блюд вместо 30")
        for d in items:
            if d["meal"] != part:
                errors.append(f"{d['id']}: meal={d['meal']}, а лежит в {part}.json")
            dishes.extend([d])

    ids = [d["id"] for d in dishes]
    dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
    if dupes:
        errors.append(f"повторяющиеся id: {dupes}")

    names = collections.defaultdict(set)   # название -> набор (aisle, unit)
    for d in dishes:
        if d["active_min"] > MAX_ACTIVE:
            errors.append(f"{d['id']}: активное время {d['active_min']} мин")
        if d["photo"] != f"photos/{d['id']}.jpg":
            errors.append(f"{d['id']}: путь к фото не совпадает с id")
        if not d.get("query"):
            errors.append(f"{d['id']}: нет поискового запроса для фото")
        if not d.get("steps"):
            errors.append(f"{d['id']}: нет шагов приготовления")
        for ing in d["ingredients"]:
            if ing["aisle"] not in AISLES:
                errors.append(f"{d['id']}: неизвестный отдел {ing['aisle']}")
            if ing["aisle"] == "специи":
                if "qty" in ing:
                    errors.append(f"{d['id']}: у специи «{ing['name']}» указано количество")
            else:
                if "qty" not in ing or "unit" not in ing:
                    errors.append(f"{d['id']}: у «{ing['name']}» нет количества или единицы")
                names[ing["name"]].add((ing["aisle"], ing.get("unit", "")))

    # каждый продукт должен быть упомянут в рецепте
    for d in dishes:
        steps = norm(" ".join(d["steps"]))
        for ing in d["ingredients"]:
            if not mentioned(ing["name"], steps):
                errors.append(f"{d['id']}: «{ing['name']}» есть в продуктах, но не в рецепте")

    # один продукт — один отдел и одна единица измерения
    for name, variants in sorted(names.items()):
        if len(variants) > 1:
            errors.append(f"«{name}» встречается по-разному: {sorted(variants)}")

    print(f"Блюд всего: {len(dishes)}  (завтраки/обеды/ужины по 30)")
    print(f"Уникальных продуктов: {len(names)}\n")

    by_aisle = collections.defaultdict(list)
    for name, variants in names.items():
        aisle, unit = next(iter(variants))
        by_aisle[aisle].append(f"{name} [{unit}]")
    for aisle in sorted(by_aisle):
        print(f"— {aisle} ({len(by_aisle[aisle])}):")
        for n in sorted(by_aisle[aisle]):
            print(f"    {n}")
    print()

    if errors:
        print("ОШИБКИ:")
        for e in errors:
            print("  •", e)
        sys.exit(1)

    out = os.path.join(ROOT, "data", "dishes.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dishes, f, ensure_ascii=False, indent=1)
    print(f"Готово: {out}")

if __name__ == "__main__":
    main()
