/**
 * Measure overlay — injected into the canvas iframe by the toolbar.
 *
 * Draws colour-coded bands showing margin (orange), padding (green), and
 * content area (blue) with pixel-value labels for the hovered element.
 *
 * Registers a cleanup function on the wrapper element so the toolbar can
 * remove event listeners when the tool is toggled off.
 */
(function () {
  "use strict";

  var container = null;
  var wrapper = document.querySelector(".canvas-wrapper");
  if (!wrapper) return;

  function createEl(cls) {
    var el = document.createElement("div");
    el.className = "gallery-measure-overlay " + cls;
    return el;
  }

  function createLabel(text) {
    var el = document.createElement("div");
    el.className = "gallery-measure-label";
    el.textContent = text;
    return el;
  }

  function px(v) {
    return parseFloat(v) || 0;
  }

  function clear() {
    if (container) {
      container.remove();
      container = null;
    }
  }

  function measure(el) {
    clear();
    var cs = window.getComputedStyle(el);
    var rect = el.getBoundingClientRect();
    var scrollX = window.scrollX;
    var scrollY = window.scrollY;

    var mt = px(cs.marginTop),
      mr = px(cs.marginRight);
    var mb = px(cs.marginBottom),
      ml = px(cs.marginLeft);
    var pt = px(cs.paddingTop),
      pr = px(cs.paddingRight);
    var pb = px(cs.paddingBottom),
      pl = px(cs.paddingLeft);
    var bt = px(cs.borderTopWidth),
      br2 = px(cs.borderRightWidth);
    var bb = px(cs.borderBottomWidth),
      bl = px(cs.borderLeftWidth);

    var w = rect.width;
    var h = rect.height;
    var contentW = w - pl - pr - bl - br2;
    var contentH = h - pt - pb - bt - bb;

    container = document.createElement("div");
    container.id = "gallery-measure-container";
    container.style.cssText =
      "position:absolute;top:0;left:0;width:0;height:0;pointer-events:none;z-index:99998;";

    var bx = rect.left + scrollX;
    var by = rect.top + scrollY;

    function addBand(cls, x, y, w, h, label) {
      if (w <= 0 || h <= 0) return;
      var band = createEl(cls);
      band.style.cssText =
        "left:" +
        x +
        "px;top:" +
        y +
        "px;width:" +
        w +
        "px;height:" +
        h +
        "px;";
      container.appendChild(band);
      if (label) {
        var lbl = createLabel(label);
        container.appendChild(lbl);
        lbl.style.left = x + w / 2 + "px";
        lbl.style.top = y + h / 2 + "px";
        lbl.style.transform = "translate(-50%, -50%)";
      }
    }

    // Margin bands (outside the border box)
    if (mt > 0)
      addBand(
        "gallery-measure-margin",
        bx - ml,
        by - mt,
        w + ml + mr,
        mt,
        mt + "",
      );
    if (mb > 0)
      addBand(
        "gallery-measure-margin",
        bx - ml,
        by + h,
        w + ml + mr,
        mb,
        mb + "",
      );
    if (ml > 0) addBand("gallery-measure-margin", bx - ml, by, ml, h, ml + "");
    if (mr > 0) addBand("gallery-measure-margin", bx + w, by, mr, h, mr + "");

    // Padding bands (inside the border box)
    var ix = bx + bl;
    var iy = by + bt;
    var iw = w - bl - br2;
    var ih = h - bt - bb;
    if (pt > 0) addBand("gallery-measure-padding", ix, iy, iw, pt, pt + "");
    if (pb > 0)
      addBand("gallery-measure-padding", ix, iy + ih - pb, iw, pb, pb + "");
    if (pl > 0)
      addBand(
        "gallery-measure-padding",
        ix,
        iy + pt,
        pl,
        ih - pt - pb,
        pl + "",
      );
    if (pr > 0)
      addBand(
        "gallery-measure-padding",
        ix + iw - pr,
        iy + pt,
        pr,
        ih - pt - pb,
        pr + "",
      );

    // Content area (innermost)
    var cx = ix + pl;
    var cy = iy + pt;
    if (contentW > 0 && contentH > 0) {
      addBand(
        "gallery-measure-content",
        cx,
        cy,
        contentW,
        contentH,
        Math.round(contentW) + " \u00d7 " + Math.round(contentH),
      );
    }

    document.body.appendChild(container);
  }

  function onMouseOver(e) {
    if (e.target === wrapper) {
      clear();
      return;
    }
    measure(e.target);
  }

  function onMouseOut(e) {
    if (!wrapper.contains(e.relatedTarget)) clear();
  }

  wrapper.addEventListener("mouseover", onMouseOver);
  wrapper.addEventListener("mouseout", onMouseOut);

  // Register cleanup so the toolbar can remove listeners on toggle-off
  wrapper._galleryMeasureCleanup = function () {
    clear();
    wrapper.removeEventListener("mouseover", onMouseOver);
    wrapper.removeEventListener("mouseout", onMouseOut);
    delete wrapper._galleryMeasureCleanup;
  };
})();
