"""Blender (4.x) script: a seamless loop of air flowing turbo compressor -> intercooler -> engine.

Run headless:
  blender -b -P blender/intercooler.py -- <out_dir> <frames> <samples> <CYCLES|BLENDER_EEVEE_NEXT>

Writes out_dir/f_000.png ... with a TRANSPARENT background; the pipeline composites it over the
brand background (src/visuals_intercooler.py). Orthographic camera so the framing is predictable:
world x runs left to right, one world unit is about 59 px in the video.

The loop is seamless: the compressor turns a whole number of blade pitches and the air parcels
shift by exactly one spacing, so frame N equals frame 0.

NOT YET RUN IN BLENDER: written without access to Blender (a mock-bpy run only checks the Python
logic). If anything looks wrong after the first render, tune the camera/materials; if the render
fails, the video falls back to the 2D animation automatically.
"""
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, N, SAMPLES, ENGINE = argv[0], int(argv[1]), int(argv[2]), argv[3]
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 520
NAVY, AMBER, CYAN, TEXT, MUTED = (0.04, 0.08, 0.15), (1.0, 0.7, 0.0), (0.18, 0.77, 0.95), (0.95, 0.96, 0.97), (0.36, 0.42, 0.52)
HOT = (1.0, 0.30, 0.06)

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


def cyl_x(name, r, length, x, mat, y=0.0, z=0.0, verts=40):
    """Cylinder whose axis runs along world X."""
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, location=(x, y, z),
                                        rotation=(0, math.pi / 2, 0), vertices=verts)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return finish(o, mat)


def cyl_z(name, r, depth, loc, mat, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts)
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


def ball(name, r, loc, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=8)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return finish(o, mat)


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


# ------------------------------------------------------------------ materials
steel, _ = material("steel", MUTED, metal=1.0, rough=0.35)
bright, _ = material("bright", TEXT, metal=0.9, rough=0.25)
amber_m, _ = material("amber", AMBER, metal=0.6, rough=0.3)
glass, _ = material("glass", (0.6, 0.75, 0.9), rough=0.1, alpha=0.14)
fin_m, _ = material("fin", (0.75, 0.8, 0.88), metal=0.8, rough=0.3)

# ------------------------------------------------------------------ geometry (x runs left -> right)
CORE_X0, CORE_X1, CORE_Y, CORE_Z = -2.6, 1.8, 1.2, 3.0
cx = (CORE_X0 + CORE_X1) / 2
TUBES = (-1.2, -0.6, 0.0, 0.6, 1.2)

cyl_x("pipe_in", 0.5, 2.7, -7.65, glass)                       # air in
cyl_x("compressor_housing", 1.3, 1.6, -5.5, glass, verts=48)   # turbo compressor
cyl_x("pipe_hot", 0.5, 1.7, -3.85, glass)                      # hot air to the intercooler
box("tank_in", (0.4, CORE_Y, CORE_Z), (CORE_X0 - 0.2, 0, 0), steel)
box("tank_out", (0.4, CORE_Y, CORE_Z), (CORE_X1 + 0.2, 0, 0), steel)
box("core_glass", (CORE_X1 - CORE_X0, CORE_Y, CORE_Z), (cx, 0, 0), glass)
for z in TUBES:                                                # tubes carrying the compressed air
    cyl_x("tube", 0.12, CORE_X1 - CORE_X0, cx, amber_m, z=z, verts=20)
for k in range(21):                                            # cooling fins
    box("fin", (0.03, 1.0, CORE_Z - 0.2), (CORE_X0 + 0.2 + 0.2 * k, 0, 0), fin_m)
cyl_x("pipe_cool", 0.5, 2.0, 3.2, glass)                       # cooled air to the engine
box("engine", (2.6, 1.7, 2.2), (5.5, 0, 0), steel)
for k in range(4):
    cyl_z("engine_cyl", 0.3, 0.5, (4.7 + 0.6 * k, 0, 1.35), bright)

wheel = bpy.data.objects.new("wheel", None)                    # compressor wheel, turns about X
wheel.location = (-5.5, 0, 0)
scene.collection.objects.link(wheel)
NB = 10
hub = cyl_x("hub", 0.2, 0.7, 0.0, bright, verts=24)
hub.parent = wheel
for k in range(NB):
    a = 2 * math.pi * k / NB
    blade = box("blade", (0.5, 0.06, 0.9), (0.0, 0.55 * math.cos(a), 0.55 * math.sin(a)), amber_m)
    blade.rotation_euler = (a - math.pi / 2, 0, 0)
    blade.parent = wheel

# ------------------------------------------------------------------ air parcels
NP, NA = 28, 16
KEYS = [(0.0, -9.0), (0.2, -5.5), (0.5, 1.8), (1.0, 6.8)]      # (u, x): sparse when hot, dense after cooling


def x_of(u):
    for (u0, x0), (u1, x1) in zip(KEYS, KEYS[1:]):
        if u <= u1:
            return x0 + (x1 - x0) * (u - u0) / (u1 - u0)
    return KEYS[-1][1]


def temp(x):
    if x < -5.9:
        return 0.0
    if x < -4.9:
        return smooth(x + 5.9)
    if x < CORE_X0:
        return 1.0
    if x < CORE_X1:
        return 1.0 - (x - CORE_X0) / (CORE_X1 - CORE_X0)
    return 0.0


parcels = []
for j in range(NP):
    m, b = material(f"parcel{j}", CYAN, rough=0.6, emit=CYAN, emit_strength=0.8)
    parcels.append((ball(f"parcel{j}", 0.14, (0, 0, 0), m), b))
ambient = []
for k in range(NA):
    m, b = material(f"amb{k}", (0.8, 0.95, 1.0), rough=0.6, emit=(0.7, 0.9, 1.0), emit_strength=1.0)
    ambient.append(ball(f"amb{k}", 0.09, (0, 0, 0), m))

# ------------------------------------------------------------------ lights, camera
bpy.ops.object.light_add(type="AREA", location=(5, -8, 9))
bpy.context.active_object.data.energy = 900
bpy.context.active_object.data.size = 8
bpy.ops.object.light_add(type="AREA", location=(-9, -6, 4))
bpy.context.active_object.data.energy = 500
bpy.context.active_object.data.color = CYAN
bpy.ops.object.light_add(type="SUN", location=(0, 0, 10))
bpy.context.active_object.data.energy = 1.5

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (*NAVY, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

CX = -1.1                                                      # frame centre (x)
YAW = 0.26                                                     # ~15 degrees, gives the 3D look
bpy.ops.object.empty_add(location=(CX, 0, 0))
target = bpy.context.active_object
bpy.ops.object.camera_add(location=(CX + 20 * math.sin(YAW), -20 * math.cos(YAW), 4.0))
cam = bpy.context.active_object
cam.data.type = "ORTHO"
cam.data.ortho_scale = 17.6                                    # world width shown (x)
con = cam.constraints.new("TRACK_TO")
con.target, con.track_axis, con.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
scene.camera = cam

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
def pose(t):
    """t in [0, 1): one full loop."""
    wheel.rotation_euler = (t * 2 * math.pi / NB * 12, 0, 0)   # 12 blade pitches per loop
    for j, (o, b) in enumerate(parcels):
        u = (j / NP + t / NP) % 1.0                            # shifts by one spacing per loop
        x = x_of(u)
        lane = TUBES[j % len(TUBES)]
        spread = smooth((x - (CORE_X0 - 0.4)) / 0.4) * smooth((CORE_X1 + 0.4 - x) / 0.4)
        o.location = (x, 0.2 * math.sin(j * 1.7), lane * spread)
        c = lerp(CYAN, HOT, temp(x))
        set_in(b, ["Base Color"], (*c, 1))
        set_in(b, ["Emission Color", "Emission"], (*c, 1))
    for k, o in enumerate(ambient):
        ph = (k * 0.37 + t) % 1.0
        o.location = (CORE_X0 + 0.3 + 0.25 * k, 0.45 * math.sin(k * 2.3), 2.1 - 4.2 * ph)


for i in range(N):
    path = os.path.join(OUT, f"f_{i:03d}.png")
    if os.path.exists(path):
        continue
    pose(i / N)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"frame {i + 1}/{N}")
