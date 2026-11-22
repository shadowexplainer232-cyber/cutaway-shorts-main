"""Find the external programs. Never installs anything; returns None when a program is not found."""
import glob
import os
import shutil
from pathlib import Path

from src.common import ROOT, load_yaml


def tools_config():
    p = ROOT / "config" / "tools.yml"
    return load_yaml(p) if p.exists() else {}


# program key -> (environment variable, PATH names, Windows default glob patterns)
_PROGRAMS = {
    "blender": ("BLENDER", ["blender"], [
        r"C:\Program Files\Blender Foundation\Blender *\blender.exe",
        r"C:\Program Files (x86)\Blender Foundation\Blender *\blender.exe"]),
    "freecadcmd": ("FREECADCMD", ["FreeCADCmd", "freecadcmd"], [
        r"C:\Program Files\FreeCAD *\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
        r"%LOCALAPPDATA%\Programs\FreeCAD *\bin\FreeCADCmd.exe"]),
    "kdenlive": ("KDENLIVE", ["kdenlive"], [
        r"C:\Program Files\kdenlive\bin\kdenlive.exe",
        r"C:\Program Files\Kdenlive\bin\kdenlive.exe"]),
    "melt": ("MELT", ["melt"], [
        r"C:\Program Files\kdenlive\bin\melt.exe",
        r"C:\Program Files\Kdenlive\bin\melt.exe"]),
    "ffmpeg": ("FFMPEG", ["ffmpeg"], []),
}


def find_tool(key, config=None):
    """Order: config/tools.yml path, environment variable, PATH, usual Windows folders."""
    env_var, names, patterns = _PROGRAMS[key]
    cfg = (config if config is not None else tools_config()).get("paths", {})
    for cand in (cfg.get(key), os.environ.get(env_var)):
        if cand and Path(cand).is_file():
            return str(cand)
    for n in names:
        found = shutil.which(n)
        if found:
            return found
    for pat in patterns:
        hits = sorted(glob.glob(os.path.expandvars(pat)))
        if hits:
            return hits[-1]                     # newest version sorts last
    return None
