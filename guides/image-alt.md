---
title: Give every image an alt text
impact: critical
summary: Each image needs an alt attribute that says what the image is for, or an empty one when it is only decoration, so screen readers can describe it or skip it.
wcag: 1.1.1
deque: https://dequeuniversity.com/rules/axe/4.10/image-alt
---

## What this means

An `<img>` without an `alt` attribute has no text alternative. A screen reader then reads the file name ("IMG_2041.jpg") or says nothing, and the visitor has no idea what the picture showed.

`alt=""` (present but empty) is not the same as missing: it tells the screen reader the image is decorative and can be skipped. That is the right choice for spacers, borders and pictures that repeat what the text already says.

## Why it matters

Photos of people, diagrams, charts and image buttons carry meaning; without alt text that meaning is lost to anyone who cannot see the image, including people using a screen reader or a slow connection. WCAG 1.1.1 (Non-text Content).

## Before

```html
<img src="prof.jpg">
<img src="divider.png">
<a href="/schedule"><img src="calendar-icon.png"></a>
```

## After

```html
<img src="prof.jpg" alt="Sesh Venugopal">
<img src="divider.png" alt="">
<a href="/schedule"><img src="calendar-icon.png" alt="Schedule"></a>
```

Write what the image conveys, not "image of". For an image inside a link, describe where the link goes. For a chart, give the takeaway in the alt ("Enrollment rose from 120 to 310 between 2020 and 2025") and put the data in the text.

## WordPress

- Open the image in the **Media Library** and fill in **Alternative Text**; every place the image is used picks it up.
- In the block editor, the Image block's settings panel has the same **Alternative text** field. Leave it empty only for decorative images, and the block prints `alt=""`.
- Featured images and logos take their alt from the media item too; theme logos usually use the site name.
- Images inserted by plugins (sliders, galleries) have their own alt fields; check the plugin's settings for the slide or gallery item.

## Canvas

- Select the image in the Rich Content Editor, open **Image Options**, and fill in **Alt Text**, or tick **Decorative Image** for pictures that add nothing.
- The editor's **Accessibility Checker** lists every image without alt text on the page and lets you fix them one after another.
- Images in files uploaded from Word or PowerPoint need their alt text re-entered after the import.

## GitHub Pages

In markdown, the text in the square brackets is the alt text:

```markdown
![Sesh Venugopal](/images/prof.jpg)
![](/images/divider.png)
```

Empty brackets give `alt=""`, which is right for decoration. For images written as HTML in the markdown, or in the theme's includes, add the `alt` attribute directly.

## Plain HTML

Add `alt="…"` to every `<img>`. Search the pages for `<img` and check each one has it. Templates and includes that print logos or icons are a common source; fix them once. Image buttons (`<input type="image">`) need `alt` as well.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live, or the axe DevTools extension on the page. The scan counts each image separately, so a page clears when every image on it has an alt attribute.
