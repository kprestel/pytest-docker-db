# pytest-docker-db

A plugin to use docker databases for pytests

## What is this?

This is a pytest plugin that hooks into the host's :code:`docker` daemon to create and teardown containers within the pytest life cycle.

## Features

- Use custom :code:`Dockerfile`s or base images from `Dockerhub`
- Use `volumes` to persist test data in between testing sessions
- Specify what port you want the container to be listening on the host machine and the container
- Optionally persist the container between test sessions
- Name the containers created

## Requirements

- docker-py>=6
- pytest>=7
- docker

## Installation

You can install `pytest-docker-db` via `pip` from `PyPI`

```bash
pip install pytest-docker-db
```

## Configuration

- db-volume-args

  - Provide the "-v" arguments that you would pass to the
    "docker run" command if you were using the cli. If you need
    multiple volumes mounted separate them with commas.
  - The basic syntax is :code:`/host/vol/path:/path/in/container:rw`.
    If using a named volume, the syntax would be :code:`vol-name:/path/in/container:rw`
    'For more information please visit the `docker documentation`'

- db-image

  - Specify the name of the image to use as the DB.

    - Must be in the form of `"image_name":"tag"`.

- db-name

  - Specify the name of the container. If this is not specified a random container name will be
    used with the prefix `docker-db`

- db-host-port

  - Specify the port that the db should be listening to on the host machine.

- db-port

  - Specify the port that the db should be listening to in the container.
    This is often the default port used by your database.

- db-persist-container

  - If set, the container created will not be torn down after the test suite has ran.
    By default any image created will be torn down and removed after the test suite has finished.

- db-dockerfile

  - Specify the name of the Dockerfile within the directory set as the :code:`db-build-context`

    - If a path is given as well as an image name, the Dockerfile will be used.

- db-docker-context

  - The directory to use as the docker build context.

- db-docker-env-vars

  - A comma separated list of environment variables to pass to `docker run`
    - `--db-docker-env-vars=FOO=BAR,PASSWORD=BAZ`

## Usage

Plugin contains one fixture:
_docker_db_ - it's a session scoped fixture that returns a `docker-py container` object.
For almost all use cases the user will not care about this object.

The recommended way to use this fixture is to create an :code:`autouse=True` fixture in your `conftest.py` file to automatically invoke the setup of the containers.

```python
    @pytest.fixture(scope='session', autouse=True)
    def my_docker_db(docker_db):
        pass
```

Can be configured via the :code:`pytest` CLI or the :code:`pytest.ini` file.

pytest.ini:

```ini
    [pytest]
    db-volume-args=/home/kp/vol:/var/lib/postgresql/data:rw
    db-image=postgres:latest
    db-name=test-postgres
    db-port=5432
    db-host-port=5434
```

pytest CLI using a `Dockerhub`

```bash
    pytest --db-image=postgrest:latest --db-name=test-postgres --db-port=5432 --db-host-port=5434
```

pytest CLI using a custom image

```bash
    pytest --db-dockerfile=Dockerfile --db-name=test-postgres --db-port=5432 --db-host-port=5434
```

pytest CLI using a custom image and passing environment variables to it

```bash
    pytest --db-dockerfile=Dockerfile --db-name=test-postgres --db-port=5432 --db-host-port=5434 --db-docker-env-vars=POSTGRES_PASSWORD=FOO,POSTGRES_USER=BAR
```

## Contributing

Contributions are very welcome. Tests can be run with `tox`, please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the `MIT` license, "pytest-docker-db" is free and open source software

## Issues

If you encounter any problems, please file an issue along with a detailed description.

`MIT`: http://opensource.org/licenses/MIT
`file an issue`: https://github.com/kprestel/pytest-docker-db/issues
`pytest`: https://github.com/pytest-dev/pytest
`pip`: https://pypi.python.org/pypi/pip/
`PyPI`: https://pypi.python.org/pypi
`docker-py container`: http://docker-py.readthedocs.io/en/stable/containers.html
`Dockerhub`: https://hub.docker.com/
`docker documentation`: https://docs.docker.com/storage/volumes/#start-a-container-with-a-volume
