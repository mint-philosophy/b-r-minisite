const mobileMenuBtn = document.getElementById("mobileMenuBtn");
const sidebar = document.getElementById("sidebar");
const mobileOverlay = document.getElementById("mobileOverlay");
const sidebarToggle = document.getElementById("sidebarToggle");
const banner = document.querySelector(".top-banner");
const searchTrigger = document.getElementById("searchTrigger");
const searchOverlay = document.getElementById("searchOverlay");
const searchInput = document.getElementById("searchInput");
const searchResults = document.getElementById("searchResults");
const paperText = document.getElementById("paperText");
const paperFootnotes = document.getElementById("paperFootnotes");
const readingLayout = document.querySelector(".reading-layout");
const leftRail = document.querySelector(".left-rail");
const rightRail = document.querySelector(".right-rail");
const hookStory = document.querySelector(".hook-story");

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

function linkifyText(value) {
  const escaped = escapeHtml(value);
  return escaped.replace(/https?:\/\/[^\s<]+/g, (match) => {
    const trailing = match.match(/[).,;:]+$/)?.[0] || "";
    const href = trailing ? match.slice(0, -trailing.length) : match;
    return `<a href="${href}" target="_blank" rel="noreferrer">${href}</a>${trailing}`;
  });
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

  const notes = window.PAPER_FOOTNOTES.filter((note) => note.marker !== "*");
  paperFootnotes.hidden = notes.length === 0;
  paperFootnotes.innerHTML = notes.map((note) => `
    <p><sup>${escapeHtml(note.marker)}</sup> ${linkifyText(note.text)}</p>
  `).join("");
}

function renderFigure(figure, caption) {
  return `
    <figure class="paper-figure">
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
      ? `<ol class="reference-list">${section.paragraphs.map((entry) => `<li>${linkifyText(entry)}</li>`).join("")}</ol>`
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

renderPaperFootnotes();
renderPaperSections();

function scrollToCurrentHash() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get("section") || window.location.hash.slice(1);
  if (!id) return;
  const target = document.getElementById(decodeURIComponent(id));
  if (target) {
    target.scrollIntoView({ block: "start" });
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
  { title: "Hook", desc: "Media Sovereignty Act user prompt", href: "#hook" },
  { title: "Responses", desc: "Deflects versus helps comparison", href: "#hook-responses" },
  { title: "Paper", desc: "Title, authors, arXiv, PDF, GitHub", href: "#paper" },
  { title: "Hook Source", desc: "Figure case and source notes", href: "#source" },
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

function syncBannerHeight() {
  if (banner) {
    document.documentElement.style.setProperty("--banner-h", `${banner.offsetHeight}px`);
  }
}

syncBannerHeight();
window.addEventListener("resize", syncBannerHeight);
window.addEventListener("load", () => {
  syncBannerHeight();
  updatePaperRails();
  setTimeout(scrollToCurrentHash, 50);
});

function setRailVariable(name, value) {
  document.documentElement.style.setProperty(name, `${Math.round(value)}px`);
}

function measureRailColumns() {
  if (!leftRail || !rightRail) return null;
  const wasFixed = document.body.classList.contains("paper-rails-fixed");
  if (wasFixed) document.body.classList.remove("paper-rails-fixed");

  const leftRect = leftRail.getBoundingClientRect();
  const rightRect = rightRail.getBoundingClientRect();

  if (wasFixed) document.body.classList.add("paper-rails-fixed");

  return { leftRect, rightRect };
}

function updatePaperRails() {
  if (!readingLayout || !leftRail || !rightRail || window.innerWidth <= 980) {
    document.body.classList.remove("paper-rails-fixed");
    return;
  }

  const bannerHeight = banner ? banner.getBoundingClientRect().height : 0;
  const statusHeight = document.querySelector(".statusline")?.getBoundingClientRect().height || 0;
  const top = Math.max(18, bannerHeight + 18);
  const height = Math.max(220, window.innerHeight - top - statusHeight - 18);
  const layoutRect = readingLayout.getBoundingClientRect();
  const shouldFix = layoutRect.top <= top && layoutRect.bottom >= top + height;

  if (!shouldFix) {
    document.body.classList.remove("paper-rails-fixed");
    return;
  }

  const railRects = measureRailColumns();
  if (!railRects) return;

  setRailVariable("--paper-rail-top", top);
  setRailVariable("--paper-rail-height", height);
  setRailVariable("--left-rail-left", railRects.leftRect.left);
  setRailVariable("--left-rail-width", railRects.leftRect.width);
  setRailVariable("--right-rail-left", railRects.rightRect.left);
  setRailVariable("--right-rail-width", railRects.rightRect.width);

  document.body.classList.add("paper-rails-fixed");
}

function updateHookStory() {
  if (!hookStory) {
    document.body.classList.remove("hook-canvas-fixed");
    return;
  }

  const rect = hookStory.getBoundingClientRect();
  const travel = Math.max(1, rect.height - window.innerHeight);
  const progress = Math.min(Math.max(-rect.top / travel, 0), 1);
  const clamp01 = (value) => Math.min(Math.max(value, 0), 1);
  const smoothstep = (start, end, value) => {
    const t = clamp01((value - start) / (end - start));
    return t * t * (3 - 2 * t);
  };
  const helpOpacity = smoothstep(0.16, 0.38, progress);
  const deflectOpacity = smoothstep(0.46, 0.62, progress);
  const highlightOpacity = smoothstep(0.72, 0.78, progress);
  const subtitleHighlightOpacity = highlightOpacity * (1 - smoothstep(0.86, 0.95, progress));
  const phase = deflectOpacity > 0.02 ? 2 : helpOpacity > 0.02 ? 1 : 0;
  const releaseStart = 0.86;
  const releaseEnd = 0.99;
  const releaseRatio = Math.min(Math.max((progress - releaseStart) / (releaseEnd - releaseStart), 0), 1);
  const contentOpacity = Math.max(0, 1 - releaseRatio);
  const responseRowOpacity = Math.min(helpOpacity, contentOpacity);
  const titleOpacity = Math.max(0, 1 - smoothstep(0.88, 0.98, progress));
  const bgOpacity = Math.max(0, 1 - releaseRatio);
  const shouldFix = rect.top <= 0 && progress < 0.99;

  hookStory.dataset.phase = String(phase);
  hookStory.dataset.release = releaseRatio > 0 ? "1" : "0";
  hookStory.dataset.highlight = highlightOpacity > 0.02 ? "1" : "0";
  hookStory.style.setProperty("--hook-content-opacity", contentOpacity.toFixed(3));
  hookStory.style.setProperty("--hook-title-opacity", titleOpacity.toFixed(3));
  hookStory.style.setProperty("--hook-bg-opacity", bgOpacity.toFixed(3));
  hookStory.style.setProperty("--response-row-opacity", responseRowOpacity.toFixed(3));
  hookStory.style.setProperty("--response-space", `${Math.round(helpOpacity * 260)}px`);
  hookStory.style.setProperty("--response-gap", `${Math.round(helpOpacity * 28)}px`);
  hookStory.style.setProperty("--response-offset", `${Math.round((1 - helpOpacity) * 18)}px`);
  hookStory.style.setProperty("--release-lift", `${Math.round(releaseRatio * -190)}px`);
  hookStory.style.setProperty("--deflect-opacity", deflectOpacity.toFixed(3));
  hookStory.style.setProperty("--deflect-offset", `${Math.round((1 - deflectOpacity) * 16)}px`);
  hookStory.style.setProperty("--subtitle-highlight-alpha", subtitleHighlightOpacity.toFixed(3));
  document.documentElement.style.setProperty("--hook-progress", progress.toFixed(3));
  document.documentElement.style.setProperty("--hook-left", `${Math.round(rect.left)}px`);
  document.documentElement.style.setProperty("--hook-width", `${Math.round(rect.width)}px`);
  document.body.classList.toggle("hook-canvas-fixed", shouldFix);
}

if (localStorage.getItem("sidebar-collapsed") === "1") {
  document.body.classList.add("sidebar-collapsed");
  if (sidebarToggle) sidebarToggle.textContent = ">";
}

sidebarToggle?.addEventListener("click", () => {
  const collapsed = document.body.classList.toggle("sidebar-collapsed");
  sidebarToggle.textContent = collapsed ? ">" : "<";
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
  return exact;
}

function updateStatus() {
  updateHookStory();
  updatePaperRails();

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
