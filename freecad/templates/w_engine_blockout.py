"""Template: simple blockout of a 16-cylinder 'W' engine layout (cylinders only; layout illustration).

Layout: two narrow-angle VR8 banks joined on one crankshaft (the W16 arrangement the 014 brief describes:
16 cylinders in four banks of four). Dimensions are PARAMETERS, not verified engine data. Do not present
the result as an accurate Bugatti model; it is a labelled illustration of the layout.
Parameters: BORE=86 STROKE=86 BANK_ANGLE=15 (degrees between neighbouring banks) PITCH=100 (mm between cylinders)
"""
import os, sys
sys.path.insert(0, os.environ["CAD_TEMPLATE_DIR"])  # set by studio.cad (__file__ is not reliable in FreeCADCmd)
from _common import *

bore, stroke, ang, pitch = param("BORE", 86), param("STROKE", 86), param("BANK_ANGLE", 15), param("PITCH", 100)
V = FreeCAD.Vector
doc = FreeCAD.newDocument("w_engine_blockout")
objs = []
# Four banks fan out around the crank axis (Y). Bank angles: -1.5a, -0.5a, +0.5a, +1.5a from vertical (a = BANK_ANGLE).
for b, k in enumerate((-1.5, -0.5, 0.5, 1.5)):
    direction = V(math.sin(math.radians(k * ang)), 0, math.cos(math.radians(k * ang)))
    for c in range(4):
        y = (c - 1.5) * pitch
        cyl = Part.makeCylinder(bore / 2, stroke * 1.6, V(0, y, 0), direction)
        objs.append(add(doc, f"cyl_b{b + 1}_{c + 1}", cyl))
crank = Part.makeCylinder(30, pitch * 4.4, V(0, -pitch * 2.2, 0), V(0, 1, 0))
objs.append(add(doc, "crankshaft_axis", crank))
export_all(doc, objs)
