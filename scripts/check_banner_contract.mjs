import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (path) => fs.readFileSync(path, 'utf8');
const html = read('index.html');
const css = read('styles.css');

const contractCss = 'https://mintresearch.org/assets/mint-banner.css';
const contractJs = 'https://mintresearch.org/assets/mint-banner.js';
assert.equal((html.match(new RegExp(contractCss, 'g')) || []).length, 1, 'load the canonical banner stylesheet exactly once');
assert.equal((html.match(new RegExp(contractJs, 'g')) || []).length, 1, 'load the canonical banner script exactly once');
assert.ok(html.includes('<link rel="stylesheet" href="theme.css">'), 'keep the local Blind Refusal theme');
assert.ok(html.includes('<script src="theme.js" defer></script>'), 'keep the local Blind Refusal theme behavior');
assert.ok(!html.includes('https://mintresearch.org/assets/theme.css'), 'do not import the full main-site theme');
assert.ok(!html.includes('https://mintresearch.org/assets/theme.js'), 'do not import the full main-site theme script');

assert.ok(html.includes('https://mintresearch.org/assets/mint-banner.png'), 'use the canonical logo asset');
for (const color of ['red', 'brown', 'yellow', 'green', 'teal', 'indigo', 'purple', 'cool']) {
  assert.ok(html.includes(`https://mintresearch.org/assets/minty-${color}.png`), `use canonical ${color} Minty`);
}

const forbidden = {
  '.top-banner': new Set(['padding', 'height', 'min-height']),
  '.top-banner-inner': new Set(['padding', 'gap', 'flex-direction']),
  '.top-banner-logo': new Set(['height']),
  '.top-banner-minties': new Set(['gap', 'flex-wrap']),
  '.top-banner-minty': new Set(['width', 'height'])
};
for (const match of css.matchAll(/(\.top-banner(?:-(?:inner|logo|minties|minty))?)\s*\{([^{}]*)\}/g)) {
  const [, selector, body] = match;
  const banned = forbidden[selector];
  if (!banned) continue;
  for (const declaration of body.split(';')) {
    const property = declaration.split(':', 1)[0].trim();
    assert.ok(!banned.has(property), `${selector} must not locally own ${property}`);
  }
}

console.log('Blind Refusal banner diagnostic passed: canonical main-site banner and local paper theme.');
