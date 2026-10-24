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
  if (p.fill) return p.fill(ctx, s, now);
  if (p.base) return p.base;
  const grad = ctx.createLinearGradient(-.32 * s, -.22 * s, .3 * s, .22 * s);
  p.forEach((c, i) => grad.addColorStop(i / (p.length - 1), c));
  return grad;
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
  ctx.fillStyle = "rgba(10,4,16,.38)";
  ctx.beginPath(); ctx.ellipse(s * .05, s * .07, s * .42, s * .36, 0, 0, 7); ctx.fill();
  ctx.fillStyle = "#26212f";
  for (const wx of [-.26, 0, .26]) for (const wy of [-.33, .33]) {
    roundRect(ctx, (wx - .09) * s, (wy - .07) * s, .18 * s, .14 * s, .04 * s); ctx.fill();
  }
  ctx.strokeStyle = "#26212f"; ctx.lineWidth = s * .05;
  ctx.beginPath(); ctx.moveTo(-.3 * s, -.27 * s); ctx.lineTo(.3 * s, -.27 * s); ctx.moveTo(-.3 * s, .27 * s); ctx.lineTo(.3 * s, .27 * s); ctx.stroke();
  const paint = PAINTS[gear.paint] || PAINTS.bone;
  ctx.fillStyle = bodyPaint(ctx, s, paint, now);
  roundRect(ctx, -.32 * s, -.22 * s, .62 * s, .44 * s, .08 * s); ctx.fill();
  if (paint.draw) {
    ctx.save(); ctx.clip(); paint.draw(ctx, s, now); ctx.restore();
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
  } else {
    ctx.strokeStyle = "#6e6290"; ctx.beginPath(); ctx.moveTo(-.05 * s, -.14 * s); ctx.lineTo(-.16 * s, -.36 * s); ctx.stroke();
    ctx.fillStyle = "#ffb547"; ctx.beginPath(); ctx.arc(-.16 * s, -.36 * s, s * .035, 0, 7); ctx.fill();
  }
}
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
