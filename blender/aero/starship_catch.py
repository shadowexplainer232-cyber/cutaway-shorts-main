"""Blender scenes for episode 013: a launch tower with two arms catching a returning booster.

  blender -b -P blender/aero/starship_catch.py -- <scene> <out_dir> [--scale 25] [--samples 32] [--fps 15] [--hdri file]
  scenes: intro | mechazilla | return | catch | engineering | ending     (python -m studio.render_scenes 013 does this for you)

STYLISED illustration built from primitives. Proportions follow public figures only where the script states them
(booster ~71 m, 33 engines). The tower height, arm length, catch hardpoints and every internal detail are
ILLUSTRATIVE, not engineering data. Only the booster is caught; the upper stage is never shown being caught.
NOT YET RUN IN REAL BLENDER (mock-bpy tested only).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aero import *  # noqa: E402

BOOSTER_H, BOOSTER_R = 71.0, 4.5          # public figures: 71 m tall; radius is the usual ~9 m diameter / 2 (illustrative)
SHIP_H = 52.0                              # upper stage shown only stacked on the booster (never caught)
TOWER_X, TOWER_H = -13.0, 125.0            # illustrative
PAD_TOP = 20.0                             # launch mount height (illustrative)
ARM_Z = 77.0                               # carriage height used for the catch (illustrative)
ARM_LEN, ARM_W, ARM_T = 20.0, 2.6, 4.0
HARD_Z = 55.0                              # catch hardpoints on the booster, local height (illustrative; hardware unverified)

M = {}


def materials():
    M["steel"] = material("steel", (0.62, 0.64, 0.68), metal=1.0, rough=0.32)
    M["dark"] = material("dark", (0.05, 0.05, 0.06), metal=0.6, rough=0.5)
    M["tower"] = material("tower", (0.72, 0.30, 0.10), metal=0.5, rough=0.55)
    M["arm"] = material("arm", (0.85, 0.55, 0.12), metal=0.6, rough=0.4)
    M["pad"] = material("pad", (0.16, 0.16, 0.17), metal=0.0, rough=0.9)
    M["ground"] = material("ground", (0.09, 0.09, 0.08), rough=1.0)
    M["flame"] = material("flame", (1, 0.6, 0.2), emit=(1.0, 0.55, 0.15), emit_strength=18.0)
    M["pin"] = material("pin", (0.9, 0.9, 0.95), metal=1.0, rough=0.25)


def build_booster(root_name="booster"):
    root = empty(root_name)
    cyl("b_body", BOOSTER_R, BOOSTER_H, (0, 0, BOOSTER_H / 2), M["steel"], verts=48, parent=root)
    cyl("b_hotring", BOOSTER_R * 1.01, 3.0, (0, 0, BOOSTER_H - 1.5), M["dark"], verts=48, parent=root)
    for k in range(4):                                          # 4 grid fins, near the top
        a = k * math.pi / 2 + math.pi / 4
        box(f"fin{k}", (0.4, 3.2, 3.2), ((BOOSTER_R + 1.2) * math.cos(a), (BOOSTER_R + 1.2) * math.sin(a), BOOSTER_H - 7),
            M["dark"], parent=root).rotation_euler = (0, 0, a)
    for sgn in (-1, 1):                                         # catch hardpoints (illustrative)
        cyl(f"pin{sgn}", 0.6, 1.8, (0, sgn * (BOOSTER_R + 0.9), HARD_Z), M["pin"], rot=(math.pi / 2, 0, 0), verts=16, parent=root)
    flames = []
    layout = [(3, 0.8), (10, 2.0), (20, 3.5)]                 # 3 + 10 + 20 = 33 engines (rings: count, radius)
    for count, rad in layout:
        for k in range(count):
            a = 2 * math.pi * k / count + (0.15 if count == 10 else 0.0)
            x, y = rad * math.cos(a), rad * math.sin(a)
            cone("bell", 0.5, 0.2, 1.0, (x, y, -0.5), M["dark"], verts=12, parent=root)
            flames.append(cone("flame", 0.38, 0.02, 1.0, (x, y, -1.4), M["flame"], rot=(math.pi, 0, 0), verts=10, parent=root))
    return root, flames


def build_ship(root):
    s = cyl("ship_body", BOOSTER_R, SHIP_H - 9, (0, 0, BOOSTER_H + (SHIP_H - 9) / 2), M["steel"], verts=48, parent=root)
    cone("ship_nose", BOOSTER_R, 0.3, 9, (0, 0, BOOSTER_H + SHIP_H - 4.5), M["steel"], verts=48, parent=root)
    return s


def build_tower():
    root = empty("tower", (TOWER_X, 0, 0))
    for sx in (-3, 3):
        for sy in (-3, 3):
            box("leg", (0.8, 0.8, TOWER_H), (sx, sy, TOWER_H / 2), M["tower"], parent=root)
    for z in range(10, int(TOWER_H), 10):
        for s in (-3, 3):
            box("ring_x", (6.8, 0.4, 0.4), (0, s, z), M["tower"], parent=root)
            box("ring_y", (0.4, 6.8, 0.4), (s, 0, z), M["tower"], parent=root)
    carriage = empty("carriage", (0, 0, ARM_Z), parent=root)
    arms = []
    for sgn in (-1, 1):                                         # two arms, each pivots about a vertical axis at the tower
        pivot = empty(f"pivot{sgn}", (4.0, sgn * 6.0, 0), parent=carriage)
        box(f"arm{sgn}", (ARM_LEN, ARM_W, ARM_T), (ARM_LEN / 2, 0, 0), M["arm"], parent=pivot)
        arms.append((sgn, pivot))
    return root, carriage, arms


def build_pad():
    box("ground", (900, 900, 1), (0, 0, -0.5), M["ground"])
    cyl("mount_table", 9.0, PAD_TOP, (0, 0, PAD_TOP / 2), M["pad"], verts=40)
    for k in range(6):                                          # simple legs
        a = k * math.pi / 3
        box("mount_leg", (1.2, 1.2, PAD_TOP), (7 * math.cos(a), 7 * math.sin(a), PAD_TOP / 2), M["dark"])


def lights():
    sun_light("key", (math.radians(55), 0, math.radians(30)), energy=3.2, color=(1.0, 0.9, 0.78))
    area_light("rim", (-30, 40, 60), (math.radians(60), 0, math.radians(200)), 40, 200000, (0.5, 0.65, 1.0))


class State:
    arm_angle = 80.0          # degrees: 80 = wide open, 0 = closed, arms point +x toward the booster


def set_arms(arms, deg):
    for sgn, pivot in arms:
        pivot.rotation_euler = (0, 0, math.radians(-sgn * deg))      # open: arms swing outward


def place_booster(root, flames, base_z, flame_k, tilt_deg=0.0, flicker=0.0):
    root.location = (0, 0, base_z)
    root.rotation_euler = (math.radians(tilt_deg), 0, 0)
    for i, f in enumerate(flames):
        k = flame_k * (1 + 0.12 * math.sin(flicker * 25 + i))
        f.scale = (1, 1, max(0.001, k * 6.0))
        f.hide_render = flame_k <= 0.01


def main():
    opts = parse_args()
    sc = setup_scene(opts, sky=(0.03, 0.05, 0.1), sky_strength=0.8)
    materials()
    build_pad()
    tower, carriage, arms = build_tower()
    lights()
    rig = Rig(lens=35)
    name = opts["scene"]
    root, flames = build_booster()
    hold_z = ARM_Z + 2.0 + 0.6 + 0.0 - HARD_Z                   # pins rest on the arms' top faces
    mid = (0, 0, 45)

    if name == "intro":
        build_ship(root)
        place_booster(root, flames, PAD_TOP, 0.0)
        set_arms(arms, 80)
        seconds = 5.0

        def pose(t, u):
            rig.look(lerp3((60, -150, 25), (30, -90, 40), smooth(u)), (-4, 0, 55 + 15 * u), lerp(30, 40, u))
    elif name == "mechazilla":
        build_ship(root)
        place_booster(root, flames, PAD_TOP, 0.0)
        seconds = 7.0

        def pose(t, u):
            set_arms(arms, lerp(80, 5, seg(u, 0.25, 0.75)))
            a = math.radians(lerp(-60, -15, smooth(u)))
            rig.look((-13 + 55 * math.cos(a + math.pi / 2) * -1, -55 * math.cos(a) - 10, 62), (-8, 0, ARM_Z), 40)
    elif name == "return":
        seconds = 10.0
        set_arms(arms, 80)

        def pose(t, u):
            z = lerp(900, hold_z + 60, seg(u, 0.0, 1.0) ** 0.8)
            place_booster(root, flames, z, 0.5 if u > 0.15 else 0.0, tilt_deg=lerp(90, 0, seg(u, 0.0, 0.35)), flicker=t)
            rig.look((70, -120, z * 0.55 + 30), (0, 0, z + 30), 35)
    elif name == "catch":
        seconds = 13.0

        def pose(t, u):
            # slow motion near the end: the descent eases out, arms close, engines cut
            z = lerp(hold_z + 55, hold_z, seg(u, 0.0, 0.62))
            engines = 0.5 * (1 - seg(u, 0.58, 0.68))
            set_arms(arms, lerp(80, 0, seg(u, 0.40, 0.62)))
            place_booster(root, flames, z, engines, flicker=t)
            if u < 0.62:
                rig.look(lerp3((55, -75, 95), (40, -55, 85), u / 0.62), (0, 0, z + 20), 35)
            else:                                              # close-up on the arms and hardpoint
                v = seg(u, 0.62, 1.0)
                rig.look(lerp3((22, -26, ARM_Z + 10), (16, -18, ARM_Z + 4), v), (0, -5.5, ARM_Z + 2), 50)
    elif name == "engineering":
        seconds = 12.0
        place_booster(root, flames, hold_z, 0.0)
        set_arms(arms, 0)

        def pose(t, u):
            a = lerp(-0.9, 0.9, smooth(u))
            rig.look((50 * math.sin(a), -80 * math.cos(a), 70), (-4, 0, 62), 38)
    elif name == "ending":
        seconds = 8.0
        place_booster(root, flames, hold_z, 0.0)
        set_arms(arms, 0)

        def pose(t, u):
            rig.look(lerp3((45, -80, 60), (140, -260, 120), smooth(u)), (-4, 0, 60), 30)
    else:
        raise SystemExit("unknown scene " + name)

    render_sequence(opts, pose, seconds)


if __name__ == "__main__":
    main()
