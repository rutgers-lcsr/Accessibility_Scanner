'use client';

import { useEffect } from 'react';

// This app signs in through CAS, on another site; none of its own fields is a login. Password
// managers still guessed fields like "Business owner" or "Users" were usernames and popped up
// over the forms. Each field gets the opt-out every major manager reads, including fields that
// render later (modals, drawers, tabs). A real password field is left alone.
const OPT_OUT: Record<string, string> = {
    autocomplete: 'off',
    'data-1p-ignore': 'true', // 1Password
    'data-lpignore': 'true', // LastPass
    'data-bwignore': 'true', // Bitwarden
    'data-form-type': 'other', // Dashlane
};

function optOut(root: ParentNode) {
    root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>('input, textarea').forEach(
        (field) => {
            if (field instanceof HTMLInputElement && field.type === 'password') return;
            if (field.dataset.bwignore) return;
            for (const [name, value] of Object.entries(OPT_OUT)) field.setAttribute(name, value);
        }
    );
}

export default function NoPasswordManagers() {
    useEffect(() => {
        optOut(document);
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                mutation.addedNodes.forEach((node) => {
                    if (node instanceof HTMLElement) {
                        if (node.matches('input, textarea')) optOut(node.parentElement ?? node);
                        else optOut(node);
                    }
                });
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
        return () => observer.disconnect();
    }, []);
    return null;
}
