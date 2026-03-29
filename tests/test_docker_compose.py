import os
import shutil

import pytest


@pytest.fixture()
def compose_file(tmp_path: os.PathLike[str]) -> str:
    """Copy the test docker-compose.yml to a temp directory and return its path."""
    src = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
    dst = os.path.join(str(tmp_path), "docker-compose.yml")
    shutil.copy(src, dst)
    return dst


@pytest.mark.skipif(
    not shutil.which("docker"), reason="Docker is not installed"
)
def test_docker_compose_options_from_testdir(
    testdir: pytest.Testdir, compose_file: str
) -> None:
    """Test that the docker_compose fixture can be configured and invoked."""
    testdir.makepyfile(
        """
        def test_compose(docker_compose):
            # The fixture yields None; just verify it was invoked without error
            pass
        """
    )

    result = testdir.runpytest(
        f"--docker-compose-file={compose_file}",
        "--docker-compose-project-name=pytest-docker-compose-test",
        "-v",
    )
    result.assert_outcomes(passed=1)
