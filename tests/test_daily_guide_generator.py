import pytest

from scripts import daily_guide_generator


def test_skip_on_error_keeps_scheduled_job_successful(monkeypatch, capsys):
    def fail(_city):
        raise RuntimeError("API timed out")

    monkeypatch.setattr(daily_guide_generator, "generate_and_save", fail)

    assert daily_guide_generator.main(["--skip-on-error"]) == 0
    assert "Daily guide skipped" in capsys.readouterr().err


def test_error_still_fails_without_skip_flag(monkeypatch):
    def fail(_city):
        raise OSError("guides path is unavailable")

    monkeypatch.setattr(daily_guide_generator, "generate_and_save", fail)

    with pytest.raises(OSError, match="guides path is unavailable"):
        daily_guide_generator.main([])
