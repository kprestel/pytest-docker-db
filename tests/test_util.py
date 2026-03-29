from pytest_docker_db.util import is_pathname_valid


class TestIsPathnameValid:
    def test_valid_absolute_path(self):
        assert is_pathname_valid("/tmp/test") is True

    def test_valid_relative_path(self):
        assert is_pathname_valid("relative/path") is True

    def test_root_path(self):
        assert is_pathname_valid("/") is True

    def test_empty_string(self):
        assert is_pathname_valid("") is False

    def test_none_returns_false(self):
        assert is_pathname_valid(None) is False

    def test_non_string_returns_false(self):
        assert is_pathname_valid(123) is False

    def test_nul_character_returns_false(self):
        assert is_pathname_valid("/tmp/\x00test") is False

    def test_named_volume_style(self):
        assert is_pathname_valid("my-volume") is True

    def test_path_with_dots(self):
        assert is_pathname_valid("/tmp/../etc") is True
