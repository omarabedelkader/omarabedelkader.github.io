/* main.js
   - Turns each H2 (##) into a tab
   - Adds search (titles + content), results list, and <mark> highlighting
   - Keyboard nav: ArrowLeft/ArrowRight/Home/End + Enter/Space to activate
*/

(function () {
  function slugify(text) {
    return String(text)
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
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

  function setPublicationGroupOpen(toggle, body, open) {
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    body.setAttribute("aria-hidden", open ? "false" : "true");

    if (open) {
      window.clearTimeout(body.publicationCloseTimer);
      body.hidden = false;
      if ("inert" in body) body.inert = false;
      window.requestAnimationFrame(() => {
        body.classList.add("is-open");
      });
      return;
    }

    body.classList.remove("is-open");
    if ("inert" in body) body.inert = true;
    window.clearTimeout(body.publicationCloseTimer);
    body.publicationCloseTimer = window.setTimeout(() => {
      if (toggle.getAttribute("aria-expanded") === "false") {
        body.hidden = true;
      }
    }, 190);
  }

  function openMatchingPublicationGroups(panel, query) {
    const q = query.toLowerCase();
    const groups = Array.from(panel.querySelectorAll(".publication-group, .service-group"));
    groups.forEach((group) => {
      const toggle = group.querySelector(".publication-toggle");
      const body = group.querySelector(".publication-list");
      if (!toggle || !body) return;

      const groupText = `${toggle.textContent || ""} ${body.textContent || ""}`.toLowerCase();
      if (groupText.includes(q)) setPublicationGroupOpen(toggle, body, true);
    });
  }

  function enhanceProfileInterests(header) {
    const paragraphs = Array.from(header.querySelectorAll("p"));
    const interests = paragraphs.find((paragraph) => {
      const text = (paragraph.textContent || "").trim();
      return /^(interests|intérêts|interets|centres d.interet)\s*:/i.test(text);
    });
    if (!interests || interests.dataset.profileInterestsEnhanced === "true") return interests || null;

    const text = (interests.textContent || "").replace(/\s+/g, " ").trim();
    const separator = text.indexOf(":");
    if (separator === -1) return interests;

    const labelText = text.slice(0, separator).trim();
    const tags = text
      .slice(separator + 1)
      .split(/[·•,]/)
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (tags.length === 0) return interests;

    interests.dataset.profileInterestsEnhanced = "true";
    interests.classList.add("profile-interests");
    interests.replaceChildren();

    const label = createEl("span", {
      class: "profile-interests-label",
      textContent: `${labelText}:`
    });
    const tagList = createEl("span", { class: "profile-interests-tags" });
    tags.forEach((tag) => {
      tagList.append(createEl("span", { class: "profile-interest-tag", textContent: tag }));
    });
    interests.append(label, tagList);
    return interests;
  }

  function trimInlineContent(element) {
    while (element.firstChild && element.firstChild.nodeType === Node.TEXT_NODE && !element.firstChild.nodeValue.trim()) {
      element.firstChild.remove();
    }
    while (element.lastChild && element.lastChild.nodeType === Node.TEXT_NODE && !element.lastChild.nodeValue.trim()) {
      element.lastChild.remove();
    }
    if (element.firstChild && element.firstChild.nodeType === Node.TEXT_NODE) {
      element.firstChild.nodeValue = element.firstChild.nodeValue.replace(/^\s+/, "");
    }
    if (element.lastChild && element.lastChild.nodeType === Node.TEXT_NODE) {
      element.lastChild.nodeValue = element.lastChild.nodeValue.replace(/\s+$/, "");
    }
  }

  function enhanceProfileCurrent(header) {
    const paragraphs = Array.from(header.querySelectorAll("p"));
    const current = paragraphs.find((paragraph) => {
      const text = (paragraph.textContent || "").trim();
      return /^(current|actuel|actuels|en cours)\s*:/i.test(text);
    });
    if (!current || current.dataset.profileCurrentEnhanced === "true") return current || null;

    const text = (current.textContent || "").replace(/\s+/g, " ").trim();
    const separator = text.indexOf(":");
    if (separator === -1) return current;

    const labelText = text.slice(0, separator).trim();
    const labelNode = Array.from(current.children).find((child) =>
      child.tagName === "STRONG" && (child.textContent || "").includes(":")
    );
    const content = createEl("span", { class: "profile-current-items" });

    if (labelNode) {
      let node = labelNode.nextSibling;
      while (node) {
        const next = node.nextSibling;
        content.append(node);
        node = next;
      }
    } else {
      content.textContent = text.slice(separator + 1).trim();
    }
    trimInlineContent(content);
    if (!content.textContent.trim()) return current;

    current.dataset.profileCurrentEnhanced = "true";
    current.classList.add("profile-interests", "profile-current");
    current.replaceChildren();

    const label = createEl("span", {
      class: "profile-interests-label profile-current-label",
      textContent: `${labelText}:`
    });
    current.append(label, content);
    return current;
  }

  function isSelectedPublicationTitle(title) {
    const normalized = title.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    return normalized === "selected publications" || normalized === "publications selectionnees";
  }

  function publicationFilterKey(text) {
    return String(text).replace(/\s+/g, " ").trim().toLowerCase();
  }

  function collectAndRemoveSelectedPublicationSeed(panel) {
    const selectedKeys = new Set();
    const headings = Array.from(panel.children).filter((child) => child.tagName === "H3");

    headings.forEach((heading) => {
      const title = (heading.textContent || "").trim();
      if (!isSelectedPublicationTitle(title)) return;

      let node = heading.nextSibling;
      heading.remove();

      while (node && !(node.nodeType === 1 && (node.tagName === "H3" || node.tagName === "HR"))) {
        const next = node.nextSibling;
        if (node.nodeType === 1) {
          node.querySelectorAll("li").forEach((item) => {
            selectedKeys.add(publicationFilterKey(item.textContent || ""));
          });
        }
        node.remove();
        node = next;
      }
    });

    return selectedKeys;
  }

  function addGroupBulkToggle(panel, groups, labels) {
    if (groups.length === 0) return;

    const firstGroup = groups[0];
    const existingFilter = firstGroup.previousElementSibling?.classList.contains("publication-filter")
      ? firstGroup.previousElementSibling
      : null;
    const bulkActions = createEl("span", { class: "publication-bulk-actions" });
    const bulkToggle = createEl("button", {
      class: "publication-bulk-button publication-bulk-toggle",
      type: "button",
      "aria-label": labels.open,
      "aria-pressed": "false",
      title: labels.open
    });
    const bulkIcon = createEl("span", {
      class: "publication-bulk-icon publication-bulk-icon-expand",
      "aria-hidden": "true"
    });
    bulkToggle.append(bulkIcon);
    bulkActions.append(bulkToggle);
    if (existingFilter) {
      existingFilter.append(bulkActions);
    } else {
      const toolbar = createEl("div", { class: "section-bulk-toolbar" });
      toolbar.append(bulkActions);
      panel.insertBefore(toolbar, firstGroup);
    }

    const visibleGroups = () => groups.filter((group) => !group.hidden);

    const refreshBulkToggle = () => {
      const visible = visibleGroups();
      const allOpen = visible.length > 0 && visible.every((group) => {
        const toggleButton = group.querySelector(".publication-toggle");
        return toggleButton && toggleButton.getAttribute("aria-expanded") === "true";
      });
      const labelText = allOpen ? labels.close : labels.open;
      bulkToggle.setAttribute("aria-pressed", allOpen ? "true" : "false");
      bulkToggle.setAttribute("aria-label", labelText);
      bulkToggle.title = labelText;
      bulkIcon.className = `publication-bulk-icon ${allOpen ? "publication-bulk-icon-collapse" : "publication-bulk-icon-expand"}`;
    };

    const setAllOpen = (open) => {
      visibleGroups().forEach((group) => {
        const toggleButton = group.querySelector(".publication-toggle");
        const body = group.querySelector(".publication-list");
        if (toggleButton && body) setPublicationGroupOpen(toggleButton, body, open);
      });
      refreshBulkToggle();
    };

    bulkToggle.addEventListener("click", () => {
      const shouldOpen = bulkToggle.getAttribute("aria-pressed") !== "true";
      setAllOpen(shouldOpen);
    });
    groups.forEach((group) => {
      const toggleButton = group.querySelector(".publication-toggle");
      if (toggleButton) {
        toggleButton.addEventListener("click", () => window.setTimeout(refreshBulkToggle, 210));
      }
    });
    panel.addEventListener("groups-visibility-change", refreshBulkToggle);

    refreshBulkToggle();
  }

  function addCurrentBadge(item, isFrench) {
    if (item.querySelector(".service-current-badge")) return;
    item.append(" ", createEl("span", {
      class: "service-current-badge",
      textContent: isFrench ? "Actuel" : "Current"
    }));
  }

  function setMarkedCurrentItem(item, datasetKey, currentClass, isFrench) {
    item.dataset[datasetKey] = "true";
    item.classList.add(currentClass);
    addCurrentBadge(item, isFrench);
  }

  function addCurrentItemFilter(panel, groups, isFrench, options) {
    const currentItems = Array.from(panel.querySelectorAll("li"))
      .filter((item) => item.dataset[options.datasetKey] === "true");
    if (currentItems.length === 0 || groups.length === 0) return;

    const control = createEl("div", { class: `publication-filter ${options.filterClass || ""}`.trim() });
    const label = createEl("span", {
      class: "publication-filter-label",
      textContent: isFrench ? "Filtrer" : "Filter"
    });
    const toggle = createEl("button", {
      class: "publication-filter-toggle",
      type: "button",
      role: "switch",
      "aria-checked": "false"
    });
    const switchTrack = createEl("span", {
      class: "publication-filter-track",
      "aria-hidden": "true"
    });
    const switchText = createEl("span", {
      class: "publication-filter-text",
      textContent: options.switchText
    });
    const count = createEl("span", {
      class: "publication-filter-count",
      textContent: ""
    });

    toggle.append(switchTrack, switchText);
    control.append(label, toggle, count);
    panel.insertBefore(control, groups[0]);

    const update = () => {
      const currentOnly = toggle.getAttribute("aria-checked") === "true";
      let visibleTotal = 0;

      groups.forEach((group) => {
        const toggleButton = group.querySelector(".publication-toggle");
        const body = group.querySelector(".publication-list");
        const items = Array.from(group.querySelectorAll("li"));
        let visibleInGroup = 0;

        items.forEach((item) => {
          const show = !currentOnly || item.dataset[options.datasetKey] === "true";
          item.hidden = !show;
          if (show) visibleInGroup += 1;
        });

        group.hidden = currentOnly && visibleInGroup === 0;
        visibleTotal += visibleInGroup;

        const meta = group.querySelector(".publication-toggle-meta");
        if (meta) meta.textContent = options.countLabel(visibleInGroup);

        if (currentOnly && visibleInGroup > 0 && toggleButton && body) {
          setPublicationGroupOpen(toggleButton, body, true);
        }
      });

      count.textContent = currentOnly ? options.countText(visibleTotal) : "";
      panel.classList.toggle(options.panelClass, currentOnly);
      panel.dispatchEvent(new CustomEvent("groups-visibility-change"));
    };

    toggle.addEventListener("click", () => {
      const next = toggle.getAttribute("aria-checked") !== "true";
      toggle.setAttribute("aria-checked", next ? "true" : "false");
      update();
    });

    update();
  }

  function addServiceCurrentFilter(panel, groups, isFrench) {
    addCurrentItemFilter(
      panel,
      groups,
      isFrench,
      {
        datasetKey: "currentService",
        filterClass: "service-current-filter",
        switchText: isFrench ? "Actuels" : "Current",
        panelClass: "is-filtering-current-services",
        countLabel: count => count === 1 ? "1 service" : `${count} services`,
        countText: count => isFrench
          ? `${count} actuel${count === 1 ? "" : "s"}`
          : `${count} current`
      }
    );
  }

  function addPublicationFilter(panel, selectedKeys, isFrench) {
    if (selectedKeys.size === 0) return;

    const groups = Array.from(panel.querySelectorAll(".publication-group"));
    if (groups.length === 0) return;

    const control = createEl("div", { class: "publication-filter" });
    const label = createEl("span", {
      class: "publication-filter-label",
      textContent: isFrench ? "Filtrer" : "Filter"
    });
    const toggle = createEl("button", {
      class: "publication-filter-toggle",
      type: "button",
      role: "switch",
      "aria-checked": "false"
    });
    const switchTrack = createEl("span", {
      class: "publication-filter-track",
      "aria-hidden": "true"
    });
    const switchText = createEl("span", {
      class: "publication-filter-text",
      textContent: isFrench ? "Publications sélectionnées" : "Selected Publications"
    });
    const count = createEl("span", {
      class: "publication-filter-count",
      textContent: ""
    });
    const bulkActions = createEl("span", {
      class: "publication-bulk-actions"
    });
    const bulkToggle = createEl("button", {
      class: "publication-bulk-button publication-bulk-toggle",
      type: "button",
      "aria-label": isFrench ? "Tout ouvrir" : "Expand all publications",
      "aria-pressed": "false",
      title: isFrench ? "Tout ouvrir" : "Expand all publications"
    });
    const bulkIcon = createEl("span", {
      class: "publication-bulk-icon publication-bulk-icon-expand",
      "aria-hidden": "true"
    });
    bulkToggle.append(bulkIcon);

    toggle.append(switchTrack, switchText);
    bulkActions.append(bulkToggle);
    control.append(label, toggle, count, bulkActions);

    const firstGroup = groups[0];
    panel.insertBefore(control, firstGroup);

    const visibleGroups = () => groups.filter((group) => !group.hidden);

    const refreshBulkToggle = () => {
      const visible = visibleGroups();
      const allOpen = visible.length > 0 && visible.every((group) => {
        const toggleButton = group.querySelector(".publication-toggle");
        return toggleButton && toggleButton.getAttribute("aria-expanded") === "true";
      });
      const labelText = allOpen
        ? (isFrench ? "Tout fermer" : "Collapse all publications")
        : (isFrench ? "Tout ouvrir" : "Expand all publications");
      bulkToggle.setAttribute("aria-pressed", allOpen ? "true" : "false");
      bulkToggle.setAttribute("aria-label", labelText);
      bulkToggle.title = labelText;
      bulkIcon.className = `publication-bulk-icon ${allOpen ? "publication-bulk-icon-collapse" : "publication-bulk-icon-expand"}`;
    };

    const setAllOpen = (open) => {
      visibleGroups().forEach((group) => {
        const toggleButton = group.querySelector(".publication-toggle");
        const body = group.querySelector(".publication-list");
        if (toggleButton && body) setPublicationGroupOpen(toggleButton, body, open);
      });
      refreshBulkToggle();
    };

    const update = () => {
      const selectedOnly = toggle.getAttribute("aria-checked") === "true";
      let visibleTotal = 0;

      groups.forEach((group) => {
        const toggleButton = group.querySelector(".publication-toggle");
        const body = group.querySelector(".publication-list");
        const items = Array.from(group.querySelectorAll("li"));
        let visibleInGroup = 0;

        items.forEach((item) => {
          const show = !selectedOnly || item.dataset.selectedPublication === "true";
          item.hidden = !show;
          if (show) visibleInGroup += 1;
        });

        group.hidden = selectedOnly && visibleInGroup === 0;
        visibleTotal += visibleInGroup;

        const meta = group.querySelector(".publication-toggle-meta");
        if (meta) {
          meta.textContent = visibleInGroup === 1 ? "1 publication" : `${visibleInGroup} publications`;
        }

        if (selectedOnly && visibleInGroup > 0 && toggleButton && body) {
          setPublicationGroupOpen(toggleButton, body, true);
        }
      });

      count.textContent = selectedOnly
        ? (isFrench ? `${visibleTotal} affichée${visibleTotal === 1 ? "" : "s"}` : `${visibleTotal} shown`)
        : "";
      panel.classList.toggle("is-filtering-selected-publications", selectedOnly);
      refreshBulkToggle();
    };

    toggle.addEventListener("click", () => {
      const next = toggle.getAttribute("aria-checked") !== "true";
      toggle.setAttribute("aria-checked", next ? "true" : "false");
      update();
    });
    bulkToggle.addEventListener("click", () => {
      const shouldOpen = bulkToggle.getAttribute("aria-pressed") !== "true";
      setAllOpen(shouldOpen);
    });
    groups.forEach((group) => {
      const toggleButton = group.querySelector(".publication-toggle");
      if (toggleButton) {
        toggleButton.addEventListener("click", () => window.setTimeout(refreshBulkToggle, 210));
      }
    });

    update();
  }

  function enhancePublicationGroups(panel) {
    if (panel.dataset.publicationsEnhanced === "true") return;
    const isFrench = document.documentElement.lang === "fr";
    const selectedKeys = collectAndRemoveSelectedPublicationSeed(panel);

    const isGroupBoundary = (node) =>
      node.nodeType === 1 && (node.tagName === "H3" || node.tagName === "HR");

    const headings = Array.from(panel.children).filter((child) => child.tagName === "H3");
    if (headings.length === 0) return;

    panel.dataset.publicationsEnhanced = "true";

    headings.forEach((heading, index) => {
      const title = (heading.textContent || "").trim();
      const headingId = heading.id || `publication-group-${index + 1}`;
      const contentId = `${headingId}-items`;

      const group = createEl("section", { class: "publication-group" });
      const groupHeading = createEl("h3", { class: "publication-heading", id: headingId });
      const toggle = createEl("button", {
        class: "publication-toggle",
        type: "button",
        "aria-expanded": "false",
        "aria-controls": contentId
      });
      const arrow = createEl("span", {
        class: "publication-toggle-arrow",
        "aria-hidden": "true"
      });
      const toggleMain = createEl("span", {
        class: "publication-toggle-main"
      });
      const label = createEl("span", {
        class: "publication-toggle-label",
        textContent: title
      });
      const meta = createEl("span", {
        class: "publication-toggle-meta",
        textContent: ""
      });
      const body = createEl("div", {
        class: "publication-list",
        id: contentId,
        "aria-hidden": "true"
      });
      body.hidden = true;
      if ("inert" in body) body.inert = true;

      toggleMain.append(label, meta);
      toggle.append(arrow, toggleMain);
      groupHeading.append(toggle);
      group.append(groupHeading, body);
      heading.parentNode.insertBefore(group, heading);

      let node = heading.nextSibling;
      heading.remove();
      while (node && !isGroupBoundary(node)) {
        const next = node.nextSibling;
        body.append(node);
        node = next;
      }

      const count = body.querySelectorAll("li").length;
      body.querySelectorAll("li").forEach((item) => {
        const key = publicationFilterKey(item.textContent || "");
        item.classList.add("publication-item");
        item.dataset.selectedPublication = selectedKeys.has(key) ? "true" : "false";
      });
      meta.textContent = count === 1 ? "1 publication" : `${count} publications`;

      toggle.addEventListener("click", () => {
        setPublicationGroupOpen(toggle, body, toggle.getAttribute("aria-expanded") !== "true");
      });
    });

    addPublicationFilter(panel, selectedKeys, isFrench);
  }

  function enhanceServiceGroups(panel) {
    if (panel.dataset.servicesEnhanced === "true") return;

    const isFrench = document.documentElement.lang === "fr";
    const isGroupBoundary = (node) =>
      node.nodeType === 1 && (node.tagName === "H3" || node.tagName === "HR");

    const headings = Array.from(panel.children).filter((child) => child.tagName === "H3");
    if (headings.length === 0) return;

    panel.dataset.servicesEnhanced = "true";

    headings.forEach((heading, index) => {
      const title = (heading.textContent || "").trim();
      const headingId = heading.id || `service-group-${index + 1}`;
      const contentId = `${headingId}-items`;

      const group = createEl("section", { class: "publication-group service-group" });
      const groupHeading = createEl("h3", { class: "publication-heading service-heading", id: headingId });
      const toggle = createEl("button", {
        class: "publication-toggle service-toggle",
        type: "button",
        "aria-expanded": "false",
        "aria-controls": contentId
      });
      const arrow = createEl("span", {
        class: "publication-toggle-arrow",
        "aria-hidden": "true"
      });
      const toggleMain = createEl("span", {
        class: "publication-toggle-main"
      });
      const label = createEl("span", {
        class: "publication-toggle-label",
        textContent: title
      });
      const meta = createEl("span", {
        class: "publication-toggle-meta",
        textContent: ""
      });
      const body = createEl("div", {
        class: "publication-list service-list",
        id: contentId,
        "aria-hidden": "true"
      });
      body.hidden = true;
      if ("inert" in body) body.inert = true;

      toggleMain.append(label, meta);
      toggle.append(arrow, toggleMain);
      groupHeading.append(toggle);
      group.append(groupHeading, body);
      heading.parentNode.insertBefore(group, heading);

      let node = heading.nextSibling;
      heading.remove();
      while (node && !isGroupBoundary(node)) {
        const next = node.nextSibling;
        body.append(node);
        node = next;
      }

      body.querySelectorAll("li").forEach((item) => {
        const marker = item.querySelector(".current-item-marker, .service-current-marker");
        const isCurrent = Boolean(marker);
        if (marker) marker.remove();
        item.classList.add("service-item");
        item.dataset.currentService = "false";
        if (isCurrent) {
          setMarkedCurrentItem(item, "currentService", "service-current-item", isFrench);
        }
      });

      const count = body.querySelectorAll("li").length;
      if (isFrench) {
        meta.textContent = count === 1 ? "1 service" : `${count} services`;
      } else {
        meta.textContent = count === 1 ? "1 service" : `${count} services`;
      }

      toggle.addEventListener("click", () => {
        setPublicationGroupOpen(toggle, body, toggle.getAttribute("aria-expanded") !== "true");
      });
    });

    const serviceGroups = Array.from(panel.querySelectorAll(".service-group"));
    addServiceCurrentFilter(panel, serviceGroups, isFrench);
    addGroupBulkToggle(
      panel,
      serviceGroups,
      {
        open: isFrench ? "Tout ouvrir" : "Expand all services",
        close: isFrench ? "Tout fermer" : "Collapse all services"
      }
    );
  }

  function enhanceStudentGroups(panel) {
    enhanceDatedGroups(panel, {
      flag: "studentsEnhanced",
      groupClass: "student-group",
      headingClass: "student-heading",
      toggleClass: "student-toggle",
      listClass: "student-list",
      itemClass: "student-item",
      currentClass: "student-current-item",
      datasetKey: "currentStudent",
      filterClass: "student-current-filter",
      switchText: isFrench => isFrench ? "Étudiants actuels" : "Current Students",
      panelClass: "is-filtering-current-students",
      countLabel: (count, isFrench) => isFrench
        ? (count === 1 ? "1 étudiant" : `${count} étudiants`)
        : (count === 1 ? "1 student" : `${count} students`),
      countText: (count, isFrench) => isFrench
        ? `${count} actuel${count === 1 ? "" : "s"}`
        : `${count} current`,
      bulkOpen: isFrench => isFrench ? "Tout ouvrir" : "Expand all students",
      bulkClose: isFrench => isFrench ? "Tout fermer" : "Collapse all students",
      fallbackLatest: false
    });
  }

  function enhanceTalkGroups(panel) {
    enhanceDatedGroups(panel, {
      flag: "talksEnhanced",
      groupClass: "talk-group",
      headingClass: "talk-heading",
      toggleClass: "talk-toggle",
      listClass: "talk-list",
      itemClass: "talk-item",
      currentClass: "talk-current-item",
      datasetKey: "currentTalk",
      filterClass: "talk-current-filter",
      switchText: isFrench => isFrench ? "Présentations actuelles" : "Current Talks",
      panelClass: "is-filtering-current-talks",
      countLabel: (count, isFrench) => isFrench
        ? (count === 1 ? "1 présentation" : `${count} présentations`)
        : (count === 1 ? "1 talk" : `${count} talks`),
      countText: (count, isFrench) => isFrench
        ? `${count} actuelle${count === 1 ? "" : "s"}`
        : `${count} current`,
      bulkOpen: isFrench => isFrench ? "Tout ouvrir" : "Expand all talks",
      bulkClose: isFrench => isFrench ? "Tout fermer" : "Collapse all talks",
      fallbackLatest: false
    });
  }

  function enhanceDatedGroups(panel, options) {
    if (panel.dataset[options.flag] === "true") return;

    const isFrench = document.documentElement.lang === "fr";
    const isGroupBoundary = (node) =>
      node.nodeType === 1 && (node.tagName === "H3" || node.tagName === "HR");

    const headings = Array.from(panel.children).filter((child) => child.tagName === "H3");
    if (headings.length === 0) return;

    panel.dataset[options.flag] = "true";
    let currentCount = 0;
    let firstGroup = null;

    headings.forEach((heading, index) => {
      const title = (heading.textContent || "").trim();
      const headingId = heading.id || `${options.groupClass}-${index + 1}`;
      const contentId = `${headingId}-items`;

      const group = createEl("section", { class: `publication-group ${options.groupClass}` });
      const groupHeading = createEl("h3", { class: `publication-heading ${options.headingClass}`, id: headingId });
      const toggle = createEl("button", {
        class: `publication-toggle ${options.toggleClass}`,
        type: "button",
        "aria-expanded": "false",
        "aria-controls": contentId
      });
      const arrow = createEl("span", {
        class: "publication-toggle-arrow",
        "aria-hidden": "true"
      });
      const toggleMain = createEl("span", {
        class: "publication-toggle-main"
      });
      const label = createEl("span", {
        class: "publication-toggle-label",
        textContent: title
      });
      const meta = createEl("span", {
        class: "publication-toggle-meta",
        textContent: ""
      });
      const body = createEl("div", {
        class: `publication-list ${options.listClass}`,
        id: contentId,
        "aria-hidden": "true"
      });
      body.hidden = true;
      if ("inert" in body) body.inert = true;

      toggleMain.append(label, meta);
      toggle.append(arrow, toggleMain);
      groupHeading.append(toggle);
      group.append(groupHeading, body);
      heading.parentNode.insertBefore(group, heading);

      let node = heading.nextSibling;
      heading.remove();
      while (node && !isGroupBoundary(node)) {
        const next = node.nextSibling;
        body.append(node);
        node = next;
      }

      const count = body.querySelectorAll("li").length;
      body.querySelectorAll("li").forEach((item) => {
        const marker = item.querySelector(".current-item-marker, .service-current-marker");
        const isCurrent = Boolean(marker);
        if (marker) marker.remove();
        item.classList.add(options.itemClass);
        item.dataset[options.datasetKey] = "false";
        if (isCurrent) {
          setMarkedCurrentItem(item, options.datasetKey, options.currentClass, isFrench);
          currentCount += 1;
        }
      });
      meta.textContent = options.countLabel(count, isFrench);
      if (!firstGroup) firstGroup = group;

      toggle.addEventListener("click", () => {
        setPublicationGroupOpen(toggle, body, toggle.getAttribute("aria-expanded") !== "true");
      });
    });

    const groups = Array.from(panel.querySelectorAll(`.${options.groupClass}`));
    if (currentCount === 0 && options.fallbackLatest && firstGroup) {
      firstGroup.querySelectorAll("li").forEach((item) => {
        setMarkedCurrentItem(item, options.datasetKey, options.currentClass, isFrench);
      });
    }

    addCurrentItemFilter(
      panel,
      groups,
      isFrench,
      {
        datasetKey: options.datasetKey,
        filterClass: options.filterClass,
        switchText: options.switchText(isFrench),
        panelClass: options.panelClass,
        countLabel: count => options.countLabel(count, isFrench),
        countText: count => options.countText(count, isFrench)
      }
    );
    addGroupBulkToggle(
      panel,
      groups,
      {
        open: options.bulkOpen(isFrench),
        close: options.bulkClose(isFrench)
      }
    );
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
    const headerRow = createEl("div", { class: "header-row" });
    const headerTitle = createEl("div", { class: "header-title" });
    const headerActions = createEl("div", { class: "header-actions" });
    const sticky = createEl("div", { class: "sticky-ui" });
    const isFrench = document.documentElement.lang === "fr";

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
      const nextTheme = currentTheme() === "dark" ? "light" : "dark";
      const label = nextTheme === "light"
        ? (isFrench ? "Passer au thème clair" : "Switch to light theme")
        : (isFrench ? "Passer au thème sombre" : "Switch to dark theme");

      themeBtn.textContent = nextTheme === "light" ? "☀️" : "🌙";
      themeBtn.setAttribute("aria-label", label);
      themeBtn.title = label;
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
    const languageBtn = createEl("a", {
      class: "topbar-btn",
      href: isFrench ? "../index.html" : "fr/",
      "aria-label": isFrench ? "Voir en anglais" : "Voir en français",
      title: isFrench ? "Voir en anglais" : "Voir en français",
      textContent: isFrench ? "🇬🇧" : "🇫🇷"
    });
    topbar.append(languageBtn);

    const assetPrefix = isFrench ? "../assets/" : "assets/";
    const quickLinks = [
      { href: isFrench ? "../cv/cv-fr.pdf" : "cv/cv-en.pdf", label: isFrench ? "CV complet" : "Full CV", icon: "📄" },
      { href: "mailto:omar.abedelkader@inria.fr", label: isFrench ? "E-mail" : "Email", icon: "✉️" },
      //{ href: "https://omarabedelkader.github.io", label: isFrench ? "Site web" : "Website", icon: "🌐" },
      //{ href: "https://huggingface.co/omarabedelkader", label: "Hugging Face", icon: "🤗" },
      //{ href: "https://github.com/omarabedelkader", label: "GitHub", icon: "🐙" },
      //{ href: "https://ollama.com/omarabedelkader", label: "Ollama", icon: "🦙" },
      { href: "https://www.linkedin.com/in/omarabedelkader/", label: "LinkedIn", icon: "in", className: "topbar-linkedin" },
      { href: "https://orcid.org/0009-0005-1339-5683", label: "ORCID", src: `${assetPrefix}orcid.svg`, className: "topbar-orcid" },
      { href: "https://dblp.org/pid/426/8188.html", label: "DBLP", src: `${assetPrefix}dblp.svg`, className: "topbar-dblp" },
      { href: "https://scholar.google.com/citations?hl=fr&user=Wl01zhQAAAAJ", label: isFrench ? "Google Scholar" : "Google Scholar", icon: "🎓" }
    ];

    quickLinks.forEach((l) => {
      const attrs = {
        class: l.className ? `topbar-btn ${l.className}` : "topbar-btn",
        href: l.href,
        "aria-label": l.label,
        title: l.label
      };
      if (!l.src) attrs.textContent = l.icon;
      if (!String(l.href).startsWith("mailto:")) {
        attrs.target = "_blank";
        attrs.rel = "me noopener noreferrer";
      }
      const a = createEl("a", attrs);
      if (l.src) {
        a.append(createEl("img", {
          class: "topbar-logo",
          src: l.src,
          alt: "",
          decoding: "async",
          draggable: false
        }));
      }
      topbar.append(a);
    });
    // ------------------------------------------------------------------------

    const searchWrap = createEl("div", { class: "search-wrap" });
    const searchLabel = createEl("label", { class: "search-label" });
    const searchLabelText = createEl("span", {
      class: "search-label-text",
      textContent: isFrench ? "Rechercher" : "Search"
    });
    const searchInput = createEl("input", {
      class: "search-input",
      type: "search",
      placeholder: isFrench ? "Que voulez-vous trouver ?" : "What do you want to find?",
      autocomplete: "off",
      inputMode: "search",
      enterKeyHint: "search",
      "aria-label": isFrench ? "Rechercher" : "Search",
      spellcheck: false
    });
    searchLabel.append(searchLabelText, searchInput);

    const searchMeta = createEl("div", { class: "search-meta" });
    const searchCount = createEl("span", { class: "search-count", textContent: "" });
    const searchClear = createEl("button", { class: "search-clear", type: "button", textContent: isFrench ? "Effacer" : "Clear" });
    searchMeta.append(searchCount, searchClear);

    const results = createEl("div", { class: "search-results", role: "region", "aria-label": isFrench ? "Résultats de recherche" : "Search results" });

    searchWrap.append(searchLabel, searchMeta, results);
    headerActions.append(searchWrap);

    const tabs = createEl("nav", {
      class: "tabs",
      role: "tablist",
       "aria-label": isFrench ? "Sections du CV" : "CV sections"
    });

    const panels = createEl("div", { class: "panels" });

    sticky.append(tabs);
    shell.append(header, sticky, panels);

    // --------- Move content before first H2 into header ----------
    const firstH2 = h2s[0];
    while (main.firstChild && main.firstChild !== firstH2) {
      header.append(main.firstChild);
    }
    const title = header.querySelector("h1");
    if (title) {
      headerTitle.append(title);
      headerTitle.append(topbar);
      headerRow.append(headerTitle, headerActions);
      header.insertBefore(headerRow, header.firstChild);
    } else {
      headerTitle.append(topbar);
      headerRow.append(headerTitle);
      headerRow.append(headerActions);
      header.prepend(headerRow);
    }

    const titleBlock = header.querySelector("#title-block-header");
    if (titleBlock && !titleBlock.textContent.trim() && titleBlock.children.length === 0) {
      titleBlock.remove();
    }
    const profileInterests = enhanceProfileInterests(header);
    const profileCurrent = enhanceProfileCurrent(header);
    if (title && profileInterests) headerTitle.append(profileInterests);
    if (title && profileCurrent) headerTitle.append(profileCurrent);

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

      // The tab already labels the section, so do not repeat the same H2 in the panel.
      h2.remove();
      while (main.firstChild && !(main.firstChild.nodeType === 1 && main.firstChild.tagName === "H2")) {
        panel.append(main.firstChild);
      }

      const sectionSlug = slugify(title);
      if (sectionSlug === "publications") {
        enhancePublicationGroups(panel);
      }
      if (sectionSlug === "services") {
        enhanceServiceGroups(panel);
      }
      if (sectionSlug === "students" || sectionSlug === "etudiants" || sectionSlug === "tudiants") {
        enhanceStudentGroups(panel);
      }
      if (sectionSlug === "public-talks" || sectionSlug === "presentations-publiques" || sectionSlug === "prsentations-publiques") {
        enhanceTalkGroups(panel);
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
      activeSection.tabBtn.scrollIntoView({ block: "nearest", inline: "nearest" });

      // Clear and re-apply highlight in active panel if search query exists
      const query = (opts.highlightQuery || "").trim();
      clearMarks(activeSection.panel);
      if (query.length >= 2) {
        openMatchingPublicationGroups(activeSection.panel, query);
        highlightInElement(activeSection.panel, query);
      }
    }

    function focusTab(nextIndex) {
      const safe = Math.max(0, Math.min(nextIndex, sections.length - 1));
      sections[safe].tabBtn.focus({ preventScroll: true });
      sections[safe].tabBtn.scrollIntoView({ block: "nearest", inline: "nearest" });
    }

    function resolveHashTarget(hash) {
      const raw = String(hash || "").replace(/^#/, "");
      if (!raw) return null;

      let id;
      try {
        id = decodeURIComponent(raw);
      } catch (_err) {
        id = raw;
      }

      let target = document.getElementById(id);
      if (!target && id === "current") {
        target = document.getElementById(isFrench ? "actuel" : "current");
      }
      return target;
    }

    function activateHashTarget(hash, options = {}) {
      const target = resolveHashTarget(hash);
      if (!target) return false;

      const targetPanel = target.closest(".tab-panel");
      const sectionIndex = sections.findIndex((section) => section.panel === targetPanel);
      if (sectionIndex >= 0) {
        setActive(sectionIndex, { focus: false, highlightQuery: searchInput.value });
      }

      if (targetPanel && ["current", "actuel"].includes(target.id)) {
        const currentToggle = targetPanel.querySelector(".service-current-filter .publication-filter-toggle");
        if (currentToggle && currentToggle.getAttribute("aria-checked") !== "true") {
          currentToggle.click();
        }
      }

      const group = target.closest(".publication-group, .service-group");
      const groupToggle = group?.querySelector(".publication-toggle");
      const groupBody = group?.querySelector(".publication-list");
      if (groupToggle && groupBody) {
        setPublicationGroupOpen(groupToggle, groupBody, true);
      }

      if (options.updateHistory !== false) {
        window.history.pushState(null, "", hash);
      }
      if (options.scroll !== false) {
        window.setTimeout(() => {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 0);
      }
      return true;
    }

    // Click activation
    tabs.addEventListener("click", (e) => {
      const btn = e.target.closest("button[role='tab']");
      if (!btn) return;
      const index = sections.findIndex(s => s.tabBtn === btn);
      if (index >= 0) setActive(index, { focus: false, highlightQuery: searchInput.value });
    });

    main.addEventListener("click", (e) => {
      const link = e.target.closest("a[href^='#']");
      if (!link) return;

      const hash = link.getAttribute("href");
      if (activateHashTarget(hash)) e.preventDefault();
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
      searchWrap.classList.toggle("has-query", Boolean(query));
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
      searchWrap.classList.toggle("has-query", Boolean(query));
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
          const text = (s.panel.textContent || "").toLowerCase();
          const contentMatch = text.includes(q);
          if (!titleMatch && !contentMatch) return null;

          const raw = (s.panel.textContent || "");
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
    if (!activateHashTarget(window.location.hash, { updateHistory: false, scroll: Boolean(window.location.hash) })) {
      setActive(0, { focus: false, highlightQuery: "" });
    }
  });
})();
