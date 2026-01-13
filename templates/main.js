document.addEventListener("DOMContentLoaded", () => {

    const TAB_SECTIONS = [
        "Education",
        "Experience",
        "Software",
        "Publications",
        "Teaching",
        "Talks",
        "Volunteering"
    ];

    const main = document.querySelector("main");
    if (!main) return;

    const headings = [...main.querySelectorAll("h2")];

    const tabsBar = document.createElement("div");
    tabsBar.className = "tabs";

    const tabContents = {};

    headings.forEach(h2 => {
        const title = h2.textContent.trim();
        if (!TAB_SECTIONS.includes(title)) return;

        // Create a stable ID
        const sectionId = title.toLowerCase().replace(/\s+/g, "-");
        h2.id = sectionId;

        const content = document.createElement("div");
        content.className = "tab-content";
        content.dataset.tab = title;
        content.dataset.target = sectionId;

        let el = h2.nextElementSibling;
        content.appendChild(h2);

        while (el && el.tagName !== "H2") {
            const next = el.nextElementSibling;
            content.appendChild(el);
            el = next;
        }

        tabContents[title] = content;
    });

    Object.entries(tabContents).forEach(([title, content], i) => {
        const button = document.createElement("button");
        button.className = "tab";
        button.textContent = title;

        if (i === 0) {
            button.classList.add("active");
            content.classList.add("active");
        }

        button.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

            button.classList.add("active");
            content.classList.add("active");

            // Scroll to the section heading
            const target = content.querySelector("h2");
            if (target) {
                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            }
        });

        tabsBar.appendChild(button);
        main.appendChild(content);
    });

    if (tabsBar.children.length > 0) {
        main.insertBefore(tabsBar, main.firstElementChild);
    }
    (function () {
  function setFooterCopyright() {
    const el = document.getElementById("copyright");
    if (!el) return;

    const year = new Date().getFullYear();
    el.textContent = `© ${year} Omar AbedelKader`;
  }

  function setupCvTabs() {
    const tabs = Array.from(document.querySelectorAll(".cv-tab"));
    const full = document.getElementById("cv-full");
    const industry = document.getElementById("cv-industry");

    if (!tabs.length || !full || !industry) return;

    function activate(which) {
      const isFull = which === "full";
      full.hidden = !isFull;
      industry.hidden = isFull;

      tabs.forEach((btn) => {
        const active = btn.dataset.cv === which;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-selected", active ? "true" : "false");
      });

      // Optional: remember choice
      try { localStorage.setItem("cvVersion", which); } catch (_) {}
    }

    tabs.forEach((btn) => {
      btn.setAttribute("role", "tab");
      btn.addEventListener("click", () => activate(btn.dataset.cv));
    });

    // Restore last selection (optional)
    let saved = null;
    try { saved = localStorage.getItem("cvVersion"); } catch (_) {}
    activate(saved === "industry" ? "industry" : "full");
  }

  document.addEventListener("DOMContentLoaded", () => {
    setFooterCopyright();
    setupCvTabs();
  });
})();

});
    