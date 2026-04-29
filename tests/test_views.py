"""Tests for the gallery views."""

import pytest
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from dj_design_system.services.navigation import (
    build_breadcrumbs,
    find_node,
)
from dj_design_system.views import get_base_context


def _get_nav_tree():
    """Build and return the current navigation tree."""
    return get_base_context()["nav_tree"]


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------


class TestURLPatterns:
    """Test that URL patterns resolve correctly."""

    def test_gallery_index(self):
        assert reverse("gallery") == "/dds/"

    def test_gallery_node_root(self):
        url = reverse("gallery-node-root", kwargs={"app_label": "myapp"})
        assert url == "/dds/myapp/"

    def test_gallery_node_nested(self):
        url = reverse(
            "gallery-node",
            kwargs={"app_label": "myapp", "path": "elements/cards"},
        )
        assert url == "/dds/myapp/elements/cards/"

    def test_gallery_node_component(self):
        url = reverse(
            "gallery-node",
            kwargs={"app_label": "myapp", "path": "elements/icon"},
        )
        assert url == "/dds/myapp/elements/icon/"

    def test_gallery_node_document(self):
        url = reverse(
            "gallery-node",
            kwargs={"app_label": "myapp", "path": "elements/icon/accessibility"},
        )
        assert url == "/dds/myapp/elements/icon/accessibility/"


# ---------------------------------------------------------------------------
# build_breadcrumbs
# ---------------------------------------------------------------------------


class TestBuildBreadcrumbs:
    """Test the breadcrumb builder."""

    def test_simple_breadcrumbs(self):
        crumbs = build_breadcrumbs("myapp", [], "Button")
        assert len(crumbs) == 3
        assert crumbs[0]["label"] == "Gallery"
        assert crumbs[1]["label"] == "Myapp"
        assert crumbs[2]["label"] == "Button"
        assert "url" not in crumbs[2]

    def test_nested_breadcrumbs(self):
        crumbs = build_breadcrumbs("myapp", ["elements", "cards"], "Icon")
        assert len(crumbs) == 5
        assert crumbs[0]["label"] == "Gallery"
        assert crumbs[1]["label"] == "Myapp"
        assert crumbs[2]["label"] == "Elements"
        assert crumbs[3]["label"] == "Cards"
        assert crumbs[4]["label"] == "Icon"
        # All except last should have urls
        for crumb in crumbs[:-1]:
            assert "url" in crumb


# ---------------------------------------------------------------------------
# find_node
# ---------------------------------------------------------------------------


class TestFindNode:
    """Test node lookup in the navigation tree."""

    def test_finds_app_node(self):
        nav_tree = _get_nav_tree()
        if not nav_tree:
            pytest.skip("No apps with components registered")
        app = nav_tree[0]
        found = find_node(nav_tree, app.slug, [])
        assert found is app

    def test_returns_none_for_unknown_app(self):
        nav_tree = _get_nav_tree()
        assert find_node(nav_tree, "nonexistent_app_xyz", []) is None

    def test_returns_none_for_unknown_child(self):
        nav_tree = _get_nav_tree()
        if not nav_tree:
            pytest.skip("No apps with components registered")
        app = nav_tree[0]
        assert find_node(nav_tree, app.slug, ["nonexistent_child"]) is None


# ---------------------------------------------------------------------------
# View integration tests (via Django test client)
# ---------------------------------------------------------------------------


class TestGalleryIndexView:
    """Test the gallery index page."""

    def test_index_returns_200(self, client):
        response = client.get(reverse("gallery"))
        assert response.status_code == 200

    def test_index_contains_design_system_name(self, client):
        response = client.get(reverse("gallery"))
        assert (
            b"Design System" in response.content or b"design_system" in response.content
        )

    def test_index_has_nav_tree(self, client):
        response = client.get(reverse("gallery"))
        assert "nav_tree" in response.context


class TestGalleryComponentView:
    """Test the component detail page."""

    def test_component_returns_200(self, client):
        """Test with a known component from dw_design_system."""
        nav_tree = _get_nav_tree()
        # Find the first component
        component = None
        for app in nav_tree:
            for child in app.children:
                if child.is_component:
                    component = child
                    break
                for grandchild in getattr(child, "children", []):
                    if grandchild.is_component:
                        component = grandchild
                        break
                if component:
                    break
            if component:
                break

        if component is None:
            pytest.skip("No components registered")

        response = client.get(component.url)
        assert response.status_code == 200

    def test_unknown_component_returns_404(self, user_client):
        url = reverse(
            "gallery-node",
            kwargs={"app_label": "dw_design_system", "path": "nonexistent"},
        )
        response = user_client.get(url)
        assert response.status_code == 404


class TestGalleryFolderView:
    """Test the folder view."""

    def test_unknown_app_returns_404(self, user_client):
        url = reverse(
            "gallery-node-root",
            kwargs={"app_label": "nonexistent_app"},
        )
        response = user_client.get(url)
        assert response.status_code == 404

    def test_app_root_returns_200(self, client):
        nav_tree = _get_nav_tree()
        if not nav_tree:
            pytest.skip("No apps with components registered")
        app = nav_tree[0]
        response = client.get(app.url)
        assert response.status_code == 200


class TestGalleryDocumentView:
    """Test the standalone document view."""

    def test_unknown_doc_returns_404(self, user_client):
        url = reverse(
            "gallery-node",
            kwargs={"app_label": "dw_design_system", "path": "nonexistent"},
        )
        response = user_client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Form integration tests
# ---------------------------------------------------------------------------


def _find_component_with_params(nav_tree):
    """Return the first component node that has at least one parameter, or None."""
    for node in _collect_all_nodes(nav_tree):
        if node.is_component and node.component.component_class.get_params():
            return node
    return None


def _find_block_component_with_params(nav_tree):
    """Return the first block component node that has at least one parameter."""
    from dj_design_system.components import BlockComponent

    for node in _collect_all_nodes(nav_tree):
        if not node.is_component:
            continue

        component_class = node.component.component_class
        if issubclass(component_class, BlockComponent) and component_class.get_params():
            return node

    return None


class TestGalleryComponentFormIntegration:
    """Test that the parameter form is wired up correctly in the component view."""

    def test_param_rows_in_context(self, client):
        """Component pages should include param_rows in the template context."""
        nav_tree = _get_nav_tree()
        component = _find_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No components with params registered")

        response = client.get(component.url)
        assert response.status_code == 200
        assert "param_rows" in response.context

    def test_form_in_context(self, client):
        """Component pages should include a form object in the template context."""
        nav_tree = _get_nav_tree()
        component = _find_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No components with params registered")

        response = client.get(component.url)
        assert response.status_code == 200
        assert "form" in response.context

    def test_form_is_unbound_without_get_params(self, client):
        """Form should be unbound when no param GET keys are present."""
        nav_tree = _get_nav_tree()
        component = _find_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No components with params registered")

        response = client.get(component.url)
        assert response.status_code == 200
        assert not response.context["form"].is_bound

    def test_form_is_bound_with_param_get_keys(self, client):
        """Form should be bound when at least one param key appears in GET."""
        nav_tree = _get_nav_tree()
        component = _find_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No components with params registered")

        params = component.component.component_class.get_params()
        first_param_name = next(iter(params))

        response = client.get(component.url, {first_param_name: "test"})
        assert response.status_code == 200
        assert response.context["form"].is_bound

    def test_param_rows_length_matches_params(self, client):
        """param_rows should contain one entry per component parameter.

        For BlockComponent subclasses an extra 'content' row is prepended.
        """
        from dj_design_system.components import BlockComponent

        nav_tree = _get_nav_tree()
        component = _find_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No components with params registered")

        component_class = component.component.component_class
        params = component_class.get_params()
        extra = 1 if issubclass(component_class, BlockComponent) else 0
        response = client.get(component.url)
        assert len(response.context["param_rows"]) == len(params) + extra

    def test_param_rows_contain_required_keys(self, client):
        """Each entry in param_rows should have 'name', 'spec', and 'field' keys."""
        nav_tree = _get_nav_tree()
        component = _find_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No components with params registered")

        response = client.get(component.url)
        for row in response.context["param_rows"]:
            assert "name" in row
            assert "spec" in row
            assert "field" in row

    def test_page_renders_with_valid_get_param(self, client):
        """A component page should return 200 when valid param data is supplied via GET."""
        nav_tree = _get_nav_tree()
        component = _find_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No components with params registered")

        params = component.component.component_class.get_params()
        first_param_name, first_spec = next(iter(params.items()))

        # Determine a value compatible with the param type.
        from dj_design_system.parameters import BoolParam, StrParam

        if isinstance(first_spec, BoolParam):
            get_data = {first_param_name: "True"}
        elif isinstance(first_spec, StrParam) and first_spec.choices:
            get_data = {first_param_name: str(first_spec.choices[0])}
        elif isinstance(first_spec, StrParam):
            get_data = {first_param_name: "hello"}
        else:
            pytest.skip("First param is a ModelParam — skip value injection")

        response = client.get(component.url, get_data)
        assert response.status_code == 200

    def test_form_auto_submit_js_in_rendered_html(self, client):
        """The rendered page should contain the htmx-wired parameter form."""
        nav_tree = _get_nav_tree()
        component = _find_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No components with params registered")

        response = client.get(component.url)
        assert response.status_code == 200
        assert b"gallery-params-form" in response.content
        assert b"hx-get" in response.content

    def test_htmx_partial_returns_fragment(self, client):
        """An htmx request returns only the sandbox fragment, not the full page."""
        nav_tree = _get_nav_tree()
        component = _find_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No components with params registered")

        response = client.get(component.url, HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        # Fragment should contain the canvas and form but NOT the full page shell.
        assert b"gallery-sandbox__canvas" in response.content
        assert b"<html" not in response.content

    def test_block_content_updates_current_usage(self, client):
        """Block content entered in the form should be reflected in current usage."""
        nav_tree = _get_nav_tree()
        component = _find_block_component_with_params(nav_tree)
        if component is None:
            pytest.skip("No block components with params registered")

        response = client.get(component.url, {"content": "Updated body"})
        assert response.status_code == 200
        assert response.context["current_signature"] is not None
        assert "Updated body" in response.context["current_signature"].minimal


# ---------------------------------------------------------------------------
# Smoke test: walk the entire nav tree and hit every URL
# ---------------------------------------------------------------------------


def _collect_all_nodes(nodes):
    """Recursively collect all NavNode objects from a tree."""
    result = []
    for node in nodes:
        result.append(node)
        if node.children:
            result.extend(_collect_all_nodes(node.children))
    return result


class TestSmokeAllPages:
    """Walk the entire navigation tree and assert every page renders."""

    def test_every_nav_node_returns_200(self, client):
        """Every node in the nav tree should have a resolvable URL that returns 200."""
        nav_tree = _get_nav_tree()
        all_nodes = _collect_all_nodes(nav_tree)

        if not all_nodes:
            pytest.skip("No navigation nodes registered")

        errors = []
        for node in all_nodes:
            url = node.url
            response = client.get(url)
            if response.status_code != 200:
                errors.append(f"{url} -> {response.status_code} ({node.label})")

        assert errors == [], "Pages that failed:\n" + "\n".join(errors)

    def test_index_page_renders(self, client):
        response = client.get(reverse("gallery"))
        assert response.status_code == 200
        assert b"gallery-nav" in response.content

    def test_breadcrumbs_present_on_component_page(self, client):
        """Component pages should have breadcrumb links."""
        nav_tree = _get_nav_tree()
        component = None
        for node in _collect_all_nodes(nav_tree):
            if node.is_component:
                component = node
                break

        if component is None:
            pytest.skip("No components registered")

        response = client.get(component.url)
        assert response.status_code == 200
        assert b"gallery-breadcrumb__sep" in response.content
        assert b"Gallery" in response.content

    def test_nav_tree_rendered_in_sidebar(self, client):
        """The nav tree should be rendered in the sidebar."""
        nav_tree = _get_nav_tree()
        if not nav_tree:
            pytest.skip("No apps registered")

        response = client.get(reverse("gallery"))
        # Check the first app label appears in the response
        first_app = nav_tree[0]
        assert first_app.label.encode() in response.content

    def test_active_state_on_component_page(self, client):
        """The active component should be highlighted in the sidebar."""
        nav_tree = _get_nav_tree()
        component = None
        for node in _collect_all_nodes(nav_tree):
            if node.is_component:
                component = node
                break

        if component is None:
            pytest.skip("No components registered")

        response = client.get(component.url)
        assert response.status_code == 200
        assert b"gallery-nav__link--active" in response.content


# ---------------------------------------------------------------------------
# Toolbar buttons on component pages
# ---------------------------------------------------------------------------


class TestToolbarButtons:
    """Test that all sandbox toolbar buttons render on component pages."""

    @pytest.fixture()
    def component_response(self, client):
        nav_tree = _get_nav_tree()
        for node in _collect_all_nodes(nav_tree):
            if node.is_component:
                return client.get(node.url)
        pytest.skip("No components registered")

    def test_outline_toggle(self, component_response):
        assert b"gallery-sandbox-toolbar__outline-toggle" in component_response.content

    def test_measure_toggle(self, component_response):
        assert b"gallery-sandbox-toolbar__measure-toggle" in component_response.content

    def test_rtl_toggle(self, component_response):
        assert b"gallery-sandbox-toolbar__rtl-toggle" in component_response.content

    def test_viewport_toggle(self, component_response):
        assert b"gallery-sandbox-toolbar__viewport-toggle" in component_response.content

    def test_zoom_toggle(self, component_response):
        assert b"gallery-sandbox-toolbar__zoom-toggle" in component_response.content

    def test_bg_toggle(self, component_response):
        assert b"gallery-sandbox-toolbar__bg-toggle" in component_response.content

    def test_measure_script_data_attribute(self, component_response):
        assert b"data-measure-script" in component_response.content

    def test_viewport_presets(self, component_response):
        content = component_response.content
        assert b'data-viewport="320"' in content
        assert b'data-viewport="1920"' in content
        assert b'data-viewport="2560"' in content
        assert b'data-viewport="responsive"' in content


# ---------------------------------------------------------------------------
# gallery_access_required — auth paths
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGalleryAccessRequired:
    """Test the gallery_access_required decorator when gallery is not public."""

    @override_settings(dj_design_system={"GALLERY_IS_PUBLIC": False})
    def test_unauthenticated_redirects(self, client):
        response = client.get(reverse("gallery"))
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    @override_settings(dj_design_system={"GALLERY_IS_PUBLIC": False})
    def test_authenticated_without_permission_is_forbidden(
        self, client, django_user_model
    ):
        user = django_user_model.objects.create_user(username="unprivileged")
        client.force_login(user)
        response = client.get(reverse("gallery"))
        assert response.status_code == 403

    @override_settings(dj_design_system={"GALLERY_IS_PUBLIC": False})
    def test_authenticated_with_permission_allowed(self, client, django_user_model):
        user = django_user_model.objects.create_user(username="privileged")
        perm = Permission.objects.get(codename="can_view_gallery")
        user.user_permissions.add(perm)
        client.force_login(user)
        response = client.get(reverse("gallery"))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# _render_markdown — codehilite disabled branch
# ---------------------------------------------------------------------------


class TestRenderMarkdown:
    """Test _render_markdown internals."""

    @override_settings(dj_design_system={"GALLERY_CODEHILITE_STYLE": ""})
    def test_no_codehilite_when_style_empty(self, client):
        """A document page renders without codehilite when the style is empty."""

        nav_tree = get_base_context()["nav_tree"]
        demo_nav_app = next((a for a in nav_tree if a.slug == "demo_nav"), None)
        if demo_nav_app is None:
            pytest.skip("demo_nav not in nav tree")

        # Find the accessibility document node
        def _find_doc(node):
            if node.is_document:
                return node
            for child in node.children:
                found = _find_doc(child)
                if found:
                    return found
            return None

        doc_node = _find_doc(demo_nav_app)
        if doc_node is None:
            pytest.skip("No document node in demo_nav")

        response = client.get(doc_node.url)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# _canvas_html_attrs — non-empty attrs branch
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCanvasHtmlAttrs:
    """Test that GALLERY_CANVAS_HTML_ATTRS is reflected in the canvas iframe."""

    @override_settings(
        dj_design_system={
            "GALLERY_CANVAS_HTML_ATTRS": {
                "html": {"class": "govuk-template"},
                "body": {"class": "govuk-template__body"},
            }
        }
    )
    def test_html_attrs_in_canvas_response(self, client):
        from django.urls import reverse

        url = reverse("gallery-canvas-iframe")
        response = client.get(url, {"component": "rich_button", "label": "Test"})
        content = response.content.decode()
        assert "govuk-template" in content
