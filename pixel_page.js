// Pixel Pals: the Stage and the Theatre. Students write Python, the server runs
// it and sends back a list of steps, and the stage plays them while the line
// that made each step lights up. It all sits on top of pixel_studio.js.
"use strict";

const StageSFX = PalStage.SFX;
let S = null;              // /pixel/state
let mode = null;           // the open mission's key, or "free"
let view = null;           // the open mission, from /pixel/level
let stage = null, watchStage = null;
let live = null;           // the show that's listening for clicks and keys
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
  everyone: "Everyone on stage does it: dance, wave, cheer or jump.",
  wave: "Waves its arm.", dance: "Dances with every part it has.", cheer: "Throws its arms up and jumps.",
  look: "Moves its eyes: left, right, up, down or front.",
  feel: "Changes its face: happy, sad, surprised, angry, sleepy, silly, cool or calm.",
  say: "Your pal says it in a speech bubble.", right: "Walks right. The number is how many spots.",
  left: "Walks left. The number is how many spots.", jump: "Jumps once.", spin: "Spins round.",
  shake: "Wobbles on the spot.", grow: "Gets bigger.", shrink: "Gets smaller.", hide: "Vanishes.",
  appear: "Comes back after hide().", pose: "Shows a frame you drew, by its name or number.",
  play: "Plays all your frames, like a flip book.", wait: "Waits a moment. Bigger numbers wait longer.",
  hearts: "Hearts float up.", stars: "Stars float up.", confetti: "Confetti falls everywhere.",
  rain: "It rains.", snow: "It snows.", sound: "Plays a noise.", scene: "Changes the place.",
  friend: "Brings a friend on stage.", friend_say: "Your friend says something.",
  friend_jump: "Your friend jumps.", bye: "Your friend leaves.", eat: "Your pet eats.",
  nap: "Your pet has a nap.", put: "Puts a thing on a spot, from 0 to 10.", take: "Picks up the thing your pal is standing on.",
  point: "Adds 1 to the score.", x: "Tells you which spot your pal is on, from 0 to 10.",
  clicks: "Tells you how many times your pal has been clicked.", hungry: "True if your pet is hungry.",
  sleepy: "True if your pet is tired.", touching: "True if your pal is standing on that thing.",
  score: "Tells you the score.", weather: 'Tells you "sun", "rain" or "snow".',
};
const SAMPLE = {
  say: 'say("Hello")', right: "right(3)", left: "left(3)", pose: 'pose("happy")', wait: "wait(2)",
  sound: 'sound("ding")', scene: 'scene("park")', friend: 'friend("cat")', friend_say: 'friend_say("Hi!")',
  put: 'put("star", 7)', take: 'take("star")', touching: 'touching("star")',
};
const sample = name => SAMPLE[name] || name + "()";
const CORE = ["say", "jump", "right", "left", "wave", "dance", "feel", "look", "hearts", "scene", "friend", "wait"];
const STORY_CORE = ["say", "feel", "right", "friend_say", "everyone", "scene"];
const PYTHON = {
  for: ["for loop", "for i in range(3):\n    ", "Repeats the lines pushed in under it."],
  list: ["list", 'names = ["Ana", "Ben"]', "Keeps a few things together."],
  variable: ["variable", 'name = "Luna"', "A name tag for something to keep."],
  fstring: ['f"..."', 'say(f"I am {name}")', "Puts a variable inside words."],
  def: ["def", "def dance():\n    ", "Teaches your pal a new word."],
  if: ["if / else", 'if mood == "happy":\n    \nelse:\n    ', "Does different things depending on the answer."],
  elif: ["elif", 'elif mood == "sad":\n    ', "One more question after an if."],
  while: ["while", "while x() < 9:\n    ", "Keeps going until the answer changes."],
  choice: ["choice", 'mood = choice(["happy", "sad"])', "Picks one thing from a list at random."],
  randint: ["randint", "randint(0, 10)", "Picks a random number between two numbers."],
  on_click: ["on_click", "def on_click():\n    ", "Runs when someone clicks your pal."],
  on_feed: ["on_feed", "def on_feed():\n    ", "Runs when someone presses Feed."],
  on_play: ["on_play", "def on_play():\n    ", "Runs when someone presses Play."],
  on_sleep: ["on_sleep", "def on_sleep():\n    ", "Runs when someone presses Sleep."],
  on_key: ["on_key", 'def on_key(key):\n    if key == "right":\n        right(1)', "Runs when someone presses a key."],
};
const ALL_PYTHON = Object.keys(PYTHON);

// ---- Getting going --------------------------------------------------------------------
function pageEnter(data) {
  S = data;
  stage = PalStage.create($("stageCanvas"), $("stageHost"));
  stage.setPal(currentPal());
  stage.fresh();
  $("mute").textContent = StageSFX.muted ? "🔇" : "🔊";
  showStars();
}
function freeToPlay() { return mode === "free" || mode === "story"; }
function currentPal() {
  return S.drawings.find(d => d.key === S.pal) || S.pip;
}
function showStars() { $("starCount").textContent = `★ ${S.stars} / ${S.max_stars}`; }

// Whatever show is going, it's over: nothing from it may land on the next screen.
function dropRun() {
  runTicket++;
  stopLive();
  if (stage) stage.stop();
  finishRun();
  setRunLine(0);
}
async function showView(name) {
  settle();
  dropRun();
  document.querySelectorAll("[data-view]").forEach(b => b.classList.toggle("on", b.dataset.view === name));
  $("drawView").hidden = name !== "draw";
  $("stageView").hidden = name !== "stage";
  $("theatreView").hidden = name !== "theatre";
  $("lifeView").hidden = name !== "life";
  $("storyView").hidden = name !== "story";
  document.querySelectorAll(".draw-only").forEach(el => { el.hidden = name !== "draw"; });
  document.querySelectorAll(".stage-only").forEach(el => { el.hidden = ["draw", "life", "story"].includes(name); });
  $("palPick").hidden = name !== "stage";
  if (name === "life") openLife(); else closeLife();     // before the wait, so its buttons always work
  if (name !== "story") closeStory();
  if (name !== "draw") await saveNow();
  if (name === "stage") {
    await refreshState();
    fillPalPick();
    if (!mode) await openMission(S.current);
    else resetStage();
  }
  if (name === "theatre") { await refreshState(); await openTheatre(); }
  if (name === "story") { await refreshState(); await openStory(); }
  if (name !== "theatre") closePark();
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
  if (key === "free") return openFree();
  const data = await get(`/pixel/level?id=${encodeURIComponent(me)}&level=${encodeURIComponent(key)}`).catch(() => null);
  if (!data || data.error) return;
  mode = key;
  view = data;
  hintsShown = 0;
  $("levelName").textContent = `${data.chapter.icon} ${data.name}`;
  const n = S.chapters.flatMap(c => c.levels).findIndex(l => l.key === key) + 1;
  $("levelWhere").textContent = `Mission ${n} of ${S.max_stars / 3}`;
  $("pipSays").innerHTML = fmt(data.pip);
  $("job").innerHTML = fmt(data.job);
  $("job").hidden = false;
  $("goals").hidden = false;
  $("hint").hidden = false;
  $("hint").textContent = "Help me";
  drawGoals(data.best);
  setCode(recall(codeKey(key)) ?? data.code ?? "");
  buildChips(data.commands, data.new, data.python, data.fresh_python);
  verdict(null);
  $("caption").textContent = "Press Show time! to see your code run.";
  resetStage();
}
function openFree(story = null) {
  mode = story ? "story" : "free";
  view = null;
  $("levelName").textContent = story ? `📖 Page ${story.pages.length + 1}` : "⭐ Free Stage";
  $("levelWhere").textContent = story ? story.title : "No mission. Just you.";
  $("pipSays").textContent = story
    ? `So far: "${story.pages.length ? story.pages[story.pages.length - 1].line : story.start}" What happens next? Make it with your pal. Everyone's pal can help!`
    : "Make anything you like! Every word you've learned works here. "
    + `Places: ${S.kit.scenes.join(", ")}. Sounds: ${S.kit.sounds.join(", ")}. Friends: ${S.kit.friends.join(", ")}.`;
  $("job").hidden = true;
  $("goals").hidden = true;
  $("hint").hidden = false;
  $("hint").textContent = "Give me an idea";
  setCode(story ? (story.waiting ? story.waiting.code : recall(codeKey("story")) ?? "") : recall(codeKey("free")) ?? S.free);
  const known = S.chapters.flatMap(c => c.levels).filter(l => l.open).map(l => l.key);
  const last = known[known.length - 1];
  get(`/pixel/level?id=${encodeURIComponent(me)}&level=${last}`).then(data => {
    if (freeToPlay() && data && data.commands) {
      buildChips(story ? S.everything : data.commands, [], data.python, []);
      if (story) castChips();
    }
  });
  verdict(story ? `<p>Press Show time! to try your page. When you like it, add it to the book.</p>`
    : `<p>When it's ready, share it with the class.</p>
    <p class="next"><button class="btn" data-publish="1">🎟️ Add to the Theatre</button></p>`);
  $("caption").textContent = "Press Show time! to see your code run.";
  resetStage();
}
function drawGoals(got) {
  $("goals").innerHTML = view.goals.map((g, i) =>
    `<li class="${got[i] ? "got" : ""}"><i>${got[i] ? "★" : "☆"}</i><span>${fmt(g)}</span></li>`).join("");
}

// ---- Chips -----------------------------------------------------------------------------
// Early on a chip writes the whole line. From Story Time on it starts the line
// and the student types the rest, so the help comes off bit by bit.
function buildChips(commands, fresh, python, freshPython) {
  const wholeLines = freeToPlay() || !view || view.number < 4;
  const cmds = commands.filter(c => WORDS[c]);
  const started = c => wholeLines || sample(c).endsWith("()") ? sample(c) : c + "(";
  // Only this chapter's words sit by the editor. The rest are in All words,
  // so the buttons never fill the screen.
  const near = cmds.length <= 12 ? cmds : cmds.filter(c => (view ? view.chapter_new : mode === "story" ? STORY_CORE : CORE).includes(c));
  $("chips").innerHTML =
    near.map(c => `<button class="chip${fresh.includes(c) ? " fresh" : ""}" data-chip="${esc(started(c))}" title="${esc(WORDS[c])}">${esc(sample(c))}</button>`).join("") +
    ALL_PYTHON.filter(k => python.includes(k) && (freshPython.includes(k) || !view || python.length <= 4)).map(k =>
      `<button class="chip py${freshPython.includes(k) ? " fresh" : ""}" data-chip="${esc(PYTHON[k][1])}" title="${esc(PYTHON[k][2])}">${esc(PYTHON[k][0])}</button>`).join("");
  const entry = (chip, label, words) =>
    `<div><dt><button class="chip" data-chip="${esc(chip)}">${esc(label)}</button></dt><dd style="margin:0">${esc(words)}</dd></div>`;
  $("book").innerHTML =
    cmds.map(c => entry(started(c), sample(c), WORDS[c])).join("") +
    ALL_PYTHON.filter(k => python.includes(k)).map(k => entry(PYTHON[k][1], PYTHON[k][0], PYTHON[k][2])).join("");
  $("kitWords").innerHTML =
    (commands.includes("scene") ? `<p><b>Places you can go:</b> ${esc(S.kit.scenes.join(", "))}</p>` : "") +
    (commands.includes("sound") ? `<p><b>Sounds:</b> ${esc(S.kit.sounds.join(", "))}</p>` : "") +
    (commands.includes("friend") ? `<p><b>Friends:</b> ${esc(S.kit.friends.join(", "))}</p>` : "") +
    (commands.includes("friend") && S.class_pals.length ? `<p><b>Classmates' pals:</b> ${esc(S.class_pals.join(", "))}, like <code>friend("${esc(S.class_pals[0])}")</code></p>` : "") +
    (commands.includes("put") ? `<p><b>Things:</b> ${esc(S.kit.props.join(", "))}</p>` : "");
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
  $("paint").innerHTML = paintCode(code);
  const count = Math.max(1, code.split("\n").length);
  $("lines").innerHTML = Array.from({length: count}, (_, i) =>
    i + 1 === runLine ? `<span class="run">▸${i + 1}</span>`
    : i + 1 === errorLine ? `<span class="err">▸${i + 1}</span>` : i + 1).join("\n");
  syncScroll();
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

// ---- Show time --------------------------------------------------------------------------
function captionFor(s) {
  const line = s.line ? `<b>Line ${s.line}:</b> ` : "";
  const says = {
    say: () => `your pal says "${esc(s.text)}"`, walk: () => `your pal walks to spot ${s.to}`,
    jump: () => "your pal jumps", spin: () => "your pal spins", shake: () => "your pal shakes",
    size: () => "your pal changes size", hide: () => "your pal vanishes", appear: () => "your pal comes back",
    pose: () => `your pal shows frame ${s.frame + 1}`, play: () => "your frames play like a flip book",
    wait: () => "your pal waits", hearts: () => "hearts float up", stars: () => "stars float up",
    confetti: () => "confetti falls", rain: () => "it rains", snow: () => "it snows",
    sound: () => `the ${esc(s.name)} sound plays`, scene: () => `the scene changes to ${esc(s.name)}`,
    friend: () => `a ${esc(s.kind)} comes on stage`, friend_say: () => `your friend says "${esc(s.text)}"`,
    friend_jump: () => "your friend jumps", bye: () => "your friend leaves", eat: () => "your pet eats",
    nap: () => "your pet has a nap", put: () => `a ${esc(s.prop)} lands on spot ${s.at}`,
    take: () => "your pal picks it up", point: () => `the score goes up to ${s.score}`,
    weather: () => `the weather is ${esc(s.kind)}`,
    event: () => s.key ? `Pip tests your game: the ${esc(s.key)} key is pressed` : `Pip tests your pet: ${esc(s.name)}`,
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
  if (running || !mode) return;
  running = true;
  const ticket = ++runTicket;
  saveCode();
  stopLive();
  StageSFX.wake();
  document.activeElement.blur();
  $("doRow").classList.add("playing");
  $("runButton").disabled = true;
  verdict(null);
  setBand(0);
  $("caption").textContent = "The curtain goes up...";
  let out = null;
  try { out = await post("/pixel/run", {id: me, level: freeToPlay() ? "free" : mode, code: $("code").value}); } catch (_) {}
  if (ticket !== runTicket) return;
  if (!out) {
    finishRun();
    verdict(`<p>The computer didn't answer. Check the Wi-Fi, then press Show time! again.</p>`, "bad");
    return;
  }
  if (out.error && !out.steps) {
    finishRun();
    verdict(`<p>${fmt(out.error)}</p>`, "bad");
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
    verdict(`<p>${fmt(out.error)}</p><p>Fix that line, then press Show time! again.</p>`, "bad");
    return;
  }
  if (mode === "story") {
    $("caption").textContent = "That's your page.";
    verdict(`<p>Nice! Change anything you like, then add it to the book.</p>
      <p class="next"><button class="btn" data-page-add="1">📖 Add to our story</button></p>`, "good");
  } else if (mode === "free") {
    if (out.rewards) showRewards(out.rewards);
    $("caption").textContent = "That's the end of your show.";
    verdict(`<p>Nice! Change something and run it again, or share it.</p>
      <p class="next"><button class="btn" data-publish="1">🎟️ Add to the Theatre</button></p>`, "good");
  } else {
    drawGoals(out.stars.map((g, i) => g || view.best[i]));
    view.best = out.stars.map((g, i) => g || view.best[i]);
    if (out.stars[0]) { stage.cheer(); missionDone(out); }
    else {
      stage.sigh();
      $("caption").textContent = "Not quite yet.";
      verdict(`<p>${fmt(out.reply || "Not quite. Read the job again.")}</p>`, "bad");
    }
    if (out.rewards) showRewards(out.rewards);
  }
  if (out.events.length) goLive(out.events, {code: $("code").value, level: freeToPlay() ? null : mode, seed: out.seed, events: out.rehearsed.slice()}, stage, $("liveBar"));
}
function finishRun() {
  running = false;
  $("runButton").disabled = false;
  $("doRow").classList.remove("playing");
}
function missionDone(out) {
  const all = out.stars.every(Boolean), order = S.chapters.flatMap(c => c.levels), at = order.findIndex(l => l.key === mode);
  const next = order[at + 1];
  $("caption").textContent = "The crowd loves it!";
  const more = out.stars.findIndex(g => !g);
  verdict(`<p><b>${all ? "Three stars! A perfect show!" : "You did it! The crowd is cheering."}</b>${more >= 0 ? ` For the next star: ${fmt(view.goals[more])}.` : ""}</p>
    <p class="next">${next ? `<button class="btn main" data-mission="${esc(next.key)}">Next mission →</button>` : `<button class="btn main" data-mission="free">Go to Free Stage →</button>`}</p>`, "good");
}
// The box always stays on screen, so the stage above it never jumps.
function verdict(html, kind) {
  const box = $("verdict");
  box.className = "panel" + (kind ? " " + kind : "");
  box.innerHTML = html || `<p style="color:var(--ink-soft)">Pip is watching. Your result shows up here.</p>`;
}
function fitScreen() {
  const wrap = $("stageHost").parentElement, room = wrap.getBoundingClientRect();
  if (!room.width) return;
  const w = Math.floor(Math.min(room.width - 6, (room.height - 6) * 16 / 9));
  $("stageHost").style.width = w + "px";
}
let hintsShown = 0;
let hintCode = "", ideaAt = 0;
function showHint() {
  if (freeToPlay()) {
    const ideas = mode === "story" ? book.ideas : S.ideas;
    hintCode = ideas[ideaAt++ % ideas.length];
    verdict(`<p><b>Try this one, then change it!</b></p><pre style="margin:2px 0 0;font:14px/18px var(--mono);white-space:pre-wrap">${esc(hintCode)}</pre><p class="next"><button class="btn" data-copy="1">Use this code</button></p>`);
    return;
  }
  if (!view) return;                  // the mission is still on its way
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
  for (const b of r.badges || []) lines.push(`${b.icon} ${b.name}`);
  for (const u of r.unlocked || []) lines.push(`🔓 New ${u.kind}: ${u.key}`);
  if (!lines.length) return;
  $("toast").textContent = lines.join("   ");
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4200);
}

// ---- Clicks and keys: a show that's still listening -----------------------------------------
const EVENT_BUTTONS = {feed: "🍎 Feed", play: "⚽ Play", sleep: "🌙 Sleep"};
function goLive(events, show, onStage, bar) {
  live = Object.assign(show, {stage: onStage, bar, wants: events, busy: false, waiting: []});
  const says = [];
  if (events.includes("click")) says.push("Click your pal!");
  if (events.includes("key")) says.push("Press the arrow keys or space!");
  bar.innerHTML = `<span>${says.join(" ")}</span>` +
    Object.entries(EVENT_BUTTONS).filter(([k]) => events.includes(k))
      .map(([k, label]) => `<button class="btn" data-event="${k}">${label}</button>`).join("");
  bar.hidden = false;
}
function stopLive() {
  if (!live) return;
  live.bar.hidden = true;
  live = null;
}
function fire(event) {
  const show = live;
  if (!show) return;
  if (show.busy) {                    // keep one waiting, so quick keys aren't lost
    if (show.waiting.length < 2) show.waiting.push(event);
    return;
  }
  answer(show, event);
}
async function answer(show, event) {
  show.busy = true;
  show.events.push(event);
  let out = null;
  try {
    out = await post("/pixel/react", {id: me, code: show.code, level: show.level, owner: show.owner, seed: show.seed, events: show.events});
  } catch (_) {}
  if (out && out.full && show === live) {
    show.bar.innerHTML = `<span>That's a lot of clicks! Press Show time! or Play again to start over.</span>`;
    show.wants = [];
  } else if (out && out.steps && show === live) {
    await show.stage.play(out.steps.filter(s => s.do !== "event"), {onStep(s) {
      if (show.stage !== stage) return;
      setRunLine(s.line);
      const text = captionFor(s);
      if (text) $("caption").innerHTML = text;
    }});
    if (show.stage === stage) setRunLine(0);
    if (out.error && show.stage === stage) { setBand(out.line || 0); verdict(`<p>${fmt(out.error)}</p>`, "bad"); }
  }
  show.busy = false;
  if (show === live && show.waiting.length) answer(show, show.waiting.shift());
}
const ARROWS = {ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down", " ": "space"};
addEventListener("keydown", e => {
  if (!live || !live.wants.includes("key") || e.target.matches("input, textarea, select") || !ARROWS[e.key]) return;
  e.preventDefault();
  if (!e.repeat) fire("key:" + ARROWS[e.key]);
});

// ---- Missions, trophies and the Theatre --------------------------------------------------------
function openMissions() {
  $("missionList").innerHTML = S.chapters.map(ch => `<h3>${ch.icon} ${esc(ch.name)}</h3><div class="lvls">${
    ch.levels.map(l => {
      const n = l.stars.filter(Boolean).length;
      return `<button class="lvl${l.key === mode ? " here" : ""}" data-mission="${esc(l.key)}" ${l.open ? "" : "disabled"}>${l.open ? "" : "🔒 "}${esc(l.name)}<span class="${n ? "" : "none"}">${"★".repeat(n)}${"☆".repeat(3 - n)}</span></button>`;
    }).join("")}</div>`).join("") +
    `<h3>⭐ Free Stage</h3><div class="lvls"><button class="lvl${mode === "free" ? " here" : ""}" data-mission="free" ${S.free_open ? "" : "disabled"}>${S.free_open ? "" : "🔒 "}Make anything<span class="none">${S.free_open ? "Your own show" : "After Jump for joy"}</span></button></div>`;
  $("trophies").innerHTML = S.badges.map(b =>
    `<div class="trophy${b.got ? " got" : ""}"><i>${b.icon}</i><span><b>${esc(b.name)}</b>${esc(b.how)}</span></div>`).join("");
  $("unlockList").innerHTML = S.unlocks.map(u =>
    `<div class="trophy${u.open ? " got" : ""}"><i>${u.open ? "🔓" : "🔒"}</i><span><b>${esc(u.key)}</b>${esc(u.kind)}: ${u.stars ? `${u.stars} stars` : `class total of ${u.class} stars`}</span></div>`).join("");
  $("missions").hidden = false;
}
function closeSheets() {
  for (const id of ["missions", "bookSheet", "publish"]) $(id).hidden = true;
}

let shows = [], watching = null;
async function openTheatre() {
  const data = await get("/pixel/theatre?id=" + encodeURIComponent(me)).catch(() => null);
  shows = data ? data.shows : [];
  $("myShowNote").textContent = !S.my_show ? "Make a show in Free Stage, then add it here."
    : S.my_show.waiting ? `"${S.my_show.title}" is waiting for your teacher to say OK.`
    : `Your show "${S.my_show.title}" has ${S.my_show.hearts} ♥`;
  $("showGrid").innerHTML = shows.length ? shows.map((s, i) => `
    <div class="show-card"><button data-watch="${i}"><canvas></canvas>
      <strong>${esc(s.title)}</strong>
      <small>by ${esc(s.by)} · ♥ ${s.hearts}${s.events.length ? " · Play with it!" : ""}</small>
    </button></div>`).join("") : `<div class="empty" style="grid-column:1/-1">No shows yet. Be the first!<br>In 🎭 Stage, press Missions and pick Free Stage.</div>`;
  $("showGrid").querySelectorAll("canvas").forEach((cv, i) => {
    const pal = shows[i].pal;
    thumbInto(cv, A.decode(pal.frames[0]), pal.size, pal.palette);
  });
  openPark(shows);
}
async function watchShow(s) {
  watching = s;
  stopLive();
  $("watch").hidden = false;
  $("watchTitle").textContent = s.title;
  $("watchBy").textContent = `by ${s.by}`;
  $("watchHeart").textContent = `${s.hearted ? "♥" : "♡"} ${s.hearts}`;
  $("watchHeart").hidden = s.mine;
  $("watchTake").hidden = !s.mine;
  if (!watchStage) watchStage = PalStage.create($("watchCanvas"), $("watchHost"));
  const out = await post("/pixel/watch", {owner: s.owner}).catch(() => null);
  if (!out || out.error && !out.steps) return;
  watchStage.setPal(out.pal);
  watchStage.fresh();
  await watchStage.play(out.steps);
  if (watching === s && out.events.length) goLive(out.events, {owner: s.owner, seed: out.seed, events: []}, watchStage, $("watchLive"));
}
function closeWatch() {
  $("watch").hidden = true;
  stopLive();
  if (watchStage) watchStage.stop();
  watching = null;
}
async function heartShow() {
  const out = await post("/pixel/heart", {id: me, owner: watching.owner}).catch(() => null);
  if (!out || !out.ok) return;
  watching.hearted = out.hearted;
  watching.hearts = out.hearts;
  $("watchHeart").textContent = `${out.hearted ? "♥" : "♡"} ${out.hearts}`;
  await openTheatre();
}
async function remix() {
  const code = `# Remixed from ${watching.title} by ${watching.by}\n${watching.code}`;
  closeWatch();
  await showView("stage");
  openFree();
  setCode(code);
  saveCode();
}
async function takeDown() {
  await post("/pixel/unpublish", {id: me}).catch(() => {});
  closeWatch();
  await refreshState();
  await openTheatre();
}
function askPublish() {
  $("publishNote").textContent = "";
  $("showTitle").value = S.my_show ? S.my_show.title : "";
  $("publishWho").textContent = S.checking ? "Your teacher looks at it first." : "";
  $("publish").hidden = false;
  $("showTitle").focus();
}
async function publishShow() {
  saveCode();
  const out = await post("/pixel/publish", {id: me, code: $("code").value, title: $("showTitle").value}).catch(() => null);
  if (!out) { $("publishNote").textContent = "The computer didn't answer. Try again."; return; }
  if (out.error) { $("publishNote").textContent = out.error; return; }
  S = out.state;
  $("publish").hidden = true;
  showRewards({badges: [...out.badges, out.waiting ? {icon: "💌", name: "Sent to your teacher!"} : {icon: "🎟️", name: "It's in the Theatre!"}]});
}

// ---- Wiring -------------------------------------------------------------------------------------
document.addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  const d = b.dataset;
  if (d.view) showView(d.view);
  else if (d.chip !== undefined) { StageSFX.play("click"); $("bookSheet").hidden = true; addLine(d.chip); }
  else if (d.mission) openMission(d.mission);
  else if (d.publish) askPublish();
  else if (d.pageAdd) openPageSheet();
  else if (d.leaf) playBook(+d.leaf);
  else if (d.takeLeaf) takeLeaf(+d.takeLeaf);
  else if (d.copy) {
    const had = $("code").value.trim();
    setCode(freeToPlay() && had ? `${had}\n${hintCode}` : hintCode);    // ideas add on, so nothing is lost
    saveCode();
  }
  else if (d.event) fire(d.event);
  else if (d.watch) watchShow(shows[+d.watch]);
});
new ResizeObserver(fitScreen).observe($("stageHost").parentElement);
$("runButton").addEventListener("click", runShow);
$("skip").addEventListener("click", () => stage.hurry());
// Esc, or a click on the dark part around a sheet, closes it.
const SHEETS = {pageSheet: "pageNo", missions: "closeMissions", bookSheet: "closeBook", watch: "closeWatch", publish: "publishNo", artSheet: "closeArt", beads: "closeBeads", cardSheet: "closeCard"};
function closeTopSheet() {
  for (const [sheet, button] of Object.entries(SHEETS)) if (!$(sheet).hidden) $(button).click();
}
addEventListener("keydown", e => { if (e.key === "Escape") closeTopSheet(); });
document.addEventListener("click", e => { if (e.target.classList.contains("sheet")) closeTopSheet(); });
// Reads the mission aloud with the computer's own voice, for anyone who'd rather
// hear it. A second press stops it.
const CODE_WORDS = {"()": " ", "(": " ", ")": " ", '"': " "};
function readAloud(text) {
  if (!("speechSynthesis" in window)) return;
  if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
  const line = new SpeechSynthesisUtterance(text.replace(/[()"]/g, c => CODE_WORDS[c]).replace(/\s+/g, " "));
  line.rate = .92;
  speechSynthesis.speak(line);
}
$("readOut").addEventListener("click", () => readAloud(`${$("pipSays").textContent} ${$("job").textContent}`));
$("hint").addEventListener("click", showHint);
$("openBook").addEventListener("click", () => { $("bookSheet").hidden = false; });
$("closeBook").addEventListener("click", closeSheets);
$("openMissions").addEventListener("click", async () => { await refreshState(); openMissions(); });
$("closeMissions").addEventListener("click", closeSheets);
$("mute").addEventListener("click", () => { $("mute").textContent = StageSFX.toggle() ? "🔇" : "🔊"; });
$("stageHost").addEventListener("click", () => { if (live && live.wants.includes("click")) fire("click"); });
$("watchHost").addEventListener("click", () => { if (live && live.wants.includes("click")) fire("click"); });
$("closeWatch").addEventListener("click", closeWatch);
$("watchAgain").addEventListener("click", () => watchShow(watching));
$("watchHeart").addEventListener("click", heartShow);
$("watchRemix").addEventListener("click", remix);
$("watchTake").addEventListener("click", takeDown);
$("publishGo").addEventListener("click", publishShow);
$("publishNo").addEventListener("click", () => { $("publish").hidden = true; });
$("palSelect").addEventListener("change", async e => {
  const out = await post("/pixel/pal", {id: me, key: e.target.value}).catch(() => null);
  if (out && out.state) { S = out.state; resetStage(); }
});
$("code").addEventListener("input", () => { errorLine = 0; updateEditor(); saveCode(); });
$("code").addEventListener("scroll", syncScroll);
$("code").addEventListener("keydown", editorKeys);

boot();
