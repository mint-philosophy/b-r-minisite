const mobileMenuBtn = document.getElementById("mobileMenuBtn");
const sidebar = document.getElementById("sidebar");
const mobileOverlay = document.getElementById("mobileOverlay");
const sidebarToggle = document.getElementById("sidebarToggle");
const banner = document.querySelector(".top-banner");
const compactBanner = document.getElementById("compactBanner");
const searchTrigger = document.getElementById("searchTrigger");
const searchOverlay = document.getElementById("searchOverlay");
const searchInput = document.getElementById("searchInput");
const searchResults = document.getElementById("searchResults");
const paperText = document.getElementById("paperText");
const paperFootnotes = document.getElementById("paperFootnotes");
const readingLayout = document.querySelector(".reading-layout");
const leftRail = document.querySelector(".left-rail");
const rightRail = document.querySelector(".right-rail");
const demoStory = document.querySelector(".demo-story");
const demoCanvas = document.querySelector(".demo-canvas");
const backToTextCue = document.getElementById("backToTextCue");
const PAPER_RAIL_COLLAPSE_WIDTH = 1280;
let citationReturnTarget = null;
let citationReturnScrollY = 0;

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function paragraphClass(paragraph) {
  if (/^Figure \d+:/.test(paragraph)) return "figure-caption";
  if (/^Table \d+:/.test(paragraph)) return "table-caption";
  if (/^[-][A-Za-z]/.test(paragraph)) return "list-like";
  return "";
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function linkifyUrls(value) {
  return value.replace(/https?:\/\/[^\s<]+/g, (match) => {
    const trailing = match.match(/[).,;:]+$/)?.[0] || "";
    const href = trailing ? match.slice(0, -trailing.length) : match;
    return `<a href="${href}" target="_blank" rel="noreferrer">${href}</a>${trailing}`;
  });
}

const citationAliases = Array.isArray(window.PAPER_CITATION_ALIASES)
  ? window.PAPER_CITATION_ALIASES
  : [];

function linkifyCitations(value) {
  return citationAliases.reduce((html, alias) => {
    if (!alias?.text || !alias?.refId) return html;
    const escapedAlias = escapeRegExp(escapeHtml(alias.text));
    const pattern = new RegExp(`(^|[^A-Za-z0-9])(${escapedAlias})(?=$|[^A-Za-z0-9])`, "g");
    return html.replace(pattern, (match, prefix, citation) => {
      return `${prefix}<a class="citation-link" href="#${escapeHtml(alias.refId)}">${citation}</a>`;
    });
  }, value);
}

function linkifyText(value) {
  const escaped = escapeHtml(value);
  return linkifyCitations(linkifyUrls(escaped));
}

const figuresByCaption = new Map(
  Array.isArray(window.PAPER_FIGURES)
    ? window.PAPER_FIGURES.map((figure) => [figure.captionPrefix, figure])
    : []
);

const tablesByCaption = new Map(
  Array.isArray(window.PAPER_TABLES)
    ? window.PAPER_TABLES.map((table) => [table.captionPrefix, table])
    : []
);

function renderPaperFootnotes() {
  if (!paperFootnotes || !Array.isArray(window.PAPER_FOOTNOTES)) return;

  const notes = window.PAPER_FOOTNOTES;
  paperFootnotes.hidden = notes.length === 0;
  paperFootnotes.innerHTML = notes.map((note) => `
    <p><sup>${escapeHtml(note.marker)}</sup> ${linkifyText(note.text)}</p>
  `).join("");
}

function renderFigure(figure, caption) {
  const id = figure.label ? ` id="${escapeHtml(figure.label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""))}"` : "";
  return `
    <figure${id} class="paper-figure">
      <a class="paper-figure-link" href="${escapeHtml(figure.src)}" target="_blank" rel="noreferrer" aria-label="Open ${escapeHtml(figure.label)} full size">
        <img src="${escapeHtml(figure.src)}" alt="${escapeHtml(figure.alt)}">
      </a>
      <figcaption>${linkifyText(caption)}</figcaption>
      <a class="figure-open" href="${escapeHtml(figure.src)}" target="_blank" rel="noreferrer">open full size</a>
    </figure>
  `;
}

function renderTable(table) {
  const headers = table.headers.map((header) => `<th scope="col">${escapeHtml(header)}</th>`).join("");
  const rows = table.rows.map((row) => `
    <tr>
      ${row.map((cell, index) => index === 0
        ? `<th scope="row">${escapeHtml(cell)}</th>`
        : `<td>${escapeHtml(cell)}</td>`).join("")}
    </tr>
  `).join("");

  return `
    <figure class="paper-table">
      <figcaption>${escapeHtml(table.caption)}</figcaption>
      <div class="table-scroll" tabindex="0" aria-label="${escapeHtml(table.label)} table">
        <table>
          <thead><tr>${headers}</tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </figure>
  `;
}

function renderReferences(section) {
  const references = Array.isArray(window.PAPER_REFERENCES) && window.PAPER_REFERENCES.length
    ? window.PAPER_REFERENCES
    : (section.paragraphs || []).map((entry, index) => ({
        id: `ref-${index + 1}`,
        text: entry,
      }));

  return `<ol class="reference-list">${references.map((reference) => {
    const id = reference.id ? ` id="${escapeHtml(reference.id)}"` : "";
    return `<li${id}>${linkifyUrls(escapeHtml(reference.text || ""))}</li>`;
  }).join("")}</ol>`;
}

function sectionNumber(section) {
  const title = section.title || "";
  const numericMatch = title.match(/^(\d+(?:\.\d+)*)\b/);
  const appendixMatch = title.match(/^([A-Z](?:\.\d+)*)\b/);

  if (section.id === "abstract") return "00";
  if (section.id === "references") return "refs";
  if (numericMatch) {
    const parts = numericMatch[1].split(".");
    return [parts[0].padStart(2, "0"), ...parts.slice(1)].join(".");
  }
  if (appendixMatch) return appendixMatch[1];
  return "";
}

function isAppendixSection(section) {
  return /^[A-Z](?:\b|\.)/.test(section.title || "");
}

function renderPaperSections() {
  if (!paperText || !Array.isArray(window.PAPER_SECTIONS)) return;

  let appendixStarted = false;
  paperText.innerHTML = window.PAPER_SECTIONS.map((section, index) => {
    const appendixSection = isAppendixSection(section);
    const appendixDivider = appendixSection && !appendixStarted
      ? `
        <section class="appendix-divider" id="appendix" aria-labelledby="appendix-title">
          <div class="section-num">appendix</div>
          <h2 id="appendix-title">Appendix</h2>
        </section>
      `
      : "";

    if (appendixSection) appendixStarted = true;

    const sectionBody = section.id === "references"
      ? renderReferences(section)
      : section.paragraphs.map((paragraph) => {
          const table = Array.from(tablesByCaption.entries()).find(([captionPrefix, candidate]) => {
            return candidate.sectionId === section.id && paragraph.startsWith(captionPrefix);
          })?.[1];

          if (table) {
            return renderTable(table);
          }

          const figure = Array.from(figuresByCaption.entries()).find(([captionPrefix, candidate]) => {
            return candidate.sectionId === section.id && paragraph.startsWith(captionPrefix);
          })?.[1];

          if (figure) {
            return renderFigure(figure, paragraph);
          }

          const klass = paragraphClass(paragraph);
          const classAttr = klass ? ` class="${klass}"` : "";
          return `<p${classAttr}>${linkifyText(paragraph)}</p>`;
        }).join("");

    return `
      ${appendixDivider}
      <section id="${escapeHtml(section.id)}" class="paper-section extracted-section${appendixSection ? " appendix-section" : ""}">
        <div class="section-num">${escapeHtml(sectionNumber(section))}</div>
        <h2>${escapeHtml(section.title)}</h2>
        ${sectionBody}
      </section>
    `;
  }).join("");
}

function renderAboutSource() {
  const aboutSource = document.getElementById("aboutSource");
  if (!aboutSource) return;

  const meta = window.PAPER_META;
  const source = meta && meta.source;
  if (!source) {
    aboutSource.hidden = true;
    return;
  }

  let lead;
  if (source.kind === "private") {
    const version = meta.sourceHash ? ` (version ${escapeHtml(meta.sourceHash)})` : "";
    lead = `This article is based on a privately provided source${version}.`;
  } else {
    const label = escapeHtml(source.label || source.kind || "the original source");
    const url = source.url || "";
    const link = url
      ? `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(url)}</a>`
      : "";
    lead = `This article is based on the version hosted at ${label}, url: ${link}`;
  }

  let updated = "";
  if (meta.retrievedAt) {
    const date = new Date(meta.retrievedAt);
    if (!Number.isNaN(date.getTime())) {
      const formatted = date.toLocaleString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        timeZoneName: "short"
      });
      const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const zoneSuffix = timeZone ? ` (${escapeHtml(timeZone)})` : "";
      updated = `<p>Last updated from that source at ${escapeHtml(formatted)}${zoneSuffix}</p>`;
    }
  }

  aboutSource.innerHTML = `<p>${lead}</p>${updated}`;
}

renderPaperFootnotes();
renderPaperSections();
renderAboutSource();

document.addEventListener("click", (event) => {
  const citationLink = event.target.closest("a.citation-link");
  if (!citationLink || !backToTextCue) return;

  citationReturnTarget = citationLink;
  citationReturnScrollY = window.scrollY;
  window.setTimeout(() => {
    backToTextCue.hidden = false;
  }, 80);
});

backToTextCue?.addEventListener("click", () => {
  if (citationReturnTarget?.isConnected) {
    citationReturnTarget.scrollIntoView({ block: "center" });
    citationReturnTarget.focus({ preventScroll: true });
  } else {
    window.scrollTo({ top: citationReturnScrollY, behavior: "smooth" });
  }

  if (window.location.hash.startsWith("#ref-")) {
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  }
  backToTextCue.hidden = true;
});

function scrollToCurrentHash() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get("section") || window.location.hash.slice(1);
  if (!id) return;
  const target = document.getElementById(decodeURIComponent(id));
  if (target) {
    target.scrollIntoView({ block: "start" });
    const applyHashActive = () => {
      updateStatus();
      const activeHref = target.id.startsWith("ref-") ? "#references" : `#${target.id}`;
      document.querySelectorAll(".nav-link, .left-rail a").forEach((link) => {
        const active = link.getAttribute("href") === activeHref;
        link.classList.toggle("active", active);
        if (active) link.classList.remove("active-parent");
      });
    };
    setTimeout(applyHashActive, 0);
    setTimeout(applyHashActive, 120);
    setTimeout(applyHashActive, 900);
  }
}

if (window.location.hash || window.location.search) {
  setTimeout(scrollToCurrentHash, 0);
}

const generatedSearchItems = Array.isArray(window.PAPER_SECTIONS)
  ? window.PAPER_SECTIONS.map((section) => ({
      title: section.title,
      desc: "Extracted paper section",
      href: `#${section.id}`
    }))
  : [];

const searchIndex = [
  { title: "Demo", desc: "Scroll-driven user, rule, and robot refusal animation", href: "#demo" },
  { title: "Paper", desc: "Title, authors, arXiv, PDF, GitHub", href: "#paper" },
  { title: "About", desc: "Site credit and citation", href: "#about-site" },
  ...generatedSearchItems
];

function closeMobileMenu() {
  sidebar?.classList.remove("open");
  mobileOverlay?.classList.remove("open");
}

mobileMenuBtn?.addEventListener("click", () => {
  sidebar?.classList.toggle("open");
  mobileOverlay?.classList.toggle("open");
});

mobileOverlay?.addEventListener("click", closeMobileMenu);
sidebar?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeMobileMenu);
});

function setCompactBanner(visible) {
  document.body.classList.toggle("compact-banner-visible", visible);
  compactBanner?.setAttribute("aria-hidden", visible ? "false" : "true");
}

if (banner && compactBanner) {
  if ("IntersectionObserver" in window) {
    const bannerObserver = new IntersectionObserver(([entry]) => {
      setCompactBanner(!entry.isIntersecting);
    });
    bannerObserver.observe(banner);
  } else {
    const updateCompactBanner = () => {
      setCompactBanner(banner.getBoundingClientRect().bottom <= 0);
    };
    updateCompactBanner();
    window.addEventListener("scroll", updateCompactBanner, { passive: true });
  }
}

window.addEventListener("load", () => {
  updatePaperRails();
  setTimeout(scrollToCurrentHash, 50);
});

function setRailVariable(name, value) {
  document.documentElement.style.setProperty(name, `${Math.round(value)}px`);
}

function measureRailColumns() {
  if (!leftRail || !rightRail) return null;
  const wasFixed = document.body.classList.contains("paper-rails-fixed");
  const notesWereFixed = document.body.classList.contains("paper-notes-fixed");
  if (wasFixed) document.body.classList.remove("paper-rails-fixed");
  if (notesWereFixed) document.body.classList.remove("paper-notes-fixed");

  const leftRect = leftRail.getBoundingClientRect();
  const rightRect = rightRail.getBoundingClientRect();

  if (wasFixed) document.body.classList.add("paper-rails-fixed");
  if (notesWereFixed) document.body.classList.add("paper-notes-fixed");

  return { leftRect, rightRect };
}

function updatePaperRails() {
  if (!readingLayout || !leftRail || !rightRail || window.innerWidth <= PAPER_RAIL_COLLAPSE_WIDTH) {
    document.body.classList.remove("paper-rails-fixed");
    document.body.classList.remove("paper-notes-fixed");
    return;
  }

  const bannerHeight = banner ? banner.getBoundingClientRect().height : 0;
  const statusHeight = document.querySelector(".statusline")?.getBoundingClientRect().height || 0;
  const top = Math.max(18, bannerHeight + 18);
  const height = Math.max(220, window.innerHeight - top - statusHeight - 18);
  const layoutRect = readingLayout.getBoundingClientRect();
  const demoRect = demoStory?.getBoundingClientRect();
  const shouldFixMap = demoRect ? demoRect.bottom > 0 || layoutRect.bottom > 0 : layoutRect.bottom > 0;
  const shouldFixNotes = layoutRect.top <= top && layoutRect.bottom >= top + height;

  if (!shouldFixMap) {
    document.body.classList.remove("paper-rails-fixed");
    document.body.classList.remove("paper-notes-fixed");
    return;
  }

  const railRects = measureRailColumns();
  if (!railRects) return;

  setRailVariable("--paper-rail-top", top);
  setRailVariable("--paper-rail-height", height);
  setRailVariable("--right-rail-left", railRects.rightRect.left);
  setRailVariable("--right-rail-width", railRects.rightRect.width);

  // The left rail is now a permanent fixed sidebar (nav.sidebar); it is never
  // promoted from the reading-layout. Only the right notes rail fixes on wide
  // screens once the paper column fully spans the viewport.
  document.body.classList.remove("paper-rails-fixed");
  document.body.classList.toggle("paper-notes-fixed", shouldFixNotes);
}

function updateDemoStory() {
  if (!demoStory || !demoCanvas) {
    document.body.classList.remove("demo-canvas-fixed");
    return;
  }

  const rect = demoStory.getBoundingClientRect();
  const canvasHeight = demoCanvas.offsetHeight;
  const storyTop = demoStory.offsetTop;
  const scrollDistance = Math.round(Math.max(window.innerHeight * 2.1, 1650));
  const paperHold = Math.round(Math.max(window.innerHeight * 0.7125, window.innerHeight - canvasHeight + 390, 465));
  const stickyTop = Math.max(0, window.innerHeight - canvasHeight - 1);
  const progress = Math.min(Math.max((window.scrollY - storyTop) / scrollDistance, 0), 1);
  const clamp01 = (value) => Math.min(Math.max(value, 0), 1);
  const smoothstep = (start, end, value) => {
    const t = clamp01((value - start) / (end - start));
    return t * t * (3 - 2 * t);
  };
  const requestProgress = smoothstep(0.10, 0.28, progress);
  const responseProgress = smoothstep(0.58, 0.72, progress);
  const refusalProgress = smoothstep(0.66, 0.78, progress);
  const questionProgress = smoothstep(0.34, 0.44, progress);
  const refuseUnderlineProgress = smoothstep(0.70, 0.84, progress);
  const phase = refusalProgress > 0.02 ? 3 : responseProgress > 0.02 ? 2 : requestProgress > 0.02 ? 1 : 0;
  const releaseStart = 0.98;
  const releaseEnd = 1;
  const releaseRatio = Math.min(Math.max((progress - releaseStart) / (releaseEnd - releaseStart), 0), 1);
  const contentOpacity = 1;
  const responseRowOpacity = Math.min(responseProgress, contentOpacity);
  const titleOpacity = 1;
  const bgOpacity = 1;
  const bounceWindow = smoothstep(0.40, 0.48, progress) * (1 - smoothstep(0.60, 0.68, progress));
  const robotJump = Math.max(0, Math.sin(progress * Math.PI * 18)) * bounceWindow;
  const demoFrame = demoStory.querySelector(".demo-player-frame");
  const frameWidth = demoFrame ? demoFrame.getBoundingClientRect().width : rect.width;
  const userMoveMax = Math.min(Math.max(frameWidth * 0.12, 28), 92);
  const userHopWindow = smoothstep(0.16, 0.24, progress) * (1 - smoothstep(0.36, 0.50, progress));
  const userHop = Math.max(0, Math.sin(progress * Math.PI * 22)) * userHopWindow;

  demoStory.dataset.phase = String(phase);
  demoStory.dataset.release = releaseRatio > 0 ? "1" : "0";
  demoStory.dataset.highlight = "0";
  demoStory.style.setProperty("--demo-content-opacity", contentOpacity.toFixed(3));
  demoStory.style.setProperty("--demo-title-opacity", titleOpacity.toFixed(3));
  demoStory.style.setProperty("--demo-bg-opacity", bgOpacity.toFixed(3));
  demoStory.style.setProperty("--response-row-opacity", responseRowOpacity.toFixed(3));
  const responseSpace = Math.min(260, Math.max(150, window.innerHeight * 0.24));
  demoStory.style.setProperty("--response-space", `${Math.round(responseProgress * responseSpace)}px`);
  demoStory.style.setProperty("--response-gap", `${Math.round(responseProgress * 22)}px`);
  demoStory.style.setProperty("--response-offset", `${Math.round((1 - responseProgress) * 18)}px`);
  demoStory.style.setProperty("--release-lift", "0px");
  demoStory.style.setProperty("--deflect-opacity", refusalProgress.toFixed(3));
  demoStory.style.setProperty("--deflect-offset", `${Math.round((1 - refusalProgress) * 16)}px`);
  demoStory.style.setProperty("--subtitle-highlight-alpha", "0");
  demoStory.style.setProperty("--demo-request", Math.min(requestProgress, contentOpacity).toFixed(3));
  demoStory.style.setProperty("--demo-response", Math.min(responseProgress, contentOpacity).toFixed(3));
  demoStory.style.setProperty("--demo-refusal", Math.min(refusalProgress, contentOpacity).toFixed(3));
  demoStory.style.setProperty("--demo-question", Math.min(questionProgress, contentOpacity).toFixed(3));
  demoStory.style.setProperty("--subtitle-refuse-progress", refuseUnderlineProgress.toFixed(3));
  demoStory.style.setProperty("--demo-subtitle-opacity", "1");
  demoStory.style.setProperty("--demo-subtitle-max", "160px");
  demoStory.style.setProperty("--demo-subtitle-margin", "18px");
  demoStory.style.setProperty("--demo-subtitle-offset", "0px");
  demoStory.style.setProperty("--demo-colon-offset", "0em");
  demoStory.style.setProperty("--user-shift-x", `${Math.round(requestProgress * userMoveMax)}px`);
  demoStory.style.setProperty("--user-hop-y", `${Math.round(userHop * -14)}px`);
  demoStory.style.setProperty("--robot-jump-y", `${Math.round(robotJump * -18)}px`);
  demoStory.style.setProperty("--demo-refusal-scale", (0.82 + refusalProgress * 0.18).toFixed(3));
  document.documentElement.style.setProperty("--demo-progress", progress.toFixed(3));
  demoStory.style.setProperty("--demo-canvas-height", `${Math.round(canvasHeight)}px`);
  demoStory.style.setProperty("--demo-scroll-distance", `${scrollDistance}px`);
  demoStory.style.setProperty("--demo-paper-hold", `${paperHold}px`);
  demoStory.style.setProperty("--demo-sticky-top", `${Math.round(stickyTop)}px`);
  document.body.classList.remove("demo-canvas-fixed");
}

if (localStorage.getItem("sidebar-collapsed") === "1") {
  document.body.classList.add("sidebar-collapsed");
  if (sidebarToggle) sidebarToggle.textContent = "»";
}

sidebarToggle?.addEventListener("click", () => {
  const collapsed = document.body.classList.toggle("sidebar-collapsed");
  sidebarToggle.textContent = collapsed ? "»" : "«";
  localStorage.setItem("sidebar-collapsed", collapsed ? "1" : "0");
  setTimeout(syncBannerHeight, 350);
});

function openSearch() {
  searchOverlay?.classList.add("open");
  renderSearchResults("");
  searchInput?.focus();
}

function closeSearch() {
  searchOverlay?.classList.remove("open");
}

function renderSearchResults(query) {
  if (!searchResults) return;
  const q = query.trim().toLowerCase();
  const hits = searchIndex.filter((item) => {
    return !q || item.title.toLowerCase().includes(q) || item.desc.toLowerCase().includes(q);
  });

  searchResults.innerHTML = hits.map((item) => `
    <a class="sr-item" href="${item.href}">
      <div class="sr-title">${item.title}</div>
      <div class="sr-desc">${item.desc}</div>
    </a>
  `).join("");

  searchResults.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeSearch);
  });
}

searchTrigger?.addEventListener("click", openSearch);
searchOverlay?.addEventListener("click", (event) => {
  if (event.target === searchOverlay) closeSearch();
});
searchInput?.addEventListener("input", () => renderSearchResults(searchInput.value));

document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    if (searchOverlay?.classList.contains("open")) {
      closeSearch();
    } else {
      openSearch();
    }
  }

  if (event.key === "Escape") {
    closeSearch();
  }
});

const statusSection = document.getElementById("statusSection");
const statusSectionTop = document.getElementById("statusSectionTop");
const statusBar = document.getElementById("statusBar");
const statusPct = document.getElementById("statusPct");
const tokenDisplay = document.getElementById("tokenDisplay");
const navLinks = Array.from(document.querySelectorAll(".nav-link"));
const navPages = Array.from(document.querySelectorAll(".nav-pages a.nav-page"));
const railLinks = Array.from(document.querySelectorAll(".left-rail a"));
const sections = Array.from(document.querySelectorAll("section[id]"));
const barLength = 16;
const mainEl = document.querySelector("main");
const totalChars = mainEl ? mainEl.textContent.length : 0;

function groupedHref(id, links) {
  const exact = `#${id}`;
  if (links.some((link) => link.getAttribute("href") === exact)) return exact;
  if (/^3(?:-|$)/.test(id)) return "#3-methods";
  if (/^4(?:-|$)/.test(id)) return "#4-results";
  if (/^5(?:-|$)/.test(id)) return "#5-discussion";
  if (/^6(?:-|$)/.test(id)) return "#6-conclusion";
  if (/^a(?:-|$)/.test(id)) return "#a-taxonomy-details";
  if (/^b(?:-|$)/.test(id)) return "#b-gate-prompts";
  if (/^c(?:-|$)/.test(id)) return "#c-evaluation-prompt";
  if (/^d(?:-|$)/.test(id)) return "#d-example-exchanges-from-dataset";
  if (/^e(?:-|$)/.test(id)) return "#e-detailed-results";
  if (id === "about-site") return "#about-site";
  return exact;
}

function updateStatus() {
  updatePaperRails();
  updateDemoStory();

  const scrollable = document.documentElement.scrollHeight - window.innerHeight;
  const ratio = scrollable > 0 ? Math.min(window.scrollY / scrollable, 1) : 0;
  const pct = Math.round(ratio * 100);
  const filled = Math.round(ratio * barLength);
  const empty = barLength - filled;

  if (statusBar) {
    statusBar.innerHTML = "▓".repeat(filled) + `<span class="bar-empty">${"░".repeat(empty)}</span>`;
  }

  if (statusPct) {
    statusPct.textContent = `${pct}%`;
  }

  if (tokenDisplay && totalChars > 0) {
    const tokens = Math.round((totalChars * ratio) / 4);
    const tokenText = tokens >= 1000 ? `${(tokens / 1000).toFixed(1)}k` : String(tokens);
    tokenDisplay.innerHTML = `<span class="arrow">down</span> ${tokenText} tokens`;
  }

  let current = sections[0]?.id || "top";
  sections.forEach((section) => {
    if (section.getBoundingClientRect().top <= 180) {
      current = section.id;
    }
  });

  if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 4) {
    current = sections[sections.length - 1]?.id || current;
  }

  if (window.location.hash.startsWith("#ref-")) {
    current = "references";
  }

  if (statusSection) {
    statusSection.textContent = current;
  }

  if (statusSectionTop) {
    statusSectionTop.textContent = current;
  }

  const navHref = groupedHref(current, navLinks);
  const railHref = groupedHref(current, railLinks);

  navLinks.forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === navHref);
    link.classList.toggle(
      "active-parent",
      link.getAttribute("href") === "#appendix" && /^(appendix|[abcde](?:-|$))/.test(current)
    );
  });

  // Page-group accordion (Repo A behaviour): mark the active nav-page group,
  // set its glyph to ❯ (inactive ▸), expand its sibling .nav-sections and
  // collapse the others.
  let activePageHref;
  if (current === "about-site") {
    activePageHref = "#about-site";
  } else if (/^(appendix|[abcde](?:-|$))/.test(current)) {
    activePageHref = "#appendix";
  } else {
    activePageHref = "#top";
  }

  navPages.forEach((page) => {
    const isActivePage = page.getAttribute("href") === activePageHref;
    page.classList.toggle("active", isActivePage);
    const mark = page.querySelector(".nav-mark");
    if (mark) mark.textContent = isActivePage ? "❯" : "▸";
    const group = page.nextElementSibling;
    if (group && group.classList.contains("nav-sections")) {
      group.classList.toggle("expanded", isActivePage);
    }
  });

  railLinks.forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === railHref);
    link.classList.toggle(
      "active-parent",
      link.getAttribute("href") === "#appendix" && /^(appendix|[abcde](?:-|$))/.test(current)
    );
  });
}

window.addEventListener("scroll", updateStatus, { passive: true });
window.addEventListener("resize", () => {
  updatePaperRails();
  updateStatus();
});
updateStatus();
