"""FreeCAD helpers: run templates, export STEP/STL/OBJ, prepare files for Blender.

  python -m studio.cad templates                       list the reusable FreeCAD templates
  python -m studio.cad make gear --param TEETH=24 --param MODULE=2     build a template -> assets/cad/gear/
  python -m studio.cad export path\\to\\model.FCStd [--split] [--formats step,stl,obj]
  python -m studio.cad blender-cmd assets\\cad\\gear\\gear.stl        print the Blender command that imports it

FreeCAD (FreeCADCmd) must be installed by you; see docs/TOOLS.md. Never installs anything.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from src.common import ROOT
from .paths import find_tool, tools_config

TEMPLATE_DIR = ROOT / "freecad" / "templates"
EXPORTER = ROOT / "freecad" / "export_models.py"


def cad_cfg():
    return tools_config().get("cad", {})


def list_templates():
    return sorted(p.stem for p in TEMPLATE_DIR.glob("*.py") if not p.stem.startswith("_"))


def build_env(base, **kw):
    """Environment for FreeCADCmd: CAD_* variables (None values are skipped). Pure, testable."""
    env = dict(base)
    for k, v in kw.items():
        if v is not None:
            env[k] = str(v)
    return env


def run_freecad(script, env, log=print):
    exe = find_tool("freecadcmd")
    if not exe:
        raise SystemExit("FreeCADCmd not found. Install FreeCAD (docs/TOOLS.md) or set paths.freecadcmd in config/tools.yml.")
    log(f"FreeCADCmd: {exe}")
    r = subprocess.run([exe, str(script)], env=env, capture_output=True, text=True)
    if r.stdout.strip():
        log(r.stdout.strip())
    if r.returncode != 0:
        raise SystemExit(f"FreeCAD failed ({r.returncode}):\n{r.stderr[-1500:]}")


def make(template, params, out_dir=None, formats="step,stl,obj", split=False):
    script = TEMPLATE_DIR / f"{template}.py"
    if not script.exists():
        raise SystemExit(f"No template '{template}'. Available: {', '.join(list_templates())}")
    out = Path(out_dir) if out_dir else ROOT / cad_cfg().get("out_dir", "assets/cad") / template
    env = build_env(os.environ, CAD_OUT=out, CAD_NAME=template, CAD_FORMATS=formats,
                    CAD_SPLIT=1 if split else 0, CAD_LIN=cad_cfg().get("linear_deflection"),
                    CAD_ANG=cad_cfg().get("angular_deflection_deg"), CAD_TEMPLATE_DIR=TEMPLATE_DIR)
    for p in params:
        k, _, v = p.partition("=")
        env["PARAM_" + k.strip().upper()] = v.strip()
    run_freecad(script, env)
    return out


def export(fcstd, out_dir=None, formats="step,stl,obj", split=False):
    fcstd = Path(fcstd)
    if not fcstd.exists():
        raise SystemExit(f"File not found: {fcstd}")
    out = Path(out_dir) if out_dir else ROOT / cad_cfg().get("out_dir", "assets/cad") / fcstd.stem
    env = build_env(os.environ, CAD_INPUT=fcstd.resolve(), CAD_OUT=out, CAD_NAME=fcstd.stem, CAD_FORMATS=formats,
                    CAD_SPLIT=1 if split else 0, CAD_LIN=cad_cfg().get("linear_deflection"),
                    CAD_ANG=cad_cfg().get("angular_deflection_deg"))
    run_freecad(EXPORTER, env)
    return out


def blender_cmd(mesh):
    exe = find_tool("blender") or "blender"
    scale = cad_cfg().get("blender_scale", 0.001)
    return (f'"{exe}" -b --python "{ROOT / "blender" / "import_cad.py"}" -- "{Path(mesh).resolve()}" '
            f'--scale {scale} --save "{Path(mesh).with_suffix(".blend")}"')


def main(argv=None):
    ap = argparse.ArgumentParser(description="FreeCAD helpers")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("templates")
    m = sub.add_parser("make"); m.add_argument("template"); m.add_argument("--param", action="append", default=[])
    m.add_argument("--out"); m.add_argument("--formats", default="step,stl,obj"); m.add_argument("--split", action="store_true")
    e = sub.add_parser("export"); e.add_argument("file"); e.add_argument("--out")
    e.add_argument("--formats", default="step,stl,obj"); e.add_argument("--split", action="store_true")
    b = sub.add_parser("blender-cmd"); b.add_argument("mesh")
    a = ap.parse_args(argv)
    if a.cmd == "templates":
        print("\n".join(list_templates()) or "(none)")
    elif a.cmd == "make":
        print("Done:", make(a.template, a.param, a.out, a.formats, a.split))
    elif a.cmd == "export":
        print("Done:", export(a.file, a.out, a.formats, a.split))
    else:
        print(blender_cmd(a.mesh))
    return 0


if __name__ == "__main__":
    sys.exit(main())
