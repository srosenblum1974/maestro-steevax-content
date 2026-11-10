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

## Univers

`_univers.json` liste les univers musicaux (classique aujourd'hui ; jazz, rock… demain). Chaque univers a son propre
parcours sous `root` : `_parcours.json`, `_index.json`, `semaines/<id>.json`, `journal/_journal.json`. Le classique est
à la racine (`root` vide) ; un nouvel univers va sous `univers/<id>/`. Règles vérifiées par `tools/build.py` :
identifiants de semaines et de pièces uniques entre univers (préfixez-les), fichier de semaine nommé d'après son id,
types de piste (`kind` : `free` ou `appleMusic`) admis par l'univers, fils (`threads`) vers des pièces existantes.
Une pièce indique ses auteurs par `composer` (classique) ou `people` (`[{name, role}]`).
