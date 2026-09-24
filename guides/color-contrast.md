---
title: Make text contrast with its background
impact: serious
summary: Normal text needs a contrast ratio of at least 4.5:1 against its background (3:1 for large text), so it stays readable for people with low vision or on a poor screen.
wcag: 1.4.3
deque: https://dequeuniversity.com/rules/axe/4.10/color-contrast
---

## What this means

The text colour and the colour behind it are too close. The failure summary on the report page gives the exact numbers: the two colours, the ratio measured, and the ratio needed. Normal text needs 4.5:1; large text (24px and up, or 19px bold) needs 3:1.

Light grey "secondary" text, placeholder text, and coloured text on coloured backgrounds are the usual causes. They tend to come from the theme's palette, so one colour change clears many pages.

## Why it matters

Low contrast is unreadable for many people with low vision or colour deficiencies, and hard for everyone in sunlight or on a cheap projector. WCAG 1.4.3 (Contrast, Minimum).

## Before

```css
.note { color: #999999; background: #ffffff; }   /* 2.8:1 */
.banner { color: #ffffff; background: #ff6666; } /* 2.7:1 */
```

## After

```css
.note { color: #595959; background: #ffffff; }   /* 7.0:1 */
.banner { color: #ffffff; background: #cc0033; } /* 5.9:1 */
```

Use a contrast checker (WebAIM's is free) while picking colours. Darkening the text is usually easier than changing the background. The Rutgers red `#cc0033` on white passes for text of any size.

## WordPress

- **Block editor.** Select the block, open **Color** in the settings panel and pick a darker text colour or a different background. The editor warns when a combination is hard to read.
- **Whole site.** Appearance → Editor → **Styles → Colors** sets the palette; changing the theme's light grey there fixes every block that uses it. In `theme.json` the same palette lives under `settings.color.palette`.
- **Classic theme.** Appearance → Customize → Additional CSS, for example `.entry-content .note { color: #595959; }`. Use the selector from the report page.

## Canvas

- Select the text in the Rich Content Editor and use the **text colour** button to choose a darker colour, or remove the custom colour to go back to the default, which passes.
- Avoid text over coloured table cells and highlighted backgrounds unless the pair passes.
- The editor's **Accessibility Checker** flags contrast and suggests a passing colour.

## GitHub Pages

Override the theme's colours in your own stylesheet. For most themes, create `assets/css/style.scss` that starts with

```scss
---
---
@import "{{ site.theme }}";
.page-header { background: #cc0033; }
body, .main-content { color: #222; }
```

and set the colours the report names. Check the compiled site: some themes set text colour on `.main-content` or `.page-header`, not on `body`.

## Plain HTML

Change the colours in the stylesheet, using the selector from the report page. If colours are set inline on many pages, move them into the stylesheet once. Check hover and focus colours for links as well; they are measured too.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live. The axe DevTools extension shows the measured ratio for every element, which is quicker than a full rescan while you are tuning colours.
