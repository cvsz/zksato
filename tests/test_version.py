import tomllib
from pathlib import Path

import zksato


def test_runtime_version_matches_project_metadata() -> None:
    with Path("pyproject.toml").open("rb") as handle:
        project_version = tomllib.load(handle)["project"]["version"]
    assert zksato.__version__ == project_version
