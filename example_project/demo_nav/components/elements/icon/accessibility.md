# Icon Accessibility

## Screen readers

Always pair icons with a visible or visually-hidden text label. The icon
component sets `aria-hidden="true"` so screen readers skip the icon element
itself.

```html
<button>
  {% icon "close" %}
  <span class="sr-only">Close</span>
</button>
```

## Colour contrast

Icon fill colour must meet a minimum 3:1 contrast ratio against its background
for non-text contrast (WCAG 1.4.11).
