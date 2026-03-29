from unittest.mock import MagicMock

import pytest

from pytest_docker_db.plugin import (
    _DockerComposeOptions,
    _DockerDBOptions,
    _get_config_bool,
    _get_config_str,
)


def _make_request(ini_values=None, cli_values=None):
    """Create a mock pytest request with configurable ini and cli values."""
    ini = ini_values or {}
    cli = cli_values or {}
    request = MagicMock(spec=pytest.FixtureRequest)
    request.config.getini.side_effect = lambda key: ini.get(key, [])
    request.config.getoption.side_effect = lambda key: cli.get(key)
    return request


class TestGetConfigStr:
    def test_returns_none_when_no_value(self):
        request = _make_request()
        assert _get_config_str("db-image", request) is None

    def test_returns_cli_value(self):
        request = _make_request(cli_values={"--db-image": "postgres:latest"})
        assert _get_config_str("db-image", request) == "postgres:latest"

    def test_returns_ini_value(self):
        request = _make_request(ini_values={"db-image": ["postgres:15"]})
        assert _get_config_str("db-image", request) == "postgres:15"

    def test_ini_takes_precedence_for_non_empty(self):
        request = _make_request(
            ini_values={"db-image": ["postgres:15"]},
            cli_values={"--db-image": "mysql:8"},
        )
        assert _get_config_str("db-image", request) == "postgres:15"


class TestGetConfigBool:
    def test_returns_false_when_no_value(self):
        request = _make_request()
        assert _get_config_bool("db-persist-container", request) is False

    def test_returns_bool_from_ini(self):
        request = _make_request(ini_values={"db-persist-container": True})
        assert _get_config_bool("db-persist-container", request) is True

    def test_returns_bool_from_cli(self):
        request = _make_request(cli_values={"--db-persist-container": True})
        assert _get_config_bool("db-persist-container", request) is True


class TestDockerDBOptions:
    def test_validates_requires_image_or_dockerfile(self):
        request = _make_request()
        with pytest.raises(pytest.fail.Exception, match="Must specify an image"):
            _DockerDBOptions(request)

    def test_accepts_image(self):
        request = _make_request(cli_values={"--db-image": "postgres:latest"})
        opts = _DockerDBOptions(request)
        assert opts.db_image == "postgres:latest"

    def test_accepts_dockerfile(self):
        request = _make_request(cli_values={"--db-dockerfile": "Dockerfile"})
        opts = _DockerDBOptions(request)
        assert opts.docker_file == "Dockerfile"

    def test_db_name_cached(self):
        request = _make_request(cli_values={"--db-image": "postgres:latest"})
        opts = _DockerDBOptions(request)
        name1 = opts.db_name
        name2 = opts.db_name
        assert name1 == name2
        assert name1.startswith("docker-db-")

    def test_db_name_explicit(self):
        request = _make_request(
            cli_values={"--db-image": "postgres:latest", "--db-name": "mydb"}
        )
        opts = _DockerDBOptions(request)
        assert opts.db_name == "mydb"

    def test_host_port_cached(self):
        request = _make_request(cli_values={"--db-image": "postgres:latest"})
        opts = _DockerDBOptions(request)
        port1 = opts.host_port
        port2 = opts.host_port
        assert port1 == port2
        assert isinstance(port1, int)

    def test_volume_args_single(self):
        request = _make_request(
            cli_values={
                "--db-image": "postgres:latest",
                "--db-volume-args": "/host:/container:rw",
            }
        )
        opts = _DockerDBOptions(request)
        assert opts.volume_args == ["/host:/container:rw"]
        assert opts.host_mount_path == ["/host"]
        assert opts.container_mount_path == ["/container"]
        assert opts.volume_permissions == ["rw"]

    def test_volume_args_multiple(self):
        request = _make_request(
            cli_values={
                "--db-image": "postgres:latest",
                "--db-volume-args": "/a:/b:rw,/c:/d:ro",
            }
        )
        opts = _DockerDBOptions(request)
        assert opts.volume_args == ["/a:/b:rw", "/c:/d:ro"]
        assert opts.host_mount_path == ["/a", "/c"]

    def test_volume_args_none(self):
        request = _make_request(cli_values={"--db-image": "postgres:latest"})
        opts = _DockerDBOptions(request)
        assert opts.volume_args is None
        assert opts.host_mount_path is None

    def test_env_vars_parsing(self):
        request = _make_request(
            cli_values={
                "--db-image": "postgres:latest",
                "--db-docker-env-vars": "FOO=bar,BAZ=qux",
            }
        )
        opts = _DockerDBOptions(request)
        assert opts.env_vars == ["FOO=bar", "BAZ=qux"]

    def test_env_vars_none(self):
        request = _make_request(cli_values={"--db-image": "postgres:latest"})
        opts = _DockerDBOptions(request)
        assert opts.env_vars is None

    def test_context_defaults_to_cwd(self):
        request = _make_request(cli_values={"--db-image": "postgres:latest"})
        opts = _DockerDBOptions(request)
        assert opts.context is not None

    def test_persist_container_default(self):
        request = _make_request(cli_values={"--db-image": "postgres:latest"})
        opts = _DockerDBOptions(request)
        assert not opts.persist_container


class TestDockerComposeOptions:
    def test_validates_requires_compose_file(self):
        request = _make_request()
        with pytest.raises(
            pytest.fail.Exception, match="Must specify a Docker Compose file"
        ):
            _DockerComposeOptions(request)

    def test_validates_compose_file_exists(self, tmp_path):
        request = _make_request(
            cli_values={"--docker-compose-file": str(tmp_path / "nonexistent.yml")}
        )
        with pytest.raises(
            pytest.fail.Exception, match="Docker Compose file not found"
        ):
            _DockerComposeOptions(request)

    def test_accepts_valid_compose_file(self, tmp_path):
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("version: '3'\n")
        request = _make_request(cli_values={"--docker-compose-file": str(compose_file)})
        opts = _DockerComposeOptions(request)
        assert opts.compose_file == str(compose_file)

    def test_project_name_cached(self, tmp_path):
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("version: '3'\n")
        request = _make_request(cli_values={"--docker-compose-file": str(compose_file)})
        opts = _DockerComposeOptions(request)
        name1 = opts.project_name
        name2 = opts.project_name
        assert name1 == name2
        assert name1.startswith("pytest-docker-compose-")

    def test_services_parsing(self, tmp_path):
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("version: '3'\n")
        request = _make_request(
            cli_values={
                "--docker-compose-file": str(compose_file),
                "--docker-compose-services": "db, redis, cache",
            }
        )
        opts = _DockerComposeOptions(request)
        assert opts.services == ["db", "redis", "cache"]

    def test_services_none(self, tmp_path):
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("version: '3'\n")
        request = _make_request(cli_values={"--docker-compose-file": str(compose_file)})
        opts = _DockerComposeOptions(request)
        assert opts.services is None
