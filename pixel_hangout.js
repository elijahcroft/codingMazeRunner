// Pixel Pals: the world behind the Hang out. Everything is drawn on a 320 by 180 map,
// the same one the pals walk on, so a tree's feet and a pal's feet agree, and it comes
// out in the same chunky pixels as the pals. The shapes are painted three times too big
// and only the middle of every 3 by 3 block is kept, which gives hard pixel edges with
// no blur. Only the words on the signs are drawn at the screen's own sharpness.
"use strict";

const PalHang = (() => {
  const W = 320, H = 180;

  // Scattered, but the same on every screen.
  const starX = i => (i * i * 37 + i * 71 + 5) % W;
  const starY = (i, tall) => (i * i * 19 + i * 53 + 11) % tall;

  // ---- Small shapes -----------------------------------------------------------------
  function oval(g, x, y, rx, ry, colour) {
    g.fillStyle = colour;
    g.beginPath();
    g.ellipse(x, y, Math.max(.75, rx), Math.max(.75, ry), 0, 0, 7);     // never thinner than a pixel
    g.fill();
  }
  function line(g, points, colour, width = 1) {
    g.strokeStyle = colour;
    g.lineWidth = Math.max(1, width);     // a thinner line would break up into dots
    g.lineCap = g.lineJoin = "round";
    g.beginPath();
    points.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y)));
    g.stroke();
  }
  function shape(g, points, colour) {
    g.fillStyle = colour;
    g.beginPath();
    points.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y)));
    g.closePath();
    g.fill();
  }
  function box(g, x, y, w, h, r, colour) {
    g.fillStyle = colour;
    g.beginPath();
    g.roundRect(x, y, w, h, r);
    g.fill();
  }
  function sky(g, top, bottom, to = 118) {
    const fill = g.createLinearGradient(0, 0, 0, to);
    fill.addColorStop(0, top);
    fill.addColorStop(1, bottom);
    g.fillStyle = fill;
    g.fillRect(0, 0, W, H);
  }
  function glow(g, x, y, r, colour) {
    const fill = g.createRadialGradient(x, y, 0, x, y, r);
    fill.addColorStop(0, colour);
    fill.addColorStop(1, colour.slice(0, 7) + "00");
    g.fillStyle = fill;
    g.fillRect(x - r, y - r, r * 2, r * 2);
  }
  function hills(g, y, colour, bumps) {
    g.fillStyle = colour;
    g.beginPath();
    g.moveTo(0, H);
    g.lineTo(0, y);
    bumps.forEach(([cx, top, x]) => g.quadraticCurveTo(cx, top, x, y));
    g.lineTo(W, y);
    g.lineTo(W, H);
    g.closePath();
    g.fill();
  }
  function ground(g, y, top, bottom) {
    const fill = g.createLinearGradient(0, y, 0, H);
    fill.addColorStop(0, top);
    fill.addColorStop(1, bottom);
    g.fillStyle = fill;
    g.fillRect(0, y, W, H - y);
  }
  // Lighter patches, so a field isn't one flat colour. The numbers are fixed so a
  // place looks the same on every screen.
  function patches(g, colour, y0, spots = 11) {
    for (let i = 0; i < spots; i++) {
      oval(g, (i * 67 + 21) % W, y0 + (i * 37) % (H - y0), 18 + (i * 13) % 20, 3 + (i * 5) % 5, colour);
    }
  }
  function cloud(g, x, y, s, colour = "#fffdf6", shade = "#d5e6f0") {
    const puffs = [[0, 0, 15, 6], [-8, 1, 8, 4.5], [8, 1, 9, 4.5], [1, -4, 7.5, 6]];
    puffs.forEach(([dx, dy, rx, ry]) => oval(g, x + dx * s, y + (dy + 1.6) * s, rx * s, ry * s, shade));
    puffs.forEach(([dx, dy, rx, ry]) => oval(g, x + dx * s, y + dy * s, rx * s, ry * s, colour));
  }
  function sun(g, x, y, r, core = "#fff0b8", halo = "#fff3c0") {
    glow(g, x, y, r * 3.4, halo + "aa");
    oval(g, x, y, r + 3, r + 3, halo + "88");
    oval(g, x, y, r, r, core);
    oval(g, x - r * .3, y - r * .3, r * .45, r * .4, "#fffbe6");
  }
  // A far-off peak, with snow or light on its tip.
  function mountain(g, x, y, half, tall, colour, cap) {
    shape(g, [[x - half, y], [x, y - tall], [x + half, y]], colour);
    shape(g, [[x, y - tall], [x + half, y], [x + half * .25, y]], "#1b153014");
    if (cap) shape(g, [[x - half * .3, y - tall * .7], [x, y - tall], [x + half * .3, y - tall * .7], [x + half * .14, y - tall * .6], [x, y - tall * .72], [x - half * .15, y - tall * .58]], cap);
  }
  function twinkle(g, x, y, r, colour) {
    box(g, x - r, y - .5, r * 2, 1, 0, colour);
    box(g, x - .5, y - r, 1, r * 2, 0, colour);
  }
  function heart(g, x, y, s, colour) {
    oval(g, x - 1.6 * s, y - 1.2 * s, 2 * s, 2 * s, colour);
    oval(g, x + 1.6 * s, y - 1.2 * s, 2 * s, 2 * s, colour);
    shape(g, [[x - 3.5 * s, y - .5 * s], [x + 3.5 * s, y - .5 * s], [x, y + 4 * s]], colour);
  }
  // Little tufts, so the ground has something growing on it.
  function tufts(g, y0, colour, count = 14) {
    for (let i = 0; i < count; i++) {
      const x = (i * 97 + 31) % W, y = y0 + (i * 43) % (H - y0 - 3);
      line(g, [[x - 2, y - 2], [x - 1, y]], colour);
      line(g, [[x, y - 3], [x, y]], colour);
      line(g, [[x + 2, y - 2], [x + 1, y]], colour);
    }
  }
  function shrub(g, x, y, s, leaf = ["#3f8f63", "#569f70", "#7fbd8c"], berry = "#ff9fb5") {
    oval(g, x, y, 12 * s, 2.4 * s, "#2f6b5022");
    oval(g, x - 6 * s, y - 4 * s, 7 * s, 5 * s, leaf[0]);
    oval(g, x + 6 * s, y - 4 * s, 7 * s, 5 * s, leaf[0]);
    oval(g, x, y - 7 * s, 8 * s, 6 * s, leaf[1]);
    oval(g, x - 2 * s, y - 10 * s, 4 * s, 2.2 * s, leaf[2]);
    if (berry) [[-7, -5], [5, -3], [1, -9], [-2, -3]].forEach(([dx, dy]) => oval(g, x + dx * s, y + dy * s, 1.1, 1.1, berry));
  }
  function rock(g, x, y, s, colour = "#b9b4a6", light = "#d9d4c6") {
    oval(g, x, y, 6 * s, 1.6 * s, "#1b15301c");
    oval(g, x, y - 2.5 * s, 5 * s, 3.2 * s, colour);
    oval(g, x - 1.2 * s, y - 3.6 * s, 2.6 * s, 1.3 * s, light);
  }
  function mushroom(g, x, y) {
    box(g, x - 1, y - 3, 2, 3, .5, "#fff6e6");
    g.fillStyle = "#e8576b";
    g.beginPath(); g.arc(x, y - 3, 3.4, Math.PI, 0); g.fill();
    oval(g, x - 1.4, y - 4.6, .8, .8, "#fff6e6");
    oval(g, x + 1.4, y - 4, .8, .8, "#fff6e6");
  }
  // A coral fan: a few branches with round tips, for the sea floor.
  function coral(g, x, y, s, colour, light) {
    oval(g, x, y, 10 * s, 2 * s, "#2b5a4a33");
    [[-9, -9], [-4, -16], [2, -20], [8, -13], [12, -6]].forEach(([dx, dy], i) => {
      line(g, [[x, y], [x + dx * s * .7, y + dy * s * .7]], colour, 2.2 * s);
      oval(g, x + dx * s, y + dy * s, (2.6 + (i % 2) * .8) * s, (2.6 + (i % 2) * .8) * s, light);
    });
  }
  // A little pink bubble vent: the "play" spot on the sea floor.
  function bubbleVent(g, x, y, s = 1) {
    oval(g, x, y + 2 * s, 14 * s, 2.6 * s, "#a98a5a33");
    rock(g, x, y, .8 * s, "#8aa6a0", "#c3d4c8");
    shape(g, [[x - 7 * s, y - 2 * s], [x, y - 12 * s], [x + 7 * s, y - 2 * s]], "#ff8fa8");
    shape(g, [[x - 4.5 * s, y - 3 * s], [x, y - 9 * s], [x + 4.5 * s, y - 3 * s]], "#ffd0e2");
    box(g, x - 2 * s, y - 8 * s, 4 * s, 5 * s, 1, "#e8709a");
    oval(g, x, y - 6 * s, 2.4 * s, 2.4 * s, "#d6f4ff"); oval(g, x - .8 * s, y - 7 * s, .9 * s, .9 * s, "#ffffff");
  }
  function balloon(g, x, y, colour, tieX, tieY) {
    line(g, [[x, y + 6], [tieX, tieY]], "#fffdf6", .6);
    ink(g, g => {
      oval(g, x, y, 4.6, 5.6, colour);
      shape(g, [[x - 1.5, y + 7], [x + 1.5, y + 7], [x, y + 5]], colour);
      oval(g, x - 1.6, y - 2, 1.2, 1.8, "#ffffffaa");
    });
  }
  function cottage(g, x, y, wall, roof, lit = "#ffe39a") {
    box(g, x + 4, y - 22, 3.4, 8, 0, roof);
    box(g, x - 9, y - 11, 18, 11, 1, wall);
    shape(g, [[x - 12, y - 10], [x, y - 21], [x + 12, y - 10]], roof);
    box(g, x - 2, y - 7, 4, 7, 1, "#8a6a4a");
    box(g, x - 7.5, y - 8, 4, 4, .5, lit);
    box(g, x + 3.5, y - 8, 4, 4, .5, lit);
  }
  function tree(g, x, y, s, leaf = ["#3f8f63", "#569f70", "#6fb583"], fruit = "#f2b56b", dark = "#2f7a58") {
    oval(g, x, y, 11 * s, 3 * s, "#2f6b5022");
    line(g, [[x, y], [x, y - 17 * s]], "#8a6a4a", 3.4 * s);
    if (s > .6) line(g, [[x - .9 * s, y - 1], [x - .9 * s, y - 13 * s]], "#a8845e", 1);
    line(g, [[x, y - 10 * s], [x + 5 * s, y - 15 * s]], "#8a6a4a", 1.6 * s);
    oval(g, x - 7 * s, y - 18.6 * s, 9 * s, 8 * s, dark);
    oval(g, x + 7 * s, y - 19.6 * s, 9 * s, 8 * s, dark);
    oval(g, x - 7 * s, y - 20.6 * s, 9 * s, 7.2 * s, leaf[0]);
    oval(g, x + 7 * s, y - 21.6 * s, 9 * s, 7.2 * s, leaf[0]);
    oval(g, x, y - 27 * s, 11 * s, 9 * s, leaf[1]);
    oval(g, x - 3 * s, y - 30 * s, 6 * s, 4.5 * s, leaf[2]);
    oval(g, x + 6 * s, y - 25 * s, 3 * s, 2 * s, leaf[2]);
    if (fruit) [[-8, -19], [7, -24], [1, -20], [-3, -31], [11, -18]].forEach(([dx, dy]) => oval(g, x + dx * s, y + dy * s, 1.1 * s, 1.1 * s, fruit));
  }
  function pine(g, x, y, s, leaf = "#4c8a72", snow = "#f5fbff", dark = "#3b7461") {
    oval(g, x, y, 9 * s, 2.4 * s, "#2c4a5522");
    box(g, x - 1.5 * s, y - 7 * s, 3 * s, 7 * s, 1, "#7d6250");
    [[0, 16], [10, 13], [19, 10]].forEach(([up, half]) => {
      shape(g, [[x - half * s, y - 5 * s - up * s], [x, y - 25 * s - up * s], [x + half * s, y - 5 * s - up * s]], leaf);
      shape(g, [[x, y - 25 * s - up * s], [x + half * s, y - 5 * s - up * s], [x + half * .2 * s, y - 5 * s - up * s]], dark);
      if (snow) shape(g, [[x - half * .55 * s, y - 14 * s - up * s], [x, y - 25 * s - up * s], [x + half * .55 * s, y - 14 * s - up * s], [x + half * .25 * s, y - 12 * s - up * s], [x, y - 15 * s - up * s], [x - half * .28 * s, y - 11.5 * s - up * s]], snow);
    });
  }
  function flowers(g, y0, colours, count = 16) {
    for (let i = 0; i < count; i++) {
      const x = (i * 83 + 13) % W, y = y0 + (i * 29) % (H - y0 - 4);
      line(g, [[x, y], [x, y - 3]], "#4f8f5f", .7);
      oval(g, x + 1.6, y - 1.4, 1.2, .8, "#5fa56c");
      for (let a = 0; a < 5; a++) oval(g, x + Math.cos(a * 1.26) * 1.5, y - 4 + Math.sin(a * 1.26) * 1.5, 1.1, 1.1, colours[i % colours.length]);
      oval(g, x, y - 4, .8, .8, "#ffe39a");
    }
  }
  function lamp(g, x, y, on = false) {
    if (on) glow(g, x, y - 26, 26, "#ffe7a0aa");
    oval(g, x, y, 5, 1.6, "#2f6b5033");
    box(g, x - 2.5, y - 2, 5, 2, .8, "#355e60");
    line(g, [[x, y], [x, y - 24]], "#355e60", 1.6);
    box(g, x - 3.5, y - 31, 7, 8, 1.5, on ? "#ffeaa6" : "#ffe9b0");
    box(g, x - 2.2, y - 30, 2, 5, .8, "#fffbe6");
    shape(g, [[x - 5, y - 31], [x, y - 35], [x + 5, y - 31]], "#355e60");
    oval(g, x, y - 36, 1, 1, "#355e60");
  }
  function bench(g, x, y) {
    oval(g, x, y + 1, 16, 2.4, "#2f6b5026");
    [-11, 11].forEach(dx => line(g, [[x + dx, y], [x + dx, y - 6]], "#3f6a68", 1.6));
    [-14, 14].forEach(dx => line(g, [[x + dx, y - 7], [x + dx, y - 15]], "#3f6a68", 1.2));
    box(g, x - 15, y - 8, 30, 3, 1.2, "#e8ad6c");
    box(g, x - 15, y - 6, 30, 1, .5, "#c88a4c");
    box(g, x - 15, y - 14, 30, 3, 1.2, "#d99a5c");
    box(g, x - 14, y - 14, 28, 1, .5, "#f0c088");
  }
  function trampoline(g, x, y) {
    oval(g, x, y + 2, 22, 4, "#2f6b5026");
    [-15, 15].forEach(dx => line(g, [[x + dx, y - 5], [x + dx, y + 1]], "#3f6a68", 2));
    oval(g, x, y - 5, 20, 6, "#e56d8c");
    oval(g, x, y - 6, 20, 6, "#ff8fa8");
    oval(g, x, y - 6, 16, 4, "#5a6fb0");
    oval(g, x - 4, y - 7, 8, 1.4, "#7388c8");
    for (let a = 0; a < 8; a++) oval(g, x + Math.cos(a * .785 + .39) * 18, y - 6 + Math.sin(a * .785 + .39) * 5, .9, .9, "#fff6fb");
  }
  function sandcastle(g, x, y) {
    oval(g, x, y + 1, 20, 3, "#a98a5a33");
    box(g, x - 16, y - 12, 32, 12, 1, "#e9cf95");
    box(g, x + 6, y - 12, 10, 12, 1, "#dcc083");
    [-16, -3, 10].forEach(dx => {
      box(g, x + dx, y - 20, 7, 9, 1, "#dfc083");
      box(g, x + dx, y - 22, 2, 3, 0, "#dfc083"); box(g, x + dx + 5, y - 22, 2, 3, 0, "#dfc083");
      box(g, x + dx + 2.5, y - 17, 2, 3, 1, "#b89a62");
    });
    g.fillStyle = "#a98756";
    g.beginPath(); g.arc(x + .5, y - 1, 4, Math.PI, 0); g.fill();
    box(g, x - 3.5, y - 2, 8, 2, 0, "#a98756");
    line(g, [[x, y - 20], [x, y - 31]], "#8a6a4a", 1);
    shape(g, [[x, y - 31], [x + 8, y - 28], [x, y - 25]], "#ff8fa8");
  }
  function beachball(g, x, y) {
    oval(g, x, y + 1, 9, 2, "#a98a5a33");
    oval(g, x, y - 8, 9, 9, "#fffdf6");
    shape(g, [[x, y - 17], [x + 8, y - 11], [x, y - 8]], "#ff8fa8");
    shape(g, [[x, y - 8], [x - 8, y - 12], [x - 3, y - 16]], "#7ab8ff");
    shape(g, [[x, y - 8], [x + 7, y - 3], [x - 4, y]], "#ffd27a");
    oval(g, x - 3, y - 12, 2, 1.4, "#ffffffcc");
  }
  function cakeTable(g, x, y) {
    oval(g, x, y + 1, 18, 3, "#3f6a6822");
    box(g, x - 16, y - 14, 32, 14, 2, "#fffdf6");
    box(g, x - 16, y - 4, 32, 4, 1, "#f1e6dc");
    for (let i = 0; i < 6; i++) oval(g, x - 13.5 + i * 5.4, y - 13, 2.7, 2.2, "#ffd6e3");
    box(g, x - 9, y - 22, 18, 8, 1, "#ffc9dc");
    box(g, x - 6, y - 29, 12, 7, 1, "#fff0f6");
    box(g, x - 9, y - 22, 18, 2, 1, "#fff6fb");
    [-6, -1, 4].forEach(dx => box(g, x + dx, y - 21, 2, 3.4, 1, "#fff6fb"));
    [-7, 0, 7].forEach(dx => oval(g, x + dx, y - 16, 1, 1, "#ff8fa8"));
    box(g, x - 6, y - 29, 12, 1.6, .8, "#ffd6e3");
    heart(g, x, y - 32, .8, "#ff6f95");
  }
  function telescope(g, x, y) {
    oval(g, x, y + 1, 12, 2.4, "#23474a");
    line(g, [[x, y - 14], [x - 7, y]], "#c7b4f0", 1.6); line(g, [[x, y - 14], [x + 7, y]], "#c7b4f0", 1.6);
    line(g, [[x, y - 14], [x, y - 1]], "#a995d8", 1.2);
    line(g, [[x - 9, y - 10], [x + 11, y - 24]], "#f5f2ff", 5);
    line(g, [[x + 7, y - 21], [x + 11, y - 24]], "#ffd27a", 5.6);
    oval(g, x - 9, y - 10, 1.6, 1.6, "#6f5bc4");
  }
  function snowballs(g, x, y) {
    oval(g, x, y + 1, 18, 3, "#9ab4c84a");
    [[-8, 0, 7], [7, 0, 7], [0, -9, 7]].forEach(([dx, dy, r]) => {
      oval(g, x + dx, y + dy - r, r, r, "#d3e2ef");
      oval(g, x + dx - .6, y + dy - r - .8, r - .8, r - 1, "#fffefb");
    });
  }
  function bunting(g, x0, y0, x1, y1, sag = 10) {
    const colours = ["#ff8fa8", "#ffd27a", "#8fd0c8", "#b9a4e8"], at = t => [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + Math.sin(t * Math.PI) * sag];
    const pts = Array.from({length: 21}, (_, i) => at(i / 20));
    line(g, pts, "#6d8b86", .6);
    for (let i = 1; i < 12; i++) {
      const [x, y] = at(i / 12);
      shape(g, [[x - 3, y], [x + 3, y], [x, y + 6]], colours[i % 4]);
    }
  }
  function fountain(g, x, y) {
    oval(g, x, y + 1, 30, 7, "#2f6b5026");
    oval(g, x, y - 2.4, 28, 8, "#b7a88e");
    oval(g, x, y - 3.6, 28, 7.4, "#d9ccb4");
    oval(g, x, y - 5, 24, 6, "#5fb6c8");
    oval(g, x, y - 4.4, 22, 4.6, "#79c9d6");
    oval(g, x - 8, y - 6, 8, 1.2, "#d9f4f7");
    oval(g, x + 9, y - 3.4, 5, .9, "#b9e7ee");
    box(g, x - 3.5, y - 18, 7, 13, 2, "#d9ccb4");
    box(g, x + 1, y - 18, 2.5, 13, 1, "#b7a88e");
    oval(g, x, y - 17.4, 11, 3.4, "#b7a88e");
    oval(g, x, y - 18, 11, 3.4, "#d9ccb4");
    oval(g, x, y - 19, 8.6, 2.2, "#8ed6e0");
    g.strokeStyle = "#d9f4f7"; g.lineWidth = 1.2;
    for (const d of [-1, 1]) { g.beginPath(); g.moveTo(x, y - 25); g.quadraticCurveTo(x + d * 10, y - 28, x + d * 13, y - 7); g.stroke(); }
    oval(g, x, y - 24, 2.2, 3.6, "#eafafc");
  }

  // ---- Chunky pixels ------------------------------------------------------------------
  const FINE = 3;
  /** A `w` by `h` picture in hard pixels of whatever `draw` paints. */
  function crisp(w, h, draw) {
    const big = document.createElement("canvas");
    big.width = w * FINE; big.height = h * FINE;
    const ink = big.getContext("2d");
    ink.scale(FINE, FINE);
    draw(ink);
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    const out = cv.getContext("2d");
    out.imageSmoothingEnabled = false;
    out.drawImage(big, 0, 0, w, h);
    return cv;
  }
  // Fewer shades, so a sky fades in bands like pixel art instead of a smooth blur.
  const RICH = 1.22;     // how much stronger the colours come out than they were painted
  function bands(cv, step = 8) {
    const g = cv.getContext("2d"), img = g.getImageData(0, 0, cv.width, cv.height), d = img.data;
    for (let i = 0; i < d.length; i += 4) {
      const grey = (d[i] + d[i + 1] + d[i + 2]) / 3;
      for (let k = 0; k < 3; k++) d[i + k] = Math.max(0, Math.min(255, Math.round((grey + (d[i + k] - grey) * RICH) / step) * step));
    }
    g.putImageData(img, 0, 0);
    return cv;
  }

  // ---- Ink ----------------------------------------------------------------------------
  // Everything a pal could walk up to gets an edge one pixel wide, in a deep shade of its
  // own colour, so it stands out like the buttons on the page. Far-off things are left
  // soft, which keeps them far off. Shadows and glows are too faint to count as an edge.
  let inking = false;
  const sheetBig = document.createElement("canvas"), sheetSmall = document.createElement("canvas");
  function ink(g, draw) {
    if (inking) return draw(g);
    const w = g.canvas.width, h = g.canvas.height, lw = Math.round(w / FINE), lh = Math.round(h / FINE);
    sheetBig.width = w; sheetBig.height = h; sheetSmall.width = lw; sheetSmall.height = lh;     // setting the size wipes them
    const big = sheetBig.getContext("2d"), small = sheetSmall.getContext("2d", {willReadFrequently: true});
    big.setTransform(g.getTransform());
    inking = true;
    try { draw(big); } finally { inking = false; }
    small.imageSmoothingEnabled = false;
    small.drawImage(sheetBig, 0, 0, lw, lh);
    const img = small.getImageData(0, 0, lw, lh), d = img.data, from = new Uint8ClampedArray(d);
    const solid = i => from[i * 4 + 3] >= 200;
    for (let y = 0, i = 0; y < lh; y++) for (let x = 0; x < lw; x++, i++) {
      if (solid(i)) continue;
      const n = y + 1 < lh && solid(i + lw) ? i + lw : y && solid(i - lw) ? i - lw : x && solid(i - 1) ? i - 1 : x + 1 < lw && solid(i + 1) ? i + 1 : -1;
      if (n < 0) continue;
      d[i * 4] = from[n * 4] * .36 + 10; d[i * 4 + 1] = from[n * 4 + 1] * .28 + 6; d[i * 4 + 2] = from[n * 4 + 2] * .42 + 26; d[i * 4 + 3] = 255;
    }
    small.putImageData(img, 0, 0);
    g.save();
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.imageSmoothingEnabled = false;
    g.drawImage(sheetSmall, 0, 0, w, h);
    g.restore();
  }
  const inked = draw => (g, ...rest) => ink(g, g => draw(g, ...rest));
  /** Draws something without its edge, for things that are far away. */
  function soft(draw) { inking = true; try { draw(); } finally { inking = false; } }
  tree = inked(tree); pine = inked(pine); shrub = inked(shrub); rock = inked(rock); mushroom = inked(mushroom); cottage = inked(cottage);
  lamp = inked(lamp); bench = inked(bench); trampoline = inked(trampoline); sandcastle = inked(sandcastle); beachball = inked(beachball);
  cakeTable = inked(cakeTable); telescope = inked(telescope); snowballs = inked(snowballs); fountain = inked(fountain); coral = inked(coral);

  // ---- The places ---------------------------------------------------------------------
  const PLACES = {
    park(g) {
      sky(g, "#9fd8ee", "#e6f6ee");
      sun(g, 262, 26, 13);
      mountain(g, 118, 100, 62, 46, "#c2e2d8", "#f0f9f4");
      mountain(g, 196, 100, 50, 34, "#cbe7dc", "#f3faf6");
      hills(g, 100, "#b5dcb0", [[45, 66, 110], [165, 72, 215], [275, 60, 320]]);
      soft(() => [[150, 88, .3], [176, 90, .36], [226, 87, .3]].forEach(([x, y, s]) => tree(g, x, y, s, ["#7fbf8c", "#8fca98", "#a4d6a8"], null, "#6fb080")));
      hills(g, 106, "#9fd09a", [[70, 84, 150], [235, 80, 320]]);
      cottage(g, 70, 98, "#fff3dc", "#e8728a");
      ground(g, 106, "#a4d48d", "#86c279");
      patches(g, "#b6df9f", 112);
      tufts(g, 112, "#6fb06a");
      // a soft path that sweeps through the middle, with a darker edge and pebbles
      const path = (dy, colour) => {
        g.fillStyle = colour;
        g.beginPath();
        g.moveTo(0, 150 + dy); g.bezierCurveTo(90, 128 + dy, 210, 168 + dy, 320, 136 + dy);
        g.lineTo(320, 158 + dy); g.bezierCurveTo(210, 188 + dy, 90, 150 + dy, 0, 174 + dy);
        g.closePath(); g.fill();
      };
      path(2, "#d9c594"); path(0, "#f4e4c1");
      for (let i = 0; i < 14; i++) {
        const t = (i + .5) / 14, u = 1 - t;
        const x = 3 * u * u * t * 90 + 3 * u * t * t * 210 + t * t * t * 320;
        const y = u * u * u * 150 + 3 * u * u * t * 128 + 3 * u * t * t * 168 + t * t * t * 136 + 5 + (i * 7) % 13;
        oval(g, x, y, 2.2 - (i % 2) * .8, 1, i % 3 ? "#e3cfa0" : "#fff6dc");
      }
      [[34, 106, .9], [286, 107, 1], [246, 101, .72], [14, 118, 1.15], [310, 124, 1.2]].forEach(([x, y, s]) => tree(g, x, y, s));
      shrub(g, 66, 116, .9); shrub(g, 296, 132, .8, undefined, "#fff0a8");
      mushroom(g, 26, 124); mushroom(g, 32, 126);
      rock(g, 236, 124, .8); rock(g, 88, 136, .6);
      fountain(g, 160, 118);
      bench(g, 104, 118);
      bench(g, 218, 118);
      trampoline(g, 262, 136);
      lamp(g, 128, 113);
      lamp(g, 193, 113);
      bunting(g, 128, 83, 193, 83, 7);
      // a kite, tied to the bench
      line(g, [[212, 48], [216, 70], [222, 104]], "#ffffffcc", .6);
      ink(g, g => {
        shape(g, [[212, 28], [219, 38], [212, 50], [205, 38]], "#ff8fa8");
        shape(g, [[212, 28], [219, 38], [212, 38]], "#ffd27a");
        shape(g, [[212, 38], [212, 50], [205, 38]], "#8fd0c8");
        [[214, 55, "#b9a4e8"], [215, 61, "#ffd27a"]].forEach(([x, y, c]) => shape(g, [[x - 2.5, y - 1.5], [x + 2.5, y + 1.5], [x + 2.5, y - 1.5], [x - 2.5, y + 1.5]], c));
      });
      flowers(g, 128, ["#ff9fb5", "#fff0a8", "#c7b4f0", "#fff"], 20);
    },
    wedding(g) {
      sky(g, "#f9d5e5", "#fdf3e2");
      sun(g, 58, 30, 12, "#fff6cf", "#fff3d0");
      mountain(g, 100, 102, 60, 42, "#ecd0e4", "#fff6fa");
      mountain(g, 226, 102, 66, 50, "#e6cbe4", "#fff6fa");
      hills(g, 102, "#cfe4b8", [[70, 74, 170], [250, 70, 320]]);
      // a little chapel up the hill
      box(g, 236.5, 70, 7, 12, 0, "#fffdf6");
      shape(g, [[234.5, 71], [240, 62], [245.5, 71]], "#f29bb5");
      oval(g, 240, 75.5, 1.4, 1.7, "#ffd27a");
      box(g, 229, 88, 22, 15, 1, "#fffdf6");
      box(g, 246, 88, 5, 15, 1, "#f1e6dc");
      shape(g, [[226, 90], [240, 78], [254, 90]], "#f29bb5");
      box(g, 237.5, 95, 5, 8, 2, "#c98aa6");
      oval(g, 233, 95, 1.6, 2.2, "#ffe39a"); oval(g, 247, 95, 1.6, 2.2, "#ffe39a");
      ground(g, 104, "#b4dc9c", "#98cd87");
      patches(g, "#c6e6ae", 112);
      tufts(g, 112, "#7fbd78", 10);
      shape(g, [[143, 106], [177, 106], [204, 180], [116, 180]], "#fffdf6");
      shape(g, [[146, 106], [174, 106], [200, 180], [120, 180]], "#fbd3e0");
      shape(g, [[153, 106], [167, 106], [186, 180], [134, 180]], "#fde4ec");
      for (let i = 0; i < 14; i++) oval(g, 160 + ((i * 37) % 31 - 15) * (1 + i / 14), 112 + i * 4.8, 1.6, 1, ["#ff9fb5", "#fff", "#ffd27a"][i % 3]);
      [[52, 108, .85], [268, 108, .85], [18, 118, 1.1], [304, 118, 1.1]].forEach(([x, y, s]) => tree(g, x, y, s, ["#4f9a72", "#68ad82", "#83c096"], "#ffc3d6", "#3f8763"));
      shrub(g, 84, 112, .8, ["#4f9a72", "#68ad82", "#83c096"]); shrub(g, 290, 132, .8, ["#4f9a72", "#68ad82", "#83c096"], "#fff");
      for (const dx of [-1, 1]) for (let row = 0; row < 2; row++) {
        const y = 119 + row * 11, x = 160 + dx * (46 + row * 4);
        for (let c = 0; c < 2; c++) {
          const cx = x + dx * c * 16;
          ink(g, g => {
            oval(g, cx, y + 1, 7, 1.6, "#3f6a6833");
            box(g, cx - 5, y - 10, 10, 11, 2, "#fffdf6");
            box(g, cx + 2, y - 10, 3, 11, 1, "#efe6dc");
            box(g, cx - 5.5, y - 4, 11, 3, 1, "#f6d4e0");
            oval(g, cx, y - 8, 1.5, 1.5, "#ff9fb5");
          });
        }
      }
      // balloons tied to the arch
      for (const d of [-1, 1]) {
        balloon(g, 160 + d * 46, 66, "#ff9fb5", 160 + d * 32, 86);
        balloon(g, 160 + d * 39, 58, "#ffd27a", 160 + d * 32, 86);
        balloon(g, 160 + d * 51, 55, "#c7b4f0", 160 + d * 32, 86);
      }
      // the arch
      ink(g, g => {
        line(g, [[128, 110], [128, 78], [133, 60], [147, 48], [160, 45], [173, 48], [187, 60], [192, 78], [192, 110]], "#e6dccb", 6);
        line(g, [[128, 110], [128, 78], [133, 60], [147, 48], [160, 45], [173, 48], [187, 60], [192, 78], [192, 110]], "#f7f0e2", 4);
        const blooms = ["#ff9fb5", "#ffd27a", "#fff", "#d6b8f0"];
        [[128, 108], [127, 98], [128, 88], [129, 78], [132, 68], [138, 58], [146, 51], [155, 47], [165, 47], [174, 51], [182, 58], [188, 68], [191, 78], [192, 88], [193, 98], [192, 108]]
          .forEach(([x, y], i) => { oval(g, x + 3, y + 2, 2.2, 2.2, "#7fbf8c"); oval(g, x, y, 4, 4, blooms[i % 4]); oval(g, x - 1, y - 1, 1.4, 1.4, "#ffffff99"); });
        heart(g, 160, 62, 2.2, "#ff6f95");
        oval(g, 157.6, 58.6, 1.4, 1.2, "#ffc3d4");
      });
      flowers(g, 130, ["#ff9fb5", "#fff", "#ffd27a"], 14);
      cakeTable(g, 44, 130);
    },
    beach(g) {
      sky(g, "#86d2ec", "#e4f6f0", 92);
      sun(g, 256, 28, 14, "#fff0b0");
      // an island far out
      oval(g, 108, 85, 26, 5, "#7fbf9a"); oval(g, 102, 83, 12, 4, "#93cfa8");
      line(g, [[118, 83], [120, 73]], "#a9835a", 1);
      [[-5, 1], [5, 1], [-4, -3], [4, -3]].forEach(([dx, dy]) => line(g, [[120, 73], [120 + dx, 73 + dy]], "#4f9f74", 1));
      const sea = g.createLinearGradient(0, 84, 0, 118);
      sea.addColorStop(0, "#4fb3d0");
      sea.addColorStop(1, "#a7e3df");
      g.fillStyle = sea;
      g.fillRect(0, 84, W, 36);
      box(g, 0, 84, W, 1, 0, "#9fdcea");
      for (let i = 0; i < 6; i++) oval(g, 256 + ((i * 7) % 9 - 4), 87 + i * 4, 10 - i, .7, "#fff6c8");
      for (let i = 0; i < 9; i++) oval(g, (i * 53 + 18) % W, 90 + (i * 11) % 24, 14, 1, "#d6f4f2");
      // a sailing boat
      shape(g, [[167, 95], [187, 95], [183, 99.5], [171, 99.5]], "#fffdf6");
      box(g, 169, 96.5, 16, 1.2, 0, "#ff8fa8");
      line(g, [[177, 95], [177, 79]], "#8a6a4a", 1);
      shape(g, [[178, 80], [178, 93], [188, 93]], "#fffdf6");
      shape(g, [[176, 83], [176, 93], [169, 93]], "#ffd27a");
      oval(g, 177, 100.5, 11, .8, "#d6f4f2");
      const shore = (dy, colour) => {
        g.fillStyle = colour;
        g.beginPath();
        g.moveTo(0, 116 + dy); g.bezierCurveTo(80, 108 + dy, 220, 124 + dy, 320, 112 + dy);
        g.lineTo(320, H); g.lineTo(0, H);
        g.closePath(); g.fill();
      };
      shore(-2, "#f4fdfc"); shore(0, "#e6d3a0"); shore(3, "#f8ecc9");
      ground(g, 134, "#f8ecc900", "#efdcaf");
      patches(g, "#fdf4da", 124);
      for (let i = 0; i < 26; i++) oval(g, (i * 71 + 9) % W, 126 + (i * 31) % 50, .8, .8, "#dcc48e");
      const palm = (x, y, s, lean) => {
        ink(g, g => {
          oval(g, x + lean * s * 3, y + 1, 12 * s, 2.5 * s, "#a98a5a33");
          g.strokeStyle = "#a9835a"; g.lineWidth = 3.2 * s; g.lineCap = "round";
          g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + lean * 2 * s, y - 24 * s, x + lean * 12 * s, y - 44 * s); g.stroke();
          g.strokeStyle = "#c29a6c"; g.lineWidth = 1;
          g.beginPath(); g.moveTo(x - lean * s, y - 2); g.quadraticCurveTo(x + lean * 1 * s, y - 24 * s, x + lean * 11 * s, y - 42 * s); g.stroke();
          const tx = x + lean * 12 * s, ty = y - 44 * s;
          [[-22, 2], [-16, 12], [16, 12], [22, 2], [8, -9], [-9, -8]].forEach(([dx, dy], i) => {
            g.fillStyle = i % 2 ? "#4f9f74" : "#62b083";
            g.beginPath(); g.moveTo(tx, ty);
            g.quadraticCurveTo(tx + dx * s * .6, ty - 9 * s + dy * s * .3, tx + dx * s, ty + dy * s);
            g.quadraticCurveTo(tx + dx * s * .5, ty + dy * s * .1, tx, ty); g.fill();
          });
          oval(g, tx - 2, ty + 2, 2 * s, 2 * s, "#8a6a4a"); oval(g, tx + 3, ty + 2, 2 * s, 2 * s, "#8a6a4a");
        });
      };
      palm(30, 124, 1.15, 1); palm(292, 126, 1.2, -1); palm(64, 114, .75, 1);
      // a surfboard stuck in the sand
      ink(g, g => {
        oval(g, 148, 125, 7, 1.6, "#a98a5a33");
        oval(g, 148, 110, 4.6, 15, "#8fd0c8");
        box(g, 147, 96, 2, 28, 1, "#fffdf6");
        oval(g, 148, 104, 2.4, 2.4, "#ff8fa8");
      });
      sandcastle(g, 176, 137); beachball(g, 72, 153);
      // a little pier to fish from
      [133, 147].forEach(x => line(g, [[x, 100], [x, 131]], "#7d573f", 2.4));
      box(g, 131, 102, 18, 27, 1, "#c79a66");
      for (let y = 107; y < 128; y += 5) line(g, [[132, y], [148, y]], "#a87c4e", .8);
      // a bucket and spade
      ink(g, g => {
        shape(g, [[197, 130], [207, 130], [205.5, 139], [198.5, 139]], "#7ab8ff");
        box(g, 196.5, 129, 11, 2, 1, "#a9d2ff");
        line(g, [[211, 139], [215, 128]], "#ff8fa8", 1.2); oval(g, 211, 139, 2, 1.4, "#ff8fa8");
      });
      // an umbrella and a towel
      ink(g, g => {
        oval(g, 232, 126, 18, 3, "#a98a5a2e");
        line(g, [[232, 126], [232, 92]], "#fffdf6", 1.6);
        g.fillStyle = "#ff8fa8"; g.beginPath(); g.moveTo(208, 100); g.quadraticCurveTo(232, 72, 256, 100); g.closePath(); g.fill();
        g.fillStyle = "#fff2c0"; g.beginPath(); g.moveTo(224, 100); g.quadraticCurveTo(232, 76, 240, 100); g.closePath(); g.fill();
        for (let i = 0; i < 6; i++) oval(g, 212 + i * 8, 100, 4, 1.8, i % 2 ? "#fff2c0" : "#ff8fa8");
        oval(g, 232, 85.5, 1.4, 1.4, "#fffdf6");
      });
      ink(g, g => {
        box(g, 104, 126, 30, 12, 2, "#8fd0c8"); box(g, 110, 126, 6, 12, 0, "#fffdf6"); box(g, 122, 126, 6, 12, 0, "#fffdf6");
      });
      [[160, 148, "#ffb37a"], [262, 160, "#ff9fb5"], [82, 164, "#c7b4f0"]].forEach(([x, y, c]) => {
        ink(g, g => {
          for (let a = 0; a < 5; a++) oval(g, x + Math.cos(a * 1.26 - 1.57) * 3, y + Math.sin(a * 1.26 - 1.57) * 3, 1.6, 1.6, c);
          oval(g, x, y, 2, 2, c);
          oval(g, x, y, .8, .8, "#ffffffaa");
        });
      });
      // shells and a little crab
      ink(g, g => {
        [[40, 148], [250, 146], [140, 171], [302, 168]].forEach(([x, y], i) => { oval(g, x, y, 2.6, 2, i % 2 ? "#ffd6e3" : "#fffdf6"); line(g, [[x - 1.5, y + 1], [x, y - 1.4], [x + 1.5, y + 1]], "#e2b8a8", .6); });
      });
      ink(g, g => {
        oval(g, 212, 163, 4.4, 2.8, "#f2785c");
        oval(g, 206.5, 160.5, 1.8, 1.4, "#f2785c"); oval(g, 217.5, 160.5, 1.8, 1.4, "#f2785c");
        oval(g, 210.4, 159.6, .9, .9, "#fffdf6"); oval(g, 213.6, 159.6, .9, .9, "#fffdf6");
      });
    },
    night(g) {
      sky(g, "#18214f", "#5b5a92");
      glow(g, 210, 34, 80, "#8f8ad855");
      for (let i = 0; i < 46; i++) oval(g, starX(i), starY(i, 84), .4 + (i % 3) * .28, .4 + (i % 3) * .28, "#f4f0ff");
      [[120, 18], [176, 44], [250, 22], [296, 52], [22, 60]].forEach(([x, y]) => twinkle(g, x, y, 2, "#fff8d8"));
      glow(g, 62, 34, 44, "#fff3c866");
      g.save();     // a crescent: the moon with a bite out of it
      g.beginPath(); g.rect(0, 0, W, H); g.arc(72, 28, 14, 0, Math.PI * 2, true); g.clip();
      oval(g, 66, 32, 15, 15, "#fff4cf");
      oval(g, 61, 38, 3, 2.4, "#f3e4b4"); oval(g, 56, 29, 1.6, 1.6, "#f3e4b4");
      g.restore();
      mountain(g, 112, 100, 72, 48, "#2c3a6c", "#4d5c94");
      mountain(g, 228, 100, 80, 54, "#283565", "#4d5c94");
      hills(g, 100, "#3a4f7a", [[60, 66, 150], [235, 62, 320]]);
      hills(g, 106, "#2f5f6e", [[90, 84, 190], [270, 88, 320]]);
      ground(g, 106, "#3f7a72", "#2e6060");
      patches(g, "#4a8a7e", 112);
      tufts(g, 112, "#57988a", 12);
      const nightLeaf = ["#2a5f5c", "#35716a", "#44847a"];
      [[30, 106, 1], [292, 106, 1], [70, 102, .75], [252, 102, .72], [10, 120, 1.15], [314, 120, 1.15]].forEach(([x, y, s]) => tree(g, x, y, s, nightLeaf, null, "#1f4b4c"));
      // an owl up in the tree
      ink(g, g => {
        oval(g, 292, 84, 3.2, 3.8, "#7d6a58");
        oval(g, 290.8, 83, 1.1, 1.1, "#ffe39a"); oval(g, 293.4, 83, 1.1, 1.1, "#ffe39a");
      });
      // a tent with a light on inside
      glow(g, 62, 110, 26, "#ffcf7a55");
      ink(g, g => {
        oval(g, 62, 117, 19, 2.6, "#1d3f4466");
        shape(g, [[45, 116], [62, 95], [79, 116]], "#d85f7c");
        shape(g, [[45, 116], [62, 95], [57, 116]], "#f08aa2");
        shape(g, [[56, 116], [62, 103], [68, 116]], "#ffd98a");
        line(g, [[62, 95], [62, 90]], "#c7b4f0", 1); shape(g, [[62, 90], [67, 92], [62, 94]], "#ffd27a");
      });
      // fairy lights from lamp to lamp
      const hang = t => [104 + 112 * t, 83 + Math.sin(t * Math.PI) * 6];
      line(g, Array.from({length: 21}, (_, i) => hang(i / 20)), "#141a40", .6);
      for (let i = 1; i < 12; i++) {
        const [x, y] = hang(i / 12), colour = ["#ffe39a", "#ff9fb5", "#8fd0c8"][i % 3];
        glow(g, x, y + 1.4, 5, colour + "77");
        oval(g, x, y + 1.4, 1.2, 1.2, colour);
      }
      // a campfire in a ring of stones
      glow(g, 160, 118, 54, "#ffb26a88");
      ink(g, g => {
        oval(g, 160, 120, 16, 4, "#23474a");
        for (let a = 0; a < 9; a++) oval(g, 160 + Math.cos(a * .7) * 15, 121 + Math.sin(a * .7) * 3.6, 2.4, 1.6, a % 2 ? "#8f9bb0" : "#a9b4c6");
        shape(g, [[150, 119], [153, 104], [157, 110], [160, 98], [164, 110], [167, 104], [170, 119]], "#ffa95c");
        shape(g, [[155, 119], [158, 108], [160, 112], [163, 106], [165, 119]], "#ffe39a");
        line(g, [[148, 120], [172, 116]], "#6d4a35", 3); line(g, [[148, 116], [172, 120]], "#7d573f", 3);
      });
      lamp(g, 104, 113, true); lamp(g, 216, 113, true);
      bench(g, 128, 130); bench(g, 194, 130);
      telescope(g, 262, 134);
      rock(g, 232, 150, .8, "#5d7f88", "#7b9da2"); rock(g, 96, 160, .7, "#5d7f88", "#7b9da2");
      [[26, 132], [300, 140], [120, 168]].forEach(([x, y]) => { mushroom(g, x, y); glow(g, x, y - 3, 7, "#ff9fb555"); });
    },
    snowy(g) {
      sky(g, "#b0d2ee", "#eaf4fa");
      sun(g, 60, 30, 10, "#fffbe8", "#ffffff");
      mountain(g, 96, 100, 72, 58, "#c3d8ea", "#ffffff");
      mountain(g, 204, 100, 60, 44, "#cfe1ef", "#ffffff");
      mountain(g, 292, 100, 58, 52, "#c0d6e9", "#ffffff");
      hills(g, 98, "#e5f0f8", [[60, 62, 160], [245, 56, 320]]);
      hills(g, 104, "#f3f8fc", [[85, 84, 180], [260, 82, 320]]);
      ground(g, 104, "#f8fbfe", "#dbe8f4");
      patches(g, "#e3edf7", 112);
      // a frozen pond
      oval(g, 70, 152.6, 37, 8.6, "#b9d4e8");
      oval(g, 70, 152, 36, 8, "#cfe6f4");
      oval(g, 70, 151.4, 32, 6.2, "#dff1fa");
      line(g, [[50, 150], [64, 148]], "#ffffff", 1); line(g, [[72, 155], [90, 152]], "#ffffff", 1);
      // a log cabin with the lights on
      ink(g, g => {
        box(g, 269, 77, 5, 12, 0, "#8f6b5a"); box(g, 268, 76, 7, 2, 1, "#fffefb");
        box(g, 247, 93, 30, 14, 1, "#a9744f");
        for (let i = 1; i < 4; i++) line(g, [[248, 93 + i * 3.5], [276, 93 + i * 3.5]], "#8f5f40", .7);
        shape(g, [[243, 94], [262, 79], [281, 94]], "#8a5a44");
        line(g, [[244, 93], [262, 79], [280, 93]], "#fffefb", 3.4);
        box(g, 259, 98, 6, 9, 1, "#6d4a35");
        glow(g, 253, 100, 8, "#ffe39a88"); glow(g, 271, 100, 8, "#ffe39a88");
        box(g, 250, 97, 6, 5, .5, "#ffe39a"); box(g, 268, 97, 6, 5, .5, "#ffe39a");
      });
      [[28, 110, 1], [78, 104, .72], [290, 110, 1.05], [240, 104, .72], [8, 126, 1.2], [314, 128, 1.2]].forEach(([x, y, s]) => pine(g, x, y, s));
      // a snowman
      ink(g, g => {
        oval(g, 160, 122, 16, 3.4, "#9ab4c84a");
        oval(g, 160, 113, 13, 12, "#d3e2ef");
        oval(g, 159, 112, 12, 11, "#fffefb");
        oval(g, 160, 96, 9.5, 9, "#d3e2ef");
        oval(g, 159.4, 95.4, 8.6, 8.2, "#fffefb");
        box(g, 151, 84, 18, 2.4, 1, "#3e4a6a"); box(g, 154, 74, 12, 11, 1, "#3e4a6a"); box(g, 154, 81, 12, 2.2, 0, "#e8728a");
        oval(g, 156.5, 94, 1, 1, "#27324f"); oval(g, 163.5, 94, 1, 1, "#27324f");
        shape(g, [[160, 96], [171, 98], [160, 99]], "#f2a15c");
        [[156, 100], [158.5, 101.2], [161.5, 101.2], [164, 100]].forEach(([x, y]) => oval(g, x, y, .6, .6, "#27324f"));
        box(g, 151, 103, 18, 3, 1, "#e8728a"); box(g, 164, 103, 4, 9, 1, "#e8728a");
        [108, 114].forEach(y => oval(g, 160, y, 1.2, 1.2, "#3e4a6a"));
        line(g, [[150, 108], [138, 100]], "#7d6250", 1.2); line(g, [[170, 108], [182, 100]], "#7d6250", 1.2);
        oval(g, 137, 99, 2.4, 2.4, "#e8728a"); oval(g, 183, 99, 2.4, 2.4, "#e8728a");
      });
      bench(g, 104, 122); bench(g, 220, 122);
      [[104, 107.4], [220, 107.4]].forEach(([x, y]) => box(g, x - 15, y, 30, 1.6, .8, "#fffefb"));
      // a sledge
      ink(g, g => {
        oval(g, 192, 137, 11, 1.8, "#9ab4c84a");
        line(g, [[183, 136], [201, 136], [203, 133]], "#7d6250", 1.2);
        box(g, 184, 130, 16, 3, 1, "#e8728a");
        [187, 197].forEach(x => line(g, [[x, 133], [x, 136]], "#7d6250", 1));
      });
      snowballs(g, 268, 140);
      for (let i = 0; i < 12; i++) twinkle(g, (i * 89 + 40) % W, 118 + (i * 37) % 58, 1.5, "#ffffff");
    },
    // ❄️ The Snow Village, open in winter: a starry evening, cottages with their lights on, and the class
    // tree. The ornaments, the snowman and the presents change, so they're painted on top as they happen.
    village(g) {
      sky(g, "#545aa8", "#f7cbdc");
      for (let i = 0; i < 16; i++) twinkle(g, (i * 71 + 23) % W, 6 + (i * 37) % 52, i % 3 ? .8 : 1.3, "#fff6d8");
      glow(g, 262, 24, 16, "#fff6d855");
      oval(g, 262, 24, 8, 8, "#fff6d8"); oval(g, 259, 22, 2, 1.6, "#f3e6bf"); oval(g, 265, 27, 1.4, 1.2, "#f3e6bf");
      mountain(g, 60, 100, 70, 46, "#8d8fd0", "#f2f0ff");
      mountain(g, 250, 100, 80, 52, "#9b9ad6", "#f2f0ff");
      hills(g, 98, "#d9def4", [[40, 60, 150], [230, 60, 320]]);
      ground(g, 104, "#f8fbfe", "#dbe3f4");
      patches(g, "#e6ebf7", 112);
      cottage(g, 172, 106, "#e8b5a0", "#f7f9ff");
      cottage(g, 214, 104, "#b9c7e8", "#f7f9ff");
      cottage(g, 300, 106, "#c9e3c2", "#f7f9ff");
      lamp(g, 142, 124, true); lamp(g, 314, 124, true);
      // the class tree, with lights. The star on top lights up when it has lots of ornaments.
      pine(g, VILLAGE_TREE_X, 124, 2.1, "#2f7a62", "#f5fbff", "#25604f");
      [[-14, 70, "#ff5fa2"], [12, 82, "#ffd93b"], [-22, 96, "#7ab8ff"], [24, 104, "#ff5fa2"], [-4, 58, "#7ab8ff"], [6, 92, "#ff9a3c"], [-26, 116, "#ffd93b"], [30, 118, "#7ab8ff"]]
        .forEach(([dx, y, c]) => { glow(g, VILLAGE_TREE_X + dx, y, 3, c + "66"); oval(g, VILLAGE_TREE_X + dx, y, .9, .9, c); });
    },
    candy(g) {
      sky(g, "#ffcfe6", "#fff0d8");
      // a rainbow from cloud to cloud
      ["#ff8fa8", "#ffb37a", "#ffe08a", "#8fd0c8", "#b9a4e8"].forEach((colour, i) => {
        g.strokeStyle = colour; g.lineWidth = 2.6;
        g.beginPath(); g.ellipse(158, 44, 90 - i * 2.5, 34 - i * 2.5, 0, Math.PI, 0); g.stroke();
      });
      cloud(g, 70, 38, 1.4, "#fff6fb", "#ffd9ea"); cloud(g, 246, 36, 1.3, "#fff6fb", "#ffd9ea");
      // two scoops of ice cream for mountains
      oval(g, 112, 92, 31, 28, "#f3dfa6"); oval(g, 110, 90, 29, 26, "#fff0c2"); oval(g, 100, 78, 9, 5, "#fff8dc");
      oval(g, 112, 62, 3.6, 3.6, "#e8576b"); oval(g, 111, 61, 1.2, 1.2, "#ffc3d4"); line(g, [[113, 59], [117, 53]], "#8a6a4a", .8);
      oval(g, 212, 96, 27, 25, "#a9dcca"); oval(g, 210, 94, 25, 23, "#c9f0e4"); oval(g, 201, 84, 8, 4.4, "#e2f8f0");
      [[204, 96], [218, 86], [222, 99], [210, 78]].forEach(([x, y]) => box(g, x, y, 2.4, 1.6, .5, "#7d573f"));
      hills(g, 100, "#ffbcd6", [[62, 64, 165], [248, 58, 320]]);
      hills(g, 106, "#d9c2f4", [[92, 82, 190], [268, 84, 320]]);
      // a gingerbread house
      ink(g, g => {
        box(g, 144, 83, 32, 18, 1, "#c98a55");
        box(g, 170, 83, 6, 18, 1, "#b47a48");
        shape(g, [[139, 86], [160, 66], [181, 86]], "#a86a3d");
        line(g, [[140, 86], [160, 67], [180, 86]], "#fffafc", 3);
        for (let i = 0; i < 7; i++) oval(g, 143 + i * 5.7, 87, 2.4, 2, "#fffafc");
        [[153, 80, "#ff8fa8"], [160, 75, "#8fd0c8"], [167, 80, "#ffd27a"]].forEach(([x, y, c]) => oval(g, x, y, 1.6, 1.6, c));
        box(g, 156.5, 91, 7, 10, 3, "#8a4f2d"); oval(g, 161.6, 96.5, .7, .7, "#ffd27a");
        box(g, 146.5, 91, 6, 6, 1, "#ffe39a"); box(g, 167.5, 91, 6, 6, 1, "#ffe39a");
      });
      ground(g, 106, "#ffe0ec", "#ffcfe2");
      // icing along the top of the ground
      box(g, 0, 104.6, W, 3, 0, "#fffafc");
      for (let i = 0; i < 23; i++) oval(g, i * 15 + 4, 108, 5, 2 + (i * 7) % 4, "#fffafc");
      for (let i = 0; i < 40; i++) {
        const x = (i * 61 + 7) % W, y = 116 + (i * 23) % 62;
        box(g, x, y, 3.4, 1.2, .6, ["#ff8fa8", "#ffd27a", "#8fd0c8", "#b9a4e8"][i % 4]);
      }
      // sweets lying about
      [[60, 152], [212, 164], [282, 144], [140, 170]].forEach(([x, y]) => {
        ink(g, g => {
          oval(g, x, y + .8, 4, 2.6, "#c76a9a33");
          oval(g, x, y, 3.6, 2.4, "#fffafc");
          shape(g, [[x, y], [x - 3.4, y - 1.4], [x - 1.6, y - 2.4]], "#ff6f95"); shape(g, [[x, y], [x + 3.4, y + 1.4], [x + 1.6, y + 2.4]], "#ff6f95");
          shape(g, [[x, y], [x + 2.4, y - 2], [x + 3.6, y - .4]], "#ff6f95"); shape(g, [[x, y], [x - 2.4, y + 2], [x - 3.6, y + .4]], "#ff6f95");
        });
      });
      ink(g, g => {
        [[104, 146], [250, 170], [22, 168], [182, 150]].forEach(([x, y], i) => heart(g, x, y, .9, ["#ff8fa8", "#b9a4e8", "#8fd0c8", "#ffb37a"][i]));
      });
      const lolly = (x, y, s, a, b) => {
        ink(g, g => {
          oval(g, x, y, 9 * s, 2 * s, "#c76a9a2e");
          line(g, [[x, y], [x, y - 32 * s]], "#fffdf6", 2.6 * s);
          oval(g, x, y - 41 * s, 15 * s, 15 * s, "#1b153018");
          oval(g, x, y - 42 * s, 15 * s, 15 * s, a);
          for (let r = 11; r > 1; r -= 4) { g.strokeStyle = b; g.lineWidth = 2 * s; g.beginPath(); g.arc(x, y - 42 * s, r * s, .5, 5.4); g.stroke(); }
          oval(g, x - 6 * s, y - 49 * s, 3.4 * s, 2 * s, "#ffffffaa");
          shape(g, [[x - 5 * s, y - 24 * s], [x, y - 27 * s], [x - 5 * s, y - 30 * s]], a); shape(g, [[x + 5 * s, y - 24 * s], [x, y - 27 * s], [x + 5 * s, y - 30 * s]], a);
        });
      };
      lolly(34, 112, 1, "#ff8fa8", "#fff0f6"); lolly(286, 114, 1.05, "#8fd0c8", "#eafffa"); lolly(82, 106, .7, "#ffd27a", "#fff6da"); lolly(238, 106, .7, "#b9a4e8", "#f3ecff");
      const cupcake = (x, y, wrap, top) => {
        ink(g, g => {
          oval(g, x, y + .6, 7, 1.6, "#c76a9a2e");
          shape(g, [[x - 5.5, y - 7], [x + 5.5, y - 7], [x + 4, y], [x - 4, y]], wrap);
          [-2.4, 0, 2.4].forEach(dx => line(g, [[x + dx * 1.2, y - 6.4], [x + dx, y - .6]], "#ffffff88", .7));
          oval(g, x, y - 8, 7, 3.2, top); oval(g, x, y - 11, 5, 2.8, "#fff6fb"); oval(g, x, y - 13.6, 3, 2.2, top);
          oval(g, x, y - 16.4, 1.6, 1.6, "#e8576b");
        });
      };
      cupcake(104, 116, "#8fd0c8", "#ff9fb5"); cupcake(220, 117, "#ffd27a", "#b9a4e8");
      [[126, 118, "#ff8fa8", "#e56d8c"], [196, 120, "#8fd0c8", "#6fb8b0"], [160, 112, "#ffd27a", "#eab858"]].forEach(([x, y, c, low]) => {
        ink(g, g => {
          oval(g, x, y, 14, 2.4, "#c76a9a2e");
          g.fillStyle = low;
          g.beginPath(); g.moveTo(x - 13, y); g.quadraticCurveTo(x, y - 27, x + 13, y); g.closePath(); g.fill();
          g.fillStyle = c;
          g.beginPath(); g.moveTo(x - 13, y - 1.6); g.quadraticCurveTo(x, y - 28, x + 11, y - 2.6); g.closePath(); g.fill();
          oval(g, x - 4, y - 10, 2.4, 3.4, "#ffffff77");
          [[-7, -4], [3, -6], [7, -3], [-1, -3]].forEach(([dx, dy]) => oval(g, x + dx, y + dy, .7, .7, "#ffffffcc"));
        });
      });
      g.lineCap = "round";
      for (const x of [14, 306]) {
        ink(g, g => {
          g.strokeStyle = "#fffdf6"; g.lineWidth = 6; g.beginPath(); g.moveTo(x, 138); g.lineTo(x, 110); g.arc(x + 7, 110, 7, Math.PI, 0); g.stroke();
          g.strokeStyle = "#ff8fa8"; g.lineWidth = 6; g.setLineDash([3, 6]); g.beginPath(); g.moveTo(x, 138); g.lineTo(x, 110); g.arc(x + 7, 110, 7, Math.PI, 0); g.stroke(); g.setLineDash([]);
        });
      }
    },
    space(g) {
      sky(g, "#10163e", "#4a3a86", 130);
      glow(g, 124, 52, 76, "#e36fb83c"); glow(g, 296, 92, 62, "#5fd0d03c"); glow(g, 20, 86, 50, "#7f8cff33");
      for (let i = 0; i < 70; i++) oval(g, starX(i), starY(i, 112), .4 + (i % 3) * .3, .4 + (i % 3) * .3, i % 7 ? "#f4f0ff" : "#ffe6a8");
      [[100, 22], [168, 58], [300, 18], [18, 52], [196, 14]].forEach(([x, y]) => twinkle(g, x, y, 2.4, "#ffffff"));
      // a ringed planet
      glow(g, 240, 40, 62, "#b08cf066");
      g.save(); g.translate(240, 40); g.rotate(-.3); g.strokeStyle = "#ffe0a8"; g.lineWidth = 3; g.beginPath(); g.ellipse(0, 0, 34, 8, 0, Math.PI + .1, -.1); g.stroke(); g.restore();
      oval(g, 240, 40, 21, 21, "#c984b4");
      oval(g, 238, 38, 19.4, 19.4, "#e3a0c8");
      g.save(); g.beginPath(); g.arc(240, 40, 21, 0, 7); g.clip();
      box(g, 216, 44, 48, 3.4, 0, "#d38ebc"); box(g, 216, 52, 48, 2.4, 0, "#c984b4"); box(g, 216, 29, 48, 2, 0, "#f0bcdc");
      g.restore();
      oval(g, 232, 31, 7, 4.4, "#f6cfe6");
      g.save(); g.translate(240, 40); g.rotate(-.3); g.strokeStyle = "#ffe0a8"; g.lineWidth = 3; g.beginPath(); g.ellipse(0, 0, 34, 8, 0, .1, Math.PI - .1); g.stroke();
      g.strokeStyle = "#fff3d0"; g.lineWidth = 1; g.beginPath(); g.ellipse(0, 0, 34, 8, 0, .3, Math.PI - .3); g.stroke(); g.restore();
      // a little blue world
      oval(g, 56, 32, 10.6, 10.6, "#4f8fd0"); oval(g, 55, 31, 9.6, 9.6, "#6fb8e8");
      oval(g, 52, 29, 4.4, 3, "#8fd9a0"); oval(g, 59, 35, 3.4, 2.4, "#8fd9a0"); oval(g, 60, 27, 2, 1.2, "#f4fbff");
      shape(g, [[0, 108], [0, 100], [16, 92], [30, 102], [52, 86], [72, 101], [96, 94], [120, 104], [150, 90], [176, 102], [204, 88], [230, 103], [258, 91], [284, 102], [304, 93], [320, 100], [320, 108]], "#4f4290");
      hills(g, 108, "#6a5aa8", [[80, 88, 170], [250, 84, 320]]);
      ground(g, 108, "#8c7cc4", "#6f5fa8");
      patches(g, "#9888cc", 114, 8);
      // a glass house to live in
      glow(g, 150, 98, 34, "#9fe8f055");
      ink(g, g => {
        g.fillStyle = "#8fcfe6"; g.beginPath(); g.arc(150, 110, 21, Math.PI, 0); g.fill();
        g.fillStyle = "#b5e6f4"; g.beginPath(); g.arc(149, 110, 19, Math.PI, 0); g.fill();
        box(g, 141, 100, 18, 10, 1, "#f5f2ff"); shape(g, [[139, 101], [150, 94], [161, 101]], "#ff8fa8");
        box(g, 148, 104, 4, 6, 1, "#6f5bc4"); box(g, 143, 103, 3, 3, .5, "#ffe39a"); box(g, 154, 103, 3, 3, .5, "#ffe39a");
        g.strokeStyle = "#ffffffcc"; g.lineWidth = 1.2; g.beginPath(); g.arc(150, 110, 16, Math.PI * 1.15, Math.PI * 1.45); g.stroke();
        box(g, 127, 108, 46, 4, 1.5, "#d9d4f0"); box(g, 127, 110.5, 46, 1.5, .7, "#b5aee0");
        line(g, [[150, 89], [150, 82]], "#d9d4f0", 1); oval(g, 150, 81, 1.6, 1.6, "#ff8fa8");
      });
      // craters
      [[50, 128, 18], [118, 150, 14], [204, 134, 20], [278, 158, 16], [152, 172, 12], [300, 126, 9], [84, 168, 8]].forEach(([x, y, r]) => {
        oval(g, x, y - .8, r, r * .3, "#a798dc");
        oval(g, x, y, r, r * .3, "#5f4f96");
        oval(g, x, y + .8, r * .8, r * .2, "#4f4088");
      });
      // glowing crystals
      const crystal = (x, y, s, colour, light) => {
        ink(g, g => {
          glow(g, x, y - 5 * s, 12 * s, colour + "66");
          shape(g, [[x - 5 * s, y], [x - 3 * s, y - 8 * s], [x - 1 * s, y]], colour);
          shape(g, [[x - 2 * s, y], [x + .5 * s, y - 13 * s], [x + 3 * s, y]], light);
          shape(g, [[x + .5 * s, y - 13 * s], [x + 3 * s, y], [x + 1 * s, y]], colour);
          shape(g, [[x + 2 * s, y], [x + 4.5 * s, y - 7 * s], [x + 6 * s, y]], colour);
        });
      };
      crystal(92, 120, 1, "#5fd0d0", "#b5f2ee"); crystal(304, 118, 1.1, "#ff8fc8", "#ffd0ea"); crystal(238, 114, .8, "#5fd0d0", "#b5f2ee"); crystal(12, 150, .9, "#b9a4e8", "#e6dcff");
      // a flag
      ink(g, g => {
        line(g, [[70, 118], [70, 98]], "#f5f2ff", 1.2);
        shape(g, [[70.5, 98], [82, 101.5], [70.5, 105]], "#ffd27a");
        twinkle(g, 74.5, 101.5, 1.5, "#ff8fa8");
      });
      // a moon buggy
      ink(g, g => {
        oval(g, 270, 122, 13, 2, "#3f2f7455");
        box(g, 259, 112, 22, 6, 2, "#f5f2ff"); box(g, 259, 115.5, 22, 2.5, 1, "#d9d4f0");
        box(g, 263, 107, 9, 6, 2, "#7fc8dc"); oval(g, 265.5, 109, 1.4, 1, "#d6f4f8");
        line(g, [[277, 112], [279, 104]], "#d9d4f0", 1); oval(g, 279, 103, 2.2, 1.4, "#ffd27a");
        [262, 270, 278].forEach(x => { oval(g, x, 120, 3, 3, "#3a2f66"); oval(g, x, 120, 1.2, 1.2, "#a798dc"); });
      });
      // a little rocket, parked
      ink(g, g => {
        oval(g, 40, 116, 15, 3, "#3f2f7455");
        line(g, [[32, 108], [27, 116]], "#b5aee0", 1.4); line(g, [[48, 108], [53, 116]], "#b5aee0", 1.4);
        g.fillStyle = "#f5f2ff"; g.beginPath(); g.moveTo(40, 66); g.quadraticCurveTo(54, 88, 50, 112); g.lineTo(30, 112); g.quadraticCurveTo(26, 88, 40, 66); g.fill();
        g.fillStyle = "#d9d4f0"; g.beginPath(); g.moveTo(40, 66); g.quadraticCurveTo(54, 88, 50, 112); g.lineTo(45, 112); g.quadraticCurveTo(48, 88, 40, 66); g.fill();
        shape(g, [[40, 66], [46, 75], [34, 75]], "#ff8fa8");
        box(g, 30, 101, 20, 2.4, 0, "#ff8fa8");
        oval(g, 40, 88, 6.4, 6.4, "#6f5bc4"); oval(g, 40, 88, 5, 5, "#7fc8dc"); oval(g, 38.4, 86.4, 2, 2, "#d6f4f8");
        shape(g, [[30, 100], [21, 116], [31, 112]], "#ff8fa8"); shape(g, [[50, 100], [59, 116], [49, 112]], "#ff8fa8");
      });
      trampoline(g, 204, 136);
      rock(g, 180, 154, .8, "#5f4f96", "#a798dc"); rock(g, 236, 168, .7, "#5f4f96", "#a798dc"); rock(g, 30, 166, .6, "#5f4f96", "#a798dc");
    },
    // 🌊 Under the sea: the last place the class party meter opens. Sunlight comes down
    // through the water onto a sandy floor with coral, a sunken chest and a reef. The
    // seaweed, fish and bubbles are painted moving in seaLife(), and hold still in 🌿 Calm.
    sea(g) {
      sky(g, "#7fdfee", "#0a3a66", 170);
      glow(g, 160, 4, 120, "#fff6c033");
      // the surface of the water, far above
      for (let i = 0; i < 5; i++) {
        const y = 5 + i * 4;
        line(g, Array.from({length: 17}, (_, n) => [n * 20, y + Math.sin(n * .9 + i) * 1.6]), i % 2 ? "#bff6ff" : "#e8fdff", .8);
      }
      soft(() => {
        hills(g, 96, "#1f6f96", [[60, 76, 150], [245, 72, 320]]);
        hills(g, 105, "#2c88a2", [[95, 92, 200], [280, 88, 320]]);
      });
      // a far-off wreck, and a rowboat half buried in the sand
      soft(() => {
        shape(g, [[18, 104], [46, 100], [58, 108], [36, 112]], "#3a6f8c");
        line(g, [[34, 101], [34, 78]], "#3a6f8c", 2);
        shape(g, [[35, 80], [54, 86], [35, 91]], "#4b86a0");
      });
      ink(g, g => {
        oval(g, 120, 112, 28, 4, "#3f2f7444");
        shape(g, [[94, 104], [146, 104], [138, 116], [102, 116]], "#5b7f86");
        shape(g, [[98, 106], [142, 106], [135, 113], [105, 113]], "#7fa6a4");
        line(g, [[100, 104], [114, 78]], "#7d573f", 2);
        shape(g, [[114, 81], [132, 89], [114, 98]], "#c9d9d2");
        line(g, [[120, 104], [120, 92]], "#5b7f86", 1);
      });
      // the sandy sea floor, where the pals walk
      ground(g, 108, "#f2dca8", "#c9a468");
      patches(g, "#fae9ba", 116, 8);
      for (let i = 0; i < 14; i++) {
        const x = (i * 61 + 12) % W, y = 118 + (i * 37) % 58;
        line(g, [[x - 7, y], [x + 7, y - 1]], "#ddc084", .8);
      }
      // flat stones and shells
      [[46, 164, .8, "#8aa6a0", "#c3d4c8"], [118, 174, .6, "#8aa6a0", "#c3d4c8"],
       [196, 168, .7, "#7f9a96", "#b8cec4"], [268, 172, .9, "#8aa6a0", "#c3d4c8"]].forEach(([x, y, s, c, l]) => rock(g, x, y, s, c, l));
      ink(g, g => {
        [[132, 170], [226, 148], [312, 164]].forEach(([x, y], i) => {
          oval(g, x, y + .6, 5, 1.6, "#a98a5a33");
          oval(g, x, y, 4.2, 2.6, i % 2 ? "#ffd6e3" : "#fffdf6");
          line(g, [[x - 2.6, y + 1], [x, y - 1.8], [x + 2.6, y + 1]], "#e2b8a8", .6);
        });
        // a little starfish
        oval(g, 88, 176, 3.4, 1.6, "#a98a5a33");
        for (let a = 0; a < 5; a++) oval(g, 88 + Math.cos(a * 1.26 - 1.57) * 3, 175 + Math.sin(a * 1.26 - 1.57) * 3, 1.5, 1.5, "#ff9a6a");
        oval(g, 88, 175, 2, 2, "#ffb37a");
      });
      // coral fans, left and right
      ink(g, g => {
        coral(g, 26, 154, 1.15, "#e8709a", "#ff9fc0");
        coral(g, 44, 168, .8, "#ff9a5c", "#ffc28c");
        coral(g, 296, 150, 1.2, "#b06fd0", "#d9a8f0");
        coral(g, 278, 168, .75, "#e8709a", "#ff9fc0");
      });
      // big reef rocks
      ink(g, g => {
        rock(g, 92, 166, 1.1, "#7f9a96", "#b8cec4");
        rock(g, 246, 172, 1.2, "#728d8a", "#a9c2b8");
        rock(g, 206, 152, .7, "#7f9a96", "#b8cec4");
      });
      // the sunken treasure chest decoration (the code chest is separate)
      ink(g, g => {
        oval(g, 286, 139, 16, 3, "#3f2f7455");
        box(g, 274, 128, 24, 11, 2, "#a5703e");
        box(g, 274, 128, 24, 3, 1.4, "#c98a4e");
        box(g, 280, 126, 12, 3, 1, "#d9a45c");
        box(g, 284, 132, 4, 4, 1, "#ffd93b");
        oval(g, 286, 134, 1.2, 1.2, "#8a5a00");
        [[278, 136], [294, 136], [282, 139], [293, 139]].forEach(([x, y]) => oval(g, x, y, 2, 1.2, "#ffd93b"));
        line(g, [[274, 138], [298, 131]], "#4f8f5f", 1.4);
        oval(g, 278, 133, 2.4, 1.4, "#6fb583"); oval(g, 296, 136, 2.2, 1.2, "#6fb583");
      });
      // the bubble vents for the bubbles toy
      ink(g, g => {
        bubbleVent(g, 160, 136, 1);
        bubbleVent(g, 92, 154, .9);
        bubbleVent(g, 300, 151, .85);
      });
      // seats: a big clam and a rock ledge
      ink(g, g => {
        oval(g, 112, 152, 20, 3, "#a98a5a33");
        shape(g, [[96, 151], [112, 142], [128, 151]], "#d98aa8");
        shape(g, [[99, 150], [112, 145], [125, 150]], "#ffc3d6");
        for (let i = 0; i < 4; i++) line(g, [[104 + i * 5, 150], [112, 146]], "#e8a8be", .6);
        oval(g, 232, 161, 22, 3.4, "#a98a5a33");
        rock(g, 232, 155, 1.8, "#7f9a96", "#b8cec4");
        oval(g, 232, 158, 18, 3, "#5f8f88");
      });
      // soft light spots on the sand
      for (let i = 0; i < 9; i++) oval(g, (i * 71 + 26) % W, 121 + (i * 43) % 52, 7, 1.7, "#fff6c833");
    },
  };

  // Where a pal can sit in each place: [x, how deep on the ground from 0 to 1].
  const SEATS = {
    park: [[104, .05], [218, .05]],
    wedding: [[102, .08], [218, .08]],
    beach: [[119, .3], [232, .05]],
    night: [[128, .2], [194, .2]],
    snowy: [[104, .05], [220, .05]],
    candy: [[126, .05], [196, .05]],
    space: [[118, .55], [278, .75]],
    sea: [[112, .55], [232, .75]],
    village: [],
    home: [],
  };
  // Things to play with: [x, depth, how tall the clickable part is, what it does].
  const TOYS = {
    park: [[160, .05, 50, "splash"], [262, .2, 30, "bounce"], [34, .05, 70, "apples"]],
    wedding: [[160, .1, 80, "bells"], [44, .1, 40, "cake"], [268, .05, 60, "petals"]],
    beach: [[176, .25, 40, "sand"], [30, .05, 80, "coconut"], [72, .6, 26, "bounce"]],
    night: [[160, .05, 50, "sparks"], [216, .05, 50, "fireflies"], [262, .15, 34, "stars"]],
    snowy: [[160, .05, 60, "snow"], [28, .05, 60, "snow"], [268, .3, 30, "bounce"]],
    candy: [[160, .05, 40, "bounce"], [34, .05, 70, "candy"], [286, .05, 70, "candy"]],
    space: [[40, .05, 70, "rocket"], [204, .2, 30, "bounce"], [160, .9, 40, "stars"]],
    sea: [[160, .12, 34, "bubbles"], [92, .62, 36, "bubbles"], [300, .55, 34, "bubbles"]],
    village: [],
    home: [],
  };
  // The gems: [x, depth]. There are three in each place, the same as HANG_FINDS.
  const GEMS = {
    park: [[70, .75], [168, .95], [304, .5]], wedding: [[22, .6], [160, .9], [300, .8]], beach: [[130, .9], [230, .55], [20, .8]],
    night: [[50, .7], [150, .9], [300, .6]], snowy: [[60, .85], [190, .6], [305, .9]], candy: [[90, .7], [240, .9], [20, .5]],
    space: [[80, .8], [240, .5], [310, .9]], sea: [[70, .78], [196, .55], [304, .92]], village: [], home: [],
  };
  // ❄️ The same spots as TREE_X, SNOWMAN_X and SNOWMAN_DEEP in pixel.py.
  const VILLAGE_TREE_X = 92, SNOWMAN_X = 238, SNOWMAN_DEEP = .2, SNOWMAN_REACH = 46;
  // Where ornaments hang on the class tree, as many as TREE_MAX, filled in an order that spreads them out.
  const ORNAMENT_SLOTS = [[52, [-5, 5]], [64, [-10, 0, 10]], [76, [-15, -5, 5, 15]], [88, [-20, -10, 0, 10, 20]],
                          [100, [-20, -12, -4, 4, 12, 20]], [112, [-28, -20, -12, -4, 4, 12, 20, 28]]].flatMap(([y, xs]) => xs.map(dx => [dx, y]));
  const ORNAMENT_ORDER = ORNAMENT_SLOTS.map((_, i) => i * 11 % ORNAMENT_SLOTS.length);
  const PLACE_LABEL = {home: "Home", park: "Park", wedding: "Wedding", beach: "Beach", night: "Night", snowy: "Snowy hill", candy: "Candy land", space: "Outer space", sea: "Under the sea", village: "Snow Village"};
  const seatFeet = deep => PalStage.GROUND_TOP + deep * PalStage.GROUND_DEEP;
  const placeAt = (places, x) => { const i = Math.floor(x / W); return places[i] ? {scene: places[i], left: i * W} : null; };
  /** The seat at a spot in the world (the furniture counts as well as the ground in front of it). */
  function seatAt(places, x, y) {
    const at = placeAt(places, x);
    const hit = at && SEATS[at.scene].find(([sx, deep]) => Math.abs(x - at.left - sx) < 22 && y > seatFeet(deep) - 34 && y < seatFeet(deep) + 9);
    return hit ? {x: at.left + hit[0], y: hit[1]} : null;
  }
  /** The toy at a spot in the world. */
  function toyAt(places, x, y) {
    const at = placeAt(places, x);
    const hit = at && TOYS[at.scene].find(([tx, deep, tall]) => Math.abs(x - at.left - tx) < 24 && y > seatFeet(deep) - tall && y < seatFeet(deep) + 9);
    return hit ? {x: at.left + hit[0], y: hit[1], fx: hit[3]} : null;
  }
  /** The key of a gem this pal is standing on and hasn't got yet. */
  function gemAt(places, x, deep, found) {
    const at = placeAt(places, x);
    if (!at) return null;
    const i = GEMS[at.scene].findIndex(([gx, gd], n) => !found.has(at.scene + n) && Math.abs(x - at.left - gx) < 18 && Math.abs(deep - gd) < .16);
    return i < 0 ? null : at.scene + i;
  }
  /** ❄️ The index of one of today's 🎁 presents this pal is standing on and hasn't found. */
  function presentAt(places, x, deep, presents) {
    const at = placeAt(places, x);
    return at ? (presents || []).findIndex(p => p.place === at.scene && !p.found && Math.abs(x - at.left - p.x) < 16 && Math.abs(deep - p.deep) < .16) : -1;
  }
  /** "tree" or "snowman", for a click or a pal near one of them in the Snow Village. */
  function villageAt(places, x, y) {
    const at = placeAt(places, x);
    if (!at || at.scene !== "village") return null;
    const dx = x - at.left;
    if (Math.abs(dx - SNOWMAN_X) < 26 && y > 96 && y < seatFeet(SNOWMAN_DEEP) + 12) return {what: "snowman", x: at.left + SNOWMAN_X, y: SNOWMAN_DEEP};
    if (Math.abs(dx - VILLAGE_TREE_X) < 34 && y > 30 && y < seatFeet(.15) + 6) return {what: "tree", x: at.left + VILLAGE_TREE_X, y: .1};
    return null;
  }
  /** The 🧰 chest this pal is standing at and hasn't opened today. The chests come from the server. */
  function chestAt(places, x, deep, chests) {
    const at = placeAt(places, x);
    return (at && (chests || []).find(c => c.place === at.scene && !c.open && Math.abs(x - at.left - c.x) < 28 && Math.abs(deep - c.deep) < .2)) || null;     // 28: a pal stops beside it, not on it
  }
  // ---- Homes ---------------------------------------------------------------------------
  // A home is a row of rooms, one screen each, with open doorways between them. Each room
  // has a wall, a floor, what its kind has built in, and whatever its owner has put in it.
  // Everything is painted behind the pals.
  const WALLS = {w_cream: ["#fdf1d8", "#f5e3bf"], w_pink: ["#ffdce8", "#f9c6d8"], w_blue: ["#d3e9f8", "#b9d8f0"], w_night: ["#2f3a72", "#252f62"],
                 w_mint: ["#d8f3e6", "#c4ead8"], w_sky: ["#a9dcf2", "#a9dcf2"], w_sea: ["#7fc8e8", "#6cbbe0"], w_candy: ["#fff4f8", "#ffb3cc"],
                 w_attic: ["#c99a6b", "#bb8c5e"], w_castle: ["#b9b4c8", "#a7a1b9"], w_green: ["#d4ecc9", "#c3e2b6"], w_dots: ["#fff0f6", "#ffc9dc"],
                 w_hearts: ["#ffe3ec", "#ff8fb3"], w_bubble: ["#dff2fa", "#bfe3f3"], w_splat: ["#fffdf6", "#f1ecdf"], w_music: ["#efe6ff", "#e2d4fb"],
                 w_paws: ["#fff2dc", "#e9cfa6"], w_leaf: ["#9fd189", "#7fbd6a"], w_space: ["#151b45", "#0f1436"], w_sweets: ["#ffeef6", "#ffd6e6"],
                 w_star: ["#5b3fa0", "#4e3590"]};
  const FLOORS = {f_wood: "#d9a86c", f_check: "#fffdf6", f_grass: "#a4d48d", f_cloud: "#dcecf8", f_carpet: "#b9a4e8", f_tile: "#bfe6f2",
                  f_sand: "#f1dca5", f_rainbow: "#ff9fb5", f_gold: "#f5cf5a", f_red: "#d84a55", f_ice: "#d6f0fb", f_stage: "#9a6a42",
                  f_moon: "#cfcfdc", f_candy: "#ffc9dc", f_diamond: "#c7ecf7"};
  const paw = (g, x, y, c) => { oval(g, x, y, 3, 2.5, c); [[-3.2, -3.6], [-1.1, -5.2], [1.3, -5.2], [3.4, -3.6]].forEach(([dx, dy]) => oval(g, x + dx, y + dy, 1.1, 1.4, c)); };
  const note = (g, x, y, c) => { oval(g, x, y, 3, 2.2, c); line(g, [[x + 2.6, y], [x + 2.6, y - 11], [x + 7, y - 8]], c, 1.4); };
  const lolly = (g, x, y, r, c) => { line(g, [[x, y], [x, y + r * 2.6]], "#fffdf6", 1.6); oval(g, x, y, r, r, c); oval(g, x, y, r * .62, r * .62, "#ffffff88"); oval(g, x, y, r * .3, r * .3, c); };
  const FLOOR_TOP = 112, FISH_X = 140;
  const FURNITURE_ART = {
    rug(g, x, y) { oval(g, x, y, 30, 9, "#ff9fb5"); oval(g, x, y, 24, 6.6, "#ffd9e3"); oval(g, x, y, 14, 3.6, "#ff9fb5"); },
    plant(g, x, y) {
      oval(g, x, y, 8, 2, "#2c535226");
      [[-6, -20, -.5], [6, -21, .5], [0, -27, 0], [-3, -17, -.2], [4, -16, .3]].forEach(([dx, dy], i) => oval(g, x + dx, y + dy, 5, 7, i % 2 ? "#569f70" : "#3f8f63"));
      shape(g, [[x - 7, y - 11], [x + 7, y - 11], [x + 5, y], [x - 5, y]], "#d98a5c");
      box(g, x - 8, y - 13, 16, 3, 1, "#e8a070");
    },
    balloons(g, x, y) {
      [[-9, -52, "#ff8fa8"], [9, -55, "#7ab8ff"], [0, -64, "#ffd27a"]].forEach(([dx, dy, c]) => {
        line(g, [[x, y], [x + dx, y + dy + 8]], "#8a8a9a", .6);
        oval(g, x + dx, y + dy, 6.5, 8, c);
        oval(g, x + dx - 2, y + dy - 3, 1.6, 2.4, "#ffffffaa");
      });
      box(g, x - 3, y - 4, 6, 4, 1, "#b9a4e8");
    },
    lamp(g, x, y) {
      glow(g, x, y - 38, 24, "#ffe7a088");
      oval(g, x, y, 7, 2, "#8a6a4a");
      line(g, [[x, y], [x, y - 34]], "#8a6a4a", 1.8);
      shape(g, [[x - 10, y - 32], [x - 6, y - 46], [x + 6, y - 46], [x + 10, y - 32]], "#ffe39a");
    },
    teddy(g, x, y) {
      oval(g, x - 5, y - 21, 2.6, 2.6, "#b57d44"); oval(g, x + 5, y - 21, 2.6, 2.6, "#b57d44");
      oval(g, x, y - 7, 7.5, 7.5, "#c98f52"); oval(g, x, y - 17, 6.5, 6, "#c98f52");
      oval(g, x, y - 6, 4, 4.4, "#f0d2a8"); oval(g, x, y - 15.5, 2.8, 2.2, "#f0d2a8");
      oval(g, x - 2.4, y - 18.4, .9, .9, "#27324f"); oval(g, x + 2.4, y - 18.4, .9, .9, "#27324f");
      oval(g, x - 7, y - 1.5, 3, 2, "#b57d44"); oval(g, x + 7, y - 1.5, 3, 2, "#b57d44");
    },
    table(g, x, y) {
      oval(g, x, y, 17, 2.6, "#2c535222");
      [-13, 13].forEach(dx => line(g, [[x + dx, y], [x + dx, y - 14]], "#a87440", 2.2));
      box(g, x - 17, y - 18, 34, 5, 1.5, "#d99a5c");
      box(g, x - 4, y - 23, 8, 5, 1, "#8fd0c8"); oval(g, x, y - 26, 3, 3, "#ff8fa8");
    },
    beanbag(g, x, y) { oval(g, x, y - 1, 15, 3, "#2c535222"); oval(g, x, y - 8, 15, 9, "#8fd0c8"); oval(g, x - 2, y - 12, 9.5, 5, "#aee3da"); },
    toybox(g, x, y) {
      oval(g, x - 5, y - 19, 5.5, 5.5, "#ff8fa8"); shape(g, [[x + 3, y - 16], [x + 9, y - 27], [x + 13, y - 16]], "#ffd27a");
      box(g, x - 15, y - 15, 30, 15, 2, "#7ab8ff"); box(g, x - 16, y - 18, 32, 5, 2, "#5a9be8");
      shape(g, [[x, y - 11], [x + 1.6, y - 7.6], [x + 5, y - 7.6], [x + 2.4, y - 5.4], [x + 3.4, y - 2], [x, y - 4], [x - 3.4, y - 2], [x - 2.4, y - 5.4], [x - 5, y - 7.6], [x - 1.6, y - 7.6]], "#ffe39a");
    },
    shelf(g, x, y) {
      box(g, x - 15, y - 48, 30, 48, 2, "#a9744a");
      [0, 1, 2].forEach(row => {
        box(g, x - 12, y - 45 + row * 15, 24, 12, 1, "#f5e3bf");
        ["#ff8fa8", "#7ab8ff", "#ffd27a", "#8fd0c8", "#b9a4e8"].forEach((c, i) => box(g, x - 11 + i * 4.4, y - 43 + row * 15 + (i + row) % 2 * 2, 3.6, 10 - (i + row) % 2 * 2, 0, c));
      });
    },
    bed(g, x, y) {
      oval(g, x, y, 27, 3, "#2c535222");
      box(g, x - 27, y - 29, 6, 29, 2, "#8a5f3c"); box(g, x - 24, y - 12, 49, 12, 2, "#a9744a");
      box(g, x - 23, y - 19, 47, 9, 3, "#fffdf6"); box(g, x - 21, y - 22, 13, 6, 3, "#ffd9e3");
      box(g, x - 6, y - 20, 30, 11, 3, "#b9a4e8"); box(g, x - 6, y - 20, 30, 3, 1.5, "#d6c8f4");
    },
    sofa(g, x, y) {
      oval(g, x, y, 27, 3, "#2c535222");
      box(g, x - 22, y - 26, 44, 16, 5, "#ff8fa8"); box(g, x - 24, y - 14, 48, 11, 4, "#ffa9bc");
      box(g, x - 27, y - 19, 8, 17, 3, "#f0718f"); box(g, x + 19, y - 19, 8, 17, 3, "#f0718f");
      box(g, x - 9, y - 21, 9, 8, 2, "#fff2c0");
    },
    tv(g, x, y) {
      box(g, x - 13, y - 10, 26, 10, 1, "#6d5560");
      box(g, x - 19, y - 33, 38, 23, 2, "#27324f"); box(g, x - 17, y - 31, 34, 19, 1, "#7fc8dc");
      oval(g, x + 9, y - 25, 3.4, 3.4, "#fff0b0"); shape(g, [[x - 17, y - 12], [x - 6, y - 23], [x + 3, y - 15], [x + 9, y - 19], [x + 17, y - 12]], "#62b083");
    },
    tank(g, x, y) {
      box(g, x - 15, y - 11, 30, 11, 1, "#8a6a4a");
      box(g, x - 17, y - 33, 34, 22, 2, "#d6f4f8"); box(g, x - 15, y - 29, 30, 16, 1, "#8ed6e0");
      line(g, [[x - 10, y - 13], [x - 11, y - 22]], "#3f8f63", 1.2); line(g, [[x + 11, y - 13], [x + 10, y - 20]], "#569f70", 1.2);
      [[-3, -22, "#ffa95c"], [6, -18, "#ff8fa8"]].forEach(([dx, dy, c]) => { oval(g, x + dx, y + dy, 3.2, 2, c); shape(g, [[x + dx + 2.5, y + dy], [x + dx + 6, y + dy - 2.4], [x + dx + 6, y + dy + 2.4]], c); });
    },
    disco(g, x, y) {
      line(g, [[x, y - 96], [x, y - 92]], "#8a8a9a", 1);
      oval(g, x, y - 84, 8.5, 8.5, "#c9c9e8");
      for (let i = 0; i < 9; i++) box(g, x - 7 + i % 3 * 5, y - 90 + Math.floor(i / 3) * 4.6, 3, 3, 0, ["#ffffff", "#ff9fb5", "#8fd0c8", "#ffd27a"][i % 4]);
    },
    cupcakes(g, x, y) {
      box(g, x - 12, y - 4, 24, 4, 1, "#fffdf6"); line(g, [[x, y - 4], [x, y]], "#c9c9e8", 1.4);
      [[-7, "#ff8fa8"], [0, "#8fd0c8"], [7, "#ffd27a"]].forEach(([dx, c], i) => {
        shape(g, [[x + dx - 4, y - 12 - i % 2 * 2], [x + dx + 4, y - 12 - i % 2 * 2], [x + dx + 3, y - 5], [x + dx - 3, y - 5]], "#e8a070");
        oval(g, x + dx, y - 14 - i % 2 * 2, 4.6, 3.4, c); oval(g, x + dx, y - 18 - i % 2 * 2, 1.4, 1.4, "#e8553f");
      });
    },
    flowers(g, x, y) {
      box(g, x - 18, y - 7, 36, 7, 2, "#a9744a"); box(g, x - 17, y - 9, 34, 4, 2, "#7a5434");
      [-13, -6, 1, 8, 14].forEach((dx, i) => {
        line(g, [[x + dx, y - 8], [x + dx, y - 18 - i % 2 * 4]], "#3f8f63", 1.2);
        oval(g, x + dx, y - 19 - i % 2 * 4, 3.2, 3.2, ["#ff8fa8", "#ffd27a", "#b9a4e8", "#ff9fb5", "#7ab8ff"][i]); oval(g, x + dx, y - 19 - i % 2 * 4, 1.2, 1.2, "#fff2c0");
      });
    },
    duck(g, x, y) {
      oval(g, x, y - 1, 9, 2, "#2c535222"); oval(g, x, y - 6, 8, 5.5, "#ffd93b"); oval(g, x + 4, y - 13, 4.6, 4.4, "#ffd93b");
      shape(g, [[x + 8, y - 13], [x + 13, y - 12], [x + 8, y - 11]], "#ffa95c"); oval(g, x + 5, y - 14.5, .9, .9, "#27324f"); oval(g, x - 3, y - 7, 3.4, 2.2, "#ffe77a");
    },
    tree(g, x, y) {
      shape(g, [[x - 9, y - 9], [x + 9, y - 9], [x + 7, y], [x - 7, y]], "#d98a5c"); box(g, x - 10, y - 11, 20, 3, 1, "#e8a070");
      line(g, [[x, y - 10], [x, y - 26]], "#8a5f3c", 3);
      [[0, -38, 12], [-9, -30, 9], [9, -30, 9]].forEach(([dx, dy, r], i) => oval(g, x + dx, y + dy, r, r * .9, i ? "#569f70" : "#62b083"));
      [[-6, -34], [5, -40], [8, -28], [-3, -27]].forEach(([dx, dy]) => oval(g, x + dx, y + dy, 1.8, 1.8, "#e8553f"));
    },
    fridge(g, x, y) {
      box(g, x - 13, y - 50, 26, 50, 3, "#f5f2ff"); line(g, [[x - 13, y - 32], [x + 13, y - 32]], "#c9c9e8", 1.2);
      box(g, x + 7, y - 46, 2.4, 10, 1, "#a9a9c8"); box(g, x + 7, y - 28, 2.4, 14, 1, "#a9a9c8");
      oval(g, x - 6, y - 42, 2.4, 2.4, "#ff8fa8"); box(g, x - 9, y - 24, 7, 8, 1, "#ffe39a");
    },
    stove(g, x, y) {
      box(g, x - 15, y - 26, 30, 26, 2, "#fffdf6"); box(g, x - 11, y - 18, 22, 13, 2, "#27324f"); box(g, x - 9, y - 16, 18, 9, 1, "#ffa95c55");
      box(g, x - 15, y - 28, 30, 3, 1, "#c9c9e8"); [-8, 8].forEach(dx => oval(g, x + dx, y - 22, 3.4, 1.2, "#8a8a9a"));
      box(g, x + 1, y - 37, 13, 8, 2, "#ff8fa8"); line(g, [[x + 14, y - 34], [x + 19, y - 35]], "#27324f", 1.4);
    },
    wardrobe(g, x, y) {
      box(g, x - 17, y - 54, 34, 54, 2, "#b57d44"); box(g, x - 15, y - 51, 14, 45, 1, "#c98f52"); box(g, x + 1, y - 51, 14, 45, 1, "#c98f52");
      oval(g, x - 3, y - 28, 1.4, 1.4, "#ffd93b"); oval(g, x + 3, y - 28, 1.4, 1.4, "#ffd93b");
      box(g, x - 17, y - 57, 34, 4, 1, "#8a5f3c"); shape(g, [[x - 9, y - 61], [x - 2, y - 57], [x - 16, y - 57]], "#ff8fa8");
    },
    swing(g, x, y) {
      [-16, 16].forEach(dx => line(g, [[x + dx, y], [x + dx * .8, y - 52]], "#a9744a", 2.6));
      line(g, [[x - 14, y - 52], [x + 14, y - 52]], "#8a5f3c", 3);
      [-7, 7].forEach(dx => line(g, [[x + dx, y - 51], [x + dx, y - 14]], "#8a8a9a", .9));
      box(g, x - 10, y - 15, 20, 3.6, 1, "#ff8fa8");
    },
    chest(g, x, y) {
      oval(g, x, y, 16, 2.4, "#2c535222");
      box(g, x - 15, y - 16, 30, 16, 2, "#a9744a"); box(g, x - 16, y - 24, 32, 9, 4, "#8a5f3c");
      [-9, 9].forEach(dx => box(g, x + dx - 1.5, y - 24, 3, 24, 0, "#ffd27a")); box(g, x - 3, y - 15, 6, 6, 1, "#ffd93b");
      [[-6, -26], [0, -27], [6, -26], [-3, -28]].forEach(([dx, dy]) => oval(g, x + dx, y + dy, 2.4, 1.6, "#ffe14a"));
    },
    drums(g, x, y) {
      oval(g, x, y - 2, 18, 3, "#2c535222");
      oval(g, x, y - 12, 11, 11, "#ff5f7a"); oval(g, x, y - 12, 8, 8, "#fffdf6");
      [[-15, -20], [15, -22]].forEach(([dx, dy]) => { line(g, [[x + dx, y], [x + dx, y + dy + 2]], "#8a8a9a", 1); box(g, x + dx - 6, y + dy, 12, 6, 2, "#7ab8ff"); oval(g, x + dx, y + dy, 6, 1.6, "#fffdf6"); });
      line(g, [[x + 21, y], [x + 21, y - 34]], "#8a8a9a", 1); oval(g, x + 21, y - 34, 8, 1.8, "#ffd93b");
    },
    telescope(g, x, y) {
      [-8, 0, 8].forEach(dx => line(g, [[x, y - 18], [x + dx, y]], "#8a5f3c", 1.6));
      g.save(); g.translate(x, y - 20); g.rotate(-.5);
      box(g, -12, -4, 26, 8, 3, "#7ab8ff"); box(g, 12, -5, 5, 10, 2, "#5a9be8"); box(g, -15, -3, 4, 6, 1, "#27324f");
      g.restore();
    },
    trampoline(g, x, y) {
      [-17, -6, 6, 17].forEach(dx => line(g, [[x + dx, y], [x + dx, y - 8]], "#8a8a9a", 1.4));
      oval(g, x, y - 9, 21, 4.6, "#5a9be8"); oval(g, x, y - 9, 17, 3.4, "#27324f");
    },
    bunkbed(g, x, y) {
      [-27, 25].forEach(dx => box(g, x + dx, y - 56, 4, 56, 1, "#8a5f3c"));
      [[-2, "#ff8fa8"], [-30, "#7ab8ff"]].forEach(([dy, c]) => {
        box(g, x - 24, y + dy - 10, 49, 8, 2, "#a9744a"); box(g, x - 23, y + dy - 16, 47, 7, 3, "#fffdf6");
        box(g, x - 21, y + dy - 18, 12, 5, 2, "#ffd9e3"); box(g, x - 6, y + dy - 17, 30, 9, 3, c);
      });
      [-44, -38].forEach(dy => line(g, [[x + 18, y + dy], [x + 25, y + dy]], "#8a5f3c", 1.2));
    },
    piano(g, x, y) {
      oval(g, x, y, 22, 2.6, "#2c535222");
      box(g, x - 22, y - 36, 44, 34, 2, "#27324f"); box(g, x - 20, y - 22, 40, 6, 1, "#fffdf6");
      for (let i = 0; i < 9; i++) box(g, x - 17 + i * 4.4, y - 22, 2, 3.6, 0, i % 3 === 2 ? "#fffdf6" : "#1b1530");
      [-17, 17].forEach(dx => box(g, x + dx - 2, y - 4, 4, 4, 0, "#1b1530"));
      oval(g, x - 8, y - 30, 2, 2.4, "#ffd27a"); line(g, [[x - 6.5, y - 30], [x - 6.5, y - 35]], "#ffd27a", 1);
    },
    fountain(g, x, y) {
      oval(g, x, y - 5, 22, 6, "#c9c9e8"); oval(g, x, y - 6, 18, 4, "#8ed6e0");
      box(g, x - 3, y - 24, 6, 18, 1, "#c9c9e8"); oval(g, x, y - 24, 9, 3, "#c9c9e8"); oval(g, x, y - 25, 7, 2, "#8ed6e0");
      line(g, [[x, y - 26], [x - 3, y - 36], [x - 9, y - 30]], "#bfeaf2", 1.4); line(g, [[x, y - 26], [x + 3, y - 36], [x + 9, y - 30]], "#bfeaf2", 1.4);
    },
    arcade(g, x, y) {
      box(g, x - 13, y - 52, 26, 52, 2, "#b9a4e8"); box(g, x - 13, y - 52, 26, 8, 2, "#ff5f7a");
      box(g, x - 10, y - 42, 20, 16, 1, "#27324f"); oval(g, x - 3, y - 35, 2, 2, "#ffd93b"); box(g, x + 2, y - 38, 4, 4, 0, "#8fd0c8");
      box(g, x - 13, y - 24, 26, 6, 1, "#9d86d8"); line(g, [[x - 5, y - 22], [x - 5, y - 27]], "#27324f", 1); oval(g, x - 5, y - 28, 1.8, 1.8, "#ff5f7a");
      oval(g, x + 4, y - 22, 1.6, 1.6, "#7ab8ff"); oval(g, x + 8, y - 22, 1.6, 1.6, "#ffd93b");
    },
    robot(g, x, y) {
      oval(g, x, y, 11, 2.2, "#2c535222");
      [-5, 5].forEach(dx => box(g, x + dx - 2.4, y - 9, 5, 9, 1, "#8a8a9a"));
      box(g, x - 10, y - 26, 20, 18, 3, "#c9c9e8"); box(g, x - 5, y - 21, 10, 7, 1, "#7fc8dc");
      box(g, x - 8, y - 40, 16, 13, 3, "#d6d6ee"); oval(g, x - 3.6, y - 34, 2, 2, "#27324f"); oval(g, x + 3.6, y - 34, 2, 2, "#27324f");
      line(g, [[x, y - 40], [x, y - 45]], "#8a8a9a", 1); oval(g, x, y - 46, 2, 2, "#ff5f7a");
      [-13, 13].forEach(dx => line(g, [[x + dx * .8, y - 22], [x + dx, y - 14]], "#8a8a9a", 2));
    },
    trophy(g, x, y) {
      box(g, x - 9, y - 6, 18, 6, 1, "#8a5f3c"); box(g, x - 3, y - 14, 6, 9, 1, "#f5b83d");
      shape(g, [[x - 11, y - 34], [x + 11, y - 34], [x + 7, y - 18], [x - 7, y - 18]], "#ffd93b");
      line(g, [[x - 11, y - 31], [x - 15, y - 26], [x - 8, y - 22]], "#f5b83d", 1.6); line(g, [[x + 11, y - 31], [x + 15, y - 26], [x + 8, y - 22]], "#f5b83d", 1.6);
      oval(g, x - 4, y - 28, 1.6, 3, "#fff6c8");
    },
    rainbowarch(g, x, y) {
      ["#ff5f7a", "#ffa95c", "#ffd93b", "#62b083", "#7ab8ff", "#b9a4e8"].forEach((c, i) => {
        g.strokeStyle = c; g.lineWidth = 3; g.beginPath(); g.arc(x, y - 4, 30 - i * 3, Math.PI, 0); g.stroke();
      });
      cloud(g, x - 28, y - 4, .5); cloud(g, x + 28, y - 4, .5);
    },
    throne(g, x, y) {
      oval(g, x, y, 15, 2.4, "#2c535222");
      box(g, x - 13, y - 46, 26, 34, 4, "#ffd93b"); box(g, x - 9, y - 42, 18, 28, 3, "#e8553f");
      [-10, 0, 10].forEach(dx => shape(g, [[x + dx - 4, y - 46], [x + dx, y - 54], [x + dx + 4, y - 46]], "#ffd93b"));
      box(g, x - 15, y - 16, 30, 8, 2, "#e8553f"); box(g, x - 15, y - 9, 4, 9, 1, "#f5b83d"); box(g, x + 11, y - 9, 4, 9, 1, "#f5b83d");
      oval(g, x, y - 30, 2.4, 2.4, "#7ab8ff");
    },
    unicornpal(g, x, y) {
      oval(g, x, y, 17, 2.4, "#2c535222");
      [-10, -4, 5, 11].forEach(dx => box(g, x + dx - 1.6, y - 13, 3.2, 13, 1, "#fffdf6"));
      oval(g, x, y - 17, 15, 8, "#fffdf6"); oval(g, x + 14, y - 28, 6, 8, "#fffdf6"); oval(g, x + 18, y - 25, 4, 3, "#fffdf6");
      shape(g, [[x + 13, y - 35], [x + 17, y - 35], [x + 16, y - 46]], "#ffd93b");
      [["#ff8fa8", -2], ["#b9a4e8", 1], ["#7ab8ff", 4]].forEach(([c, d]) => oval(g, x + 9 - d, y - 30 + d * 1.6, 2.6, 4.2, c));
      [["#ff8fa8", 0], ["#b9a4e8", 3], ["#7ab8ff", 6]].forEach(([c, d]) => line(g, [[x - 14, y - 20], [x - 19 - d * .3, y - 10 + d]], c, 2));
      oval(g, x + 16, y - 29, .9, .9, "#27324f");
    },
    slide(g, x, y) {
      [-20, -12].forEach(dx => line(g, [[x + dx, y], [x + dx, y - 42]], "#7ab8ff", 2));
      for (let i = 1; i < 5; i++) line(g, [[x - 20, y - i * 9], [x - 12, y - i * 9]], "#7ab8ff", 1.4);
      box(g, x - 22, y - 45, 14, 4, 1, "#5a9be8");
      shape(g, [[x - 10, y - 45], [x - 3, y - 45], [x + 22, y - 5], [x + 24, y], [x + 14, y]], "#ffd27a");
      line(g, [[x - 8, y - 44], [x + 18, y - 3]], "#ffa95c", 1.4);
    },
    rocketbed(g, x, y) {
      oval(g, x, y, 28, 3, "#2c535222");
      shape(g, [[x - 24, y - 12], [x - 36, y - 9], [x - 24, y - 6]], "#ffa95c"); shape(g, [[x - 24, y - 11], [x - 31, y - 9], [x - 24, y - 7]], "#ffe39a");
      box(g, x - 24, y - 18, 46, 16, 7, "#e8e8f6");
      shape(g, [[x + 20, y - 18], [x + 34, y - 10], [x + 20, y - 2]], "#ff5f7a");
      shape(g, [[x - 22, y - 18], [x - 28, y - 25], [x - 14, y - 18]], "#ff5f7a"); shape(g, [[x - 22, y - 2], [x - 28, y + 1], [x - 14, y - 2]], "#ff5f7a");
      oval(g, x + 12, y - 10, 3.6, 3.6, "#7fc8dc");
      box(g, x - 20, y - 23, 26, 7, 3, "#b9a4e8"); box(g, x - 22, y - 22, 9, 5, 2, "#fffdf6");
    },
    dragonegg(g, x, y) {
      glow(g, x, y - 16, 22, "#c5a3ff55");
      oval(g, x, y - 2, 15, 3.4, "#a9744a");
      oval(g, x, y - 16, 10, 14, "#62b083");
      [[-4, -20], [3, -12], [-2, -8], [5, -22], [-5, -12]].forEach(([dx, dy]) => oval(g, x + dx, y + dy, 2.2, 1.6, "#3f8f63"));
      line(g, [[x - 3, y - 27], [x, y - 24], [x - 2, y - 21], [x + 1, y - 18]], "#fff6c8", 1);
      line(g, [[x - 15, y - 3], [x + 14, y]], "#8a5f3c", 1.6); line(g, [[x - 13, y], [x + 15, y - 4]], "#7a5434", 1.4);
    },
    globe(g, x, y) {
      oval(g, x, y - 1, 9, 2, "#2c535222"); box(g, x - 7, y - 4, 14, 4, 1, "#a9744a"); line(g, [[x, y - 4], [x, y - 10]], "#a9744a", 2);
      oval(g, x, y - 22, 12, 12, "#5aa8e8"); shape(g, [[x - 8, y - 28], [x - 1, y - 31], [x + 1, y - 24], [x - 5, y - 18]], "#62b083");
      shape(g, [[x + 3, y - 20], [x + 9, y - 25], [x + 10, y - 15], [x + 5, y - 13]], "#62b083"); oval(g, x - 4, y - 28, 2.4, 1.4, "#ffffff99");
      g.strokeStyle = "#ffd27a"; g.lineWidth = 1.4; g.beginPath(); g.arc(x, y - 22, 14.5, Math.PI * .6, Math.PI * 1.6); g.stroke();
    },
    snowglobe(g, x, y) {
      box(g, x - 11, y - 7, 22, 7, 2, "#a9744a"); box(g, x - 9, y - 9, 18, 3, 1, "#8a5f3c");
      oval(g, x, y - 20, 11, 11, "#d6ecfa"); oval(g, x, y - 14, 4.4, 4, "#ffffff"); oval(g, x, y - 20, 3.2, 3, "#ffffff"); oval(g, x + 2, y - 20.4, .8, .8, "#ffa95c");
      [[-6, -26], [5, -27], [-3, -30], [7, -21], [-7, -18]].forEach(([dx, dy]) => oval(g, x + dx, y + dy, .9, .9, "#ffffff"));
      oval(g, x - 5, y - 25, 2.6, 1.6, "#ffffffaa");
    },
    partycake(g, x, y) {
      oval(g, x, y, 16, 2.4, "#2c535222"); box(g, x - 15, y - 4, 30, 4, 1, "#c9c9e8");
      box(g, x - 13, y - 15, 26, 11, 2, "#ff8fa8"); box(g, x - 9, y - 24, 18, 9, 2, "#fffdf6"); box(g, x - 5, y - 31, 10, 7, 2, "#8fd0c8");
      [-9, -3, 3, 9].forEach(dx => oval(g, x + dx, y - 15, 2.4, 1.8, "#fffdf6"));
      [-3, 0, 3].forEach(dx => { box(g, x + dx - .6, y - 37, 1.2, 6, 0, "#ffd27a"); oval(g, x + dx, y - 38, 1.2, 1.8, "#ffa95c"); });
    },
    gumball(g, x, y) {
      box(g, x - 9, y - 14, 18, 14, 2, "#e8553f"); box(g, x - 3, y - 10, 6, 5, 1, "#c9c9e8");
      oval(g, x, y - 26, 12, 12, "#e6f6fbcc");
      [[-5, -30, "#ff8fa8"], [4, -32, "#ffd27a"], [0, -25, "#7ab8ff"], [-6, -22, "#62b083"], [6, -23, "#b9a4e8"], [1, -35, "#ff5f7a"], [-2, -19, "#ffa95c"]].forEach(([dx, dy, c]) => oval(g, x + dx, y + dy, 2.6, 2.6, c));
      oval(g, x - 5, y - 32, 2.4, 1.6, "#ffffffbb"); box(g, x - 3, y - 41, 6, 4, 1, "#e8553f");
    },
    mirror(g, x, y) {
      oval(g, x, y, 11, 2, "#2c535222"); [-7, 7].forEach(dx => line(g, [[x + dx, y], [x + dx * .6, y - 12]], "#d9a93a", 2));
      oval(g, x, y - 34, 12, 20, "#ffd93b"); oval(g, x, y - 34, 9.5, 17.5, "#bfe6f2");
      line(g, [[x - 5, y - 44], [x - 1, y - 49]], "#ffffff", 1.6); line(g, [[x - 5, y - 38], [x + 1, y - 46]], "#ffffffaa", 1.2);
      twinkle(g, x + 10, y - 50, 3, "#fff6c8"); oval(g, x, y - 55, 3, 3, "#ff8fc7");
    },
    easel(g, x, y) {
      line(g, [[x - 12, y], [x - 2, y - 46]], "#a9744a", 2); line(g, [[x + 12, y], [x + 2, y - 46]], "#a9744a", 2); line(g, [[x, y - 40], [x + 3, y]], "#8a5f3c", 1.6);
      box(g, x - 16, y - 46, 32, 28, 1, "#fffdf6"); box(g, x - 16, y - 19, 32, 3, 1, "#8a5f3c");
      oval(g, x + 7, y - 39, 4, 4, "#ffd93b"); shape(g, [[x - 14, y - 22], [x - 6, y - 34], [x + 1, y - 26], [x + 6, y - 31], [x + 14, y - 22]], "#62b083");
      heart(g, x - 7, y - 40, .75, "#ff5f7a");
      [[-14, "#ff5f7a"], [-9, "#7ab8ff"], [-4, "#ffd93b"]].forEach(([dx, c]) => box(g, x + dx + 20, y - 5, 4, 5, 1, c));
    },
    bathtub(g, x, y) {
      oval(g, x, y, 26, 2.6, "#2c535222"); [-18, 18].forEach(dx => box(g, x + dx - 2, y - 5, 4, 5, 1, "#ffd27a"));
      box(g, x - 25, y - 20, 50, 16, 7, "#fffdf6"); box(g, x - 23, y - 21, 46, 4, 2, "#8ed6e0");
      [[-16, -23, 5], [-8, -26, 6], [1, -24, 5], [9, -27, 6], [17, -23, 4.4], [-3, -30, 4], [5, -32, 3.4]].forEach(([dx, dy, r]) => { oval(g, x + dx, y + dy, r, r * .9, "#ffffff"); oval(g, x + dx - r * .3, y + dy - r * .3, r * .3, r * .25, "#d6f4f8"); });
      line(g, [[x + 22, y - 18], [x + 22, y - 32], [x + 16, y - 32]], "#c9c9e8", 2); oval(g, x + 4, y - 37, 3.4, 2.6, "#ffd93b"); oval(g, x + 7, y - 40, 2.2, 2.2, "#ffd93b");
    },
    saturn(g, x, y) {
      glow(g, x, y - 36, 24, "#ffd27a77");
      oval(g, x, y, 8, 2, "#8a6a4a"); line(g, [[x, y], [x, y - 26]], "#8a6a4a", 1.8);
      oval(g, x, y - 36, 10, 10, "#ffb35c"); line(g, [[x - 8, y - 39], [x + 8, y - 39]], "#ffd27a", 1.6); line(g, [[x - 9, y - 33], [x + 9, y - 33]], "#e8903a", 1.4);
      g.strokeStyle = "#c5a3ff"; g.lineWidth = 2.2; g.beginPath(); g.ellipse(x, y - 36, 18, 4.4, -.25, 0, Math.PI * 2); g.stroke();
      oval(g, x, y - 36, 10, 4, "#ffb35c"); line(g, [[x - 9, y - 35], [x + 9, y - 37]], "#ffd27a", 1.2);
    },
    guitar(g, x, y) {
      [-6, 6].forEach(dx => line(g, [[x, y - 14], [x + dx, y]], "#8a8a9a", 1.2));
      g.save(); g.translate(x, y - 22); g.rotate(-.18);
      box(g, -2, -40, 4, 28, 1, "#8a5f3c"); box(g, -3.4, -46, 6.8, 7, 2, "#6d4a2c");
      [-44, -42, -40].forEach(dy => { oval(g, -4.6, dy, 1, 1, "#ffd27a"); oval(g, 4.6, dy, 1, 1, "#ffd27a"); });
      oval(g, 0, 8, 12, 11, "#ff5f7a"); oval(g, 0, -6, 9, 8.4, "#ff5f7a"); oval(g, 0, 0, 3.6, 3.6, "#27324f");
      box(g, -5, 9, 10, 2.4, 1, "#27324f"); line(g, [[0, -38], [0, 10]], "#fff6c8", .6);
      g.restore();
    },
    hammock(g, x, y) {
      [-26, 26].forEach(dx => { box(g, x + dx - 2, y - 48, 4, 48, 1, "#8a5f3c"); oval(g, x + dx, y - 50, 7, 7, "#62b083"); oval(g, x + dx - 3, y - 54, 5, 5, "#569f70"); });
      shape(g, [[x - 24, y - 38], [x - 10, y - 18], [x, y - 15], [x + 10, y - 18], [x + 24, y - 38], [x + 12, y - 25], [x, y - 22], [x - 12, y - 25]], "#ffa95c");
      [-14, -4, 6, 16].forEach(dx => line(g, [[x + dx, y - 22 - Math.abs(dx) * .5], [x + dx, y - 17 - Math.abs(dx) * .5]], "#ffe39a", 1.4));
      oval(g, x - 8, y - 25, 4.4, 2.6, "#fffdf6");
    },
    bunny(g, x, y) {
      oval(g, x, y, 10, 2, "#2c535222");
      oval(g, x - 3, y - 26, 2.6, 8, "#fffdf6"); oval(g, x + 3, y - 27, 2.6, 8, "#fffdf6"); oval(g, x - 3, y - 26, 1.2, 5.4, "#ffc9e3"); oval(g, x + 3, y - 27, 1.2, 5.4, "#ffc9e3");
      oval(g, x, y - 7, 9, 7.5, "#fffdf6"); oval(g, x, y - 16, 6.4, 5.6, "#fffdf6"); oval(g, x - 9, y - 5, 3, 3, "#ffffff");
      oval(g, x - 2.4, y - 17, .9, .9, "#27324f"); oval(g, x + 2.4, y - 17, .9, .9, "#27324f"); oval(g, x, y - 14.6, 1.1, .8, "#ff8fa8");
      oval(g, x - 4, y - 1.4, 2.6, 1.6, "#ffe3ec"); oval(g, x + 4, y - 1.4, 2.6, 1.6, "#ffe3ec");
    },
    icecream(g, x, y) {
      oval(g, x, y, 24, 2.6, "#2c535222"); [-14, 14].forEach(dx => { oval(g, x + dx, y - 4, 4.4, 4.4, "#27324f"); oval(g, x + dx, y - 4, 1.6, 1.6, "#c9c9e8"); });
      box(g, x - 20, y - 26, 40, 20, 3, "#fffdf6"); box(g, x - 20, y - 14, 40, 3, 0, "#ff8fa8"); box(g, x - 20, y - 26, 40, 4, 2, "#8fd0c8");
      line(g, [[x + 16, y - 26], [x + 16, y - 52]], "#c9c9e8", 1.4); shape(g, [[x - 4, y - 50], [x + 16, y - 60], [x + 36, y - 50]], "#ff8fa8");
      [[-12, "#ffd9e3"], [-4, "#c8f0d8"], [4, "#fff0b0"]].forEach(([dx, c]) => { shape(g, [[x + dx - 3, y - 30], [x + dx + 3, y - 30], [x + dx, y - 22]], "#e8a070"); oval(g, x + dx, y - 31.5, 3.4, 3, c); });
    },
    puppy(g, x, y) {
      oval(g, x, y, 13, 2.2, "#2c535222");
      oval(g, x + 9, y - 10, 2.4, 6, "#c98f52"); oval(g, x, y - 8, 10, 8, "#d9a86c"); oval(g, x - 1, y - 6, 5.4, 5, "#f5dfbe");
      [-5, 3].forEach(dx => oval(g, x + dx, y - 1.4, 3.2, 2, "#d9a86c"));
      oval(g, x - 3, y - 20, 8, 7, "#d9a86c"); oval(g, x - 10, y - 18, 3.2, 6.4, "#8a5f3c"); oval(g, x + 4, y - 18, 3.2, 6.4, "#8a5f3c");
      oval(g, x - 3, y - 16.4, 4.4, 3.2, "#f5dfbe"); oval(g, x - 3, y - 18, 1.6, 1.2, "#27324f");
      oval(g, x - 6, y - 22, 1, 1, "#27324f"); oval(g, x, y - 22, 1, 1, "#27324f"); box(g, x - 8, y - 13.4, 10, 2, 1, "#ff5f7a"); oval(g, x - 3, y - 11.4, 1.4, 1.4, "#ffd93b");
    },
    kitty(g, x, y) {
      oval(g, x, y, 12, 2.2, "#2c535222");
      line(g, [[x + 8, y - 3], [x + 15, y - 8], [x + 13, y - 18]], "#ffa95c", 3);
      oval(g, x, y - 8, 9, 8, "#ffa95c"); oval(g, x, y - 5, 4.4, 4.6, "#fff0dc");
      shape(g, [[x - 7, y - 23], [x - 6, y - 31], [x - 1, y - 25]], "#ffa95c"); shape(g, [[x + 7, y - 23], [x + 6, y - 31], [x + 1, y - 25]], "#ffa95c");
      oval(g, x, y - 20, 7.6, 6.6, "#ffa95c"); [-4, 0, 4].forEach(dx => line(g, [[x + dx - 1, y - 26], [x + dx, y - 23]], "#e8833a", 1));
      oval(g, x - 3, y - 20.6, 1.2, 1.6, "#3f8f63"); oval(g, x + 3, y - 20.6, 1.2, 1.6, "#3f8f63"); oval(g, x, y - 17.6, 1, .7, "#ff8fa8");
      line(g, [[x - 2, y - 17], [x - 9, y - 18]], "#fffdf6", .5); line(g, [[x + 2, y - 17], [x + 9, y - 18]], "#fffdf6", .5);
    },
    canopy(g, x, y) {
      oval(g, x, y, 28, 3, "#2c535222");
      [-26, 24].forEach(dx => box(g, x + dx, y - 62, 3, 62, 1, "#fffdf6"));
      shape(g, [[x - 30, y - 60], [x + 30, y - 60], [x + 24, y - 68], [x - 24, y - 68]], "#ff8fc7"); [-20, -6, 8, 22].forEach(dx => oval(g, x + dx - 3, y - 59, 7, 3, "#ffc9e3"));
      shape(g, [[x - 26, y - 58], [x - 16, y - 58], [x - 22, y - 16]], "#ffc9e3aa"); shape(g, [[x + 26, y - 58], [x + 16, y - 58], [x + 22, y - 16]], "#ffc9e3aa");
      box(g, x - 24, y - 12, 49, 12, 2, "#fffdf6"); box(g, x - 23, y - 19, 47, 9, 3, "#ffffff"); box(g, x - 21, y - 22, 13, 6, 3, "#ffd9e3");
      box(g, x - 6, y - 20, 30, 11, 3, "#ff8fc7"); heart(g, x + 9, y - 16, .65, "#ffffff");
      shape(g, [[x - 4, y - 72], [x, y - 77], [x + 4, y - 72]], "#ffd93b");
    },
    rocketship(g, x, y) {
      oval(g, x, y, 12, 2.2, "#2c535222");
      shape(g, [[x - 8, y - 14], [x - 15, y], [x - 6, y - 3]], "#ff5f7a"); shape(g, [[x + 8, y - 14], [x + 15, y], [x + 6, y - 3]], "#ff5f7a");
      box(g, x - 8, y - 46, 16, 44, 7, "#f1f1fb"); shape(g, [[x - 8, y - 40], [x, y - 58], [x + 8, y - 40]], "#ff5f7a");
      oval(g, x, y - 32, 4.6, 4.6, "#7ab8ff"); oval(g, x, y - 32, 3, 3, "#bfe6f2"); box(g, x - 8, y - 16, 16, 3, 0, "#7ab8ff");
      shape(g, [[x - 4, y - 2], [x + 4, y - 2], [x, y + 6]], "#ffa95c");
    },
    crystalball(g, x, y) {
      glow(g, x, y - 20, 28, "#c5a3ff66");
      shape(g, [[x - 11, y], [x + 11, y], [x + 7, y - 9], [x - 7, y - 9]], "#ffd93b"); box(g, x - 8, y - 11, 16, 3, 1, "#f5b83d");
      oval(g, x, y - 22, 12, 12, "#b9a4e8cc"); oval(g, x + 2, y - 20, 6, 4, "#ff8fc7aa"); oval(g, x - 4, y - 26, 3.6, 2.4, "#ffffffcc");
      twinkle(g, x + 4, y - 26, 2.4, "#fff6c8"); twinkle(g, x - 2, y - 16, 1.8, "#ffffff");
    },
    babydragon(g, x, y) {
      oval(g, x, y, 15, 2.4, "#2c535222");
      line(g, [[x - 8, y - 6], [x - 18, y - 4], [x - 20, y - 10]], "#62b083", 3.4); shape(g, [[x - 20, y - 10], [x - 24, y - 15], [x - 17, y - 13]], "#ffd93b");
      shape(g, [[x - 4, y - 20], [x - 18, y - 34], [x - 14, y - 22], [x - 20, y - 22], [x - 6, y - 14]], "#b9a4e8");
      oval(g, x, y - 10, 10, 9, "#62b083"); oval(g, x + 1, y - 8, 5, 6, "#d6f0b0");
      [-5, 4].forEach(dx => oval(g, x + dx, y - 1.4, 3.2, 2, "#3f8f63"));
      oval(g, x + 6, y - 23, 7.4, 6.6, "#62b083"); oval(g, x + 12, y - 21, 3.6, 3, "#62b083"); oval(g, x + 14, y - 21.6, .6, .6, "#27324f");
      oval(g, x + 7, y - 25, 1.8, 2.2, "#ffffff"); oval(g, x + 7.6, y - 25, 1, 1.4, "#27324f");
      [[2, -29], [6, -30.6], [10, -29]].forEach(([dx, dy]) => shape(g, [[x + dx - 1.6, y + dy + 1], [x + dx, y + dy - 3], [x + dx + 1.6, y + dy + 1]], "#ffd93b"));
      oval(g, x + 3, y - 20, 1.4, 1, "#ff8fa8");
    },
  };
  function homeWall(g, wall) {
    const [colour, stripe] = WALLS[wall] || WALLS.w_cream;
    g.fillStyle = colour; g.fillRect(0, 0, W, FLOOR_TOP);
    if (wall === "w_sky") {
      const fill = g.createLinearGradient(0, 0, 0, FLOOR_TOP);
      fill.addColorStop(0, "#8fd0ee"); fill.addColorStop(1, "#e6f6ee");
      g.fillStyle = fill; g.fillRect(0, 0, W, FLOOR_TOP);
      cloud(g, 60, 30, .7); cloud(g, 150, 52, .5);
    } else if (wall === "w_sea") {
      for (let y = 14; y < FLOOR_TOP; y += 18) line(g, Array.from({length: 21}, (_, i) => [i * 16, y + (i % 2 ? 3 : -3)]), "#9fd8f0", 1.2);
      for (let i = 0; i < 14; i++) oval(g, starX(i), starY(i, 100), 1.6 + i % 3, 1.6 + i % 3, "#d6f4f8aa");
    } else if (wall === "w_castle") {
      for (let r = 0; r * 12 < FLOOR_TOP; r++) for (let c = -1; c < 11; c++) box(g, c * 32 + r % 2 * 16 + 1, r * 12 + 1, 30, 10, 2, (r * 3 + c) % 4 ? stripe : "#c6c1d4");
    } else if (wall === "w_attic") {
      for (let x = 0; x < W; x += 20) { box(g, x, 0, 19, FLOOR_TOP, 0, x % 40 ? colour : stripe); oval(g, x + 10, 20, .9, .9, "#7a5434"); oval(g, x + 10, 90, .9, .9, "#7a5434"); }
    } else if (wall === "w_dots") {
      for (let r = 0; r * 16 < FLOOR_TOP; r++) for (let c = 0; c < 21; c++) oval(g, c * 16 + r % 2 * 8 + 4, r * 16 + 8, 3, 3, stripe);
    } else if (wall === "w_hearts") {
      for (let r = 0; r * 22 < FLOOR_TOP; r++) for (let c = 0; c < 12; c++) heart(g, c * 28 + r % 2 * 14 + 8, r * 22 + 8, 1, r % 2 ? stripe : "#ffb3cc");
    } else if (wall === "w_bubble") {
      box(g, 0, FLOOR_TOP - 34, W, 34, 0, "#fffdf6"); for (let x = 0; x < W; x += 12) line(g, [[x, FLOOR_TOP - 34], [x, FLOOR_TOP]], "#d6ecf4", .8);
      line(g, [[0, FLOOR_TOP - 22], [W, FLOOR_TOP - 22]], "#d6ecf4", .8); line(g, [[0, FLOOR_TOP - 10], [W, FLOOR_TOP - 10]], "#d6ecf4", .8);
      for (let i = 0; i < 22; i++) { const r = 2 + i % 4 * 1.6; g.strokeStyle = "#ffffffcc"; g.lineWidth = 1; g.beginPath(); g.arc(starX(i), starY(i, 70) + 4, r, 0, 7); g.stroke(); oval(g, starX(i) - r * .35, starY(i, 70) + 4 - r * .35, r * .25, r * .2, "#ffffff"); }
    } else if (wall === "w_splat") {
      for (let i = 0; i < 16; i++) { const c = ["#ff8fa8", "#ffd27a", "#8fd0c8", "#b9a4e8", "#7ab8ff"][i % 5], sx = starX(i), sy = starY(i, 100) + 4;
        oval(g, sx, sy, 5 + i % 3 * 2, 4 + i % 2 * 2, c + "aa"); oval(g, sx + 7, sy - 4, 1.6, 1.6, c + "aa"); oval(g, sx - 6, sy + 5, 1.2, 1.2, c + "aa"); }
    } else if (wall === "w_music") {
      for (let x = 16; x < W; x += 32) box(g, x, 0, 16, FLOOR_TOP, 0, stripe);
      for (let i = 0; i < 12; i++) note(g, starX(i), starY(i, 90) + 16, ["#b9a4e8", "#ff8fb3", "#7ab8ff"][i % 3]);
    } else if (wall === "w_paws") {
      for (let i = 0; i < 18; i++) paw(g, starX(i), starY(i, 96) + 10, stripe);
    } else if (wall === "w_leaf") {
      for (let i = 0; i < 46; i++) oval(g, starX(i), starY(i, 104) + 4, 7 + i % 3 * 2, 4 + i % 2 * 2, ["#86c46f", "#6fb05a", "#a8d98f"][i % 3]);
    } else if (wall === "w_space") {
      for (let i = 0; i < 40; i++) oval(g, starX(i), starY(i, 106), .6 + i % 3 * .4, .6 + i % 3 * .4, i % 7 ? "#fff4cf" : "#c5a3ff");
      glow(g, 70, 40, 30, "#c5a3ff33"); glow(g, 250, 70, 26, "#7ab8ff33");
    } else if (wall === "w_sweets") {
      for (let x = 10; x < W; x += 40) { line(g, [[x, 0], [x + 12, FLOOR_TOP]], "#ffb3cc", 5); line(g, [[x + 6, 0], [x + 18, FLOOR_TOP]], "#ffffff", 2); }
    } else if (wall === "w_star") {
      for (let x = 16; x < W; x += 32) box(g, x, 0, 16, FLOOR_TOP, 0, stripe);
      for (let i = 0; i < 16; i++) twinkle(g, starX(i), starY(i, 100) + 6, 2.6 + i % 3, "#ffd93b");
    } else {
      for (let x = 16; x < W; x += 32) box(g, x, 0, 16, FLOOR_TOP, 0, stripe);
      if (wall === "w_night") for (let i = 0; i < 30; i++) oval(g, starX(i), starY(i, 100), .7 + i % 3 * .3, .7 + i % 3 * .3, "#fff4cf");
      if (wall === "w_candy") for (let i = 0; i < 18; i++) oval(g, starX(i), starY(i, 100), 1.4, 1.4, ["#8fd0c8", "#ffd27a", "#b9a4e8"][i % 3]);
    }
  }
  function homeFloor(g, floor) {
    const plank = colour => { for (let r = 0; r < 5; r++) { line(g, [[0, FLOOR_TOP + r * 14], [W, FLOOR_TOP + r * 14]], colour, .8); for (let c = 0; c < 6; c++) line(g, [[c * 60 + r % 2 * 30, FLOOR_TOP + r * 14], [c * 60 + r % 2 * 30, FLOOR_TOP + r * 14 + 14]], colour, .8); } };
    g.fillStyle = FLOORS[floor] || FLOORS.f_wood; g.fillRect(0, FLOOR_TOP, W, H - FLOOR_TOP);
    if (floor === "f_check") { for (let r = 0; r < 5; r++) for (let c = 0; c < 20; c++) if ((r + c) % 2) box(g, c * 16, FLOOR_TOP + r * 14, 16, 14, 0, "#ffc9dc"); }
    else if (floor === "f_grass") { patches(g, "#b6df9f", FLOOR_TOP + 6); flowers(g, FLOOR_TOP + 10, ["#ff9fb5", "#fff0a8", "#c7b4f0"], 10); }
    else if (floor === "f_cloud") { for (let i = 0; i < 12; i++) cloud(g, (i * 67 + 21) % W, FLOOR_TOP + 10 + (i * 23) % 56, .8, "#ffffff"); }
    else if (floor === "f_carpet") { for (let r = 0; r < 6; r++) for (let c = 0; c < 16; c++) oval(g, c * 20 + r % 2 * 10 + 5, FLOOR_TOP + 6 + r * 11, 1.6, 1.2, "#cdbcf2"); }
    else if (floor === "f_tile") { for (let r = 0; r < 6; r++) line(g, [[0, FLOOR_TOP + r * 12], [W, FLOOR_TOP + r * 12]], "#fffdf6", 1); for (let c = 0; c < 20; c++) line(g, [[c * 16, FLOOR_TOP], [c * 16, H]], "#fffdf6", 1); }
    else if (floor === "f_sand") { for (let i = 0; i < 60; i++) oval(g, starX(i), FLOOR_TOP + 4 + starY(i, 62), .8, .8, i % 2 ? "#e2c27e" : "#fff4d4"); }
    else if (floor === "f_rainbow") { ["#ff9fb5", "#ffc59a", "#ffe9a0", "#b6e3a8", "#a9d4f5", "#cdbcf2"].forEach((c, i) => box(g, 0, FLOOR_TOP + i * 12, W, 12, 0, c)); }
    else if (floor === "f_gold") { plank("#d9a93a"); for (let i = 0; i < 16; i++) twinkle(g, starX(i), FLOOR_TOP + 6 + starY(i, 58), 1.6, "#fff6c8"); }
    else if (floor === "f_red") { [6, H - FLOOR_TOP - 8].forEach(dy => line(g, [[0, FLOOR_TOP + dy], [W, FLOOR_TOP + dy]], "#ffd27a", 1.6)); for (let i = 0; i < 20; i++) oval(g, starX(i), FLOOR_TOP + 14 + starY(i, 40), 1, 1, "#e8707a"); }
    else if (floor === "f_ice") { for (let i = 0; i < 14; i++) line(g, [[starX(i), FLOOR_TOP + 6 + starY(i, 56)], [starX(i) + 14, FLOOR_TOP + 2 + starY(i, 56)]], "#ffffff", 1.4); for (let i = 0; i < 8; i++) twinkle(g, starX(i + 20), FLOOR_TOP + 6 + starY(i + 20, 58), 1.6, "#ffffff"); }
    else if (floor === "f_stage") { plank("#7a5434"); glow(g, 90, FLOOR_TOP + 30, 40, "#fff6c855"); glow(g, 230, FLOOR_TOP + 34, 40, "#ffc9e355"); }
    else if (floor === "f_moon") { for (let i = 0; i < 14; i++) { const r = 2 + i % 4 * 1.6; oval(g, starX(i), FLOOR_TOP + 8 + starY(i, 54), r * 1.6, r * .7, "#b2b2c6"); oval(g, starX(i), FLOOR_TOP + 7.4 + starY(i, 54), r * 1.2, r * .45, "#bdbdcf"); } }
    else if (floor === "f_candy") { for (let i = 0; i < 70; i++) box(g, starX(i), FLOOR_TOP + 4 + starY(i, 62), 3, 1.2, .5, ["#ffffff", "#8fd0c8", "#ffd27a", "#b9a4e8", "#ff5f7a"][i % 5]); }
    else if (floor === "f_diamond") { for (let r = 0; r < 5; r++) for (let c = 0; c < 17; c++) shape(g, [[c * 20 + r % 2 * 10, FLOOR_TOP + 6 + r * 14], [c * 20 + r % 2 * 10 + 6, FLOOR_TOP + r * 14], [c * 20 + r % 2 * 10 + 12, FLOOR_TOP + 6 + r * 14], [c * 20 + r % 2 * 10 + 6, FLOOR_TOP + 12 + r * 14]], (r + c) % 3 ? "#e3f6fb" : "#ffffff"); for (let i = 0; i < 10; i++) twinkle(g, starX(i), FLOOR_TOP + 6 + starY(i, 58), 1.8, "#ffffff"); }
    else plank("#c2915a");
    box(g, 0, FLOOR_TOP - 4, W, 5, 0, "#fffdf6");
  }
  function homeWindow(g, wall) {
    const dark = ["w_night", "w_castle"].includes(wall);
    box(g, 196, 26, 60, 46, 3, "#fffdf6"); box(g, 200, 30, 52, 38, 2, dark ? "#1f2a5c" : "#a9dcec");
    if (dark) { oval(g, 238, 42, 6, 6, "#fff4cf"); oval(g, 241, 40, 5.4, 5.4, "#1f2a5c"); } else cloud(g, 226, 50, .62);
    line(g, [[226, 30], [226, 68]], "#fffdf6", 2); line(g, [[200, 49], [252, 49]], "#fffdf6", 2);
  }
  const flags = (g, y) => { for (let i = 0; i < 16; i++) { line(g, [[i * 20, y + i % 2 * 3], [i * 20 + 20, y + (i + 1) % 2 * 3]], "#27324f", .8); shape(g, [[i * 20 + 5, y + 2], [i * 20 + 15, y + 2], [i * 20 + 10, y + 11]], ["#ff5f7a", "#ffd93b", "#8fd0c8", "#b9a4e8"][i % 4]); } };
  // What each kind of room has built in (pixel.py HOME_ROOMS), painted on its back wall or its floor.
  const ROOM_ART = {
    living(g, room) {
      homeWindow(g, room.wall);
      box(g, 92, 34, 40, 30, 2, "#c08a56"); box(g, 95, 37, 34, 24, 1, "#a9dcec");
      shape(g, [[95, 61], [107, 45], [116, 54], [121, 48], [129, 61]], "#62b083"); oval(g, 122, 43, 3, 3, "#ffe14a");
      line(g, [[160, 0], [160, 14]], "#27324f", 1); shape(g, [[150, 22], [170, 22], [164, 14], [156, 14]], "#ffd27a");
    },
    r_bed(g, room) {
      homeWindow(g, room.wall);
      [[188, 1], [264, -1]].forEach(([x, way]) => shape(g, [[x, 22], [x + way * 14, 22], [x + way * 9, 76], [x - way * 2, 78]], "#ff9fb5"));
      box(g, 184, 20, 84, 4, 2, "#a9744a");
      box(g, 92, 30, 34, 28, 2, "#a9744a"); box(g, 95, 33, 28, 22, 1, "#27324f");
      oval(g, 104, 42, 4, 4, "#fff4cf"); oval(g, 106, 40, 3.6, 3.6, "#27324f"); twinkle(g, 115, 46, 2, "#fff4cf");
      [[40, 20], [140, 12], [290, 16]].forEach(([x, y]) => twinkle(g, x, y, 3, "#ffffffcc"));
    },
    r_kitchen(g, room) {
      homeWindow(g, room.wall);
      box(g, 66, 22, 108, 26, 2, "#fffdf6"); [0, 1, 2, 3].forEach(i => { box(g, 69 + i * 26.5, 25, 24, 20, 1, "#ffd9e3"); box(g, 79 + i * 26.5, 33, 4, 2, 1, "#a9744a"); });
      box(g, 66, 80, 108, 32, 1, "#fffdf6"); box(g, 64, 76, 112, 5, 1, "#c9c9e8");
      [0, 1, 2, 3].forEach(i => { box(g, 69 + i * 26.5, 84, 24, 24, 1, "#ffd9e3"); oval(g, 81 + i * 26.5, 88, 1.4, 1.4, "#a9744a"); });
      box(g, 104, 74, 26, 4, 1, "#a9dcec"); line(g, [[117, 74], [117, 66], [123, 66]], "#a9a9c8", 1.6);
      [[188, "#ff8fa8"], [276, "#ffd27a"]].forEach(([x, c]) => { line(g, [[x, 22], [x, 30]], "#8a8a9a", .8); oval(g, x, 36, 6, 6, c); line(g, [[x, 42], [x, 50]], "#8a5f3c", 1.6); });
    },
    r_play(g, room) {
      homeWindow(g, room.wall);
      flags(g, 6);
      box(g, 80, 30, 76, 46, 2, "#a9744a"); box(g, 83, 33, 70, 40, 1, "#3f6b58");
      line(g, [[92, 62], [100, 50], [108, 62]], "#fffdf6", 1.2); box(g, 94, 62, 12, 8, 0, "#fffdf6aa");
      oval(g, 130, 46, 5, 5, "#ffe39a"); line(g, [[118, 66], [124, 60], [130, 66], [136, 60], [142, 66]], "#ff9fb5", 1.2);
      [[40, 70, "#ffd93b"], [60, 40, "#ff8fa8"], [176, 56, "#8fd0c8"], [290, 40, "#b9a4e8"]].forEach(([x, y, c]) => twinkle(g, x, y, 5, c));
    },
    r_garden(g) {
      g.fillStyle = "#ffe14a"; g.beginPath(); g.arc(266, 26, 12, 0, 7); g.fill();
      for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; line(g, [[266 + Math.cos(a) * 16, 26 + Math.sin(a) * 16], [266 + Math.cos(a) * 21, 26 + Math.sin(a) * 21]], "#ffe14a", 1.6); }
      line(g, [[0, 92], [W, 92]], "#fffdf6", 2); line(g, [[0, 102], [W, 102]], "#fffdf6", 2);
      for (let x = 6; x < W; x += 14) shape(g, [[x - 4, 108], [x - 4, 86], [x, 82], [x + 4, 86], [x + 4, 108]], "#fffdf6");
      [70, 160, 250].forEach((x, i) => { oval(g, x, 102, 16, 10, i % 2 ? "#569f70" : "#62b083"); oval(g, x - 5, 98, 2, 2, "#ff8fa8"); oval(g, x + 6, 100, 2, 2, "#ffd27a"); });
      [[120, 40], [128, 36]].forEach(([x, y]) => { oval(g, x - 2, y, 2.4, 1.6, "#ff8fc7"); oval(g, x + 2, y, 2.4, 1.6, "#ff8fc7"); });     // butterflies
    },
    r_attic(g) {
      shape(g, [[0, 0], [54, 0], [0, 34]], "#8a5f3c"); shape(g, [[W, 0], [W - 54, 0], [W, 34]], "#8a5f3c");
      line(g, [[0, 34], [54, 0]], "#6d4a2c", 3); line(g, [[W, 34], [W - 54, 0]], "#6d4a2c", 3);
      box(g, 0, 6, W, 5, 0, "#7a5434");
      oval(g, 160, 50, 18, 18, "#fffdf6"); oval(g, 160, 50, 15, 15, "#1f2a5c");
      [[154, 44], [166, 52], [158, 58]].forEach(([x, y]) => oval(g, x, y, .9, .9, "#fff4cf"));
      line(g, [[145, 50], [175, 50]], "#fffdf6", 1.6); line(g, [[160, 35], [160, 65]], "#fffdf6", 1.6);
      line(g, [[100, 11], [100, 30]], "#27324f", 1); glow(g, 100, 34, 18, "#ffe7a088"); oval(g, 100, 34, 4, 5, "#fff6c8");
      [[56, 11], [70, 11], [62, 24]].forEach(p => line(g, [[56, 11], p], "#fffdf6aa", .6));     // a cobweb
      line(g, [[62, 15], [66, 11]], "#fffdf6aa", .6); line(g, [[59, 17], [64, 18]], "#fffdf6aa", .6);
    },
    r_games(g) {
      flags(g, 8);
      glow(g, 160, 50, 36, "#c5a3ff55");
      box(g, 132, 34, 56, 32, 6, "#b9a4e8"); box(g, 135, 37, 50, 26, 5, "#2f3a72");
      line(g, [[150, 56], [150, 44]], "#8fd0c8", 2); oval(g, 150, 43, 3.4, 3.4, "#ff5f7a");
      [[168, 46, "#ffd93b"], [176, 52, "#8fd0c8"], [168, 54, "#ff8fa8"]].forEach(([x, y, c]) => oval(g, x, y, 2.6, 2.6, c));
      [[64, "#ff8fa8"], [234, "#7ab8ff"]].forEach(([x, c]) => { box(g, x, 30, 30, 40, 1, c); twinkle(g, x + 15, 46, 6, "#fff4cf"); box(g, x + 5, 60, 20, 4, 1, "#fffdf6"); });
    },
    r_pool(g, room) {
      homeWindow(g, room.wall);
      oval(g, 70, 54, 12, 12, "#ff5f7a"); oval(g, 70, 54, 6.4, 6.4, WALLS[room.wall] ? WALLS[room.wall][0] : "#fdf1d8");
      [0, 1, 2, 3].forEach(i => box(g, 70 + Math.cos(i * 1.57 + .78) * 9 - 2, 54 + Math.sin(i * 1.57 + .78) * 9 - 2, 4, 4, 1, "#fffdf6"));
      box(g, 78, FLOOR_TOP + 14, 164, 40, 8, "#fffdf6"); box(g, 82, FLOOR_TOP + 18, 156, 32, 6, "#5cc4e6");
      for (let i = 0; i < 6; i++) line(g, [[96 + i * 24, FLOOR_TOP + 26 + i % 2 * 12], [108 + i * 24, FLOOR_TOP + 26 + i % 2 * 12]], "#bfeaf2", 1.4);
      [226, 232].forEach(x => line(g, [[x, FLOOR_TOP + 8], [x, FLOOR_TOP + 26]], "#c9c9e8", 1.4));
      [12, 18].forEach(dy => line(g, [[226, FLOOR_TOP + dy], [232, FLOOR_TOP + dy]], "#c9c9e8", 1.2));
    },
    r_secret(g) {
      [70, 250].forEach(x => { glow(g, x, 40, 24, "#ffb35c66"); box(g, x - 2, 42, 4, 16, 1, "#8a5f3c"); shape(g, [[x - 5, 42], [x + 5, 42], [x, 28]], "#ffa95c"); shape(g, [[x - 2.4, 42], [x + 2.4, 42], [x, 34]], "#ffe39a"); });
      glow(g, 160, 82, 34, "#c5a3ff55");
      [[146, 108, 8, 22, "#b9a4e8"], [160, 108, 10, 30, "#c5a3ff"], [174, 108, 8, 20, "#8fd0c8"]].forEach(([x, y, w, h, c]) => shape(g, [[x - w / 2, y], [x - w / 2, y - h + 6], [x, y - h], [x + w / 2, y - h + 6], [x + w / 2, y]], c));
      [[120, 106], [126, 104], [200, 106], [194, 103], [206, 104]].forEach(([x, y]) => oval(g, x, y, 3, 2, "#ffe14a"));
    },
    r_bath(g, room) {
      homeWindow(g, room.wall);
      oval(g, 110, 46, 16, 20, "#ffd27a"); oval(g, 110, 46, 13, 17, "#bfe6f2"); line(g, [[104, 38], [110, 32]], "#ffffff", 1.6);
      box(g, 96, 70, 28, 4, 1, "#fffdf6"); oval(g, 102, 67, 3, 3, "#ff8fc7"); box(g, 114, 62, 4, 8, 1, "#8fd0c8");
      line(g, [[140, 44], [176, 44]], "#c9c9e8", 2); box(g, 144, 44, 12, 22, 2, "#ff8fa8"); box(g, 159, 44, 12, 18, 2, "#8fd0c8"); line(g, [[144, 60], [156, 60]], "#ffffff", 1.2);
      [[52, 30, 6], [70, 20, 4], [276, 18, 5], [290, 34, 3.4]].forEach(([x, y, r]) => { g.strokeStyle = "#ffffff"; g.lineWidth = 1.2; g.beginPath(); g.arc(x, y, r, 0, 7); g.stroke(); });
    },
    r_art(g, room) {
      homeWindow(g, room.wall);
      line(g, [[30, 18], [180, 24]], "#8a5f3c", .8);
      [[44, "#ff8fa8"], [80, "#7ab8ff"], [116, "#ffd27a"], [152, "#8fd0c8"]].forEach(([x, c], i) => {
        const y = 19 + (x - 30) * .04; box(g, x - 11, y - 1, 22, 26, 1, "#c9b48c"); box(g, x - 10, y, 20, 24, 1, "#fffdf6"); box(g, x - 2, y - 2, 4, 4, 1, "#ff5f7a");
        if (i % 2) oval(g, x, y + 11, 6, 6, c); else shape(g, [[x - 7, y + 20], [x, y + 6], [x + 7, y + 20]], c);
        oval(g, x - 5, y + 5, 2, 2, "#ffd93b"); });
      box(g, 60, 62, 70, 40, 2, "#d9a86c"); box(g, 64, 66, 62, 32, 1, "#fffdf6");
      shape(g, [[66, 96], [80, 74], [94, 88], [106, 70], [124, 96]], "#62b083"); oval(g, 112, 74, 4, 4, "#ffd93b"); heart(g, 76, 74, .9, "#ff8fa8");
      [[150, "#ff5f7a"], [160, "#ffd93b"], [170, "#7ab8ff"]].forEach(([x, c]) => { box(g, x - 4, 100, 8, 10, 2, "#fffdf6"); box(g, x - 4, 100, 8, 3, 1, c); });
    },
    r_music(g) {
      [[60, "#ffd27a"], [160, "#ff8fc7"], [260, "#8fd0c8"]].forEach(([x, c]) => { shape(g, [[x - 6, 0], [x + 6, 0], [x + 30, FLOOR_TOP], [x - 30, FLOOR_TOP]], c + "22"); box(g, x - 7, 0, 14, 6, 2, "#27324f"); oval(g, x, 6, 5, 2, c); });
      [[34, 54], [286, 54]].forEach(([x, y]) => { box(g, x - 14, y - 20, 28, 54, 2, "#27324f"); oval(g, x, y - 6, 8, 8, "#4a5578"); oval(g, x, y - 6, 3.4, 3.4, "#27324f"); oval(g, x, y + 18, 11, 11, "#4a5578"); oval(g, x, y + 18, 4.6, 4.6, "#27324f"); });
      box(g, 120, 28, 80, 30, 4, "#ff5f7a"); box(g, 124, 32, 72, 22, 3, "#ffe39a");
      ["#ff5f7a", "#7ab8ff", "#62b083", "#b9a4e8"].forEach((c, i) => note(g, 136 + i * 16, 48 - i % 2 * 4, c));
      line(g, [[0, 74], [W, 74]], "#ffd27a", 1.6); for (let x = 6; x < W; x += 12) oval(g, x, 74, 2.2, 2.2, ["#ff5f7a", "#ffd93b", "#8fd0c8", "#c5a3ff"][x / 12 % 4 | 0]);
    },
    r_library(g) {
      [[24, 120], [200, 296]].forEach(([a, b]) => {
        box(g, a, 8, b - a, FLOOR_TOP - 8, 2, "#8a5f3c");
        for (let row = 0; row < 4; row++) {
          box(g, a + 3, 11 + row * 25, b - a - 6, 22, 1, "#5a3a22");
          for (let x = a + 5, i = row; x < b - 7; i++) { const w = 4 + (i * 7) % 4, h = 14 + (i * 5) % 7;
            box(g, x, 33 + row * 25 - h, w, h, .5, ["#e8553f", "#7ab8ff", "#ffd27a", "#62b083", "#b9a4e8", "#ff8fa8", "#fffdf6"][i % 7]); x += w + .8; }
        }
      });
      box(g, 132, 26, 56, 40, 2, "#fffdf6"); box(g, 136, 30, 48, 32, 1, "#a9dcec"); cloud(g, 160, 48, .5); line(g, [[160, 30], [160, 62]], "#fffdf6", 2);
      line(g, [[160, 70], [160, 84]], "#ffd27a", 1.2); glow(g, 160, 92, 18, "#fff2a066"); shape(g, [[150, 92], [170, 92], [165, 84], [155, 84]], "#62b083");
    },
    r_pets(g, room) {
      homeWindow(g, room.wall);
      [[64, 30, "#ff8fa8"], [120, 24, "#7ab8ff"]].forEach(([x, y, c]) => { box(g, x - 16, y, 32, 28, 2, c); box(g, x - 13, y + 3, 26, 22, 1, "#fffdf6"); paw(g, x, y + 18, c); });
      box(g, 60, 72, 30, 3, 1, "#a9744a"); [66, 74, 82].forEach(x => { line(g, [[x, 75], [x, 82]], "#8a8a9a", 1); oval(g, x, 84, 2, 2, "#8a8a9a"); });
      shape(g, [[150, 60], [152, 54], [158, 57], [168, 57], [174, 54], [176, 60], [174, 66], [168, 63], [158, 63], [152, 66]], "#fffdf6");
      [[30, FLOOR_TOP + 12, "#ff8fa8"], [290, FLOOR_TOP + 10, "#7ab8ff"]].forEach(([x, y, c]) => { oval(g, x, y, 10, 3.4, c); oval(g, x, y - 1, 7, 2, "#a9744a"); });
    },
    r_tree(g) {
      box(g, 140, 0, 40, FLOOR_TOP, 4, "#8a5f3c"); for (let y = 8; y < FLOOR_TOP; y += 16) line(g, [[146, y], [152, y + 6]], "#6d4a2c", 1.2);
      oval(g, 160, 50, 10, 12, "#5a3a22"); oval(g, 162, 52, 6, 8, "#3a2614"); oval(g, 158, 46, 2.2, 2.2, "#ffd93b"); oval(g, 163, 46, 2.2, 2.2, "#ffd93b");     // an owl's hole
      line(g, [[180, 30], [250, 16]], "#8a5f3c", 5); line(g, [[140, 40], [70, 24]], "#8a5f3c", 5);
      box(g, 222, 34, 56, 44, 22, "#7a5434"); box(g, 226, 38, 48, 36, 18, "#a9dcec"); cloud(g, 250, 58, .5); line(g, [[250, 38], [250, 74]], "#7a5434", 2);
      [[56, 64], [62, 64]].forEach(([x]) => line(g, [[x, 10], [x, FLOOR_TOP]], "#c9a26b", 1.6)); for (let y = 20; y < FLOOR_TOP; y += 12) line(g, [[56, y], [62, y]], "#c9a26b", 1.6);
      [[100, 18], [270, 10]].forEach(([x, y]) => { oval(g, x, y, 4, 3, "#ff8fa8"); oval(g, x + 3, y - 2, 2.4, 2.2, "#ff8fa8"); shape(g, [[x + 5, y - 2], [x + 8, y - 1], [x + 5, y]], "#ffa95c"); });
    },
    r_space(g) {
      oval(g, 160, 50, 34, 34, "#c9c9e8"); oval(g, 160, 50, 29, 29, "#0b0f2c");
      oval(g, 160, 54, 16, 16, "#5aa8e8"); shape(g, [[150, 46], [158, 42], [160, 50], [152, 58]], "#62b083"); shape(g, [[164, 56], [172, 50], [174, 60], [166, 66]], "#62b083");
      [[136, 34], [184, 30], [180, 74], [140, 70]].forEach(([x, y]) => oval(g, x, y, 1, 1, "#fff4cf"));
      [0, 1, 2, 3, 4, 5, 6, 7].forEach(i => oval(g, 160 + Math.cos(i * .785) * 31.5, 50 + Math.sin(i * .785) * 31.5, 1.6, 1.6, "#8a8aa8"));
      oval(g, 60, 34, 14, 14, "#ffb35c"); g.strokeStyle = "#c5a3ff"; g.lineWidth = 2; g.beginPath(); g.ellipse(60, 34, 24, 5, -.3, 0, 7); g.stroke(); oval(g, 60, 34, 14, 5, "#ffb35c");
      oval(g, 270, 26, 9, 9, "#fff4cf"); oval(g, 274, 23, 8, 8, "#151b45");
      line(g, [[230, 80], [262, 68]], "#ffffff88", 1.4); twinkle(g, 264, 67, 3, "#ffffff");
      box(g, 90, 66, 24, 34, 2, "#fffdf6"); box(g, 93, 69, 18, 28, 1, "#27324f"); shape(g, [[102, 72], [106, 80], [106, 90], [98, 90], [98, 80]], "#ff5f7a"); oval(g, 102, 83, 2, 2, "#7ab8ff");
    },
    r_candy(g) {
      [[50, 34, 13, "#ff8fa8"], [270, 30, 15, "#8fd0c8"], [110, 22, 9, "#ffd27a"], [214, 24, 10, "#b9a4e8"]].forEach(([x, y, r, c]) => lolly(g, x, y, r, c));
      [[150, "#ff5f7a"], [174, "#62b083"]].forEach(([x, c]) => { line(g, [[x, 96], [x, 46], [x + 8, 38], [x + 16, 46]], "#fffdf6", 5); line(g, [[x, 92], [x, 84]], c, 5); line(g, [[x, 74], [x, 66]], c, 5); line(g, [[x, 56], [x, 48]], c, 5); });
      for (let x = 8; x < W; x += 22) { oval(g, x, FLOOR_TOP - 6, 7, 6, ["#ff8fa8", "#ffd27a", "#8fd0c8", "#b9a4e8"][x / 22 % 4 | 0]); oval(g, x - 2, FLOOR_TOP - 9, 2, 1.4, "#ffffffaa"); }
      box(g, 226, 56, 30, 36, 3, "#8a5f3c"); for (let r = 0; r < 3; r++) for (let c = 0; c < 2; c++) box(g, 229 + c * 13.5, 59 + r * 11, 11, 9, 2, "#a0703f");
      box(g, 226, 78, 30, 14, 2, "#ffd9e3"); twinkle(g, 241, 85, 3, "#ffd93b");
    },
  };
  // Half of an open doorway at the left (way 1) or right (way -1) edge of a room. The two
  // halves meet at the join, so a pal walks straight through.
  function doorway(g, x, way) {
    const left = way > 0 ? x : x - 20;
    box(g, left, 36, 20, FLOOR_TOP - 34, 0, "#fffdf6");
    box(g, way > 0 ? x : x - 16, 40, 16, FLOOR_TOP - 38, 0, "#1b153033");
    box(g, way > 0 ? x : x - 16, FLOOR_TOP - 2, 16, 3, 0, "#c2915a");
  }
  // A piece's colour (pixel.py FURN_PAINTS: 0 is how it came) and size (FURN_SIZES).
  const PAINTS = ["none", "hue-rotate(60deg)", "hue-rotate(120deg)", "hue-rotate(180deg)", "hue-rotate(240deg)", "hue-rotate(300deg)",
                  "sepia(1) saturate(3) brightness(1.05)", "grayscale(1) brightness(1.12)"];
  const SIZES = [1, 1.4, 1.9];
  const sizeOf = item => SIZES[item.size === undefined ? 1 : item.size] || 1.4;
  function drawPiece(g, item, x, y) {
    if (!FURNITURE_ART[item.key]) return;
    const s = sizeOf(item);
    g.save(); g.translate(x, y); g.scale(item.flip ? -s : s, s);
    if (item.paint) g.filter = PAINTS[item.paint] || "none";
    FURNITURE_ART[item.key](g, 0, 0);
    g.restore();
  }
  /** The things standing in room `n` of a home, each with its x from that room's left. */
  const roomItems = (home, n) => (home.items || []).filter(item => Math.floor(item.x / W) === n).map(item => Object.assign({}, item, {x: item.x - n * W}));
  function homeRoom(g, home, n) {
    const rooms = home.rooms && home.rooms.length ? home.rooms : [{kind: "living", wall: "w_cream", floor: "f_wood"}], room = rooms[n] || rooms[0];
    homeWall(g, room.wall);
    homeFloor(g, room.floor);
    (ROOM_ART[room.kind] || ROOM_ART.living)(g, room);
    if (n === 0) {     // the door back outside
      box(g, 12, 40, 40, 70, 3, "#8a5f3c"); box(g, 16, 44, 32, 66, 2, "#c08a56");
      box(g, 20, 49, 24, 22, 2, "#d6a473"); box(g, 20, 76, 24, 28, 2, "#d6a473"); oval(g, 43, 80, 2, 2, "#ffd93b");
    }
    if (n > 0) doorway(g, 0, 1);
    if (n < rooms.length - 1) doorway(g, W, -1);
    for (const item of roomItems(home, n).sort((a, b) => a.y - b.y)) drawPiece(g, item, item.x, seatFeet(item.y));     // normal size sits beside a pal
  }
  /** The piece of furniture at a spot in a home, frontmost first. */
  function furnitureAt(home, x, y) {
    return ((home && home.items) || []).filter(item => FURNITURE_ART[item.key]).sort((a, b) => b.y - a.y).find(item => {
      const pic = furniturePicture(item.key), s = sizeOf(item), wide = pic.width * s / 2 + 4, tall = pic.height * s;
      return Math.abs(x - item.x) < wide && y > seatFeet(item.y) - tall && y < seatFeet(item.y) + 9;
    }) || null;
  }
  const pictures = {};
  /** A little picture of a piece of furniture, for a button. */
  function furniturePicture(key, paint = 0) {
    const name = key + ":" + paint;
    return pictures[name] || (pictures[name] = trimmed(crisp(72, 100, ink => drawPiece(ink, {key, paint, size: 0}, 36, 96))));
  }
  /** A room as it looks when it's built, for the shop: its kind's own things, or just a wall and a floor. */
  function roomPicture(kind, wall, floor) {
    const name = [kind, wall, floor].join(":");
    return pictures[name] || (pictures[name] = crisp(W, FLOOR_TOP + 26, ink => {
      homeWall(ink, wall);
      homeFloor(ink, floor);
      if (ROOM_ART[kind]) ROOM_ART[kind](ink, {wall, floor});
    }));
  }
  // Just the part of a picture that has something in it.
  function trimmed(cv) {
    const d = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height).data;
    let x0 = cv.width, y0 = cv.height, x1 = 0, y1 = 0;
    for (let y = 0; y < cv.height; y++) for (let x = 0; x < cv.width; x++) if (d[(y * cv.width + x) * 4 + 3] > 40) {
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
    const out = document.createElement("canvas");
    out.width = Math.max(1, x1 - x0 + 1); out.height = Math.max(1, y1 - y0 + 1);
    out.getContext("2d").drawImage(cv, -x0, -y0);
    return out;
  }
  const lookColour = key => (WALLS[key] || [FLOORS[key]])[0];
  /** Whether a click in a home is on the door back outside, in the first room. */
  const doorAt = (x, y) => y > 38 && y < FLOOR_TOP + 4 && x > 10 && x < 54;
  /** The pier at the Beach, if this spot in the world is on it. */
  function fishAt(places, x, y) {
    const at = placeAt(places, x);
    return at && at.scene === "beach" && Math.abs(x - at.left - FISH_X) < 20 && y > 96 && y < seatFeet(0) + 9 ? {x: at.left + FISH_X, y: 0} : null;
  }

  // The hiding places. Each one is a thing that belongs where it stands: an oak, a log,
  // a picnic and a berry bush in the Park; roses, gifts, flower crates and a party tent
  // in the Wedding garden. Empty and occupied cover looks exactly the same; only the
  // hidden child's own marker gives feedback.
  function coverAt(covers, x, y) {
    return (covers || []).slice().reverse().find(c => Math.abs(x - c.x) < 24 && y > seatFeet(c.y) - 40 && y < seatFeet(c.y) + 8);
  }
  const COVER_ART = {
    oak(g, x, y) {
      shape(g, [[x - 14, y + 1], [x - 7, y - 11], [x + 7, y - 11], [x + 14, y + 1]], "#84603f");
      box(g, x - 8, y - 38, 16, 38, 3, "#946c47");
      line(g, [[x - 4, y - 30], [x - 4, y - 6]], "#b58a5a", 1.6);
      oval(g, x + 2, y - 17, 3.2, 4.6, "#5a412d");
      oval(g, x - 15, y - 41, 16, 13, "#3d7d5e");
      oval(g, x + 15, y - 42, 16, 13, "#438366");
      oval(g, x - 6, y - 52, 17, 13, "#58956b");
      oval(g, x + 9, y - 54, 15, 11, "#58956b");
      oval(g, x, y - 59, 13, 9, "#70a77b");
      oval(g, x - 5, y - 62, 6, 3.4, "#8cbb8e");
      [[-20, -40], [-8, -47], [6, -44], [20, -45], [12, -57], [-12, -58]].forEach(([dx, dy]) => oval(g, x + dx, y + dy, 1.2, 1.5, "#d9a85b"));
    },
    log(g, x, y) {
      box(g, x - 22, y - 19, 44, 19, 9, "#8f6a47");
      box(g, x - 16, y - 19, 34, 5, 2.5, "#a98058");
      line(g, [[x - 6, y - 11], [x + 8, y - 11]], "#775538", 1);
      line(g, [[x, y - 5], [x + 15, y - 5]], "#775538", 1);
      oval(g, x - 15, y - 9.5, 7.5, 9.5, "#c9a274");
      oval(g, x - 15, y - 9.5, 5.4, 7.4, "#46322a");
      oval(g, x + 7, y - 19, 10, 2.8, "#6aa56f");
      oval(g, x + 15, y - 17.5, 5, 2.2, "#7fb87d");
      line(g, [[x + 22, y], [x + 22, y - 5]], "#fff6e6", 1.8);
      shape(g, [[x + 17, y - 5], [x + 22, y - 10], [x + 27, y - 5]], "#e8728a");
      oval(g, x + 21, y - 7, .9, .9, "#fff6e6");
    },
    picnic(g, x, y) {
      [-19, 19].forEach(dx => line(g, [[x + dx, y], [x + dx, y - 6]], "#8a6a4a", 2));
      box(g, x - 22, y - 21, 44, 18, 2, "#fffdf6");
      g.fillStyle = "#ef7d8e";
      for (let i = 0; i < 8; i++) for (let j = 0; j < 3; j++) if ((i + j) % 2) g.fillRect(x - 22 + i * 5.5, y - 21 + j * 6, 5.5, 6);
      box(g, x - 24, y - 24, 48, 4, 1.5, "#d99a5c");
      g.strokeStyle = "#a87440"; g.lineWidth = 1.4;
      g.beginPath(); g.arc(x - 3, y - 31, 6, Math.PI, 0); g.stroke();
      box(g, x - 10, y - 32, 14, 8, 2, "#c98f52");
      box(g, x - 9, y - 33, 12, 2.4, 1, "#fffdf6");
      oval(g, x + 11, y - 26.5, 2.6, 2.6, "#e8576b");
    },
    bush(g, x, y, c) {
      oval(g, x - 11, y - 10, 13, 11, "#3a7955");
      oval(g, x + 11, y - 10, 13, 11, "#47895c");
      oval(g, x, y - 16, 14, 12, "#65a16c");
      oval(g, x - 3, y - 22, 6, 3.2, "#7fb682");
      [[-16, -12], [-6, -20], [6, -10], [12, -18], [18, -8], [-4, -6]].forEach(([dx, dy]) => {
        if (c.key === "roses") { oval(g, x + dx, y + dy, 2.4, 2.4, "#ff9fb5"); oval(g, x + dx, y + dy, 1, 1, "#ffd9e3"); }
        else oval(g, x + dx, y + dy, 1.8, 1.8, "#6f5bc4");
      });
    },
    gifts(g, x, y) {
      box(g, x - 20, y - 20, 24, 20, 2, "#ff9fb5");
      box(g, x - 10, y - 20, 4, 20, 0, "#fff6fb");
      box(g, x - 20, y - 12, 24, 3.5, 0, "#fff6fb");
      box(g, x + 3, y - 14, 18, 14, 2, "#8fd0c8");
      box(g, x + 10, y - 14, 3.5, 14, 0, "#fff2c0");
      box(g, x - 9, y - 31, 17, 11, 2, "#ffd27a");
      box(g, x - 2, y - 31, 3.5, 11, 0, "#b9a4e8");
      oval(g, x - 3.4, y - 33, 3.2, 2.4, "#b9a4e8");
      oval(g, x + 3, y - 33, 3.2, 2.4, "#b9a4e8");
      oval(g, x + 11.7, y - 15.5, 2.6, 2, "#fff2c0");
    },
    crate(g, x, y) {
      box(g, x - 23, y - 24, 28, 24, 2, "#b88655");
      box(g, x + 1, y - 16, 22, 16, 2, "#d4a16b");
      for (let i = 0; i < 3; i++) line(g, [[x - 21, y - 4 - i * 7], [x + 2, y - 4 - i * 7]], "#8c6547", 1);
      line(g, [[x + 3, y - 8], [x + 21, y - 8]], "#b08052", 1);
      oval(g, x - 10, y - 26, 13, 6, "#5b9466");
      oval(g, x + 12, y - 18, 9, 4.5, "#6aa56f");
      [[-16, -29, "#f7c0ca"], [-9, -31, "#fff6fb"], [-3, -28, "#ffd27a"], [9, -21, "#f7c0ca"], [16, -20, "#d6b8f0"]]
        .forEach(([dx, dy, colour]) => oval(g, x + dx, y + dy, 2.6, 2.6, colour));
    },
    tent(g, x, y) {
      box(g, x - 22, y - 17, 44, 17, 1, "#fffdf6");
      for (let i = 0; i < 4; i++) box(g, x - 22 + i * 11.6, y - 17, 5.8, 17, 0, "#ffd6e3");
      shape(g, [[x - 8, y], [x, y - 15], [x + 8, y]], "#6b5560");
      shape(g, [[x - 26, y - 16], [x, y - 36], [x + 26, y - 16]], "#ff9fb5");
      shape(g, [[x - 9, y - 16], [x, y - 36], [x + 9, y - 16]], "#ffc3d4");
      for (let i = 0; i < 6; i++) oval(g, x - 22 + i * 8.8, y - 15.5, 4.4, 2.6, i % 2 ? "#ffc3d4" : "#ff9fb5");
      line(g, [[x, y - 36], [x, y - 43]], "#8a6a4a", 1);
      shape(g, [[x, y - 43], [x + 7, y - 41], [x, y - 39]], "#ffd27a");
    },
  };
  // Each hiding place as a little pixel picture, with its feet at (SPRITE_X, SPRITE_Y).
  const SPRITE_X = 36, SPRITE_Y = 72, sprites = {};
  function coverSprite(c) {
    const key = c.kind + ":" + c.key;
    if (!sprites[key]) sprites[key] = crisp(72, 80, g => inked(COVER_ART[c.kind] || COVER_ART.bush)(g, SPRITE_X, SPRITE_Y, c));
    return sprites[key];
  }
  const coverFeet = c => Math.round(seatFeet(c.y));
  /** Draws a hiding place at its spot in the world. The stage also uses it to hide the pals behind. */
  const cutCover = (g, c, cam = 0) => g.drawImage(coverSprite(c), Math.round(c.x) - cam - SPRITE_X, coverFeet(c) - SPRITE_Y);
  // How tall the solid part of each hiding place is, so a hidden pal can duck just below the top.
  const COVER_HIGH = {oak: 60, log: 19, picnic: 22, bush: 21, gifts: 20, crate: 21, tent: 24};
  const coverHigh = c => COVER_HIGH[c.kind] || 20;
  // The shadow under a hiding place, and a ring round it while a round of hide and seek is on.
  function coverGround(g, c, cam, active) {
    const x = Math.round(c.x) - cam, y = coverFeet(c);
    oval(g, x, y + 2, 25, 4.6, "#234a3526");
    if (!active) return;
    g.strokeStyle = "#fff8cf"; g.lineWidth = 1.6;
    g.beginPath(); g.ellipse(x, y + 3, 24, 5, 0, 0, Math.PI * 2); g.stroke();
  }
  function gem(g, x, y, shine = 0) {
    shape(g, [[x - 6.2, y - 3], [x - 2.6, y - 8.2], [x + 2.6, y - 8.2], [x + 6.2, y - 3], [x, y + 5.4]], "#2f6fc4");
    shape(g, [[x - 5, y - 3], [x - 2, y - 7], [x + 2, y - 7], [x + 5, y - 3], [x, y + 4]], "#6fb6ff");
    shape(g, [[x - 5, y - 3], [x - 2, y - 7], [x - 1, y - 3]], "#a5d2ff");
    shape(g, [[x - 2, y - 7], [x + 2, y - 7], [x, y - 3]], "#e6f3ff");
    if (shine > .7) twinkle(g, x + 5, y - 8, 2.4, "#ffffff");
  }
  // 🍎 An apple to grab: red, or golden and worth more. It sits on the ground and bobs gently unless Calm is on.
  function apple(g, ax, ay, gold = false, shine = 0) {
    g.save(); g.translate(ax, ay); g.scale(1.7, 1.7);       // big enough to spot next to a pal
    const x = 0, y = 0;
    oval(g, x, y + 1, 6.4, 1.8, "#1b15302e");
    oval(g, x, y - 5.2, 5.4, 5.2, gold ? "#f0b52e" : "#e0453f");
    oval(g, x - 1.4, y - 6.8, 2.1, 1.7, gold ? "#ffeaa0" : "#ff9c9c");
    line(g, [[x, y - 10], [x + .8, y - 13]], "#7a4a2a", 1.1);
    shape(g, [[x + .8, y - 12], [x + 5, y - 13.2], [x + 2.8, y - 10.4]], "#5aa45c");
    if (gold && shine) twinkle(g, x, y - 15, 2.2 + shine, "#fff2b0");
    g.restore();
  }
  // ⚽ Pal ball: a goal frame at each end of the game area, and one big pixel ball.
  // Blue scores in the right goal, Orange in the left one.
  const BALL_GAME_WIDTH = 640, BALL_GOAL_X = 14, BALL_INK = {blue: "#3f7ddc", orange: "#e8832f"};
  function goalFrame(g, x, into, colour) {
    const top = seatFeet(.22), bottom = seatFeet(.98), back = x + into * 10;
    line(g, [[x, top], [x, bottom]], colour, 2.4);       // the posts, and the net behind them
    line(g, [[back, top - 4], [back, bottom + 2]], colour, 2.4);
    line(g, [[x, top], [back, top - 4]], colour, 2.4);
    line(g, [[x, bottom], [back, bottom + 2]], colour, 2.4);
    for (let i = 1; i < 5; i++) {
      const y = top + (bottom - top) * i / 5;
      line(g, [[x + into, y], [back, y - 3]], colour + "66", .8);
    }
  }
  function ball(g, x, feet, roll = 0) {
    const r = 8;
    oval(g, x, feet + 1, 9, 2, "#1b15302e");
    g.save(); g.translate(x, feet - r); g.rotate(roll);
    oval(g, 0, 0, r + 1.2, r + 1.2, "#243b53");
    oval(g, 0, 0, r, r, "#fffdf6");
    shape(g, [[-2.8, -2.6], [2.8, -2.6], [3.6, 1.4], [0, 3.8], [-3.6, 1.4]], "#243b53");
    oval(g, -r * .62, -r * .5, 2.2, 2.2, "#cfdae4");
    oval(g, r * .58, -r * .62, 1.7, 1.7, "#cfdae4");
    oval(g, r * .4, r * .55, 1.5, 1.5, "#cfdae4");
    g.restore();
  }
  // A treasure chest: shut with a gold lock, or open with the lid up and coins shining.
  function chest(g, x, y, open, shine = 0) {
    g.save();
    g.translate(x, y); g.scale(1.3, 1.3); g.translate(-x, -y);
    if (!open) oval(g, x, y, 15, 4.5, `rgba(255, 217, 59, ${.25 + shine * .3})`);
    oval(g, x, y + 1, 11, 2.4, "#1b15302e");
    if (open) {
      box(g, x - 9.5, y - 21, 19, 8, 2.5, "#7a4318");
      box(g, x - 8, y - 19.5, 16, 5, 1.5, "#4a2410");
      oval(g, x, y - 11, 7.5, 2.6, "#ffd93b");
      oval(g, x - 2.5, y - 12, 2, 1.3, "#fff2a6");
    }
    box(g, x - 9, y - 11, 18, 11, 1.5, "#8a4f22");
    box(g, x - 9, y - 11, 18, 2, 0, "#6b3a16");
    box(g, x - 6.5, y - 11, 2, 11, 0, "#e0a92e");
    box(g, x + 4.5, y - 11, 2, 11, 0, "#e0a92e");
    if (!open) {
      box(g, x - 9.5, y - 17, 19, 7, 3, "#a8642c");
      box(g, x - 6.5, y - 17, 2, 7, 0, "#e0a92e");
      box(g, x + 4.5, y - 17, 2, 7, 0, "#e0a92e");
      box(g, x - 2.2, y - 12.5, 4.4, 5, 1, "#ffd93b");
      box(g, x - .6, y - 10.5, 1.2, 1.8, 0, "#6b3a16");
      if (shine > .7) twinkle(g, x + 8, y - 17, 2.4, "#ffffff");
    } else twinkle(g, x + 4, y - 16, 2.4 + shine, "#fff8cf");
    g.restore();
  }
  // 🎨 Draw & guess: the picture on a big easel in the middle of the Park, for everyone to watch it grow.
  function easel(g, x, game) {
    const n = game.grid, cell = 4, side = n * cell, left = Math.round(x - side / 2), top = 30;
    line(g, [[x - 18, top + side], [x - 26, 128]], "#8a5a33", 3);
    line(g, [[x + 18, top + side], [x + 26, 128]], "#8a5a33", 3);
    line(g, [[x, top + side], [x, 120]], "#6b4426", 2.4);
    box(g, left - 4, top - 4, side + 8, side + 8, 2, "#8a5a33");
    box(g, left - 2, top - 2, side + 4, side + 4, 1, "#1b1530");
    box(g, left, top, side, side, 0, "#fffdf6");
    for (let i = 0; i < n * n; i++) {
      const ink = game.board[i];
      if (ink !== ".") box(g, left + i % n * cell, top + Math.floor(i / n) * cell, cell, cell, 0, game.colours["0123456789".indexOf(ink)]);
    }
    box(g, left - 6, top + side + 3, side + 12, 3, 1, "#a8723f");
  }
  // ❄️ A present to find: a box with a ribbon, a different colour in each place.
  const PRESENT_INK = [["#e8294f", "#ffd93b"], ["#2f6fe4", "#ffffff"], ["#35b55a", "#e8294f"], ["#a05ce8", "#ffd93b"], ["#ff8fc7", "#ffffff"]];
  function present(g, x, y, i, shine = 0) {
    const [c, r] = PRESENT_INK[i % PRESENT_INK.length];
    oval(g, x, y + 1, 7, 1.8, "#1b15302e");
    box(g, x - 5, y - 8, 10, 8, 1, c);
    box(g, x - 6, y - 10, 12, 3, 1, c);
    box(g, x - 1, y - 10, 2, 10, 0, r);
    oval(g, x - 2.2, y - 11.4, 2, 1.4, r); oval(g, x + 2.2, y - 11.4, 2, 1.4, r);
    if (shine > .7) twinkle(g, x + 6, y - 11, 2.2, "#ffffff");
  }
  // ⛄ The class snowman, bigger with every snowball: the bottom, then the middle, then the head.
  function snowmanBuilt(g, x, feet, s) {
    oval(g, x, feet + 1, 13 * s, 3 * s, "#9ab4c84a");
    oval(g, x, feet - 9 * s, 10 * s, 9.4 * s, "#d3e2ef"); oval(g, x - .6, feet - 9.6 * s, 9.2 * s, 8.6 * s, "#fffefb");
    oval(g, x, feet - 23 * s, 7.4 * s, 7 * s, "#d3e2ef"); oval(g, x - .5, feet - 23.5 * s, 6.8 * s, 6.4 * s, "#fffefb");
    oval(g, x, feet - 34 * s, 5.6 * s, 5.2 * s, "#d3e2ef"); oval(g, x - .4, feet - 34.4 * s, 5 * s, 4.8 * s, "#fffefb");
    box(g, x - 6 * s, feet - 29 * s, 12 * s, 2.4 * s, 1, "#e8294f"); box(g, x + 2 * s, feet - 29 * s, 3 * s, 7 * s, 1, "#e8294f");
    box(g, x - 6 * s, feet - 40 * s, 12 * s, 1.6 * s, .5, "#3e4a6a"); box(g, x - 4 * s, feet - 46 * s, 8 * s, 6.4 * s, .5, "#3e4a6a");
    oval(g, x - 2 * s, feet - 35 * s, .8 * s, .8 * s, "#27324f"); oval(g, x + 2 * s, feet - 35 * s, .8 * s, .8 * s, "#27324f");
    shape(g, [[x, feet - 34 * s], [x + 6 * s, feet - 33 * s], [x, feet - 32.4 * s]], "#f2a15c");
    [16, 21].forEach(up => oval(g, x, feet - up * s, .9 * s, .9 * s, "#3e4a6a"));
  }
  function snowmanGrowing(g, x, feet, balls, need) {
    const f = balls / need;
    oval(g, x, feet + 1, 15, 3.2, "#9ab4c84a");
    oval(g, x + 9, feet - 1, 5, 2.4, "#eef4fb");      // the pile of snow it's rolled from
    if (!balls) { oval(g, x, feet - 2, 8, 3.4, "#fffefb"); return; }
    const r1 = 3 + 7 * Math.min(1, f * 3);
    oval(g, x, feet - r1, r1 + .8, r1, "#d3e2ef"); oval(g, x - .6, feet - r1 - .5, r1, r1 - .5, "#fffefb");
    if (f <= 1 / 3) return;
    const r2 = 2.4 + 5 * Math.min(1, (f - 1 / 3) * 3), y2 = feet - 2 * r1 - r2 + 2.4;
    oval(g, x, y2, r2 + .6, r2, "#d3e2ef"); oval(g, x - .5, y2 - .4, r2, r2 - .4, "#fffefb");
    if (f <= 2 / 3) return;
    const r3 = 2 + 3.6 * Math.min(1, (f - 2 / 3) * 3), y3 = y2 - r2 - r3 + 2;
    oval(g, x, y3, r3 + .5, r3, "#d3e2ef"); oval(g, x - .4, y3 - .3, r3, r3 - .3, "#fffefb");
    if (f >= .85) { oval(g, x - 1.6, y3 - .6, .7, .7, "#27324f"); oval(g, x + 1.6, y3 - .6, .7, .7, "#27324f"); shape(g, [[x, y3 + .2], [x + 4, y3 + .8], [x, y3 + 1.4]], "#f2a15c"); }
  }
  // 🎄 The ornaments: each one a classmate's drawing, small, on a little gold hook.
  const ORNAMENTS = new Map();
  function ornamentSprite(pal) {
    const key = JSON.stringify(pal);
    if (!ORNAMENTS.has(key)) {
      if (ORNAMENTS.size > 120) ORNAMENTS.clear();
      ORNAMENTS.set(key, trimmed(PalStage.puppet(pal, 1).picture(0, {})));
    }
    return ORNAMENTS.get(key);
  }
  function villageLive(g, state, now) {
    const tree = (state.tree || []).slice(-ORNAMENT_SLOTS.length);
    const star = tree.length >= 10, t = now / 1000;
    tree.forEach((o, n) => {
      const [dx, y] = ORNAMENT_SLOTS[ORNAMENT_ORDER[n]], x = VILLAGE_TREE_X + dx;
      let img = null;
      try { img = ornamentSprite(o.pal); } catch (_) { return; }
      const fit = 11 / Math.max(img.width, img.height), w = img.width * fit, h = img.height * fit;
      line(g, [[x, y - h / 2 - 2], [x, y - h / 2]], "#e0a92e", .6);
      g.drawImage(img, x - w / 2, y - h / 2 + (PalStage.calm ? 0 : Math.sin(t * 1.4 + n) * .5), w, h);
    });
    const glowing = star && !PalStage.calm ? .7 + Math.sin(t * 3) * .3 : star ? 1 : 0;
    if (star) glow(g, VILLAGE_TREE_X, 30, 9, `rgba(255, 217, 59, ${.4 * glowing})`);
    shape(g, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(i => [VILLAGE_TREE_X + Math.sin(i * Math.PI / 5) * (i % 2 ? 2.2 : 5.4), 31 - Math.cos(i * Math.PI / 5) * (i % 2 ? 2.2 : 5.4)]),
          star ? "#ffd93b" : "#d9d4c6");
    const man = state.snowman || {balls: 0, need: 30, built: 0};
    [190, 254, 206, 270, 222, 286].slice(0, Math.min(6, man.built)).forEach(x => snowmanBuilt(g, x, 118, .42));
    if (state.snowmanDone && now - state.snowmanDone < 4000) snowmanBuilt(g, SNOWMAN_X, seatFeet(SNOWMAN_DEEP), .62);
    else snowmanGrowing(g, SNOWMAN_X, seatFeet(SNOWMAN_DEEP), man.balls, man.need);
  }
  // Mist where one place turns into the next.
  function seam(g, x) {
    const fill = g.createLinearGradient(x - 34, 0, x + 34, 0);
    fill.addColorStop(0, "#fffdf600"); fill.addColorStop(.5, "#fffdf6"); fill.addColorStop(1, "#fffdf600");
    g.fillStyle = fill;
    g.fillRect(x - 34, 0, 68, H);
  }
  // A paper sign with a dark edge and a hard shadow, like the buttons on the rest of the page.
  function sign(g, x, label, top = 88, size = 7) {
    g.font = `800 ${size}px ui-rounded, Nunito, system-ui, sans-serif`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    const wide = Math.ceil(g.measureText(label).width) + 10, tall = size + 5;
    const left = Math.round(Math.max(3, Math.min(W - wide - 4, x - wide / 2)));     // the whole sign stays on the screen
    g.fillStyle = "#1b1530";
    g.fillRect(left + 1, top + 1, wide, tall);
    g.fillRect(left, top, wide, tall);
    g.fillStyle = "#fffdf6";
    g.fillRect(left + 1, top + 1, wide - 2, tall - 2);
    g.fillStyle = "#1b1530";
    g.fillText(label, left + wide / 2, top + tall / 2 + .5);
  }

  // ---- What moves: only a little, and none of it in calm mode -------------------------------
  function butterfly(g, x, y, flap, colour) {
    oval(g, x - 1.2 - flap * 1.4, y, .5 + flap * 1.6, 2, colour);
    oval(g, x + 1.2 + flap * 1.4, y, .5 + flap * 1.6, 2, colour);
    box(g, x - .5, y - 1.5, 1, 3.4, 0, "#3e4a6a");
  }
  function butterflies(g, t, colours, spots) {
    spots.forEach(([x, y], i) => butterfly(g, x + Math.sin(t * .5 + i * 2) * 22, y + Math.sin(t * .9 + i) * 7, Math.abs(Math.sin(t * 9 + i)), colours[i % colours.length]));
  }
  // 🌊 A slow fish, with a dark edge and a lighter tail fin.
  function seaFish(g, x, y, dir, colour, fin) {
    oval(g, x, y, 5.8, 3, "#123f5e");
    oval(g, x + dir * .2, y, 5, 2.4, colour);
    shape(g, [[x - dir * 4.6, y], [x - dir * 8, y - 3.6], [x - dir * 8, y + 3.6]], "#123f5e");
    shape(g, [[x - dir * 4.8, y], [x - dir * 7, y - 2.2], [x - dir * 7, y + 2.2]], fin);
    oval(g, x + dir * 2.6, y - .8, .9, .9, "#102a44");
    oval(g, x + dir * 2.8, y - 1.1, .4, .4, "#ffffff");
    shape(g, [[x - dir * .8, y - 2.3], [x + dir * 1.2, y - 4.4], [x + dir * 1.8, y - 2]], fin);
  }
  // A little fish for the school, small enough to read as a shoal.
  function tinyFish(g, x, y, dir, colour) {
    oval(g, x, y, 2.6, 1.3, colour);
    shape(g, [[x - dir * 2, y], [x - dir * 4, y - 1.6], [x - dir * 4, y + 1.6]], colour);
    oval(g, x + dir * 1.2, y - .3, .4, .4, "#143452");
  }
  // A jellyfish, its tentacles drifting behind it.
  function jellyfish(g, x, y, t, calm) {
    glow(g, x, y, 15, "#ff9fc044");
    g.fillStyle = "#ff9fc0";
    g.beginPath(); g.arc(x, y, 7, Math.PI, 0); g.fill();
    g.fillStyle = "#ffd9ea";
    g.beginPath(); g.arc(x - .6, y - .8, 5.6, Math.PI, 0); g.fill();
    for (let i = 0; i < 5; i++) {
      const wob = calm ? 0 : Math.sin(t * 1.5 + i) * 2;
      line(g, [[x - 5.4 + i * 2.7, y], [x - 5.4 + i * 2.7 + wob, y + 10 + (i % 2) * 3]], "#e8a8c0", 1);
    }
    oval(g, x - 2.4, y - 2.2, 1.2, .8, "#ffffffaa");
  }
  // A little sea turtle, paddling slowly.
  function seaTurtle(g, x, y, t, calm) {
    const paddle = calm ? 0 : Math.sin(t * 2.2) * 1.6;
    oval(g, x - 8, y + 2 + paddle, 4.4, 2, "#2f8a68");
    oval(g, x + 7, y + 2 - paddle, 4.4, 2, "#2f8a68");
    oval(g, x, y, 8.4, 5.4, "#1f5f55");
    oval(g, x, y - 1, 7.2, 4.2, "#3f9f72");
    oval(g, x - 2.4, y - 2, 2.2, 1.4, "#8ee0a0");
    oval(g, x + 2.2, y - 1, 1.8, 1.2, "#6fcf8e");
    oval(g, x + 8.2, y - 2, 2.8, 2.2, "#7fcf8e");
    oval(g, x + 9.6, y - 2.7, .5, .5, "#143452");
  }
  // 🌿 A seaweed stem that bends in the water. In calm mode the clock is 0, so it holds still.
  function seaweed(g, x, feet, tall, colour, light, phase, t, calm) {
    const points = [];
    for (let i = 0; i <= 6; i++) {
      const f = i / 6, sway = calm ? 0 : Math.sin(t * 1.1 + phase + f * 2.6) * (1 + f * 4);
      points.push([x + sway, feet - tall * f]);
    }
    line(g, points, "#1f5f55", 3);
    line(g, points, colour, 1.6);
    for (let i = 1; i < 6; i++) {
      const [lx, ly] = points[i], side = i % 2 ? 1 : -1;
      oval(g, lx + side * (2.6 + i * .25), ly - .6, 2.4, 1.2, light);
    }
  }
  // Everything that moves under the sea. Called for the sea even in calm mode, with t = 0,
  // so the fish and seaweed stay in the picture but stop moving.
  function seaLife(g, t, calm) {
    const time = calm ? 0 : t;
    for (let i = 0; i < 3; i++) {
      const x = 52 + i * 104 + (calm ? 0 : Math.sin(time * .22 + i * 1.4) * 8);
      g.globalAlpha = .10;
      shape(g, [[x, 0], [x + 26, 0], [x + 38 + (calm ? 0 : Math.sin(time * .3 + i) * 5), 120], [x + 4, 120]], "#d6fbff");
      g.globalAlpha = 1;
    }
    [[18, 166, 48, "#3f9f72", "#8ee0a0", .2], [38, 178, 32, "#2f8a68", "#6fcf8e", 1.3],
     [62, 180, 24, "#2f8a68", "#6fcf8e", 2.4], [286, 172, 42, "#3f9f72", "#8ee0a0", 2.1],
     [306, 164, 34, "#2f8a68", "#6fcf8e", .8], [238, 178, 26, "#3f9f72", "#8ee0a0", 2.8],
     [272, 180, 20, "#2f8a68", "#6fcf8e", 1.7]].forEach(([x, feet, tall, colour, light, phase]) =>
      seaweed(g, x, feet, tall, colour, light, phase, time, calm));
    [[28, 70, 1, "#ff9a6a", "#ffd0a8"], [212, 52, -1, "#ff8fc7", "#ffd9ea"], [150, 94, 1, "#7ab8ff", "#d6f4ff"]].forEach(([fx, fy, dir, colour, fin], i) => {
      const travel = (time * (4.5 + i * 1.4) + i * 90) % (W + 60);
      const x = calm ? fx : dir > 0 ? travel - 30 : W + 30 - travel;
      const y = fy + (calm ? 0 : Math.sin(time * .6 + i * 2) * 3);
      seaFish(g, x, y, dir, colour, fin);
    });
    // a little school, drifting together
    [[142, 40], [152, 45], [147, 51], [160, 37], [165, 49], [137, 46]].forEach(([sx, sy], i) => {
      const x = calm ? sx : (sx + time * (3.2 + (i % 3) * .7) + i * 7) % (W + 30) - 12;
      const y = sy + (calm ? 0 : Math.sin(time * .9 + i * 1.7) * 2.2);
      tinyFish(g, x, y, 1, i % 2 ? "#8fd0c8" : "#7ab8ff");
    });
    seaTurtle(g, calm ? 206 : 206 + Math.sin(time * .22) * 14, calm ? 30 : 30 + Math.sin(time * .4) * 4, time, calm);
    jellyfish(g, calm ? 238 : 238 + Math.sin(time * .3) * 22, calm ? 55 : 55 + Math.sin(time * .55) * 5, time, calm);
    const n = calm ? 4 : 14;
    for (let i = 0; i < n; i++) {
      const p = calm ? .14 + i * .21 : (time * .13 + i / n) % 1;
      const x = 26 + (i * 47 + 17) % 270 + (calm ? 0 : Math.sin(time * .8 + i) * 4);
      const y = 168 - p * 150, r = 1.5 + (i % 3) * .6;
      oval(g, x, y, r, r, "#d6f4ffdd");
      oval(g, x - r * .35, y - r * .35, r * .4, r * .4, "#ffffff");
    }
  }
  function drift(g, scene, t) {
    if (scene === "village") {
      for (let i = 0; i < 26; i++) {
        const fall = (t * (9 + i % 5 * 2) + i * 47) % 200 - 10;
        oval(g, (i * 53 + Math.sin(t * .8 + i) * 8) % W, fall, .9, .9, "#ffffff");
      }
    }
    if (scene === "park" || scene === "wedding" || scene === "beach" || scene === "snowy") {
      [[.012, 28, 1.1], [.008, 48, .8], [.016, 18, .7]].forEach(([speed, y, s], i) => {
        cloud(g, ((t * 1000 * speed + i * 137) % 400) - 40, y, s, scene === "wedding" ? "#fff7f2" : "#fffdf6", scene === "wedding" ? "#f6d6e2" : "#d5e6f0");
      });
    }
    if (scene === "park") {
      // a hot air balloon, far away
      const bx = ((t * 3 + 60) % 380) - 30, by = 58 + Math.sin(t * .4) * 3;
      oval(g, bx, by, 7, 8, "#ff8fa8"); oval(g, bx, by, 3, 8, "#ffd27a"); box(g, bx - 2, by + 10, 4, 3, .6, "#a9835a");
      line(g, [[bx - 4, by + 6], [bx - 2, by + 10]], "#8a6a4a", .5); line(g, [[bx + 4, by + 6], [bx + 2, by + 10]], "#8a6a4a", .5);
      // the fountain splashing
      for (let i = 0; i < 6; i++) {
        const p = (t * .9 + i / 6) % 1, d = i % 2 ? 1 : -1;
        oval(g, 160 + d * p * 13, 93 - Math.sin(p * 2.2) * 5 + p * p * 20, .8, .8, "#eafafc");
      }
      butterflies(g, t, ["#ffd27a", "#ff9fb5", "#c7b4f0"], [[70, 134], [230, 142], [150, 150]]);
    }
    if (scene === "wedding") {
      butterflies(g, t, ["#fffdf6", "#ff9fb5"], [[90, 140], [236, 136]]);
      for (let i = 0; i < 10; i++) {
        const fall = (t * (5 + i % 4) + i * 41) % 150;
        oval(g, 120 + (i * 53) % 90 + Math.sin(t + i) * 5, 40 + fall, 1.4, .9, i % 2 ? "#ff9fb5" : "#fff6fb");
      }
    }
    if (scene === "beach") {
      for (let i = 0; i < 4; i++) oval(g, ((t * 6 + i * 91) % 340) - 10, 108 + Math.sin(t + i) * 3 + i * 2, 18, .8, "#ffffffa0");
      for (let i = 0; i < 2; i++) {
        const x = ((t * (9 + i * 3) + i * 170) % 380) - 30, y = 44 + i * 16 + Math.sin(t * .8 + i) * 4, up = Math.sin(t * 5 + i) * 2.4;
        line(g, [[x - 5, y - up], [x, y], [x + 5, y - up]], "#fffdf6", 1.2);
      }
    }
    if (scene === "snowy") {
      for (let i = 0; i < 4; i++) {
        const p = (t * .22 + i / 4) % 1;
        g.globalAlpha = (1 - p) * .8;
        oval(g, 271.5 + Math.sin(p * 5 + i) * 3 + p * 6, 74 - p * 26, 2 + p * 3.4, 1.6 + p * 2.6, "#ffffff");
        g.globalAlpha = 1;
      }
      for (let i = 0; i < 46; i++) {
        oval(g, ((i * 53 + Math.sin(t * .6 + i) * 8) % W + W) % W, ((t * (7 + i % 6) + i * 37) % 190) - 6, .8 + (i % 3) * .3, .8 + (i % 3) * .3, "#ffffff");
      }
    }
    if (scene === "night") {
      // the fire flickering
      const lick = Math.sin(t * 9) * 2, lean = Math.sin(t * 5) * 1.6;
      shape(g, [[153, 119], [156, 108], [160 + lean, 99 - lick], [164, 108], [167, 119]], "#ffa95c");
      shape(g, [[156, 119], [160 + lean * .6, 106 + lick], [164, 119]], "#ffe39a");
      for (let i = 0; i < 4; i++) {
        const p = (t * .5 + i / 4) % 1;
        g.globalAlpha = 1 - p;
        oval(g, 160 + Math.sin(p * 6 + i * 2) * 7, 100 - p * 30, .8, .8, "#ffd27a");
        g.globalAlpha = 1;
      }
      // a shooting star now and then
      const s = (t % 11) / .9;
      if (s < 1) {
        const x = 110 + s * 120, y = 12 + s * 40;
        g.globalAlpha = 1 - s;
        line(g, [[x - 18, y - 6], [x, y]], "#fff8d8", 1); twinkle(g, x, y, 2, "#ffffff");
        g.globalAlpha = 1;
      }
      for (let i = 0; i < 16; i++) {
        const on = .35 + .65 * Math.abs(Math.sin(t * .9 + i * 1.7));
        const x = (i * 83 + Math.sin(t * .4 + i) * 16 + W) % W, y = 112 + (i * 31) % 52 + Math.cos(t * .5 + i * 2) * 6;
        g.globalAlpha = on;
        glow(g, x, y, 6, "#fff2a0cc");
        oval(g, x, y, .9, .9, "#fff8c8");
        g.globalAlpha = 1;
      }
    }
    if (scene === "candy") for (let i = 0; i < 7; i++) {
      const p = (t * (.05 + (i % 3) * .015) + i / 7) % 1;
      g.globalAlpha = Math.min(1, (1 - p) * 2.5) * .8;
      heart(g, (i * 47 + 22) % W + Math.sin(t + i * 2) * 5, 104 - p * 80, .8 + (i % 2) * .3, ["#ff8fa8", "#fffafc", "#b9a4e8"][i % 3]);
      g.globalAlpha = 1;
    }
    if (scene === "space") {
      for (let i = 0; i < 12; i++) {
        g.globalAlpha = .4 + .6 * Math.abs(Math.sin(t * 1.3 + i * 2.1));
        oval(g, (i * 113 + 40) % W, (i * 59 + 11) % 100, 1.2, 1.2, "#ffffff");
        g.globalAlpha = 1;
      }
      // a flying saucer going by
      const ux = ((t * 7 + 120) % 420) - 50, uy = 66 + Math.sin(t * 1.1) * 5;
      g.fillStyle = "#b5f2ee"; g.beginPath(); g.arc(ux, uy - 1, 4.4, Math.PI, 0); g.fill();
      oval(g, ux, uy, 10, 2.8, "#c7b4f0"); oval(g, ux, uy + .8, 10, 1.8, "#9a86d8");
      [-6, 0, 6].forEach((dx, i) => oval(g, ux + dx, uy + .4, 1, 1, Math.sin(t * 6 + i * 2) > 0 ? "#ffe39a" : "#ff8fa8"));
    }
  }
  // A pool of light on whoever is doing their My Move.
  function spotlight(g, x, feet) {
    g.fillStyle = "rgba(255, 244, 196, .34)";
    g.beginPath();
    g.moveTo(x - 7, 0); g.lineTo(x + 7, 0); g.lineTo(x + 31, feet + 3); g.lineTo(x - 31, feet + 3);
    g.closePath(); g.fill();
    oval(g, x, feet + 2, 33, 7, "rgba(255, 244, 196, .62)");
  }

  // ---- Keeping one canvas painted --------------------------------------------------------
  /** Paints `canvas` until the function it returns is called. `read()` gives the
      stage's state, so it can follow the scene and the pals. */
  function start(canvas, read) {
    const g = canvas.getContext("2d"), kept = {};
    const small = document.createElement("canvas"), fine = document.createElement("canvas");
    small.width = W; small.height = H;
    fine.width = W * FINE; fine.height = H * FINE;
    const lo = small.getContext("2d"), ink = fine.getContext("2d");
    let frame = 0, last = 0, stopped = false, ballDrawn = null;     // the ball eases towards the server's spot
    // The canvas's size, kept by the browser as it changes, so painting never has to stop and measure the page.
    let boxW = canvas.getBoundingClientRect().width, boxH = canvas.getBoundingClientRect().height;
    const sizer = new ResizeObserver(([e]) => { boxW = e.contentRect.width; boxH = e.contentRect.height; });
    sizer.observe(canvas);
    const homeArt = {};
    function artFor(scene, home, n) {
      if (scene === "home") {     // each room is painted again only when something in it changes
        home = home || {};
        const key = JSON.stringify([(home.rooms || [])[n], (home.rooms || []).length, roomItems(home, n)]);
        if (!homeArt[n] || homeArt[n].key !== key) homeArt[n] = {key, art: crisp(W, H, ink => homeRoom(ink, home, n))};
        return homeArt[n].art;
      }
      if (!kept[scene]) kept[scene] = bands(crisp(W, H, ink => {
        (PLACES[scene] || PLACES.park)(ink);
        const ring = (x, deep, inside, edge) => {
          oval(ink, x, seatFeet(deep) + 1, 13, 3.2, inside);
          ink.strokeStyle = edge;
          ink.lineWidth = 1.6;     // thick enough to stay one unbroken ring of pixels
          ink.beginPath();
          ink.ellipse(x, seatFeet(deep) + 1, 13, 3.2, 0, 0, 7);
          ink.stroke();
        };
        for (const [x, deep] of SEATS[scene]) ring(x, deep, "#fff6c866", "#f5b83d");
        for (const [x, deep] of TOYS[scene]) ring(x, deep, "#ffe0ec66", "#ff5fa2");
        if (scene === "beach") ring(FISH_X, 0, "#d6f4f866", "#2f7fd0");
        if (scene === "village") { ring(SNOWMAN_X, SNOWMAN_DEEP, "#d6f4f866", "#2f7fd0"); ring(VILLAGE_TREE_X, .1, "#fff6c866", "#f5b83d"); }
      }));
      return kept[scene];
    }
    function paint(now) {
      if (stopped) return;
      frame = requestAnimationFrame(paint);
      if (!boxW || now - last < 33) return;
      last = now;
      const ratio = Math.min(1.5, devicePixelRatio || 1), w = Math.round(boxW * ratio), h = Math.round(boxH * ratio);
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      const state = read(), places = state.places || ["park"], cam = Math.round(state.camX || 0), first = Math.floor(cam / W);
      const showing = [first, first + 1].filter(i => places[i]);
      const playing = state.game && ["hiding", "playing"].includes(state.game.phase), hiding = playing && state.game.kind === "hide";
      const covers = (state.cover || []).filter(c => c.x - cam > -40 && c.x - cam < W + 40).sort((a, b) => a.y - b.y);
      const inside = places[0] === "home", race = playing && state.game.kind === "race" ? state.game : null;
      const locked = !inside && places.filter(p => p !== "village").length < Object.keys(PLACES).length - 1 && !places.includes("village")
        && Math.abs(places.length * W - cam - W) < 40;
      const edge = playing && cam > 320 - W && 640 - cam >= 0 && 640 - cam <= W ? 640 - cam : null;
      // 1. The places themselves, already in pixels.
      lo.clearRect(0, 0, W, H);
      for (const i of showing) lo.drawImage(artFor(places[i], state.home, i), i * W - cam, 0);
      // 2. What moves or changes, painted fine and then turned into pixels.
      ink.setTransform(1, 0, 0, 1, 0, 0);
      ink.clearRect(0, 0, fine.width, fine.height);
      ink.scale(FINE, FINE);
      for (const i of showing) {
        ink.save();
        ink.beginPath(); ink.rect(i * W - cam, 0, W, H); ink.clip();
        ink.translate(i * W - cam, 0);
        if (!PalStage.calm) drift(ink, places[i], now / 1000);
        if (places[i] === "sea") seaLife(ink, now / 1000, PalStage.calm);
        if (state.found) GEMS[places[i]].forEach(([x, deep], n) => {
          if (state.found.has(places[i] + n)) return;
          oval(ink, x, seatFeet(deep) + 1, 5, 1.4, "#1b15302e");
          gem(ink, x, seatFeet(deep) - 6 + (PalStage.calm ? 0 : Math.sin(now / 300 + n) * 1.5), PalStage.calm ? 0 : Math.abs(Math.sin(now / 700 + n * 2)));
        });
        for (const c of state.chests || []) if (c.place === places[i]) chest(ink, c.x, seatFeet(c.deep), c.open, PalStage.calm ? 0 : Math.abs(Math.sin(now / 600 + c.x)));
        if (places[i] === "village") villageLive(ink, state, now);
        (state.presents || []).forEach((p, n) => {
          if (p.place === places[i] && !p.found) present(ink, p.x, seatFeet(p.deep) + (PalStage.calm ? 0 : Math.sin(now / 400 + n) * .8), n, PalStage.calm ? 0 : Math.abs(Math.sin(now / 650 + n * 3)));
        });
        ink.restore();
      }
      if (!inside) for (let i = 1; i < places.length; i++) if (Math.abs(i * W - cam - W / 2) < W / 2 + 40) seam(ink, i * W - cam);
      if (locked) seam(ink, places.length * W - cam);
      const clock = performance.now();
      for (const m of state.room || []) if (m.spotUntil > clock) spotlight(ink, m.x - cam, PalStage.groundOf(m));
      for (const c of covers) coverGround(ink, c, cam, hiding);
      if (edge !== null) line(ink, [[edge - 2, 110], [edge - 2, H]], "#b76e43", 3);
      if (race) for (let i = 0; i < 12; i++) box(ink, race.finish - cam + i % 2 * 4, PalStage.GROUND_TOP - 8 + i * 5, 4, 5, 0, i % 4 < 2 ? "#1b1530" : "#fffdf6");
      if (playing && state.game.kind === "draw" && state.game.board) easel(ink, 160 - cam, state.game);
      if (playing && state.game.kind === "apples") for (const a of state.game.apples || []) {
        const bob = PalStage.calm ? 0 : Math.sin(now / 360 + a.id) * 1.2;
        apple(ink, a.x - cam, seatFeet(a.y) + bob, a.gold, PalStage.calm ? 0 : Math.abs(Math.sin(now / 520 + a.id)));
      }
      lo.drawImage(fine, 0, 0, W, H);
      // 3. The hiding places, standing on top of all that.
      for (const c of covers) cutCover(lo, c, cam);
      // The ⚽ ball and its goals stay on top of the scenery, so they are never lost behind a bush.
      if (playing && state.game.kind === "ball") {
        goalFrame(lo, BALL_GOAL_X - cam, 1, BALL_INK.orange);       // Orange scores on the left
        goalFrame(lo, BALL_GAME_WIDTH - BALL_GOAL_X - cam, -1, BALL_INK.blue);   // Blue scores on the right
        const b = state.game.ball;
        if (b) {
          const tx = b.x, ty = seatFeet(b.y);
          if (!ballDrawn || Math.hypot(tx - ballDrawn.x, ty - ballDrawn.y) > 120) ballDrawn = {x: tx, y: ty, at: now};
          else {
            const dt = Math.max(0, Math.min(.1, (now - ballDrawn.at) / 1000));
            ballDrawn.at = now;
            const ease = 1 - Math.exp(-14 * dt);       // the server sends the ball 5 times a second: ease in between
            ballDrawn.x += (tx - ballDrawn.x) * ease;
            ballDrawn.y += (ty - ballDrawn.y) * ease;
          }
          ball(lo, ballDrawn.x - cam, ballDrawn.y, PalStage.calm ? 0 : ballDrawn.x / 10);
        }
      }
      // 4. Onto the screen in big pixels, with the words kept sharp enough to read.
      g.setTransform(1, 0, 0, 1, 0, 0);
      g.imageSmoothingEnabled = false;
      g.clearRect(0, 0, w, h);
      g.drawImage(small, 0, 0, w, h);
      g.scale(w / W, h / H);
      const rooms = inside && state.home && state.home.rooms, label = i => (rooms ? rooms[i].name : PLACE_LABEL[places[i]]);
      for (let i = 1; i < places.length; i++) if (Math.abs(i * W - cam - W / 2) < W / 2 + 40) sign(g, i * W - cam, `${label(i - 1)} ← → ${label(i)}`, rooms ? 22 : 88);
      if (rooms && state.home.mine && state.home.more && Math.abs(places.length * W - cam - W) < 40) sign(g, places.length * W - cam - 70, "🔨 Build more rooms in the 🛍️ Shop!", 22);
      if (locked) sign(g, places.length * W - cam - 52, "🔒 Fill the party meter!");
      const v = places.indexOf("village");
      const onScreen = x => x > 30 && x < W - 30;          // a sign only over something you can see
      if (v >= 0 && !inside) {
        const man = state.snowman || {balls: 0, need: 30}, sx = v * W - cam + SNOWMAN_X, tx = v * W - cam + VILLAGE_TREE_X;
        if (onScreen(sx)) sign(g, sx, `⛄ ${man.balls} of ${man.need}: click to roll!`, 90, 6);
        if (onScreen(tx)) sign(g, tx, `🎄 Class tree: ${(state.tree || []).length}`, 6, 6);
      }
      if (edge !== null && !race) sign(g, edge - 48, "Play area ends here", 104);     // under the sign for the next place
      if (race) {
        sign(g, W / 2, race.light === "red" ? "🔴 RED LIGHT: FREEZE!" : "🟢 GREEN LIGHT: RUN!", 8, 11);
        if (race.finish - cam > 0 && race.finish - cam < W) sign(g, race.finish - cam, "🏁 Finish", 104);
      }
      if (playing && state.game.kind === "ball") {
        const lx = BALL_GOAL_X - cam, rx = BALL_GAME_WIDTH - BALL_GOAL_X - cam;
        if (onScreen(lx + 30)) sign(g, lx + 34, "← Orange goal", 70, 6);
        if (onScreen(rx - 30)) sign(g, rx - 34, "Blue goal →", 70, 6);
      }
      if (hiding) for (const c of covers) sign(g, Math.round(c.x) - cam, c.name, Math.min(coverFeet(c) + 7, H - 13), 6);     // the name stays on the screen
      // On the class screen, each chest says what it asks for and how many have opened it today.
      if (!playing) for (const c of state.chests || []) {
        const i = places.indexOf(c.place), x = i * W + c.x - cam;
        if (i >= 0 && "count" in c && x > 0 && x < W) sign(g, x, `🧰 ${c.job}${c.count ? ` ✅ ${c.count}` : ""}`, seatFeet(c.deep) - 66, 6);     // above a pal standing at it
      }
      // On a student's screen, a shut chest says it can be opened with code.
      const me = (state.room || []).find(m => m.seat === state.you);
      if (!playing) for (const c of state.chests || []) {
        const i = places.indexOf(c.place), x = i * W + c.x - cam;
        if (me && Math.abs(me.x - i * W - c.x) < 34) continue;     // standing at it: the panel on the right says it all
        if (i >= 0 && !("count" in c) && !c.open && x > 0 && x < W) sign(g, x, "🧰 Code me open!", seatFeet(c.deep) - 30 + (PalStage.calm ? 0 : Math.round(Math.sin(now / 400) * 1.5)), 6);
      }
    }
    frame = requestAnimationFrame(paint);
    return () => { stopped = true; cancelAnimationFrame(frame); sizer.disconnect(); };
  }

  return {start, seatAt, toyAt, gemAt, chestAt, presentAt, villageAt, coverAt, cutCover, coverHigh, furniturePicture, roomPicture, furnitureAt, lookColour, doorAt, fishAt, PLACES: Object.keys(PLACES)};
})();
