"""Print the path of the next episode with status 'approved' that has not been uploaded yet."""
import json
import sys
from .common import ROOT, load_yaml

done = set(json.loads((ROOT / "state" / "done.json").read_text())) if (ROOT / "state" / "done.json").exists() else set()
for p in sorted((ROOT / "episodes").glob("*.yml")):
    ep = load_yaml(p)
    if ep.get("status") == "approved" and ep["id"] not in done:
        print(p.relative_to(ROOT))
        sys.exit(0)
print("")  # nothing to do
