---
title: Give every link a name
impact: serious
summary: A link must have text a screen reader can announce; icon-only and image-only links need alt text or an aria-label.
wcag: 2.4.4, 4.1.2
deque: https://dequeuniversity.com/rules/axe/4.10/link-name
---

## What this means

The link has nothing a screen reader can read: it holds only an icon font, an image without alt text, or nothing at all. The visitor hears "link" and has to guess where it goes. Social icons, "read more" arrows and logo links are the usual cases.

## Why it matters

Screen-reader users often pull up a list of all the links on a page; unnamed links appear as blanks. WCAG 2.4.4 (Link Purpose) and 4.1.2 (Name, Role, Value).

## Before

```html
<a href="https://github.com/rutgers-cs"><i class="fa fa-github"></i></a>
<a href="/"><img src="logo.png"></a>
<a href="/news/12"></a>
```

## After

```html
<a href="https://github.com/rutgers-cs" aria-label="Rutgers CS on GitHub">
  <i class="fa fa-github" aria-hidden="true"></i>
</a>
<a href="/"><img src="logo.png" alt="Rutgers Computer Science home"></a>
<a href="/news/12">Read the full story</a>
```

Say where the link goes, not what it looks like ("GitHub", not "icon"). Visible text is best; `aria-label` is for icon links where there is no room for text.

## WordPress

- **Social Icons block**: each icon takes a **Link label** in its settings; fill it in ("Rutgers CS on GitHub").
- **Image block** set to link somewhere: the image's alt text becomes the link's name, so describe the destination.
- Theme icon links (search, menu, "scroll to top") come from the theme; add `aria-label` in a child theme, or find a theme option for screen-reader text.
- Empty links are often leftovers in the classic editor or in a Custom HTML block; give them text or delete them.

## Canvas

- An image you have linked needs alt text that says where the link goes: select the image, open **Image Options**, fill in **Alt Text**.
- Avoid links made of an icon or an emoji only; write the destination as text, "Syllabus (PDF)" rather than an arrow.
- The editor's **Accessibility Checker** does not catch every empty link; use the HTML view to find `<a>` tags with nothing inside.

## GitHub Pages

Social and icon links come from the theme's includes (`_includes/social.html`, `footer.html`). Copy the include into your repository and add `aria-label` to each icon link, or put the network name in a `<span class="sr-only">`. Markdown links always have text, so those are fine.

## Plain HTML

For each link the report names: give it visible text, or an `aria-label`, or alt text on the image inside it. Mark decorative icon fonts inside the link with `aria-hidden="true"` so they are not read as odd characters.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live. Icon links in the header or footer come from the template, so one fix clears every page.
