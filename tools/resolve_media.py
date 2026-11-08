"""Finds the free recordings and paintings listed in tools/media.json on Wikimedia Commons, then writes:
- into each semaines/*.json work: "audio": [{label, url (MP3), performer, license, source}]
- into each week: "image": {path, credit, license, source}; the painting itself is downloaded to illus/
- into _parcours.json: "heroImage"
and prints a report. Only files whose licence is public domain or Creative Commons are accepted.

Runs in GitHub Actions (resolve-media.yml), where the network is open:  python3 tools/resolve_media.py
"""
import json, pathlib, re, sys, time, urllib.parse, urllib.request

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


def main():
    media = json.loads((ROOT / "tools/media.json").read_text())
    (ROOT / "illus").mkdir(exist_ok=True)

    def image(spec, name):
        i = pick(spec, "bitmap", width=2000)
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

    hero = image(media["hero"], "accueil")
    if hero:
        p = json.loads((ROOT / "_parcours.json").read_text())
        p["heroImage"] = hero
        (ROOT / "_parcours.json").write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n")

    for wid, spec in media["weeks"].items():
        path = ROOT / f"semaines/{wid}.json"
        week = json.loads(path.read_text())
        img = image(spec["image"], wid)
        if img:
            week["image"] = img
        for work in week["works"]:
            tracks = []
            for t in spec.get("audio", {}).get(work["id"], []):
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
