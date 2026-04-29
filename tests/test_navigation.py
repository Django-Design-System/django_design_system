"""Tests for the gallery navigation tree builder."""

from unittest.mock import MagicMock, patch

import pytest

from dj_design_system.data import ComponentInfo, NavNode
from dj_design_system.services.navigation import (
    NodeType,
    _build_navigation,
    _discover_markdown_files,
    _effective_path_parts,
    build_navigation,
    build_search_index,
    to_display_label,
)
from tests.conftest import make_info


# ---------------------------------------------------------------------------
# to_display_label
# ---------------------------------------------------------------------------


class TestToDisplayLabel:
    """Test the sentence-case formatting function."""

    def test_single_word(self):
        assert to_display_label("icon") == "Icon"

    def test_snake_case(self):
        assert to_display_label("info_card") == "Info card"

    def test_kebab_case(self):
        assert to_display_label("hero-banner") == "Hero banner"

    def test_multiple_underscores(self):
        assert to_display_label("my_fancy_button") == "My fancy button"

    def test_already_capitalised(self):
        assert to_display_label("Icon") == "Icon"

    def test_all_caps(self):
        """Sentence case lowercases everything after the first character."""
        assert to_display_label("HTML") == "Html"

    def test_mixed_separators(self):
        assert to_display_label("my_fancy-widget") == "My fancy widget"

    def test_single_char(self):
        assert to_display_label("x") == "X"

    def test_empty_string(self):
        assert to_display_label("") == ""

    def test_component_verbose_name_override(self):
        """When a component kwarg has Meta.verbose_name, it takes precedence."""
        cls = type("Cls", (), {"Meta": type("Meta", (), {"verbose_name": "My widget"})})
        info = ComponentInfo(
            component_class=cls, name="widget", app_label="app", relative_path=""
        )
        assert to_display_label("widget", component=info) == "My widget"

    def test_component_without_verbose_name_falls_back(self):
        """Without Meta.verbose_name, falls back to slug formatting."""
        cls = type("Cls", (), {})
        info = ComponentInfo(
            component_class=cls, name="widget", app_label="app", relative_path=""
        )
        assert to_display_label("fancy_widget", component=info) == "Fancy widget"

    def test_app_label_unknown_falls_back(self):
        """Unknown app_label falls back to slug formatting."""
        assert (
            to_display_label("nonexistent_app", app_label="nonexistent_app")
            == "Nonexistent app"
        )


# ---------------------------------------------------------------------------
# _effective_path_parts
# ---------------------------------------------------------------------------


class TestEffectivePathParts:
    """Test the leaf-folder collapsing rule."""

    def test_no_path(self):
        """Root-level component has no path parts."""
        info = make_info("button", relative_path="")
        assert _effective_path_parts(info) == []

    def test_simple_path_no_collapse(self):
        """Component name differs from leaf folder."""
        info = make_info("badge", relative_path="elements")
        assert _effective_path_parts(info) == ["elements"]

    def test_leaf_folder_matches_name(self):
        """Leaf folder equals component name → collapse."""
        info = make_info("icon", relative_path="elements.icon")
        assert _effective_path_parts(info) == ["elements"]

    def test_deep_path_leaf_matches(self):
        """Deeply nested with matching leaf folder → collapse."""
        info = make_info("info_card", relative_path="cards.info_card")
        assert _effective_path_parts(info) == ["cards"]

    def test_deep_path_no_collapse(self):
        """Deeply nested, leaf folder differs → no collapse."""
        info = make_info("hero", relative_path="cards.layouts")
        assert _effective_path_parts(info) == ["cards", "layouts"]

    def test_single_segment_collapse(self):
        """Only one folder segment that matches → collapse to root."""
        info = make_info("callout", relative_path="callout")
        assert _effective_path_parts(info) == []


# ---------------------------------------------------------------------------
# build_navigation — structure (no markdown)
# ---------------------------------------------------------------------------


class TestBuildNavigationStructure:
    """Test tree structure from component data alone."""

    def test_single_root_component(self):
        """A single component with no path appears directly under the app."""
        components = [make_info("button")]
        tree = _build_navigation(components)

        assert len(tree) == 1
        app = tree[0]
        assert app.label == "Test app"
        assert app.node_type == NodeType.APP
        assert len(app.children) == 1
        assert app.children[0].label == "Button"
        assert app.children[0].node_type == NodeType.COMPONENT

    def test_component_in_subfolder(self):
        """Component in a subfolder creates a folder node."""
        components = [make_info("badge", relative_path="elements")]
        tree = _build_navigation(components)

        app = tree[0]
        assert len(app.children) == 1
        folder = app.children[0]
        assert folder.label == "Elements"
        assert folder.node_type == NodeType.FOLDER
        assert len(folder.children) == 1
        assert folder.children[0].label == "Badge"

    def test_leaf_folder_collapsing(self):
        """Leaf folder matching component name is collapsed."""
        components = [make_info("icon", relative_path="elements.icon")]
        tree = _build_navigation(components)

        app = tree[0]
        elements = app.children[0]
        assert elements.label == "Elements"
        # Icon should be directly under Elements, not Elements > Icon > Icon
        assert len(elements.children) == 1
        assert elements.children[0].label == "Icon"
        assert elements.children[0].is_component

    def test_root_level_collapsing(self):
        """Single-segment path matching name collapses to app root."""
        components = [make_info("callout", relative_path="callout")]
        tree = _build_navigation(components)

        app = tree[0]
        assert len(app.children) == 1
        assert app.children[0].label == "Callout"
        assert app.children[0].is_component

    def test_multiple_apps_sorted(self):
        """Multiple apps appear sorted alphabetically."""
        components = [
            make_info("zebra", app_label="zoo"),
            make_info("alpha", app_label="abc"),
        ]
        tree = _build_navigation(components)

        assert len(tree) == 2
        assert tree[0].label == "Abc"
        assert tree[1].label == "Zoo"

    def test_siblings_sorted(self):
        """Components at the same level are sorted by label."""
        components = [
            make_info("zebra", relative_path="elements"),
            make_info("alpha", relative_path="elements"),
        ]
        tree = _build_navigation(components)

        elements = tree[0].children[0]
        assert elements.children[0].label == "Alpha"
        assert elements.children[1].label == "Zebra"

    def test_folders_before_components(self):
        """Folders are sorted before components at the same level."""
        components = [
            make_info("button"),
            make_info("icon", relative_path="elements"),
        ]
        tree = _build_navigation(components)

        app = tree[0]
        # "Elements" folder before "Button" component
        assert app.children[0].label == "Elements"
        assert app.children[0].node_type == NodeType.FOLDER
        assert app.children[1].label == "Button"
        assert app.children[1].node_type == NodeType.COMPONENT

    def test_shared_folder_not_duplicated(self):
        """Two components in the same folder share one folder node."""
        components = [
            make_info("badge", relative_path="elements"),
            make_info("icon", relative_path="elements"),
        ]
        tree = _build_navigation(components)

        app = tree[0]
        assert len(app.children) == 1
        elements = app.children[0]
        assert elements.label == "Elements"
        assert len(elements.children) == 2

    def test_deep_nesting(self):
        """Components at different nesting depths produce correct tree."""
        components = [
            make_info("button"),
            make_info("hero", relative_path="cards.layouts"),
        ]
        tree = _build_navigation(components)

        app = tree[0]
        cards = [c for c in app.children if c.label == "Cards"][0]
        layouts = cards.children[0]
        assert layouts.label == "Layouts"
        assert layouts.children[0].label == "Hero"


# ---------------------------------------------------------------------------
# build_navigation — with markdown discovery
# ---------------------------------------------------------------------------


class TestBuildNavigationWithDocs:
    """Test markdown file discovery and insertion into the tree."""

    def test_index_md_attached_to_folder(self, nav_tree):
        """index.md in elements/ is attached to the Elements folder node."""
        app = nav_tree[0]
        elements = [c for c in app.children if c.slug == "elements"][0]
        assert elements.has_index_doc
        assert elements.index_doc_path.name == "index.md"

    def test_index_md_not_in_children(self, nav_tree):
        """index.md should not appear as a separate child node."""
        app = nav_tree[0]
        elements = [c for c in app.children if c.slug == "elements"][0]
        child_slugs = [c.slug for c in elements.children]
        assert "index" not in child_slugs

    def test_standalone_md_in_children(self, nav_tree):
        """accessibility.md in icon/ appears as a document child."""
        app = nav_tree[0]
        elements = [c for c in app.children if c.slug == "elements"][0]
        # Icon should be a child of elements (collapsed from elements/icon/)
        icon = [c for c in elements.children if c.slug == "icon"][0]
        doc_children = [c for c in icon.children if c.node_type == NodeType.DOCUMENT]
        assert len(doc_children) == 1
        assert doc_children[0].label == "Accessibility"
        assert doc_children[0].doc_path.name == "accessibility.md"

    def test_root_level_md(self, nav_tree):
        """design_guidelines.md at root level appears under the app node."""
        app = nav_tree[0]
        root_docs = [c for c in app.children if c.node_type == NodeType.DOCUMENT]
        assert len(root_docs) == 1
        assert root_docs[0].label == "Design guidelines"

    def test_documents_sorted_after_components(self, nav_tree):
        """Documents appear after folders and components in sort order."""
        app = nav_tree[0]
        type_sequence = [c.node_type for c in app.children]
        # Folders first, then components, then documents
        folder_indices = [
            i for i, t in enumerate(type_sequence) if t == NodeType.FOLDER
        ]
        component_indices = [
            i for i, t in enumerate(type_sequence) if t == NodeType.COMPONENT
        ]
        document_indices = [
            i for i, t in enumerate(type_sequence) if t == NodeType.DOCUMENT
        ]

        if folder_indices and component_indices:
            assert max(folder_indices) < min(component_indices)
        if component_indices and document_indices:
            assert max(component_indices) < min(document_indices)


# ---------------------------------------------------------------------------
# build_navigation — fake_app_nav integration
# ---------------------------------------------------------------------------


class TestFakeAppNavIntegration:
    """Integration tests using the full demo_nav fixture."""

    def test_app_label_display(self, nav_tree):
        assert nav_tree[0].label == "Demo Nav"

    def test_discovered_components(self, nav_registry):
        """Verify the registry found the expected components."""
        names = sorted(c.name for c in nav_registry.list_all())
        assert names == ["badge", "button", "divider", "icon", "info_card", "tooltip"]

    def test_icon_collapsed_into_elements(self, nav_tree_no_docs):
        """IconComponent at elements/icon/ collapses to Elements > Icon."""
        app = nav_tree_no_docs[0]
        elements = [c for c in app.children if c.slug == "elements"][0]
        icon = [c for c in elements.children if c.slug == "icon"][0]
        assert icon.is_component
        assert icon.label == "Icon"

    def test_info_card_collapsed_into_cards(self, nav_tree_no_docs):
        """InfoCardComponent at cards/info_card/ collapses to Cards > Info card."""
        app = nav_tree_no_docs[0]
        cards = [c for c in app.children if c.slug == "cards"][0]
        info_card = [c for c in cards.children if c.slug == "info_card"][0]
        assert info_card.is_component
        assert info_card.label == "Info card"

    def test_badge_no_collapse(self, nav_tree_no_docs):
        """BadgeComponent at elements/badge.py stays in Elements."""
        app = nav_tree_no_docs[0]
        elements = [c for c in app.children if c.slug == "elements"][0]
        badge = [c for c in elements.children if c.slug == "badge"][0]
        assert badge.is_component
        assert badge.label == "Badge"

    def test_button_at_root_with_verbose_name(self, nav_tree_no_docs):
        """ButtonComponent has Meta.verbose_name='Action button'."""
        app = nav_tree_no_docs[0]
        button = [c for c in app.children if c.slug == "button"][0]
        assert button.is_component
        assert button.label == "Action button"

    def test_icon_index_md_attached(self, nav_tree):
        """index.md in icon/ is attached to the Icon node (collapsed folder)."""
        app = nav_tree[0]
        elements = [c for c in app.children if c.slug == "elements"][0]
        icon = [c for c in elements.children if c.slug == "icon"][0]
        assert icon.has_index_doc

    def test_collapsed_component_no_duplicate_with_index_md(self, nav_tree):
        """A collapsed component with an index.md must not appear twice.

        Regression: icon/ contains component.py and index.md. The collapsing
        rule creates a component node under elements/; markdown discovery
        must reuse that node, not create a second 'icon' node.
        """
        app = nav_tree[0]
        elements = [c for c in app.children if c.slug == "elements"][0]
        icon_nodes = [c for c in elements.children if c.slug == "icon"]
        assert len(icon_nodes) == 1, f"Expected 1 'icon' node, found {len(icon_nodes)}"
        # The single node should be both a component and have index docs
        node = icon_nodes[0]
        assert node.is_component
        assert node.has_index_doc

    def test_full_tree_shape(self, nav_tree_no_docs):
        """Verify the overall tree shape matches expectations.

        Expected::

            FAKE_APP_NAV
            ├── Cards (folder)
            │   └── Info card (component)
            ├── Elements (folder)
            │   ├── Badge (component)
            │   └── Icon (component)
            ├── Generic (folder)
            │   ├── Divider (component)
            │   └── Tooltip (component)
            └── Action button (component, verbose_name)
        """
        app = nav_tree_no_docs[0]
        top_labels = [c.label for c in app.children]
        assert top_labels == ["Cards", "Elements", "Generic", "Action button"]

        cards = app.children[0]
        assert [c.label for c in cards.children] == ["Info card"]

        elements = app.children[1]
        assert sorted(c.label for c in elements.children) == ["Badge", "Icon"]

        generic = app.children[2]
        assert sorted(c.label for c in generic.children) == ["Divider", "Tooltip"]

    def test_tooltip_collapsed_into_generic(self, nav_tree_no_docs):
        """TooltipComponent at generic/tooltip/ collapses to Generic > Tooltip."""
        app = nav_tree_no_docs[0]
        generic = [c for c in app.children if c.slug == "generic"][0]
        tooltip = [c for c in generic.children if c.slug == "tooltip"][0]
        assert tooltip.is_component
        assert tooltip.label == "Tooltip"

    def test_divider_in_generic_no_collapse(self, nav_tree_no_docs):
        """DividerComponent at generic/divider.py stays in Generic."""
        app = nav_tree_no_docs[0]
        generic = [c for c in app.children if c.slug == "generic"][0]
        divider = [c for c in generic.children if c.slug == "divider"][0]
        assert divider.is_component
        assert divider.label == "Divider"


# ---------------------------------------------------------------------------
# verbose_name override
# ---------------------------------------------------------------------------


class TestVerboseNameOverride:
    """Test that Meta.verbose_name and AppConfig.verbose_name take precedence."""

    def test_component_with_verbose_name(self):
        """Meta.verbose_name overrides the auto-derived label."""
        cls = type(
            "TestCls", (), {"Meta": type("Meta", (), {"verbose_name": "My button"})}
        )
        info = ComponentInfo(
            component_class=cls, name="button", app_label="app", relative_path=""
        )
        tree = _build_navigation([info])
        assert tree[0].children[0].label == "My button"

    def test_component_without_verbose_name(self):
        """Without Meta.verbose_name, to_display_label is used."""
        cls = type("TestCls", (), {})
        info = ComponentInfo(
            component_class=cls, name="fancy_widget", app_label="app", relative_path=""
        )
        tree = _build_navigation([info])
        assert tree[0].children[0].label == "Fancy widget"

    def test_verbose_name_on_collapsed_component(self):
        """Meta.verbose_name applies even when the leaf folder is collapsed."""
        cls = type(
            "TestCls", (), {"Meta": type("Meta", (), {"verbose_name": "Custom icon"})}
        )
        info = ComponentInfo(
            component_class=cls,
            name="icon",
            app_label="app",
            relative_path="elements.icon",
        )
        tree = _build_navigation([info])
        elements = tree[0].children[0]
        icon = elements.children[0]
        assert icon.label == "Custom icon"
        assert icon.is_component

    def test_button_verbose_name_in_fixture(self, nav_tree_no_docs):
        """ButtonComponent in fake_app_nav has Meta.verbose_name='Action button'."""
        app = nav_tree_no_docs[0]
        button = [c for c in app.children if c.slug == "button"][0]
        assert button.label == "Action button"


# ---------------------------------------------------------------------------
# Subfolder stability
# ---------------------------------------------------------------------------


class TestSubfolderStability:
    """Tests for components inside nested subfolder structures.

    These specifically target the scenario where components live inside
    a grouping subfolder (like ``generic/``) to ensure the navigation
    tree is built correctly.
    """

    def test_multiple_components_in_subfolder(self):
        """Multiple components under a shared subfolder both appear."""
        components = [
            make_info("alpha", relative_path="group.alpha"),
            make_info("beta", relative_path="group.beta"),
        ]
        tree = _build_navigation(components)
        app = tree[0]
        group = [c for c in app.children if c.slug == "group"][0]
        labels = sorted(c.label for c in group.children)
        assert labels == ["Alpha", "Beta"]
        assert all(c.is_component for c in group.children)

    def test_component_in_deep_subfolder(self):
        """Component at three levels: a/b/c/ with collapsing."""
        components = [make_info("widget", relative_path="a.b.widget")]
        tree = _build_navigation(components)
        app = tree[0]
        a = app.children[0]
        assert a.slug == "a"
        b = a.children[0]
        assert b.slug == "b"
        assert b.children[0].label == "Widget"
        assert b.children[0].is_component

    def test_mixed_direct_and_collapsed_in_subfolder(self):
        """Mix of direct file and collapsed folder under the same parent."""
        components = [
            make_info("divider", relative_path="group"),
            make_info("tooltip", relative_path="group.tooltip"),
        ]
        tree = _build_navigation(components)
        app = tree[0]
        group = [c for c in app.children if c.slug == "group"][0]
        labels = sorted(c.label for c in group.children)
        assert labels == ["Divider", "Tooltip"]

    def test_subfolder_with_markdown(self, tmp_path):
        """Components in a subfolder with markdown files."""
        (tmp_path / "group").mkdir()
        (tmp_path / "group" / "notes.md").write_text("# Notes")
        components = [
            make_info("widget", app_label="app", relative_path="group.widget"),
        ]
        tree = _build_navigation(components, app_component_paths={"app": tmp_path})
        app = tree[0]
        group = [c for c in app.children if c.slug == "group"][0]
        child_labels = sorted(c.label for c in group.children)
        assert "Notes" in child_labels
        assert "Widget" in child_labels


# ---------------------------------------------------------------------------
# build_navigation — with tmp_path for isolated markdown tests
# ---------------------------------------------------------------------------


class TestMarkdownDiscoveryWithTmpPath:
    """Test markdown discovery using temporary directories for isolation."""

    def test_empty_directory(self):
        """No components, no paths → empty tree."""
        tree = _build_navigation([])
        assert tree == []

    def test_app_with_only_docs(self, tmp_path):
        """An app in app_component_paths with no components but with docs."""
        (tmp_path / "guide.md").write_text("# Guide")
        tree = _build_navigation(
            [],
            app_component_paths={"doc_only_app": tmp_path},
        )
        assert len(tree) == 1
        app = tree[0]
        assert app.label == "Doc only app"
        assert len(app.children) == 1
        assert app.children[0].label == "Guide"

    def test_case_insensitive_index_md(self, tmp_path):
        """INDEX.MD and Index.md are both treated as index files."""
        subdir = tmp_path / "section"
        subdir.mkdir()
        (subdir / "INDEX.MD").write_text("# Index")

        tree = _build_navigation(
            [make_info("widget", app_label="app", relative_path="section")],
            app_component_paths={"app": tmp_path},
        )
        app = tree[0]
        section = [c for c in app.children if c.slug == "section"][0]
        assert section.has_index_doc
        assert section.index_doc_path.name == "INDEX.MD"

    def test_nested_docs_without_components(self, tmp_path):
        """Markdown in a subfolder that has no component still appears."""
        subdir = tmp_path / "guides" / "getting_started"
        subdir.mkdir(parents=True)
        (subdir / "setup.md").write_text("# Setup")

        tree = _build_navigation(
            [],
            app_component_paths={"app": tmp_path},
        )
        app = tree[0]
        guides = [c for c in app.children if c.slug == "guides"][0]
        started = [c for c in guides.children if c.slug == "getting_started"][0]
        assert len(started.children) == 1
        assert started.children[0].label == "Setup"

    def test_collapsed_component_with_index_md_no_duplicate(self, tmp_path):
        """Collapsed component + index.md in same folder must produce one node.

        Simulates dw_design_system's icon/ which has component.py + index.md.
        The leaf-folder collapsing places the component under the parent, and
        markdown discovery must attach to that same node.
        """
        icon_dir = tmp_path / "icon"
        icon_dir.mkdir()
        (icon_dir / "index.md").write_text("# Icon docs")

        tree = _build_navigation(
            [make_info("icon", app_label="app", relative_path="icon")],
            app_component_paths={"app": tmp_path},
        )
        app = tree[0]
        icon_nodes = [c for c in app.children if c.slug == "icon"]
        assert len(icon_nodes) == 1
        node = icon_nodes[0]
        assert node.is_component
        assert node.has_index_doc


# ---------------------------------------------------------------------------
# Sort order setting
# ---------------------------------------------------------------------------


class TestNavSortOrder:
    """GALLERY_NAV_ORDER controls child ordering at each level."""

    @staticmethod
    def _build_mixed_tree(tmp_path):
        """Build a tree with a folder, a component, and a document at the same level."""
        sub = tmp_path / "zebra"
        sub.mkdir()
        (sub / "nested.md").write_text("# Nested")
        (tmp_path / "beta_guide.md").write_text("# Beta guide")

        infos = [make_info("alpha", app_label="app", relative_path="")]
        return _build_navigation(
            infos,
            app_component_paths={"app": tmp_path},
        )

    @staticmethod
    def _child_labels(tree):
        """Return labels of the app's direct children."""
        return [c.label for c in tree[0].children]

    def test_default_order_folders_components_documents(self, tmp_path):
        """Default: folders first, then components, then documents."""
        tree = self._build_mixed_tree(tmp_path)
        labels = self._child_labels(tree)
        assert labels == ["Zebra", "Alpha", "Beta guide"]

    @pytest.mark.parametrize(
        "order,expected",
        [
            (
                [NodeType.DOCUMENT, NodeType.COMPONENT, NodeType.FOLDER],
                ["Beta guide", "Alpha", "Zebra"],
            ),
            (
                [NodeType.COMPONENT, NodeType.FOLDER, NodeType.DOCUMENT],
                ["Alpha", "Zebra", "Beta guide"],
            ),
            (
                [NodeType.COMPONENT, NodeType.DOCUMENT, NodeType.FOLDER],
                ["Alpha", "Beta guide", "Zebra"],
            ),
            (
                [NodeType.DOCUMENT, NodeType.FOLDER, NodeType.COMPONENT],
                ["Beta guide", "Zebra", "Alpha"],
            ),
            (
                [NodeType.FOLDER, NodeType.DOCUMENT, NodeType.COMPONENT],
                ["Zebra", "Beta guide", "Alpha"],
            ),
        ],
    )
    def test_custom_order(self, tmp_path, settings, order, expected):
        settings.dj_design_system = {"GALLERY_NAV_ORDER": order}
        tree = self._build_mixed_tree(tmp_path)
        labels = self._child_labels(tree)
        assert labels == expected

    def test_alphabetical_ignores_type(self, tmp_path, settings):
        settings.dj_design_system = {"GALLERY_NAV_ORDER": "alphabetical"}
        tree = self._build_mixed_tree(tmp_path)
        labels = self._child_labels(tree)
        assert labels == ["Alpha", "Beta guide", "Zebra"]


# ---------------------------------------------------------------------------
# NavNode validation
# ---------------------------------------------------------------------------


class TestNavNodeValidation:
    """Ensure NavNode rejects inconsistent node_type / data field combinations."""

    def test_component_without_info_rejected(self):
        with pytest.raises(ValueError, match="COMPONENT nodes must have"):
            NavNode(label="x", slug="x", node_type=NodeType.COMPONENT)

    def test_folder_with_component_info_rejected(self):
        info = make_info("btn")
        with pytest.raises(ValueError, match="must not carry a ComponentInfo"):
            NavNode(label="x", slug="x", node_type=NodeType.FOLDER, component=info)

    def test_document_without_doc_path_rejected(self):
        with pytest.raises(ValueError, match="DOCUMENT nodes must have"):
            NavNode(label="x", slug="x", node_type=NodeType.DOCUMENT)

    def test_folder_with_doc_path_rejected(self):
        from pathlib import Path

        with pytest.raises(ValueError, match="must not carry a doc_path"):
            NavNode(
                label="x",
                slug="x",
                node_type=NodeType.FOLDER,
                doc_path=Path("readme.md"),
            )

    def test_valid_component_accepted(self):
        info = make_info("btn")
        node = NavNode(
            label="Btn", slug="btn", node_type=NodeType.COMPONENT, component=info
        )
        assert node.is_component

    def test_valid_document_accepted(self):
        from pathlib import Path

        node = NavNode(
            label="Guide",
            slug="guide",
            node_type=NodeType.DOCUMENT,
            doc_path=Path("guide.md"),
        )
        assert node.is_document

    def test_valid_folder_accepted(self):
        node = NavNode(label="Cards", slug="cards", node_type=NodeType.FOLDER)
        assert not node.is_component
        assert not node.is_document

    def test_upgrade_to_component(self):
        info = make_info("icon")
        node = NavNode(label="Icon", slug="icon", node_type=NodeType.FOLDER)
        node.upgrade_to_component(info, "Icon")
        assert node.is_component
        assert node.component is info


# ---------------------------------------------------------------------------
# Public build_navigation() — delegates to registry
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPublicBuildNavigation:
    """Verify build_navigation() (no args) reads from the global registry."""

    def test_returns_list_of_app_nodes(self):
        """build_navigation() returns a list where every node is an APP."""
        tree = build_navigation()
        assert isinstance(tree, list)
        for node in tree:
            assert node.node_type == NodeType.APP

    def test_returns_empty_list_with_no_registered_apps(self):
        """build_navigation() returns [] when no component apps are registered."""
        with (
            patch(
                "dj_design_system.services.registry.component_registry.list_all",
                return_value=[],
            ),
            patch(
                "dj_design_system.services.navigation.get_app_component_paths",
                return_value={},
            ),
        ):
            tree = build_navigation()
        assert tree == []


# ---------------------------------------------------------------------------
# Additional coverage: navigation edge cases
# ---------------------------------------------------------------------------


class TestNavigationEdgeCases:
    """Targeted tests for uncovered branches in navigation service."""

    def test_to_display_label_app_with_verbose_name(self):
        """AppConfig subclass with verbose_name defined in class dict."""
        from unittest.mock import patch

        cfg = MagicMock()
        type(cfg).__dict__  # ensure it's a real class
        # Simulate an AppConfig that has verbose_name defined on the class itself
        mock_cfg_class = type("MockAppConfig", (), {"verbose_name": "My Cool App"})
        mock_instance = mock_cfg_class()

        with patch(
            "django.apps.apps.get_app_config",
            return_value=mock_instance,
        ):
            result = to_display_label("my_app", app_label="my_app")
        assert result == "My Cool App"

    def test_folder_upgraded_to_component(self):
        """When a collapsed component's raw path already exists as a folder, it gets upgraded."""
        # Add "other" component that creates elements/icon as a folder
        # (because "icon" != "other", no collapsing happens, elements/icon is a folder)
        components = [
            make_info("other", app_label="app", relative_path="elements.icon"),
            make_info("icon", app_label="app", relative_path="elements.icon"),
        ]
        tree = _build_navigation(components)
        app = tree[0]
        elements = [c for c in app.children if c.slug == "elements"][0]
        # "icon" should have upgraded the elements/icon folder to a component
        icon_node = [c for c in elements.children if c.slug == "icon"][0]
        assert icon_node.is_component
        assert icon_node.component.name == "icon"

    def test_discover_markdown_non_dir_returns_empty(self, tmp_path):
        """_discover_markdown_files returns empty list for non-existent path."""

        result = _discover_markdown_files(tmp_path / "does_not_exist")
        assert result == []

    def test_build_navigation_components_none_with_explicit_empty_paths(self):
        """When components=None but app_component_paths={}, uses registry but skips path discovery."""
        tree = _build_navigation(components=None, app_component_paths={})
        # Should return a tree (possibly with apps from global registry)
        assert isinstance(tree, list)

    def test_search_index_oserror_on_index_doc(self, tmp_path):
        """OSError reading an index doc is silently swallowed."""

        from dj_design_system.data import NavNode
        from dj_design_system.services.navigation import (
            NodeType,
        )

        # Build a tree with a folder whose index_doc_path doesn't actually exist
        missing = tmp_path / "missing.md"
        folder = NavNode(label="Things", slug="things", node_type=NodeType.FOLDER)
        folder._app_label = "app"
        folder._path_parts = ["things"]
        folder.index_doc_path = missing  # points to non-existent file

        app = NavNode(label="App", slug="app", node_type=NodeType.APP)
        app._app_label = "app"
        app._path_parts = []
        app.children = [folder]

        # Should not raise, should silently skip the unreadable index doc
        index = build_search_index([app])
        things_entry = next(e for e in index if e["label"] == "Things")
        assert things_entry["content"] == ""

    def test_search_index_oserror_on_doc_path(self, tmp_path):
        """OSError reading a document's content is silently swallowed."""

        from dj_design_system.data import NavNode
        from dj_design_system.services.navigation import (
            NodeType,
        )

        missing = tmp_path / "missing.md"
        doc = NavNode(
            label="Guide",
            slug="guide",
            node_type=NodeType.DOCUMENT,
            doc_path=missing,
        )
        doc._app_label = "app"
        doc._path_parts = ["guide"]

        app = NavNode(label="App", slug="app", node_type=NodeType.APP)
        app._app_label = "app"
        app._path_parts = []
        app.children = [doc]

        index = build_search_index([app])
        guide_entry = next(e for e in index if e["label"] == "Guide")
        assert guide_entry["content"] == ""
