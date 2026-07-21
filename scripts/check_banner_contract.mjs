import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (path) => fs.readFileSync(path, 'utf8');
const html = read('index.html');
const css = read('styles.css');
const script = read('script.js');

const contractCss = 'https://mintresearch.org/assets/mint-banner.css';
const contractJs = 'https://mintresearch.org/assets/mint-banner.js';
assert.equal((html.match(new RegExp(contractCss, 'g')) || []).length, 1, 'load the canonical banner stylesheet exactly once');
assert.equal((html.match(new RegExp(contractJs, 'g')) || []).length, 1, 'load the canonical banner script exactly once');
assert.ok(html.includes('<link rel="stylesheet" href="theme.css">'), 'keep the local Blind Refusal theme');
assert.ok(html.includes('<script src="theme.js" defer></script>'), 'keep the local Blind Refusal theme behavior');
assert.ok(!html.includes('https://mintresearch.org/assets/theme.css'), 'do not import the full main-site theme');
assert.ok(!html.includes('https://mintresearch.org/assets/theme.js'), 'do not import the full main-site theme script');

assert.ok(html.includes('<div class="top-banner" aria-label="MINT Lab masthead"></div>'), 'provide an empty shared-banner mount');
assert.ok(!html.includes('class="top-banner-logo"'), 'do not duplicate the canonical logo markup');
assert.ok(!html.includes('class="top-banner-minty"'), 'do not duplicate the canonical Minty image list');
assert.ok(!script.includes('syncBannerHeight'), 'the shared banner must be the only --banner-h publisher');

assert.equal((html.match(/https:\/\/mintresearch\.org\/assets\/mint-site-nav\.v1\.js/g) || []).length, 1, 'load the versioned shared navigation exactly once');
assert.ok(html.includes('id="siteNav" data-mint-site-nav'), 'provide a marked shared-navigation mount');
assert.ok(html.includes('currentId: "blind-refusal"'), 'select the canonical Blind Refusal navigation node');
assert.ok(html.includes('parentId: "blind-refusal"'), 'attach local paper anchors to Blind Refusal');

const demoPaperCues = Array.from(
  html.matchAll(/<a\s+class="demo-scroll-cue(?: demo-scroll-cue--top)?"\s+href="#paper">([\s\S]*?)<\/a>/g)
);
assert.match(html, /<section\s+id="paper"(?:\s|>)/, 'the demo cue target must exist');
assert.equal(demoPaperCues.length, 2, 'both demo scroll cues must link directly to the paper');
for (const [, cue] of demoPaperCues) {
  assert.ok(cue.includes('Scroll for demo'), 'each paper cue must retain the demo instruction');
  assert.ok(cue.includes('Paper below'), 'each paper cue must retain the paper destination label');
  assert.match(cue, /class="demo-scroll-icon" aria-hidden="true"/, 'the decorative cue arrow must stay hidden from assistive technology');
}
assert.match(css, /\.demo-scroll-cue:hover\s*\{[^}]*text-decoration:\s*none/s, 'linked demo cues must retain their non-underlined visual treatment');

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

console.log('Blind Refusal shared-site diagnostic passed: inherited banner/navigation and local paper theme.');
