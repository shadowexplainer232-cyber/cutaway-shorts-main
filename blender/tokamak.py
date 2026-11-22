"""Blender (4.x) script: a tokamak (ring-shaped fusion machine) with glowing plasma and magnet coils.

Run headless:
  blender -b -P blender/tokamak.py -- <out_dir> <frames> <samples> <CYCLES|BLENDER_EEVEE_NEXT>

Writes out_dir/f_000.png ... with a TRANSPARENT background (1080x780). Orthographic camera at
elevation ~32.5 degrees, 86.4 px per world unit, looking at the origin; src/visuals_fusion.py draws
the same geometry in 2D (same projection) as the fallback. Seamless loop: the plasma glow particles
shift by exactly 3 spacings per loop.

NOT YET RUN IN BLENDER (a mock-bpy run only checks the Python logic). Schematic, not to scale.
"""
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, N, SAMPLES, ENGINE = argv[0], int(argv[1]), int(argv[2]), argv[3]
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 780
NAVY, AMBER, CYAN, TEXT, MUTED = (0.04, 0.08, 0.15), (1.0, 0.7, 0.0), (0.18, 0.77, 0.95), (0.95, 0.96, 0.97), (0.36, 0.42, 0.52)
PLASMA = (1.0, 0.55, 0.12)
R, R_TUBE, R_PLASMA, N_COILS = 3.0, 1.1, 0.45, 16

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


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


def torus(name, major, minor, loc, mat, rot=(0, 0, 0), maj_seg=96, min_seg=24):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc, rotation=rot,
                                     major_segments=maj_seg, minor_segments=min_seg)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return finish(o, mat)


def ball(name, r, loc, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=8)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return finish(o, mat)


glass, _ = material("glass", (0.6, 0.75, 0.9), rough=0.1, alpha=0.12)
plasma_m, _ = material("plasma", PLASMA, rough=0.7, alpha=0.55, emit=PLASMA, emit_strength=3.0)
coil_m, _ = material("coil", CYAN, metal=0.8, rough=0.3)
spark_m, _ = material("spark", (1.0, 0.9, 0.6), emit=(1.0, 0.85, 0.5), emit_strength=8.0)

torus("vessel", R, R_TUBE, (0, 0, 0), glass)                         # vacuum vessel
torus("plasma", R, R_PLASMA, (0, 0, 0), plasma_m)                     # glowing plasma ring
for k in range(N_COILS):                                              # magnet coils around the tube
    phi = 2 * math.pi * k / N_COILS
    torus(f"coil{k}", R_TUBE + 0.45, 0.12, (R * math.cos(phi), R * math.sin(phi), 0), coil_m,
          rot=(math.pi / 2, 0, phi), maj_seg=40, min_seg=12)

NS = 18
sparks = [ball(f"spark{k}", 0.09, (0, 0, 0), spark_m) for k in range(NS)]

bpy.ops.object.light_add(type="AREA", location=(5, -9, 9))
bpy.context.active_object.data.energy = 1200
bpy.context.active_object.data.size = 8
bpy.ops.object.light_add(type="AREA", location=(-8, -5, 4))
bpy.context.active_object.data.energy = 500
bpy.context.active_object.data.color = CYAN
bpy.ops.object.light_add(type="SUN", location=(0, 0, 10))
bpy.context.active_object.data.energy = 1.2

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (*NAVY, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

bpy.ops.object.empty_add(location=(0, 0, 0))
target = bpy.context.active_object
bpy.ops.object.camera_add(location=(0, -11, 7))                       # elevation ~32.5 degrees
cam = bpy.context.active_object
cam.data.type = "ORTHO"
cam.data.ortho_scale = 12.5                                           # 1080 px / 12.5 = 86.4 px per unit
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


def pose(t):
    for k, o in enumerate(sparks):
        theta = 2 * math.pi * (k / NS + 3 * t / NS)                   # 3 spacings per loop: seamless
        psi = 3 * theta                                               # helical path around the ring
        r = R + 0.28 * math.cos(psi)
        o.location = (r * math.cos(theta), r * math.sin(theta), 0.28 * math.sin(psi))


for i in range(N):
    path = os.path.join(OUT, f"f_{i:03d}.png")
    if os.path.exists(path):
        continue
    pose(i / N)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"frame {i + 1}/{N}")
