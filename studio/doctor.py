"""Report which studio tools were found on this PC. Read-only: it never installs or changes anything.

  python -m studio.doctor
"""
import platform
import shutil
import sys

from .paths import find_tool

INFO = {
    "blender": "3D scenes and renders (required for 3D episodes)",
    "freecadcmd": "mechanical modelling, STEP/STL/OBJ export (optional)",
    "kdenlive": "final editing (optional; the pipeline also builds a finished MP4 by itself)",
    "melt": "command-line rough-cut renderer that ships with Kdenlive (optional)",
    "ffmpeg": "required for every video build",
}


def main():
    print(f"Python {sys.version.split()[0]} on {platform.system()}")
    missing = 0
    for key, why in INFO.items():
        p = find_tool(key)
        print(f"  {'FOUND  ' if p else 'MISSING'} {key:<11} {p or '-'}   ({why})")
        missing += 0 if p else 1
    for tool, why in (("piper", "Piper narration (optional here: the cloud workflow bundles it)"),
                      ("ollama", "local Qwen server (optional)")):
        p = shutil.which(tool)
        print(f"  {'FOUND  ' if p else 'MISSING'} {tool:<11} {p or '-'}   ({why})")
    print("\nNothing was installed. To install the free tools on Windows, read docs/TOOLS.md or run "
          "scripts\\setup_windows.ps1 (it asks before every install).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
