/* Gallery client-side search
 *
 * Reads a pre-built JSON index embedded by Django's json_script tag,
 * then provides fast, debounced, case-insensitive full-text search
 * across component titles, breadcrumbs, and documentation content.
 *
 * No external dependencies. Pure vanilla JS (ES2017+).
 */

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Index loading
  // ---------------------------------------------------------------------------

  /** @returns {Array<{label: string, url: string, type: string, breadcrumb: string, content: string}>} */
  function loadIndex() {
    const el = document.getElementById("gallery-search-index");
    if (!el) return [];
    try {
      return JSON.parse(el.textContent);
    } catch (_) {
      return [];
    }
  }

  // ---------------------------------------------------------------------------
  // Search logic
  // ---------------------------------------------------------------------------

  /**
   * Return all index entries that match every word in `query`.
   * Matching is case-insensitive, checked against label + breadcrumb + content.
   *
   * @param {string} query
   * @param {Array} index
   * @returns {Array}
   */
  function search(query, index) {
    const words = query
      .trim()
      .toLowerCase()
      .split(/\s+/)
      .filter((w) => w.length > 0);

    if (words.length === 0) return [];

    return index.filter((entry) => {
      const haystack = (
        entry.label +
        " " +
        entry.breadcrumb +
        " " +
        entry.content
      ).toLowerCase();
      return words.every((word) => haystack.includes(word));
    });
  }

  // ---------------------------------------------------------------------------
  // Text highlight helper
  // ---------------------------------------------------------------------------

  /**
   * Append text with matching words wrapped in <mark> without using innerHTML.
   *
   * @param {HTMLElement} parent
   * @param {string} text
   * @param {string[]} words
   */
  function appendHighlightedText(parent, text, words) {
    if (words.length === 0) {
      parent.appendChild(document.createTextNode(text));
      return;
    }

    const pattern = new RegExp(
      "(" +
        words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") +
        ")",
      "gi",
    );

    let lastIndex = 0;
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const start = match.index;
      const end = start + match[0].length;

      if (start > lastIndex) {
        parent.appendChild(
          document.createTextNode(text.slice(lastIndex, start)),
        );
      }

      const markEl = document.createElement("mark");
      markEl.textContent = text.slice(start, end);
      parent.appendChild(markEl);

      lastIndex = end;
    }

    if (lastIndex < text.length) {
      parent.appendChild(document.createTextNode(text.slice(lastIndex)));
    }
  }

  /**
   * Allow only http(s) URLs for result links.
   *
   * @param {string} rawUrl
   * @returns {string}
   */
  function sanitizeResultUrl(rawUrl) {
    try {
      const parsed = new URL(rawUrl, window.location.origin);
      if (parsed.protocol === "http:" || parsed.protocol === "https:") {
        return parsed.href;
      }
    } catch (_) {
      // Ignore parse failures and fall through to the safe fallback.
    }
    return "#";
  }

  // ---------------------------------------------------------------------------
  // DOM helpers
  // ---------------------------------------------------------------------------

  /**
   * Build a single result item element.
   *
   * @param {object} entry
   * @param {string[]} words
   * @returns {HTMLElement}
   */
  function buildResultItem(entry, words) {
    const a = document.createElement("a");
    a.className = "gallery-search-result";
    a.href = sanitizeResultUrl(entry.url);
    a.setAttribute("role", "option");

    const headerEl = document.createElement("span");
    headerEl.className = "gallery-search-result__header";

    const iconEl = document.createElement("span");
    if (entry.type === "component") {
      iconEl.className = "gallery-nav__icon gallery-nav__icon--component";
    } else if (entry.type === "document") {
      iconEl.className = "gallery-nav__icon gallery-nav__icon--doc";
    } else if (entry.type === "folder") {
      iconEl.className = "gallery-nav__icon gallery-nav__icon--folder";
    }
    iconEl.setAttribute("aria-hidden", "true");
    headerEl.appendChild(iconEl);

    const labelEl = document.createElement("span");
    labelEl.className = "gallery-search-result__label";
    appendHighlightedText(labelEl, entry.label, words);
    headerEl.appendChild(labelEl);

    a.appendChild(headerEl);

    if (entry.breadcrumb) {
      const crumbEl = document.createElement("span");
      crumbEl.className = "gallery-search-result__breadcrumb";
      crumbEl.textContent = entry.breadcrumb;
      a.appendChild(crumbEl);
    }

    return a;
  }

  /**
   * Render results into the results panel and toggle visibility.
   *
   * @param {Array} results
   * @param {string[]} words
   * @param {HTMLElement} resultsEl
   * @param {HTMLElement} navEl
   */
  function renderResults(results, words, resultsEl, navEl) {
    resultsEl.innerHTML = "";

    if (results.length === 0) {
      const empty = document.createElement("p");
      empty.className = "gallery-search-empty";
      empty.textContent = "No results found.";
      resultsEl.appendChild(empty);
    } else {
      const MAX_RESULTS = 50;
      results.slice(0, MAX_RESULTS).forEach((entry) => {
        resultsEl.appendChild(buildResultItem(entry, words));
      });
      if (results.length > MAX_RESULTS) {
        const more = document.createElement("p");
        more.className = "gallery-search-empty";
        more.textContent =
          "Showing first " +
          MAX_RESULTS +
          " of " +
          results.length +
          " results. Refine your search for more specific results.";
        resultsEl.appendChild(more);
      }
    }

    resultsEl.hidden = false;
    navEl.hidden = true;
  }

  /**
   * Clear results and restore the nav tree.
   *
   * @param {HTMLElement} resultsEl
   * @param {HTMLElement} navEl
   */
  function clearResults(resultsEl, navEl) {
    resultsEl.hidden = true;
    resultsEl.innerHTML = "";
    navEl.hidden = false;
  }

  // ---------------------------------------------------------------------------
  // Debounce
  // ---------------------------------------------------------------------------

  /**
   * Return a debounced version of `fn` that waits `delay` ms after the
   * last call before executing.
   *
   * @param {Function} fn
   * @param {number} delay
   * @returns {Function}
   */
  function debounce(fn, delay) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  // ---------------------------------------------------------------------------
  // Initialisation
  // ---------------------------------------------------------------------------

  function init() {
    const input = document.getElementById("gallery-search-input");
    const resultsEl = document.getElementById("gallery-search-results");
    const navEl = document.getElementById("gallery-nav");

    if (!input || !resultsEl || !navEl) return;

    const index = loadIndex();

    const handleInput = debounce(function () {
      const query = input.value;
      if (query.trim().length === 0) {
        clearResults(resultsEl, navEl);
        return;
      }
      const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
      const results = search(query, index);
      renderResults(results, words, resultsEl, navEl);
    }, 150);

    input.addEventListener("input", handleInput);

    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        input.value = "";
        clearResults(resultsEl, navEl);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
