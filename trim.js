// A gallery's picture without the empty border its file carries (data/gallery_trim.py), for browsers that do not
// know object-view-box (Safari, Firefox). A picture marked data-tb="top right bottom left" (in %) is still the
// gallery's own file, fetched whole from the gallery: here it becomes the element's background, scaled and placed
// so that only the part inside the border shows, and the element itself holds an empty picture of that part's
// size, so every layout that goes by the picture's own size still does. csp.py adds this file to the pages that
// mark a picture. ?tb=js tries it in a browser that would not need it.
(function () {
  var force = /[?&]tb=js(&|$)/.test(location.search);
  if (!force && window.CSS && CSS.supports && CSS.supports("object-view-box", "inset(1%)")) return;
  var real = function (i) { var s = i.getAttribute("src") || ""; return s && s.slice(0, 5) !== "data:" };
  var place = function (i) {
    var t = i._tb; if (!t) return;
    var W = i.clientWidth, H = i.clientHeight; if (!W || !H) return;
    var fit = getComputedStyle(i).objectFit, sx = W / t.w, sy = H / t.h;
    if (fit === "cover") sx = sy = Math.max(sx, sy);
    else if (fit === "contain" || fit === "scale-down") sx = sy = Math.min(sx, sy);
    var rx = (W - t.w * sx) / 2, ry = (H - t.h * sy) / 2;            // where the part inside the border is drawn
    i.style.backgroundSize = t.nw * sx + "px " + t.nh * sy + "px";
    i.style.backgroundPosition = (rx - t.x * sx) + "px " + (ry - t.y * sy) + "px";
    i.style.clipPath = rx > .5 || ry > .5 ? "inset(" + Math.max(0, ry) + "px " + Math.max(0, rx) + "px)" : "";
  };
  var ro = window.ResizeObserver ? new ResizeObserver(function (es) { es.forEach(function (e) { place(e.target) }) }) : null;
  var take = function (i) {
    var tb = i.getAttribute("data-tb"); if (!tb || !real(i)) return;
    var v = tb.split(" ").map(parseFloat); if (v.length !== 4 || v.some(isNaN)) return;
    var src = i.currentSrc || i.src, probe = new Image();
    i.removeAttribute("data-tb");                                    // once: and the pages' own sums go by the new size
    probe.referrerPolicy = i.referrerPolicy || "";
    probe.onload = function () {
      var nw = probe.naturalWidth, nh = probe.naturalHeight; if (!nw || !nh) return;
      var t = i._tb = { nw: nw, nh: nh, x: nw * v[3] / 100, y: nh * v[0] / 100, w: nw * (100 - v[1] - v[3]) / 100, h: nh * (100 - v[0] - v[2]) / 100 };
      if (force) i.style.objectViewBox = "none";
      i.style.backgroundImage = 'url("' + src.replace(/["\\\n]/g, encodeURIComponent) + '")';
      i.style.backgroundRepeat = "no-repeat";
      i.src = "data:image/svg+xml," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="' + Math.round(t.w) + '" height="' + Math.round(t.h) + '"/>');
      if (ro) ro.observe(i);
      place(i); i.addEventListener("load", function () { place(i) });
    };
    probe.src = src;
  };
  var scan = function (n) {
    if (n.nodeType !== 1) return;
    if (n.tagName === "IMG") take(n); else if (n.querySelectorAll) Array.prototype.forEach.call(n.querySelectorAll("img[data-tb]"), take);
  };
  new MutationObserver(function (ms) {
    ms.forEach(function (m) {
      if (m.type === "attributes") take(m.target); else Array.prototype.forEach.call(m.addedNodes, scan);
    });
  }).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["src", "data-tb"] });
  var all = function () { scan(document.documentElement) };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", all); else all();
  addEventListener("resize", function () { Array.prototype.forEach.call(document.querySelectorAll("img"), place) });
})();
