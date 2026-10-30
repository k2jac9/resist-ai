"""Public UI launch must not expose paid provider operations anonymously."""
import pytest


def test_default_bind_is_loopback():
    from src.ui_security import launch_options
    opts = launch_options({})
    assert opts["server_name"] == "127.0.0.1"
    assert opts["share"] is False
    assert opts["show_error"] is False


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "example.com"])
def test_public_bind_requires_auth(host):
    from src.ui_security import launch_options
    with pytest.raises(ValueError, match="authentication"):
        launch_options({"RESISTAI_HOST": host})


def test_public_bind_uses_explicit_auth():
    from src.ui_security import launch_options
    opts = launch_options({"RESISTAI_HOST":"0.0.0.0", "RESISTAI_UI_USER":"judge", "RESISTAI_UI_PASSWORD":"a-long-test-password", "PORT":"7860"})
    assert opts["auth"] == ("judge", "a-long-test-password")
    assert opts["server_port"] == 7860
    assert opts["share"] is False


@pytest.mark.parametrize("env", [
    {"RESISTAI_UI_USER":"judge"},
    {"RESISTAI_UI_PASSWORD":"a-long-test-password"},
    {"RESISTAI_UI_USER":"judge", "RESISTAI_UI_PASSWORD":"short"},
    {"RESISTAI_HOST":"0.0.0.0", "RESISTAI_ALLOW_NO_AUTH":"true"},
])
def test_incomplete_or_weak_auth_is_not_silently_ignored(env):
    from src.ui_security import launch_options
    with pytest.raises(ValueError):
        launch_options(env)


@pytest.mark.parametrize("port", ["0", "65536", "nonsense", "-1"])
def test_invalid_port_is_rejected(port):
    from src.ui_security import launch_options
    with pytest.raises(ValueError):
        launch_options({"PORT":port})
