"""Template nodes and compilation functions for slotted block components.

Provides:
- ``SlotNode``: captures content for a single named slot.
- ``SlottedComponentNode``: renders a block component that declares slots,
  enforcing strict gap validation.
- ``make_slotted_block_tag``: factory that builds a compilation function
  for a given slotted component class.
- ``do_slot``: compilation function for the ``{% slot %}`` tag.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django import template
from django.template import TemplateSyntaxError
from django.template.base import TextNode
from django.utils.safestring import mark_safe

from dj_design_system.slots import validate_slots


if TYPE_CHECKING:
    from dj_design_system.components import BlockComponent


class SlotNode(template.Node):
    """A template node representing a single named slot's content."""

    def __init__(self, name: str, nodelist: template.NodeList) -> None:
        self.name = name
        self.nodelist = nodelist

    def render(self, context: template.Context) -> str:
        return self.nodelist.render(context)


class SlottedComponentNode(template.Node):
    """A template node that renders a slotted BlockComponent.

    Validates that:
    - Only ``SlotNode`` children and whitespace-only ``TextNode``s appear
      in the outer nodelist (strict gap enforcement).
    - All required slots are provided.
    - No unknown or duplicate slot names are used.
    """

    def __init__(
        self,
        nodelist: template.NodeList,
        component_class: type[BlockComponent],
        tag_name: str,
        kwargs: dict[str, Any],
    ) -> None:
        self.nodelist = nodelist
        self.component_class = component_class
        self.tag_name = tag_name
        self.kwargs = kwargs

    def render(self, context: template.Context) -> str:
        # Resolve any template variables in kwargs
        resolved_kwargs = {}
        for key, value in self.kwargs.items():
            if isinstance(value, template.base.FilterExpression):
                resolved_kwargs[key] = value.resolve(context)
            else:
                resolved_kwargs[key] = value
        kwargs = resolved_kwargs

        # Walk children: extract slots, validate gaps
        provided_slots: dict[str, str] = {}
        for node in self.nodelist:
            if isinstance(node, SlotNode):
                if node.name in provided_slots:
                    raise TemplateSyntaxError(
                        f"'{self.tag_name}' received duplicate slot '{node.name}'."
                    )
                provided_slots[node.name] = node.render(context)
            elif isinstance(node, TextNode):
                if node.s.strip():
                    snippet = node.s.strip()[:80]
                    raise TemplateSyntaxError(
                        f"'{self.tag_name}' component requires all content inside "
                        f"{{% slot %}}...{{% endslot %}} tags. "
                        f'Found content outside slots: "{snippet}"'
                    )
                # Whitespace-only TextNodes are fine — skip them
            else:
                # Any other node type (other template tags, variable nodes, etc.)
                raise TemplateSyntaxError(
                    f"'{self.tag_name}' component requires all content inside "
                    f"{{% slot %}}...{{% endslot %}} tags. "
                    f"Found unexpected content between slots."
                )

        # Validate against declared slots and fill defaults
        declared_slots = self.component_class.get_slots()
        slots = validate_slots(declared_slots, provided_slots, self.tag_name)

        # Mark each slot value as safe (content was rendered from template nodes)
        safe_slots = {name: mark_safe(value) for name, value in slots.items()}

        return str(self.component_class(slots=safe_slots, **kwargs))


def _parse_tag_kwargs(
    parser: template.base.Parser,
    bits: list[str],
) -> dict[str, Any]:
    """Parse keyword arguments from template tag token bits.

    Supports: ``key="value"``, ``key='value'``, ``key=variable``.
    Also supports positional string args (bare quoted strings).
    """
    kwargs: dict[str, Any] = {}
    positional: list[Any] = []

    for bit in bits:
        if "=" in bit:
            key, value = bit.split("=", 1)
            # Strip quotes from string literals
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                kwargs[key] = value[1:-1]
            elif value in ("True", "true"):
                kwargs[key] = True
            elif value in ("False", "false"):
                kwargs[key] = False
            else:
                # Treat as a template variable
                kwargs[key] = parser.compile_filter(value)
        else:
            # Positional argument — strip quotes
            if (bit.startswith('"') and bit.endswith('"')) or (
                bit.startswith("'") and bit.endswith("'")
            ):
                positional.append(bit[1:-1])
            else:
                positional.append(parser.compile_filter(bit))

    return {"_positional": positional, **kwargs}


def make_slotted_block_tag(
    component_class: type[BlockComponent],
    tag_name: str,
) -> Any:
    """Build a compilation function for a slotted block component.

    Returns a function suitable for ``library.tag(name=...)(func)``.
    """

    def _compile(parser: template.base.Parser, token: template.base.Token):
        bits = token.split_contents()
        # bits[0] is the tag name
        raw_kwargs = _parse_tag_kwargs(parser, bits[1:])
        positional = raw_kwargs.pop("_positional", [])

        # Map positional args using component's Meta.positional_args
        positional_args = component_class.get_positional_args()
        for i, arg_name in enumerate(positional_args):
            if i < len(positional):
                raw_kwargs[arg_name] = positional[i]

        # Parse until the end tag
        end_tag = f"end{tag_name}"
        nodelist = parser.parse((end_tag,))
        parser.delete_first_token()

        return SlottedComponentNode(
            nodelist=nodelist,
            component_class=component_class,
            tag_name=tag_name,
            kwargs=raw_kwargs,
        )

    _compile.__name__ = f"do_{tag_name}"
    return _compile


def do_slot(parser: template.base.Parser, token: template.base.Token):
    """Compilation function for ``{% slot "name" %}...{% endslot %}``."""
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError(
            f"'{bits[0]}' tag requires exactly one argument: the slot name."
        )

    name = bits[1]
    # Strip quotes
    if (name.startswith('"') and name.endswith('"')) or (
        name.startswith("'") and name.endswith("'")
    ):
        name = name[1:-1]

    nodelist = parser.parse(("endslot",))
    parser.delete_first_token()

    return SlotNode(name=name, nodelist=nodelist)
