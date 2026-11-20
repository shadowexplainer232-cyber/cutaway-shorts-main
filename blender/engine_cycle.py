"""Blender (4.x) script: one full 720-degree four-stroke cycle of a cutaway piston engine.

Run headless:
  blender -b -P blender/engine_cycle.py -- <out_dir> <frames> <samples> <CYCLES|BLENDER_EEVEE_NEXT>

Writes out_dir/f_000.png ... with a TRANSPARENT background so the pipeline composites it over the
brand background. Geometry uses real slider-crank kinematics (same maths as the 2D fallback).
Units: 1 unit = 100 px of the 2D design. Crank centre is the origin, cylinder axis is +Z.

NOT YET RUN: this file was written without access to Blender. Expect to tune the camera/materials
after the first render.
"""
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, N, SAMPLES, ENGINE = argv[0], int(argv[1]), int(argv[2]), argv[3]
os.makedirs(OUT, exist_ok=True)

R, ROD, HEAD_Z, BORE_R = 1.0, 2.6, 4.6, 1.7
W, H = 1080, 780

# colours (linear-ish RGBA)
NAVY, AMBER, CYAN, TEXT, MUTED = (0.04, 0.08, 0.15), (1.0, 0.7, 0.0), (0.18, 0.77, 0.95), (0.95, 0.96, 0.97), (0.36, 0.42, 0.52)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


# ------------------------------------------------------------------ helpers
def set_in(bsdf, names, value):
    for n in names:
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = value
            return


def material(name, color, metal=0.0, rough=0.5, alpha=1.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    set_in(b, ["Base Color"], (*color, 1))
    set_in(b, ["Metallic"], metal)
    set_in(b, ["Roughness"], rough)
    set_in(b, ["Alpha"], alpha)
    if emit:
        set_in(b, ["Emission Color", "Emission"], (*emit, 1))
        set_in(b, ["Emission Strength"], emit_strength)
    return m, b


def finish(obj, mat):
    obj.data.materials.append(mat)
    return obj


def cyl(name, r, depth, loc, mat, rot=(0, 0, 0), verts=48):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return finish(o, mat)


def box(name, size, loc, mat):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    return finish(o, mat)


# ------------------------------------------------------------------ materials
steel, _ = material("steel", MUTED, metal=1.0, rough=0.35)
bright, _ = material("bright", TEXT, metal=0.9, rough=0.25)
amber_m, _ = material("amber", AMBER, metal=0.6, rough=0.3)
glass, _ = material("glass", (0.6, 0.75, 0.9), rough=0.1, alpha=0.16)
gas_m, gas_b = material("gas", CYAN, rough=0.8, alpha=0.4, emit=CYAN, emit_strength=0.3)
spark_m, spark_b = material("spark", AMBER, emit=AMBER, emit_strength=0.0)

# ------------------------------------------------------------------ cylinder (half cut away)
shell = cyl("shell", BORE_R, HEAD_Z - 1.2, (0, 0, (HEAD_Z + 1.2) / 2), glass, verts=64)
shell.modifiers.new("solid", "SOLIDIFY").thickness = 0.12
cutter = box("cutter", (6, 3, 8), (0, -1.5, 2.9), steel)          # removes the front half (y < 0)
bool_mod = shell.modifiers.new("cut", "BOOLEAN")
bool_mod.operation, bool_mod.object = "DIFFERENCE", cutter
bpy.context.view_layer.objects.active = shell
bpy.ops.object.modifier_apply(modifier="solid")
bpy.ops.object.modifier_apply(modifier="cut")
bpy.data.objects.remove(cutter)

box("head", (3.9, 3.9, 0.7), (0, 0, HEAD_Z + 0.35), steel)

# ------------------------------------------------------------------ moving parts
piston = cyl("piston", BORE_R - 0.08, 0.9, (0, 0, 3), bright)
gas = cyl("gas", BORE_R - 0.1, 1.0, (0, 0, 4), gas_m)
rod = cyl("rod", 0.09, ROD, (0, 0, 2), bright)
piston_pin = cyl("ppin", 0.14, 1.0, (0, 0, 3), steel, rot=(math.pi / 2, 0, 0))

crank = bpy.data.objects.new("crank", None)
scene.collection.objects.link(crank)
web = box("web", (0.5, 0.25, 2.3), (0, 0, 0), steel)
cpin = cyl("cpin", 0.17, 0.5, (0, 0, R), amber_m, rot=(math.pi / 2, 0, 0))
for o in (web, cpin):
    o.parent = crank
cyl("crank_hub", 0.3, 0.5, (0, 0, 0), steel, rot=(math.pi / 2, 0, 0))

VALVES = {}
for name, x in (("intake", -0.95), ("exhaust", 0.95)):
    stem = cyl(f"{name}_stem", 0.05, 1.0, (x, 0, HEAD_Z + 0.4), bright)
    vhead = cyl(f"{name}_head", 0.34, 0.08, (x, 0, HEAD_Z - 0.04), amber_m)
    VALVES[name] = (stem, vhead)

cyl("spark_plug", 0.09, 1.0, (0, 0, HEAD_Z + 0.6), bright)
flash = cyl("flash", 0.2, 0.2, (0, 0, HEAD_Z - 0.15), spark_m)

# ------------------------------------------------------------------ lights, camera, world
bpy.ops.object.light_add(type="AREA", location=(5, -8, 9))
bpy.context.active_object.data.energy = 900
bpy.context.active_object.data.size = 6
bpy.ops.object.light_add(type="AREA", location=(-7, -6, 3))
bpy.context.active_object.data.energy = 400
bpy.context.active_object.data.color = CYAN
bpy.ops.object.light_add(type="SUN", location=(0, 0, 10))
bpy.context.active_object.data.energy = 1.5

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (*NAVY, 1)
bg.inputs["Strength"].default_value = 0.6

bpy.ops.object.empty_add(location=(0, 0, 2.1))
target = bpy.context.active_object
bpy.ops.object.camera_add(location=(6.5, -16.5, 4.2))
cam = bpy.context.active_object
cam.data.lens = 60
con = cam.constraints.new("TRACK_TO")
con.target, con.track_axis, con.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
scene.camera = cam

# ------------------------------------------------------------------ render settings
try:
    scene.render.engine = ENGINE
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
if scene.render.engine == "CYCLES":
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.cycles.device = "CPU"
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = W, H, 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"


# ------------------------------------------------------------------ per-frame state
def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lift(theta, start, end):
    """Valve lift 0..1: opens over 15 degrees at `start`, closes over 15 degrees before `end`."""
    return smooth((theta - start) / 15) * smooth((end - theta) / 15)


def blend(c1, c2, a):
    return tuple(c1[i] * (1 - a) + c2[i] * a for i in range(3))


def pose(theta):
    rad = math.radians(theta)
    pin_x, pin_z = R * math.sin(rad), R * math.cos(rad)
    ppin_z = pin_z + math.sqrt(ROD ** 2 - pin_x ** 2)
    top = ppin_z + 0.6

    crank.rotation_euler = (0, rad, 0)
    piston.location = (0, 0, top - 0.45)
    piston_pin.location = (0, 0, ppin_z)
    # rod from crank pin to piston pin
    mid = ((pin_x + 0) / 2, 0, (pin_z + ppin_z) / 2)
    rod.location = mid
    rod.rotation_euler = (0, math.atan2(-pin_x, ppin_z - pin_z), 0)

    h = max(0.05, HEAD_Z - top)
    gas.scale = (1, 1, h)
    gas.location = (0, 0, top + h / 2)

    idx, loc = int(theta // 180) % 4, (theta % 180) / 180
    if idx == 0:
        col, a, em = blend(NAVY, CYAN, 0.35 + 0.2 * loc), 0.25 + 0.15 * loc, 0.2
    elif idx == 1:
        col, a, em = blend(NAVY, CYAN, 0.55 + 0.4 * loc), 0.35 + 0.25 * loc, 0.4
    elif idx == 2:
        col, a, em = blend(AMBER, MUTED, 0.15 + 0.75 * loc), 0.55, 2.5 * (1 - loc) + 0.2
    else:
        col, a, em = blend(MUTED, NAVY, 0.2 + 0.6 * loc), 0.3 * (1 - loc) + 0.1, 0.0
    set_in(gas_b, ["Base Color"], (*col, 1))
    set_in(gas_b, ["Emission Color", "Emission"], (*col, 1))
    set_in(gas_b, ["Emission Strength"], em)
    set_in(gas_b, ["Alpha"], a)

    for name, (s, e) in (("intake", (0, 180)), ("exhaust", (540, 720))):
        d = 0.26 * lift(theta, s, e)
        stem, head = VALVES[name]
        stem.location.z = HEAD_Z + 0.4 - d
        head.location.z = HEAD_Z - 0.04 - d

    set_in(spark_b, ["Emission Strength"], 40.0 * max(0.0, 1 - (theta - 360) / 36) if 360 <= theta < 396 else 0.0)


for i in range(N):
    path = os.path.join(OUT, f"f_{i:03d}.png")
    if os.path.exists(path):
        continue
    pose(i / N * 720.0)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"frame {i + 1}/{N}")
