"""Blender scenes for episode 015: a simplified liquid rocket engine (tanks, pumps, chamber, nozzle, exhaust).

  blender -b -P blender/aero/rocket_engine.py -- <scene> <out_dir> [--scale 25] [--samples 32] [--fps 15] [--hdri file]
  scenes: hook | tanks | chamber | nozzle | thrust | space

Schematic and NOT to scale: a generic pump-fed liquid-propellant engine, not any real engine. Fuel (amber) and oxidiser
(cyan) flow down, burn in the chamber, and the hot exhaust (orange) speeds up through the narrow throat and the bell.
NOT YET RUN IN REAL BLENDER (mock-bpy tested only).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aero import *  # noqa: E402

M = {}


def materials():
    M["tank_f"] = material("tank_f", (0.9, 0.6, 0.1), metal=0.6, rough=0.4)
    M["tank_o"] = material("tank_o", (0.2, 0.6, 0.9), metal=0.6, rough=0.4)
    M["steel"] = material("steel", (0.62, 0.64, 0.68), metal=1.0, rough=0.32)
    M["dark"] = material("dark", (0.06, 0.06, 0.07), metal=0.7, rough=0.5)
    M["fuel"] = material("fuel", (1, 0.7, 0), emit=(1.0, 0.7, 0.0), emit_strength=6.0)
    M["ox"] = material("ox", (0.2, 0.7, 1), emit=(0.2, 0.7, 1.0), emit_strength=6.0)
    M["gas"] = material("gas", (1, 0.5, 0.1), emit=(1.0, 0.45, 0.08), emit_strength=10.0)


def build_engine(root):
    parts = {}
    parts["tank_f"] = cyl("tank_fuel", 0.9, 2.2, (-1.3, 0, 5.2), M["tank_f"], parent=root)
    parts["tank_o"] = cyl("tank_ox", 0.9, 2.2, (1.3, 0, 5.2), M["tank_o"], parent=root)
    for sx, m in ((-1, "fuel"), (1, "ox")):
        cyl("pump", 0.35, 0.8, (sx * 1.3, 0, 3.6), M["steel"], parent=root)
        cyl("pipe", 0.07, 2.0, (sx * 1.3, 0, 2.6), M["dark"], parent=root)
        cyl("pipe_h", 0.07, 1.3, (sx * 0.65, 0, 1.6), M["dark"], rot=(0, math.pi / 2, 0), parent=root)
    parts["chamber"] = cyl("chamber", 0.8, 1.6, (0, 0, 1.0), M["steel"], parent=root)
    parts["throat"] = cone("throat", 0.8, 0.3, 0.8, (0, 0, -0.2), M["steel"], parent=root)
    parts["bell"] = cone("bell", 0.3, 1.5, 2.2, (0, 0, -1.7), M["steel"], parent=root)
    return parts


def path_point(kind, u, sx):
    """Position along the flow path (u 0..1). Speeds are drawn faster in the nozzle: schematic only."""
    if kind == "prop":        # tank -> pump -> pipe -> chamber
        if u < 0.7:
            return (sx * 1.3, 0, lerp(5.2, 1.6, u / 0.7))
        v = (u - 0.7) / 0.3
        return (sx * 1.3 * (1 - v), 0, 1.6)
    z = lerp(1.2, -3.6, u ** 1.7)              # exhaust: chamber -> throat -> bell, accelerating
    r = 0.55 if z > -0.1 else lerp(0.2, 1.3, min(1.0, (-0.1 - z) / 3.0))
    return (r * 0.6 * math.cos(u * 40), r * 0.6 * math.sin(u * 40), z)


def main():
    opts = parse_args()
    setup_scene(opts, sky=(0.005, 0.007, 0.012), sky_strength=0.3)
    materials()
    area_light("key", (6, -8, 8), (math.radians(55), 0, math.radians(30)), 8, 1500, (1, 0.95, 0.9))
    area_light("rim", (-8, 6, 5), (math.radians(70), 0, math.radians(215)), 8, 900, (0.4, 0.6, 1.0))
    root = empty("engine")
    build_engine(root)
    rig = Rig(lens=38)
    ps = []
    for sx, mat in ((-1, "fuel"), (1, "ox")):
        for k in range(8):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, segments=10, ring_count=6)
            o = bpy.context.object; assign(o, M[mat]); o.parent = root
            ps.append((o, "prop", sx, k / 8))
    for k in range(24):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, segments=10, ring_count=6)
        o = bpy.context.object; assign(o, M["gas"]); o.parent = root
        ps.append((o, "gas", 0, k / 24))
    name = opts["scene"]

    def flow(t, show_prop=True, show_gas=True):
        for o, kind, sx, off in ps:
            on = show_prop if kind == "prop" else show_gas
            o.hide_render = not on
            if on:
                o.location = path_point(kind, (t * 0.35 + off) % 1.0, sx)

    cfg = {
        "hook": (6.0, lambda t, u: (flow(t), rig.look((7 * math.sin(lerp(-0.5, 0.3, u)), -9, 3.5), (0, 0, 1.5), 38))),
        "tanks": (7.0, lambda t, u: (flow(t, True, False), rig.look(lerp3((6, -8, 7), (4, -6, 5), u), (0, 0, 4.2), 38))),
        "chamber": (7.0, lambda t, u: (flow(t), rig.look(lerp3((4, -5, 3), (2.5, -3.2, 1.8), u), (0, 0, 1.0), 40))),
        "nozzle": (8.0, lambda t, u: (flow(t, False, True), rig.look(lerp3((5, -6, -1), (3.2, -4, -2.5), u), (0, 0, -1.3), 38))),
        "thrust": (8.0, lambda t, u: (flow(t, False, True), rig.look((9, -11, lerp(-4, 3, u)), (0, 0, -1 + 2 * u), 38))),
        "space": (8.0, lambda t, u: (flow(t, False, True), rig.look(lerp3((7, -9, 0), (11, -14, 4), u), (0, 0, -0.5), 38))),
    }
    if name not in cfg:
        raise SystemExit("unknown scene " + name)
    seconds, fn = cfg[name]
    render_sequence(opts, lambda t, u: fn(t, u), seconds)


if __name__ == "__main__":
    main()
