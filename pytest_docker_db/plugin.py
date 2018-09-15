# -*- coding: utf-8 -*-
import os
from typing import List, TYPE_CHECKING

import pytest
import docker
from docker.errors import APIError
import pytest_docker_db.util as utils

if TYPE_CHECKING:
    from _pytest.config.argparsing import Parser
    from _pytest.config import Config, PytestPluginManager
    from pytest_docker_db.docker_db import DockerDBSettings
    from docker import DockerClient


def pytest_addoption(parser: "Parser"):
    group = parser.getgroup(
        "docker-db", "Arguments to configure the " "pytest-docker-db plugin."
    )

    db_vol_args_help = (
        'Provide the "-v" arguments that you would pass to the '
        '"docker run" command if you were using the cli. If you need '
        "multiple volumes mounted separate them with commas.\n"
        "The basic syntax is /host/vol/path:/path/in/container:rw. "
        "If using a named volume, the syntax would be "
        "vol-name:/path/in/container:rw "
        "For more information please visit the docker documentation: "
        "https://docs.docker.com/storage/volumes/#start-a-container-with-a-volume"  # noqa
    )
    group.addoption(
        "--db-volume-args", action="store", default=None, help=db_vol_args_help
    )
    parser.addini("db-volume-args", db_vol_args_help, type="args")

    db_image_help = (
        "Specify the name of the image to use as the DB. "
        'Must be in the form of "image_name":"tag".'
    )
    group.addoption(
        "--db-image", action="store", default=None, help=db_image_help
    )
    parser.addini("db-image", db_image_help, type="args")

    db_name_help = (
        "Specify the name of the container. If this is not "
        "specified a random container name will be used with the "
        'prefix "docker-db"'
    )

    group.addoption(
        "--db-name", action="store", default=None, help=db_name_help
    )
    parser.addini("db-name", db_name_help, type="args")

    db_host_port_help = (
        "Specify the port that the db should be listening to on the host"
        "machine."
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

    group.addoption(
        "--db-port", action="store", default=None, help=db_port_help
    )
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
    parser.addini(
        "db-persist-container", db_persist_container_help, type="bool"
    )

    db_docker_file_help = (
        "Specify the path to the directory containing the "
        "Dockerfile to use in the build. "
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


def pytest_addhooks(pluginmanager: "PytestPluginManager"):
    from pytest_docker_db import hooks

    pluginmanager.add_hookspecs(hooks)


@pytest.mark.trylast
def pytest_configure(config: "Config"):
    from pytest_docker_db.docker_db import (
        DockerDBSettings,  # noqa: F811
        DockerDB,  # noqa: F811
    )

    config.docker_db = DockerDBSettings(config)
    db = DockerDB(config.docker_db)
    config.pluginmanager.register(db, "db")


@pytest.fixture(scope="session")
def _docker():
    """
    Returns the actual docker client.

    This should not be used by users of this plugin.
    """
    return docker.from_env()


@pytest.fixture(scope="session")
def docker_db(pytestconfig, _docker):
    """
    A fixture that creates returns a `Container` object that is running the
    specified database instance.
    """
    opts: "DockerDBSettings" = pytestconfig.docker_db
    opts.validate()

    container = None

    # find the container
    for c in _docker.containers.list(all=True):
        if opts.db_name in c.name:
            container = c
            break

    # create the container
    if container is None:
        if opts.docker_file is not None:
            img_name = f"{opts.db_name}"
            try:
                _ = _docker.images.build(  # noqa: F841
                    path=os.getcwd(),
                    rm=True,
                    tag=opts.db_name,
                    pull=False,
                    dockerfile=opts.docker_file,
                )
            except APIError as e:
                pytest.fail(
                    f"Unable to build image at "
                    f"path: {os.getcwd() + os.sep + opts.docker_file}."
                    f"\n{e}"
                )
            opts.db_image = img_name
        else:
            try:
                _docker.images.pull(opts.db_image)
            except APIError as e:
                pytest.fail(f"Unable to pull image: {opts.db_image}. \n{e}")

        host_config = _docker.api.create_host_config(
            port_bindings={opts.db_port: opts.host_port}
        )

        if opts.volume_args:
            _create_volume(_docker, opts.host_mount_path)
            host_config["binds"] = opts.volume_args

        try:
            container = _docker.containers.create(
                image=opts.db_image,
                name=opts.db_name,
                ports={opts.db_port: opts.host_port},
                detach=True,
                volumes=opts.volume_args or None,
            )
        except APIError as e:
            pytest.fail(f"Unable to create container.\n{e}")

    try:
        container.start()
    except APIError as e:
        # TODO: make this smart and kill a container that is already running on the port # noqa
        pytest.fail(
            f'Unable to start container with ID: {container["Id"]}. ' f"\n{e}"
        )

    yield container

    if not opts.persist_container:
        _kill_rm_container(container.id, _docker)


def _kill_rm_container(container_id: str, _docker: "DockerClient") -> None:
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


def _create_volume(_docker: "DockerClient", vols: List[str]) -> None:
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
