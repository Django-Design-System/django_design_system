/**
 * Gallery toolbar – background colour popout + zoom popout.
 *
 * Communicates with the sandbox iframe via contentDocument (same-origin).
 *
 * initToolbar() is called on first load and again after every HTMX swap of
 * #gallery-sandbox-body, so the toolbar stays functional when component
 * parameters change without a full page reload.
 *
 * All user selections are stored in IIFE-scope state and restored each time
 * the toolbar and iframe are recreated after an HTMX swap.
 */
(function () {
  "use strict";

  /* ---- State preserved across re-inits --------------------------- */

  // Aborted at the start of each re-init to remove stale document listeners.
  var currentAbortController = null;

  // Toolbar selections – null means "use default / not yet chosen".
  var currentBg = null; // e.g. "white", "grey"
  var currentZoom = null; // integer percent, e.g. 100
  var currentViewportWidth = null; // px integer, null = responsive

  // On/off toggle states – objects so initToggle can mutate .active and .cleanup in place.
  var outlineState = { active: false, cleanup: null };
  var rtlState = { active: false, cleanup: null };
  var measureState = { active: false, cleanup: null };

  // Resolved once and kept in scope so applyIframeEffects can access it.
  var measureScriptSrc = null;

  /* ---- Helpers --------------------------------------------------- */

  function getSandboxIframe() {
    return document.querySelector(".gallery-sandbox__iframe");
  }

  function getCanvasWrapper(iframe) {
    try {
      return iframe.contentDocument.querySelector(".canvas-wrapper");
    } catch (e) {
      return null;
    }
  }

  function getIframeDocument() {
    var iframe = getSandboxIframe();
    if (!iframe) return null;
    try {
      return iframe.contentDocument;
    } catch (e) {
      return null;
    }
  }

  /**
   * Wire up a toggle button + popout panel pair.
   * Handles open/close, outside-click dismissal, and closing sibling popouts.
   *
   * @param {Element} toggle
   * @param {Element} panel
   * @param {AbortSignal} signal  Used to remove the document click listener on re-init.
   */
  function initPopout(toggle, panel, signal) {
    if (!toggle || !panel) return;

    toggle.addEventListener("click", function () {
      var opening = panel.hidden;
      closeAllPopouts();
      if (opening) {
        panel.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
      }
    });

    document.addEventListener(
      "click",
      function (e) {
        if (
          !panel.hidden &&
          !toggle.contains(e.target) &&
          !panel.contains(e.target)
        ) {
          panel.hidden = true;
          toggle.setAttribute("aria-expanded", "false");
        }
      },
      { signal: signal },
    );
  }

  /**
   * Wire up a simple on/off toggle button with aria-pressed.
   *
   * @param {string} selector  CSS selector for the toggle button.
   * @param {function} onActivate  Called with (iframeDoc) when toggling on. Should return a cleanup function.
   * @param {{ active: boolean, cleanup: ?function }} state  Shared state object persisted across
   *   re-inits. .active tracks on/off; .cleanup holds the teardown function for the current effect.
   */
  function initToggle(selector, onActivate, state) {
    var btn = document.querySelector(selector);
    if (!btn) return;

    // Restore button visual state after a re-init.
    // iframe effects are re-applied by reapplyToggleEffects() on the iframe load event.
    if (state.active) {
      btn.setAttribute("aria-pressed", "true");
      btn.classList.add("gallery-sandbox-toolbar__btn--active");
    }

    btn.addEventListener("click", function () {
      var doc = getIframeDocument();
      if (!doc) return;

      if (state.active) {
        if (state.cleanup) {
          state.cleanup(doc);
          state.cleanup = null;
        }
        state.active = false;
        btn.setAttribute("aria-pressed", "false");
        btn.classList.remove("gallery-sandbox-toolbar__btn--active");
      } else {
        state.cleanup = onActivate(doc);
        state.active = true;
        btn.setAttribute("aria-pressed", "true");
        btn.classList.add("gallery-sandbox-toolbar__btn--active");
      }
    });
  }

  /** Close every popout on the toolbar. */
  function closeAllPopouts() {
    document
      .querySelectorAll(".gallery-sandbox-toolbar__popout")
      .forEach(function (p) {
        p.hidden = true;
      });
    document.querySelectorAll("[aria-expanded]").forEach(function (btn) {
      btn.setAttribute("aria-expanded", "false");
    });
  }

  /**
   * Apply viewport scaling.
   * When the chosen viewport width exceeds the container, scale the iframe
   * down using CSS transform so media queries still fire at the true width.
   */
  function applyViewportScale() {
    var iframe = getSandboxIframe();
    if (!iframe) return;

    var container = iframe.closest(".gallery-sandbox__canvas");
    if (!container) return;

    if (!currentViewportWidth) {
      // Responsive: fill the container
      iframe.style.width = "";
      iframe.style.maxWidth = "";
      iframe.style.transform = "";
      iframe.style.transformOrigin = "";
      container.style.height = "";
      container.classList.remove("gallery-sandbox__canvas--viewport");
      return;
    }

    var paneWidth = container.clientWidth;
    iframe.style.width = currentViewportWidth + "px";
    iframe.style.maxWidth = "none";
    container.classList.add("gallery-sandbox__canvas--viewport");

    if (currentViewportWidth > paneWidth) {
      var scale = paneWidth / currentViewportWidth;
      iframe.style.transform = "scale(" + scale + ")";
      iframe.style.transformOrigin = "top left";
      // Correct container height for the scaled iframe
      container.style.height = iframe.offsetHeight * scale + "px";
    } else {
      iframe.style.transform = "";
      iframe.style.transformOrigin = "";
      container.style.height = "";
    }
  }

  /* ---- Constants ------------------------------------------------- */

  var OUTLINE_STYLE_ID = "gallery-box-model-outline";
  var outlineCSS =
    ".canvas-wrapper > * { outline: 2px solid rgba(255, 140, 0, 0.5) !important; " +
    "background-color: rgba(65, 105, 225, 0.2) !important; }" +
    ".canvas-wrapper > * * { outline: 2px solid rgba(255, 140, 0, 0.5) !important; " +
    "box-shadow: inset 0 0 0 1000px rgba(50, 205, 50, 0.12) !important; }";

  var MEASURE_STYLE_ID = "gallery-measure-style";
  var measureCSS = [
    ".gallery-measure-overlay { position: absolute; pointer-events: none; z-index: 99999; }",
    ".gallery-measure-margin { background: rgba(255, 165, 0, 0.3); }",
    ".gallery-measure-padding { background: rgba(50, 205, 50, 0.25); }",
    ".gallery-measure-content { background: rgba(65, 105, 225, 0.15); }",
    ".gallery-measure-label {",
    "  position: absolute; pointer-events: none; z-index: 100000;",
    "  background: rgba(35, 35, 50, 0.88); color: #fff;",
    "  font: 600 10px/1 monospace; padding: 2px 4px; border-radius: 2px;",
    "  white-space: nowrap;",
    "}",
  ].join("\n");

  /* ---- applyIframeEffects ---------------------------------------- */

  /**
   * Re-apply bg and zoom state to the sandbox iframe's contentDocument.
   *
   * Called each time the iframe finishes loading. Toggle effects (outline, RTL,
   * measure) are handled by reapplyToggleEffects() which is also called on load.
   */
  function applyIframeEffects() {
    var iframe = getSandboxIframe();
    var doc = iframe ? iframe.contentDocument : null;
    if (!doc || !doc.body) return;

    var wrapper = getCanvasWrapper(iframe);

    if (wrapper) {
      // Restore background colour selection
      if (currentBg !== null) {
        wrapper.className =
          wrapper.className.replace(/\bcanvas-bg-\S+/g, "").trim() +
          " canvas-bg-" +
          currentBg;
      }

      // Restore zoom level
      if (currentZoom !== null) {
        wrapper.style.zoom = currentZoom / 100;
      }
    }
  }

  /**
   * Re-apply active on/off toggle effects to the newly-loaded iframe document
   * and refresh each state's cleanup reference.
   *
   * Must be called from the iframe 'load' event (not { once: true }) so it
   * fires on every navigation of the iframe, not just the first blank-document
   * load that occurs when the element is inserted into the DOM.
   */
  function reapplyToggleEffects() {
    var doc = getIframeDocument();
    if (!doc || !doc.body) return;

    if (outlineState.active) {
      if (!doc.getElementById(OUTLINE_STYLE_ID)) {
        var outlineStyle = doc.createElement("style");
        outlineStyle.id = OUTLINE_STYLE_ID;
        outlineStyle.textContent = outlineCSS;
        doc.head.appendChild(outlineStyle);
      }
      outlineState.cleanup = function (d) {
        var el = d.getElementById(OUTLINE_STYLE_ID);
        if (el) el.remove();
      };
    }

    if (rtlState.active) {
      doc.documentElement.setAttribute("dir", "rtl");
      rtlState.cleanup = function (d) {
        d.documentElement.removeAttribute("dir");
      };
    }

    if (measureState.active && !doc.getElementById(MEASURE_STYLE_ID)) {
      var measureStyle = doc.createElement("style");
      measureStyle.id = MEASURE_STYLE_ID;
      measureStyle.textContent = measureCSS;
      doc.head.appendChild(measureStyle);

      var measureScript = doc.createElement("script");
      if (measureScriptSrc) {
        measureScript.src = measureScriptSrc;
      }
      doc.body.appendChild(measureScript);

      measureState.cleanup = function (d) {
        var wrapper = d.querySelector(".canvas-wrapper");
        if (wrapper && wrapper._galleryMeasureCleanup) {
          wrapper._galleryMeasureCleanup();
        }
        var el = d.getElementById(MEASURE_STYLE_ID);
        if (el) el.remove();
        var container = d.getElementById("gallery-measure-container");
        if (container) container.remove();
      };
    }
  }

  /* ---- initToolbar ----------------------------------------------- */

  /**
   * (Re-)initialise all toolbar event listeners.
   *
   * Safe to call multiple times: document-level listeners from the previous
   * call are removed via AbortController before new ones are added.
   * Element-level listeners are naturally cleaned up because HTMX replaces
   * the DOM nodes, discarding any listeners attached to the old elements.
   */
  function initToolbar() {
    if (currentAbortController) {
      currentAbortController.abort();
    }
    currentAbortController = new AbortController();
    var signal = currentAbortController.signal;

    /* -- Background colour -- */

    var bgToggle = document.querySelector(
      ".gallery-sandbox-toolbar__bg-toggle",
    );
    var bgPanel = document.querySelector('[data-gallery-panel="bg"]');

    initPopout(bgToggle, bgPanel, signal);

    if (bgPanel) {
      // Restore active selection in the newly-created panel
      if (currentBg !== null) {
        bgPanel
          .querySelectorAll(".gallery-sandbox-toolbar__bg-option")
          .forEach(function (opt) {
            opt.classList.toggle(
              "gallery-sandbox-toolbar__popout-option--active",
              opt.dataset.bg === currentBg,
            );
          });
        var activeChip = bgPanel.querySelector(
          "[data-bg='" + currentBg + "'] .gallery-sandbox-toolbar__bg-chip",
        );
        var swatch = bgToggle
          ? bgToggle.querySelector(".gallery-sandbox-toolbar__bg-swatch")
          : null;
        if (activeChip && swatch) {
          swatch.style.background =
            window.getComputedStyle(activeChip).background;
        }
      }

      bgPanel.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-bg]");
        if (!btn) return;

        var bgValue = btn.dataset.bg;
        currentBg = bgValue;
        var iframe = getSandboxIframe();
        if (!iframe) return;

        var wrapper = getCanvasWrapper(iframe);
        if (wrapper) {
          wrapper.className =
            wrapper.className.replace(/\bcanvas-bg-\S+/g, "").trim() +
            " canvas-bg-" +
            bgValue;
        }

        // Update swatch colour
        var swatch = bgToggle
          ? bgToggle.querySelector(".gallery-sandbox-toolbar__bg-swatch")
          : null;
        if (swatch) {
          var chip = btn.querySelector(".gallery-sandbox-toolbar__bg-chip");
          if (chip) {
            swatch.style.background = window.getComputedStyle(chip).background;
          }
        }

        // Update active state
        bgPanel
          .querySelectorAll(".gallery-sandbox-toolbar__bg-option")
          .forEach(function (opt) {
            opt.classList.toggle(
              "gallery-sandbox-toolbar__popout-option--active",
              opt === btn,
            );
          });

        closeAllPopouts();
      });
    }

    /* -- Zoom -- */

    var zoomToggle = document.querySelector(
      ".gallery-sandbox-toolbar__zoom-toggle",
    );
    var zoomPanel = document.querySelector('[data-gallery-panel="zoom"]');
    var zoomValueEl = document.querySelector(
      ".gallery-sandbox-toolbar__zoom-value",
    );

    initPopout(zoomToggle, zoomPanel, signal);

    if (zoomPanel) {
      // Restore zoom label and active state
      if (currentZoom !== null && zoomValueEl) {
        zoomValueEl.textContent = currentZoom + "%";
        zoomPanel
          .querySelectorAll(".gallery-sandbox-toolbar__zoom-btn")
          .forEach(function (b) {
            b.classList.toggle(
              "gallery-sandbox-toolbar__popout-option--active",
              parseInt(b.dataset.zoom, 10) === currentZoom,
            );
          });
      }

      zoomPanel.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-zoom]");
        if (!btn) return;

        currentZoom = parseInt(btn.dataset.zoom, 10);
        var zoomLevel = currentZoom / 100;
        var iframe = getSandboxIframe();
        if (!iframe) return;

        var wrapper = getCanvasWrapper(iframe);
        if (wrapper) {
          wrapper.style.zoom = zoomLevel;
        }

        // Update toggle label
        if (zoomValueEl) {
          zoomValueEl.textContent = btn.dataset.zoom + "%";
        }

        // Update active state
        zoomPanel
          .querySelectorAll(".gallery-sandbox-toolbar__zoom-btn")
          .forEach(function (b) {
            b.classList.toggle(
              "gallery-sandbox-toolbar__popout-option--active",
              b === btn,
            );
          });

        closeAllPopouts();
      });
    }

    /* -- Viewport -- */

    var viewportToggle = document.querySelector(
      ".gallery-sandbox-toolbar__viewport-toggle",
    );
    var viewportPanel = document.querySelector(
      '[data-gallery-panel="viewport"]',
    );
    var viewportValueEl = document.querySelector(
      ".gallery-sandbox-toolbar__viewport-value",
    );

    initPopout(viewportToggle, viewportPanel, signal);

    // Restore viewport label and active state in the newly-created toolbar
    if (viewportValueEl) {
      viewportValueEl.textContent =
        currentViewportWidth === null
          ? "Responsive"
          : currentViewportWidth + "px";
    }
    if (viewportPanel && currentViewportWidth !== null) {
      viewportPanel
        .querySelectorAll(".gallery-sandbox-toolbar__viewport-btn")
        .forEach(function (b) {
          b.classList.toggle(
            "gallery-sandbox-toolbar__popout-option--active",
            parseInt(b.dataset.viewport, 10) === currentViewportWidth,
          );
        });
    }

    // Recalculate on pane resize and iframe load
    var sandboxIframe = getSandboxIframe();
    if (sandboxIframe) {
      var canvasContainer = sandboxIframe.closest(".gallery-sandbox__canvas");

      // Re-apply all tool effects after every iframe load
      sandboxIframe.addEventListener("load", function () {
        applyViewportScale();
        applyIframeEffects();
        reapplyToggleEffects();
      });

      if (canvasContainer && typeof ResizeObserver !== "undefined") {
        new ResizeObserver(function () {
          if (currentViewportWidth) {
            applyViewportScale();
          }
        }).observe(canvasContainer);
      }
    }

    if (viewportPanel) {
      viewportPanel.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-viewport]");
        if (!btn) return;

        var value = btn.dataset.viewport;
        if (value === "responsive") {
          currentViewportWidth = null;
        } else {
          currentViewportWidth = parseInt(value, 10);
        }

        // Update toggle label
        if (viewportValueEl) {
          viewportValueEl.textContent =
            value === "responsive" ? "Responsive" : value + "px";
        }

        // Update active state
        viewportPanel
          .querySelectorAll(".gallery-sandbox-toolbar__viewport-btn")
          .forEach(function (b) {
            b.classList.toggle(
              "gallery-sandbox-toolbar__popout-option--active",
              b === btn,
            );
          });

        applyViewportScale();
        closeAllPopouts();
      });
    }

    /* -- Box model outline -- */

    initToggle(
      ".gallery-sandbox-toolbar__outline-toggle",
      function (doc) {
        var style = doc.createElement("style");
        style.id = OUTLINE_STYLE_ID;
        style.textContent = outlineCSS;
        doc.head.appendChild(style);
        return function (doc) {
          var el = doc.getElementById(OUTLINE_STYLE_ID);
          if (el) el.remove();
        };
      },
      outlineState,
    );

    /* -- RTL direction -- */

    initToggle(
      ".gallery-sandbox-toolbar__rtl-toggle",
      function (doc) {
        doc.documentElement.setAttribute("dir", "rtl");
        return function (doc) {
          doc.documentElement.removeAttribute("dir");
        };
      },
      rtlState,
    );

    /* -- Measure -- */

    var toolbar = document.querySelector(".gallery-sandbox-toolbar");
    measureScriptSrc = toolbar ? toolbar.dataset.measureScript : null;

    initToggle(
      ".gallery-sandbox-toolbar__measure-toggle",
      function (doc) {
        var style = doc.createElement("style");
        style.id = MEASURE_STYLE_ID;
        style.textContent = measureCSS;
        doc.head.appendChild(style);

        var script = doc.createElement("script");
        if (measureScriptSrc) {
          script.src = measureScriptSrc;
        }
        doc.body.appendChild(script);

        return function (doc) {
          // Call the cleanup function registered by the measure script
          var wrapper = doc.querySelector(".canvas-wrapper");
          if (wrapper && wrapper._galleryMeasureCleanup) {
            wrapper._galleryMeasureCleanup();
          }
          var el = doc.getElementById(MEASURE_STYLE_ID);
          if (el) el.remove();
          var container = doc.getElementById("gallery-measure-container");
          if (container) container.remove();
        };
      },
      measureState,
    );
  }

  /* ---- Bootstrap ------------------------------------------------- */

  initToolbar();

  // Re-initialise whenever HTMX swaps the gallery sandbox body. Added once at
  // module level (no abort needed) so it survives across multiple swaps.
  document.addEventListener("htmx:afterSwap", function (e) {
    if (e.detail.target.hasAttribute("data-gallery-sandbox-body")) {
      initToolbar();
    }
  });
})();
