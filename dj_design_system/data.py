from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Type

from dj_design_system.types import NodeType, TagType


class InvalidTagType(Exception):
    """Raised when a component class is not a TagComponent or BlockComponent."""


BLOCK_CONTENT_PLACEHOLDER = "Sample content"
"""Default content used for block component previews in the canvas and code examples."""


@dataclass(frozen=True)
class CanvasSpec:
    """Specification for rendering a single component inside a canvas.

    Holds the component name, keyword parameters, and any positional arguments
    needed to instantiate and render the component.
    """

    component_name: str
    params: dict[str, Any] = field(default_factory=dict)
    positional_args: tuple[Any, ...] = field(default_factory=tuple)


@dataclass
class ComponentMedia:
    """
    Holds the static URL paths for CSS and JS files required by a component.

    Paths are Django static URL strings (e.g.
    ``"myapp/components/icon/icon.css"``), with no leading slash.  They
    are served by ``ComponentsStaticFinder`` and can be passed directly to
    ``{% static %}`` or used in ``<link>`` / ``<script>`` tags.
    """

    css: list[str] = field(default_factory=list)
    js: list[str] = field(default_factory=list)

    def merge(self, other: "ComponentMedia") -> "ComponentMedia":
        """Return a new ``ComponentMedia`` combining *self* and *other*.

        ``self`` entries appear first; duplicates are removed while
        preserving the original order of first appearance.
        """
        combined_css = list(dict.fromkeys(self.css + other.css))
        combined_js = list(dict.fromkeys(self.js + other.js))
        return ComponentMedia(css=combined_css, js=combined_js)

    def __bool__(self) -> bool:
        return bool(self.css or self.js)


@dataclass(frozen=True)
class ComponentInfo:
    """Metadata about a discovered component."""

    component_class: Type
    name: str
    app_label: str
    relative_path: str

    @property
    def qualified_name(self) -> str:
        """Return a fully qualified tag name: ``app_label__path__name``.

        Parts are joined with ``__``. If ``relative_path`` is empty,
        the result is ``{app_label}__{name}``.

        Examples::

            "fake_app__button"
            "fake_app__cards__info_card"
            "fake_app__cards__layouts__hero"
        """
        parts = [self.app_label]
        if self.relative_path:
            parts.extend(self.relative_path.split("."))
        parts.append(self.name)
        return "__".join(parts)

    @property
    def media(self) -> ComponentMedia:
        """Return the CSS and JS static URL paths required by this component.

        Both sources below are always consulted and merged together.  Explicit
        entries appear first; auto-discovered files are appended (duplicates
        removed):

        1. **Explicit ``Media`` class**: If any class in the component's MRO
           defines an inner ``Media`` class (like Django form widgets), those
           entries are collected.  Media from parent classes is merged before
           child additions, with duplicates removed.

        2. **Auto-discovery**: The registry looks for ``{name}.css`` and
           ``{name}.js`` files in the same directory as the component's Python
           source file.  Files that do not exist on disk are silently omitted.
        """
        from dj_design_system.services.media import build_static_url, get_own_media

        # Collect any explicit Media classes from the MRO.
        mro_media = [
            m
            for cls in self.component_class.__mro__
            if (m := get_own_media(cls)) is not None
        ]

        if mro_media:
            # MRO is child-first; reverse so parent media is merged first.
            mro_media.reverse()
            result = ComponentMedia()
            for m in mro_media:
                result = result.merge(m)
        else:
            result = ComponentMedia()

        # Always auto-discover co-located CSS/JS files.
        try:
            source_file = inspect.getfile(self.component_class)
        except (TypeError, OSError):
            return result

        source_dir = Path(source_file).parent
        auto_css: list[str] = []
        auto_js: list[str] = []

        for ext, target in ((".css", auto_css), (".js", auto_js)):
            if (source_dir / f"{self.name}{ext}").is_file():
                target.append(
                    build_static_url(self.app_label, self.relative_path, self.name, ext)
                )

        return result.merge(ComponentMedia(css=auto_css, js=auto_js))

    @property
    def tag_type(self) -> TagType:
        """Return the tag registration type for this component.

        Returns ``TagType.TAG`` for ``TagComponent`` subclasses or
        ``TagType.BLOCK`` for ``BlockComponent`` subclasses.

        Raises ``InvalidTagType`` if the component class is a direct
        ``BaseComponent`` subclass that cannot be registered as a
        template tag.
        """
        from dj_design_system.components import BlockComponent, TagComponent

        if issubclass(self.component_class, BlockComponent):
            return TagType.BLOCK
        if issubclass(self.component_class, TagComponent):
            return TagType.TAG
        raise InvalidTagType(
            f"Component '{self.name}' ({self.component_class.__name__}) is a "
            f"direct BaseComponent subclass. Use TagComponent or BlockComponent."
        )


@dataclass
class NavNode:
    """A single node in the gallery navigation tree.

    A node can represent an app root, a folder, a component, or a markdown
    document — or a combination (e.g. a folder that also carries a component
    when the leaf-folder collapsing rule is applied).
    """

    label: str
    slug: str
    node_type: NodeType
    children: list[NavNode] = field(default_factory=list)
    component: ComponentInfo | None = None
    doc_path: Path | None = None
    index_doc_path: Path | None = None
    _app_label: str = ""
    _path_parts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate that data fields are consistent with ``node_type``."""
        if self.node_type == NodeType.COMPONENT and self.component is None:
            raise ValueError("COMPONENT nodes must have a ComponentInfo")
        if self.node_type != NodeType.COMPONENT and self.component is not None:
            raise ValueError(
                f"{self.node_type.value.upper()} nodes must not carry a ComponentInfo"
            )
        if self.node_type == NodeType.DOCUMENT and self.doc_path is None:
            raise ValueError("DOCUMENT nodes must have a doc_path")
        if self.node_type != NodeType.DOCUMENT and self.doc_path is not None:
            raise ValueError(
                f"{self.node_type.value.upper()} nodes must not carry a doc_path"
            )

    # ------------------------------------------------------------------
    # Mutation helpers — keep *node_type* and data fields in sync
    # ------------------------------------------------------------------

    def upgrade_to_component(self, info: ComponentInfo, label: str) -> None:
        """Atomically convert a folder node into a component node."""
        self.component = info
        self.node_type = NodeType.COMPONENT
        self.label = label

    # ------------------------------------------------------------------
    # Convenience predicates
    # ------------------------------------------------------------------

    @property
    def has_children(self) -> bool:
        return bool(self.children)

    @property
    def is_component(self) -> bool:
        return self.node_type == NodeType.COMPONENT

    @property
    def is_document(self) -> bool:
        return self.node_type == NodeType.DOCUMENT

    @property
    def has_index_doc(self) -> bool:
        return self.index_doc_path is not None

    @property
    def url(self) -> str:
        """Return the gallery URL for this node.

        Requires ``_app_label`` and ``_path_parts`` to be set via
        ``_annotate_paths``.
        """
        from django.urls import reverse

        app = self._app_label or self.slug
        path = "/".join(self._path_parts)

        if not path:
            return reverse("gallery-node-root", kwargs={"app_label": app})

        return reverse("gallery-node", kwargs={"app_label": app, "path": path})

    @property
    def active_path(self) -> str:
        """Return a slash-joined path for active-state matching in the nav tree.

        Derived from :attr:`url` via the Django URL resolver, stripping the
        gallery root prefix and trailing slash so that the result is a bare
        path like ``myapp/elements/icon``.
        """
        from django.urls import reverse

        gallery_root = reverse("gallery")
        return self.url.removeprefix(gallery_root).rstrip("/")
