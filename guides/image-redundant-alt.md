---
title: Do not repeat an image's alt text next to it
impact: minor
summary: When a caption or link already says what the image shows, the alt text should not say it again, or a screen reader reads the same words twice.
wcag: 1.1.1
deque: https://dequeuniversity.com/rules/axe/4.10/image-redundant-alt
---

## What this means

The image's `alt` text is the same as the text right beside it: a caption, or the text of the link the image sits in. A screen reader reads "Sesh Venugopal, Sesh Venugopal". The image is doing no extra work, so its alt text should be empty, or should add something the text does not say.

## Why it matters

Hearing everything twice makes a page slow and confusing to listen to. WCAG 1.1.1 (Non-text Content) asks for a text alternative that serves the same purpose, and duplication does not.

## Before

```html
<a href="/people/sesh">
  <img src="sesh.jpg" alt="Sesh Venugopal">
  Sesh Venugopal
</a>

<figure>
  <img src="lab.jpg" alt="The robotics lab">
  <figcaption>The robotics lab</figcaption>
</figure>
```

## After

```html
<a href="/people/sesh">
  <img src="sesh.jpg" alt="">
  Sesh Venugopal
</a>

<figure>
  <img src="lab.jpg" alt="Students at the benches, with the robot arm in the back">
  <figcaption>The robotics lab</figcaption>
</figure>
```

In a link, the link text names the destination, so the image can be decorative. With a caption, the alt should describe what is in the picture; the caption says what it is.

## WordPress

- Image block with a caption: open the block settings and change **Alternative text** so it describes the picture rather than repeating the caption, or leave it empty when the caption says it all.
- Image inside a link or button (a person's card linking to their profile): set the alt text to empty; the link text carries the name.
- Gallery and slider plugins often copy the title into both the caption and the alt; edit one of them in the plugin's item settings.

## Canvas

In the Rich Content Editor, select the image and open **Image Options**. If the same words appear right next to the image (as a caption line or link text), tick **Decorative Image**, or write alt text that adds something, such as what the diagram shows. The editor's **Accessibility Checker** flags alt text that repeats nearby text.

## GitHub Pages

In markdown, a linked image with the name beside it can use empty brackets:

```markdown
[![](/images/sesh.jpg) Sesh Venugopal](/people/sesh)
```

For figures written in HTML, make the alt describe the picture and let the `<figcaption>` name it.

## Plain HTML

Find the image the report names, look at the text beside it, and either empty the alt (`alt=""`) when the text already names the image, or change the alt to describe what the picture shows.

## Check your fix

Use the **Rescan this page** action next to any affected page once your change is live, or the axe DevTools extension on the page.
