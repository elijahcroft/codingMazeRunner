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
