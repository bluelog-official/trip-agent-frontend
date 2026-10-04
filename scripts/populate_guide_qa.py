#!/usr/bin/env python3
"""현재 가이드 파일의 QA 점수와 95% 이상 유사 쌍을 output/guides.db에 기록한다.

게시 상태, 공개 여부, 리다이렉트는 변경하지 않는다. 다시 실행하면 점수와 유사 쌍만 갱신한다.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.guides import db_path  # noqa: E402
from app.services.guide_qa_worker import populate_from_files  # noqa: E402


def main() -> int:
    path = db_path()
    summary = populate_from_files(path)
    print("database: {0}".format(path))
    print("files: {0}".format(summary["files"]))
    print("guides: {0}".format(summary["guides"]))
    print("similarities: {0}".format(summary["similarities"]))
    if summary["guides"] <= 0:
        print("no guides scored", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
