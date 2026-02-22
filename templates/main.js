/* main.js
   - Turns each H2 (##) into a tab
   - Adds search (titles + content), results list, and <mark> highlighting
   - Keyboard nav: ArrowLeft/ArrowRight/Home/End + Enter/Space to activate
*/

(function () {
  function slugify(text) {
    return String(text)
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-");
  }

  function uniqueId(base, used) {
    let id = base;
    let i = 2;
    while (used.has(id)) {
      id = `${base}-${i++}`;
    }
    used.add(id);
    return id;
  }

  function createEl(tag, attrs = {}, children = []) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") el.className = v;
      else if (k === "html") el.innerHTML = v;
      else if (k.startsWith("aria-")) el.setAttribute(k, v);
      else if (k === "role") el.setAttribute("role", v);
      else el[k] = v;
    }
    for (const c of children) el.append(c);
    return el;
  }
  
  function clearMarks(root) {
    const marks = root.querySelectorAll("mark.search-hit");
    for (const m of marks) {
      m.replaceWith(document.createTextNode(m.textContent || ""));
    }
    root.normalize();
  }

  function highlightInElement(root, query) {
    if (!query) return;
    const q = query.toLowerCase();

    const walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode(node) {
          if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
          const p = node.parentElement;
          if (!p) return NodeFilter.FILTER_REJECT;
          const tag = p.tagName;
          if (tag === "SCRIPT" || tag === "STYLE" || tag === "NOSCRIPT") return NodeFilter.FILTER_REJECT;
          // Avoid highlighting inside existing mark tags
          if (p.closest("mark.search-hit")) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    const toProcess = [];
    while (walker.nextNode()) toProcess.push(walker.currentNode);

    for (const textNode of toProcess) {
      const text = textNode.nodeValue;
      const lower = text.toLowerCase();
      let idx = lower.indexOf(q);
      if (idx === -1) continue;

      const frag = document.createDocumentFragment();
      let lastIndex = 0;

      while (idx !== -1) {
        const before = text.slice(lastIndex, idx);
        if (before) frag.append(document.createTextNode(before));

        const match = text.slice(idx, idx + query.length);
        frag.append(createEl("mark", { class: "search-hit" }, [document.createTextNode(match)]));

        lastIndex = idx + query.length;
        idx = lower.indexOf(q, lastIndex);
      }

      const after = text.slice(lastIndex);
      if (after) frag.append(document.createTextNode(after));

      textNode.replaceWith(frag);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const main = document.querySelector("main#cv");
    if (!main) return;

    const h2s = Array.from(main.querySelectorAll("h2"));
    if (h2s.length === 0) return;

    // --------- Build shell (header + sticky UI + panels) ----------
    const usedIds = new Set();

    const shell = createEl("div", { class: "cv-shell" });
    const header = createEl("header", { class: "site-header" });
    const sticky = createEl("div", { class: "sticky-ui" });

    // ---------------- NEW: Top emoji bar (theme + quick links) ----------------
    const topbar = createEl("div", {
      class: "topbar",
      role: "navigation",
      "aria-label": "Quick links"
    });

    // Theme toggle button (☀️/🌙) with persistence
    const THEME_KEY = "cv-theme";
    const themeBtn = createEl("button", {
      class: "topbar-btn topbar-theme",
      type: "button",
      "aria-label": "Toggle theme",
      title: "Toggle theme",
      textContent: "☀️"
    });

    function applyTheme(theme) {
      document.documentElement.classList.remove("theme-light", "theme-dark");
      if (theme === "light") document.documentElement.classList.add("theme-light");
      if (theme === "dark") document.documentElement.classList.add("theme-dark");
    }

    function preferredTheme() {
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }

    function currentTheme() {
      if (document.documentElement.classList.contains("theme-dark")) return "dark";
      if (document.documentElement.classList.contains("theme-light")) return "light";
      return preferredTheme();
    }

    function updateThemeIcon() {
      const t = currentTheme();
      themeBtn.textContent = t === "dark" ? "🌙" : "☀️";
    }

    const savedTheme = localStorage.getItem(THEME_KEY);
    if (savedTheme === "light" || savedTheme === "dark") applyTheme(savedTheme);
    updateThemeIcon();

    themeBtn.addEventListener("click", () => {
      const next = currentTheme() === "dark" ? "light" : "dark";
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
      updateThemeIcon();
    });

    topbar.append(themeBtn);
        const isFrench = document.documentElement.lang === "fr";
    const languageBtn = createEl("a", {
      class: "topbar-btn",
      href: isFrench ? "../index.html" : "fr/",
      "aria-label": isFrench ? "Voir en anglais" : "Voir en français",
      title: isFrench ? "Voir en anglais" : "Voir en français",
      textContent: isFrench ? "🇬🇧" : "🇫🇷"
    });
    topbar.append(languageBtn);

    const quickLinks = [
      { href: "mailto:omar.abedelkader@inria.fr", label: isFrench ? "E-mail" : "Email", icon: "✉️" },
      { href: "https://omarabedelkader.github.io", label: isFrench ? "Site web" : "Website", icon: "🌐" },
      { href: "https://huggingface.co/omarabedelkader", label: "Hugging Face", icon: "🤗" },
      { href: "https://github.com/omarabedelkader", label: "GitHub", icon: "🐙" },
      { href: "https://ollama.com/omarabedelkader", label: "Ollama", icon: "🦙" },
      { href: "https://www.linkedin.com/in/omarabedelkader/", label: "LinkedIn", icon: "💼" },
      { href: "https://scholar.google.com/citations?hl=fr&user=Wl01zhQAAAAJ", label: isFrench ? "Google Scholar" : "Google Scholar", icon: "🎓" }
    ];

    quickLinks.forEach((l) => {
      const attrs = {
        class: "topbar-btn",
        href: l.href,
        "aria-label": l.label,
        title: l.label,
        textContent: l.icon
      };
      if (!String(l.href).startsWith("mailto:")) {
        attrs.target = "_blank";
        attrs.rel = "me noopener noreferrer";
      }
      const a = createEl("a", attrs);
      topbar.append(a);
    });
    // ------------------------------------------------------------------------

    const searchWrap = createEl("div", { class: "search-wrap" });
    const searchLabel = createEl("label", { class: "search-label", html: isFrench ? "Rechercher" : "Search" });
    const searchInput = createEl("input", {
      class: "search-input",
      type: "search",
      placeholder: isFrench ? "Rechercher dans les sections et le contenu…" : "Search sections and content…",
      autocomplete: "off",
      spellcheck: false
    });
    searchLabel.append(searchInput);

    const searchMeta = createEl("div", { class: "search-meta" });
    const searchCount = createEl("span", { class: "search-count", textContent: "" });
    const searchClear = createEl("button", { class: "search-clear", type: "button", textContent: isFrench ? "Effacer" : "Clear" });
    searchMeta.append(searchCount, searchClear);

    const results = createEl("div", { class: "search-results", role: "region", "aria-label": isFrench ? "Résultats de recherche" : "Search results" });

    searchWrap.append(searchLabel, searchMeta, results);

    const tabs = createEl("nav", {
      class: "tabs",
      role: "tablist",
       "aria-label": isFrench ? "Sections du CV" : "CV sections"
    });

    const panels = createEl("div", { class: "panels" });

    // CHANGED: topbar is first inside the sticky area
    sticky.append(topbar, searchWrap, tabs);
    shell.append(header, sticky, panels);

    // --------- Move content before first H2 into header ----------
    const firstH2 = h2s[0];
    while (main.firstChild && main.firstChild !== firstH2) {
      header.append(main.firstChild);
    }

    // --------- Build tabs/panels from each H2 block ----------
    const sections = [];
    const allH2 = Array.from(main.querySelectorAll("h2")); // (fresh, after moves)

    allH2.forEach((h2, idx) => {
      const title = (h2.textContent || `Section ${idx + 1}`).trim();
      const base = slugify(title) || `section-${idx + 1}`;
      const key = uniqueId(base, usedIds);

      const tabId = `tab-${key}`;
      const panelId = `panel-${key}`;

      const tabBtn = createEl("button", {
        class: "tab",
        type: "button",
        id: tabId,
        role: "tab",
        "aria-selected": "false",
        "aria-controls": panelId,
        tabIndex: -1,
        textContent: title
      });

      const panel = createEl("section", {
        class: "tab-panel",
        id: panelId,
        role: "tabpanel",
        "aria-labelledby": tabId
      });
      panel.hidden = true;

      // Move H2 + following siblings until next H2 into panel
      panel.append(h2);
      let node = panel.lastChild.nextSibling; // after moving h2, but it has no nextSibling in panel
      // We need to read from DOM: next sibling in main after h2
      node = panel.querySelector("h2").nextSibling; // inside panel it's empty, so use main traversal instead

      // Correct approach: walk in main from after this h2 (still in main at this moment? no, we moved it)
      // So: capture siblings before moving. We'll rebuild by scanning main nodes:
      // (We already moved h2; now repeatedly move main.firstChild until next H2)
      while (main.firstChild && !(main.firstChild.nodeType === 1 && main.firstChild.tagName === "H2")) {
        panel.append(main.firstChild);
      }

      tabs.append(tabBtn);
      panels.append(panel);
      sections.push({ title, tabBtn, panel });
    });

    // Replace main content with shell
    main.innerHTML = "";
    main.append(shell);

    function setActive(index, opts = { focus: true, highlightQuery: "" }) {
      const safeIndex = Math.max(0, Math.min(index, sections.length - 1));
      sections.forEach((s, i) => {
        const active = i === safeIndex;
        s.tabBtn.classList.toggle("is-active", active);
        s.tabBtn.setAttribute("aria-selected", active ? "true" : "false");
        s.tabBtn.tabIndex = active ? 0 : -1;
        s.panel.hidden = !active;
      });

      const activeSection = sections[safeIndex];
      if (opts.focus) activeSection.tabBtn.focus({ preventScroll: true });

      // Clear and re-apply highlight in active panel if search query exists
      const query = (opts.highlightQuery || "").trim();
      clearMarks(activeSection.panel);
      if (query.length >= 2) highlightInElement(activeSection.panel, query);
    }

    function focusTab(nextIndex) {
      const safe = Math.max(0, Math.min(nextIndex, sections.length - 1));
      sections[safe].tabBtn.focus({ preventScroll: true });
    }

    // Click activation
    tabs.addEventListener("click", (e) => {
      const btn = e.target.closest("button[role='tab']");
      if (!btn) return;
      const index = sections.findIndex(s => s.tabBtn === btn);
      if (index >= 0) setActive(index, { focus: false, highlightQuery: searchInput.value });
    });

    // Keyboard navigation (Arrow keys move focus; Enter/Space activates)
    tabs.addEventListener("keydown", (e) => {
      const currentIndex = sections.findIndex(s => s.tabBtn === document.activeElement);
      if (currentIndex === -1) return;

      switch (e.key) {
        case "ArrowRight":
          e.preventDefault();
          focusTab((currentIndex + 1) % sections.length);
          break;
        case "ArrowLeft":
          e.preventDefault();
          focusTab((currentIndex - 1 + sections.length) % sections.length);
          break;
        case "Home":
          e.preventDefault();
          focusTab(0);
          break;
        case "End":
          e.preventDefault();
          focusTab(sections.length - 1);
          break;
        case "Enter":
        case " ":
          e.preventDefault();
          setActive(currentIndex, { focus: true, highlightQuery: searchInput.value });
          break;
        default:
          break;
      }
    });

    // --------- Search ----------
    function renderResults(items, query) {
      results.innerHTML = "";
      if (!query || items.length === 0) {
        results.classList.remove("is-open");
        searchCount.textContent = query ? (isFrench ? "Aucun résultat" : "No matches") : "";
        return;
      }

      const list = createEl("ul", { class: "results-list" });
      items.slice(0, 10).forEach((item) => {
        const li = createEl("li", { class: "results-item" });
        const btn = createEl("button", {
          class: "results-btn",
          type: "button"
        });

        const title = createEl("div", { class: "results-title", textContent: item.title });
        const snippet = createEl("div", { class: "results-snippet", textContent: item.snippet });

        btn.append(title, snippet);
        btn.addEventListener("click", () => {
          setActive(item.index, { focus: false, highlightQuery: query });
          results.classList.remove("is-open");
          // Scroll into view nicely
          sections[item.index].panel.scrollIntoView({ behavior: "smooth", block: "start" });
        });

        li.append(btn);
        list.append(li);
      });

      results.append(list);
      results.classList.add("is-open");
      searchCount.textContent = isFrench
        ? `${items.length} correspondance${items.length === 1 ? "" : "s"}`
        : `${items.length} match${items.length === 1 ? "" : "es"}`;
    }

    function makeSnippet(text, query) {
      const q = query.toLowerCase();
      const t = text.replace(/\s+/g, " ").trim();
      const i = t.toLowerCase().indexOf(q);
      if (i === -1) return t.slice(0, 140) + (t.length > 140 ? "…" : "");
      const start = Math.max(0, i - 50);
      const end = Math.min(t.length, i + q.length + 70);
      const prefix = start > 0 ? "…" : "";
      const suffix = end < t.length ? "…" : "";
      return prefix + t.slice(start, end) + suffix;
    }

    let searchTimer = null;
    function runSearch() {
      const query = (searchInput.value || "").trim();
      if (!query) {
        results.innerHTML = "";
        results.classList.remove("is-open");
        searchCount.textContent = "";
        // Clear highlight from active panel only
        const active = sections.find(s => s.tabBtn.getAttribute("aria-selected") === "true") || sections[0];
        clearMarks(active.panel);
        return;
      }

      const q = query.toLowerCase();
      const matches = sections
        .map((s, index) => {
          const titleMatch = s.title.toLowerCase().includes(q);
          const text = (s.panel.innerText || "").toLowerCase();
          const contentMatch = text.includes(q);
          if (!titleMatch && !contentMatch) return null;

          const raw = (s.panel.innerText || "");
          return {
            index,
            title: s.title,
            snippet: makeSnippet(raw, query)
          };
        })
        .filter(Boolean);

      renderResults(matches, query);

      // Also highlight in the active tab (only) so it stays fast
      const activeIndex = sections.findIndex(s => s.tabBtn.getAttribute("aria-selected") === "true");
      if (activeIndex >= 0) {
        const activePanel = sections[activeIndex].panel;
        clearMarks(activePanel);
        if (query.length >= 2) highlightInElement(activePanel, query);
      }
    }

    searchInput.addEventListener("input", () => {
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(runSearch, 120);
    });

    searchClear.addEventListener("click", () => {
      searchInput.value = "";
      runSearch();
      searchInput.focus();
    });

    // Initial active tab
    setActive(0, { focus: false, highlightQuery: "" });
  });
})();
