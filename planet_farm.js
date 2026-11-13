// The Rover Farm page: a student's own field, farmed by their code. The rules
// are the server's (planet_farm.py). This page shows the farm, sends the code,
// and plays back the day it gets in reply. The rover is drawn by
// planet_render.js, so it wears what the student picked in the garage.
"use strict";

const $ = id => document.getElementById(id);
function store(key, value) { try { localStorage.setItem(key, value); } catch (_) {} }
function recall(key) { try { return localStorage.getItem(key); } catch (_) { return null; } }
let CALM = matchMedia("(prefers-reduced-motion: reduce)").matches || recall("planetCalm") === "1";
document.body.classList.toggle("calm", CALM);
document.body.classList.toggle("big", recall("planetBig") === "1");
const me = recall("mazeId");
const sleep = ms => new Promise(done => setTimeout(done, ms));
const clone = value => JSON.parse(JSON.stringify(value));
const coinText = n => Math.round(n).toLocaleString("en-US");

function esc(value) {
  return String(value).replace(/[&<>"]/g, ch => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[ch]));
}
// Messages mark code with two spaces each side, like  east(3) . Those bits get
// the code look, as on the planet (the same rules as planet.html's codeSpans).
const PY_WORD = /^(?:for|in|if|not|and|or|while|def|is|else|elif|return|global|print|range)$/;
function depth(s) { let d = 0; for (const ch of s) d += ch === "(" ? 1 : ch === ")" ? -1 : 0; return d; }
function looksLikeCode(s) {
  if (!s || s.length > 48) return false;
  if (s.length > 1 && s.startsWith("(") && depth(s) > 0) return false;
  const words = s.split(" ");
  if (words.length === 1)
    return /^[a-z]+$/i.test(s) ? PY_WORD.test(s) || s.length <= 2 : /[\w()\[\]:="'<>!+\-*\/%&|]/.test(s) && !/^[?—–]+$/.test(s);
  const [a, b] = words;
  if (!(PY_WORD.test(a) || /[(\["'<>=!]/.test(a) || /^[<>=!+\-*/%]+=?$/.test(b))) return false;
  let run = 0, all = 0;
  for (const w of words) {
    if (/^\(?[a-z']+[,:.)]*$/i.test(w) && !PY_WORD.test(w)) { if (++run >= 2 || ++all >= 3) return false; } else run = 0;
  }
  return true;
}
function codeSpans(text) {
  const parts = String(text).split(/ {2,}/).map(part => {
    let core = part, after = "", d = 0, q = "";
    for (let i = 0; i < core.length; i++) {
      const ch = core[i];
      if (q) { if (ch === q) q = ""; } else if (ch === '"' || ch === "'") q = ch;
      else if (ch === "(") d++; else if (ch === ")") d--;
      else if (ch === "," && core[i + 1] === " " && d === 0) { after = core.slice(i); core = core.slice(0, i); break; }
    }
    while (core.length > 1 && (/[.,?]$/.test(core) || core.endsWith(" ") || core.endsWith(")") && depth(core) < 0)) {
      after = core.slice(-1) + after; core = core.slice(0, -1);
    }
    return {part, core, after, code: looksLikeCode(core)};
  });
  parts.forEach((p, i) => {
    if (p.code && /^(?:or|and|not)$/.test(p.core) && parts[i - 1]?.code) {
      p.code = false;
      const n = parts[i + 1];
      if (n && /^[a-z_]\w*$/i.test(n.core)) n.code = true;
    }
  });
  return parts.map(p => p.code ? `<code>${esc(p.core)}</code>${esc(p.after)}` : esc(p.part)).join(" ");
}
async function post(url, data) {
  const response = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
  return response.json();
}
async function get(url) { return (await fetch(url)).json(); }

// ---- Sound: synthesized, and off until the student (or the class setting) turns it on ----
const SFX = (() => {
  let ac = null, master = null, muted = recall("planetMuted") !== "0";
  function context() {
    if (!ac) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ac = new AC(); master = ac.createGain(); master.gain.value = .2; master.connect(ac.destination);
    }
    if (ac.state === "suspended") ac.resume();
    return ac;
  }
  function tone(freq, dur, {type = "sine", vol = .5, at = 0, slide = 0} = {}) {
    const t = ac.currentTime + at, o = ac.createOscillator(), g = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(master); o.start(t); o.stop(t + dur + .05);
  }
  const chord = (notes, gap, opts) => notes.forEach((f, i) => tone(f, .2, {...opts, at: i * gap}));
  const sounds = {
    // Each pick in a day sounds a step higher than the last.
    pick: n => tone(520 * Math.pow(1.06, Math.min(n, 16)), .12, {type: "triangle", vol: .5}),
    gold: () => chord([880, 1175, 1568], .07, {type: "triangle", vol: .5}),
    plant: () => tone(300, .08, {vol: .35, slide: 140}),
    nope: () => tone(170, .09, {type: "square", vol: .16}),
    bump: () => tone(110, .1, {type: "square", vol: .2}),
    coins: () => chord([988, 1319], .08, {type: "square", vol: .22}),
    job: () => chord([523, 659, 784, 1047], .09, {type: "triangle", vol: .5}),
    buy: () => chord([392, 523, 659], .06, {type: "triangle", vol: .45}),
    error: () => tone(160, .25, {type: "sawtooth", vol: .18, slide: -60}),
    night: () => tone(240, .5, {vol: .16, slide: -90}),
    crate: () => chord([523, 659, 784, 1047, 1319], .08, {type: "triangle", vol: .5}),
  };
  return {
    play(name, arg) { if (!muted && context() && sounds[name]) sounds[name](arg); },
    classDefault(on) { if (recall("planetMuted") == null) muted = !on; },
    toggle() { muted = !muted; store("planetMuted", muted ? "1" : "0"); if (!muted) context(); return muted; },
    get muted() { return muted; },
  };
})();

function toast(icon, title, text) {
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<span class="ico">${icon}</span><div><b>${esc(title)}</b><small>${esc(text || "")}</small></div>`;
  const shown = [...$("toasts").children].filter(t => !t.classList.contains("out"));
  if (shown.length >= 3) { shown[0].classList.add("out"); setTimeout(() => shown[0].remove(), 350); }
  $("toasts").appendChild(el);
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 350); }, 5200);
}

// ---- What the page knows ------------------------------------------------------------
let farm = null;          // the farm as the server last gave it
let scene = null;         // what the yard shows: the farm, changed square by square as a day plays
let visiting = null;      // a classmate's farm, while the Visit window shows one
const rover = {x: 1, y: 1, px: 1, py: 1, angle: 0};   // on the field, in squares
let play = null;          // the day being played back
let night = null;         // the night passing after it
let busy = false, idleDays = 0, lastInput = performance.now();
let floaters = [], bubble = null, pops = {}, wiggles = {};
let coinsShown = 0, coinsGoal = 0;
let errorLine = null, activeLine = null, sampleHidden = null;
const SPEEDS = [1, 2, 4];
let speed = SPEEDS.includes(Number(recall("farmSpeed"))) ? Number(recall("farmSpeed")) : 1;
const editor = $("code");

function leave() { location.href = "/planet"; }
function showClosed() {
  $("app").hidden = true; $("closed").hidden = false; $("auto").checked = false;
}

// ---- The yard, drawn from above -------------------------------------------------------
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

// ---- Playing a day back -----------------------------------------------------------------
const WAYS = {east: 0, south: Math.PI / 2, west: Math.PI, north: -Math.PI / 2};
const VEC = {east: [1, 0], south: [0, 1], west: [-1, 0], north: [0, -1]};
function stepMs(n) { return Math.max(34, Math.min(250, 2800 / Math.max(n, 1))) / speed; }
function float(text, color, big) {
  if (play && play.skip) return;
  floaters.push({x: rover.x, y: rover.y, text, color, big, t0: performance.now(), life: big ? 1100 : 800});
}
function playDay(out) {
  return new Promise(done => {
    scene.field = clone(out.start);
    Object.assign(rover, {x: 1, y: 1, px: 1, py: 1, angle: 0});
    play = {out, i: 0, t0: performance.now(), step: stepMs(out.frames.length), from: {x: 1, y: 1},
            begun: false, picks: 0, skip: false, done};
    $("runButton").textContent = "⏩ Skip to the end";
  });
}
function stepPlay(now) {
  const frames = play.out.frames;
  while (play.i < frames.length) {
    const f = frames[play.i];
    if (!play.begun) {
      play.begun = true; play.from = {x: rover.x, y: rover.y};
      showLine(f.line);
      if (f.do === "move") rover.angle = f.x > rover.x ? 0 : f.x < rover.x ? Math.PI : f.y > rover.y ? Math.PI / 2 : -Math.PI / 2;
      if (f.do === "bump") rover.angle = WAYS[f.way];
    }
    const u = play.skip ? 1 : (now - play.t0) / play.step;
    if (u < 1) {
      if (f.do === "move") { const e = ease(u); rover.px = play.from.x + (f.x - play.from.x) * e; rover.py = play.from.y + (f.y - play.from.y) * e; }
      if (f.do === "bump" && !CALM) { const k = Math.sin(u * Math.PI) * .2; rover.px = f.x + VEC[f.way][0] * k; rover.py = f.y + VEC[f.way][1] * k; }
      return;
    }
    applyFrame(f);
    play.i++; play.begun = false;
    play.t0 = play.skip || now - play.t0 > play.step * 3 ? now : play.t0 + play.step;
    const said = play.out.prints.filter(p => p.t === play.i).pop();
    if (said && !play.skip) bubble = {text: said.text, until: now + 1400};
  }
  const done = play.done;
  play = null;
  done();
}
function applyFrame(f) {
  Object.assign(rover, {x: f.x, y: f.y, px: f.x, py: f.y});
  const row = scene.field[f.y - 1], quiet = play.skip;
  if (f.do === "pick") {
    row[f.x - 1] = null; play.picks++;
    coinsGoal += f.pay;
    float(`+${f.pay}`, "#ffd36b", f.gold);
    if (!quiet) SFX.play(f.gold ? "gold" : "pick", play.picks);
  } else if (f.do === "plant") {
    row[f.x - 1] = [f.crop, 0, f.gold ? 1 : 0]; pops[`${f.x},${f.y}`] = performance.now();
    if (!quiet) SFX.play("plant");
  } else if (f.do === "dig") {
    row[f.x - 1] = null; float("dug up", "#cfc6ea");
  } else if (f.do === "early") { float("not ripe yet", "#ffb547"); if (!quiet) SFX.play("nope"); }
  else if (f.do === "nothing") { float("nothing here", "#cfc6ea"); if (!quiet) SFX.play("nope"); }
  else if (f.do === "full") { float("already planted", "#ffb547"); if (!quiet) SFX.play("nope"); }
  else if (f.do === "bump") { float("fence!", "#ff9d8f"); if (!quiet) SFX.play("bump"); }
  else if (f.do === "wait") float("💤", "#cfc6ea");
  showBattery(play.out.battery - play.i - 1, play.out.battery);
}
// The night after a day: the yard goes dark, and the morning shows what grew.
function nightfall(swap, quick) {
  return new Promise(done => {
    if (CALM || quick) { swap(); done(); return; }
    SFX.play("night");
    night = {t0: performance.now(), dur: 950 / Math.sqrt(speed), swapped: false, swap, done};
  });
}
function stepNight(now) {
  const u = (now - night.t0) / night.dur;
  if (u >= .5 && !night.swapped) { night.swapped = true; night.swap(); }
  if (u >= 1) { const done = night.done; night = null; done(); }
}

let lazy = 0;
function loop(now) {
  requestAnimationFrame(loop);
  if (document.hidden || !scene) return;
  if (play) stepPlay(now);
  if (night) stepNight(now);
  floaters = floaters.filter(f => now - f.t0 < f.life);
  if (bubble && now > bubble.until) bubble = null;
  if (coinsShown !== coinsGoal) {
    const gap = coinsGoal - coinsShown;
    coinsShown += Math.abs(gap) < 1 || CALM ? gap : gap * .22;
    if (Math.abs(coinsGoal - coinsShown) < 1) coinsShown = coinsGoal;
    $("coins").textContent = $("shopCoins").textContent = coinText(coinsShown);
  }
  // Nothing moving: twenty pictures a second is plenty for a class laptop.
  const moving = play || night || floaters.length || bubble;
  if (!moving && ++lazy % 3) return;
  if (!$("visit").hidden) { if (visiting) drawYard($("visitYard"), visiting, now, false); return; }
  yardView = drawYard($("yard"), scene, now, true);
}
let yardView = null;

// ---- The code box -------------------------------------------------------------------------
function codeLines(code) {
  return code.split("\n").filter(line => line.trim() && !line.trim().startsWith("#")).length;
}
function lineHeight() { return parseFloat(getComputedStyle(editor).lineHeight) || 24; }
function updateEditor() {
  const lines = editor.value.split("\n");
  $("gutter").innerHTML = lines.map((_, i) =>
    `<span class="${i + 1 === errorLine ? "bad" : i + 1 === activeLine ? "on" : ""}">${i + 1}</span>`).join("");
  $("gutter").scrollTop = editor.scrollTop;
  const bar = $("lineBar"), n = errorLine || activeLine;
  bar.hidden = !n;
  if (n) { bar.style.top = `${8 + (n - 1) * lineHeight() - editor.scrollTop}px`; bar.classList.toggle("bad", !!errorLine); }
  if (farm) {
    const used = codeLines(editor.value);
    $("lines").textContent = `🧠 ${used} of ${farm.memory} lines`;
    $("lines").classList.toggle("over", used > farm.memory);
  }
  renderSample();
}
function showLine(n) {
  activeLine = n || null;
  if (n) {
    const h = lineHeight(), top = (n - 1) * h;
    if (top < editor.scrollTop || top + h > editor.scrollTop + editor.clientHeight - 16)
      editor.scrollTop = Math.max(0, top - editor.clientHeight / 2);
  }
  updateEditor();
}
function replaceAll(text) {
  editor.focus(); editor.setSelectionRange(0, editor.value.length);
  if (!document.execCommand("insertText", false, text)) editor.value = text;
  typed();
}
function typed() {
  if (errorLine) errorLine = null;
  store(`farmCode:${me}`, editor.value);
  updateEditor();
}
// Typing: Tab pushes a line in, Enter keeps the push (and adds one after a
// colon), brackets and quotes close themselves, and Ctrl+Enter runs the day.
function codeKey(e) {
  const t = editor, at = t.selectionStart, flat = at === t.selectionEnd;
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); pressRun(); return; }
  if (e.key === "Tab") {
    e.preventDefault();
    if (!e.shiftKey) { document.execCommand("insertText", false, "    "); return; }
    const start = t.value.lastIndexOf("\n", at - 1) + 1, pad = t.value.slice(start).match(/^ {1,4}/);
    if (pad) { t.setSelectionRange(start, start + pad[0].length); document.execCommand("delete"); }
    return;
  }
  if (e.key === "Enter") {
    const before = t.value.slice(0, at), line = before.slice(before.lastIndexOf("\n") + 1);
    const indent = line.match(/^ */)[0] + (/:\s*$/.test(line) ? "    " : "");
    e.preventDefault(); document.execCommand("insertText", false, "\n" + indent); return;
  }
  if (e.key === "Backspace" && flat) {
    const start = t.value.lastIndexOf("\n", at - 1) + 1, before = t.value.slice(start, at);
    if (before && !before.trim() && before.length % 4 === 0) {
      e.preventDefault(); t.setSelectionRange(at - 4, at); document.execCommand("delete"); return;
    }
    if (/\(\)|""/.test(t.value.slice(at - 1, at + 1))) {
      e.preventDefault(); t.setSelectionRange(at - 1, at + 1); document.execCommand("delete"); return;
    }
  }
  const next = t.value[at] || "";
  if (flat && (e.key === ")" || e.key === '"') && next === e.key) { e.preventDefault(); t.setSelectionRange(at + 1, at + 1); return; }
  if (flat && (e.key === "(" || e.key === '"') && !/\w/.test(next)) {
    e.preventDefault(); document.execCommand("insertText", false, e.key === "(" ? "()" : '""');
    t.setSelectionRange(at + 1, at + 1);
  }
}

// ---- The words under the code box -------------------------------------------------------------
// [what to type, what it does, the first job (counting from 0) it shows on]
const WORDS = [
  ["harvest()", "Picks the plant under the rover, if it's ripe, and sells it for coins.", 0, "do"],
  ['plant("berry")', "Plants a crop on the square under the rover, if it's empty.", 2, "do"],
  ["east()", "Drives one square east.  east(3)  drives three.", 0, "do"],
  ["west()", "Drives one square west.", 0, "do"],
  ["south()", "Drives one square south, to the next row down.", 0, "do"],
  ["north()", "Drives one square north, to the row above.", 0, "do"],
  ["for", "for i in range(3):  repeats the lines under it 3 times. Push those lines in with Tab.", 5, "shape"],
  ["ripe()", "True when the plant under the rover is ready to pick. Use it like  if ripe():", 9, "ask"],
  ["empty()", "True when nothing is planted under the rover. Use it like  if empty():", 9, "ask"],
  ["if", "if ripe():  does the lines under it only when that's true.", 9, "shape"],
  ["def", "def care():  names the lines under it. After that,  care()  runs them.", 11, "shape"],
  ['look("east")', 'Says what\'s on the next square: "ripe", "growing", "empty" or "fence".', 12, "ask"],
  ["while", 'while look("east") != "fence":  repeats the lines under it while that\'s true.', 12, "shape"],
  ["dig()", "Clears the square under the rover, so you can plant something else.", 13, "do"],
  ["wait()", "Stays still for one tick.", 13, "do"],
  ["crop()", 'The name of the plant under the rover, like "berry". An empty square is "none".', 13, "ask"],
  ["x()", "How far east the rover is. The first square is 1.", 13, "ask"],
  ["y()", "How far south the rover is. The top row is 1.", 13, "ask"],
  ["width()", "How many squares wide your field is. Try  for i in range(width()):", 13, "ask"],
  ["height()", "How many rows your field has.", 13, "ask"],
  ["battery()", "Ticks of battery left today.", 13, "ask"],
  ["coins()", "How many coins you have.", 13, "ask"],
  ["day()", "Which day it is on your farm.", 13, "ask"],
];
// The words that come after the last job fold away, so the code box keeps its room.
const EXTRA_FROM = 13;
let moreWords = false;
function renderChips() {
  const at = farm.job ? farm.job.n - 1 : 99;
  const seeds = farm.crops.map(c => `"${c}"`).join(", ");
  const extra = WORDS.some(w => w[2] >= EXTRA_FROM && w[2] <= at);
  $("chips").innerHTML = WORDS.filter(w => w[2] <= at && (moreWords || w[2] < EXTRA_FROM)).map(w =>
    `<button class="${w[3] === "do" ? "" : w[3]}" data-word="${esc(w[0])}">${esc(w[0])}</button>`).join("") +
    (extra ? `<button class="more" data-more="1" title="${moreWords ? "Fewer words" : "More words your rover knows"}">${moreWords ? "fewer ▴" : "more ▾"}</button>` : "");
  $("chips").onclick = e => {
    if (e.target.dataset && e.target.dataset.more) { moreWords = !moreWords; renderChips(); return; }
    const word = e.target.dataset && e.target.dataset.word;
    if (!word) return;
    const w = WORDS.find(x => x[0] === word);
    $("chipHelp").innerHTML = `✍️ Type it: <code>${esc(w[3] === "shape" ? word + " …" : word)}</code> ` +
      codeSpans(w[1] + (word.startsWith("plant") ? ` Your seeds: ${seeds}.` : ""));
    $("chipHelp").title = $("chipHelp").textContent;
  };
  $("helpWords").innerHTML = WORDS.map(w => `<tr><td><code>${esc(w[0])}</code></td><td>${codeSpans(w[1])}</td></tr>`).join("");
}

// ---- The job (or order) card, and the code to type beside the code box ----------------------
function renderJob() {
  const j = farm.job, o = farm.order;
  let html = "";
  if (j) {
    html = `<div class="job-head"><small>Job ${j.n} of ${j.of}</small><b>${esc(j.title)}</b><span class="pay">🪙 +${j.pay}</span></div>` +
      `<p>${codeSpans(j.say)}</p>` +
      (j.code && sampleHidden === j.n ? `<div class="row"><button class="quiet small" id="sampleShow">📖 Show the code</button></div>` : "");
  } else if (o) {
    html = `<div class="job-head"><small>📦 Order ${farm.orders + 1}</small><b>${o.need} × ${o.icon} ${esc(o.name)}</b>` +
      `<span class="pay">🪙 +${coinText(o.pay)}${o.crate ? " and a 🎁" : ""}</span></div>` +
      `<p>The space station wants ${o.need}. Pick them on any days: <code>plant("${esc(o.crop)}")</code></p>` +
      `<div class="row"><div class="meter"><b style="width:${100 * o.have / o.need}%"></b></div><span>${o.have} of ${o.need}</span>` +
      `<button class="quiet small" id="orderSkip" title="Get a different order. It's free.">🔄 Different order</button></div>`;
  }
  $("job").innerHTML = html;
  $("job").hidden = !html;
  if ($("sampleShow")) $("sampleShow").onclick = () => { sampleHidden = null; renderJob(); };
  if ($("orderSkip")) $("orderSkip").onclick = async () => {
    const out = await post("/planet/farm/buy", {id: me, kind: "order"}).catch(() => null);
    if (out && out.farm) take(out.farm);
  };
  renderSample();
}
function renderSample() {
  const j = farm && farm.job, on = !!(j && j.code && sampleHidden !== j.n);
  $("sample").hidden = !on;
  $("work").classList.toggle("with-sample", on);
  if (!on) return;
  const want = j.code.replace(/\n+$/, "").split("\n"), have = editor.value.split("\n");
  let next = -1;
  $("sampleCode").innerHTML = want.map((line, i) => {
    const ok = (have[i] || "").replace(/\s+$/, "") === line;
    if (!ok && next < 0) next = i;
    return `<span class="${ok ? "ok" : i === next ? "next" : ""}">${esc(line) || " "}</span>`;
  }).join("");
  $("sampleFoot").hidden = !j.give;
  const all = next < 0 && have.slice(want.length).every(line => !line.trim());
  $("runButton").classList.toggle("nudge", all || farm.day === 0);
}

// ---- The top of the page -----------------------------------------------------------------
function showBattery(left, full) {
  $("batteryFill").style.width = `${Math.max(0, 100 * left / full)}%`;
  $("batteryText").textContent = `${Math.max(0, left)} of ${full}`;
  $("battery").classList.toggle("low", left / full <= .2);
}
function renderTop() {
  $("title").textContent = farm.title;
  $("hot").innerHTML = `📈 <span>Wanted today: </span><b>${farm.hot.icon} ${esc(farm.hot.name)}</b> pays double`;
  $("hot").title = farm.hot.have ? "Today the space station pays double for this crop. It changes every day."
    : "Today the space station pays double for this crop. Its seeds are in the shop.";
  $("bonus").innerHTML = `⭐ <span>Star bonus </span><b>+${farm.stars}%</b>`;
  $("dayLabel").textContent = `Day ${farm.day + 1}`;
  showBattery(farm.battery, farm.battery);
  const goods = [...farm.shop.upgrades, ...farm.shop.crops, ...farm.shop.decor].filter(g => g.can).length;
  $("shopPip").hidden = !goods; $("shopPip").textContent = goods;
  $("shopButton").classList.toggle("can", goods > 0);
  $("muteButton").textContent = SFX.muted ? "🔇" : "🔊";
  $("speedButton").textContent = `${speed}×`;
}
function take(view, keepScene) {
  farm = view;
  coinsGoal = farm.coins;
  if (!keepScene) scene = {...farm, own: true};
  renderTop(); renderJob(); renderChips(); updateEditor();
  if (!$("shop").hidden) renderShop();
}

// ---- Running a day ------------------------------------------------------------------------
function say(kind, head, lines) {
  const box = $("result");
  box.className = `result ${kind}`;
  box.innerHTML = `<b class="head">${head}</b>` + lines.map(line => `<p>${line}</p>`).join("");
  box.scrollTop = 0;
}
function stopAuto(why) {
  $("auto").checked = false; $("autoLabel").classList.remove("on");
  if (why) toast("🔁", "Auto is off", why);
}
async function pressRun() {
  lastInput = performance.now(); idleDays = 0;
  if (play) { play.skip = true; return; }
  if (!busy) runDay();
}
async function runDay() {
  if (busy || !farm) return;
  busy = true;
  errorLine = null; activeLine = null; updateEditor();
  $("runButton").classList.remove("nudge");
  let out = null;
  for (let tries = 0; tries < 4 && (!out || out.wait); tries++) {
    if (out) await sleep(350);
    out = await post("/planet/farm/run", {id: me, code: editor.value}).catch(() => null);
  }
  if (!out || out.wait) {
    busy = false; stopAuto();
    say("bad", "No answer from the game", ["Check with your teacher that the game is still running, then press ▶ Run a day again."]);
    return;
  }
  if (out.error === "join") { leave(); return; }
  if (out.open === false) { showClosed(); return; }
  if (!out.counted) {   // the code couldn't be read, so the day never started
    busy = false; stopAuto();
    errorLine = out.line || null; showLine(null);
    if (errorLine) { const h = lineHeight(); editor.scrollTop = Math.max(0, (errorLine - 3) * h); updateEditor(); }
    SFX.play("error");
    say("bad", out.memory_full ? "🧠 Too many lines" : "🛠 One thing to fix", [codeSpans(out.error), "Nothing is broken, and the day hasn't started. Fix it and run again."]);
    take(out.farm);
    return;
  }
  const before = farm;
  coinsGoal = coinsShown = before.coins;
  $("today").textContent = "";
  await playDay(out);
  if (bubble) await sleep(Math.max(0, Math.min(1200, bubble.until - performance.now())));   // let it finish talking
  $("runButton").textContent = "▶ Run a day";
  showLine(null);
  const quick = !out.frames.length;
  await nightfall(() => { take(out.farm); Object.assign(rover, {x: 1, y: 1, px: 1, py: 1, angle: 0}); pops = {}; }, quick);
  // What the day came to.
  const got = Object.entries(out.picked).map(([crop, n]) => `${before.icons[crop]}×${n}`).join("  ");
  const lines = [];
  if (out.golden) lines.push(`<span class="gold">✨ ${out.golden} golden! Each one pays 5 times over.</span>`);
  if (out.best) lines.push(`<span class="gold">🏆 Your best day yet!</span>`);
  if (out.error) { errorLine = out.line || null; updateEditor(); lines.push(`🛠 ${codeSpans(out.error)}`); }
  for (const line of out.say) lines.push(codeSpans(line));
  const total = out.income + out.bonus;
  const head = total ? `☀️ Day ${before.day + 1}: <span class="gold">🪙 +${coinText(total)}</span>` +
    (out.bonus ? ` <small>(${coinText(out.income)} and ⭐ ${coinText(out.bonus)} star bonus)</small>` : "") + (got ? `   ${got}` : "")
    : `☀️ Day ${before.day + 1}: nothing picked today.`;
  say(out.error ? "bad" : total ? "fine" : "", head, lines);
  $("today").textContent = total ? `Yesterday: 🪙 +${coinText(total)}  ·  best day 🪙 ${coinText(out.farm.best)}` : "";
  if (total) { SFX.play("coins"); $("coinsBox").classList.remove("bump"); void $("coinsBox").offsetWidth; $("coinsBox").classList.add("bump"); }
  if (out.error) { SFX.play("error"); stopAuto(); }
  for (const job of out.jobs) {
    SFX.play("job");
    toast("✅", `Job done: ${job.title}`, `+${job.pay} coins`);
    $("job").classList.remove("done"); void $("job").offsetWidth; $("job").classList.add("done");
  }
  for (const badge of out.badges || []) toast(badge.icon, `New badge: ${badge.name}`, badge.how);
  if (out.order) {
    SFX.play("job");
    toast("📦", "Order filled!", `+${coinText(out.order.pay)} coins`);
    if (out.order.crate) await openCrate(out.order.crate);
  }
  busy = false;
  if ($("auto").checked) {
    if (++idleDays >= farm.idle_days) {
      stopAuto();
      say("", "💤 Your rover stopped for a rest", ["Press ▶ Run a day, or turn 🔁 Auto back on, to keep farming."]);
      return;
    }
    await sleep(Math.max(250, 700 / speed));
    if ($("auto").checked && !busy) runDay();
  }
}
function openCrate(crate) {
  return new Promise(done => {
    const box = $("crateBox"), button = $("crateOpen");
    box.textContent = "🎁"; box.className = "box shake";
    $("crateTitle").textContent = "A crate from the space station!";
    $("crateSay").textContent = "You filled the order. Press the crate to open it.";
    button.textContent = "Open it";
    $("crate").hidden = false;
    let opened = false;
    box.onclick = button.onclick = () => {
      if (opened) { $("crate").hidden = true; done(); return; }
      opened = true; SFX.play("crate");
      box.className = "box pop";
      if (crate.key) {
        box.textContent = crate.icon;
        $("crateTitle").textContent = `You found a ${crate.name.toLowerCase()}!`;
        $("crateSay").textContent = "It's in your yard now. You can only get it from a crate.";
      } else {
        box.textContent = "💰";
        $("crateTitle").textContent = `${coinText(crate.coins)} coins!`;
        $("crateSay").textContent = "You have everything the crates can hold, so this one was full of coins.";
      }
      button.textContent = "Nice!";
    };
  });
}

// ---- The shop -------------------------------------------------------------------------------
function buyButton(kind, g) {
  return `<button class="buy" data-kind="${kind}" data-key="${esc(g.key)}" ${g.can ? "" : "disabled"} ` +
    `title="${g.can ? "Buy it" : `You need ${coinText(g.cost - farm.coins)} more coins`}">🪙 ${coinText(g.cost)}</button>`;
}
function renderShop() {
  const s = farm.shop;
  $("shopCoins").textContent = coinText(coinsShown);
  const ups = s.upgrades.map(g => `<div class="good"><span class="ico">${g.icon}</span><div><b>${esc(g.name)}</b>` +
    `<small>${g.next ? `${esc(g.now)} → <b style="display:inline;color:var(--bone)">${esc(g.next)}</b>` : esc(g.now)}</small></div>` +
    (g.next ? buyButton("upgrade", g) : `<span class="tag">✓ As big as it gets</span>`) + `</div>`).join("");
  const crops = s.crops.map(g => `<div class="good ${g.have ? "" : "locked"}"><span class="ico">${g.icon}</span><div><b>${esc(g.name)}</b>` +
    `<small>${g.days} ${g.days > 1 ? "days" : "day"} to grow · pays 🪙 ${g.pay}</small><small>${codeSpans(g.about)}</small>` +
    (g.have ? `<small><code>plant("${esc(g.key)}")</code></small>` : "") + `</div>` +
    (g.have ? `<span class="tag">✓ Yours</span>` : buyButton("crop", g)) + `</div>`).join("");
  const order = g => g.cost == null ? 1e12 : g.cost;
  const decor = [...s.decor].sort((a, b) => order(a) - order(b)).map(g =>
    `<div class="good ${g.have ? "have" : g.crate ? "locked" : ""}"><span class="ico">${g.icon}</span><div><b>${esc(g.name)}</b>` +
    (g.until && !g.have ? `<small>Only here for a while</small>` : "") + `</div>` +
    (g.have ? `<span class="tag">✓ Yours</span>` : g.crate ? `<span class="tag" style="color:var(--haze)">🎁 Crate</span>` : buyButton("decor", g)) +
    `</div>`).join("");
  $("shopBody").innerHTML = `<h3>Make the farm bigger</h3><div class="goods">${ups}</div>` +
    `<h3>Seeds</h3><div class="goods">${crops}</div>` +
    `<h3>For your yard (click one in the yard and it says hello). 🎁 ones only come in crates, from orders.</h3><div class="goods decor-grid">${decor}</div>`;
}
async function buy(kind, key) {
  const out = await post("/planet/farm/buy", {id: me, kind, key}).catch(() => null);
  if (!out) return;
  if (out.open === false) { showClosed(); return; }
  if (out.error) { toast("🛒", "Not yet", out.error); if (out.farm) take(out.farm, !!play); return; }
  SFX.play("buy");
  const news = {field: "The new squares are empty. Plant them!", battery: "Your rover can do more in a day.",
                memory: "Your rover remembers more lines of code."};
  toast("🛒", `You bought: ${out.bought}`, kind === "upgrade" ? news[key] : kind === "crop" ? `Plant them with  plant("${key}")` : "Look for it in your yard.");
  for (const job of out.jobs || []) { SFX.play("job"); toast("✅", `Job done: ${job.title}`, `+${job.pay} coins`); }
  take(out.farm, !!play);
}

// ---- Visiting a classmate's farm --------------------------------------------------------------
function openVisit() {
  visiting = null;
  $("visitYardBox").hidden = true; $("visitSay").textContent = "";
  const rows = farm.class_farms;
  $("friends").innerHTML = rows.length ? rows.map(r => `<button data-who="${esc(r.who)}">${esc(r.name)}</button>`).join("")
    : "<p>Nobody else has started a farm yet. Yours is the first!</p>";
  $("visit").hidden = false;
}
async function visitFarm(who, button) {
  const out = await get(`/planet/farm/visit?id=${encodeURIComponent(me)}&who=${encodeURIComponent(who)}`).catch(() => null);
  if (!out || out.error) { toast("👀", "Can't visit right now", out ? out.error : "No answer from the game."); return; }
  for (const b of $("friends").children) b.classList.toggle("on", b === button);
  visiting = out;
  $("visitYardBox").hidden = false;
  $("visitSay").textContent = `${out.name} · ${out.title} · day ${out.day}`;
}

// ---- Wiring it up -------------------------------------------------------------------------------
function closeDialogs() {
  for (const id of ["shop", "visit", "help"]) $(id).hidden = true;
  visiting = null;
}
editor.addEventListener("keydown", codeKey);
editor.addEventListener("input", typed);
editor.addEventListener("scroll", updateEditor);
$("runButton").addEventListener("click", pressRun);
$("auto").addEventListener("change", e => {
  $("autoLabel").classList.toggle("on", e.target.checked);
  idleDays = 0;
  if (e.target.checked && !busy) runDay();
});
$("speedButton").addEventListener("click", () => {
  speed = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length];
  store("farmSpeed", speed); $("speedButton").textContent = `${speed}×`;
  if (play) play.step = stepMs(play.out.frames.length);
});
$("muteButton").addEventListener("click", () => { $("muteButton").textContent = SFX.toggle() ? "🔇" : "🔊"; });
$("shopButton").addEventListener("click", () => { renderShop(); $("shop").hidden = false; });
$("shopBody").addEventListener("click", e => { const b = e.target.closest(".buy"); if (b && !b.disabled) buy(b.dataset.kind, b.dataset.key); });
$("shopClose").addEventListener("click", closeDialogs);
$("visitButton").addEventListener("click", openVisit);
$("friends").addEventListener("click", e => { if (e.target.dataset.who) visitFarm(e.target.dataset.who, e.target); });
$("visitClose").addEventListener("click", closeDialogs);
$("helpButton").addEventListener("click", () => { $("calmBox").checked = CALM; $("bigBox").checked = document.body.classList.contains("big"); $("help").hidden = false; });
$("helpClose").addEventListener("click", closeDialogs);
$("calmBox").addEventListener("change", e => { CALM = e.target.checked; store("planetCalm", CALM ? "1" : "0"); document.body.classList.toggle("calm", CALM); });
$("bigBox").addEventListener("change", e => { document.body.classList.toggle("big", e.target.checked); store("planetBig", e.target.checked ? "1" : "0"); updateEditor(); });
$("sampleClose").addEventListener("click", () => { sampleHidden = farm.job && farm.job.n; renderJob(); });
$("sampleGive").addEventListener("click", () => { if (farm.job && farm.job.code) replaceAll(farm.job.code); });
for (const id of ["shop", "visit", "help"]) $(id).addEventListener("click", e => { if (e.target === $(id)) closeDialogs(); });
document.addEventListener("keydown", e => { lastInput = performance.now(); idleDays = 0; if (e.key === "Escape") closeDialogs(); });
document.addEventListener("pointerdown", () => { lastInput = performance.now(); idleDays = 0; });
// Clicking the yard: a thing in it says hello, and the dotted outline opens the shop.
$("yard").addEventListener("click", e => {
  if (!yardView) return;
  const box = $("yard").getBoundingClientRect(), x = e.clientX - box.left, y = e.clientY - box.top;
  const hit = yardView.hits.find(h => Math.hypot(h.cx - x, h.cy - y) < h.r);
  if (hit) { wiggles[hit.d.key] = performance.now(); return; }
  const L = yardView.L, fx = (x - L.ox) / L.cell - 2, fy = (y - L.oy) / L.cell - 2, nf = farm.next_field;
  if (nf && fx >= 0 && fy >= 0 && fx < nf.w && fy < nf.h && (fx >= farm.w || fy >= farm.h)) { renderShop(); $("shop").hidden = false; }
});
window.addEventListener("resize", updateEditor);

// The teacher's messages reach the farm too, and so does closing it.
let noticeSeen = null;
setInterval(async () => {
  if (!farm) return;
  const lately = performance.now() - lastInput < 90000 ? "&busy=1" : "";
  const out = await get(`/planet/ping?id=${encodeURIComponent(me)}${lately}`).catch(() => null);
  if (!out) return;
  if (out.farm === false) { showClosed(); return; }
  if (out.notice) {
    if (noticeSeen != null && out.notice.n && out.notice.n !== noticeSeen) toast(out.notice.icon, out.notice.title, out.notice.text);
    noticeSeen = out.notice.n;
  }
}, 6000);

async function start() {
  if (!me) { leave(); return; }
  const view = await get(`/planet/farm/state?id=${encodeURIComponent(me)}`).catch(() => null);
  if (!view) { $("closed").hidden = false; $("closedSay").textContent = "No answer from the game. Check with your teacher that it's still running."; return; }
  if (view.error === "join") { leave(); return; }
  if (!view.open) { showClosed(); return; }
  SFX.classDefault(!!view.sound);
  $("app").hidden = false;
  const kept = recall(`farmCode:${me}`);
  editor.value = kept != null && kept.trim() ? kept : view.code;
  coinsShown = view.coins;
  take(view);
  $("coins").textContent = coinText(view.coins);
  say("", view.day ? `Welcome back, ${esc(view.name)}!` : `Welcome to your farm, ${esc(view.name)}!`,
      [view.day ? "Your farm is just as you left it. Press ▶ Run a day." : "Your code is one farm day. Press ▶ Run a day and watch your rover work."]);
  requestAnimationFrame(loop);
}
start();
