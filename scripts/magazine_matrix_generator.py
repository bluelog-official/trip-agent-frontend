#!/usr/bin/env python3
"""Write a duration x budget magazine into /guides.

The filename is ``{city}_{duration}_{budget}_guide.md``.

Examples
--------
    python scripts/magazine_matrix_generator.py --examples
    python scripts/magazine_matrix_generator.py --city Tokyo --duration 1_days --budget 50usd
    python scripts/magazine_matrix_generator.py --city Tokyo --duration "3 Days" --budget 200usd
    python scripts/magazine_matrix_generator.py --city Tokyo --duration "1 week" --budget budget

``--examples`` writes:

    guides/tokyo_1_days_50usd_guide.md
    guides/tokyo_3_days_200usd_guide.md
    guides/tokyo_1_week_budget_guide.md

The default path builds the article from the duration and budget curation table.
It does not call a model. ``--llm`` asks the research and writer agents to draft
the body, then stores the same frontmatter.
"""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.magazine_matrix import (  # noqa: E402
    EXAMPLE_MATRIX,
    attach_matrix_frontmatter,
    build_matrix_article_prompt,
    render_offline_guide,
    resolve_matrix,
)

GUIDES_DIR = ROOT_DIR / "guides"


def write_guide(city: str, duration: str, budget: str, directory: Path, use_llm: bool = False) -> Path:
    spec = resolve_matrix(city, duration, budget)
    if spec is None:
        raise ValueError("duration and budget are required")
    if use_llm:
        markdown = asyncio.run(_llm_article(spec))
    else:
        markdown = render_offline_guide(spec)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / spec.filename
    path.write_text(markdown, encoding="utf-8")
    return path


async def _llm_article(spec):
    from app.agents.research_agent import run_research_agent
    from app.agents.writer_agent import run_writer_agent

    research, _model = await run_research_agent(
        spec.city,
        "",
        None,
        spec.duration_key,
        spec.budget_key,
    )
    article, _writer = await run_writer_agent(
        spec.city,
        research,
        None,
        "en",
        spec.duration_key,
        spec.budget_key,
    )
    return attach_matrix_frontmatter(article, spec)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a duration x budget city magazine under /guides.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--city", default="", help='City name, for example "Tokyo".')
    parser.add_argument("--duration", default="", help="1_days, 3_days, or 1_week.")
    parser.add_argument("--budget", default="", help="50usd, 100usd, 200usd, budget, or luxury.")
    parser.add_argument("--examples", action="store_true", help="Write the three Tokyo sample magazines.")
    parser.add_argument("--llm", action="store_true", help="Draft the body with the research and writer agents.")
    parser.add_argument("--prompt-only", action="store_true", help="Print the curation prompt and do not write a file.")
    parser.add_argument("--output", default="", help="Directory for the markdown file. Defaults to /guides.")
    args = parser.parse_args(argv)

    directory = Path(args.output) if args.output else GUIDES_DIR
    jobs = list(EXAMPLE_MATRIX) if args.examples else [(args.city, args.duration, args.budget)]
    if not args.examples and (not args.city.strip() or not args.duration.strip() or not args.budget.strip()):
        parser.error("Pass --city, --duration, and --budget, or use --examples.")

    for city, duration, budget in jobs:
        spec = resolve_matrix(city, duration, budget)
        if args.prompt_only:
            print(build_matrix_article_prompt(spec))
            continue
        path = write_guide(city, duration, budget, directory, use_llm=args.llm)
        print("Saved {0}".format(path))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
