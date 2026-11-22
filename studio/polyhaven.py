"""Poly Haven (CC0) downloader: small by default, keeps a manifest of every asset's URL and licence.

  python -m studio.polyhaven search "launch pad concrete" --type textures --limit 8
  python -m studio.polyhaven info concrete_floor_02
  python -m studio.polyhaven get kloppenheim_06_puresky --type hdris --res 1k
  python -m studio.polyhaven get concrete_floor_02 --type textures
  python -m studio.polyhaven list

Rules this tool follows (from Poly Haven's pages, read 2026-11-22):
  * All assets are CC0; credit is not required but appreciated. The live API asks that users are
    told the assets came from Poly Haven, so credits are written to assets/polyhaven/CREDITS.md.
  * Every API request carries a unique User-Agent (config/tools.yml: polyhaven.user_agent).
  * Web scraping is not allowed; only the documented API endpoints are used.
  * Files are checked against the size limit BEFORE downloading, then verified by MD5.
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from src.common import ROOT
from .paths import tools_config

API = "https://api.polyhaven.com"
SITE = "https://polyhaven.com/a/"
LICENSE = "CC0 1.0 (public domain dedication)"
LICENSE_URL = "https://polyhaven.com/license"
TYPES = ("hdris", "textures", "models")


def _cfg():
    return tools_config().get("polyhaven", {})


def api_get(path, params=None):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": _cfg().get("user_agent", "CutawayStudio/1.0")})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def download_file(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": _cfg().get("user_agent", "CutawayStudio/1.0")})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def root_dir():
    return ROOT / _cfg().get("dir", "assets/polyhaven")


# ---------------------------------------------------------------- choosing files from /files/{id}
def _pick_res(options, want):
    """options: dict of resolution -> ... ; prefer `want`, else the closest smaller, else the smallest."""
    if want in options:
        return want
    order = sorted(options, key=lambda r: int(r.rstrip("k")))
    smaller = [r for r in order if int(r.rstrip("k")) <= int(want.rstrip("k"))]
    return (smaller or order)[-1 if smaller else 0]


def _pick_fmt(options, want, fallbacks=()):
    for f in (want, *fallbacks):
        if f in options:
            return f
    return sorted(options)[0]


def plan_files(asset_type, files, cfg=None):
    """Return [(relative_path, url, size_bytes, md5)] for the files we want. Pure function (testable)."""
    cfg = cfg or _cfg()
    out = []
    if asset_type == "hdris":
        block = files["hdri"]
        res = _pick_res(block, cfg.get("hdri_resolution", "1k"))
        fmt = _pick_fmt(block[res], cfg.get("hdri_format", "hdr"), ("exr",))
        f = block[res][fmt]
        out.append((f"{res}_{Path(f['url']).name}", f["url"], f.get("size", 0), f.get("md5")))
    elif asset_type == "textures":
        want_res = cfg.get("texture_resolution", "1k")
        for map_name in cfg.get("texture_maps", ["Diffuse", "nor_gl", "Rough", "arm"]):
            if map_name not in files:
                continue
            res = _pick_res(files[map_name], want_res)
            fmt = _pick_fmt(files[map_name][res], cfg.get("texture_format", "jpg"), ("png", "exr"))
            f = files[map_name][res][fmt]
            out.append((f"{map_name}_{res}_{Path(f['url']).name}", f["url"], f.get("size", 0), f.get("md5")))
    elif asset_type == "models":
        kind = cfg.get("model_format", "blend")
        if kind not in files:
            kind = next(k for k in ("blend", "gltf", "fbx") if k in files)
        block = files[kind]
        res = _pick_res(block, cfg.get("model_resolution", "1k"))
        main_fmt = _pick_fmt(block[res], kind)
        f = block[res][main_fmt]
        out.append((Path(f["url"]).name, f["url"], f.get("size", 0), f.get("md5")))
        for rel, inc in (f.get("include") or {}).items():       # textures/bins the model refers to
            out.append((rel, inc["url"], inc.get("size", 0), inc.get("md5")))
    else:
        raise ValueError(f"unknown asset type {asset_type}")
    return out


# ---------------------------------------------------------------- manifest + credits
def manifest_path():
    return root_dir() / "manifest.json"


def load_manifest():
    p = manifest_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_manifest(m):
    root_dir().mkdir(parents=True, exist_ok=True)
    manifest_path().write_text(json.dumps(m, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# Poly Haven credits", "",
             "Assets below come from Poly Haven (https://polyhaven.com) and are CC0 (public domain). "
             "Credit is not required but is appreciated; add this line to a video description if you like:", "",
             "> 3D assets: Poly Haven (polyhaven.com), CC0", "",
             "| Asset | Type | Authors | URL | Licence |", "|---|---|---|---|---|"]
    for aid, e in sorted(m.items()):
        lines.append(f"| {e.get('name', aid)} | {e['type']} | {', '.join(e.get('authors', [])) or '-'} | "
                     f"{e['url']} | {e['license']} |")
    (root_dir() / "CREDITS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_asset(asset_id, asset_type, force=False, dry_run=False, log=print):
    cfg = _cfg()
    info = api_get(f"/info/{asset_id}")
    files = api_get(f"/files/{asset_id}")
    plan = plan_files(asset_type, files, cfg)
    total = sum(p[2] for p in plan)
    limit = float(cfg.get("max_download_mb", 60)) * 1024 * 1024
    log(f"{asset_id}: {len(plan)} file(s), {total / 1e6:.1f} MB (limit {limit / 1e6:.0f} MB)")
    if total > limit and not force:
        raise SystemExit(f"Refusing: {total / 1e6:.1f} MB is over max_download_mb. "
                         f"Pick a lower resolution in config/tools.yml or add --force.")
    if dry_run:
        for rel, url, size, _ in plan:
            log(f"  would download {rel} ({size / 1e6:.2f} MB) from {url}")
        return None
    dest = root_dir() / asset_type / asset_id
    got = []
    for rel, url, size, md5 in plan:
        target = dest / rel
        if target.exists() and (not md5 or md5_of(target) == md5):
            log(f"  have {rel}")
        else:
            log(f"  downloading {rel} ({size / 1e6:.2f} MB)")
            download_file(url, target)
            if md5 and md5_of(target) != md5:
                target.unlink()
                raise SystemExit(f"Checksum mismatch for {rel}; the file was removed. Try again.")
            time.sleep(0.3)                                       # be polite to the free service
        got.append({"path": str(target.relative_to(root_dir())).replace("\\", "/"),
                    "bytes": target.stat().st_size, "md5": md5 or md5_of(target), "source_url": url})
    m = load_manifest()
    m[asset_id] = {
        "type": asset_type, "name": info.get("name", asset_id), "url": SITE + asset_id,
        "api": f"{API}/files/{asset_id}", "license": LICENSE, "license_url": LICENSE_URL,
        "authors": sorted((info.get("authors") or {}).keys()), "tags": info.get("tags", []),
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": sum(g["bytes"] for g in got), "files": got}
    save_manifest(m)
    log(f"Saved to {dest}  (manifest + CREDITS.md updated)")
    return dest


def find_hdri():
    """First downloaded HDRI file (for blender/aero/*), or None."""
    for e in load_manifest().values():
        if e["type"] == "hdris" and e.get("files"):
            return root_dir() / e["files"][0]["path"]
    return None


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Poly Haven (CC0) downloader")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--type", choices=TYPES)
    s.add_argument("--limit", type=int, default=10)
    i = sub.add_parser("info"); i.add_argument("id")
    g = sub.add_parser("get"); g.add_argument("id"); g.add_argument("--type", choices=TYPES)
    g.add_argument("--force", action="store_true"); g.add_argument("--dry-run", action="store_true")
    sub.add_parser("list")
    a = ap.parse_args(argv)

    if a.cmd == "search":
        params = {"q": a.query, "limit": a.limit}
        if a.type:
            params["type"] = a.type
        res = api_get("/search", params)
        slugs = res if isinstance(res, list) else res.get("results", res.get("data", []))
        for slug in slugs[: a.limit]:
            slug = slug["id"] if isinstance(slug, dict) else slug
            print(slug, "-", SITE + slug)
    elif a.cmd == "info":
        d = api_get(f"/info/{a.id}")
        print(json.dumps({k: d.get(k) for k in ("name", "type", "authors", "categories", "tags", "max_resolution")}, indent=2))
    elif a.cmd == "get":
        t = a.type
        if not t:
            t = TYPES[int(api_get(f"/info/{a.id}").get("type", 0))]
        get_asset(a.id, t, force=a.force, dry_run=a.dry_run)
    elif a.cmd == "list":
        m = load_manifest()
        for aid, e in sorted(m.items()):
            print(f"{aid:<32} {e['type']:<9} {e['bytes'] / 1e6:6.1f} MB  {e['url']}")
        print(f"{len(m)} asset(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
