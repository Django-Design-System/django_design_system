"""Shared fixtures for e2e (Playwright) tests."""

import os

import pytest


# pytest-playwright runs an async event loop which triggers Django's
# SynchronousOnlyOperation check during DB setup. Allow it explicitly.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")


@pytest.fixture(scope="session")
def base_url(live_server):
    """Return the live server base URL for Playwright tests."""
    return live_server.url


@pytest.fixture()
def gallery_url(live_server):
    """URL of the gallery index."""
    return f"{live_server.url}/dds/"
