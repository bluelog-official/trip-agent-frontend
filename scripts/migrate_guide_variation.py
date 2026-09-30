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
    fresh_title,
    retitle_markdown,
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


def _already_varied(markdown: str) -> bool:
    return bool(re.search(r"^duration_key:\s*", markdown, re.MULTILINE))


def _release(reserved: Reserved, template_id: str, title: str) -> None:
    count = reserved.template_count(template_id)
    if count <= 1:
        reserved.templates.pop(template_id, None)
    else:
        reserved.templates[template_id] = count - 1
    reserved.titles.discard(title)


def _retitle_duplicates(rows, reserved: Reserved):
    """같은 제목 형식이 겹치면, 이번에 새로 고친 파일을 비어 있는 형식으로 옮긴다."""
    grouped = {}
    for row in rows:
        grouped.setdefault(row["form"], []).append(row)
    for form, group in grouped.items():
        if len(group) < 2:
            continue
        keeper = group[-1]
        for row in group:
            if row is keeper:
                continue
            _release(reserved, row["form"], row["title"])
            language = "ko" if row["form"].startswith("ko_") else "en"
            title, template_id = fresh_title(row["city"], row["duration_key"], language, row["salt"], reserved)
            text = row["path"].read_text(encoding="utf-8")
            updated = retitle_markdown(text, title, template_id)
            row["path"].write_text(updated, encoding="utf-8")
            row["state"] = "updated"
            row["form"] = template_id
            row["title"] = title
            reserved.templates[template_id] = reserved.template_count(template_id) + 1
            reserved.titles.add(title)


def main() -> int:
    reserved = Reserved()
    failures = []
    rows = []
    pending = []
    for index, path in enumerate(guide_paths(ROOT)):
        original = path.read_text(encoding="utf-8")
        city = _city_name(path, original)
        if _already_varied(original):
            updated, variation = vary_markdown(original, city, reserved, salt=index)
            rows.append(
                {
                    "state": "unchanged" if updated == original else "updated",
                    "path": path,
                    "rel": path.relative_to(ROOT),
                    "duration_key": variation.duration_key,
                    "form": variation.template_id,
                    "title": variation.title,
                    "tags": " ".join(variation.hashtags),
                    "city": city,
                    "salt": index,
                }
            )
            if updated != original:
                path.write_text(updated, encoding="utf-8")
        else:
            pending.append((index, path, original, city))

    for index, path, original, city in pending:
        updated, variation = vary_markdown(original, city, reserved, salt=index)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            state = "updated"
        else:
            state = "unchanged"
        rows.append(
            {
                "state": state,
                "path": path,
                "rel": path.relative_to(ROOT),
                "duration_key": variation.duration_key,
                "form": variation.template_id,
                "title": variation.title,
                "tags": " ".join(variation.hashtags),
                "city": city,
                "salt": index,
            }
        )

    _retitle_duplicates(rows, reserved)
    rows.sort(key=lambda row: str(row["rel"]))

    for row in rows:
        issues = audit_varied_guide(row["path"].read_text(encoding="utf-8"))
        if issues:
            failures.append("{0}: {1}".format(row["rel"].name, ", ".join(issues)))

    titles = [row["title"] for row in rows]
    forms = [row["form"] for row in rows]
    tags = [row["tags"] for row in rows]
    if len(titles) != len(set(titles)):
        failures.append("duplicate titles")
    if len(forms) != len(set(forms)):
        failures.append("duplicate title formats")
    if len(tags) != len(set(tags)):
        failures.append("duplicate hashtag sets")
    local_food = sum(1 for tag in tags if "#LocalFood" in tag.split())
    if rows and local_food == len(rows):
        failures.append("LocalFood on every guide")

    for row in rows:
        print("{0}\t{1}\t{2}\t{3}\t{4}".format(row["state"], row["rel"], row["duration_key"], row["form"], row["title"]))
        print("  {0}".format(row["tags"]))

    if failures:
        print("Migration audit failed:", file=sys.stderr)
        for item in failures:
            print("- {0}".format(item), file=sys.stderr)
        return 1
    print("Varied {0} guides. LocalFood on {1}.".format(len(rows), local_food))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
