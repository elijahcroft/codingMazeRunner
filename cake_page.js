// Cake Shop: the student page. Customers come in, students write Python, the
// cake bakes step by step on the counter and the customer reacts.
"use strict";

const $ = id => document.getElementById(id);
function esc(value) {
  return String(value).replace(/[&<>"']/g, ch => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch]));
}
async function post(url, data) {
  const response = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
  return response.json();
}
async function get(url) { return (await fetch(url)).json(); }
function store(key, value) { try { localStorage.setItem(key, value); } catch (_) {} }
function recall(key) { try { return localStorage.getItem(key); } catch (_) { return null; } }
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }
function announce(text) { $("announce").textContent = text; }
// Text with code in it: `backticks` mark the code in tips, rules and hints.
// The interpreter's messages put two spaces round code instead, like
//   Did you mean  layer("vanilla") ?
function fmt(text) {
  if (String(text).includes("`")) return esc(text).replace(/`([^`]+)`/g, "<code>$1</code>");
  return esc(text).replace(/(^|\s{2})(\S.*?)(?=\s{2}|$)/g, (m, sp, bit) =>
    /[()"=\[\]]/.test(bit) && sp ? `${sp}<code>${bit}</code>` : m);
}

// ---- Sound: every kitchen step makes a little noise -------------------------------------
const SFX = (() => {
  let ac = null, muted = recall("cakeMuted") === "1", last = 0;
  function context() {
    if (!ac) { try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (_) { return null; } }
    if (ac.state === "suspended") ac.resume();
    return ac;
  }
  function tone(freq, dur, {type = "sine", vol = .2, at = 0, slide = 0} = {}) {
    const c = context(); if (!c) return;
    const t = c.currentTime + at, o = c.createOscillator(), g = c.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.linearRampToValueAtTime(Math.max(30, freq + slide), t + dur);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol * .5, t + .008);
    g.gain.exponentialRampToValueAtTime(.0005, t + dur);
    o.connect(g).connect(c.destination); o.start(t); o.stop(t + dur + .02);
  }
  function noise(dur, {vol = .15, at = 0, from = 800, to = 2000, q = 1} = {}) {
    const c = context(); if (!c) return;
    const t = c.currentTime + at, n = Math.floor(c.sampleRate * dur);
    const buf = c.createBuffer(1, n, c.sampleRate), data = buf.getChannelData(0);
    for (let i = 0; i < n; i++) data[i] = Math.random() * 2 - 1;
    const src = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
    src.buffer = buf; f.type = "bandpass"; f.Q.value = q;
    f.frequency.setValueAtTime(from, t); f.frequency.linearRampToValueAtTime(to, t + dur);
    g.gain.setValueAtTime(vol * .5, t); g.gain.exponentialRampToValueAtTime(.0005, t + dur);
    src.connect(f).connect(g).connect(c.destination); src.start(t);
  }
  const sounds = {
    layer: () => { tone(190, .18, {vol: .4, slide: -100}); noise(.07, {vol: .1, from: 300, to: 200}); },
    frosting: () => noise(.32, {vol: .16, from: 500, to: 1700, q: .7}),
    drip: () => { tone(950, .1, {vol: .14, slide: -520}); tone(720, .12, {vol: .12, slide: -420, at: .09}); },
    sprinkles: () => { for (let i = 0; i < 10; i++) tone(2300 + Math.random() * 1900, .03, {vol: .05, at: i * .024, type: "triangle"}); },
    swirl: () => tone(480, .15, {type: "triangle", vol: .15, slide: 440}),
    topping: () => tone(860, .1, {vol: .22, slide: 320}),
    candle: () => { tone(1320, .05, {type: "square", vol: .04}); noise(.1, {vol: .06, from: 2500, to: 4200, at: .02}); },
    write: () => noise(.22, {vol: .07, from: 3000, to: 2400, q: 3}),
    tier: () => tone(130, .24, {vol: .4, slide: -50}),
    happy: () => [523, 659, 784, 1047].forEach((f, i) => tone(f, .2, {type: "triangle", vol: .2, at: i * .09})),
    sad: () => { tone(392, .2, {type: "triangle", vol: .16}); tone(311, .32, {type: "triangle", vol: .16, at: .18, slide: -20}); },
    star: i => tone(880 * Math.pow(1.26, i || 0), .3, {vol: .22}),
    error: () => { tone(220, .14, {type: "square", vol: .05}); tone(175, .2, {type: "square", vol: .05, at: .13}); },
    click: () => tone(1200, .03, {vol: .07}),
    whoosh: () => noise(.3, {vol: .08, from: 400, to: 3000}),
    fire: () => noise(.7, {vol: .2, from: 180, to: 900, q: .5}),
    heart: () => { tone(988, .1, {vol: .14}); tone(1319, .16, {vol: .14, at: .08}); },
    unlock: () => [784, 988, 1175, 1568].forEach((f, i) => tone(f, .16, {type: "sine", vol: .16, at: i * .07})),
  };
  return {
    play(name, arg) {
      if (muted || !sounds[name]) return;
      try { sounds[name](arg); } catch (_) {}
    },
    // For steps that come thick and fast (100 candles), not every one beeps.
    step(name) {
      const now = performance.now();
      if (now - last < 65) return;
      last = now; this.play(name);
    },
    toggle() { muted = !muted; store("cakeMuted", muted ? "1" : "0"); return muted; },
    get muted() { return muted; },
    wake() { if (!muted) context(); },
  };
})();

// ---- State ---------------------------------------------------------------------------------
let me = null;          // player id
let state = null;       // /cake/state
let mode = "orders";    // orders | studio | window
let view = null;        // the open level, from /cake/level
let results = null;     // the last bake's runs, one per customer
let rewards = null;
let sel = 0;            // which customer is on screen
let busy = false;
let play = null;        // the bake being animated
let shown = null;       // {tiers, fit}: the cake on the counter when nothing is playing
let queueToken = 0;     // bumped to stop a queue that's playing
let served = 0;         // customers who've had their cake so far this bake
let studio = {run: null, seed: 0};
let errorLine = 0, errorCount = 0;
let pantryTab = "flavours";
let windowData = null, windowTimer = null, detail = null;

const JOIN_PALETTE = {
  flavours: {vanilla: "#f7e1ae", strawberry: "#f6a3b6", chocolate: "#7b4a2d", lemon: "#fbe07a"},
  colours: {white: "#fffcf6", pink: "#f9a6c8", red: "#e5474f"},
  toppings: {strawberry: "🍓", cherry: "🍒", star: "⭐"},
};
const STAND_ICONS = {plate: "🍽️", board: "🪵", glass: "🥂", pink: "🌸", gold: "👑"};
const SHOP_IDEAS = ["The Sugar Plum", "Sprinkle Palace", "Cloud Nine Cakes", "Crumbs & Co",
  "The Happy Whisk", "Frosted Dreams", "The Little Oven", "Butter & Bloom"];

// "cakeCode2": the levels changed in Oct 2026, so code saved for the old ones isn't loaded.
function codeKey(key) { return `cakeCode2:${me}:${key}`; }
// What the editor holds: the Studio, the open level, or nothing on the Shop Window
// (which keeps whatever the editor had, so it mustn't be saved as a level).
function contextKey() { return mode === "studio" ? "studio" : mode === "window" ? null : view && view.key; }
function saveCode() {
  const key = contextKey();
  if (me && key) store(codeKey(key), $("code").value);
}

// ---- Joining ---------------------------------------------------------------------------------
async function join(event) {
  event.preventDefault();
  const name = $("name").value.trim();
  if (!name) { $("name").focus(); return; }
  SFX.wake();
  $("joinButton").disabled = true;
  try {
    const player = await post("/join", {name});
    store("mazeId", player.id);
    if (await enter(player.id)) return;
  } catch (_) {}
  $("joinButton").disabled = false;
  $("joinButton").textContent = "No answer. Try again";
}
async function resume() {
  const id = recall("mazeId");
  if (!id || !(await enter(id))) joinScene();
}
async function enter(id) {
  let data;
  try { data = await get("/cake/state?id=" + encodeURIComponent(id)); } catch (_) { return false; }
  if (!data.you) return false;
  me = id;
  CakeArt.setPalette(data.palette);
  useState(data);
  $("join").hidden = true; $("app").hidden = false;
  joinArt = null;
  $("baker").textContent = data.you.name;
  $("muteButton").textContent = SFX.muted ? "🔇" : "🔊";
  requestAnimationFrame(frameLoop);
  setInterval(checkForNews, 20000);
  const lastLevel = recall(`cakeLevel:${me}`);
  const open = allLevels().filter(l => l.open).map(l => l.key);
  await openLevel(open.includes(lastLevel) ? lastLevel : data.current);
  return true;
}
// Levels the teacher opens for everyone show up without a reload.
async function checkForNews() {
  if (busy || play || document.hidden || !state) return;
  let data;
  try { data = await get("/cake/state?id=" + encodeURIComponent(me)); } catch (_) { return; }
  if (!data.you || busy || play) return;
  const was = new Set(allLevels().filter(l => l.open).map(l => l.key));
  const before = state;
  useState(data);
  const fresh = allLevels().filter(l => l.open && !was.has(l.key));
  if (fresh.length && before)
    showToasts([{icon: "🔓", name: fresh.length === 1 ? `${fresh[0].name} is open!` : `${fresh.length} new customers are open!`,
                 how: "Your teacher opened them for you."}]);
}
function useState(data) {
  const before = state;
  if (!data.palette && before) data.palette = before.palette;   // only /cake/state sends it
  state = data;
  $("totalStars").textContent = data.total_stars;
  $("shopName").textContent = data.you.shop || `${data.you.name}'s Bakery`;
  document.title = `${data.you.shop || "Cake Shop"} · Cake Shop`;
  applyLook();
  renderRoute();
  if (before && mode === "studio") renderStudioCard();
}
function applyLook() {
  const scene = $("scene");
  scene.className = scene.className.replace(/wp-\w+/, "wp-" + (state.look.wallpaper || "strawberry"));
}

// ---- The route of customers ---------------------------------------------------------------
function allLevels() { return state.chapters.flatMap(ch => ch.levels.map(l => ({...l, chapter: ch}))); }
function renderRoute() {
  const here = view && view.key;
  $("route").innerHTML = state.chapters.map(ch => {
    const open = ch.levels.some(l => l.open);
    const isHere = ch.levels.some(l => l.key === here);
    return `<div class="chap${isHere ? " here" : ""}${open ? "" : " locked"}" title="${esc(ch.name)}: ${esc(ch.blurb)}">` +
      `<span class="ci" aria-hidden="true">${ch.icon}</span><span class="cn">${esc(ch.name)}</span>` +
      ch.levels.map(l => {
        const n = l.stars.filter(Boolean).length;
        const cls = ["lvl", l.key === here ? "now" : "", n === 3 ? "gold" : l.solved ? "done" : ""].join(" ");
        return `<button class="${cls}" data-level="${l.key}" ${l.open ? "" : "disabled"} ` +
          `title="${esc(l.name)}${l.open ? ` · ${n} of 3 stars` : " · not open yet"}" aria-label="${esc(l.name)}${l.open ? `, ${n} of 3 stars` : ", locked"}">` +
          `<span aria-hidden="true">${esc(l.key)}</span>` +
          (l.open ? `<span class="mini" aria-hidden="true">${"★".repeat(n)}<s>${"★".repeat(3 - n)}</s></span>` : "") + `</button>`;
      }).join("") + `</div>`;
  }).join("");
  const now = $("route").querySelector(".lvl.now");
  if (now && here !== renderRoute.shown) now.scrollIntoView({block: "nearest", inline: "center"});
  renderRoute.shown = here;   // scroll only when the level changes, not on every refresh
}
$("route").addEventListener("click", e => {
  const b = e.target.closest("button[data-level]");
  if (!b || b.disabled || busy) return;
  SFX.play("click");
  if (mode === "orders") openLevel(b.dataset.level);
  else setMode("orders", b.dataset.level);
});

// ---- Opening a level --------------------------------------------------------------------------
// fromMode: setMode has already saved the editor under the page we came from.
async function openLevel(key, fromMode = false) {
  if (!fromMode) saveCode();
  stopQueue();
  let data;
  try { data = await get(`/cake/level?id=${encodeURIComponent(me)}&level=${encodeURIComponent(key)}`); }
  catch (_) { showBanner("error", "The shop isn't answering. Try again in a moment, or tell your teacher."); return; }
  if (data.you === null) { forget(); return; }
  if (data.error) { showBanner("error", data.error); return; }
  view = data; results = null; rewards = null; sel = 0;
  store(`cakeLevel:${me}`, key);
  const saved = recall(codeKey(key));
  $("code").value = saved !== null ? saved : (data.code || data.starter);
  $("code").scrollTop = 0;
  errorLine = 0;
  renderRoute();
  renderLevel();
  renderTip(data.tip, !recall(`cakeTip:${me}:${key}`));
  store(`cakeTip:${me}:${key}`, "1");
  shown = {tiers: [CakeArt.newTier()], fit: null};
  showCustomer(0, {enter: true});
  hideBanner();
  updateEditor();
  renderNotes();
}
function renderLevel() {
  $("levelName").innerHTML = `<span class="key">${esc(view.key)}</span>${esc(view.name)}`;
  renderGoals();
  renderRules();
  renderBook(view.commands, view.new);
  renderChips();
  renderHints();
  $("hintButton").hidden = false;
  $("resetButton").hidden = false;
  $("surpriseButton").hidden = true;
  $("studioCard").hidden = true;
  $("ticket").hidden = false;
}
function renderGoals() {
  $("goals").innerHTML = view.goals.map((g, i) =>
    `<span class="goal${view.stars[i] ? " got" : ""}"><i>★</i>${fmt(g)}</span>`).join("");
}
// What to bake, at the top of the kitchen: the level's rules, the same for
// every customer, so ONE program can follow them.
function renderRules() {
  let html;
  if (mode === "studio") {
    html = `<h2>🎨 Bake anything you like</h2><p>Every command works here, and so do <code>choice()</code> and <code>randint()</code> for surprise cakes.</p>`;
  } else {
    const n = view.customers.length;
    html = `<h2>${view.bake_off ? "🏆 Bake exactly what each ticket says" : `One program, ${n} customers. Each cake:`}</h2>` +
      `<ul>${view.rules.map(r => `<li>${fmt(r)}</li>`).join("")}</ul>`;
  }
  $("rules").innerHTML = html;
}

// ---- The customer, the ticket and the queue -----------------------------------------------
function customerData(i) {
  if (mode === "studio") return {name: "You", face: "🧑‍🍳", says: "What shall we bake today?"};
  return results ? results[i] : view.customers[i];
}
function showCustomer(i, {enter = false, reacted = false} = {}) {
  sel = i;
  const c = customerData(i);
  $("face").textContent = c.face;
  $("nametag").textContent = c.name;
  const bubble = $("bubble");
  if (reacted && c.reply) {
    bubble.textContent = c.reply;
    bubble.className = "bubble pop " + (c.happy ? "happy" : "sad");
  } else {
    bubble.textContent = c.says;
    bubble.className = "bubble";
  }
  if (enter) restartClass($("face"), "enter");
  if (results && results[i] && !play) shown = {tiers: results[i].cake, fit: results[i].cake};
  renderTicket();
  renderQueue();
  renderNotes();
}
function restartClass(el, cls) {
  el.classList.remove("enter", "happy", "sad");
  void el.offsetWidth;
  el.classList.add(cls);
}
function pyValue(v) {
  if (v === true) return "True";
  if (v === false) return "False";
  if (v === null) return "None";
  if (Array.isArray(v)) return "[" + v.map(pyValue).join(", ") + "]";
  if (typeof v === "string") return JSON.stringify(v);
  return String(v);
}
function ticketCode(t) {
  return "order = {\n" + Object.entries(t).map(([k, v]) => `  "${k}": ${pyValue(v)},`).join("\n") + "\n}";
}
// The ticket as lines that wrap with a hanging indent, so a long list stays
// readable. Click a line to put  order["that key"]  in the code.
function ticketHtml(t) {
  return ticketCode(t).split("\n").map(l => {
    const key = (/^  "(\w+)":/.exec(l) || [])[1];
    return key && mode === "orders"
      ? `<button class="tl key" data-key="${esc(key)}" title='Click to add order["${esc(key)}"] to your code'>${highlight(l)}</button>`
      : `<span class="tl">${highlight(l)}</span>`;
  }).join("");
}
// A quoted word under the cursor (or selected) becomes the ticket's value:
// layer("lemon") turns into layer(order["flavour"]).
function insertTicketKey(key) {
  const t = $("code"), v = t.value, text = `order["${key}"]`;
  let s = t.selectionStart, e = t.selectionEnd;
  if (v[s - 1] === '"' && v[e] === '"' && !v.slice(s, e).includes('"')) { s -= 1; e += 1; }
  else if (s === e) {
    const lineStart = v.lastIndexOf("\n", s - 1) + 1;
    let lineEnd = v.indexOf("\n", s); if (lineEnd < 0) lineEnd = v.length;
    const m = [...v.slice(lineStart, lineEnd).matchAll(/"[^"]*"/g)]
      .find(m => lineStart + m.index < s && s < lineStart + m.index + m[0].length);
    if (m) { s = lineStart + m.index; e = s + m[0].length; }
  }
  replaceText(s, e, text);
  t.setSelectionRange(s + text.length, s + text.length);
}
function renderTicket() {
  if (mode === "studio") return;
  const c = customerData(sel);
  const r = results && sel < served ? results[sel] : null;   // the checks once they've had their cake
  let html = `<span class="pin" aria-hidden="true">📌</span>`;
  // After a bake the checks come first, and a long ticket folds away so it all fits.
  if (c.ticket && r) {
    html += `<h3>🎫 ${esc(c.name)}'s cake</h3>`;
  } else if (c.ticket) {
    html += `<h3>🎫 ${esc(c.name)}'s ticket</h3><pre class="tk-code">${ticketHtml(c.ticket)}</pre>`;
  } else {
    html += `<h3>🧾 Order for ${esc(c.name)}</h3>`;
  }
  if (r) {
    html += `<ul>${r.checks.map(ch => `<li class="${ch.ok ? "ok" : "no"}"><b>${ch.ok ? "✓" : "✗"}</b><span>${esc(ch.text)}</span></li>`).join("")}</ul>`;
    if (r.extras.length && !r.error) html += `<div class="extras">✨ Your own touch: ${esc(r.extras.join(", "))}</div>`;
    if (c.ticket) html += `<details class="tk"${ticketOpen ? " open" : ""}><summary>🎫 The ticket: <code>order</code></summary><pre class="tk-code">${ticketHtml(c.ticket)}</pre></details>`;
  } else if (!c.ticket && (c.checklist || view.customers[sel].checklist)) {
    html += `<ul>${(c.checklist || view.customers[sel].checklist).map(t => `<li><b>•</b><span>${esc(t)}</span></li>`).join("")}</ul>`;
  } else if (view.bake_off) {
    html += `<p style="margin:6px 0 0;color:var(--mocha)">Every bake brings five NEW customers. This is just an example ticket.</p>`;
  }
  $("ticket").innerHTML = html;
  $("ticket").scrollTop = 0;
}
let ticketOpen = true;   // the ticket stays open under the checks: it is what the code reads
$("ticket").addEventListener("toggle", e => { if (e.target.matches("details.tk")) ticketOpen = e.target.open; }, true);
$("ticket").addEventListener("mousedown", e => { if (e.target.closest("button.key")) e.preventDefault(); });   // keep the cursor in the code
$("ticket").addEventListener("click", e => {
  const b = e.target.closest("button.key");
  if (b) { SFX.play("click"); insertTicketKey(b.dataset.key); }
});
function renderQueue() {
  const list = mode === "studio" ? [] : (results || view.customers);
  const q = $("queue");
  q.hidden = list.length < 2;
  if (q.hidden) return;
  q.innerHTML = list.map((c, i) => {
    const seen = results && i < served;   // no spoilers for customers still waiting
    const st = seen ? (c.happy ? " ok" : " no") : "";
    const mark = seen ? (c.happy ? "😊" : "😕") : "";
    return `<button class="${i === sel ? "on" : ""}${st}" data-c="${i}" title="${esc(c.name)}"><span class="qf">${c.face}</span>${esc(c.name.split(" ")[0].length > 3 ? c.name.split(" ")[0] : c.name)}${mark ? ` ${mark}` : ""}</button>`;
  }).join("");
}
$("queue").addEventListener("click", e => {
  const b = e.target.closest("button[data-c]");
  if (!b) return;
  SFX.play("click");
  // Jumping to a customer mid-bake finishes the bake first, so the stars still come.
  if (results && served < results.length && mode === "orders") skipToEnd();
  stopQueue();
  const i = Number(b.dataset.c);
  showCustomer(i, {enter: true, reacted: !!results});
  if (results) { shown = {tiers: results[i].cake, fit: results[i].cake}; markError(results[i]); }
});

// ---- Kitchen notes ---------------------------------------------------------------------------------
let notice = null;   // a message under the output: how the bake went, or the shop not answering
function renderNotes() {
  const notes = $("notes");
  const r = mode === "studio" ? studio.run : results && results[sel];
  const who = mode === "studio" ? "your cake" : `${customerData(sel).name}'s cake`;
  const live = play && r && play.run === r;   // still baking: show what's printed so far
  let html = `<div class="nh">Output${r ? " · " + esc(who) : ""}</div>`;
  if (!r) {
    html += `<div class="dim">print() shows here. So do mistakes in your code.</div>`;
  } else {
    const prints = live ? r.prints.filter(p => p.step <= play.k) : r.prints;
    if (prints.length) html += prints.map(p => esc(p.text)).join("\n") + "\n";
    if (live) { /* the result comes at the end */ }
    else if (r.error) html += `<span class="err">🐛 ${esc(r.error)}</span>`;
    else html += `<span class="ok">✓ Baked in ${r.steps.length} step${r.steps.length === 1 ? "" : "s"}.</span>`;
  }
  if (notice) html += `\n<span class="${notice.kind === "error" ? "err" : "say"}">${fmt(notice.text)}${notice.extra}</span>`;
  notes.innerHTML = html;
  notes.classList.toggle("bad", !live && !!(r && r.error || notice && notice.kind === "error"));
  notes.scrollTop = notes.scrollHeight;
}

// ---- The counter: drawing, playing a bake, particles -------------------------------------------
const cakeCanvas = $("cakeCanvas"), fxCanvas = $("fx");
let lastFrame = 0, particles = [], confetti = [];
function fitCanvas(c) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = c.clientWidth, h = c.clientHeight;
  if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) {
    c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
  }
  const ctx = c.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return {ctx, w, h};
}
// Full speed while something moves; when it's just candles flickering, about
// 15 frames a second (2 in calm mode), to spare the Chromebooks' batteries.
let lastDrawn = 0;
function frameLoop(ts) {
  const dt = Math.min(64, ts - (lastFrame || ts));
  lastFrame = ts;
  const moving = play || particles.length || confetti.length;
  if (!$("app").hidden && mode !== "window" && !document.hidden &&
      (moving || ts - lastDrawn > (CALM ? 500 : 66))) {
    lastDrawn = ts;
    advance(dt);
    drawCounter(ts);
    drawFx(dt);
  }
  if (detail) drawDetail(ts);
  requestAnimationFrame(frameLoop);
}
function drawCounter(now) {
  if (CALM) now = 1000;   // still candles and sparkles
  const {ctx, w, h} = fitCanvas(cakeCanvas);
  ctx.clearRect(0, 0, w, h);
  const stand = state ? state.look.stand : "plate";
  // The stand sits on the counter, which starts 80% of the way down the scene.
  const floor = $("scene").clientHeight * .86 - cakeCanvas.offsetTop;
  if (play) {
    const k = play.k + (play.u > 0 ? 1 : 0);
    const tiers = CakeArt.replay(play.steps, Math.min(k, play.steps.length));
    const anim = play.u > 0 && play.k < play.steps.length
      ? {do: play.steps[play.k].do, tier: tiers.length - 1, u: play.u} : null;
    CakeArt.draw(ctx, w, h, {tiers, fit: play.fit, stand, anim, now, floor});
  } else if (shown) {
    CakeArt.draw(ctx, w, h, {tiers: shown.tiers, fit: shown.fit || shown.tiers, stand, now, floor});
  }
}
// Step through the bake: each step takes a moment, and lots of steps go faster.
function advance(dt) {
  if (!play || play.done) return;
  while (dt > 0 && play.k < play.steps.length) {
    if (play.u === 0) startStep(play.steps[play.k]);
    const need = (1 - play.u) * play.dur;
    if (dt < need) { play.u += dt / play.dur; dt = 0; }
    else { dt -= need; play.k += 1; play.u = 0; }
  }
  if (play.k >= play.steps.length) finishPlay();
}
function startStep(step) {
  SFX.step(step.do);
  if (step.do === "sprinkles") puff("✨", 4);
  setRunLine(step.line);
  if (play.run.prints.length) renderNotes();
}
function startPlay(run, speed = 1) {
  return new Promise(resolve => {
    const n = run.steps.length;
    const base = n > 40 ? 3600 / n : n > 14 ? 5200 / n : 380;
    play = {steps: run.steps, fit: run.cake, k: 0, u: 0, dur: Math.max(28, base) / speed, done: false, resolve, run};
    playing(true);
    if (!n) finishPlay();
    else renderNotes();
  });
}
function finishPlay() {
  if (!play || play.done) return;
  play.done = true;
  setRunLine(0);
  shown = {tiers: play.run.cake, fit: play.run.cake};
  const resolve = play.resolve;
  play = null;
  resolve();
}
// Skip shows while a bake (or a queue of them) plays; Replay once it's over.
function playing(on) {
  $("skipButton").hidden = !on;
  $("replayButton").hidden = on || !(mode === "studio" ? studio.run : results);
}
function stopQueue() {
  queueToken += 1;
  if (play) finishPlay();
  playing(false);
}

// Emoji particles (hearts, flames) and confetti.
function sceneXY(el, fx = .5, fy = .3) {
  const a = el.getBoundingClientRect(), b = $("scene").getBoundingClientRect();
  return [a.left - b.left + a.width * fx, a.top - b.top + a.height * fy];
}
function puff(icon, n, from = null) {
  if (CALM) return;
  const [x, y] = from || (() => {
    const r = cakeCanvas.getBoundingClientRect(), b = $("scene").getBoundingClientRect();
    return [r.left - b.left + r.width / 2, r.top - b.top + r.height * .35];
  })();
  for (let i = 0; i < n; i++) {
    particles.push({x: x + (Math.random() - .5) * 60, y: y + (Math.random() - .5) * 30,
      vx: (Math.random() - .5) * .12, vy: -.06 - Math.random() * .08, life: 1, icon,
      size: 18 + Math.random() * 16, spin: (Math.random() - .5) * .004, rot: 0});
  }
}
function throwConfetti(n = 140) {
  if (CALM) return;
  const r = $("scene").getBoundingClientRect();
  const colours = ["#ff6f9f", "#ffd447", "#6fd3b5", "#8fb8ff", "#c8a6ff", "#ff9b54"];
  for (let i = 0; i < n; i++) {
    confetti.push({x: r.width * (.2 + Math.random() * .6), y: r.height * .45, vx: (Math.random() - .5) * .9,
      vy: -.5 - Math.random() * .7, life: 1, c: colours[i % colours.length], w: 5 + Math.random() * 5, rot: Math.random() * 6, vr: (Math.random() - .5) * .3});
  }
}
function drawFx(dt) {
  const {ctx, w, h} = fitCanvas(fxCanvas);
  ctx.clearRect(0, 0, w, h);
  particles = particles.filter(p => (p.life -= dt / 1600) > 0);
  for (const p of particles) {
    p.x += p.vx * dt; p.y += p.vy * dt; p.rot += p.spin * dt;
    ctx.save(); ctx.globalAlpha = Math.min(1, p.life * 1.6);
    ctx.translate(p.x, p.y); ctx.rotate(p.rot);
    ctx.font = `${p.size}px "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", sans-serif`;
    ctx.textAlign = "center"; ctx.fillStyle = "#000"; ctx.fillText(p.icon, 0, 0);
    ctx.restore();
  }
  confetti = confetti.filter(p => (p.life -= dt / 2600) > 0 && p.y < h + 20);
  for (const p of confetti) {
    p.vy += .0016 * dt; p.x += p.vx * dt * .5; p.y += p.vy * dt * .5; p.rot += p.vr;
    ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot);
    ctx.fillStyle = p.c; ctx.globalAlpha = Math.min(1, p.life * 2);
    ctx.fillRect(-p.w / 2, -p.w / 4, p.w, p.w / 2);
    ctx.restore();
  }
}

// ---- Baking ---------------------------------------------------------------------------------------
async function bake() {
  if (busy || !me) return;
  if (mode === "studio") return bakeStudio(false);
  busy = true;
  SFX.wake(); SFX.play("whoosh");
  saveCode(); hideBanner(); closeCelebrate(); stopQueue();
  $("hintButton").classList.remove("nudge");
  $("bakeButton").disabled = true; $("bakeButton").textContent = "Baking…";
  const key = view.key;
  try {
    const data = await post("/cake/run", {id: me, level: key, code: $("code").value});
    if (data.error === "join") { forget(); return; }
    if (data.error) { showBanner("error", data.error); return; }
    if (!view || view.key !== key) return;
    results = data.runs; rewards = data.rewards; served = 0;
    view.stars = rewards.best;
    useState(data.state);
    $("totalStars").textContent = rewards.total_stars - rewards.new_stars;
    renderGoals();
    markError(results.find(r => r.error) || results[0]);
    showScene();
    playQueue();
  } catch (_) {
    showBanner("error", "The shop isn't answering. Try again in a moment, or tell your teacher.");
  } finally {
    busy = false;
    $("bakeButton").disabled = false; $("bakeButton").textContent = "Bake! ▶";
  }
}
// On narrow screens the shop sits above the kitchen: bring it into view to watch the bake.
function showScene() {
  if (matchMedia("(max-width: 1060px)").matches)
    $("scene").scrollIntoView({block: "nearest", behavior: CALM ? "auto" : "smooth"});
}
function markError(r) {
  errorLine = r && r.line || 0;
  errorCount = Math.max(1, $("code").value.split("\n").length);
  updateEditor();
}
// Every customer in turn: their cake bakes, they react. The first one is shown
// at full speed, the rest quicker; clicking a customer or Skip jumps ahead.
async function playQueue() {
  const token = ++queueToken;
  $("skipButton").hidden = false;
  // A code error stops every customer's cake the same way: show it once.
  const count = results.every(r => r.error) ? 1 : results.length;
  for (let i = 0; i < count; i++) {
    if (token !== queueToken) return;
    showCustomer(i, {enter: i > 0});
    shown = {tiers: [CakeArt.newTier()], fit: results[i].cake};
    if (i > 0) await wait(350);
    if (token !== queueToken) return;
    await startPlay(results[i], i === 0 ? 1 : 2.4);
    if (token !== queueToken) return;
    react(i);
    await wait(i < count - 1 ? 1300 : 900);
  }
  if (token === queueToken) { playing(false); endOfBake(); }
}
// Some customers show their joy their own way.
const DELIGHT = {"🐱": "🐟", "🦄": "🌈", "🐧": "❄️", "🦓": "⭐", "👻": "👻", "🐸": "💚", "🤖": "⚙️",
  "👽": "🛸", "🧜": "🫧", "🧚": "✨", "🐶": "🦴", "🐼": "🎋", "🦖": "🦴", "🦔": "🍂", "🦉": "🪶",
  "🦊": "🍊", "🐭": "🧀", "👸": "👑", "👰": "💐", "👵": "🌷"};
function react(i) {
  const r = results[i];
  served = Math.max(served, i + 1);
  showCustomer(i, {reacted: true});
  restartClass($("face"), r.happy ? "happy" : "sad");
  const at = sceneXY($("face"), .5, .2);
  if (r.happy) {
    SFX.play("happy");
    if (r.face === "🐉") { SFX.play("fire"); puff("🔥", 14, [at[0] + 80, at[1]]); }
    const extra = Object.entries(DELIGHT).find(([face]) => r.face.startsWith(face));
    puff(extra ? extra[1] : "💖", extra ? 5 : 6, at);
    if (extra) puff("💖", 3, at);
  } else {
    SFX.play(r.error ? "error" : "sad");
    puff(r.error ? "💨" : "❓", 2, at);
  }
  announce(`${r.name}: ${r.reply}`);
}
function skipToEnd() {
  if (mode === "studio") { stopQueue(); return; }
  stopQueue();
  if (!results) return;
  const first = results.findIndex(r => !r.happy);
  const i = first >= 0 ? first : results.length - 1;
  showCustomer(i, {reacted: true});
  shown = {tiers: results[i].cake, fit: results[i].cake};
  endOfBake();
}
function endOfBake() {
  served = results.length;
  renderQueue();
  const happy = results.filter(r => r.happy).length;
  const won = rewards.stars[0];
  $("totalStars").textContent = rewards.total_stars;
  if (rewards.new_stars) restartClass($("starsButton"), "bump");
  // A Bake-Off run that pleases some but earns nothing new is a nudge, not a party.
  const partial = view.bake_off && happy < results.length && !rewards.new_stars;
  if (won && !partial) {
    const bad = results.findIndex(r => !r.happy);
    if (bad >= 0) {   // the Bake-Off can earn a star with some customers unhappy
      showCustomer(bad, {reacted: true, enter: true});
      showBanner("", `😕 ${results[bad].name}: “${results[bad].reply}”`);
    }
    celebrate();
  } else {
    const bad = results.findIndex(r => !r.happy);
    const r = results[bad];
    if (results.length > 1) showCustomer(bad, {reacted: true, enter: true});
    if (r.error) {
      showBanner("error", "", misses());
    } else {
      const lead = results.length > 1 ? `${happy} of ${results.length} happy. ` : "";
      showBanner("", `😕 ${lead}${r.name}: “${r.reply}”`, misses());
    }
  }
  showToasts(rewards.badges);
}
function misses() {
  // After a few tries in a row, point at the hint button.
  const stuck = rewards && rewards.misses >= 3 && view.hints.length < view.hint_count;
  $("hintButton").classList.toggle("nudge", !!stuck);
  return stuck ? `<button class="soft" onclick="askHint()">💡 Want a hint?</button>` : "";
}
// A message at the bottom of the output, under the code where the student is looking.
function showBanner(kind, text, extra = "") {
  notice = text || extra ? {kind, text, extra} : null;
  renderNotes();
  if (kind === "error" && text) SFX.play("error");
}
function hideBanner() {
  if (!notice) return;
  notice = null;
  renderNotes();
}

// ---- The celebration ---------------------------------------------------------------------------------
async function celebrate() {
  const st = rewards.stars, best = rewards.best;
  const all = results.length > 1;
  const happy = results.filter(r => r.happy).length;
  const nextKey = nextLevel();
  const nextCh = nextKey && allLevels().find(l => l.key === nextKey).chapter;
  const newChapter = rewards.first && nextCh && nextCh.key !== view.chapter.key;
  $("celTitle").textContent = view.bake_off ? `${happy} of ${results.length} happy customers!`
    : newChapter ? `${view.chapter.icon} ${view.chapter.name}: done!`
    : st.every(Boolean) ? "Perfect bake! 🎉" : all ? "Everyone's happy!" : `${results[0].name} loves it!`;
  const spans = [...$("celStars").children];
  spans.forEach(s => { s.className = ""; });
  $("celGoals").innerHTML = view.goals.map((g, i) =>
    `<li class="${best[i] ? "" : "miss"}"><b>${best[i] ? "★" : "☆"}</b><span>${fmt(g)}</span></li>`).join("");
  const unlocks = rewards.unlocked || [];
  $("celUnlocks").hidden = !unlocks.length;
  const howTo = u => u.kind === "topping" ? ` <code>topping("${esc(u.key)}")</code>`
    : u.kind === "special" ? ` <code>frosting("${esc(u.key)}")</code>` : " (tap ★ to use it)";
  $("celUnlocks").innerHTML = unlocks.length ? "🔓 New in your pantry:<br>" +
    unlocks.map(u => `${esc(u.name)}${howTo(u)}`).join("<br>") : "";
  const next = nextKey;
  const label = newChapter ? `On to ${nextCh.icon} ${esc(nextCh.name)} ▶` : "Next customer ▶";
  $("celButtons").innerHTML = (next ? `<button class="go" onclick="goNext()">${label}</button>` : "") +
    `<button class="soft" onclick="closeCelebrate()">${best.every(Boolean) ? "Stay here" : "Go for more stars"}</button>`;
  $("celebrate").hidden = false;
  // Enter goes on, as in any dialog, and doesn't add a line to the recipe.
  $("celButtons").firstElementChild.focus({preventScroll: true});
  if (st.every(Boolean) || rewards.first) throwConfetti();
  for (let i = 0; i < 3; i++) {
    await wait(260);
    spans[i].classList.add("in");
    if (st[i]) { spans[i].classList.add("got"); SFX.play("star", i); }
    else if (best[i]) spans[i].classList.add("old");
  }
  if (unlocks.length) { await wait(300); SFX.play("unlock"); }
}
function closeCelebrate() {
  const inside = $("celebrate").contains(document.activeElement);
  $("celebrate").hidden = true;
  if (inside) $("code").focus({preventScroll: true});   // back to the recipe for more stars
}
function nextLevel() {
  const list = allLevels(), i = list.findIndex(l => l.key === view.key);
  return list[i + 1] && list[i + 1].open ? list[i + 1].key : null;
}
function goNext() {
  const next = nextLevel();
  closeCelebrate();
  if (next) openLevel(next);
}

// ---- Toasts for badges ------------------------------------------------------------------------------
function showToasts(badges) {
  if (!badges || !badges.length) return;
  const list = badges.length > 2
    ? [{icon: "🏅", name: `${badges.length} new badges!`, how: badges.map(b => b.icon + " " + b.name).join(", ")}]
    : badges;
  list.forEach((b, i) => setTimeout(() => {
    const t = document.createElement("div");
    t.className = "toast";
    t.innerHTML = `<span>${b.icon}</span><div>${esc(b.name)}<small>${esc(b.how)}</small></div>`;
    $("toasts").append(t);
    SFX.play("unlock");
    setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), 450); }, 4200);
  }, 1400 + i * 700));
}

// ---- The editor -------------------------------------------------------------------------------------
const KEYWORDS = new Set(["def", "if", "elif", "else", "for", "in", "while", "return", "and", "or", "not",
  "True", "False", "None", "break", "continue", "pass", "global", "is"]);
const KITCHEN = new Set(["layer", "frosting", "drip", "sprinkles", "swirl", "topping", "candle", "write", "tier"]);
const BUILTINS = new Set(["print", "len", "str", "int", "range", "choice", "randint", "max", "min", "abs", "order"]);
function highlight(code) {
  const re = /(#.*$)|(f?"(?:[^"\\\n]|\\.)*"?|f?'(?:[^'\\\n]|\\.)*'?)|(\b\d+\b)|([A-Za-z_]\w*)/gm;
  let out = "", at = 0, m;
  while ((m = re.exec(code))) {
    out += esc(code.slice(at, m.index));
    const [t] = m;
    if (m[1]) out += `<span class="hl-c">${esc(t)}</span>`;
    else if (m[2]) out += `<span class="hl-s">${esc(t)}</span>`;
    else if (m[3]) out += `<span class="hl-n">${t}</span>`;
    else if (KEYWORDS.has(t)) out += `<span class="hl-k">${t}</span>`;
    else if (KITCHEN.has(t)) out += `<span class="hl-f">${t}</span>`;
    else if (BUILTINS.has(t)) out += `<span class="hl-b">${t}</span>`;
    else out += esc(t);
    at = re.lastIndex;
  }
  return out + esc(code.slice(at));
}
function renderGutter() {
  const count = Math.max(1, $("code").value.split("\n").length);
  $("lines").innerHTML = Array.from({length: count}, (_, i) =>
    i + 1 === runLine ? `<span class="run" title="Running this line">▸${i + 1}</span>`
    : i + 1 === errorLine ? `<span class="err" title="The problem is on this line">▸${i + 1}</span>` : i + 1).join("\n");
  $("lines").scrollTop = $("code").scrollTop;
}
// While the cake bakes, the line that made each step lights up, so you can
// watch the program run: round a loop, into an if, through a def.
let runLine = 0;
function setRunLine(n) {
  if ((n || 0) === runLine) return;
  runLine = n || 0;
  const t = $("code");
  if (runLine) {
    const lh = parseFloat(getComputedStyle(t).lineHeight), top = 10 + (runLine - 1) * lh;
    if (top < t.scrollTop || top + lh > t.scrollTop + t.clientHeight) t.scrollTop = Math.max(0, top - t.clientHeight / 3);
  }
  renderGutter();
  syncScroll();
}
function placeRunLine() {
  const band = $("runline"), t = $("code");
  band.hidden = !runLine;
  if (!runLine) return;
  const lh = parseFloat(getComputedStyle(t).lineHeight);
  band.style.top = `${10 + (runLine - 1) * lh - t.scrollTop}px`;
  band.style.height = `${lh}px`;
}
function updateEditor() {
  const code = $("code").value;
  const count = Math.max(1, code.split("\n").length);
  if (count !== errorCount) errorLine = 0;
  renderGutter();
  $("hl").innerHTML = highlight(code) + "\n ";
  const lines = code.split("\n").filter(l => l.trim() && !l.trim().startsWith("#")).length;
  const goal = mode === "orders" && view && view.goals.find(g => g.startsWith("✂️"));
  const target = goal ? Number(/\d+/.exec(goal)[0]) : null;
  $("lineCount").textContent = `${lines} line${lines === 1 ? "" : "s"}${target ? ` · ✂️ ${target}` : ""}`;
  $("lineCount").className = "ed-meta" + (target && lines && lines <= target ? " fits" : "");
  syncScroll();
  saveCode();
}
function syncScroll() {
  const t = $("code");
  $("hl").scrollTop = t.scrollTop; $("hl").scrollLeft = t.scrollLeft;
  $("lines").scrollTop = t.scrollTop;
  placeRunLine();
}
// Every change the page makes to the code goes through the browser's own
// typing, so Ctrl+Z still undoes it (setRangeText and .value skip the history).
function replaceText(start, end, text) {
  const t = $("code");
  t.focus(); t.setSelectionRange(start, end);
  // (Inserting "" puts the cursor back a line in Chrome, so deleting is a delete.)
  const done = text ? document.execCommand("insertText", false, text)
                    : start === end || document.execCommand("delete");
  if (!done) t.setRangeText(text, start, end, "end");
  updateEditor();
}
// The whole recipe at once (Reset, a Studio idea, a remix), still undoable.
function replaceAll(text) {
  replaceText(0, $("code").value.length, text);
  $("code").setSelectionRange(0, 0);
  $("code").scrollTop = 0;
}
let tabOut = false;   // after Escape, Tab leaves the editor instead of indenting
function editorKey(event) {
  const t = event.target, start = t.selectionStart, end = t.selectionEnd;
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) { event.preventDefault(); bake(); return; }
  if (event.key === "Escape") { tabOut = true; return; }
  if (event.key === "Tab" && tabOut) { tabOut = false; return; }
  tabOut = false;
  if (event.key === "Tab") {
    event.preventDefault();
    replaceText(start, end, "    ");
  } else if (event.key === "Enter") {
    event.preventDefault();
    const lineStart = t.value.lastIndexOf("\n", start - 1) + 1;
    const line = t.value.slice(lineStart, start);
    let indent = (line.match(/^\s*/) || [""])[0];
    if (line.trimEnd().endsWith(":")) indent += "    ";
    replaceText(start, end, "\n" + indent);
  } else if (event.key === "Backspace" && start === end) {
    // In the spaces at the start of a line, go back a whole level.
    const before = t.value.slice(t.value.lastIndexOf("\n", start - 1) + 1, start);
    if (!before || /[^ ]/.test(before)) return;
    event.preventDefault();
    const back = (before.length - 1) % 4 + 1;
    replaceText(start - back, start, "");
  }
}
// Put a command on its own line (pushed in under a line ending in : ), with the
// word in its quotes selected, so typing, or clicking an ingredient, replaces it.
function insertLine(snippet) {
  const t = $("code");
  const pos = t.selectionStart;
  const lineStart = t.value.lastIndexOf("\n", pos - 1) + 1;
  let lineEnd = t.value.indexOf("\n", pos); if (lineEnd < 0) lineEnd = t.value.length;
  const line = t.value.slice(lineStart, lineEnd);
  let indent = (line.match(/^\s*/) || [""])[0];
  if (line.trimEnd().endsWith(":")) indent += "    ";
  const body = snippet.split("\n").join("\n" + indent);
  let at;
  if (!line.trim()) {
    replaceText(lineStart, lineEnd, indent + body);
    at = lineStart + indent.length;
  } else {
    replaceText(lineEnd, lineEnd, "\n" + indent + body);
    at = lineEnd + 1 + indent.length;
  }
  const q = /"([^"]*)"/.exec(body);
  if (q && !body.includes("\n")) {
    t.selectionStart = at + q.index + 1;
    t.selectionEnd = at + q.index + 1 + q[1].length;
  }
  t.focus(); updateEditor();
}
// Put a value at the cursor. A quoted word clicked while the cursor is in (or
// on a line with just one) "..." replaces what's in the quotes instead.
function insertHere(text) {
  const t = $("code");
  const s = t.selectionStart, e = t.selectionEnd;
  if (text.startsWith('"')) {
    const word = text.slice(1, -1);
    const lineStart = t.value.lastIndexOf("\n", s - 1) + 1;
    let lineEnd = t.value.indexOf("\n", s); if (lineEnd < 0) lineEnd = t.value.length;
    const line = t.value.slice(lineStart, lineEnd);
    const quoted = [...line.matchAll(/"([^"]*)"/g)];
    const inside = quoted.find(m => lineStart + m.index < s && s <= lineStart + m.index + m[0].length - 1 + (e > s ? 1 : 0));
    const target = inside || (quoted.length === 1 && !/^\s*$/.test(line) ? quoted[0] : null);
    if (target) {
      const from = lineStart + target.index + 1;
      replaceText(from, from + target[1].length, word);
      t.setSelectionRange(from, from + word.length);
      return;
    }
  }
  replaceText(s, e, text);
}
const SNIPPETS = {
  layer: 'layer("vanilla")', frosting: 'frosting("pink")', drip: 'drip("chocolate")',
  sprinkles: "sprinkles()", swirl: 'swirl("white")', topping: 'topping("cherry")',
  candle: "candle()", write: 'write("Hello")', tier: "tier()",
};
function renderBook(commands, fresh = []) {
  const chapter = mode === "studio" || view.bake_off ? 9 : Number(view.chapter.key);
  const py = [["print()", 'print("hello")', "line", 1]];
  if (mode !== "studio") py.push(['order["…"]', 'order["name"]', "here", 1]);
  if (chapter >= 2) py.push(["for loop", "for i in range(3):\n    ", "line", 2]);
  if (chapter >= 3) py.push(["if / else", 'if order["sprinkles"]:\n    \nelse:\n    ', "line", 3]);
  if (chapter >= 4) py.push(["[list]", 'flavours = ["lemon", "lime"]', "line", 4]);
  if (chapter >= 5) py.push(["def", "def my_recipe():\n    ", "line", 5]);
  if (mode === "studio") py.push(["choice()", 'choice(["pink", "blue"])', "here", 9], ["randint()", "randint(1, 6)", "here", 9]);
  $("book").innerHTML = commands.map(c =>
    `<button class="${fresh.includes(c) && chapter > 1 ? "new" : ""}" data-line="${esc(SNIPPETS[c])}" title="Add ${esc(SNIPPETS[c])}">${esc(SNIPPETS[c])}</button>`).join("") +
    py.map(([label, code, how, ch]) =>
      `<button class="py${mode !== "studio" && ch === chapter && ch > 1 ? " new" : ""}" data-${how}="${esc(code)}" title="Add ${esc(label)}">${esc(label)}</button>`).join("");
}
$("book").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  SFX.play("click");
  if (b.dataset.line !== undefined) insertLine(b.dataset.line);
  else insertHere(b.dataset.here);
  // Show the ingredients that fit the command just added, ready to click.
  const cmd = (/^(\w+)\(/.exec(b.dataset.line || "") || [])[1];
  const tab = cmd === "layer" ? "flavours" : cmd === "topping" ? "toppings"
    : ["frosting", "drip", "sprinkles", "swirl", "candle", "write"].includes(cmd) ? "colours" : null;
  if (tab && tab !== pantryTab) { pantryTab = tab; renderChips(); }
});
function renderChips() {
  const pal = state.palette, open = new Set(state.pantry.filter(u => u.open).map(u => u.kind + ":" + u.key));
  const need = {};
  state.pantry.forEach(u => { need[u.kind + ":" + u.key] = u; });
  const lock = key => need[key] && !open.has(key) ? need[key] : null;
  const tip = u => u ? ` (unlocks at ${u.stars ? u.stars + " stars" : "class " + u.class + " stars"})` : "";
  let html = "";
  if (pantryTab === "flavours") {
    html = Object.entries(pal.flavours).map(([k, c]) => `<button class="chip" data-v="${esc(k)}" title="layer(&quot;${esc(k)}&quot;)"><i style="background:${c}"></i>${esc(k)}</button>`).join("");
  } else if (pantryTab === "colours") {
    html = Object.entries(pal.colours).map(([k, c]) => `<button class="chip" data-v="${esc(k)}"><i style="background:${c}"></i>${esc(k)}</button>`).join("") +
      pal.specials.map(k => { const u = lock("special:" + k); return `<button class="chip${u ? " locked" : ""}" data-v="${esc(k)}" title="${esc(k)} frosting${tip(u)}"><i style="background:${{glitter: "linear-gradient(135deg,#f6d7e8,#fff4d6,#e3dcfb,#d6f5ec)", galaxy: "linear-gradient(135deg,#1c1440,#4b2a8a,#2a4d9b)", rainbow: "linear-gradient(90deg,#ff5f6d,#ffd93d,#6bd66b,#5cb8ff,#a77bff)", gold: "linear-gradient(135deg,#9c6f12,#ffe08a,#d9a52b)"}[k]}"></i>${u ? "🔒 " : "✨ "}${esc(k)}</button>`; }).join("");
  } else {
    html = Object.entries(pal.toppings).map(([k, icon]) => { const u = lock("topping:" + k); return `<button class="chip${u ? " locked" : ""}" data-v="${esc(k)}" title="topping(&quot;${esc(k)}&quot;)${tip(u)}"><i>${u ? "🔒" : icon}</i>${esc(k)}</button>`; }).join("");
  }
  $("chips").innerHTML = html;
  [...$("pantryTabs").querySelectorAll("button")].forEach(b => b.classList.toggle("on", b.dataset.p === pantryTab));
}
// The commands and ingredients fold away; each browser remembers if they're open.
$("pantry").open = recall("cakePantryOpen") === "1";
$("pantry").addEventListener("toggle", () => store("cakePantryOpen", $("pantry").open ? "1" : "0"));
$("pantryTabs").addEventListener("click", e => {
  const b = e.target.closest("button[data-p]");
  if (b) { pantryTab = b.dataset.p; renderChips(); }
});
$("chips").addEventListener("click", e => {
  const b = e.target.closest("button[data-v]");
  if (b) { SFX.play("click"); insertHere(`"${b.dataset.v}"`); }
});

// ---- Tips and hints ------------------------------------------------------------------------------------
function renderTip(tip, open, tag = "New") {
  $("tip").hidden = !tip;
  if (!tip) return;
  document.querySelector("#tip .new-tag").textContent = tag;
  $("tipTitle").textContent = tip.title;
  $("tipBody").innerHTML = `<p>${fmt(tip.text)}</p>` + (tip.code ? `<pre>${highlight(tip.code)}</pre>` : "");
  $("tip").open = open;
}
function renderHints() {
  if (mode === "studio") { $("hints").innerHTML = ""; return; }
  $("hints").innerHTML = view.hints.map((h, i) => {
    const isCode = h.includes("\n") || /^[a-z_]+\(|^for |^if |^def /.test(h);
    return `<div class="hint"><b>💡 Hint ${i + 1}</b>${isCode ? `<pre>${highlight(h)}</pre>` : ` ${fmt(h)}`}</div>`;
  }).join("");
  const left = view.hint_count - view.hints.length;
  $("hintButton").textContent = left ? `💡 Hint (${view.hints.length + 1} of ${view.hint_count})` : "💡 No more hints";
  $("hintButton").disabled = !left;
}
async function askHint() {
  if (!view || view.hints.length >= view.hint_count) return;
  const data = await post("/cake/hint", {id: me, level: view.key});
  if (data.hints) { view.hints = data.hints; renderHints(); SFX.play("click"); }
  hideBanner();
  $("hints").lastElementChild && $("hints").lastElementChild.scrollIntoView({block: "nearest", behavior: "smooth"});
}
let resetArmed = null;
function resetCode() {
  if (!resetArmed) {
    $("resetButton").textContent = "Sure? ↺";
    resetArmed = setTimeout(() => { resetArmed = null; $("resetButton").textContent = "↺"; }, 3000);
    return;
  }
  clearTimeout(resetArmed); resetArmed = null; $("resetButton").textContent = "↺";
  errorLine = 0;
  replaceAll(mode === "studio" ? state.studio : view.starter);   // Ctrl+Z brings it back
}

// ---- The Studio ------------------------------------------------------------------------------------------
// quiet: put the cake on the counter at once, with no fuss (coming back to the Studio).
async function bakeStudio(fresh, quiet = false) {
  if (busy) return;
  busy = true;
  if (!quiet) { SFX.wake(); SFX.play("whoosh"); }
  saveCode(); hideBanner(); stopQueue();
  $("bakeButton").disabled = true; $("bakeButton").textContent = "Baking…";
  try {
    const data = await post("/cake/studio", {id: me, code: $("code").value, new_seed: true});
    if (data.error === "join") { forget(); return; }
    studio = {run: data, seed: data.seed};
    markError(data);
    renderNotes();
    if (quiet) {
      shown = {tiers: data.cake, fit: data.cake};
      playing(false);
      $("surpriseButton").hidden = !/\b(choice|randint)\s*\(/.test($("code").value);
      return;
    }
    shown = {tiers: [CakeArt.newTier()], fit: data.cake};
    showScene();
    const token = ++queueToken;
    await startPlay(data, 1);
    if (token !== queueToken) return;
    playing(false);
    if (data.error) {
      showBanner("error", `🐛 ${data.error}`);
      $("bubble").textContent = "Oops! Something went wrong in the kitchen."; $("bubble").className = "bubble pop sad";
      restartClass($("face"), "sad");
    } else {
      SFX.play("happy");
      puff("✨", 6);
      $("bubble").textContent = ["Ooh, beautiful!", "Now THAT is a cake.", "Put it in the window!", "Masterpiece!", "Yum yum yum!"][Math.floor(Math.random() * 5)];
      $("bubble").className = "bubble pop happy";
      restartClass($("face"), "happy");
    }
    $("surpriseButton").hidden = !/\b(choice|randint)\s*\(/.test($("code").value);
  } catch (_) {
    showBanner("error", "The shop isn't answering. Try again in a moment, or tell your teacher.");
  } finally {
    busy = false;
    $("bakeButton").disabled = false; $("bakeButton").textContent = "Bake! ▶";
  }
}
async function putInWindow() {
  const title = $("cakeTitle").value.trim();
  if (!title) { $("cakeTitle").focus(); showBanner("", "Give your cake a name first ✍️"); return; }
  if (!studio.run || studio.run.error) { showBanner("", "Bake your cake first (without errors), then put it in the window."); return; }
  $("windowButton").disabled = true;
  try {
    const data = await post("/cake/window", {id: me, code: $("code").value, seed: studio.seed, title});
    if (data.error) { showBanner("error", data.error); return; }
    useState(data.state);
    renderStudioCard();
    SFX.play("unlock");
    throwConfetti(90);
    showBanner("", `🪟 “${title}” is in the shop window!`, `<button class="soft" onclick="setMode('window')">Go and look</button>`);
    showToasts(data.badges);
  } finally {
    $("windowButton").disabled = false;
  }
}
function renderStudioCard() {
  const w = state.window;
  $("nowIn").innerHTML = w ? `In the window now: <b>${esc(w.title)}</b> · ❤️ ${w.hearts}${w.hidden ? " · <i>hidden by your teacher</i>" : ""}` : "Nothing in the window yet.";
}

let undoCode = null;
$("tipBody").addEventListener("click", e => {
  const b = e.target.closest("button[data-idea]");
  if (!b) return;
  const idea = state.palette.ideas[Number(b.dataset.idea)];
  undoCode = $("code").value;
  errorLine = 0;
  replaceAll(idea.code);
  SFX.play("click");
  showBanner("", `Loaded “${idea.name}”. Bake it, then change it to make it yours!`,
    `<button class="soft" onclick="undoIdea()">↩ Undo</button>`);
});
function undoIdea() {
  if (undoCode === null) return;
  replaceAll(undoCode);
  undoCode = null;
  hideBanner();
}

// A picture of the cake to keep.
function savePhoto(tiers, look, title, by) {
  const a = document.createElement("a");
  a.href = CakeArt.photo(tiers, look, title, by);
  a.download = (title || "my cake").replace(/[^\w -]+/g, "").trim().replace(/\s+/g, "-").toLowerCase() + ".png";
  document.body.append(a); a.click(); a.remove();
  SFX.play("click");
}
$("photoButton").addEventListener("click", () => {
  if (!studio.run || studio.run.error || !studio.run.cake[0].layers.length) {
    showBanner("", "Bake a cake first, then take its photo 📸"); return;
  }
  const title = $("cakeTitle").value.trim() || "My cake";
  savePhoto(studio.run.cake, state.look, title, `by ${state.you.name} · ${$("shopName").textContent}`);
});
$("cmPhoto").addEventListener("click", () => {
  if (detail) savePhoto(detail.cake, detail.look, detail.title, `by ${detail.baker} · ${detail.shop}`);
});

// ---- Switching between Orders, Studio and the Shop Window --------------------------------------------
async function setMode(next, level = null) {
  if (next === mode) return;
  saveCode();
  stopQueue(); hideBanner(); closeCelebrate();
  mode = next;
  [...document.querySelectorAll(".tabs button")].forEach(b => b.classList.toggle("on", b.dataset.mode === mode));
  $("route").hidden = mode !== "orders";
  $("main").hidden = mode === "window";
  $("windowView").hidden = mode !== "window";
  clearInterval(windowTimer);
  if (mode === "window") {
    await loadWindow();
    windowTimer = setInterval(loadWindow, 15000);
    return;
  }
  if (mode === "studio") {
    $("levelName").textContent = "🎨 The Studio";
    $("goals").innerHTML = `<span class="goal"><i>✨</i>No orders, no rules: just bake something lovely</span>`;
    renderRules();
    renderBook(["layer", "frosting", "drip", "sprinkles", "swirl", "topping", "candle", "write", "tier"]);
    renderChips();
    renderHints();
    $("tip").hidden = false;
    renderTip({title: "Start from one of these", text: "Then make it your own: change the colours, add a loop, let `choice()` pick a surprise.",
      code: ""}, true, "Ideas");
    $("tipBody").insertAdjacentHTML("beforeend", `<div class="ideas">${state.palette.ideas.map((idea, i) =>
      `<button data-idea="${i}">${esc(idea.name)}</button>`).join("")}</div>`);
    $("hintButton").hidden = true;
    $("ticket").hidden = true; $("queue").hidden = true;
    $("studioCard").hidden = false;
    renderStudioCard();
    const saved = recall(codeKey("studio"));
    $("code").value = saved !== null ? saved : state.studio;
    $("code").scrollTop = 0;
    studio = {run: null, seed: 0};
    shown = {tiers: [CakeArt.newTier()], fit: null};
    errorLine = 0;
    showCustomer(0, {enter: true});
    updateEditor();
    if ($("code").value.trim()) await bakeStudio(false, true);
  } else {
    await openLevel(level || view.key, true);
  }
}
document.querySelector(".tabs").addEventListener("click", e => {
  const b = e.target.closest("button[data-mode]");
  if (b && !busy) { SFX.play("click"); setMode(b.dataset.mode); }
});

// ---- The Shop Window ------------------------------------------------------------------------------------
async function loadWindow() {
  let data;
  try { data = await get(`/cake/window?id=${encodeURIComponent(me)}`); } catch (_) { return; }
  const same = windowData && JSON.stringify(data) === JSON.stringify(windowData);
  windowData = data;
  if (same) return;
  $("theme").hidden = !data.theme;
  $("theme").textContent = data.theme ? `This week's theme: ${data.theme}` : "";
  if (!data.cakes.length) {
    $("gallery").innerHTML = `<div class="empty"><div style="font-size:44px">🪟</div><b>The window is empty!</b><br>Bake something in the Studio and be the first to put a cake in it.<br><button class="go" style="margin-top:16px" onclick="setMode('studio')">🎨 Bake one in the Studio</button></div>`;
    return;
  }
  $("gallery").innerHTML = data.cakes.map((c, i) => `
    <article class="card${c.mine ? " mine" : ""}">
      <button class="pic wp-${esc(c.look.wallpaper)}" data-i="${i}" aria-label="Look at ${esc(c.title)}"><canvas></canvas></button>
      <div class="info">
        <div><h3>${esc(c.title)}</h3><small>${c.mine ? "Your cake" : "by " + esc(c.baker)} · ${esc(c.shop)}</small></div>
        <button class="heart${c.hearted || c.mine ? " on" : ""}" data-heart="${i}" ${c.mine ? "disabled title='Hearts from your classmates'" : ""}><span class="hi">${c.hearted || c.mine ? "❤️" : "🤍"}</span> ${c.hearts}</button>
      </div>
    </article>`).join("");
  requestAnimationFrame(() => {
    [...$("gallery").querySelectorAll(".card")].forEach((card, i) => {
      CakeArt.still(card.querySelector("canvas"), data.cakes[i].cake, data.cakes[i].look.stand);
    });
  });
}
async function heart(i) {
  const c = windowData.cakes[i];
  const data = await post("/cake/heart", {id: me, owner: c.owner});
  if (data.error) return;
  c.hearted = data.hearted; c.hearts = data.hearts;
  if (data.hearted) SFX.play("heart");
  windowData = null;
  await loadWindow();
  if (detail && detail.owner === c.owner) openDetail(i);
  showToasts(data.badges);
}
$("gallery").addEventListener("click", e => {
  const h = e.target.closest("button[data-heart]");
  if (h) { heart(Number(h.dataset.heart)); return; }
  const p = e.target.closest("button[data-i]");
  if (p) openDetail(Number(p.dataset.i));
});
function openDetail(i) {
  const c = windowData.cakes[i];
  detail = {...c, i};
  $("cmTitle").textContent = c.title;
  $("cmBy").textContent = `${c.mine ? "Your cake" : "Baked by " + c.baker} at ${c.shop} · ❤️ ${c.hearts}`;
  $("cmPic").className = "pic wp-" + c.look.wallpaper;
  $("cmCode").innerHTML = highlight(c.code);
  $("cmHeart").hidden = c.mine;
  $("cmHeart").className = "heart" + (c.hearted ? " on" : "");
  $("cmHeart").innerHTML = `<span class="hi">${c.hearted ? "❤️" : "🤍"}</span> ${c.hearted ? "You love it" : "Heart it"}`;
  $("cakeModal").hidden = false;
}
function drawDetail(now) {
  const c = $("cmCanvas");
  if ($("cakeModal").hidden) { detail = null; return; }
  const {ctx, w, h} = fitCanvas(c);
  ctx.clearRect(0, 0, w, h);
  CakeArt.draw(ctx, w, h, {tiers: detail.cake, stand: detail.look.stand, now: CALM ? 1000 : now, floor: h * .86});
}
$("cmHeart").addEventListener("click", () => detail && heart(detail.i));
$("cakeClose").addEventListener("click", () => { $("cakeModal").hidden = true; });
$("cmRemix").addEventListener("click", async () => {
  const code = detail.code, title = detail.title, who = detail.mine ? "your" : detail.baker + "'s";
  $("cakeModal").hidden = true;
  await setMode("studio");
  replaceAll(`# Remixed from ${who} “${title}”. Make it your own!\n` + code.replace(/^# Remixed from .*\n/, ""));
  await bakeStudio(false);
  showBanner("", `🎨 Remixing ${who} “${title}”. Change something and bake it!`);
});

// ---- The pantry: stars, unlocks, the look of the shop, badges ------------------------------------------
function openPantry() {
  const pm = state.pantry;
  $("pmStars").textContent = `${state.total_stars} of ${state.max_stars}`;
  const next = pm.filter(u => u.stars && !u.open).sort((a, b) => a.stars - b.stars)[0];
  const plural = n => `${n} star${n === 1 ? "" : "s"}`;
  $("pmNext").textContent = next ? `Next unlock: ${next.name} at ${plural(next.stars)} (${next.stars - state.total_stars} to go).` : "You've unlocked everything you can on your own!";
  const look = state.look;
  const openKind = (kind, key) => (kind === "stand" && key === "plate") || (kind === "wallpaper" && key === "strawberry") || pm.some(u => u.kind === kind && u.key === key && u.open);
  const needOf = (kind, key) => { const u = pm.find(x => x.kind === kind && x.key === key); return u ? (u.stars ? `${u.stars} ★` : `class ${u.class} ★`) : ""; };
  $("pmLook").innerHTML =
    state.palette.stands.map(k => { const o = openKind("stand", k); return `<button class="item${look.stand === k ? " on" : ""}${o ? "" : " locked"}" data-look="stand" data-key="${k}" ${o ? "" : "disabled"}><span class="ico">${STAND_ICONS[k] || "🍽️"}</span>${esc(k)} stand<span class="need">${o ? (look.stand === k ? "in use" : "tap to use") : "🔒 " + needOf("stand", k)}</span></button>`; }).join("") +
    state.palette.wallpapers.map(k => { const o = openKind("wallpaper", k); return `<button class="item${look.wallpaper === k ? " on" : ""}${o ? "" : " locked"}" data-look="wallpaper" data-key="${k}" ${o ? "" : "disabled"}><span class="ico"><span class="swatch wp-${k}"></span></span>${esc(k)} wall<span class="need">${o ? (look.wallpaper === k ? "in use" : "tap to use") : "🔒 " + needOf("wallpaper", k)}</span></button>`; }).join("");
  const specialSwatch = {glitter: "✨", galaxy: "🌌", rainbow: "🌈", gold: "🥇"};
  $("pmItems").innerHTML = pm.filter(u => u.kind === "topping" || u.kind === "special").map(u =>
    `<div class="item${u.open ? "" : " locked"}"><span class="ico">${u.kind === "topping" ? state.palette.toppings[u.key] : specialSwatch[u.key]}</span>${esc(u.key[0].toUpperCase() + u.key.slice(1))} ${u.kind === "topping" ? "topping" : "frosting"}<span class="need">${u.open ? "✓ in your pantry" : "🔒 " + (u.stars ? u.stars + " ★" : "class " + u.class + " ★")}</span></div>`).join("");
  const cls = state.class, goal = cls.goals.find(g => g > cls.stars) || cls.goals[cls.goals.length - 1];
  $("pmMeter").style.width = Math.min(100, cls.stars / goal * 100) + "%";
  const classItem = pm.find(u => u.class === goal);
  $("pmClass").textContent = cls.stars >= goal ? `The class has ${cls.stars} stars and has unlocked everything. Amazing!`
    : `The class has ${cls.stars} stars together. At ${goal}, everyone gets the ${classItem ? classItem.name : "next surprise"}!`;
  $("pmBadges").innerHTML = state.badges.map(b =>
    `<div class="badge${b.earned ? "" : " off"}"><span>${b.icon}</span><div><b>${esc(b.name)}</b><small>${esc(b.how)}</small></div></div>`).join("");
  $("pantryModal").hidden = false;
}
$("pmLook").addEventListener("click", async e => {
  const b = e.target.closest("button[data-look]");
  if (!b || b.disabled) return;
  SFX.play("click");
  const data = await post("/cake/look", {id: me, [b.dataset.look]: b.dataset.key});
  if (data.look) { state.look = data.look; applyLook(); openPantry(); }
});
$("starsButton").addEventListener("click", openPantry);
$("pantryClose").addEventListener("click", () => { $("pantryModal").hidden = true; });

// ---- Naming the bakery -------------------------------------------------------------------------------------
function openShopName() {
  const name = state.you.name;
  $("shopInput").value = state.you.shop || `${name}'s Bakery`;
  $("suggest").innerHTML = [`${name}'s Bakery`, ...SHOP_IDEAS].map(s => `<button class="soft">${esc(s)}</button>`).join("");
  $("shopModal").hidden = false;
  setTimeout(() => $("shopInput").select(), 50);
}
async function saveShopName() {
  const name = $("shopInput").value.trim();
  if (!name) { $("shopInput").focus(); return; }
  const data = await post("/cake/shop", {id: me, name});
  if (data.you) useState(data);
  $("shopModal").hidden = true;
  SFX.play("happy");
}
$("suggest").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (b) { $("shopInput").value = b.textContent; SFX.play("click"); }
});
$("shopSave").addEventListener("click", saveShopName);
$("shopInput").addEventListener("keydown", e => { if (e.key === "Enter") saveShopName(); });
$("renameButton").addEventListener("click", openShopName);

// ---- The join screen: a birthday cake with flickering candles ---------------------------------------
let joinArt = null;
function joinScene() {
  $("join").hidden = false;
  $("app").hidden = true;
  CakeArt.setPalette(JOIN_PALETTE);
  const steps = [];
  ["strawberry", "vanilla", "strawberry"].forEach(f => steps.push({do: "layer", arg: f}));
  steps.push({do: "frosting", arg: "pink"}, {do: "drip", arg: "white"}, {do: "sprinkles", arg: "rainbow"});
  for (let i = 0; i < 7; i++) steps.push({do: "candle", arg: "classic"});
  for (let i = 0; i < 10; i++) steps.push({do: "swirl", arg: i % 2 ? "pink" : "white"});
  steps.push({do: "write", arg: "Welcome!"});
  joinArt = {steps, start: performance.now()};
  const loop = now => {
    if (!joinArt) return;
    const c = $("joinCanvas"), {ctx, w, h} = fitCanvas(c);
    ctx.clearRect(0, 0, w, h);
    const t = Math.max(0, now - joinArt.start) / 260;   // a frame can be stamped just before the start
    if (t > joinArt.steps.length + 40) joinArt.start = now;   // bake it again
    const k = Math.min(joinArt.steps.length, Math.floor(t));
    const tiers = CakeArt.replay(joinArt.steps, Math.min(joinArt.steps.length, k + 1));
    const anim = k < joinArt.steps.length ? {do: joinArt.steps[k].do, tier: 0, u: t - k} : null;
    CakeArt.draw(ctx, w, h, {tiers, fit: CakeArt.replay(joinArt.steps, joinArt.steps.length), stand: "pink", anim, now});
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
  $("name").focus();
}
function forget() {
  try { localStorage.removeItem("mazeId"); } catch (_) {}
  location.reload();
}

// ---- Calm mode and bigger text ---------------------------------------------------------------------------
// Calm mode is on when the computer asks for less motion, until the student
// says otherwise. Both ticks are on the welcome card and in the ★ panel.
let CALM = recall("cakeCalm") !== null ? recall("cakeCalm") === "1" : matchMedia("(prefers-reduced-motion: reduce)").matches;
function applyPrefs() {
  const big = recall("cakeBig") === "1";
  document.body.classList.toggle("calm", CALM);
  document.body.classList.toggle("big", big);
  document.querySelectorAll("input[data-pref]").forEach(i => { i.checked = i.dataset.pref === "calm" ? CALM : big; });
}
document.addEventListener("change", e => {
  const i = e.target.closest("input[data-pref]");
  if (!i) return;
  if (i.dataset.pref === "calm") { CALM = i.checked; store("cakeCalm", CALM ? "1" : "0"); particles = []; confetti = []; }
  else store("cakeBig", i.checked ? "1" : "0");
  applyPrefs();
  updateEditor();
});
applyPrefs();

// ---- Wiring ----------------------------------------------------------------------------------------------------
$("joinForm").addEventListener("submit", join);
$("code").addEventListener("input", updateEditor);
$("code").addEventListener("scroll", syncScroll);
$("code").addEventListener("keydown", editorKey);
$("bakeButton").addEventListener("click", bake);
$("surpriseButton").addEventListener("click", () => bakeStudio(true));
$("hintButton").addEventListener("click", askHint);
$("resetButton").addEventListener("click", resetCode);
$("skipButton").addEventListener("click", skipToEnd);
$("replayButton").addEventListener("click", async () => {
  hideBanner(); closeCelebrate();
  stopQueue();
  const token = ++queueToken;
  if (mode === "studio") {
    if (!studio.run) return;
    shown = {tiers: [CakeArt.newTier()], fit: studio.run.cake};
    await startPlay(studio.run);
    if (token === queueToken) playing(false);
    return;
  }
  if (!results) return;
  const i = sel;
  showCustomer(i);
  shown = {tiers: [CakeArt.newTier()], fit: results[i].cake};
  await startPlay(results[i]);
  if (token === queueToken) { playing(false); react(i); }
});
$("windowButton").addEventListener("click", putInWindow);
$("cakeTitle").addEventListener("keydown", e => { if (e.key === "Enter") putInWindow(); });
$("muteButton").addEventListener("click", () => { $("muteButton").textContent = SFX.toggle() ? "🔇" : "🔊"; SFX.wake(); });
$("switchButton").addEventListener("click", forget);
document.addEventListener("keydown", e => {
  if (e.key === "F5" && !$("app").hidden) { e.preventDefault(); bake(); }
  if (e.key === "Escape") {
    if (!$("celebrate").hidden) { closeCelebrate(); return; }
    for (const id of ["cakeModal", "pantryModal", "shopModal"]) if (!$(id).hidden) { $(id).hidden = true; return; }
  }
});
for (const id of ["cakeModal", "pantryModal", "shopModal", "celebrate"]) {
  $(id).addEventListener("click", e => { if (e.target === $(id)) $(id).hidden = true; });
}
resume();
