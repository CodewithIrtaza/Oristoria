"""Isolate the fixture stall: no HTTP, no app, only the DB fixture."""


def test_fixture_only(db_available: str):
    assert db_available
