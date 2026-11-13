"""Finds the free recordings and paintings listed in tools/media.json on Wikimedia Commons, then writes:
- into each semaines/*.json work: "audio": [{label, url (MP3), performer, license, source}]
- into each week: "image": {path, credit, license, source}; the painting itself is downloaded to illus/
- into _parcours.json: "heroImage" (and each universe's own _parcours.json, from "heroes")
- Apple Music tracks ("kind": "appleMusic", "itunes": {...}): the catalogue id, a 30-second preview URL and the
  Apple Music link, found with the public iTunes Search API
and prints a report. Only files whose licence is public domain or Creative Commons are accepted.

Images can also come from Pixabay (free to use under the Pixabay Content License): give an image a "pixabay" list of
search phrases. It is used when the PIXABAY_API_KEY secret is set in the repository; otherwise, or when nothing fits,
the Wikimedia Commons "search"/"file" of the same image is used. The key never goes into the repository.

Runs in GitHub Actions (resolve-media.yml), where the network is open:  python3 tools/resolve_media.py
"""
import json, os, pathlib, re, sys, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://commons.wikimedia.org/w/api.php"
UA = "MaestroSteevax/0.1 (https://maestrosteevax.com; classical music learning app)"
FREE = re.compile(r"public domain|^pd|cc0|cc[- ]by|creative commons", re.I)
report, failures = [], []


def get(params):
    q = urllib.parse.urlencode({**params, "format": "json", "formatversion": 2})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # network hiccup: retry
            if attempt == 2:
                raise
            time.sleep(2)


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def info(title, width=None):
    p = {"action": "query", "titles": title, "prop": "imageinfo|videoinfo",
         "iiprop": "url|extmetadata|mime", "viprop": "derivatives|url"}
    if width:
        p["iiurlwidth"] = width
    pages = get(p)["query"]["pages"]
    page = pages[0]
    if page.get("missing") or not page.get("imageinfo"):
        return None
    ii = page["imageinfo"][0]
    meta = ii.get("extmetadata", {})
    lic = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
    artist = strip_html(meta.get("Artist", {}).get("value", ""))
    raw_date = strip_html(meta.get("DateTimeOriginal", {}).get("value", ""))
    year = re.search(r"\b(1[0-9]{3})\b", raw_date)   # keep a clean year; Commons dates carry wiki markup
    date = (("c. " if re.search(r"circa|ca\.|c\.", raw_date, re.I) else "") + year.group(1)) if year else ""
    derivs = (page.get("videoinfo") or [{}])[0].get("derivatives", [])
    return {"title": page["title"], "license": lic, "artist": artist, "date": date,
            "mime": ii.get("mime", ""), "url": ii.get("url"), "thumb": ii.get("thumburl"),
            "page": ii.get("descriptionurl"), "derivatives": derivs}


def search(q, kind):
    r = get({"action": "query", "list": "search", "srnamespace": 6, "srlimit": 8,
             "srsearch": f"{q} filetype:{kind}"})
    return [h["title"] for h in r["query"]["search"]]


def mp3_url(i):
    if i["mime"] == "audio/mpeg":
        return i["url"]
    for d in i["derivatives"]:
        if d.get("transcodekey") == "mp3" or d.get("type", "").startswith("audio/mpeg"):
            return d["src"]
    return None


def pick(spec, kind, width=None):
    if "file" in spec:
        titles = [f"File:{spec['file']}"]
    else:
        queries = spec["search"] if isinstance(spec["search"], list) else [spec["search"]]
        titles = [t for q in queries for t in search(q, kind)]
    req_re = re.compile(spec["require"], re.I) if spec.get("require") else None
    exc_re = re.compile(spec["exclude"], re.I) if spec.get("exclude") else None
    for t in dict.fromkeys(titles):
        if (req_re and not req_re.search(t)) or (exc_re and exc_re.search(t)):
            continue
        i = info(t, width)
        if not i:
            continue
        if not FREE.search(i["license"]):
            report.append(f"  - skipped {t} (licence: {i['license'] or '?'})")
            continue
        if kind == "audio" and ("midi" in i["mime"] or not mp3_url(i)):
            report.append(f"  - skipped {t} (no MP3 version)")
            continue
        return i
    return None


ITUNES = "https://itunes.apple.com/search"
PIXABAY = "https://pixabay.com/api/"
PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()


def pixabay(spec):
    """The first wide Pixabay photo or illustration matching one of the phrases (tags filtered by require/exclude)."""
    if not PIXABAY_KEY or not spec.get("pixabay"):
        return None
    req_re = re.compile(spec["pixabay_require"], re.I) if spec.get("pixabay_require") else None
    exc_re = re.compile(spec["pixabay_exclude"], re.I) if spec.get("pixabay_exclude") else None
    phrases = spec["pixabay"] if isinstance(spec["pixabay"], list) else [spec["pixabay"]]
    for phrase in phrases:
        q = urllib.parse.urlencode({"key": PIXABAY_KEY, "q": phrase, "image_type": spec.get("pixabay_type", "photo"),
                                    "orientation": "horizontal", "safesearch": "true", "min_width": 1600, "per_page": 30,
                                    "order": "popular", "lang": "en"})
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{PIXABAY}?{q}", headers={"User-Agent": UA}), timeout=30) as r:
                hits = json.load(r).get("hits", [])
        except Exception as e:  # never print the URL: it carries the key
            report.append(f"  - pixabay '{phrase}': {type(e).__name__}")
            continue
        for h in hits:
            tags = h.get("tags", "")
            if (req_re and not req_re.search(tags)) or (exc_re and exc_re.search(tags)):
                continue
            return {"title": f"Pixabay {h['id']} ({tags})", "license": "Pixabay Content License", "artist": f"{h.get('user', '?')} / Pixabay",
                    "date": "", "thumb": h.get("largeImageURL") or h.get("webformatURL"), "url": h.get("largeImageURL"), "page": h.get("pageURL")}
    return None


def itunes(spec):
    """The catalogue entry matching artist, title, album (tried in order) and length; None if nothing fits."""
    q = urllib.parse.urlencode({"term": spec["term"], "entity": "song", "limit": 100, "country": spec.get("country", "fr")})
    req = urllib.request.Request(f"{ITUNES}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        results = json.load(r).get("results", [])
    low = lambda s: (s or "").lower()
    lo, hi = spec.get("seconds", [0, 10**6])
    ok = [x for x in results if low(spec["artist"]) in low(x.get("artistName")) and low(spec["title"]) in low(x.get("trackName"))
          and lo <= (x.get("trackTimeMillis") or 0) / 1000 <= hi and x.get("previewUrl")]
    for album in spec.get("albums", []) + [""]:
        for x in ok:
            if low(album) in low(x.get("collectionName")):
                return x
    return None


def universe_files():
    """Week id → its file, and universe id → its _parcours.json, across every universe."""
    weeks, parcours = {}, {}
    uni = json.loads((ROOT / "_univers.json").read_text()) if (ROOT / "_univers.json").exists() else {"universes": [{"id": "classique", "root": ""}]}
    for u in uni["universes"]:
        base = ROOT / u["root"]
        parcours[u["id"]] = base / "_parcours.json"
        for p in (base / "semaines").glob("*.json"):
            weeks[p.stem] = p
    return weeks, parcours


def main():
    media = json.loads((ROOT / "tools/media.json").read_text())
    (ROOT / "illus").mkdir(exist_ok=True)

    def image(spec, name):
        i = pixabay(spec) or (pick(spec, "bitmap", width=2000) if ("search" in spec or "file" in spec) else None)
        if not i:
            failures.append(f"image {name}: {spec}")
            return None
        src = i["thumb"] or i["url"]
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        try:  # keep paintings light for phones: 1800 px wide, JPEG 80
            from PIL import Image
            import io
            im = Image.open(io.BytesIO(data)).convert("RGB")
            if im.width > 1800:
                im = im.resize((1800, round(im.height * 1800 / im.width)), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=80, optimize=True, progressive=True)
            data = buf.getvalue()
        except ImportError:
            pass
        (ROOT / f"illus/{name}.jpg").write_bytes(data)
        report.append(f"IMAGE {name}: {i['title']} — {i['artist']} — {i['license']}")
        return {"path": f"illus/{name}.jpg", "credit": spec.get("credit") or (i["artist"] + (f", {i['date']}" if i["date"] else "")),
                "license": i["license"], "source": i["page"], "focus": spec.get("focus", "50% 40%")}

    week_files, parcours_files = universe_files()
    heroes = {"classique": (media["hero"], "accueil"), **{u: (sp, f"accueil-{u}") for u, sp in media.get("heroes", {}).items()}}
    for uid, (spec, name) in heroes.items():
        hero = image(spec, name)
        if hero and uid in parcours_files:
            p = json.loads(parcours_files[uid].read_text())
            p["heroImage"] = hero
            parcours_files[uid].write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n")

    for wid, spec in media["weeks"].items():
        path = week_files.get(wid)
        if not path:
            failures.append(f"week {wid}: no file")
            continue
        week = json.loads(path.read_text())
        img = image(spec["image"], wid)
        if img:
            week["image"] = img
        for work in week["works"]:
            tracks = []
            for t in spec.get("audio", {}).get(work["id"], []):
                if t.get("kind") == "appleMusic":
                    # A track already found is kept as it is: the catalogue refuses too many searches in a row.
                    known = next((k for k in work.get("audio", []) if k.get("kind") == "appleMusic" and k.get("label") == t["label"]), None)
                    if known:
                        tracks.append(known)
                        continue
                    try:
                        x = itunes(t["itunes"])
                    except Exception as e:
                        failures.append(f"apple music {wid}/{work['id']}: {type(e).__name__}")
                        continue
                    if not x:
                        failures.append(f"apple music {wid}/{work['id']}: {t['label']['en']}")
                        continue
                    report.append(f"APPLE MUSIC {wid}/{work['id']}: {x['trackName']} — {x['artistName']} — {x['collectionName']} ({x['trackId']})")
                    tracks.append({"label": t["label"], "kind": "appleMusic", "appleMusicId": str(x["trackId"]),
                                   "previewUrl": x["previewUrl"], "performer": x["artistName"], "license": "Apple Music",
                                   "source": x.get("trackViewUrl")})
                    if x.get("trackViewUrl"):
                        work["links"]["appleMusic"] = x["trackViewUrl"]
                    continue
                i = pick(t, "audio")
                if not i:
                    failures.append(f"audio {wid}/{work['id']}: {t['label']['en']}")
                    continue
                report.append(f"AUDIO {wid}/{work['id']}: {i['title']} — {i['artist']} — {i['license']}")
                tracks.append({"label": t["label"], "url": mp3_url(i), "performer": t.get("performer") or i["artist"] or "?",
                               "license": i["license"], "source": i["page"]})
            if tracks:
                work["audio"] = tracks
            else:
                work.pop("audio", None)   # never keep a stale or wrong track
        path.write_text(json.dumps(week, ensure_ascii=False, indent=1) + "\n")

    print("\n".join(report))
    if failures:
        print("\nNOT FOUND:\n" + "\n".join(failures))
    (ROOT / "tools/media-report.txt").write_text("\n".join(report + ["", "NOT FOUND:"] + failures) + "\n")


if __name__ == "__main__":
    sys.exit(main())
