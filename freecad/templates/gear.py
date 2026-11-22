"""Template: simple spur gear blank with trapezoid teeth (illustration-grade, not an involute profile).
Parameters (env PARAM_*): TEETH=20 MODULE=2 (mm) WIDTH=15 BORE=10
Run:  python -m studio.cad make gear --param TEETH=24 --param MODULE=2
"""
import os, sys
sys.path.insert(0, os.environ["CAD_TEMPLATE_DIR"])  # set by studio.cad (__file__ is not reliable in FreeCADCmd)
from _common import *

teeth, mod, width, bore = param("TEETH", 20, int), param("MODULE", 2), param("WIDTH", 15), param("BORE", 10)
pitch_r = mod * teeth / 2.0
root_r, tip_r = pitch_r - 1.25 * mod, pitch_r + mod
V = FreeCAD.Vector
pts = []
step = 2 * math.pi / teeth
for i in range(teeth):
    a = i * step
    for frac, r in ((0.0, root_r), (0.2, tip_r), (0.5, tip_r), (0.7, root_r)):
        t = a + frac * step
        pts.append(V(r * math.cos(t), r * math.sin(t), 0))
pts.append(pts[0])
face = Part.Face(Part.makePolygon(pts))
body = face.extrude(V(0, 0, width))
body = body.cut(Part.makeCylinder(bore / 2.0, width, V(0, 0, 0), V(0, 0, 1)))
doc = FreeCAD.newDocument("gear")
export_all(doc, [add(doc, "gear", body)])
