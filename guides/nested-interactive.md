---
title: Do not nest one control inside another
impact: serious
summary: A button inside a link, or a link inside a button, cannot be operated reliably by keyboard or screen reader; make them siblings instead.
wcag: 4.1.2
deque: https://dequeuniversity.com/rules/axe/4.10/nested-interactive
---

## What this means

An interactive element (a link, a button, an input) contains another one. "Clickable cards" are the typical case: a whole card is wrapped in a link, and the card has its own buttons inside. Keyboard users cannot reach the inner control separately, and screen readers announce a link that is also a button, or skip the inner one.

## Why it matters

Each control needs its own focus stop and its own name. Nesting takes both away from the inner control. WCAG 4.1.2 (Name, Role, Value).

## Before

```html
<a href="/courses/cs440" class="card">
  <h3>CS 440</h3>
  <p>Introduction to Artificial Intelligence</p>
  <button>Enroll</button>
</a>
```

## After

```html
<div class="card">
  <h3><a href="/courses/cs440">CS 440</a></h3>
  <p>Introduction to Artificial Intelligence</p>
  <button>Enroll</button>
</div>
```

Link the heading (or a "Details" link) and keep the button beside it. If you want the whole card to act as a link, do it with CSS on the heading link (`.card { position: relative } .card h3 a::after { position: absolute; inset: 0 }`) and keep the button outside that link's area.

## WordPress

- **Cover, Group and Image blocks** with a link set on the block, containing a **Buttons** block: remove the block-level link and link the heading or add a text link instead; keep the Buttons block as a sibling.
- "Card" patterns from page builders often wrap everything in an `<a>`; look for a "link the whole card" option and turn it off, then link the title.
- Menu plugins that put a `<button>` (a dropdown toggle) inside the menu `<a>`: update the plugin or turn off the toggle inside the link; the core Navigation block renders the toggle as a sibling.

## Canvas

Content from the Rich Content Editor rarely produces this. A failing element is usually an embedded tool or Canvas's own interface: if the selector is outside `.user_content`, mark the finding **Accepted** with the note "Canvas interface" and report it to the Rutgers Canvas team; for an embedded tool (an iframe or LTI app) report it to whoever runs it. In your own HTML, do not put a button inside a link.

## GitHub Pages

The card markup lives in a theme include or in HTML you wrote in the markdown. Copy the include into your repository and restructure it so the link and the button are siblings, linking the heading instead of the whole card.

## Plain HTML

Find the outer control from the report's selector, move the inner control out so the two are siblings, and link the heading or a short text link instead of the whole block.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live, or the axe DevTools extension on the page. A pattern used on many pages clears everywhere once its template changes.
