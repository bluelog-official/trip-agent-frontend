"""QA 칼럼과 유사도 테이블 마이그레이션. 기존 행과 다른 테이블은 유지한다."""

import sqlite3

from app.models.guides import apply_migration, connect, migrate_file


def _columns(conn, table):
    return {
        row[1]: {"type": row[2], "notnull": row[3], "default": row[4]}
        for row in conn.execute("PRAGMA table_info({0})".format(table))
    }


def test_existing_rows_keep_values_and_gain_defaults(tmp_path):
    path = tmp_path / "guides.db"
    raw = sqlite3.connect(str(path))
    raw.execute(
        "CREATE TABLE guides (id INTEGER PRIMARY KEY, city TEXT NOT NULL, slug TEXT NOT NULL)"
    )
    raw.execute("INSERT INTO guides (city, slug) VALUES ('Seoul', 'seoul_guide.md')")
    raw.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)")
    raw.execute("INSERT INTO notes (body) VALUES ('keep me')")
    raw.commit()
    raw.close()

    summary = migrate_file(path)
    assert summary["guides_created"] is False
    assert summary["columns_added"] == ["qa_score", "rating_grade", "star_rating", "qa_reason"]
    assert summary["similarities_created"] is True
    assert summary["rows_before"] == 1
    assert summary["rows_after"] == 1

    conn = connect(path)
    row = conn.execute(
        "SELECT id, city, slug, qa_score, rating_grade, star_rating, qa_reason FROM guides"
    ).fetchone()
    assert row["city"] == "Seoul"
    assert row["slug"] == "seoul_guide.md"
    assert row["qa_score"] == 75
    assert row["rating_grade"] == "B-"
    assert float(row["star_rating"]) == 3.0
    assert row["qa_reason"] is None
    note = conn.execute("SELECT body FROM notes").fetchone()
    assert note["body"] == "keep me"

    columns = _columns(conn, "guides")
    assert columns["qa_score"]["type"] == "INTEGER"
    assert columns["rating_grade"]["type"] == "VARCHAR(10)"
    assert columns["star_rating"]["type"] == "NUMERIC(3, 2)"
    assert columns["qa_reason"]["type"] == "TEXT"
    assert columns["qa_reason"]["notnull"] == 0

    links = _columns(conn, "guide_similarities")
    assert list(links) == [
        "id",
        "source_guide_id",
        "target_guide_id",
        "similarity_score",
        "created_at",
    ]
    assert links["similarity_score"]["type"] == "FLOAT"
    assert links["created_at"]["type"] == "TIMESTAMP"
    conn.close()


def test_existing_qa_score_is_not_rewritten_and_rerun_is_safe(tmp_path):
    path = tmp_path / "guides.db"
    raw = sqlite3.connect(str(path))
    raw.execute("CREATE TABLE guides (id INTEGER PRIMARY KEY, city TEXT, qa_score INTEGER)")
    raw.execute("INSERT INTO guides (city, qa_score) VALUES ('Busan', 91)")
    raw.commit()
    raw.close()

    first = migrate_file(path)
    assert "qa_score" not in first["columns_added"]
    assert first["rows_before"] == first["rows_after"] == 1

    second = migrate_file(path)
    assert second["columns_added"] == []
    assert second["guides_created"] is False
    assert second["similarities_created"] is False
    assert second["rows_before"] == second["rows_after"] == 1

    conn = connect(path)
    row = conn.execute(
        "SELECT city, qa_score, rating_grade, star_rating, qa_reason FROM guides"
    ).fetchone()
    assert row["city"] == "Busan"
    assert row["qa_score"] == 91
    assert row["rating_grade"] == "B-"
    assert float(row["star_rating"]) == 3.0
    assert row["qa_reason"] is None
    conn.close()


def test_fresh_database_accepts_a_similarity_link(tmp_path):
    path = tmp_path / "guides.db"
    summary = migrate_file(path)
    assert summary["guides_created"] is True
    assert summary["rows_before"] == summary["rows_after"] == 0

    conn = connect(path)
    conn.execute("INSERT INTO guides (qa_reason) VALUES ('thin local detail')")
    conn.execute("INSERT INTO guides DEFAULT VALUES")
    conn.execute(
        """
        INSERT INTO guide_similarities (source_guide_id, target_guide_id, similarity_score)
        VALUES (1, 2, 0.968)
        """
    )
    link = conn.execute(
        "SELECT similarity_score, created_at FROM guide_similarities WHERE id = 1"
    ).fetchone()
    assert abs(float(link["similarity_score"]) - 0.968) < 0.0001
    assert link["created_at"]

    try:
        conn.execute(
            """
            INSERT INTO guide_similarities (source_guide_id, target_guide_id, similarity_score)
            VALUES (1, 99, 0.99)
            """
        )
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised is True
    conn.close()


def test_migration_refuses_a_guides_table_without_id(tmp_path):
    path = tmp_path / "guides.db"
    conn = connect(path)
    conn.execute("CREATE TABLE guides (city TEXT)")
    try:
        apply_migration(conn)
        refused = False
    except RuntimeError as exc:
        refused = "no id column" in str(exc)
    assert refused is True
    assert conn.execute("SELECT city FROM guides").fetchone() is None
    conn.close()
