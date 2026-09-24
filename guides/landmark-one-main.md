---
title: Mark the main content with one main landmark
impact: moderate
summary: Each page needs exactly one main element around its content, so screen-reader users can skip the header and navigation in one step.
wcag: 1.3.1, 2.4.1
deque: https://dequeuniversity.com/rules/axe/4.10/landmark-one-main
---

## What this means

The page has no `<main>` landmark, or has two. "Skip to main content" and the screen reader's landmark shortcut rely on it. Without one, visitors have to tab or read through the whole header and menu on every page; with two, they cannot tell which is the real content.

## Why it matters

The `main` landmark is the single most used shortcut for screen-reader users. WCAG 1.3.1 (Info and Relationships) and 2.4.1 (Bypass Blocks).

## Before

```html
<header>…</header>
<div class="content">
  <h1>Schedule</h1>
  …
</div>
<footer>…</footer>
```

Or, the two-mains version some themes produce:

```html
<div role="main"><main>…</main></div>
```

## After

```html
<header>…</header>
<main>
  <h1>Schedule</h1>
  …
</main>
<footer>…</footer>
```

One `<main>` per page, containing the content that is unique to the page and not the header, menus or footer. If you cannot change the tag, use `role="main"` on the wrapper, but not both on nested elements.

## WordPress

- **Block theme.** Appearance → Editor → Templates → the page template. The Group block that holds the content must have its HTML element set to `main` (block settings → **Advanced → HTML element**). Make sure only one block on the template is set that way.
- **Classic theme.** In the page templates (`page.php`, `single.php`, `index.php`) wrap the loop in `<main>`. If the theme prints `<div id="main" role="main">` around a `<main>`, remove the role from the wrapper. Change these in a child theme.

## Canvas

Canvas provides the `main` landmark on its pages, so a failing page here is Canvas's own interface. Mark the finding **Accepted** with the note "Canvas interface" and report it to the Rutgers Canvas team. Content in the editor cannot add or remove landmarks.

## GitHub Pages

Put it in the layout around the content:

```liquid
<main>{{ content }}</main>
```

If your theme already wraps the content in `<main>` or `<div role="main">`, do not add a second one in your pages. Copy the theme's `_layouts/default.html` into your repository when you need to change it.

## Plain HTML

Wrap the page's own content in `<main>…</main>` in the template or in each page, and remove any second `<main>` or `role="main"`. Header, navigation and footer stay outside it.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live. A template fix clears every page that uses it.
