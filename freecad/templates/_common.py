"""Shared helpers for FreeCAD templates (imported by exec from the template files; FreeCADCmd only)."""
import math
import os

import FreeCAD
import Import
import Mesh
import MeshPart
import Part


def param(name, default, cast=float):
    return cast(os.environ.get("PARAM_" + name.upper(), default))


def add(doc, label, shape, color=None):
    o = doc.addObject("Part::Feature", label)
    o.Label = label
    o.Shape = shape
    return o


def export_all(doc, objs):
    out = os.environ["CAD_OUT"]
    name = os.environ.get("CAD_NAME", "model")
    formats = [f.strip().lower() for f in os.environ.get("CAD_FORMATS", "step,stl,obj").split(",") if f.strip()]
    lin = float(os.environ.get("CAD_LIN", "0.1"))
    ang = math.radians(float(os.environ.get("CAD_ANG", "15")))
    os.makedirs(out, exist_ok=True)
    doc.recompute()
    doc.saveAs(os.path.join(out, name + ".FCStd"))
    if "step" in formats:
        Import.export(objs, os.path.join(out, name + ".step"))
    meshes = [(o, MeshPart.meshFromShape(Shape=o.Shape, LinearDeflection=lin, AngularDeflection=ang)) for o in objs]
    for ext in ("stl", "obj"):
        if ext in formats:
            m = Mesh.Mesh()
            for _, mm in meshes:
                m.addMesh(mm)
            m.write(os.path.join(out, f"{name}.{ext}"))
    if os.environ.get("CAD_SPLIT") == "1":
        os.makedirs(os.path.join(out, "parts"), exist_ok=True)
        for o, mm in meshes:
            mm.write(os.path.join(out, "parts", o.Label + ".stl"))
    print(f"Built {len(objs)} part(s) -> {out} ({', '.join(formats)})")
