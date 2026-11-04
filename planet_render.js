// Strange Planet's rover, drawn the same on the student page and the class
// screen: its paints, toppers and the shapes they're made of. Each page
// defines CALM (true when motion should stay still) before drawing.

function hash(a, b, k = 0) {
  let h = (a * 374761393 + b * 668265263 + k * 2147483647) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

// Seen from above, facing +x: six wheels, a painted body with a solar deck at
// the back, and a camera mast at the front with a mint lens. The student's
// garage picks the paint and what sits on top.
function bodyPaint(ctx, s, p, now) {
  if (typeof p === "string") return p;
  // Before p.fill: every array has a .fill of its own.
  if (Array.isArray(p)) {
    const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
    p.forEach((c, i) => grad.addColorStop(i / (p.length - 1), c));
    return grad;
  }
  if (p.fill) return p.fill(ctx, s, now);
  return p.base;
}
// Square pixels across the body, ten along it: `pick` colours each one.
function pixelArt(ctx, s, pick) {
  const n = 10, w = .62 * s / n, rows = Math.ceil(.44 * s / w);
  for (let j = 0; j < rows; j++) for (let i = 0; i < n; i++) {
    ctx.fillStyle = pick(i, j, n, rows);
    ctx.fillRect(-.32 * s + i * w, -.22 * s + j * w, w + .5, w + .5);
  }
}
function drawRover(ctx, x, y, s, angle, alpha, gear, now = performance.now()) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(x, y); ctx.rotate(angle);
  if (GLOWS[gear.glow]) GLOWS[gear.glow](ctx, s, now);
  ctx.fillStyle = "rgba(10,4,16,.38)";
  ctx.beginPath(); ctx.ellipse(s * .05, s * .07, s * .42, s * .36, 0, 0, 7); ctx.fill();
  (WHEELS[gear.wheels] || WHEELS.std)(ctx, s, now);
  const paint = PAINTS[gear.paint] || PAINTS.bone;
  ctx.fillStyle = bodyPaint(ctx, s, paint, now);
  roundRect(ctx, -.32 * s, -.22 * s, .62 * s, .44 * s, .08 * s); ctx.fill();
  if (paint.draw) {
    ctx.save(); ctx.clip(); paint.draw(ctx, s, now, gear); ctx.restore();
    roundRect(ctx, -.32 * s, -.22 * s, .62 * s, .44 * s, .08 * s);
  }
  ctx.strokeStyle = "#6e6290"; ctx.lineWidth = Math.max(1, s * .03); ctx.stroke();
  if (!paint.swatch) {
    ctx.fillStyle = "#3f5f96";
    roundRect(ctx, -.29 * s, -.18 * s, .3 * s, .36 * s, .03 * s); ctx.fill();
    ctx.strokeStyle = "rgba(200,225,255,.45)"; ctx.lineWidth = Math.max(1, s * .015);
    ctx.beginPath(); ctx.moveTo(-.14 * s, -.18 * s); ctx.lineTo(-.14 * s, .18 * s); ctx.moveTo(-.29 * s, 0); ctx.lineTo(.01 * s, 0); ctx.stroke();
  }
  drawTopper(ctx, s, gear.topper, now);
  ctx.fillStyle = "#e6dccb"; ctx.strokeStyle = "#6e6290"; ctx.lineWidth = Math.max(1, s * .03);
  ctx.beginPath(); ctx.arc(.15 * s, 0, s * .1, 0, 7); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#231d3f"; roundRect(ctx, .18 * s, -.06 * s, .1 * s, .12 * s, .02 * s); ctx.fill();
  ctx.fillStyle = "#8cf2c6"; ctx.beginPath(); ctx.arc(.25 * s, 0, s * .025, 0, 7); ctx.fill();
  const set = fullSet(gear);
  if (set) { ctx.rotate(-angle); setSparkle(ctx, s, set, now); }
  ctx.restore();
}
function drawTopper(ctx, s, topper, now) {
  ctx.lineWidth = Math.max(1, s * .025);
  if (topper === "flag") {
    ctx.strokeStyle = "#e6dccb"; ctx.beginPath(); ctx.moveTo(-.05 * s, -.12 * s); ctx.lineTo(-.05 * s, -.46 * s); ctx.stroke();
    ctx.fillStyle = "#ff8a7a"; ctx.beginPath(); ctx.moveTo(-.05 * s, -.46 * s); ctx.lineTo(-.3 * s, -.4 * s); ctx.lineTo(-.05 * s, -.33 * s); ctx.fill();
  } else if (topper === "dish") {
    ctx.fillStyle = "#e6dccb"; ctx.strokeStyle = "#6e6290";
    ctx.beginPath(); ctx.arc(-.06 * s, .08 * s, s * .12, 0, 7); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.arc(-.06 * s, .08 * s, s * .04, 0, 7); ctx.stroke();
  } else if (topper === "light") {
    const k = CALM ? 1 : .6 + .4 * Math.sin(now / 160);
    ctx.fillStyle = `rgba(255,181,71,${k})`; ctx.shadowColor = "#ffb547"; ctx.shadowBlur = s * .4 * k;
    ctx.beginPath(); ctx.arc(-.06 * s, 0, s * .07, 0, 7); ctx.fill(); ctx.shadowBlur = 0;
  } else if (topper === "crown") {
    ctx.fillStyle = "#ffd36b"; ctx.strokeStyle = "#a07a20";
    ctx.beginPath(); ctx.moveTo(-.2 * s, .1 * s);
    for (const [px, py] of [[-.2, -.12], [-.12, -.02], [-.06, -.16], [0, -.02], [.06, -.12], [.06, .1]]) ctx.lineTo(px * s, py * s);
    ctx.closePath(); ctx.fill(); ctx.stroke();
  } else if (topper === "party") {   // a striped cone with a pom-pom
    ctx.beginPath(); ctx.moveTo(-.2 * s, .06 * s); ctx.lineTo(.04 * s, .06 * s); ctx.lineTo(-.08 * s, -.4 * s); ctx.closePath();
    ctx.fillStyle = "#ff6fae"; ctx.fill();
    ctx.save(); ctx.clip(); ctx.fillStyle = "#ffd36b";
    for (const y of [-.3, -.17, -.04]) ctx.fillRect(-.24 * s, y * s, .32 * s, .055 * s);
    ctx.restore();
    ctx.fillStyle = "#8fc8ff"; ctx.beginPath(); ctx.arc(-.08 * s, -.41 * s, s * .045, 0, 7); ctx.fill();
  } else if (topper === "cat") {   // two ears behind the camera head
    for (const x of [.08, .22]) {
      ctx.fillStyle = "#3a3048"; ctx.beginPath(); ctx.moveTo((x - .06) * s, -.04 * s); ctx.lineTo(x * s, -.22 * s); ctx.lineTo((x + .06) * s, -.04 * s); ctx.fill();
      ctx.fillStyle = "#ff9ec4"; ctx.beginPath(); ctx.moveTo((x - .03) * s, -.06 * s); ctx.lineTo(x * s, -.16 * s); ctx.lineTo((x + .03) * s, -.06 * s); ctx.fill();
    }
  } else if (topper === "wizard") {   // a tall starry hat on a brim
    ctx.fillStyle = "#4b2f8f"; ctx.beginPath(); ctx.ellipse(-.07 * s, .06 * s, .2 * s, .05 * s, 0, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.moveTo(-.2 * s, .06 * s); ctx.lineTo(.06 * s, .06 * s); ctx.quadraticCurveTo(-.06 * s, -.2 * s, -.2 * s, -.5 * s);
    ctx.quadraticCurveTo(-.12 * s, -.2 * s, -.2 * s, .06 * s); ctx.fillStyle = "#6a46c8"; ctx.fill();
    ctx.fillStyle = "#ffd36b"; ctx.font = `${Math.round(s * .1)}px system-ui, sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("★", -.08 * s, -.04 * s); ctx.fillText("★", -.14 * s, -.22 * s);
  } else if (topper === "shark") {   // a fin, like it's swimming through the ground
    ctx.fillStyle = "#7d93a8"; ctx.strokeStyle = "#4a5a6c";
    ctx.beginPath(); ctx.moveTo(-.26 * s, .06 * s); ctx.quadraticCurveTo(-.12 * s, -.08 * s, -.02 * s, -.4 * s);
    ctx.quadraticCurveTo(-.01 * s, -.12 * s, .06 * s, .06 * s); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,.4)"; ctx.beginPath(); ctx.moveTo(-.15 * s, .02 * s); ctx.quadraticCurveTo(-.07 * s, -.1 * s, -.03 * s, -.3 * s); ctx.stroke();
  } else if (topper === "pumpkin") {   // a jack-o'-lantern
    ctx.fillStyle = "#3f8a2e"; ctx.fillRect(-.15 * s, -.22 * s, .05 * s, .08 * s);
    ctx.fillStyle = "#ff8a1f"; ctx.strokeStyle = "#c25a0c";
    ctx.beginPath(); ctx.ellipse(-.12 * s, -.02 * s, .18 * s, .14 * s, 0, 0, 7); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(-.12 * s, -.02 * s, .07 * s, .14 * s, 0, 0, 7); ctx.stroke();
    ctx.fillStyle = "#2a1408";
    for (const x of [-.19, -.05]) { ctx.beginPath(); ctx.moveTo((x - .03) * s, -.03 * s); ctx.lineTo(x * s, -.08 * s); ctx.lineTo((x + .03) * s, -.03 * s); ctx.fill(); }
    ctx.beginPath(); ctx.moveTo(-.22 * s, .03 * s);
    for (let k = 1; k <= 6; k++) ctx.lineTo((-.22 + k * .033) * s, (k % 2 ? .07 : .03) * s);
    ctx.lineTo(-.02 * s, .09 * s); ctx.lineTo(-.22 * s, .09 * s); ctx.fill();
  } else if (topper === "propeller") {   // a striped cap with a spinning propeller
    for (const [k, color] of [[0, "#ff5a5a"], [1, "#ffd34d"], [2, "#4dc3ff"]]) {
      ctx.fillStyle = color; ctx.beginPath(); ctx.moveTo(-.12 * s, .04 * s);
      ctx.arc(-.12 * s, .04 * s, .15 * s, Math.PI + k * Math.PI / 3, Math.PI + (k + 1) * Math.PI / 3); ctx.fill();
    }
    ctx.strokeStyle = "#6e6290"; ctx.beginPath(); ctx.moveTo(-.12 * s, -.11 * s); ctx.lineTo(-.12 * s, -.18 * s); ctx.stroke();
    const spin = CALM ? .8 : Math.cos(now / 50);
    for (const side of [-1, 1]) {
      ctx.fillStyle = side * spin > 0 ? "#ff5a5a" : "#4dc3ff";
      ctx.beginPath(); ctx.ellipse((-.12 + side * spin * .1) * s, -.19 * s, Math.max(.01, Math.abs(spin) * .1) * s, .03 * s, 0, 0, 7); ctx.fill();
    }
  } else if (topper === "sword") {   // a pixel sword across the deck
    const art = ["......cw", ".....cwc", "....cwc.", "b..cwc..", ".bcwc...", "..bb....", ".hb.b...", "h......."];
    const px = .05 * s, colors = {c: "#4ee6e0", w: "#c8fffb", b: "#2a2a35", h: "#7a5230"};
    art.forEach((row, j) => [...row].forEach((ch, i) => {
      if (colors[ch]) { ctx.fillStyle = colors[ch]; ctx.fillRect(-.32 * s + i * px, -.2 * s + j * px, px + .5, px + .5); }
    }));
  } else if (topper === "headphones") {   // a band over the camera head, a cup each side
    ctx.strokeStyle = "#3a3048"; ctx.lineWidth = s * .05;
    ctx.beginPath(); ctx.arc(.15 * s, 0, s * .15, Math.PI * .1, Math.PI * .9, true); ctx.stroke();
    for (const y of [-.15, .15]) { ctx.fillStyle = "#ff6fae"; roundRect(ctx, .09 * s, (y - .05) * s, .12 * s, .1 * s, .03 * s); ctx.fill(); }
  } else if (topper === "halo") {   // a golden ring floating above
    const bob = CALM ? 0 : Math.sin(now / 400) * s * .02;
    ctx.strokeStyle = "#ffd36b"; ctx.lineWidth = s * .04; ctx.shadowColor = "#ffd36b"; ctx.shadowBlur = s * .25;
    ctx.beginPath(); ctx.ellipse(-.02 * s, bob, .2 * s, .08 * s, 0, 0, 7); ctx.stroke(); ctx.shadowBlur = 0;
  } else if (topper === "rocket") {   // a little rocket on the deck, flame and all
    const flick = CALM ? 1 : .8 + .3 * Math.sin(now / 60);
    ctx.fillStyle = "#ff9d3c"; ctx.beginPath(); ctx.moveTo(-.28 * s, -.05 * s); ctx.lineTo((-.28 - .12 * flick) * s, 0); ctx.lineTo(-.28 * s, .05 * s); ctx.fill();
    ctx.fillStyle = "#f2eadb"; ctx.beginPath(); ctx.moveTo(-.28 * s, -.06 * s); ctx.lineTo(.0 * s, -.06 * s); ctx.quadraticCurveTo(.1 * s, 0, 0, .06 * s); ctx.lineTo(-.28 * s, .06 * s); ctx.fill();
    ctx.fillStyle = "#ff5a5a"; ctx.beginPath(); ctx.moveTo(-.28 * s, -.06 * s); ctx.lineTo(-.34 * s, -.13 * s); ctx.lineTo(-.2 * s, -.06 * s); ctx.fill();
    ctx.beginPath(); ctx.moveTo(-.28 * s, .06 * s); ctx.lineTo(-.34 * s, .13 * s); ctx.lineTo(-.2 * s, .06 * s); ctx.fill();
    ctx.fillStyle = "#8fc8ff"; ctx.beginPath(); ctx.arc(-.06 * s, 0, s * .03, 0, 7); ctx.fill();
  } else if (topper === "medal") {   // a gold medal on a ribbon, across the deck
    ctx.fillStyle = "#4dc3ff"; ctx.beginPath(); ctx.moveTo(-.3 * s, -.08 * s); ctx.lineTo(-.14 * s, 0); ctx.lineTo(-.3 * s, .08 * s); ctx.fill();
    ctx.fillStyle = "#ff5a5a"; ctx.beginPath(); ctx.moveTo(-.3 * s, -.02 * s); ctx.lineTo(-.18 * s, 0); ctx.lineTo(-.3 * s, .02 * s); ctx.fill();
    ctx.fillStyle = "#ffd36b"; ctx.strokeStyle = "#a07a20"; ctx.shadowColor = "#ffd36b"; ctx.shadowBlur = s * .15;
    ctx.beginPath(); ctx.arc(-.08 * s, 0, s * .09, 0, 7); ctx.fill(); ctx.shadowBlur = 0; ctx.stroke();
    ctx.fillStyle = "#a07a20"; ctx.font = `900 ${Math.round(s * .1)}px system-ui, sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("★", -.08 * s, .005 * s);
  } else if (topper === "ufo") {   // a saucer hovering over the deck, lights blinking
    const bob = CALM ? 0 : Math.sin(now / 300) * s * .02;
    ctx.fillStyle = "rgba(143,227,255,.7)"; ctx.beginPath(); ctx.ellipse(-.06 * s, bob - .03 * s, .09 * s, .08 * s, 0, Math.PI, 0); ctx.fill();
    ctx.fillStyle = "#9aa3b5"; ctx.beginPath(); ctx.ellipse(-.06 * s, bob, .22 * s, .07 * s, 0, 0, 7); ctx.fill();
    for (let k = 0; k < 5; k++) {
      const on = CALM || Math.floor(now / 200 + k) % 2;
      ctx.fillStyle = on ? ["#ff6fae", "#ffd36b", "#7ff0d6"][k % 3] : "#5a6070";
      ctx.beginPath(); ctx.arc((-.22 + k * .08) * s, bob + .01 * s, s * .02, 0, 7); ctx.fill();
    }
  } else if (topper === "ninjaband") {   // a knot behind the camera head, two tails fluttering back
    ctx.strokeStyle = "#e3262f"; ctx.lineWidth = s * .055; ctx.lineCap = "round";
    for (const side of [-1, 1]) {
      ctx.beginPath(); ctx.moveTo(.04 * s, side * .03 * s);
      for (let j = 1; j <= 5; j++) {
        const wave = CALM ? .4 : Math.sin(now / 90 + j * 1.1 + side);
        ctx.lineTo((.04 - j * .08) * s, (side * (.04 + j * .012) + wave * .015 * j) * s);
      }
      ctx.stroke();
    }
    ctx.fillStyle = "#b5141c"; ctx.beginPath(); ctx.arc(.04 * s, 0, s * .05, 0, 7); ctx.fill();
  } else if (topper === "police") {   // a light bar, red and blue taking turns
    const red = CALM || Math.floor(now / 220) % 2 === 0, blue = CALM || !red;
    ctx.fillStyle = "#2a2a35"; roundRect(ctx, -.12 * s, -.2 * s, .1 * s, .4 * s, .03 * s); ctx.fill();
    for (const [y, color, dim, on] of [[-.1, "#ff2e3d", "#5a1a20", red], [.1, "#2e7dff", "#1a2a5a", blue]]) {
      ctx.fillStyle = on ? color : dim; ctx.shadowColor = color; ctx.shadowBlur = on ? s * .45 : 0;
      roundRect(ctx, -.11 * s, (y - .08) * s, .08 * s, .16 * s, .03 * s); ctx.fill();
    }
    ctx.shadowBlur = 0;
  } else if (topper === "unicorn") {   // a gold spiral horn out the front, a rainbow mane down the back
    ["#ff5a7a", "#ffb84d", "#ffe56b", "#7ff07a", "#5ad1ff", "#b07aff"].forEach((color, k) => {
      ctx.fillStyle = color; ctx.beginPath(); ctx.ellipse((-.28 + k * .055) * s, (k % 2 ? .03 : -.03) * s, .06 * s, .045 * s, 0, 0, 7); ctx.fill();
    });
    ctx.fillStyle = "#ffd36b"; ctx.strokeStyle = "#c79a2a"; ctx.lineWidth = Math.max(1, s * .015);
    ctx.beginPath(); ctx.moveTo(.18 * s, -.06 * s); ctx.lineTo(.52 * s, 0); ctx.lineTo(.18 * s, .06 * s); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.beginPath();
    for (const x of [.27, .35, .43]) { const w = (.52 - x) / .34 * .06; ctx.moveTo(x * s, -w * s); ctx.lineTo((x + .03) * s, w * s); }
    ctx.stroke();
  } else if (topper === "wings") {   // feathered wings out the sides, flapping
    const flap = CALM ? 1 : .75 + .25 * Math.sin(now / 130);
    for (const side of [-1, 1]) {
      ctx.save(); ctx.translate(-.06 * s, side * .2 * s); ctx.scale(1, side * flap);
      ctx.fillStyle = "#ffffff"; ctx.strokeStyle = "#c9d6ee"; ctx.lineWidth = Math.max(1, s * .015);
      ctx.beginPath(); ctx.moveTo(.1 * s, 0); ctx.quadraticCurveTo(.12 * s, .3 * s, -.12 * s, .42 * s);
      for (let k = 0; k < 4; k++) ctx.quadraticCurveTo((-.14 - k * .03) * s, (.32 - k * .09) * s, (-.18 - k * .02) * s, (.3 - k * .1) * s);
      ctx.lineTo(-.14 * s, 0); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.beginPath();
      for (let k = 0; k < 3; k++) { ctx.moveTo(.02 * s, (.06 + k * .08) * s); ctx.lineTo((-.12 - k * .02) * s, (.14 + k * .09) * s); }
      ctx.stroke(); ctx.restore();
    }
  } else if (topper === "viking") {   // a round helmet with a horn each side
    ctx.lineWidth = Math.max(1, s * .015);
    for (const side of [-1, 1]) {
      ctx.fillStyle = "#f2e6c8"; ctx.strokeStyle = "#b8a476";
      ctx.beginPath(); ctx.moveTo(-.1 * s, side * .1 * s); ctx.quadraticCurveTo(-.12 * s, side * .3 * s, .06 * s, side * .38 * s);
      ctx.quadraticCurveTo(-.04 * s, side * .26 * s, -.01 * s, side * .1 * s); ctx.closePath(); ctx.fill(); ctx.stroke();
    }
    ctx.fillStyle = "#9aa3b5"; ctx.strokeStyle = "#5a6070";
    ctx.beginPath(); ctx.arc(-.06 * s, 0, s * .15, 0, 7); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#c7a05a"; ctx.fillRect(-.09 * s, -.15 * s, .06 * s, .3 * s);
    ctx.fillStyle = "#e6c98a"; for (const y of [-.1, 0, .1]) { ctx.beginPath(); ctx.arc(-.06 * s, y * s, s * .015, 0, 7); ctx.fill(); }
  } else if (topper === "mohawk") {   // a row of rainbow spikes down the middle
    for (let k = 0; k < 7; k++) {
      const x = -.28 + k * .05, h = .1 + .04 * Math.sin(k * 1.3) + (CALM ? 0 : .015 * Math.sin(now / 150 + k));
      ctx.fillStyle = `hsl(${k * 50},95%,62%)`;
      ctx.beginPath(); ctx.moveTo((x - .03) * s, 0); ctx.lineTo((x + .02) * s, -h * s); ctx.lineTo((x + .04) * s, 0); ctx.lineTo((x + .02) * s, h * s); ctx.closePath(); ctx.fill();
    }
  } else if (topper === "daisy") {   // a big daisy on the deck, petals swaying
    const sway = CALM ? 0 : Math.sin(now / 500) * .12;
    ctx.save(); ctx.translate(-.1 * s, 0); ctx.rotate(sway);
    ctx.fillStyle = "#ffffff"; ctx.strokeStyle = "#e3dccd"; ctx.lineWidth = Math.max(1, s * .01);
    for (let k = 0; k < 8; k++) {
      ctx.save(); ctx.rotate(k * Math.PI / 4);
      ctx.beginPath(); ctx.ellipse(.1 * s, 0, .07 * s, .035 * s, 0, 0, 7); ctx.fill(); ctx.stroke(); ctx.restore();
    }
    ctx.fillStyle = "#ffc928"; ctx.beginPath(); ctx.arc(0, 0, .05 * s, 0, 7); ctx.fill();
    ctx.fillStyle = "#e0a020"; for (let k = 0; k < 5; k++) { ctx.beginPath(); ctx.arc(Math.cos(k * 1.3) * .025 * s, Math.sin(k * 1.3) * .025 * s, .008 * s, 0, 7); ctx.fill(); }
    ctx.restore();
  } else if (topper === "captain") {   // a captain's cap: navy, a gold band and a star
    ctx.fillStyle = "#1f2f6b"; ctx.beginPath(); ctx.ellipse(-.1 * s, 0, .17 * s, .19 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#16224f"; ctx.beginPath(); ctx.ellipse(.04 * s, 0, .07 * s, .16 * s, 0, -Math.PI / 2, Math.PI / 2); ctx.fill();
    ctx.strokeStyle = "#ffc928"; ctx.lineWidth = s * .03; ctx.beginPath(); ctx.ellipse(-.1 * s, 0, .13 * s, .15 * s, 0, 0, 7); ctx.stroke();
    ctx.fillStyle = "#ffd36b"; ctx.shadowColor = "#ffd36b"; ctx.shadowBlur = s * .15;
    ctx.beginPath();
    for (let k = 0; k < 10; k++) { const r = (k % 2 ? .03 : .075) * s, a = k * Math.PI / 5; ctx.lineTo(-.1 * s + Math.cos(a) * r, Math.sin(a) * r); }
    ctx.fill(); ctx.shadowBlur = 0;
  } else if (topper === "frostcrown") {   // a ring of ice spikes seen from above, glowing, a sparkle running round
    const cx = -.08 * s, lit = CALM ? 2 : Math.floor(now / 140) % 8;
    ctx.shadowColor = "#8fe3ff"; ctx.shadowBlur = s * .25; ctx.lineWidth = Math.max(1, s * .012);
    for (let k = 0; k < 8; k++) {
      const a = k * Math.PI / 4, c = Math.cos(a), si = Math.sin(a);
      ctx.fillStyle = k === lit ? "#ffffff" : "rgba(190,240,255,.9)"; ctx.strokeStyle = "#ffffff";
      ctx.beginPath(); ctx.moveTo(cx + (c * .1 - si * .035) * s, (si * .1 + c * .035) * s);
      ctx.lineTo(cx + c * .2 * s, si * .2 * s); ctx.lineTo(cx + (c * .1 + si * .035) * s, (si * .1 - c * .035) * s);
      ctx.closePath(); ctx.fill(); ctx.stroke();
    }
    ctx.shadowBlur = 0;
    ctx.strokeStyle = "rgba(220,248,255,.95)"; ctx.lineWidth = s * .035; ctx.beginPath(); ctx.arc(cx, 0, .1 * s, 0, 7); ctx.stroke();
    ctx.fillStyle = "#4dc3ff"; for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + Math.PI / 4; ctx.beginPath(); ctx.arc(cx + Math.cos(a) * .1 * s, Math.sin(a) * .1 * s, .022 * s, 0, 7); ctx.fill(); }
  } else if (topper === "cape") {   // a hero's cape streaming out behind
    ctx.fillStyle = "#e3262f"; ctx.strokeStyle = "#a01018"; ctx.lineWidth = Math.max(1, s * .015);
    ctx.beginPath(); ctx.moveTo(-.02 * s, -.08 * s);
    for (let j = 0; j <= 5; j++) {
      const x = -.02 - j * .08, w = .08 + j * .02, wave = CALM ? .01 : Math.sin(now / 120 - j * .9) * .025 * j / 3;
      ctx.lineTo(x * s, (-w + wave) * s);
    }
    for (let j = 5; j >= 0; j--) {
      const x = -.02 - j * .08, w = .08 + j * .02, wave = CALM ? .01 : Math.sin(now / 120 - j * .9 + 1) * .025 * j / 3;
      ctx.lineTo(x * s, (w + wave) * s);
    }
    ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.strokeStyle = "rgba(120,10,20,.5)"; ctx.beginPath();
    for (const y of [-.05, .05]) { ctx.moveTo(-.04 * s, y * s); ctx.lineTo(-.4 * s, y * 2 * s); }
    ctx.stroke();
    ctx.fillStyle = "#ffd36b"; ctx.beginPath(); ctx.arc(-.02 * s, -.08 * s, .028 * s, 0, 7); ctx.arc(-.02 * s, .08 * s, .028 * s, 0, 7); ctx.fill();
  } else if (topper === "lasereyes") {   // two red beams out of the camera, flickering
    const k = CALM ? 1 : .75 + .25 * hash(Math.floor(now / 70), 9);
    ctx.lineCap = "round";
    for (const y of [-.035, .035]) {
      const grad = ctx.createLinearGradient(.25 * s, 0, .85 * s, 0);
      grad.addColorStop(0, `rgba(255,255,255,${k})`); grad.addColorStop(.15, `rgba(255,60,60,${k})`); grad.addColorStop(1, "rgba(255,30,30,0)");
      ctx.strokeStyle = grad; ctx.lineWidth = s * .035; ctx.shadowColor = "#ff2e2e"; ctx.shadowBlur = s * .25;
      ctx.beginPath(); ctx.moveTo(.25 * s, y * s); ctx.lineTo(.85 * s, y * 1.6 * s); ctx.stroke();
    }
    ctx.shadowBlur = 0;
  } else if (topper === "binoculars") {   // binoculars on the deck, looking out ahead
    ctx.fillStyle = "#2a2a35"; ctx.strokeStyle = "#5a6070"; ctx.lineWidth = Math.max(1, s * .015);
    for (const y of [-.07, .07]) { roundRect(ctx, -.2 * s, (y - .055) * s, .2 * s, .11 * s, .04 * s); ctx.fill(); ctx.stroke(); }
    ctx.fillRect(-.14 * s, -.03 * s, .07 * s, .06 * s);
    for (const y of [-.07, .07]) {
      const grad = ctx.createRadialGradient(.0, y * s, 0, 0, y * s, .05 * s);
      grad.addColorStop(0, "#c8f0ff"); grad.addColorStop(1, "#3a7fb0");
      ctx.fillStyle = grad; ctx.beginPath(); ctx.ellipse(0, y * s, .02 * s, .045 * s, 0, 0, 7); ctx.fill();
    }
  } else if (topper === "donut") {   // a pink-iced donut on the deck, sprinkles and all
    const cx = -.1 * s;
    ctx.beginPath(); ctx.arc(cx, 0, .16 * s, 0, 7); ctx.arc(cx, 0, .05 * s, 0, 7, true);
    ctx.fillStyle = "#d9954a"; ctx.fill();
    ctx.beginPath();
    for (let k = 0; k <= 40; k++) {
      const a = k / 40 * Math.PI * 2, r = (.135 + .012 * Math.sin(a * 7)) * s;
      ctx.lineTo(cx + Math.cos(a) * r, Math.sin(a) * r);
    }
    ctx.arc(cx, 0, .065 * s, 0, 7, true);
    ctx.fillStyle = "#ff8ac2"; ctx.fill();
    for (let k = 0; k < 11; k++) {
      const a = k * .57 + hash(k, 170), r = (.085 + hash(k, 171) * .035) * s;
      ctx.save(); ctx.translate(cx + Math.cos(a) * r, Math.sin(a) * r); ctx.rotate(hash(k, 172) * 3);
      ctx.fillStyle = ["#ffffff", "#ffd34d", "#4dc3ff", "#7ff07a", "#b07aff"][k % 5];
      ctx.fillRect(-.018 * s, -.006 * s, .036 * s, .012 * s + .5); ctx.restore();
    }
  } else if (topper === "witchhat") {   // a crooked witch's hat, an orange band and a gold buckle
    ctx.fillStyle = "#2a1838"; ctx.beginPath(); ctx.ellipse(-.07 * s, .06 * s, .22 * s, .06 * s, 0, 0, 7); ctx.fill();
    const tip = CALM ? 0 : Math.sin(now / 600) * .03;
    ctx.fillStyle = "#3d2352"; ctx.beginPath(); ctx.moveTo(-.2 * s, .05 * s); ctx.lineTo(.06 * s, .05 * s);
    ctx.quadraticCurveTo(-.02 * s, -.22 * s, -.1 * s, -.34 * s);
    ctx.quadraticCurveTo((-.2 + tip) * s, -.42 * s, (-.3 + tip) * s, -.36 * s);
    ctx.quadraticCurveTo(-.2 * s, -.3 * s, -.16 * s, -.18 * s); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#ff8a1f"; ctx.beginPath(); ctx.moveTo(-.19 * s, .03 * s); ctx.lineTo(.05 * s, .03 * s);
    ctx.lineTo(.03 * s, -.03 * s); ctx.lineTo(-.18 * s, -.03 * s); ctx.fill();
    ctx.strokeStyle = "#ffd36b"; ctx.lineWidth = Math.max(1, s * .02); ctx.strokeRect(-.1 * s, -.035 * s, .06 * s, .07 * s);
  } else if (topper === "candybucket") {   // a jack-o'-lantern pail, its handle up, candy heaped in it
    ctx.strokeStyle = "#3a2410"; ctx.lineWidth = Math.max(1, s * .025);
    ctx.beginPath(); ctx.arc(-.1 * s, -.02 * s, .2 * s, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke();
    ctx.fillStyle = "#ff8a1f"; ctx.strokeStyle = "#c25a0c";
    ctx.beginPath(); ctx.arc(-.1 * s, .02 * s, .15 * s, 0, 7); ctx.fill(); ctx.stroke();
    for (let k = 0; k < 7; k++) {
      ctx.fillStyle = ["#ff4f7a", "#ffe14d", "#7ff07a", "#b07aff", "#4dc3ff"][k % 5];
      ctx.beginPath(); ctx.arc((-.18 + k * .028) * s, (-.06 - hash(k, 31) * .05) * s, .035 * s, 0, 7); ctx.fill();
    }
    ctx.fillStyle = "#2a1408";
    for (const x of [-.15, -.05]) { ctx.beginPath(); ctx.moveTo((x - .03) * s, .06 * s); ctx.lineTo((x + .03) * s, .06 * s); ctx.lineTo(x * s, .01 * s); ctx.fill(); }
    ctx.fillRect(-.16 * s, .1 * s, .12 * s, .025 * s);
  } else if (topper === "tophat") {   // a tall black hat, a purple band, and a little ghost peeking out
    const peek = CALM ? .5 : .5 + .5 * Math.sin(now / 700);
    ctx.fillStyle = "#18121f"; ctx.beginPath(); ctx.ellipse(-.08 * s, .06 * s, .2 * s, .055 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#f4f1ff"; ctx.globalAlpha = .9;
    ctx.beginPath(); ctx.arc(-.08 * s, (-.28 - peek * .08) * s, .075 * s, Math.PI, 0); ctx.lineTo(-.005 * s, -.22 * s); ctx.lineTo(-.155 * s, -.22 * s); ctx.fill();
    ctx.globalAlpha = 1; eyes(ctx, s, [-.105, -.055], -.28 - peek * .08, .016);
    ctx.fillStyle = "#231a2c"; ctx.fillRect(-.19 * s, -.26 * s, .22 * s, .32 * s);
    ctx.fillStyle = "#7a3fc0"; ctx.fillRect(-.19 * s, -.03 * s, .22 * s, .06 * s);
    ctx.fillStyle = "#2e2338"; ctx.beginPath(); ctx.ellipse(-.08 * s, -.26 * s, .11 * s, .03 * s, 0, 0, 7); ctx.fill();
  } else {
    ctx.strokeStyle = "#6e6290"; ctx.beginPath(); ctx.moveTo(-.05 * s, -.14 * s); ctx.lineTo(-.16 * s, -.36 * s); ctx.stroke();
    ctx.fillStyle = "#ffb547"; ctx.beginPath(); ctx.arc(-.16 * s, -.36 * s, s * .035, 0, 7); ctx.fill();
  }
}
// Under the rover: a light on the ground, facing +x like the rover.
function underglow(ctx, s, rgb, k) {
  const grad = ctx.createRadialGradient(0, 0, s * .2, 0, 0, s * .7);
  grad.addColorStop(0, `rgba(${rgb},${.75 * k})`); grad.addColorStop(1, `rgba(${rgb},0)`);
  ctx.fillStyle = grad; ctx.beginPath(); ctx.ellipse(0, 0, s * .7, s * .58, 0, 0, 7); ctx.fill();
}
const pulse = (now, speed) => CALM ? 1 : .7 + .3 * Math.sin(now / speed);
const GLOWS = {
  mintglow: (ctx, s, now) => underglow(ctx, s, "140,242,198", pulse(now, 300)),
  pinkglow: (ctx, s, now) => underglow(ctx, s, "255,111,174", pulse(now, 260)),
  iceglow: (ctx, s, now) => underglow(ctx, s, "143,227,255", pulse(now, 420)),
  rainbowglow(ctx, s, now) {
    const h = CALM ? 280 : (now / 8) % 360;
    const grad = ctx.createRadialGradient(0, 0, s * .2, 0, 0, s * .72);
    grad.addColorStop(0, `hsla(${h},100%,65%,.8)`); grad.addColorStop(.6, `hsla(${h + 90},100%,65%,.4)`); grad.addColorStop(1, `hsla(${h + 180},100%,65%,0)`);
    ctx.fillStyle = grad; ctx.beginPath(); ctx.ellipse(0, 0, s * .72, s * .6, 0, 0, 7); ctx.fill();
  },
  plasmaring(ctx, s, now) {   // a spinning ring of electric sparks
    underglow(ctx, s, "185,140,255", .6);
    const spin = CALM ? 0 : now / 400;
    ctx.strokeStyle = "#d9c2ff"; ctx.lineWidth = Math.max(1, s * .035); ctx.shadowColor = "#b98cff"; ctx.shadowBlur = s * .2;
    ctx.setLineDash([s * .12, s * .08]); ctx.lineDashOffset = -spin * s;
    ctx.beginPath(); ctx.ellipse(0, 0, s * .56, s * .5, 0, 0, 7); ctx.stroke();
    ctx.setLineDash([]); ctx.fillStyle = "#ffffff";
    for (let k = 0; k < 3; k++) {
      const a = spin * 2.3 + k * 2.1;
      ctx.beginPath(); ctx.arc(Math.cos(a) * s * .56, Math.sin(a) * s * .5, s * .035, 0, 7); ctx.fill();
    }
    ctx.shadowBlur = 0;
  },
  afterburner(ctx, s, now) {   // twin jets of flame out of the back
    for (const y of [-.13, .13]) {
      const len = s * (.38 + (CALM ? .1 : .14 * hash(Math.floor(now / 60), y * 100)));
      const grad = ctx.createLinearGradient(-.3 * s, 0, -.3 * s - len, 0);
      grad.addColorStop(0, "rgba(255,255,220,.95)"); grad.addColorStop(.3, "rgba(120,200,255,.9)"); grad.addColorStop(.7, "rgba(90,90,255,.55)"); grad.addColorStop(1, "rgba(60,40,200,0)");
      ctx.fillStyle = grad; ctx.shadowColor = "#7fb8ff"; ctx.shadowBlur = s * .25;
      ctx.beginPath(); ctx.moveTo(-.28 * s, (y - .07) * s); ctx.quadraticCurveTo(-.3 * s - len * .6, y * s, -.3 * s - len, y * s);
      ctx.quadraticCurveTo(-.3 * s - len * .6, y * s, -.28 * s, (y + .07) * s); ctx.fill();
    }
    ctx.shadowBlur = 0;
  },
  aura(ctx, s, now) {   // dark smoke curling round the rover, purple at the edges
    for (let k = 0; k < 7; k++) {
      const a = (CALM ? 0 : now / 900) + k * .9, r = s * (.42 + .1 * Math.sin((CALM ? 0 : now / 300) + k * 2));
      const x = Math.cos(a) * r, y = Math.sin(a) * r * .85;
      const grad = ctx.createRadialGradient(x, y, 0, x, y, s * .3);
      grad.addColorStop(0, "rgba(40,10,70,.55)"); grad.addColorStop(.6, "rgba(130,60,220,.25)"); grad.addColorStop(1, "rgba(130,60,220,0)");
      ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(x, y, s * .3, 0, 7); ctx.fill();
    }
  },
};

// The sidekick, floating beside the rover: s is the rover's size, (x, y) the
// pet's middle. Drawn upright, whichever way the rover faces.
function drawPet(ctx, x, y, s, pet, now) {
  if (!PETS[pet]) return;
  const t = CALM ? 0 : now, bob = Math.sin(t / 320) * s * .05;
  ctx.save();
  ctx.fillStyle = "rgba(10,4,16,.3)";
  ctx.beginPath(); ctx.ellipse(x, y + s * .32, s * .16, s * .05, 0, 0, 7); ctx.fill();
  ctx.translate(x, y + bob);
  ctx.lineWidth = Math.max(1, s * .02);
  PETS[pet](ctx, s * .5, t);
  ctx.restore();
}
function eyes(ctx, s, xs, y, r = .06) {
  for (const x of xs) {
    ctx.fillStyle = "#1b1530"; ctx.beginPath(); ctx.arc(x * s, y * s, r * s, 0, 7); ctx.fill();
    ctx.fillStyle = "#ffffff"; ctx.beginPath(); ctx.arc((x + r * .35) * s, (y - r * .35) * s, r * .4 * s, 0, 7); ctx.fill();
  }
}
const PETS = {
  drone(ctx, s, t) {   // four rotors and a blinking light
    ctx.strokeStyle = "#4a4466"; ctx.lineWidth = s * .08;
    ctx.beginPath(); ctx.moveTo(-.4 * s, -.25 * s); ctx.lineTo(.4 * s, .25 * s); ctx.moveTo(.4 * s, -.25 * s); ctx.lineTo(-.4 * s, .25 * s); ctx.stroke();
    for (const [rx, ry] of [[-.4, -.25], [.4, -.25], [-.4, .25], [.4, .25]]) {
      const w = Math.abs(Math.cos(t / 30 + rx * 9)) * .2 + .04;
      ctx.fillStyle = "rgba(200,220,255,.55)"; ctx.beginPath(); ctx.ellipse(rx * s, ry * s - .08 * s, w * s, .05 * s, 0, 0, 7); ctx.fill();
    }
    ctx.fillStyle = "#e6dccb"; roundRect(ctx, -.22 * s, -.16 * s, .44 * s, .32 * s, .1 * s); ctx.fill();
    ctx.fillStyle = "#231d3f"; ctx.beginPath(); ctx.arc(0, .02 * s, .1 * s, 0, 7); ctx.fill();
    ctx.fillStyle = "#8cf2c6"; ctx.beginPath(); ctx.arc(0, .02 * s, .05 * s, 0, 7); ctx.fill();
    ctx.fillStyle = Math.floor(t / 400) % 2 ? "#ff5a5a" : "#5a2030";
    ctx.beginPath(); ctx.arc(0, -.2 * s, .04 * s, 0, 7); ctx.fill();
  },
  duck(ctx, s, t) {   // a rubber duck, bobbing as if it's floating
    ctx.rotate(Math.sin(t / 400) * .12);
    ctx.fillStyle = "#ffd84d"; ctx.strokeStyle = "#d9a520";
    ctx.beginPath(); ctx.ellipse(0, .12 * s, .42 * s, .26 * s, 0, 0, 7); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-.42 * s, .05 * s); ctx.lineTo(-.55 * s, -.12 * s); ctx.lineTo(-.3 * s, 0); ctx.fill();
    ctx.beginPath(); ctx.arc(.18 * s, -.2 * s, .22 * s, 0, 7); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#ff8a1f"; ctx.beginPath(); ctx.ellipse(.43 * s, -.16 * s, .13 * s, .06 * s, 0, 0, 7); ctx.fill();
    eyes(ctx, s, [.22], -.26, .05);
    ctx.fillStyle = "#f2b820"; ctx.beginPath(); ctx.ellipse(-.05 * s, .1 * s, .18 * s, .1 * s, -.3, 0, 7); ctx.fill();
  },
  spacecat(ctx, s, t) {   // a cat in a glass helmet
    ctx.fillStyle = "#ff9d4d";
    for (const x of [-.22, .22]) { ctx.beginPath(); ctx.moveTo((x - .13) * s, -.12 * s); ctx.lineTo(x * 1.3 * s, -.42 * s); ctx.lineTo((x + .13) * s, -.12 * s); ctx.fill(); }
    ctx.beginPath(); ctx.arc(0, 0, .3 * s, 0, 7); ctx.fill();
    ctx.fillStyle = "#ffe0c2"; ctx.beginPath(); ctx.ellipse(0, .1 * s, .17 * s, .12 * s, 0, 0, 7); ctx.fill();
    eyes(ctx, s, [-.11, .11], -.04, .055);
    ctx.fillStyle = "#ff6f9f"; ctx.beginPath(); ctx.arc(0, .06 * s, .035 * s, 0, 7); ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,.5)"; ctx.lineWidth = s * .03;
    for (const side of [-1, 1]) { ctx.beginPath(); ctx.moveTo(side * .12 * s, .1 * s); ctx.lineTo(side * .4 * s, (.06 + .03 * Math.sin(t / 200)) * s); ctx.stroke(); }
    ctx.fillStyle = "rgba(170,230,255,.2)"; ctx.strokeStyle = "rgba(200,240,255,.8)"; ctx.lineWidth = s * .04;
    ctx.beginPath(); ctx.arc(0, -.02 * s, .5 * s, 0, 7); ctx.fill(); ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,.75)"; ctx.beginPath(); ctx.arc(0, -.02 * s, .4 * s, Math.PI * 1.15, Math.PI * 1.45); ctx.stroke();
  },
  ghost(ctx, s, t) {   // a friendly ghost with a wavy hem
    ctx.globalAlpha = .88; ctx.rotate(Math.sin(t / 500) * .1);
    ctx.fillStyle = "#f4f1ff"; ctx.shadowColor = "#c9b8ff"; ctx.shadowBlur = s * .4;
    ctx.beginPath(); ctx.moveTo(-.32 * s, .35 * s); ctx.lineTo(-.32 * s, -.05 * s); ctx.arc(0, -.05 * s, .32 * s, Math.PI, 0);
    ctx.lineTo(.32 * s, .35 * s);
    for (let k = 0; k < 4; k++) {
      const x = .32 - (k + 1) * .16, wave = Math.sin(t / 150 + k) * .05;
      ctx.quadraticCurveTo((x + .08) * s, (.45 + wave) * s, x * s, (.35 - wave) * s);
    }
    ctx.fill(); ctx.shadowBlur = 0; ctx.globalAlpha = 1;
    eyes(ctx, s, [-.12, .12], -.06, .07);
    ctx.fillStyle = "#ff9ec4"; ctx.beginPath(); ctx.ellipse(0, .1 * s, .07 * s, .05 * s, 0, 0, 7); ctx.fill();
  },
  jelly(ctx, s, t) {   // a glowing jellyfish, tentacles drifting
    ctx.strokeStyle = "rgba(255,160,230,.75)"; ctx.lineWidth = s * .05; ctx.lineCap = "round";
    for (let k = 0; k < 5; k++) {
      const x = (-.24 + k * .12) * s;
      ctx.beginPath(); ctx.moveTo(x, .05 * s);
      for (let j = 1; j <= 4; j++) ctx.lineTo(x + Math.sin(t / 220 + j + k) * .06 * s, (.05 + j * .12) * s);
      ctx.stroke();
    }
    const squish = 1 + Math.sin(t / 250) * .08;
    ctx.fillStyle = "rgba(255,120,210,.85)"; ctx.shadowColor = "#ff8ad8"; ctx.shadowBlur = s * .5;
    ctx.beginPath(); ctx.ellipse(0, .05 * s, .36 * s * squish, .36 * s / squish, 0, Math.PI, 0); ctx.fill(); ctx.shadowBlur = 0;
    ctx.fillStyle = "rgba(255,255,255,.35)"; ctx.beginPath(); ctx.ellipse(-.12 * s, -.14 * s, .08 * s, .05 * s, -.5, 0, 7); ctx.fill();
    eyes(ctx, s, [-.1, .1], -.06, .045);
  },
  robodog(ctx, s, t) {   // a boxy robot pup, tail wagging
    ctx.strokeStyle = "#9aa3b5"; ctx.lineWidth = s * .07; ctx.lineCap = "round";
    const wag = Math.sin(t / 90) * .5;
    ctx.beginPath(); ctx.moveTo(-.3 * s, 0); ctx.lineTo((-.3 - .2 * Math.cos(wag)) * s, (-.2 * Math.abs(Math.cos(wag)) - .05) * s); ctx.stroke();
    for (const x of [-.22, -.05, .1, .25]) { ctx.beginPath(); ctx.moveTo(x * s, .1 * s); ctx.lineTo(x * s, .32 * s); ctx.stroke(); }
    ctx.fillStyle = "#c3cad6"; roundRect(ctx, -.32 * s, -.1 * s, .62 * s, .26 * s, .08 * s); ctx.fill();
    ctx.fillStyle = "#dfe4ec"; roundRect(ctx, .14 * s, -.36 * s, .32 * s, .3 * s, .07 * s); ctx.fill();
    ctx.fillStyle = "#6e7a90";
    ctx.beginPath(); ctx.moveTo(.16 * s, -.34 * s); ctx.lineTo(.1 * s, -.48 * s); ctx.lineTo(.26 * s, -.36 * s); ctx.fill();
    ctx.fillStyle = "#4dc3ff"; ctx.shadowColor = "#4dc3ff"; ctx.shadowBlur = s * .2;
    ctx.fillRect(.26 * s, -.27 * s, .12 * s, .06 * s); ctx.shadowBlur = 0;
    ctx.fillStyle = "#1b1530"; ctx.beginPath(); ctx.arc(.46 * s, -.15 * s, .04 * s, 0, 7); ctx.fill();
  },
  dragon(ctx, s, t) {   // a baby dragon, flapping, with a puff of fire now and then
    const flap = Math.sin(t / 110);
    ctx.fillStyle = "#3fae6a";
    for (const side of [-1, 1]) {
      ctx.save(); ctx.scale(side, 1); ctx.rotate(-.3 + flap * .35);
      ctx.beginPath(); ctx.moveTo(.08 * s, -.05 * s); ctx.lineTo(.5 * s, -.38 * s); ctx.lineTo(.42 * s, -.12 * s); ctx.lineTo(.5 * s, .02 * s); ctx.closePath();
      ctx.fillStyle = "#7ee0a0"; ctx.fill(); ctx.restore();
    }
    ctx.fillStyle = "#3fae6a"; ctx.beginPath(); ctx.ellipse(0, .1 * s, .22 * s, .26 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#b8f0c8"; ctx.beginPath(); ctx.ellipse(0, .16 * s, .12 * s, .17 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#3fae6a"; ctx.beginPath(); ctx.arc(0, -.22 * s, .2 * s, 0, 7); ctx.fill();
    ctx.fillStyle = "#ffd36b";
    for (const x of [-.1, .1]) { ctx.beginPath(); ctx.moveTo((x - .04) * s, -.36 * s); ctx.lineTo(x * 1.4 * s, -.5 * s); ctx.lineTo((x + .04) * s, -.36 * s); ctx.fill(); }
    eyes(ctx, s, [-.08, .08], -.24, .05);
    if (Math.floor(t / 1600) % 3 === 0 && t % 1600 < 500) {
      const k = (t % 1600) / 500, grad = ctx.createRadialGradient(0, -.05 * s, 0, 0, -.05 * s, .3 * s * k + .01);
      grad.addColorStop(0, "rgba(255,240,150,.95)"); grad.addColorStop(.5, "rgba(255,140,40,.8)"); grad.addColorStop(1, "rgba(220,40,20,0)");
      ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(0, (-.05 + k * .12) * s, .3 * s * k + .01, 0, 7); ctx.fill();
    }
  },
  verity(ctx, s, t) {   // Verity, a smiley face that blinks and now and then winks
    ctx.rotate(Math.sin(t / 600) * .1);
    const grad = ctx.createRadialGradient(-.12 * s, -.14 * s, .05 * s, 0, 0, .4 * s);
    grad.addColorStop(0, "#fff38a"); grad.addColorStop(1, "#ffc928");
    ctx.fillStyle = grad; ctx.strokeStyle = "#d99a12"; ctx.lineWidth = s * .04;
    ctx.beginPath(); ctx.arc(0, 0, .38 * s, 0, 7); ctx.fill(); ctx.stroke();
    const blink = t % 3200 > 3060, wink = !blink && t % 9600 > 9000;   // eyes open at t = 0 (calm mode)
    ctx.fillStyle = ctx.strokeStyle = "#3a2410"; ctx.lineWidth = s * .05; ctx.lineCap = "round";
    for (const x of [-.13, .13]) {
      if (blink || (wink && x > 0)) { ctx.beginPath(); ctx.moveTo((x - .06) * s, -.1 * s); ctx.lineTo((x + .06) * s, -.1 * s); ctx.stroke(); }
      else { ctx.beginPath(); ctx.ellipse(x * s, -.1 * s, .045 * s, .08 * s, 0, 0, 7); ctx.fill(); }
    }
    ctx.beginPath(); ctx.arc(0, .02 * s, .22 * s, .15 * Math.PI, .85 * Math.PI); ctx.stroke();
    ctx.fillStyle = "rgba(255,120,120,.4)";
    for (const x of [-.25, .25]) { ctx.beginPath(); ctx.ellipse(x * s, .08 * s, .06 * s, .035 * s, 0, 0, 7); ctx.fill(); }
  },
  minicrew(ctx, s, t) {   // a little crewmate in a spacesuit, waddling along
    const step = Math.sin(t / 140);
    ctx.fillStyle = "#7a0838";
    roundRect(ctx, -.34 * s, -.12 * s, .14 * s, .3 * s, .05 * s); ctx.fill();          // backpack
    for (const [x, k] of [[-.13, 1], [.1, -1]]) {
      roundRect(ctx, x * s, (.22 - Math.max(0, step * k) * .06) * s, .14 * s, .16 * s, .05 * s); ctx.fill();   // legs
    }
    ctx.fillStyle = "#c51111";
    ctx.beginPath(); ctx.moveTo(-.24 * s, .3 * s); ctx.lineTo(-.24 * s, -.12 * s);
    ctx.arc(0, -.12 * s, .24 * s, Math.PI, 0); ctx.lineTo(.24 * s, .3 * s); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "rgba(0,0,0,.18)"; ctx.fillRect(-.24 * s, .18 * s, .48 * s, .12 * s);
    ctx.fillStyle = "#3f5f7a"; roundRect(ctx, -.02 * s, -.24 * s, .34 * s, .2 * s, .1 * s); ctx.fill();   // visor
    ctx.fillStyle = "#9ad8f0"; roundRect(ctx, .01 * s, -.24 * s, .3 * s, .16 * s, .08 * s); ctx.fill();
    ctx.fillStyle = "#ffffff"; roundRect(ctx, .12 * s, -.21 * s, .12 * s, .05 * s, .025 * s); ctx.fill();
  },
};

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}

// Rover paints: a colour, a few that sweep across the body, or a pattern
// with a `swatch` for the garage button, painted over the whole body (no solar
// deck, so the pattern shows).
const PAINTS = {bone: "#f2eadb", coral: "#ff8a7a", mint: "#8cf2c6", sky: "#8fc8ff", gold: "#ffd36b",
  aurora: ["#7ff0d6", "#8fb8ff", "#c69bff"], nebula: ["#c69bff", "#ff8ad8", "#8fb8ff"],
  supernova: ["#fff6d0", "#ffe08a", "#ff9d5c"],
  copper: "#d9894a", racer: ["#ff6b5a", "#ffb84d", "#ffd36b"],
  granite: ["#9a9ba6", "#6e7079"], laser: ["#ff3b5c", "#ff8a9e"], cardboard: "#c8a06a",
  trailblazer: ["#3fb68b", "#f2c14e", "#e4572e"],
  ocean: ["#5ad1ff", "#2a7fd8", "#1b3f8a"], chrome: ["#ffffff", "#c3cad6", "#8a94a3", "#e8edf5"],
  holo: {swatch: "conic-gradient(#ffb3e6, #b3e6ff, #d9b3ff, #b3ffd9, #ffb3e6)", fill(ctx, s, now) {
    const h = CALM ? 200 : (now / 20) % 360;
    const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
    [0, 90, 180, 270].forEach((d, i) => grad.addColorStop(i / 3, `hsl(${h + d},90%,82%)`));
    return grad;
  }},
  comet: {base: "#0e1030", swatch: "linear-gradient(120deg, #0e1030 40%, #8fe3ff 55%, #ffffff 62%, #0e1030 75%)", draw(ctx, s) {
    // A comet streaking across the body, with a few far stars.
    const grad = ctx.createLinearGradient(-.32 * s, .14 * s, .2 * s, -.1 * s);
    grad.addColorStop(0, "rgba(143,227,255,0)"); grad.addColorStop(1, "rgba(200,245,255,.9)");
    ctx.strokeStyle = grad; ctx.lineWidth = s * .09; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(-.3 * s, .14 * s); ctx.lineTo(.16 * s, -.08 * s); ctx.stroke();
    ctx.fillStyle = "#ffffff"; ctx.shadowColor = "#8fe3ff"; ctx.shadowBlur = s * .15;
    ctx.beginPath(); ctx.arc(.17 * s, -.085 * s, s * .055, 0, 7); ctx.fill(); ctx.shadowBlur = 0;
    for (let k = 0; k < 10; k++) { ctx.beginPath(); ctx.arc((-.3 + hash(k, 13) * .58) * s, (-.2 + hash(k, 14) * .4) * s, s * .01, 0, 7); ctx.fill(); }
  }},
  legend: {swatch: "linear-gradient(135deg, #ffd36b, #ff8ad8, #8fb8ff, #7ff0d6)", fill(ctx, s, now) {
    const h = CALM ? 0 : (now / 25) % 360;
    const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
    grad.addColorStop(0, "#ffd36b"); grad.addColorStop(.5, `hsl(${320 + h},90%,75%)`); grad.addColorStop(1, `hsl(${180 + h},90%,72%)`);
    return grad;
  }, draw(ctx, s, now) {
    ctx.fillStyle = "#fff6d0";
    for (let k = 0; k < 6; k++) {
      const tw = CALM ? .8 : .5 + .5 * Math.sin(now / 220 + k * 1.9);
      ctx.globalAlpha = tw; ctx.font = `${Math.round(s * .1)}px system-ui, sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("✦", (-.26 + hash(k, 15) * .5) * s, (-.16 + hash(k, 16) * .32) * s);
    }
    ctx.globalAlpha = 1;
  }},
  galaxy: {base: "#1b1240", swatch: "radial-gradient(circle at 30% 30%, #c69bff, #1b1240 70%)", draw(ctx, s) {
    for (const [x, y, r, color] of [[-.14, -.08, .24, "rgba(198,155,255,.55)"], [.12, .1, .2, "rgba(255,138,216,.4)"]]) {
      const grad = ctx.createRadialGradient(x * s, y * s, 0, x * s, y * s, r * s);
      grad.addColorStop(0, color); grad.addColorStop(1, "rgba(27,18,64,0)");
      ctx.fillStyle = grad; ctx.fillRect(-.32 * s, -.22 * s, .62 * s, .44 * s);
    }
    ctx.fillStyle = "#ffffff";
    for (let k = 0; k < 16; k++) { ctx.beginPath(); ctx.arc((-.3 + hash(k, 3) * .58) * s, (-.2 + hash(k, 4) * .4) * s, s * (.008 + hash(k, 5) * .012), 0, 7); ctx.fill(); }
  }},
  lava: {base: "#3a140c", swatch: "radial-gradient(circle, #ffd36b, #ff7a2e 40%, #3a140c 75%)", draw(ctx, s, now) {
    const k = CALM ? 1 : .75 + .25 * Math.sin(now / 300);
    ctx.strokeStyle = `rgba(255,122,46,${k})`; ctx.lineWidth = s * .035; ctx.lineJoin = "round";
    ctx.shadowColor = "#ff7a2e"; ctx.shadowBlur = s * .12;
    ctx.beginPath();
    ctx.moveTo(-.32 * s, -.05 * s); ctx.lineTo(-.18 * s, .02 * s); ctx.lineTo(-.06 * s, -.1 * s); ctx.lineTo(.08 * s, .04 * s); ctx.lineTo(.3 * s, -.02 * s);
    ctx.moveTo(-.18 * s, .02 * s); ctx.lineTo(-.12 * s, .22 * s);
    ctx.moveTo(.08 * s, .04 * s); ctx.lineTo(.14 * s, -.22 * s);
    ctx.stroke(); ctx.shadowBlur = 0;
    ctx.fillStyle = `rgba(255,211,107,${k * .8})`;
    for (const [x, y] of [[-.06, -.1], [.08, .04], [-.18, .02]]) { ctx.beginPath(); ctx.arc(x * s, y * s, s * .03, 0, 7); ctx.fill(); }
  }},
  pizza: {base: "#ffcf5c", swatch: "radial-gradient(circle at 35% 35%, #c4372b 22%, #ffcf5c 25%)", draw(ctx, s) {
    roundRect(ctx, -.32 * s, -.22 * s, .62 * s, .44 * s, .08 * s);
    ctx.strokeStyle = "#d9933f"; ctx.lineWidth = s * .09; ctx.stroke();
    for (const [x, y] of [[-.19, -.08], [-.02, .09], [.15, -.09], [.17, .1], [-.2, .11], [.0, -.11]]) {
      ctx.fillStyle = "#c4372b"; ctx.beginPath(); ctx.arc(x * s, y * s, s * .055, 0, 7); ctx.fill();
      ctx.fillStyle = "#9e2a20"; ctx.beginPath(); ctx.arc((x + .015) * s, (y - .01) * s, s * .012, 0, 7); ctx.fill();
    }
    ctx.fillStyle = "#4f9a3a";
    for (const [x, y] of [[-.1, .02], [.07, -.02], [.24, 0]]) ctx.fillRect(x * s, y * s, s * .035, s * .02);
  }},
  rgb: {swatch: "conic-gradient(#ff4d4d, #ffd34d, #4dff88, #4dc3ff, #b04dff, #ff4d4d)", fill(ctx, s, now) {
    const h = CALM ? 0 : (now / 12) % 360;
    const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
    [0, 120, 240].forEach((d, i) => grad.addColorStop(i / 2, `hsl(${h + d},100%,62%)`));
    return grad;
  }},
  matrix: {base: "#03150a", swatch: "repeating-linear-gradient(90deg, #03150a 0 4px, #2bff88 4px 6px)", draw(ctx, s, now) {
    // Green code raining down the body.
    ctx.font = `700 ${Math.round(s * .09)}px monospace`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    for (let col = 0; col < 7; col++) {
      const x = (-.28 + col * .09) * s, head = ((CALM ? 0 : now / (180 + hash(col, 30) * 160)) + hash(col, 31) * 9) % 9;
      for (let j = 0; j < 6; j++) {
        const fade = 1 - ((head - j + 9) % 9) / 6;
        if (fade <= 0) continue;
        ctx.fillStyle = fade > .9 ? "#d8ffe6" : `rgba(43,255,136,${fade})`;
        ctx.fillText("01<>{}=+"[Math.floor(hash(col, j, Math.floor(head)) * 8)], x, (-.2 + j * .08) * s);
      }
    }
  }},
  lavalamp: {base: "#3a0a4a", swatch: "radial-gradient(circle at 35% 60%, #ffb347 18%, transparent 20%), radial-gradient(circle at 65% 30%, #ff5fa2 16%, #3a0a4a 18%)", draw(ctx, s, now) {
    // Blobs that drift up, squash and drift back.
    const t = CALM ? 0 : now / 1400;
    for (let k = 0; k < 4; k++) {
      const x = (-.2 + k * .13 + .04 * Math.sin(t * 1.3 + k)) * s, y = Math.sin(t + k * 1.7) * .14 * s, r = (.07 + .03 * hash(k, 32)) * s;
      ctx.fillStyle = ["#ffb347", "#ff5fa2", "#ff7a3d", "#ffd36b"][k];
      ctx.beginPath(); ctx.ellipse(x, y, r * (1 + .25 * Math.sin(t * 3 + k)), r * (1 - .2 * Math.sin(t * 3 + k)), 0, 0, 7); ctx.fill();
    }
  }},
  glitch: {base: "#1a1430", swatch: "linear-gradient(#ff2e88 0 20%, #1a1430 20% 45%, #2ef3ff 45% 60%, #1a1430 60% 80%, #f2eadb 80%)", draw(ctx, s, now) {
    // Bands that jump sideways, in the colours of a broken screen.
    const frame = CALM ? 0 : Math.floor(now / 110);
    for (let j = 0; j < 9; j++) {
      const shift = (hash(j, frame, 33) - .5) * .2 * s, hit = hash(j, frame, 34);
      ctx.fillStyle = hit > .8 ? "#ff2e88" : hit > .6 ? "#2ef3ff" : hit > .45 ? "#f2eadb" : "#2a2250";
      ctx.fillRect(-.32 * s + shift, (-.22 + j * .05) * s, .62 * s, .05 * s);
    }
  }},
  plasma: {base: "#1d0f4a", swatch: "conic-gradient(from 90deg, #4b2cff, #ff2ed1, #2ef3ff, #4b2cff)", draw(ctx, s, now) {
    // Bolts of plasma crackling across a swirling body.
    const t = CALM ? 0 : now;
    for (const [k, color] of [[0, "rgba(75,44,255,.8)"], [1, "rgba(255,46,209,.6)"], [2, "rgba(46,243,255,.55)"]]) {
      const a = t / (700 + k * 300) + k * 2, x = Math.cos(a) * .15 * s, y = Math.sin(a) * .1 * s;
      const grad = ctx.createRadialGradient(x, y, 0, x, y, .3 * s);
      grad.addColorStop(0, color); grad.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = grad; ctx.fillRect(-.32 * s, -.22 * s, .62 * s, .44 * s);
    }
    ctx.strokeStyle = "#ffffff"; ctx.lineWidth = Math.max(1, s * .015); ctx.shadowColor = "#2ef3ff"; ctx.shadowBlur = s * .12;
    const frame = Math.floor(t / 90);
    for (let b = 0; b < 2; b++) {
      ctx.beginPath(); ctx.moveTo(-.3 * s, (hash(b, frame, 35) - .5) * .4 * s);
      for (let j = 1; j <= 5; j++) ctx.lineTo((-.3 + j * .12) * s, (hash(b, frame, j + 40) - .5) * .4 * s);
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
  }},
  crewmate: {base: "#c51111", swatch: "radial-gradient(ellipse 36% 26% at 62% 38%, #9ad8f0 70%, #3f5f7a 72%, #c51111 76%)", draw(ctx, s) {
    // A crewmate's suit seen from above: a backpack at the back, the visor in the middle.
    ctx.fillStyle = "rgba(0,0,0,.16)"; ctx.fillRect(-.32 * s, .1 * s, .62 * s, .12 * s);
    ctx.fillStyle = "#7a0838"; roundRect(ctx, -.32 * s, -.15 * s, .1 * s, .3 * s, .04 * s); ctx.fill();
    ctx.fillStyle = "#3f5f7a"; roundRect(ctx, -.16 * s, -.16 * s, .22 * s, .32 * s, .1 * s); ctx.fill();
    ctx.fillStyle = "#9ad8f0"; roundRect(ctx, -.14 * s, -.16 * s, .2 * s, .28 * s, .09 * s); ctx.fill();
    ctx.fillStyle = "#ffffff"; roundRect(ctx, -.1 * s, -.12 * s, .05 * s, .12 * s, .025 * s); ctx.fill();
  }},
  // Blocky ones: pixel art across the body.
  grass: {base: "#6dbb44", swatch: "linear-gradient(#6dbb44 50%, #7a5230 50%)", draw(ctx, s) {
    pixelArt(ctx, s, (i, j, n, rows) => i === 0 || j === 0 || i === n - 1 || j === rows - 1
      ? ["#7a5230", "#8c6239", "#5f3f22"][Math.floor(hash(i, j, 1) * 3)]
      : ["#5fa83a", "#6dbb44", "#4f9330", "#7cc94f"][Math.floor(hash(i, j, 2) * 4)]);
  }},
  diamond: {base: "#4ee6e0", swatch: "linear-gradient(135deg, #a8fff9, #3cc9c4, #2aa3a0)", draw(ctx, s) {
    pixelArt(ctx, s, (i, j) => hash(i, j, 3) > .9 ? "#ffffff" : ["#4ee6e0", "#3cc9c4", "#a8fff9", "#2aa3a0"][Math.floor(hash(i, j, 4) * 4)]);
  }},
  tnt: {base: "#d63a2a", swatch: "linear-gradient(#d63a2a 35%, #f4f1ea 35% 65%, #d63a2a 65%)", draw(ctx, s) {
    pixelArt(ctx, s, i => i % 2 ? "#d63a2a" : "#b52a1e");
    ctx.fillStyle = "#f4f1ea"; ctx.fillRect(-.32 * s, -.075 * s, .62 * s, .15 * s);
    ctx.fillStyle = "#1e1a1a"; ctx.font = `900 ${Math.round(s * .13)}px system-ui, sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText("TNT", -.12 * s, .005 * s);
  }}};

// ---- The packs from STRANGE_PLANET_SKINS.md: Blocky Boom, Spooky, Ninja,
// Dino, Thunder, Sparkle and everyday cool. Added here, after the rest, so the
// lists above stay as they were.

// A face drawn from rows of letters ("#" filled), u the size of one pixel,
// upright when the rover faces up the screen (the face's top is the front).
function pixelFace(ctx, s, rows, cx, u, color) {
  ctx.save(); ctx.translate(cx * s, 0); ctx.rotate(Math.PI / 2);
  const h = rows.length, w = rows[0].length;
  ctx.fillStyle = color;
  rows.forEach((row, j) => [...row].forEach((ch, i) => {
    if (ch === "#") ctx.fillRect((i - w / 2) * u * s, (j - h / 2) * u * s, u * s + .5, u * s + .5);
  }));
  ctx.restore();
}
const CREEPER_FACE = ["........", "........", ".##..##.", ".##..##.", "...##...", "..####..", "..####..", "..#..#.."];
// Little blobs spread over the body, the same every redraw: k picks the place.
function blobs(ctx, s, n, seed, colors, size) {
  for (let k = 0; k < n; k++) {
    ctx.fillStyle = colors[k % colors.length];
    ctx.beginPath();
    ctx.ellipse((-.3 + hash(k, seed) * .58) * s, (-.2 + hash(k, seed + 1) * .4) * s,
                (size + hash(k, seed + 2) * size) * s, (size * .7 + hash(k, seed + 3) * size * .6) * s, hash(k, seed + 4) * 3, 0, 7);
    ctx.fill();
  }
}
Object.assign(PAINTS, {
  creeper: {base: "#5dae3f", swatch: "linear-gradient(90deg, #5dae3f 22%, #10200b 22% 40%, #5dae3f 40% 60%, #10200b 60% 78%, #5dae3f 78%)", draw(ctx, s) {
    pixelArt(ctx, s, (i, j) => ["#5dae3f", "#4f9a35", "#6fc24e", "#8ad66a", "#3f8a2a"][Math.floor(hash(i, j, 50) * 5)]);
    pixelFace(ctx, s, CREEPER_FACE, -.07, .05, "#10200b");
  }},
  skeleton: {base: "#15121c", swatch: "repeating-linear-gradient(90deg, #15121c 0 6px, #e8f4ff 6px 9px)", draw(ctx, s, now) {
    // A spine down the middle and ribs curving off it, glowing a little.
    const k = CALM ? 1 : .75 + .25 * Math.sin(now / 350);
    ctx.strokeStyle = ctx.fillStyle = `rgba(232,244,255,${k})`; ctx.shadowColor = "#bfe3ff"; ctx.shadowBlur = s * .12;
    ctx.lineWidth = s * .035; ctx.lineCap = "round";
    for (const x of [-.2, -.12, -.04]) {
      for (const side of [-1, 1]) {
        ctx.beginPath(); ctx.moveTo(x * s, side * .03 * s); ctx.quadraticCurveTo((x - .02) * s, side * .17 * s, (x - .09) * s, side * .18 * s); ctx.stroke();
      }
    }
    for (let j = 0; j < 8; j++) { roundRect(ctx, (-.3 + j * .055) * s, -.025 * s, .04 * s, .05 * s, .01 * s); ctx.fill(); }
    ctx.shadowBlur = 0;
  }},
  zombie: {base: "#6f9a52", swatch: "linear-gradient(90deg, #2fa7a7 45%, #6f9a52 45%)", draw(ctx, s) {
    // A ragged teal shirt over the back half, stitches over the rest.
    ctx.fillStyle = "#2fa7a7"; ctx.beginPath(); ctx.moveTo(-.32 * s, -.22 * s); ctx.lineTo(-.02 * s, -.22 * s);
    for (let j = 0; j <= 8; j++) ctx.lineTo((j % 2 ? -.06 : .01) * s, (-.22 + j * .055) * s);
    ctx.lineTo(-.32 * s, .22 * s); ctx.fill();
    ctx.fillStyle = "#24898a"; ctx.fillRect(-.2 * s, -.08 * s, .07 * s, .06 * s); ctx.fillRect(-.27 * s, .07 * s, .05 * s, .07 * s);
    ctx.fillStyle = "#587d40"; ctx.fillRect(.05 * s, .1 * s, .08 * s, .07 * s);
    ctx.strokeStyle = "#2c1d24"; ctx.lineWidth = Math.max(1, s * .015);
    ctx.beginPath(); ctx.moveTo(.02 * s, -.16 * s); ctx.lineTo(.2 * s, -.12 * s);
    for (let k = 0; k < 4; k++) { const x = .05 + k * .045, y = -.153 + k * .01; ctx.moveTo(x * s, (y - .03) * s); ctx.lineTo((x + .01) * s, (y + .03) * s); }
    ctx.stroke();
  }},
  ninja: {base: "#16161d", swatch: "linear-gradient(90deg, #16161d 45%, #e3262f 45% 58%, #16161d 58%)", draw(ctx, s) {
    // A red band across the middle and a silver throwing star on the back.
    ctx.fillStyle = "#e3262f"; ctx.fillRect(-.02 * s, -.22 * s, .07 * s, .44 * s);
    ctx.fillStyle = "#2a2a35"; ctx.fillRect(-.32 * s, -.22 * s, .3 * s, .04 * s); ctx.fillRect(-.32 * s, .18 * s, .3 * s, .04 * s);
    ctx.save(); ctx.translate(-.17 * s, 0); ctx.rotate(Math.PI / 4);
    ctx.fillStyle = "#c3cad6";
    ctx.beginPath();
    for (let k = 0; k < 8; k++) { const r = (k % 2 ? .035 : .1) * s, a = k * Math.PI / 4; ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r); }
    ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#16161d"; ctx.beginPath(); ctx.arc(0, 0, s * .018, 0, 7); ctx.fill();
    ctx.restore();
  }},
  dino: {base: "#4caf50", swatch: "radial-gradient(circle at 30% 50%, #ff9d3c 14%, #4caf50 16%)", draw(ctx, s) {
    // Rows of scales, and orange spikes all down the back.
    ctx.strokeStyle = "rgba(30,90,40,.55)"; ctx.lineWidth = Math.max(1, s * .015);
    for (let j = 0; j < 6; j++) for (let i = 0; i < 9; i++) {
      ctx.beginPath(); ctx.arc((-.31 + i * .07 + (j % 2) * .035) * s, (-.2 + j * .08) * s, .035 * s, 0, Math.PI); ctx.stroke();
    }
    ctx.fillStyle = "#ff9d3c"; ctx.strokeStyle = "#c2621a";
    for (let k = 0; k < 6; k++) {
      const x = -.3 + k * .07, h = .06 + (k > 0 && k < 5 ? .025 : 0);
      ctx.beginPath(); ctx.moveTo(x * s, 0); ctx.lineTo((x + .035) * s, -h * s); ctx.lineTo((x + .07) * s, 0); ctx.lineTo((x + .035) * s, h * s); ctx.closePath(); ctx.fill(); ctx.stroke();
    }
  }},
  storm: {base: "#2b3350", swatch: "linear-gradient(135deg, #2b3350 40%, #ffe14d 40% 50%, #2b3350 50% 60%, #ffe14d 60% 66%, #2b3350 66%)", draw(ctx, s, now) {
    // Dark clouds, and a bolt that flashes every so often.
    blobs(ctx, s, 7, 60, ["#4a5370", "#3b4360", "#5a6382"], .08);
    const t = CALM ? 0 : now % 1700, k = t < 120 || (t > 220 && t < 300) ? 1 : .45;
    if (k === 1) { ctx.fillStyle = "rgba(220,235,255,.35)"; ctx.fillRect(-.32 * s, -.22 * s, .62 * s, .44 * s); }
    ctx.fillStyle = `rgba(255,225,77,${k})`; ctx.shadowColor = "#ffe14d"; ctx.shadowBlur = s * .2 * k;
    ctx.beginPath();
    for (const [x, y] of [[.06, -.22], [-.05, -.02], [.02, -.02], [-.1, .22], [.0, .03], [-.06, .03], [.12, -.22]]) ctx.lineTo(x * s, y * s);
    ctx.fill(); ctx.shadowBlur = 0;
  }},
  cottoncandy: {base: "#ffb3d9", swatch: "linear-gradient(135deg, #ffb3d9, #b3e0ff)", fill(ctx, s) {
    const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
    grad.addColorStop(0, "#ffb3d9"); grad.addColorStop(.5, "#e7c6ff"); grad.addColorStop(1, "#b3e0ff");
    return grad;
  }, draw(ctx, s) {
    for (let k = 0; k < 18; k++) {
      ctx.save(); ctx.translate((-.29 + hash(k, 70) * .56) * s, (-.19 + hash(k, 71) * .38) * s); ctx.rotate(hash(k, 72) * 3);
      ctx.fillStyle = ["#ff4d8d", "#ffd34d", "#4dc3ff", "#7ff07a", "#ffffff"][k % 5];
      ctx.fillRect(-.02 * s, -.006 * s, .04 * s, .012 * s + .5);
      ctx.restore();
    }
  }},
  camo: {base: "#5b6b3a", swatch: "radial-gradient(circle at 30% 35%, #3e4a26 20%, transparent 22%), radial-gradient(circle at 70% 65%, #8a7d4f 20%, #5b6b3a 22%)", draw(ctx, s) {
    blobs(ctx, s, 12, 80, ["#3e4a26", "#8a7d4f", "#2b2f1c"], .06);
  }},
  watermelon: {base: "#ff4f6d", swatch: "radial-gradient(circle, #ff4f6d 50%, #f4ffe0 52% 60%, #3f9a3a 62%)", draw(ctx, s) {
    roundRect(ctx, -.32 * s, -.22 * s, .62 * s, .44 * s, .08 * s);
    ctx.strokeStyle = "#3f9a3a"; ctx.lineWidth = s * .1; ctx.stroke();
    ctx.strokeStyle = "#f4ffe0"; ctx.lineWidth = s * .03;
    roundRect(ctx, -.27 * s, -.17 * s, .52 * s, .34 * s, .05 * s); ctx.stroke();
    ctx.fillStyle = "#2a1414";
    for (const [x, y] of [[-.18, -.06], [-.08, .06], [.0, -.07], [.1, .05], [-.2, .07], [.12, -.06], [-.1, -.03]]) {
      ctx.beginPath(); ctx.ellipse(x * s, y * s, .013 * s, .022 * s, .5, 0, 7); ctx.fill();
    }
  }},
  tiger: {base: "#ff9a2e", swatch: "repeating-linear-gradient(90deg, #ff9a2e 0 7px, #1e1410 7px 10px)", draw(ctx, s) {
    // Black stripes that taper in from both sides.
    ctx.fillStyle = "#1e1410";
    for (let k = 0; k < 6; k++) for (const side of [-1, 1]) {
      const x = -.28 + k * .1 + hash(k, side + 90) * .02, d = .11 + hash(k, side + 92) * .05;
      ctx.beginPath(); ctx.moveTo((x - .025) * s, side * .23 * s); ctx.quadraticCurveTo((x + .03) * s, side * (.23 - d / 2) * s, (x + .01) * s, side * (.23 - d) * s);
      ctx.lineTo((x + .025) * s, side * .23 * s); ctx.fill();
    }
  }},
});

Object.assign(GLOWS, {
  jacko(ctx, s, now) {   // an orange glow that flickers like a candle
    underglow(ctx, s, "255,140,30", CALM ? .9 : .65 + .35 * hash(Math.floor(now / 90), 3));
  },
  toxic(ctx, s, now) {   // green goo underneath, bubbles rising and popping
    underglow(ctx, s, "120,255,60", pulse(now, 340));
    for (let k = 0; k < 6; k++) {
      const u = CALM ? .5 : ((now / 1300 + hash(k, 100)) % 1), a = hash(k, 101) * 7;
      const x = Math.cos(a) * s * .5, y = Math.sin(a) * s * .42 - u * s * .1;
      ctx.strokeStyle = `rgba(190,255,120,${1 - u})`; ctx.lineWidth = Math.max(1, s * .02);
      ctx.beginPath(); ctx.arc(x, y, s * (.03 + u * .04), 0, 7); ctx.stroke();
    }
  },
  electric(ctx, s, now) {   // sparks crackling round the rover
    underglow(ctx, s, "90,200,255", .55);
    const frame = CALM ? 0 : Math.floor(now / 80);
    ctx.strokeStyle = "#e6f8ff"; ctx.lineWidth = Math.max(1, s * .02); ctx.shadowColor = "#5ac8ff"; ctx.shadowBlur = s * .2;
    for (let b = 0; b < 4; b++) {
      const a = hash(b, frame, 110) * 7, len = .25 + hash(b, frame, 111) * .2;
      ctx.beginPath();
      for (let j = 0; j <= 4; j++) {
        const r = (.38 + j * len / 4) * s, wob = (hash(b, frame, j + 112) - .5) * .5;
        ctx.lineTo(Math.cos(a + wob * .3) * r, Math.sin(a + wob * .3) * r * .85);
      }
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
  },
  blackhole(ctx, s, now) {   // a dark swirl underneath, specks spiralling in
    const grad = ctx.createRadialGradient(0, 0, s * .1, 0, 0, s * .75);
    grad.addColorStop(0, "rgba(0,0,0,.9)"); grad.addColorStop(.55, "rgba(60,20,120,.55)"); grad.addColorStop(.75, "rgba(255,140,60,.35)"); grad.addColorStop(1, "rgba(255,140,60,0)");
    ctx.fillStyle = grad; ctx.beginPath(); ctx.ellipse(0, 0, s * .75, s * .62, 0, 0, 7); ctx.fill();
    for (let k = 0; k < 10; k++) {
      const u = CALM ? hash(k, 120) : (now / 2400 + hash(k, 120)) % 1, a = hash(k, 121) * 7 + u * 5, r = s * .75 * (1 - u);
      ctx.fillStyle = `rgba(255,${200 - k * 8},${160 + k * 8},${u})`;
      ctx.beginPath(); ctx.arc(Math.cos(a) * r, Math.sin(a) * r * .82, s * .02, 0, 7); ctx.fill();
    }
  },
});

Object.assign(PETS, {
  bat(ctx, s, t) {   // a little bat, wings beating, fangs out
    const flap = Math.sin(t / 70);
    ctx.fillStyle = "#4a2f6b";
    for (const side of [-1, 1]) {
      ctx.save(); ctx.scale(side, 1); ctx.rotate(flap * .35);
      ctx.beginPath(); ctx.moveTo(.1 * s, -.05 * s); ctx.lineTo(.55 * s, -.25 * s);
      ctx.quadraticCurveTo(.48 * s, -.05 * s, .55 * s, .08 * s); ctx.quadraticCurveTo(.42 * s, .02 * s, .35 * s, .12 * s);
      ctx.quadraticCurveTo(.25 * s, .05 * s, .1 * s, .1 * s); ctx.fill(); ctx.restore();
    }
    ctx.fillStyle = "#3a2356"; ctx.beginPath(); ctx.ellipse(0, 0, .17 * s, .22 * s, 0, 0, 7); ctx.fill();
    for (const x of [-.1, .1]) { ctx.beginPath(); ctx.moveTo((x - .06) * s, -.12 * s); ctx.lineTo(x * 1.6 * s, -.34 * s); ctx.lineTo((x + .06) * s, -.12 * s); ctx.fill(); }
    eyes(ctx, s, [-.07, .07], -.05, .045);
    ctx.fillStyle = "#ffffff";
    for (const x of [-.04, .04]) { ctx.beginPath(); ctx.moveTo((x - .02) * s, .06 * s); ctx.lineTo(x * s, .12 * s); ctx.lineTo((x + .02) * s, .06 * s); ctx.fill(); }
  },
  axolotl(ctx, s, t) {   // pink, smiling, frilly gills that wiggle
    ctx.fillStyle = "#ff9ec4";
    ctx.beginPath(); ctx.ellipse(-.05 * s, .22 * s, .3 * s, .12 * s, Math.sin(t / 300) * .15, 0, 7); ctx.fill();
    for (const side of [-1, 1]) for (let k = 0; k < 3; k++) {
      const a = side * (.7 + k * .45) - Math.PI / 2 + Math.sin(t / 160 + k) * .12 * side;
      ctx.strokeStyle = "#e0558f"; ctx.lineWidth = s * .07; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(Math.cos(a) * .22 * s, -.05 * s + Math.sin(a) * .22 * s); ctx.lineTo(Math.cos(a) * .42 * s, -.05 * s + Math.sin(a) * .42 * s); ctx.stroke();
    }
    ctx.fillStyle = "#ffb3d2"; ctx.beginPath(); ctx.ellipse(0, -.05 * s, .3 * s, .24 * s, 0, 0, 7); ctx.fill();
    eyes(ctx, s, [-.13, .13], -.08, .045);
    ctx.strokeStyle = "#a0335e"; ctx.lineWidth = s * .025;
    ctx.beginPath(); ctx.arc(0, .0, .08 * s, .2 * Math.PI, .8 * Math.PI); ctx.stroke();
    ctx.fillStyle = "rgba(255,90,140,.45)";
    for (const x of [-.2, .2]) { ctx.beginPath(); ctx.arc(x * s, .03 * s, .04 * s, 0, 7); ctx.fill(); }
  },
  slimecube(ctx, s, t) {   // a see-through green cube that squishes as it bounces
    const squish = 1 + Math.sin(t / 160) * .1;
    ctx.scale(1 / squish, squish);
    ctx.fillStyle = "rgba(110,210,80,.75)"; roundRect(ctx, -.3 * s, -.3 * s, .6 * s, .6 * s, .06 * s); ctx.fill();
    ctx.strokeStyle = "#3f8a2a"; ctx.lineWidth = s * .03; ctx.stroke();
    ctx.fillStyle = "rgba(70,160,50,.8)"; ctx.fillRect(-.16 * s, -.12 * s, .32 * s, .3 * s);
    ctx.fillStyle = "#1e3a14"; ctx.fillRect(-.14 * s, -.1 * s, .08 * s, .08 * s); ctx.fillRect(.06 * s, -.1 * s, .08 * s, .08 * s);
    ctx.fillRect(-.03 * s, .06 * s, .06 * s, .04 * s);
    ctx.fillStyle = "rgba(255,255,255,.45)"; ctx.fillRect(-.26 * s, -.26 * s, .1 * s, .05 * s);
  },
  trex(ctx, s, t) {   // a tiny T. rex, jaw chomping, little arms
    const chomp = Math.max(0, Math.sin(t / 180)) * .25;
    ctx.fillStyle = "#4caf50";
    ctx.beginPath(); ctx.moveTo(-.15 * s, .1 * s); ctx.quadraticCurveTo(-.45 * s, .2 * s, -.55 * s, .02 * s); ctx.lineTo(-.15 * s, -.05 * s); ctx.fill();
    ctx.beginPath(); ctx.ellipse(-.05 * s, .1 * s, .2 * s, .22 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#3a8f3e"; for (const x of [-.12, .04]) ctx.fillRect(x * s, .26 * s, .08 * s, .1 * s);
    ctx.strokeStyle = "#3a8f3e"; ctx.lineWidth = s * .05; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(.1 * s, .08 * s); ctx.lineTo(.18 * s, .14 * s); ctx.stroke();
    ctx.save(); ctx.translate(.08 * s, -.18 * s);
    ctx.fillStyle = "#4caf50"; ctx.beginPath(); ctx.ellipse(.08 * s, 0, .2 * s, .13 * s, 0, 0, 7); ctx.fill();
    ctx.save(); ctx.rotate(chomp); ctx.fillStyle = "#3a8f3e"; ctx.beginPath(); ctx.ellipse(.12 * s, .1 * s, .16 * s, .05 * s, 0, 0, 7); ctx.fill(); ctx.restore();
    ctx.fillStyle = "#ffffff"; for (let k = 0; k < 3; k++) { ctx.beginPath(); ctx.moveTo((.1 + k * .06) * s, .07 * s); ctx.lineTo((.13 + k * .06) * s, .12 * s); ctx.lineTo((.16 + k * .06) * s, .07 * s); ctx.fill(); }
    eyes(ctx, s, [.06], -.04, .04);
    ctx.restore();
  },
  penguin(ctx, s, t) {   // a penguin, waddling
    ctx.rotate(Math.sin(t / 180) * .15);
    ctx.fillStyle = "#ff9d3c"; for (const x of [-.1, .1]) { ctx.beginPath(); ctx.ellipse(x * s, .36 * s, .09 * s, .04 * s, 0, 0, 7); ctx.fill(); }
    ctx.fillStyle = "#1e1e2e"; ctx.beginPath(); ctx.ellipse(0, .05 * s, .26 * s, .34 * s, 0, 0, 7); ctx.fill();
    for (const side of [-1, 1]) { ctx.beginPath(); ctx.ellipse(side * .26 * s, .08 * s, .06 * s, .18 * s, side * -.3, 0, 7); ctx.fill(); }
    ctx.fillStyle = "#ffffff"; ctx.beginPath(); ctx.ellipse(0, .12 * s, .17 * s, .25 * s, 0, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.ellipse(0, -.12 * s, .16 * s, .12 * s, 0, 0, 7); ctx.fill();
    eyes(ctx, s, [-.07, .07], -.14, .035);
    ctx.fillStyle = "#ff9d3c"; ctx.beginPath(); ctx.moveTo(-.05 * s, -.07 * s); ctx.lineTo(.05 * s, -.07 * s); ctx.lineTo(0, .0); ctx.fill();
  },
  minicreeper(ctx, s, t) {   // a little blocky creeper that flashes white now and then
    const flash = t % 3000 > 2600 && Math.floor(t / 100) % 2 === 0;
    ctx.fillStyle = "#3f8a2a"; for (const x of [-.2, .06]) ctx.fillRect(x * s, .26 * s, .14 * s, .12 * s);
    ctx.fillStyle = flash ? "#ffffff" : "#5dae3f"; ctx.fillRect(-.16 * s, -.05 * s, .32 * s, .34 * s);
    for (let j = 0; j < 4; j++) for (let i = 0; i < 3; i++) {
      if (flash) continue;
      ctx.fillStyle = ["#4f9a35", "#6fc24e", "#5dae3f"][Math.floor(hash(i, j, 130) * 3)];
      ctx.fillRect((-.16 + i * .107) * s, (-.05 + j * .085) * s, .107 * s + .5, .085 * s + .5);
    }
    ctx.fillStyle = flash ? "#ffffff" : "#6fc24e"; ctx.fillRect(-.24 * s, -.5 * s, .48 * s, .46 * s);
    const u = .06;
    ctx.fillStyle = "#10200b";
    CREEPER_FACE.forEach((row, j) => [...row].forEach((ch, i) => {
      if (ch === "#") ctx.fillRect((-.24 + i * u) * s, (-.5 + j * u * .96) * s, u * s + .5, u * .96 * s + .5);
    }));
  },
});

// ---- Batch 3 from STRANGE_PLANET_SKINS.md: animal prints, the Speedway,
// snacks and a robot. Several unlock with the coding badges.

// Turned so a drawing's top is the rover's front, like pixelFace: upright
// when the rover faces up the screen.
function faceForward(ctx, s, cx, fn) {
  ctx.save(); ctx.translate(cx * s, 0); ctx.rotate(Math.PI / 2); fn(); ctx.restore();
}
Object.assign(PAINTS, {
  cow: {base: "#f7f4ee", swatch: "radial-gradient(circle at 30% 35%, #1e1a1a 22%, transparent 24%), radial-gradient(circle at 72% 70%, #1e1a1a 18%, #f7f4ee 20%)", draw(ctx, s) {
    // Black patches, each two blobs so it isn't a plain oval.
    ctx.fillStyle = "#1e1a1a";
    for (const [x, y, r, a] of [[-.22, -.12, .08, .4], [-.04, .13, .09, -.3], [.12, -.15, .06, .8], [-.27, .15, .05, 0], [.22, .12, .05, .2]]) {
      ctx.beginPath(); ctx.ellipse(x * s, y * s, r * s, r * .75 * s, a, 0, 7); ctx.fill();
      ctx.beginPath(); ctx.ellipse((x + r * .6) * s, (y + r * .4) * s, r * .6 * s, r * .5 * s, -a, 0, 7); ctx.fill();
    }
  }},
  ladybug: {base: "#e8262f", swatch: "radial-gradient(circle at 30% 30%, #16121a 12%, transparent 14%), radial-gradient(circle at 70% 68%, #16121a 12%, #e8262f 14%)", draw(ctx, s) {
    // A black head at the front, a line where the wings meet, and spots.
    ctx.fillStyle = "#16121a";
    ctx.fillRect(.14 * s, -.22 * s, .16 * s, .44 * s);
    ctx.fillRect(-.32 * s, -.012 * s, .46 * s, .024 * s);
    for (const [x, y, r] of [[-.22, -.11, .045], [-.22, .11, .045], [-.06, -.14, .05], [-.06, .14, .05], [-.28, 0, .04], [.07, -.08, .035], [.07, .08, .035]]) {
      ctx.beginPath(); ctx.arc(x * s, y * s, r * s, 0, 7); ctx.fill();
    }
    ctx.fillStyle = "#ffffff";
    for (const y of [-.16, .16]) { ctx.beginPath(); ctx.arc(.22 * s, y * s, .025 * s, 0, 7); ctx.fill(); }
    ctx.fillStyle = "rgba(255,255,255,.3)"; ctx.beginPath(); ctx.ellipse(-.14 * s, -.17 * s, .08 * s, .025 * s, 0, 0, 7); ctx.fill();
  }},
  racecar: {base: "#e3262f", swatch: "linear-gradient(#e3262f 28%, #ffffff 28% 40%, #e3262f 40% 60%, #ffffff 60% 72%, #e3262f 72%)", draw(ctx, s) {
    // Two stripes nose to tail, a chequered tail and a number 1.
    ctx.fillStyle = "#ffffff";
    for (const y of [-.075, .035]) ctx.fillRect(-.32 * s, y * s, .62 * s, .04 * s);
    for (let j = 0; j < 8; j++) for (let i = 0; i < 2; i++) {
      ctx.fillStyle = (i + j) % 2 ? "#16121a" : "#ffffff";
      ctx.fillRect((-.32 + i * .055) * s, (-.22 + j * .055) * s, .055 * s + .5, .055 * s + .5);
    }
    ctx.fillStyle = "#ffffff"; ctx.strokeStyle = "#16121a"; ctx.lineWidth = Math.max(1, s * .015);
    ctx.beginPath(); ctx.arc(-.09 * s, 0, .09 * s, 0, 7); ctx.fill(); ctx.stroke();
    faceForward(ctx, s, -.09, () => {
      ctx.fillStyle = "#16121a"; ctx.font = `900 ${Math.round(s * .13)}px system-ui, sans-serif`;
      ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText("1", 0, .005 * s);
    });
  }},
  robot: {base: "#aeb6c4", swatch: "radial-gradient(circle at 30% 50%, #ff5a5a 10%, transparent 12%), radial-gradient(circle at 55% 50%, #4dff88 10%, transparent 12%), linear-gradient(135deg, #dfe4ec, #8a94a3)", fill(ctx, s) {
    const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
    grad.addColorStop(0, "#dfe4ec"); grad.addColorStop(.5, "#aeb6c4"); grad.addColorStop(1, "#8a94a3");
    return grad;
  }, draw(ctx, s, now) {
    // Panels and rivets, a vent at the back, and lights that blink in turn.
    ctx.strokeStyle = "rgba(60,66,84,.55)"; ctx.lineWidth = Math.max(1, s * .012);
    ctx.beginPath();
    for (const x of [-.13, .07]) { ctx.moveTo(x * s, -.22 * s); ctx.lineTo(x * s, .22 * s); }
    ctx.moveTo(-.32 * s, -.11 * s); ctx.lineTo(-.13 * s, -.11 * s); ctx.moveTo(-.32 * s, .11 * s); ctx.lineTo(-.13 * s, .11 * s);
    ctx.stroke();
    ctx.fillStyle = "#6e7a90";
    for (const x of [-.29, -.16, -.1, .04, .1, .27]) for (const y of [-.19, .19]) { ctx.beginPath(); ctx.arc(x * s, y * s, .012 * s, 0, 7); ctx.fill(); }
    ctx.fillStyle = "#3a4054";
    for (let k = 0; k < 4; k++) roundRect(ctx, -.28 * s, (-.075 + k * .042) * s, .11 * s, .022 * s, .01 * s), ctx.fill();
    const lit = CALM ? -1 : Math.floor(now / 300) % 3;
    ["#ff5a5a", "#ffd34d", "#4dff88"].forEach((color, k) => {
      const on = lit === -1 || lit === k;
      ctx.fillStyle = on ? color : "#4a5062"; ctx.shadowColor = color; ctx.shadowBlur = on ? s * .12 : 0;
      ctx.beginPath(); ctx.arc(-.03 * s, (-.09 + k * .09) * s, .025 * s, 0, 7); ctx.fill();
    });
    ctx.shadowBlur = 0;
  }},
  cheetah: {base: "#f2b440", swatch: "radial-gradient(circle at 25% 30%, #2a1a0e 9%, transparent 11%), radial-gradient(circle at 60% 65%, #2a1a0e 9%, transparent 11%), radial-gradient(circle at 82% 25%, #2a1a0e 8%, #f2b440 10%)", fill(ctx, s) {
    const grad = ctx.createLinearGradient(0, -.22 * s, 0, .22 * s);
    grad.addColorStop(0, "#e0a030"); grad.addColorStop(.5, "#f7c459"); grad.addColorStop(1, "#e0a030");
    return grad;
  }, draw(ctx, s) {
    ctx.fillStyle = "#2a1a0e";
    for (let k = 0; k < 24; k++) {
      ctx.beginPath();
      ctx.ellipse((-.3 + hash(k, 140) * .58) * s, (-.2 + hash(k, 141) * .4) * s, (.018 + hash(k, 142) * .014) * s, (.016 + hash(k, 143) * .01) * s, hash(k, 144) * 3, 0, 7);
      ctx.fill();
    }
  }},
  zebra: {base: "#f7f7f2", swatch: "repeating-linear-gradient(100deg, #f7f7f2 0 6px, #16121a 6px 10px)", draw(ctx, s) {
    // Wavy black stripes from side to side.
    ctx.strokeStyle = "#16121a"; ctx.lineWidth = s * .032; ctx.lineCap = "round";
    for (let k = 0; k < 9; k++) {
      const x = -.31 + k * .075, bend = k % 2 ? .035 : -.035;
      ctx.beginPath(); ctx.moveTo(x * s, -.24 * s);
      ctx.quadraticCurveTo((x + bend) * s, -.11 * s, x * s, 0); ctx.quadraticCurveTo((x - bend) * s, .11 * s, x * s, .24 * s);
      ctx.stroke();
    }
  }},
  banana: {base: "#ffe14d", swatch: "linear-gradient(90deg, #4a2f14 0 7%, #ffe14d 7% 93%, #4a2f14 93%)", fill(ctx, s) {
    // Rounder in the middle, like a real banana.
    const grad = ctx.createLinearGradient(0, -.22 * s, 0, .22 * s);
    grad.addColorStop(0, "#e8b923"); grad.addColorStop(.5, "#fff07a"); grad.addColorStop(1, "#e8b923");
    return grad;
  }, draw(ctx, s) {
    ctx.strokeStyle = "rgba(190,140,20,.55)"; ctx.lineWidth = Math.max(1, s * .012);
    ctx.beginPath();
    for (const y of [-.09, .09]) { ctx.moveTo(-.32 * s, y * s); ctx.quadraticCurveTo(0, y * 1.25 * s, .3 * s, y * s); }
    ctx.stroke();
    ctx.fillStyle = "#4a2f14";
    ctx.fillRect(-.32 * s, -.22 * s, .035 * s, .44 * s); ctx.fillRect(.265 * s, -.22 * s, .035 * s, .44 * s);
    ctx.fillStyle = "rgba(110,70,20,.6)";
    for (let k = 0; k < 7; k++) { ctx.beginPath(); ctx.arc((-.26 + hash(k, 150) * .5) * s, (-.18 + hash(k, 151) * .36) * s, .01 * s, 0, 7); ctx.fill(); }
  }},
  panda: {base: "#f7f7f2", swatch: "radial-gradient(circle at 35% 42%, #1a1a1f 12%, transparent 14%), radial-gradient(circle at 65% 42%, #1a1a1f 12%, #f7f7f2 14%)", draw(ctx, s) {
    // Black shoulders and paws, and a panda face looking forward.
    ctx.fillStyle = "#1a1a1f";
    ctx.fillRect(.06 * s, -.22 * s, .09 * s, .44 * s);
    for (const y of [-.22, .22]) { ctx.beginPath(); ctx.ellipse(-.3 * s, y * s, .07 * s, .06 * s, 0, 0, 7); ctx.fill(); }
    faceForward(ctx, s, -.13, () => {
      for (const x of [-.1, .1]) { ctx.beginPath(); ctx.arc(x * s, -.1 * s, .045 * s, 0, 7); ctx.fill(); }
      ctx.fillStyle = "#ffffff"; ctx.strokeStyle = "#c9c9c4"; ctx.lineWidth = Math.max(1, s * .01);
      ctx.beginPath(); ctx.arc(0, 0, .12 * s, 0, 7); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#1a1a1f";
      for (const side of [-1, 1]) { ctx.beginPath(); ctx.ellipse(side * .05 * s, -.01 * s, .032 * s, .045 * s, side * -.5, 0, 7); ctx.fill(); }
      ctx.beginPath(); ctx.ellipse(0, .05 * s, .025 * s, .016 * s, 0, 0, 7); ctx.fill();
      ctx.fillStyle = "#ffffff";
      for (const x of [-.045, .045]) { ctx.beginPath(); ctx.arc(x * s, -.018 * s, .011 * s, 0, 7); ctx.fill(); }
    });
  }},
  firetruck: {base: "#d7261e", swatch: "repeating-linear-gradient(90deg, #d7261e 0 6px, #dfe4ec 6px 8px)", draw(ctx, s, now) {
    // White side stripes, a silver ladder on top, lights at the front.
    ctx.fillStyle = "#f4f1ea";
    ctx.fillRect(-.32 * s, -.2 * s, .62 * s, .03 * s); ctx.fillRect(-.32 * s, .17 * s, .62 * s, .03 * s);
    ctx.strokeStyle = "#dfe4ec"; ctx.lineWidth = Math.max(1, s * .02);
    ctx.beginPath();
    for (const y of [-.07, .07]) { ctx.moveTo(-.3 * s, y * s); ctx.lineTo(.06 * s, y * s); }
    for (let x = -.28; x < .06; x += .05) { ctx.moveTo(x * s, -.07 * s); ctx.lineTo(x * s, .07 * s); }
    ctx.stroke();
    const red = CALM || Math.floor(now / 250) % 2 === 0;
    for (const [y, on] of [[-.15, red], [.15, CALM || !red]]) {
      ctx.fillStyle = on ? "#ff3b3b" : "#7a1a1a"; ctx.shadowColor = "#ff3b3b"; ctx.shadowBlur = on ? s * .15 : 0;
      ctx.beginPath(); ctx.arc(.25 * s, y * s, .03 * s, 0, 7); ctx.fill();
    }
    ctx.shadowBlur = 0;
  }},
  bumblebee: {base: "#ffd02e", swatch: "repeating-linear-gradient(90deg, #ffd02e 0 7px, #1e1a1a 7px 12px)", draw(ctx, s, now) {
    // Black stripes across, and see-through wings that buzz.
    ctx.fillStyle = "#1e1a1a";
    for (const x of [-.3, -.18, -.06]) ctx.fillRect(x * s, -.22 * s, .06 * s, .44 * s);
    const buzz = CALM ? 1 : .8 + .2 * Math.sin(now / 30);
    ctx.fillStyle = "rgba(225,245,255,.6)"; ctx.strokeStyle = "rgba(255,255,255,.85)"; ctx.lineWidth = Math.max(1, s * .01);
    for (const side of [-1, 1]) {
      ctx.beginPath(); ctx.ellipse(-.1 * s, side * .1 * s, .15 * s, .07 * s * buzz, side * .45, 0, 7); ctx.fill(); ctx.stroke();
    }
  }},
  hotrod: {base: "#16121a", swatch: "linear-gradient(90deg, #16121a 35%, #ff3d1f 35% 55%, #ffb21f 55% 72%, #ffe66b 72% 80%, #16121a 80%)", draw(ctx, s, now) {
    // Flames licking back from the front, in three colours.
    const t = CALM ? 0 : now / 140;
    for (const [color, len] of [["#ff3d1f", 1], ["#ffb21f", .72], ["#ffe66b", .45]]) {
      ctx.fillStyle = color; ctx.beginPath(); ctx.moveTo(.31 * s, -.23 * s);
      for (let j = 0; j < 5; j++) {
        const tip = .3 - len * (.42 + .14 * hash(j, 160) + .03 * Math.sin(t + j * 1.7)), y = -.2 + j * .1;
        ctx.quadraticCurveTo((tip + .12 * len) * s, (y - .03) * s, tip * s, y * s);
        ctx.quadraticCurveTo((tip + .1 * len) * s, (y + .04) * s, (.3 - len * .12) * s, (y + .05) * s);
      }
      ctx.lineTo(.31 * s, .23 * s); ctx.closePath(); ctx.fill();
    }
  }},
  sharkbite: {base: "#7d93a8", swatch: "linear-gradient(90deg, #7d93a8 66%, #f4f1ea 66% 72%, #7a1020 72% 82%, #f4f1ea 82% 88%, #7d93a8 88%)", fill(ctx, s) {
    const grad = ctx.createLinearGradient(0, -.22 * s, 0, .22 * s);
    grad.addColorStop(0, "#9fb2c4"); grad.addColorStop(.5, "#5f758c"); grad.addColorStop(1, "#9fb2c4");
    return grad;
  }, draw(ctx, s) {
    // Gills down each side, and a toothy grin round the nose.
    ctx.strokeStyle = "#3e4f60"; ctx.lineWidth = Math.max(1, s * .015);
    ctx.beginPath();
    for (const x of [-.04, 0, .04]) for (const side of [-1, 1]) {
      ctx.moveTo(x * s, side * .22 * s); ctx.quadraticCurveTo((x - .02) * s, side * .18 * s, x * s, side * .14 * s);
    }
    ctx.stroke();
    ctx.strokeStyle = "#7a1020"; ctx.lineWidth = s * .07;
    ctx.beginPath(); ctx.arc(.02 * s, 0, .25 * s, -1.05, 1.05); ctx.stroke();
    ctx.fillStyle = "#ffffff";
    for (let k = -6; k <= 6; k++) {
      const a = k * .17;
      for (const [r, dir] of [[.215, 1], [.285, -1]]) {
        const x = .02 + Math.cos(a) * r, y = Math.sin(a) * r, w = .022;
        ctx.beginPath(); ctx.moveTo((x - Math.sin(a) * w) * s, (y + Math.cos(a) * w) * s);
        ctx.lineTo((x + Math.cos(a) * .035 * dir) * s, (y + Math.sin(a) * .035 * dir) * s);
        ctx.lineTo((x + Math.sin(a) * w) * s, (y - Math.cos(a) * w) * s); ctx.fill();
      }
    }
    ctx.fillStyle = "#16121a";
    for (const y of [-.17, .17]) { ctx.beginPath(); ctx.arc(.13 * s, y * s, .025 * s, 0, 7); ctx.fill(); }
  }},
  armor: {base: "#4fd8d4", swatch: "linear-gradient(135deg, #b8fffb, #4fd8d4 45%, #2a9ea0 55%, #8af3ef)", fill(ctx, s) {
    const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
    grad.addColorStop(0, "#a8fff9"); grad.addColorStop(.5, "#4fd8d4"); grad.addColorStop(1, "#2aa3a0");
    return grad;
  }, draw(ctx, s, now) {
    // Plates overlapping front to back, rivets, and a glint sweeping over.
    ctx.lineWidth = Math.max(1, s * .02);
    for (let k = 1; k < 5; k++) {
      const x = -.32 + k * .125;
      ctx.strokeStyle = "rgba(20,90,95,.6)";
      ctx.beginPath(); ctx.moveTo(x * s, -.22 * s); ctx.quadraticCurveTo((x + .04) * s, 0, x * s, .22 * s); ctx.stroke();
      ctx.strokeStyle = "rgba(230,255,253,.7)";
      ctx.beginPath(); ctx.moveTo((x + .015) * s, -.22 * s); ctx.quadraticCurveTo((x + .055) * s, 0, (x + .015) * s, .22 * s); ctx.stroke();
    }
    ctx.fillStyle = "#e8fffd";
    for (let k = 0; k < 5; k++) for (const y of [-.17, .17]) { ctx.beginPath(); ctx.arc((-.29 + k * .125) * s, y * s, .014 * s, 0, 7); ctx.fill(); }
    const g = CALM ? .35 : (now / 1800) % 1.6 - .3;
    ctx.fillStyle = "rgba(255,255,255,.45)";
    ctx.beginPath(); ctx.moveTo((-.45 + g * .8) * s, .22 * s); ctx.lineTo((-.35 + g * .8) * s, -.22 * s);
    ctx.lineTo((-.29 + g * .8) * s, -.22 * s); ctx.lineTo((-.39 + g * .8) * s, .22 * s); ctx.fill();
  }},
});

Object.assign(PETS, {
  bunny(ctx, s, t) {   // a white bunny that hops, one ear twitching now and then
    ctx.translate(0, -Math.abs(Math.sin(t / 260)) * .1 * s);
    ctx.strokeStyle = "#c9c3d6"; ctx.lineWidth = Math.max(1, s * .025);
    for (const side of [-1, 1]) {
      const twitch = side > 0 && t % 2400 > 2150 ? .45 : 0;
      ctx.save(); ctx.translate(side * .1 * s, -.28 * s); ctx.rotate(side * (.15 + twitch));
      ctx.fillStyle = "#ffffff"; ctx.beginPath(); ctx.ellipse(0, -.16 * s, .075 * s, .2 * s, 0, 0, 7); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#ffb3cf"; ctx.beginPath(); ctx.ellipse(0, -.15 * s, .035 * s, .14 * s, 0, 0, 7); ctx.fill();
      ctx.restore();
    }
    ctx.fillStyle = "#ffffff";
    ctx.beginPath(); ctx.ellipse(0, .18 * s, .26 * s, .2 * s, 0, 0, 7); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, -.1 * s, .22 * s, 0, 7); ctx.fill(); ctx.stroke();
    eyes(ctx, s, [-.08, .08], -.13, .04);
    ctx.fillStyle = "#ff8ab3"; ctx.beginPath(); ctx.moveTo(-.035 * s, -.04 * s); ctx.lineTo(.035 * s, -.04 * s); ctx.lineTo(0, 0); ctx.fill();
    ctx.fillStyle = "rgba(255,140,180,.4)";
    for (const x of [-.14, .14]) { ctx.beginPath(); ctx.arc(x * s, -.03 * s, .035 * s, 0, 7); ctx.fill(); }
  },
  buzzy(ctx, s, t) {   // a round little bee, wings a blur
    const flap = Math.abs(Math.sin(t / 25));
    ctx.fillStyle = "rgba(225,245,255,.7)"; ctx.strokeStyle = "rgba(255,255,255,.9)"; ctx.lineWidth = Math.max(1, s * .02);
    for (const side of [-1, 1]) {
      ctx.beginPath(); ctx.ellipse(side * .2 * s, -.25 * s, .15 * s, (.1 + .1 * flap) * s, side * -.5, 0, 7); ctx.fill(); ctx.stroke();
    }
    ctx.strokeStyle = "#1e1a1a"; ctx.lineWidth = s * .03; ctx.lineCap = "round";
    for (const side of [-1, 1]) {
      ctx.beginPath(); ctx.moveTo(side * .06 * s, -.22 * s); ctx.lineTo(side * .12 * s, -.38 * s); ctx.stroke();
      ctx.fillStyle = "#1e1a1a"; ctx.beginPath(); ctx.arc(side * .12 * s, -.38 * s, .035 * s, 0, 7); ctx.fill();
    }
    ctx.save();
    ctx.beginPath(); ctx.ellipse(0, .02 * s, .3 * s, .27 * s, 0, 0, 7);
    ctx.fillStyle = "#ffd02e"; ctx.fill(); ctx.clip();
    ctx.fillStyle = "#1e1a1a"; for (const y of [.08, .2]) ctx.fillRect(-.3 * s, y * s, .6 * s, .06 * s);
    ctx.restore();
    eyes(ctx, s, [-.09, .09], -.07, .045);
    ctx.strokeStyle = "#1e1a1a"; ctx.lineWidth = s * .025;
    ctx.beginPath(); ctx.arc(0, -.02 * s, .05 * s, .2 * Math.PI, .8 * Math.PI); ctx.stroke();
  },
});

// The Paint Shop's paint: 70 letters from the student's own code, ten along
// the body and seven across, the front on the right (see planet.ART_COLORS).
const ART = {r: "#ff4d4d", o: "#ff9d3c", y: "#ffe14d", l: "#b6f04a", g: "#3fbf5a", m: "#8cf2c6", c: "#4de0ff",
             b: "#3f7dff", v: "#1f2f6b", p: "#a463ff", k: "#ff8ac2", d: "#8a5a32", a: "#ffc928", w: "#ffffff",
             e: "#9aa3b5", n: "#1e1a1a"};
const ART_COLS = 10, ART_ROWS = 7;
Object.assign(PAINTS, {mine: {base: "#f2eadb", swatch: "conic-gradient(#ff4d4d, #ffe14d, #3fbf5a, #3f7dff, #a463ff, #ff4d4d)", draw(ctx, s, now, gear) {
  const art = (gear && gear.art) || "", w = .62 * s / ART_COLS, h = .44 * s / ART_ROWS;
  for (let j = 0; j < ART_ROWS; j++) for (let i = 0; i < ART_COLS; i++) {
    const color = ART[art[j * ART_COLS + i]];
    if (color) { ctx.fillStyle = color; ctx.fillRect(-.32 * s + i * w, -.22 * s + j * h, w + .5, h + .5); }
  }
}}});

// What the rover drives on (the garage's wheels slot): everything under the
// body, axles too. Six wheels, three a side; `roll` turns their treads.
function wheelSpots(fn) { for (const wx of [-.26, 0, .26]) for (const wy of [-.33, .33]) fn(wx, wy); }
function axles(ctx, s, color = "#26212f", width = .05) {
  ctx.strokeStyle = color; ctx.lineWidth = s * width;
  ctx.beginPath(); ctx.moveTo(-.3 * s, -.27 * s); ctx.lineTo(.3 * s, -.27 * s); ctx.moveTo(-.3 * s, .27 * s); ctx.lineTo(.3 * s, .27 * s); ctx.stroke();
}
function tyres(ctx, s, color, w = .18, h = .14, r = .04) {
  ctx.fillStyle = color;
  wheelSpots((wx, wy) => { roundRect(ctx, (wx - w / 2) * s, (wy - h / 2) * s, w * s, h * s, r * s); ctx.fill(); });
}
// Tread lines across each tyre, moving back as the wheels turn.
function treadLines(ctx, s, now, color, w = .18, h = .14, n = 4) {
  const roll = CALM ? .5 : (now / 110) % 1;
  ctx.strokeStyle = color; ctx.lineWidth = Math.max(1, s * .02);
  ctx.beginPath();
  wheelSpots((wx, wy) => {
    for (let k = 0; k < n; k++) {
      const x = wx - w / 2 + ((k + 1 - roll) / n) * w;
      ctx.moveTo(x * s, (wy - h / 2 + .02) * s); ctx.lineTo(x * s, (wy + h / 2 - .02) * s);
    }
  });
  ctx.stroke();
}
const WHEELS = {
  std(ctx, s) { tyres(ctx, s, "#26212f"); axles(ctx, s); },
  monster(ctx, s, now) {   // big knobbly tyres on thick axles
    axles(ctx, s, "#26212f", .07);
    tyres(ctx, s, "#18141e", .23, .2, .06);
    ctx.fillStyle = "#18141e";
    wheelSpots((wx, wy) => { for (const k of [-.07, 0, .07]) ctx.fillRect((wx + k - .02) * s, (wy + Math.sign(wy) * .1) * s - (wy < 0 ? .03 * s : 0), .04 * s, .03 * s); });
    treadLines(ctx, s, now, "#4a4258", .23, .2, 5);
  },
  glowrims(ctx, s, now) {   // dark tyres with a glowing stripe round each one
    tyres(ctx, s, "#15121c"); axles(ctx, s, "#15121c");
    const k = CALM ? 1 : .7 + .3 * Math.sin(now / 250);
    ctx.strokeStyle = `rgba(127,240,214,${k})`; ctx.shadowColor = "#7ff0d6"; ctx.shadowBlur = s * .18 * k; ctx.lineWidth = Math.max(1, s * .03);
    ctx.beginPath(); wheelSpots((wx, wy) => { ctx.moveTo((wx - .07) * s, wy * s); ctx.lineTo((wx + .07) * s, wy * s); }); ctx.stroke();
    ctx.shadowBlur = 0;
  },
  pixelwheels(ctx, s) {   // square blocky wheels, three by three pixels
    axles(ctx, s, "#3a3a3a");
    const u = .06;
    wheelSpots((wx, wy) => {
      for (let j = 0; j < 3; j++) for (let i = 0; i < 3; i++) {
        ctx.fillStyle = i === 1 && j === 1 ? "#8a8a8a" : ["#3a3a3a", "#2a2a2a", "#4a4a4a"][Math.floor(hash(i + wx * 10, j + wy * 10, 7) * 3)];
        ctx.fillRect((wx - .09 + i * u) * s, (wy - .09 + j * u) * s, u * s + .5, u * s + .5);
      }
    });
  },
  flamerims(ctx, s, now) {   // flames streaming back off every wheel
    wheelSpots((wx, wy) => {
      const len = .16 + (CALM ? .04 : .06 * hash(Math.floor(now / 70), wx * 10 + wy * 30));
      const grad = ctx.createLinearGradient((wx - .08) * s, 0, (wx - .08 - len) * s, 0);
      grad.addColorStop(0, "rgba(255,230,107,.95)"); grad.addColorStop(.4, "rgba(255,120,30,.85)"); grad.addColorStop(1, "rgba(220,40,20,0)");
      ctx.fillStyle = grad; ctx.beginPath(); ctx.moveTo((wx - .06) * s, (wy - .06) * s);
      ctx.quadraticCurveTo((wx - .08 - len * .6) * s, (wy - .05) * s, (wx - .08 - len) * s, wy * s);
      ctx.quadraticCurveTo((wx - .08 - len * .6) * s, (wy + .05) * s, (wx - .06) * s, (wy + .06) * s); ctx.fill();
    });
    tyres(ctx, s, "#26212f"); axles(ctx, s);
    ctx.fillStyle = "#ff7a1e"; wheelSpots((wx, wy) => { ctx.fillRect((wx - .05) * s, (wy - .025) * s, .1 * s, .05 * s); });
  },
  treads(ctx, s, now) {   // a tank's tracks, one long one each side
    const roll = CALM ? .5 : (now / 110) % 1;
    for (const wy of [-.33, .33]) {
      ctx.fillStyle = "#2b2a24"; roundRect(ctx, -.4 * s, (wy - .09) * s, .8 * s, .18 * s, .09 * s); ctx.fill();
      ctx.fillStyle = "#4f4d42"; for (const wx of [-.31, .31]) { ctx.beginPath(); ctx.arc(wx * s, wy * s, .06 * s, 0, 7); ctx.fill(); }
      ctx.strokeStyle = "#5e5b4e"; ctx.lineWidth = Math.max(1, s * .02); ctx.beginPath();
      for (let k = 0; k < 12; k++) {
        const x = -.38 + ((k + 1 - roll) / 12) * .76;
        ctx.moveTo(x * s, (wy - .085) * s); ctx.lineTo(x * s, (wy - .05) * s);
        ctx.moveTo(x * s, (wy + .05) * s); ctx.lineTo(x * s, (wy + .085) * s);
      }
      ctx.stroke();
    }
  },
  hover(ctx, s, now) {   // no wheels at all: glowing pads it floats on
    wheelSpots((wx, wy) => {
      const k = CALM ? 1 : .7 + .3 * Math.sin(now / 180 + wx * 9 + wy * 4);
      const grad = ctx.createRadialGradient(wx * s, wy * s, 0, wx * s, wy * s, .14 * s);
      grad.addColorStop(0, `rgba(200,250,255,${k})`); grad.addColorStop(.45, `rgba(77,195,255,${.7 * k})`); grad.addColorStop(1, "rgba(77,195,255,0)");
      ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(wx * s, wy * s, .14 * s, 0, 7); ctx.fill();
      ctx.strokeStyle = "#9aa3b5"; ctx.lineWidth = Math.max(1, s * .02);
      ctx.beginPath(); ctx.arc(wx * s, wy * s, .06 * s, 0, 7); ctx.stroke();
    });
    axles(ctx, s, "#5a6070", .035);
  },
  goldrims(ctx, s, now) {   // black tyres with shiny gold hubs
    tyres(ctx, s, "#1c1820"); axles(ctx, s, "#3a2f10");
    const glint = CALM ? .3 : (now / 900) % 1.4;
    wheelSpots((wx, wy) => {
      const grad = ctx.createLinearGradient((wx - .06) * s, 0, (wx + .06) * s, 0);
      grad.addColorStop(0, "#a07a20"); grad.addColorStop(Math.min(1, glint), "#fff3b0"); grad.addColorStop(1, "#d9a520");
      ctx.fillStyle = grad; roundRect(ctx, (wx - .06) * s, (wy - .04) * s, .12 * s, .08 * s, .02 * s); ctx.fill();
    });
  },
  rainbowwheels(ctx, s, now) {   // every wheel a different colour, going round the rainbow
    axles(ctx, s);
    let k = 0;
    wheelSpots((wx, wy) => {
      ctx.fillStyle = `hsl(${(k++ * 60 + (CALM ? 0 : now / 8)) % 360},90%,60%)`;
      roundRect(ctx, (wx - .09) * s, (wy - .07) * s, .18 * s, .14 * s, .04 * s); ctx.fill();
    });
    treadLines(ctx, s, now, "rgba(0,0,0,.25)");
  },
};

// ---- The practice zones' mystery gifts, for a younger class.
Object.assign(PAINTS, {
  chalkboard: {base: "#2f4a3c", swatch: "linear-gradient(135deg, #3a5a49, #24392e)", draw(ctx, s) {
    // A sum in chalk, and a line of working under it.
    ctx.strokeStyle = "rgba(240,240,225,.85)"; ctx.lineWidth = Math.max(1, s * .014); ctx.lineCap = "round";
    ctx.beginPath();
    for (const [a, b, c, d] of [[-.25, -.1, -.13, -.1], [-.19, -.16, -.19, -.04], [-.06, -.12, .06, -.12],
                                [-.06, -.07, .06, -.07], [.13, -.15, .22, -.15], [.22, -.15, .13, -.05],
                                [.13, -.05, .22, -.05], [-.25, .1, -.05, .1], [.02, .08, .2, .12]]) {
      ctx.moveTo(a * s, b * s); ctx.lineTo(c * s, d * s);
    }
    ctx.stroke();
  }},
  graphpaper: {base: "#f6f8ff", swatch: "repeating-linear-gradient(0deg, #9db7ff 0 1px, transparent 1px 6px), repeating-linear-gradient(90deg, #9db7ff 0 1px, transparent 1px 6px), #f6f8ff", draw(ctx, s) {
    // Squares, and a line climbing across them.
    ctx.strokeStyle = "rgba(120,150,235,.7)"; ctx.lineWidth = Math.max(1, s * .008);
    ctx.beginPath();
    for (let k = -4; k <= 4; k++) {
      ctx.moveTo(k * .08 * s, -.3 * s); ctx.lineTo(k * .08 * s, .3 * s);
      ctx.moveTo(-.4 * s, k * .08 * s); ctx.lineTo(.4 * s, k * .08 * s);
    }
    ctx.stroke();
    ctx.strokeStyle = "#ef5b6b"; ctx.lineWidth = Math.max(1.5, s * .02); ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(-.26 * s, .14 * s); ctx.lineTo(-.08 * s, .06 * s); ctx.lineTo(.06 * s, .08 * s); ctx.lineTo(.24 * s, -.14 * s); ctx.stroke();
  }},
  frosty: {base: "#cfefff", swatch: "radial-gradient(circle at 35% 35%, #ffffff 12%, transparent 14%), linear-gradient(135deg, #e8f8ff, #8fd3ff)", fill(ctx, s) {
    const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
    grad.addColorStop(0, "#f2fbff"); grad.addColorStop(1, "#8fd3ff");
    return grad;
  }, draw(ctx, s) {
    // Snowflakes, and frost round the edge.
    ctx.strokeStyle = "rgba(255,255,255,.95)"; ctx.lineWidth = Math.max(1, s * .012); ctx.lineCap = "round";
    for (const [x, y, r] of [[-.22, -.1, .06], [-.05, .11, .05], [.08, -.13, .04], [-.25, .13, .035], [.2, .14, .035]]) {
      ctx.beginPath();
      for (let k = 0; k < 3; k++) {
        const a = k * Math.PI / 3;
        ctx.moveTo((x - Math.cos(a) * r) * s, (y - Math.sin(a) * r) * s); ctx.lineTo((x + Math.cos(a) * r) * s, (y + Math.sin(a) * r) * s);
      }
      ctx.stroke();
    }
    roundRect(ctx, -.32 * s, -.22 * s, .62 * s, .44 * s, .08 * s);
    ctx.strokeStyle = "rgba(255,255,255,.7)"; ctx.lineWidth = s * .04; ctx.stroke();
  }},
});
Object.assign(GLOWS, {
  portalglow(ctx, s, now) {   // a pad's purple swirl turning underneath
    const spin = CALM ? 0 : now / 600;
    underglow(ctx, s, "185,140,255", .6);
    ctx.lineWidth = Math.max(1, s * .04); ctx.lineCap = "round";
    for (let k = 0; k < 3; k++) {
      ctx.strokeStyle = ["#d9cbff", "#b98cff", "#8f6bff"][k];
      ctx.beginPath();
      for (let j = 0; j <= 20; j++) {
        const a = spin + k * 2.1 + j * .22, r = (.2 + j * .02) * s;
        ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r * .85);
      }
      ctx.stroke();
    }
  },
});
Object.assign(PETS, {
  chick(ctx, s, t) {   // a fluffy yellow chick, pecking now and then
    const peck = t % 2000 > 1750 ? .25 : 0;
    ctx.fillStyle = "#ff9d3c"; for (const x of [-.1, .1]) ctx.fillRect((x - .02) * s, .28 * s, .04 * s, .1 * s);
    ctx.fillStyle = "#ffe066"; ctx.beginPath(); ctx.ellipse(0, .12 * s, .28 * s, .24 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#ffd23a"; ctx.beginPath(); ctx.ellipse(-.18 * s, .12 * s, .1 * s, .14 * s, .5, 0, 7); ctx.fill();
    ctx.save(); ctx.rotate(peck);
    ctx.fillStyle = "#ffe066"; ctx.beginPath(); ctx.arc(.05 * s, -.18 * s, .19 * s, 0, 7); ctx.fill();
    for (const a of [-.4, 0, .4]) { ctx.beginPath(); ctx.ellipse((.05 + a * .1) * s, -.38 * s, .03 * s, .06 * s, a, 0, 7); ctx.fill(); }
    eyes(ctx, s, [-.02, .14], -.22, .035);
    ctx.fillStyle = "#ff8a1f"; ctx.beginPath(); ctx.moveTo(.18 * s, -.16 * s); ctx.lineTo(.32 * s, -.12 * s); ctx.lineTo(.18 * s, -.08 * s); ctx.fill();
    ctx.restore();
  },
  froggy(ctx, s, t) {   // a green frog that hops, throat puffing
    const hop = Math.max(0, Math.sin(t / 300)) * .12, puff = .06 + (t % 1800 > 1400 ? .05 : 0);
    ctx.translate(0, -hop * s);
    ctx.fillStyle = "#3f9a3a";
    for (const side of [-1, 1]) { ctx.beginPath(); ctx.ellipse(side * .24 * s, .22 * s, .14 * s, .08 * s, side * .3, 0, 7); ctx.fill(); }
    ctx.fillStyle = "#5cc152"; ctx.beginPath(); ctx.ellipse(0, .08 * s, .3 * s, .24 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#c8f0a0"; ctx.beginPath(); ctx.ellipse(0, .14 * s, .14 * s, puff * 1.6 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#5cc152";
    for (const x of [-.14, .14]) { ctx.beginPath(); ctx.arc(x * s, -.14 * s, .1 * s, 0, 7); ctx.fill(); }
    eyes(ctx, s, [-.14, .14], -.15, .055);
    ctx.strokeStyle = "#2a6a25"; ctx.lineWidth = s * .025; ctx.lineCap = "round";
    ctx.beginPath(); ctx.arc(0, -.02 * s, .12 * s, .2 * Math.PI, .8 * Math.PI); ctx.stroke();
  },
});

// ---- The zone master legendaries: each zone's Master badge earns one.
Object.assign(PAINTS, {
  goldtruck: {base: "#e0b030", swatch: "repeating-linear-gradient(45deg, #ffd96b 0 4px, #c9952a 4px 6px, #ffd96b 6px 10px)", fill(ctx, s) {
    const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
    grad.addColorStop(0, "#fff0a8"); grad.addColorStop(.45, "#e0b030"); grad.addColorStop(1, "#a87a18");
    return grad;
  }, draw(ctx, s, now) {
    // Diamond plate, and a shine sliding along it.
    ctx.strokeStyle = "rgba(255,248,210,.65)"; ctx.lineWidth = Math.max(1, s * .014); ctx.lineCap = "round";
    ctx.beginPath();
    for (let j = 0; j < 6; j++) for (let i = 0; i < 9; i++) {
      const x = -.3 + i * .07 + (j % 2) * .035, y = -.19 + j * .075, d = (i + j) % 2 ? 1 : -1;
      ctx.moveTo((x - .015) * s, (y - .015 * d) * s); ctx.lineTo((x + .015) * s, (y + .015 * d) * s);
    }
    ctx.stroke();
    const g = CALM ? .4 : (now / 1400) % 1.6 - .3;
    ctx.fillStyle = "rgba(255,255,255,.4)";
    ctx.beginPath(); ctx.moveTo((-.45 + g * .8) * s, .22 * s); ctx.lineTo((-.33 + g * .8) * s, -.22 * s);
    ctx.lineTo((-.27 + g * .8) * s, -.22 * s); ctx.lineTo((-.39 + g * .8) * s, .22 * s); ctx.fill();
  }},
});
Object.assign(WHEELS, {
  portalwheels(ctx, s, now) {   // every wheel a little portal, swirling
    axles(ctx, s, "#3a2a6a");
    const spin = CALM ? 0 : now / 300;
    wheelSpots((wx, wy) => {
      const grad = ctx.createRadialGradient(wx * s, wy * s, 0, wx * s, wy * s, .1 * s);
      grad.addColorStop(0, "#ffffff"); grad.addColorStop(.35, "#b98cff"); grad.addColorStop(1, "#3a1a7a");
      ctx.fillStyle = grad; ctx.beginPath(); ctx.ellipse(wx * s, wy * s, .1 * s, .08 * s, 0, 0, 7); ctx.fill();
      ctx.strokeStyle = "#e6dbff"; ctx.lineWidth = Math.max(1, s * .015);
      ctx.beginPath(); ctx.ellipse(wx * s, wy * s, .07 * s, .055 * s, spin + wx * 5, 0, 4); ctx.stroke();
    });
  },
});

// Packs worn whole: with every piece of one on at once, the pack's icon
// circles the rover, upright, wherever it's drawn.
const SETS = [
  {name: "Blocky Boom", icon: "💥", items: {paint: "creeper", pet: "minicreeper", dance: "kaboom", horn: "hiss"}},
  {name: "Spooky", icon: "👻", items: {paint: "skeleton", pet: "bat", glow: "jacko", horn: "spooky"}},
  {name: "Ninja", icon: "🥷", items: {paint: "ninja", topper: "ninjaband", trail: "clones", dance: "smokebomb"}},
  {name: "Dino", icon: "🦖", items: {paint: "dino", pet: "trex", horn: "roar", world: "jurassic"}},
  {name: "Thunder", icon: "⚡", items: {paint: "storm", trail: "lightning", glow: "electric", dance: "tornado"}},
  {name: "Sparkle", icon: "🦄", items: {paint: "cottoncandy", topper: "unicorn", pet: "axolotl", trail: "bubbles"}},
  {name: "Gold Rush", icon: "🪙", items: {paint: "gold", topper: "crown", wheels: "goldrims", trail: "coins"}},
  {name: "Speedway", icon: "🏁", items: {paint: "racecar", wheels: "flamerims", glow: "afterburner"}},
  {name: "Farmyard", icon: "🐄", items: {paint: "cow", horn: "moo", pet: "bunny"}},
];
function fullSet(gear) {
  return SETS.find(set => Object.entries(set.items).every(([slot, key]) => gear[slot] === key));
}
function setSparkle(ctx, s, set, now) {
  const turn = CALM ? 0 : now / 1400;
  ctx.font = `${Math.max(8, Math.round(s * .2))}px system-ui, sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  for (let k = 0; k < 3; k++) {
    const a = turn + k * Math.PI * 2 / 3, bob = CALM ? 0 : Math.sin(now / 250 + k * 2) * .04;
    ctx.fillText(set.icon, Math.cos(a) * .55 * s, (Math.sin(a) * .5 + bob) * s);
  }
}

// Look-Out Point's and Fork Road's gifts.
Object.assign(PETS, {
  owl(ctx, s, t) {   // a round owl that blinks and tilts its head, thinking
    const tilt = Math.sin(t / 900) * .15, blink = t % 3600 > 3450;
    ctx.fillStyle = "#8a5a32";
    for (const side of [-1, 1]) { ctx.beginPath(); ctx.moveTo(side * .12 * s, -.3 * s); ctx.lineTo(side * .26 * s, -.46 * s); ctx.lineTo(side * .28 * s, -.22 * s); ctx.fill(); }
    ctx.beginPath(); ctx.ellipse(0, .02 * s, .32 * s, .36 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#e8d2b0"; ctx.beginPath(); ctx.ellipse(0, .14 * s, .18 * s, .2 * s, 0, 0, 7); ctx.fill();
    ctx.strokeStyle = "#b08860"; ctx.lineWidth = s * .02;
    for (const y of [.06, .14, .22]) { ctx.beginPath(); ctx.arc(0, y * s, .06 * s, .2 * Math.PI, .8 * Math.PI); ctx.stroke(); }
    ctx.save(); ctx.rotate(tilt);
    ctx.fillStyle = "#f4ead8";
    for (const x of [-.12, .12]) { ctx.beginPath(); ctx.arc(x * s, -.14 * s, .11 * s, 0, 7); ctx.fill(); }
    if (blink) {
      ctx.strokeStyle = "#3a2410"; ctx.lineWidth = s * .03;
      for (const x of [-.12, .12]) { ctx.beginPath(); ctx.moveTo((x - .05) * s, -.14 * s); ctx.lineTo((x + .05) * s, -.14 * s); ctx.stroke(); }
    } else {
      ctx.fillStyle = "#ffb52e"; for (const x of [-.12, .12]) { ctx.beginPath(); ctx.arc(x * s, -.14 * s, .065 * s, 0, 7); ctx.fill(); }
      eyes(ctx, s, [-.12, .12], -.14, .04);
    }
    ctx.fillStyle = "#ff9d3c"; ctx.beginPath(); ctx.moveTo(-.035 * s, -.07 * s); ctx.lineTo(.035 * s, -.07 * s); ctx.lineTo(0, .0); ctx.fill();
    ctx.restore();
  },
});

// Halloween night's limited-time things: the candy road, the gifts and badges.
Object.assign(PAINTS, {
  candycorn: {base: "#ffd23f", swatch: "linear-gradient(90deg, #ffd23f 36%, #ff8a1f 36% 68%, #fff6e8 68%)", fill(ctx, s) {
    // Yellow at the back, orange in the middle, white at the tip, and a shine along it.
    const grad = ctx.createLinearGradient(-.32 * s, 0, .3 * s, 0);
    grad.addColorStop(0, "#ffd23f"); grad.addColorStop(.36, "#ffd23f"); grad.addColorStop(.37, "#ff8a1f");
    grad.addColorStop(.68, "#ff8a1f"); grad.addColorStop(.69, "#fff6e8"); grad.addColorStop(1, "#fff6e8");
    return grad;
  }, draw(ctx, s) {
    ctx.fillStyle = "rgba(255,255,255,.35)"; ctx.fillRect(-.32 * s, -.17 * s, .62 * s, .05 * s);
    ctx.fillStyle = "rgba(120,50,0,.12)"; ctx.fillRect(-.32 * s, .12 * s, .62 * s, .1 * s);
  }},
  mummy: {base: "#e9e0c9", swatch: "repeating-linear-gradient(160deg, #e9e0c9 0 5px, #b8ab8a 5px 6px)", draw(ctx, s) {
    // Bandages wound round and round, one loose end, and two eyes peeping out at the front.
    for (let k = 0; k < 9; k++) {
      const x = (-.4 + k * .085) * s, tilt = (hash(k, 61) - .5) * .12 * s;
      ctx.fillStyle = k % 2 ? "#ded3b8" : "#f1e9d4";
      ctx.beginPath(); ctx.moveTo(x, -.24 * s); ctx.lineTo(x + .07 * s, -.24 * s); ctx.lineTo(x + .14 * s + tilt, .24 * s); ctx.lineTo(x + .07 * s + tilt, .24 * s); ctx.fill();
      ctx.strokeStyle = "rgba(120,100,70,.35)"; ctx.lineWidth = Math.max(1, s * .008); ctx.stroke();
    }
    ctx.fillStyle = "#14101c"; ctx.fillRect(.06 * s, -.1 * s, .2 * s, .07 * s);
    for (const y of [-.14, .06]) {
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(.17 * s, (y + .075) * s, .035 * s, 0, 7); ctx.fill();
    }
    ctx.fillStyle = "#14101c";
    for (const y of [-.14, .06]) { ctx.beginPath(); ctx.arc(.18 * s, (y + .075) * s, .017 * s, 0, 7); ctx.fill(); }
  }},
  vampire: {base: "#16101c", swatch: "linear-gradient(90deg, #b3122e 0 22%, #16101c 22% 78%, #f4f1ff 78%)", draw(ctx, s, now) {
    // A high red collar at the back, a bat on the cape, and fangs at the front.
    ctx.fillStyle = "#b3122e";
    ctx.beginPath(); ctx.moveTo(-.32 * s, -.22 * s); ctx.lineTo(-.16 * s, -.22 * s); ctx.lineTo(-.24 * s, 0); ctx.lineTo(-.16 * s, .22 * s); ctx.lineTo(-.32 * s, .22 * s); ctx.fill();
    ctx.fillStyle = "#6e0a1c"; ctx.beginPath(); ctx.moveTo(-.32 * s, -.12 * s); ctx.lineTo(-.24 * s, 0); ctx.lineTo(-.32 * s, .12 * s); ctx.fill();
    const flap = CALM ? 1 : .8 + .2 * Math.sin(now / 160);
    ctx.fillStyle = "#c8203c"; ctx.beginPath(); ctx.ellipse(-.04 * s, 0, .03 * s, .04 * s, 0, 0, 7); ctx.fill();
    for (const side of [-1, 1]) {
      ctx.beginPath(); ctx.moveTo(-.04 * s, 0); ctx.quadraticCurveTo(-.06 * s, side * .1 * flap * s, -.02 * s, side * .14 * flap * s);
      ctx.quadraticCurveTo(-.01 * s, side * .08 * s, .02 * s, side * .1 * flap * s); ctx.lineTo(-.02 * s, 0); ctx.fill();
    }
    ctx.fillStyle = "#f4f1ff";
    for (const y of [-.08, .08]) { ctx.beginPath(); ctx.moveTo(.3 * s, (y - .03) * s); ctx.lineTo(.3 * s, (y + .03) * s); ctx.lineTo(.22 * s, y * s); ctx.fill(); }
  }},
  ghostsheet: {base: "#f4f1ff", swatch: "radial-gradient(ellipse 10% 14% at 40% 45%, #1b1530 90%, transparent 100%), radial-gradient(ellipse 10% 14% at 64% 45%, #1b1530 90%, #f4f1ff 100%)", draw(ctx, s, now) {
    // A bedsheet costume: soft folds, and two eye holes that blink now and then.
    ctx.strokeStyle = "rgba(160,150,200,.35)"; ctx.lineWidth = Math.max(1, s * .02);
    for (const y of [-.14, 0, .14]) { ctx.beginPath(); ctx.moveTo(-.32 * s, y * s); ctx.bezierCurveTo(-.15 * s, (y + .05) * s, -.05 * s, (y - .05) * s, .1 * s, y * s); ctx.stroke(); }
    const blink = !CALM && now % 4200 > 4050;
    ctx.fillStyle = "#1b1530";
    for (const y of [-.08, .08]) { ctx.beginPath(); ctx.ellipse(.16 * s, y * s, .035 * s, blink ? .008 * s : .045 * s, 0, 0, 7); ctx.fill(); }
  }},
  jackolantern: {base: "#ff8a1f", swatch: "radial-gradient(circle at 50% 55%, #fff27a 12%, #ff8a1f 15% 60%, #c25a0c 62%)", draw(ctx, s, now) {
    // A carved pumpkin with a candle inside: ribs, a stalk, and a face that flickers.
    const k = CALM ? 1 : .75 + .25 * Math.sin(now / 90) * Math.sin(now / 230);
    ctx.strokeStyle = "rgba(150,60,0,.55)"; ctx.lineWidth = Math.max(1, s * .02);
    for (const y of [-.14, -.05, .05, .14]) { ctx.beginPath(); ctx.ellipse(-.01 * s, y * s, .34 * s, .05 * s, 0, 0, 7); ctx.stroke(); }
    ctx.fillStyle = "#3f8a2e"; ctx.fillRect(-.34 * s, -.03 * s, .06 * s, .06 * s);
    ctx.fillStyle = `rgba(255,236,120,${k})`; ctx.shadowColor = "#ffd34d"; ctx.shadowBlur = s * .25 * k;
    for (const y of [-.1, .1]) { ctx.beginPath(); ctx.moveTo(.2 * s, (y - .05) * s); ctx.lineTo(.2 * s, (y + .05) * s); ctx.lineTo(.12 * s, y * s); ctx.fill(); }
    ctx.beginPath(); ctx.moveTo(.0, -.12 * s);
    for (let j = 0; j <= 6; j++) ctx.lineTo((j % 2 ? .04 : -.01) * s, (-.12 + j * .04) * s);
    ctx.lineTo(-.08 * s, .1 * s); ctx.lineTo(-.08 * s, -.1 * s); ctx.fill();
    ctx.shadowBlur = 0;
  }},
});
Object.assign(PETS, {
  blackcat(ctx, s, t) {   // a black cat with green eyes, its tail swishing, an ear flicking now and then
    const swish = Math.sin(t / 380) * .25, flick = t % 3000 > 2850 ? .08 : 0;
    ctx.strokeStyle = "#16121c"; ctx.lineWidth = s * .09; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(-.2 * s, .22 * s); ctx.quadraticCurveTo(-.55 * s, (.1 + swish) * s, -.42 * s, (-.25 + swish) * s); ctx.stroke();
    ctx.fillStyle = "#16121c";
    ctx.beginPath(); ctx.ellipse(-.02 * s, .2 * s, .28 * s, .18 * s, 0, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(.14 * s, -.1 * s, .22 * s, 0, 7); ctx.fill();
    for (const [x, f] of [[.0, flick], [.26, 0]]) { ctx.beginPath(); ctx.moveTo((x - .04) * s, -.2 * s); ctx.lineTo((x + .02 - f) * s, (-.42 + f) * s); ctx.lineTo((x + .12) * s, -.24 * s); ctx.fill(); }
    ctx.fillStyle = "#7dff6b";
    for (const x of [.06, .22]) { ctx.beginPath(); ctx.ellipse(x * s, -.12 * s, .05 * s, .065 * s, 0, 0, 7); ctx.fill(); }
    ctx.fillStyle = "#16121c";
    for (const x of [.06, .22]) { ctx.beginPath(); ctx.ellipse(x * s, -.12 * s, .015 * s, .05 * s, 0, 0, 7); ctx.fill(); }
    ctx.fillStyle = "#ff9ec4"; ctx.beginPath(); ctx.arc(.14 * s, -.03 * s, .025 * s, 0, 7); ctx.fill();
  },
  spider(ctx, s, t) {   // a fuzzy spider on its thread, bobbing up and down, legs wiggling
    const drop = Math.sin(t / 600) * .12;
    ctx.strokeStyle = "rgba(240,240,255,.7)"; ctx.lineWidth = Math.max(1, s * .015);
    ctx.beginPath(); ctx.moveTo(0, -.9 * s); ctx.lineTo(0, (-.2 + drop) * s); ctx.stroke();
    ctx.translate(0, drop * s);
    ctx.strokeStyle = "#1a1420"; ctx.lineWidth = s * .045; ctx.lineCap = "round";
    for (let k = 0; k < 4; k++) for (const side of [-1, 1]) {
      const wig = Math.sin(t / 120 + k * 1.3 + side) * .04, y = (-.08 + k * .07) * s;
      ctx.beginPath(); ctx.moveTo(side * .08 * s, y); ctx.quadraticCurveTo(side * .3 * s, y - .14 * s, side * .38 * s, y + (.12 + wig) * s); ctx.stroke();
    }
    ctx.fillStyle = "#2a1f33"; ctx.beginPath(); ctx.ellipse(0, .04 * s, .2 * s, .22 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#ff8a1f"; ctx.beginPath(); ctx.moveTo(0, .02 * s); ctx.lineTo(.06 * s, .12 * s); ctx.lineTo(0, .2 * s); ctx.lineTo(-.06 * s, .12 * s); ctx.fill();
    eyes(ctx, s, [-.07, .07], -.08, .055);
  },
});
Object.assign(GLOWS, {
  spookyfog(ctx, s, now) {   // purple and green mist curling round underneath
    const t = CALM ? 0 : now / 900;
    for (let k = 0; k < 7; k++) {
      const a = t + k * Math.PI * 2 / 7, r = (.42 + .08 * Math.sin(t * 2 + k)) * s;
      const grad = ctx.createRadialGradient(Math.cos(a) * r, Math.sin(a) * r * .8, 0, Math.cos(a) * r, Math.sin(a) * r * .8, .3 * s);
      grad.addColorStop(0, k % 2 ? "rgba(156,255,107,.32)" : "rgba(170,110,255,.38)"); grad.addColorStop(1, "rgba(120,80,200,0)");
      ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(Math.cos(a) * r, Math.sin(a) * r * .8, .3 * s, 0, 7); ctx.fill();
    }
  },
});
Object.assign(WHEELS, {
  pumpkinwheels(ctx, s, now) {   // every wheel a little pumpkin, ribs turning, a green stalk for a hub
    axles(ctx, s, "#2a3a1c");
    tyres(ctx, s, "#ff8a1f", .2, .16, .07);
    treadLines(ctx, s, now, "rgba(150,60,0,.6)", .2, .16, 4);
    ctx.fillStyle = "#3f8a2e";
    wheelSpots((wx, wy) => { ctx.beginPath(); ctx.arc(wx * s, wy * s, .025 * s, 0, 7); ctx.fill(); });
  },
});
Object.assign(PETS, {
  cauldron(ctx, s, t) {   // a witch's cauldron on little legs, green brew bubbling over
    ctx.fillStyle = "#1a1620";
    for (const x of [-.22, .22]) { ctx.fillRect((x - .04) * s, .22 * s, .08 * s, .16 * s); }
    ctx.beginPath(); ctx.ellipse(0, .08 * s, .38 * s, .3 * s, 0, 0, Math.PI); ctx.lineTo(-.38 * s, .08 * s); ctx.fill();
    ctx.fillRect(-.38 * s, -.02 * s, .76 * s, .12 * s);
    ctx.fillStyle = "#2c2634"; ctx.beginPath(); ctx.ellipse(0, -.02 * s, .42 * s, .08 * s, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#7dff5a"; ctx.shadowColor = "#7dff5a"; ctx.shadowBlur = s * .3;
    ctx.beginPath(); ctx.ellipse(0, -.03 * s, .34 * s, .055 * s, 0, 0, 7); ctx.fill(); ctx.shadowBlur = 0;
    for (let k = 0; k < 4; k++) {   // bubbles rising and popping
      const u = ((t / 900 + k * .27) % 1), x = (-.2 + k * .13 + Math.sin(t / 300 + k) * .03) * s;
      ctx.strokeStyle = `rgba(160,255,130,${1 - u})`; ctx.lineWidth = Math.max(1, s * .025);
      ctx.beginPath(); ctx.arc(x, (-.06 - u * .4) * s, (.04 + u * .03) * s, 0, 7); ctx.stroke();
    }
    eyes(ctx, s, [-.1, .1], .1, .05);
  },
});
SETS.push({name: "Trick-or-Treat", icon: "🎃", items: {topper: "witchhat", paint: "candycorn", pet: "blackcat", trail: "candytrail"}});
