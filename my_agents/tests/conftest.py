"""Pytest conftest for my_agents tests.

Overrides the VCR cassette_dir fixture from the root conftest
since my_agents tests don't use VCR cassettes.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def vcr_cassette_dir(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Return a temporary cassette directory for my_agents tests."""
    return str(tmp_path_factory.mktemp("cassettes"))
