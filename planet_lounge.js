// The Rover Lounge on the student page: a room the teacher opens, where
// everyone's rovers hang out. Kids drive around, honk, dance, cheer for each
// other and take the stage. Writing a show in code is an extra they can pick,
// and nothing here needs it. The page's script calls into this; it uses the
// page's helpers (esc, get, post, toast, look, me, state, SFX) and planet_render.js.

// The room in squares: the same size as LOUNGE_COLS and friends in server.py.
// `box` is how far a show can roam on the stage: left, right, top, bottom.
const LOUNGE = {cols: 14, rows: 9, floor: 3, speed: 3.5, mid: [7, 1.5], box: [4.5, 9.5, .8, 2.3]};
const lounge = {rovers: new Map(), you: null, after: null, stage: null, queue: [], cheers: [], emotes: null,
                run: 0, timer: 0, last: 0, bg: null, cell: 0, card: null, moveTimer: 0, open: false,
                ball: null, kicked: 0, trophies: []};
const DANCE_FLOOR = {left: 3.4, top: 4.3, tile: .72, cols: 10, rows: 5};
const DISCO = ["#ff8ad8", "#8cf2c6", "#ffd36b", "#8fc8ff", "#b9a3ff", "#ff8a7a"];
const BALL = {size: .27, drag: 1.1, kick: 5, reach: .62, right: LOUNGE.cols - .3, top: LOUNGE.floor + .3, bottom: LOUNGE.rows - .3};
const showMaker = {play: null};
const SHOW_START = `# Your rover's show. Change it any way you like!
spin()
dance()
honk()
`;
const SHOW_EXAMPLES = [
  ["Spin and honk", `spin()\nhonk()\nspin()\nhonk()\n`],
  ["Across the stage", `for i in range(3):\n    east()\n    honk()\n    west()\n`],
  ["Big finish", `def twirl():\n    spin()\n    wave()\n\nfor i in range(2):\n    twirl()\n\ndance()\nhonk()\n`],
];
const SHOW_CHIPS = ["spin()", "dance()", "honk()", "wave()", "north()", "south()", "east()", "west()", "wait()"];
const SHOW_MOVES = {north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0]};

// ---- Drawing the room ---------------------------------------------------------------

function paintRoom(ctx, c) {
  const {cols, rows, floor} = LOUNGE, box = (x, y, w, h, r, fill) => { ctx.fillStyle = fill; roundRect(ctx, x * c, y * c, w * c, h * c, r * c); ctx.fill(); };
  // The back wall and a two-tone floor.
  const wall = ctx.createLinearGradient(0, 0, 0, floor * c);
  wall.addColorStop(0, "#14214a"); wall.addColorStop(1, "#1f1a4e");
  ctx.fillStyle = wall; ctx.fillRect(0, 0, cols * c, floor * c);
  for (let y = floor; y < rows; y++) for (let x = 0; x < cols; x++) {
    ctx.fillStyle = (x + y) % 2 ? "#253a63" : "#21345a";
    ctx.fillRect(x * c, y * c, c + 1, c + 1);
  }
  ctx.fillStyle = "#5af0e0"; ctx.fillRect(0, floor * c - c * .05, cols * c, c * .05);
  // The window on the left, looking out at space and a ringed planet.
  box(.2, .2, 2.3, 1.55, .12, "#5af0e0");
  box(.27, .27, 2.16, 1.41, .08, "#080a22");
  for (let i = 0; i < 26; i++) {
    ctx.fillStyle = i % 3 ? "#cfd8ff" : "#ffd36b";
    ctx.fillRect((.35 + hash(i, 3) * 2) * c, (.34 + hash(i, 7) * 1.26) * c, c * .03, c * .03);
  }
  ctx.fillStyle = "#ff8a7a"; ctx.beginPath(); ctx.arc(1.8 * c, 1 * c, c * .32, 0, 7); ctx.fill();
  ctx.strokeStyle = "#ffd36b"; ctx.lineWidth = c * .05; ctx.beginPath(); ctx.ellipse(1.8 * c, 1 * c, c * .52, c * .13, -.3, 0, 7); ctx.stroke();
  // The neon sign under the window.
  ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.font = `800 ${c * .3}px system-ui, sans-serif`;
  ctx.shadowColor = "#5af0e0"; ctx.shadowBlur = c * .35; ctx.fillStyle = "#c8fff6";
  ctx.fillText("ROVER", 1.35 * c, 2.08 * c); ctx.fillText("LOUNGE", 1.35 * c, 2.42 * c);
  ctx.shadowBlur = 0;
  // The stage, with curtains either side and footlights along the front.
  box(3.4, .2, 7.2, 2.65, .14, "#5af0e0");
  box(3.48, .25, 7.04, 2.52, .1, "#2e2a6b");
  ctx.fillStyle = "rgba(255,255,255,.05)";
  for (let y = 0; y < 5; y++) ctx.fillRect(3.48 * c, (.48 + y * .48) * c, 7.04 * c, c * .03);
  for (const left of [2.65, 10.55]) for (let i = 0; i < 4; i++) box(left + i * .2, 0, .24, 2.75, .1, i % 2 ? "#7a4fd8" : "#a884ff");
  for (let i = 0; i < 12; i++) {
    const x = (3.8 + i * .58) * c;
    ctx.fillStyle = i % 2 ? "#8cf2c6" : "#ffd36b";
    ctx.beginPath(); ctx.arc(x, 2.79 * c, c * .05, 0, 7); ctx.fill();
  }
  // The trophy shelf on the right: the trophies themselves go on in drawTrophies.
  ctx.fillStyle = "#ffd36b"; ctx.font = `800 ${c * .19}px system-ui, sans-serif`;
  ctx.fillText("CLASS TROPHIES", 12.6 * c, .34 * c);
  for (const y of [1.3, 2.3]) box(11.5, y, 2.25, .1, .04, "#a7643f");
  // The dance floor. It lights up in drawDanceFloor.
  const {left, top, tile, cols: wide, rows: tall} = DANCE_FLOOR;
  box(left - .1, top - .1, wide * tile + .2, tall * tile + .2, .1, "#ffd36b");
  for (let y = 0; y < tall; y++) for (let x = 0; x < wide; x++) box(left + x * tile, top + y * tile, tile, tile, 0, (x + y) % 2 ? "#332a6e" : "#2a2360");
  // Sofas along the bottom corners, with an alien plant at each end of the wall.
  for (const x of [.15, 11.35]) {
    box(x, 7.75, 2.5, 1.05, .22, "#1f9e92");
    box(x + .12, 8.3, 2.26, .42, .1, "#167a71");
    box(x + .2, 7.85, 1, .46, .12, "#5af0e0");
    box(x + 1.3, 7.85, 1, .46, .12, "#5af0e0");
  }
  for (const x of [.6, 13.4]) {
    box(x - .24, 3.5, .48, .36, .08, "#7a4fd8");
    for (const [dx, h, colour] of [[-.2, .42, "#ff8ad8"], [0, .56, "#ffd36b"], [.2, .42, "#ff8ad8"]]) {
      ctx.fillStyle = "#4fbf8b"; ctx.fillRect((x + dx - .025) * c, (3.52 - h) * c, c * .05, h * c);
      ctx.fillStyle = colour; ctx.beginPath(); ctx.arc((x + dx) * c, (3.5 - h) * c, c * .09, 0, 7); ctx.fill();
    }
  }
}
// The dance floor: a slow shimmer, with a bright tile under every rover on it.
function drawDanceFloor(ctx, cell, ts) {
  const {left, top, tile, cols, rows} = DANCE_FLOOR, lit = new Set();
  for (const r of lounge.rovers.values()) {
    const x = Math.floor((r.x - left) / tile), y = Math.floor((r.y - top) / tile);
    if (x >= 0 && x < cols && y >= 0 && y < rows) lit.add(y * cols + x);
  }
  for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
    const on = lit.has(y * cols + x), glow = on ? .75 : CALM ? 0 : .09 * (1 + Math.sin(ts / 700 + hash(x, y) * 9));
    if (!glow) continue;
    ctx.globalAlpha = glow;
    ctx.fillStyle = DISCO[(x + y * 2 + (CALM ? 0 : Math.floor(ts / 900))) % DISCO.length];
    ctx.fillRect((left + x * tile + .03) * cell, (top + y * tile + .03) * cell, (tile - .06) * cell, (tile - .06) * cell);
  }
  ctx.globalAlpha = 1;
}
// One trophy for each Team Mission level: dim until the class has finished it.
function drawTrophies(ctx, cell) {
  ctx.font = `${cell * .46}px system-ui, "Noto Color Emoji", sans-serif`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = "#fff";
  lounge.trophies.forEach((t, i) => {
    ctx.globalAlpha = t.won ? 1 : .16;
    ctx.fillText("🏆", (11.8 + (i % 4) * .55) * cell, (i < 4 ? .98 : 1.98) * cell);
  });
  ctx.globalAlpha = 1;
}
// Where the ball has rolled to, `secs` after the kick. Every page works it out
// the same way from the same kick, so everyone sees the same ball.
function ballRoll(ball, secs) {
  let {x, y, vx, vy} = ball;
  const step = 1 / 30, slow = Math.exp(-BALL.drag * step);
  for (let t = 0; t < Math.min(secs, 8); t += step) {
    vx *= slow; vy *= slow; x += vx * step; y += vy * step;
    if (x < .3 || x > BALL.right) { x = Math.max(.3, Math.min(BALL.right, x)); vx = -vx; }
    if (y < BALL.top || y > BALL.bottom) { y = Math.max(BALL.top, Math.min(BALL.bottom, y)); vy = -vy; }
  }
  return {x, y, vx, vy};
}
function drawBall(ctx, spot, cell) {
  const x = spot.x * cell, y = spot.y * cell, size = BALL.size * cell;
  ctx.fillStyle = "rgba(8,6,20,.35)"; ctx.beginPath(); ctx.ellipse(x, y + size * .9, size, size * .35, 0, 0, 7); ctx.fill();
  ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(x, y, size, 0, 7); ctx.fill();
  DISCO.slice(0, 3).forEach((colour, i) => {
    ctx.fillStyle = colour; ctx.beginPath(); ctx.moveTo(x, y);
    ctx.arc(x, y, size, (spot.x + spot.y) * 2 + i * 2.09, (spot.x + spot.y) * 2 + i * 2.09 + 1.05); ctx.fill();
  });
}
// Your own rover bumping the ball sends it off. Each page only watches its own
// rover, and the room hears about the kick.
function ballBump(ball, now) {
  const r = lounge.rovers.get(lounge.you);
  if (!r || now - lounge.kicked < 350) return;
  const dx = ball.x - r.x, dy = ball.y - r.y, far = Math.hypot(dx, dy) || .01;
  if (far > BALL.reach) return;
  lounge.kicked = now;
  const kick = {x: ball.x, y: ball.y, vx: dx / far * BALL.kick, vy: dy / far * BALL.kick};
  lounge.ball = {...kick, n: lounge.ball.n, start: now};
  loungeDo("kick", kick);
}
// What a trick does to a rover, u from 0 to 1. Same shape as dance() in planet_render.js.
function trickPose(word, u, kind) {
  if (CALM) return {};
  if (word === "dance") return dance(kind, u);
  if (word === "spin") return {angle: u * Math.PI * 2};
  if (word === "wave") return {angle: Math.sin(u * Math.PI * 6) * .35};
  if (word === "honk") return {lift: Math.sin(u * Math.PI) * .22};
  if (word === "jump") return {lift: Math.abs(Math.sin(u * Math.PI * 2)) * .9};
  return {};
}
// Where a show has got to, t seconds in: rolling on, each step, rolling off.
// `step` goes up by one each time a new trick starts.
function stagePose(steps, roll, t, home) {
  const [left, right, top, bottom] = LOUNGE.box, mix = (a, b, u) => [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u];
  let at = LOUNGE.mid, time = roll;
  if (t < roll) return {spot: mix(home, at, t / roll), step: -1};
  for (let i = 0; i < steps.length; i++) {
    const [word, secs] = steps[i], go = SHOW_MOVES[word] || [0, 0];
    const next = [Math.max(left, Math.min(right, at[0] + go[0])), Math.max(top, Math.min(bottom, at[1] + go[1]))];
    if (t < time + secs) {
      const u = (t - time) / secs;
      return {spot: mix(at, next, u), step: i, word, u, face: go[0] || go[1] ? Math.atan2(go[1], go[0]) : null};
    }
    at = next; time += secs;
  }
  return {spot: mix(at, home, Math.min(1, (t - time) / roll)), step: steps.length};
}
function drawTrickRover(ctx, gear, x, y, size, cell, angle, pose, now) {
  const t = CALM ? 0 : now, lift = pose.lift || 0, px = x + (pose.dx || 0) * cell, py = y + (pose.dy || 0) * cell - lift * cell * .6;
  if (lift) {
    ctx.fillStyle = "rgba(10,6,24,.35)"; ctx.beginPath();
    ctx.ellipse(x, y + cell * .3, cell * .4, cell * .14, 0, 0, 7); ctx.fill();
  }
  if (pose.ring) discoRing(ctx, px, py, cell, pose.ring, t);
  ctx.save(); ctx.translate(px, py); ctx.scale(pose.sx == null ? 1 : pose.sx || .02, 1);
  drawRover(ctx, 0, 0, size * (1 + lift * .25), angle + (pose.angle || 0), pose.alpha == null ? 1 : pose.alpha, gear, t);
  ctx.restore();
  danceFx(ctx, px, py, cell, pose);
  if (PETS[gear.pet]) drawPet(ctx, x + size * .5, y - size * .5, size * 1.15, gear.pet, t);
}
function drawBubbles(ctx, r, x, y, cell, now) {
  r.bubbles = r.bubbles.filter(b => now - b.at < 1800);
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  for (const b of r.bubbles) {
    const p = (now - b.at) / 1800;
    ctx.globalAlpha = 1 - p * p;
    ctx.font = `${cell * .55}px system-ui, "Noto Color Emoji", sans-serif`;
    ctx.fillText(b.text, x, y - cell * (.75 + p * .9));
  }
  ctx.globalAlpha = 1;
}
function drawTag(ctx, text, x, y, cell, mine) {
  ctx.font = `700 ${Math.max(11, cell * .21)}px system-ui, sans-serif`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const w = ctx.measureText(text).width + cell * .3, h = Math.max(16, cell * .3);
  ctx.fillStyle = mine ? "rgba(140,242,198,.92)" : "rgba(18,15,36,.78)";
  roundRect(ctx, x - w / 2, y - h / 2, w, h, h / 2); ctx.fill();
  ctx.fillStyle = mine ? "#10291f" : "#f4eee2";
  ctx.fillText(text, x, y + 1);
}
// A rover's moves on the floor, one frame's worth, and where it is now.
function roverFrame(r, dt, now) {
  const dx = r.tx - r.x, dy = r.ty - r.y, far = Math.hypot(dx, dy), go = CALM ? far : LOUNGE.speed * dt;
  if (far > .01) {
    r.x += dx * Math.min(1, go / far); r.y += dy * Math.min(1, go / far);
    r.angle = Math.atan2(dy, dx);
  }
  if (r.act && now - r.act.at > r.act.secs * 1000) r.act = null;
}
function drawLounge(ts) {
  const cv = $("loungeRoom"), dpr = devicePixelRatio || 1, w = cv.clientWidth, h = w * LOUNGE.rows / LOUNGE.cols;
  if (!w) return;
  const cell = w / LOUNGE.cols, dt = Math.min(.1, (ts - (lounge.last || ts)) / 1000);
  lounge.last = ts;
  if (cv.width !== Math.round(w * dpr)) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    lounge.bg = document.createElement("canvas");
    lounge.bg.width = cv.width; lounge.bg.height = cv.height;
    paintRoom(lounge.bg.getContext("2d"), cell * dpr);
  }
  const ctx = cv.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(lounge.bg, 0, 0);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  drawDanceFloor(ctx, cell, ts);
  drawTrophies(ctx, cell);
  if (lounge.ball) {
    const spot = ballRoll(lounge.ball, (ts - lounge.ball.start) / 1000);
    drawBall(ctx, spot, cell);
    ballBump(spot, ts);
  }
  const stage = lounge.stage, star = stage && lounge.rovers.get(stage.seat);
  if (star) { ctx.fillStyle = "rgba(8,5,20,.4)"; ctx.fillRect(0, 0, w, h); }
  const order = [...lounge.rovers.values()].sort((a, b) => a.y - b.y);
  for (const r of order) {
    roverFrame(r, dt, ts);
    let x = r.x, y = r.y, angle = r.angle, pose = r.act ? trickPose(r.act.word, (ts - r.act.at) / (r.act.secs * 1000), r.row.look.dance) : {}, size = cell;
    if (r === star) {
      const p = stagePose(stage.steps, stage.roll, (ts - stage.start) / 1000, [r.x, r.y]);
      [x, y] = p.spot; size = cell * (1 + .3 * Math.min(1, (LOUNGE.floor + 1 - y) / 2));
      pose = p.word ? trickPose(p.word, p.u, r.row.look.dance) : {};
      if (p.face != null) stage.face = p.face;
      if (stage.face != null) angle = stage.face;
      if (p.step > stage.played) { stage.played = p.step; stepStarted(r, p.word); }
      const glow = ctx.createRadialGradient(x * cell, y * cell, 0, x * cell, y * cell, cell * 1.7);
      glow.addColorStop(0, "rgba(255,240,190,.5)"); glow.addColorStop(1, "rgba(255,240,190,0)");
      ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(x * cell, y * cell, cell * 1.7, 0, 7); ctx.fill();
    }
    drawTrickRover(ctx, r.row.look, x * cell, y * cell, size, cell, angle, pose, ts);
    r.at = [x, y];
  }
  for (const r of order) {
    drawTag(ctx, r.row.tag, r.at[0] * cell, (r.at[1] + .62) * cell, cell, r.seat === lounge.you);
    drawBubbles(ctx, r, r.at[0] * cell, r.at[1] * cell, cell, ts);
  }
}
function loungeLoop(ts) {
  if ($("lounge").hidden) return;
  drawLounge(ts);
  requestAnimationFrame(loungeLoop);
}
// A show's trick begins: a bubble for everyone, and only the rover's own kid hears the horn.
function stepStarted(r, word) {
  if (word === "honk") { r.bubbles.push({text: "📯", at: performance.now()}); if (r.seat === lounge.you) SFX.play(look.horn || "beep"); }
  if (word === "wave") r.bubbles.push({text: "👋", at: performance.now()});
}

// ---- Keeping up with the room ---------------------------------------------------------

function loungeEvent(e) {
  const r = lounge.rovers.get(e.kind === "cheer" ? e.to : e.seat), at = performance.now();
  if (!r) return;
  if (e.kind === "emote") { r.bubbles.push({text: e.emote, at}); return; }
  if (e.kind === "cheer") {
    r.bubbles.push({text: e.cheer, at});
    if (e.to === lounge.you) toast(e.cheer, `${e.tag} cheered for your rover!`, "Everyone in the lounge saw it.");
    return;
  }
  r.act = {word: e.kind, at, secs: e.kind === "dance" ? 1.6 : 1};
  stepStarted(r, e.kind);
}
function loungeSay() {
  const place = lounge.queue.indexOf(lounge.you), s = lounge.stage;
  const mine = s && s.seat === lounge.you, waiting = place >= 0;
  $("loungeSay").textContent = mine ? "🎤 You're on stage!"
    : waiting && place === 0 ? `🎤 ${s ? `${s.tag} is on stage. ` : ""}You're next!`
    : waiting ? `🎤 ${place + 1} rovers to go before you. You're in the queue.`
    : s ? `🎤 Now on stage: ${s.tag}`
    : "Click the floor to drive. Bump the ball! Click a rover to see it up close.";
  $("loungeStage").disabled = mine || waiting;
}
// The emote buttons and the line about the class's trophies.
function loungePanel(out) {
  if (!lounge.emotes) {
    lounge.emotes = out.emotes;
    $("loungeEmotes").innerHTML = out.emotes.map(e => `<button data-emote="${esc(e)}" aria-label="Show ${esc(e)} over your rover">${esc(e)}</button>`).join("");
  }
  const won = out.trophies.filter(t => t.won).length;
  const timed = out.trophies.filter(t => t.best).sort((a, b) => a.best - b.best)[0];
  const quickest = timed ? ` Your quickest: ${timed.name} in ${Math.floor(timed.best / 60)}:${String(timed.best % 60).padStart(2, "0")}.` : "";
  $("loungeWins").textContent = won ? `🏆 Your class has won ${won} of ${out.trophies.length} Team Mission trophies together!${quickest}`
    : `🏆 Finish a Team Mission level together to win a trophy for the shelf.`;
}
function loungeTake(out) {
  if (out.error === "join") { localStorage.removeItem("mazeId"); location.reload(); return; }
  if (out.open === false) { loungeSet(false); closeLounge(true); return; }
  if (out.open !== true || $("lounge").hidden) return;
  lounge.you = out.you; lounge.queue = out.queue; lounge.cheers = out.cheers; lounge.trophies = out.trophies;
  if (!lounge.ball || lounge.ball.n < out.ball.n) lounge.ball = {...out.ball, start: performance.now() - out.ball.ago * 1000};
  loungePanel(out);
  const here = new Set();
  for (const row of out.rovers) {
    here.add(row.seat);
    const r = lounge.rovers.get(row.seat);
    if (!r) lounge.rovers.set(row.seat, {seat: row.seat, row, x: row.x, y: row.y, tx: row.x, ty: row.y, angle: Math.PI / 2, act: null, bubbles: [], at: [row.x, row.y]});
    else {
      r.row = row;
      if (row.seat !== lounge.you) { r.tx = row.x; r.ty = row.y; }   // your own rover goes where you just clicked
    }
  }
  for (const seat of lounge.rovers.keys()) if (!here.has(seat)) lounge.rovers.delete(seat);
  if (lounge.card != null && !here.has(lounge.card)) closeRoverCard();
  // Only what's new: a poll and a press can bring the same moment twice.
  if (lounge.after != null) for (const e of out.events) if (e.n > lounge.after) loungeEvent(e);
  lounge.after = Math.max(lounge.after || 0, out.seq);
  if (!out.stage) lounge.stage = null;
  else if (!lounge.stage || lounge.stage.n !== out.stage.n)
    lounge.stage = {...out.stage, start: performance.now() - out.stage.ago * 1000, played: -1, face: null};
  loungeSay();
}
async function loungePoll() {
  clearTimeout(lounge.timer);
  const run = lounge.run;
  const out = await get(`/planet/lounge?id=${encodeURIComponent(me)}${lounge.after == null ? "" : `&after=${lounge.after}`}`).catch(() => null);
  if (run !== lounge.run || $("lounge").hidden) return;
  if (out) loungeTake(out);
  if (!$("lounge").hidden) lounge.timer = setTimeout(loungePoll, 400);
}
async function loungeDo(what, extra) {
  SFX.wake();
  const out = await post("/planet/lounge", {id: me, do: what, after: lounge.after, ...extra}).catch(() => null);
  if (out) loungeTake(out);
}

// ---- Coming and going --------------------------------------------------------------

// The teacher opened or closed the lounge. `tell` says so on a change.
function loungeSet(on, tell) {
  if (on === lounge.open) return;
  lounge.open = on;
  $("loungeButton").hidden = !on;
  if (on && tell) toast("🛋", "The Rover Lounge is open!", "Press 🛋 Lounge at the top of the page to bring your rover in.");
}
function openLounge() {
  clearToasts();
  lounge.run++;
  lounge.rovers.clear();
  Object.assign(lounge, {you: null, after: null, stage: null, queue: [], card: null, last: 0, ball: null});
  $("loungeSay").textContent = "Your rover is rolling in…";
  $("lounge").hidden = false;
  closeRoverCard();
  loungePoll();
  requestAnimationFrame(loungeLoop);
  $("loungeClose").focus();
}
function closeLounge(byTeacher) {
  if ($("lounge").hidden) return;
  lounge.run++;
  clearTimeout(lounge.timer);
  $("lounge").hidden = true;
  $("showMaker").hidden = true;
  if (byTeacher) toast("🛋", "The lounge is closed for now", "You're back on your level, and your code is just as you left it.");
}
// Escape closes the show maker, then the lounge. True if it did something.
function loungeEscape() {
  if (!$("showMaker").hidden) { closeShowMaker(); return true; }
  if ($("lounge").hidden) return false;
  if (lounge.card != null) closeRoverCard(); else closeLounge();
  return true;
}

// ---- Driving and the rover card ---------------------------------------------------------

// Your rover sets off at once. The room hears about it a moment later,
// however fast the keys go.
function driveTo(x, y) {
  const r = lounge.rovers.get(lounge.you);
  if (!r) return;
  r.tx = Math.max(.5, Math.min(LOUNGE.cols - .5, x));
  r.ty = Math.max(LOUNGE.floor, Math.min(LOUNGE.rows - .5, y));
  if (lounge.moveTimer) return;
  lounge.moveTimer = setTimeout(() => { lounge.moveTimer = 0; loungeDo("move", {x: r.tx, y: r.ty}); }, 150);
}
function roomClick(e) {
  const cv = $("loungeRoom"), box = cv.getBoundingClientRect(), cell = box.width / LOUNGE.cols;
  const x = (e.clientX - box.left) / cell, y = (e.clientY - box.top) / cell;
  const near = [...lounge.rovers.values()].map(r => ({r, far: Math.hypot(r.at[0] - x, r.at[1] - y)})).sort((a, b) => a.far - b.far)[0];
  if (near && near.far < .6) openRoverCard(near.r);
  else { closeRoverCard(); driveTo(x, y); }
}
function loungeKey(e) {
  const ways = {ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0]}, go = ways[e.key];
  const r = lounge.rovers.get(lounge.you);
  if (!go || !r || $("lounge").hidden || !$("showMaker").hidden) return;
  e.preventDefault(); e.stopPropagation();   // not the scouting keys behind the room
  driveTo(r.tx + go[0], r.ty + go[1]);
}
function openRoverCard(r) {
  const {row} = r, mine = r.seat === lounge.you, box = $("loungeRover"), tier = row.best && row.best.rarity !== "common" ? ` (${RARITY_NAMES[row.best.rarity]})` : "";
  lounge.card = r.seat;
  box.innerHTML = `<button class="quiet round lc-close" aria-label="Close this card">✕</button><canvas width="132" height="132"></canvas><b>${esc(row.tag)}</b>`
    + (row.best ? `<span>✨ Wearing ${esc(row.best.name)}${esc(tier)}</span>` : "")
    + (row.pet ? `<span>🐾 ${esc(row.pet)}</span>` : "")
    + (row.badge ? `<span>${esc(row.badge.icon)} ${esc(row.badge.name)}</span>` : "")
    + (mine ? `<small>That's your rover!</small>` : `<small>Send a cheer:</small><div class="lc-cheers">${lounge.cheers.map(c => `<button data-cheer="${esc(c)}" aria-label="Cheer ${esc(c)}">${esc(c)}</button>`).join("")}</div>`);
  const g = box.querySelector("canvas").getContext("2d");
  drawRover(g, 62, 72, 104, -Math.PI / 2 + .35, 1, row.look, 0);
  if (PETS[row.look.pet]) drawPet(g, 104, 38, 72, row.look.pet, 0);
  box.hidden = false;
}
function closeRoverCard() { lounge.card = null; $("loungeRover").hidden = true; }

// ---- 🎬 Make your own show: an extra, for anyone who wants it -------------------------

function showSay(text, kind = "") {
  $("showMsg").className = "shop-msg" + (kind ? " " + kind : "");
  $("showMsg").innerHTML = text;
}
function openShowMaker() {
  $("showMaker").hidden = false;
  if (!$("showCode").value) $("showCode").value = state.show_code || SHOW_START;
  $("showExamples").innerHTML = `<span>Try:</span>` + SHOW_EXAMPLES.map(([name], k) => `<button data-k="${k}">${name}</button>`).join("");
  $("showWords").innerHTML = SHOW_CHIPS.map(w => `<button data-word="${w}">${w}</button>`).join("");
  showSay("Press <b>▶ Try it</b> to watch your rover do it. Only you can see this.");
  $("showCode").focus();
  requestAnimationFrame(makerLoop);
}
function closeShowMaker() { $("showMaker").hidden = true; showMaker.play = null; }
function showKey(e) {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); showTry(); return; }
  shopKey(e);
}
async function showSend(what) {
  const code = $("showCode").value;
  const out = await post("/planet/lounge", {id: me, do: what, code}).catch(() => null);
  if (!out) { showSay("No answer from mission control. Try again.", "err"); return null; }
  if (out.open === false) { loungeTake(out); return null; }
  state.show_code = code;
  if (out.error) { showSay(esc(out.error), "err"); SFX.play("error"); return null; }
  return out;
}
async function showTry() {
  SFX.wake();
  const out = await showSend("try_show");
  if (!out) return;
  showMaker.play = {steps: out.steps, start: performance.now(), played: -1, face: null, bubbles: []};
  showSay(!out.steps.length ? `Your show doesn't do anything yet. Press a word below, or try a line like <code>spin()</code>.`
    : out.cut ? `That's longer than one turn on the stage, so your show stops after ${out.steps.length} moves. Like it? Press <b>💾 Keep this show</b>.`
    : `🎬 Watch your rover! Like it? Press <b>💾 Keep this show</b>.`);
}
async function showKeep() {
  SFX.wake();
  const out = await showSend("keep_show");
  if (!out) return;
  state.has_show = true;
  SFX.play("gift");
  showSay("✓ Kept! Press <b>← Lounge</b>, then <b>🎤 Take the stage</b>, and your rover will do this show.", "ok");
}
// The stage on its own, with just your rover, for trying a show.
function drawMaker(ts) {
  const cv = $("showStage"), dpr = devicePixelRatio || 1, w = cv.clientWidth, h = w * .45, cell = w / 8;
  if (!w) return;
  if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
  ctx.save(); ctx.translate(-3 * cell, 0); paintRoom(ctx, cell);
  const play = showMaker.play, roll = .3;
  let [x, y] = LOUNGE.mid, pose = {}, angle = Math.PI / 2;
  if (play) {
    const p = stagePose(play.steps, roll, (ts - play.start) / 1000, LOUNGE.mid);
    [x, y] = p.spot;
    pose = p.word ? trickPose(p.word, p.u, look.dance) : {};
    if (p.face != null) play.face = p.face;
    if (play.face != null) angle = play.face;
    if (p.step > play.played) {
      play.played = p.step;
      stepStarted({seat: lounge.you, bubbles: play.bubbles}, p.word);
    }
  }
  drawTrickRover(ctx, look, x * cell, y * cell, cell * 1.1, cell, angle, pose, ts);
  if (play) drawBubbles(ctx, play, x * cell, y * cell, cell, ts);
  ctx.restore();
}
function makerLoop(ts) {
  if ($("showMaker").hidden) return;
  drawMaker(ts);
  requestAnimationFrame(makerLoop);
}

// ---- Wiring, called once by the page ------------------------------------------------

function loungeWire() {
  $("loungeButton").addEventListener("click", openLounge);
  $("loungeClose").addEventListener("click", () => closeLounge());
  $("loungeRoom").addEventListener("click", roomClick);
  $("loungeHonk").addEventListener("click", () => loungeDo("honk"));
  $("loungeDance").addEventListener("click", () => loungeDo("dance"));
  $("loungeWave").addEventListener("click", () => loungeDo("wave"));
  $("loungeSpin").addEventListener("click", () => loungeDo("spin"));
  $("loungeJump").addEventListener("click", () => loungeDo("jump"));
  $("loungeEmotes").addEventListener("click", e => {
    const b = e.target.closest("[data-emote]");
    if (b) loungeDo("emote", {emote: b.dataset.emote});
  });
  $("loungeStage").addEventListener("click", () => loungeDo("stage"));
  $("loungeShow").addEventListener("click", openShowMaker);
  $("loungeRover").addEventListener("click", e => {
    if (e.target.closest(".lc-close")) closeRoverCard();
    const cheer = e.target.closest("[data-cheer]");
    if (cheer) { loungeDo("cheer", {to: lounge.card, cheer: cheer.dataset.cheer}); closeRoverCard(); }
  });
  window.addEventListener("keydown", loungeKey, true);
  $("showBack").addEventListener("click", closeShowMaker);
  $("showTry").addEventListener("click", showTry);
  $("showKeep").addEventListener("click", showKeep);
  $("showCode").addEventListener("keydown", showKey);
  $("showExamples").addEventListener("click", e => {
    const b = e.target.closest("[data-k]");
    if (b) { $("showCode").value = SHOW_EXAMPLES[b.dataset.k][1]; showTry(); }
  });
  $("showWords").addEventListener("click", e => {
    const b = e.target.closest("[data-word]");
    if (!b) return;
    const t = $("showCode");
    t.focus();
    t.setSelectionRange(t.value.length, t.value.length);
    document.execCommand("insertText", false, (t.value && !t.value.endsWith("\n") ? "\n" : "") + b.dataset.word + "\n");
  });
}
