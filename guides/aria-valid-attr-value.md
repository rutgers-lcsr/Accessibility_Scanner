---
title: Fix ARIA attributes with invalid values
impact: critical
summary: An ARIA attribute must use a value it allows, and an id it points at must exist; otherwise assistive technology ignores it or announces the wrong thing.
wcag: 4.1.2
deque: https://dequeuniversity.com/rules/axe/4.10/aria-valid-attr-value
---

## What this means

ARIA attributes describe controls to assistive technology, but only with the values they define. `aria-expanded` takes `true` or `false`, not `yes`; `aria-hidden` takes `true` or `false`; `aria-labelledby` and `aria-controls` must name the `id` of an element that is actually on the page. The scan's failure summary tells you which attribute and value failed.

This almost always comes from a theme, a menu plugin or a script, not from content, so one fix in the template clears every page.

## Why it matters

A screen reader that reads `aria-expanded="yes"` cannot tell whether the menu is open. A label that points at a missing id gives the control no name at all, so a button reads as "button". WCAG 4.1.2 (Name, Role, Value).

## Before

```html
<button aria-expanded="yes" aria-controls="menu">Menu</button>
<div id="nav-menu">…</div>

<h2 id="hours">Office hours</h2>
<section aria-labelledby="office-hours">…</section>
```

`yes` is not a valid value, `aria-controls` names an id that does not exist, and `aria-labelledby` points at `office-hours` while the heading's id is `hours`.

## After

```html
<button aria-expanded="false" aria-controls="nav-menu">Menu</button>
<div id="nav-menu">…</div>

<h2 id="hours">Office hours</h2>
<section aria-labelledby="hours">…</section>
```

Toggle `aria-expanded` between `"true"` and `"false"` in the script that opens the menu. When you cannot make an attribute valid, removing it is better than leaving a wrong one.

## WordPress

- Note the element's selector from the report page; it usually names a plugin or theme class (`.menu-toggle`, `.slick-slide`).
- A menu or slider plugin: update it first; many fixed their ARIA in recent versions. If it is still wrong, check its settings for accessibility options, then report it to the plugin author.
- The theme's own markup: correct it in a child theme (`header.php` or the block template part) so updates do not undo the fix.
- Custom HTML blocks: edit the attribute directly.

## Canvas

The Rich Content Editor removes most ARIA attributes, so a failing element is usually Canvas's own interface or an embedded tool (an iframe, an LTI app). If the selector is outside `.user_content`, mark the finding **Accepted** with the note "Canvas interface" and report it to the Rutgers Canvas team. For an embedded tool, report it to whoever runs that tool. For HTML you wrote in the editor's HTML view, correct or remove the attribute.

## GitHub Pages

Search the theme's includes and any JavaScript in `assets/` for the attribute named in the failure summary. Copy the include into your repository and correct it there. Menu toggles from remote themes are the usual source: make the script set `aria-expanded` to `"true"` or `"false"` and make `aria-controls` match the menu's `id`.

## Plain HTML

Search the template or include for the attribute the summary names and give it a valid value, or remove it. For `aria-labelledby`, `aria-describedby` and `aria-controls`, make sure an element with exactly that `id` exists on the page.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live, or the axe DevTools extension, which names the attribute and the allowed values. A template fix clears every page that uses it.
