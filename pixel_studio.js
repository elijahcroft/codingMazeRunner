// Pixel Pals: the Studio page. Students here are on laptop touchpads, where
// holding a click while sliding is hard. So one click colours a square, shapes
// go click-then-click, and Easy pen draws with nothing held down.
"use strict";

const $ = id => document.getElementById(id);
const A = PixelArt;
function store(key, value) { try { localStorage.setItem(key, value); } catch (_) {} }
function recall(key) { try { return localStorage.getItem(key); } catch (_) { return null; } }
async function post(url, data) {
  const response = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
  return response.json();
}
function esc(value) {
  return String(value).replace(/[&<>"']/g, ch => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch]));
}

const SIZES = [{size: 16, name: "Small"}, {size: 24, name: "Medium"}, {size: 32, name: "Big"}, {size: 48, name: "Huge"}];
const SPEEDS = [{fps: 3, name: "Slow"}, {fps: 6, name: "Medium"}, {fps: 10, name: "Fast"}];
const MAX_COLOURS = 62, UNDO_STEPS = 60;

const TOOLS = [
  ["pencil", "Pencil"], ["eraser", "Eraser"], ["fill", "Fill"],
  ["line", "Line"], ["box", "Box"], ["circle", "Circle"],
  ["stamp", "Stamp"], ["shade", "Shade"], ["swap", "Swap"],
  ["select", "Move"], ["picker", "Picker"],
];
const PENS = ["pencil", "eraser", "shade"];     // the tools with strokes
const RAINBOW = [11, 16, 19, 22, 25, 28, 30, 13];     // places in the palette, red round to pink
const SHAPES = ["line", "box", "circle"];

// Little pictures for the tool buttons, drawn the same way the students draw.
const ICON_INK = {k: "#1b1530", y: "#ffc21f", p: "#ff5fa2", w: "#ffffff", b: "#2f6fe4", g: "#9a96a8"};
const ICONS = {
  pencil: [".........kk.", "........kppk", ".......kykkk", "......kyyyk.", ".....kyyyk..", "....kyyyk...",
           "...kyyyk....", "..kyyyk.....", ".kgyyk......", ".kkgk.......", ".kk.........", "............"],
  eraser: ["............", ".......kkkk.", "......kppppk", ".....kppppkk", "....kppppkgk", "...kppppkgk.",
           "..kwwwwkgk..", ".kwwwwkgk...", ".kwwwwkk....", ".kkkkkk.....", "............", "............"],
  fill:   ["....kkkk....", "...k....k...", "..k......k..", ".kkkkkkkkkk.", ".kbbbbbbbbk.", ".kbbbbbbbbk.",
           ".kbbbbbbbbk.", "..kbbbbbbk..", "..kbbbbbbk..", "..kbbbbbbk..", "...kkkkkk...", "............"],
  picker: [".........kk.", ".......kkkkk", "........kkk.", ".......kwkk.", "......kwgwk.", ".....kwgwk..",
           "....kwgwk...", "...kwgwk....", "..kwgwk.....", ".kbkk.......", ".kk.........", "............"],
  line:   ["..........kk", ".........kkk", "........kkk.", ".......kkk..", "......kkk...", ".....kkk....",
           "....kkk.....", "...kkk......", "..kkk.......", ".kkk........", "kkk.........", "kk.........."],
  box:    ["............", ".kkkkkkkkkk.", ".kkkkkkkkkk.", ".kk......kk.", ".kk......kk.", ".kk......kk.",
           ".kk......kk.", ".kk......kk.", ".kk......kk.", ".kkkkkkkkkk.", ".kkkkkkkkkk.", "............"],
  circle: ["....kkkk....", "..kkkkkkkk..", ".kkk....kkk.", ".kk......kk.", "kk........kk", "kk........kk",
           "kk........kk", "kk........kk", ".kk......kk.", ".kkk....kkk.", "..kkkkkkkk..", "....kkkk...."],
  stamp:  ["....kkkk....", "....kbbk....", "....kbbk....", "...kkbbkk...", "..kbbbbbbk..", ".kkkkkkkkkk.",
           ".kppppppppk.", ".kkkkkkkkkk.", "............", "..pp.pp.pp..", "..pp.pp.pp..", "............"],
  shade:  ["....kkkk....", "..kkyygkkk..", ".kyyyyggggk.", ".kyyyyggggk.", "kyyyyyyggggk", "kyyyyyyggggk",
           "kyyyyyyggggk", "kyyyyyyggggk", ".kyyyyggggk.", ".kyyyyggggk.", "..kkyygkkk..", "....kkkk...."],
  swap:   ["pppp........", "pppp....k...", "pppp...kkk..", "pppp....k...", "........k...", "...k....k...",
           "...k....k...", "...k........", "..kkk...bbbb", "...k....bbbb", "........bbbb", "........bbbb"],
  select: ["kk.kk.kk.kk.", "k..........k", "..........k.", "k...bbb....k", "k...bbb.....", "....bbb....k",
           "k..........k", "k...........", "...........k", "k..........k", ".kk.kk.kk.kk", "............"],
  more:   ["............", "............", "............", "............", ".kk..kk..kk.", ".kk..kk..kk.",
           ".kk..kk..kk.", "............", "............", "............", "............", "............"],
};

let me = null, name = "";
let art = null;           // the open drawing: its frames are arrays of numbers
let shelfList = [];
let limits = {max_drawings: 12, max_frames: 12};
let cur = 0;              // which frame is open
let tool = "pencil", toolBefore = "pencil";
let brush = 1, colour = A.INK;
let solid = false, mirror = false, showGrid = true, onion = false;
let shadeWay = -1, stampKey = "Heart", penStyle = "plain";
let zoom = 1, fit = 16, panAt = {x: 0, y: 0};
let easy = recall("pixelEasyPen") === "1";
let undoList = [], redoList = [];
let hover = null;         // the square under the pointer
let stroke = null;        // a pencil or eraser line being drawn: {before, x, y, held}
let shape = null;         // a shape between its two ends: {x, y, pressed}
let shapeEnd = null;
let sel = null;           // squares picked up to move: {x, y, w, h, pix, before, grab}
let cell = 16;

// ---- Saving --------------------------------------------------------------------------------
let dirty = false, saving = false, saveTimer = 0;

function savedSays(text, bad) {
  $("saved").textContent = text;
  $("saved").classList.toggle("bad", !!bad);
}
function payload() {
  return {id: me, drawing: {key: art.key, title: art.title, size: art.size, speed: art.speed, palette: art.palette,
                            frames: art.frames.map(A.encode), names: art.names, marks: art.marks || "", guide: art.guide || ""}};
}
function changed() {
  dirty = true;
  savedSays("Saving...");
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveNow, 2000);
}
async function saveNow() {
  clearTimeout(saveTimer);
  if (!dirty || saving || !art) return true;
  saving = true;
  dirty = false;
  let answer = null;
  try { answer = await post("/pixel/save", payload()); } catch (_) {}
  saving = false;
  if (answer && answer.ok) {
    if (answer.badges && answer.badges.length) showRewards({badges: answer.badges});
    if (dirty) saveTimer = setTimeout(saveNow, 2000);
    else savedSays("Saved ✓");
    return true;
  }
  if (answer && answer.error === "join") { store("mazeId", ""); location.reload(); return false; }
  dirty = true;
  savedSays("Not saved yet. Trying again...", true);
  saveTimer = setTimeout(saveNow, 5000);
  return false;
}
addEventListener("pagehide", () => {
  if (dirty && art) navigator.sendBeacon("/pixel/save", new Blob([JSON.stringify(payload())], {type: "application/json"}));
});

// ---- Undo: a snapshot of the frames from before each change --------------------------------
function snap() { return JSON.stringify({frames: art.frames.map(A.encode), names: art.names, cur}); }
function restore(text) {
  const saved = JSON.parse(text);
  art.frames = saved.frames.map(A.decode);
  art.names = saved.names;
  cur = saved.cur;
  buildReel();
  changed();
  checkGuide();
}
// Call with a snapshot from before a change, after making it.
function done(before) {
  if (snap() === before) return;
  undoList.push(before);
  if (undoList.length > UNDO_STEPS) undoList.shift();
  redoList = [];
  changed();
  refreshButtons();
  repaint();
  checkGuide();
}
function undo() {
  settle();
  if (!undoList.length) return;
  redoList.push(snap());
  restore(undoList.pop());
}
function redo() {
  settle();
  if (!redoList.length) return;
  undoList.push(snap());
  restore(redoList.pop());
}

// ---- Colour by numbers ----------------------------------------------------------------------
// The colours still to do, numbered from the one with the most squares.
function guideColours() {
  const target = A.decode(art.guide), counts = new Map(), base = PalGallery.outlined(target);
  target.forEach((n, i) => { if (n !== base[i]) counts.set(n, (counts.get(n) || 0) + 1); });
  return [...counts].sort((a, b) => b[1] - a[1]).map(c => c[0]);
}
function buildGuideKey() {
  const on = !!art.guide;
  $("guideKey").hidden = !on;
  $("shades").hidden = on;
  if (!on) return;
  const target = A.decode(art.guide), f = art.frames[0];
  $("guideKey").innerHTML = guideColours().map((n, i) => {
    const left = target.some((t, at) => t === n && f[at] !== n);
    const ink = (A.PALETTE[n] && parseInt(A.PALETTE[n].slice(1, 3), 16) + parseInt(A.PALETTE[n].slice(3, 5), 16) > 300) ? "#1b1530" : "#ffffff";
    return `<button data-colour="${n}" class="${left ? "" : "done"}" style="background:${art.palette[n]};color:${ink}" aria-pressed="${n === colour}" aria-label="Number ${i + 1}">${left ? i + 1 : "✓"}</button>`;
  }).join("");
}
function checkGuide() {
  if (!art.guide) return;
  buildGuideKey();
  const target = A.decode(art.guide), f = art.frames[0];
  if (target.some((n, i) => n !== f[i])) return;
  art.guide = "";
  buildGuideKey();
  changed();
  repaint();
  guideFinished();
}
function paintNumbers(g) {
  const target = A.decode(art.guide), f = frame(), size = art.size, list = guideColours();
  g.font = `900 ${Math.round(cell * .6)}px ui-rounded, system-ui, sans-serif`;
  g.textAlign = "center";
  g.textBaseline = "middle";
  target.forEach((n, at) => {
    if (n === f[at]) return;
    const number = list.indexOf(n) + 1;
    if (!number) return;
    if (n === colour) {               // the squares she's looking for
      g.fillStyle = "#ffe98a";
      g.fillRect(at % size * cell, Math.floor(at / size) * cell, cell, cell);
    }
    g.fillStyle = n === colour ? "#1b1530" : "#8d84a8";
    g.fillText(number, (at % size + .5) * cell, (Math.floor(at / size) + .55) * cell);
  });
}

// ---- Putting squares on the frame -----------------------------------------------------------
function frame() { return art.frames[cur]; }

// Which squares the pen covers at each of these points, mirrored when Mirror is on.
function covered(points, width) {
  const out = new Set(), size = art.size, before = Math.floor((width - 1) / 2);
  for (const [px, py] of points) {
    for (let dy = 0; dy < width; dy++) for (let dx = 0; dx < width; dx++) {
      const x = px + dx - before, y = py + dy - before;
      if (x < 0 || y < 0 || x >= size || y >= size) continue;
      out.add(y * size + x);
      if (mirror) out.add(y * size + size - 1 - x);
    }
  }
  return out;
}
function put(squares, value) {
  const f = frame();
  for (const at of squares) f[at] = value;
}
function shapeSquares(x1, y1) {
  const {x, y} = shape;
  if (tool === "line") return covered(A.line(x, y, x1, y1), brush);
  const picked = tool === "box" ? A.box(x, y, x1, y1, solid) : A.circle(x, y, x1, y1, solid);
  return covered(picked, solid ? 1 : brush);
}

// ---- The pointer on the board ---------------------------------------------------------------
function squareAt(e) {
  const r = $("board").getBoundingClientRect();
  return {x: Math.floor((e.clientX - r.left - 2 + panAt.x) / cell), y: Math.floor((e.clientY - r.top - 2 + panAt.y) / cell)};
}
function onBoard(sq) { return sq.x >= 0 && sq.y >= 0 && sq.x < art.size && sq.y < art.size; }

function startStroke(sq, held) {
  stroke = {before: snap(), x: sq.x, y: sq.y, held, path: [], under: new Map(), shaded: new Set(), steps: 0};
  layDown(sq.x, sq.y);
  $("board").classList.toggle("pen-down", !held);
  repaint();
  showTip();
}
function layDown(x, y) {
  const f = frame(), {path, under, shaded} = stroke, squares = covered([[x, y]], brush);
  if (tool === "eraser") { put(squares, -1); return; }
  if (tool === "shade") {
    for (const at of squares) {
      if (f[at] < 0 || shaded.has(at)) continue;
      shaded.add(at);
      f[at] = shadeIndex(f[at]);
    }
    return;
  }
  stroke.steps++;
  const ink = penStyle === "rainbow" ? RAINBOW[Math.floor(stroke.steps / 2) % RAINBOW.length] : colour;
  for (const at of squares) {
    if (penStyle === "checks" && (at % art.size + Math.floor(at / art.size)) % 2) continue;
    if (!under.has(at)) under.set(at, f[at]);
    f[at] = ink;
  }
  if (brush !== 1 || penStyle !== "plain") return;
  // A clean line never turns a corner on a square of its own: when a line steps
  // diagonally through a square, that square comes back off.
  const last = path[path.length - 1];
  if (last && last[0] === x && last[1] === y) return;
  path.push([x, y]);
  if (path.length < 3) return;
  const [r, q, p] = path.slice(-3);
  if (Math.abs(p[0] - r[0]) === 1 && Math.abs(p[1] - r[1]) === 1) {
    for (const at of covered([q], 1)) if (!covered([p], 1).has(at)) f[at] = under.get(at);
    path.splice(path.length - 2, 1);
  }
}
// Clicking along a line square by square is what a child does when dragging is
// hard. Easy pen would help, so it's offered then, once.
let lonelyClicks = 0, lastClick = null, offerUntil = 0;
function noticeClick(sq) {
  const near = lastClick && Math.abs(lastClick.x - sq.x) <= 1 && Math.abs(lastClick.y - sq.y) <= 1
    && performance.now() - lastClick.at < 3000;
  lonelyClicks = near ? lonelyClicks + 1 : 0;
  lastClick = {x: sq.x, y: sq.y, at: performance.now()};
  if (lonelyClicks < 7 || easy || recall("pixelEasyOffered")) return;
  store("pixelEasyOffered", "1");
  clearTimeout(tipHold);
  $("tip").innerHTML = `Lots of clicking? <button class="tip-try" id="tryEasy">Try Easy pen</button>`;
  $("tryEasy").addEventListener("click", () => { easy = true; offerUntil = 0; store("pixelEasyPen", "1"); refreshOptions(); showTip(); });
  offerUntil = performance.now() + 9000;
  tipHold = setTimeout(showTip, 9000);
  return true;
}
function endStroke() {
  if (!stroke) return;
  const {before, path, held, x, y} = stroke;
  stroke = null;
  if (held && tool === "pencil" && path.length <= 1) noticeClick({x, y});
  $("board").classList.remove("pen-down");
  done(before);
  showTip();
}
function finishShape(sq) {
  const before = snap();
  put(shapeSquares(sq.x, sq.y), colour);
  dropTheShape();
  done(before);
}
function dropTheShape() {
  shape = null;
  shapeEnd = null;
  showTip();
  repaint();
}
function pourAt(sq) {
  const before = snap(), f = frame();
  if (f[sq.y * art.size + sq.x] === colour) return;
  const size = art.size, spots = A.flood(f, size, sq.x, sq.y);
  put(spots.map(([x, y]) => y * size + x), colour);
  const across = size - 1 - sq.x;
  if (mirror && f[sq.y * size + across] !== colour) {
    put(A.flood(f, size, across, sq.y).map(([x, y]) => y * size + x), colour);
  }
  PalStage.SFX.play("pop");
  done(before);
}
// Every square of the colour you click turns into your colour, in all the frames.
function swapAt(sq) {
  const found = frame()[sq.y * art.size + sq.x];
  if (found < 0) { tipNow("That square is empty. Try a coloured one."); return; }
  if (found === colour) { tipNow("Pick a new colour first."); return; }
  const before = snap();
  art.frames = art.frames.map(f => f.map(n => n === found ? colour : n));
  buildReel();
  done(before);
}
// ---- Shade: one step darker or lighter than the colour already there --------------------------
function nearestColour(hex, not) {
  const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const [r, g, b] = rgb(hex);
  let best = -1, gap = Infinity;
  art.palette.forEach((c, i) => {
    if (i === not) return;
    const [cr, cg, cb] = rgb(c), d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2;
    if (d < gap) { gap = d; best = i; }
  });
  return {index: best, gap};
}
function colourFor(hex, not) {
  const near = nearestColour(hex, not);
  if (near.gap < 200 || art.palette.length >= MAX_COLOURS) return near.index;
  art.palette.push(hex);
  buildMine();
  return art.palette.length - 1;
}
function shadeIndex(n) { return colourFor(A.shade(art.palette[n], shadeWay), n); }
// ---- Stamps ------------------------------------------------------------------------------------
function stampSquares(sq) {
  const rows = A.STAMPS[stampKey], out = [], size = art.size;
  const left = sq.x - Math.floor(rows[0].length / 2), top = sq.y - Math.floor(rows.length / 2);
  rows.forEach((row, dy) => Array.from(row).forEach((ch, dx) => {
    if (ch === ".") return;
    const x = left + dx, y = top + dy;
    if (x < 0 || y < 0 || x >= size || y >= size) return;
    out.push([y * size + x, ch]);
    if (mirror) out.push([y * size + size - 1 - x, ch]);
  }));
  return out;
}
function stampInk(ch) { return ch === "x" ? art.palette[colour] : A.STAMP_INK[ch]; }
function stampAt(sq) {
  const before = snap(), f = frame();
  for (const [at, ch] of stampSquares(sq)) f[at] = ch === "x" ? colour : colourFor(A.STAMP_INK[ch], -1);
  PalStage.SFX.play("pop");
  done(before);
}
function chooseStamp(key) {
  stampKey = key;
  document.querySelectorAll("[data-stamp]").forEach(b => b.setAttribute("aria-pressed", b.dataset.stamp === key));
  showTip();
}
// ---- Move: pick up some squares, slide them, put them down ------------------------------------
function inSel(sq) { return sel && sq.x >= sel.x && sq.y >= sel.y && sq.x < sel.x + sel.w && sq.y < sel.y + sel.h; }
function liftSquares(x0, y0, x1, y1) {
  const [left, right] = [Math.min(x0, x1), Math.max(x0, x1)], [top, bottom] = [Math.min(y0, y1), Math.max(y0, y1)];
  const before = snap(), f = frame(), size = art.size, w = right - left + 1, h = bottom - top + 1, pix = [];
  for (let y = top; y <= bottom; y++) for (let x = left; x <= right; x++) {
    pix.push(f[y * size + x]);
    f[y * size + x] = -1;
  }
  if (pix.every(n => n < 0)) { tipNow("There's nothing in those squares."); return; }
  sel = {x: left, y: top, w, h, pix, before, grab: null};
  refreshOptions();
  showTip();
  repaint();
}
function pasteSel(f) {
  for (let y = 0; y < sel.h; y++) for (let x = 0; x < sel.w; x++) {
    const n = sel.pix[y * sel.w + x], tx = sel.x + x, ty = sel.y + y;
    if (n >= 0 && tx >= 0 && ty >= 0 && tx < art.size && ty < art.size) f[ty * art.size + tx] = n;
  }
}
function dropSel() {
  if (!sel) return;
  const {before} = sel;
  pasteSel(frame());
  sel = null;
  done(before);
  refreshOptions();
  showTip();
}
function selectEverything() {
  settle();
  const f = frame(), size = art.size, xs = [], ys = [];
  f.forEach((n, i) => { if (n >= 0) { xs.push(i % size); ys.push(Math.floor(i / size)); } });
  if (!xs.length) { tipNow("There's nothing to pick up yet."); return; }
  liftSquares(Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys));
}
function selDown(sq, e) {
  if (sel && sel.grab) { sel.grab = null; showTip(); return; }             // it was following: put it here
  if (inSel(sq)) {
    $("board").setPointerCapture(e.pointerId);
    sel.grab = {dx: sq.x - sel.x, dy: sq.y - sel.y, held: true, moved: false};
    return;
  }
  if (sel) { dropSel(); return; }
  if (shape) { const {x, y} = shape; dropTheShape(); liftSquares(x, y, sq.x, sq.y); return; }
  $("board").setPointerCapture(e.pointerId);
  shape = {x: sq.x, y: sq.y, pressed: true};
  shapeEnd = sq;
  showTip();
  repaint();
}
function pickAt(sq) {
  const found = frame()[sq.y * art.size + sq.x];
  if (found < 0) {
    tipNow("That square is empty. Try a coloured one.");
    return;
  }
  chooseColour(found);
  chooseTool(toolBefore);
}

function pointerDown(e) {
  if (e.button !== 0) return;
  const sq = squareAt(e);
  if (!onBoard(sq)) return;
  if (tool === "select") selDown(sq, e);
  else if (PENS.includes(tool)) {
    if (easy) {
      if (stroke) endStroke(); else startStroke(sq, false);
    } else {
      $("board").setPointerCapture(e.pointerId);
      startStroke(sq, true);
    }
  } else if (tool === "fill") {
    pourAt(sq);
  } else if (tool === "picker") {
    pickAt(sq);
  } else if (tool === "swap") {
    swapAt(sq);
  } else if (tool === "stamp") {
    stampAt(sq);
  } else if (shape) {
    finishShape(sq);
  } else {
    $("board").setPointerCapture(e.pointerId);
    shape = {x: sq.x, y: sq.y, pressed: true};
    shapeEnd = sq;
    showTip();
    repaint();
  }
}
function pointerMove(e) {
  const sq = squareAt(e);
  if (stroke) {
    for (const [x, y] of A.line(stroke.x, stroke.y, sq.x, sq.y)) layDown(x, y);
    stroke.x = sq.x;
    stroke.y = sq.y;
  }
  if (shape) shapeEnd = sq;
  if (sel && sel.grab) {
    const x = sq.x - sel.grab.dx, y = sq.y - sel.grab.dy;
    if (x !== sel.x || y !== sel.y) { sel.grab.moved = true; sel.x = x; sel.y = y; repaint(); }
  }
  const next = onBoard(sq) ? sq : null;
  if (stroke || shape || !next !== !hover || (next && (next.x !== hover.x || next.y !== hover.y))) repaint();
  hover = next;
}
function pointerUp(e) {
  if (stroke && stroke.held) endStroke();
  if (sel && sel.grab && sel.grab.held) {
    if (sel.grab.moved) sel.grab = null;            // dragged it there
    else { sel.grab.held = false; showTip(); }      // clicked it: now it follows until the next click
    return;
  }
  if (shape && shape.pressed) {
    shape.pressed = false;
    const sq = squareAt(e);
    if (sq.x === shape.x && sq.y === shape.y) return;           // that was one end
    if (tool === "select") {
      const {x, y} = shape;
      dropTheShape();
      liftSquares(x, y, Math.max(0, Math.min(art.size - 1, sq.x)), Math.max(0, Math.min(art.size - 1, sq.y)));
    } else finishShape(sq);
  }
}
function pointerLeave() {
  hover = null;
  if (stroke && !stroke.held) endStroke();    // heading for a button: lift the pen
  repaint();
}
// Put down whatever is in the pen's hands, before changing what's being worked on.
function settle() {
  endStroke();
  dropTheShape();
  dropSel();
}

// ---- Drawing the board ----------------------------------------------------------------------
let repaintAsked = false;
function repaint() {
  if (repaintAsked) return;
  repaintAsked = true;
  requestAnimationFrame(() => { repaintAsked = false; paintBoard(); });
}

function paintChecks(g, size, px) {
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    g.fillStyle = (x + y) % 2 ? "#ece8f5" : "#ffffff";
    g.fillRect(x * px, y * px, px, px);
  }
}
function paintFrame(g, f, size, px, palette) {
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const n = f[y * size + x];
    if (n < 0) continue;
    g.fillStyle = palette[n];
    g.fillRect(x * px, y * px, px, px);
  }
}

function shownFrame() {
  if (!sel) return frame();
  const f = frame().slice();
  pasteSel(f);
  return f;
}
function paintBoard() {
  if (!art) return;
  const cv = $("board"), dpr = window.devicePixelRatio || 1, size = art.size, whole = cell * size;
  const box = $("boardBox"), wide = Math.min(whole, box.clientWidth - 10), tall = Math.min(whole, box.clientHeight - 10);
  if (cv.width !== Math.round(wide * dpr) || cv.height !== Math.round(tall * dpr)) {
    cv.width = Math.round(wide * dpr);
    cv.height = Math.round(tall * dpr);
    cv.style.width = wide + 4 + "px";
    cv.style.height = tall + 4 + "px";
  }
  panAt.x = Math.max(0, Math.min(whole - wide, panAt.x));
  panAt.y = Math.max(0, Math.min(whole - tall, panAt.y));
  const g = cv.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, -panAt.x * dpr, -panAt.y * dpr);
  paintChecks(g, size, cell);
  if (onion && art.frames.length > 1) {
    g.globalAlpha = .3;
    paintFrame(g, art.frames[(cur - 1 + art.frames.length) % art.frames.length], size, cell, art.palette);
    g.globalAlpha = 1;
  }
  paintFrame(g, shownFrame(), size, cell, art.palette);
  if (art.guide && cur === 0) paintNumbers(g);

  if (shape && shapeEnd) {
    if (tool === "select") {
      const left = Math.min(shape.x, shapeEnd.x), top = Math.min(shape.y, shapeEnd.y);
      ants(g, left, top, Math.abs(shape.x - shapeEnd.x) + 1, Math.abs(shape.y - shapeEnd.y) + 1);
    } else {
      g.fillStyle = art.palette[colour];
      for (const at of shapeSquares(shapeEnd.x, shapeEnd.y)) g.fillRect(at % size * cell, Math.floor(at / size) * cell, cell, cell);
    }
  }
  if (showGrid && cell >= 6) {
    g.strokeStyle = "rgba(27, 21, 48, .14)";
    g.lineWidth = 1;
    g.beginPath();
    for (let i = 1; i < size; i++) {
      g.moveTo(i * cell + .5, 0); g.lineTo(i * cell + .5, whole);
      g.moveTo(0, i * cell + .5); g.lineTo(whole, i * cell + .5);
    }
    g.stroke();
  }
  if (mirror) {
    g.fillStyle = "#ff5fa2";
    g.fillRect(whole / 2 - 1, 0, 2, whole);
  }
  if (sel) ants(g, sel.x, sel.y, sel.w, sel.h);
  // The square the pen is over: its colour, with a ring so it shows on anything.
  if (hover && !shape && !stroke && !sel) {
    if (tool === "stamp") {
      for (const [at, ch] of stampSquares(hover)) {
        g.fillStyle = stampInk(ch);
        g.fillRect(at % size * cell, Math.floor(at / size) * cell, cell, cell);
      }
    } else {
      const painting = tool === "pencil" || SHAPES.includes(tool);
      const width = PENS.includes(tool) || (SHAPES.includes(tool) && !solid) ? brush : 1;
      for (const at of covered([[hover.x, hover.y]], width)) {
        const x = at % size * cell, y = Math.floor(at / size) * cell;
        if (painting) { g.fillStyle = art.palette[colour]; g.fillRect(x, y, cell, cell); }
        g.lineWidth = 2;
        g.strokeStyle = "#ffffff";
        g.strokeRect(x + 1, y + 1, cell - 2, cell - 2);
        g.lineWidth = 1;
        g.strokeStyle = "#1b1530";
        g.strokeRect(x + .5, y + .5, cell - 1, cell - 1);
      }
    }
  }
  paintThumb(cur);
}
function ants(g, x, y, w, h) {
  for (const [ink, gap] of [["#ffffff", 0], ["#1b1530", 5]]) {
    g.strokeStyle = ink;
    g.lineWidth = 2;
    g.setLineDash([5, 5]);
    g.lineDashOffset = gap;
    g.strokeRect(x * cell + 1, y * cell + 1, w * cell - 2, h * cell - 2);
  }
  g.setLineDash([]);
}

function fitBoard() {
  if (!art) return;
  const box = $("boardBox"), room = Math.min(box.clientWidth, box.clientHeight) - 10;
  fit = Math.max(4, Math.floor(room / art.size));
  const next = fit * zoom;
  if (next !== cell) { cell = next; }
  repaint();
  $("zoomIn").disabled = zoom >= 4;
  $("zoomOut").disabled = zoom <= 1;
}
// Zoom keeps the square under `at` (a point on the board) where it is.
function setZoom(next, at) {
  next = Math.max(1, Math.min(4, next));
  if (next === zoom) return;
  const cv = $("board"), pointX = at ? at.x : cv.clientWidth / 2, pointY = at ? at.y : cv.clientHeight / 2;
  const sx = (pointX + panAt.x) / cell, sy = (pointY + panAt.y) / cell;
  zoom = next;
  fitBoard();
  panAt.x = sx * cell - pointX;
  panAt.y = sy * cell - pointY;
  repaint();
}

// ---- Frames ---------------------------------------------------------------------------------
function thumbInto(cv, f, size, palette) {
  cv.width = cv.height = size;
  const g = cv.getContext("2d");
  paintChecks(g, size, 1);
  paintFrame(g, f, size, 1, palette);
}
function paintThumb(n) {
  const cv = document.querySelector(`#frames [data-frame="${n}"] canvas`);
  if (cv) thumbInto(cv, n === cur ? shownFrame() : art.frames[n], art.size, art.palette);
}
function buildReel() {
  $("frames").innerHTML = art.frames.map((_, i) =>
    `<button class="frame" data-frame="${i}" aria-pressed="${i === cur}" aria-label="Frame ${i + 1}"><canvas></canvas>${art.names[i] ? `<b>${esc(art.names[i])}</b>` : ""}<span>${i + 1}</span></button>`).join("");
  art.frames.forEach((_, i) => paintThumb(i));
  $("frameName").value = art.names[cur] || "";
  const on = document.querySelector("#frames [aria-pressed=true]");
  if (on) on.scrollIntoView({block: "nearest", inline: "nearest"});
  $("speed").hidden = art.frames.length < 2;
  $("quick").hidden = art.frames.length > 1;
  $("reelNote").textContent = art.frames.length < 2
    ? "Copy it, change a bit, and it moves!"
    : `${art.frames.length} pictures in a row.`;
  refreshButtons();
  repaint();
}
function refreshButtons() {
  const n = art.frames.length, full = n >= limits.max_frames;
  $("undo").disabled = !undoList.length;
  $("redo").disabled = !redoList.length;
  $("copyFrame").disabled = $("newFrame").disabled = full;
  $("deleteFrame").disabled = n < 2;
  $("frameLeft").disabled = cur === 0;
  $("frameRight").disabled = cur === n - 1;
  $("download").title = n > 1 ? "Save your animation as a GIF" : "Save your picture";
}
function openFrame(n) {
  settle();
  cur = n;
  buildReel();
}
function addFrame(pixels) {
  settle();
  const before = snap();
  art.frames.splice(cur + 1, 0, pixels);
  art.names.splice(cur + 1, 0, "");
  cur++;
  buildReel();
  done(before);
}
function moveFrame(by) {
  const before = snap();
  const [taken] = art.frames.splice(cur, 1), [name] = art.names.splice(cur, 1);
  cur += by;
  art.frames.splice(cur, 0, taken);
  art.names.splice(cur, 0, name);
  buildReel();
  done(before);
}
function deleteFrame() {
  const before = snap();
  art.frames.splice(cur, 1);
  art.names.splice(cur, 1);
  cur = Math.min(cur, art.frames.length - 1);
  buildReel();
  done(before);
}
// A name is how code finds a frame, so one name can only be on one frame.
function nameFrame(word) {
  const before = snap();
  art.names = art.names.map(n => n === word ? "" : n);
  art.names[cur] = word;
  buildReel();
  done(before);
}
function changeWhole(make) {
  settle();
  const before = snap();
  art.frames[cur] = make(frame());
  done(before);
}

// ---- The side panels ------------------------------------------------------------------------
function iconInto(cv, rows) {
  cv.width = cv.height = 12;
  const g = cv.getContext("2d");
  rows.forEach((row, y) => Array.from(row).forEach((ch, x) => {
    if (ch === ".") return;
    g.fillStyle = ICON_INK[ch];
    g.fillRect(x, y, 1, 1);
  }));
}
function buildTools() {
  $("tools").innerHTML = TOOLS.map(([key, label]) =>
    `<button class="tool" data-tool="${key}" aria-pressed="false"><canvas></canvas>${label}</button>`).join("");
  $("tools").insertAdjacentHTML("beforeend", `<button class="tool" id="openMore" aria-expanded="false"><canvas></canvas>More</button>`);
  for (const [key] of TOOLS) iconInto(document.querySelector(`[data-tool=${key}] canvas`), ICONS[key]);
  iconInto(document.querySelector("#openMore canvas"), ICONS.more);
  $("stampBar").innerHTML = Object.keys(A.STAMPS).map(key =>
    `<button data-stamp="${key}" title="${key}" aria-label="${key}" aria-pressed="false"><canvas></canvas></button>`).join("");
  document.querySelectorAll("[data-stamp]").forEach(b => paintStampIcon(b.querySelector("canvas"), b.dataset.stamp));
  $("sizes").innerHTML = [1, 2, 3].map(n =>
    `<button data-brush="${n}" aria-label="Pen size ${n}"><i style="width:${n * 5}px;height:${n * 5}px"></i></button>`).join("");
  $("speed").innerHTML = SPEEDS.map(s =>
    `<button data-fps="${s.fps}">${s.name}</button>`).join("");
  $("swatches").innerHTML = A.PALETTE.map((hex, i) =>
    `<button data-colour="${i}" style="background:${hex}" aria-label="Colour ${i + 1}"></button>`).join("");
}
function paintStampIcon(cv, key) {
  const rows = A.STAMPS[key], side = Math.max(rows.length, rows[0].length, 7);
  cv.width = cv.height = side;
  const g = cv.getContext("2d"), left = Math.floor((side - rows[0].length) / 2), top = Math.floor((side - rows.length) / 2);
  rows.forEach((row, y) => Array.from(row).forEach((ch, x) => {
    if (ch === ".") return;
    g.fillStyle = ch === "x" ? "#ff5fa2" : A.STAMP_INK[ch];
    g.fillRect(left + x, top + y, 1, 1);
  }));
  if (rows.some(r => r.includes("w"))) { cv.style.background = "#7ab8ff"; cv.style.borderRadius = "3px"; }
}
function buildMine() {
  const mine = art.palette.slice(A.PALETTE.length);
  $("mine").hidden = !mine.length;
  $("mine").innerHTML = mine.map((hex, i) =>
    `<button data-colour="${i + A.PALETTE.length}" style="background:${hex}" aria-label="Your colour ${i + 1}"></button>`).join("");
  $("mix").disabled = art.palette.length >= MAX_COLOURS;
}
function refreshOptions() {
  document.querySelectorAll("[data-tool]").forEach(b => b.setAttribute("aria-pressed", b.dataset.tool === tool));
  document.querySelectorAll("[data-brush]").forEach(b => b.setAttribute("aria-pressed", +b.dataset.brush === brush));
  document.querySelectorAll("[data-shade]").forEach(b => b.setAttribute("aria-pressed", +b.dataset.shade === shadeWay));
  $("optSize").hidden = ![...PENS, ...SHAPES].includes(tool);
  $("solid").hidden = tool !== "box" && tool !== "circle";
  $("optShade").hidden = tool !== "shade";
  $("optPen").hidden = tool !== "pencil";
  document.querySelectorAll("[data-pen]").forEach(b => b.setAttribute("aria-pressed", b.dataset.pen === penStyle));
  $("optAll").hidden = tool !== "select" || !!sel;
  $("optSelect").hidden = tool !== "select" || !sel;
  $("stampBar").hidden = tool !== "stamp";
  document.querySelectorAll("[data-colour]").forEach(b => b.setAttribute("aria-pressed", +b.dataset.colour === colour));
  if (art && art.guide) buildGuideKey();
  document.querySelectorAll("[data-fps]").forEach(b => b.setAttribute("aria-pressed", +b.dataset.fps === art.speed));
  $("nowColour").style.background = art.palette[colour];
  $("solid").setAttribute("aria-pressed", solid);
  const near = [A.shade(A.shade(art.palette[colour], -1), -1), A.shade(art.palette[colour], -1), art.palette[colour],
                A.shade(art.palette[colour], 1), A.shade(A.shade(art.palette[colour], 1), 1)];
  $("shades").innerHTML = near.map((hex, i) =>
    `<button data-tone="${hex}" style="background:${hex}" aria-pressed="${i === 2}" aria-label="${["Much darker", "Darker", "This colour", "Lighter", "Much lighter"][i]}"></button>`).join("");
  $("easy").setAttribute("aria-pressed", easy);
  $("mirror").setAttribute("aria-pressed", mirror);
  $("grid").setAttribute("aria-pressed", showGrid);
  $("showLast").textContent = `Ghost: ${onion ? "On" : "Off"}`;
}
function chooseTool(key) {
  settle();
  if (key === "picker" && tool !== "picker") toolBefore = tool;
  tool = key;
  refreshOptions();
  showTip();
}
function chooseColour(n) {
  colour = n;
  if (tool === "eraser" || tool === "picker" || tool === "select") chooseTool("pencil");   // picking a colour means painting
  refreshOptions();
  showTip();
  repaint();
}
function addColour(hex) {
  const known = art.palette.indexOf(hex);
  if (known >= 0) { chooseColour(known); return; }
  if (art.palette.length >= MAX_COLOURS) return;
  art.palette.push(hex);
  buildMine();
  chooseColour(art.palette.length - 1);
  changed();
}

// What to do next, always on screen, in words for a child who's new to all this.
let tipHold = 0;
function tipNow(text) {
  clearTimeout(tipHold);
  $("tip").textContent = text;
  tipHold = setTimeout(showTip, 3500);
}
function showTip() {
  if (performance.now() < offerUntil && $("tryEasy")) return;
  clearTimeout(tipHold);
  const pen = {pencil: "colour it", eraser: "rub it out", shade: shadeWay < 0 ? "make it darker" : "make it lighter"}[tool];
  let html;
  if (art && art.guide && tool !== "fill") {
    html = "Pick a number, then colour all its squares.";
  } else if (PENS.includes(tool)) {
    if (stroke && !stroke.held) html = "<b>The pen is down.</b> Slide, then click to stop.";
    else if (easy) html = `<b>Easy pen:</b> click, slide, click to stop.`;
    else if (tool === "shade") html = `Click on your colours to ${pen}.`;
    else html = tool === "pencil" && nextStep ? nextStep : `Click a square to ${pen}.`;
  } else if (tool === "fill") {
    html = "Click a shape to pour your colour in.";
  } else if (tool === "picker") {
    html = "Click a colour in your drawing to use it again.";
  } else if (tool === "swap") {
    html = "Pick a colour, then click one to change.";
  } else if (tool === "stamp") {
    html = `<b>${esc(stampKey)}.</b> Click your drawing to stamp it.`;
  } else if (tool === "select") {
    if (sel && sel.grab && !sel.grab.held) html = "<b>It's following you.</b> Click where it should go.";
    else if (sel) html = "Slide the box, or use the arrow keys.";
    else if (shape) html = "<b>Now click the other corner.</b>";
    else html = "Click one corner, then the other corner.";
  } else if (shape) {
    html = "<b>Now click where it ends.</b> Esc to stop.";
  } else {
    html = `Click where it starts, then where it ends.`;
  }
  $("tip").innerHTML = html;
}

// ---- See it play: one frame is alive, and two or more play like a flip book --------------------
let shown = -1, shownVersion = "";
let playedAt = 0, checkedAt = 0;
function playLoop(now) {
  requestAnimationFrame(playLoop);
  if (!art || now - playedAt < 45) return;     // a little pal doesn't need 60 frames a second
  playedAt = now;
  const n = art.frames.length;
  if (now - checkedAt > 160) { checkedAt = now; freshMini(); }
  if (n === 1) { livePreview(now); return; }
  const at = Math.floor(now / 1000 * art.speed) % n;
  const version = `${at}:${A.encode(art.frames[at])}:${art.size}`;
  if (at === shown && version === shownVersion) return;
  shown = at;
  shownVersion = version;
  thumbInto($("preview"), art.frames[at], art.size, art.palette);
}

// ---- Download -------------------------------------------------------------------------------
function fileName(ending) {
  return (art.title.replace(/[^\w -]/g, "").trim() || "my-pixel-art") + ending;
}
function hand(blob, name) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 5000);
}
function download() {
  const scale = Math.floor(512 / art.size);
  if (art.frames.length > 1) {
    hand(new Blob([A.gif(art.frames, art.size, scale, art.palette, art.speed)], {type: "image/gif"}), fileName(".gif"));
    return;
  }
  const cv = document.createElement("canvas");
  cv.width = cv.height = art.size * scale;
  paintFrame(cv.getContext("2d"), frame(), art.size, scale, art.palette);
  cv.toBlob(blob => hand(blob, fileName(".png")));
}

// ---- A drawing is code, and a pattern --------------------------------------------------------
const LETTER = n => n < 0 ? "." : (n < 10 ? String(n) : A.encode([n]));
function artRows() {
  const text = A.encode(frame()), rows = [];
  for (let y = 0; y < art.size; y++) rows.push(text.slice(y * art.size, (y + 1) * art.size));
  return rows.join("\n");
}
function showArtSheet() {
  const box = $("artCode");
  box.value = artRows();
  box.cols = art.size + 1;
  box.rows = Math.min(art.size, 20);
  fillArtKey();
  $("artSheet").hidden = false;
  thumbInto($("artPreview"), frame(), art.size, art.palette);
  artBefore = snap();
}
let artBefore = "";
function fillArtKey() {
  const used = [...new Set(frame())].filter(n => n >= 0).sort((a, b) => a - b).slice(0, 16);
  $("artKey").innerHTML = used.map(n =>
    `<span>${esc(LETTER(n))}<i style="background:${art.palette[n]}"></i></span>`).join("");
}
// Any row of the right shape goes straight onto the picture. Half-typed rows wait.
function artTyped() {
  const rows = $("artCode").value.split("\n").map(r => r.trim());
  if (rows.length !== art.size || rows.some(r => r.length !== art.size)) return;
  const letters = rows.join("");
  const numbers = A.decode(letters);
  if (numbers.some((n, i) => (n < 0 && letters[i] !== ".") || n >= art.palette.length)) return;
  art.frames[cur] = numbers;
  thumbInto($("artPreview"), frame(), art.size, art.palette);
  fillArtKey();
  repaint();
}
function closeArtSheet() {
  $("artSheet").hidden = true;
  done(artBefore);
}
function showBeads() {
  const size = art.size, px = 18, cv = $("beadGrid"), g = cv.getContext("2d"), f = frame();
  cv.width = cv.height = size * px + 1;
  g.fillStyle = "#ffffff";
  g.fillRect(0, 0, cv.width, cv.height);
  const counts = new Map();
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const n = f[y * size + x];
    g.strokeStyle = "#d3d0dc";
    g.lineWidth = 1;
    g.strokeRect(x * px + .5, y * px + .5, px, px);
    if (n < 0) continue;
    counts.set(n, (counts.get(n) || 0) + 1);
    g.fillStyle = art.palette[n];
    g.beginPath();
    g.arc(x * px + px / 2 + .5, y * px + px / 2 + .5, px / 2 - 1.5, 0, Math.PI * 2);
    g.fill();
    g.strokeStyle = "#1b1530";
    g.stroke();
    g.fillStyle = "#ffffff";
    g.beginPath();
    g.arc(x * px + px / 2 + .5, y * px + px / 2 + .5, 2.5, 0, Math.PI * 2);
    g.fill();
  }
  const list = [...counts].sort((a, b) => b[1] - a[1]);
  $("beadTitle").textContent = art.title ? `Bead pattern: ${art.title}` : "Bead pattern";
  $("beadTotal").textContent = `${list.reduce((sum, c) => sum + c[1], 0)} beads in ${list.length} colours`;
  $("beadList").innerHTML = list.map(([n, count]) =>
    `<span><i style="background:${art.palette[n]}"></i>× ${count}</span>`).join("");
  $("beads").hidden = false;
}

// ---- Opening and starting drawings ----------------------------------------------------------
function openDrawing(saved) {
  art = Object.assign({}, saved, {frames: saved.frames.map(A.decode), palette: saved.palette.slice(), marks: saved.marks || "",
                                  names: (saved.names || saved.frames.map(() => "")).slice()});
  cur = 0;
  undoList = [];
  redoList = [];
  stroke = null;
  shape = null;
  shapeEnd = null;
  sel = null;
  zoom = 1;
  panAt = {x: 0, y: 0};
  if (colour >= art.palette.length) colour = A.INK;
  $("title").value = art.title;
  buildMine();
  buildGuideKey();
  refreshOptions();
  fitBoard();
  buildReel();
  showTip();
  savedSays("Saved ✓");
}
function newKey() {
  return Array.from(crypto.getRandomValues(new Uint8Array(6)), n => (n % 36).toString(36)).join("");
}
function startDrawing(size, pixels, title = "", guide = "") {
  openDrawing({key: newKey(), title, size, speed: 6, palette: A.PALETTE.slice(),
               frames: [A.encode(pixels || A.blank(size))], names: [""], guide});
  changed();
  closeShelf();
}
let galleryWay = "colour";
function galleryPicture(name) {
  const pic = PalGallery.pictures[name];
  return galleryWay === "ready" ? pic : PalGallery.outlined(pic);
}
function startFromGallery(name) {
  const pic = PalGallery.pictures[name];
  startDrawing(PalGallery.size, galleryPicture(name), name, galleryWay === "numbers" ? A.encode(pic) : "");
  if (art.guide) chooseColour(guideColours()[0]);
}
function buildGallery() {
  const full = shelfList.length >= limits.max_drawings;
  document.querySelectorAll("[data-way]").forEach(b => b.setAttribute("aria-pressed", b.dataset.way === galleryWay));
  $("gallery").innerHTML = PalGallery.names.map(name =>
    `<button data-gallery="${name}" ${full ? "disabled" : ""}><canvas></canvas>${name}</button>`).join("");
  for (const name of PalGallery.names) {
    thumbInto(document.querySelector(`[data-gallery="${name}"] canvas`), galleryPicture(name), PalGallery.size, A.PALETTE);
  }
}

async function openShelf() {
  settle();
  await saveNow();
  try {
    const data = await (await fetch("/pixel/state?id=" + encodeURIComponent(me))).json();
    if (data.drawings) shelfList = data.drawings;
  } catch (_) {}
  buildShelf();
  $("shelf").hidden = false;
  $("closeShelf").hidden = !art;
}
function closeShelf() { $("shelf").hidden = true; }

function buildShelf() {
  const full = shelfList.length >= limits.max_drawings;
  $("notMe").textContent = `Not ${name}?`;
  $("shelfTitle").textContent = shelfList.length ? "My drawings" : `Welcome, ${name}! Let's draw`;
  $("savedBlock").hidden = !shelfList.length;
  $("savedArt").innerHTML = shelfList.map(d => `
    <div class="saved-card${art && d.key === art.key ? " here" : ""}">
      <button data-open="${esc(d.key)}"><canvas></canvas><span>${esc(d.title || "No name yet")}</span></button>
      <button class="gone" data-gone="${esc(d.key)}">Delete</button>
    </div>`).join("");
  shelfList.forEach((d, i) => thumbInto($("savedArt").children[i].querySelector("canvas"),
                                        A.decode(d.frames[0]), d.size, d.palette));
  buildGallery();
  $("picks").innerHTML =
    SIZES.map(s =>
      `<button class="pick" data-size="${s.size}" ${full ? "disabled" : ""}><canvas></canvas>${s.name}<small>Blank, ${s.size} × ${s.size}</small></button>`).join("");
  SIZES.forEach(s => thumbInto(document.querySelector(`[data-size="${s.size}"] canvas`), A.blank(s.size), s.size, A.PALETTE));
  $("shelfNote").textContent = full
    ? `Your shelf is full with ${limits.max_drawings} drawings. Delete one to start another.`
    : "";
}

async function deleteDrawing(key, button) {
  if (!button.classList.contains("sure")) {     // a second click makes it certain
    button.classList.add("sure");
    button.textContent = "Click again to delete";
    return;
  }
  const open = art && art.key === key;
  if (open) { dirty = false; clearTimeout(saveTimer); }
  await post("/pixel/delete", {id: me, key}).catch(() => {});
  shelfList = shelfList.filter(d => d.key !== key);
  if (open) {
    art = null;
    if (shelfList.length) openDrawing(shelfList[0]);
  }
  buildShelf();
  $("closeShelf").hidden = !art;
}

// ---- Getting in -----------------------------------------------------------------------------
let joinTimer = 0;
// Four pals from the gallery, up and dancing before anyone has typed a thing.
function joinScene() {
  const cv = $("joinArt"), g = cv.getContext("2d");
  const names = PalGallery.names.slice().sort(() => Math.random() - .5).slice(0, 4);
  const pals = names.map((n, i) => PalStage.puppet({size: 16, palette: A.PALETTE, frames: [A.encode(PalGallery.pictures[n])]}, 5, i + 2));
  const moves = ["dance", "wave", "cheer", "walk"];
  g.imageSmoothingEnabled = false;
  const paint = () => {
    const t = performance.now() / 1000;
    g.clearRect(0, 0, cv.width, cv.height);
    pals.forEach((pup, i) => {
      const beat = Math.floor((t + i * 1.7) / 3), move = beat % 2 ? moves[(beat + i) % moves.length] : null;
      const pose = PalStage.livePose(pup.rigOf(0), pup.lifeline, t + i, {move, moveT: t + i * .2});
      pup.draw(g, 0, pose, 60 + i * 120, cv.height - 6);
    });
  };
  paint();
  joinTimer = setInterval(paint, 66);
  $("join").hidden = false;
  $("name").focus();
}
async function enter(id) {
  let data;
  try { data = await (await fetch("/pixel/state?id=" + encodeURIComponent(id))).json(); } catch (_) { return false; }
  if (!data.you) return false;
  me = id;
  name = data.you.name;
  shelfList = data.drawings;
  limits = {max_drawings: data.max_drawings, max_frames: data.max_frames};
  clearInterval(joinTimer);
  $("join").hidden = true;
  $("app").hidden = false;
  if (shelfList.length) openDrawing(shelfList[0]);
  else openDrawing({key: newKey(), title: "", size: 16, speed: 6, palette: A.PALETTE.slice(), frames: [A.encode(A.blank(16))], names: [""]});
  if (!shelfList.length) { buildShelf(); $("shelf").hidden = false; $("closeShelf").hidden = true; }
  requestAnimationFrame(playLoop);
  $("frameName").innerHTML = `<option value="">No name</option>` +
    data.poses.map(p => `<option>${esc(p)}</option>`).join("");
  $("frameName").value = art.names[cur] || "";
  pageEnter(data);
  return true;
}
async function join(event) {
  event.preventDefault();
  const typed = $("name").value.trim();
  if (!typed) { $("name").focus(); return; }
  $("joinButton").disabled = true;
  try {
    const player = await post("/join", {name: typed});
    store("mazeId", player.id);
    if (await enter(player.id)) return;
  } catch (_) {}
  $("joinButton").disabled = false;
  $("joinButton").textContent = "No answer. Try again";
}

// ---- Wiring ---------------------------------------------------------------------------------
buildTools();
$("joinForm").addEventListener("submit", join);

const board = $("board");
board.addEventListener("pointerdown", pointerDown);
board.addEventListener("pointermove", pointerMove);
board.addEventListener("pointerup", pointerUp);
board.addEventListener("pointercancel", () => { endStroke(); dropTheShape(); });
board.addEventListener("pointerleave", pointerLeave);
board.addEventListener("contextmenu", e => e.preventDefault());      // a two-finger tap
// A pinch on the touchpad zooms. Two fingers sliding moves around a zoomed picture.
let pinched = 0;
board.addEventListener("wheel", e => {
  e.preventDefault();
  if (e.ctrlKey) {
    pinched += e.deltaY;
    if (Math.abs(pinched) < 24) return;
    const r = board.getBoundingClientRect();
    setZoom(zoom + (pinched < 0 ? 1 : -1), {x: e.clientX - r.left - 2, y: e.clientY - r.top - 2});
    pinched = 0;
  } else if (zoom > 1) {
    panAt.x += e.deltaX;
    panAt.y += e.deltaY;
    repaint();
  }
}, {passive: false});

new ResizeObserver(fitBoard).observe($("boardBox"));

document.addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  const d = b.dataset;
  if (d.tool) chooseTool(d.tool);
  else if (d.brush) { brush = +d.brush; refreshOptions(); }
  else if (d.stamp) chooseStamp(d.stamp);
  else if (d.pen) { penStyle = d.pen; refreshOptions(); }
  else if (d.tone) addColour(d.tone);
  else if (d.shade) { shadeWay = +d.shade; refreshOptions(); showTip(); }
  else if (d.colour) chooseColour(+d.colour);
  else if (d.fps) { art.speed = +d.fps; refreshOptions(); changed(); }
  else if (d.frame) openFrame(+d.frame);
  else if (d.dx) changeWhole(f => A.shift(f, art.size, +d.dx, +d.dy));
  else if (d.open) { const pick = shelfList.find(s => s.key === d.open); openDrawing(pick); closeShelf(); }
  else if (d.gone) deleteDrawing(d.gone, b);
  else if (d.gallery) startFromGallery(d.gallery);
  else if (d.way) { galleryWay = d.way; buildGallery(); }
  else if (d.size) startDrawing(+d.size);
  if (!b.closest("#moreMenu") && b.id !== "openMore") hideMenu("moreMenu");
  if (!b.closest("#frameMenu") && b.id !== "frameMore") hideMenu("frameMenu");
});
function hideMenu(id) { $(id).hidden = true; }
function toggleMenu(id) { $(id).hidden = !$(id).hidden; }

function flipSwitch(id, turn) {
  $(id).addEventListener("click", () => { turn(); refreshOptions(); showTip(); repaint(); });
}
flipSwitch("solid", () => { solid = !solid; });
flipSwitch("easy", () => { settle(); easy = !easy; store("pixelEasyPen", easy ? "1" : "0"); });
flipSwitch("mirror", () => { mirror = !mirror; });
flipSwitch("grid", () => { showGrid = !showGrid; });
flipSwitch("showLast", () => { onion = !onion; });

$("undo").addEventListener("click", undo);
$("redo").addEventListener("click", redo);
$("flip").addEventListener("click", () => changeWhole(f => A.flip(f, art.size)));
$("clear").addEventListener("click", () => changeWhole(() => A.blank(art.size)));
$("spin").addEventListener("click", () => changeWhole(f => A.turn(f, art.size)));
$("outline").addEventListener("click", () => changeWhole(f => {
  const out = f.slice();
  for (const at of A.outline(f, art.size)) out[at] = colour;
  return out;
}));
// A new colour for every colour in the drawing, except its dark outline.
$("surprise").addEventListener("click", () => {
  settle();
  const before = snap(), used = [...new Set(art.frames.flat())].filter(n => n >= 0 && n !== A.INK);
  const pool = A.PALETTE.map((_, i) => i).filter(i => i !== A.INK && i !== 9).sort(() => Math.random() - .5);
  const swap = new Map(used.map((n, i) => [n, pool[i % pool.length]]));
  art.frames = art.frames.map(f => f.map(n => swap.has(n) ? swap.get(n) : n));
  buildReel();
  done(before);
});
$("openMore").addEventListener("click", () => toggleMenu("moreMenu"));
$("closeMore").addEventListener("click", () => hideMenu("moreMenu"));
$("frameMore").addEventListener("click", () => toggleMenu("frameMenu"));
$("closeFrameMenu").addEventListener("click", () => hideMenu("frameMenu"));
$("zoomIn").addEventListener("click", () => setZoom(zoom + 1));
$("zoomOut").addEventListener("click", () => setZoom(zoom - 1));
$("selectAll").addEventListener("click", selectEverything);
$("selCopy").addEventListener("click", () => {
  pasteSel(frame());
  sel.before = snap();
  if (sel.x + 1 + sel.w <= art.size) sel.x++;
  if (sel.y + 1 + sel.h <= art.size) sel.y++;
  changed();
  tipNow("Copied! Now slide the new one.");
  repaint();
});
$("selFlip").addEventListener("click", () => {
  const out = [];
  for (let y = 0; y < sel.h; y++) for (let x = sel.w - 1; x >= 0; x--) out.push(sel.pix[y * sel.w + x]);
  sel.pix = out;
  repaint();
});
$("selDelete").addEventListener("click", () => { sel.pix = sel.pix.map(() => -1); dropSel(); });
$("copyFrame").addEventListener("click", () => addFrame(frame().slice()));
$("newFrame").addEventListener("click", () => addFrame(A.blank(art.size)));
$("frameLeft").addEventListener("click", () => moveFrame(-1));
$("frameRight").addEventListener("click", () => moveFrame(1));
$("deleteFrame").addEventListener("click", deleteFrame);
$("download").addEventListener("click", download);
$("seeCode").addEventListener("click", showArtSheet);
$("closeArt").addEventListener("click", closeArtSheet);
$("artCode").addEventListener("input", artTyped);
$("seeBeads").addEventListener("click", showBeads);
$("closeBeads").addEventListener("click", () => { $("beads").hidden = true; });
function printSheet(id) {
  $(id).classList.add("printing");
  print();
  $(id).classList.remove("printing");
}
$("printBeads").addEventListener("click", () => printSheet("beads"));
$("openShelf").addEventListener("click", openShelf);
$("closeShelf").addEventListener("click", closeShelf);
// Typing a name again finds that student's work, so nothing is lost by this.
$("notMe").addEventListener("click", async () => {
  await saveNow();
  store("mazeId", "");
  location.reload();
});
$("frameName").addEventListener("change", e => nameFrame(e.target.value));
$("mix").addEventListener("change", e => addColour(e.target.value));
$("title").addEventListener("input", e => { art.title = e.target.value; changed(); });

addEventListener("keydown", e => {
  const typing = e.target.matches("input");
  if ((e.ctrlKey || e.metaKey) && !typing && e.key.toLowerCase() === "z") {
    e.preventDefault();
    if (!$("drawView").hidden) { if (e.shiftKey) redo(); else undo(); }
  } else if ((e.ctrlKey || e.metaKey) && !typing && e.key.toLowerCase() === "y") {
    e.preventDefault();
    if (!$("drawView").hidden) redo();
  } else if (e.key === "Escape") {
    if (!$("shelf").hidden && art && !$("closeShelf").hidden) closeShelf();
    hideMenu("moreMenu");
    hideMenu("frameMenu");
    settle();
  } else if (sel && !typing && e.key.startsWith("Arrow")) {
    e.preventDefault();
    sel.x += {ArrowLeft: -1, ArrowRight: 1}[e.key] || 0;
    sel.y += {ArrowUp: -1, ArrowDown: 1}[e.key] || 0;
    repaint();
  }
});

// pixel_page.js starts things off once it has loaded.
async function boot() {
  const id = recall("mazeId");
  if (!id || !(await enter(id))) joinScene();
}
