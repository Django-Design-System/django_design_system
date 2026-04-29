from __future__ import annotations

import enum


class NodeType(enum.Enum):
    """Discriminates the kind of navigation node."""

    APP = "app"
    FOLDER = "folder"
    COMPONENT = "component"
    DOCUMENT = "document"


class TagType(enum.Enum):
    """The type of template tag a component should be registered as."""

    TAG = "tag"
    BLOCK = "block"


class CanvasMode(enum.Enum):
    """Rendering mode for a canvas instance."""

    BASIC = "basic"
    EXTENDED = "extended"
