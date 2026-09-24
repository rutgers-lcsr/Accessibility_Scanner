---
title: Label landmarks that share a role
impact: moderate
summary: When a page has two navigation areas or two sidebars, each needs its own label so a screen reader can tell them apart.
wcag: 1.3.1
deque: https://dequeuniversity.com/rules/axe/4.10/landmark-unique
---

## What this means

Landmarks (`nav`, `aside`, `header`, `footer`, `main`, `section` with a role) are listed by screen readers so people can jump to them. When two landmarks have the same role, the list shows "navigation, navigation" and the visitor has to guess which one is the site menu and which is the footer links.

The fix is a label: `aria-label="Main"` on one and `aria-label="Footer"` on the other. A landmark that is the only one of its kind needs no label.

## Why it matters

The landmark list is a shortcut through the page. Duplicate, unlabelled entries make it a guessing game. WCAG 1.3.1 (Info and Relationships) and the ARIA landmark best practice.

## Before

```html
<nav>
  <a href="/">Home</a> <a href="/schedule">Schedule</a>
</nav>
…
<nav>
  <a href="/privacy">Privacy</a> <a href="/contact">Contact</a>
</nav>
```

## After

```html
<nav aria-label="Main">
  <a href="/">Home</a> <a href="/schedule">Schedule</a>
</nav>
…
<nav aria-label="Footer">
  <a href="/privacy">Privacy</a> <a href="/contact">Contact</a>
</nav>
```

Labels are read by screen readers only, so keep them short and different from each other. If a visible heading already names the area, point at it instead: `<nav aria-labelledby="footer-links-heading">`.

## WordPress

- **Block theme.** Each Navigation block uses the name of its menu as its label, so give the two menus different names (Appearance → Editor → Navigation): "Main" and "Footer", not "Menu 1" and "Menu 2". A Group block used as a sidebar can be given an HTML element of `aside` and an ARIA label under **Advanced**.
- **Classic theme.** `wp_nav_menu()` accepts `'container_aria_label' => 'Footer'`; add it to the second menu call in `footer.php`, or wrap the call in `<nav aria-label="Footer">` and set `'container' => false`.
- Menu and sidebar plugins usually print their own `<nav>`; look for a label setting, or wrap their output.

## Canvas

Canvas draws the page frame, including its navigation landmarks; you cannot label them from a course. If the failing element's selector is outside `.user_content`, mark the finding **Accepted** with the note "Canvas interface" and report it to the Rutgers Canvas team. Content inside the editor does not create landmarks, so this rule does not apply to it.

## GitHub Pages

The landmarks come from the layout or the theme's includes. Copy the theme's `_layouts/default.html` (or the include that prints the menu) into your repository and add the labels:

```liquid
<nav aria-label="Site">{% include nav.html %}</nav>
…
<nav aria-label="Footer">{% include footer-links.html %}</nav>
```

## Plain HTML

Find the elements with the same role (`<nav>`, `<aside>`, or `role="navigation"`) in the template or include and give each an `aria-label`. If the pages are separate copies, fix one and copy the change.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live. Because the landmarks come from the template, clearing it on one page clears every page that uses it.
