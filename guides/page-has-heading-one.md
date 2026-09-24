---
title: Start each page with one main heading
impact: moderate
summary: Every page needs exactly one h1 that names the page, because it anchors the outline screen readers use to understand what the page is about.
wcag: 1.3.1, 2.4.6
deque: https://dequeuniversity.com/rules/axe/4.10/page-has-heading-one
---

## What this means

The page has no `<h1>`. Screen-reader users jump to the first heading to find out what a page is, and the `h1` is the top of the outline that the other headings hang from. A page that starts at `h2`, or uses a big styled paragraph as its title, has no top.

## Why it matters

Without an `h1` the outline has no root, and a visitor cannot tell the page's title from its sections. WCAG 1.3.1 (Info and Relationships) and 2.4.6 (Headings and Labels).

## Before

```html
<div class="page-title">Schedule</div>
<h2>Week 1</h2>
```

## After

```html
<h1>Schedule</h1>
<h2>Week 1</h2>
```

Keep the site name for the `<title>` and the header; the `h1` is the page's own name. One per page.

## WordPress

- **Block theme.** The page template should contain a **Title** block (Post Title) set to the H1 level; check Appearance → Editor → Templates → *Page*. Some themes only show the title on posts, not pages; add the block to the page template.
- **Classic theme.** The page template prints `the_title()`; make sure it is wrapped in `<h1>`, not `<h2>` or a `div`. Change it in a child theme.
- On the home page, themes sometimes hide the title; give the front page a visible `h1` block (the site name or a short heading) instead.

## Canvas

Canvas prints the page's title as the `h1`, so a course page failing this rule is Canvas's own interface. Mark the finding **Accepted** with the note "Canvas interface" and report it to the Rutgers Canvas team. Do not add another `h1` in the editor; content headings start at Heading 2.

## GitHub Pages

Let the layout print the title as the page's `h1`:

```liquid
<main>
  <h1>{{ page.title }}</h1>
  {{ content }}
</main>
```

and set `title:` in each page's front matter. If the layout does not print it, start each markdown file with one `# Title` line and continue with `##`. Do not do both, or the page will have two.

## Plain HTML

Give each page one `<h1>` with the page's name, usually the first thing inside `<main>`. If a styled `div` or `p` plays the part of the title, change its tag to `h1` and keep the styling in CSS.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live. A layout fix clears every page that uses it.
