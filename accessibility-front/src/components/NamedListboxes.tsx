'use client';

import { useEffect } from 'react';

// antd's Select renders its options in a role="listbox" element (id `<select id>_list`)
// with no accessible name and no prop to give it one, which axe reports as
// aria-input-field-name. Each such listbox is named after its own field: the field's
// <label>, else its aria-label, else its placeholder. antd re-creates the listbox while
// you type, so new ones are named as they appear.
function fieldName(field: HTMLElement | null): string | null {
    if (!field) return null;
    const labels = field instanceof HTMLInputElement ? field.labels : null;
    const text =
        (labels && labels.length ? labels[0].textContent : null) ||
        field.getAttribute('aria-label') ||
        (field.getAttribute('aria-labelledby') &&
            document.getElementById(field.getAttribute('aria-labelledby')!)?.textContent) ||
        field.getAttribute('placeholder');
    return text?.trim() || null;
}

function nameListboxes(root: ParentNode) {
    root.querySelectorAll<HTMLElement>('[role="listbox"][id$="_list"]').forEach((list) => {
        if (list.getAttribute('aria-label') || list.getAttribute('aria-labelledby')) return;
        const name = fieldName(document.getElementById(list.id.slice(0, -'_list'.length)));
        if (name) list.setAttribute('aria-label', name);
    });
}

export default function NamedListboxes() {
    useEffect(() => {
        nameListboxes(document);
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                mutation.addedNodes.forEach((node) => {
                    if (node instanceof HTMLElement) nameListboxes(node.parentElement ?? node);
                });
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
        return () => observer.disconnect();
    }, []);
    return null;
}
