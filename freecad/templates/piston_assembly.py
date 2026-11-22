"""Template: cylinder, piston, connecting rod and crank pin (generic engineering shapes, no real engine data).
Parameters: BORE=86 STROKE=86 ROD=143 (mm) EXPLODE=0 (mm gap between parts for exploded views)
Run:  python -m studio.cad make piston_assembly --param EXPLODE=40 --split
"""
import os, sys
sys.path.insert(0, os.environ["CAD_TEMPLATE_DIR"])  # set by studio.cad (__file__ is not reliable in FreeCADCmd)
from _common import *

bore, stroke, rod, ex = param("BORE", 86), param("STROKE", 86), param("ROD", 143), param("EXPLODE", 0)
V = FreeCAD.Vector
Z = V(0, 0, 1)
wall = 6.0
liner = Part.makeCylinder(bore / 2 + wall, stroke + 40, V(0, 0, 0), Z).cut(
    Part.makeCylinder(bore / 2, stroke + 40, V(0, 0, 0), Z))
liner.translate(V(0, 0, ex * 2 + rod * 0.5))
piston = Part.makeCylinder(bore / 2 - 0.2, bore * 0.6, V(0, 0, 0), Z)
piston.translate(V(0, 0, ex * 1 + rod + stroke / 2 + 20))
pin = Part.makeCylinder(bore * 0.12, bore * 0.8, V(-bore * 0.4, 0, 0), V(1, 0, 0))
pin.translate(V(0, 0, rod + stroke / 2 + 20 + ex))
rod_shape = Part.makeCylinder(bore * 0.09, rod, V(0, 0, 0), Z)
rod_shape.translate(V(0, 0, stroke / 2 + ex * 0.5))
crank = Part.makeCylinder(bore * 0.2, bore * 0.5, V(-bore * 0.25, stroke / 2, 0), V(1, 0, 0))
doc = FreeCAD.newDocument("piston_assembly")
export_all(doc, [add(doc, "cylinder_liner", liner), add(doc, "piston", piston), add(doc, "piston_pin", pin),
                 add(doc, "connecting_rod", rod_shape), add(doc, "crank_pin", crank)])
