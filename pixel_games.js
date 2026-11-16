// Shared playground rounds: opt in, then walk with the same controls as Hang out.
"use strict";
let gamePendingCover = null, gameBusy = false, gamePaintKey = "", gameRewardSeen = "";
let gameClock = {server: 0, local: 0};
const gameNow = () => gameClock.server + (performance.now() - gameClock.local) / 1000;
const currentGame = () => roomInfo && roomInfo.game;
const inRound = () => { const g = currentGame(); return g && g.joined.includes(roomInfo.you) && ["hiding", "playing"].includes(g.phase); };
const GAME_NAMES = {hide: "Hide & seek", tag: "Tag", race: "Red light, green light", dance: "Copy the dance", code: "💻 Code race"};
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
    box.innerHTML = jobsHtml() + `<p class="me-note">Invite the other kids! Anyone can start a game. Friends choose whether to join.</p>
      <button class="wide race-start" data-game="create" data-kind="code"><b>💻 Code race</b><small>Everyone codes the same job · solve it and your pal does it for everyone</small></button>
      <button data-game="create" data-kind="hide"><b>Hide & seek</b><small>Random seeker · 20 seconds to hide</small></button>
      <button data-game="create" data-kind="tag"><b>Tag</b><small>Chase your friends · pass “it”</small></button>
      <button data-game="create" data-kind="race"><b>Red light, green light</b><small>Race to the flag · freeze on red</small></button>
      <button data-game="create" data-kind="dance"><b>Copy the dance</b><small>Tap the moves in order · 3 rounds</small></button>
      <p class="me-note">Finish a round for 🪙 coins, 2 class-party points and a badge. Winners get extra coins. Your first round of each game earns a gift; then every third round earns another while gifts remain.</p>`;
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
    body += `<p class="me-note">Another round will be available in a moment.</p>`;
  } else if (!joined && g.kind === "code") {
    body += `<p class="me-note">Your friends are coding! Join in now: everyone gets the same job.</p><button class="wide race-run" data-game="join">💻 Join the Code race</button>`;
  } else if (!joined) {
    body += `<p class="me-note">A round is underway. You can join the next one, or keep hanging out.</p>`;
  } else if (g.kind === "code") {
    body = racePane(g, you);
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
  } else if (g.kind === "tag") {
    body += `<p class="me-note">${g.it === you ? "You're IT! Get close to another player to tag them." : esc(gamePerson(g.it)) + " is IT! Keep moving!"} Play in the Park and Wedding garden. No teleporting. After a tag, everyone gets 3 seconds to scatter.</p>`;
    body += `<p class="me-note">Your tags: ${g.tags[you] || 0}. Click to run, or use the arrow keys.</p>`;
  } else if (g.phase === "hiding" && g.it === you) {
    body += `<p class="me-note">You're the seeker! Count while everyone hides. Their pals and names are hidden from you. When the countdown ends, walk up to cover and search it.</p>`;
  } else if (g.found.includes(you)) {
    body += `<p class="me-note">You were found! Cheer on your friends while the seeker finishes. Stay for your reward.</p>`;
  } else if (g.it !== you && g.phase === "playing") {
    body += `<p class="me-note">${g.hiding ? "You're tucked away. Stay quiet!" : "You didn't reach cover in time. Stay still and hope the seeker misses you!"} ${esc(gamePerson(g.it))} is searching.</p>`;
  } else {
    const searching = g.it === you;
    body += `<p class="me-note">${searching ? "Choose a hiding place to walk over and search. You must get close!" : g.hiding ? "You're hidden! Choose another spot to move before time runs out." : "Choose cover below, or tap it on the map. Walk there and tuck away!"}</p>`;
    body += (roomInfo.cover || []).map(c => `<button data-cover="${c.key}" aria-pressed="${g.hiding === c.key}">${esc(c.name)}<small>${c.x < 320 ? "Park" : "Wedding garden"}</small></button>`).join("");
  }
  if (joined && g.phase !== "results") body += `<button data-game="leave">Leave game</button>`;
  const typing = document.activeElement?.id === "raceCode" && [$("raceCode").selectionStart, $("raceCode").selectionEnd];
  box.innerHTML = body;
  if (typing && $("raceCode")) { $("raceCode").focus(); $("raceCode").setSelectionRange(...typing); }
}
function paintGameState(data) {
  const g = data.game, status = $("gameStatus"), open = data.open;
  gameClock = {server: g?.now || Date.now() / 1000, local: performance.now()};
  status.hidden = !open;
  const key = JSON.stringify([g?.id, g?.phase, g?.joined, g?.it, g?.found, g?.hiding, g?.tags, g?.message, g?.reward, data.you,
                              g?.light, g?.done, g?.seq, g?.step, g?.round,
                              g?.solved, g?.bonus, g?.pause, g?.reveal, g?.score, g?.job?.job]);
  if (key !== gamePaintKey) {
    gamePaintKey = key;
    if (roomPane === "games") buildRoomButtons();
    gamePendingCover = null;
  }
  // A Code race needs room for the code, and every pal in view: the camera stays on the Park.
  const racing = g?.kind === "code" && g.phase === "playing" && g.joined.includes(data.you);
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
  paintGameClock();
}
function paintGameClock() {
  if (!roomInfo || $("hangView").hidden) return;
  const g = currentGame(), title = $("gameTitle"), detail = $("gameDetail");
  if (!g) {
    title.textContent = "Play with friends";
    detail.textContent = jobsWord() + "💻 Code race, tag, hide & seek, a race or a dance →";
    return;
  }
  const seconds = Math.max(0, Math.ceil(g.until - gameNow()));
  const job = g.kind === "code" && g.phase === "playing" && !g.pause && g.job;
  title.textContent = job ? `💻 ${job.job}` : gameName(g);
  const joined = g.joined.includes(roomInfo.you);
  detail.textContent = g.phase === "lobby" ? `${g.joined.length} joined · starts in ${seconds}s · ${joined ? "You're in!" : "Join in Games"}`
    : g.phase === "results" ? `Round over · next game in ${seconds}s`
    : g.kind === "race" ? `${seconds}s left · ${g.light === "red" ? "🔴 Red light: freeze!" : "🟢 Green light: run!"} · ${g.done.length} at the flag`
    : g.kind === "dance" ? `Round ${g.round + 1} of 3 · ${seconds}s left · ${g.step} of ${g.seq.length} moves`
    : g.kind === "code" ? (g.pause ? `Next job in ${seconds}s` : `${g.job.icons} · Job ${g.round + 1} of ${g.rounds} · ${seconds}s · ${g.solved.length} of ${g.joined.length} solved`)
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
$("gameStatus").addEventListener("click", () => { roomPane = "games"; artArmed = null; buildRoomButtons(); });
$("roomButtons").addEventListener("click", e => {
  const action = e.target.closest("[data-game]"), cover = e.target.closest("[data-cover]");
  const step = e.target.closest("[data-step]"), run = e.target.closest("[data-run]"), mine = myMember();
  if (step && !step.disabled) { PalStage.SFX.wake(); gameBusy = false; gameDo("step", {name: step.dataset.step}); }
  else if (run && !run.disabled && mine) walkTo(mine.x + 30, mine.y);
  else if (action) gameDo(action.dataset.game, {kind: action.dataset.kind});
  else if (cover) chooseGameCover(cover.dataset.cover);
  else if (e.target.closest("[data-put]")) raceAdd(e.target.closest("[data-put]").dataset.put);
  else if (e.target.closest("[data-race]")) raceButton(e.target.closest("[data-race]").dataset.race);
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
function raceEditor(job, help) {
  const chips = ["for i in range(3):", ...RACE_CHIPS, ...job.chips];
  return `<textarea id="raceCode" spellcheck="false" autocapitalize="off" autocomplete="off" aria-label="Your code"
      placeholder="Tap the green commands, or type here">${esc(raceCode)}</textarea>
    <div class="race-chips">${chips.map(c => `<button data-put="${esc(c)}"${c.startsWith("for") ? ' class="loop"' : ""}>${c.startsWith("for") ? "🔁 " : ""}${esc(c)}</button>`).join("")}</div>
    <button class="wide race-run" data-race="run">▶ Run my code</button>
    <div class="race-row"><button data-race="undo">⌫ Undo line</button><button data-race="out">⇤ Out of loop</button>
      ${help ? `<button data-race="help">💡 ${raceHelp ? "More help" : "Help"}</button>` : ""}</div>
    <p class="race-msg${raceGood ? " good" : ""}" id="raceMsg" role="status">${esc(raceMsg)}</p>`;
}
function raceHelpText(g) {
  if (!raceHelp) return "";
  const loops = g.job.loops, answerIn = Math.ceil(g.round_at + g.answer_after - gameNow());
  const tip = loops === 2 ? "Use two 🔁 for lines. Tap ⇤ Out of loop before the second one, so it isn't inside the first."
    : loops ? "Tap 🔁 for and type how many times. The moves pushed in under it happen again and again. For a move that happens once, after the loop, tap ⇤ Out of loop first."
    : `One line for each move, top to bottom: ${g.job.icons}`;
  const answer = raceHelp > 1 && answerIn <= 0 ? `<pre class="race-reveal">${esc(g.job.hint)}</pre>`
    : raceHelp > 1 ? `<p class="me-note">The whole answer shows in ${answerIn}s. Try first!</p>` : "";
  return `<p class="me-note">💡 ${tip}</p>${answer}`;
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
  if (el) { el.textContent = text; el.classList.toggle("good", good); }
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
