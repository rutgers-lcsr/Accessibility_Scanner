// node --test (Node 22 strips the types of the module under test).
import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { getInitalPageSize } from './browser.ts';

const fail = () => {
    throw new Error('NS_ERROR_FAILURE');
};

// A browser window of the given width whose localStorage is `storage` (a getter, so it can
// throw). As in a browser, the bare global `localStorage` is the same as window.localStorage.
const setWindow = (innerWidth, storage) => {
    globalThis.window = {
        innerWidth,
        get localStorage() {
            return storage();
        },
    };
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, get: storage });
};

afterEach(() => {
    delete globalThis.window;
    delete globalThis.localStorage;
});

test('the saved page size wins', () => {
    setWindow(1440, () => ({ getItem: () => '50' }));
    assert.equal(getInitalPageSize(), 50);
});

test('nothing saved: sized by the window width', () => {
    setWindow(1440, () => ({ getItem: () => null }));
    assert.equal(getInitalPageSize(), 20);
    setWindow(800, () => ({ getItem: () => null }));
    assert.equal(getInitalPageSize(), 10);
});

// Firefox throws NS_ERROR_FAILURE from getItem when the site's stored data is damaged, and
// reading window.localStorage itself throws when storage is blocked. Either one used to crash
// the Websites, Reports and Domains pages, which read the page size while rendering.
test('storage that throws falls back to the window width', () => {
    setWindow(1440, () => ({ getItem: fail }));
    assert.equal(getInitalPageSize(), 20);
    setWindow(1440, fail);
    assert.equal(getInitalPageSize(), 20);
});

test('on the server: the default', () => {
    assert.equal(getInitalPageSize(), 5);
});
