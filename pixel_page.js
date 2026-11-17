// Pixel Pals: the Code tab. Students write Python, the server runs
// it and sends back a list of steps, and the stage plays them while the line
// that made each step lights up. It all sits on top of pixel_studio.js.
"use strict";

const StageSFX = PalStage.SFX;
let S = null;              // /pixel/state
let mode = null;           // the open mission's key
let view = null;           // the open mission, from /pixel/level
let stage = null;
let running = false, runTicket = 0;

function get(url) { return fetch(url).then(r => r.json()); }
// Two spaces on each side of something mark it as code to copy.
function fmt(text) {
  return esc(text).split(/ {2}/).map((part, i) => i % 2 ? `<code>${part}</code>` : part).join(" ")
    .replace(/<\/code> ([.,?!:])/g, "</code>$1");
}
function codeKey(key) { return `pixelCode:${me}:${key}`; }

// ---- Words for every command, shown on chips and in All words ------------------------
const WORDS = {
  wave: "Waves its arm.", dance: "Dances with every part it has.", cheer: "Throws its arms up and jumps.",
  feel: "Changes its face: happy, sad, surprised, angry, sleepy, silly, cool or calm.",
  say: "Your pal says it in a speech bubble.", right: "Walks right. The number is how many spots.",
  left: "Walks left. The number is how many spots.", jump: "Jumps once.", spin: "Spins round.",
  wait: "Waits a moment. Bigger numbers wait longer.",
  hearts: "Hearts float up.", stars: "Stars float up.", confetti: "Confetti falls everywhere.",
  grow: "Gets bigger.", shrink: "Gets smaller again.", shake: "Wobbles like a jelly.",
  look: "Moves its eyes: left, right, up, down or front.",
  clicks: "How many times your pal has been clicked so far: 1, then 2, then 3...",
  x: "The spot your pal is on, from 0 at the left to 10 at the right.",
  scene: "Changes the place: stage, wedding, park, beach, night, snowy, candy, space or castle.",
  sound: "Plays a sound: ding, boing, pop, tada, meow, drum, whoosh or yay.",
  note: "Sings a note: C, D, E, F, G, A, B, the high C2, or rest. A second number is how many beats.",
  rain: "Rain falls.", snow: "Snow falls.",
  friend: "Brings a friend on stage: cat, bunny, kid or bean.", friend_say: "Your friend says something.",
  friend_jump: "Your friend jumps.", bye: "Your friend goes off stage.",
  hide: "Your pal disappears.", appear: "Your pal comes back.",
};
const SAMPLE = {scene: 'scene("beach")', sound: 'sound("tada")', note: 'note("C", 2)', friend: 'friend("cat")', friend_say: 'friend_say("Hi!")', say: 'say("Hello!")', right: "right(3)", left: "left(3)", wait: "wait(2)", feel: 'feel("happy")', look: 'look("left")'};
const sample = name => SAMPLE[name] || name + "()";
const PYTHON = {
  for: ["for loop", "for i in range(3):\n    ", "Repeats the lines pushed in under it."],
  list: ["list", 'for name in ["Ana", "Ben"]:\n    ', "Visits each thing in the [ ] list, one at a time."],
  variable: ["variable", 'name = "Luna"', "A name tag that keeps a word or a number."],
  fstring: ["f-string", 'say(f"{name}!")', "Puts a variable inside the words, in { } brackets."],
  def: ["def", "def my_move():\n    ", "Makes a new command. The lines pushed in under it are what it does."],
  if: ["if", "if i == 3:\n    ", "Only runs the lines pushed in under it when the answer is yes."],
  click: ["on click", "def on_click():\n    ", "Makes your pal wait for a click. The lines pushed in under it run every time it's clicked."],
  while: ["while loop", "while x() < 10:\n    ", "Goes round and round as long as its question is yes."],
  else: ["else", "else:\n    ", "Goes under an if, lined up with it. Its lines run when the if's answer is no."],
  random: ["surprise", 'mood = choice(["happy", "silly"])', "choice() picks one thing from a list by surprise. randint(1, 6) picks a number from 1 to 6."],
  len: ["len()", "len(snacks)", "How many things are on a list, or how many letters are in a word."],
  append: [".append()", 'guests.append("Ben")', "Adds one more thing to the end of a list."],
  index: ["[0] and [-1]", "moods[0]", "One thing from a list, or one letter from a word, by its position. [0] is the first, [-1] is the last."],
  word: ["words", 'name = "Luna"', "A word goes in quotes. Keep it in a variable, and * repeats it: name * 3 is LunaLunaLuna."],
  letters: ["for each letter", "for letter in word:\n    ", "Visits each letter in a word, one at a time, like a list."],
  change: ["+=", "points += 2", "Changes a number variable: adds to what it already is."],
  elif: ["elif", "elif roll >= 4:\n    ", "Goes after an if, lined up with it. Asks a second question when the first answer was no."],
  param: ["def with a number", "def hop(n):\n    ", "Makes a command that takes a number. n is whatever goes in its ( )."],
  nested: ["loop in a loop", "for i in range(3):\n    for j in range(2):\n        ", "A loop pushed in under another loop. The inside loop runs all the way through each time the outside loop goes round."],
  return: ["return", "return n * 2", "Hands a value back out of a def, so say(double(3)) can use it."],
};
const ALL_PYTHON = Object.keys(PYTHON);

// ---- Getting going --------------------------------------------------------------------
function pageEnter(data) {
  S = data;
  stage = PalStage.create($("stageCanvas"), $("stageHost"));
  stage.slow($("slow").getAttribute("aria-pressed") === "true");
  stage.setPal(currentPal());
  stage.fresh();
  $("mute").textContent = StageSFX.muted ? "🔇" : "🔊";
  paintCalm();
  paintTags();
  showStars();
  paintSteps("draw");
}
function paintCalm() {
  $("calm").setAttribute("aria-pressed", PalStage.calm);
  document.body.classList.toggle("calm", PalStage.calm);
}
let hideTags = false;
try { hideTags = localStorage.getItem("pixelHideTags") === "1"; } catch (_) {}
function paintTags() {
  $("tags").setAttribute("aria-pressed", hideTags);
  document.body.classList.toggle("no-tags", hideTags);
}
function currentPal() {
  return S.drawings.find(d => d.key === S.pal) || S.pip;
}
function showStars() { $("starCount").textContent = `★ ${S.stars} / ${S.max_stars} · 🪙 ${S.hang.coins}`; }

// Whatever show is going, it's over: nothing from it may land on the next screen.
function dropRun() {
  runTicket++;
  stopPokes();
  if (stage) stage.stop();
  finishRun();
  setRunLine(0);
}
async function showView(name) {
  if (name === "hang") await refreshState();
  if (name === "hang" && S.hang.needs) {
    flashToast(`🔒 Finish ${missionsWord(S.hang.needs)} to open the Hang out!`);
    name = "stage";
  }
  settle();
  dropRun();
  document.querySelectorAll("nav [data-view]").forEach(b => b.classList.toggle("on", b.dataset.view === (name === "life" ? "draw" : name)));
  $("drawView").hidden = name !== "draw";
  $("stageView").hidden = name !== "stage";
  $("lifeView").hidden = name !== "life";
  $("hangView").hidden = name !== "hang";
  document.querySelectorAll(".draw-only").forEach(el => { el.hidden = name !== "draw"; });
  document.querySelectorAll(".stage-only").forEach(el => { el.hidden = name !== "stage"; });
  $("palPick").hidden = name !== "stage";
  if (name === "life") openLife(); else closeLife();     // before the wait, so its buttons always work
  if (name === "hang") openRoom(); else closeRoom();
  if (name !== "draw") await saveNow();
  if (name === "stage") {
    await refreshState();
    fillPalPick();
    if (!mode) await openMission(S.current);
    else { resetStage(); coachFocus(); }
  }
  paintSteps(name);
}
// A student who has drawn but never coded gets a way into the Code tab from Draw.
function drewSomething() {
  return shelfList.some(d => /[^.]/.test(d.frames[0])) || (!!art && /[^.]/.test(A.encode(art.frames[0])));
}
function missionsWord(n) { return `${n} more mission${n === 1 ? "" : "s"}`; }
// The three steps along the top, and the one big button saying what's next.
function paintSteps(name) {
  $("tabHang").textContent = S.hang.needs ? "🔒 Hang out" : "🎉 Hang out";
  const go = $("goNext"), hasMove = !!S.hang.move;
  // On Code it points at more code: nothing while a mission is unfinished, the next mission after
  // a win, and the Hang out only once every mission is done. The Hang out tab is always there too.
  const all = S.chapters.flatMap(c => c.levels), todo = all.find(l => l.open && !l.stars[0]);
  // My Move can be a few missions away: say how far, since the button opens the next one first.
  const toMove = all.slice(0, all.findIndex(l => l.key === "m1") + 1).filter(l => !l.stars[0]).length;
  const next = name === "life" ? ["💻 Code my pal →", "stage"]
    : name === "draw" && !S.stars && drewSomething() ? ["💻 Now code my pal →", "stage"]
    : name === "draw" && S.stars && todo ? ["💻 Keep coding →", "stage"]          // back next lesson: the way to their mission
    : name === "stage" && todo && view && view.best[0] && todo.key !== mode ? ["💻 Next mission →", null, todo.key]
    : name === "stage" && !todo && S.free_open && mode !== "free" && view && view.best[0] ? ["🎬 Free stage →", null, "free"]
    : name === "stage" && !todo && !S.hang.needs ? ["🎉 Go hang out →", "hang"]
    : name === "hang" && !hasMove && toMove > 1 ? [`🌟 My Move in ${toMove - 1} mission${toMove === 2 ? "" : "s"} →`, "stage"]
    : name === "hang" && !hasMove ? ["🌟 Make My Move →", "stage"]
    : name === "hang" ? ["💻 Code more →", "stage"] : null;
  go.hidden = !next;
  delete go.dataset.view;
  delete go.dataset.mission;
  if (next) { go.textContent = next[0]; if (next[1]) go.dataset.view = next[1]; else go.dataset.mission = next[2]; }
  $("hangNote").hidden = name !== "stage" || !S.hang.needs;
  $("hangNote").textContent = `🔒 ${missionsWord(S.hang.needs)} to the Hang out`;
}
function flashToast(words) {
  $("toast").textContent = words;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4200);
}
async function refreshState() {
  const data = await get("/pixel/state?id=" + encodeURIComponent(me)).catch(() => null);
  if (data && data.you) { S = data; shelfList = data.drawings; showStars(); }
}
function fillPalPick() {
  const options = S.drawings.filter(d => d.frames[0].replace(/\./g, "")).map(d => `<option value="${esc(d.key)}">${esc(d.title || "My drawing")}</option>`);
  $("palSelect").innerHTML = options.join("") + `<option value="pip">Pip</option>`;
  $("palSelect").value = S.pal;
}
function resetStage() {
  stage.setPal(currentPal());
  stage.fresh();
  setRunLine(0);
  setBand(0);
}

// ---- Opening a mission ------------------------------------------------------------------
async function openMission(key) {
  closeSheets();
  saveCode();
  dropRun();
  const data = await get(`/pixel/level?id=${encodeURIComponent(me)}&level=${encodeURIComponent(key)}`).catch(() => null);
  if (!data || data.error) return;
  mode = key;
  view = data;
  hintsShown = 0;
  missStreak = 0;
  guessAsked = false;
  guessWaiting = false;
  guessPick = null;
  remixOn = false;
  remixHint = false;
  fixOn = false;
  fixHint = false;
  deletingShow = false;
  coachWay = data.free ? "own" : null;
  coachOops = "";
  $("levelName").textContent = `${data.chapter.icon} ${data.name}`;
  const n = S.chapters.flatMap(c => c.levels).findIndex(l => l.key === key) + 1;
  $("levelWhere").textContent = data.free ? "No stars, no rules" : `Mission ${n} of ${S.max_stars / 3}`;
  $("pipSays").innerHTML = fmt(data.pip);
  $("job").innerHTML = fmt(data.job);
  $("job").hidden = false;
  $("goals").hidden = !!data.free;
  $("hint").hidden = false;
  $("hint").textContent = data.free ? "💡 Give me an idea" : "Help me";
  drawGoals(data.best);
  paintYourTurn();
  setCode(recall(codeKey(key)) ?? data.code ?? "");
  buildChips(data.commands, data.new, data.python, data.fresh_python);
  verdict(null);
  $("caption").textContent = "Press Show time! to see your code run.";
  resetStage();
  coachFocus();
  if (!$("stageView").hidden) paintSteps("stage");
}
function drawGoals(got) {
  $("goals").innerHTML = view.goals.map((g, i) =>
    `<li class="${got[i] ? "got" : ""}"><i>${got[i] ? "★" : "☆"}</i><span>${fmt(g)}</span></li>`).join("");
}

// ---- Guess first: before the guide's code runs the first time, what will it do? ---------------
let guessAsked = false, guessPick = null, guessWaiting = false;
function wantsGuess() {
  return !!view.guess && !guessAsked && !view.best[0] && !remixOn && !fixOn && $("code").value === coachTarget();
}
function askGuess() {
  guessAsked = true;
  guessWaiting = true;
  paintCoach();
  const g = view.guess;
  $("caption").textContent = "Guess first, then watch!";
  verdict(`<p><b>🔮 Guess first!</b> ${fmt(g.ask)}</p><p class="next">${g.choices.map((c, i) =>
    `<button class="btn main" data-guess="${i}">${esc(c)}</button>`).join(" ")} <button class="btn" data-guess="skip">Just show me</button></p>`);
}
function guessLine(g) {
  return g.right ? `<p class="guess-said">🔮 You guessed right! +${view.guess.coins} 🪙</p>`
    : `<p class="guess-said">🔮 Good guess! It was really: <b>${esc(g.answer)}</b>${/[.!?]$/.test(g.answer) ? "" : "."} Look at the code to see why.</p>`;
}

// ---- 📼 My shows: on the Free stage, shows kept to come back to ------------------------------------
let deletingShow = false;
function showName(code) {
  const said = /say\("([^"]{1,40})"\)/.exec(code), first = code.split("\n").find(l => l.trim()) || "A show";
  const name = said ? said[1] : first.trim();
  return name.length > 18 ? name.slice(0, 17) + "…" : name;
}
function paintShows() {
  const box = $("yourTurn");
  box.hidden = false;
  box.classList.remove("fix");
  box.classList.toggle("on", deletingShow);
  const shows = view.shows.map((c, i) => `<button class="btn${deletingShow ? " danger" : ""}" data-show="${i}">${deletingShow ? "🗑" : "📼"} ${esc(showName(c))}</button>`).join(" ");
  const hangOpen = !S.hang.needs;
  box.innerHTML = `<p>📼 My shows: ${deletingShow ? "click the one to delete." : view.shows.length ? "click one to open it. The show you're making is kept." : "keep this show and start another."}</p>
    <p class="show-row">${shows} ${deletingShow ? `<button class="btn" data-show-del="0">Don't delete</button>`
      : `<button class="btn main" data-show-new="1">🆕 New show</button>${view.shows.length ? ` <button class="btn" data-show-del="1">🗑 Delete one…</button>` : ""}`}</p>
    ${hangOpen ? `<p class="show-friends"><button class="btn main" data-show-perform="1">🎤 Show my friends</button><small>Plays your show on your pal in the Hang out</small></p>` : ""}`;
}
async function showsDo(action, at) {
  const out = await post("/pixel/free/shows", {id: me, action, at, code: $("code").value}).catch(() => null);
  if (!out || out.error) { verdict(`<p>${fmt(out ? out.error : "The computer didn't answer. Try again.")}</p>`, "bad"); return; }
  const had = view.shows;
  view.shows = out.shows;
  deletingShow = false;
  if (action !== "delete") { setCode(out.code); saveCode(); stopPokes(); resetStage(); }
  paintShows();
  verdict(action === "new" ? `<p>${out.shows.length > had.length ? "📼 Kept! " : ""}Here's an empty stage for a new show.</p>`
    : action === "open" ? `<p>📼 Here's <b>${esc(showName(out.code))}</b>. Press ▶ Show time! to watch it.</p>`
    : `<p>🗑 Deleted <b>${esc(showName(had[at]))}</b>.</p>`, "good");
}
// 🎤 Play this show on your pal in the Hang out, so everyone there sees it.
async function showFriends() {
  const code = $("code").value;
  if (!code.trim() && !view.shows.length) {
    verdict(`<p>Make a show first, then press 🎤 Show my friends.</p>`, "bad");
    return;
  }
  const kept = await post("/pixel/free/shows", {id: me, action: "save", code}).catch(() => null);
  if (!kept || kept.error) {
    verdict(`<p>${fmt(kept ? kept.error : "The computer didn't answer. Try again.")}</p>`, "bad");
    return;
  }
  await showView("hang");
  await tap("join");
  PalStage.SFX.wake();
  const out = await tap("perform");
  if (!out || !out.ok) {
    tipFor((out && out.error) || "Couldn't start your show. Try again.", 6000);
    return;
  }
  if (out.badges && out.badges.length) showRewards({badges: out.badges});
}

// ---- Your turn: after a mission, one change to make with the guide off ----------------------
let remixOn = false, remixHint = false;
// The same box shows Fix it once Your turn is done, or while a Fix it is on.
function paintYourTurn() {
  if (view.free) { paintShows(); return; }
  const box = $("yourTurn"), t = view.remix, f = view.fix;
  const showFix = fixOn || (!remixOn && t.done && !!f && !f.done);
  box.hidden = !view.best[0] || (t.done && !showFix);
  box.classList.toggle("on", remixOn || fixOn);
  box.classList.toggle("fix", showFix);
  if (box.hidden) return;
  if (showFix) { box.innerHTML = fixCard(); return; }
  box.innerHTML = remixOn
    ? `<p>🎨 Your turn: ${fmt(t.ask)}</p><p class="turn-hint">No guide this time. Change the code yourself, then press <b>▶ Show time!</b></p>` +
      (remixHint ? `<p class="turn-hint">💡 ${fmt(t.hint)}</p>` : `<button class="btn" data-remix-hint="1">💡 Where do I change it?</button>`)
    : `<p>🎨 Your turn: ${fmt(t.ask)}</p><button class="btn main" data-remix="1">Try it! +${t.coins} 🪙</button>`;
}
function startRemix() {
  fixOn = false;
  remixOn = true;
  coachWay = "own";
  if (!$("code").value.trim()) setCode(view.code || view.coach.map(c => c[0]).join("\n"));
  paintYourTurn();
  updateEditor();
  verdict(`<p>🎨 <b>Your turn!</b> ${fmt(view.remix.ask)}</p><p>Change the code on the left yourself. You can do it!</p>`);
  $("code").focus();
}
function remixButton() {
  return view.remix.done || remixOn ? "" : ` <button class="btn" data-remix="1">🎨 Your turn +${view.remix.coins} 🪙</button>`;
}
// One extra button after a mission: Your turn first, then Fix it.
function extraButton() {
  return remixOn || fixOn ? "" : remixButton() || fixButton();
}

// ---- Fix it: Pip's code for the mission, with one bug to find and fix ----------------------------
let fixOn = false, fixHint = false;
function fixCard() {
  const f = view.fix;
  if (!fixOn) return `<p>🐞 Fix it: ${fmt(f.ask)}</p><button class="btn main" data-fix="1">Fix Pip's code +${f.coins} 🪙</button>`;
  return `<p>🐞 Fix it: ${fmt(f.ask)}</p><p class="turn-hint">Find the bug in the code and fix it, then press <b>▶ Show time!</b></p>` +
    (fixHint ? `<p class="turn-hint">💡 ${fmt(f.hint)}</p>` : `<button class="btn" data-fix-hint="1">💡 Where's the bug?</button>`) +
    ` <button class="btn" data-fix-reset="1">↩ Pip's code again</button>`;
}
function fixButton() {
  const f = view.fix;
  return !f || f.done || fixOn || !view.best[0] ? "" : ` <button class="btn" data-fix="1">🐞 Fix it +${f.coins} 🪙</button>`;
}
function startFix() {
  remixOn = false;
  fixOn = true;
  fixHint = false;
  coachWay = "own";
  setCode(view.fix.code);
  paintYourTurn();
  updateEditor();
  verdict(`<p>🐞 <b>Fix it!</b> ${fmt(view.fix.ask)}</p><p>Press <b>▶ Show time!</b> to see what goes wrong. Then find the bug in the code and fix it.</p>`);
  $("code").focus();
}
function fixDone() {
  view.fix.done = true;
  fixOn = false;
  confettiBurst();
  StageSFX.play("fanfare");
  const order = S.chapters.flatMap(c => c.levels), next = order[order.findIndex(l => l.key === mode) + 1];
  $("caption").textContent = "Bug fixed!";
  verdict(`<p><b>🐞 Bug fixed! You found it and fixed it. Real coders do that every day!</b></p>
    <p class="next">${nextButton(next)}</p>`, "good");
}

// ---- Chips -----------------------------------------------------------------------------
// A chip writes the whole line.
function buildChips(commands, fresh, python, freshPython) {
  const cmds = commands.filter(c => WORDS[c]);
  $("chips").innerHTML =
    cmds.map(c => `<button class="chip${fresh.includes(c) ? " fresh" : ""}" data-chip="${esc(sample(c))}" title="${esc(WORDS[c])}">${esc(sample(c))}</button>`).join("") +
    ALL_PYTHON.filter(k => python.includes(k)).map(k =>
      `<button class="chip py${freshPython.includes(k) ? " fresh" : ""}" data-chip="${esc(PYTHON[k][1])}" title="${esc(PYTHON[k][2])}">${esc(PYTHON[k][0])}</button>`).join("");
  const entry = (chip, label, words) =>
    `<div><dt><button class="chip" data-chip="${esc(chip)}">${esc(label)}</button></dt><dd style="margin:0">${esc(words)}</dd></div>`;
  $("book").innerHTML =
    cmds.map(c => entry(sample(c), sample(c), WORDS[c])).join("") +
    ALL_PYTHON.filter(k => python.includes(k)).map(k => entry(PYTHON[k][1], PYTHON[k][0], PYTHON[k][2])).join("");
}
function addLine(snippet) {
  const t = $("code"), pos = t.selectionStart;
  const start = t.value.lastIndexOf("\n", pos - 1) + 1;
  let end = t.value.indexOf("\n", pos);
  if (end < 0) end = t.value.length;
  const line = t.value.slice(start, end);
  let indent = (line.match(/^ */) || [""])[0];
  if (line.trimEnd().endsWith(":")) indent += "    ";
  const body = snippet.split("\n").join("\n" + indent);
  let at;
  if (!line.trim()) {
    t.setRangeText(indent + body, start, end, "end");
    at = start + indent.length;
  } else {
    t.setRangeText("\n" + indent + body, end, end, "end");
    at = end + 1 + indent.length;
  }
  const quoted = /"([^"]*)"/.exec(body);              // ready to type over the word
  if (quoted && !body.includes("\n")) t.setSelectionRange(at + quoted.index + 1, at + quoted.index + 1 + quoted[1].length);
  else if (!snippet.endsWith("    ")) t.setSelectionRange(t.selectionEnd, t.selectionEnd);
  t.focus();
  updateEditor();
}

// ---- The editor -------------------------------------------------------------------------
const KEYWORDS = new Set(["for", "in", "if", "elif", "else", "while", "def", "and", "or", "not", "True", "False", "global", "return", "break"]);
const KNOWN = new Set(Object.keys(WORDS));
let runLine = 0, errorLine = 0;

function paintCode(code) {
  const pattern = /#.*|f?"(?:[^"\\\n]|\\.)*"?|f?'(?:[^'\\\n]|\\.)*'?|\b\d+\b|\b[A-Za-z_]\w*\b/g;
  let out = "", at = 0, m;
  while ((m = pattern.exec(code))) {
    out += esc(code.slice(at, m.index));
    const t = m[0], c = t[0];
    if (c === "#") out += `<span class="hl-h">${esc(t)}</span>`;
    else if (c === '"' || c === "'" || (c === "f" && t.length > 1 && (t[1] === '"' || t[1] === "'"))) out += `<span class="hl-s">${esc(t)}</span>`;
    else if (/^\d/.test(t)) out += `<span class="hl-n">${t}</span>`;
    else if (KEYWORDS.has(t)) out += `<span class="hl-k">${t}</span>`;
    else if (KNOWN.has(t)) out += `<span class="hl-c">${t}</span>`;
    else out += esc(t);
    at = m.index + t.length;
  }
  return out + esc(code.slice(at)) + "\n";
}
function updateEditor() {
  const code = $("code").value;
  $("paint").innerHTML = paintCode(code).slice(0, -1) + coachGhost() + "\n";
  const count = Math.max(1, code.split("\n").length);
  $("lines").innerHTML = Array.from({length: count}, (_, i) =>
    i + 1 === runLine ? `<span class="run">▸${i + 1}</span>`
    : i + 1 === errorLine ? `<span class="err">▸${i + 1}</span>` : i + 1).join("\n");
  syncScroll();
  paintCoach();
}
function syncScroll() {
  const t = $("code");
  $("paint").scrollTop = t.scrollTop;
  $("paint").scrollLeft = t.scrollLeft;
  $("lines").scrollTop = t.scrollTop;
  placeBand();
}
function placeBand() {
  const n = runLine || errorLine, band = $("band");
  band.hidden = !n;
  band.className = runLine ? "run" : "err";
  if (n) band.style.top = `${8 + (n - 1) * 22 - $("code").scrollTop}px`;
}
function setBand(n) { errorLine = n; updateEditor(); }
function setRunLine(n) {
  runLine = n || 0;
  if (runLine) {
    const t = $("code"), top = 8 + (runLine - 1) * 22;
    if (top < t.scrollTop || top + 22 > t.scrollTop + t.clientHeight) t.scrollTop = Math.max(0, top - t.clientHeight / 3);
  }
  updateEditor();
}
function setCode(text) {
  $("code").value = text;
  runLine = errorLine = 0;
  updateEditor();
}
function saveCode() {
  if (me && mode) store(codeKey(mode), $("code").value);
}
function editorKeys(e) {
  if (coachKey(e)) return;
  const t = $("code"), s = t.selectionStart, end = t.selectionEnd;
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    runShow();
  } else if (e.key === "Tab") {
    e.preventDefault();
    const start = t.value.lastIndexOf("\n", s - 1) + 1;
    if (e.shiftKey) {
      if (t.value.startsWith("    ", start)) t.setRangeText("", start, start + 4, "end");
    } else t.setRangeText("    ", s, end, "end");
    updateEditor();
  } else if (e.key === "Enter") {
    e.preventDefault();
    const start = t.value.lastIndexOf("\n", s - 1) + 1, line = t.value.slice(start, s);
    let indent = (line.match(/^ */) || [""])[0];
    if (line.trimEnd().endsWith(":")) indent += "    ";
    t.setRangeText("\n" + indent, s, end, "end");
    updateEditor();
  } else if (e.key === "Backspace" && s === end) {
    const start = t.value.lastIndexOf("\n", s - 1) + 1, before = t.value.slice(start, s);
    if (before.length && before.length % 4 === 0 && !before.trim()) {
      e.preventDefault();
      t.setRangeText("", s - 4, s, "end");
      updateEditor();
    }
  }
}

// ---- The step-by-step guide ------------------------------------------------------------------
// It reads what's in the editor and works out what comes next, so there's nothing to
// get out of step. Only the right key goes in, and a wrong one says which to look for.
const KEY_HELP = {
  "(": "Hold Shift and press 9", ")": "Hold Shift and press 0", '"': "Hold Shift and press the ' key, next to Enter",
  ":": "Hold Shift and press the ; key", "!": "Hold Shift and press 1", " ": "Press the long space bar", "\n": "Press Enter", ".": "Press the . key",
  "+": "Hold Shift and press the = key, next to Backspace", "=": "Press the = key, next to Backspace", ",": "Press the , key, next to M",
  "-": "Press the - key, next to 0", "<": "Hold Shift and press the , key", ">": "Hold Shift and press the . key", "_": "Hold Shift and press the - key, next to 0", "[": "Press the [ key, next to P", "]": "Press the ] key, next to [", "{": "Hold Shift and press the [ key", "}": "Hold Shift and press the ] key",
  "*": "Hold Shift and press the 8 key",
};
const ACTIONS = /^\s*(say|jump|right|left|wave|dance|cheer|spin|hearts|stars|confetti|feel)\(/gm;
let coachWay = null, coachOops = "", coachEarly = false;     // coachWay: "type", "build", or "own" for a student's own way

function coachTarget() { return view.coach.map(c => c[0]).join("\n"); }
function coachMode() {
  if (!view || !mode) return null;
  const way = coachWay || (view.build ? "build" : "type");        // every mission starts with the guide on
  return way === "own" ? null : way;
}
function coachTyping() { return coachMode() === "type" && coachTarget().startsWith($("code").value); }
function keyName(ch) { return ch === " " ? "space bar" : ch === "\n" ? "Enter" : ch; }
function keyHelp(ch) { return KEY_HELP[ch] || `Press the ${ch.toUpperCase()} key`; }
function coachShake() {
  const box = $("coach");
  box.classList.remove("shake");
  void box.offsetWidth;
  box.classList.add("shake");
}
function coachFocus() {
  if (coachMode() !== "type" || !$("code").offsetParent) return;
  const t = $("code");
  t.focus();
  t.setSelectionRange(t.value.length, t.value.length);
}
function coachPut(text) {
  const t = $("code");
  t.value = text;
  t.setSelectionRange(text.length, text.length);
  errorLine = 0;
  saveCode();
  updateEditor();
  t.scrollTop = t.scrollHeight;
}
/** One key press while being walked through. True if the guide dealt with it. */
function coachKey(e) {
  if (!coachTyping() || e.ctrlKey || e.metaKey || e.altKey) return false;
  const code = $("code").value, target = coachTarget();
  coachEarly = false;
  if (e.key === "Backspace") {
    e.preventDefault();
    const line = /\n *$/.exec(code);      // the pushed-in spaces go with their line
    coachOops = "";
    coachPut(line ? code.slice(0, line.index) : code.slice(0, -1));
    return true;
  }
  if (e.key !== "Enter" && e.key.length !== 1) { if (e.key === "Tab") e.preventDefault(); return e.key === "Tab"; }
  e.preventDefault();
  if (code === target) { coachShake(); return true; }
  const want = target[code.length], typed = e.key === "Enter" ? "\n" : e.key;
  if (typed.toLowerCase() !== want.toLowerCase()) {
    coachOops = want;
    coachShake();
    paintCoach();
    return true;
  }
  coachOops = "";
  let next = code + want;
  if (want === "\n") next += /^ */.exec(target.slice(next.length))[0];   // pushed in for them
  StageSFX.play(want === "\n" || next === target ? "ding" : "click");
  coachPut(next);
  return true;
}
function coachGhost() {
  if (!coachTyping()) return "";
  const code = $("code").value, target = coachTarget(), end = target.indexOf("\n", code.length);
  return `<span class="hl-ghost">${esc(target.slice(code.length, end < 0 ? target.length : end))}</span>`;
}
// Show time! only goes once the typing is done, so there's one thing to do at a time.
function coachBlocks() {
  if (!coachTyping() || $("code").value === coachTarget()) return false;
  coachOops = "";
  coachEarly = true;
  coachShake();
  paintCoach();
  coachFocus();
  return true;
}
function goodPrefix() {
  const code = $("code").value, target = coachTarget();
  let n = 0;
  while (n < code.length && code[n] === target[n]) n++;
  return code.slice(0, n);
}
const coachActions = {
  back() { coachOops = ""; coachPut(goodPrefix()); coachFocus(); },
  own() { coachWay = "own"; updateEditor(); $("code").focus(); },
  steps() { showSteps(); },
};
function showSteps() {
  remixOn = false;
  fixOn = false;
  paintYourTurn();
  coachWay = "type";
  coachOops = "";
  updateEditor();
  coachFocus();
}
function stepList(names, now) {
  return `<ol class="coach-steps">${names.map((name, i) => `<li class="${i < now ? "done" : i === now ? "now" : ""}">${i < now ? "✓" : i + 1 + "."} ${name}</li>`).join("")}</ol>`;
}
function paintBuild(box) {
  const count = ($("code").value.match(ACTIONS) || []).length, ready = count >= 3;
  $("runButton").classList.toggle("nudge", ready);
  box.innerHTML = stepList(["Click 3 green buttons", "▶ Show time!"], ready ? 1 : 0) +
    (ready ? `<p class="coach-say">✅ You have ${count} actions. Add more if you like!</p><p class="coach-next">👇 Then press the pink <b>▶ Show time!</b> button.</p>`
      : `<p class="coach-say">👇 Click ${3 - count} more green button${3 - count === 1 ? "" : "s"} under your code. Each one adds an action to your move.</p><p class="coach-next">You have <b>${count}</b> of 3 actions.</p>`) +
    `<div class="coach-row"><button class="btn" data-coach="steps">🖐 Show me step by step, with a sparkle trail</button></div>`;
}
function paintType(box) {
  const code = $("code").value, target = coachTarget(), lines = view.coach;
  if (!target.startsWith(code)) {
    box.innerHTML = `<p class="coach-say">Your code is different from the steps.</p>
      <div class="coach-row"><button class="btn main" data-coach="back">↩ Go back to where it was right</button><button class="btn" data-coach="own">✋ Keep my code</button></div>`;
    return;
  }
  const at = code.split("\n").length - 1, done = code === target;
  const names = [...lines.map((c, i) => `Line ${i + 1}`), "▶ Show time!"];
  if (done) {
    const won = !!view.best[0] && !guessWaiting && !running;
    if (!won && !running) $("runButton").classList.add("nudge");
    box.innerHTML = stepList(names, won ? lines.length + 1 : lines.length) + (guessWaiting
      ? `<p class="coach-say">🔮 Before you watch: guess what will happen!</p><p class="coach-next">👉 Pick your guess under the stage, on the right.</p>`
      : running ? `<p class="coach-say">👀 Watch your code run!</p><p class="coach-next">The lit-up line is the one your pal is doing now.</p>`
      : won ? `<p class="coach-say">✅ Mission done! Your code works.</p><p class="coach-next">👉 Pick what's next under the stage, on the right.</p>`
      : `<p class="coach-say">🎉 You typed it all!</p><p class="coach-next">👇 Now press the pink <b>▶ Show time!</b> button.</p>`);
    return;
  }
  const whole = lines[at][0], indent = /^ */.exec(whole)[0].length, line = whole.slice(indent);
  const typed = Math.max(0, code.length - (code.lastIndexOf("\n") + 1) - indent), last = at === lines.length - 1;
  const tiles = [...line].map((ch, i) => `<kbd class="${i < typed ? "got" : i === typed ? "next" : ""}${ch === " " ? " gap" : ""}">${ch === " " ? "␣" : esc(ch)}</kbd>`).join("") +
    (last ? "" : `<kbd class="enter${typed === line.length ? " next" : ""}">Enter ↵</kbd>`);
  const want = target[code.length];
  box.innerHTML = stepList(names, at) +
    `<p class="coach-say">${esc(lines[at][1])}</p>
     <p class="coach-do">Type this, one key at a time:</p>
     <div class="coach-keys">${tiles}</div>
     <p class="coach-next">👉 Next key: <b>${esc(keyName(want))}</b> ${esc(keyHelp(want))}</p>` +
    (coachEarly ? `<p class="coach-oops" role="status">Not yet! Finish typing first, then press Show time!</p>` : "") +
    (coachOops ? `<p class="coach-oops" role="status">Not that key. Find the ${esc(keyName(coachOops))} key.</p>` : "") +
    `<div class="coach-row"><button class="btn" data-coach="own">✋ I can type it myself</button></div>`;
}
function paintCoach() {
  const box = $("coach"), way = coachMode();
  document.body.classList.toggle("coaching", !!way);
  document.body.classList.toggle("building", way === "build");
  $("runButton").classList.remove("nudge");
  box.hidden = !way;
  $("coachBack").hidden = !!way || !mode || !!view.free;
  $("code").placeholder = way === "type" ? "" : "Type your code here";
  if (way === "build") paintBuild(box);
  else if (way === "type") paintType(box);
}
function coachSpeech() {
  const code = $("code").value;
  if (coachMode() !== "type" || !coachTyping() || code === coachTarget()) return "";
  return `${$("job").textContent} ${view.coach[code.split("\n").length - 1][1]}`;
}

// ---- Show time --------------------------------------------------------------------------
function captionFor(s) {
  const line = s.line ? `<b>Line ${s.line}:</b> ` : "";
  const says = {
    say: () => `your pal says "${esc(s.text)}"`, walk: () => `your pal walks to spot ${s.to}`,
    jump: () => "your pal jumps", spin: () => "your pal spins", wave: () => "your pal waves", dance: () => "your pal dances",
    cheer: () => "your pal cheers", feel: () => `your pal feels ${esc(s.mood)}`, wait: () => "your pal waits",
    note: () => s.name === "rest" ? "🎵 your pal rests" : `🎵 your pal sings ${esc(s.name)}`,
    hearts: () => "hearts float up", stars: () => "stars float up", confetti: () => "confetti falls",
    event: () => "👆 Pip clicks your pal to test it",
  };
  return says[s.do] ? line + says[s.do]() : "";
}
async function playSteps(steps) {
  await stage.play(steps, {onStep(s) {
    setRunLine(s.line);
    const text = captionFor(s);
    if (text) $("caption").innerHTML = text;
  }});
  setRunLine(0);
}
async function runShow() {
  if (running || !mode || coachBlocks()) return;
  if (wantsGuess()) { askGuess(); return; }
  if (guessWaiting) { guessWaiting = false; paintCoach(); }
  running = true;
  stopPokes();
  paintCoach();
  $("palSelect").disabled = true;           // a new pal mid-show would cut the show short
  const ticket = ++runTicket;
  saveCode();
  StageSFX.wake();
  document.activeElement.blur();
  $("doRow").classList.add("playing");
  $("runButton").disabled = true;
  verdict(null);
  setBand(0);
  $("caption").textContent = "The curtain goes up...";
  let out = null;
  try { out = await post("/pixel/run", {id: me, level: mode, code: $("code").value, guess: guessPick, fixing: fixOn}); } catch (_) {}
  if (ticket !== runTicket) return;
  if (!out) {
    finishRun();
    verdict(`<p>The computer didn't answer. Check the Wi-Fi, then press Show time! again.</p>`, "bad");
    return;
  }
  if (out.error && !out.steps) {
    finishRun();
    missed();
    verdict(`<p>${fmt(out.error)}</p>${stuckOffer()}`, "bad");
    return;
  }
  resetStage();
  await playSteps(out.steps);
  if (ticket !== runTicket) return;
  finishRun();
  if (out.state) { S = out.state; showStars(); }
  if (out.error) {
    setBand(out.line || 0);
    stage.sigh();
    $("caption").textContent = out.line ? `The show stopped on line ${out.line}.` : "The show stopped.";
    missed();
    verdict(`<p>${fmt(out.error)}</p><p>Fix that line, then press Show time! again.</p>${stuckOffer()}`, "bad");
    return;
  }
  if (view.free) {
    stage.cheer();
    $("caption").textContent = "What a show!";
    verdict(`<p><b>🎬 What a show!</b> Change anything you like, then press Show time! again. Your code is saved.</p>`, "good");
    showRewards(out.rewards || {});
    paintSteps("stage");
    listenForPokes(out);
    return;
  }
  drawGoals(out.stars.map((g, i) => g || view.best[i]));
  view.best = out.stars.map((g, i) => g || view.best[i]);
  if (out.rewards.fixed) { stage.cheer(); fixDone(); }
  else if (out.rewards.remixed) { stage.cheer(); remixDone(out); }
  else if (fixOn) {
    stage.sigh();
    $("caption").textContent = "The bug is still there.";
    verdict(`<p>The show ran, but the bug is still there: <b>${fmt(view.fix.ask)}</b></p><p>Look at the code again, fix it, then press Show time!</p>`, "bad");
  }
  else if (out.stars[0]) { missStreak = 0; stage.cheer(); missionDone(out); }
  else {
    stage.sigh();
    $("caption").textContent = "Not quite yet.";
    missed();
    verdict(`<p>${fmt(out.reply || "Not quite. Read the job again.")}</p>${stuckOffer()}`, "bad");
  }
  paintYourTurn();
  paintCoach();
  if (out.rewards.guess) $("verdict").insertAdjacentHTML("afterbegin", guessLine(out.rewards.guess));
  guessPick = null;
  if (out.rewards.first) celebrate(out.rewards);
  else if (out.rewards.gained) { flyStars(out.rewards.gained); showRewards(out.rewards); }
  else showRewards(out.rewards);
  paintSteps("stage");
  listenForPokes(out);
}
// ---- Click Me!: after a show whose code has def on_click():, a click on the pal runs it ------------
// Each click runs the program again with every click so far (so clicks() counts up), and the
// stage plays only what this click does, lighting up each line as it runs.
// def on_key(key): works the same way with the arrow keys and space, when the editor isn't in use.
let poke = null;
const POKE_KEYS = {ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down", " ": "space"};
function listenForPokes(out) {
  const hears = out.error ? [] : (out.events || []).filter(e => e === "click" || e === "key");
  poke = hears.length ? {code: $("code").value, level: mode, events: [], queue: [], ticket: 0, hears, seed: out.seed || 0} : null;     // the show's own surprises
  $("stageHost").classList.toggle("pokeable", !!poke && hears.includes("click"));
  if (!poke) return;
  if (hears.includes("key")) document.activeElement.blur();      // so the keys go to the pal, not the code
  $("caption").innerHTML = [hears.includes("click") && "👆 Now <b>click your pal</b> on the stage!",
                            hears.includes("key") && "⌨️ Press the <b>arrow keys</b> or <b>space</b>!"].filter(Boolean).join(" ");
}
function stopPokes() {
  poke = null;
  $("stageHost").classList.remove("pokeable");
}
function pokePal() { if (poke && poke.hears.includes("click")) sendPoke("click"); }
async function sendPoke(event) {
  if (!poke || running) return;
  if ($("code").value !== poke.code || mode !== poke.level) {
    stopPokes();
    $("caption").textContent = "Your code changed. Press Show time! to try it.";
    return;
  }
  const mine = poke;
  if (mine.busy) { if (mine.queue.length < 8) mine.queue.push(event); return; }      // one at a time to the server; quick presses wait in line
  const ticket = ++mine.ticket;
  mine.busy = true;
  mine.events.push(event);
  if (event === "click") StageSFX.play("click");
  const out = await post("/pixel/poke", {id: me, level: mine.level, code: mine.code, events: mine.events, seed: mine.seed}).catch(() => null);
  mine.busy = false;
  if (poke !== mine || ticket !== mine.ticket) return;          // a new show took over
  if (mine.queue.length) sendPoke(mine.queue.shift());
  if (!out || out.error) {
    stopPokes();
    if (out && out.error) { setBand(out.line || 0); verdict(`<p>${fmt(out.error)}</p><p>Fix that line, then press Show time! again.</p>`, "bad"); }
    return;
  }
  $("caption").innerHTML = event === "click" ? `👆 Click ${mine.events.filter(e => e === "click").length}!` : `⌨️ ${event.slice(4)}`;
  await stage.play(out.steps, {onStep(s) { if (poke === mine && ticket === mine.ticket) setRunLine(s.line); }});
  if (poke === mine && ticket === mine.ticket) setRunLine(0);
}
// Three misses in a row with the guide off: offer the guide back, right where they're looking.
let missStreak = 0;
function missed() { if (!remixOn && !fixOn && !view.free) missStreak++; }
function stuckOffer() {
  if (missStreak < 3 || coachMode() || view.build || remixOn || fixOn) return "";
  return `<p class="next"><button class="btn main" data-steps="1">🖐 Show me step by step</button> Stuck? That's OK. The guide shows every key.</p>`;
}
function finishRun() {
  const was = running;
  running = false;
  if (was && mode) paintCoach();
  $("palSelect").disabled = false;
  $("runButton").disabled = false;
  $("doRow").classList.remove("playing");
}
function nextButton(next) {
  return next ? `<button class="btn main" data-mission="${esc(next.key)}">Next mission →</button>`
    : `<button class="btn main" data-view="hang">🎉 Go hang out →</button>`;
}
function remixDone(out) {
  view.remix.done = true;
  remixOn = false;
  confettiBurst();
  StageSFX.play("fanfare");
  const order = S.chapters.flatMap(c => c.levels), next = order[order.findIndex(l => l.key === mode) + 1];
  $("caption").textContent = "You changed the code yourself!";
  verdict(`<p><b>🎨 Your turn: done! You changed the code yourself. That's real coding!</b></p>
    <p class="next">${nextButton(next)}${fixButton()}</p>`, "good");
}
function missionDone(out) {
  if (remixOn) {
    $("caption").textContent = "The show works!";
    verdict(`<p>The show works! But Your turn wants: <b>${fmt(view.remix.ask)}</b></p><p>Change the code a bit more, then press Show time! again.</p>`, "bad");
    return;
  }
  const all = out.stars.every(Boolean), order = S.chapters.flatMap(c => c.levels), at = order.findIndex(l => l.key === mode);
  const next = order[at + 1];
  $("caption").textContent = "The crowd loves it!";
  const more = out.stars.findIndex(g => !g);
  verdict(`<p><b>${all ? "Three stars! A perfect show!" : "You did it! The crowd is cheering."}</b>${more >= 0 ? ` For the next star: ${fmt(view.goals[more])}${/[.!?]$/.test(view.goals[more]) ? "" : "."}${out.reply ? ` ${fmt(out.reply)}` : ""}` : ""}</p>
    <p class="next">${nextButton(next)}${extraButton()}${mode === "m1" ? ` <button class="btn" data-rename="1">Rename my move</button>` : ""}</p>`, "good");
}
// The box always stays on screen, so the stage above it never jumps.
function verdict(html, kind) {
  const box = $("verdict");
  box.className = "panel" + (kind ? " " + kind : "");
  box.innerHTML = html || `<p style="color:var(--ink-soft)">Pip is watching. Your result shows up here.</p>`;
  // Error messages are the longest reading on the page, so they can be heard too.
  if (kind === "bad" && "speechSynthesis" in window)
    box.insertAdjacentHTML("afterbegin", `<button class="btn verdict-read" data-read="1" title="Read this to me">🔈 Read it</button>`);
}
function fitScreen() {
  const wrap = $("stageHost").parentElement, room = wrap.getBoundingClientRect();
  if (!room.width) return;
  const w = Math.floor(Math.min(room.width - 6, (room.height - 6) * 16 / 9));
  $("stageHost").style.width = w + "px";
}
let hintsShown = 0;
let hintCode = "";
function showHint() {
  if (!view) return;                  // the mission is still on its way
  if (view.free) {                    // the Free stage gives ideas, one after another
    const [title, code] = view.ideas[hintsShown++ % view.ideas.length];
    hintCode = code;
    verdict(`<p><b>💡 ${esc(title)}</b> <button class="btn main" data-copy="1">Use this idea</button> Then change it to make it yours!</p>
      <pre style="margin:2px 0 0;font:14px/18px var(--mono);white-space:pre-wrap">${esc(code)}</pre>`);
    return;
  }
  const hints = view.hints, text = hints[Math.min(hintsShown, hints.length - 1)];
  hintCode = hints[hints.length - 1];
  const isCode = hintsShown >= hints.length - 1;
  hintsShown++;
  verdict(isCode
    ? `<p><b>Here's one way to do it:</b></p><pre style="margin:2px 0 0;font:14px/18px var(--mono);white-space:pre-wrap">${esc(text)}</pre><p class="next"><button class="btn" data-copy="1">Use this code</button></p>`
    : `<p>${fmt(text)}</p>`);
}

let toastTimer = 0;
function showRewards(r) {
  const lines = [];
  if (r.gained) lines.push(`+${r.gained} ★`);
  if (r.coins) lines.push(`+${r.coins} 🪙`);
  for (const b of r.badges || []) lines.push(`${b.icon} ${b.name}`);
  if (!lines.length) return;
  $("toast").textContent = lines.join("   ");
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4200);
}

// ---- The big win ---------------------------------------------------------------------------
// A first finish gets the whole thing: stars, confetti and a gift box to tap open.
function flyStars(n) {
  const to = $("starCount").getBoundingClientRect();
  if (PalStage.calm || !to.width) { showStars(); return; }
  for (let i = 0; i < Math.min(n, 3); i++) {
    const el = document.createElement("div");
    el.className = "fly-star";
    el.textContent = "★";
    el.style.setProperty("--dx", `${to.left + to.width / 2 - innerWidth / 2}px`);
    el.style.setProperty("--dy", `${to.top + to.height / 2 - innerHeight / 2}px`);
    el.style.animationDelay = `${i * 140}ms`;
    document.body.appendChild(el);
    setTimeout(() => { StageSFX.climb(i * 3); el.remove(); $("starCount").classList.remove("bump"); void $("starCount").offsetWidth; $("starCount").classList.add("bump"); }, 800 + i * 140);
  }
}
function confettiBurst() {
  if (PalStage.calm) return;
  const box = $("winBits"), colours = ["#ff5fa2", "#ffd93b", "#35d0bd", "#7ab8ff", "#c5a3ff"];
  box.innerHTML = Array.from({length: 46}, (_, i) =>
    `<i style="left:${Math.random() * 100}%;background:${colours[i % 5]};animation-delay:${Math.random() * .5}s;animation-duration:${1.3 + Math.random()}s"></i>`).join("");
}
function winButtons(r) {
  const order = S.chapters.flatMap(c => c.levels), next = order[order.findIndex(l => l.key === mode) + 1];
  const hang = !S.hang.needs;
  if (r.hang_opened) return `<button class="btn main" data-view="hang">🎉 Go to the Hang out!</button>${next ? ` <button class="btn" data-mission="${esc(next.key)}">Next mission →</button>` : ""}`;
  if (mode === "m1") return `<button class="btn main" data-view="hang">🎉 Go show everyone!</button>${next ? ` <button class="btn" data-mission="${esc(next.key)}">Next mission →</button>` : ""}${S.free_open ? ` <button class="btn" data-mission="free">🎬 Free stage</button>` : ""}`;
  return `${next ? `<button class="btn main" data-mission="${esc(next.key)}">Next mission →</button>` : ""}${remixButton()}${hang ? ` <button class="btn" data-view="hang">🎉 Hang out</button>` : ""}`;
}
function celebrate(r) {
  const n = view.best.filter(Boolean).length;
  $("winTitle").textContent = mode === "m1" ? "Your own move!" : r.hang_opened ? "The Hang out is open!" : "You did it!";
  $("winStars").innerHTML = [0, 1, 2].map(i => `<span class="${i < n ? "on" : ""}" style="animation-delay:${i * 180}ms">★</span>`).join("");
  $("winBody").innerHTML = r.guess ? guessLine(r.guess) : "";
  $("winDo").innerHTML = "";
  $("win").hidden = false;
  confettiBurst();
  StageSFX.play("fanfare");
  if (r.gained) flyStars(r.gained);
  if ((r.badges && r.badges.length) || r.coins) showRewards({badges: r.badges, coins: r.coins});
  const after = () => (r.move ? showMoveNames(r) : ($("winDo").innerHTML = winButtons(r)));
  if (!r.gift) { after(); return; }
  $("winBody").innerHTML = (r.guess ? guessLine(r.guess) : "") + `<button class="gift-box" id="giftOpen" aria-label="Open your gift"><span>🎁</span>Tap to open!</button>`;
  $("winDo").innerHTML = `<button class="btn" id="giftLater">Open it later</button>`;
  $("giftLater").addEventListener("click", after);
  $("giftOpen").addEventListener("click", () => {
    const gift = S.hang.catalog[r.gift];
    StageSFX.play("gift");
    confettiBurst();
    $("winBody").innerHTML = `<div class="gift-open"><canvas id="giftPic"></canvas><b>${esc(gift.name)}!</b><small>Wear it in the Hang out: press 🧢 Me.</small></div>`;
    wearInto($("giftPic"), r.gift, 9);
    $("winDo").innerHTML = "";
    if (r.move) setTimeout(after, PalStage.calm ? 0 : 1100); else after();
  });
}
function moveMeaning(move) {
  return `<ul class="move-perks">
    <li class="${move.loop ? "on" : ""}">${move.loop ? "✅" : "⬜"} A for loop gives it a <b>sparkle trail</b></li>
    <li class="${move.big ? "on" : ""}">${move.big ? "✅" : "⬜"} 8 actions gives it a <b>big finish</b>: you have ${move.actions}</li></ul>`;
}
function nameTiles() {
  return `<div class="name-tiles">${S.hang.names.map(n => `<button class="btn" data-move-name="${esc(n)}">${esc(n)}</button>`).join("")}</div>`;
}
function showMoveNames(r) {
  const unlocked = r.free_opened ? `<p class="guess-said">🔓 New: 🎬 Free stage, with stage toys like  scene("beach")  and  friend("cat")!</p>` : "";
  $("winBody").insertAdjacentHTML("beforeend", `${unlocked}${moveMeaning(r.move)}<p class="win-ask">Pick a name for your move:</p>${nameTiles()}`);
  $("winDo").innerHTML = "";
  nameThen(() => { $("winDo").innerHTML = winButtons(r); });
}
function askMoveName() {
  $("winTitle").textContent = "Rename your move";
  $("winStars").innerHTML = "";
  $("winBody").innerHTML = nameTiles();
  $("winDo").innerHTML = "";
  $("win").hidden = false;
  nameThen(() => { $("win").hidden = true; });
}
function nameThen(done) {
  $("winBody").querySelectorAll("[data-move-name]").forEach(b => b.addEventListener("click", async () => {
    const out = await post("/pixel/move/name", {id: me, name: b.dataset.moveName}).catch(() => null);
    if (out && out.state) S = out.state;
    StageSFX.play("ding");
    $("winBody").querySelector(".win-ask")?.remove();
    $("winBody").querySelector(".name-tiles").innerHTML = `<p class="named">✨ ${esc(b.dataset.moveName)} ✨</p>`;
    done();
  }));
}

// ---- Missions and trophies ---------------------------------------------------------------------
function openMissions() {
  $("missionList").innerHTML = S.chapters.map(ch => `<h3>${ch.icon} ${esc(ch.name)}</h3><div class="lvls">${
    ch.levels.map(l => {
      const n = l.stars.filter(Boolean).length;
      return `<button class="lvl${l.key === mode ? " here" : ""}" data-mission="${esc(l.key)}" ${l.open ? "" : "disabled"}>${l.open ? "" : "🔒 "}${esc(l.name)}${l.remixed ? " 🎨" : ""}${l.fixed ? " 🐞" : ""}<span class="${n ? "" : "none"}">${"★".repeat(n)}${"☆".repeat(3 - n)}</span></button>`;
    }).join("")}</div>`).join("") +
    `<h3>🎬 Free stage</h3><div class="lvls"><button class="lvl${mode === "free" ? " here" : ""}" data-mission="free" ${S.free_open ? "" : "disabled"}>${S.free_open ? "" : "🔒 "}Free stage<span class="none">${S.free_open ? "Any show you like" : "Finish My Move"}</span></button></div>`;
  $("trophies").innerHTML = S.badges.map(b =>
    `<div class="trophy${b.got ? " got" : ""}"><i>${b.icon}</i><span><b>${esc(b.name)}</b>${esc(b.how)}</span></div>`).join("");
  $("missions").hidden = false;
  const here = $("missionList").querySelector(".here");
  if (here) here.scrollIntoView({block: "center"});         // seventeen chapters: start where they are
}
function closeSheets() {
  for (const id of ["missions", "bookSheet"]) $(id).hidden = true;
}

// ---- Wiring -------------------------------------------------------------------------------------
document.addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  const d = b.dataset;
  if (d.view) { $("win").hidden = true; showView(d.view); }
  else if (d.chip !== undefined) { StageSFX.play("click"); $("bookSheet").hidden = true; addLine(d.chip); }
  else if (d.mission) { $("win").hidden = true; openMission(d.mission); }
  else if (d.rename) askMoveName();
  else if (d.copy) {
    const mine = $("code").value.trimEnd();       // on the Free stage an idea goes under their own show, never over it
    setCode(view.free && mine ? `${mine}\n${hintCode}` : hintCode);
    saveCode();
  }
  else if (d.guess) { guessPick = d.guess === "skip" ? null : Number(d.guess); runShow(); }
  else if (d.remix) { $("win").hidden = true; startRemix(); }
  else if (d.remixHint) { remixHint = true; paintYourTurn(); }
  else if (d.fix) { $("win").hidden = true; startFix(); }
  else if (d.fixHint) { fixHint = true; paintYourTurn(); }
  else if (d.showNew) showsDo("new");
  else if (d.showPerform) showFriends();
  else if (d.show !== undefined) showsDo(deletingShow ? "delete" : "open", Number(d.show));
  else if (d.showDel !== undefined) { deletingShow = d.showDel === "1"; paintShows(); }
  else if (d.read) readAloud([...$("verdict").querySelectorAll("p")].map(p => p.textContent).join(" "));
  else if (d.steps) { missStreak = 0; verdict(null); showSteps(); }
  else if (d.fixReset) { setCode(view.fix.code); $("code").focus(); }
});
new ResizeObserver(fitScreen).observe($("stageHost").parentElement);
$("runButton").addEventListener("click", runShow);
$("stageHost").addEventListener("click", pokePal);
$("skip").addEventListener("click", () => stage.hurry());
// 🐢 Slow: shows at half speed, to follow the lit-up line. Remembered on each computer.
function paintSlow(on) {
  $("slow").setAttribute("aria-pressed", on);
  if (stage) stage.slow(on);
  try { localStorage.setItem("pixelSlow", on ? "1" : "0"); } catch (_) {}
}
$("slow").addEventListener("click", () => paintSlow($("slow").getAttribute("aria-pressed") !== "true"));
try { paintSlow(localStorage.getItem("pixelSlow") === "1"); } catch (_) {}
// Esc, or a click on the dark part around a sheet, closes it.
const SHEETS = {missions: "closeMissions", bookSheet: "closeBook", artSheet: "closeArt", thingSheet: "closeThing", beads: "closeBeads", win: "winClose"};
function closeTopSheet() {
  for (const [sheet, button] of Object.entries(SHEETS)) if (!$(sheet).hidden) $(button).click();
}
addEventListener("keydown", e => { if (e.key === "Escape") closeTopSheet(); });
document.addEventListener("click", e => { if (e.target.classList.contains("sheet")) closeTopSheet(); });
// Reads the mission aloud with the computer's own voice, for anyone who'd rather
// hear it. A second press stops it.
const CODE_WORDS = {"()": " ", "(": " ", ")": " ", '"': " "};
const SYMBOL_NAMES = {"(": "open bracket", ")": "close bracket", '"': "quote mark", ":": "colon", "+": "plus", "=": "equals", "==": "two equals", "[": "open square bracket", "]": "close square bracket"};
function readAloud(text) {
  if (!("speechSynthesis" in window)) return;
  if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
  const said = text.replace(/"\s+marks/g, "quote marks").replace(/(^|\s)(==|[()":+=\[\]])(?=[\s.,]|$)/g, (_, gap, c) => `${gap}${SYMBOL_NAMES[c]}`)   // a symbol on its own is said by name
    .replace(/[()"]/g, c => CODE_WORDS[c]).replace(/\s+/g, " ");
  const line = new SpeechSynthesisUtterance(said);
  line.rate = .92;
  speechSynthesis.speak(line);
}
$("readOut").addEventListener("click", () => readAloud(coachWay && coachSpeech() || `${$("pipSays").textContent} ${$("job").textContent}`));
$("hint").addEventListener("click", showHint);
$("openBook").addEventListener("click", () => { $("bookSheet").hidden = false; });
$("closeBook").addEventListener("click", closeSheets);
$("openMissions").addEventListener("click", async () => { await refreshState(); openMissions(); });
$("closeMissions").addEventListener("click", closeSheets);
$("mute").addEventListener("click", () => { $("mute").textContent = StageSFX.toggle() ? "🔇" : "🔊"; });
$("calm").addEventListener("click", () => { PalStage.calm = !PalStage.calm; paintCalm(); });
$("tags").addEventListener("click", () => {
  hideTags = !hideTags;
  try { localStorage.setItem("pixelHideTags", hideTags ? "1" : "0"); } catch (_) {}
  paintTags();
});
$("winClose").addEventListener("click", () => { $("win").hidden = true; });
$("palSelect").addEventListener("change", async e => {
  const out = await post("/pixel/pal", {id: me, key: e.target.value}).catch(() => null);
  if (out && out.state) { S = out.state; resetStage(); }
});
$("code").addEventListener("input", () => { errorLine = 0; updateEditor(); saveCode(); });
$("code").addEventListener("scroll", syncScroll);
$("code").addEventListener("keydown", editorKeys);
$("code").addEventListener("paste", e => { if (coachTyping()) e.preventDefault(); });
// A click somewhere else shouldn't stop the keys from working.
addEventListener("keydown", e => {
  if (poke && poke.hears.includes("key") && POKE_KEYS[e.key] && document.activeElement === document.body && !$("stageView").hidden
      && !document.querySelector(".sheet:not([hidden]), .shelf:not([hidden])") && !e.ctrlKey && !e.metaKey && !e.altKey) {
    e.preventDefault();
    if (!e.repeat) sendPoke("key:" + POKE_KEYS[e.key]);       // holding a key down doesn't flood the server
    return;
  }
  if (document.activeElement !== document.body || $("stageView").hidden || running || !mode) return;
  if (document.querySelector(".sheet:not([hidden]), .shelf:not([hidden])") || (e.key.length !== 1 && e.key !== "Enter" && e.key !== "Backspace")) return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (!coachTyping()) { if (!coachMode()) $("code").focus(); return; }    // their own way: the key goes back where they were typing
  coachFocus();
  coachKey(e);
});
$("coachBack").addEventListener("click", () => showSteps());
$("coach").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (b) coachActions[b.dataset.coach]();
});

boot();
