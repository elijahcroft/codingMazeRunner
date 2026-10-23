// Cake Shop: draws a cake on a canvas, and animates it being made.
// Shared by the student page, the shop window and the projector.
//
// A cake is a list of tiers, bottom first, each one
//   {layers: [...], frosting, drip, sprinkles, swirls: [...], toppings: [...],
//    candles: [...], text}
// exactly as cake.py builds it. A bake is a list of steps ({do, arg}); apply()
// replays them so the page can show the cake at any point while it's made.
(function () {
  "use strict";
  let P = {flavours: {}, colours: {}, toppings: {}};
  const RAINBOW = ["#ff5f6d", "#ffa94d", "#ffd93d", "#6bd66b", "#5cb8ff", "#a77bff"];
  const SPRINKLE_MIX = ["#ff5f8f", "#ffd447", "#5cc8ff", "#7ee081", "#b38cff", "#ffffff", "#ff9b54"];

  function setPalette(palette) { P = palette; }

  // ---- the cake as data ----------------------------------------------------------
  function newTier() {
    return {layers: [], frosting: null, drip: null, sprinkles: null, swirls: [], toppings: [], candles: [], text: null};
  }
  function apply(tiers, step) {
    const t = tiers[tiers.length - 1];
    switch (step.do) {
      case "tier": tiers.push(newTier()); break;
      case "layer": t.layers.push(step.arg); break;
      case "swirl": t.swirls.push(step.arg); break;
      case "topping": t.toppings.push(step.arg); break;
      case "candle": t.candles.push(step.arg); break;
      case "write": t.text = step.arg; break;
      default: t[step.do] = step.arg;   // frosting, drip, sprinkles
    }
    return tiers;
  }
  function replay(steps, k) {
    const tiers = [newTier()];
    for (let i = 0; i < k && i < steps.length; i++) apply(tiers, steps[i]);
    return tiers;
  }

  // ---- colour helpers ---------------------------------------------------------------
  function hexOf(name, kind) {
    if (!name) return null;
    if (name[0] === "#") return name;
    if (kind === "flavour") return P.flavours[name] || "#f2dcb0";
    return P.colours[name] || {glitter: "#f3e3b3", galaxy: "#3b2a6b", rainbow: "#ff9ec7", gold: "#e3b341", classic: "#fff6e8", rainbowsprinkles: "#fff"}[name] || "#ffffff";
  }
  function rgb(hex) {
    const h = hex.replace("#", "");
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }
  function shade(hex, f) {
    const [r, g, b] = rgb(hex);
    const t = f < 0 ? 0 : 255, p = Math.abs(f);
    const mix = v => Math.round((t - v) * p + v);
    return `rgb(${mix(r)},${mix(g)},${mix(b)})`;
  }
  function light(hex) {
    const [r, g, b] = rgb(hex);
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  }
  function hash(a, b = 0, c = 0) {
    let h = (a * 374761393 + b * 668265263 + c * 2147483647) | 0;
    h = (h ^ (h >>> 13)) * 1274126177 | 0;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }
  const easeOut = u => 1 - Math.pow(1 - u, 3);
  const easeBack = u => { const c = 1.9; return 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); };
  function bounce(u) {
    const n = 7.5625, d = 2.75;
    if (u < 1 / d) return n * u * u;
    if (u < 2 / d) return n * (u -= 1.5 / d) * u + .75;
    if (u < 2.5 / d) return n * (u -= 2.25 / d) * u + .9375;
    return n * (u -= 2.625 / d) * u + .984375;
  }
  const clamp01 = u => Math.max(0, Math.min(1, u));

  // A fill for a colour name: plain colours get a soft cylinder shading, and the
  // special frostings get their own look.
  function paint(ctx, name, kind, x0, x1, y0, y1, flat) {
    const hex = hexOf(name, kind);
    if (name === "rainbow" && kind !== "sprinkles") {
      const g = ctx.createLinearGradient(x0, 0, x1, 0);
      RAINBOW.forEach((c, i) => g.addColorStop(i / (RAINBOW.length - 1), c));
      return g;
    }
    if (name === "galaxy") {
      const g = ctx.createLinearGradient(x0, y0, x1, y1);
      g.addColorStop(0, "#1c1440"); g.addColorStop(.45, "#4b2a8a"); g.addColorStop(.7, "#2a4d9b"); g.addColorStop(1, "#160f33");
      return g;
    }
    if (name === "gold") {
      const g = ctx.createLinearGradient(x0, y0, x1, y1);
      g.addColorStop(0, "#9c6f12"); g.addColorStop(.3, "#ffe08a"); g.addColorStop(.5, "#d9a52b"); g.addColorStop(.75, "#fff1b8"); g.addColorStop(1, "#8f6410");
      return g;
    }
    if (flat) return hex;
    const g = ctx.createLinearGradient(x0, 0, x1, 0);
    g.addColorStop(0, shade(hex, -.3)); g.addColorStop(.28, shade(hex, .12)); g.addColorStop(.5, hex); g.addColorStop(1, shade(hex, -.34));
    return g;
  }
  // Glitter sparkles and galaxy stars, inside whatever path is clipped.
  function texture(ctx, name, x0, y0, w, h, s, now, seed) {
    if (name !== "glitter" && name !== "galaxy") return;
    const n = Math.min(90, Math.round(w * h / (220 * s * s)));
    for (let i = 0; i < n; i++) {
      const x = x0 + hash(seed, i, 1) * w, y = y0 + hash(seed, i, 2) * h;
      const tw = .5 + .5 * Math.sin(now / 300 + i * 1.7);
      ctx.fillStyle = name === "galaxy" ? `rgba(255,255,255,${.35 + .6 * tw})` : `rgba(255,250,220,${.3 + .7 * tw})`;
      const r = (name === "galaxy" ? .9 : 1.3) * s * (.6 + hash(seed, i, 3));
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
      if (name === "glitter" && tw > .85) {
        ctx.strokeStyle = "rgba(255,255,255,.9)"; ctx.lineWidth = .8 * s;
        ctx.beginPath(); ctx.moveTo(x - 3 * s, y); ctx.lineTo(x + 3 * s, y); ctx.moveTo(x, y - 3 * s); ctx.lineTo(x, y + 3 * s); ctx.stroke();
      }
    }
  }

  // ---- shapes ---------------------------------------------------------------------------
  // The side of a cylinder from yTop to yBot (front half only).
  function side(ctx, cx, yTop, yBot, rx, ry) {
    ctx.beginPath();
    ctx.moveTo(cx - rx, yTop);
    ctx.lineTo(cx - rx, yBot);
    ctx.ellipse(cx, yBot, rx, ry, 0, Math.PI, 0, true);
    ctx.lineTo(cx + rx, yTop);
    ctx.ellipse(cx, yTop, rx, ry, 0, 0, Math.PI, false);
    ctx.closePath();
  }
  function ellipse(ctx, cx, cy, rx, ry) {
    ctx.beginPath(); ctx.ellipse(cx, cy, Math.max(rx, .1), Math.max(ry, .1), 0, 0, Math.PI * 2);
  }

  // ---- layout: how big everything is, from the finished cake ----------------------
  const LH = 34, FILL = 6, CAP = 8, BASE_W = 300;
  const STAND_H = {plate: 10, board: 14, glass: 64, pink: 64, gold: 64};
  function tierWidth(i) { return BASE_W * Math.max(.42, 1 - .21 * i); }
  function tierHeight(t) {
    const n = Math.max(1, t.layers.length);
    return n * LH + (n - 1) * FILL + (t.frosting ? 4 : 0);
  }
  function layout(w, h, fit, stand) {
    const tiers = fit && fit.length ? fit : [newTier()];
    let height = (STAND_H[stand] || 10) + 18;
    tiers.forEach((t, i) => { height += tierHeight(t); });
    const top = tiers[tiers.length - 1];
    const topRy = tierWidth(tiers.length - 1) / 2 * .27;
    height += topRy + (top.candles.length ? 44 : top.toppings.length ? 34 : top.swirls.length ? 22 : 8);
    height += BASE_W / 2 * .27 + 10;
    const width = BASE_W * 1.3;
    const s = Math.min(w * .94 / width, h * .94 / height, 2.4);
    const base = h - (h - height * s) / 2 - (BASE_W / 2 * .27 + 10) * s;
    return {s, cx: w / 2, base};
  }

  // ---- the stand ---------------------------------------------------------------------------
  function drawStand(ctx, L, stand) {
    const {s, cx} = L;
    const rx = BASE_W / 2 * 1.18 * s, ry = rx * .27;
    const y = L.base;
    const lift = (STAND_H[stand] || 10) * s;
    ctx.save();
    // soft shadow on the counter
    ctx.fillStyle = "rgba(80,40,30,.16)";
    ellipse(ctx, cx, y + 6 * s, rx * 1.02, ry * 1.05); ctx.fill();
    if (stand === "glass" || stand === "pink" || stand === "gold") {
      const col = {glass: "rgba(210,236,255,.55)", pink: "#f7a8c4", gold: "#e0b04a"}[stand];
      const edge = {glass: "rgba(150,190,220,.9)", pink: "#d97699", gold: "#a57818"}[stand];
      // foot and stem
      ctx.fillStyle = col; ctx.strokeStyle = edge; ctx.lineWidth = 1.5 * s;
      ellipse(ctx, cx, y, rx * .5, ry * .5); ctx.fill(); ctx.stroke();
      const g = ctx.createLinearGradient(cx - 14 * s, 0, cx + 14 * s, 0);
      g.addColorStop(0, edge); g.addColorStop(.4, stand === "glass" ? "rgba(255,255,255,.8)" : shade(stand === "pink" ? "#f7a8c4" : "#e0b04a", .4)); g.addColorStop(1, edge);
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.moveTo(cx - 18 * s, y - 4 * s); ctx.quadraticCurveTo(cx - 8 * s, y - lift * .5, cx - 10 * s, y - lift + 6 * s);
      ctx.lineTo(cx + 10 * s, y - lift + 6 * s); ctx.quadraticCurveTo(cx + 8 * s, y - lift * .5, cx + 18 * s, y - 4 * s); ctx.closePath(); ctx.fill();
      // the plate on top
      ctx.fillStyle = col;
      side(ctx, cx, y - lift, y - lift + 7 * s, rx, ry); ctx.fill(); ctx.stroke();
      ctx.fillStyle = stand === "glass" ? "rgba(235,248,255,.75)" : shade(stand === "pink" ? "#f7a8c4" : "#e0b04a", .25);
      ellipse(ctx, cx, y - lift, rx, ry); ctx.fill(); ctx.stroke();
      if (stand === "gold") { ctx.strokeStyle = "rgba(255,245,200,.8)"; ctx.lineWidth = 2 * s; ellipse(ctx, cx, y - lift, rx * .92, ry * .92); ctx.stroke(); }
    } else if (stand === "board") {
      ctx.fillStyle = "#a8714a";
      side(ctx, cx, y - lift, y, rx, ry); ctx.fill();
      ctx.fillStyle = "#c98f61"; ellipse(ctx, cx, y - lift, rx, ry); ctx.fill();
      ctx.strokeStyle = "rgba(120,70,40,.35)"; ctx.lineWidth = 1.2 * s;
      for (let k = 1; k <= 4; k++) { ellipse(ctx, cx, y - lift, rx * k / 4.6, ry * k / 4.6); ctx.stroke(); }
    } else {
      ctx.fillStyle = "#e9e3e6";
      side(ctx, cx, y - lift, y, rx, ry); ctx.fill();
      ctx.fillStyle = "#fffefe"; ellipse(ctx, cx, y - lift, rx, ry); ctx.fill();
      ctx.strokeStyle = "rgba(200,185,195,.9)"; ctx.lineWidth = 1.2 * s;
      ellipse(ctx, cx, y - lift, rx * .84, ry * .84); ctx.stroke();
    }
    ctx.restore();
    return y - lift;
  }

  // ---- one tier ------------------------------------------------------------------------------
  function drawTier(ctx, t, i, L, baseY, anim, now, isTop, above) {
    const s = L.s, cx = L.cx;
    const rx = tierWidth(i) / 2 * s, ry = rx * .27;
    const n = t.layers.length;
    if (!n) return {top: baseY, rx, ry, front: []};
    const cur = anim && anim.tier === i ? anim : null;
    const lift = cur && cur.do === "layer" ? -(1 - bounce(cur.u)) * 150 * s : 0;
    const frostU = cur && cur.do === "frosting" ? easeOut(cur.u) : 1;
    let y = baseY;
    let topY = baseY;
    // Layers and the filling between them, bottom first.
    for (let k = 0; k < n; k++) {
      const last = k === n - 1;
      const dy = last ? lift : 0;
      const yb = y + dy, yt = y - LH * s + dy;
      const hex = hexOf(t.layers[k], "flavour");
      ctx.save();
      if (last && lift) ctx.globalAlpha = .4 + .6 * clamp01(cur.u * 2);
      side(ctx, cx, yt, yb, rx, ry);
      ctx.fillStyle = paint(ctx, t.layers[k], "flavour", cx - rx, cx + rx, yt, yb);
      ctx.fill();
      // crumbs, and dark chips for cookies
      ctx.clip();
      const chips = t.layers[k] === "cookies";
      for (let c = 0; c < (chips ? 26 : 14); c++) {
        const px = cx - rx + hash(i, k, c) * rx * 2, py = yt + hash(k, c, i + 9) * LH * s + ry * .4;
        ctx.fillStyle = chips ? "rgba(50,30,25,.75)" : `rgba(255,255,255,${.12 + hash(c, k) * .12})`;
        ctx.beginPath(); ctx.arc(px, py, (chips ? 1.8 : 1.4) * s, 0, Math.PI * 2); ctx.fill();
      }
      ctx.restore();
      y -= LH * s;
      topY = y + dy;
      if (!last) {
        // the filling: frosting if there is any, cream if not
        const fill = t.frosting || "cream";
        ctx.save();
        ctx.globalAlpha = t.frosting ? frostU : 1;
        side(ctx, cx, y - FILL * s, y, rx * 1.005, ry);
        ctx.fillStyle = paint(ctx, fill, "colour", cx - rx, cx + rx, y - FILL * s, y);
        ctx.fill();
        if (t.frosting) { ctx.clip(); texture(ctx, t.frosting, cx - rx, y - FILL * s, rx * 2, FILL * s + ry, s, now, 7 + k); }
        ctx.restore();
        y -= FILL * s;
      }
    }
    const textY = (baseY + topY) / 2 + ry * .95;
    // The writing goes on the front of the side.
    // The drip runs over the rim and down the side.
    if (t.drip) {
      const u = cur && cur.do === "drip" ? easeOut(cur.u) : 1;
      const H = baseY - topY;
      ctx.save();
      ctx.fillStyle = paint(ctx, t.drip, "colour", cx - rx, cx + rx, topY, baseY);
      ctx.beginPath();
      const drops = 15;
      ctx.moveTo(cx - rx, topY);
      for (let d = 0; d <= drops; d++) {
        const a = Math.PI * (.97 - d / drops * .94);       // left to right across the front
        const x = cx + Math.cos(a) * rx;
        const yEdge = topY + Math.sin(a) * ry;
        const len = (6 + hash(i, d, 3) * (d % 2 ? .55 : .3) * H / s) * s * u;
        const w = rx / drops * .55;
        ctx.lineTo(x - w, yEdge + 4 * s);
        ctx.lineTo(x - w, yEdge + len);
        ctx.arc(x, yEdge + len, w, Math.PI, 0, true);
        ctx.lineTo(x + w, yEdge + 4 * s);
      }
      ctx.lineTo(cx + rx, topY);
      ctx.ellipse(cx, topY, rx, ry, 0, 0, Math.PI, true);
      ctx.closePath();
      ctx.fill();
      ctx.clip(); texture(ctx, t.drip, cx - rx, topY - ry, rx * 2, H + 2 * ry, s, now, 31);
      ctx.restore();
      // a little shine on each drip
      ctx.save(); ctx.globalAlpha = .35 * u; ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.4 * s; ctx.lineCap = "round";
      for (let d = 2; d < 14; d += 3) {
        const a = Math.PI - d / 15 * Math.PI, x = cx + Math.cos(a) * rx - 1.5 * s, yEdge = topY + Math.sin(a) * ry;
        ctx.beginPath(); ctx.moveTo(x, yEdge + 6 * s); ctx.lineTo(x, yEdge + 6 * s + 5 * s * u); ctx.stroke();
      }
      ctx.restore();
    }
    if (t.text) drawText(ctx, t, cx, textY, rx, ry, s, cur, i);
    // The top: frosting, or the sponge itself.
    ctx.save();
    if (t.frosting) {
      ctx.globalAlpha = frostU;
      // the frosted rim hangs a little way down the side, with a wavy edge
      const band = CAP * s;
      ctx.beginPath();
      ctx.moveTo(cx - rx * 1.01, topY);
      const waves = 18;
      for (let wv = 0; wv <= waves; wv++) {
        const a = Math.PI - wv / waves * Math.PI;
        const x = cx + Math.cos(a) * rx * 1.01, yy = topY + Math.sin(a) * ry + band * (.7 + .3 * Math.sin(wv * 2.1 + i));
        ctx.lineTo(x, yy);
      }
      ctx.lineTo(cx + rx * 1.01, topY);
      ctx.ellipse(cx, topY, rx * 1.01, ry, 0, 0, Math.PI, true);
      ctx.closePath();
      ctx.fillStyle = paint(ctx, t.frosting, "colour", cx - rx, cx + rx, topY, topY + band);
      ctx.fill();
      const spread = .35 + .65 * frostU;
      ellipse(ctx, cx, topY, rx * 1.01 * spread, ry * spread);
      const fhex = hexOf(t.frosting, "colour");
      ctx.fillStyle = ["rainbow", "galaxy", "gold"].includes(t.frosting) ? paint(ctx, t.frosting, "colour", cx - rx, cx + rx, topY - ry, topY + ry) : (() => {
        const g = ctx.createRadialGradient(cx - rx * .3, topY - ry * .4, rx * .1, cx, topY, rx * 1.05);
        g.addColorStop(0, shade(fhex, .25)); g.addColorStop(1, shade(fhex, -.06)); return g; })();
      ctx.fill();
      ctx.clip(); texture(ctx, t.frosting, cx - rx, topY - ry, rx * 2, ry * 2, s, now, 3 + i);
    } else {
      ellipse(ctx, cx, topY, rx, ry);
      const top = hexOf(t.layers[n - 1], "flavour");
      ctx.fillStyle = shade(top, .18);
      ctx.fill();
    }
    ctx.restore();
    // Sprinkles on top.
    if (t.sprinkles) drawSprinkles(ctx, t, cx, topY, rx, ry, s, cur, i);
    // Decorations on top, split into the back half and the front half so a
    // tier above can sit between them.
    const inner = above ? tierWidth(i + 1) / tierWidth(i) : 0;
    const items = decorations(ctx, t, cx, topY, rx, ry, s, cur, inner, now);
    const back = items.filter(d => !d.front), front = items.filter(d => d.front);
    back.sort((a, b) => a.y - b.y).forEach(d => d.draw());
    return {top: topY, rx, ry, front};
  }

  function drawSprinkles(ctx, t, cx, topY, rx, ry, s, cur, i) {
    const u = cur && cur.do === "sprinkles" ? cur.u : 1;
    const n = 54;
    ctx.save();
    for (let k = 0; k < n; k++) {
      const a = hash(k, i, 11) * Math.PI * 2, r = Math.sqrt(hash(k, i, 12)) * .9;
      const x = cx + Math.cos(a) * rx * r, y = topY + Math.sin(a) * ry * r;
      const fall = clamp01(u * 1.7 - k / n * .7);
      if (fall <= 0) continue;
      const dy = -(1 - easeOut(fall)) * 90 * s;
      const col = t.sprinkles === "rainbow" ? SPRINKLE_MIX[k % SPRINKLE_MIX.length] : hexOf(t.sprinkles, "colour");
      ctx.save();
      ctx.translate(x, y + dy);
      ctx.rotate(hash(k, i, 13) * Math.PI);
      ctx.fillStyle = col;
      ctx.strokeStyle = "rgba(0,0,0,.12)"; ctx.lineWidth = .6 * s;
      const L = 5.5 * s, W = 1.9 * s;
      ctx.beginPath(); ctx.moveTo(-L / 2, -W / 2); ctx.lineTo(L / 2, -W / 2); ctx.arc(L / 2, 0, W / 2, -Math.PI / 2, Math.PI / 2); ctx.lineTo(-L / 2, W / 2); ctx.arc(-L / 2, 0, W / 2, Math.PI / 2, -Math.PI / 2); ctx.fill(); ctx.stroke();
      ctx.restore();
    }
    ctx.restore();
  }

  // Swirls round the rim, toppings and candles on top, each with a depth.
  function decorations(ctx, t, cx, topY, rx, ry, s, cur, inner, now) {
    const out = [];
    const ns = t.swirls.length;
    const swirlR = (ns > 24 ? 6.5 : ns > 14 ? 8 : 10) * s;
    t.swirls.forEach((c, k) => {
      const a = Math.PI / 2 + k / ns * Math.PI * 2;
      const x = cx + Math.cos(a) * rx * .86, y = topY + Math.sin(a) * ry * .86;
      const last = k === ns - 1 && cur && cur.do === "swirl";
      const sc = last ? Math.max(0, easeBack(cur.u)) : 1;
      out.push({y, front: Math.sin(a) > .05, draw: () => drawSwirl(ctx, x, y, swirlR * sc, c, s)});
    });
    // Candles and toppings share the top: candles in the middle, toppings round them.
    const nc = t.candles.length, nt = t.toppings.length;
    const ring0 = inner ? (inner + 1) / 2 : 0;
    const spots = (count, rMin, rMax, offset) => {
      const pts = [];
      if (count === 1 && !ring0) { pts.push([0, 0]); return pts; }
      if (count <= 9 || ring0) {
        const r = ring0 ? Math.max(ring0, rMin) : (rMin + rMax) / 2;
        for (let k = 0; k < count; k++) {
          const a = Math.PI / 2 + offset + k / count * Math.PI * 2;
          pts.push([Math.cos(a) * r, Math.sin(a) * r]);
        }
        return pts;
      }
      for (let k = 0; k < count; k++) {   // a sunflower spiral packs lots evenly
        const r = rMin + (rMax - rMin) * Math.sqrt((k + .5) / count);
        const a = k * 2.39996 + offset;
        pts.push([Math.cos(a) * r, Math.sin(a) * r]);
      }
      return pts;
    };
    // Lots of candles fill the whole top, and the toppings ring the edge.
    const crowd = nc > 20;
    const candleSpots = spots(nc, 0, crowd ? .66 : nt ? .42 : .66, 0);
    const toppingSpots = crowd ? spots(nt, .82, .82, .3).map(([x, y], k) => {
      const a = Math.PI / 2 + .3 + k / nt * Math.PI * 2;
      return [Math.cos(a) * .82, Math.sin(a) * .82];
    }) : spots(nt, nc ? .5 : 0, nc ? .72 : .66, nc ? .3 : .4);
    const candleH = (nc > 40 ? 20 : nc > 12 ? 26 : 34) * s;
    t.candles.forEach((c, k) => {
      const [px, py] = candleSpots[k];
      const x = cx + px * rx, y = topY + py * ry;
      const last = k === nc - 1 && cur && cur.do === "candle";
      const grow = last ? Math.max(0, easeBack(cur.u)) : 1;
      const lit = !last || cur.u > .55;
      out.push({y, front: py > 0, draw: () => drawCandle(ctx, x, y, candleH * grow, c, s * (nc > 40 ? .8 : 1), lit, now, k, nc > 30)});
    });
    const tSize = (nt > 24 ? 17 : nt > 12 ? 21 : nt > 6 ? 25 : 30) * s;
    t.toppings.forEach((name, k) => {
      const [px, py] = toppingSpots[k];
      const x = cx + px * rx, y = topY + py * ry;
      const last = k === nt - 1 && cur && cur.do === "topping";
      const dy = last ? -(1 - bounce(cur.u)) * 110 * s : 0;
      out.push({y, front: py > 0, draw: () => drawTopping(ctx, x, y + dy, tSize, name, s)});
    });
    return out;
  }

  // A piped rosette seen from a little above: a puffy base, a spiral ridge
  // winding into the middle, and a shine on top.
  function drawSwirl(ctx, x, y, r, colour, s) {
    if (r <= .2) return;
    const hex = hexOf(colour, "colour");
    const special = ["rainbow", "galaxy", "gold"].includes(colour);
    const base = special ? {rainbow: "#ff9ec7", galaxy: "#4b2a8a", gold: "#e3b341"}[colour] : hex;
    const ry = r * .72, lift = r * .42;
    ctx.save();
    ctx.fillStyle = "rgba(60,30,20,.18)";
    ellipse(ctx, x, y + r * .18, r * 1.08, ry * .9); ctx.fill();
    // the side of the rosette, darker
    ctx.fillStyle = shade(base, -.16);
    ctx.beginPath();
    ctx.ellipse(x, y, r, ry, 0, 0, Math.PI);
    ctx.lineTo(x - r, y - lift);
    ctx.ellipse(x, y - lift, r, ry, 0, Math.PI, 0, true);
    ctx.closePath(); ctx.fill();
    // the top
    const g = ctx.createRadialGradient(x - r * .35, y - lift - ry * .4, r * .1, x, y - lift, r * 1.1);
    if (colour === "rainbow") { RAINBOW.forEach((c, i) => g.addColorStop(i / (RAINBOW.length - 1), c)); }
    else { g.addColorStop(0, shade(base, .38)); g.addColorStop(1, shade(base, -.04)); }
    ctx.fillStyle = g;
    ellipse(ctx, x, y - lift, r, ry); ctx.fill();
    // the spiral ridge
    ctx.strokeStyle = shade(base, light(base) > .6 ? -.24 : -.35);
    ctx.lineWidth = Math.max(.8, r * .13); ctx.lineCap = "round";
    ctx.beginPath();
    const turns = 2.2, n = 34;
    for (let k = 0; k <= n; k++) {
      const u = k / n, a = u * turns * Math.PI * 2 + 1, rr = (1 - u) * .82;
      const px = x + Math.cos(a) * r * rr, py = y - lift - u * r * .25 + Math.sin(a) * ry * rr;
      if (k) ctx.lineTo(px, py); else ctx.moveTo(px, py);
    }
    ctx.stroke();
    if (colour === "galaxy" || colour === "gold") {
      ctx.fillStyle = "rgba(255,255,255,.7)";
      ctx.beginPath(); ctx.arc(x + r * .25, y - lift - ry * .3, r * .12, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = "rgba(255,255,255,.55)";
    ctx.beginPath(); ctx.ellipse(x - r * .35, y - lift - ry * .35, r * .22, ry * .14, -.5, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  function drawCandle(ctx, x, y, h, colour, s, lit, now, k, many) {
    if (h <= .5) return;
    const w = 4.6 * s;
    ctx.save();
    const base = colour === "classic" ? "#fff6e8" : hexOf(colour, "colour");
    ctx.fillStyle = colour === "rainbow" || colour === "galaxy" || colour === "gold" ? paint(ctx, colour, "colour", x - w, x + w, y - h, y) : base;
    ctx.fillRect(x - w / 2, y - h, w, h);
    // stripes
    ctx.strokeStyle = colour === "classic" ? "#ff7aa8" : shade(colour === "rainbow" ? "#ff9ec7" : base, light(base) > .5 ? -.25 : .35);
    ctx.lineWidth = 1.4 * s;
    ctx.save(); ctx.beginPath(); ctx.rect(x - w / 2, y - h, w, h); ctx.clip();
    for (let yy = y - h - w; yy < y + w; yy += 5 * s) { ctx.beginPath(); ctx.moveTo(x - w / 2, yy + w); ctx.lineTo(x + w / 2, yy); ctx.stroke(); }
    ctx.restore();
    ctx.strokeStyle = "rgba(0,0,0,.15)"; ctx.lineWidth = .7 * s; ctx.strokeRect(x - w / 2, y - h, w, h);
    // wick and flame
    ctx.strokeStyle = "#3a2a22"; ctx.lineWidth = 1 * s;
    ctx.beginPath(); ctx.moveTo(x, y - h); ctx.lineTo(x, y - h - 3 * s); ctx.stroke();
    if (lit) {
      const f = 1 + .14 * Math.sin(now / 90 + k * 2.3) + .08 * Math.sin(now / 37 + k);
      const fy = y - h - 3 * s;
      const gr = (many ? 7 : 14) * s;
      const glow = ctx.createRadialGradient(x, fy - 4 * s, 0, x, fy - 4 * s, gr);
      glow.addColorStop(0, `rgba(255,210,120,${many ? .3 : .55})`); glow.addColorStop(1, "rgba(255,210,120,0)");
      ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(x, fy - 4 * s, gr, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#ffb42e";
      ctx.beginPath(); ctx.moveTo(x, fy - 11 * s * f); ctx.quadraticCurveTo(x + 4.2 * s, fy - 3 * s, x, fy + 1 * s); ctx.quadraticCurveTo(x - 4.2 * s, fy - 3 * s, x, fy - 11 * s * f); ctx.fill();
      ctx.fillStyle = "#fff4c2";
      ctx.beginPath(); ctx.moveTo(x, fy - 6.5 * s * f); ctx.quadraticCurveTo(x + 2 * s, fy - 2 * s, x, fy); ctx.quadraticCurveTo(x - 2 * s, fy - 2 * s, x, fy - 6.5 * s * f); ctx.fill();
    }
    ctx.restore();
  }

  function drawTopping(ctx, x, y, size, name, s) {
    const icon = (P.toppings && P.toppings[name]) || "🍒";
    ctx.save();
    ctx.fillStyle = "rgba(60,30,20,.18)";
    ellipse(ctx, x, y + size * .08, size * .38, size * .13); ctx.fill();
    ctx.font = `${size}px "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
    ctx.fillStyle = "#000";   // emoji take the fill's transparency, so keep it solid
    ctx.fillText(icon, x, y + size * .12);
    ctx.restore();
  }

  // Writing piped onto the front of the cake, following its curve.
  function drawText(ctx, t, cx, cy, rx, ry, s, cur, i) {
    let text = t.text;
    if (cur && cur.do === "write") text = text.slice(0, Math.ceil(text.length * cur.u));
    if (!text) return;
    const words = t.text.split(" ");
    // One line if it fits, otherwise two.
    let lines = [t.text];
    const maxSize = Math.min(22 * s, (LH * Math.max(1, t.layers.length) * s) * .55);
    ctx.save();
    const font = size => `800 ${size}px ui-rounded, "Nunito", "Varela Round", "Arial Rounded MT Bold", "Trebuchet MS", system-ui, sans-serif`;
    let size = maxSize;
    ctx.font = font(size);
    const room = rx * 1.75;
    if (ctx.measureText(t.text).width > room && words.length > 1 && t.layers.length > 1) {
      let best = 1;
      for (let k = 1; k < words.length; k++) {
        const a = words.slice(0, k).join(" "), b = words.slice(k).join(" ");
        if (Math.max(a.length, b.length) < Math.max(words.slice(0, best).join(" ").length, words.slice(best).join(" ").length)) best = k;
      }
      lines = [words.slice(0, best).join(" "), words.slice(best).join(" ")];
    }
    const widest = Math.max(...lines.map(l => ctx.measureText(l).width));
    if (widest > room) size *= room / widest;
    size = Math.max(size, 7 * s);
    ctx.font = font(size);
    // Which colour reads well on this layer?
    const mid = hexOf(t.layers[Math.floor(t.layers.length / 2)] || "vanilla", "flavour");
    const dark = light(mid) < .55;
    const fill = dark ? "#fff7fb" : "#6b2f45";
    const edge = dark ? "#d4588a" : "#ffffff";
    let shown = text.length;
    const lineH = size * 1.05;
    const y0 = cy - (lines.length - 1) * lineH / 2;
    lines.forEach((line, li) => {
      const visible = line.slice(0, Math.max(0, shown));
      shown -= line.length + 1;
      const total = ctx.measureText(line).width;
      let pos = -total / 2;
      for (const ch of visible) {
        const w = ctx.measureText(ch).width;
        const phi = (pos + w / 2) / rx;
        const x = cx + Math.sin(phi) * rx;
        const y = y0 + li * lineH + Math.cos(phi) * ry * .9 - ry * .9;
        ctx.save();
        ctx.translate(x, y);
        ctx.scale(Math.max(.2, Math.cos(phi)), 1);
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.lineJoin = "round";
        ctx.strokeStyle = edge; ctx.lineWidth = Math.max(2, size * .22);
        ctx.strokeText(ch, 0, 0);
        ctx.fillStyle = fill;
        ctx.fillText(ch, 0, 0);
        ctx.restore();
        pos += w;
      }
    });
    ctx.restore();
  }

  // ---- everything ----------------------------------------------------------------------------
  // opts: {tiers, fit, stand, anim: {do, tier, u}, now}
  function draw(ctx, w, h, opts) {
    const tiers = opts.tiers || [newTier()];
    const L = layout(w, h, opts.fit || tiers, opts.stand || "plate");
    const now = opts.now || 0;
    let y = drawStand(ctx, L, opts.stand || "plate");
    let pendingFront = [];
    tiers.forEach((t, i) => {
      const above = i < tiers.length - 1 && tiers[i + 1].layers.length > 0;
      const r = drawTier(ctx, t, i, L, y, opts.anim, now, i === tiers.length - 1, above);
      pendingFront.sort((a, b) => a.y - b.y).forEach(d => d.draw());
      pendingFront = r.front;
      y = r.top;
    });
    pendingFront.sort((a, b) => a.y - b.y).forEach(d => d.draw());
    return L;
  }

  // Where the top of the cake is, for effects like sparkles and flames.
  function topOf(w, h, opts) {
    const tiers = opts.tiers || [newTier()];
    const L = layout(w, h, opts.fit || tiers, opts.stand || "plate");
    let y = L.base - (STAND_H[opts.stand || "plate"] || 10) * L.s;
    tiers.forEach(t => { if (t.layers.length) y -= tierHeight(t) * L.s; });
    return {x: L.cx, y, s: L.s};
  }

  // A quick still picture of a finished cake (shop window cards).
  function still(canvas, tiers, stand) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = canvas.clientWidth || canvas.width, h = canvas.clientHeight || canvas.height;
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    draw(ctx, w, h, {tiers, stand, now: 1000});
  }

  window.CakeArt = {setPalette, newTier, apply, replay, draw, topOf, still, hexOf};
})();
