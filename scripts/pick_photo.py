#!/usr/bin/env python3
"""Выбор фото вручную, когда автоматический поиск промахнулся.

  python3 scripts/pick_photo.py --candidates b-grechka-moloko "buckwheat porridge"
      скачает 12 вариантов в /tmp/cand/<id>/ и соберёт лист /tmp/cand_<id>.jpg

  python3 scripts/pick_photo.py --set b-grechka-moloko 1234567
      поставит блюду снимок Pexels с этим номером

Номер снимка подписан под каждым вариантом на листе.
"""
import argparse, io, json, os, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
WIDTH = 600


def key():
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        if line.startswith("PEXELS_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("нет PEXELS_API_KEY в .env")


def get(url, headers):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=40).read()


def search(query, n=12):
    url = ("https://api.pexels.com/v1/search?query=" + urllib.parse.quote(query) +
           f"&per_page={n}")
    return json.loads(get(url, {"Authorization": key(), "User-Agent": UA}))["photos"]


def save(raw, path):
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    h = round(im.height * WIDTH / im.width)
    im.resize((WIDTH, h), Image.LANCZOS).save(path, "JPEG", quality=82, optimize=True)


def sheet(dish_id, photos, files):
    from PIL import Image, ImageDraw, ImageFont
    F = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
    CW, CH, LB, COLS = 260, 190, 20, 4
    rows = (len(files) + COLS - 1) // COLS
    sh = Image.new("RGB", (CW * COLS, (CH + LB) * rows), "white")
    dr = ImageDraw.Draw(sh)
    for k, (p, f) in enumerate(zip(photos, files)):
        im = Image.open(f).convert("RGB")
        r = max(CW / im.width, CH / im.height)
        im = im.resize((round(im.width * r), round(im.height * r)))
        l, t = (im.width - CW) // 2, (im.height - CH) // 2
        im = im.crop((l, t, l + CW, t + CH))
        x, y = (k % COLS) * CW, (k // COLS) * (CH + LB)
        sh.paste(im, (x, y))
        dr.rectangle([x, y + CH, x + CW, y + CH + LB], fill="black")
        dr.text((x + 4, y + CH + 2), str(p["id"]), font=F, fill="white")
    out = f"/tmp/cand_{dish_id}.jpg"
    sh.save(out, quality=78)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", nargs=2, metavar=("DISH_ID", "QUERY"))
    ap.add_argument("--set", nargs=2, metavar=("DISH_ID", "PHOTO_ID"))
    a = ap.parse_args()

    if a.candidates:
        dish_id, query = a.candidates
        d = os.path.join("/tmp/cand", dish_id)
        os.makedirs(d, exist_ok=True)
        photos = search(query)
        files = []
        for p in photos:
            f = os.path.join(d, f"{p['id']}.jpg")
            if not os.path.exists(f):
                save(get(p["src"]["medium"], {"User-Agent": UA}), f)
            files.append(f)
        print(sheet(dish_id, photos, files))
        return

    if a.set:
        dish_id, photo_id = a.set
        src = os.path.join("/tmp/cand", dish_id, f"{photo_id}.jpg")
        if not os.path.exists(src):
            sys.exit(f"нет скачанного варианта {photo_id} для {dish_id}")
        raw = open(src, "rb").read()
        save(raw, os.path.join(ROOT, "photos", f"{dish_id}.jpg"))
        cp = os.path.join(ROOT, "photos", "credits.json")
        c = json.load(open(cp, encoding="utf-8"))
        c.setdefault(dish_id, {})["photo_id"] = int(photo_id)
        c[dish_id]["page"] = f"https://www.pexels.com/photo/{photo_id}/"
        json.dump(c, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{dish_id} ← снимок {photo_id}")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
