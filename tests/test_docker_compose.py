import subprocess

import pytest


def is_container_running(service_name: str, project_name: str) -> bool:
    """Check if a container for the given service is running."""
    import shutil

    # Determine which Docker Compose command format to use
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
            "-p",
            project_name,
            "ps",
            "--services",
            "--filter",
            "status=running",
        ]
    else:
        # Fall back to old-style docker-compose command
        cmd = [
            "docker-compose",
            "-p",
            project_name,
            "ps",
            "--services",
            "--filter",
            "status=running",
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    return service_name in result.stdout


# @pytest.mark.usefixtures("docker_compose")
def test_docker_compose(testdir: pytest.Testdir, request: pytest.FixtureRequest):
    """Test that a user provided docker-compose.yml brings up the services in a pytest test and then after the test finishes checks that the containers are down"""
    testdir.makepyfile(
        """
        def test_compose(docker_compose):
            # Check that the docker-compose fixture is not None
            assert docker_compose is not None

            # Check that the service is running
            assert docker_compose.is_running("test_service")

            # Check that the service is healthy
            assert docker_compose.is_healthy("test_service")
        """
    )

    testdir.runpytest(
        "--docker-compose-file=docker-compose.yml",
        "--docker-compose-project-name=pytest-docker-compose-test",
        "-v",
    )

    project_name = "pytest-docker-compose-test"

    # Hardcode service name since we know what's in our test docker-compose.yml
    service_list = ["test_service"]

    for service in service_list:
        assert not is_container_running(
            service, project_name
        ), f"Service {service} is not running"
