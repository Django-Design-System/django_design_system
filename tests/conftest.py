"""Shared fixtures for dj_design_system tests."""

import pkgutil
from importlib import import_module
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

from dj_design_system.data import ComponentInfo
from dj_design_system.services.component import derive_relative_path
from dj_design_system.services.navigation import _build_navigation
from dj_design_system.services.registry import ComponentRegistry


User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEMO_NAV = "example_project.demo_nav"
DEMO_NAV_COMPONENTS = (
    Path(__file__).parent.parent / "example_project" / "demo_nav" / "components"
)


def discover_app_into_registry(
    reg: ComponentRegistry, app_name: str, app_label: str
) -> None:
    """Simulate autodiscovery for a single app into an existing registry."""
    module_path = f"{app_name}.components"
    module = import_module(module_path)
    reg._discover_module(module, app_label, relative_path="")

    if hasattr(module, "__path__"):
        for _importer, modname, _ispkg in pkgutil.walk_packages(
            module.__path__, prefix=module.__name__ + "."
        ):
            submodule = import_module(modname)
            relative_path = derive_relative_path(modname, module_path)
            reg._discover_module(submodule, app_label, relative_path)


def make_info(
    name: str,
    app_label: str = "test_app",
    relative_path: str = "",
) -> ComponentInfo:
    """Create a minimal ComponentInfo for testing (no real class needed)."""
    return ComponentInfo(
        component_class=type(f"{name}_cls", (), {}),
        name=name,
        app_label=app_label,
        relative_path=relative_path,
    )


# ---------------------------------------------------------------------------
# Registry fixtures
#
# Fixtures return only the registry — component classes are imported at the
# top of each test file, avoiding brittle positional tuple unpacking.
# ---------------------------------------------------------------------------


@pytest.fixture()
def registry_with_demo_components():
    """Create a fresh ComponentRegistry with demo_components only."""
    reg = ComponentRegistry()
    discover_app_into_registry(
        reg, "example_project.demo_components", "demo_components"
    )
    return reg


@pytest.fixture()
def registry_with_two_apps(registry_with_demo_components):
    """Extend the demo_components registry with demo_extra to test duplicate names."""
    reg = registry_with_demo_components
    discover_app_into_registry(reg, "example_project.demo_extra", "demo_extra")
    return reg


@pytest.fixture()
def registry_with_demo_single():
    """Create a registry with the single-file components.py app."""
    reg = ComponentRegistry()
    discover_app_into_registry(reg, "example_project.demo_single", "demo_single")
    return reg


# ---------------------------------------------------------------------------
# Navigation fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def nav_registry():
    """Registry loaded with demo_nav components."""
    reg = ComponentRegistry()
    discover_app_into_registry(reg, DEMO_NAV, "demo_nav")
    return reg


@pytest.fixture()
def nav_tree(nav_registry):
    """Full navigation tree for demo_nav including markdown discovery."""
    return _build_navigation(
        nav_registry.list_all(),
        app_component_paths={"demo_nav": DEMO_NAV_COMPONENTS},
    )


@pytest.fixture()
def nav_tree_no_docs(nav_registry):
    """Navigation tree for demo_nav without markdown discovery."""
    return _build_navigation(nav_registry.list_all())


# ---------------------------------------------------------------------------
# View fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def user_client(client):
    """A test client logged in as a user with a profile (needed for 404 pages)."""
    user = User.objects.create_user(username="testgallery")
    client.force_login(user)
    return client


# ---------------------------------------------------------------------------
# Canvas fixtures
# ---------------------------------------------------------------------------
