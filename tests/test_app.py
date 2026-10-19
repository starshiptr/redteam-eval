from streamlit.testing.v1 import AppTest


def test_app_boots():
    at = AppTest.from_file("app.py").run(timeout=30)
    assert not at.exception 