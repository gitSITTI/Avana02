/* Checks that run inside the page for b20.py (accessibility). Nothing here changes the page.
   window.reqinA11y.contrast()    text whose colour against its background is below WCAG 2.x AA (4.5 to 1, or 3 to 1 for large text)
   window.reqinA11y.nonText()     the edges of fields and buttons, and the marks in charts, against what is behind them (3 to 1, WCAG 1.4.11)
   window.reqinA11y.pointerOnly() things that react to a mouse click but cannot be reached with the keyboard
   window.reqinA11y.hiddenStops() things the Tab key can land on that cannot be seen
   The page is checked as it is drawn, so a colour set by a rule, a variable or a style attribute is the colour that is measured. */
(function () {
  function parse(s) {
    let m = /^rgba?\(([^)]+)\)$/.exec(s);
    if (m) { const p = m[1].split(/[\s,\/]+/).filter(Boolean); return { r: +p[0], g: +p[1], b: +p[2], a: p.length > 3 ? +p[3] : 1 }; }
    m = /^color\(srgb ([^)]+)\)$/.exec(s);
    if (m) { const p = m[1].split(/[\s\/]+/).filter(Boolean).map(Number); return { r: p[0] * 255, g: p[1] * 255, b: p[2] * 255, a: p.length > 3 ? p[3] : 1 }; }
    return null;
  }
  const over = (t, b) => { const a = t.a + b.a * (1 - t.a); return a === 0 ? { r: 0, g: 0, b: 0, a: 0 } : { r: (t.r * t.a + b.r * b.a * (1 - t.a)) / a, g: (t.g * t.a + b.g * b.a * (1 - t.a)) / a, b: (t.b * t.a + b.b * b.a * (1 - t.a)) / a, a }; };
  const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const lum = (c) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const hex = (c) => '#' + [c.r, c.g, c.b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');
  const rgbText = (c) => c ? 'rgb(' + Math.round(c.r) + ',' + Math.round(c.g) + ',' + Math.round(c.b) + ')' : '';
  const WHITE = { r: 255, g: 255, b: 255, a: 1 };

  /* what is behind an element: the first solid colour on the way up, with every translucent layer above it laid over */
  function backdrop(el) {
    const layers = [];
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage !== 'none') return { unknown: 'a gradient or picture behind it (' + e.tagName.toLowerCase() + ')' };
      const bg = parse(cs.backgroundColor);
      if (bg && bg.a > 0) { layers.push(bg); if (bg.a >= 1) break; }
    }
    let acc = layers.length && layers[layers.length - 1].a >= 1 ? layers.pop() : WHITE;
    while (layers.length) acc = over(layers.pop(), acc);
    return { color: acc };
  }
  function opacityOf(el) { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity); return o; }
  function visible(el) {
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return false; }
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  }
  const describe = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.getAttribute('data-dc-tpl') ? '[tpl ' + el.getAttribute('data-dc-tpl') + ']' : '');
  const inactive = (el) => !!el.closest('[disabled],[aria-disabled="true"]');

  /* inside an svg, what is behind a mark is the last shape drawn before it that covers its middle */
  function svgBackdrop(t) {
    const svg = t.ownerSVGElement; if (!svg) return backdrop(t);
    const r = t.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    let found = null;
    for (const s of svg.querySelectorAll('rect,circle,ellipse,polygon,path')) {
      if (s === t || (t.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
      const cs = getComputedStyle(s), f = parse(cs.fill);
      if (!f || f.a === 0 || cs.fill === 'none') continue;
      const b = s.getBoundingClientRect();
      if (cx >= b.left && cx <= b.right && cy >= b.top && cy <= b.bottom) found = { f, o: parseFloat(cs.fillOpacity) * parseFloat(cs.opacity) };
    }
    const base = backdrop(svg);
    if (base.unknown) return base;
    return found ? { color: over({ r: found.f.r, g: found.f.g, b: found.f.b, a: found.f.a * found.o }, base.color) } : base;
  }

  function contrast() {
    const bad = [], unknown = []; let checked = 0;
    const els = document.body.querySelectorAll('*');
    for (const el of els) {
      const tag = el.tagName.toLowerCase();
      if (['script', 'style', 'noscript', 'option'].indexOf(tag) >= 0) continue;
      if (!Array.prototype.some.call(el.childNodes, (n) => n.nodeType === 3 && n.nodeValue.trim())) continue;
      if (!visible(el) || inactive(el)) continue;
      if (el.closest('[aria-hidden="true"]') && !/[A-Za-z0-9]/.test(el.textContent)) continue;   // a decorative mark such as a slash between two names
      const cs = getComputedStyle(el);
      if (cs.clipPath !== 'none' || (cs.position === 'absolute' && cs.overflow === 'hidden' && el.getBoundingClientRect().width <= 1)) continue;
      const isSvg = el instanceof SVGElement;
      const fg0 = parse(isSvg ? cs.fill : cs.color); if (!fg0) continue;
      const bd = isSvg ? svgBackdrop(el) : backdrop(el);
      const px = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 700, large = px >= 24 || (px >= 18.66 && bold);
      const text = el.textContent.trim().replace(/\s+/g, ' ').slice(0, 50);
      if (bd.unknown) { unknown.push({ el: describe(el), text, why: bd.unknown }); continue; }
      const fg = over({ r: fg0.r, g: fg0.g, b: fg0.b, a: fg0.a * opacityOf(el) }, bd.color);
      const rt = ratio(fg, bd.color), need = large ? 3 : 4.5;
      checked++;
      if (rt < need - 0.005) bad.push({ el: describe(el), text, ratio: Math.round(rt * 100) / 100, need, fg: hex(fg), bg: hex(bd.color), size: px });
    }
    return { bad, unknown, checked };
  }

  /* the edge of a field or a button must stand out from what is behind it by 3 to 1, unless the button has a filled face or its words say what it is */
  function nonText() {
    const bad = []; let checked = 0;
    for (const el of document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]),select,textarea')) {
      if (!visible(el) || inactive(el)) continue;
      const cs = getComputedStyle(el), bd = backdrop(el.parentElement || el);
      if (bd.unknown) continue;
      const edge = parse(cs.borderTopColor), fill = parse(cs.backgroundColor);
      const w = parseFloat(cs.borderTopWidth) || 0;
      const edgeRatio = w >= 1 && edge && edge.a > 0 ? ratio(over(edge, bd.color), bd.color) : 0;
      const fillRatio = fill && fill.a > 0 ? ratio(over(fill, bd.color), bd.color) : 0;
      checked++;
      if (Math.max(edgeRatio, fillRatio) < 3) bad.push({ el: describe(el), edge: Math.round(edgeRatio * 100) / 100, fill: Math.round(fillRatio * 100) / 100 });
    }
    return { bad, checked };
  }

  function pointerOnly() {
    const out = [];
    for (const e of document.body.querySelectorAll('*')) {
      const cs = getComputedStyle(e);
      if (cs.cursor !== 'pointer') continue;
      if (e.closest('a,button,[role=button],[role=tab],[role=link],[role=menuitem],input,select,textarea,summary,label,[tabindex],[aria-hidden="true"]')) continue;
      if (!visible(e)) continue;
      out.push(describe(e) + ' ' + (e.getAttribute('title') || e.textContent || '').trim().slice(0, 40));
    }
    return out;
  }

  function hiddenStops() {
    const out = [];
    const sel = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[tabindex]';
    for (const e of document.body.querySelectorAll(sel)) {
      if (e.disabled || e.tabIndex < 0) continue;
      if (e.closest('[hidden],[inert]')) continue;
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      const r = e.getBoundingClientRect();
      const skipLink = e.classList && e.classList.contains('skip-link');
      if (!skipLink && (r.width < 1 || r.height < 1)) out.push(describe(e) + ' has no size');
    }
    return out;
  }

  window.reqinA11y = { contrast, nonText, pointerOnly, hiddenStops, ratio, parse, hex, rgbText };
})();
