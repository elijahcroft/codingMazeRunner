// The Team Mission: the whole class on one map, live. The student page and the
// class screen (planet_team_watch.html) both draw it from here. It needs
// planet_render.js and planet_lounge.js for rovers and name tags, plus the
// page's $, get and CALM; the student page adds post, toast, SFX, me and look.
// The rules are in planet_team.py.

const TEAM_COLOURS = {A: "#ff8a7a", B: "#8fc8ff", C: "#8cf2c6", D: "#ffd36b", E: "#ff8ad8", F: "#b9a3ff", G: "#ffb547", V: "#f4eee2", Q: "#7df9ff"};
const TEAM_WAYS = {north: [-1, 0], south: [1, 0], east: [0, 1], west: [0, -1]};
const TEAM_KEYS = {ArrowUp: "north", ArrowDown: "south", ArrowLeft: "west", ArrowRight: "east"};
const TEAM_ROWS = 15, TEAM_COLS = 30;
const TEAM_STEP_MS = 130;       // a rover's pace, a step at a time
const TEAM_HOLD_MS = 220;       // a key held this long keeps driving, so a tap is one square
const TEAM_ROVER_SPEED = 9;     // squares a second on screen
const TEAM_CODE_WAIT_MS = 400;  // how long wait() holds a rover
// What a level's look says when the class arrives, for the levels with something new.
const TEAM_NEWS = {rink: "❄️ Ice! A rover or a boulder on ice slides until something stops it.",
                   drill: "💎 Find every gem! Drive over one to pick it up for the whole class.",
                   portals: "✨ Teleport pads! Drive onto one and you come out of the other one with the same number.",
                   hollow: "🔦 Lights out! You only see what's near the class's rovers. Spread out and explore!",
                   ice: "❄️ Ice and craters! A boulder that slides into a crater fills it in.",
                   laser: "🔦💎 Dark caves full of gems. Spread out and light them up!",
                   relay: "✨❄️ Teleports and ice together. Watch where things come out!",
                   tour: "🏁 The last mission: a bit of everything. You can do it together!"};
const TEAM_EXAMPLES = {repeat: 'for i in range(3):\n    east()\n', rock: 'while look("east") != "rock":\n    east()\n',
                       check: 'if look("south") == "boulder":\n    south()\n'};
const team = {open: false, watching: false, map: null, you: null, view: null, seq: null, roster: null, level: null,
              people: new Map(), rovers: new Map(), boulders: [], pops: [], run: 0, timer: 0, last: 0,
              bg: null, held: null, heldAt: 0, path: [], bubbles: [], heard: 0, wonAt: 0, auto: null,
              links: {}, fog: null, confetti: [], choiceAt: 0};

// ---- Drawing the map ------------------------------------------------------------------

const teamSquare = (r, c) => (team.map[r] || "#")[c] || "#";
const teamSame = (list, r, c) => list.some(s => s[0] === r && s[1] === c);
const teamIsDoor = ch => ch in TEAM_COLOURS;
const teamIsPlate = ch => ch !== ch.toUpperCase() && ch.toUpperCase() in TEAM_COLOURS && ch !== "q";
const teamIsPortal = ch => ch in TEAM_PORTALS;

// What each level's ground looks like: the zones of the planet, so a team map
// looks like the levels everyone plays on their own.
const TEAM_BIOMES = {
  team: {ground: "#5d4f96", rock: "#2e2656", bed: "#120f24"},
  hub: {ground: "#4f4a86", rock: "#2a2650", bed: "#0c0a1c", stars: "rgba(220,210,255,.7)"},
  landing: {ground: "#b5683f", rock: "#5a3125", bed: "#2e1912"},
  wind: {ground: "#c39457", rock: "#6a4628", bed: "#2f2014"},
  crumble: {ground: "#8f7c70", rock: "#4b3f3a", bed: "#211b19"},
  signal: {ground: "#a8936a", rock: "#5b4a33", bed: "#272016"},
  solar: {ground: "#d0a868", rock: "#76552f", bed: "#2d2112"},
  hops: {ground: "#9a8a9e", rock: "#4e4258", bed: "#211a26"},
  gates: {ground: "#8a9a86", rock: "#424d43", bed: "#1a201b"},
  push: {ground: "#a08f7d", rock: "#4f4339", bed: "#231c16"},
  rink: {ground: "#7f8fa8", rock: "#44506a", bed: "#1c2230"},
  ice: {ground: "#8e7f93", rock: "#4b4157", bed: "#231d2b"},
  drill: {ground: "#b8946a", rock: "#5e4632", bed: "#2a1d12"},
  portals: {ground: "#716a8c", rock: "#3c3655", bed: "#1a1729", stars: "rgba(229,220,255,.55)"},
  laser: {ground: "#5f5a80", rock: "#2c2846", bed: "#100e1c", stars: "rgba(140,242,198,.5)"},
  relay: {ground: "#b08a72", rock: "#5a4335", bed: "#281c15"},
  tour: {ground: "#a7866a", rock: "#53402f", bed: "#241b13"},
  hollow: {ground: "#3c4a37", rock: "#1b1f25", bed: "#07080c", edge: "#9cff6b",
           grit: ["rgba(156,255,107,.16)", "rgba(10,6,20,.35)"], stars: "rgba(185,140,255,.6)"},
};
const TEAM_GRIT = ["rgba(30,10,20,.14)", "rgba(255,240,220,.10)"];
const TEAM_PORTALS = {"1": "#b9a3ff", "2": "#8cf2c6", "3": "#ffb547", "4": "#ff8ad8"};
function teamShade(hex, f) {
  const n = parseInt(hex.slice(1), 16);
  const ch = s => Math.max(0, Math.min(255, Math.round(((n >> s) & 255) * f)));
  return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
}
const teamRock = (r, c) => teamSquare(r, c) === "#";
const teamVault = (r, c) => teamSquare(r, c) === "*";

// The map's still parts, drawn once a level: bedrock, ground, rock cliffs with a
// lit lip and a shadow, ice, the lander and the gold vault.
function teamPaintGround(g, cell, biome) {
  const pal = TEAM_BIOMES[biome] || TEAM_BIOMES.team, grit = pal.grit || TEAM_GRIT;
  g.fillStyle = pal.bed; g.fillRect(0, 0, TEAM_COLS * cell, TEAM_ROWS * cell);
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    const ch = teamSquare(r, c), x = c * cell, y = r * cell;
    if (ch === "#") continue;
    if (biome === "hub") { teamDeck(g, r, c, cell); continue; }
    g.fillStyle = teamShade(pal.ground, .9 + hash(r, c) * .14);
    g.fillRect(x, y, cell + .5, cell + .5);
    for (let k = 0; k < 6; k++) {   // grit
      g.fillStyle = grit[Math.floor(hash(r, c, k + 9) * grit.length)];
      const s = 1 + hash(r, c, k + 20) * cell * .07;
      g.fillRect(x + hash(r, c, k + 1) * cell, y + hash(r, c, k + 5) * cell, s, s);
    }
    if (ch === "*") {                // the vault: gold tiles with a bevel
      g.fillStyle = (r + c) % 2 ? "#d9ac3f" : "#c99a32"; g.fillRect(x, y, cell + .5, cell + .5);
      g.fillStyle = "rgba(255,240,190,.35)"; g.fillRect(x + 1, y + 1, cell - 2, cell * .1);
      g.fillStyle = "rgba(90,52,8,.28)"; g.fillRect(x + 1, y + cell * .88, cell - 2, cell * .1);
      g.fillStyle = "rgba(255,248,215,.45)";
      g.beginPath(); g.moveTo(x + cell / 2, y + cell * .3); g.lineTo(x + cell * .62, y + cell / 2);
      g.lineTo(x + cell / 2, y + cell * .7); g.lineTo(x + cell * .38, y + cell / 2); g.fill();
    } else if (ch === "~") {         // ice, the same as on the Ice Field
      const grad = g.createLinearGradient(x, y, x + cell, y + cell);
      grad.addColorStop(0, "#d8f1fb"); grad.addColorStop(1, "#8cc4dc");
      g.fillStyle = grad; g.fillRect(x, y, cell + .5, cell + .5);
      g.strokeStyle = "rgba(255,255,255,.6)"; g.lineWidth = Math.max(1, cell / 18);
      const o = hash(r, c, 3) * cell * .3;
      g.beginPath();
      g.moveTo(x + cell * .15 + o, y + cell * .78); g.lineTo(x + cell * .5 + o, y + cell * .3);
      g.moveTo(x + cell * .45 + o * .5, y + cell * .9); g.lineTo(x + cell * .7 + o * .5, y + cell * .55);
      g.stroke();
    } else if (ch === "S") {         // the lander's footprint
      g.strokeStyle = "rgba(242,234,219,.5)"; g.lineWidth = Math.max(1, cell / 16);
      g.beginPath();
      for (let a = 0; a < 6; a++) {
        const ang = a / 6 * Math.PI * 2 + Math.PI / 6;
        g.lineTo(x + cell / 2 + Math.cos(ang) * cell * .36, y + cell / 2 + Math.sin(ang) * cell * .36);
      }
      g.closePath(); g.stroke();
    } else if (ch === "%") {         // ♻: a round pad
      const cx = x + cell / 2, cy = y + cell / 2;
      g.fillStyle = "rgba(20,40,32,.55)"; g.beginPath(); g.arc(cx, cy, cell * .44, 0, 7); g.fill();
      g.strokeStyle = "#8cf2c6"; g.lineWidth = Math.max(1.5, cell / 14);
      g.beginPath(); g.arc(cx, cy, cell * .4, 0, 7); g.stroke();
      g.font = `${cell * .52}px system-ui, "Noto Color Emoji", sans-serif`;
      g.textAlign = "center"; g.textBaseline = "middle"; g.fillStyle = "#fff"; g.fillText("♻️", cx, cy + 1);
    }
  }
  // Faint seams on open ground, so squares can be counted.
  g.strokeStyle = "rgba(20,8,24,.16)"; g.lineWidth = 1;
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    const ch = teamSquare(r, c);
    if (ch !== "#" && ch !== "*" && ch !== "~") g.strokeRect(c * cell + .5, r * cell + .5, cell - 1, cell - 1);
  }
  // A gold edge round the vault.
  g.strokeStyle = "#ffe08f"; g.lineWidth = Math.max(1.5, cell * .07); g.lineCap = "round";
  g.beginPath();
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    if (!teamVault(r, c)) continue;
    const x = c * cell, y = r * cell;
    if (!teamVault(r - 1, c) && !teamRock(r - 1, c)) { g.moveTo(x, y); g.lineTo(x + cell, y); }
    if (!teamVault(r + 1, c) && !teamRock(r + 1, c)) { g.moveTo(x, y + cell); g.lineTo(x + cell, y + cell); }
    if (!teamVault(r, c - 1) && !teamRock(r, c - 1)) { g.moveTo(x, y); g.lineTo(x, y + cell); }
    if (!teamVault(r, c + 1) && !teamRock(r, c + 1)) { g.moveTo(x + cell, y); g.lineTo(x + cell, y + cell); }
  }
  g.stroke();
  // Rock: shadows it casts onto the ground first, then the rock on top.
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    if (!teamRock(r, c)) continue;
    const x = c * cell, y = r * cell;
    if (r + 1 < TEAM_ROWS && !teamRock(r + 1, c)) {
      const sh = g.createLinearGradient(0, y + cell, 0, y + cell * 1.25);
      sh.addColorStop(0, "rgba(10,4,12,.3)"); sh.addColorStop(1, "rgba(10,4,12,0)");
      g.fillStyle = sh; g.fillRect(x, y + cell, cell + .5, cell * .25);
    }
    if (c + 1 < TEAM_COLS && !teamRock(r, c + 1)) { g.fillStyle = "rgba(10,4,12,.16)"; g.fillRect(x + cell, y, cell * .1, cell); }
  }
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    if (!teamRock(r, c)) continue;
    const x = c * cell, y = r * cell;
    // Rock deep inside the edge fades into the bedrock, so the map doesn't end in a box.
    const inner = [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, 1], [-1, 1], [1, -1]].every(([dr, dc]) => teamRock(r + dr, c + dc));
    g.fillStyle = teamShade(pal.rock, (inner ? .5 : .66) + hash(r, c, 2) * .08);
    g.fillRect(x, y, cell + .5, cell + .5);
    if (hash(r, c, 29) < .55) {      // a loose stone or two on top
      const bx = x + cell * (.3 + hash(r, c, 30) * .4), by = y + cell * (.3 + hash(r, c, 33) * .4);
      const br = cell * (.1 + hash(r, c, 36) * .12);
      g.fillStyle = teamShade(pal.rock, (inner ? .62 : .84) + hash(r, c, 4) * .14);
      g.beginPath();
      for (let a = 0; a < 7; a++) {
        const ang = a / 7 * Math.PI * 2, rr = br * (.75 + hash(r, c, a + 40) * .35);
        a ? g.lineTo(bx + Math.cos(ang) * rr, by + Math.sin(ang) * rr) : g.moveTo(bx + Math.cos(ang) * rr, by + Math.sin(ang) * rr);
      }
      g.fill();
    }
  }
  // A cliff face under rock that drops to the ground, and a lit lip on every edge.
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    if (!teamRock(r, c) || teamRock(r + 1, c) || r + 1 >= TEAM_ROWS) continue;
    const x = c * cell, y = r * cell, face = g.createLinearGradient(0, y + cell * .78, 0, y + cell);
    face.addColorStop(0, teamShade(pal.rock, .95)); face.addColorStop(1, teamShade(pal.rock, .6));
    g.fillStyle = face; g.fillRect(x, y + cell * .78, cell + .5, cell * .22);
  }
  g.strokeStyle = pal.edge || teamShade(pal.rock, 1.5); g.lineWidth = Math.max(1.5, cell * .07); g.lineCap = "round";
  g.beginPath();
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    if (!teamRock(r, c)) continue;
    const x = c * cell, y = r * cell, k = g.lineWidth / 2, drop = teamRock(r + 1, c) ? 0 : cell * .22;
    if (r + 1 < TEAM_ROWS && !teamRock(r + 1, c)) { g.moveTo(x, y + cell - drop - k); g.lineTo(x + cell, y + cell - drop - k); }
    if (r > 0 && !teamRock(r - 1, c)) { g.moveTo(x, y + k); g.lineTo(x + cell, y + k); }
    if (c + 1 < TEAM_COLS && !teamRock(r, c + 1)) { g.moveTo(x + cell - k, y); g.lineTo(x + cell - k, y + cell - drop); }
    if (c > 0 && !teamRock(r, c - 1)) { g.moveTo(x + k, y); g.lineTo(x + k, y + cell - drop); }
  }
  g.stroke();
  // Specks of starlight on the bedrock, for the levels out in space.
  if (pal.stars) for (let k = 0; k < 160; k++) {
    const c = Math.floor(hash(k, 1, 7) * TEAM_COLS), r = Math.floor(hash(k, 2, 7) * TEAM_ROWS);
    if (!teamRock(r, c) || !teamRock(r - 1, c) || !teamRock(r + 1, c)) continue;
    g.fillStyle = pal.stars;
    g.beginPath(); g.arc((c + hash(k, 3)) * cell, (r + hash(k, 4)) * cell, .4 + hash(k, 5) * 1.1, 0, 7); g.fill();
  }
}
// The hub is a space station: metal deck plates with rivets, and lit lanes
// that lead out from the lander to the two rows of levels.
function teamDeck(g, r, c, cell) {
  const x = c * cell, y = r * cell, lane = c === 14 || c === 15 || r === 3 || r === 10;
  g.fillStyle = lane ? "#3d3a6e" : (r + c) % 2 ? "#34325f" : "#2f2d58"; g.fillRect(x, y, cell + .5, cell + .5);
  g.fillStyle = "rgba(255,255,255,.06)"; g.fillRect(x + 1, y + 1, cell - 2, cell * .06);
  g.fillStyle = "rgba(0,0,0,.22)"; g.fillRect(x + 1, y + cell * .9, cell - 2, cell * .08);
  g.fillStyle = "rgba(200,190,255,.22)";
  for (const [i, j] of [[.14, .14], [.86, .14], [.14, .86], [.86, .86]]) { g.beginPath(); g.arc(x + i * cell, y + j * cell, Math.max(.8, cell * .035), 0, 7); g.fill(); }
  if (lane) {
    g.fillStyle = r === 3 ? "rgba(255,211,107,.35)" : r === 10 ? "rgba(140,242,198,.35)" : "rgba(185,163,255,.3)";
    if (r === 3 || r === 10) g.fillRect(x, y + cell * .47, cell + .5, cell * .06);
    else g.fillRect(x + (c === 14 ? cell * .88 : 0), y, cell * .12, cell + .5);
  }
}
function teamCrater(ctx, r, c, cell) {
  const cx = (c + .5) * cell, cy = (r + .5) * cell, grad = ctx.createRadialGradient(cx - cell * .06, cy - cell * .06, cell * .04, cx, cy, cell * .47);
  grad.addColorStop(0, "#050308"); grad.addColorStop(.72, "#1d1016"); grad.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(cx, cy, cell * .47, 0, 7); ctx.fill();
  ctx.strokeStyle = "rgba(255,230,210,.3)"; ctx.lineWidth = Math.max(1, cell / 12);
  ctx.beginPath(); ctx.arc(cx, cy, cell * .42, Math.PI * .15, Math.PI * .95); ctx.stroke();
}
function teamLetter(ctx, text, x, y, size, colour) {
  ctx.fillStyle = colour; ctx.font = `800 ${size}px system-ui, sans-serif`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(text, x, y + 1);
}
// A plate: a round pressure pad in its door's colour. Pressed, it sinks in and
// glows; a boulder sunk into it leaves a stone top and a tick.
function teamPlate(ctx, r, c, cell, ch, pressed, sunk, ts) {
  const cx = (c + .5) * cell, cy = (r + .5) * cell, colour = TEAM_COLOURS[ch.toUpperCase()], R = cell * .4;
  ctx.fillStyle = "rgba(10,6,24,.42)"; ctx.beginPath(); ctx.arc(cx, cy + cell * .04, R + cell * .05, 0, 7); ctx.fill();
  ctx.fillStyle = "#6f6890"; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.fill();
  ctx.strokeStyle = "#a59fc4"; ctx.lineWidth = Math.max(1, cell * .04);
  ctx.beginPath(); ctx.arc(cx, cy, R, Math.PI * 1.05, Math.PI * 1.95); ctx.stroke();
  if (sunk) {
    const grad = ctx.createRadialGradient(cx - R * .25, cy - R * .3, R * .1, cx, cy, R * .78);
    grad.addColorStop(0, "#c9c2d0"); grad.addColorStop(1, "#6a6372");
    ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(cx, cy, R * .74, 0, 7); ctx.fill();
    ctx.strokeStyle = colour; ctx.lineWidth = Math.max(2, cell * .09); ctx.lineCap = "round"; ctx.lineJoin = "round";
    ctx.beginPath(); ctx.moveTo(cx - R * .34, cy + R * .02); ctx.lineTo(cx - R * .06, cy + R * .3); ctx.lineTo(cx + R * .38, cy - R * .26); ctx.stroke();
    return;
  }
  if (pressed && !CALM) {
    ctx.fillStyle = colour; ctx.globalAlpha = .35 + Math.sin(ts / 200) * .15;
    ctx.beginPath(); ctx.arc(cx, cy, R * 1.25, 0, 7); ctx.fill(); ctx.globalAlpha = 1;
  }
  ctx.fillStyle = pressed ? teamShade(colour, .8) : colour;
  ctx.beginPath(); ctx.arc(cx, cy + (pressed ? cell * .03 : 0), R * (pressed ? .62 : .72), 0, 7); ctx.fill();
  if (!pressed) {
    ctx.fillStyle = "rgba(255,255,255,.35)"; ctx.beginPath(); ctx.arc(cx - R * .2, cy - R * .25, R * .22, 0, 7); ctx.fill();
  }
  teamLetter(ctx, ch.toUpperCase(), cx, cy + (pressed ? cell * .03 : 0), cell * .36, "#1b1734");
}
// A door: two posts in the wall, and a force field between them while it's shut.
function teamDoor(ctx, r, c, cell, ch, door, ts) {
  const x = c * cell, y = r * cell, colour = TEAM_COLOURS[ch], across = teamRock(r, c - 1) || teamRock(r, c + 1);
  const post = cell * .18, cx = x + cell / 2, cy = y + cell / 2;
  ctx.fillStyle = "rgba(10,6,24,.35)"; ctx.fillRect(x, y, cell, cell);
  if (!door.open) {
    const flick = CALM ? .85 : .7 + Math.sin(ts / 90 + c) * .15;
    ctx.globalAlpha = .28 * flick; ctx.fillStyle = colour; ctx.fillRect(x, y, cell, cell);
    ctx.globalAlpha = flick; ctx.strokeStyle = colour; ctx.lineWidth = Math.max(1.5, cell * .07);
    ctx.beginPath();
    for (let k = 1; k <= 3; k++) {
      const wob = CALM ? 0 : Math.sin(ts / 140 + k * 2 + r) * cell * .04;
      if (across) { ctx.moveTo(x + post, y + k * cell / 4 + wob); ctx.lineTo(x + cell - post, y + k * cell / 4 - wob); }
      else { ctx.moveTo(x + k * cell / 4 + wob, y + post); ctx.lineTo(x + k * cell / 4 - wob, y + cell - post); }
    }
    ctx.stroke(); ctx.globalAlpha = 1;
  }
  // The posts.
  ctx.fillStyle = "#3b3560";
  const posts = across ? [[x, y, post, cell], [x + cell - post, y, post, cell]] : [[x, y, cell, post], [x, y + cell - post, cell, post]];
  for (const [px, py, pw, ph] of posts) {
    ctx.fillStyle = "#2a2548"; roundRect(ctx, px, py, pw, ph, post * .4); ctx.fill();
    ctx.fillStyle = door.open ? (door.good ? colour : teamShade(colour, .75)) : colour;
    roundRect(ctx, px + pw * .25, py + ph * .25, pw * .5, ph * .5, post * .2); ctx.fill();
  }
  // Its letter, on a badge.
  const b = cell * .4;
  ctx.fillStyle = door.open ? "rgba(18,15,36,.75)" : "#f4eee2";
  roundRect(ctx, cx - b / 2, cy - b / 2, b, b, b * .3); ctx.fill();
  ctx.strokeStyle = colour; ctx.lineWidth = Math.max(1, cell * .045); ctx.stroke();
  teamLetter(ctx, ch === "Q" ? "💎" : ch, cx, cy, cell * (ch === "Q" ? .24 : .3), door.open ? colour : "#1b1734");
}
function teamBoulder(ctx, r, c, cell) {
  const cx = (c + .5) * cell, cy = (r + .5) * cell, R = cell * .4;
  ctx.fillStyle = "rgba(10,6,24,.38)"; ctx.beginPath(); ctx.ellipse(cx + cell * .04, cy + cell * .3, R * .95, cell * .12, 0, 0, 7); ctx.fill();
  const grad = ctx.createRadialGradient(cx - R * .3, cy - R * .35, R * .1, cx, cy, R * 1.05);
  grad.addColorStop(0, "#e2dce6"); grad.addColorStop(.55, "#9a93a4"); grad.addColorStop(1, "#5a5364");
  ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.fill();
  ctx.fillStyle = "rgba(60,52,72,.35)";
  ctx.beginPath(); ctx.arc(cx + R * .3, cy + R * .2, R * .17, 0, 7); ctx.fill();
  ctx.beginPath(); ctx.arc(cx - R * .25, cy + R * .4, R * .11, 0, 7); ctx.fill();
  ctx.beginPath(); ctx.arc(cx + R * .05, cy - R * .45, R * .09, 0, 7); ctx.fill();
}
// A teleport pad: rings that turn, in the pad's colour, with its number.
function teamPortal(ctx, r, c, cell, ch, ts) {
  const cx = (c + .5) * cell, cy = (r + .5) * cell, colour = TEAM_PORTALS[ch], spin = CALM ? 0 : ts / 500;
  const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, cell * .46);
  grad.addColorStop(0, "rgba(255,255,255,.9)"); grad.addColorStop(.35, colour); grad.addColorStop(1, "rgba(20,14,40,.2)");
  ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(cx, cy, cell * .44, 0, 7); ctx.fill();
  ctx.strokeStyle = colour; ctx.lineWidth = Math.max(1.5, cell * .06); ctx.lineCap = "round";
  for (let k = 0; k < 3; k++) {
    ctx.beginPath(); ctx.arc(cx, cy, cell * (.28 + k * .07), spin * (k % 2 ? -1 : 1) + k, spin * (k % 2 ? -1 : 1) + k + 2.2); ctx.stroke();
  }
  teamLetter(ctx, ch, cx, cy, cell * .32, "#1b1734");
}
// A gem: a little diamond that bobs and twinkles.
function teamGem(ctx, r, c, cell, ts) {
  const cx = (c + .5) * cell, cy = (r + .5) * cell + (CALM ? 0 : Math.sin(ts / 300 + c * 1.7 + r) * cell * .05), s = cell * .3;
  ctx.fillStyle = "rgba(10,6,24,.3)"; ctx.beginPath(); ctx.ellipse(cx, (r + .5) * cell + cell * .3, s * .8, s * .25, 0, 0, 7); ctx.fill();
  ctx.fillStyle = "#7df9ff";
  ctx.beginPath(); ctx.moveTo(cx, cy - s); ctx.lineTo(cx + s * .8, cy - s * .2); ctx.lineTo(cx, cy + s); ctx.lineTo(cx - s * .8, cy - s * .2); ctx.closePath(); ctx.fill();
  ctx.fillStyle = "#d8fdff";
  ctx.beginPath(); ctx.moveTo(cx, cy - s); ctx.lineTo(cx + s * .8, cy - s * .2); ctx.lineTo(cx, cy - s * .05); ctx.lineTo(cx - s * .8, cy - s * .2); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = "#1b6f8a"; ctx.lineWidth = Math.max(1, cell * .03);
  ctx.beginPath(); ctx.moveTo(cx, cy - s); ctx.lineTo(cx + s * .8, cy - s * .2); ctx.lineTo(cx, cy + s); ctx.lineTo(cx - s * .8, cy - s * .2); ctx.closePath(); ctx.stroke();
  const tw = CALM ? 0 : Math.max(0, Math.sin(ts / 260 + c * 3 + r * 5));
  if (tw > .6) {
    ctx.strokeStyle = `rgba(255,255,255,${(tw - .6) * 2.5})`; ctx.lineWidth = 1.5;
    const sx = cx + s * .5, sy = cy - s * .6, k = s * .4;
    ctx.beginPath(); ctx.moveTo(sx - k, sy); ctx.lineTo(sx + k, sy); ctx.moveTo(sx, sy - k); ctx.lineTo(sx, sy + k); ctx.stroke();
  }
}
// The vault shimmers: a band of light that sweeps across the gold.
function teamShimmer(ctx, cell, ts) {
  if (CALM) return;
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    if (!teamVault(r, c)) continue;
    const u = Math.sin(ts / 700 - (r + c) * .45);
    if (u > .55) { ctx.fillStyle = `rgba(255,250,220,${(u - .55) * .5})`; ctx.fillRect(c * cell, r * cell, cell + .5, cell + .5); }
  }
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
// ---- The hub: a pad for every level, and the class votes by standing on one -----------

function teamClockShort(secs) { return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`; }
function teamHub(ctx, cell, ts) {
  const view = team.view, wins = view.wins || [], bests = view.bests || {}, votes = view.votes || {};
  const choice = view.choice && view.choice.level;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  // A heading over each chapter's row.
  for (const [row, chapter] of [[1, 0], [8, 1]]) {
    const levels = view.hub.filter(p => p.r === (row === 1 ? 3 : 10));
    if (!levels.length) continue;
    const done = levels.filter(p => wins.includes(p.level)).length, fresh = done === 0;
    ctx.font = `900 ${cell * .46}px system-ui, sans-serif`; ctx.textAlign = "left";
    const name = (chapter ? "DEEP SPACE" : "FIRST MISSIONS"), x0 = cell * 1.3, y0 = (row + .55) * cell;
    ctx.fillStyle = "rgba(10,6,24,.55)"; ctx.fillText(name, x0 + 2, y0 + 2);
    ctx.fillStyle = chapter ? "#8cf2c6" : "#ffd36b"; ctx.fillText(name, x0, y0);
    const w = ctx.measureText(name).width;
    ctx.font = `700 ${cell * .32}px system-ui, sans-serif`;
    const note = fresh ? "✨ NEW: nobody has been here yet!" : `🏆 ${done} of ${levels.length} done`;
    ctx.fillStyle = "rgba(244,238,226,.85)"; ctx.fillText(note, x0 + w + cell * .4, y0 + 1);
  }
  ctx.textAlign = "center";
  for (const pad of view.hub) {
    const cx = (pad.c + .5) * cell, cy = (pad.r + .5) * cell, won = wins.includes(pad.level), n = votes[pad.level] || 0;
    const chosen = choice === pad.level, deep = pad.level >= 8;
    const colour = won ? "#ffd36b" : deep ? "#8cf2c6" : "#b9a3ff";
    const pulse = CALM ? 0 : Math.sin(ts / 300 + pad.c) * .5 + .5;
    // A launch pad: a glow, a metal ring and the level's number.
    const glow = ctx.createRadialGradient(cx, cy, cell * .2, cx, cy, cell * (chosen ? 1.2 : .9));
    glow.addColorStop(0, colour + (chosen ? "cc" : "66")); glow.addColorStop(1, colour + "00");
    ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(cx, cy, cell * (chosen ? 1.2 : .9), 0, 7); ctx.fill();
    ctx.fillStyle = "#2a2548"; ctx.beginPath(); ctx.arc(cx, cy, cell * .5, 0, 7); ctx.fill();
    ctx.strokeStyle = colour; ctx.lineWidth = Math.max(2, cell * .08);
    ctx.beginPath(); ctx.arc(cx, cy, cell * .5, 0, 7); ctx.stroke();
    if (!won && !CALM) {
      ctx.globalAlpha = .6 * (1 - pulse); ctx.beginPath(); ctx.arc(cx, cy, cell * (.5 + pulse * .35), 0, 7); ctx.stroke(); ctx.globalAlpha = 1;
    }
    ctx.font = `900 ${cell * .42}px system-ui, sans-serif`; ctx.fillStyle = colour;
    ctx.fillText(pad.level + 1, cx, cy + 1);
    // Its name underneath, in two lines if it's long, then a trophy or NEW.
    ctx.font = `800 ${Math.max(9, cell * .3)}px system-ui, sans-serif`;
    const words = pad.name.split(" "), lines = [];
    for (const w of words) {
      const last = lines[lines.length - 1];
      if (last && ctx.measureText(last + " " + w).width < cell * 2.7) lines[lines.length - 1] = last + " " + w;
      else lines.push(w);
    }
    lines.forEach((line, i) => {
      const y = cy + cell * (.85 + i * .34);
      ctx.fillStyle = "rgba(10,6,24,.6)"; ctx.fillText(line, cx + 1, y + 1);
      ctx.fillStyle = "#f4eee2"; ctx.fillText(line, cx, y);
    });
    const y = cy + cell * (.88 + lines.length * .34);
    ctx.font = `800 ${Math.max(8, cell * .26)}px system-ui, "Noto Color Emoji", sans-serif`;
    if (won) {
      const best = bests[String(pad.level)];
      ctx.fillStyle = "#ffd36b"; ctx.fillText(`🏆${best ? " " + teamClockShort(best) : ""}`, cx, y);
    } else {
      const w = cell * 1.05, h = cell * .34;
      ctx.fillStyle = deep ? "#8cf2c6" : "#b9a3ff"; roundRect(ctx, cx - w / 2, y - h / 2, w, h, h / 2); ctx.fill();
      ctx.fillStyle = "#1b1734"; ctx.fillText(deep ? "NEW!" : "TRY IT", cx, y + 1);
    }
    // How many rovers are voting for it.
    if (n) {
      const w = cell * .9, h = cell * .42, by = cy - cell * .95;
      ctx.fillStyle = chosen ? "#ffd36b" : "#f4eee2"; roundRect(ctx, cx - w / 2, by - h / 2, w, h, h / 2); ctx.fill();
      ctx.font = `900 ${cell * .3}px system-ui, "Noto Color Emoji", sans-serif`; ctx.fillStyle = "#1b1734";
      ctx.fillText(`🗳 ${n}`, cx, by + 1);
    }
  }
}
// The countdown when half the class is on one pad.
function teamCountdown(ctx, cell, ts) {
  const view = team.view;
  if (!view.choice) return;
  const left = Math.max(0, Math.ceil(view.choice.in - (performance.now() - team.choiceAt) / 1000));
  const pad = view.hub.find(p => p.level === view.choice.level);
  const text = `🚀 Off to ${pad ? pad.name : "the level"} in ${left || "…"}`;
  ctx.font = `900 ${cell * .55}px system-ui, "Noto Color Emoji", sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const w = ctx.measureText(text).width + cell * 1.2, h = cell * 1.05, x = TEAM_COLS * cell / 2, y = 6.95 * cell;
  ctx.fillStyle = "rgba(18,15,36,.9)"; roundRect(ctx, x - w / 2, y - h / 2, w, h, h / 2); ctx.fill();
  ctx.strokeStyle = "#ffd36b"; ctx.lineWidth = 3; ctx.stroke();
  ctx.fillStyle = "#ffd36b"; ctx.fillText(text, x, y + 2);
}

// ---- The dark: only what the class has lit up shows ------------------------------------

function teamFog(ctx, cell) {
  const view = team.view;
  if (!view.seen) return;
  const w = TEAM_COLS * cell, h = TEAM_ROWS * cell;
  if (!team.fog || team.fog.width !== Math.ceil(w)) { team.fog = document.createElement("canvas"); team.fog.width = Math.ceil(w); team.fog.height = Math.ceil(h); }
  const g = team.fog.getContext("2d");
  g.globalCompositeOperation = "source-over"; g.clearRect(0, 0, w, h);
  g.fillStyle = "rgb(4,3,10)"; g.fillRect(0, 0, w, h);
  g.globalCompositeOperation = "destination-out";
  g.fillStyle = "rgba(0,0,0,.55)";
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    if (view.seen[r * TEAM_COLS + c] === "1") g.fillRect(c * cell - .5, r * cell - .5, cell + 1, cell + 1);
  }
  for (const rover of team.rovers.values()) {
    const x = (rover.c + .5) * cell, y = (rover.r + .5) * cell, R = cell * 2.7;
    const grad = g.createRadialGradient(x, y, cell * .6, x, y, R);
    grad.addColorStop(0, "rgba(0,0,0,1)"); grad.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = grad; g.beginPath(); g.arc(x, y, R, 0, 7); g.fill();
  }
  ctx.drawImage(team.fog, 0, 0, w, h);
}

// ---- A win: confetti over the map --------------------------------------------------------

function teamConfetti(ctx, dt) {
  if (CALM) return;
  for (const p of team.confetti) {
    p.vy += 260 * dt; p.x += p.vx * dt; p.y += p.vy * dt; p.spin += dt * 8;
    ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.spin);
    ctx.fillStyle = p.colour; ctx.fillRect(-p.s, -p.s / 2, p.s * 2, p.s); ctx.restore();
  }
  team.confetti = team.confetti.filter(p => p.y < team.size);
}
function teamBurst(cell) {
  if (CALM) return;
  const colours = ["#ffd36b", "#8cf2c6", "#ff8ad8", "#b9a3ff", "#7df9ff", "#ff8a7a"];
  for (let i = 0; i < 140; i++) {
    team.confetti.push({x: Math.random() * TEAM_COLS * cell, y: -Math.random() * cell * 4, vx: (Math.random() - .5) * 90,
                        vy: Math.random() * 60, s: cell * (.08 + Math.random() * .08), spin: Math.random() * 6,
                        colour: colours[i % colours.length]});
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
    teamPaintGround(team.bg.getContext("2d"), cell * dpr, view.biome);
  }
  const ctx = cv.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(team.bg, 0, 0);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  teamShimmer(ctx, cell, ts);
  for (let r = 0; r < TEAM_ROWS; r++) for (let c = 0; c < TEAM_COLS; c++) {
    const ch = teamSquare(r, c);
    if (ch === "o") { if (!teamSame(view.filled, r, c)) teamCrater(ctx, r, c, cell); }
    else if (teamIsPlate(ch)) teamPlate(ctx, r, c, cell, ch, teamSame(view.pressed, r, c), teamSame(view.sunk, r, c), ts);
    else if (teamIsDoor(ch)) teamDoor(ctx, r, c, cell, ch, view.doors[ch], ts);
    else if (teamIsPortal(ch)) teamPortal(ctx, r, c, cell, ch, ts);
  }
  for (const [r, c] of view.gems || []) teamGem(ctx, r, c, cell, ts);
  if (view.hub) teamHub(ctx, cell, ts);
  teamMarks(ctx, cell, ts);
  teamTrail(ctx, cell, ts);
  // Rovers and boulders glide to where the server says they are.
  const glide = (t, step) => {
    const far = Math.hypot(t.tr - t.r, t.tc - t.c), go = far > 3 || CALM ? far : step;
    if (far > .001) { t.r += (t.tr - t.r) * Math.min(1, go / far); t.c += (t.tc - t.c) * Math.min(1, go / far); }
  };
  for (const b of team.boulders) if (b) { glide(b, TEAM_ROVER_SPEED * 1.6 * dt); teamBoulder(ctx, b.r, b.c, cell); }
  teamPops(ctx, cell, ts);
  for (const rover of team.rovers.values()) glide(rover, TEAM_ROVER_SPEED * (teamSquare(rover.tr, rover.tc) === "~" ? 1.8 : 1) * dt);
  teamFog(ctx, cell);
  teamPlan(ctx, cell);
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
  if (view.hub) teamCountdown(ctx, cell, ts);
  teamConfetti(ctx, dt);
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
  if (out.won && !old.won) { teamSound("win"); team.wonAt = performance.now(); teamBurst(team.size / TEAM_COLS); }
  if (out.found > old.found) teamSound(out.gems.length ? "sample" : "gift");
}
function teamHear(out) {
  for (const [n, seat, words] of out.shouts) if (n > team.heard) {
    team.heard = n;
    team.bubbles.push({seat, words, at: performance.now()});
  }
}
function teamPanel(out) {
  $("teamLevel").textContent = out.hub ? "🗺 Mission Hub" : `${out.chapter.name} ${out.chapter.at} of ${out.chapter.of}: ${out.name}${out.seen ? " 🔦" : ""}`;
  $("teamGoal").textContent = out.hub ? `Pick a level together! ${out.needed} ${out.needed === 1 ? "rover needs" : "rovers need"} to stand on it.`
    : `Get to the gold vault together! ${out.in_vault} of ${out.needed} ${out.needed === 1 ? "rover is" : "rovers are"} in.`;
  $("teamJob").textContent = out.mine || (out.job ? out.job.text : "");
  $("teamJob").parentElement.style.visibility = out.job ? "" : "hidden";
  $("teamClock").textContent = out.hub ? "" : `⏱ ${teamClock(out.secs)}${out.best ? ` · Class best ${teamClock(out.best)}` : ""}`;
  $("teamDoors").parentElement.hidden = out.hub;
  $("teamDoors").innerHTML = Object.keys(out.doors).sort().map(letter => {
    const d = out.doors[letter], state = d.good ? "good" : d.open ? "held" : "";
    const what = letter === "Q" ? `${d.pressed}/${d.plates}` : d.good ? "✓" : d.plates > 1 ? `${d.pressed}/${d.plates}` : d.open ? "open" : "shut";
    return `<span class="${state}" style="--door:${TEAM_COLOURS[letter]}"><b>${letter === "Q" ? "💎" : letter}</b>${what}</span>`;
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
  const done = out.next_hub ? `🏆 You finished ${out.chapter.name}, together! Back to the hub in ${out.next_in}…`
    : out.next_in ? `Next level in ${out.next_in}…` : "";
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
      teamSay(out.hub ? "Back on the hub! Drive onto the level you want to play next."
        : TEAM_NEWS[out.biome] || "New level! Arrow keys drive. Drive into a boulder to push it.");
      teamSound("fanfare");
    }
    if (team.auto) teamCodeSay("New level! Your program stopped, so check your code still fits this map.");
    Object.assign(team, {map: out.map, bg: null, boulders: [], path: [], auto: null, bubbles: [], heard: 0, confetti: [], links: teamLinks(out.map)});
    team.rovers.clear();
    if (out.hub && team.level == null) teamSay("🗳 Drive onto a level's pad to vote for it. When half the class is on one, you all go!");
  }
  if (out.people) team.people = new Map(out.people.map(p => [p.seat, p]));
  Object.assign(team, {you: out.you, seq: out.seq, roster: out.roster, level: out.level, view: out});
  if (out.choice) team.choiceAt = performance.now();
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
// The teleport pads on a map: each one, and the pad with the same number.
function teamLinks(map) {
  const pads = {}, links = {};
  map.forEach((row, r) => [...row].forEach((ch, c) => { if (teamIsPortal(ch)) (pads[ch] = pads[ch] || []).push([r, c]); }));
  for (const [a, b] of Object.values(pads)) if (a && b) { links[a.join()] = b; links[b.join()] = a; }
  return links;
}
// Where a rover that drives onto a square ends up: ice slides it on, and a
// teleport pad takes it across. The same as the server's Mission.glide.
function teamGlide(at, way) {
  const [dr, dc] = TEAM_WAYS[way], boulder = s => team.view.boulders.some(b => b && b[0] === s[0] && b[1] === s[1]);
  for (let i = 0; i < 60; i++) {
    const link = team.links[at.join()];
    if (link && !boulder(link)) return link;
    if (teamSquare(...at) !== "~") return at;
    const ahead = [at[0] + dr, at[1] + dc];
    if (teamBlocked(...ahead)) return at;
    at = ahead;
  }
  return at;
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
      const step = [at[0] + dr, at[1] + dc];
      if (teamBlocked(...step)) continue;
      const next = teamGlide(step, way);
      if (came.has(next.join())) continue;
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
