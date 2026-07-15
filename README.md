# Blind Refusal — minisite

A static, single-paper "minisite" for **_Blind Refusal: Language Models Refuse
to Help Users Evade Unjust, Absurd, and Illegitimate Rules_** (Cameron Pattison,
Lorenzo Manuali, Seth Lazar), built by the [MINT Lab](https://www.mintresearch.org).

The site renders the paper as a readable web page (sections, figures, tables,
references) from content extracted directly out of the paper's arXiv source, with
machine-stamped provenance so a reader can see exactly which version of the source
the page was built from and when.

Source of record: [arXiv:2604.06233](https://arxiv.org/abs/2604.06233).

---

## Auto-sync from source

**This site keeps itself up to date with arXiv automatically.**

A scheduled GitHub Action (`.github/workflows/sync-from-source.yml`) runs **once a
day**. It downloads the current arXiv artifacts, regenerates the page, and — only
if the source actually changed — commits the update. On a normal day it finds the
source unchanged and does nothing.

The whole thing is gated by one conspicuous flag in `paper.config.json`, sitting
right under the `source` block:

```json
"autoSyncFromSource": true,
```

| `autoSyncFromSource` | Behaviour |
|:---|:---|
| `true` (default) | arXiv is the source of truth. The daily workflow checks arXiv and updates the site whenever the source changes. |
| `false` | **Auto-sync is off.** The daily workflow does nothing. Set this when the arXiv version is out of date, or when you want a **different source of truth** (a newer local draft, a private manuscript, `source.kind: "private"`, etc.). While it is `false`, nothing touches the committed content — you regenerate the site by hand (below). |

Set it to `false` the moment arXiv stops being authoritative for this paper. That
is the one switch that decides whether the robot or a human owns the content.

> Every minisite built from this template carries this same flag and this same
> section. If you are looking at a sibling site and wondering whether it
> auto-updates, check `autoSyncFromSource` in its `paper.config.json`.

### Manual regeneration (when `autoSyncFromSource` is `false`, or any time)

The extractor reads whatever is in `paper-assets/` — it does not go to the
network. To rebuild from a source of your choosing:

1. Put the source in `paper-assets/` matching the paths declared in
   `paper.config.json` → `inputs`:
   - `inputs.pdf` (default `paper-assets/2604.06233v1.pdf`)
   - `inputs.latexDir` (default `paper-assets/latex from arxiv/`, containing
     `main.tex`, `main.bbl`, figure assets, etc.)
2. Regenerate:
   ```bash
   pip install pypdf pillow
   python3 scripts/extract_paper.py
   ```
   This rewrites `paper-content.js` (including `PAPER_META` with a fresh
   `sourceHash` and `retrievedAt`) and re-extracts `figure-1.png`.
3. If `figure-1.png` came out larger than the committed version, re-encode it
   optimized (Pillow, `optimize=True`) so you never commit an unoptimized figure —
   `scripts/sync_from_source.py` does this automatically; by hand it's a one-liner
   with Pillow.
4. Commit the regenerated `paper-content.js` (and any changed figures).

You can also run the full sync pipeline (download + extract + compare + optimize)
on any machine:

```bash
python3 scripts/sync_from_source.py    # exit 0 = in sync, 10 = updated, >0 = error
```

It respects the `autoSyncFromSource` flag and `source.kind`, so with the flag
`false` it exits immediately without touching anything.

---

## Architecture

Everything the reader sees is driven by generated data, not hand-written HTML:

- **`paper.config.json`** — the hand-edited, per-paper metadata. Title, authors,
  the `source` declaration (`kind`/`label`/`url`/`id`), the `autoSyncFromSource`
  flag, input paths, and the figure/table/citation definitions. Nothing here is
  machine-overwritten except the `source.id` version string on an auto-sync
  update.
- **`paper-assets/`** — the raw source (arXiv PDF + LaTeX). **Git-ignored**, so CI
  always downloads it fresh; locally it holds your working copy of the source.
- **`scripts/extract_paper.py`** — reads the config + assets and generates
  `paper-content.js`. Alongside the content it emits `window.PAPER_META`:

  ```js
  window.PAPER_META = {
    source: { kind, label, url },       // url omitted when kind == "private"
    retrievedAt: "2026-07-13T01:45:00Z", // when extraction ran (UTC)
    sourceHash: "9656aea8117c"           // 12-hex SHA-256 over the source inputs
  };
  ```

  `sourceHash` is a truncated SHA-256 over every file under `inputs.latexDir` plus
  the PDF (sorted relative path + content). It identifies the exact source version
  publicly without revealing anything about a private source, and it drives **drift
  detection**: the extractor reports whether the hash is unchanged or changed vs
  the previous `PAPER_META`. That comparison is what the auto-sync workflow uses to
  decide "in sync" vs "update".
- **`scripts/sync_from_source.py`** — the substance behind the workflow:
  check-flag → download → extract → compare → optimize figures → update version id.
  Distinct exit codes (`0`/`10`/`>0`) let the thin workflow decide whether to
  commit.
- **`index.html` / `script.js` / `styles.css`** — the static shell. `script.js`
  reads the generated globals and renders the page, including the **Source** block
  in the About section (built from `PAPER_META`, with a local-timezone
  "last updated" date).

### Sidebar navigation

The primary sidebar is rendered by the versioned
`https://mintresearch.org/assets/mint-site-nav.v1.js` contract. Global labels,
URLs, ordering, glyphs, and peers therefore stay synchronized with the main
site. This repository supplies only `MintSiteNavConfig.local`: Blind Refusal's
paper anchors and Appendix nesting. The local scroll-spy refreshes its link
references after the shared renderer dispatches `mint-site-nav:rendered`.

The masthead is the deliberate exception to the self-contained runtime boundary:
`index.html` provides an empty `.top-banner` mount and loads
`https://mintresearch.org/assets/mint-banner.css` plus `mint-banner.js`. Those
banner-only files own its markup, dimensions, responsive wrapping, image list,
motion, and measured `--banner-h`. Do not import the full main-site `theme.css`
or `theme.js`, and do not reintroduce local banner internals in `styles.css`.

Typography follows the same division of labour as the other microsites:
JetBrains Mono is reserved for navigation, headings, labels, legends, metadata,
and data tables; Newsreader is used for sustained paper prose and references.

### Deployment

GitHub Pages deploys through `.github/workflows/deploy.yml`, not the legacy
publish-every-push path. Banner compatibility does not gate deployment. The
oversized-banner regression came from duplicate local banner geometry being
restored by whole-theme rollbacks, so the fix is the ownership boundary above:
only the main site's banner-only files own dimensions and assets.

The contract diagnostic checks both inherited components:

```bash
node scripts/check_banner_contract.mjs
```

The arXiv auto-sync may stage only `paper-content.js`, `paper.config.json`, and
generated paper figures. It refuses unexpected shell or theme changes instead
of sweeping them into an automated commit, then explicitly dispatches the Pages
workflow because GitHub does not start push-triggered workflows for commits made
with the workflow token.

Build order: edit `paper.config.json` and/or `paper-assets/` → run
`extract_paper.py` → open `index.html`.

---

## Local preview

No build server needed — it's a static site. Serve the directory and open it:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

(Opening `index.html` via `file://` mostly works, but a local HTTP server avoids
browser restrictions on loading the generated `paper-content.js`.)

---

## Template note

This README, the `autoSyncFromSource` flag, and the `sync-from-source.yml`
workflow are part of the **minisite template**: every per-paper minisite carries
its own `paper.config.json` + `paper-assets/`, the shared extractor, and this same
daily auto-sync automation. When cloning this into a new minisite, keep this README
section on auto-sync intact and set the flag according to whether arXiv (or another
declared source) is authoritative for that paper.
