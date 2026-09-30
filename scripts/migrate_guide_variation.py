#!/usr/bin/env python3
"""Rewrite published guide markdown so titles, durations, and hashtags are not one template.

Safe to run again: a file that already has duration_key is left as it is.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.content_variation import (  # noqa: E402
    Reserved,
    audit_varied_guide,
    vary_markdown,
)

import re  # noqa: E402


def _city_name(path: Path, markdown: str) -> str:
    match = re.search(r'^city:\s*"?([^"\n]+)"?', markdown, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return path.name.replace("_guide.md", "").replace("_", " ")


def guide_paths(root: Path):
    paths = []
    guides = root / "guides"
    if guides.is_dir():
        paths.extend(sorted(guides.glob("*.md")))
    output = root / "output"
    if output.is_dir():
        paths.extend(sorted(output.glob("*_guide.md")))
    return paths


def main() -> int:
    reserved = Reserved()
    failures = []
    rows = []
    for index, path in enumerate(guide_paths(ROOT)):
        original = path.read_text(encoding="utf-8")
        city = _city_name(path, original)
        updated, variation = vary_markdown(original, city, reserved, salt=index)
        issues = audit_varied_guide(updated)
        if issues:
            failures.append("{0}: {1}".format(path.name, ", ".join(issues)))
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            state = "updated"
        else:
            state = "unchanged"
        rows.append((state, path.relative_to(ROOT), variation.duration_key, variation.template_id, variation.title, " ".join(variation.hashtags)))

    titles = [row[4] for row in rows]
    forms = [row[3] for row in rows]
    tags = [row[5] for row in rows]
    if len(titles) != len(set(titles)):
        failures.append("duplicate titles")
    if len(forms) != len(set(forms)):
        failures.append("duplicate title formats")
    if len(tags) != len(set(tags)):
        failures.append("duplicate hashtag sets")
    local_food = sum(1 for tag in tags if "#LocalFood" in tag.split())
    if rows and local_food == len(rows):
        failures.append("LocalFood on every guide")

    for state, rel, duration_key, form, title, tag_line in rows:
        print("{0}\t{1}\t{2}\t{3}\t{4}".format(state, rel, duration_key, form, title))
        print("  {0}".format(tag_line))

    if failures:
        print("Migration audit failed:", file=sys.stderr)
        for item in failures:
            print("- {0}".format(item), file=sys.stderr)
        return 1
    print("Varied {0} guides. LocalFood on {1}.".format(len(rows), local_food))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
