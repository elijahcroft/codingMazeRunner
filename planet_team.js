// The Team Mission: the whole class on one map, live. The student page and the
// class screen (planet_team_watch.html) both draw it from here. It needs
// planet_render.js and planet_lounge.js for rovers and name tags, plus the
// page's $, get and CALM; the student page adds post, toast, SFX, me and look.
// The rules are in planet_team.py.

const TEAM_COLOURS = {A: "#ff8a7a", B: "#8fc8ff", C: "#8cf2c6", D: "#ffd36b", E: "#ff8ad8", F: "#b9a3ff", G: "#ffb547", V: "#f4eee2"};
const TEAM_WAYS = {north: [-1, 0], south: [1, 0], east: [0, 1], west: [0, -1]};
const TEAM_KEYS = {ArrowUp: "north", ArrowDown: "south", ArrowLeft: "west", ArrowRight: "east"};
const TEAM_ROWS = 15, TEAM_COLS = 30;
const TEAM_STEP_MS = 130;       // a rover's pace, a step at a time
const TEAM_HOLD_MS = 220;       // a key held this long keeps driving, so a tap is one square
const TEAM_ROVER_SPEED = 9;     // squares a second on screen
const TEAM_CODE_WAIT_MS = 400;  // how long wait() holds a rover
const TEAM_EXAMPLES = {repeat: 'for i in range(3):\n    east()\n', rock: 'while look("east") != "rock":\n    east()\n',
                       check: 'if look("south") == "boulder":\n    south()\n'};
const team = {open: false, watching: false, map: null, you: null, view: null, seq: null, roster: null, level: null,
              people: new Map(), rovers: new Map(), boulders: [], pops: [], run: 0, timer: 0, last: 0,
              bg: null, held: null, heldAt: 0, path: [], bubbles: [], heard: 0, wonAt: 0, auto: null};

// ---- Drawing the map ------------------------------------------------------------------

const teamSquare = (r, c) => (team.map[r] || "#")[c] || "#";
const teamSame = (list, r, c) => list.some(s => s[0] === r && s[1] === c);
const teamIsDoor = ch => ch in TEAM_COLOURS;
const teamIsPlate = ch => ch !== ch.toUpperCase() && ch.toUpperCase() in TEAM_COLOURS;

function teamPaintGround(g, cell) {
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    const ch = teamSquare(r, c), x = c * cell, y = r * cell;
    g.fillStyle = ch === "#" ? "#1d1736" : ch === "*" ? ((r + c) % 2 ? "#7a6430" : "#6d5828") : (r + c) % 2 ? "#4f4386" : "#483d7c";
    g.fillRect(x, y, cell + .5, cell + .5);
    if (ch === "#" && teamSquare(r + 1, c) !== "#") {   // rock: lit along the edge you can see
      g.fillStyle = "rgba(185,163,255,.2)"; g.fillRect(x, y + cell * .84, cell, cell * .16);
    } else if (ch === "S") {
      g.fillStyle = "rgba(140,242,198,.16)"; g.fillRect(x + 1, y + 1, cell - 2, cell - 2);
    } else if (ch === "%") {
      g.fillStyle = "rgba(140,242,198,.3)"; g.fillRect(x + 2, y + 2, cell - 4, cell - 4);
      g.fillStyle = "#fff"; g.font = `${cell * .62}px system-ui, "Noto Color Emoji", sans-serif`;
      g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("♻️", x + cell / 2, y + cell / 2 + 1);
    }
  }
}
function teamCrater(ctx, r, c, cell) {
  const cx = (c + .5) * cell, cy = (r + .5) * cell, grad = ctx.createRadialGradient(cx, cy, cell * .05, cx, cy, cell * .47);
  grad.addColorStop(0, "#000"); grad.addColorStop(.8, "#120d22"); grad.addColorStop(1, "#4f4386");
  ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(cx, cy, cell * .47, 0, 7); ctx.fill();
}
function teamLetter(ctx, text, x, y, size, colour) {
  ctx.fillStyle = colour; ctx.font = `800 ${size}px system-ui, sans-serif`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(text, x, y + 1);
}
function teamPlate(ctx, r, c, cell, ch, pressed, sunk) {
  const x = c * cell, y = r * cell, colour = TEAM_COLOURS[ch.toUpperCase()], gap = cell * (pressed ? .14 : .08);
  ctx.globalAlpha = sunk ? .4 : 1;
  ctx.fillStyle = "rgba(10,6,24,.5)"; roundRect(ctx, x + cell * .05, y + cell * .05, cell * .9, cell * .9, cell * .14); ctx.fill();
  ctx.fillStyle = colour; roundRect(ctx, x + gap, y + gap, cell - gap * 2, cell - gap * 2, cell * .1); ctx.fill();
  teamLetter(ctx, ch.toUpperCase(), x + cell / 2, y + cell / 2, cell * .56, "#1b1734");
  ctx.globalAlpha = 1;
}
function teamDoor(ctx, r, c, cell, ch, open) {
  const x = c * cell, y = r * cell, colour = TEAM_COLOURS[ch], across = teamSquare(r, c - 1) === "#" || teamSquare(r, c + 1) === "#";
  if (open) {          // two posts, with the way between them clear
    ctx.fillStyle = colour;
    if (across) { ctx.fillRect(x, y, cell * .14, cell); ctx.fillRect(x + cell * .86, y, cell * .14, cell); }
    else { ctx.fillRect(x, y, cell, cell * .14); ctx.fillRect(x, y + cell * .86, cell, cell * .14); }
    return;
  }
  ctx.fillStyle = colour; ctx.fillRect(x + 1, y + 1, cell - 2, cell - 2);
  ctx.fillStyle = "rgba(27,23,52,.28)";
  for (let k = 1; k < 4; k++) {
    if (across) ctx.fillRect(x + k * cell / 4 - 1, y + 1, 2, cell - 2);
    else ctx.fillRect(x + 1, y + k * cell / 4 - 1, cell - 2, 2);
  }
  teamLetter(ctx, ch, x + cell / 2, y + cell / 2, cell * .62, "#1b1734");
}
function teamBoulder(ctx, r, c, cell) {
  const cx = (c + .5) * cell, cy = (r + .5) * cell, grad = ctx.createRadialGradient(cx - cell * .12, cy - cell * .14, cell * .05, cx, cy, cell * .42);
  ctx.fillStyle = "rgba(10,6,24,.35)"; ctx.beginPath(); ctx.ellipse(cx, cy + cell * .3, cell * .38, cell * .12, 0, 0, 7); ctx.fill();
  grad.addColorStop(0, "#d6d0dc"); grad.addColorStop(1, "#6a6372");
  ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(cx, cy, cell * .4, 0, 7); ctx.fill();
}
// A gold box that pulses round the squares of the class's next job.
function teamMarks(ctx, cell, ts) {
  const glow = CALM ? .9 : .65 + Math.sin(ts / 280) * .35;
  ctx.strokeStyle = `rgba(255,211,107,${glow})`; ctx.lineWidth = Math.max(2, cell * .09);
  for (const [r, c] of team.view.job ? team.view.job.marks : []) {
    roundRect(ctx, c * cell + 1, r * cell + 1, cell - 2, cell - 2, cell * .16); ctx.stroke();
  }
}
// A dotted line along the way your rover is about to drive.
function teamPlan(ctx, cell) {
  const mine = team.rovers.get(team.you);
  if (!mine || team.path.length < 2) return;
  let {tr: r, tc: c} = mine;
  ctx.strokeStyle = "rgba(140,242,198,.85)"; ctx.lineWidth = Math.max(2, cell * .1); ctx.lineCap = "round";
  ctx.setLineDash([cell * .12, cell * .26]);
  ctx.beginPath(); ctx.moveTo((c + .5) * cell, (r + .5) * cell);
  for (const way of team.path) if (TEAM_WAYS[way]) {
    r += TEAM_WAYS[way][0]; c += TEAM_WAYS[way][1];
    ctx.lineTo((c + .5) * cell, (r + .5) * cell);
  }
  ctx.stroke(); ctx.setLineDash([]);
}
// When a level is won, the map lights up everywhere the class drove.
function teamTrail(ctx, cell, ts) {
  const trail = team.view.recap && team.view.recap.trail;
  if (!trail || !trail.length) return;
  const most = Math.max(...trail.map(s => s[2])), rise = CALM ? 1 : Math.min(1, (ts - team.wonAt) / 1500);
  for (const [r, c, n] of trail) {
    ctx.fillStyle = `rgba(140,242,198,${rise * (.14 + .46 * Math.sqrt(n / most))})`;
    ctx.fillRect(c * cell, r * cell, cell + .5, cell + .5);
  }
}
// What rovers shouted: a bubble over the rover that said it.
function teamBubbles(ctx, cell, ts) {
  team.bubbles = team.bubbles.filter(b => ts - b.at < 5000);
  const size = Math.max(13, cell * .62);
  ctx.font = `700 ${size}px system-ui, "Noto Color Emoji", sans-serif`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const placed = [];
  for (const b of team.bubbles) {
    const rover = team.rovers.get(b.seat);
    if (!rover || !rover.at) continue;
    const u = (ts - b.at) / 900, wide = ctx.measureText(b.words).width + size, tall = size * 1.6;
    const x = Math.min(Math.max(wide / 2, rover.at[0]), team.size - wide / 2);
    let y = Math.max(tall / 2, rover.at[1] - cell * 1.1);
    while (placed.some(p => Math.abs(p.y - y) < tall && Math.abs(p.x - x) < (p.wide + wide) / 2)) y += tall + 2;
    placed.push({x, y, wide});
    if (u < 1 && !CALM) {
      ctx.strokeStyle = `rgba(255,255,255,${1 - u})`; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(rover.at[0], rover.at[1], cell * (.5 + u * 1.4), 0, 7); ctx.stroke();
    }
    ctx.fillStyle = "rgba(244,238,226,.96)"; roundRect(ctx, x - wide / 2, y - tall / 2, wide, tall, tall * .4); ctx.fill();
    ctx.fillStyle = "#1b1734"; ctx.fillText(b.words, x, y + 1);
  }
}
// A ring that spreads out where a boulder just went into the ground.
function teamPops(ctx, cell, now) {
  team.pops = team.pops.filter(p => now - p.at < 700);
  for (const p of team.pops) {
    const u = (now - p.at) / 700;
    ctx.strokeStyle = `rgba(255,211,107,${1 - u})`; ctx.lineWidth = Math.max(2, cell * .1);
    ctx.beginPath(); ctx.arc((p.c + .5) * cell, (p.r + .5) * cell, cell * (.3 + u), 0, 7); ctx.stroke();
  }
}
function drawTeam(ts) {
  const cv = $("teamMap"), dpr = devicePixelRatio || 1, w = cv.clientWidth, h = w / 2, view = team.view;
  if (!w || !view) return;
  const cell = w / TEAM_COLS, dt = Math.min(.1, (ts - (team.last || ts)) / 1000), now = CALM ? 0 : ts;
  team.last = ts; team.size = w;
  if (cv.width !== Math.round(w * dpr) || !team.bg) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    team.bg = document.createElement("canvas");
    team.bg.width = cv.width; team.bg.height = cv.height;
    teamPaintGround(team.bg.getContext("2d"), cell * dpr);
  }
  const ctx = cv.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(team.bg, 0, 0);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    const ch = teamSquare(r, c);
    if (ch === "o") { if (!teamSame(view.filled, r, c)) teamCrater(ctx, r, c, cell); }
    else if (teamIsPlate(ch)) teamPlate(ctx, r, c, cell, ch, teamSame(view.pressed, r, c), teamSame(view.sunk, r, c));
    else if (teamIsDoor(ch)) teamDoor(ctx, r, c, cell, ch, view.doors[ch].open);
  }
  teamMarks(ctx, cell, ts);
  teamTrail(ctx, cell, ts);
  teamPlan(ctx, cell);
  // Rovers and boulders glide to where the server says they are.
  const glide = (t, step) => {
    const far = Math.hypot(t.tr - t.r, t.tc - t.c), go = far > 3 || CALM ? far : step;
    if (far > .001) { t.r += (t.tr - t.r) * Math.min(1, go / far); t.c += (t.tc - t.c) * Math.min(1, go / far); }
  };
  for (const b of team.boulders) if (b) { glide(b, TEAM_ROVER_SPEED * dt); teamBoulder(ctx, b.r, b.c, cell); }
  teamPops(ctx, cell, ts);
  // Rovers on one square fan out a little, so nobody vanishes under a friend.
  const squares = new Map();
  for (const rover of team.rovers.values()) {
    const key = rover.tr + "," + rover.tc;
    squares.set(key, [...(squares.get(key) || []), rover]);
  }
  const order = [...team.rovers.values()].sort((a, b) => a.r - b.r);
  for (const rover of order) {
    const dr = rover.tr - rover.r, dc = rover.tc - rover.c, person = team.people.get(rover.seat);
    if (Math.hypot(dr, dc) > .05) rover.angle = Math.atan2(dr, dc);
    glide(rover, TEAM_ROVER_SPEED * dt);
    if (!person) continue;
    const same = squares.get(rover.tr + "," + rover.tc), i = same.indexOf(rover), spread = same.length > 1 ? cell * .2 : 0;
    const x = (rover.c + .5) * cell + Math.cos(i * 2.4) * spread, y = (rover.r + .5) * cell + Math.sin(i * 2.4) * spread;
    const mine = rover.seat === team.you;
    if (mine) {
      ctx.strokeStyle = "#8cf2c6"; ctx.lineWidth = Math.max(2, cell * .08);
      ctx.beginPath(); ctx.arc(x, y, cell * (.56 + (CALM ? 0 : Math.sin(ts / 260) * .05)), 0, 7); ctx.stroke();
    }
    const pose = view.won ? trickPose("dance", (ts / 1600 + rover.seat * .13) % 1, person.look.dance) : {};
    drawTrickRover(ctx, person.look, x, y, cell * .92, cell, rover.angle, pose, now);
    rover.at = [x, y];
  }
  for (const rover of order) {
    const person = team.people.get(rover.seat);
    if (person && rover.at) drawTag(ctx, person.tag, rover.at[0], rover.at[1] + cell * .66, cell, rover.seat === team.you);
  }
  teamBubbles(ctx, cell, ts);
}
function teamLoop(ts) {
  if (!team.watching && $("team").hidden) return;
  drawTeam(ts);
  requestAnimationFrame(teamLoop);
}

// ---- Keeping up with the map ------------------------------------------------------------

function teamSound(name) { if (!team.watching) SFX.play(name); }
function teamClock(secs) { return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`; }
function teamSay(text) { $("teamSay").textContent = text; }

function teamFollow(out) {
  const was = team.boulders;
  team.boulders = out.boulders.map((at, i) => {
    if (!at) return null;
    const b = was[i] || {r: at[0], c: at[1]};
    return Object.assign(b, {tr: at[0], tc: at[1]});
  });
  const here = new Set();
  for (const [seat, r, c] of out.rovers) {
    here.add(seat);
    const rover = team.rovers.get(seat);
    if (rover) Object.assign(rover, {tr: r, tc: c});
    else team.rovers.set(seat, {seat, r, c, tr: r, tc: c, angle: Math.PI / 2});
  }
  for (const seat of team.rovers.keys()) if (!here.has(seat)) team.rovers.delete(seat);
}
// The good news since the last look: sounds, and a ring where a boulder went in.
function teamCheer(old, out) {
  if (!old || old.level !== out.level) return;
  const fresh = out.sunk.concat(out.filled).filter(s => !teamSame(old.sunk.concat(old.filled), s[0], s[1]));
  for (const [r, c] of fresh) team.pops.push({r, c, at: performance.now()});
  if (fresh.length) teamSound(out.sunk.length > old.sunk.length ? "gift" : "sample");
  if (out.won && !old.won) { teamSound("win"); team.wonAt = performance.now(); }
}
function teamHear(out) {
  for (const [n, seat, words] of out.shouts) if (n > team.heard) {
    team.heard = n;
    team.bubbles.push({seat, words, at: performance.now()});
  }
}
function teamPanel(out) {
  $("teamLevel").textContent = `Level ${out.level + 1} of ${out.levels}: ${out.name}`;
  $("teamGoal").textContent = `Get to the gold vault together! ${out.in_vault} of ${out.needed} ${out.needed === 1 ? "rover is" : "rovers are"} in.`;
  $("teamJob").textContent = out.mine || (out.job ? out.job.text : "");
  $("teamJob").parentElement.style.visibility = out.job ? "" : "hidden";
  $("teamClock").textContent = `⏱ ${teamClock(out.secs)}${out.best ? ` · Class best ${teamClock(out.best)}` : ""}`;
  $("teamDoors").innerHTML = Object.keys(out.doors).sort().map(letter => {
    const d = out.doors[letter], state = d.good ? "good" : d.open ? "held" : "";
    return `<span class="${state}" style="--door:${TEAM_COLOURS[letter]}"><b>${letter}</b>${d.good ? "✓" : d.plates > 1 ? `${d.pressed}/${d.plates}` : d.open ? "open" : "shut"}</span>`;
  }).join("");
  const news = $("teamNews");
  news.replaceChildren(...out.news.slice().reverse().map(text => Object.assign(document.createElement("li"), {textContent: text})));
  const win = $("teamWin");
  win.hidden = !out.won;
  if (out.won) win.innerText = teamRecap(out);
}
// The class's level in a few words: the time, then what they did to get there.
function teamRecap(out) {
  const time = out.record === "first" ? `That's your class's time to beat.`
    : out.record ? `New class best, ${out.record} second${out.record === 1 ? "" : "s"} faster!`
    : out.best ? `Class best: ${teamClock(out.best)}.` : "";
  const done = out.next_in ? `Next level in ${out.next_in}…` : `🏆 You finished every level, together!`;
  const did = out.recap && out.recap.steps ? `Your class drove ${out.recap.steps} squares and pushed boulders ${out.recap.pushes} times.` : "";
  return [`🎉 Level ${out.level + 1} done in ${teamClock(out.secs)}!`, time, did, done].filter(Boolean).join("\n");
}
function teamTake(out) {
  if (out.error === "join") { localStorage.removeItem("mazeId"); location.reload(); return; }
  if (out.open === false) { teamSet(false); closeTeam(true); return; }
  if (out.open !== true) return;
  const old = team.view;
  if (out.map) {
    if (team.level != null && team.level !== out.level) {
      teamSay("New level! Arrow keys drive. Drive into a boulder to push it.");
      teamSound("fanfare");
    }
    if (team.auto) teamCodeSay("New level! Your program stopped, so check your code still fits this map.");
    Object.assign(team, {map: out.map, bg: null, boulders: [], path: [], auto: null, bubbles: [], heard: 0});
    team.rovers.clear();
  }
  if (out.people) team.people = new Map(out.people.map(p => [p.seat, p]));
  Object.assign(team, {you: out.you, seq: out.seq, roster: out.roster, level: out.level, view: out});
  teamFollow(out);
  teamCheer(old, out);
  teamHear(out);
  teamPanel(out);
  if (out.tip != null) {
    if (team.auto) teamCodeSay(`🤖 Something changed on the map and your rover stopped. Look where it is, then press Run again.`);
    Object.assign(team, {path: [], auto: null});
    teamSound("bump");
    if (out.tip) teamSay(out.tip);
  }
}
function teamUrl() {
  const id = team.watching ? "" : `id=${encodeURIComponent(me)}&`;
  return `/planet/team?${id}${team.seq == null ? "" : `after=${team.seq}&`}roster=${team.roster}&level=${team.level}`;
}
async function teamPoll() {
  clearTimeout(team.timer);
  const run = team.run, out = await get(teamUrl()).catch(() => null);
  if (run !== team.run) return;
  if (out) teamTake(out);
  if (run === team.run) team.timer = setTimeout(teamPoll, out && out.open ? 120 : 2000);
}

// ---- Driving --------------------------------------------------------------------------

const teamWait = ms => new Promise(done => setTimeout(done, ms));
// One step at a time, so a rover goes no faster on a quick computer.
async function teamDrive(run) {
  while (run === team.run) {
    const held = team.held && performance.now() - team.heldAt > TEAM_HOLD_MS ? team.held : null;
    const way = team.path.shift() || held;
    teamCoding();
    if (!way) { await teamWait(30); continue; }
    if (way === "wait") { await teamWait(TEAM_CODE_WAIT_MS); continue; }
    const out = await post("/planet/team", {id: me, do: "move", way, level: team.level, roster: team.roster}).catch(() => null);
    if (run !== team.run) return;
    if (out) teamTake(out);
    await teamWait(TEAM_STEP_MS);
  }
}
function teamBlocked(r, c) {
  const view = team.view, ch = teamSquare(r, c);
  return ch === "#" || (ch === "o" && !teamSame(view.filled, r, c)) || (teamIsDoor(ch) && !view.doors[ch].open)
    || view.boulders.some(b => b && b[0] === r && b[1] === c);
}
// The ways to drive from one square to another, round whatever's in the way.
function teamRoute(from, to) {
  const came = new Map([[from.join(), null]]), queue = [from];
  while (queue.length) {
    const at = queue.shift();
    if (at[0] === to[0] && at[1] === to[1]) {
      const ways = [];
      for (let step = came.get(at.join()); step; step = came.get(step.from.join())) ways.unshift(step.way);
      return ways;
    }
    for (const [way, [dr, dc]] of Object.entries(TEAM_WAYS)) {
      const next = [at[0] + dr, at[1] + dc];
      if (came.has(next.join()) || teamBlocked(...next)) continue;
      came.set(next.join(), {from: at, way});
      queue.push(next);
    }
  }
  return null;
}
function teamClick(e) {
  const box = $("teamMap").getBoundingClientRect(), cell = box.width / TEAM_COLS;
  const r = Math.floor((e.clientY - box.top) / cell), c = Math.floor((e.clientX - box.left) / cell);
  const mine = team.rovers.get(team.you);
  if (!mine || !team.view) return;
  SFX.wake();
  const from = [mine.tr, mine.tc], next = Object.entries(TEAM_WAYS).find(([, [dr, dc]]) => from[0] + dr === r && from[1] + dc === c);
  if (next) { team.path = [next[0]]; return; }            // next door: push or bump, the same as a key
  if (team.view.boulders.some(b => b && b[0] === r && b[1] === c)) { teamSay("Drive right next to that boulder, then click it to push it."); return; }
  const ways = teamRoute(from, [r, c]);
  if (ways) team.path = ways; else teamSay("Your rover can't get there yet.");
}
function teamKey(e) {
  const way = TEAM_KEYS[e.key];
  if ($("team").hidden || e.target.id === "teamCode" || !$("predict").hidden) return;
  const shout = !e.repeat && !e.ctrlKey && !e.metaKey && !e.altKey && document.querySelectorAll("[data-shout]")[e.key - 1];
  if (shout) { shout.click(); return; }             // 1 to 5, for the hand that isn't driving
  if (!way) return;
  e.preventDefault(); e.stopPropagation();   // not the scouting keys behind the map
  if (e.repeat) return;
  SFX.wake();
  Object.assign(team, {path: [way], held: way, heldAt: performance.now()});
}
function teamKeyUp(e) {
  if (TEAM_KEYS[e.key] === team.held) team.held = null;
}

// ---- 🤖 Code my rover: a program drives the rover, the same as the keys ---------------

function teamCodeSay(text, bad) {
  const say = $("teamCodeSay");
  say.textContent = text;
  say.classList.toggle("bad", !!bad);
}
// How a running program is getting on. Keys and clicks swap in a new path, and
// that stops the program.
function teamCoding() {
  const auto = team.auto;
  if (!auto) return;
  if (auto.path !== team.path) { team.auto = null; teamCodeSay("🤖 You took over, so your program stopped."); return; }
  if (team.path.length) { teamCodeSay(`🤖 Driving: move ${auto.total - team.path.length} of ${auto.total}`); return; }
  team.auto = null;
  teamCodeSay(auto.stopped ? `🤖 ${auto.stopped}` : "✅ Your program finished!", !!auto.stopped);
}
async function teamRunCode() {
  const code = $("teamCode").value;
  store("teamCode", code);
  SFX.wake();
  $("teamRun").disabled = true;
  const out = await post("/planet/team", {id: me, do: "code", code, level: team.level, roster: team.roster}).catch(() => null);
  $("teamRun").disabled = false;
  if (!out) { teamCodeSay("Your program didn't get through. Press Run again.", true); return; }
  teamTake(out);
  const p = out.program;
  if (!p) { teamCodeSay("Wait a second, then press Run again."); return; }
  $("teamPrints").textContent = p.prints.join("\n");
  if (p.error) { teamCodeSay(`${p.line && !p.error.startsWith("Line") ? `Line ${p.line}: ` : ""}${p.error}`, true); return; }
  if (!p.ways.length) { teamCodeSay(p.stopped ? `🤖 ${p.stopped}` : "Your program didn't drive anywhere. Try a line like  east(3)", true); return; }
  team.path = p.ways.slice();
  team.auto = {path: team.path, total: p.ways.length, stopped: p.stopped};
}
function teamCoder(open) {
  $("teamCoder").hidden = !open;
  if (open) {
    const box = $("teamCode");
    box.value = box.value || recall("teamCode") || "east(2)\nsouth(1)\n";
    box.focus();
  } else {
    store("teamCode", $("teamCode").value);
    $("teamClose").focus();
  }
}
function teamCodeKey(e) {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); teamRunCode(); return; }
  if (e.key === "Tab" && !e.shiftKey) { e.preventDefault(); document.execCommand("insertText", false, "    "); return; }
  if (e.key === "Enter") {
    const before = e.target.value.slice(0, e.target.selectionStart), line = before.slice(before.lastIndexOf("\n") + 1);
    e.preventDefault();
    document.execCommand("insertText", false, "\n" + line.match(/^ */)[0] + (/:\s*$/.test(line) ? "    " : ""));
  }
}

// ---- Coming and going -----------------------------------------------------------------

// The teacher opened or closed the mission. `tell` says so on a change.
function teamSet(on, tell) {
  if (on === team.open) return;
  team.open = on;
  if (team.watching) return;
  $("teamButton").hidden = !on;
  if (on && tell) toast("🤝", "The Team Mission is open!", "Press 🤝 Team Mission at the top of the page to join your class.");
}
function openTeam() {
  team.run++;
  Object.assign(team, {map: null, view: null, you: null, seq: null, roster: null, level: null, boulders: [], path: [], held: null, last: 0, auto: null});
  team.rovers.clear();
  if (!team.watching) {
    clearToasts();
    $("team").hidden = false;
    $("teamClose").focus();
    teamDrive(team.run);
  }
  teamSay("Arrow keys drive. Or click a square. Drive into a boulder to push it.");
  teamPoll();
  requestAnimationFrame(teamLoop);
}
function closeTeam(byTeacher) {
  if (team.watching) return;
  if ($("team").hidden) return;
  team.run++;
  clearTimeout(team.timer);
  $("team").hidden = true;
  if (byTeacher) toast("🤝", "The Team Mission is closed for now", "You're back on your level, and your code is just as you left it.");
}
function teamEscape() {
  if ($("team").hidden) return false;
  closeTeam();
  return true;
}
function teamWire() {
  $("teamButton").addEventListener("click", openTeam);
  $("teamClose").addEventListener("click", () => closeTeam());
  $("teamMap").addEventListener("click", teamClick);
  $("teamPad").addEventListener("click", e => {
    const b = e.target.closest("[data-way]");
    if (b) { SFX.wake(); team.path = [b.dataset.way]; }
  });
  $("teamShouts").addEventListener("click", async e => {
    const b = e.target.closest("[data-shout]");
    if (!b) return;
    SFX.wake();
    const out = await post("/planet/team", {id: me, do: "shout", key: b.dataset.shout, level: team.level, roster: team.roster}).catch(() => null);
    if (out) teamTake(out);
  });
  $("teamCodeOpen").addEventListener("click", () => teamCoder(true));
  $("teamCodeClose").addEventListener("click", () => teamCoder(false));
  $("teamRun").addEventListener("click", teamRunCode);
  $("teamStop").addEventListener("click", () => { team.path = []; });
  $("teamCode").addEventListener("keydown", teamCodeKey);
  $("teamExamples").addEventListener("click", e => {
    const b = e.target.closest("[data-eg]"), box = $("teamCode");
    if (!b) return;
    box.focus();
    box.selectionStart = box.selectionEnd = box.value.length;
    document.execCommand("insertText", false, (box.value && !box.value.endsWith("\n") ? "\n" : "") + TEAM_EXAMPLES[b.dataset.eg]);
  });
  $("teamHome").addEventListener("click", async () => {
    SFX.wake();
    team.path = [];
    const out = await post("/planet/team", {id: me, do: "home", level: team.level, roster: team.roster}).catch(() => null);
    if (out) teamTake(out);
  });
  window.addEventListener("keydown", teamKey, true);
  window.addEventListener("keyup", teamKeyUp, true);
}
