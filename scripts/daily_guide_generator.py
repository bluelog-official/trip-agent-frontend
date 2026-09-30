#!/usr/bin/env python3
"""Write one English travel guide into /guides.

The article is saved as Markdown with YAML frontmatter so the site and
sitemap pick it up on the next request. No backend process has to restart.

Examples
--------
    python scripts/daily_guide_generator.py
    python scripts/daily_guide_generator.py --city "Rome"

Dependencies
------------
Install the project requirements (requests and python-dotenv are required):

    pip install -r requirements.txt

Environment
-----------
Loaded from the project ``.env`` when the variables are not already set.

    GEMINI_API_KEY or GOOGLE_API_KEY   Gemini generateContent
    OPENROUTER_API_KEY                  used when Gemini is unavailable
    PEXELS_API_KEY                      hero photograph
    SITE_URL                            optional public site origin

The default review status written into frontmatter is ``Verified Travel Guide``.
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.content_variation import (  # noqa: E402
    apply_variation,
    build_daily_article_prompt,
    choose_variation,
    load_reserved,
)

GUIDES_DIR = ROOT_DIR / "guides"
DEFAULT_STATUS = "Verified Travel Guide"

GEMINI_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
)
OPENROUTER_MODELS = (
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-small-3.2-24b-instruct",
)

CITY_POOL = (
    "Lisbon",
    "Prague",
    "Vienna",
    "Amsterdam",
    "Berlin",
    "Florence",
    "Madrid",
    "Athens",
    "Istanbul",
    "Dubrovnik",
    "Hanoi",
    "Chiang Mai",
    "Hong Kong",
    "Busan",
    "Vancouver",
    "San Francisco",
    "Mexico City",
    "Buenos Aires",
    "Reykjavik",
    "Edinburgh",
    "Porto",
    "Queenstown",
    "Cape Town",
    "Marrakech",
)

_FENCE = re.compile(r"^```(?:markdown|md)?\s*|\s*```$", re.IGNORECASE)
_SCRIPT = re.compile(r"<script\b[^>]*/>|<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_FRONTMATTER = re.compile(r"^---\r?\n[\s\S]*?\r?\n---\r?\n?")


def slugify(city: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", city.strip().lower())
    return cleaned.strip("_") or "city"


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return '"{0}"'.format(escaped)


def choose_city(explicit: str) -> str:
    if explicit.strip():
        return explicit.strip()
    for city in CITY_POOL:
        if not (GUIDES_DIR / "{0}_guide.md".format(slugify(city))).is_file():
            return city
    index = date.today().toordinal() % len(CITY_POOL)
    return CITY_POOL[index]


def output_path(city: str) -> Path:
    slug = slugify(city)
    canonical = GUIDES_DIR / "{0}_guide.md".format(slug)
    if not canonical.exists():
        return canonical
    stamped = GUIDES_DIR / "{0}_{1}_guide.md".format(slug, date.today().strftime("%Y%m%d"))
    return stamped


def fetch_hero_image(city: str) -> dict:
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    fallback = {
        "url": "https://images.pexels.com/photos/346885/pexels-photo-346885.jpeg?auto=compress&cs=tinysrgb&w=1600",
        "alt": "{0} travel".format(city),
        "photographer": "Pexels",
        "photographer_url": "https://www.pexels.com",
    }
    if not api_key:
        return fallback
    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": "{0} city travel".format(city), "per_page": 1, "orientation": "landscape"},
            timeout=20,
        )
        response.raise_for_status()
        photos = response.json().get("photos") or []
    except (requests.RequestException, ValueError) as exc:
        print("Pexels image lookup failed: {0}".format(exc), file=sys.stderr)
        return fallback
    if not photos:
        return fallback
    photo = photos[0]
    src = (photo.get("src") or {})
    url = src.get("large2x") or src.get("large") or src.get("original") or fallback["url"]
    return {
        "url": url,
        "alt": (photo.get("alt") or "{0} travel".format(city)).strip(),
        "photographer": (photo.get("photographer") or "Pexels").strip(),
        "photographer_url": (photo.get("photographer_url") or "https://www.pexels.com").strip(),
    }


def _article_prompt(city: str, variation) -> str:
    return build_daily_article_prompt(city, variation)


def _gemini_text(city: str, api_key: str, variation) -> str:
    last_error = "Gemini request failed"
    for model in GEMINI_MODELS:
        try:
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/{0}:generateContent".format(model),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"role": "user", "parts": [{"text": _article_prompt(city, variation)}]}],
                    "generationConfig": {"temperature": 0.7},
                },
                timeout=90,
            )
            response.raise_for_status()
            payload = response.json()
            parts = payload["candidates"][0]["content"]["parts"]
            text = "\n".join(part.get("text", "") for part in parts).strip()
            if text:
                return text
        except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
            last_error = "{0}: {1}".format(model, exc)
            print("Gemini skipped ({0})".format(last_error), file=sys.stderr)
    raise RuntimeError(last_error)


def _openrouter_text(city: str, api_key: str, variation) -> str:
    last_error = "OpenRouter request failed"
    for model in OPENROUTER_MODELS:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": "Bearer {0}".format(api_key),
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0.7,
                    "messages": [
                        {"role": "system", "content": "You write original English city guides."},
                        {"role": "user", "content": _article_prompt(city, variation)},
                    ],
                },
                timeout=90,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"].strip()
            if text:
                return text
        except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
            last_error = "{0}: {1}".format(model, exc)
            print("OpenRouter skipped ({0})".format(last_error), file=sys.stderr)
    raise RuntimeError(last_error)


def generate_article(city: str, variation) -> str:
    gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    errors = []
    if gemini_key:
        try:
            return _gemini_text(city, gemini_key, variation)
        except RuntimeError as exc:
            errors.append(str(exc))
    if openrouter_key:
        try:
            return _openrouter_text(city, openrouter_key, variation)
        except RuntimeError as exc:
            errors.append(str(exc))
    if not gemini_key and not openrouter_key:
        raise RuntimeError("Set GEMINI_API_KEY or OPENROUTER_API_KEY in .env before generating a guide.")
    raise RuntimeError("Guide generation failed: {0}".format("; ".join(errors)))


def clean_article(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").strip()
    cleaned = _FENCE.sub("", cleaned).strip()
    cleaned = _FRONTMATTER.sub("", cleaned).strip()
    cleaned = _SCRIPT.sub("", cleaned).strip()
    if "| Category | Recommended Location | Estimated Cost | Rating |" not in cleaned:
        raise RuntimeError("The model omitted the required restaurant table.")
    if "## " not in cleaned:
        raise RuntimeError("The model omitted H2 sections.")
    return cleaned + "\n"


def build_document(city: str, article: str, image: dict, variation) -> str:
    hero = "![{0}]({1})\n*Photo by [{2}]({3})*\n\n".format(
        image["alt"].replace("[", "").replace("]", ""),
        image["url"],
        image["photographer"],
        image["photographer_url"],
    )
    body = article
    head = "\n".join(body.splitlines()[:8])
    if "![" not in head:
        lines = body.splitlines()
        insert_at = 1 if lines and lines[0].startswith("# ") else 0
        if insert_at and len(lines) > 1 and lines[1].strip():
            lines.insert(1, "")
            insert_at = 2
        lines.insert(insert_at, hero.rstrip("\n"))
        body = "\n".join(lines).strip() + "\n"
    frontmatter = "\n".join(
        [
            "---",
            "title: {0}".format(yaml_quote(variation.title)),
            "date: {0}".format(yaml_quote(date.today().isoformat())),
            "city: {0}".format(yaml_quote(city.strip())),
            "status: {0}".format(yaml_quote(DEFAULT_STATUS)),
            "image_url: {0}".format(yaml_quote(image["url"])),
            "---",
            "",
        ]
    )
    return frontmatter + body


def main(argv=None) -> int:
    load_dotenv(ROOT_DIR / ".env")
    parser = argparse.ArgumentParser(
        description="Generate one English city guide and save it under /guides.",
        epilog=(
            "Examples: python scripts/daily_guide_generator.py\n"
            '         python scripts/daily_guide_generator.py --city "Rome"\n'
            "Install dependencies with: pip install -r requirements.txt"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--city", default="", help='City name, for example "Rome". Omit to pick the next unpublished city.')
    args = parser.parse_args(argv)

    city = choose_city(args.city)
    variation = choose_variation(
        city,
        load_reserved(GUIDES_DIR),
        salt=date.today().toordinal(),
        structural=True,
        language="en",
    )
    image = fetch_hero_image(city)
    article = clean_article(generate_article(city, variation))
    document = apply_variation(build_document(city, article, image, variation), variation)
    GUIDES_DIR.mkdir(parents=True, exist_ok=True)
    path = output_path(city)
    path.write_text(document, encoding="utf-8")
    print("Saved {0}".format(path.relative_to(ROOT_DIR)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
