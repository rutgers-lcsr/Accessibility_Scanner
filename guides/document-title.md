---
title: Give every page a title
impact: serious
summary: Each page needs a title element that says what the page is, because it is the first thing a screen reader announces and what the browser tab and history show.
wcag: 2.4.2
deque: https://dequeuniversity.com/rules/axe/4.10/document-title
---

## What this means

The `<title>` in the page's `<head>` is missing or empty. Screen readers announce it when the page loads, tabs and bookmarks show it, and search engines use it. Without one, every page of the site is "Untitled" to a visitor switching between tabs.

## Why it matters

The title is how people confirm they landed on the right page before reading it. WCAG 2.4.2 (Page Titled).

## Before

```html
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="style.css">
</head>
```

## After

```html
<head>
  <meta charset="utf-8">
  <title>Schedule – CS 440 – Rutgers CS</title>
  <link rel="stylesheet" href="style.css">
</head>
```

Put the page-specific part first, then the site, so tabs stay readable when they are narrow. Make each page's title different.

## WordPress

- The theme must let WordPress print the title: `header.php` needs `<?php wp_head(); ?>` and the theme's `functions.php` needs `add_theme_support('title-tag');`. Block themes do this already.
- Do not hard-code `<title>` in `header.php`; remove it and let `title-tag` print one per page.
- An SEO plugin (Yoast, Rank Math) writes the title too and offers a per-page field; make sure only one of them is active.

## Canvas

Canvas sets the title of every course page itself, so a failing page here is Canvas's own interface. Mark the finding **Accepted** with the note "Canvas interface" and report it to the Rutgers Canvas team. Content in the editor cannot add or change the title.

## GitHub Pages

Put the title in the layout so every page gets one:

```liquid
<title>{{ page.title }} – {{ site.title }}</title>
```

Set `title:` in `_config.yml` and in each page's front matter. The `jekyll-seo-tag` plugin (`{% seo %}` in the head) prints it too, with sensible fallbacks. If you use a remote theme, copy its `_layouts/default.html` or `_includes/head.html` into your repository and edit that copy.

## Plain HTML

Add a `<title>` to the `<head>` of each page or to the shared head include, with a value that differs per page. Pages generated from a template need the template to fill it in.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live. A fix in the layout clears every page that uses it; hand-written pages clear one by one.
