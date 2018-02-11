# -*- coding: utf-8 -*-
import uuid
import socket
from typing import List, Optional

import pytest
import docker
from docker import Client
from docker.errors import APIError


def pytest_addoption(parser):
    group = parser.getgroup('docker-db')

    group.addoption(
        '--db-volume-name',
        action='store',
        default=None,
        help=('Specify the name of the volume to use to store the data. '
              'If this is not specified then no volume will be used.')
    )

    group.addoption(
        '--db-volume-args',
        action='store',
        default=None,
        help=('Provide the "-v" arguments that you would pass to the '
              '"docker run" command if you were using the cli. If you need '
              'multiple volumes mounted separate them with commas.\n'
              'The basic syntax is /host/vol/path:/path/in/container:rw. '
              'For more information please visit the docker documentation: '
              'https://docs.docker.com/storage/volumes/#start-a-container-with-a-volume')
    )

    group.addoption(
        '--db-image',
        action='store',
        default=None,
        help=('Specify the name of the image to use as the DB. '
              'Must be in the form of "image_name":"tag".')
    )

    group.addoption(
        '--db-name',
        action='store',
        default=None,
        help='Specify the name of the image.'
    )

    group.addoption(
        '--db-host-port',
        action='store',
        default=None,
        help=('Specify the port that the db should be listening to on the host'
              'machine.')
    )

    group.addoption(
        '--db-port',
        action='store',
        default=None,
        help=('Specify the port that the db should be listening to in the '
              'container. This should be the default port used by your '
              'database.')
    )

    group.addoption(
        '--db-persist-container',
        action='store_true',
        help=('If set, the container created will not be torn down '
              'after the test suite has ran. By default any image created '
              'will be torn down and removed after the test suite has '
              'finished.')
    )


@pytest.fixture(scope='session')
def _docker():
    """
    Returns the actual docker client.

    This should not be used by users of this plugin.
    """
    return docker.from_env()


@pytest.fixture(scope='session')
def docker_db(request, _docker: Client):
    opts = _DockerDBOptions(request)

    container = None

    for c in _docker.containers(all=True):
        for name in c['Names']:
            if opts.db_name in name:
                container = c
                break

    if container is None:
        port = opts._host_port
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
            host_config['binds'] = [opts.volume_args]

        container = _docker.create_container(
            image=opts.db_image,
            name=opts.db_name,
            ports=[opts.db_port],
            detach=True,
            host_config=host_config
        )

    try:
        _docker.start(container=container['Id'])
    except APIError as e:
        # TODO: make this smart and kill a container that is already running on the port
        pytest.fail(f'Unable to start container with ID: {container["Id"]}. '
                    f'\n{e}')

    yield container

    if not opts.persist_container:
        _docker.kill(container=container['Id'])
        _docker.remove_container(container=container['Id'])


class _DockerDBOptions:
    """Holds docker_db options."""

    def __init__(self, request):
        self._db_image = request.config.getoption('--db-image')
        self._db_name = request.config.getoption('--db-name')
        self._host_port = request.config.getoption('--db-host-port')
        self._db_port = request.config.getoption('--db-port')
        self.persist_container = request.config.getoption(
            '--db-persist-container')
        self._volume_args = request.config.getoption('--db-volume-args')

        self._validate()

    def _validate(self):
        if self.db_image is None:
            pytest.fail('Must specify an image to use as the database.')

    @property
    def db_image(self):
        return self._db_image

    @property
    def db_name(self):
        return self._db_name

    @db_name.getter
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
        return self._host_port

    @host_port.getter
    def host_port(self):
        if self._host_port is None:
            return self._find_unused_port()
        else:
            return self._host_port

    @property
    def host_mount_path(self) -> Optional[List[str]]:
        return self.host_mount_path

    @host_mount_path.getter
    def host_mount_path(self) -> Optional[List[str]]:
        return self._parse_volume_args(0)

    @property
    def container_mount_path(self) -> Optional[List[str]]:
        return self.container_mount_path

    @container_mount_path.getter
    def container_mount_path(self) -> Optional[List[str]]:
        return self._parse_volume_args(1)

    @property
    def volume_permissions(self) -> Optional[List[str]]:
        return self.volume_permissions

    @volume_permissions.getter
    def volume_permissions(self) -> List[str]:
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
        return self.volume_args

    @volume_args.getter
    def volume_args(self) -> Optional[List[str]]:
        if self._volume_args:
            if ',' in self._volume_args:
                return self._volume_args.split(',')
            else:
                return self._volume_args

    @staticmethod
    def _find_unused_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[0]
