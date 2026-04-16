from jarvis.core.datetime_info import DateTimeInfo


def test_now_iso_has_separator() -> None:
    assert "T" in DateTimeInfo().now_iso()
