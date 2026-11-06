// Strange Planet's run replay for the class pages (teacher and projector): a
// site's map as students see it, and the rover driving the route of a run
// from /planet/overview's "runs". Needs planet_render.js, and CALM defined.

const REPLAY_REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
const REPLAY_TILE = {"#": "#1d1736", ".": "#4f4386", S: "#4f4386", "*": "#4f4386", G: "#4f4386", "~": "#7fb2e6",
                     O: "#4f4386", "+": "#7a6430", P: "#4f4386", D: "#7a4f2a", ">": "#4a4766", "<": "#4a4766",
                     "^": "#4a4766", v: "#4a4766", H: "#2f7a60", k: "#4f4386", B: "#4f4386",
                     h: "#1d1736", z: "#1d1736", m: "#1d1736", c: "#4f4386", g: "#4f4386"};
const DANCE_MS = 900, DANCE_REST = 700;   // a dance at the beacon, then a breather
const REPLAY_BELT = {"^": -Math.PI / 2, ">": 0, v: Math.PI / 2, "<": Math.PI};

// The map, with what the rover has already picked up (`taken`) gone. `pal`
// is the student's map look from the garage (planet_render's WORLDS), if any:
// its ground and rock in place of the replay's own.
function replayMap(g, map, cell, taken, now, pal) {
  const tile = ch => {
    const t = REPLAY_TILE[ch] || REPLAY_TILE["."];
    return !pal ? t : t === REPLAY_TILE["."] ? pal.ground : t === REPLAY_TILE["#"] ? pal.rock : t;
  };
  map.forEach((row, r) => [...row].forEach((ch, c) => {
    const x = c * cell, y = r * cell, cx = x + cell / 2, cy = y + cell / 2, at = r + "," + c;
    g.fillStyle = tile(ch);
    g.fillRect(x, y, cell + .5, cell + .5);
    if (ch === "#") {   // rock: dark, with a lit top edge
      g.fillStyle = "rgba(185,163,255,.16)"; g.fillRect(x, y, cell, cell * .14);
    } else if ((r + c) % 2 && ch !== "~") {
      g.fillStyle = "rgba(255,255,255,.04)"; g.fillRect(x, y, cell, cell);
    }
    if (ch === "O") {
      const grad = g.createRadialGradient(cx, cy, cell * .05, cx, cy, cell * .46);
      grad.addColorStop(0, "#000"); grad.addColorStop(.8, "#120d22"); grad.addColorStop(1, tile("."));
      g.fillStyle = grad; g.beginPath(); g.arc(cx, cy, cell * .46, 0, 7); g.fill();
    } else if (ch === "*" && !taken.has(at)) {
      g.fillStyle = "#ffb547"; g.beginPath();
      g.moveTo(cx, cy - cell * .26); g.lineTo(cx + cell * .2, cy); g.lineTo(cx, cy + cell * .26); g.lineTo(cx - cell * .2, cy); g.fill();
    } else if (ch === "k" && !taken.has(at)) {
      g.font = `${cell * .6}px serif`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("🔑", cx, cy);
    } else if (ch === "G") {
      const k = REPLAY_REDUCED ? .5 : .5 + .5 * Math.sin(now / 300);
      g.strokeStyle = `rgba(140,242,198,${.35 + .4 * k})`; g.lineWidth = cell * .08;
      g.beginPath(); g.arc(cx, cy, cell * (.3 + .1 * k), 0, 7); g.stroke();
      g.fillStyle = "#8cf2c6"; g.beginPath(); g.arc(cx, cy, cell * .16, 0, 7); g.fill();
    } else if (ch === "P") {
      g.strokeStyle = "#d9cbff"; g.lineWidth = cell * .08;
      g.beginPath(); g.arc(cx, cy, cell * .3, 0, 7); g.stroke();
      g.fillStyle = "rgba(185,163,255,.45)"; g.fill();
    } else if (REPLAY_BELT[ch] != null) {
      g.save(); g.translate(cx, cy); g.rotate(REPLAY_BELT[ch]); g.fillStyle = "#a9a3c8";
      g.beginPath(); g.moveTo(cell * .22, 0); g.lineTo(-cell * .12, -cell * .2); g.lineTo(-cell * .12, cell * .2); g.fill(); g.restore();
    } else if (ch === "B") {
      g.fillStyle = "#b8b2c0"; g.beginPath(); g.arc(cx, cy, cell * .38, 0, 7); g.fill();
      g.fillStyle = "rgba(0,0,0,.2)"; g.beginPath(); g.arc(cx + cell * .08, cy + cell * .08, cell * .28, 0, 7); g.fill();
    } else if (ch === "+") {
      g.fillStyle = "rgba(255,211,107,.55)"; g.beginPath(); g.arc(cx, cy, cell * .18, 0, 7); g.fill();
    } else if (ch >= "1" && ch <= "9") {
      g.font = `${cell * .5}px serif`; g.textAlign = "center"; g.textBaseline = "middle";
      g.globalAlpha = taken.has(at) ? .35 : 1; g.fillText("🚩", cx, cy); g.globalAlpha = 1;
    } else if (ch === "H") {
      g.font = `${cell * .55}px serif`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("📦", cx, cy);
    } else if (ch === "D") {
      g.fillStyle = "#3a2410"; g.fillRect(x + cell * .2, y + cell * .1, cell * .6, cell * .8);
    } else if (ch === "h" || ch === "z" || ch === "m") {   // Halloween night's houses
      g.font = `${cell * .7}px serif`; g.textAlign = "center"; g.textBaseline = "middle";
      g.fillText(ch === "h" ? "🏠" : ch === "z" ? "🏚" : "❓", cx, cy);
      if (ch === "h" && taken.has("knock " + at)) { g.font = `800 ${cell * .4}px system-ui`; g.fillStyle = "#8cf2c6"; g.fillText("✓", cx + cell * .28, cy - cell * .28); }
    } else if (ch === "c" && !taken.has(at)) {
      g.font = `${cell * .55}px serif`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("🍬", cx, cy);
    } else if (ch === "g") {
      g.font = `${cell * .55}px serif`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("🪦", cx, cy);
    }
  }));
}

// Where the rover is at moment `u` of a route: between two frames, with a
// hop for a jump, and straight through for a pad.
function replayAt(path, u) {
  const i = Math.min(path.length - 1, Math.floor(u)), j = Math.min(path.length - 1, i + 1), f = u - i;
  const a = path[i], b = path[j];
  if (b[2] === "portal") return {r: a[0], c: a[1], lift: 0, i, a, b: a};
  return {r: a[0] + (b[0] - a[0]) * f, c: a[1] + (b[1] - a[1]) * f,
          lift: b[2] === "jump" ? Math.sin(Math.PI * f) : 0, i, a, b};
}

// One stage: play(run) starts a replay, draw(now) paints a frame of it, and
// onFinish(run) is called once when the rover gets to the end of its route.
function replayStage(screen, canvas) {
  const st = {run: null, started: 0, step: 200, done: false, held: 0, angle: 0, confetti: [], tick: "", onFinish: null};
  st.play = run => {
    st.run = run; st.started = performance.now(); st.done = false; st.confetti = [];
    st.step = Math.max(90, Math.min(320, 3600 / Math.max(1, run.path.length)));
  };
  st.draw = now => {
    const rect = screen.getBoundingClientRect(), dpr = devicePixelRatio || 1;
    if (canvas.width !== Math.round(rect.width * dpr) || canvas.height !== Math.round(rect.height * dpr)) {
      canvas.width = Math.round(rect.width * dpr); canvas.height = Math.round(rect.height * dpr);
    }
    const g = canvas.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, rect.width, rect.height);
    const run = st.run;
    if (!run) return;
    const map = run.map, rows = map.length, cols = map[0].length;
    const pad = st.pad == null ? 40 : st.pad, cell = Math.min((rect.width - pad) / cols, (rect.height - pad) / rows, 72);
    const ox = (rect.width - cols * cell) / 2, oy = (rect.height - rows * cell) / 2;
    const path = run.path, total = Math.max(0, path.length - 1);
    // A frame's time can be a moment before play() was called.
    const u = st.done ? total : Math.max(0, Math.min(total, (now - st.started) / st.step));
    const pos = replayAt(path, u);
    const taken = new Set();
    for (let k = 0; k <= pos.i; k++) {
      taken.add(path[k][0] + "," + path[k][1]);
      if (path[k][3]) taken.add(`knock ${path[k][3][0]},${path[k][3][1]}`);   // a door knocked on
    }
    g.save(); g.translate(ox, oy);
    // The student's own map look, except on Halloween night's spooky streets.
    const look = run.look || {};
    replayMap(g, map, cell, taken, now, /^h\d+$/.test(run.site || "") ? null : WORLDS[look.world]);
    if (look.trail && look.trail !== "tracks") {
      // Their trail from the garage, as it looks on their own screen.
      const frames = path.slice(0, pos.i + 1).map(([r, c, e]) => ({r, c, e}));
      drawTrail(g, frames, frames.length - 1, {r: pos.r, c: pos.c}, cell, now, look);
    } else {
      // The route so far, broken where a pad sent the rover somewhere else.
      g.strokeStyle = "rgba(140,242,198,.65)"; g.lineWidth = Math.max(2, cell * .1); g.lineCap = "round"; g.lineJoin = "round";
      g.beginPath();
      for (let k = 0; k <= pos.i; k++) {
        const [r, c, e] = path[k], x = (c + .5) * cell, y = (r + .5) * cell;
        if (!k || e === "portal") g.moveTo(x, y); else g.lineTo(x, y);
      }
      if (!st.done) g.lineTo((pos.c + .5) * cell, (pos.r + .5) * cell);
      g.stroke();
    }
    const dr = pos.b[0] - pos.a[0], dc = pos.b[1] - pos.a[1];
    if (dr || dc) st.angle = Math.atan2(Math.sign(dr), Math.sign(dc));
    const party = st.done && run.reached && !REPLAY_REDUCED;
    const shrink = st.done && run.end === "fell" ? Math.max(.2, 1 - (now - st.held) / 700) : 1;
    const x = (pos.c + .5) * cell, y = (pos.r + .5) * cell - pos.lift * cell * .7;
    if (pos.lift) {
      g.fillStyle = "rgba(0,0,0,.35)"; g.beginPath();
      g.ellipse(x, (pos.r + .5) * cell + cell * .25, cell * .3 * (1 - pos.lift * .4), cell * .1, 0, 0, 7); g.fill();
    }
    // At the beacon: the student's own victory dance, again and again.
    const u2 = party ? ((now - st.held) % (DANCE_MS + DANCE_REST)) / DANCE_MS : 1;
    const d = dance(u2 < 1 ? look.dance : "none", Math.min(1, u2));
    const rx = x + d.dx * cell, ry = y + d.dy * cell - d.lift * cell * .6;
    if (d.ring) discoRing(g, rx, ry, cell, d.ring, now);
    g.save(); g.translate(rx, ry); g.scale(d.sx || .02, 1);
    drawRover(g, 0, 0, cell * 1.15 * (1 + pos.lift * .3 + d.lift * .25) * shrink, st.angle + d.angle, d.alpha, look, now);
    g.restore();
    danceFx(g, rx, ry, cell, d);
    if (look.pet && look.pet !== "nopet") drawPet(g, x + cell * .55, y - cell * .55, cell * 1.2, look.pet, now);
    // Halloween night's ghosts, floating to and fro (a square a tick, as on the planet).
    for (const gh of run.ghosts || []) {
      const n = gh.path.length, span = 2 * (n - 1) || 1, t = u, k = Math.floor(t), f = t - k;
      const at = j => { const i = ((gh.start || 0) + j) % span; return gh.path[i < n ? i : span - i]; };
      const a = at(k), b = at(k + 1), gx = (a[1] + (b[1] - a[1]) * f + .5) * cell, gy = (a[0] + (b[0] - a[0]) * f + .45) * cell;
      g.globalAlpha = .85; g.font = `${cell * .8}px serif`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("👻", gx, gy); g.globalAlpha = 1;
    }
    g.restore();
    st.tick = `tick ${Math.round(u)} / ${total}`;
    for (const p of st.confetti) {
      p.x += p.vx; p.y += p.vy; p.r += .1;
      g.save(); g.translate(p.x * rect.width, p.y * rect.height); g.rotate(p.r);
      g.fillStyle = p.c; g.fillRect(-4, -2, 8, 4); g.restore();
    }
    st.confetti = st.confetti.filter(p => p.y < 1.1);
    if (!st.done && u >= total) {
      st.done = true; st.held = now;
      if (run.reached && !REPLAY_REDUCED) for (let i = 0; i < 90; i++)
        st.confetti.push({x: Math.random(), y: -Math.random() * .3, vx: (Math.random() - .5) * .004, vy: .003 + Math.random() * .006,
                          r: Math.random() * 6.3, c: ["#8cf2c6", "#ffd36b", "#ff8ad8", "#b9a3ff", "#ffb547"][i % 5]});
      if (st.onFinish) st.onFinish(run);
    }
  };
  return st;
}

// A rover and its pet, standing still: for a card or a name tag.
function replayAvatar(canvas, look, px) {
  const dpr = devicePixelRatio || 1;
  if (canvas.width !== px * dpr) { canvas.width = px * dpr; canvas.height = px * dpr; }
  const g = canvas.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, px, px);
  drawRover(g, px * .45, px * .55, px * .78, -Math.PI / 2 + .35, 1, look, 0);
  if (look.pet && look.pet !== "nopet") drawPet(g, px * .78, px * .3, px * .55, look.pet, 0);
}
