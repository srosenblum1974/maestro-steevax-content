# Maestro Steevax — contenu

Un entrepreneur découvre la musique classique, semaine après semaine. Ce dépôt public est la source unique du
parcours : l'app iOS le lit depuis `raw.githubusercontent.com` (aucun nouveau build pour une nouvelle semaine) et le
site est servi par GitHub Pages.

| Fichier | Contenu |
|---|---|
| `_parcours.json` | Les 3 étapes, les phases, les périodes, les icônes du carnet (`palette`), l'histoire (`history`) (FR/EN) |
| `semaines/semaine-NN.json` | Une semaine : œuvres, version de référence, par où commencer, quoi écouter, liens, guide débutant (`guide` : contexte, moments, défi d'oreille, quiz) |
| `journal/_journal.json` | Le carnet public de Steve (son propre chemin) |
| `_index.json`, `_manifest.json` | Générés par `python3 tools/build.py` (liste des semaines, empreintes des fichiers) |
| `index.html` | Le site : parcours personnel (gardé dans le navigateur, exportable), carnet, méthode |

Ajouter une semaine : créer `semaines/semaine-NN.json`, lancer `python3 tools/build.py`, committer.

Règles : commits sous `Steve Rosenblum <s.rosenblum@me.com>` ; ne jamais réécrire l'historique.
