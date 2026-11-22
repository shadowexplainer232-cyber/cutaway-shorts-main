"""Blender scenes for episode 014: a W16 engine layout, four turbochargers and a stylised hypercar.

  blender -b -P blender/aero/w16.py -- <scene> <out_dir> [--scale 25] [--samples 32] [--fps 15] [--hdri file]
  scenes: intro | reveal | layout | turbos | running | ending

HONEST LIMITS: the car is a STYLISED GENERIC hypercar (no Bugatti badge, grille or body surfaces; it is NOT a Chiron
model). The engine is a simplified layout model: 16 cylinders in 4 rows of 4 (two V-banks of 8 at 90 degrees, each bank
two staggered rows 15 degrees apart), one shared crankshaft, 4 turbochargers. 73 mm pitch is the only figure taken from a
source (Bugatti press release); bore, stroke, rod length and firing phases are ILLUSTRATIVE. Units: 1 unit = 100 mm.
NOT YET RUN IN REAL BLENDER (mock-bpy tested only).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aero import *  # noqa: E402

PITCH = 0.73                         # 73 mm between neighbouring cylinders of the staggered pair (source: Bugatti)
BORE, CR, ROD = 0.86, 0.43, 1.45     # illustrative
ROW_ANGLES = [-52.5, -37.5, 37.5, 52.5]          # two 90-degree banks (-45 / +45), each with two rows 15 deg apart
ROW_COLORS = [(1.0, 0.7, 0.0), (0.18, 0.77, 0.95), (1.0, 0.7, 0.0), (0.18, 0.77, 0.95)]
M = {}
CAR = []                              # objects hidden in the engine-only scenes


def materials():
    M["paint"] = material("paint", (0.02, 0.03, 0.08), metal=0.9, rough=0.12)
    M["trim"] = material("trim", (0.7, 0.45, 0.1), metal=1.0, rough=0.3)
    M["tyre"] = material("tyre", (0.02, 0.02, 0.02), rough=0.8)
    M["alu"] = material("alu", (0.62, 0.64, 0.68), metal=1.0, rough=0.35)
    M["dark"] = material("dark", (0.05, 0.05, 0.06), metal=0.6, rough=0.5)
    M["floor"] = material("floor", (0.03, 0.03, 0.04), metal=0.2, rough=0.35)
    M["hot"] = material("hot", (1, 0.45, 0.1), emit=(1.0, 0.4, 0.08), emit_strength=6.0)
    M["cold"] = material("cold", (0.2, 0.6, 1.0), emit=(0.2, 0.65, 1.0), emit_strength=6.0)
    for i, c in enumerate(ROW_COLORS):
        M[f"row{i}"] = material(f"row{i}", (0.55, 0.57, 0.6), metal=1.0, rough=0.35, emit=c, emit_strength=0.0)


# ---------------------------------------------------------------- car (stylised, generic)
def build_car():
    root = empty("car")
    parts = [
        box("floor_plate", (2.0, 4.6, 0.25), (0, 0, 0.35), M["dark"], parent=root),
    ]
    body = bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0.75), segments=48, ring_count=24)
    b = bpy.context.object
    b.name = "body"
    b.scale = (0.95, 2.3, 0.42)
    assign(b, M["paint"]); b.parent = root
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, -0.2, 1.1), segments=32, ring_count=16)
    cab = bpy.context.object
    cab.name = "cabin"; cab.scale = (0.7, 1.1, 0.35); assign(cab, M["dark"]); cab.parent = root
    cover = box("engine_cover", (1.3, 1.3, 0.12), (0, 1.35, 0.98), M["paint"], parent=root)     # lifted off in 'reveal'
    wheels = []
    for sx in (-1, 1):
        for y in (-1.5, 1.5):
            w = cyl("wheel", 0.38, 0.32, (sx * 1.0, y, 0.38), M["tyre"], rot=(0, math.pi / 2, 0), parent=root)
            hub = cyl("hub", 0.22, 0.34, (sx * 1.0, y, 0.38), M["trim"], rot=(0, math.pi / 2, 0), parent=root)
            wheels += [w, hub]
    for o in [b, cab, cover, *parts, *wheels]:
        CAR.append(o)
    return root, cover


# ---------------------------------------------------------------- engine
def build_engine(root):
    cyls = []
    n = 0
    for r, ang in enumerate(ROW_ANGLES):
        stagger = PITCH if r in (1, 3) else 0.0
        for i in range(4):
            y = (i * 2 * PITCH) + stagger - 3.5 * PITCH      # centred on the crank
            th = math.radians(ang)
            d = (math.sin(th), math.cos(th))
            liner = cyl(f"liner{n}", BORE / 2 + 0.08, 1.7, (d[0] * 1.85, y, d[1] * 1.85), M[f"row{r}"],
                        rot=(0, th, 0), verts=24, parent=root)
            piston = cyl(f"piston{n}", BORE / 2 - 0.02, 0.5, (0, y, 0), M["alu"], rot=(0, th, 0), verts=24, parent=root)
            rod = cyl(f"rod{n}", 0.08, 1.0, (0, y, 0), M["alu"], verts=10, parent=root)
            throw = int(round((y + 3.5 * PITCH) / PITCH))     # 0..7: eight crank throws shared by the rows
            cyls.append({"th": th, "d": d, "y": y, "piston": piston, "rod": rod, "phase": math.radians(90 * (throw % 4) + 180 * (throw // 4)), "row": r})
            n += 1
    crank = cyl("crankshaft", 0.18, 8 * PITCH + 1.2, (0, 0, 0), M["alu"], rot=(math.pi / 2, 0, 0), verts=20, parent=root)
    pins = [cyl(f"pin{k}", 0.1, 0.5, (0, (k - 3.5) * PITCH, CR), M["trim"], rot=(math.pi / 2, 0, 0), verts=12, parent=root)
            for k in range(8)]
    return cyls, crank, pins


def animate_engine(cyls, pins, phi):
    """phi = crank angle (radians). Piston s = r cos(a) + sqrt(L^2 - r^2 sin^2 a), a = phi - bank angle."""
    for p in pins:
        pass
    for c in cyls:
        a = phi + c["phase"] - c["th"]
        s = CR * math.cos(a) + math.sqrt(ROD * ROD - (CR * math.sin(a)) ** 2)
        Q = (c["d"][0] * s, c["d"][1] * s)
        c["piston"].location = (Q[0], c["y"], Q[1])
        P = (CR * math.sin(phi + c["phase"]), CR * math.cos(phi + c["phase"]))
        dx, dz = Q[0] - P[0], Q[1] - P[1]
        L = math.hypot(dx, dz)
        c["rod"].location = ((P[0] + Q[0]) / 2, c["y"], (P[1] + Q[1]) / 2)
        c["rod"].rotation_euler = (0, math.atan2(dx, dz), 0)
        c["rod"].scale = (1, 1, L)


def build_turbos(root):
    """Four turbochargers: two each side behind the engine. Returns [(wheel_t, wheel_c, pos)]."""
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            pos = (sx * 3.6, sy * 2.2, 0.9)
            t = empty(f"turbo_{sx}_{sy}", pos, parent=root)
            cone("turbine_housing", 0.8, 0.45, 1.0, (0, 0, 0), M["dark"], rot=(0, math.pi / 2 * sx, 0), parent=t).location = (sx * 0.5, 0, 0)
            cone("compressor_housing", 0.6, 0.3, 0.9, (0, 0, 0), M["alu"], rot=(0, -math.pi / 2 * sx, 0), parent=t).location = (-sx * 0.6, 0, 0)
            wt = cyl("turbine_wheel", 0.5, 0.08, (sx * 0.45, 0, 0), M["hot"], rot=(0, math.pi / 2, 0), parent=t)
            wc = cyl("compressor_wheel", 0.4, 0.08, (-sx * 0.55, 0, 0), M["cold"], rot=(0, math.pi / 2, 0), parent=t)
            out.append({"wt": wt, "wc": wc, "pos": pos, "sx": sx, "sy": sy})
    return out


def build_flow(root, turbos, per=6):
    """Small glowing spheres that travel along exhaust (hot) and intake (cold) paths; positioned per frame."""
    flow = []
    for tb in turbos:
        for k in range(per):
            for hot in (True, False):
                bpy.ops.mesh.primitive_uv_sphere_add(radius=0.09, location=(0, 0, 0), segments=10, ring_count=6)
                o = bpy.context.object
                assign(o, M["hot" if hot else "cold"]); o.parent = root
                flow.append({"o": o, "tb": tb, "k": k, "hot": hot, "n": per})
    return flow


def update_flow(flow, t, strength=1.0):
    for f in flow:
        tb = f["tb"]
        u = (t * 0.5 + f["k"] / f["n"]) % 1.0
        sx, sy = tb["sx"], tb["sy"]
        if f["hot"]:     # exhaust: from the cylinder area outward to the turbine
            a, b = (sx * 1.8, sy * 1.2, 1.5), (tb["pos"][0] + sx * 0.4, tb["pos"][1], tb["pos"][2])
        else:            # intake: out of the compressor, up and back into the engine
            a, b = (tb["pos"][0] - sx * 0.7, tb["pos"][1], tb["pos"][2] + 0.1), (sx * 1.2, sy * 0.6, 2.4)
        p = lerp3(a, b, u)
        f["o"].location = (p[0], p[1], p[2] + 0.5 * math.sin(math.pi * u))
        f["o"].scale = (strength,) * 3


def lights():
    area_light("key", (6, -8, 10), (math.radians(55), 0, math.radians(30)), 8, 1500, (1.0, 0.95, 0.9))
    area_light("rim", (-8, 6, 6), (math.radians(70), 0, math.radians(215)), 8, 900, (0.4, 0.6, 1.0))
    area_light("top", (0, 0, 12), (0, 0, 0), 10, 600, (1, 1, 1))


def main():
    opts = parse_args()
    setup_scene(opts, sky=(0.005, 0.007, 0.012), sky_strength=0.3)
    materials()
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    assign(bpy.context.object, M["floor"])
    car, cover = build_car()
    erot = empty("engine_root", (0, 1.35, 0.7))
    cyls, crank, pins = build_engine(erot)
    turbos = build_turbos(erot)
    flow = build_flow(erot, turbos)
    lights()
    rig = Rig(lens=40)
    name = opts["scene"]

    def engine_only(on):
        for o in CAR:
            o.hide_render = on
        car.hide_render = on

    def set_engine(scale, loc):
        erot.scale = (scale,) * 3
        erot.location = loc

    def spin(t, rate=2.5):
        phi = t * rate
        animate_engine(cyls, pins, phi)
        for tb in turbos:
            tb["wt"].rotation_euler = (phi * 4, 0, 0)
            tb["wc"].rotation_euler = (phi * 4, 0, 0)
        crank.rotation_euler = (math.pi / 2, phi, 0)
        return phi

    ES = 0.1                                                    # engine scale inside the car
    if name == "intro":
        seconds = 6.0
        set_engine(ES, (0, 1.35, 0.7)); spin(0)

        def pose(t, u):
            a = lerp(-0.7, 0.2, smooth(u))
            rig.look((6 * math.sin(a), -6.5 * math.cos(a), 1.3), (0, 0, 0.8), lerp(40, 55, u))
    elif name == "reveal":
        seconds = 7.0
        set_engine(ES, (0, 1.35, 0.7))

        def pose(t, u):
            cover.location = (0, 1.35, 0.98 + 2.5 * seg(u, 0.3, 0.7))
            spin(t, 1.5)
            rig.look(lerp3((4.5, -3.0, 1.6), (0.9, 3.4, 1.9), smooth(u)), (0, 1.35, 0.85), lerp(40, 55, u))
    elif name == "layout":
        seconds = 12.0
        engine_only(True); set_engine(1.0, (0, 0, 0))

        def pose(t, u):
            spin(t, 0.8)
            for r in range(4):                                    # light the four rows one after another
                k = seg(u, 0.12 + r * 0.17, 0.2 + r * 0.17) * (1 - seg(u, 0.84, 0.95) * 0)
                M[f"row{r}"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 5.0 * k
            a = lerp(-0.4, 0.4, smooth(u))
            rig.look((8 * math.sin(a), -10 * math.cos(a), 5), (0, 0, 1), 40)
    elif name == "turbos":
        seconds = 12.0
        engine_only(True); set_engine(1.0, (0, 0, 0))

        def pose(t, u):
            spin(t, 3.0)
            update_flow(flow, t)
            a = lerp(0.2, 1.2, smooth(u))
            rig.look((9 * math.sin(a), -9 * math.cos(a), 4.5), (0, 0, 1.0), 38)
    elif name == "running":
        seconds = 11.0
        engine_only(True); set_engine(1.0, (0, 0, 0))

        def pose(t, u):
            spin(t, 2.5)
            update_flow(flow, t)
            a = lerp(-0.6, 0.6, smooth(u))
            rig.look((7 * math.sin(a), -9 * math.cos(a), 5.5), (0, 0, 1.0), 38)
    elif name == "ending":
        seconds = 8.0
        set_engine(ES, (0, 1.35, 0.7)); spin(0)

        def pose(t, u):
            a = lerp(0.2, -0.5, smooth(u))
            rig.look(lerp3((5.0 * math.sin(a), -7 * math.cos(a), 1.2), (7.5 * math.sin(a), -11 * math.cos(a), 2.2), u), (0, 0, 0.8), 38)
    else:
        raise SystemExit("unknown scene " + name)
    render_sequence(opts, pose, seconds)


if __name__ == "__main__":
    main()
