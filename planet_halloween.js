// Halloween night on the student page (a limited-time event, see planet.py's
// HALLOWEEN_ZONES): lit houses, haunted ones and mystery ones, candy on the
// ground, ghosts floating to and fro, a moonlit sky over the map, and the
// event's own screens: the invitation and the candy road. The page's script
// calls into this; it uses the page's helpers (hash, esc, plural, look...).

const SPOOKY_ZONES = ["street", "hollow"];
function spooky(zone) { return SPOOKY_ZONES.includes(zone); }

// ---- On the map ---------------------------------------------------------------------

// Where a ghost is at time t, which can fall between two ticks: it floats to
// and fro along its path, a square a tick (the same as planet.py's World).
function ghostSpot(g, t) {
  const n = g.path.length, span = 2 * (n - 1) || 1;
  const at = k => { const i = (((g.start || 0) + k) % span + span) % span; return g.path[i < n ? i : span - i]; };
  const k = Math.floor(t), u = t - k, a = at(k), b = at(k + 1);
  return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u];
}
// The planet time the picture is at: between frames while the replay moves,
// and (before anything has run) a clock, so the ghosts patrol for a look.
function spookyTime(i, now) {
  const f = scene.frames[i], g = scene.frames[Math.min(i + 1, scene.frames.length - 1)];
  if (!scene.run && !scout) return CALM ? 0 : now / 650;
  return f.t + (g.t - f.t) * Math.max(0, Math.min(1, pos - i));
}
// A ghost, `z` tall, floating at (x, y): a glowing sheet with a wavy hem.
function drawSpook(ctx, x, y, z, now, alpha = .88, face = "o") {
  const t = CALM ? 0 : now;
  ctx.save(); ctx.translate(x, y + Math.sin(t / 300 + x) * z * .05); ctx.globalAlpha = alpha;
  ctx.shadowColor = "#c9b8ff"; ctx.shadowBlur = z * .5; ctx.fillStyle = "#f1edff";
  const w = z * .36;
  ctx.beginPath(); ctx.moveTo(-w, z * .4); ctx.lineTo(-w, -z * .05); ctx.arc(0, -z * .05, w, Math.PI, 0); ctx.lineTo(w, z * .4);
  for (let k = 0; k < 4; k++) {
    const hx = w - (k + 1) * w / 2, wave = Math.sin(t / 140 + k) * z * .05;
    ctx.quadraticCurveTo(hx + w / 4, z * .52 + wave, hx, z * .4 - wave);
  }
  ctx.fill(); ctx.shadowBlur = 0;
  ctx.fillStyle = "#1b1530";
  for (const side of [-1, 1]) { ctx.beginPath(); ctx.ellipse(side * w * .38, -z * .08, w * .14, w * .2, 0, 0, 7); ctx.fill(); }
  if (face === "o") { ctx.beginPath(); ctx.ellipse(0, z * .12, w * .14, w * .18, 0, 0, 7); ctx.fill(); }
  else { ctx.beginPath(); ctx.ellipse(0, z * .14, w * .34, w * .3, 0, 0, Math.PI); ctx.fill(); }
  ctx.restore();
}
// A house, drawn upright on its square: lit windows, a pumpkin on the step,
// and once it's been visited, its door open and light spilling out.
function drawHouse(ctx, r, c, cell, now, visited) {
  const x = c * cell, y = r * cell, s = cell, k = CALM ? 1 : .85 + .15 * Math.sin(now / 170 + c * 3);
  ctx.fillStyle = "rgba(10,6,24,.4)"; ctx.fillRect(x + s * .1, y + s * .9, s * .84, s * .08);
  ctx.fillStyle = "#6b4a6e"; ctx.fillRect(x + s * .14, y + s * .44, s * .72, s * .5);
  ctx.fillStyle = "#4a3150"; ctx.fillRect(x + s * .66, y + s * .1, s * .1, s * .24);   // the chimney
  ctx.fillStyle = "#2a1838"; ctx.beginPath(); ctx.moveTo(x + s * .04, y + s * .48); ctx.lineTo(x + s * .5, y + s * .1); ctx.lineTo(x + s * .96, y + s * .48); ctx.fill();
  ctx.shadowColor = "#ffb547"; ctx.shadowBlur = s * .25 * k;
  ctx.fillStyle = `rgba(255,${190 + Math.round(30 * k)},90,${.75 + .25 * k})`;
  for (const wx of [.2, .62]) ctx.fillRect(x + s * wx, y + s * .52, s * .17, s * .15);
  ctx.shadowBlur = 0;
  ctx.strokeStyle = "#2a1838"; ctx.lineWidth = Math.max(1, s * .025);
  for (const wx of [.2, .62]) { ctx.beginPath(); ctx.moveTo(x + s * (wx + .085), y + s * .52); ctx.lineTo(x + s * (wx + .085), y + s * .67); ctx.stroke(); }
  if (visited) {   // the door open, light pouring out, and a tick of thanks over it
    ctx.fillStyle = "#ffe6a0"; ctx.fillRect(x + s * .41, y + s * .7, s * .18, s * .24);
    ctx.fillStyle = "#3a2410"; ctx.beginPath(); ctx.moveTo(x + s * .41, y + s * .7); ctx.lineTo(x + s * .33, y + s * .74); ctx.lineTo(x + s * .33, y + s * .97); ctx.lineTo(x + s * .41, y + s * .94); ctx.fill();
    ctx.fillStyle = "#8cf2c6"; ctx.font = `800 ${Math.round(s * .26)}px system-ui, sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("✓", x + s * .5, y + s * .32);
  } else {
    ctx.fillStyle = "#5a3418"; ctx.fillRect(x + s * .41, y + s * .7, s * .18, s * .24);
    ctx.fillStyle = "#ffd36b"; ctx.beginPath(); ctx.arc(x + s * .55, y + s * .83, s * .022, 0, 7); ctx.fill();
  }
  // A jack-o'-lantern on the step, grinning.
  const px = x + s * .8, py = y + s * .86;
  ctx.fillStyle = "#ff8a1f"; ctx.beginPath(); ctx.ellipse(px, py, s * .1, s * .08, 0, 0, 7); ctx.fill();
  ctx.fillStyle = `rgba(255,236,120,${k})`; ctx.fillRect(px - s * .05, py - s * .025, s * .03, s * .025); ctx.fillRect(px + s * .02, py - s * .025, s * .03, s * .025);
  ctx.fillRect(px - s * .045, py + s * .02, s * .09, s * .02);
}
// A haunted house: crooked and dark, boarded up, a green light in a broken
// window with eyes in it, and a cobweb.
function drawHaunted(ctx, r, c, cell, now) {
  const x = c * cell, y = r * cell, s = cell, k = CALM ? .7 : .55 + .45 * Math.abs(Math.sin(now / 900 + c));
  ctx.fillStyle = "rgba(10,6,24,.45)"; ctx.fillRect(x + s * .1, y + s * .9, s * .84, s * .08);
  ctx.save(); ctx.translate(x + s * .5, y + s * .94); ctx.rotate(-.06); ctx.translate(-x - s * .5, -y - s * .94);
  ctx.fillStyle = "#33293f"; ctx.fillRect(x + s * .14, y + s * .42, s * .72, s * .52);
  ctx.fillStyle = "#16101e"; ctx.beginPath(); ctx.moveTo(x + s * .02, y + s * .46); ctx.lineTo(x + s * .44, y + s * .06); ctx.lineTo(x + s * .56, y + s * .16); ctx.lineTo(x + s * .98, y + s * .48); ctx.fill();
  ctx.shadowColor = "#9cff6b"; ctx.shadowBlur = s * .3 * k;
  ctx.fillStyle = `rgba(156,255,107,${.35 + .5 * k})`;
  ctx.beginPath(); ctx.moveTo(x + s * .22, y + s * .5); ctx.lineTo(x + s * .42, y + s * .5); ctx.lineTo(x + s * .38, y + s * .58); ctx.lineTo(x + s * .42, y + s * .68); ctx.lineTo(x + s * .22, y + s * .68); ctx.fill();
  ctx.shadowBlur = 0;
  ctx.fillStyle = "#16101e";
  for (const ex of [.27, .35]) { ctx.beginPath(); ctx.arc(x + s * ex, y + s * .6, s * .022, 0, 7); ctx.fill(); }
  ctx.fillStyle = "#4a3a2a"; ctx.fillRect(x + s * .58, y + s * .68, s * .2, s * .26);
  ctx.strokeStyle = "#7a5a3a"; ctx.lineWidth = Math.max(1, s * .04);
  ctx.beginPath(); ctx.moveTo(x + s * .56, y + s * .72); ctx.lineTo(x + s * .8, y + s * .84); ctx.moveTo(x + s * .56, y + s * .88); ctx.lineTo(x + s * .8, y + s * .76); ctx.stroke();
  ctx.restore();
  ctx.strokeStyle = "rgba(230,225,255,.55)"; ctx.lineWidth = Math.max(.7, s * .012);
  const wx = x + s * .86, wy = y + s * .44;
  ctx.beginPath();
  for (let j = 0; j < 4; j++) { const a = Math.PI / 2 + j * Math.PI / 6; ctx.moveTo(wx, wy); ctx.lineTo(wx + Math.cos(a) * s * .2, wy + Math.sin(a) * s * .2); }
  for (const rr of [.08, .15]) { ctx.moveTo(wx, wy + s * rr); ctx.quadraticCurveTo(wx - s * rr * .5, wy + s * rr * .5, wx - s * rr, wy); }
  ctx.stroke();
}
// A mystery house on the Haunted Mansion's streets: lit or haunted, nobody
// knows until the run. A dark house with a ? glowing in its window.
function drawMystery(ctx, r, c, cell, now) {
  const x = c * cell, y = r * cell, s = cell, k = CALM ? .8 : .6 + .4 * Math.sin(now / 500 + r + c);
  ctx.fillStyle = "rgba(10,6,24,.4)"; ctx.fillRect(x + s * .1, y + s * .9, s * .84, s * .08);
  ctx.fillStyle = "#3f3550"; ctx.fillRect(x + s * .14, y + s * .44, s * .72, s * .5);
  ctx.fillStyle = "#1e1630"; ctx.beginPath(); ctx.moveTo(x + s * .04, y + s * .48); ctx.lineTo(x + s * .5, y + s * .1); ctx.lineTo(x + s * .96, y + s * .48); ctx.fill();
  ctx.fillStyle = "#24193a"; ctx.fillRect(x + s * .41, y + s * .7, s * .18, s * .24);
  ctx.fillStyle = `rgba(185,163,255,${k})`; ctx.shadowColor = "#b9a3ff"; ctx.shadowBlur = s * .3 * k;
  ctx.font = `900 ${Math.round(s * .3)}px system-ui, sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText("?", x + s * .5, y + s * .58); ctx.shadowBlur = 0;
}
function drawCandy(ctx, r, c, cell, now) {
  const bob = CALM ? 0 : Math.sin(now / 380 + r * 2 + c) * cell * .04;
  ctx.fillStyle = "rgba(255,138,31,.16)"; ctx.beginPath(); ctx.arc((c + .5) * cell, (r + .5) * cell, cell * .34, 0, 7); ctx.fill();
  drawSweet(ctx, (c + .5) * cell, (r + .5) * cell + bob, cell * .62, -.4 + hash(r, c, 7) * .8,
            ["#ff4f7a", "#ffe14d", "#7ff07a", "#b07aff", "#ff8a1f"][Math.floor(hash(r, c, 8) * 5)]);
}
// The golden pumpkin: Halloween night's bonus pick-up (a crystal elsewhere).
function drawGoldPumpkin(ctx, r, c, cell, now) {
  const bob = CALM ? 0 : Math.sin(now / 350 + r * 2 + c) * cell * .05;
  const cx = (c + .5) * cell, cy = (r + .5) * cell + bob, z = cell * .3;
  ctx.shadowColor = "#ffd36b"; ctx.shadowBlur = cell * .5;
  ctx.fillStyle = "#ffc93c"; ctx.beginPath(); ctx.ellipse(cx, cy, z * 1.2, z, 0, 0, 7); ctx.fill(); ctx.shadowBlur = 0;
  ctx.strokeStyle = "rgba(170,110,0,.6)"; ctx.lineWidth = Math.max(1, cell / 30);
  ctx.beginPath(); ctx.ellipse(cx, cy, z * .45, z, 0, 0, 7); ctx.stroke();
  ctx.fillStyle = "#3f8a2e"; ctx.fillRect(cx - z * .1, cy - z * 1.25, z * .2, z * .35);
  ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.beginPath(); ctx.ellipse(cx - z * .5, cy - z * .4, z * .2, z * .12, -.5, 0, 7); ctx.fill();
}
// The Haunted Mansion itself, filling the rock between H10's streets (rows 3
// to 7, columns 1 to 11): towers, a crooked roof, windows flickering green
// and orange, and now and then a ghost at one of them.
function drawMansion(ctx, cell, now) {
  const X = c => c * cell, Y = r => r * cell, t = CALM ? 0 : now;
  ctx.save();
  ctx.fillStyle = "rgba(6,4,12,.55)"; ctx.fillRect(X(1.3), Y(7.85), X(10), cell * .12);
  const body = "#1a1426", roof = "#0e0a16", trim = "rgba(185,140,255,.35)";
  // The wings and the middle, then the towers, then their roofs.
  ctx.fillStyle = body;
  ctx.fillRect(X(1.5), Y(5.2), X(3.6), Y(2.7)); ctx.fillRect(X(7.9), Y(5.2), X(3.6), Y(2.7));
  ctx.fillRect(X(4.6), Y(4.2), X(3.8), Y(3.7));
  ctx.fillRect(X(2.2), Y(4.1), X(1.2), Y(1.2)); ctx.fillRect(X(9.6), Y(4.3), X(1.1), Y(1));
  ctx.fillStyle = roof;
  const peak = (x0, x1, base, top, lean = 0) => { ctx.beginPath(); ctx.moveTo(X(x0), Y(base)); ctx.lineTo(X((x0 + x1) / 2 + lean), Y(top)); ctx.lineTo(X(x1), Y(base)); ctx.fill(); };
  peak(1.3, 5.3, 5.3, 4.4); peak(7.7, 11.7, 5.3, 4.5, .2); peak(4.4, 8.6, 4.3, 3.15);
  peak(2.0, 3.6, 4.15, 3.1, -.15); peak(9.4, 10.9, 4.35, 3.4, .2);
  ctx.strokeStyle = trim; ctx.lineWidth = Math.max(1, cell * .04);
  ctx.strokeRect(X(1.5), Y(5.2), X(3.6), Y(2.7)); ctx.strokeRect(X(7.9), Y(5.2), X(3.6), Y(2.7)); ctx.strokeRect(X(4.6), Y(4.2), X(3.8), Y(3.7));
  // Windows, each flickering in its own time.
  const spots = [[2.1, 5.7], [3.0, 5.7], [4.0, 5.7], [2.1, 6.7], [4.0, 6.7], [8.5, 5.7], [9.5, 5.7], [10.5, 5.7], [8.5, 6.7], [10.5, 6.7],
                 [5.1, 4.8], [6.2, 4.8], [7.3, 4.8], [5.1, 5.9], [7.3, 5.9], [2.55, 4.4], [10.0, 4.6]];
  spots.forEach(([cx, cy], k) => {
    const on = CALM ? k % 3 !== 0 : Math.sin(t / (700 + k * 90) + k * 1.7) > -.3;
    const green = k % 4 === 1;
    ctx.fillStyle = on ? (green ? "rgba(156,255,107,.85)" : "rgba(255,190,90,.85)") : "#0b0812";
    if (on) { ctx.shadowColor = green ? "#9cff6b" : "#ffb547"; ctx.shadowBlur = cell * .4; }
    ctx.beginPath(); ctx.moveTo(X(cx), Y(cy + .55)); ctx.lineTo(X(cx), Y(cy + .15)); ctx.arc(X(cx + .25), Y(cy + .15), cell * .25, Math.PI, 0); ctx.lineTo(X(cx + .5), Y(cy + .55)); ctx.fill();
    ctx.shadowBlur = 0;
  });
  // The front door, arched, and its steps.
  ctx.fillStyle = "#3a2410"; ctx.beginPath(); ctx.moveTo(X(5.95), Y(7.85)); ctx.lineTo(X(5.95), Y(7.0)); ctx.arc(X(6.5), Y(7.0), cell * .55, Math.PI, 0); ctx.lineTo(X(7.05), Y(7.85)); ctx.fill();
  ctx.fillStyle = "#ffd36b"; ctx.beginPath(); ctx.arc(X(6.85), Y(7.4), cell * .06, 0, 7); ctx.fill();
  // Now and then a ghost drifts past a window of the middle tower.
  if (!CALM) {
    const u = (now % 9000) / 9000;
    if (u < .3) drawSpook(ctx, X(5.1 + u / .3 * 2.6), Y(5.05), cell * .7, now, .65 * Math.sin(u / .3 * Math.PI));
  }
  ctx.restore();
}
// The houses visited by frame i.
function knockedBy(i) {
  return new Set(scene.frames.slice(0, i + 1).filter(f => f.kn && f.kn[2] >= 0).map(f => f.kn[0] + "," + f.kn[1]));
}
// Everything Halloween on one square of the map, under the rover.
function drawSpookySquare(ctx, ch, r, c, cell, now, knocked, picked) {
  if (ch === "h") drawHouse(ctx, r, c, cell, now, knocked.has(r + "," + c));
  else if (ch === "z") drawHaunted(ctx, r, c, cell, now);
  else if (ch === "m") drawMystery(ctx, r, c, cell, now);
  else if (ch === "c" && !picked.has(r + "," + c)) drawCandy(ctx, r, c, cell, now);
}
// The ghosts, over everything else on the map.
function drawGhosts(ctx, i, cell, now) {
  if (!scene.ghosts) return;
  const t = spookyTime(i, now);
  for (const g of scene.ghosts) {
    const [r, c] = ghostSpot(g, t);
    drawSpook(ctx, (c + .5) * cell, (r + .45) * cell, cell * .95, now);
  }
}
// A BOO: a big ghost rises out of where it came from, and the rover jumps.
function drawBoo(ctx, cell, now) {
  const b = scene.boo;
  if (!b) return;
  const u = (now - b.at) / 1500;
  if (u > 1) { scene.boo = null; return; }
  const grow = CALM ? 1 : Math.min(1, u * 3), fade = u < .7 ? 1 : 1 - (u - .7) / .3;
  drawSpook(ctx, (b.c + .5) * cell, (b.r + .2 - grow * .6) * cell, cell * (1 + grow * 1.4), now, .95 * fade, "boo");
  ctx.save(); ctx.globalAlpha = fade;
  ctx.font = `900 ${Math.round(cell * (.6 + grow * .5))}px system-ui, sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.lineWidth = 6; ctx.strokeStyle = "rgba(12,9,26,.9)"; ctx.fillStyle = "#b9ff8c";
  const bx = (b.c + .5) * cell, by = (b.r - 1.2 * grow) * cell;
  ctx.strokeText("BOO!", bx, by); ctx.fillText("BOO!", bx, by);
  ctx.restore();
}
// The sky over Halloween night, behind the map: a big moon, stars, and now
// and then a bat flapping past.
function drawNightSky(ctx, w, h, now) {
  const mx = w - 70, my = 70, glow = ctx.createRadialGradient(mx, my, 10, mx, my, 120);
  glow.addColorStop(0, "rgba(255,230,170,.35)"); glow.addColorStop(1, "rgba(255,230,170,0)");
  ctx.fillStyle = glow; ctx.fillRect(mx - 120, my - 120, 240, 240);
  ctx.fillStyle = "#fff2cc"; ctx.beginPath(); ctx.arc(mx, my, 30, 0, 7); ctx.fill();
  ctx.fillStyle = "rgba(220,200,150,.5)";
  for (const [dx, dy, z] of [[-9, -6, 6], [8, 9, 4], [5, -12, 3]]) { ctx.beginPath(); ctx.arc(mx + dx, my + dy, z, 0, 7); ctx.fill(); }
  ctx.fillStyle = "rgba(255,240,210,.7)";
  for (let k = 0; k < 40; k++) {
    const tw = CALM ? .7 : .4 + .6 * Math.abs(Math.sin(now / 900 + k));
    ctx.globalAlpha = tw; ctx.fillRect(hash(k, 1, 90) * w, hash(k, 2, 90) * h, 1.6, 1.6);
  }
  ctx.globalAlpha = 1;
  if (CALM) return;
  for (let k = 0; k < 3; k++) {   // bats crossing the sky, each on a loop of its own
    const loop = 9000 + k * 3700, u = ((now + k * 4100) % loop) / loop;
    if (u > .45) continue;
    const bx = -40 + u / .45 * (w + 80), by = 40 + k * 60 + Math.sin(now / 260 + k) * 12, flap = Math.sin(now / 70 + k) * 6;
    ctx.fillStyle = "rgba(20,10,30,.85)";
    ctx.beginPath(); ctx.moveTo(bx, by);
    ctx.quadraticCurveTo(bx - 9, by - 8 - flap, bx - 18, by - 2 + flap); ctx.quadraticCurveTo(bx - 10, by, bx, by + 4);
    ctx.quadraticCurveTo(bx + 10, by, bx + 18, by - 2 + flap); ctx.quadraticCurveTo(bx + 9, by - 8 - flap, bx, by); ctx.fill();
  }
}
// Mist drifting slowly over the map, and the light falling off at its edges.
function drawMist(ctx, worldW, worldH, cell, now) {
  const t = CALM ? 0 : now / 14000;
  for (let k = 0; k < 5; k++) {
    const x = ((hash(k, 3, 91) + t * (k % 2 ? 1 : -1)) % 1 + 1) % 1 * worldW, y = hash(k, 4, 91) * worldH;
    const grad = ctx.createRadialGradient(x, y, 0, x, y, cell * 3);
    grad.addColorStop(0, "rgba(200,190,255,.10)"); grad.addColorStop(1, "rgba(200,190,255,0)");
    ctx.fillStyle = grad; ctx.fillRect(x - cell * 3, y - cell * 3, cell * 6, cell * 6);
  }
}
// What happened on a Halloween step of the replay: a knock, candy, a BOO.
function spookyStep(f, p) {
  if (f.kn) {
    const [r, c, n] = f.kn;
    SFX.play("knock");
    if (n >= 0) {
      setTimeout(() => SFX.play("treat"), 260);
      pop({r, c}, `+${n} 🍬`, "#ffd36b"); burst(r, c, "gift", 14);
      if (!scene.run || scene.run.end !== "goal" || f.e !== "goal") say(pick(["Trick or treat!", "Happy Halloween!", "Candy!", "Yum!", "Thank you!"]));
    }
  }
  if (f.e === "spooked") {
    SFX.play("boo"); shake();
    scene.boo = {at: performance.now(), r: f.kn ? f.kn[0] : f.r, c: f.kn ? f.kn[1] : f.c};
    say(pick(["AAAAH!", "Eeek!", "Nope nope nope!", "Run!!"]));
  }
  if (f.p && p && f.cy > (p.cy || 0) && !f.kn) { combo(f, "🍬"); burst(f.r, f.c, "sparkle", 10); }
}

// ---- The event: the invitation, the candy chip and the candy road ------------------

function halloweenSeenKey() { return `planetHalloweenSeen:${me}`; }
// The chip at the top: the candy in the bag. Press it for the candy road.
function renderCandyChip() {
  const h = state && state.halloween, chip = $("candyButton");
  chip.hidden = !h;
  if (!h) return;
  const next = h.road.find(i => !i.open);
  $("candyCount").textContent = h.candy;
  chip.title = `Halloween night: ${h.candy} candy in your bag` + (next ? `. ${next.candy - h.candy} more unlocks ${next.name}.` : ". Every candy prize is yours!");
}
function roadThumbs(road) {
  return road.map(i => `<div class="road-item${i.open ? " got" : ""} r-${i.rarity}" title="${esc(i.name)}: ${i.open ? "unlocked!" : `${i.candy} candy`}">
    <canvas data-slot="${i.slot}" data-key="${i.key}"></canvas><b>${esc(i.name)}</b><small>${i.open ? "✓ yours" : `🍬 ${i.candy}`}</small></div>`).join("");
}
// The candy road: a bar of the candy in the bag, with every prize along it.
function openCandyRoad() {
  const h = state.halloween;
  if (!h) return;
  closePops();
  const top = h.road[h.road.length - 1].candy, next = h.road.find(i => !i.open);
  $("roadBag").innerHTML = `<b>${h.candy}</b> 🍬 in your bag` + (next ? ` · <b>${next.candy - h.candy}</b> more for the ${esc(next.name)}` : " · every prize unlocked! 🎉");
  $("roadFill").style.width = `${Math.min(100, h.candy / top * 100)}%`;
  $("roadMarks").innerHTML = h.road.map(i => `<i class="${i.open ? "got" : ""}" style="left:${i.candy / top * 100}%" title="${esc(i.name)}: ${i.candy}"></i>`).join("");
  $("roadItems").innerHTML = roadThumbs(h.road);
  $("roadItems").querySelectorAll("canvas").forEach(cv => thumb(cv, cv.dataset.slot, cv.dataset.key));
  const badges = state.badges.filter(b => b.limited);
  $("roadBadges").innerHTML = badges.map(b => `<span class="rb${b.earned ? " got" : ""}" title="${esc(b.how)}">${b.icon} ${esc(b.name)}${b.earned ? " ✓" : ""}<small>${esc(b.how)}</small></span>`).join("");
  $("roadStats").textContent = `★ ${h.stars} / ${h.max_stars} Halloween stars · ${h.done} of ${h.sites} levels done`;
  $("roadPlay").textContent = h.done === h.sites ? "🎃 Play again" : `🎃 Play ${h.next.toUpperCase()}`;
  $("candyRoad").hidden = false;
  $("roadPlay").focus();
}
function closeCandyRoad() { $("candyRoad").hidden = true; }
// The invitation, the first time Halloween night opens for this student
// (on another laptop, a student who has already started gets a toast instead).
function welcomeHalloween() {
  const h = state && state.halloween;
  if (!h || recall(halloweenSeenKey()) === "1") return;
  if (h.done || h.candy) {
    store(halloweenSeenKey(), "1");
    toast("🎃", "Halloween night is still on!", `${h.candy} 🍬 in your bag. Press the 🎃 at the top for the candy road.`);
  } else showInvite();
}
function showInvite() {
  const h = state.halloween;
  if (!h) return;
  store(halloweenSeenKey(), "1");
  $("inviteRoad").innerHTML = roadThumbs(h.road.slice(0, 5));
  $("inviteRoad").querySelectorAll("canvas").forEach(cv => thumb(cv, cv.dataset.slot, cv.dataset.key));
  $("invite").hidden = false;
  SFX.play("spooky");
  $("inviteGo").focus();
}
function closeInvite() { $("invite").hidden = true; }
function playHalloween() {
  closeInvite(); closeCandyRoad();
  const h = state.halloween;
  if (h) openSite(h.next);
}
// A student page checks now and then whether the teacher has opened (or
// closed) Halloween night for it, so an invitation arrives without a reload.
async function pingHalloween() {
  if (!me || !state || document.hidden || busy) return;
  let data;
  try { data = await get(`/planet/ping?id=${encodeURIComponent(me)}`); } catch (_) { return; }
  if (data.halloween === !!state.halloween) return;
  let fresh;
  try { fresh = await get(`/planet/state?id=${encodeURIComponent(me)}`); } catch (_) { return; }
  if (!fresh.you) return;
  useState(fresh);
  if (fresh.halloween) {
    if (recall(halloweenSeenKey()) !== "1") welcomeHalloween();
    else toast("🎃", "Halloween night is open!", "Press the 🎃 at the top for the candy road.");
  } else if (site && spooky(site.zoneKey)) {
    toast("🌙", "Halloween night is over", "Your candy prizes are yours to keep. Back to the planet!");
    openSite(fresh.current);
  }
}
// After a Halloween run: the candy news for the celebration card.
function candyNote(c) {
  if (!c) return "";
  const gained = c.total - c.before;
  if (c.dropped) return `<span class="candy-note dropped">😱 The rover dropped its ${c.run} candy running away!</span>`;
  return `<span class="candy-note">🍬 ${gained > 0 ? `+${gained} candy in your bag` : `${c.run} candy (your best here: ${c.best})`} · ${c.total} in all${c.next ? "" : " · every candy prize is yours! 🎉"}</span>`;
}
// The next candy prize under the celebration card, its bar filling up with
// this run's candy. Returns what fills it, like showNextUnlock.
function showNextCandy(c) {
  const box = $("celeNext"), road = (state.halloween || {}).road || [];
  const next = road.find(i => i.candy > c.total);
  box.hidden = !next;
  if (!next) return null;
  const from = Math.max(0, ...road.filter(i => i.candy <= c.total).map(i => i.candy));
  const pct = n => Math.max(0, Math.min(100, (n - from) / (next.candy - from) * 100));
  box.innerHTML = `<span>${SLOT_ICON[next.slot] || "🎃"}</span><span>Next: <b>${esc(next.name)}</b></span>`
    + `<span class="nu-bar"><i class="nu-fill candy-fill" style="width:${pct(c.before)}%"></i></span><small>${next.candy - c.total} 🍬 to go</small>`;
  box.title = `${next.candy - c.total} more candy unlocks the ${next.name}, Halloween only`;
  return () => { box.querySelector(".nu-fill").style.width = pct(c.total) + "%"; };
}
