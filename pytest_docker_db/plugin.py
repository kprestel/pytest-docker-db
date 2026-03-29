from __future__ import annotations

import os
import shutil
import socket
import subprocess
import uuid
from collections.abc import Generator
from typing import Any

import docker
import pytest
from docker import DockerClient
from docker.errors import APIError
from docker.models.containers import Container

import pytest_docker_db.util as utils


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup(
        "docker-db", "Arguments to configure the pytest-docker-db plugin."
    )

    db_vol_args_help = (
        'Provide the "-v" arguments that you would pass to the '
        '"docker run" command if you were using the cli. If you need '
        "multiple volumes mounted separate them with commas.\n"
        "The basic syntax is /host/vol/path:/path/in/container:rw. "
        "If using a named volume, the syntax would be "
        "vol-name:/path/in/container:rw "
    )
    group.addoption(
        "--db-volume-args", action="store", default=None, help=db_vol_args_help
    )
    parser.addini("db-volume-args", db_vol_args_help, type="args")

    db_image_help = (
        "Specify the name of the image to use as the DB. "
        'Must be in the form of "image_name":"tag".'
    )
    group.addoption("--db-image", action="store", default=None, help=db_image_help)
    parser.addini("db-image", db_image_help, type="args")

    db_name_help = (
        "Specify the name of the container. If this is not "
        "specified a random container name will be used with the "
        'prefix "docker-db"'
    )

    group.addoption("--db-name", action="store", default=None, help=db_name_help)
    parser.addini("db-name", db_name_help, type="args")

    db_host_port_help = (
        "Specify the port that the db should be listening to on the host machine."
    )
    group.addoption(
        "--db-host-port", action="store", default=None, help=db_host_port_help
    )
    parser.addini("db-host-port", db_host_port_help, type="args")

    db_port_help = (
        "Specify the port that the db should be listening to in the "
        "container. This should be the default port used by your "
        "database."
    )

    group.addoption("--db-port", action="store", default=None, help=db_port_help)
    parser.addini("db-port", db_port_help, type="args")

    db_persist_container_help = (
        "If set, the container created will not be torn down "
        "after the test suite has ran. By default any image created "
        "will be torn down and removed after the test suite has "
        "finished."
    )
    group.addoption(
        "--db-persist-container",
        action="store_true",
        help=db_persist_container_help,
    )
    parser.addini("db-persist-container", db_persist_container_help, type="bool")

    db_docker_file_help = (
        "Specify the name of the Dockerfile within the directory set as the "
        "db-docker-context."
        "If a path is given as well as an image name, "
        "the Dockerfile will be used."
    )
    group.addoption(
        "--db-dockerfile",
        action="store",
        default=None,
        help=db_docker_file_help,
    )
    parser.addini("db-dockerfile", db_docker_file_help, type="args")

    db_docker_context_help = "The directory to use as the docker build context."

    group.addoption(
        "--db-docker-context",
        action="store",
        default=None,
        help=db_docker_context_help,
    )

    parser.addini("db-docker-context", db_docker_context_help, type="args")

    db_docker_env_vars_help = (
        "Comma separated list of environment variables to pass to 'docker run'"
    )

    parser.addini("db-docker-env-vars", help=db_docker_env_vars_help, type="args")

    group.addoption(
        "--db-docker-env-vars",
        action="store",
        default=None,
        help=db_docker_env_vars_help,
    )

    docker_compose_file_help = (
        "Path to the Docker Compose file to use for setting up multiple containers."
    )
    group.addoption(
        "--docker-compose-file",
        action="store",
        default=None,
        help=docker_compose_file_help,
    )
    parser.addini("docker-compose-file", docker_compose_file_help, type="args")

    docker_compose_project_name_help = "Specify the project name for Docker Compose."
    group.addoption(
        "--docker-compose-project-name",
        action="store",
        default=None,
        help=docker_compose_project_name_help,
    )
    parser.addini(
        "docker-compose-project-name", docker_compose_project_name_help, type="args"
    )

    docker_compose_services_help = (
        "Specify which services to start (comma-separated). "
        "If not specified, all services in the compose file will be started."
    )
    group.addoption(
        "--docker-compose-services",
        action="store",
        default=None,
        help=docker_compose_services_help,
    )
    parser.addini("docker-compose-services", docker_compose_services_help, type="args")


@pytest.fixture(scope="session")
def _docker() -> DockerClient:
    """
    Returns the actual docker client.

    This should not be used by users of this plugin.
    """
    return docker.from_env()


@pytest.fixture(scope="session")
def docker_db(
    request: pytest.FixtureRequest, _docker: DockerClient
) -> Generator[Container, None, None]:
    """
    A fixture that creates returns a `Container` object that is running the
    specified database instance.
    """
    opts = _DockerDBOptions(request)

    container = None

    # find the container
    for c in _docker.containers.list(all=True):
        if opts.db_name in c.name:
            container = c
            break

    # create the container
    if container is None:
        if opts.docker_file is not None:
            opts.db_image = _build_image(_docker, opts)
        elif opts.db_image is not None:
            try:
                _docker.images.pull(opts.db_image)
            except APIError as e:
                pytest.fail(f"Unable to pull image: {opts.db_image}. \n{e}")

        if opts.volume_args:
            _create_volume(_docker, opts.host_mount_path)

        try:
            container = _docker.containers.create(
                image=opts.db_image,
                name=opts.db_name,
                ports={opts.db_port: opts.host_port},
                detach=True,
                volumes=opts.volume_args or None,
                environment=opts.env_vars,
            )
        except APIError as e:
            pytest.fail(f"Unable to create container.\n{e}")

    if container is None:
        pytest.fail("Could not create container")
        return

    if container.status != "running":
        try:
            container.start()
        except APIError as e:
            # TODO: make this smart and kill a container that is already running on the port # noqa
            pytest.fail(f"Unable to start container with ID: {container}. \n{e}")

    yield container

    if not opts.persist_container:
        _kill_rm_container(container.id, _docker)


def _build_image(_docker: DockerClient, opts: _DockerDBOptions) -> str:
    img_name = f"{opts.db_name}"
    try:
        _ = _docker.images.build(  # noqa: F841
            path=opts.context,
            rm=True,
            tag=opts.db_name,
            pull=False,
            dockerfile=opts.docker_file,
        )
    except APIError as e:
        pytest.fail(
            f"Unable to build image at "
            f"path: {os.getcwd() + os.sep + (opts.docker_file or '')}."
            f"\n{e}"
        )
    return img_name


def _kill_rm_container(container_id: str, _docker: DockerClient) -> None:
    """
    Kills and removes the container.

    .. note::

        If there is an exception raised when killing or removing the container,
        it will not be raised. It will be printed to stdout, so it is not
        just swallowed.
    """
    try:
        _docker.api.kill(container=container_id)
    except APIError:
        print(f"Unable to kill container with ID: {container_id}")

    try:
        _docker.api.remove_container(container=container_id)
    except APIError:
        print(f"Unable to remove container with ID: {container_id}")


def _create_volume(_docker: DockerClient, vols: list[str] | None) -> None:
    """
    Try to create a named volume.

    If the volume is path, a named volume will not be created.
    If there is already a volume with the given name, it will not be touched.

    If the volume cannot be created, then the tests will fail quickly.
    :param _docker: The docker client.
    :param vols: A list of *host* volume paths.
    """
    if not vols:
        return

    for p in vols:
        if not utils.is_pathname_valid(p):
            vol = _docker.volumes.list(filters={"name": p})
            if not vol:
                try:
                    _docker.create_volume(p)
                except APIError:
                    pytest.fail(f"Unable to create volume: {p}")


def _get_config_str(key: str, request: pytest.FixtureRequest) -> str | None:
    """
    Gets a string config value from the command line arg or the ini file.

    Preference is given to the ini file, then the command line arg.
    """
    val: Any = request.config.getini(key)

    if val:
        if isinstance(val, list):
            return str(val[0])
        if isinstance(val, str):
            return val
        return None

    opt: Any = request.config.getoption(f"--{key}")
    if isinstance(opt, str):
        return opt

    return None


def _get_config_bool(key: str, request: pytest.FixtureRequest) -> bool:
    """
    Gets a boolean config value from the ini file or the command line arg.

    Preference is given to the ini file for bools (due to how store_true works
    on the CLI).
    """
    val: Any = request.config.getini(key)
    if isinstance(val, bool) and val:
        return val

    val = request.config.getoption(f"--{key}")
    if isinstance(val, bool):
        return val

    return False


class _DockerDBOptions:
    """Holds docker_db options."""

    def __init__(self, request: pytest.FixtureRequest) -> None:
        self._db_image = _get_config_str("db-image", request)
        self._db_name = _get_config_str("db-name", request)
        self._host_port: str | int | None = _get_config_str("db-host-port", request)
        self._db_port = _get_config_str("db-port", request)
        self.persist_container = _get_config_bool("db-persist-container", request)
        self._volume_args = _get_config_str("db-volume-args", request)
        self._docker_file = _get_config_str("db-dockerfile", request)
        self._context = _get_config_str("db-docker-context", request)
        self._env_vars = _get_config_str("db-docker-env-vars", request)

        self._validate()

    def _validate(self) -> None:
        if self.db_image is None and self.docker_file is None:
            pytest.fail("Must specify an image or a Dockerfile to use as the database.")

    @property
    def context(self) -> str:
        return self._context or os.getcwd()

    @property
    def docker_file(self) -> str | None:
        return self._docker_file

    @property
    def db_image(self) -> str | None:
        return self._db_image

    @db_image.setter
    def db_image(self, val: str | None) -> None:
        self._db_image = val

    @property
    def db_name(self) -> str:
        if self._db_name is None:
            self._db_name = f"docker-db-{str(uuid.uuid4())}"
        return self._db_name

    @property
    def db_port(self) -> str | None:
        return self._db_port

    @property
    def host_port(self) -> str | int:
        if self._host_port is None:
            self._host_port = self._find_unused_port()
        return self._host_port

    @property
    def host_mount_path(self) -> list[str] | None:
        return self._parse_volume_args(0)

    @property
    def container_mount_path(self) -> list[str] | None:
        return self._parse_volume_args(1)

    @property
    def volume_permissions(self) -> list[str] | None:
        try:
            return self._parse_volume_args(2)
        except IndexError:
            return ["rw"]

    def _parse_volume_args(self, ix: int) -> list[str] | None:
        if self.volume_args is None:
            return None
        args = []
        for p in self.volume_args:
            if p:
                args.append(p.split(":")[ix])
        return args

    @property
    def volume_args(self) -> list[str] | None:
        if self._volume_args:
            if "," in self._volume_args:
                return self._volume_args.split(",")
            else:
                return [self._volume_args]
        return None

    @property
    def env_vars(self) -> list[str] | None:
        if self._env_vars:
            return self._env_vars.split(",")
        else:
            return None

    @staticmethod
    def _find_unused_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            port: int = s.getsockname()[1]
            return port


class _DockerComposeOptions:
    """Holds docker-compose options."""

    def __init__(self, request: pytest.FixtureRequest) -> None:
        self._compose_file = _get_config_str("docker-compose-file", request)
        self._project_name = _get_config_str("docker-compose-project-name", request)
        self._services = _get_config_str("docker-compose-services", request)
        self.persist_container = _get_config_bool("db-persist-container", request)
        self._validate()

    def _validate(self) -> None:
        if self.compose_file is None:
            pytest.fail(
                "Must specify a Docker Compose file. Use --docker-compose-file option."
            )
        elif not os.path.isfile(self.compose_file):
            pytest.fail(f"Docker Compose file not found: {self.compose_file}")

    @property
    def compose_file(self) -> str | None:
        return self._compose_file

    @property
    def project_name(self) -> str:
        if self._project_name is None:
            self._project_name = f"pytest-docker-compose-{str(uuid.uuid4())}"
        return self._project_name

    @property
    def services(self) -> list[str] | None:
        if self._services:
            return [s.strip() for s in self._services.split(",") if s.strip()]
        else:
            return None


@pytest.fixture(scope="session")
def docker_compose(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    A fixture that brings up and tears down containers using Docker Compose.

    This fixture validates that Docker Compose is installed before attempting
    to bring up containers.
    """
    # Check if Docker Compose is installed
    if not _check_docker_compose_installed():
        pytest.fail(
            "Docker Compose is not installed or not working on this system. "
            "Please install Docker Compose to use this fixture."
        )

    opts = _DockerComposeOptions(request)
    compose_file = opts.compose_file
    project_name = opts.project_name
    services = opts.services
    persist = opts.persist_container

    def compose_cmd(base: str) -> list[str]:
        if (
            shutil.which("docker")
            and subprocess.run(
                ["docker", "compose", "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).returncode
            == 0
        ):
            # Use new-style docker compose subcommand
            cmd = [
                "docker",
                "compose",
                "-f",
                compose_file or "",
                "-p",
                project_name,
                base,
            ]
        else:
            # Fall back to old-style docker-compose command
            cmd = [
                "docker-compose",
                "-f",
                compose_file or "",
                "-p",
                project_name,
                base,
            ]

        if services:
            cmd.extend(services)
        return cmd

    try:
        up_cmd = compose_cmd("up") + ["-d"]
        subprocess.run(up_cmd, check=True)
    except Exception as e:
        pytest.fail(f"Failed to bring up docker compose services: {e}")

    yield  # No return value; user can interact with containers via docker SDK if needed

    if not persist:
        try:
            down_cmd = compose_cmd("down")
            subprocess.run(down_cmd, check=True)
        except Exception as e:
            print(f"Failed to tear down docker compose services: {e}")


def _check_docker_compose_installed() -> bool:
    """
    Check if Docker Compose is installed on the system.

    Returns:
        bool: True if Docker Compose is installed, False otherwise
    """
    # First check if docker compose is available as a plugin to docker CLI (new style)
    try:
        # Use shutil.which to check if docker is in PATH
        if not shutil.which("docker"):
            return False

        result = subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        # If docker compose as plugin fails, check for docker-compose binary (old style)
        try:
            if shutil.which("docker-compose"):
                result = subprocess.run(
                    ["docker-compose", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                return result.returncode == 0
        except Exception:
            pass

    return False
