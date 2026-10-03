#!/usr/bin/env python3
"""guides QA 칼럼과 guide_similarities 테이블을 기존 행을 유지한 채 적용한다.

다시 실행해도 이미 있는 칼럼과 행은 그대로 둔다.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.guides import db_path, migrate_file  # noqa: E402


def main() -> int:
    path = db_path()
    summary = migrate_file(path)
    print("database: {0}".format(path))
    print("guides_created: {0}".format(summary["guides_created"]))
    print("columns_added: {0}".format(", ".join(summary["columns_added"]) or "(none)"))
    print("similarities_created: {0}".format(summary["similarities_created"]))
    print("rows_before: {0}".format(summary["rows_before"]))
    print("rows_after: {0}".format(summary["rows_after"]))
    print("columns: {0}".format(", ".join(summary["columns"])))
    if summary["rows_before"] != summary["rows_after"]:
        print("row count changed; migration refused", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
