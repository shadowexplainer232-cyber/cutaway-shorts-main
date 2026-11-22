"""Draft an episode script with a local Qwen model (Ollama). Output is ALWAYS a draft.

  python -m studio.qwen "How a Bugatti W16 engine works" --scenes 7 --out episodes/drafts
  python -m studio.qwen --prompt-only "Topic"        print the prompt (paste into any chat model)

Safety: the result is forced to status: draft and sources_status: UNVERIFIED, so the pipeline refuses to build
or upload it until you fact-check it and change both fields yourself. Files go to episodes/drafts/ (not picked
by the scheduler). Ollama must run on your PC; nothing is installed or sent anywhere else.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

from src.common import ROOT
from .paths import tools_config

VISUALS = "title_card, fact_card, boost_compare, gearbox, rocket_steer, concrete, regen, reactor, intercooler, cooling, fusion, render_clip"

PROMPT = """You write scripts for CUTAWAY, a YouTube Shorts channel (science, engineering, history explainers; 9:16; 40-55 seconds).
Topic: {topic}

Rules: one idea per scene; {n} scenes; about 110-140 words of narration in total; plain spoken English; every number
must be one you are sure is correct and publicly documented (otherwise leave it out); mark nothing as fact that is only
an illustration. End with a recap or lesson, a bonus fact, a question to the viewer, then the channel line.
Return ONLY YAML with keys: id, slug, titles (list of 3), description, hashtags, tags, pinned_comment, sources (list of
URLs you believe support the facts), scenes (list of: id, on_screen (max 4 words), text, visual {{type: one of {visuals}}}, pause_after).
"""


def build_prompt(topic, scenes=7):
    return PROMPT.format(topic=topic, n=scenes, visuals=VISUALS)


def extract_yaml(text):
    m = re.search(r"```(?:ya?ml)?\s*(.*?)```", text, re.S)
    data = yaml.safe_load(m.group(1) if m else text)
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list) or not data["scenes"]:
        raise ValueError("The model did not return a YAML mapping with a non-empty 'scenes' list.")
    return data


def force_draft(data, next_id="draft"):
    data["status"] = "draft"
    data["sources_status"] = "UNVERIFIED"
    data.setdefault("id", next_id)
    data["id"] = str(data["id"])
    data.setdefault("slug", re.sub(r"[^a-z0-9]+", "-", str(data.get("titles", ["episode"])[0]).lower()).strip("-")[:40])
    for i, s in enumerate(data["scenes"], 1):
        s.setdefault("id", f"s{i}")
        s.setdefault("on_screen", "")
        s.setdefault("pause_after", 0.3)
        s.setdefault("visual", {"type": "title_card"})
    return data


def ask(prompt):
    q = tools_config().get("qwen", {})
    body = json.dumps({"model": q.get("model", "qwen2.5:7b"), "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(q.get("endpoint", "http://localhost:11434/api/generate"), data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=int(q.get("timeout_sec", 600))) as r:
            return json.loads(r.read().decode())["response"]
    except OSError as e:
        raise SystemExit(f"Cannot reach Ollama ({e}). Start it (ollama serve) or use --prompt-only.")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--scenes", type=int, default=7)
    ap.add_argument("--out", default=str(ROOT / "episodes" / "drafts"))
    ap.add_argument("--prompt-only", action="store_true")
    a = ap.parse_args(argv)
    prompt = build_prompt(a.topic, a.scenes)
    if a.prompt_only:
        print(prompt)
        return 0
    data = force_draft(extract_yaml(ask(prompt)))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{data['id']}-{data['slug']}.yml"
    f.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print("Draft saved:", f, "\nIt is UNVERIFIED: fact-check every claim before changing the status.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
