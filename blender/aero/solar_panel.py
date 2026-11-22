"""Blender scenes for episode 016: a solar panel, one cell, electrons becoming current, and the inverter to a home.

  blender -b -P blender/aero/solar_panel.py -- <scene> <out_dir> [--scale 25] [--samples 32] [--fps 15] [--hdri file]
  scenes: hook | cell | current | panel | home

Schematic and NOT to scale. Amber spheres = light energy arriving, cyan spheres = electrons (shown as simple dots, not
physics). No internal layers (p-n junction etc.) are modelled because the script does not claim them.
NOT YET RUN IN REAL BLENDER (mock-bpy tested only).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aero import *  # noqa: E402

M = {}
TILT = math.radians(35)


def materials():
    M["cell"] = material("cell", (0.02, 0.05, 0.16), metal=0.6, rough=0.2)
    M["frame"] = material("frame", (0.7, 0.72, 0.75), metal=1.0, rough=0.35)
    M["finger"] = material("finger", (0.85, 0.85, 0.9), metal=1.0, rough=0.25)
    M["photon"] = material("photon", (1, 0.75, 0.1), emit=(1.0, 0.7, 0.05), emit_strength=8.0)
    M["electron"] = material("electron", (0.2, 0.7, 1), emit=(0.2, 0.7, 1.0), emit_strength=8.0)
    M["sun"] = material("sun", (1, 0.8, 0.2), emit=(1.0, 0.75, 0.15), emit_strength=20.0)
    M["wall"] = material("wall", (0.75, 0.72, 0.68), rough=0.8)
    M["roof"] = material("roof", (0.35, 0.12, 0.1), rough=0.7)
    M["box"] = material("box", (0.15, 0.17, 0.2), metal=0.5, rough=0.4)
    M["ground"] = material("ground", (0.04, 0.05, 0.05), rough=0.9)


def build_panel(root, cols=6, rows=10, size=0.5):
    cells = []
    w, h = cols * size, rows * size
    box("frame", (w + 0.2, h + 0.2, 0.08), (0, 0, -0.05), M["frame"], parent=root)
    for i in range(cols):
        for j in range(rows):
            x, y = (i - (cols - 1) / 2) * size, (j - (rows - 1) / 2) * size
            c = box("cell", (size * 0.92, size * 0.92, 0.04), (x, y, 0), M["cell"], parent=root)
            for k in (-1, 0, 1):
                box("finger", (0.02, size * 0.9, 0.045), (x + k * size * 0.28, y, 0.01), M["finger"], parent=root)
            cells.append(c)
    return cells


def spheres(n, mat, r=0.07):
    out = []
    for _ in range(n):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=10, ring_count=6)
        o = bpy.context.object
        assign(o, M[mat])
        out.append(o)
    return out


def main():
    opts = parse_args()
    setup_scene(opts, sky=(0.02, 0.04, 0.09), sky_strength=0.8)
    materials()
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -2.2))
    assign(bpy.context.object, M["ground"])
    sun_light("sun_key", (math.radians(50), 0, math.radians(-30)), energy=4.0, color=(1.0, 0.92, 0.8))
    area_light("fill", (-6, -6, 6), (math.radians(60), 0, math.radians(-135)), 8, 500, (0.5, 0.65, 1.0))
    panel = empty("panel", (0, 0, 0))
    panel.rotation_euler = (TILT, 0, 0)
    cells = build_panel(panel)
    sun = cyl("sun", 1.0, 1.0, (0, 14, 12), M["sun"], rot=(math.pi / 2, 0, 0))
    house = empty("house", (9, -3, -2.2))
    box("walls", (4, 3, 2.4), (0, 0, 1.2), M["wall"], parent=house)
    cone("roof", 3.2, 0.1, 1.6, (0, 0, 3.2), M["roof"], verts=4, parent=house).rotation_euler = (0, 0, math.pi / 4)
    inv = box("inverter", (0.9, 0.35, 0.7), (4.6, 1.2, -1.5), M["box"])
    photons, electrons, house_e = spheres(18, "photon"), spheres(22, "electron"), spheres(12, "electron", 0.06)
    for o in house_e:
        o.hide_render = True
    rig = Rig(lens=38)
    name = opts["scene"]

    def rays(t, show):
        for k, o in enumerate(photons):
            o.hide_render = not show
            u = (t * 0.4 + k / len(photons)) % 1.0
            a = (-2.5 + (k * 0.37) % 5.0, 0.3 + (k * 0.29) % 4.0, 0.15)             # landing spot on the panel plane
            land = (a[0], a[1] * math.cos(TILT), a[1] * math.sin(TILT) + 0.15)
            o.location = lerp3((0, 14, 12), land, u)

    def flow(t, show):
        for k, o in enumerate(electrons):
            o.hide_render = not show
            u = (t * 0.3 + k / len(electrons)) % 1.0
            row = (k % 6) - 2.5
            if u < 0.6:                      # across the cell towards the metal contacts
                p = lerp3((row * 0.5, 0.0, 0.1), (row * 0.5, 2.2, 0.1), u / 0.6)
                o.location = (p[0], p[1] * math.cos(TILT), p[1] * math.sin(TILT) + p[2])
            else:                            # out along a wire to the right, towards the inverter
                p = lerp3((row * 0.5, 2.2 * math.cos(TILT), 2.2 * math.sin(TILT) + 0.1), (4.6, 1.2, -1.5), (u - 0.6) / 0.4)
                o.location = p

    def home_flow(t, show):
        for k, o in enumerate(house_e):
            o.hide_render = not show
            u = (t * 0.35 + k / len(house_e)) % 1.0
            o.location = lerp3((4.6, 1.2, -1.5), (9, -3, -0.8), u)

    cfg = {
        "hook": (6.0, lambda t, u: (rays(t, True), flow(t, False), rig.look(lerp3((9, -12, 4), (6, -9, 3), u), (0, 2, 1.5), 36))),
        "cell": (8.0, lambda t, u: (rays(t, True), flow(t, False), rig.look(lerp3((1.5, -2.5, 2.2), (0.6, -0.5, 1.2), u), (0, 0.3, 0.3), 45))),
        "current": (8.0, lambda t, u: (rays(t, False), flow(t, True), rig.look(lerp3((2, -3, 3), (4, -5, 3), u), (1, 1.5, 0.5), 40))),
        "panel": (7.0, lambda t, u: (rays(t, True), flow(t, False), rig.look(lerp3((0, -3, 6), (0, -9, 5), u), (0, 2, 1.8), 36))),
        "home": (8.0, lambda t, u: (rays(t, False), flow(t, True), home_flow(t, True), rig.look(lerp3((4, -9, 4), (8, -13, 4), u), (5.5, -1, -0.5), 36))),
    }
    if name not in cfg:
        raise SystemExit("unknown scene " + name)
    seconds, fn = cfg[name]
    render_sequence(opts, lambda t, u: fn(t, u), seconds)


if __name__ == "__main__":
    main()
