// node --test (Node 22 strips the types of the module under test).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { isAppPath, proxiedAssetTarget } from './proxyTarget.ts';

const APP = 'https://a11y.example';
const target = (pathname, referer, cookie) =>
    proxiedAssetTarget(pathname, referer, cookie, APP)?.href ?? null;

test('our own routes are never forwarded', () => {
    assert.ok(isAppPath('/') && isAppPath('/reports/3') && isAppPath('/proxy'));
    assert.ok(!isAppPath('/assets/a.js') && !isAppPath('/reportsx'));
    const referer = `${APP}/proxy?url=https%3A%2F%2Fsite.edu%2F`;
    assert.equal(target('/reports/3', referer), null);
    assert.equal(target('/', referer), null);
});

test('the site comes from a /proxy or /proxy/asset Referer', () => {
    assert.equal(
        target('/assets/a.js', `${APP}/proxy?report=1&url=https%3A%2F%2Fsite.edu%2Fpage`),
        'https://site.edu/page'
    );
    assert.equal(
        target('/assets/b.js', `${APP}/proxy/asset/https/cdn.site.edu/assets/a.js`),
        'https://cdn.site.edu/'
    );
});

test('requests without a Referer, or from another origin, are left alone', () => {
    assert.equal(target('/assets/a.js', null, 'https://site.edu/'), null);
    assert.equal(target('/assets/a.js', 'https://evil.example/proxy?url=https://site.edu/'), null);
    assert.equal(target('/assets/a.js', `${APP}/proxy?url=`), null);
});

test('a preview that moved to its own path is found with the cookie', () => {
    const cookie = 'https://codepost.example/integrations';
    assert.equal(target('/assets/logo.png', `${APP}/integrations`, cookie), cookie);
    // ...also after client-side navigation to another path of the site
    assert.equal(target('/assets/logo.png', `${APP}/features`, cookie), cookie);
    // ...and when the previewed page's path is one of ours
    assert.equal(target('/assets/a.js', `${APP}/`, 'https://site.edu/'), 'https://site.edu/');
    assert.equal(
        target('/assets/a.js', `${APP}/help?x=1`, 'https://site.edu/help?x=1'),
        'https://site.edu/help?x=1'
    );
});

test('our own pages are not taken for a preview', () => {
    const cookie = 'https://site.edu/about';
    assert.equal(target('/assets/a.js', `${APP}/dashboard`, cookie), null);
    assert.equal(target('/assets/a.js', `${APP}/`, cookie), null);
    assert.equal(target('/assets/a.js', `${APP}/features`, undefined), null);
});

test('an unusable app URL or cookie forwards nothing and does not throw', () => {
    assert.equal(proxiedAssetTarget('/a.js', `${APP}/x`, 'https://site.edu/', ''), null);
    assert.equal(target('/a.js', `${APP}/x`, 'not a url'), null);
});
