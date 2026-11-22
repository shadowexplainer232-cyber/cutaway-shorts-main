"""Offline tests for the studio tools (no network, no Blender/FreeCAD/Kdenlive needed).  python -m unittest tests.test_studio"""
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from studio import polyhaven, subtitles, qwen, cad, paths
from studio.edit_project import build_mlt, vertical_profile
from src.common import load_brand

FILES_HDRI = {"hdri": {"1k": {"hdr": {"url": "https://x/a_1k.hdr", "size": 1000, "md5": "m1"}},
                       "4k": {"hdr": {"url": "https://x/a_4k.hdr", "size": 99999999, "md5": "m4"}}}}
FILES_TEX = {"Diffuse": {"1k": {"jpg": {"url": "https://x/d.jpg", "size": 10, "md5": "a"}}},
             "nor_gl": {"1k": {"jpg": {"url": "https://x/n.jpg", "size": 10, "md5": "b"}}},
             "Displacement": {"1k": {"png": {"url": "https://x/disp.png", "size": 10, "md5": "c"}}}}
FILES_MODEL = {"blend": {"1k": {"blend": {"url": "https://x/m.blend", "size": 5, "md5": "z",
                                          "include": {"textures/t.jpg": {"url": "https://x/t.jpg", "size": 7, "md5": "y"}}}}}}


class PolyHaven(unittest.TestCase):
    def test_hdri_small_resolution(self):
        p = polyhaven.plan_files("hdris", FILES_HDRI, {"hdri_resolution": "1k", "hdri_format": "hdr"})
        self.assertEqual(len(p), 1); self.assertIn("1k", p[0][0]); self.assertEqual(p[0][2], 1000)

    def test_hdri_falls_back_to_smaller(self):
        p = polyhaven.plan_files("hdris", FILES_HDRI, {"hdri_resolution": "2k"})
        self.assertIn("1k", p[0][0])

    def test_textures_only_wanted_maps(self):
        p = polyhaven.plan_files("textures", FILES_TEX, {"texture_maps": ["Diffuse", "nor_gl", "Rough"]})
        self.assertEqual(len(p), 2)

    def test_model_includes(self):
        p = polyhaven.plan_files("models", FILES_MODEL, {"model_format": "blend"})
        self.assertEqual([x[0] for x in p], ["m.blend", "textures/t.jpg"])

    def test_unknown_type(self):
        with self.assertRaises(ValueError):
            polyhaven.plan_files("sounds", {}, {})

    def test_manifest_and_credits(self):
        with tempfile.TemporaryDirectory() as d:
            old = polyhaven.root_dir
            polyhaven.root_dir = lambda: Path(d)
            try:
                polyhaven.save_manifest({"a": {"type": "hdris", "name": "A", "authors": ["Bob"], "url": "https://polyhaven.com/a/a",
                                               "license": polyhaven.LICENSE}})
                self.assertIn("polyhaven.com/a/a", (Path(d) / "CREDITS.md").read_text())
                self.assertEqual(json.loads((Path(d) / "manifest.json").read_text())["a"]["type"], "hdris")
            finally:
                polyhaven.root_dir = old


class Subs(unittest.TestCase):
    EP = {"id": "9", "slug": "t"}
    SC = [({"id": "a", "text": "one two three four five six", "pause_after": 0.5}, None, 3.5),
          ({"id": "b", "text": "seven eight", "pause_after": 1.0}, None, 2.0)]

    def test_timeline_and_srt(self):
        tl = subtitles.timeline(self.EP, self.SC, 0.3)
        self.assertAlmostEqual(tl["total_seconds"], 5.5)
        self.assertAlmostEqual(tl["scenes"][1]["start"], 3.5)
        srt = subtitles.to_srt(tl)
        self.assertEqual(srt.count("-->"), 3)
        self.assertIn("00:00:00,000 -->", srt)

    def test_chunks_stay_inside_speaking_time(self):
        tl = subtitles.timeline(self.EP, self.SC, 0.3)
        ch = subtitles.chunk_times(tl["scenes"][0])
        self.assertLessEqual(ch[-1][1], 3.0 + 1e-6)


class Mlt(unittest.TestCase):
    def test_mlt_is_valid_xml(self):
        tl = {"total_seconds": 4.0, "scenes": [{"id": "a", "duration": 2.0}, {"id": "b", "duration": 2.0}]}
        xml = build_mlt(tl, {"auto_build": "x.mp4", "voice": "v.wav", "music": "m.mp3"}, load_brand())
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "mlt")
        self.assertIsNotNone(root.find("tractor"))
        self.assertIn("width=1080", vertical_profile(load_brand()))


class Misc(unittest.TestCase):
    def test_qwen_forces_draft(self):
        d = qwen.force_draft(qwen.extract_yaml("```yaml\ntitles: [Hello World]\nscenes:\n - text: hi\n```"))
        self.assertEqual((d["status"], d["sources_status"]), ("draft", "UNVERIFIED"))
        self.assertEqual(d["scenes"][0]["id"], "s1")

    def test_qwen_rejects_garbage(self):
        with self.assertRaises(ValueError):
            qwen.extract_yaml("no yaml here")

    def test_cad_env_skips_none(self):
        e = cad.build_env({"A": "1"}, CAD_OUT="x", CAD_LIN=None)
        self.assertEqual(e["CAD_OUT"], "x"); self.assertNotIn("CAD_LIN", e)

    def test_templates_listed(self):
        self.assertIn("gear", cad.list_templates())
        self.assertNotIn("_common", cad.list_templates())

    def test_find_tool_missing(self):
        self.assertIsNone(paths.find_tool("kdenlive", {"paths": {}}) if not paths.shutil.which("kdenlive") else None)


class Render(unittest.TestCase):
    def test_plan_and_command(self):
        from studio import render_scenes as rs
        from src.common import load_yaml, ROOT
        ep = load_yaml(ROOT / "episodes" / "013-starship-booster-catch.yml")
        script, clips = rs.plan(ep)
        self.assertEqual(clips, ["intro", "mechazilla", "return", "catch", "engineering"])
        self.assertTrue((ROOT / script).exists())
        cmd = rs.command("blender", script, "catch", "out", {"preview_scale": 25, "final_scale": 100}, False, frames=3)
        self.assertIn("25", cmd); self.assertIn("--frames", cmd)
        self.assertIn("100", rs.command("blender", script, "catch", "out", {}, True))

    def test_w16_plan_and_kinematics(self):
        import math
        from studio import render_scenes as rs
        from src.common import load_yaml, ROOT
        script, clips = rs.plan(load_yaml(ROOT / "episodes" / "014-bugatti-w16-engine.yml"))
        self.assertEqual(clips, ["intro", "reveal", "layout", "turbos", "running", "ending"])
        self.assertTrue((ROOT / script).exists())
        cr, rod = 0.43, 1.45                       # connecting rod length must stay constant (same formula as w16.py)
        for th in (-52.5, -37.5, 37.5, 52.5):
            t = math.radians(th)
            for k in range(30):
                phi = k * 0.4
                a = phi - t
                s = cr * math.cos(a) + math.sqrt(rod ** 2 - (cr * math.sin(a)) ** 2)
                q = (math.sin(t) * s, math.cos(t) * s); p = (cr * math.sin(phi), cr * math.cos(phi))
                self.assertAlmostEqual(math.hypot(q[0] - p[0], q[1] - p[1]), rod, places=9)

    def test_frame_index_stretches_clip(self):
        from src.visuals_clip import frame_index
        m = {"frames": 11, "fps": 15}
        self.assertEqual([frame_index(m, p) for p in (0, 0.5, 1, 2)], [1, 6, 11, 11])

    def test_all_episodes_use_known_visuals(self):
        from src.common import load_yaml, ROOT
        from src.visuals import VISUALS
        for f in (ROOT / "episodes").glob("*.yml"):
            for sc in load_yaml(f)["scenes"]:
                self.assertIn(sc["visual"]["type"], VISUALS, f.name)


if __name__ == "__main__":
    unittest.main()
