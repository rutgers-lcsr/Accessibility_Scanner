---
title: Put every part of the page inside a landmark
impact: moderate
summary: Wrap the header, navigation, main content and footer in landmark elements so screen-reader users can jump straight to the part of the page they want.
wcag: 1.3.1, 2.4.1
deque: https://dequeuniversity.com/rules/axe/4.10/region
---

## What this means

Screen readers offer a list of the page's *landmarks*: banner (header), navigation, main content, complementary (sidebar) and content info (footer). A visitor presses one key to jump between them. This rule fails when some content sits outside every landmark, so that shortcut skips it.

It is almost always a template problem: the theme or layout prints a block of content (a sidebar, a notice, a copyright line) as a plain `<div>` next to the landmarks instead of inside one. One change to the template fixes every page that uses it.

## Why it matters

Without landmarks a screen-reader user has to read the whole page from the top, on every page, to find the content. With them, "jump to main" takes one keystroke. Landmarks also help voice-control and reading-mode users. This is WCAG 1.3.1 (Info and Relationships) and 2.4.1 (Bypass Blocks).

## Before

```html
<body>
  <div class="topbar">Rutgers CS · Course pages</div>
  <header>
    <a href="/">CS 440</a>
  </header>
  <div class="menu">
    <a href="/syllabus">Syllabus</a>
    <a href="/schedule">Schedule</a>
  </div>
  <div class="content">
    <h1>Schedule</h1>
    <p>…</p>
  </div>
  <div class="sidebar">Office hours: Tue 2–4</div>
  <div class="copyright">© Rutgers</div>
</body>
```

The topbar, the menu, the content, the sidebar and the copyright line are all outside every landmark.

## After

```html
<body>
  <header>
    <p class="topbar">Rutgers CS · Course pages</p>
    <a href="/">CS 440</a>
    <nav aria-label="Course">
      <a href="/syllabus">Syllabus</a>
      <a href="/schedule">Schedule</a>
    </nav>
  </header>
  <main>
    <h1>Schedule</h1>
    <p>…</p>
  </main>
  <aside aria-label="Office hours">Office hours: Tue 2–4</aside>
  <footer>© Rutgers</footer>
</body>
```

Every block now lives in `header`, `nav`, `main`, `aside` or `footer`. If you cannot change an element's tag, add a role instead: `role="banner"`, `role="navigation"`, `role="main"`, `role="complementary"`, `role="contentinfo"`. Use exactly one `main`; give a second `nav` or `aside` its own `aria-label`.

## WordPress

- **Block theme (Site Editor, most themes since 2022).** Appearance → Editor → Templates. Open the template the page uses (usually *Page* or *Single*). Everything must sit inside a Header template part, a Group block set to `main` (block settings → Advanced → HTML element), and a Footer template part. Move stray blocks (sidebars, banners, notices) into one of those, or wrap them in a Group whose HTML element is `aside`.
- **Classic theme.** The markup is in `header.php`, `footer.php`, `sidebar.php` and the page templates. Make `header.php` print `<header>`, the menu `<nav>`, the loop `<main>`, `sidebar.php` `<aside>`, and `footer.php` `<footer>`. Change these in a child theme so the next theme update does not undo them.
- **Plugins** that print banners (cookie notices, announcement bars) outside the theme's landmarks are a common cause. Check the failing element's selector on the report page: if it names the plugin's class, look for an option to place it inside the content, or wrap it with `role="region"` and an `aria-label` through the plugin's template filter.

## Canvas

Canvas draws the page frame (navigation, header, footer) itself; the part you edit in the Rich Content Editor already sits inside Canvas's main landmark. You cannot add or move landmarks from a course.

- If the failing element is Canvas's own interface (its selector is outside `.user_content`), there is nothing to change in your course. Mark the finding **Accepted** with the note "Canvas interface" so it stops counting, and report it to the Rutgers Canvas team so they can raise it with Instructure.
- If the selector is inside `.user_content`, the content itself is fine for this rule; look at the other rules listed for the page instead (headings, alt text, link text), which you can fix in the editor.

## GitHub Pages

With Jekyll the frame lives in `_layouts/default.html` (or the theme's layout, which you override by copying it into your repository's `_layouts/`). Make it print:

```liquid
<body>
  <header>{% include header.html %}</header>
  <nav aria-label="Site">{% include nav.html %}</nav>
  <main>{{ content }}</main>
  <footer>{% include footer.html %}</footer>
</body>
```

If you use a remote theme (`remote_theme:` in `_config.yml`), copy its `default.html` into `_layouts/` and edit that copy. Pages built from raw HTML files (no layout) need the same elements in each file. Push the change and the next scan should show the rule cleared on every page that uses the layout.

## Plain HTML

Edit each page's template or server-side include so all content is inside one of `<header>`, `<nav>`, `<main>`, `<aside>` and `<footer>`. If the pages are generated from one include (`header.inc`, `footer.inc`), fix the include. If they are hand-written copies, fix one, then copy the structure to the rest. Keep one `<main>` per page.

## Check your fix

Open one fixed page and use the axe DevTools browser extension (see the Help page), or wait for the next scan. Use the **Rescan this page** action next to any affected page once your change is live; when the rule is gone from that page it will be gone from every page that shares the template.
