// The Rover Farm's yard, drawn from above. Shared by the farm page
// (planet_farm.js) and the class screen (planet_show.html), which plays farm
// days when nothing else is on. Needs planet_render.js first. With mine=true
// it reads the page's rover, floaters, bubble, night, falls and FALL_MS;
// it always reads CALM, pops, wiggles and coinText.
"use strict";

const EMOJI = '"Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", system-ui, sans-serif';
function fit(cv) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2), w = cv.clientWidth, h = cv.clientHeight;
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}
// The yard is the field with two squares of grass all round it, so it zooms
// out by itself as the field grows.
function layoutOf(cv, view) {
  const W = cv.clientWidth, H = cv.clientHeight, cols = view.w + 4, rows = view.h + 4;
  const cell = Math.min(W / cols, H / rows, 112);
  return {W, H, cols, rows, cell, ox: (W - cols * cell) / 2, oy: (H - rows * cell) / 2};
}
const sx = (L, x) => L.ox + (x + 1.5) * L.cell;   // the middle of field square x (1 is the first)
const sy = (L, y) => L.oy + (y + 1.5) * L.cell;
// Where the yard's things stand: grass squares in a fixed scatter, clear of
// the field and of where the next field will reach.
function decorSpots(view) {
  const tiles = [];
  for (let j = 0; j < view.h + 4; j++) for (let i = 0; i < view.w + 4; i++) {
    if (i >= 2 && i <= view.w + 2 && j >= 2 && j <= view.h + 2) continue;
    tiles.push([i, j, hash(i, j, 77)]);
  }
  return tiles.sort((a, b) => a[2] - b[2]);
}
function emoji(ctx, text, x, y, size) {
  ctx.font = `${Math.max(8, size)}px ${EMOJI}`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillStyle = "#fff";
  ctx.fillText(text, x, y + size * .04);
}
function drawYard(cv, view, now, mine) {
  const ctx = fit(cv), L = layoutOf(cv, view), c = L.cell, t = CALM ? 0 : now;
  // Grass, with tufts and a few tiny flowers that stay put.
  ctx.fillStyle = "#24493f"; ctx.fillRect(0, 0, L.W, L.H);
  const i0 = Math.floor(-L.ox / c), j0 = Math.floor(-L.oy / c);
  for (let j = j0; j * c + L.oy < L.H; j++) for (let i = i0; i * c + L.ox < L.W; i++) {
    const x = L.ox + i * c, y = L.oy + j * c;
    for (let k = 0; k < 3; k++) {
      const tx = x + hash(i, j, k) * c, ty = y + hash(j, i, k + 9) * c;
      ctx.strokeStyle = k ? "#2f6152" : "#3a7563"; ctx.lineWidth = Math.max(1.5, c * .03); ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(tx + c * .04, ty - c * .09); ctx.moveTo(tx + c * .07, ty); ctx.lineTo(tx + c * .09, ty - c * .07); ctx.stroke();
    }
    if (hash(i, j, 31) < .16) {
      ctx.fillStyle = hash(i, j, 32) < .5 ? "#b9a3ff" : "#ffd36b";
      ctx.beginPath(); ctx.arc(x + hash(i, j, 33) * c, y + hash(i, j, 34) * c, Math.max(1.5, c * .035), 0, 7); ctx.fill();
    }
  }
  const fx = L.ox + 2 * c, fy = L.oy + 2 * c;
  // Where the next field will reach, for the farm's owner.
  if (mine && view.next_field) {
    const nf = view.next_field;
    ctx.save();
    ctx.setLineDash([c * .16, c * .12]); ctx.strokeStyle = "rgba(242,234,219,.4)"; ctx.lineWidth = Math.max(2, c * .035);
    roundRect(ctx, fx - c * .06, fy - c * .06, nf.w * c + c * .12, nf.h * c + c * .12, c * .14); ctx.stroke();
    ctx.restore();
    const label = `🔒 🌾 ${coinText(nf.cost)}`;
    ctx.font = `700 ${Math.max(11, c * .2)}px system-ui, ${EMOJI}`;
    const lw = ctx.measureText(label).width + c * .24, lx = fx + nf.w * c - lw - c * .08, ly = fy + nf.h * c - c * .36;
    ctx.fillStyle = "rgba(27,23,51,.78)"; roundRect(ctx, lx, ly, lw, c * .3, c * .15); ctx.fill();
    ctx.fillStyle = view.coins >= nf.cost ? "#ffd36b" : "#cfc6ea"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(label, lx + lw / 2, ly + c * .16);
  }
  // The field: soil with furrows, and a fence round it.
  ctx.fillStyle = "rgba(10,20,16,.35)"; roundRect(ctx, fx - c * .1, fy - c * .04, view.w * c + c * .2, view.h * c + c * .2, c * .16); ctx.fill();
  for (let y = 1; y <= view.h; y++) for (let x = 1; x <= view.w; x++) {
    const px = fx + (x - 1) * c, py = fy + (y - 1) * c;
    ctx.fillStyle = (x + y) % 2 ? "#6c4b36" : "#644531"; ctx.fillRect(px, py, c + .5, c + .5);
    ctx.strokeStyle = "rgba(40,24,14,.38)"; ctx.lineWidth = Math.max(1, c * .03);
    ctx.beginPath();
    for (let k = 1; k <= 3; k++) { ctx.moveTo(px + c * .1, py + c * k / 4); ctx.lineTo(px + c * .9, py + c * k / 4); }
    ctx.stroke();
  }
  ctx.strokeStyle = "#e3d3b0"; ctx.lineWidth = Math.max(2, c * .055); ctx.lineJoin = "round";
  roundRect(ctx, fx - c * .08, fy - c * .08, view.w * c + c * .16, view.h * c + c * .16, c * .12); ctx.stroke();
  ctx.fillStyle = "#f4e8cb";
  for (let x = 0; x <= view.w; x++) for (const y of [0, view.h]) { ctx.beginPath(); ctx.arc(fx + x * c, fy + y * c + (y ? c * .08 : -c * .08), c * .055, 0, 7); ctx.fill(); }
  for (let y = 1; y < view.h; y++) for (const x of [0, view.w]) { ctx.beginPath(); ctx.arc(fx + x * c + (x ? c * .08 : -c * .08), fy + y * c, c * .055, 0, 7); ctx.fill(); }
  // What's growing.
  for (let y = 1; y <= view.h; y++) for (let x = 1; x <= view.w; x++) {
    const cell = view.field[y - 1] && view.field[y - 1][x - 1];
    if (!cell) continue;
    if (cell[0] === "rock") {
      // A meteor still falling hasn't made its rock yet.
      if (mine && falls.some(f => f.x === x && f.y === y && now < f.t0 + FALL_MS)) continue;
      const cx = sx(L, x), cy = sy(L, y);
      ctx.fillStyle = "rgba(20,10,6,.45)"; ctx.beginPath(); ctx.ellipse(cx, cy + c * .14, c * .4, c * .22, 0, 0, 7); ctx.fill();
      emoji(ctx, "🪨", cx, cy, c * .66);
      continue;
    }
    const [crop, age, gold] = cell, days = view.days[crop] || 1, ripe = age >= days;
    const cx = sx(L, x), cy = sy(L, y), born = pops[`${x},${y}`];
    const grow = born && !CALM ? Math.min(1, (now - born) / 260) : 1;
    if (gold) {
      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, c * .5);
      glow.addColorStop(0, `rgba(255,211,107,${ripe ? .6 : .32})`); glow.addColorStop(1, "rgba(255,211,107,0)");
      ctx.fillStyle = glow; ctx.fillRect(cx - c * .5, cy - c * .5, c, c);
    }
    if (ripe) {
      const bob = Math.sin(t / 420 + x * 1.7 + y) * c * .025;
      ctx.fillStyle = "rgba(10,4,16,.28)"; ctx.beginPath(); ctx.ellipse(cx, cy + c * .3, c * .22, c * .07, 0, 0, 7); ctx.fill();
      emoji(ctx, view.icons[crop] || "🌱", cx, cy + bob, c * .58 * grow);
    } else {
      emoji(ctx, "🌱", cx, cy + c * .06, c * (.26 + .26 * age / days) * grow);
      // How many nights until it's ripe.
      const left = days - age;
      ctx.fillStyle = "rgba(27,23,51,.72)"; ctx.beginPath(); ctx.arc(cx + c * .3, cy - c * .3, c * .13, 0, 7); ctx.fill();
      ctx.fillStyle = "#f2eadb"; ctx.font = `700 ${Math.max(9, c * .17)}px system-ui`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(String(left), cx + c * .3, cy - c * .29);
    }
    if (gold) emoji(ctx, "✨", cx + c * .26, cy - (ripe ? c * .26 : -c * .22) + Math.sin(t / 300 + x) * c * .03, c * .26);
  }
  // The yard's things, back to front.
  const spots = decorSpots(view), things = [];
  view.decor.forEach((d, i) => { if (spots[i]) things.push({d, i: spots[i][0], j: spots[i][1]}); });
  things.sort((a, b) => a.j - b.j);
  const hits = [];
  for (const {d, i, j} of things) {
    const size = c * (d.big ? 1.15 : .74), cx = Math.max(size * .55, Math.min(L.W - size * .55, L.ox + (i + .5) * c));
    const cy = Math.max(size * .6, Math.min(L.H - size * .6, L.oy + (j + .5) * c));
    const w = wiggles[d.key], u = w && !CALM ? (now - w) / 600 : 1;
    const hop = u < 1 ? -Math.abs(Math.sin(u * Math.PI * 2)) * c * .16 * (1 - u) : 0;
    ctx.fillStyle = "rgba(10,4,16,.26)"; ctx.beginPath(); ctx.ellipse(cx, cy + size * .42, size * .36, size * .1, 0, 0, 7); ctx.fill();
    emoji(ctx, d.icon, cx, cy + hop, size);
    hits.push({d, cx, cy, r: size * .55});
    if (w && now - w < 1800) speech(ctx, d.say, cx, cy - size * .62, c, L.W);
  }
  // The rover.
  const r = mine ? rover : {px: 1, py: 1, angle: 0};
  const rx = sx(L, r.px), ry = sy(L, r.py), gear = view.look || {};
  drawRover(ctx, rx, ry, c * 1.02, r.angle, 1, gear, now);
  if (gear.pet && PETS[gear.pet]) drawPet(ctx, rx + c * .46, ry - c * .5, c * 1.15, gear.pet, now);
  // What's under the rover would be hidden by it, so it shows in the corner.
  const ux = Math.round(r.px), uy = Math.round(r.py), under = view.field[uy - 1] && view.field[uy - 1][ux - 1];
  if (under && Math.abs(r.px - ux) + Math.abs(r.py - uy) < .05) {
    const ripe = under[1] >= (view.days[under[0]] || 1), bx = sx(L, ux) + c * .3, by = sy(L, uy) + c * .3;
    ctx.fillStyle = "rgba(27,23,51,.82)"; ctx.beginPath(); ctx.arc(bx, by, c * .19, 0, 7); ctx.fill();
    if (under[2]) { ctx.strokeStyle = "#ffd36b"; ctx.lineWidth = Math.max(1.5, c * .03); ctx.stroke(); }
    emoji(ctx, ripe ? view.icons[under[0]] || "🌱" : "🌱", bx, by, c * (ripe ? .26 : .2));
  }
  if (mine) {
    for (const f of floaters) {
      const u = Math.min(1, (now - f.t0) / f.life), rise = CALM ? .5 : .5 + u * .45;
      ctx.globalAlpha = u < .7 ? 1 : 1 - (u - .7) / .3;
      ctx.font = `800 ${Math.max(12, c * (f.big ? .34 : .22))}px system-ui, ${EMOJI}`;
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.lineWidth = Math.max(3, c * .05); ctx.strokeStyle = "rgba(20,12,36,.85)"; ctx.lineJoin = "round";
      ctx.strokeText(f.text, sx(L, f.x), sy(L, f.y) - c * rise);
      ctx.fillStyle = f.color; ctx.fillText(f.text, sx(L, f.x), sy(L, f.y) - c * rise);
      ctx.globalAlpha = 1;
    }
    if (bubble && now < bubble.until) speech(ctx, bubble.text, rx, ry - c * .62, c, L.W);
    if (night) {
      const u = Math.min(1, (now - night.t0) / night.dur), a = Math.sin(u * Math.PI);
      ctx.fillStyle = `rgba(12,9,38,${a * .62})`; ctx.fillRect(0, 0, L.W, L.H);
      ctx.globalAlpha = a; emoji(ctx, u < .5 ? "🌙" : "☀️", L.W / 2, L.H * .14, Math.min(L.W, L.H) * .12); ctx.globalAlpha = 1;
    }
    for (const f of falls) {
      const u = (now - f.t0) / FALL_MS, tx = sx(L, f.x), ty = sy(L, f.y);
      if (u < 0) continue;
      if (u < 1) {   // from high up and to the east, down onto its square
        const e = u * u;
        emoji(ctx, "☄️", tx + (1 - e) * c * 3, ty - (1 - e) * c * 4, c * .9);
      } else if (u < 1.5) {
        ctx.globalAlpha = 1 - (u - 1) * 2; emoji(ctx, "💥", tx, ty, c * (.8 + (u - 1) * .8)); ctx.globalAlpha = 1;
      }
    }
  }
  return {L, hits};
}
function speech(ctx, text, x, y, c, W) {
  text = String(text); if (text.length > 30) text = text.slice(0, 29) + "…";
  ctx.font = `700 ${Math.max(12, c * .2)}px system-ui, ${EMOJI}`;
  const w = ctx.measureText(text).width + 18, h = Math.max(22, c * .34);
  const left = Math.max(4, Math.min(W - w - 4, x - w / 2));
  ctx.fillStyle = "#f2eadb"; roundRect(ctx, left, y - h, w, h, h / 2.4); ctx.fill();
  ctx.beginPath(); ctx.moveTo(x - 6, y - 1); ctx.lineTo(x + 6, y - 1); ctx.lineTo(x, y + 7); ctx.fill();
  ctx.fillStyle = "#231d3f"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(text, left + w / 2, y - h / 2 + 1);
}

