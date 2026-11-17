// node --test (Node 22 strips the types of the module under test).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
    contrastRatio,
    isCodeHighlight,
    parseContrast,
    plainContrastFix,
    suggestColour,
} from './contrast.ts';

const SUMMARY =
    'Fix any of the following:\n  Element has insufficient color contrast of 2.68 (foreground color: #39adb5, background color: #ffffff, font size: 8.9pt (11.9px), font weight: normal). Expected contrast ratio of 4.5:1';

test('reads the colours and the ratios out of axe text', () => {
    assert.deepEqual(parseContrast(SUMMARY), {
        ratio: 2.68,
        foreground: '#39adb5',
        background: '#ffffff',
        expected: 4.5,
    });
    assert.equal(parseContrast('Element has no alt text'), null);
});

test('suggests the nearest colour of the same hue that passes', () => {
    const fix = suggestColour('#39adb5', '#ffffff', 4.5);
    assert.ok(contrastRatio(fix, '#ffffff') >= 4.5);
    assert.ok(contrastRatio(fix, '#ffffff') < 5.2, 'not darker than needed');
    // Light text on a dark background goes lighter.
    const light = suggestColour('#555555', '#000000', 4.5);
    assert.ok(contrastRatio(light, '#000000') >= 4.5);
});

test('says the fix in words', () => {
    const line = plainContrastFix(SUMMARY);
    assert.match(
        line,
        /^The text colour #39adb5 on #ffffff is 2\.68:1; it needs 4\.5:1\. Use #[0-9a-f]{6} or darker\.$/
    );
});

test('code-highlight colours get theme advice, not a colour per word', () => {
    const html =
        '<span class="token decorator annotation" style="color: rgb(57, 173, 181);">@test</span>';
    assert.ok(isCodeHighlight({ html }));
    assert.ok(isCodeHighlight({ selector: 'code > span:nth-child(1) > span:nth-child(3)' }));
    assert.ok(!isCodeHighlight({ html: '<div class="note">x</div>', selector: '#annotate > div' }));
    assert.match(plainContrastFix(SUMMARY, { html }), /highlighting theme/);
});
