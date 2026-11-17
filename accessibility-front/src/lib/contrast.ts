// Colour contrast in words: what axe measured, and the nearest colour that passes.

export type ContrastFailure = {
    ratio: number;
    foreground: string;
    background: string;
    expected: number;
};

const MEASURED =
    /contrast of ([\d.]+) \(foreground color: (#[0-9a-fA-F]{6}), background color: (#[0-9a-fA-F]{6})/;
const EXPECTED = /Expected contrast ratio of ([\d.]+):1/;

/** The colours and ratios in axe's color-contrast failure text; null for other text. */
export function parseContrast(summary: string | null | undefined): ContrastFailure | null {
    const measured = MEASURED.exec(summary ?? '');
    const expected = EXPECTED.exec(summary ?? '');
    if (!measured || !expected) return null;
    return {
        ratio: Number(measured[1]),
        foreground: measured[2].toLowerCase(),
        background: measured[3].toLowerCase(),
        expected: Number(expected[1]),
    };
}

function channels(hex: string): [number, number, number] {
    return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];
}

function luminance(hex: string): number {
    const [r, g, b] = channels(hex).map((v) => {
        const c = v / 255;
        return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(a: string, b: string): number {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
}

const toHex = (rgb: number[]) =>
    '#' + rgb.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');

/**
 * The nearest colour to ``foreground`` that reaches ``expected`` against ``background``:
 * mixed step by step towards black on a light background (white on a dark one), so the
 * hue stays and it gets no darker than it must.
 */
export function suggestColour(foreground: string, background: string, expected: number): string {
    const target = luminance(background) > 0.18 ? [0, 0, 0] : [255, 255, 255];
    const start = channels(foreground);
    for (let step = 1; step <= 100; step++) {
        const t = step / 100;
        const mixed = toHex(start.map((v, i) => v + (target[i] - v) * t));
        if (contrastRatio(mixed, background) >= expected + 0.05) return mixed;
    }
    return toHex(target);
}

/** One sentence a non-developer can act on, or null when the text is not a contrast failure. */
export function plainContrastFix(summary: string | null | undefined): string | null {
    const failure = parseContrast(summary);
    if (!failure) return null;
    const suggestion = suggestColour(failure.foreground, failure.background, failure.expected);
    const direction = luminance(failure.background) > 0.18 ? 'darker' : 'lighter';
    return `The text colour ${failure.foreground} on ${failure.background} is ${failure.ratio}:1; it needs ${failure.expected}:1. Use ${suggestion} or ${direction}.`;
}
