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
  if (!mini) return;
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
  lifeSeen = performance.now();
  dozing = false;
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
  tellServer("/pixel/game", {game: "alive"});
  const words = art.title ? `Hello ${name}! I'm ${art.title}!` : `Hello ${name}! You made me!`;
  lifeStage.state.mood = "sleepy";
  act([{do: "wait", beats: 2}, {do: "feel", mood: "calm"}, {do: "say", text: words}, {do: "wave"}]);
}
function closeLife() {
  endGame(false);
  if (lifeStage) lifeStage.stop();
}

function fitLifeScreen() {
  const wrap = $("lifeHost").parentElement, host = $("lifeHost");
  const width = Math.min(wrap.clientWidth - 8, (wrap.clientHeight - 8) * 16 / 9);
  host.style.width = Math.max(120, Math.floor(width)) + "px";
}

let playing = false;     // a game is on, so the pal doesn't wander off
function tellServer(path, data) {
  post(path, Object.assign({id: me}, data)).then(out => {
    if (out.badges && out.badges.length) showRewards({badges: out.badges});
  }).catch(() => {});
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
  if (copying) { copyAnswer(word); return; }
  if (playing) return;
  lastMove = word;
  const ticket = ++moveTicket;
  noticed();
  document.querySelectorAll("[data-move]").forEach(b => b.setAttribute("aria-pressed", b.dataset.move === word));
  const entry = MOVE_BUTTONS.find(m => m[1] === word);
  const spot = lifeStage.state.spot;
  // Pressing a face again puts it away.
  const again = entry[2] && entry[2].mood && lifeStage.state.mood === entry[2].mood;
  const steps = again ? [{do: "feel", mood: "calm"}] : entry[2] ? [entry[2]]
    : [{do: "walk", to: 8, by: Math.abs(8 - spot)}, {do: "walk", to: 2, by: 6}];
  await act(steps);
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
$("playCatch").addEventListener("click", startCatch);
$("playCopy").addEventListener("click", startCopy);
$("gameStop").addEventListener("click", () => endGame(false));
$("openCard").addEventListener("click", () => { drawCard(); $("cardSheet").hidden = false; });
$("closeCard").addEventListener("click", () => { $("cardSheet").hidden = true; });
$("printCard").addEventListener("click", () => printSheet("cardSheet"));
$("saveCard").addEventListener("click", () => $("cardCanvas").toBlob(blob => hand(blob, fileName("-card.png"))));
$("nextPlace").addEventListener("click", () => {
  const open = S.kit.scenes, at = open.indexOf(lifeStage.state.scene);
  noticed();
  act([{do: "scene", name: open[(at + 1) % open.length]}]);
});
addEventListener("keydown", e => {
  if (!catching || !["ArrowLeft", "ArrowRight"].includes(e.key)) return;
  e.preventDefault();
  catching.aim = Math.max(10, Math.min(PalStage.W - 10, lifeStage.state.x + (e.key === "ArrowLeft" ? -40 : 40)));
});
$("bakeMove").addEventListener("click", bakeMove);
$("gifMove").addEventListener("click", gifMove);

// Talking, poking, and watching the pointer.
$("lifeSay").addEventListener("submit", e => {
  e.preventDefault();
  const text = $("lifeWords").value.trim();
  if (!text) return;
  $("lifeWords").value = "";
  noticed();
  act([{do: "say", text}]);
});
const lifeCanvas = $("lifeCanvas");
function onLifeCanvas(e) {
  const r = lifeCanvas.getBoundingClientRect();
  return [(e.clientX - r.left) / r.width * PalStage.W, (e.clientY - r.top) / r.height * PalStage.H];
}
lifeCanvas.addEventListener("pointermove", e => {
  const [x, y] = onLifeCanvas(e);
  noticed();
  if (catching) catching.aim = x; else lifeStage.aim(x, y);
});
lifeCanvas.addEventListener("pointerleave", () => lifeStage.aim(null));
lifeCanvas.addEventListener("click", e => {
  const [x, y] = onLifeCanvas(e);
  noticed();
  if (playing) return;
  if (lifeStage.touching(x, y)) { act([{do: "giggle"}]); return; }
  const spot = Math.max(0, Math.min(10, Math.round((x - 26) / 26.8)));     // come here!
  act([{do: "walk", to: spot}]);
});

// ---- Catch the stars: slide your finger and your pal runs ---------------------------------------
const CATCH_SECONDS = 30, GROUND = 162;
const FALLING = [{prop: "star", points: 1, odds: 62}, {prop: "gem", points: 3, odds: 14}, {prop: "cake", points: 2, odds: 8}, {prop: "ball", points: -2, odds: 16}];
let catching = null, catchFrame = 0, copying = null;

function hud(words) {
  $("gameHud").hidden = !words;
  $("gameWords").textContent = words || "";
}
function bestCatch() { return +(recall("pixelBestCatch") || 0); }

function startCatch() {
  if (playing || lifeRig.empty) return;
  noticed();
  playing = true;
  lifeBusy = false;
  lifeStage.stop();
  const st = lifeStage.state;
  Object.assign(st, {move: null, y: 0, tilt: 0, mood: null, talk: false});
  catching = {aim: st.x, score: 0, left: CATCH_SECONDS, items: [], drop: 0, last: performance.now(), wall: 0};
  $("gameLayer").hidden = false;
  $("gameLayer").width = PalStage.W;
  $("gameLayer").height = PalStage.H;
  catchFrame = requestAnimationFrame(catchStep);
}
function pickFalling() {
  let roll = Math.random() * 100;
  return FALLING.find(f => (roll -= f.odds) < 0) || FALLING[0];
}
function catchStep(now) {
  if (!catching) return;
  catchFrame = requestAnimationFrame(catchStep);
  const c = catching, st = lifeStage.state, dt = Math.min(50, now - c.last);
  c.last = now;
  c.left -= dt / 1000;
  // It gets busier as the time runs out.
  const hurry = 1 + (CATCH_SECONDS - c.left) / CATCH_SECONDS;
  c.drop -= dt;
  if (c.drop <= 0) {
    c.drop = 620 / hurry;
    c.items.push({x: 16 + Math.random() * (PalStage.W - 32), y: -24, vy: (.7 + Math.random() * .5) * hurry, kind: pickFalling()});
  }
  const gap = c.aim - st.x, speed = dt * .22;
  if (Math.abs(gap) > 2) {
    st.x += Math.sign(gap) * Math.min(Math.abs(gap), speed);
    st.flip = gap < 0;
    if (st.move !== "walk") { st.move = "walk"; st.moveFrom = now; }
  } else st.move = null;
  const g = $("gameLayer").getContext("2d");
  g.clearRect(0, 0, PalStage.W, PalStage.H);
  g.imageSmoothingEnabled = false;
  const reach = Math.max(20, lifeRig.size * Math.floor(68 / lifeRig.size) * .4);
  c.items = c.items.filter(item => {
    item.y += item.vy * dt / 16;
    const img = PalStage.PROPS[item.kind.prop];
    g.drawImage(img, Math.round(item.x - img.width / 2), Math.round(item.y));
    if (item.y > GROUND - 62 && item.y < GROUND && Math.abs(item.x - st.x) < reach) {
      c.score = Math.max(0, c.score + item.kind.points);
      PalStage.SFX.play(item.kind.points > 0 ? "ding" : "nope");
      if (item.kind.points < 0) { st.mood = "surprised"; setTimeout(() => { if (catching) st.mood = null; }, 450); }
      return false;
    }
    return item.y < PalStage.H;
  });
  hud(`★ ${c.score}   ${Math.ceil(c.left)}s`);
  if (c.left <= 0) endGame(true);
}
function endGame(finished) {
  if (catching) {
    const score = catching.score, best = bestCatch();
    cancelAnimationFrame(catchFrame);
    catching = null;
    $("gameLayer").hidden = true;
    lifeStage.state.move = null;
    if (finished) {
      if (score > best) {
        store("pixelBestCatch", score);
        tellServer("/pixel/caught", {score});
      }
      act([{do: "cheer"}, {do: "say", text: score > best ? `${score}! That's my best ever!` : `I got ${score}! Best is ${best}.`}]);
    }
  }
  copying = null;
  playing = false;
  hud("");
}

// ---- Copy me: a row of moves to do back, one longer each time ---------------------------------
const COPY_MOVES = ["Wave", "Jump", "Happy", "Sad", "Wow", "Cool"];

function startCopy() {
  if (playing || lifeRig.empty) return;
  noticed();
  playing = true;
  copying = {list: [], at: 0, turn: false};
  copyRound();
}
function light(word, on) {
  const b = document.querySelector(`[data-move="${word}"]`);
  if (b) b.setAttribute("aria-pressed", on ? "true" : "false");
}
async function copyRound() {
  const c = copying;
  c.list.push(COPY_MOVES[Math.floor(Math.random() * COPY_MOVES.length)]);
  if (c.list.length < 2) c.list.push(COPY_MOVES[Math.floor(Math.random() * COPY_MOVES.length)]);
  c.at = 0;
  c.turn = false;
  hud(`Watch! ${c.list.length} moves`);
  await lifeStage.play([{do: "feel", mood: "calm"}, {do: "wait", beats: 1}]);
  for (const word of c.list) {
    if (copying !== c) return;
    light(word, true);
    await lifeStage.play([MOVE_BUTTONS.find(m => m[1] === word)[2], {do: "wait", beats: 1}]);
    light(word, false);
    await lifeStage.play([{do: "feel", mood: "calm"}]);
  }
  if (copying !== c) return;
  c.turn = true;
  hud(`Your turn! ${c.list.length} moves`);
}
async function copyAnswer(word) {
  const c = copying;
  if (!c.turn) return;
  if (word === c.list[c.at]) {
    c.at++;
    lifeStage.act("noop");
    lifeStage.state.mood = (MOVE_BUTTONS.find(m => m[1] === word)[2] || {}).mood || null;
    PalStage.SFX.play("ding");
    if (c.at < c.list.length) return;
    c.turn = false;
    await lifeStage.play([{do: "cheer"}]);
    if (copying === c) copyRound();
    return;
  }
  const score = c.list.length - 1;
  tellServer("/pixel/game", {game: "copy", score});
  copying = null;
  playing = false;
  hud("");
  act([{do: "feel", mood: "sad"}, {do: "say", text: score > 1 ? `Oops! You got ${score} right!` : "Oops! Try again?"}, {do: "feel", mood: "calm"}]);
}

// ---- A trading card -----------------------------------------------------------------------------
const CARD_TRAITS = ["Loves long naps", "Always a bit hungry", "Brave when it counts", "Shy at first", "Super silly", "Best dancer in class",
                     "Tells great jokes", "Afraid of nothing", "Collects shiny things", "Very good at hugs", "Sings in the rain", "Never stops bouncing"];
function palHash() {
  let h = 7;
  for (const ch of A.encode(art.frames[0])) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return h;
}
function mainColour() {
  const counts = new Map();
  for (const n of art.frames[0]) if (n >= 0 && n !== A.INK) counts.set(n, (counts.get(n) || 0) + 1);
  const top = [...counts].sort((a, b) => b[1] - a[1])[0];
  return top ? art.palette[top[0]] : "#ff5fa2";
}
function drawCard() {
  const cv = $("cardCanvas"), g = cv.getContext("2d"), W2 = cv.width, H2 = cv.height, rig = lifeRig, ink = "#1b1530";
  const hash = palHash(), colour = mainColour();
  g.imageSmoothingEnabled = false;
  g.fillStyle = ink; g.fillRect(0, 0, W2, H2);
  g.fillStyle = colour; g.fillRect(14, 14, W2 - 28, H2 - 28);
  g.fillStyle = "#ffffff"; g.fillRect(34, 34, W2 - 68, H2 - 68);
  g.fillStyle = ink;
  g.textAlign = "left";
  g.textBaseline = "alphabetic";
  g.font = "900 46px ui-rounded, system-ui, sans-serif";
  g.fillText(art.title || "My Pal", 54, 94, W2 - 108);
  g.font = "700 25px ui-rounded, system-ui, sans-serif";
  g.fillStyle = "#57506e";
  g.fillText(`Made by ${name}`, 54, 128, W2 - 108);
  g.drawImage(PalStage.sceneArt("park"), 40, 60, 240, 120, 54, 146, W2 - 108, 330);
  g.strokeStyle = ink; g.lineWidth = 6; g.strokeRect(54, 146, W2 - 108, 330);
  const size = art.size, tall = rig.empty ? 1 : rig.feet - rig.top + 1, px = Math.max(1, Math.floor(270 / Math.max(tall, size * .8)));
  const left = W2 / 2 - (rig.axis + .5) * px, top = 462 - (rig.feet + 1) * px;
  art.frames[0].forEach((n, i) => {
    if (n < 0) return;
    g.fillStyle = art.palette[n];
    g.fillRect(left + i % size * px, top + Math.floor(i / size) * px, px, px);
  });
  const parts = PART_CHIPS.filter(c => !rig.empty && c.has(rig)).map(c => c.icon).join(" ");
  const count = art.frames[0].filter(n => n >= 0).length;
  const colours = new Set(art.frames[0].filter(n => n >= 0)).size;
  g.fillStyle = ink;
  g.font = "800 30px ui-rounded, system-ui, sans-serif";
  g.fillText(CARD_TRAITS[hash % CARD_TRAITS.length], 54, 530, W2 - 108);
  g.font = "700 26px ui-rounded, system-ui, sans-serif";
  g.fillText(`Bounce  ${"★".repeat(1 + (hash >>> 3) % 5)}`, 54, 580);
  g.fillText(`Cuddles  ${"★".repeat(1 + (hash >>> 9) % 5)}`, 54, 620);
  g.fillText(`Mischief  ${"★".repeat(1 + (hash >>> 15) % 5)}`, 54, 660);
  g.font = "700 25px ui-rounded, system-ui, sans-serif";
  g.fillStyle = "#57506e";
  g.fillText(`${count} squares in ${colours} colours`, 54, 712, W2 - 108);
  g.fillStyle = ink;
  g.font = "28px ui-rounded, system-ui, sans-serif";
  g.fillText(parts, 54, 760, W2 - 108);
}

// ---- A pal left alone: it fidgets, then it nods off ---------------------------------------------
let lifeSeen = 0, lifeBusy = false, dozing = false, nextFidget = 6;
function act(steps) {
  lifeBusy = true;
  return lifeStage.play(steps).finally(() => { lifeBusy = false; });
}
function noticed() {
  lifeSeen = performance.now();
  nextFidget = 6 + Math.random() * 5;
  if (!dozing) return;
  dozing = false;
  act([{do: "feel", mood: "surprised"}, {do: "jump"}, {do: "feel", mood: "calm"}]);
}
function fidget() {
  if ($("lifeView").hidden || lifeBusy || playing || !lifeStage || lifeRig.empty) return;
  const quiet = (performance.now() - lifeSeen) / 1000;
  if (dozing) { act([{do: "snooze"}]); return; }
  if (quiet > 30) {
    dozing = true;
    act([{do: "feel", mood: "sleepy"}, {do: "snooze"}]);
  } else if (quiet > nextFidget) {
    nextFidget = quiet + 5 + Math.random() * 6;
    const spot = 1 + Math.floor(Math.random() * 9), picks = [
      [{do: "look", way: "left"}, {do: "wait", beats: 1}, {do: "look", way: "right"}, {do: "wait", beats: 1}, {do: "look", way: "front"}],
      [{do: "walk", to: spot}], [{do: "jump"}], [{do: "wave"}], [{do: "feel", mood: "happy"}, {do: "wait", beats: 2}, {do: "feel", mood: "calm"}],
    ];
    act(picks[Math.floor(Math.random() * picks.length)]);
  }
}
setInterval(fidget, 1000);

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
