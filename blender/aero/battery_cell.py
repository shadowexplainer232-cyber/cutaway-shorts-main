"""Blender scenes for episode 017: a lithium-ion cell (anode, cathode, separator, electrolyte) discharging and charging.

  blender -b -P blender/aero/battery_cell.py -- <scene> <out_dir> [--scale 25] [--samples 32] [--fps 15] [--hdri file]
  scenes: hook | parts | discharge | charge

Schematic and NOT to scale. Amber spheres = lithium ions (move THROUGH the cell: anode -> cathode when discharging,
back when charging). Cyan spheres = electrons (move through the OUTSIDE wire). Materials named on screen follow the
source (anode = negative side, cathode = positive side); no chemistry beyond that is modelled.
NOT YET RUN IN REAL BLENDER (mock-bpy tested only).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aero import *  # noqa: E402

M = {}
AX, CX = -2.1, 2.1        # anode / cathode centre x


def materials():
    M["anode"] = material("anode", (0.12, 0.12, 0.14), metal=0.3, rough=0.6)
    M["cathode"] = material("cathode", (0.75, 0.75, 0.8), metal=0.5, rough=0.4)
    M["sep"] = material("sep", (0.9, 0.9, 0.5), rough=0.7)
    M["case"] = material("case", (0.3, 0.32, 0.36), metal=0.9, rough=0.35)
    M["wire"] = material("wire", (0.7, 0.45, 0.15), metal=1.0, rough=0.3)
    M["ion"] = material("ion", (1, 0.7, 0.1), emit=(1.0, 0.65, 0.05), emit_strength=8.0)
    M["electron"] = material("electron", (0.2, 0.7, 1), emit=(0.2, 0.7, 1.0), emit_strength=8.0)
    M["bulb"] = material("bulb", (0.9, 0.9, 0.7), emit=(1.0, 0.9, 0.5), emit_strength=0.0)
    M["floor"] = material("floor", (0.03, 0.03, 0.04), metal=0.2, rough=0.4)


def main():
    opts = parse_args()
    setup_scene(opts, sky=(0.005, 0.007, 0.012), sky_strength=0.3)
    materials()
    area_light("key", (4, -8, 8), (math.radians(55), 0, math.radians(20)), 8, 1500, (1, 0.95, 0.9))
    area_light("rim", (-6, 5, 5), (math.radians(70), 0, math.radians(215)), 8, 800, (0.4, 0.6, 1.0))
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -1.6))
    assign(bpy.context.object, M["floor"])
    root = empty("cell")
    box("anode", (1.8, 2.6, 2.2), (AX, 0, 0), M["anode"], parent=root)
    box("cathode", (1.8, 2.6, 2.2), (CX, 0, 0), M["cathode"], parent=root)
    box("separator", (0.08, 2.7, 2.3), (0, 0, 0), M["sep"], parent=root)
    for s in (-1, 1):                                                       # case rails top and bottom
        box("rail", (6.4, 2.8, 0.1), (0, 0, s * 1.2), M["case"], parent=root)
    # outside wire from anode up, over a bulb, to the cathode
    box("wire_a", (0.1, 0.1, 1.6), (AX, 0, 1.9), M["wire"], parent=root)
    box("wire_c", (0.1, 0.1, 1.6), (CX, 0, 1.9), M["wire"], parent=root)
    box("wire_top_l", (1.7, 0.1, 0.1), (AX + 0.85, 0, 2.7), M["wire"], parent=root)
    box("wire_top_r", (1.7, 0.1, 0.1), (CX - 0.85, 0, 2.7), M["wire"], parent=root)
    bulb = bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, location=(0, 0, 2.7), segments=24, ring_count=12)
    bulb_o = bpy.context.object
    assign(bulb_o, M["bulb"]); bulb_o.parent = root

    def mk(n, mat, r):
        out = []
        for _ in range(n):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=10, ring_count=6)
            o = bpy.context.object; assign(o, M[mat]); o.parent = root; out.append(o)
        return out
    ions, electrons = mk(14, "ion", 0.09), mk(10, "electron", 0.07)
    rig = Rig(lens=36)
    name = opts["scene"]

    def move(t, direction, on_ions=True, on_el=True):
        """direction +1 = discharge (ions anode->cathode, electrons through the wire anode->cathode), -1 = charge."""
        for k, o in enumerate(ions):
            o.hide_render = not on_ions
            u = (t * 0.25 * direction + k / len(ions)) % 1.0
            y, z = ((k * 0.37) % 2.0) - 1.0, ((k * 0.53) % 1.6) - 0.8
            o.location = (lerp(AX + 0.5, CX - 0.5, u), y, z)
        for k, o in enumerate(electrons):
            o.hide_render = not on_el
            u = (t * 0.3 * direction + k / len(electrons)) % 1.0
            pts = [(AX, 0, 1.2), (AX, 0, 2.7), (CX, 0, 2.7), (CX, 0, 1.2)]
            seg_i = min(2, int(u * 3)); f = u * 3 - seg_i
            o.location = lerp3(pts[seg_i], pts[seg_i + 1], f)
        bulb_o.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 8.0 if (direction > 0 and on_el) else 0.0

    cfg = {
        "hook": (6.0, lambda t, u: (move(t, 1, False, False), rig.look((lerp(-4, 3, u), -11, 4), (0, 0, 0.8), 36))),
        "parts": (9.0, lambda t, u: (move(t, 1, False, False), rig.look(lerp3((0, -10, 3), (0, -8, 2), u), (lerp(-2.1, 2.1, seg(u, 0.1, 0.9)), 0, 0.3), 36))),
        "discharge": (9.0, lambda t, u: (move(t, 1), rig.look(lerp3((-2, -11, 4.5), (2, -10, 4), u), (0, 0, 1.0), 36))),
        "charge": (7.0, lambda t, u: (move(t, -1), rig.look(lerp3((2, -11, 4.5), (-2, -10, 4), u), (0, 0, 1.0), 36))),
    }
    if name not in cfg:
        raise SystemExit("unknown scene " + name)
    seconds, fn = cfg[name]
    render_sequence(opts, lambda t, u: fn(t, u), seconds)


if __name__ == "__main__":
    main()
