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
ROLES = {"artist", "piece", "period"}
EXERCISE_TYPES = {"choice"}


def both(text, where):
    assert isinstance(text, dict) and text.get("fr") and text.get("en"), f"{where}: texte fr/en incomplet"


def check_skills(parcours, path):
    """Les compétences de l'univers (« skills » de _parcours.json). 'role' permet à l'app d'écrire seule des questions."""
    skills = parcours.get("skills", [])
    ids = [s["id"] for s in skills]
    assert len(ids) == len(set(ids)), f"{path}: compétences en double"
    for s in skills:
        both(s["name"], f"{path}/skills/{s['id']}")
        assert s.get("icon"), f"{path}/skills/{s['id']}: icône manquante"
        if "role" in s:
            assert s["role"] in ROLES, f"{path}/skills/{s['id']}: rôle inconnu {s['role']}"
            both(s.get("ask"), f"{path}/skills/{s['id']}/ask")
    roles = [s["role"] for s in skills if "role" in s]
    assert len(roles) == len(set(roles)), f"{path}: un seul 'skill' par rôle"
    return set(ids)


def check_sessions(week, path, skills, works, seen):
    """Les séances d'oreille d'une semaine : extraits vers des pistes existantes de l'univers, une bonne réponse valide."""
    for s in week.get("sessions", []):
        where = f"{path}/{s.get('id')}"
        assert s["id"] not in seen, f"{where}: séance en double"
        seen.add(s["id"])
        both(s["title"], where)
        if "teaser" in s:
            both(s["teaser"], where + "/teaser")
        assert len(s["exercises"]) >= 2, f"{where}: au moins deux exercices"
        for e in s["exercises"]:
            w = f"{where}/{e.get('id')}"
            assert e["id"] not in seen, f"{w}: exercice en double"
            seen.add(e["id"])
            assert e.get("type", "choice") in EXERCISE_TYPES, f"{w}: type inconnu {e.get('type')}"
            assert e["skill"] in skills, f"{w}: compétence '{e['skill']}' absente de _parcours.json"
            both(e["prompt"], w)
            for k in ("tip", "why"):
                if k in e:
                    both(e[k], f"{w}/{k}")
            assert 1 <= len(e["excerpts"]) <= 2, f"{w}: un ou deux extraits"
            for x in e["excerpts"]:
                assert x["work"] in works, f"{w}: extrait d'une pièce absente de cet univers ({x['work']})"
                tracks = works[x["work"]]
                t = x.get("track", 0)
                assert 0 <= t < len(tracks), f"{w}: piste {t} inexistante pour {x['work']}"
                start, dur = x.get("start", 0), x.get("duration", 15)
                assert start >= 0 and 3 <= dur <= 40, f"{w}: extrait hors bornes"
                if tracks[t].get("kind", "free") != "free":
                    assert start + dur <= 30, f"{w}: un extrait Apple Music tient dans les 30 s de l'aperçu"
            assert len(e["options"]) >= 2, f"{w}: au moins deux réponses"
            for o in e["options"]:
                both(o, w + "/options")
            assert 0 <= e["answer"] < len(e["options"]), f"{w}: bonne réponse invalide"


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
    seen_weeks, seen_works, seen_sessions, files = set(), {}, set(), [ROOT / "_univers.json"]
    for u in uni["universes"]:
        base = ROOT / u["root"]
        weeks = []
        skills = check_skills(json.loads((base / "_parcours.json").read_text()), u["id"])
        tracks = {x["id"]: x.get("audio", []) for p in (base / "semaines").glob("*.json") for x in json.loads(p.read_text())["works"]}
        sessions = 0
        for p in sorted((base / "semaines").glob("*.json")):
            w = json.loads(p.read_text())
            assert p.stem == w["id"], f"{p.relative_to(ROOT)}: le fichier doit s'appeler {w['id']}.json"
            check(w, p.relative_to(ROOT), set(u.get("audio", ["free"])))
            check_sessions(w, p.relative_to(ROOT), skills, tracks, seen_sessions)
            sessions += len(w.get("sessions", []))
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
        print(f"{u['id']}: {len(weeks)} semaines, {sessions} séances écrites, {len(skills)} compétences")
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
