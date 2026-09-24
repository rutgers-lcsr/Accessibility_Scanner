---
title: Keep heading levels in order
impact: moderate
summary: Headings must step down one level at a time (h1, h2, h3), so the page outline a screen reader builds matches the structure you see.
wcag: 1.3.1, 2.4.6
deque: https://dequeuniversity.com/rules/axe/4.10/heading-order
---

## What this means

Screen readers turn the headings into an outline and let a visitor jump from heading to heading, or list them like a table of contents. When a page jumps from an `h2` straight to an `h4`, the outline has a hole: the visitor cannot tell whether something is missing or the author picked `h4` because it looked smaller.

That is nearly always why it happens: heading levels were chosen for their size, not for their place in the structure. Fix the structure, then use CSS for the size.

## Why it matters

Headings are the main way screen-reader users skim a page. A consistent outline lets them find "Assignments" or "Office hours" in seconds; a broken one makes them read the page top to bottom. WCAG 1.3.1 (Info and Relationships) and 2.4.6 (Headings and Labels).

## Before

```html
<h1>CS 440</h1>
<h4>Week 1</h4>
<h2>Lectures</h2>
<h4>Readings</h4>
```

`h1` to `h4` skips two levels, and "Lectures" (an `h2`) ends up above "Week 1" in the outline although it belongs under it.

## After

```html
<h1>CS 440</h1>
<h2>Week 1</h2>
<h3>Lectures</h3>
<h3>Readings</h3>
```

If "Week 1" looked better small, keep the structure and change the size:

```css
h2.week { font-size: 1.1rem; }
```

## WordPress

- In the block editor, select the heading and pick the level from the **H2 / H3 / H4** dropdown in the toolbar. The post title is already the `h1`, so content starts at `h2` and steps down from there.
- Do not choose a level to get a smaller font: use the block's **Typography → Size** setting instead.
- The classic editor's paragraph dropdown (Heading 2, Heading 3…) works the same way.
- If every page fails at the same spot, the theme template is printing a heading with the wrong level (a widget title as `h4`, for example); change it in a child theme.

## Canvas

The page title Canvas shows is the `h1`, so content in the Rich Content Editor starts at **Heading 2** and steps down: Heading 3 under a Heading 2, never a Heading 4 directly under a Heading 2.

- Select the text, open the paragraph style menu (the one that reads "Paragraph") and pick the right level.
- Run the editor's **Accessibility Checker** (the icon at the bottom of the editor); it flags skipped levels and can fix them in place.
- Content pasted from Word often arrives with bold paragraphs instead of headings, or with odd levels; re-apply the levels after pasting.

## GitHub Pages

The layout prints the page title as `h1`, so headings in your markdown start at `##` and step down:

```markdown
## Week 1
### Lectures
### Readings
```

Do not reach for `####` to get smaller text. If the theme does not print the title, start the file with a single `# Title` and go on from `##`. Check the compiled site, not just the markdown: some themes add their own heading around the content.

## Plain HTML

Search the page for `<h` and read the levels in order. Each heading must be at most one level deeper than the previous one. Fix the tags, then adjust sizes with CSS classes rather than heading levels. If the pages share an include for the header, fix it there once.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live, or check one page with the axe DevTools browser extension. The rule clears page by page, because each page's own headings decide.
