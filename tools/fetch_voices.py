"""Downloads the narrations listed in tools/voix.json into voix/ and links them to their works.

tools/voix.json: {workID: {lang: {"hash": fingerprint of the narrated text, "url": temporary address of the mp3}}}
Each file lands in voix/<workID>-<lang>.mp3 and the work gets "narration": {lang: path}.
Once a file is in the repository its temporary address is removed from tools/voix.json.
"""
import json, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIST = ROOT / "tools" / "voix.json"


def main():
    voices = json.loads(LIST.read_text())
    (ROOT / "voix").mkdir(exist_ok=True)
    failed = []
    for work, langs in voices.items():
        for lang, v in langs.items():
            dest = ROOT / "voix" / f"{work}-{lang}.mp3"
            url = v.pop("url", None)
            if url:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "maestro-steevax"})
                    data = urllib.request.urlopen(req, timeout=120).read()
                    assert len(data) > 20000 and (data[:3] == b"ID3" or data[0] == 0xFF), "pas un mp3"
                    dest.write_bytes(data)
                    print(f"ok   {dest.name}  {len(data) // 1024} Ko")
                except Exception as e:
                    v["url"] = url
                    failed.append(f"{work}-{lang}: {e}")
                    print(f"ÉCHEC {work}-{lang}: {e}")
            v["file"] = dest.exists()

    linked = 0
    for p in [*ROOT.glob("semaines/*.json"), *ROOT.glob("univers/*/semaines/*.json")]:
        week = json.loads(p.read_text())
        for w in week["works"]:
            have = {lang: f"voix/{w['id']}-{lang}.mp3" for lang, v in voices.get(w["id"], {}).items() if v["file"]}
            if have:
                w["narration"] = have
                linked += len(have)
            else:
                w.pop("narration", None)
        p.write_text(json.dumps(week, ensure_ascii=False, indent=1) + "\n")

    for langs in voices.values():
        for v in langs.values():
            v.pop("file")
    LIST.write_text(json.dumps(voices, ensure_ascii=False, indent=1) + "\n")
    print(f"{linked} récits reliés, {len(failed)} échec(s)")
    sys.exit(1 if failed and not linked else 0)


if __name__ == "__main__":
    main()
