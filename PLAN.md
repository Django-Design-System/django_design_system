# Plan: Named Slots for BlockComponent (Option B — Nested)

## TL;DR

Introduce named slots to `BlockComponent` via `Meta.slots` dict. When declared, the
component uses a custom parser (`@library.tag`) with `{% slot "name" %}...{% endslot %}`
nested inside the block. Strict gap enforcement: ANY non-whitespace content outside slot
tags raises `TemplateSyntaxError`. Backward compatible: `BlockComponent` without
`Meta.slots` continues to use `simple_block_tag` unchanged.

## Decisions

- Tag syntax: `{% slot "name" %}...{% endslot %}` (no namespace prefix)
- Errors: raised at parse time (`TemplateSyntaxError`)
- Definition: `Meta.slots = {"name": Slot(...)}` dict
- No default slot concept: either a component has NO slots (simple block, content as
  today) or ALL slots are explicitly named — no implicit routing
- Class: same `BlockComponent` — presence of `Meta.slots` auto-switches registration
- Example: `CardComponent` in `demo_components/components/`
- Gallery: one textarea per slot in the parameter form
- Gap enforcement: strict — ANY non-whitespace/non-comment content outside
  `{% slot %}...{% endslot %}` raises `TemplateSyntaxError`; whitespace and Django
  comments (`{# ... #}`) are silently stripped
- Optional slots that are not provided render as `""` in the template context

## Template Usage

```htmldjango
{# No slots — works exactly as today, unchanged #}
{% alert "warning" %}
  Content here.
{% endalert %}

{# Slotted — every slot must be explicitly named #}
{% card title="Hello" %}
  {% slot "body" %}
    <p>Body content.</p>
  {% endslot %}
  {% slot "actions" %}
    <button>Save</button>
  {% endslot %}
{% endcard %}

{# Optional slots can simply be omitted #}
{% card title="Hello" %}
  {% slot "body" %}
    <p>Only the required slot.</p>
  {% endslot %}
{% endcard %}

{# ERROR — content outside slots #}
{% card title="Hello" %}
  <p>This text is not inside a slot!</p>
  {% slot "body" %}
    <p>Body.</p>
  {% endslot %}
{% endcard %}
{# → TemplateSyntaxError: 'card' component requires all content inside
#    {% slot %}...{% endslot %} tags. Found content outside slots:
#    "<p>This text is not inside a slot!</p>" #}
```

## Component Definition

```python
from dj_design_system.components import BlockComponent
from dj_design_system.parameters import StrParam
from dj_design_system.slots import Slot


class CardComponent(BlockComponent):
    """A card with optional header and footer areas."""

    title = StrParam("Card title", required=False)

    class Meta:
        slots = {
            "body": Slot(required=True, description="Main card content"),
            "header": Slot(required=False, description="Optional header area"),
            "footer": Slot(required=False, description="Optional footer area"),
        }

    def render(self) -> str:
        header = (
            f"<div class='card-header'>{self.slots['header']}</div>"
            if self.slots.get("header")
            else ""
        )
        footer = (
            f"<div class='card-footer'>{self.slots['footer']}</div>"
            if self.slots.get("footer")
            else ""
        )
        title = (
            f"<h3 class='card-title'>{self.title}</h3>" if self.title else ""
        )
        return (
            f"<div class='card {self.get_classes_string()}'>"
            f"{header}{title}"
            f"<div class='card-body'>{self.slots['body']}</div>"
            f"{footer}"
            f"</div>"
        )
```

---

## Phase 1: Core Slot Infrastructure

### Step 1: Slot class
- New file: `dj_design_system/slots.py`
- `Slot(required=False, default="", description="")`
- `validate_slots(declared_slots, provided_slots, component_name)`:
  - Missing required slot → error
  - Unknown slot name → error
  - Duplicate slot name → error
  - Optional missing → fill with `default` (empty string by default)

### Step 2: Custom template Nodes
- New file: `dj_design_system/services/slot_node.py`
- `SlotNode(template.Node)` — holds slot name + inner nodelist
- `SlottedComponentNode(template.Node)` — holds outer nodelist + component class + kwargs
  - `render()`: iterates child nodes, extracts `SlotNode` instances, validates gaps,
    renders each slot's nodelist, calls `validate_slots()`, instantiates component
  - Gap validation: for each `TextNode`, check `node.s.strip() == ""` — if not, raise
    `TemplateSyntaxError` with the offending content in the message
  - Non-TextNode, non-SlotNode children: also raise `TemplateSyntaxError`
    (catches stray `{% other_tag %}` between slots)

### Step 3: Compilation function factory
- In `slot_node.py`: `make_slotted_block_tag(component_class)`
  - Returns a `do_<tagname>(parser, token)` compilation function
  - Parses kwargs from opening token
  - Calls `parser.parse(('end<tagname>',))` to capture full inner nodelist
  - Calls `parser.delete_first_token()` to consume the end tag
  - Returns `SlottedComponentNode(nodelist, component_class, kwargs)`
- `do_slot(parser, token)`: extracts slot name from token, calls
  `parser.parse(('endslot',))`, consumes end token, returns `SlotNode`

### Step 4: Modify BlockComponent
- `as_tag()`: if `cls.has_slots()` → return compilation function; else → existing behaviour
- New `__init__` path: when slots declared, accept `slots: dict[str, SafeString]`
  (no `content` argument). Store as `self.slots`.
- `get_context()`: when slotted, inject each slot value as `{slot_name}` into context
  (enables `template_format_str` use for simple cases where optional slots = "")
- New classmethods: `has_slots() -> bool`, `get_slots() -> dict[str, Slot]`

### Step 5: Modify registry registration
- `ComponentRegistry._register_tag()`: if block + `has_slots()` →
  `library.tag(name=tag_name)(compilation_func)`
- Register `{% slot %}` / `{% endslot %}` globally on the design_components library

---

## Phase 2: Example Card Component

### Step 6: CardComponent
- `example_project/demo_components/components/card/card.py`
- Slots: `body` (required), `header` (optional), `footer` (optional)
- Overrides `render()` for conditional header/footer wrapping
- Co-located `card.css` with minimal card styling

### Step 7: Template format strategy
- For simple slotted components: `template_format_str` works — optional slots render as
  empty string (component author designs format knowing this)
- For conditional wrapping (like CardComponent): override `render()`
- No new framework machinery needed

---

## Phase 3: Gallery & Documentation Support

### Step 8: Forms — slot textareas
- `dj_design_system/forms.py`: when `has_slots()`, add one `CharField(widget=Textarea)`
  per declared slot (prefixed `slot__` to distinguish from params)
- Initial value: `Slot.default` or `"Sample {slot_name} content"`

### Step 9: Canvas service
- `dj_design_system/services/canvas.py`: `render_component()` — when slotted, extract
  `slot__*` keys from kwargs, pass as `slots={name: value}`
- `build_canvas_url()`: encode slot values with `slot__` prefix

### Step 10: Tag signature generation
- `dj_design_system/services/tag_signature.py`: slotted components produce:
  - Minimal: only required slots with placeholder content
  - Maximal: all slots with example content
  - Format: multi-line with `{% slot "name" %}...{% endslot %}` blocks

### Step 11: Markdown canvas
- `dj_design_system/services/markdown_canvas.py`: extend regex to parse
  `{% slot "name" %}...{% endslot %}` inside canvas fenced blocks, extract to
  `CanvasSpec.slots` dict

### Step 12: Views — component detail page
- `dj_design_system/views.py`: display slot metadata in a "Slots" section
  (name, required, default, description)

---

## Phase 4: Testing

### Step 13: Slot class unit tests
- `tests/test_slots.py`
- Slot instantiation, defaults, required flag, description
- `validate_slots()`: missing required raises, unknown raises, duplicate raises,
  optional missing returns default

### Step 14: Gap enforcement tests (CRITICAL)
- Whitespace between slots → renders OK
- Django comment `{# ... #}` between slots → renders OK (already stripped by parser)
- Non-whitespace text between slots → `TemplateSyntaxError`
- HTML tags between slots → `TemplateSyntaxError`
- Another template tag between slots (not `{% slot %}`) → `TemplateSyntaxError`
- Content before first `{% slot %}` (whitespace only) → OK
- Content before first `{% slot %}` (non-whitespace) → `TemplateSyntaxError`
- Content after last `{% endslot %}` (whitespace only) → OK
- Content after last `{% endslot %}` (non-whitespace) → `TemplateSyntaxError`
- Error message includes component name and offending content snippet

### Step 15: SlottedComponentNode rendering tests
- All required slots provided → renders correctly
- Optional slot omitted → uses default value (empty string)
- Optional slot with custom default → default appears in output
- Unknown slot name → `TemplateSyntaxError`
- Duplicate slot name → `TemplateSyntaxError`
- Slot content renders Django template variables/tags correctly (context passes through)
- Nested design system components inside slots → works

### Step 16: Backward compatibility
- Existing BlockComponent (no Meta.slots) works identically
- ALL existing tests pass without modification

### Step 17: Integration — template rendering
- Full template with `{% load design_components %}` + slotted component
- Card with all slots filled
- Card with only required slot
- Card nested inside another component
- Slot containing other design system components

### Step 18: Integration — gallery
- Canvas renders slotted component with slot params
- Form shows textarea per slot
- Tag signature generates correct examples
- Markdown canvas parses slotted syntax

---

## Phase 5: Documentation

### Step 19: User docs
- `docs/components.md` — "Slots" section: Slot class, Meta.slots, gap rules, examples
- `docs/templatetags.md` — slot usage patterns

### Step 20: CardComponent docs
- Class docstring
- `index.md` with canvas examples showing slot combinations

### Step 21: API reference
- `docs/api/components.md` — Slot class API

---

## Files

### Create
- `dj_design_system/slots.py`
- `dj_design_system/services/slot_node.py`
- `example_project/demo_components/components/card/card.py`
- `example_project/demo_components/components/card/card.css`
- `tests/test_slots.py`

### Modify
- `dj_design_system/components.py`
- `dj_design_system/services/registry.py`
- `dj_design_system/forms.py`
- `dj_design_system/services/canvas.py`
- `dj_design_system/services/tag_signature.py`
- `dj_design_system/services/markdown_canvas.py`
- `dj_design_system/views.py`
- `dj_design_system/templatetags/design_components.py`
- `docs/components.md`
- `docs/templatetags.md`

---

## Verification

1. `just test` — all existing tests pass unchanged
2. `just test-one "test_slots"` — new tests pass
3. `just check` — ruff/ty clean
4. Manual: gallery renders CardComponent (signatures, canvas, form, preview)
5. Manual: gap content raises `TemplateSyntaxError` with useful message

---

## Phasing

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| **1** | Steps 1–5, 13–16 | Core infra + all unit tests + backward compat verified |
| **2** | Steps 6–7, 17 | Card component + integration tests |
| **3** | Steps 8–12, 18–21 | Gallery support + documentation |

Phase 1 is the hardest (custom parser, gap validation). Phase 2 is small.
Phase 3 is wide but mechanical.

---

## Open Consideration

**`template_format_str` with optional slots**: `format_html()` cannot do conditionals.
Optional slots default to `""` — simple slotted components can use `template_format_str`
if they're fine with empty strings in the output. For conditional wrapping (e.g., only
render a `<header>` div when the header slot is provided), override `render()`. No new
framework machinery needed.
