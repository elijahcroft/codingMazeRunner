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
    crack: () => { tone(140, .14, {type: "square", vol: .3, slide: -70}); tone(900, .06, {type: "square", vol: .12, at: .03}); },
    boom: () => tone(90, .45, {type: "sawtooth", vol: .3, slide: -50}),
    streak: n => chord([660, 880, 1100].map(f => f * Math.pow(1.06, Math.min(n / 5, 8))), .05, {type: "triangle", vol: .4}),
    perfect: () => chord([523, 659, 784, 1047, 1319, 1568], .07, {type: "triangle", vol: .5}),
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
let farmSerial = 0;       // bumped by take(): a buy during a day makes its snapshot newer
let scene = null;         // what the yard shows: the farm, changed square by square as a day plays
let visiting = null;      // a classmate's farm, while the Visit window shows one
const rover = {x: 1, y: 1, px: 1, py: 1, angle: 0};   // on the field, in squares
let play = null;          // the day being played back
let night = null;         // the night passing after it
let busy = false, idleDays = 0, lastInput = performance.now();
let floaters = [], bubble = null, pops = {}, wiggles = {};
let falls = [];           // meteors on their way down: {x, y, t0}, landing at t0 + FALL_MS
const FALL_MS = 700;
let coinsShown = 0, coinsGoal = 0;
let errorLine = null, activeLine = null, sampleHidden = null;
const SPEEDS = [1, 2, 4];
let speed = SPEEDS.includes(Number(recall("farmSpeed"))) ? Number(recall("farmSpeed")) : 1;
const editor = $("code");

function leave() { location.href = "/planet"; }
function showClosed() {
  closeDialogs();
  $("app").hidden = true; $("closed").hidden = false; $("auto").checked = false;
}

// ---- Playing a day back -----------------------------------------------------------------
const WAYS = {east: 0, south: Math.PI / 2, west: Math.PI, north: -Math.PI / 2};
const VEC = {east: [1, 0], south: [0, 1], west: [-1, 0], north: [0, -1]};
function stepMs(n) { return Math.max(34, Math.min(250, 2800 / Math.max(n, 1))) / speed; }
function float(text, color, big, at) {
  if (play && play.skip) return;
  floaters.push({x: at ? at[0] : rover.x, y: at ? at[1] : rover.y, text, color, big, t0: performance.now(), life: big ? 1100 : 800});
}
// A tick that did nothing ends the 🔥 streak of picks.
function wasted(text, color, sound) {
  float(text, color);
  if (!play.skip) SFX.play(sound);
  play.streak = 0;
}
function playDay(out) {
  return new Promise(done => {
    scene.field = clone(out.start);
    Object.assign(rover, {x: 1, y: 1, px: 1, py: 1, angle: 0});
    play = {out, i: 0, t0: performance.now(), step: stepMs(out.frames.length), from: {x: 1, y: 1},
            begun: false, picks: 0, streak: 0, skip: false, done};
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
      if (f.do === "bump" || f.do === "drill" || f.do === "nodrill") rover.angle = WAYS[f.way];
    }
    const u = play.skip ? 1 : (now - play.t0) / play.step;
    if (u < 1) {
      if (f.do === "move") { const e = ease(u); rover.px = play.from.x + (f.x - play.from.x) * e; rover.py = play.from.y + (f.y - play.from.y) * e; }
      if ((f.do === "bump" || f.do === "drill") && !CALM) { const k = Math.sin(u * Math.PI) * .2; rover.px = f.x + VEC[f.way][0] * k; rover.py = f.y + VEC[f.way][1] * k; }
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
    row[f.x - 1] = null; play.picks++; play.streak++;
    coinsGoal += f.pay;
    float(`+${f.pay}`, "#ffd36b", f.gold);
    if (!quiet) SFX.play(f.gold ? "gold" : "pick", play.picks);
    if (play.streak % 5 === 0) {
      const n = play.streak;
      setTimeout(() => float(`🔥 ${n} in a row!`, "#ff9d4d", true), 300);
      if (!quiet) SFX.play("streak", play.streak);
    }
  } else if (f.do === "drill") {
    scene.field[f.at[1] - 1][f.at[0] - 1] = null;
    coinsGoal += f.pay;
    float(f.gem ? `💎 +${f.pay}` : `💥 +${f.pay}`, "#ffd36b", true, f.at);
    if (!quiet) { SFX.play("crack"); if (f.gem) SFX.play("gold"); }
  } else if (f.do === "nodrill") { wasted("no rock there", "#ffb547", "nope");
  } else if (f.do === "plant") {
    row[f.x - 1] = [f.crop, 0, f.gold ? 1 : 0]; pops[`${f.x},${f.y}`] = performance.now();
    if (!quiet) SFX.play("plant");
  } else if (f.do === "dig") {
    row[f.x - 1] = null; float("dug up", "#cfc6ea");
  } else if (f.do === "early") wasted("not ripe yet", "#ffb547", "nope");
  else if (f.do === "nothing") wasted("nothing here", "#cfc6ea", "nope");
  else if (f.do === "full") wasted("already planted", "#ffb547", "nope");
  else if (f.do === "bump") wasted(f.rock ? "🪨 rock!" : "fence!", "#ff9d8f", "bump");
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
  falls = falls.filter(f => now < f.t0 + FALL_MS * 1.5);
  const moving = play || night || floaters.length || bubble || falls.length;
  if (!moving && ++lazy % 3) return;
  if (!$("visit").hidden) {
    if (visiting) visitView = drawYard($("visitYard"), visiting, now, false);
    return;
  }
  yardView = drawYard($("yard"), scene, now, true);
}
let yardView = null, visitView = null;

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
    editor.scrollLeft = 0;
    const h = lineHeight(), top = (n - 1) * h;
    if (top < editor.scrollTop || top + h > editor.scrollTop + editor.clientHeight - 16)
      editor.scrollTop = Math.max(0, top - editor.clientHeight / 2);
  }
  updateEditor();
}
function replaceAll(text) {
  editor.focus(); editor.setSelectionRange(0, editor.value.length);
  if (!document.execCommand("insertText", false, text)) editor.value = text;
  editor.scrollTop = 0; editor.scrollLeft = 0;
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
  if (ac && !$("ac").hidden && acKey(e)) return;
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
    e.preventDefault(); document.execCommand("insertText", false, "\n" + indent);
    t.scrollLeft = 0; return;
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

// ---- Suggestions while typing ------------------------------------------------------------------
// Start a word and the box under the cursor offers the farm words this
// student has met (the same ones as the chips), Python's words, and their own
// defs and variables. Inside plant(" it offers their seeds, inside look(" and
// drill(" the four ways, and after look(...) == " what look() can say.
// Up and down choose, Enter or Tab use one, Escape closes it.
const SAYS = ["ripe", "growing", "empty", "rock", "fence"];
const WAY_HELP = {north: "↑ north", south: "↓ south", east: "→ east", west: "← west"};
// Python words that come with a farm word: [word, help, the farm word they come with]
const PY_EXTRA = [
  ["range", "range(3)  counts 0, 1, 2. Use it like  for i in range(3):", "for"],
  ["in", "for i in range(3):", "for"],
  ["else", "else:  does the lines under it when the  if  wasn't true.", "if"],
  ["elif", "elif empty():  asks again when the  if  wasn't true.", "if"],
  ["not", "not  turns True into False. Like  if not empty():", "if"],
  ["and", "Both must be true. Like  if ripe() and x() > 2:", "if"],
  ["or", "One is enough. Like  if ripe() or empty():", "if"],
  ["print", "print(\"hi\")  makes your rover say it.", "for"],
];
// Typed alone on a line, these come with their shape.
const SHAPES = {for: ["for i in range(", "):"], while: ["while ", ":"], if: ["if ", ":"], elif: ["elif ", ":"], else: ["else:", ""], def: ["def ", "():"]};
const QUOTED = ["plant", "look", "drill"];
let ac = null;   // the open list: {ctx, items, i}

function wordName(w) { return w[0].replace(/\(.*$/, ""); }
function knownWords() {
  const at = farm && farm.job ? farm.job.n - 1 : 99, met = WORDS.filter(w => w[2] <= at), list = [], seen = new Set();
  const add = (name, kind, help) => { if (!seen.has(name)) { seen.add(name); list.push({name, kind, help}); } };
  const v = editor.value;
  for (const m of v.matchAll(/^\s*def\s+([A-Za-z_]\w*)\s*\(/gm)) add(m[1], "own", `Your own command, made with def. ${m[1]}()  runs it.`);
  // One-letter names (like the i in a for loop) would hide if and in.
  for (const m of v.matchAll(/^\s*([A-Za-z_]\w+)\s*[-+*/]?=(?!=)/gm)) add(m[1], "var", "Your variable.");
  for (const m of v.matchAll(/\bfor\s+([A-Za-z_]\w+)\s+in\b/g)) add(m[1], "var", "Your loop's counter.");
  for (const w of met) add(wordName(w), w[3], w[1]);
  const names = new Set(met.map(wordName));
  for (const [name, help, with_] of PY_EXTRA) if (names.has(with_)) add(name, "shape", help);
  return list;
}
// Is the cursor in a note or in words in quotes? (Quotes we fill are handled first.)
function inWords(before) {
  let q = "";
  for (const ch of before) {
    if (q) { if (ch === q) q = ""; }
    else if (ch === '"' || ch === "'") q = ch;
    else if (ch === "#") return true;
  }
  return !!q;
}
function completionContext() {
  const v = editor.value, at = editor.selectionStart;
  if (at !== editor.selectionEnd || /\w/.test(v[at] || "")) return null;
  const lineStart = v.lastIndexOf("\n", at - 1) + 1, before = v.slice(lineStart, at);
  const call = /\b(plant|look|drill)\(\s*(["'])([a-z]*)$/i.exec(before);
  if (call) return {mode: call[1] === "plant" ? "seed" : "way", from: at - call[3].length, word: call[3], quote: call[2]};
  const said = /\b(look\([^)]*\)|crop\(\))\s*[!=]=\s*(["'])([a-z]*)$/i.exec(before);
  if (said) return {mode: said[1].startsWith("crop") ? "seed" : "says", from: at - said[3].length, word: said[3], quote: said[2], said: true};
  if (inWords(before) || /\bdef\s+\w*$/.test(before)) return null;
  const w = /(^|[^\w.])([A-Za-z_]\w*)$/.exec(before);
  if (!w) return null;
  return {mode: "name", from: at - w[2].length, word: w[2], lineStart, before};
}
function complete(open) {
  if (!farm) return closeComplete();
  const ctx = completionContext();
  if (!ctx) return closeComplete();
  let items;
  if (ctx.mode === "seed") {
    items = farm.crops.map(c => ({name: c, kind: "text", help: `${(farm.shop && (farm.shop.crops.find(g => g.key === c) || {}).icon) || "🌱"} Your ${c} seeds.`}));
    if (ctx.said) items.push({name: "none", kind: "text", help: "crop() says \"none\" when nothing is planted there."});
  } else if (ctx.mode === "way") items = Object.keys(WAY_HELP).map(n => ({name: n, kind: "text", help: WAY_HELP[n]}));
  else if (ctx.mode === "says") items = SAYS.map(n => ({name: n, kind: "text", help: `look() says "${n}"`}));
  else {
    // Names open only as a word is typed, and never once it's a whole word,
    // so Enter after it is still a new line.
    if (!open && !ac) return closeComplete();
    items = knownWords();
    if (items.some(c => c.name === ctx.word)) return closeComplete();
  }
  const w = ctx.word.toLowerCase();
  const shown = items.filter(c => c.name.toLowerCase().startsWith(w));
  if (!shown.length || (ctx.mode !== "name" && shown.length === 1 && shown[0].name === ctx.word)) return closeComplete();
  const keep = ac && ac.items[ac.i] && shown.findIndex(c => c.name === ac.items[ac.i].name);
  ac = {ctx, items: shown, i: keep > 0 ? keep : 0};
  drawComplete();
}
const KIND_WORD = {do: "command", ask: "question", shape: "python", text: "", own: "yours", var: "variable"};
function drawComplete() {
  const box = $("ac");
  box.innerHTML = `<div class="ac-list" role="listbox">` + ac.items.map((c, i) =>
    `<div class="ac-item${i === ac.i ? " on" : ""}" role="option" data-i="${i}"${i === ac.i ? ' aria-selected="true"' : ""}>` +
    `<span class="ac-name ${c.kind}">${esc(c.name)}</span><small>${KIND_WORD[c.kind] || ""}</small></div>`).join("") + `</div>` +
    `<div class="ac-help">${codeSpans(ac.items[ac.i].help || "")}<span>Enter or Tab to use it</span></div>`;
  box.hidden = false;
  placeBox(box, ac.ctx.from);
  const on = box.querySelector(".on");
  if (on) on.scrollIntoView({block: "nearest"});
}
function closeComplete() { ac = null; $("ac").hidden = true; }
function charWidth() {
  const cs = getComputedStyle(editor), font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
  if (charWidth.font !== font) {
    const c = document.createElement("canvas").getContext("2d");
    c.font = font; charWidth.font = font; charWidth.w = c.measureText("0000000000").width / 10;
  }
  return charWidth.w;
}
// Under the cursor's line, or over it near the bottom of the box.
function placeBox(box, index) {
  const v = editor.value, row = v.slice(0, index).split("\n").length - 1, col = index - v.lastIndexOf("\n", index - 1) - 1;
  const lh = lineHeight(), wrap = editor.parentElement.getBoundingClientRect(), h = box.offsetHeight, w = box.offsetWidth;
  const x = editor.offsetLeft + 8 + col * charWidth() - editor.scrollLeft, y = 8 + row * lh - editor.scrollTop;
  const under = y + lh + h + 4 <= wrap.height || y - h - 4 < 0;
  box.style.top = (under ? y + lh + 2 : y - h - 2) + "px";
  box.style.left = Math.max(0, Math.min(wrap.width - w - 4, x - 4)) + "px";
}
// Up, down, Enter, Tab and Escape steer the list while it's open.
function acKey(e) {
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    ac.i = (ac.i + (e.key === "ArrowDown" ? 1 : -1) + ac.items.length) % ac.items.length;
    drawComplete(); return true;
  }
  if ((e.key === "Enter" || e.key === "Tab") && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
    e.preventDefault(); acceptComplete(ac.items[ac.i]); return true;
  }
  if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeComplete(); return true; }
  return false;
}
function acceptComplete(item) {
  const ctx = ac.ctx, at = editor.selectionStart, v = editor.value;
  closeComplete();
  const put = (from, text, caret) => {
    editor.setSelectionRange(from, at);
    if (!document.execCommand("insertText", false, text)) editor.setRangeText(text, from, at, "end");
    editor.setSelectionRange(from + caret, from + caret);
  };
  if (ctx.mode !== "name") {
    // The word, then past the closing quote (and bracket) it sits in.
    put(ctx.from, item.name, item.name.length);
    let p = ctx.from + item.name.length;
    if (editor.value[p] === ctx.quote) p++;
    if (!ctx.said && editor.value[p] === ")") p++;
    editor.setSelectionRange(p, p);
    typed();
    return;
  }
  const name = item.name, lineEnd = (v.indexOf("\n", at) + 1 || v.length + 1) - 1;
  const alone = !ctx.before.slice(0, ctx.before.length - ctx.word.length).trim() && !v.slice(at, lineEnd).trim();
  let text = name, caret = name.length;
  if (SHAPES[name] && alone) { const [a, b] = SHAPES[name]; text = a + b; caret = a.length; }
  else if (QUOTED.includes(name) && v[at] !== "(") { text = name + '("")'; caret = name.length + 2; }
  else if (["do", "ask", "own"].includes(item.kind) && v[at] !== "(") text = name + "()", caret = text.length;
  else if (name === "range" && v[at] !== "(") text = "range()", caret = 6;
  else if (name === "print" && v[at] !== "(") text = 'print("")', caret = 7;
  else if (["in", "not", "and", "or", "for", "while", "if", "elif", "def"].includes(name) && v[at] !== " ") text = name + " ", caret = text.length;
  put(ctx.from, text, caret);
  typed();
  complete(false);
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
  ['look("east")', 'Says what\'s on the next square: "ripe", "growing", "empty", "rock" or "fence".', 12, "ask"],
  ["while", 'while look("east") != "fence":  repeats the lines under it while that\'s true.', 12, "shape"],
  ['drill("east")', 'Breaks the rock on the next square east and sells it. Use it like  if look("east") == "rock":', 13, "do"],
  ["dig()", "Clears the square under the rover, so you can plant something else.", 15, "do"],
  ["wait()", "Stays still for one tick.", 15, "do"],
  ["crop()", 'The name of the plant under the rover, like "berry". An empty square is "none".', 15, "ask"],
  ["x()", "How far east the rover is. The first square is 1.", 15, "ask"],
  ["y()", "How far south the rover is. The top row is 1.", 15, "ask"],
  ["width()", "How many squares wide your field is. Try  for i in range(width()):", 15, "ask"],
  ["height()", "How many rows your field has.", 15, "ask"],
  ["battery()", "Ticks of battery left today.", 15, "ask"],
  ["coins()", "How many coins you have.", 15, "ask"],
  ["day()", "Which day it is on your farm.", 15, "ask"],
];
// The words that come after the last job fold away, so the code box keeps its room.
const EXTRA_FROM = 15;
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
  // 🔁 Auto comes with the job that runs the same code again: before it, every job needs new code.
  $("autoLabel").hidden = !!(j && !j.auto);
  if ($("autoLabel").hidden && $("auto").checked) stopAuto();
  if ($("sampleShow")) $("sampleShow").onclick = () => { sampleHidden = null; renderJob(); };
  if ($("orderSkip")) $("orderSkip").onclick = async () => {
    const out = await post("/planet/farm/buy", {id: me, kind: "order"}).catch(() => null);
    if (out && out.farm) take(out.farm);
  };
  renderSample();
}
// A wrapped line looks like two lines to type, so first shrink the text (down to 75%)
// until the longest line fits; it only wraps if it still doesn't.
function fitSample() {
  const pre = $("sampleCode");
  pre.style.fontSize = ""; pre.classList.add("measure");   // measure with no wrapping
  const full = parseFloat(getComputedStyle(pre).fontSize);
  const room = pre.parentElement.clientWidth - 2;
  for (let size = full; size >= full * .75 && pre.offsetWidth > room; size -= .5) pre.style.fontSize = size + "px";
  pre.classList.remove("measure");
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
  fitSample();
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
  const rec = farm.record;
  $("record").hidden = !rec;
  if (rec) $("record").innerHTML = `🏆 <span>Class record </span><b>🪙 ${coinText(rec.coins)}</b> ${esc(rec.name)}`;
  showBattery(farm.battery, farm.battery);
  const goods = [...farm.shop.upgrades, ...farm.shop.crops, ...farm.shop.decor].filter(g => g.can).length;
  $("shopPip").hidden = !goods; $("shopPip").textContent = goods;
  $("shopButton").classList.toggle("can", goods > 0);
  $("muteButton").textContent = SFX.muted ? "🔇" : "🔊";
  $("speedButton").textContent = `${speed}×`;
}
function take(view, keepScene) {
  farmSerial++;
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
    if (errorLine) { const h = lineHeight(); editor.scrollTop = Math.max(0, (errorLine - 3) * h);
      editor.scrollLeft = 0; updateEditor(); }
    SFX.play("error");
    say("bad", out.memory_full ? "🧠 Too many lines" : "🛠 One thing to fix", [codeSpans(out.error), "Nothing is broken, and the day hasn't started. Fix it and run again."]);
    take(out.farm);
    return;
  }
  const before = farm, serial = farmSerial;
  coinsGoal = coinsShown = before.coins;
  $("today").textContent = "";
  await playDay(out);
  if (bubble) await sleep(Math.max(0, Math.min(1200, bubble.until - performance.now())));   // let it finish talking
  $("runButton").textContent = "▶ Run a day";
  showLine(null);
  const quick = !out.frames.length;
  const landed = [];
  await nightfall(() => {
    const was = scene.field;
    // A shop buy during the day has a newer farm than the day's reply.
    const latest = farmSerial === serial ? out.farm : farm;
    take(latest); Object.assign(rover, {x: 1, y: 1, px: 1, py: 1, angle: 0}); pops = {};
    // A rock that wasn't there at the end of the day came down in the night.
    latest.field.forEach((row, y) => row.forEach((cell, x) => {
      if (cell && cell[0] === "rock" && !(was[y] && was[y][x] && was[y][x][0] === "rock")) landed.push({x: x + 1, y: y + 1});
    }));
    if (!CALM) landed.forEach((f, i) => {
      falls.push({...f, t0: performance.now() + i * 220});
      setTimeout(() => SFX.play("boom"), i * 220 + FALL_MS);
    });
  }, quick);
  // What the day came to.
  const got = Object.entries(out.picked).map(([crop, n]) => `${before.icons[crop]}×${n}`)
    .concat(out.drilled ? [`🪨×${out.drilled}`] : []).join("  ");
  const lines = [];
  const picks = Object.values(out.picked).reduce((a, b) => a + b, 0);
  if (out.perfect) lines.push(`<span class="gold">✨ Perfect day! Not one tick wasted: 🪙 +${coinText(out.perfect)}</span>`);
  else if (picks >= 3 && out.wasted && out.wasted <= 3 && !out.error)
    lines.push(`⚡ So close! ${out.wasted} tick${out.wasted > 1 ? "s" : ""} wasted. With none it's a ✨ Perfect day, and pays 50% more.`);
  if (out.gems) lines.push(`<span class="gold">💎 A space gem was inside a rock!</span>`);
  if (out.golden) lines.push(`<span class="gold">✨ ${out.golden} golden! Each one pays 5 times over.</span>`);
  if (out.best) lines.push(`<span class="gold">🏆 Your best day yet!</span>`);
  if (out.error) { errorLine = out.line || null; editor.scrollLeft = 0; updateEditor(); lines.push(`🛠 ${codeSpans(out.error)}`); }
  for (const line of out.stuck ? out.say.slice(0, 1) : out.say) lines.push(codeSpans(line));   // stuck: just the job line
  if (out.stuck) {   // the same code keeps missing the job: stop Auto and point at the code to type
    lines.unshift(`<span class="gold">${codeSpans(out.stuck)}</span>`);
    stopAuto(); sampleHidden = null; renderJob();
    const pane = $("sample"); pane.classList.remove("nudge"); void pane.offsetWidth; pane.classList.add("nudge");
  }
  const total = out.income + out.bonus + out.perfect;
  const extras = [out.bonus && `⭐ ${coinText(out.bonus)} star bonus`, out.perfect && `✨ ${coinText(out.perfect)} perfect`].filter(Boolean);
  const head = total ? `☀️ Day ${before.day + 1}: <span class="gold">🪙 +${coinText(total)}</span>` +
    (extras.length ? ` <small>(${coinText(out.income)} and ${extras.join(" and ")})</small>` : "") + (got ? `   ${got}` : "")
    : `☀️ Day ${before.day + 1}: nothing picked today.`;
  say(out.error ? "bad" : total ? "fine" : "", head, lines);
  $("today").textContent = total ? `Yesterday: 🪙 +${coinText(total)}  ·  best day 🪙 ${coinText(out.farm.best)}` : "";
  if (total) { SFX.play("coins"); $("coinsBox").classList.remove("bump"); void $("coinsBox").offsetWidth; $("coinsBox").classList.add("bump"); }
  if (out.error) { SFX.play("error"); stopAuto(); }
  if (out.perfect) setTimeout(() => SFX.play("perfect"), 250);
  if (out.record) { SFX.play("job"); toast("🏆", "New class record!", `🪙 ${coinText(out.farm.best)} in one day. Nobody in the class has done better.`); }
  if (landed.length) toast("🌠", landed.length > 1 ? `${landed.length} meteors landed!` : "A meteor landed!",
    'Rocks block your rover.  drill("east")  breaks one for coins.');
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
  visiting = null; visitView = null;
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
editor.addEventListener("input", e => { typed(); complete(e.inputType === "insertText"); });
editor.addEventListener("scroll", () => { updateEditor(); closeComplete(); });
editor.addEventListener("blur", closeComplete);
editor.addEventListener("click", () => complete(false));
editor.addEventListener("keyup", e => { if (/^(Arrow(Left|Right)|Home|End)$/.test(e.key)) complete(false); });
$("ac").addEventListener("mousedown", e => {
  e.preventDefault();
  const item = e.target.closest(".ac-item");
  if (item && ac) acceptComplete(ac.items[Number(item.dataset.i)]);
});
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
// A classmate's yard says hello too (the same speech bubble as your own).
$("visitYard").addEventListener("click", e => {
  if (!visitView) return;
  const box = $("visitYard").getBoundingClientRect(), x = e.clientX - box.left, y = e.clientY - box.top;
  const hit = visitView.hits.find(h => Math.hypot(h.cx - x, h.cy - y) < h.r);
  if (hit) wiggles[hit.d.key] = performance.now();
});
window.addEventListener("resize", () => { updateEditor(); if (farm) renderSample(); });

// The teacher's messages reach the farm too, and so does closing it.
let noticeSeen = null;
setInterval(async () => {
  const lately = performance.now() - lastInput < 90000 ? "&busy=1" : "";
  const out = await get(`/planet/ping?id=${encodeURIComponent(me)}${lately}`).catch(() => null);
  if (!out) return;
  if (out.farm === false) { showClosed(); return; }
  // The teacher turned it back on while this page was showing "the farm is closed".
  if (out.farm === true && !$("closed").hidden) { location.reload(); return; }
  if (!farm) return;
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
