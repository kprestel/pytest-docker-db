import socket
import uuid
from typing import Optional, List

import pytest


class DockerDB:
    """Contains hook definitions"""

    def __init__(self, settings: "DockerDBSettings"):
        self.settings = settings
        self.config = settings.config

    def pytest_runtest_setup(self, item):
        self.config.hook.pytest_docker_db_init_db(config=self.config)

    def pytest_runtest_teardown(self, item):
        self.config.hook.pytest_docker_db_teardown_db(config=self.config)


class DockerDBSettings:
    """Holds docker_db options."""

    def __init__(self, config):
        self.config = config
        self._db_image = self._get_config_val("db-image")
        self._db_name = self._get_config_val("db-name")
        self._host_port = self._get_config_val("db-host-port")
        self._db_port = self._get_config_val("db-port")
        self._volume_args = self._get_config_val("db-volume-args")
        self._docker_file = self._get_config_val("db-dockerfile")

    def _get_config_val(self, key: str):
        """
        Gets the config value from the command line arg or the ini file.

        .. note::

            Preference is given to the command line arg, meaning if the
            argument is set via the command line and the ini file, the command
            line argument will be used.

        :param key: the key to look up. Must not have the beginning dashes.
        :param request: the pytest `request` object.
        """
        # have to check the ini file first due to the way bools work on the cli
        val = self.config.getini(key)

        if val:
            if type(val) == bool:
                return val
            else:
                return val[0]

        val = self.config.getoption(f"--{key}")
        if val is not None:
            return val

    def validate(self):
        if self.db_image is None and self.docker_file is None:
            pytest.fail(
                "Must specify an image or a Dockerfile "
                "to use as the database."
            )

    @property
    def persist_container(self):
        return self._get_config_val("db-persist-container")

    @property
    def docker_file(self):
        return self._get_config_val("db-dockerfile")

    @property
    def db_image(self):
        if not self._db_image:
            return self._get_config_val("db-image")
        else:
            return self._db_image

    @db_image.setter
    def db_image(self, val):
        self._db_image = val

    @property
    def db_name(self):
        if self._db_name is None:
            return f"docker-db-{str(uuid.uuid4())}"
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
            return self._get_config_val("db-host-port")

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
            return ["rw"]

    def _parse_volume_args(self, ix: int) -> Optional[List[str]]:
        if self.volume_args is None:
            return
        args = []
        for p in self.volume_args:
            if p:
                args.append(p.split(":")[ix])
        return args

    @property
    def volume_args(self) -> Optional[List[str]]:
        self._volume_args = self._get_config_val("db-volume-args")
        if self._volume_args:
            if "," in self._volume_args:
                return self._volume_args.split(",")
            else:
                return [self._volume_args]

    @staticmethod
    def _find_unused_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[0]
