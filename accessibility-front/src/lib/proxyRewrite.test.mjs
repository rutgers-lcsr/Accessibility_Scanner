// node --test (Node 22 strips the types of the module under test).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import {
    decodeBody,
    isHtml,
    pageBase,
    PREVIEW_URL_GLOBAL,
    previewGuard,
    resolveUrl,
    rewritePage,
    textPage,
} from './proxyRewrite.ts';

const SCRIPT = 'https://a11y.example/api/reports/script/tok/';
const page = (body, url = 'https://site.edu/about') => rewritePage(body, url, SCRIPT);
const INJECT = `<meta charset="utf-8">${previewGuard('https://site.edu/about')}<script defer src="${SCRIPT}"></script>`;

test('relative links resolve like a browser would', () => {
    assert.equal(resolveUrl('img/x.png', 'https://site.edu/about'), 'https://site.edu/img/x.png');
    assert.equal(
        resolveUrl('img/x.png', 'https://site.edu/about/'),
        'https://site.edu/about/img/x.png'
    );
    assert.equal(
        resolveUrl('/css/a.css', 'https://site.edu/deep/page.html'),
        'https://site.edu/css/a.css'
    );
    assert.equal(resolveUrl('//cdn.example/a.js', 'https://site.edu/'), 'https://cdn.example/a.js');
    assert.equal(
        resolveUrl('https://other.example/x', 'https://site.edu/'),
        'https://other.example/x'
    );
    for (const untouched of [
        '#top',
        'data:image/png;base64,AAA',
        'javascript:void(0)',
        'mailto:a@b',
        '',
    ]) {
        assert.equal(resolveUrl(untouched, 'https://site.edu/'), untouched);
    }
    assert.equal(resolveUrl('http://[bad', 'https://site.edu/'), 'http://[bad');
});

test('a base href is honoured and then removed', () => {
    const html =
        '<html><head><base href="/app/"><title>x</title></head><body><img src="main.png"></body></html>';
    assert.equal(pageBase(html, 'https://site.edu/deep/page'), 'https://site.edu/app/');
    const out = page(html, 'https://site.edu/deep/page');
    assert.ok(out.includes('src="https://site.edu/app/main.png"'));
    assert.ok(!out.includes('<base'));
});

test('single-quoted attributes, srcset, poster and css urls are rewritten', () => {
    const out = page(
        `<html><head><style>.a{background:url(/bg.png)} .b{background:url("../b.png")}</style></head>` +
            `<body><img src='pics/one.png' srcset="pics/one.png 1x,\n pics/two.png 2x"><video poster="p.jpg"></video>` +
            `<div style="background: url('i.svg')"></div></body></html>`
    );
    assert.ok(out.includes(`src='https://site.edu/pics/one.png'`));
    assert.ok(
        out.includes('srcset="https://site.edu/pics/one.png 1x, https://site.edu/pics/two.png 2x"')
    );
    assert.ok(out.includes('poster="https://site.edu/p.jpg"'));
    assert.ok(out.includes('url(https://site.edu/bg.png)'));
    assert.ok(out.includes('url("https://site.edu/b.png")'));
    assert.ok(out.includes(`url('https://site.edu/i.svg')`));
});

test('only scripts that navigate away are removed, one script at a time', () => {
    const out = page(
        '<html><head><script src="/app.js"></script>' +
            '<script>gtag("config", {page: location.href, path: window.location.pathname});</script>' +
            '<script>if (top !== self) top.location = self.location;</script>' +
            '<script>window.location.replace("https://elsewhere.example/");</script>' +
            '<script>state.location = "x"; location.hash = "#y";</script>' +
            '<link rel="stylesheet" href="/s.css"></head><body></body></html>'
    );
    assert.ok(out.includes('src="https://site.edu/app.js"'));
    assert.ok(out.includes('gtag("config"'));
    assert.ok(out.includes('state.location = "x"'));
    assert.ok(!out.includes('top.location = self.location'));
    assert.ok(!out.includes('elsewhere.example'));
    assert.equal((out.match(/Removed redirect script/g) ?? []).length, 2);
    assert.ok(out.includes('href="https://site.edu/s.css"'));
});

test('meta refresh, meta CSP and the charset declaration go; ours comes in', () => {
    const out = page(
        '<html><head><meta http-equiv="refresh" content="0;url=/x">' +
            `<meta http-equiv='Content-Security-Policy' content="script-src 'self'">` +
            '<meta http-equiv="content-type" content="text/html; charset=iso-8859-1"><meta charset="iso-8859-1">' +
            '<link rel="icon" href="/f.ico"></head><body>hi</body></html>'
    );
    assert.ok(
        !out.includes('refresh') &&
            !out.includes('Content-Security-Policy') &&
            !out.includes('iso-8859-1')
    );
    assert.ok(!out.includes('f.ico'));
    assert.ok(out.startsWith(`<html><head>${INJECT}`));
});

test('a page without a head, or without html, still gets the script', () => {
    assert.ok(page('<html><body>x</body></html>').includes(`<html><head>${INJECT}</head><body>`));
    assert.ok(page('<p>fragment</p>').startsWith('<head><meta charset="utf-8">'));
    assert.ok(!page('<header>site</header>').includes('<header><meta'));
});

test('integrity and crossorigin leave script and link tags but not the text', () => {
    const out = page(
        '<html><head><script src="https://cdn.example/a.js" integrity="sha384-abc" crossorigin="anonymous"></script>' +
            `<link rel="stylesheet" href="/s.css" integrity='sha384-x' crossorigin></head><body>data integrity matters</body></html>`
    );
    assert.ok(out.includes('<script src="https://cdn.example/a.js"></script>'));
    assert.ok(out.includes('<link rel="stylesheet" href="https://site.edu/s.css">'));
    assert.ok(out.includes('data integrity matters'));
});

test('module scripts are served through the asset proxy', () => {
    const out = page(
        '<html><head><script type="module" src="/js/main.js"></script><link rel="modulepreload" href="/js/chunk.js"></head><body></body></html>'
    );
    assert.ok(out.includes('src="/proxy/asset/https/site.edu/js/main.js"'));
    assert.ok(out.includes('href="/proxy/asset/https/site.edu/js/chunk.js"'));
});

test('bodies are decoded with their own charset', () => {
    const latin1 = new Uint8Array([0x63, 0x61, 0x66, 0xe9]); // "café" in ISO-8859-1
    assert.equal(decodeBody(latin1, 'text/html; charset=ISO-8859-1'), 'café');
    const withMeta = new TextEncoder().encode('<meta charset="utf-8"><p>naïve</p>');
    assert.equal(decodeBody(withMeta, 'text/html'), '<meta charset="utf-8"><p>naïve</p>');
    assert.equal(decodeBody(latin1, 'text/html; charset=no-such-charset'), 'caf�');
});

test('what counts as html, and how plain text is shown', () => {
    assert.ok(isHtml('text/html; charset=utf-8', ''));
    assert.ok(isHtml('', '<!DOCTYPE html><html>'));
    assert.ok(!isHtml('application/json', '{"a": "<html>"}'));
    assert.ok(textPage('<b>&').includes('<pre>&lt;b&gt;&amp;</pre>'));
});

/** Runs the guard's script against a fake window; returns what it did. */
function runGuard(pageUrl) {
    const calls = { replaced: [], listener: null };
    const context = {
        location: { origin: 'https://a11y.example', href: 'https://a11y.example/proxy?report=1' },
        history: { state: null, replaceState: (_, __, url) => calls.replaced.push(url) },
        navigation: {
            addEventListener: (type, fn) => type === 'navigate' && (calls.listener = fn),
        },
    };
    context.window = context;
    const code = /<script>([\s\S]*)<\/script>/.exec(previewGuard(pageUrl))[1];
    vm.runInNewContext(code, context);
    const navigate = (event) => {
        let prevented = false;
        calls.listener({ cancelable: true, ...event, preventDefault: () => (prevented = true) });
        return prevented;
    };
    return { replaced: calls.replaced, navigate, previewUrl: context[PREVIEW_URL_GLOBAL] };
}

test('the guard keeps the /proxy address for the report script', () => {
    assert.equal(runGuard('https://site.edu/x').previewUrl, 'https://a11y.example/proxy?report=1');
});

test('the guard moves the page to its own path', () => {
    assert.deepEqual(runGuard('https://site.edu/view/cs344/?tab=1#top').replaced, [
        'https://a11y.example/view/cs344/?tab=1',
    ]);
    assert.deepEqual(runGuard('https://site.edu').replaced, ['https://a11y.example/']);
});

test('the guard cancels only navigations the page starts itself', () => {
    const { navigate } = runGuard('https://site.edu/');
    const away = { destination: { sameDocument: false, url: 'https://site.edu/' } };
    assert.equal(navigate({ ...away, userInitiated: false }), true);
    assert.equal(navigate({ ...away, userInitiated: true }), false);
    assert.equal(navigate({ ...away, userInitiated: false, cancelable: false }), false);
    // Client-side routing (pushState) stays within the document.
    assert.equal(
        navigate({
            userInitiated: false,
            destination: { sameDocument: true, url: 'https://a11y.example/x' },
        }),
        false
    );
});

test('the guard works without the Navigation API', () => {
    const context = {
        location: { origin: 'https://a11y.example' },
        history: { state: null, replaceState: () => {} },
    };
    context.window = context;
    const code = /<script>([\s\S]*)<\/script>/.exec(previewGuard('https://site.edu/'))[1];
    assert.doesNotThrow(() => vm.runInNewContext(code, context));
});

test('the guard cannot be closed early by the page URL', () => {
    const guard = previewGuard('https://site.edu/a?q=</script><script>alert(1)</script>');
    assert.equal(guard.match(/<\/script>/gi).length, 1);
    assert.ok(guard.endsWith('</script>'));
});

test('the guard runs before any of the page scripts and survives the redirect filter', () => {
    const out = page(
        '<html><head><script>var early = 1;</script><script src="/app.js"></script></head><body></body></html>'
    );
    assert.ok(out.indexOf(previewGuard('https://site.edu/about')) >= 0);
    assert.ok(out.indexOf('replaceState') < out.indexOf('var early'));
});
