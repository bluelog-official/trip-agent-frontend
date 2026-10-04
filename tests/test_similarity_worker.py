"""95% 이상인 가이드 쌍만 남긴다. 게시 칼럼은 점수 갱신 대상이 아니다."""

import sqlite3

from app.models.guides import connect, migrate_file
from app.services.guide_qa_worker import GuideText, populate_connection
from app.services.similarity_worker import cosine_similarity, pairwise_similarity


_SHARED = " ".join("market{0} temple river palace".format(index) for index in range(40))


def test_identical_text_is_one_and_unrelated_text_is_dropped():
    pairs = pairwise_similarity(
        (
            ("b.md", _SHARED),
            ("a.md", _SHARED),
            ("c.md", "ocean harbor lighthouse ferry"),
        )
    )
    assert len(pairs) == 1
    assert pairs[0].source_key == "a.md"
    assert pairs[0].target_key == "b.md"
    assert pairs[0].similarity_score == 1.0


def test_threshold_rejects_a_perfect_pair_when_set_above_one():
    assert pairwise_similarity((("a.md", _SHARED), ("b.md", _SHARED)), threshold=1.01) == []


def test_empty_vectors_have_zero_cosine():
    assert cosine_similarity({}, {"market": 1.0}) == 0.0


def test_low_score_does_not_change_publication_columns(tmp_path):
    path = tmp_path / "guides.db"
    migrate_file(path)
    raw = sqlite3.connect(str(path))
    raw.execute("ALTER TABLE guides ADD COLUMN slug TEXT")
    raw.execute("ALTER TABLE guides ADD COLUMN status TEXT NOT NULL DEFAULT 'APPROVED'")
    raw.execute("ALTER TABLE guides ADD COLUMN visibility TEXT NOT NULL DEFAULT 'public'")
    raw.execute("ALTER TABLE guides ADD COLUMN redirect_url TEXT")
    raw.execute(
        """
        INSERT INTO guides (slug, status, visibility, redirect_url, qa_score)
        VALUES ('thin_guide.md', 'APPROVED', 'public', NULL, 75)
        """
    )
    raw.commit()
    raw.close()

    thin = GuideText(slug="thin_guide.md", city="Thin", markdown="짧은 메모.")
    copy = GuideText(slug="copy_guide.md", city="Thin", markdown="짧은 메모.")
    distinct = GuideText(
        slug="other_guide.md",
        city="Other",
        markdown="harbor lighthouse ferry ocean cliff",
    )
    conn = connect(path)
    summary = populate_connection(conn, (thin, copy, distinct))
    row = conn.execute(
        "SELECT status, visibility, redirect_url, qa_score, rating_grade, star_rating FROM guides WHERE slug = ?",
        ("thin_guide.md",),
    ).fetchone()
    assert row["status"] == "APPROVED"
    assert row["visibility"] == "public"
    assert row["redirect_url"] is None
    assert row["rating_grade"] == "REISSUE"
    assert float(row["star_rating"]) == 0.0
    assert int(row["qa_score"]) < 60
    links = conn.execute(
        "SELECT source_guide_id, target_guide_id, similarity_score FROM guide_similarities"
    ).fetchall()
    assert summary["similarities"] == 1
    assert len(links) == 1
    assert float(links[0]["similarity_score"]) >= 0.95

    again = populate_connection(conn, (thin, copy, distinct))
    assert again["guides"] == 3
    assert again["similarities"] == 1
    assert conn.execute("SELECT COUNT(*) AS n FROM guides").fetchone()["n"] == 3
    assert conn.execute("SELECT COUNT(*) AS n FROM guide_similarities").fetchone()["n"] == 1
    kept = conn.execute("SELECT status, visibility FROM guides WHERE slug = 'thin_guide.md'").fetchone()
    assert kept["status"] == "APPROVED"
    assert kept["visibility"] == "public"
    conn.close()
