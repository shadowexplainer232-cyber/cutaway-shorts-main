"""Reusable Blender helpers for aerospace / engineering scenes (Eevee, lightweight, procedural).

Import from a scene script with:  sys.path.insert(0, <this folder>); from aero import *
Everything is primitives + materials (no external files), so nothing large is needed. Models are STYLISED
illustrations with simple proportions, NOT engineering drawings. NOT YET RUN IN REAL BLENDER (mock-bpy tested only).
"""
import math
import os
import sys

import bpy

# ---------------------------------------------------------------- arguments
def parse_args(argv=None):
    """blender -b -P scene.py -- <scene> <out_dir> [--scale 25] [--samples 32] [--engine BLENDER_EEVEE_NEXT] [--fps 15] [--hdri file]"""
    argv = argv if argv is not None else sys.argv
    a = argv[argv.index("--") + 1:] if "--" in argv else []
    o = {"scene": None, "out": None, "scale": 25, "samples": 32, "engine": "BLENDER_EEVEE_NEXT", "fps": 15, "hdri": None,
         "frames": None}
    pos, i = [], 0
    while i < len(a):
        if a[i].startswith("--"):
            k = a[i][2:]
            o[k] = type(o[k])(a[i + 1]) if o.get(k) is not None else a[i + 1]
            i += 2
        else:
            pos.append(a[i]); i += 1
    if len(pos) < 2:
        raise SystemExit("usage: -- <scene> <out_dir> [--scale 25] [--samples 32] [--engine ...] [--fps 15] [--hdri file]")
    o["scene"], o["out"] = pos[0], pos[1]
    return o


# ---------------------------------------------------------------- math helpers
def lerp(a, b, t):
    return a + (b - a) * t


def clamp01(t):
    return max(0.0, min(1.0, t))


def smooth(t):
    t = clamp01(t)
    return t * t * (3 - 2 * t)


def seg(t, a, b):
    """0..1 progress of t inside [a, b] (smoothed)."""
    return smooth((t - a) / (b - a)) if b > a else 1.0


def lerp3(p, q, t):
    return tuple(lerp(p[i], q[i], t) for i in range(3))


# ---------------------------------------------------------------- scene / render
def setup_scene(opts, sky=(0.02, 0.03, 0.06), sky_strength=0.6):
    """Empty scene, vertical 1080x1920 at opts['scale'] %, Eevee, optional Poly Haven HDRI for lighting."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    r = sc.render
    r.resolution_x, r.resolution_y = 1080, 1920
    r.resolution_percentage = int(opts["scale"])
    r.image_settings.file_format = "PNG"
    r.film_transparent = False
    try:
        sc.render.engine = opts["engine"]
    except TypeError:                                   # older Blender: Eevee was called BLENDER_EEVEE
        sc.render.engine = "BLENDER_EEVEE"
    for attr in ("taa_render_samples",):
        if hasattr(sc.eevee, attr):
            setattr(sc.eevee, attr, int(opts["samples"]))
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    sc.world = world
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    hdri = opts.get("hdri")
    if hdri and os.path.exists(hdri):
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 1.0
    else:
        bg.inputs["Color"].default_value = (*sky, 1)
        bg.inputs["Strength"].default_value = sky_strength
    return sc


def set_in(bsdf, names, value):
    for n in names:
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = value
            return


def material(name, color, metal=0.0, rough=0.5, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    set_in(b, ["Base Color"], (*color, 1))
    set_in(b, ["Metallic"], metal)
    set_in(b, ["Roughness"], rough)
    if emit:
        set_in(b, ["Emission Color", "Emission"], (*emit, 1))
        set_in(b, ["Emission Strength"], emit_strength)
    return m


def assign(obj, mat):
    obj.data.materials.append(mat)
    return obj


def sun_light(name, rot, energy=3.0, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="SUN", rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.energy = energy
    o.data.color = color
    return o


def area_light(name, loc, rot, size, energy, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.size = size
    o.data.energy = energy
    o.data.color = color
    return o


# ---------------------------------------------------------------- primitives
def cyl(name, r, h, loc, mat=None, rot=(0, 0, 0), verts=32, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    if mat:
        assign(o, mat)
    if parent:
        o.parent = parent
    return o


def cone(name, r1, r2, h, loc, mat=None, rot=(0, 0, 0), verts=24, parent=None):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    if mat:
        assign(o, mat)
    if parent:
        o.parent = parent
    return o


def box(name, size, loc, mat=None, parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    if mat:
        assign(o, mat)
    if parent:
        o.parent = parent
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    if parent:
        o.parent = parent
    return o


# ---------------------------------------------------------------- camera
class Rig:
    """Camera that always looks at a target empty; set per frame with look(pos, target, lens)."""

    def __init__(self, lens=35):
        bpy.ops.object.camera_add()
        self.cam = bpy.context.object
        self.cam.data.lens = lens
        self.cam.data.clip_end = 5000
        self.target = empty("cam_target")
        c = self.cam.constraints.new("TRACK_TO")
        c.target = self.target
        c.track_axis = "TRACK_NEGATIVE_Z"
        c.up_axis = "UP_Y"
        bpy.context.scene.camera = self.cam

    def look(self, pos, target, lens=None):
        self.cam.location = pos
        self.target.location = target
        if lens:
            self.cam.data.lens = lens


# ---------------------------------------------------------------- render loop
def render_sequence(opts, apply_pose, seconds, log=print):
    """Resumable: renders f_0001.png ... into opts['out'] (skips frames that exist); writes meta.json last.

    apply_pose(t, u): set every object for time t seconds (u = t / seconds, 0..1).
    """
    import json
    sc = bpy.context.scene
    fps = int(opts["fps"])
    n = int(opts["frames"]) if opts.get("frames") else max(1, round(seconds * fps))
    os.makedirs(opts["out"], exist_ok=True)
    for i in range(n):
        path = os.path.join(opts["out"], f"f_{i + 1:04d}.png")
        if os.path.exists(path):
            continue
        t = (i / max(1, n - 1)) * seconds
        apply_pose(t, t / seconds if seconds else 0.0)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if i % 10 == 0:
            log(f"  frame {i + 1}/{n}")
    with open(os.path.join(opts["out"], "meta.json"), "w") as f:
        json.dump({"scene": opts["scene"], "frames": n, "fps": fps, "seconds": seconds, "scale_percent": int(opts["scale"])}, f)
    log(f"Done: {n} frames in {opts['out']}")
