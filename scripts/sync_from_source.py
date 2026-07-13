#!/usr/bin/env python3
"""Auto-sync a minisite from its declared source (currently: arXiv).

This is the substance behind ``.github/workflows/sync-from-source.yml``. It can
also be run by hand on any machine that has ``pypdf`` and ``pillow`` installed:

    python3 scripts/sync_from_source.py

What it does, in order:
  1. Read ``paper.config.json``. If ``autoSyncFromSource`` is not exactly ``true``
     or ``source.kind`` is not ``"arxiv"``, log why and exit 0 (nothing to do).
  2. Download the CURRENT arXiv artifacts using versionless URLs (always latest):
       - e-print tarball  https://arxiv.org/e-print/<bare-id>  -> inputs.latexDir
       - PDF              https://arxiv.org/pdf/<bare-id>       -> inputs.pdf
  3. Run ``scripts/extract_paper.py`` to regenerate ``paper-content.js`` and its
     ``PAPER_META`` provenance (source hash + drift detection).
  4. Compare the freshly emitted ``sourceHash`` to the one that was already in
     ``paper-content.js``:
       - unchanged -> restore paper-content.js and figures byte-for-byte, exit 0.
       - changed   -> re-encode any changed PNGs (Pillow, optimize=True), refresh
                       the source.id version string from the arXiv API, exit 10.

Exit codes (consumed by the workflow):
    0   in sync, or sync disabled / source not arXiv  -> no commit
    10  source updated, paper-content.js regenerated   -> commit + push
    >0  error
"""

import io
import json
import re
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "paper.config.json"
EXTRACTOR = ROOT / "scripts" / "extract_paper.py"
CONTENT_JS = ROOT / "paper-content.js"
FIGURE_DIR = ROOT / "assets" / "paper-figures"

HTTP_TIMEOUT = 90  # seconds; every network call is bounded (never unbounded)
USER_AGENT = "minisite-sync/1.0 (+https://github.com/; mailto:mintlabjhu@gmail.com)"

EXIT_IN_SYNC = 0
EXIT_UPDATED = 10
EXIT_ERROR = 1


def log(msg):
    print(f"[sync] {msg}", flush=True)


def http_get(url, timeout=HTTP_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def bare_arxiv_id(source):
    """Bare id (no vN suffix) from source.id, falling back to source.url."""
    for field in (source.get("id"), source.get("url")):
        if not field:
            continue
        match = re.search(r"(\d{4}\.\d{4,5})", field)
        if match:
            return match.group(1)
    return None


def sourcehash_in_content():
    if not CONTENT_JS.exists():
        return None
    match = re.search(r'"sourceHash"\s*:\s*"([0-9a-f]+)"', CONTENT_JS.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def safe_member_path(base_dir, name):
    """Resolve a tar member name under base_dir, refusing path traversal."""
    target = (base_dir / name).resolve()
    if base_dir.resolve() not in target.parents and target != base_dir.resolve():
        raise ValueError(f"Refusing unsafe tar member path: {name}")
    return target


def download_eprint(bare_id, latex_dir):
    url = f"https://arxiv.org/e-print/{bare_id}"
    log(f"downloading e-print tarball: {url}")
    data, ctype = http_get(url)
    log(f"  got {len(data)} bytes ({ctype})")
    latex_dir.mkdir(parents=True, exist_ok=True)
    try:
        tar = tarfile.open(fileobj=io.BytesIO(data), mode="r:*")
    except tarfile.TarError as exc:
        raise RuntimeError(f"e-print payload is not a tarball: {exc}")
    count = 0
    with tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            dest = safe_member_path(latex_dir, member.name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            src = tar.extractfile(member)
            if src is None:
                continue
            dest.write_bytes(src.read())
            count += 1
    log(f"  extracted {count} files into {latex_dir}")
    return count


def download_pdf(bare_id, pdf_path):
    url = f"https://arxiv.org/pdf/{bare_id}"
    log(f"downloading PDF: {url}")
    data, ctype = http_get(url)
    if b"%PDF" not in data[:1024]:
        raise RuntimeError(f"PDF endpoint did not return a PDF ({ctype}, {len(data)} bytes)")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(data)
    log(f"  wrote {len(data)} bytes to {pdf_path}")


def snapshot_pngs():
    if not FIGURE_DIR.exists():
        return {}
    return {p: p.read_bytes() for p in sorted(FIGURE_DIR.glob("*.png"))}


def reencode_changed_pngs(before):
    """Re-encode any PNG whose bytes changed vs `before` with Pillow optimize=True.

    The extractor writes figure-1.png as a verbatim copy of the LaTeX asset
    (overspill.png) which is larger than the committed, optimized re-encode of the
    same pixels. Re-encoding normalizes it so we never commit an unoptimized figure.
    """
    from PIL import Image

    after = snapshot_pngs()
    changed = [p for p, b in after.items() if before.get(p) != b]
    for path in changed:
        with Image.open(path) as img:
            img.load()
            params = {"optimize": True}
            if img.mode == "P":
                params["bits"] = 8
            img.save(path, format="PNG", **params)
        log(f"  re-encoded (optimized) {path.relative_to(ROOT)}: "
            f"{len(after[path])} -> {path.stat().st_size} bytes")
    if not changed:
        log("  no changed PNGs to re-encode")
    return changed


def latest_arxiv_version(bare_id):
    """Best-effort: latest version string (e.g. '2604.06233v2') from the API.

    arXiv rate-limits (HTTP 429) aggressively; failure here is non-fatal.
    """
    url = f"http://export.arxiv.org/api/query?id_list={bare_id}"
    try:
        data, _ = http_get(url, timeout=HTTP_TIMEOUT)
    except Exception as exc:  # noqa: BLE001 - any failure is non-fatal here
        log(f"  arXiv API version lookup failed ({type(exc).__name__}: {exc}); keeping existing id")
        return None
    match = re.search(rf"arxiv\.org/abs/({re.escape(bare_id)}v\d+)", data.decode("utf-8", "replace"))
    if match:
        return match.group(1)
    log("  arXiv API returned no versioned id; keeping existing id")
    return None


def update_source_id(new_version):
    """Rewrite source.id in-place, preserving the file's hand formatting."""
    text = CONFIG_PATH.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r'("id"\s*:\s*")\d{4}\.\d{4,5}v\d+(")',
        rf"\g<1>{new_version}\g<2>",
        text,
        count=1,
    )
    if n and new_text != text:
        CONFIG_PATH.write_text(new_text, encoding="utf-8")
        log(f"  updated source.id -> {new_version}")
        return True
    return False


def run_extractor():
    log("running scripts/extract_paper.py")
    proc = subprocess.run(
        [sys.executable, str(EXTRACTOR), "--config", str(CONFIG_PATH)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    for line in (proc.stdout or "").splitlines():
        log(f"  extractor: {line}")
    if proc.returncode != 0:
        for line in (proc.stderr or "").splitlines():
            log(f"  extractor[err]: {line}")
        raise RuntimeError(f"extract_paper.py failed (exit {proc.returncode})")
    return proc.stdout or ""


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    flag = config.get("autoSyncFromSource")
    if flag is not True:
        log(f"autoSyncFromSource is {flag!r} (not exactly true). Source treated as "
            f"the manual source of truth; nothing to do.")
        return EXIT_IN_SYNC

    source = config.get("source") or {}
    kind = source.get("kind")
    if kind != "arxiv":
        log(f"source.kind is {kind!r}, not 'arxiv'. Auto-sync only handles arXiv; "
            f"nothing to do.")
        return EXIT_IN_SYNC

    bare_id = bare_arxiv_id(source)
    if not bare_id:
        log("could not parse a bare arXiv id from source.id/source.url.")
        return EXIT_ERROR

    inputs = config.get("inputs") or {}
    if not inputs.get("latexDir") or not inputs.get("pdf"):
        log("config inputs.latexDir and inputs.pdf are required.")
        return EXIT_ERROR
    latex_dir = (ROOT / inputs["latexDir"]).resolve()
    pdf_path = (ROOT / inputs["pdf"]).resolve()

    log(f"bare arXiv id: {bare_id}  (config source.id={source.get('id')!r})")
    previous_hash = sourcehash_in_content()
    log(f"previous sourceHash (from paper-content.js): {previous_hash}")

    # --- download current artifacts (versionless = latest) ---
    download_eprint(bare_id, latex_dir)
    download_pdf(bare_id, pdf_path)

    # --- snapshot committed outputs so we can byte-restore on an in-sync run ---
    content_before = CONTENT_JS.read_bytes() if CONTENT_JS.exists() else None
    pngs_before = snapshot_pngs()

    # --- regenerate ---
    run_extractor()
    new_hash = sourcehash_in_content()
    log(f"new sourceHash (from paper-content.js): {new_hash}")

    if previous_hash is not None and new_hash == previous_hash:
        log(f"source unchanged (hash {new_hash}). Restoring generated files to "
            f"committed state (byte-preserving) and exiting in-sync.")
        if content_before is not None:
            CONTENT_JS.write_bytes(content_before)
        for path, data in pngs_before.items():
            if path.read_bytes() != data:
                path.write_bytes(data)
        return EXIT_IN_SYNC

    log(f"source CHANGED (was {previous_hash}, now {new_hash}). "
        f"Optimizing figures and refreshing version id.")
    reencode_changed_pngs(pngs_before)
    new_version = latest_arxiv_version(bare_id)
    if new_version and new_version != source.get("id"):
        update_source_id(new_version)
    return EXIT_UPDATED


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - top-level guard: report and fail non-zero
        log(f"ERROR: {type(exc).__name__}: {exc}")
        sys.exit(EXIT_ERROR)
