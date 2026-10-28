/* MPx Lab — shared interactions: bench launcher, deck viewer, lightbox, sortable tables,
   FMEA filters, requirement matrix, workbook viewer, small SVG line charts, section nav. */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  const json = (id) => JSON.parse(document.getElementById(id).textContent);

  /* ---------- bench launcher ---------- */
  $$(".bench").forEach((b) => {
    const stage = $(".bench-stage", b), poster = $(".bench-poster", b);
    const src = b.dataset.src;
    const launch = () => {
      if ($("iframe", stage)) return;
      const f = document.createElement("iframe");
      f.src = src; f.title = b.dataset.title || "Interactive bench"; f.loading = "eager";
      f.allow = "fullscreen"; stage.appendChild(f);
      poster && poster.remove();
      const r = $("[data-reload]", b); if (r) r.hidden = false;
    };
    poster && poster.addEventListener("click", launch);
    $$("[data-launch]", b).forEach((x) => x.addEventListener("click", launch));
    const r = $("[data-reload]", b);
    r && r.addEventListener("click", () => { const f = $("iframe", stage); if (f) f.src = src; });
  });

  /* ---------- deck viewer ---------- */
  $$(".deck").forEach((d) => {
    const slides = json(d.dataset.json);
    const img = $(".deck-stage img", d), ttl = $(".deck-foot .ttl", d), ctr = $(".deck-foot .ctr", d), strip = $(".deck-strip", d);
    const open = $("[data-open]", d);
    let i = 0;
    strip.innerHTML = slides.map((s, k) => `<button title="${esc(s.title)}" data-k="${k}"><img loading="lazy" src="${s.thumb}" alt=""><span>${String(k + 1).padStart(2, "0")}</span></button>`).join("");
    const show = (k) => {
      i = (k + slides.length) % slides.length;
      img.src = slides[i].src; img.alt = slides[i].title;
      ttl.textContent = slides[i].title; ctr.textContent = `${i + 1} / ${slides.length}`;
      if (open) open.href = slides[i].src;
      $$("button", strip).forEach((b, k2) => b.classList.toggle("on", k2 === i));
      const on = $("button.on", strip);
      if (on) strip.scrollTo({ left: on.offsetLeft - strip.clientWidth / 2 + on.clientWidth / 2, behavior: "smooth" });
      const nx = slides[(i + 1) % slides.length]; const pre = new Image(); pre.src = nx.src;
    };
    strip.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) show(+b.dataset.k); });
    $(".deck-nav.prev", d).addEventListener("click", () => show(i - 1));
    $(".deck-nav.next", d).addEventListener("click", () => show(i + 1));
    d.tabIndex = 0;
    d.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") { show(i + 1); e.preventDefault(); }
      if (e.key === "ArrowLeft") { show(i - 1); e.preventDefault(); }
    });
    const fs = $("[data-fs]", d);
    fs && fs.addEventListener("click", () => { document.fullscreenElement ? document.exitFullscreen() : d.requestFullscreen && d.requestFullscreen(); d.focus(); });
    let tx = null;
    $(".deck-stage", d).addEventListener("touchstart", (e) => { tx = e.touches[0].clientX; }, { passive: true });
    $(".deck-stage", d).addEventListener("touchend", (e) => { if (tx == null) return; const dx = e.changedTouches[0].clientX - tx; if (Math.abs(dx) > 40) show(i + (dx < 0 ? 1 : -1)); tx = null; });
    show(0);
  });

  /* ---------- lightbox with zoom + pan ---------- */
  const lb = document.createElement("div");
  lb.className = "lb";
  lb.innerHTML = `<div class="lb-bar"><button data-a="prev" aria-label="Previous">←</button><button data-a="next" aria-label="Next">→</button><div class="t"></div><button data-a="out">−</button><button data-a="fit">Fit</button><button data-a="in">+</button><a data-a="open" target="_blank" rel="noopener">Open file ↗</a><button data-a="close">Close ✕</button></div><div class="lb-view"><img alt=""></div><div class="lb-hint">Scroll or pinch to zoom · drag to pan · ← → for next · Esc to close</div>`;
  document.body.appendChild(lb);
  const view = $(".lb-view", lb), limg = $("img", view);
  let group = [], gi = 0, sc = 1, ox = 0, oy = 0;
  const apply = () => { limg.style.transform = `translate(${ox}px,${oy}px) scale(${sc})`; };
  const fit = () => {
    const it = group[gi] || {}; let iw = it.w || limg.naturalWidth || 1600, ih = it.h || limg.naturalHeight || 1000;
    if (it.w && it.w < 2400) { const k = 2400 / it.w; iw *= k; ih *= k; }
    const vw = view.clientWidth, vh = view.clientHeight;
    limg.style.width = iw + "px"; limg.style.height = ih + "px";
    sc = Math.min(vw / iw, vh / ih) * 0.96; ox = (vw - iw * sc) / 2; oy = (vh - ih * sc) / 2; apply();
  };
  const zoomAt = (f, cx, cy) => { const n = Math.min(Math.max(sc * f, 0.05), 40); ox = cx - (cx - ox) * (n / sc); oy = cy - (cy - oy) * (n / sc); sc = n; apply(); };
  const showLb = (k) => {
    gi = (k + group.length) % group.length; const it = group[gi];
    $(".t", lb).textContent = it.title || ""; $("[data-a=open]", lb).href = it.href;
    limg.onload = fit;
    limg.src = it.href;
    $("[data-a=prev]", lb).style.visibility = $("[data-a=next]", lb).style.visibility = group.length > 1 ? "visible" : "hidden";
  };
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-lb]");
    if (!a) return;
    e.preventDefault();
    const g = a.dataset.lb;
    group = $$(`a[data-lb="${g}"]`).map((x) => ({ href: x.getAttribute("href"), title: x.dataset.title || x.textContent.trim(), w: +x.dataset.w || 0, h: +x.dataset.h || 0 }));
    lb.classList.add("open"); document.body.style.overflow = "hidden";
    showLb(group.findIndex((x) => x.href === a.getAttribute("href")));
  });
  const closeLb = () => { lb.classList.remove("open"); document.body.style.overflow = ""; limg.src = ""; };
  lb.addEventListener("click", (e) => {
    const b = e.target.closest("[data-a]"); if (!b) return;
    const a = b.dataset.a, r = view.getBoundingClientRect();
    if (a === "close") closeLb();
    if (a === "prev") showLb(gi - 1);
    if (a === "next") showLb(gi + 1);
    if (a === "in") zoomAt(1.4, r.width / 2, r.height / 2);
    if (a === "out") zoomAt(1 / 1.4, r.width / 2, r.height / 2);
    if (a === "fit") fit();
  });
  document.addEventListener("keydown", (e) => {
    if (!lb.classList.contains("open")) return;
    if (e.key === "Escape") closeLb();
    if (e.key === "ArrowRight") showLb(gi + 1);
    if (e.key === "ArrowLeft") showLb(gi - 1);
    if (e.key === "+" || e.key === "=") zoomAt(1.3, view.clientWidth / 2, view.clientHeight / 2);
    if (e.key === "-") zoomAt(1 / 1.3, view.clientWidth / 2, view.clientHeight / 2);
  });
  view.addEventListener("wheel", (e) => { e.preventDefault(); const r = view.getBoundingClientRect(); zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top); }, { passive: false });
  const pts = new Map(); let pinch = null;
  view.addEventListener("pointerdown", (e) => { view.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); view.classList.add("drag"); });
  view.addEventListener("pointermove", (e) => {
    if (!pts.has(e.pointerId)) return;
    const [px, py] = pts.get(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2) {
      const [a, b] = Array.from(pts.values()); const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      const r = view.getBoundingClientRect();
      if (pinch) zoomAt(d / pinch, (a[0] + b[0]) / 2 - r.left, (a[1] + b[1]) / 2 - r.top);
      pinch = d; return;
    }
    ox += e.clientX - px; oy += e.clientY - py; apply();
  });
  const up = (e) => { pts.delete(e.pointerId); if (pts.size < 2) pinch = null; if (!pts.size) view.classList.remove("drag"); };
  view.addEventListener("pointerup", up); view.addEventListener("pointercancel", up);
  view.addEventListener("dblclick", (e) => { const r = view.getBoundingClientRect(); zoomAt(2, e.clientX - r.left, e.clientY - r.top); });
  window.addEventListener("resize", () => lb.classList.contains("open") && fit());

  /* ---------- sortable tables ---------- */
  const cellVal = (td) => {
    const v = td.dataset.v ?? td.textContent.trim();
    const n = parseFloat(String(v).replace(/[₹,%\s×]/g, ""));
    return isNaN(n) ? String(v).toLowerCase() : n;
  };
  $$("table.sortable").forEach((t) => {
    $$("thead th", t).forEach((th, ci) => {
      if (th.dataset.nosort !== undefined) return;
      th.classList.add("sortable");
      th.addEventListener("click", () => {
        const dir = th.classList.contains("asc") ? -1 : 1;
        $$("thead th", t).forEach((x) => x.classList.remove("asc", "desc"));
        th.classList.add(dir === 1 ? "asc" : "desc");
        const tb = t.tBodies[0];
        const rows = $$("tr", tb).filter((r) => !r.classList.contains("grp"));
        rows.sort((a, b) => { const x = cellVal(a.cells[ci]), y = cellVal(b.cells[ci]); return (x > y ? 1 : x < y ? -1 : 0) * dir; });
        $$("tr.grp", tb).forEach((r) => r.remove());
        rows.forEach((r) => tb.appendChild(r));
      });
    });
  });

  /* ---------- table filters (FMEA etc.) ---------- */
  $$("[data-filter-for]").forEach((box) => {
    const t = document.getElementById(box.dataset.filterFor);
    const run = () => {
      const q = ($("input[type=search]", box) || {}).value?.toLowerCase() || "";
      const crit = ($("input[data-crit]", box) || {}).checked;
      const st = ($("select[data-col]", box) || {});
      $$("tbody tr", t).forEach((r) => {
        let ok = !q || r.textContent.toLowerCase().includes(q);
        if (crit) ok = ok && r.dataset.crit === "1";
        if (st.value) ok = ok && (r.dataset[st.dataset.col] || "").split(" ").includes(st.value);
        r.classList.toggle("hide", !ok);
      });
    };
    $$("input,select", box).forEach((x) => x.addEventListener("input", run));
  });

  /* ---------- requirement matrix ---------- */
  $$("[data-reqm]").forEach((box) => {
    const t = document.getElementById(box.dataset.reqm);
    $$(".seg button", box).forEach((b) => b.addEventListener("click", () => {
      $$(".seg button", box).forEach((x) => x.classList.toggle("on", x === b));
      t.classList.toggle("compact", b.dataset.mode === "compact");
    }));
    const sel = $("select", box);
    sel && sel.addEventListener("input", () => {
      const v = sel.value;
      $$("tbody tr", t).forEach((r) => r.classList.toggle("hide", !!v && !r.dataset.st.split(" ").includes(v)));
    });
  });

  /* ---------- workbook viewer ---------- */
  const fmtCell = (v) => {
    if (v === null || v === undefined) return ["", ""];
    if (typeof v === "number") {
      let s;
      if (Number.isInteger(v)) s = Math.abs(v) >= 10000 ? v.toLocaleString("en-IN") : String(v);
      else if (Math.abs(v) >= 1000) s = Math.round(v).toLocaleString("en-IN");
      else if (Math.abs(v) >= 1) s = (+v.toFixed(2)).toString();
      else s = (+v.toPrecision(3)).toString();
      return [s, "n"];
    }
    const str = String(v);
    if (/^https?:\/\//.test(str)) return [`<a href="${esc(str)}" target="_blank" rel="noopener">${esc(str.replace(/^https?:\/\/(www\.|m\.)?/, "").slice(0, 48))}${str.length > 60 ? "…" : ""}</a>`, "", true];
    return [esc(str), str.length > 60 ? "wide" : str.length > 28 ? "mid" : ""];
  };
  $$(".wb").forEach((w) => {
    const data = json(w.dataset.json);
    const tabs = $(".wb-tabs", w), body = $(".wb-body", w);
    const render = (k) => {
      $$("button", tabs).forEach((b, i) => b.classList.toggle("on", i === k));
      const sh = data.sheets[k];
      let h = "";
      if (sh.title) h += `<p class="wb-title">${esc(sh.title)}</p>`;
      h += `<div class="tbl-wrap"><table class="tbl"><thead><tr>${sh.header.map((c) => `<th>${esc(c ?? "")}</th>`).join("")}</tr></thead><tbody>`;
      for (const r of sh.rows) {
        const filled = r.filter((c) => c !== null && c !== "");
        if (filled.length === 1 && typeof filled[0] === "string" && filled[0].length <= 60 && sh.header.length > 2) { h += `<tr class="grp"><td colspan="${sh.header.length}">${esc(filled[0])}</td></tr>`; continue; }
        const isTot = typeof r[0] === "string" && /total|landed|sum/i.test(r[0]) || typeof r[1] === "string" && /^total/i.test(r[1]) || typeof r[2] === "string" && /^total/i.test(r[2]);
        h += `<tr${isTot ? ' class="tot"' : ""}>` + sh.header.map((_, i) => { const [s, c] = fmtCell(r[i]); return `<td class="${c}">${s}</td>`; }).join("") + "</tr>";
      }
      h += "</tbody></table></div>";
      if (sh.notes && sh.notes.length) h += `<div class="note" style="margin-top:8px">${sh.notes.map(esc).join("<br>")}</div>`;
      body.innerHTML = h;
    };
    tabs.innerHTML = data.sheets.map((s) => `<button>${esc(s.name)}</button>`).join("");
    $$("button", tabs).forEach((b, i) => b.addEventListener("click", () => render(i)));
    render(0);
  });

  /* ---------- small line charts ---------- */
  const nice = (lo, hi, n = 5) => {
    const span = hi - lo || 1, step0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= n) || 10 * mag;
    const a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, t = [];
    for (let v = a; v <= b + step / 2; v += step) t.push(+v.toPrecision(10));
    return t;
  };
  $$(".chart[data-json]").forEach((c) => {
    const cfg = json(c.dataset.json);
    const W = 640, H = 300, m = { l: 52, r: 16, t: 12, b: 42 };
    const xs = cfg.x, all = cfg.series.flatMap((s) => s.y.filter((v) => v != null));
    const xt = nice(cfg.xmin ?? Math.min(...xs), cfg.xmax ?? Math.max(...xs), 6);
    const yt = nice(cfg.ymin ?? Math.min(0, ...all), cfg.ymax ?? Math.max(...all), 5);
    const X = (v) => m.l + ((v - xt[0]) / (xt[xt.length - 1] - xt[0])) * (W - m.l - m.r);
    const Y = (v) => H - m.b - ((v - yt[0]) / (yt[yt.length - 1] - yt[0])) * (H - m.t - m.b);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(cfg.title || "")}">`;
    if (cfg.band) s += `<rect x="${X(cfg.band[0])}" y="${m.t}" width="${X(cfg.band[1]) - X(cfg.band[0])}" height="${H - m.t - m.b}" fill="#DFF0E5" opacity=".7"/><text x="${(X(cfg.band[0]) + X(cfg.band[1])) / 2}" y="${m.t + 14}" text-anchor="middle" font-size="11" fill="#23784A">${esc(cfg.bandLabel || "")}</text>`;
    yt.forEach((v) => { s += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="#ECEBE6"/><text x="${m.l - 8}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#6A6963">${v}</text>`; });
    xt.forEach((v) => { s += `<text x="${X(v)}" y="${H - m.b + 18}" text-anchor="middle" font-size="11" fill="#6A6963">${v}</text>`; });
    s += `<line x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}" stroke="#C9C7BF"/>`;
    (cfg.hlines || []).forEach((h) => { s += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(h.y)}" y2="${Y(h.y)}" stroke="${h.color || "#1B1B19"}" stroke-dasharray="5 4"/><text x="${W - m.r}" y="${Y(h.y) - 5}" text-anchor="end" font-size="11" fill="${h.color || "#1B1B19"}">${esc(h.label)}</text>`; });
    (cfg.vlines || []).forEach((h) => { s += `<line y1="${m.t}" y2="${H - m.b}" x1="${X(h.x)}" x2="${X(h.x)}" stroke="${h.color || "#1B1B19"}" stroke-dasharray="5 4"/><text x="${X(h.x) + 5}" y="${m.t + 12}" font-size="11" fill="${h.color || "#1B1B19"}">${esc(h.label)}</text>`; });
    cfg.series.forEach((se) => {
      const p = xs.map((x, i) => (se.y[i] == null ? null : `${X(x).toFixed(1)},${Y(se.y[i]).toFixed(1)}`)).filter(Boolean);
      s += `<polyline points="${p.join(" ")}" fill="none" stroke="${se.color}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"${se.dash ? ' stroke-dasharray="6 4"' : ""}/>`;
      if (se.dots !== false) xs.forEach((x, i) => { if (se.y[i] != null) s += `<circle cx="${X(x)}" cy="${Y(se.y[i])}" r="3" fill="${se.color}"><title>${esc(se.name)}: ${x} → ${(+se.y[i].toPrecision(3))}</title></circle>`; });
    });
    s += `<text x="${(m.l + W - m.r) / 2}" y="${H - 6}" text-anchor="middle" font-size="11.5" fill="#1B1B19">${esc(cfg.xlabel || "")}</text>`;
    s += `<text transform="translate(13 ${(m.t + H - m.b) / 2}) rotate(-90)" text-anchor="middle" font-size="11.5" fill="#1B1B19">${esc(cfg.ylabel || "")}</text></svg>`;
    s += `<div class="lg">${cfg.series.map((se) => `<span><i style="background:${se.color}"></i>${esc(se.name)}</span>`).join("")}</div>`;
    $(".plot", c).innerHTML = s;
  });

  /* ---------- section nav highlight ---------- */
  const links = $$(".toc a[href^='#']");
  if (links.length && "IntersectionObserver" in window) {
    const map = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
    const io = new IntersectionObserver((es) => {
      es.forEach((e) => {
        if (!e.isIntersecting) return;
        links.forEach((a) => a.classList.remove("on"));
        const a = map.get(e.target.id); if (a) { a.classList.add("on"); const toc = a.parentElement; if (toc.scrollWidth > toc.clientWidth) toc.scrollTo({ left: a.offsetLeft - 20, behavior: "smooth" }); }
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    map.forEach((_, id) => { const el = document.getElementById(id); el && io.observe(el); });
  }
})();
