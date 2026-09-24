// node --test (Node 22 strips the types of the module under test).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { guideHref, isPlatformId, platformHint, reportHref, violationsHref } from './guides.ts';

test('a platform is guessed from the website categories', () => {
    assert.equal(platformHint(['cs440', 'canvas']), 'canvas');
    assert.equal(platformHint(['WordPress site']), 'wordpress');
    assert.equal(platformHint(['wp']), 'wordpress');
    assert.equal(platformHint(['GitHub pages']), 'github-pages');
    assert.equal(platformHint(['jekyll']), 'github-pages');
    assert.equal(platformHint(['labs', 'swp']), null);
    assert.equal(platformHint([]), null);
});

test('platform ids are validated', () => {
    assert.ok(isPlatformId('html') && isPlatformId('github-pages'));
    assert.ok(!isPlatformId('drupal') && !isPlatformId(null) && !isPlatformId(undefined));
});

test('links carry the rule id safely', () => {
    assert.equal(guideHref('region'), '/help/fix/region');
    assert.equal(guideHref('region', 'canvas'), '/help/fix/region?platform=canvas');
    assert.equal(guideHref('odd/rule', null), '/help/fix/odd%2Frule');
    assert.equal(
        violationsHref(7, 'image-alt'),
        '/websites/7?tab=violations&rule=image-alt#violation-image-alt'
    );
    assert.equal(reportHref(12, 'link name'), '/reports/12?rule=link%20name#violation-link%20name');
    assert.equal(reportHref(null, 'region'), null);
});
