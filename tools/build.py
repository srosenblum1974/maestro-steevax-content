"""Rebuilds each universe's _index.json and the global _manifest.json.

Run from the repo root after adding or editing content:  python3 tools/build.py
_univers.json lists the universes (classical, later jazz, rock…). Each one has its own path under 'root':
_parcours.json, semaines/semaine-*.json, journal/_journal.json. The app and the site read _index.json for the list
of weeks and _manifest.json (fingerprints of every file) to know which files changed.
"""
import hashlib, json, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED = {"id", "n", "phase", "period", "title", "works"}
WORK_REQUIRED = {"id", "title", "recording", "startWith", "listenFor", "links"}
SOURCES = {"free", "appleMusic"}


def check(week, path, allowed):
    missing = REQUIRED - week.keys()
    assert not missing, f"{path}: champs manquants {missing}"
    for lang in ("fr", "en"):
        assert week["title"].get(lang), f"{path}: titre {lang} manquant"
    for w in week["works"]:
        miss = WORK_REQUIRED - w.keys()
        assert not miss, f"{path}/{w.get('id')}: champs manquants {miss}"
        assert w.get("composer") or w.get("people"), f"{path}/{w['id']}: ni 'composer' ni 'people'"
        for k in ("title", "startWith", "listenFor"):
            assert w[k].get("fr") and w[k].get("en"), f"{path}/{w['id']}: {k} incomplet"
        for a in w.get("audio", []):
            src = a.get("kind", "free")
            assert src in SOURCES and src in allowed, f"{path}/{w['id']}: source audio '{src}' non admise dans cet univers"
            if src == "free":
                assert a.get("url"), f"{path}/{w['id']}: piste libre sans url"
            elif not a.get("appleMusicId"):
                print(f"  ! {path}/{w['id']}: piste Apple Music pas encore résolue (lancer le workflow Resolve media)")
        g = w.get("guide")
        if g:
            assert set(g["ear"]["answer"]) <= set(g["ear"]["options"]), f"{w['id']}: réponses hors options"
            for q in g["quiz"]:
                assert 0 <= q["answer"] < len(q["options"]), f"{w['id']}: réponse de quiz invalide"


def main():
    uni = json.loads((ROOT / "_univers.json").read_text())
    assert uni["default"] in {u["id"] for u in uni["universes"]}, "univers par défaut inconnu"
    seen_weeks, seen_works, files = set(), {}, [ROOT / "_univers.json"]
    for u in uni["universes"]:
        base = ROOT / u["root"]
        weeks = []
        for p in sorted((base / "semaines").glob("*.json")):
            w = json.loads(p.read_text())
            assert p.stem == w["id"], f"{p.relative_to(ROOT)}: le fichier doit s'appeler {w['id']}.json"
            check(w, p.relative_to(ROOT), set(u.get("audio", ["free"])))
            assert w["id"] not in seen_weeks, f"semaine {w['id']} en double entre univers"
            seen_weeks.add(w["id"])
            for x in w["works"]:
                assert x["id"] not in seen_works, f"pièce {x['id']} en double ({seen_works.get(x['id'])})"
                seen_works[x["id"]] = u["id"]
            weeks.append({"id": w["id"], "n": w["n"], "phase": w["phase"], "period": w["period"], "title": w["title"],
                          "works": [{"id": x["id"], "composer": x.get("composer") or ", ".join(p["name"] for p in x["people"]),
                                     "title": x["title"]} for x in w["works"]]})
        weeks.sort(key=lambda w: w["n"])
        (base / "_index.json").write_text(json.dumps({"weeks": weeks}, ensure_ascii=False, indent=1) + "\n")
        files += [base / "_index.json", base / "_parcours.json", base / "journal" / "_journal.json", *(base / "semaines").glob("*.json")]
        print(f"{u['id']}: {len(weeks)} semaines")
    # Threads (« fils ») must point to existing works, in any universe.
    for f in files:
        if f.parent.name == "semaines":
            for x in json.loads(f.read_text())["works"]:
                for t in x.get("threads", []):
                    assert t["to"] in seen_works, f"{x['id']}: fil vers une pièce inconnue {t['to']}"
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in sorted(set(files))}
    (ROOT / "_manifest.json").write_text(json.dumps({"version": int(time.time()), "files": manifest}, indent=1) + "\n")
    print(f"{len(manifest)} fichiers dans le manifeste")


if __name__ == "__main__":
    main()
