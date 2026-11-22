"""Blender: import STL/OBJ made by FreeCAD, scale mm -> m, smooth shading, optional .blend save.

  blender -b --python blender/import_cad.py -- model.stl [--scale 0.001] [--save model.blend] [--origin]
Works on Blender 3.x (import_mesh.stl / import_scene.obj) and 4.x (wm.stl_import / wm.obj_import).
NOT YET RUN IN REAL BLENDER (tested only against a mock bpy).
"""
import sys
from pathlib import Path

import bpy


def parse(argv):
    a = argv[argv.index("--") + 1:] if "--" in argv else []
    opts = {"file": None, "scale": 0.001, "save": None, "origin": False}
    i = 0
    while i < len(a):
        if a[i] == "--scale":
            opts["scale"] = float(a[i + 1]); i += 2
        elif a[i] == "--save":
            opts["save"] = a[i + 1]; i += 2
        elif a[i] == "--origin":
            opts["origin"] = True; i += 1
        else:
            opts["file"] = a[i]; i += 1
    if not opts["file"]:
        raise SystemExit("usage: -- model.stl|obj [--scale 0.001] [--save out.blend] [--origin]")
    return opts


def import_mesh(path):
    ext = Path(path).suffix.lower()
    ops = bpy.ops
    if ext == ".stl":
        (ops.wm.stl_import if hasattr(ops.wm, "stl_import") else ops.import_mesh.stl)(filepath=str(path))
    elif ext == ".obj":
        (ops.wm.obj_import if hasattr(ops.wm, "obj_import") else ops.import_scene.obj)(filepath=str(path))
    else:
        raise SystemExit("Blender cannot import " + ext + ". Export STL or OBJ from FreeCAD (python -m studio.cad export).")


def main():
    o = parse(sys.argv)
    before = set(bpy.data.objects)
    import_mesh(o["file"])
    new = [ob for ob in bpy.data.objects if ob not in before]
    for ob in new:
        ob.scale = (o["scale"],) * 3
    bpy.ops.object.select_all(action="DESELECT")
    for ob in new:
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.shade_smooth()
    if o["origin"]:
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    print(f"Imported {len(new)} object(s) from {o['file']} at scale {o['scale']}")
    if o["save"]:
        bpy.ops.wm.save_as_mainfile(filepath=str(o["save"]))
        print("Saved", o["save"])


if __name__ == "__main__":
    main()
