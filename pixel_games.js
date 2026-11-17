// Shared playground rounds: opt in, then walk with the same controls as Hang out.
"use strict";
let gamePendingCover = null, gameBusy = false, gamePaintKey = "", gameRewardSeen = "";
let gameClock = {server: 0, local: 0};
const gameNow = () => gameClock.server + (performance.now() - gameClock.local) / 1000;
const currentGame = () => roomInfo && roomInfo.game;
const inRound = () => { const g = currentGame(); return g && g.joined.includes(roomInfo.you) && ["hiding", "playing"].includes(g.phase); };
const GAME_NAMES = {hide: "Hide & seek", tag: "Tag", race: "Red light, green light", dance: "Copy the dance", code: "💻 Code race", draw: "🎨 Draw & guess", apples: "🍎 Apple grab", ball: "⚽ Pal ball"};
const gameName = g => GAME_NAMES[g.kind];
const DANCE_ICONS = {wave: ["👋", "Wave"], jump: ["🦘", "Jump"], spin: ["🌀", "Spin"], cheer: ["🎉", "Cheer"]};
let danceReady = false;
const gamePerson = seat => ((roomStage?.state.room || []).find(m => m.seat === seat) || {}).name || "A friend";

async function gameDo(action, extra = {}) {
  if (gameBusy) return;
  gameBusy = true;
  const out = await tap("game", Object.assign({action}, extra));
  gameBusy = false;
  if (!out) tipFor("Couldn't reach the game. Please try again.");
  else if (out.error) tipFor(out.error);
  else if (out.message) tipFor(out.message);
  return out;
}
function buildGamePane(box) {
  const g = currentGame(), you = roomInfo?.you;
  box.classList.add("games-pane");
  if (!g) {
    box.innerHTML = jobsHtml() + winterCard() + `<p class="me-note">Invite the other kids! Anyone can start a game. Friends choose whether to join.</p>
      <button class="wide race-start" data-game="create" data-kind="code"><b>💻 Code race</b><small>Everyone codes the same job · solve it and your pal does it for everyone</small></button>
      <button class="wide draw-start" data-game="create" data-kind="draw"><b>🎨 Draw & guess</b><small>Take turns drawing a secret thing · friends tap the picture they think it is</small></button>
      <button data-game="create" data-kind="hide"><b>Hide & seek</b><small>Random seeker · 20 seconds to hide</small></button>
      <button data-game="create" data-kind="tag"><b>Tag</b><small>Chase your friends · pass “it”</small></button>
      <button data-game="create" data-kind="race"><b>Red light, green light</b><small>Race to the flag · freeze on red</small></button>
      <button data-game="create" data-kind="dance"><b>Copy the dance</b><small>Tap the moves in order · 3 rounds</small></button>
      <button data-game="create" data-kind="apples"><b>🍎 Apple grab</b><small>Walk onto apples · most apples in 60 seconds wins</small></button>
      <button data-game="create" data-kind="ball"><b>⚽ Pal ball</b><small>Two teams · walk into the ball to kick it into your goal</small></button>
      <p class="me-note">Finish a game for 🪙 coins and class-party points. Winners get extra coins. Your first game of each kind gives a 🎁 gift, and so does every third one after that.</p>`;
    return;
  }
  const joined = g.joined.includes(you);
  let body = `<h4>${esc(gameName(g))}</h4>`;
  if (g.phase === "lobby") {
    body += `<p class="me-note">${g.joined.length} joined: ${g.joined.map(s => esc(gamePerson(s))).join(", ")}. At least 2 needed. The round starts after the countdown.</p>`;
    if (!joined) body += `<button data-game="join">Join game</button>`;
    if (g.host === you) body += `<button data-game="start" ${g.joined.length < 2 ? "disabled" : ""}>Start now</button>`;
  } else if (g.phase === "results") {
    body += `<p class="me-note">${esc(g.message)}</p>`;
    if (g.reward) body += `<p class="me-note">${g.reward.won ? "🏆 You won! " : ""}${g.reward.coins ? `+${g.reward.coins} 🪙 coins! ` : ""}+${g.reward.points} class-party points!${g.reward.gift ? " Your gift: " + esc(S.hang.catalog[g.reward.gift].name) + ". Find it in Me." : ""}</p>`;
    body += `<p class="me-note">Another game can start in a moment.</p>`;
  } else if (!joined && g.kind === "code") {
    body += `<p class="me-note">Your friends are coding! Join in now: everyone gets the same job.</p><button class="wide race-run" data-game="join">💻 Join the Code race</button>`;
  } else if (!joined && g.kind === "draw") {
    body += `<p class="me-note">Your friends are drawing and guessing! Join in now and guess the next picture.</p><button class="wide race-run" data-game="join">🎨 Join Draw & guess</button>`;
  } else if (!joined) {
    body += `<p class="me-note">A game is on. You can join the next one, or keep playing here.</p>`;
  } else if (g.kind === "code") {
    body = racePane(g, you);
  } else if (g.kind === "draw") {
    body = drawPane(g, you);
  } else if (g.kind === "race") {
    const done = g.done.includes(you);
    body += `<p class="me-note">${done ? "🏁 You made it! Cheer for your friends." : g.light === "red" ? "🔴 <b>RED LIGHT!</b> Don't move!" : "🟢 <b>GREEN LIGHT!</b> Run to the flag!"}</p>`;
    if (!done) body += `<button class="wide" data-run="1" ${g.light === "red" ? "disabled" : ""}><span>🏃</span>Run!</button>
      <p class="me-note">Press Run, or the → key, again and again to run. Stop pressing when the light turns red, or you go back a bit.</p>`;
  } else if (g.kind === "dance") {
    const ready = gameNow() >= g.ready, finished = g.step >= g.seq.length;
    body += `<p class="me-note">Round ${g.round + 1} of 3. ${finished ? "⭐ You did the whole dance! Wait for the next round." : ready ? "Tap the lit-up move!" : "Get ready... look at the dance!"} Rounds won: ${g.score}</p>
      <div class="dance-seq">${g.seq.map((m, i) => `<span class="${i < g.step ? "done" : i === g.step && ready ? "now" : ""}" title="${DANCE_ICONS[m][1]}">${DANCE_ICONS[m][0]}</span>`).join("")}</div>` +
      Object.entries(DANCE_ICONS).map(([m, [icon, word]]) => `<button data-step="${m}" ${ready && !finished ? "" : "disabled"}><span>${icon}</span>${word}</button>`).join("");
  } else if (g.kind === "apples") {
    const scores = g.scores || {};
    body += `<p class="me-note">Walk your pal onto an apple to grab it. A golden apple is worth 3! Most apples when the 60 seconds end wins.</p>`;
    body += g.joined.map(s => `<p class="me-note">🍎 ${esc(gamePerson(s))}${s === you ? " (you)" : ""}: ${scores[s] || 0}</p>`).join("");
    body += `<p class="me-note">Click the ground to walk, or use the arrow keys.</p>`;
  } else if (g.kind === "ball") {
    const teams = g.teams || {}, scores = g.team_scores || {}, mine = teams[you];
    body += `<p class="me-note">${mine ? `You're on ${mine === "blue" ? "🔵 Blue" : "🟠 Orange"}!` : "Cheer for your friends!"} Walk into the ball to kick it. Chase the ball and kick it again!</p>`;
    body += `<p class="me-note">🔵 Blue team: kick the ball right, into the blue goal. 🟠 Orange team: kick the ball left, into the orange goal. More goals when the 90 seconds end wins.</p>`;
    body += `<p class="me-note"><b>🔵 Blue ${scores.blue || 0} — ${scores.orange || 0} Orange 🟠</b></p>`;
    body += g.joined.map(s => `<p class="me-note">${teams[s] === "blue" ? "🔵" : "🟠"} ${esc(gamePerson(s))}${s === you ? " (you)" : ""}</p>`).join("");
    body += `<p class="me-note">Click the ground to walk, or use the arrow keys.</p>`;
  } else if (g.kind === "tag") {
    body += `<p class="me-note">${g.it === you ? "You're IT! Get close to another player to tag them." : esc(gamePerson(g.it)) + " is IT! Keep moving!"} Stay in the Park and Wedding garden. After a tag, everyone gets 3 seconds to run away.</p>`;
    body += `<p class="me-note">Your tags: ${g.tags[you] || 0}. Click to run, or use the arrow keys.</p>`;
  } else if (g.phase === "hiding" && g.it === you) {
    body += `<p class="me-note">You're the seeker! Count while everyone hides. When the countdown ends, click a hiding place to look behind it.</p>`;
  } else if (g.found.includes(you)) {
    body += `<p class="me-note">You were found! Cheer on your friends while the seeker finishes. Stay for your reward.</p>`;
  } else if (g.it !== you && g.phase === "playing") {
    body += `<p class="me-note">${g.hiding ? "You're tucked away. Stay quiet!" : "You didn't get to a hiding place in time. Stay still and hope the seeker misses you!"} ${esc(gamePerson(g.it))} is searching.</p>`;
  } else {
    const searching = g.it === you;
    body += `<p class="me-note">${searching ? "Click a hiding place to walk over and look behind it." : g.hiding ? "You're hidden! Choose another spot to move before time runs out." : "Pick a hiding place below, or click one in the world. Your pal walks there and hides!"}</p>`;
    body += (roomInfo.cover || []).map(c => `<button data-cover="${c.key}" aria-pressed="${g.hiding === c.key}">${esc(c.name)}<small>${c.x < 320 ? "Park" : "Wedding garden"}</small></button>`).join("");
  }
  if (joined && g.phase !== "results") body += `<button data-game="leave">Leave game</button>`;
  const typing = document.activeElement?.id === "raceCode" && [$("raceCode").selectionStart, $("raceCode").selectionEnd];
  box.innerHTML = body;
  if (typing && $("raceCode")) { $("raceCode").focus(); $("raceCode").setSelectionRange(...typing); }
  paintDrawBoard();
}
function paintGameState(data) {
  const g = data.game, status = $("gameStatus"), open = data.open;
  gameClock = {server: g?.now || Date.now() / 1000, local: performance.now()};
  status.hidden = !open;
  const key = JSON.stringify([g?.id, g?.phase, g?.joined, g?.it, g?.found, g?.hiding, g?.tags, g?.message, g?.reward, data.you,
                              g?.light, g?.done, g?.seq, g?.step, g?.round,
                              g?.solved, g?.bonus, g?.pause, g?.reveal, g?.score, g?.job?.job,
                              g?.drawer, g?.guessed, g?.word, g?.choices, g?.apples, g?.scores,
                              g?.teams, g?.team_scores]);
  if (key !== gamePaintKey) {
    gamePaintKey = key;
    if (roomPane === "games") buildRoomButtons();
    gamePendingCover = null;
  }
  // A Code race needs room for the code, and every pal in view: the camera stays on the Park.
  const racing = ["code", "draw"].includes(g?.kind) && g.phase === "playing" && g.joined.includes(data.you);
  $("hangView").classList.toggle("racing", !!racing);
  $("hangView").classList.toggle("playing", !!inRound());
  if (roomStage) roomStage.state.camera = racing ? () => 0 : null;
  // A round's controls are in Games (the job, the moves, the hiding places), so a player is taken there once when it starts.
  if (g && g.joined.includes(data.you) && ["hiding", "playing"].includes(g.phase) && raceShown !== g.id) {
    raceShown = g.id;
    if (roomPane !== "games") { roomPane = "games"; artArmed = furnArmed = buyArmed = null; buildRoomButtons(); }
  }
  if (g?.phase === "results" && g.reward && gameRewardSeen !== String(g.id)) {
    gameRewardSeen = String(g.id);
    refreshState().then(() => { if (roomPane === "me" || roomPane === "games") buildRoomButtons(); });
    banner(`${g.reward.won ? "🏆 You won!" : "Round complete!"}<small>${g.reward.coins ? `+${g.reward.coins} 🪙 · ` : ""}+${g.reward.points} class-party points${g.reward.gift ? " · A new gift in Me!" : ""}</small>`, 4500);
  }
  const counting = g?.kind === "hide" && g.phase === "hiding" && g.it === data.you;
  $("seekerCurtain").hidden = !counting;
  $("myMove").disabled = !!inRound();
  paintDrawBoard();
  paintGameClock();
}
function paintGameClock() {
  if (!roomInfo || $("hangView").hidden) return;
  const g = currentGame(), title = $("gameTitle"), detail = $("gameDetail");
  if (!g) {
    $("gameStatus").classList.remove("invite");
    title.textContent = "Play with friends";
    detail.textContent = jobsWord() + "💻 Code race, 🎨 draw & guess, 🍎 apple grab, ⚽ pal ball, tag, hide & seek, a race or a dance →";
    return;
  }
  const seconds = Math.max(0, Math.ceil(g.until - gameNow()));
  const job = g.kind === "code" && g.phase === "playing" && !g.pause && g.job;
  title.textContent = job ? `💻 ${job.job}` : gameName(g);
  const joined = g.joined.includes(roomInfo.you);
  $("gameStatus").classList.toggle("invite", g.phase === "lobby" && !joined);
  detail.textContent = g.phase === "lobby" ? `${g.joined.length} joined · starts in ${seconds}s · ${joined ? "You're in!" : "👉 Tap here to join!"}`
    : g.phase === "results" ? `Round over · next game in ${seconds}s`
    : g.kind === "race" ? `${seconds}s left · ${g.light === "red" ? "🔴 Red light: freeze!" : "🟢 Green light: run!"} · ${g.done.length} at the flag`
    : g.kind === "dance" ? `Round ${g.round + 1} of 3 · ${seconds}s left · ${g.step} of ${g.seq.length} moves`
    : g.kind === "apples" ? `${seconds}s left · 🍎 ${(g.apples || []).length} on the ground · You have ${g.score}`
    : g.kind === "ball" ? `${seconds}s left · 🔵 ${(g.team_scores || {}).blue || 0} — ${(g.team_scores || {}).orange || 0} 🟠`
    : g.kind === "code" ? (g.pause ? `Next job in ${seconds}s` : `${g.job.icons} · Job ${g.round + 1} of ${g.rounds} · ${seconds}s · ${g.solved.length} of ${g.joined.length} solved`)
    : g.kind === "draw" ? (g.pause ? `Next picture in ${seconds}s` : `${g.drawer === roomInfo.you ? "You're drawing!" : gamePerson(g.drawer) + " is drawing"} · Picture ${g.round + 1} of ${g.turns} · ${seconds}s · ${g.guessed.length} guessed`)
    : g.phase === "hiding" ? `${seconds}s to hide · ${g.it === roomInfo.you ? "You're counting!" : gamePerson(g.it) + " is counting"}`
    : `${seconds}s left · ${gamePerson(g.it)} ${g.kind === "tag" ? "is IT" : "is seeking"}${g.kind === "hide" ? " · " + g.found.length + "/" + (g.joined.length - 1) + " found" : g.grace > gameNow() ? " · Head start!" : ""}`;
  $("seekerCount").textContent = seconds;
  const ready = g.kind === "dance" && g.phase === "playing" && gameNow() >= g.ready;
  if (ready !== danceReady) { danceReady = ready; if (roomPane === "games") buildRoomButtons(); }
  const answer = g.kind === "code" && g.phase === "playing" && gameNow() - g.round_at >= g.answer_after;
  if (answer !== raceAnswerOpen) { raceAnswerOpen = answer; if (roomPane === "games" && raceHelp) buildRoomButtons(); }
}
setInterval(() => { paintGameClock(); tipKeepUp(); }, 250);
function chooseGameCover(key) {
  const g = currentGame();
  if (!inRound() || g.kind !== "hide") return;
  const action = g.phase === "hiding" && g.it !== roomInfo.you ? "hide" : g.phase === "playing" && g.it === roomInfo.you ? "search" : null;
  if (!action) return;
  const cover = roomInfo.cover.find(c => c.key === key);
  if (!cover) return;
  gamePendingCover = {cover, action, id: g.id};
  walkTo(cover.x, cover.y);
  tipFor(`Walking to the ${cover.name.toLowerCase()} to ${action}…`);
}
function gameTick(mine) {
  if (!gamePendingCover || !inRound() || gameBusy) return;
  const {cover, action, id} = gamePendingCover;
  if (currentGame().id !== id) { gamePendingCover = null; return; }
  if (Math.hypot(mine.x - cover.x, (mine.y - cover.y) * 42) > 12) return;
  gamePendingCover = null;
  gameDo(action, {cover: cover.key}).then(out => {
    if (out?.ok && action === "hide") tipFor(`You're hidden ${cover.at}!`);
  });
}
// The bar above the world: one tap joins a game that's waiting for players, and opens Games.
$("gameStatus").addEventListener("click", () => {
  const g = currentGame();
  if (g && g.phase === "lobby" && !g.joined.includes(roomInfo.you)) gameDo("join");
  roomPane = "games"; artArmed = null; buildRoomButtons();
});
$("roomButtons").addEventListener("click", e => {
  const action = e.target.closest("[data-game]"), cover = e.target.closest("[data-cover]");
  const step = e.target.closest("[data-step]"), run = e.target.closest("[data-run]"), mine = myMember();
  if (step && !step.disabled) { PalStage.SFX.wake(); gameBusy = false; gameDo("step", {name: step.dataset.step}); }
  else if (run && !run.disabled && mine) walkTo(mine.x + 30, mine.y);
  else if (action) gameDo(action.dataset.game, {kind: action.dataset.kind});
  else if (cover) chooseGameCover(cover.dataset.cover);
  else if (e.target.closest("[data-put]")) raceAdd(e.target.closest("[data-put]").dataset.put);
  else if (e.target.closest("[data-race]")) raceButton(e.target.closest("[data-race]").dataset.race);
  else if (e.target.closest("[data-ink]")) { drawInk = +e.target.closest("[data-ink]").dataset.ink; buildRoomButtons(); }
  else if (e.target.closest("[data-drawwipe]")) { drawPending.clear(); tap("game", {action: "paint", wipe: true}); }
  else if (e.target.closest("[data-guess]")) drawGuess(e.target.closest("[data-guess]"));
  else if (e.target.closest("[data-chestleave]")) { roomPane = "do"; buildRoomButtons(); }     // the chest stays shut; walk back to try again
});

// ---- Code race: everyone codes the same little job ------------------------------------------
// Green chips add a line at the bottom, pushed in under a for line. Solving it makes
// your pal do the code in front of everyone.
const RACE_CHIPS = ["jump()", "wave()", "spin()", "cheer()", "dance()", "hearts()", "stars()", 'say("Hello!")'];
let raceCode = "", raceFor = "", raceMsg = "", raceGood = false, raceHelp = 0, raceShown = null, raceAnswerOpen = false, raceOut = 0;
function racePane(g, you) {
  const job = g.job, key = `${g.id}:${g.round}`;
  if (raceFor !== key) { raceFor = key; raceCode = ""; raceMsg = ""; raceGood = false; raceHelp = 0; raceOut = 0; }
  let body = "";      // the job itself is in the bar above the world, so it never scrolls away
  if (g.pause) {
    const r = g.reveal || {};
    body += `<p class="me-note">${r.by ? `⚡ <b>${esc(r.by)}</b> was fastest! Here's their code:` : "Time! Here's one way to code it:"}</p>
      <pre class="race-reveal">${esc(r.code || "")}</pre><p class="me-note">The next job is coming...</p>`;
  } else if ((g.bonus || []).includes(you)) {
    body += `<p class="race-msg good">🌟 Bonus done! Clap for your friends while they finish.</p><pre class="race-reveal">${esc(g.mine)}</pre>`;
  } else if (g.solved.includes(you)) {        // solved: the same code box, for the bonus
    if (!raceCode) raceCode = g.mine;
    body += `<p class="race-msg good">⭐ You solved it!</p><p class="race-bonus">🌟 Bonus: do the whole job 2 times! ${esc(g.bonus_icons)}</p>
      <p class="me-note">💡 Copy your lines again under them, or put them all in a 🔁 loop.</p>` + raceEditor(job, false);
  } else {
    body += raceEditor(job, true) + raceHelpText(g);
  }
  const names = g.solved.map(s => esc(gamePerson(s)) + ((g.bonus || []).includes(s) ? " 🌟" : "")).join(", ");
  body += `<p class="me-note race-score">Solved: ${names || "nobody yet"} · Your points: ${g.score}<br><small>Solve it: 1 point. First: 2 points. +3 🪙 each time! 🌟 Bonus: +1 🪙</small></p>`;
  return body;
}
function raceEditor(job, help, chest = false) {
  // At a 🧰 chest, only the moves its puzzle needs, and the loop only when it wants one.
  const loops = !chest || job.loops, chips = [...(loops ? ["for i in range(3):"] : []), ...(chest ? job.moves : [...RACE_CHIPS, ...job.chips])];
  return `<textarea id="raceCode" spellcheck="false" autocapitalize="off" autocomplete="off" aria-label="Your code"
      placeholder="${chest ? "Tap a green button ↓" : "Tap the green commands, or type here"}">${esc(raceCode)}</textarea>
    <div class="race-chips">${chips.map(c => `<button data-put="${esc(c)}"${c.startsWith("for") ? ' class="loop"' : ""}>${c.startsWith("for") ? "🔁 " : ""}${esc(c)}</button>`).join("")}</div>
    <button class="wide race-run" data-race="run">▶ Run my code</button>
    <div class="race-row${loops ? "" : " two"}"><button data-race="undo">⌫ ${chest ? "Take back" : "Undo line"}</button>${loops ? `<button data-race="out">⇤ Out of loop</button>` : ""}
      ${help ? `<button data-race="help">💡 ${raceHelp ? "More help" : "Help"}</button>` : ""}</div>
    <p class="race-msg${raceGood ? " good" : ""}${raceMsg ? " said" : ""}" id="raceMsg" role="status">${esc(raceMsg)}</p>`;
}
function raceTip(job) {
  return job.loops === 2 ? "Use two 🔁 for lines. Tap ⇤ Out of loop before the second one, so it isn't inside the first."
    : job.loops ? "Tap 🔁 for and type how many times. The moves pushed in under it happen again and again. For a move that happens once, after the loop, tap ⇤ Out of loop first."
    : `One line for each move, top to bottom: ${job.icons}`;
}
function raceHelpText(g) {
  if (!raceHelp) return "";
  const answerIn = Math.ceil(g.round_at + g.answer_after - gameNow());
  const answer = raceHelp > 1 && answerIn <= 0 ? `<pre class="race-reveal">${esc(g.job.hint)}</pre>`
    : raceHelp > 1 ? `<p class="me-note">The whole answer shows in ${answerIn}s. Try first!</p>` : "";
  return `<p class="me-note">💡 ${raceTip(g.job)}</p>${answer}`;
}
function raceLines() {
  const text = $("raceCode").value.replace(/\s+$/, "");
  return text ? text.split("\n") : [];
}
function raceSet(lines) {
  $("raceCode").value = lines.join("\n");
  raceCode = $("raceCode").value;
}
function raceAdd(line) {
  const lines = raceLines(), last = lines[lines.length - 1] || "";
  const indent = (last.match(/^ */)[0] + (last.trimEnd().endsWith(":") ? "    " : "")).slice(4 * raceOut);
  raceOut = 0;
  raceSet([...lines, indent + line]);
  raceSay("", false);
  PalStage.SFX.play("pop");
  if (line.startsWith("for")) {       // pick the 3, so typing a number changes it
    const box = $("raceCode"), at = box.value.lastIndexOf("3");
    box.focus();
    box.setSelectionRange(at, at + 1);
    raceSay("Type how many times! Then tap the moves to repeat.", false);
  }
}
function raceSay(text, good) {
  raceMsg = text; raceGood = good;
  const el = $("raceMsg");
  if (el) { el.textContent = text; el.classList.toggle("good", good); el.classList.toggle("said", !!text && text !== "Running..."); }
}
async function raceButton(what) {
  if (what === "help") { raceHelp = Math.min(2, raceHelp + 1); buildRoomButtons(); return; }
  if (!$("raceCode")) return;
  const lines = raceLines();
  if (what === "undo") { raceSet(lines.slice(0, -1)); raceOut = 0; return; }
  if (what === "out") {      // the next command goes one step further out
    const last = lines[lines.length - 1] || "", deep = last.match(/^ */)[0].length / 4;
    if (last.trimEnd().endsWith(":")) raceSay("Put a move inside the loop first!", false);
    else if (raceOut >= Math.floor(deep)) raceSay("You're not inside a loop. Tap any command.", false);
    else { raceOut += 1; raceSay("⇤ The next command goes outside the loop.", true); }
    return;
  }
  const code = $("raceCode").value;
  if (!code.trim()) { raceSay("Tap a green command first!", false); return; }
  raceSay("Running...", false);
  if (roomPane === "chest") return chestRun(code);
  const out = await tap("game", {action: "run", code});
  if (!out) raceSay("Couldn't reach the game. Please try again.", false);
  else if (out.error) raceSay(out.error, false);
  else {
    const good = "bonus" in out ? out.bonus : !!out.solved;      // a solver's runs are for the bonus
    raceSay(out.message, good);
    if (good) refreshState();
    else PalStage.SFX.play("boing");
  }
}
$("roomButtons").addEventListener("input", e => { if (e.target.id === "raceCode") raceCode = e.target.value; });
// Tab puts in 4 spaces, Enter after a : starts the next line 4 spaces further in, and Ctrl+Enter runs.
$("roomButtons").addEventListener("keydown", e => {
  const box = e.target;
  if (box.id !== "raceCode") return;
  const at = box.selectionStart;
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); raceButton("run"); }
  else if (e.key === "Tab") { e.preventDefault(); box.setRangeText("    ", at, box.selectionEnd, "end"); }
  else if (e.key === "Enter") {
    const line = box.value.slice(box.value.lastIndexOf("\n", at - 1) + 1, at);
    e.preventDefault();
    box.setRangeText("\n" + line.match(/^ */)[0] + (line.trimEnd().endsWith(":") ? "    " : ""), at, box.selectionEnd, "end");
  } else return;
  raceCode = box.value;
});

// ---- 🧰 Code chests: one in each place, and today's puzzle opens it ------------------------------
// Walking up to a chest opens its pane, with the same code box as the Code race. The chests further
// along the world are harder, and they all lock again tomorrow with new puzzles.
const CHEST_ANSWER_AFTER = 30;      // seconds of trying before More help shows the whole answer
let chestPlace = null, chestNear = null, chestSince = 0, chestJust = "";
const chestNow = () => (S.hang.chests || []).find(c => c.place === chestPlace);
function lookForChest(mine) {
  const c = PalHang.chestAt(roomStage.state.places || ["park"], mine.x, mine.y, S.hang.chests);
  if (!c) { chestNear = null; return; }
  if (c.place === chestNear) return;
  chestNear = chestPlace = c.place;
  roomPane = "chest"; artArmed = furnArmed = buyArmed = null;
  buildRoomButtons();
  PalStage.SFX.play("ding");
  tipFor("🧰 A code chest! Code it open on the right.", 5000);
}
// 🧰 Take me: the 🎯 chest job walks your pal to the nearest chest still shut.
function goToChest() {
  const mine = myMember(), places = roomStage.state.places || [];
  if (!mine || atHome()) { tipFor("Go out the door first! The chests are outside."); return; }
  const shut = (S.hang.chests || []).filter(c => !c.open && places.includes(c.place))
    .map(c => ({c, x: places.indexOf(c.place) * PalStage.W + c.x})).sort((a, b) => Math.abs(a.x - mine.x) - Math.abs(b.x - mine.x));
  if (!shut.length) { tipFor("You opened every chest today! New puzzles tomorrow."); return; }
  walkTo(shut[0].x, shut[0].c.deep);
  tipFor(`🧰 Walking to the ${PLACE_NAMES[shut[0].c.place][1]} chest...`);
}
function buildChestPane(box) {
  const c = chestNow(), world = (roomInfo && roomInfo.world) || ["park"];
  box.classList.add("games-pane");
  if (!c) { box.innerHTML = ""; return; }
  const key = `chest:${c.place}:${c.job}`;
  if (raceFor !== key) { raceFor = key; raceCode = ""; raceMsg = ""; raceGood = false; raceHelp = 0; raceOut = 0; chestSince = performance.now(); chestJust = ""; }
  const here = S.hang.chests.filter(x => world.includes(x.place)), opened = here.filter(x => x.open).length;
  let body = `<div class="chest-head"><span class="chest-icon" aria-hidden="true">${c.open ? "🪙" : "🧰"}</span>
      <div><h4>${c.open ? "You opened it!" : "Code the chest open!"}</h4><small>${esc(PLACE_NAMES[c.place][1])} chest${c.open ? "" : " · wins 10 🪙"}</small></div>
      <button data-chestleave>← Leave</button></div>`;
  if (c.open) {
    const left = here.length - opened;
    body += `<p class="race-msg good said">${esc(chestJust || "✅ You opened it!")}</p>
      <p class="me-note">🧰 You've opened ${opened} of ${here.length} chests today.${left ? "" : " That's all of them! New puzzles tomorrow."}</p>` +
      (left ? `<button class="wide race-run" data-go-chest="1">🧰 Take me to the next chest</button>` : "");
  } else {
    let help = "";
    if (raceHelp) {
      const wait = Math.ceil(CHEST_ANSWER_AFTER - (performance.now() - chestSince) / 1000);
      help = `<p class="me-note">💡 ${raceTip(c)}</p>` + (raceHelp < 2 ? "" : wait <= 0 ? `<pre class="race-reveal">${esc(c.hint)}</pre>`
        : `<p class="me-note">The whole answer shows in ${wait}s. Try first, then press More help again!</p>`);
    }
    body += `<div class="chest-want"><small>🔒 The chest wants your pal to:</small><b>${esc(c.words || c.icons)}</b>${c.loops ? `<small>💡 ${esc(c.job)}</small>` : ""}</div>
      <ol class="chest-steps">${c.loops ? "<li>Tap <b>🔁 for</b>, then type how many times.</li><li>Tap the moves to put them in the loop.</li>"
        : "<li>Tap the green buttons to add code.</li>"}<li>Press <b>▶ Run my code</b>.</li></ol>` + raceEditor(c, true, true) + help;
  }
  box.innerHTML = body;
  if (raceHelp && !c.open) box.lastElementChild.scrollIntoView({block: "nearest"});      // the help, under the code box
}
async function chestRun(code) {
  const c = chestNow();
  if (!c) return;
  const out = await tap("chest", {place: c.place, code});
  if (!out) raceSay("Couldn't reach the Hang out. Please try again.", false);
  else if (out.error) raceSay(out.error, false);
  else if (!out.open) { raceSay(out.message, false); PalStage.SFX.play("boing"); }
  else {
    c.open = true;
    chestJust = out.message;
    PalStage.SFX.play("fanfare");
    buildRoomButtons();
    refreshState().then(() => { if (roomPane === "chest") buildRoomButtons(); });
  }
  if ($("raceMsg")) $("raceMsg").scrollIntoView({block: "nearest"});      // a small laptop's panel can hide it
}

// ---- 🎨 Draw & guess: one friend draws a secret thing, the others tap the picture --------------
// The drawer clicks squares to colour them (or drags). Everyone sees the picture grow, here and
// on an easel in the Park. Guesses are pictures with words, so nobody has to type or spell.
let drawInk = 0, drawLast = -1;
const drawPending = new Map();         // squares the drawer coloured that the server hasn't sent back yet
function drawPane(g, you) {
  const drawing = g.drawer === you, word = g.word, got = g.guessed.includes(you);
  let body = `<h4>🎨 Draw & guess <small>· picture ${g.round + 1} of ${g.turns}</small></h4>`;
  if (g.pause) body += `<p class="race-msg good">It was ${word[1]} ${esc(word[2])}!</p>`;
  else if (drawing) body += `<p class="race-bonus">🤫 Draw this: <b>${word[1]} ${esc(word[2])}</b></p>`;
  else body += `<p class="me-note">${esc(gamePerson(g.drawer))} is drawing. What is it? Tap the picture!</p>`;
  // Guessers watch the big easel in the Park (the camera stays there), so their panel has room for every picture.
  if (drawing) body += `<canvas id="drawBoard" class="draw-board${g.pause ? "" : " mine"}" width="${g.grid * 16}" height="${g.grid * 16}" aria-label="Your drawing"></canvas>`;
  else if (!g.pause && !got) body += `<p class="me-note">👀 Watch the easel in the Park!</p>`;
  if (drawing && !g.pause) {
    body += `<div class="draw-inks">${g.colours.map((c, i) => `<button data-ink="${i}" aria-pressed="${drawInk === i}" style="background:${c}" title="Colour ${i + 1}"></button>`).join("")}
      <button data-ink="-1" aria-pressed="${drawInk === -1}" title="Rub out">🧽</button></div>
      <p class="me-note">Click squares to colour them. No letters! Your friends guess from pictures.</p>
      <button class="wide" data-drawwipe="1"><span>🗑</span>Start my picture again</button>`;
  } else if (!g.pause && got) body += `<p class="race-msg good">⭐ You got it! Wait for your friends.</p>`;
  else if (!g.pause) body += `<div class="guess-grid">${g.choices.map(([key, icon, name]) =>
    `<button data-guess="${key}"><span>${icon}</span>${esc(name)}</button>`).join("")}</div>`;
  const names = g.guessed.map(s => esc(gamePerson(s))).join(", ");
  body += `<p class="me-note race-score">Guessed it: ${names || "nobody yet"} · Your points: ${g.scores[you] || 0}<br>
    <small>First right guess: 3 points. Second: 2. Then 1. The drawer gets 1 for each friend who guesses.</small></p>`;
  return body;
}
function paintDrawBoard() {
  const cv = $("drawBoard"), g = currentGame();
  if (!cv || !g || g.kind !== "draw" || !g.board) return;
  const now = performance.now();
  for (const [cell, {ink, at}] of drawPending) if (g.board[cell] === ink || now - at > 2500) drawPending.delete(cell);
  const c = cv.getContext("2d"), size = cv.width / g.grid;
  c.fillStyle = "#fffdf6"; c.fillRect(0, 0, cv.width, cv.height);
  for (let i = 0; i < g.grid * g.grid; i++) {
    const ink = drawPending.has(i) ? drawPending.get(i).ink : g.board[i];
    if (ink === ".") continue;
    c.fillStyle = g.colours["0123456789".indexOf(ink)];
    c.fillRect(i % g.grid * size, Math.floor(i / g.grid) * size, size, size);
  }
  c.strokeStyle = "#1b153018"; c.lineWidth = 1;
  for (let k = 1; k < g.grid; k++) {
    c.beginPath(); c.moveTo(k * size + .5, 0); c.lineTo(k * size + .5, cv.height); c.stroke();
    c.beginPath(); c.moveTo(0, k * size + .5); c.lineTo(cv.width, k * size + .5); c.stroke();
  }
}
function drawAt(e) {
  const cv = e.target, g = currentGame();
  if (cv.id !== "drawBoard" || !g || g.kind !== "draw" || g.drawer !== roomInfo.you || g.pause) return;
  const r = cv.getBoundingClientRect();
  const x = Math.floor((e.clientX - r.left) / r.width * g.grid), y = Math.floor((e.clientY - r.top) / r.height * g.grid);
  if (x < 0 || y < 0 || x >= g.grid || y >= g.grid) return;
  const cell = y * g.grid + x, ink = drawInk < 0 ? "." : String(drawInk);
  if (cell === drawLast) return;
  drawLast = cell;
  drawPending.set(cell, {ink, at: performance.now()});
  paintDrawBoard();
  tap("game", {action: "paint", cell, colour: drawInk < 0 ? null : drawInk});
}
$("roomButtons").addEventListener("pointerdown", e => { drawLast = -1; drawAt(e); });
$("roomButtons").addEventListener("pointermove", e => { if (e.buttons) drawAt(e); });
async function drawGuess(button) {
  const grid = button.closest(".guess-grid");
  if (!grid || grid.classList.contains("wait")) return;
  PalStage.SFX.wake();
  const out = await tap("game", {action: "guess", word: button.dataset.guess});
  if (!out) { tipFor("Couldn't reach the game. Please try again."); return; }
  if (out.error) { tipFor(out.error); return; }
  tipFor(out.message);
  if (out.right) { PalStage.SFX.play("fanfare"); return; }
  PalStage.SFX.play("boing");
  button.classList.add("nope");
  grid.classList.add("wait");          // a moment to look again, so tapping every picture isn't the way to win
  setTimeout(() => grid.classList.remove("wait"), 3000);
}
