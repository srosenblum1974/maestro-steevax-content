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


## Séances d'oreille (moteur commun à tous les univers)

L'app entraîne l'oreille par séances de quelques minutes sur des extraits courts. Rien n'y est propre à un genre :
tout vient des fichiers de l'univers.

- **Compétences** : `skills` dans le `_parcours.json` de l'univers (`id`, `icon`, `name`). Un `role` (`artist`, `piece`
  ou `period`, avec la question `ask`) permet à l'app d'écrire seule des questions à partir des pièces : qui, quel
  morceau, quelle époque. Sans `skills`, l'app utilise trois compétences génériques.
- **Séances écrites** : `sessions` dans un fichier de semaine. Chaque exercice (`type: "choice"`) a une compétence
  (`skill`), une question (`prompt`), un ou deux extraits (`excerpts` : `work`, `track`, `start`, `duration` en
  secondes), des réponses (`options`), la bonne (`answer`), une explication (`why`) et une phrase d'introduction
  facultative (`tip`). Avec deux extraits, les réponses sont dans l'ordre A, B.
- **Séances automatiques** : une semaine sans `sessions` reçoit une séance écrite par l'app. Le test à l'aveugle et les
  révisions sont toujours automatiques. Un nouvel univers fonctionne donc dès que ses pièces ont une piste.
- Pistes Apple Music : l'extrait est pris dans l'aperçu de 30 secondes (`start + duration` ≤ 30).

`tools/build.py` vérifie les compétences, les extraits (pièce et piste existantes dans l'univers) et les réponses.
