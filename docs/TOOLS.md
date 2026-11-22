# Studio tools: FreeCAD, Kdenlive, Poly Haven (+ Blender, Qwen, Piper)

These run on **your Windows PC** and add to the existing cloud pipeline (GitHub Actions). Nothing here replaces or
changes how episodes 001-012 build. Nothing is installed automatically.

## Install (all free)
| Tool | Needed for | Install |
|---|---|---|
| Python 3.10+ | all scripts | python.org (tick "Add to PATH"), then `pip install -r requirements.txt` |
| Blender 4.2 LTS | 3D renders | blender.org/download |
| FreeCAD | CAD models, STEP/STL/OBJ | freecad.org/downloads.php |
| Kdenlive | final edit | kdenlive.org/download |
| Ollama + Qwen (optional) | script drafts | ollama.com, then `ollama pull qwen2.5:7b` |

Or: `powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Install` (asks y/N for each).
Check: `python -m studio.doctor`. If a program is not found, put its path in `config/tools.yml` (`paths:`).
8 GB RAM advice: install and run one heavy program at a time; close Blender before rendering/editing in Kdenlive.

## Poly Haven (CC0 assets)
```
python -m studio.polyhaven search "studio" --type hdris
python -m studio.polyhaven get <asset-id> --type hdris        # 1k by default, refuses > 60 MB
python -m studio.polyhaven list
```
Files go to `assets/polyhaven/<type>/<id>/` (git-ignored). `manifest.json` (URL, licence, authors, checksums) and
`CREDITS.md` are kept up to date and can be committed. All Poly Haven assets are CC0; credit is optional but welcome.

## FreeCAD
```
python -m studio.cad templates
python -m studio.cad make gear --param TEETH=24
python -m studio.cad make piston_assembly --param EXPLODE=40 --split
python -m studio.cad export my_part.FCStd --split
python -m studio.cad blender-cmd assets\cad\gear\gear.stl     # prints the command that imports it into Blender
```
Output: `assets/cad/<name>/` with `.FCStd`, `.step`, `.stl`, `.obj` (+ `parts/`). Blender cannot read STEP, so use STL/OBJ;
`blender/import_cad.py` rescales mm to metres. Templates are parametric illustrations, not verified engine data.

## Kdenlive
```
python -m src.run_episode 013 --tts piper --force --out out
python -m studio.edit_project 013            # builds edit/013-<slug>/ (organised folders, SRT, guide, manifest)
```
Open Kdenlive, create the 1080x1920 30 fps project once, save it as `edit/templates/cutaway_vertical.kdenlive`;
later episodes start from it. The tool never overwrites your edits (use `--force` to refresh media only).

## Qwen script drafts
`python -m studio.qwen "Topic"` writes `episodes/drafts/*.yml` forced to `draft` / `UNVERIFIED`. Fact-check before use.

## Tests
`python -m unittest tests.test_studio` (offline; no tools needed).

## What is verified
Verified in the build sandbox: Poly Haven file selection, manifest, SRT/timeline, MLT XML validity, edit-folder
creation, Qwen YAML handling. **Not yet run against real Blender, FreeCAD, Kdenlive, melt, Ollama or the live Poly Haven API.**
Report any error and it will be fixed.

## 3D episodes with the aero toolkit (episode 013 and later)
`blender/aero/aero.py` = reusable helpers (Eevee setup, HDRI hook, materials, primitives, tracking camera, resumable render loop).
`blender/aero/starship_catch.py` = tower, two arms, booster (33 engines as 3+10+20), launch mount; scenes intro, mechazilla,
return, catch, engineering, ending. Models are **illustrations**: only the booster height (71 m) and engine count come from a source.
```
python -m studio.render_scenes 013 --list
python -m studio.render_scenes 013 --preview            # 25% size, 15 frames/s, one scene at a time
python -m studio.render_scenes 013 --final --only catch # full size, resumable
python -m studio.edit_project 013                       # after: python -m src.run_episode 013 --tts piper --force
```
Frames go to `renders/013/<scene>/` (git-ignored). The episode's `render_clip` visual stretches each clip to its scene and
adds labels and an ILLUSTRATIVE badge; without renders it draws a 2D stand-in. Use a Poly Haven HDRI for lighting:
`python -m studio.polyhaven get <hdri-id> --type hdris` (picked up automatically). First real-Blender run is untested:
start with `--preview --frames 5` and send me any error.
