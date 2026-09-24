---
title: Make links in text recognisable without colour
impact: serious
summary: A link inside a paragraph needs an underline, or a colour that contrasts 3:1 with the surrounding text, so it can be spotted without seeing colour.
wcag: 1.4.1
deque: https://dequeuniversity.com/rules/axe/4.10/link-in-text-block
---

## What this means

Links in the body text have had their underline removed, and their colour is too close to the text around them. Someone who does not see colour differences, or who is reading on a dim screen, cannot tell which words are links.

The underline is the fix in almost every case, and it comes from one rule in the stylesheet.

## Why it matters

If colour is the only difference, people with colour-vision deficiencies see plain text. WCAG 1.4.1 (Use of Color).

## Before

```css
.content a {
  color: #4a6fa5;
  text-decoration: none;
}
```

Body text is `#333`; the link is blue but only 2.4:1 against it, and nothing else marks it.

## After

```css
.content a {
  color: #005a8c;
  text-decoration: underline;
}
```

Underlining is enough on its own. Links in menus and buttons are not affected by this rule, only links inside blocks of text.

## WordPress

- **Block theme.** Appearance → Editor → **Styles → Typography → Links** (or **Elements → Link**) and turn the underline on, or set it in `theme.json` under `styles.elements.link.typography.textDecoration`.
- **Classic theme.** Appearance → Customize → **Additional CSS**: `.entry-content a { text-decoration: underline; }`.
- Some themes offer a "link underline" toggle in the customizer; check that before writing CSS.

## Canvas

The Rich Content Editor underlines links by default, so a failing page usually has custom styling applied to the text, or the link is styled to look like plain text. Select the link and remove the custom colour or formatting; the default style passes. Content built with a design tool that strips underlines needs its link style restored in that tool.

## GitHub Pages

Override the theme in `assets/css/style.scss`:

```scss
---
---
@import "{{ site.theme }}";
.main-content a { text-decoration: underline; }
```

Match the selector the theme uses for the content area (`.main-content`, `.post-content`, `article`).

## Plain HTML

Find the rule that removes the underline (`text-decoration: none`) for links in the content and delete it, or set `text-decoration: underline` for those links. Leave navigation and buttons as they are.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live. Because the style is site-wide, one CSS change clears every page.
