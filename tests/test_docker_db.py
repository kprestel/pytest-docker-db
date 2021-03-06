# -*- coding: utf-8 -*-
import os
from pathlib import Path
from shutil import copy2
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.pytester import Testdir
    from docker import Client


def test_docker_fixture(testdir):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    testdir.makepyfile(
        """
            def test_sth(docker_db):
                assert docker_db is not None
        """
    )

    # run pytest with the following cmd args
    result = testdir.runpytest(
        "--db-image=postgres:latest",
        "--db-name=test-postgres-1",
        "--db-port=5432",
        "--db-host-port=5342",
        "-v",
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["*::test_sth PASSED*"])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_bad_container_name(testdir):
    """
    Test that given a bad image name, the test fails.
    """
    testdir.makepyfile(
        """
            def test_bad_container(docker_db):
                assert docker_db is None
            """
    )

    result = testdir.runpytest(
        "--db-image=not-an-image:latest",
        "--db-name=test-bad",
        "--db-port=1010",
        "--db-host-port=1011",
        "-v",
    )

    assert result.ret == 1


def test_no_image(testdir):
    """
    Test that given no image, pytest fails.
    """
    testdir.makepyfile(
        """
            def test_bad_container(docker_db):
                assert docker_db is None
            """
    )

    result = testdir.runpytest(
        "--db-name=test-bad", "--db-port=1010", "--db-host-port=1011", "-v"
    )

    result.stdout.fnmatch_lines(
        ["*Must specify an image or a Dockerfile " "to use as the database.*"]
    )

    assert result.ret == 1


def _make_postgres_pyfile(
    testdir,
    host_port,
    container_name,
    volume="/tmp/docker",
    image_name="postgres:latest",
):
    testdir.makepyfile(
        """
            def test_container(docker_db, _docker):
                inspect = _docker.api.inspect_container(docker_db.id)
                ports = inspect['NetworkSettings']['Ports']
                assert f'/{container_name}' == inspect.get('Name')
                assert f'{image_name}' == inspect.get('Config')['Image']
                assert '5432/tcp' in ports
                assert '{host_port}' == ports['5432/tcp'][0]['HostPort']
                host_config = inspect['HostConfig']
                assert ('{volume}:/var/lib/postgresql/data:rw'
                == host_config['Binds'][0])
            """.format(
            host_port=host_port,
            container_name=container_name,
            volume=volume,
            image_name=image_name,
        )
    )


def test_postgres_options(testdir: "Testdir", tmpdir):
    """
    Ensure that the container gets set up properly with
    different options.
    """
    db_name = "test-postgres-2"
    host_port = "5434"
    vol = str(tmpdir)
    _make_postgres_pyfile(
        testdir, host_port=host_port, container_name=db_name, volume=vol
    )

    result = testdir.runpytest(
        f"--db-volume-args={vol}:/var/lib/postgresql/data:rw",
        "--db-image=postgres:latest",
        f"--db-name={db_name}",
        "--db-port=5432",
        f"--db-host-port={host_port}",
        "--db-persist-container",
        "--db-docker-env-vars=POSTGRES_PASSWORD='FOO',POSTGRES_USER=postgres",
        "-v",
    )

    assert 0 == result.ret

    # manually kill the container because it is persisted
    kill_res = testdir.run("docker", "kill", db_name)
    assert 0 == kill_res.ret
    kill_res = testdir.run("docker", "rm", db_name)
    assert 0 == kill_res.ret


def test_named_volume(testdir: "Testdir", _docker: "Client"):
    """
    Ensure that the container gets set up properly with
    different options.
    """
    db_name = "test-postgres-3"
    host_port = "5438"
    vol_name = "test-vol"
    _make_postgres_pyfile(
        testdir, host_port=host_port, container_name=db_name, volume=vol_name
    )

    result = testdir.runpytest(
        f"--db-volume-args={vol_name}:/var/lib/postgresql/data:rw",
        "--db-image=postgres:latest",
        f"--db-name={db_name}",
        "--db-port=5432",
        f"--db-host-port={host_port}",
        "-v",
    )

    assert 0 == result.ret

    kill_res = testdir.run("docker", "volume", "rm", vol_name)
    assert 0 == kill_res.ret


def test_postgres_ini(testdir: "Testdir"):
    """
    Ensure that the container gets setup properly using the ini config
    """
    db_name = "test-postgres-ini"
    host_port = "5346"
    _make_postgres_pyfile(testdir, host_port=host_port, container_name=db_name)

    testdir.makeini(
        """
            [pytest]
            db-volume-args=/tmp/docker:/var/lib/postgresql/data:rw
            db-image=postgres:latest
            db-name={db_name}
            db-port=5432
            db-host-port={host_port}
            """.format(
            db_name=db_name, host_port=host_port
        )
    )

    result = testdir.runpytest("-v")

    assert 0 == result.ret


def test_postgres_no_volume(testdir):
    """
    Ensure that the container is set up properly and does not have a volume.
    """
    db_name = "test-postgres-no-vol"
    testdir.makepyfile(
        """
            def test_container_no_vol(docker_db, _docker):
                inspect = _docker.api.inspect_container(docker_db.id)
                host_config = inspect['HostConfig']
                assert host_config['Binds'] is None
            """
    )

    result = testdir.runpytest(
        "--db-image=postgres:latest",
        f"--db-name={db_name}",
        "--db-port=5432",
        "--db-host-port=5435",
        "-v",
    )

    assert 0 == result.ret

    # this should return a 1 because the container shouldn't exist
    kill_res = testdir.run("docker", "kill", db_name)
    assert 1 == kill_res.ret
    kill_res = testdir.run("docker", "rm", db_name)
    assert 1 == kill_res.ret


def test_mysql(testdir):
    """
    Test a MySQL container
    """
    db_name = "test-mysql"
    testdir.makepyfile(
        """
            def test_mysql(docker_db, _docker):
                inspect = _docker.api.inspect_container(docker_db.id)
                assert '/test-mysql' == inspect.get('Name')
            """
    )

    result = testdir.runpytest(
        "--db-image=mysql:latest",
        f"--db-name={db_name}",
        "--db-port=3306",
        "--db-host-port=3308",
        "-v",
    )

    assert 0 == result.ret


def test_dockerfile(testdir: "Testdir"):
    """
    Test using a custom Dockerfile.
    """
    db_name = "test-dockerfile"
    image_name = "test-dockerfile"
    host_port = "5351"
    vol_name = "test-dockerfile-vol"
    _make_postgres_pyfile(
        testdir,
        host_port=host_port,
        container_name=db_name,
        volume=vol_name,
        image_name=image_name,
    )
    docker_file = """
    FROM postgres:latest
    ENV POSTGRES_PASSWORD foo
    """
    _ = testdir.makefile("", Dockerfile=docker_file)  # noqa: F841

    result = testdir.runpytest(
        "--db-dockerfile=Dockerfile",
        f"--db-volume-args={vol_name}:/var/lib/postgresql/data:rw",
        f"--db-name={db_name}",
        "--db-port=5432",
        f"--db-host-port={host_port}",
        "-v",
    )

    assert result.ret == 0


def test_docker_context(testdir: "Testdir"):
    """
    Test using a custom Dockerfile.
    """
    db_name = "test-docker-context"
    image_name = "test-docker-context"
    host_port = "5356"
    vol_name = "test-dockerfile-vol-2"
    _make_postgres_pyfile(
        testdir,
        host_port=host_port,
        container_name=db_name,
        volume=vol_name,
        image_name=image_name,
    )
    docker_dir = testdir.mkdir("test-docker")
    dockerfile = docker_dir / "Dockerfile"
    create_users = docker_dir / "create-user.sh"
    docker_contents = (
        "FROM postgres:alpine",
        "COPY create-user.sh /docker-entrypoint-initdb.d/create-user.sh",
        "RUN chmod +x /docker-entrypoint-initdb.d/create-user.sh",
        'CMD ["postgres"]',
    )
    docker_contents = "\n".join(docker_contents)
    create_users_contents = (
        r"#!/bin/bash",
        r"set -e",
        r'psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" <<-EOSQL',
        r"CREATE USER test WITH PASSWORD 'foo';",
        r"ALTER USER hhs WITH SUPERUSER;",
        r"CREATE DATABASE docker-test;",
        r"GRANT ALL PRIVILEGES ON DATABASE docker-test TO test;",
        r"EOSQL",
    )
    create_users_contents = "\n".join(create_users_contents)
    with open(dockerfile, "w") as f:
        f.write(docker_contents)
    with open(create_users, "w") as f:
        f.writelines(create_users_contents)
    # create_users.write_text(create_users_contents)

    result = testdir.runpytest(
        "--db-dockerfile=Dockerfile",
        f"--db-docker-context={str(docker_dir)}",
        f"--db-volume-args={vol_name}:/var/lib/postgresql/data:rw",
        f"--db-name={db_name}",
        "--db-port=5432",
        f"--db-host-port={host_port}",
        "-v",
    )

    assert result.ret == 0


# @pytest.mark.skip
# def test_help_message(testdir):
#     result = testdir.runpytest(
#         '--help',
#     )
# fnmatch_lines does an assertion internally
# result.stdout.fnmatch_lines([
#     'docker-db:',
#     '*--foo=DEST_FOO*Set the value for the fixture "bar".',
# ])
