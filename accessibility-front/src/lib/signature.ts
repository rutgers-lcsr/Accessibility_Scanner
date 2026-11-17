// The markup elements share, as services/elements.py signature() builds it: tag and
// classes (no generated css-* classes, no positions), plus the colour pair of a contrast
// failure. Elements with one signature usually come from one template or style.
const TAG = /<\s*([a-zA-Z][a-zA-Z0-9-]*)([^>]*)>?/;
const CLASS = /\bclass\s*=\s*["']([^"']*)["']/;
const COLOURS = /foreground color: (#[0-9a-fA-F]{3,8}), background color: (#[0-9a-fA-F]{3,8})/;

export function signature(
    html: string | null | undefined,
    failureSummary: string | null | undefined
): string {
    let label = '(no markup)';
    const tag = TAG.exec(html ?? '');
    if (tag) {
        const classes = CLASS.exec(tag[2] ?? '');
        const names = classes
            ? [...new Set(classes[1].split(/\s+/).filter((c) => c && !c.startsWith('css-')))].sort()
            : [];
        label = names.length
            ? `<${tag[1].toLowerCase()} class="${names.join(' ')}">`
            : `<${tag[1].toLowerCase()}>`;
    }
    const colours = COLOURS.exec(failureSummary ?? '');
    if (colours) label += ` · ${colours[1].toLowerCase()} on ${colours[2].toLowerCase()}`;
    return label;
}
