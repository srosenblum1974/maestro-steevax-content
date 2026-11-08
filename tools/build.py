"""Rebuilds _index.json and _manifest.json from semaines/*.json.

Run from the repo root after adding or editing a week:  python3 tools/build.py
The app and the site read _index.json for the list of weeks and _manifest.json to know which files changed.
"""
import hashlib, json, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED = {"id", "n", "phase", "period", "title", "works"}
WORK_REQUIRED = {"id", "composer", "title", "recording", "startWith", "listenFor", "links"}


def check(week, path):
    missing = REQUIRED - week.keys()
    assert not missing, f"{path.name}: champs manquants {missing}"
    for lang in ("fr", "en"):
        assert week["title"].get(lang), f"{path.name}: titre {lang} manquant"
    for w in week["works"]:
        miss = WORK_REQUIRED - w.keys()
        assert not miss, f"{path.name}/{w.get('id')}: champs manquants {miss}"
        for k in ("title", "startWith", "listenFor"):
            assert w[k].get("fr") and w[k].get("en"), f"{path.name}/{w['id']}: {k} incomplet"


def main():
    weeks = []
    for p in sorted((ROOT / "semaines").glob("semaine-*.json")):
        w = json.loads(p.read_text())
        check(w, p)
        weeks.append({"id": w["id"], "n": w["n"], "phase": w["phase"], "period": w["period"], "title": w["title"],
                      "works": [{"id": x["id"], "composer": x["composer"], "title": x["title"]} for x in w["works"]]})
    weeks.sort(key=lambda w: w["n"])
    (ROOT / "_index.json").write_text(json.dumps({"weeks": weeks}, ensure_ascii=False, indent=1) + "\n")

    files = {}
    for p in sorted([ROOT / "_index.json", ROOT / "_parcours.json", ROOT / "journal" / "_journal.json",
                     *(ROOT / "semaines").glob("*.json")]):
        files[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    (ROOT / "_manifest.json").write_text(json.dumps({"version": int(time.time()), "files": files}, indent=1) + "\n")
    print(f"{len(weeks)} semaines, {len(files)} fichiers dans le manifeste")


if __name__ == "__main__":
    main()
