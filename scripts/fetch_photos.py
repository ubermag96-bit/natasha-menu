#!/usr/bin/env python3
"""Разово скачивает фото блюд с Pexels в папку photos/.

Ключ: положить в .env строку  PEXELS_API_KEY=...  (бесплатно на pexels.com/api)

  python3 scripts/fetch_photos.py            # скачать недостающие
  python3 scripts/fetch_photos.py --check    # только показать, чего не хватает
  python3 scripts/fetch_photos.py --force b-syrniki l-plov-kurica   # перекачать эти

Файл кладётся как photos/<id>.jpg, шириной 600 px. Уже скачанное не трогается,
поэтому скрипт можно запускать сколько угодно раз.
"""
import argparse, io, json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTOS = os.path.join(ROOT, "photos")
WIDTH = 600
API = "https://api.pexels.com/v1/search?query={q}&per_page=5&orientation=landscape"
# Pexels отвечает 403 на подпись Python-urllib, поэтому представляемся браузером
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "\
     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def api_key():
    env = os.path.join(ROOT, ".env")
    if os.path.exists(env):
        for line in open(env, encoding="utf-8"):
            if line.strip().startswith("PEXELS_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("PEXELS_API_KEY", "")


def search(query, key):
    url = API.format(q=urllib.parse.quote(query))
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data.get("photos", [])


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def resize(raw, path):
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    h = round(im.height * WIDTH / im.width)
    im = im.resize((WIDTH, h), Image.LANCZOS)
    im.save(path, "JPEG", quality=82, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", nargs="*", default=None)
    args = ap.parse_args()

    dishes = json.load(open(os.path.join(ROOT, "data", "dishes.json"), encoding="utf-8"))
    os.makedirs(PHOTOS, exist_ok=True)

    missing = [d for d in dishes
               if not os.path.exists(os.path.join(ROOT, d["photo"]))]
    if args.force:
        todo = [d for d in dishes if d["id"] in args.force]
    else:
        todo = missing

    print(f"Блюд: {len(dishes)}   без фото: {len(missing)}   скачать сейчас: {len(todo)}")
    if args.check:
        for d in missing:
            print("  нет фото:", d["id"], "—", d["title"])
        return

    key = api_key()
    if not key:
        print("\nНет ключа Pexels. Положи в .env строку PEXELS_API_KEY=твой_ключ")
        print("Ключ бесплатный: https://www.pexels.com/api/")
        sys.exit(1)

    credits_path = os.path.join(PHOTOS, "credits.json")
    credits = json.load(open(credits_path, encoding="utf-8")) if os.path.exists(credits_path) else {}
    # какие снимки уже заняты другими блюдами — чтобы не повторяться
    used = {c["photo_id"] for cid, c in credits.items()
            if c.get("photo_id") and cid not in {d["id"] for d in todo}}

    ok = fail = 0
    for i, d in enumerate(todo, 1):
        try:
            photos = search(d["query"], key)
            if not photos:
                print(f"  [{i}/{len(todo)}] {d['id']}: ничего не найдено по «{d['query']}»")
                fail += 1
                continue
            p = next((x for x in photos if x["id"] not in used), None)
            if p is None:
                print(f"  [{i}/{len(todo)}] {d['id']}: все найденные снимки уже заняты")
                fail += 1
                continue
            raw = download(p["src"]["large"])
            resize(raw, os.path.join(ROOT, d["photo"]))
            used.add(p["id"])
            credits[d["id"]] = {"photo_id": p["id"], "author": p.get("photographer"),
                                "page": p.get("url")}
            ok += 1
            print(f"  [{i}/{len(todo)}] {d['id']} — ok")
        except Exception as e:
            fail += 1
            print(f"  [{i}/{len(todo)}] {d['id']}: ошибка {e}")
        time.sleep(0.4)          # бережно к лимиту Pexels

    json.dump(credits, open(credits_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nСкачано: {ok}, не вышло: {fail}")
    if fail:
        print("Что не скачалось — поправить query в data/<приём>.json и запустить снова.")


if __name__ == "__main__":
    main()
