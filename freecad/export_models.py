"""FreeCAD script: export a .FCStd document to STEP, STL and OBJ.

Run by `python -m studio.cad export ...` through FreeCADCmd (no GUI). Parameters arrive as environment
variables so the same file works on Windows and elsewhere:
  CAD_INPUT    path to the .FCStd file
  CAD_OUT      output folder
  CAD_NAME     base file name
  CAD_FORMATS  comma list from: step,stl,obj      (default step,stl,obj)
  CAD_SPLIT    1 = also write one STL per top-level object into <out>/parts/ (for exploded views / animation)
  CAD_LIN      mesh linear deflection in mm (default 0.1)
  CAD_ANG      mesh angular deflection in degrees (default 15)

Formats: STEP keeps exact CAD geometry for CAD programs (Blender cannot import STEP); STL/OBJ are meshes
that Blender imports directly (FreeCAD works in mm; blender/import_cad.py rescales to metres).
NOT YET RUN ON A REAL FreeCAD INSTALL in this repo's tests (FreeCAD is not available in the build sandbox).
"""
import math
import os

import FreeCAD
import Import
import Mesh
import MeshPart

src = os.environ["CAD_INPUT"]
out = os.environ["CAD_OUT"]
name = os.environ.get("CAD_NAME") or os.path.splitext(os.path.basename(src))[0]
formats = [f.strip().lower() for f in os.environ.get("CAD_FORMATS", "step,stl,obj").split(",") if f.strip()]
lin = float(os.environ.get("CAD_LIN", "0.1"))
ang = math.radians(float(os.environ.get("CAD_ANG", "15")))
split = os.environ.get("CAD_SPLIT", "0") == "1"
os.makedirs(out, exist_ok=True)

doc = FreeCAD.openDocument(src)
objs = [o for o in doc.Objects
        if hasattr(o, "Shape") and not o.Shape.isNull() and o.Shape.Solids and not o.InList]
if not objs:
    raise SystemExit("No solid, top-level objects found in " + src)


def mesh_of(o):
    return MeshPart.meshFromShape(Shape=o.Shape, LinearDeflection=lin, AngularDeflection=ang, Relative=False)


if "step" in formats:
    Import.export(objs, os.path.join(out, name + ".step"))
for ext in ("stl", "obj"):
    if ext in formats:
        m = Mesh.Mesh()
        for o in objs:
            m.addMesh(mesh_of(o))
        m.write(os.path.join(out, f"{name}.{ext}"))
if split:
    pdir = os.path.join(out, "parts")
    os.makedirs(pdir, exist_ok=True)
    for o in objs:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in o.Label)
        mesh_of(o).write(os.path.join(pdir, safe + ".stl"))
print(f"Exported {len(objs)} object(s) from {src} to {out}: {', '.join(formats)}{' + parts' if split else ''}")
