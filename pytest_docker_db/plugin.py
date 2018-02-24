# -*- coding: utf-8 -*-
import uuid
import socket
from typing import List, Optional

import pytest
import docker
from _pytest.config import Parser
from docker import Client
from docker.errors import APIError
import pytest_docker_db.util as utils

def pytest_addoption(parser: Parser):
    group = parser.getgroup('docker-db', 'Arguments to configure the '
                                         'pytest-docker-db plugin.')

    db_vol_args_help = (
        'Provide the "-v" arguments that you would pass to the '
        '"docker run" command if you were using the cli. If you need '
        'multiple volumes mounted separate them with commas.\n'
        'The basic syntax is /host/vol/path:/path/in/container:rw. '
        'If using a named volume, the syntax would be '
        'vol-name:/path/in/container:rw '
        'For more information please visit the docker documentation: '
        'https://docs.docker.com/storage/volumes/#start-a-container-with-a-volume'
    )
    group.addoption(
        '--db-volume-args',
        action='store',
        default=None,
        help=db_vol_args_help
    )
    parser.addini('db-volume-args', db_vol_args_help, type='args')

    db_image_help = ('Specify the name of the image to use as the DB. '
                     'Must be in the form of "image_name":"tag".')
    group.addoption(
        '--db-image',
        action='store',
        default=None,
        help=db_image_help
    )
    parser.addini('db-image', db_image_help, type='args')

    db_name_help = ('Specify the name of the container. If this is not '
                    'specified a random container name will be used with the '
                    'prefix "docker-db"')
    group.addoption(
        '--db-name',
        action='store',
        default=None,
        help=db_name_help
    )
    parser.addini('db-name', db_name_help, type='args')

    db_host_port_help = (
        'Specify the port that the db should be listening to on the host'
        'machine.')
    group.addoption(
        '--db-host-port',
        action='store',
        default=None,
        help=db_host_port_help
    )
    parser.addini('db-host-port', db_host_port_help, type='args')

    db_port_help = (
        'Specify the port that the db should be listening to in the '
        'container. This should be the default port used by your '
        'database.')

    group.addoption(
        '--db-port',
        action='store',
        default=None,
        help=db_port_help
    )
    parser.addini('db-port', db_port_help, type='args')

    db_persist_container_help = (
        'If set, the container created will not be torn down '
        'after the test suite has ran. By default any image created '
        'will be torn down and removed after the test suite has '
        'finished.')
    group.addoption(
        '--db-persist-container',
        action='store_true',
        help=db_persist_container_help
    )
    parser.addini('db-persist-container', db_persist_container_help,
                  type='bool')


@pytest.fixture(scope='session')
def _docker():
    """
    Returns the actual docker client.

    This should not be used by users of this plugin.
    """
    return docker.from_env()


@pytest.fixture(scope='session')
def docker_db(request, _docker: Client):
    """
    A fixture that creates returns a `Container` object that is running the
    specified database instance.
    """
    opts = _DockerDBOptions(request)

    container = None

    # find the container
    for c in _docker.containers(all=True):
        for name in c['Names']:
            if opts.db_name in name:
                container = c
                break

    # create the container
    if container is None:
        port = opts.host_port
        try:
            _docker.pull(opts.db_image)
        except APIError as e:
            pytest.fail(f'Unable to pull image: {opts.db_image}. \n{e}')

        host_config = _docker.create_host_config(
            port_bindings={
                opts.db_port: port
            }
        )

        if opts.volume_args:
            _create_volume(_docker, opts.host_mount_path)
            host_config['binds'] = opts.volume_args

        container = _docker.create_container(
            image=opts.db_image,
            name=opts.db_name,
            ports=[opts.db_port],
            detach=True,
            host_config=host_config,
            volumes=opts.container_mount_path or None
        )

    try:
        _docker.start(container=container['Id'])
    except APIError as e:
        # TODO: make this smart and kill a container that is already running on the port
        pytest.fail(f'Unable to start container with ID: {container["Id"]}. '
                    f'\n{e}')

    yield container

    if not opts.persist_container:
        _kill_rm_container(container['Id'], _docker)


def _kill_rm_container(container_id: str, _docker: Client) -> None:
    """
    Kills and removes the container.

    .. note::

        If there is an exception raised when killing or removing the container,
        it will not be raised. It will be printed to stdout, so it is not
        just swallowed.
    """
    try:
        _docker.kill(container=container_id)
    except APIError:
        print(f'Unable to kill container with ID: {container_id}')

    try:
        _docker.remove_container(container=container_id)
    except APIError:
        print(f'Unable to remove container with ID: {container_id}')


def _create_volume(_docker: Client, vols: List[str]) -> None:
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
            vol = _docker.volumes.list(filters={'name': p})
            if not vol:
                try:
                    _docker.create_volume(p)
                except APIError:
                    pytest.fail(f'Unable to create volume: {p}')


class _DockerDBOptions:
    """Holds docker_db options."""

    def __init__(self, request):
        self._db_image = self._get_config_val('db-image', request)
        self._db_name = self._get_config_val('db-name', request)
        self._host_port = self._get_config_val('db-host-port', request)
        self._db_port = self._get_config_val('db-port', request)
        self.persist_container = self._get_config_val('db-persist-container',
                                                      request)
        self._volume_args = self._get_config_val('db-volume-args', request)

        self._validate()

    def _get_config_val(self, key: str, request):
        """
        Gets the config value from the command line arg or the ini file.

        .. note::

            Preference is given to the command line arg, meaning if the
            argument is set via the command line and the ini file, the command
            line argument will be used.

        :param key: the key to look up. Must not have the beginning dashes.
        :param request: the pytest `request` object.
        """
        val = request.config.getoption(f'--{key}')
        if val is not None:
            return val

        val = request.config.getini(key)

        if val:
            return val[0]

    def _validate(self):
        if self.db_image is None:
            pytest.fail('Must specify an image to use as the database.')

    @property
    def db_image(self):
        return self._db_image

    @property
    def db_name(self):
        if self._db_name is None:
            return f'docker-db-{str(uuid.uuid4())}'
        else:
            return self._db_name

    @property
    def db_port(self):
        return self._db_port

    @property
    def host_port(self):
        if self._host_port is None:
            return self._find_unused_port()
        else:
            return self._host_port

    @property
    def host_mount_path(self) -> Optional[List[str]]:
        return self._parse_volume_args(0)

    @property
    def container_mount_path(self) -> Optional[List[str]]:
        return self._parse_volume_args(1)

    @property
    def volume_permissions(self) -> Optional[List[str]]:
        try:
            return self._parse_volume_args(2)
        except IndexError:
            return ['rw']

    def _parse_volume_args(self, ix: int) -> Optional[List[str]]:
        if self.volume_args is None:
            return
        args = []
        for p in self.volume_args:
            if p:
                args.append(p.split(':')[ix])
        return args

    @property
    def volume_args(self) -> Optional[List[str]]:
        if self._volume_args:
            if ',' in self._volume_args:
                return self._volume_args.split(',')
            else:
                return [self._volume_args]

    @staticmethod
    def _find_unused_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[0]
