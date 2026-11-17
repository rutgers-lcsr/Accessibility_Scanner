// node --test (Node 22 strips the types of the module under test).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { signature } from './signature.ts';

const SUMMARY =
    'Element has insufficient color contrast of 2.68 (foreground color: #39adb5, background color: #ffffff, font size: 8.9pt (11.9px), font weight: normal). Expected contrast ratio of 4.5:1';

test('matches the backend signature (services/elements.py)', () => {
    const a = signature(
        '<span class="token decorator annotation" style="color: red">@a</span>',
        SUMMARY
    );
    const b = signature('<span class="annotation token decorator css-1x2y">@b</span>', SUMMARY);
    assert.equal(a, b);
    assert.equal(a, '<span class="annotation decorator token"> · #39adb5 on #ffffff');
    assert.equal(signature('<div>', null), '<div>');
    assert.equal(signature(null, null), '(no markup)');
});
