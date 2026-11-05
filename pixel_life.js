// Pixel Pals: bringing a drawing to life. The little pal in the Studio's corner
// watches the pen, and the Life tab shows the parts the computer found, lets the
// student fix them, and tries out every move.
"use strict";

// The drawing that's open, in the shape the stage wants.
function artAsPal() {
  return {size: art.size, palette: art.palette, frames: art.frames.map(A.encode), names: art.names,
          speed: art.speed, marks: art.marks || ""};
}

// ---- The live pal in the corner of the Studio --------------------------------------------------
let mini = null, miniText = "", miniKey = "", miniMove = null, miniMoveAt = 0, miniBorn = performance.now();

// The parts a pal can have, and what it does the moment you draw one.
const PART_CHIPS = [
  {key: "eyes", icon: "👀", word: "Eyes", has: r => r.eyes.length > 0, move: "happy", cheer: "👀 Your pal opened its eyes!"},
  {key: "mouth", icon: "👄", word: "Mouth", has: r => !!r.mouth, move: "giggle", cheer: "👄 Now your pal can talk!"},
  {key: "arms", icon: "💪", word: "Arms", has: r => r.arms.length > 0, move: "wave", cheer: "💪 Arms! Your pal can wave!"},
  {key: "legs", icon: "🦵", word: "Legs", has: r => r.legs.length > 0, move: "walk", cheer: "🦵 Legs! Your pal can walk!"},
  {key: "ears", icon: "🐰", word: "Ears", has: r => r.limbs.some(l => l.kind === "ear"), move: "dance", cheer: "🐰 Look at those ears go!"},
  {key: "tail", icon: "🐾", word: "Tail", has: r => r.limbs.some(l => l.kind === "tail" || l.kind === "wing"), move: "dance", cheer: "🐾 Wag, wag, wag!"},
];
let miniHad = null;       // which parts the drawing had last time we looked

function freshMini() {
  const text = A.encode(art.frames[0]) + art.palette.length + (art.marks || "");
  if (text === miniText) return;
  miniText = text;
  mini = PalStage.puppet(artAsPal(), 1, art.size + art.palette.length);
  const rig = mini.rigOf(0), now = new Set(PART_CHIPS.filter(c => !rig.empty && c.has(rig)).map(c => c.key));
  // Opening a drawing isn't news. Only a part that has just been drawn is.
  if (miniHad && miniKey === art.key) {
    const fresh = PART_CHIPS.find(c => now.has(c.key) && !miniHad.has(c.key));
    if (fresh) partDrawn(fresh);
  }
  miniHad = now;
  miniKey = art.key;
  document.querySelectorAll("[data-chip-part]").forEach(el => el.classList.toggle("on", now.has(el.dataset.chipPart)));
}
function partDrawn(chip) {
  miniMove = chip.move;
  miniMoveAt = performance.now();
  $("toast").textContent = chip.cheer;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 3200);
  PalStage.SFX.play("ding");
}

function guideFinished() {
  miniMove = "cheer";
  miniMoveAt = performance.now();
  $("toast").textContent = "🎉 You finished it! Press ✨ Bring to life!";
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4200);
  PalStage.SFX.play("tada");
}

function livePreview(now) {
  const cv = $("preview"), rig = mini.rigOf(0), room = Math.ceil(art.size * 1.4);
  if (cv.width !== room) cv.width = cv.height = room;
  const g = cv.getContext("2d");
  g.clearRect(0, 0, room, room);
  if (rig.empty) return;
  const t = (now - miniBorn) / 1000;
  let aim = null;
  if (hover) {                    // it watches the pen
    const dx = hover.x - rig.axis, dy = hover.y - (rig.top + rig.neck) / 2;
    aim = [Math.abs(dx) > art.size / 6 ? Math.sign(dx) : 0, Math.abs(dy) > art.size / 5 ? Math.sign(dy) : 0];
  }
  if (miniMove && (now - miniMoveAt) / 1000 > (PixelRig.LASTS[miniMove] || 1)) miniMove = null;
  const pose = PalStage.livePose(rig, mini.lifeline, t, {move: miniMove, moveT: (now - miniMoveAt) / 1000, aim});
  mini.draw(g, 0, pose, room / 2, room - Math.round(art.size * .1));
}

// ---- The Life tab ------------------------------------------------------------------------------
const MOVE_BUTTONS = [
  ["👋", "Wave", {do: "wave"}], ["🚶", "Walk", null], ["💃", "Dance", {do: "dance"}],
  ["🦘", "Jump", {do: "jump"}], ["🎉", "Cheer", {do: "cheer"}], ["😴", "Nap", {do: "nap"}],
  ["😊", "Happy", {do: "feel", mood: "happy"}], ["😢", "Sad", {do: "feel", mood: "sad"}],
  ["😮", "Wow", {do: "feel", mood: "surprised"}], ["😠", "Cross", {do: "feel", mood: "angry"}],
  ["🤪", "Silly", {do: "feel", mood: "silly"}], ["😎", "Cool", {do: "feel", mood: "cool"}],
];
const WALK_THERE = [{do: "walk", to: 8, by: 6}, {do: "walk", to: 2, by: 6}];
// What each move is called in the rig, for making frames and GIFs of it.
const RIG_MOVES = {Wave: "wave", Walk: "walk", Dance: "dance", Jump: "jump", Cheer: "cheer", Nap: "sleep",
                   Happy: "happy", Sad: "sad", Wow: "surprised", Cross: "cross", Silly: "giggle", Cool: "idle"};
const BONE_KEYS = [
  ["o", "👀 Eyes", "#1b1530"], ["m", "👄 Mouth", "#e8294f"], ["a", "💪 Arm", "#ff8a2a"], ["l", "🦵 Leg", "#2f6fe4"],
  ["e", "🐰 Ear", "#2fa84f"], ["t", "🐾 Tail", "#c2258c"], ["w", "🦋 Wing", "#7a3fe4"], ["b", "🧽 Body", "#d3d0dc"],
];
const KIND_INK = {arm: "#ff8a2a", leg: "#2f6fe4", ear: "#2fa84f", tail: "#c2258c", wing: "#7a3fe4"};

let lifeStage = null, boneKey = null, painting = false, lastMove = "Wave", lifeRig = null;

function buildLifeTab() {
  $("moves").innerHTML = MOVE_BUTTONS.map(([icon, word]) =>
    `<button data-move="${word}" aria-pressed="false"><span>${icon}</span>${word}</button>`).join("");
  $("boneKeys").innerHTML = BONE_KEYS.map(([key, word, ink]) =>
    `<button data-bone="${key}" aria-pressed="false"><i style="background:${ink}"></i>${word}</button>`).join("");
}

function openLife() {
  if (!lifeStage) lifeStage = PalStage.create($("lifeCanvas"), $("lifeHost"));
  lifeStage.setPal(artAsPal());
  lifeStage.fresh();
  lifeStage.state.scene = "park";
  boneKey = null;
  refreshBones();
  fitLifeScreen();
  wakeUp();
}
// The first time a pal is brought to life, it opens its eyes and says hello.
const wokenPals = new Set();
function wakeUp() {
  if (wokenPals.has(art.key) || lifeRig.empty) return;
  wokenPals.add(art.key);
  if (!lifeRig.eyes.length) return;
  const words = art.title ? `Hello ${name}! I'm ${art.title}!` : `Hello ${name}! You made me!`;
  lifeStage.state.mood = "sleepy";
  lifeStage.play([{do: "wait", beats: 2}, {do: "feel", mood: "calm"}, {do: "say", text: words}, {do: "wave"}]);
}
function closeLife() { if (lifeStage) lifeStage.stop(); }

function fitLifeScreen() {
  const wrap = $("lifeHost").parentElement, host = $("lifeHost");
  const width = Math.min(wrap.clientWidth - 8, (wrap.clientHeight - 8) * 16 / 9);
  host.style.width = Math.max(120, Math.floor(width)) + "px";
}

function refreshBones() {
  lifeRig = PixelRig.build(art.frames[0], art.size, art.palette, art.marks || "");
  paintBones();
  document.querySelectorAll("[data-bone]").forEach(b => b.setAttribute("aria-pressed", b.dataset.bone === boneKey));
  $("boneNote").innerHTML = boneKey ? `<b>${esc(BONE_KEYS.find(k => k[0] === boneKey)[1])}:</b> click the squares that belong to it.` : boneWords(lifeRig);
  $("bonesAgain").hidden = !(art.marks || "").replace(/\./g, "");
  document.querySelector('[data-move="Wave"]').title = lifeRig.arms.length ? "" : "Your pal has no arms yet, so it wiggles";
}

function boneWords(rig) {
  if (rig.empty) return "There's nothing here yet. Go to 🎨 Draw and make your pal first!";
  const count = kind => rig.limbs.filter(l => l.kind === kind).length;
  const say = (n, one, many) => n ? `${n === 1 ? "1 " + one : n + " " + many}` : "";
  const list = [say(rig.eyes.length, "eye", "eyes"), rig.mouth ? "a mouth" : "", say(count("arm"), "arm", "arms"), say(count("leg"), "leg", "legs"),
                say(count("ear"), "ear", "ears"), say(count("tail"), "tail", "tails"), say(count("wing"), "wing", "wings")].filter(Boolean);
  const found = list.length ? `I found ${list.length > 1 ? list.slice(0, -1).join(", ") + " and " + list[list.length - 1] : list[0]}.` : "I can't find any parts yet.";
  if (!rig.eyes.length) return `${found} <b>No eyes yet!</b> Draw two dots on its face in 🎨 Draw. Or press 👀 Eyes and click them here.`;
  return `${found} Wrong? Press a part, then click the squares.`;
}

function paintBones() {
  const cv = $("boneBoard"), size = art.size, px = Math.max(4, Math.floor(320 / size));
  if (cv.width !== size * px) cv.width = cv.height = size * px;
  const g = cv.getContext("2d"), f = art.frames[0], rig = lifeRig;
  paintChecks(g, size, px);
  paintFrame(g, f, size, px, art.palette);
  const eyes = new Set(rig.eyes.flatMap(e => e.at)), mouth = new Set(rig.mouth ? rig.mouth.at : []);
  g.lineWidth = 2;
  for (const limb of rig.limbs) {
    g.fillStyle = KIND_INK[limb.kind] + "aa";
    for (const n of limb.at) g.fillRect(n % size * px, Math.floor(n / size) * px, px, px);
  }
  for (const [list, ink] of [[eyes, "#ffd93b"], [mouth, "#ff5fa2"]]) {
    g.strokeStyle = ink;
    for (const n of list) g.strokeRect(n % size * px + 1, Math.floor(n / size) * px + 1, px - 2, px - 2);
  }
  // Each joint, with a bone out to the tip.
  for (const limb of rig.limbs) {
    const x = (limb.pivot[0] + .5) * px, y = (limb.pivot[1] + .5) * px;
    g.strokeStyle = "#ffffff";
    g.lineWidth = Math.max(2, px / 3);
    g.beginPath(); g.moveTo(x, y); g.lineTo((limb.tip[0] + .5) * px, (limb.tip[1] + .5) * px); g.stroke();
    g.fillStyle = "#ffffff"; g.beginPath(); g.arc(x, y, px * .55, 0, 7); g.fill();
    g.fillStyle = "#1b1530"; g.beginPath(); g.arc(x, y, px * .3, 0, 7); g.fill();
  }
}

function boneSquare(e) {
  const r = $("boneBoard").getBoundingClientRect();
  const x = Math.floor((e.clientX - r.left - 2) / (r.width - 4) * art.size), y = Math.floor((e.clientY - r.top - 2) / (r.height - 4) * art.size);
  return x >= 0 && y >= 0 && x < art.size && y < art.size ? y * art.size + x : -1;
}
function markSquare(n) {
  if (n < 0 || !boneKey || art.frames[0][n] < 0) return;
  const now = art.marks && art.marks.length === art.frames[0].length ? art.marks : ".".repeat(art.frames[0].length);
  if (now[n] === boneKey) return;
  art.marks = now.slice(0, n) + boneKey + now.slice(n + 1);
  refreshBones();
  lifeStage.setPal(artAsPal());
  changed();
}

let moveTicket = 0;
async function playMove(word) {
  lastMove = word;
  const ticket = ++moveTicket;
  document.querySelectorAll("[data-move]").forEach(b => b.setAttribute("aria-pressed", b.dataset.move === word));
  const entry = MOVE_BUTTONS.find(m => m[1] === word);
  const spot = lifeStage.state.spot;
  // Pressing a face again puts it away.
  const again = entry[2] && entry[2].mood && lifeStage.state.mood === entry[2].mood;
  const steps = again ? [{do: "feel", mood: "calm"}] : entry[2] ? [entry[2]]
    : [{do: "walk", to: 8, by: Math.abs(8 - spot)}, {do: "walk", to: 2, by: 6}];
  await lifeStage.play(steps);
  if (ticket === moveTicket) document.querySelectorAll("[data-move]").forEach(b => b.setAttribute("aria-pressed", "false"));
}

// The move as a row of pictures, with the moving parts sitting in the frame.
function movePictures(word, count) {
  const name = RIG_MOVES[word], rig = lifeRig, last = PixelRig.LASTS[name] || 1, out = [];
  for (let i = 0; i < count; i++) {
    const t = name === "jump" ? i / (count - 1) : (name === "walk" ? .46 : last) * i / count;
    const face = {};
    const mood = {Happy: "happy", Sad: "sad", Wow: "surprised", Cross: "angry", Silly: "silly", Cool: "cool"}[word];
    if (mood) Object.assign(face, PixelRig.MOODS[mood]);
    out.push(PixelRig.render(rig, art.frames[0], PixelRig.tidy(Object.assign({}, PixelRig.pose(name, t, rig), face))));
  }
  return out;
}
function gifMove() {
  const pics = movePictures(lastMove, 8), wide = lifeRig.wide;
  const file = A.gif(pics.map(p => Array.from(p)), wide, Math.max(2, Math.floor(400 / wide)), art.palette, 10);
  hand(new Blob([file], {type: "image/gif"}), fileName(`-${lastMove.toLowerCase()}.gif`));
}
// Frames she can then change by hand. They're cut down to the size of her canvas.
function bakeMove() {
  const free = limits.max_frames - art.frames.length;
  if (free < 2) { $("boneNote").innerHTML = "<b>No room!</b> Delete some frames in 🎨 Draw first."; return; }
  const pics = movePictures(lastMove, Math.min(6, free)), {pad, wide, size} = lifeRig;
  const before = snap();
  cur = art.frames.length - 1;
  for (const pic of pics) {
    const f = A.blank(size);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) f[y * size + x] = pic[(y + pad) * wide + x + pad];
    art.frames.push(f);
    art.names.push("");
  }
  cur = art.frames.length - pics.length;
  buildReel();
  done(before);
  $("boneNote").innerHTML = `<b>Done!</b> ${pics.length} new frames are in 🎨 Draw. Change them however you like.`;
}

buildLifeTab();
$("partChips").innerHTML = PART_CHIPS.map(c => `<span data-chip-part="${c.key}" title="${c.word}">${c.icon}</span>`).join("");
new ResizeObserver(fitLifeScreen).observe($("lifeHost").parentElement);

$("moves").addEventListener("click", e => {
  const b = e.target.closest("[data-move]");
  if (b) playMove(b.dataset.move);
});
$("boneKeys").addEventListener("click", e => {
  const b = e.target.closest("[data-bone]");
  if (!b) return;
  boneKey = boneKey === b.dataset.bone ? null : b.dataset.bone;
  refreshBones();
});
const boneBoard = $("boneBoard");
boneBoard.addEventListener("pointerdown", e => {
  if (!boneKey) { $("boneNote").innerHTML = "Press a part first, like 💪 Arm. Then click the squares."; return; }
  painting = true;
  boneBoard.setPointerCapture(e.pointerId);
  markSquare(boneSquare(e));
});
boneBoard.addEventListener("pointermove", e => { if (painting) markSquare(boneSquare(e)); });
boneBoard.addEventListener("pointerup", () => { painting = false; });
$("bonesAgain").addEventListener("click", () => {
  art.marks = "";
  boneKey = null;
  refreshBones();
  lifeStage.setPal(artAsPal());
  changed();
});
$("bakeMove").addEventListener("click", bakeMove);
$("gifMove").addEventListener("click", gifMove);

// Talking, poking, and watching the pointer.
$("lifeSay").addEventListener("submit", e => {
  e.preventDefault();
  const text = $("lifeWords").value.trim();
  if (!text) return;
  $("lifeWords").value = "";
  lifeStage.play([{do: "say", text}]);
});
const lifeCanvas = $("lifeCanvas");
function onLifeCanvas(e) {
  const r = lifeCanvas.getBoundingClientRect();
  return [(e.clientX - r.left) / r.width * PalStage.W, (e.clientY - r.top) / r.height * PalStage.H];
}
lifeCanvas.addEventListener("pointermove", e => { const [x, y] = onLifeCanvas(e); lifeStage.aim(x, y); });
lifeCanvas.addEventListener("pointerleave", () => lifeStage.aim(null));
lifeCanvas.addEventListener("click", e => {
  const [x, y] = onLifeCanvas(e);
  if (lifeStage.touching(x, y)) lifeStage.play([{do: "giggle"}]);
});

// ---- The Class Park: every shared pal, out together ---------------------------------------------
let parkPals = [], parkFrame = 0, parkLast = 0;
const PARK_GROUND = 188;

function openPark(list) {
  const seen = new Set();
  parkPals = list.filter(s => {
    const same = seen.has(s.pal.frames[0]);
    seen.add(s.pal.frames[0]);
    return !same;
  }).slice(0, 20).map((s, i) => ({
    pup: PalStage.puppet(s.pal, Math.max(1, Math.round(96 / s.pal.size)), i + 11), by: s.by, x: 60 + (i * 197) % 840,
    way: i % 2 ? -1 : 1, move: null, moveAt: 0, until: 0, hearts: 0,
  }));
  $("park").hidden = !parkPals.length;
  if (parkPals.length && !parkFrame) parkFrame = requestAnimationFrame(paintPark);
}
function closePark() {
  cancelAnimationFrame(parkFrame);
  parkFrame = 0;
}
function parkDo(p, move, seconds, now) {
  p.move = move;
  p.moveAt = now;
  p.until = now + seconds * 1000;
}
// Stand a while, then stroll somewhere. Two pals who meet say hello.
function wander(p, now, dt) {
  if (p.move === "walk") {
    p.x += p.way * dt * .05;
    if (p.x < 40 || p.x > 920) p.way = -p.way;
    const near = parkPals.find(q => q !== p && !q.move && Math.abs(q.x - p.x) < 90);
    if (near && Math.random() < .004) {
      parkDo(p, "wave", 1.4, now);
      parkDo(near, "wave", 1.4, now);
      near.way = p.x < near.x ? -1 : 1;
      p.way = -near.way;
    }
  }
  if (now < p.until) return;
  if (p.move) { p.move = null; p.until = now + 900 + Math.random() * 3200; return; }
  if (Math.random() < .75) { p.way = Math.random() < .5 ? -1 : 1; parkDo(p, "walk", 1.5 + Math.random() * 3, now); }
  else parkDo(p, Math.random() < .5 ? "dance" : "happy", 1.6, now);
}
function paintPark(now) {
  parkFrame = requestAnimationFrame(paintPark);
  const dt = Math.min(50, now - (parkLast || now)), cv = $("park"), g = cv.getContext("2d");
  parkLast = now;
  g.imageSmoothingEnabled = false;
  g.drawImage(PalStage.sceneArt("park"), 0, 98, 320, 70, 0, 0, 960, 210);
  const order = parkPals.slice().sort((a, b) => a.x - b.x);
  for (const p of order) {
    wander(p, now, dt);
    const rig = p.pup.rigOf(0);
    const pose = PalStage.livePose(rig, p.pup.lifeline, now / 1000, {move: p.move, moveT: (now - p.moveAt) / 1000});
    p.pup.draw(g, 0, pose, p.x, PARK_GROUND, {flip: p.way < 0});
    g.font = "800 15px ui-rounded, system-ui, sans-serif";
    g.textAlign = "center";
    g.lineWidth = 4;
    g.lineJoin = "round";
    g.strokeStyle = "#ffffff";
    g.strokeText(p.by, p.x, PARK_GROUND + 17);
    g.fillStyle = "#1b1530";
    g.fillText(p.by, p.x, PARK_GROUND + 17);
    if (p.hearts > now) {
      const up = (p.hearts - now) / 12;
      g.drawImage(PalStage.HEART, p.x - 21, PARK_GROUND - 130 + up - 60, 42, 36);
    }
  }
}
$("park").addEventListener("click", e => {
  const r = $("park").getBoundingClientRect(), x = (e.clientX - r.left) / r.width * 960, now = performance.now();
  const hit = parkPals.slice().sort((a, b) => Math.abs(a.x - x) - Math.abs(b.x - x))[0];
  if (!hit || Math.abs(hit.x - x) > 70) return;
  parkDo(hit, "cheer", 1.3, now);
  hit.hearts = now + 900;
  PalStage.SFX.play("ding");
});

$("preview").addEventListener("click", () => {
  if (art.frames.length > 1) return;
  miniMove = "giggle";
  miniMoveAt = performance.now();
});
$("quick").addEventListener("click", e => {
  const b = e.target.closest("[data-quick]");
  if (!b) return;
  miniMove = b.dataset.quick;
  miniMoveAt = performance.now();
});
$("toLife").addEventListener("click", () => showView("life"));
