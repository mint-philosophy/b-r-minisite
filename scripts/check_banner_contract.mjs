import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (path) => fs.readFileSync(path, 'utf8');
const html = read('index.html');
const css = read('styles.css');
const deploy = read('.github/workflows/deploy.yml');
const sync = read('.github/workflows/sync-from-source.yml');

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

assert.ok(deploy.includes('node scripts/check_banner_contract.mjs'), 'Pages deploy must enforce the banner contract');
assert.ok(sync.includes('node scripts/check_banner_contract.mjs'), 'source sync must enforce the banner contract');
assert.ok(!sync.includes('git add -A'), 'source sync must not stage shell/theme changes');
assert.ok(sync.includes('git add --all -- paper-content.js paper.config.json assets/paper-figures/'), 'source sync must stage only generated paper files');
assert.ok(sync.includes('actions: write'), 'source sync needs permission to dispatch the deployment workflow');
assert.ok(sync.includes('gh workflow run deploy.yml --ref main'), 'source sync must explicitly deploy GITHUB_TOKEN commits');

console.log('Blind Refusal banner contract passed: canonical main-site banner, local paper theme, guarded deployment.');
