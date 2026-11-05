// Pixel Pals: the art itself, with no page in it. A frame is an array with one
// number per square, left to right and top to bottom: -1 is empty and anything
// else is a place in the drawing's palette.
"use strict";

const PixelArt = (() => {
  const LETTERS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";

  // Eight across and four down on the page. Five skin tones are in here because
  // most of what gets drawn is people.
  const PALETTE = [
    "#1b1530", "#55506a", "#9a96a8", "#d3d0dc", "#ffffff", "#ffe2c8", "#f1c27d", "#c68642",
    "#8d5524", "#4a2c1d", "#b3123c", "#e8294f", "#ff7a7a", "#ff8fc7", "#ffc9e3", "#c2258c",
    "#ff8a2a", "#ffc266", "#d9a21b", "#ffd93b", "#fff2a6", "#14633a", "#2fa84f", "#8ee06b",
    "#0e8f83", "#35d0bd", "#a5f2e4", "#1f2a6b", "#2f6fe4", "#7ab8ff", "#7a3fe4", "#c5a3ff",
  ];
  const INK = 0, WHITE = 4;

  // Colouring-book outlines to start from: "k" is ink and "w" is white.
  const STARTERS = {
    Bean: [
      "................",
      ".....kkkkkk.....",
      "...kkwwwwwwkk...",
      "..kwwwwwwwwwwk..",
      "..kwwwwwwwwwwk..",
      ".kwwwkwwwwkwwwk.",
      ".kwwwkwwwwkwwwk.",
      ".kwwwwwwwwwwwwk.",
      ".kwwwkwwwwkwwwk.",
      ".kwwwwkkkkwwwwk.",
      ".kwwwwwwwwwwwwk.",
      ".kwwwwwwwwwwwwk.",
      "..kwwwwwwwwwwk..",
      "...kkkwwwwkkk...",
      "..kwwk.kk.kwwk..",
      "...kk......kk...",
    ],
    Cat: [
      "................",
      "..kk........kk..",
      "..kwk......kwk..",
      "..kwwkkkkkkwwk..",
      "..kwwwwwwwwwwk..",
      "..kwwwwwwwwwwk..",
      "..kwkwwwwwwkwk..",
      "..kwkwwwwwwkwk..",
      "..kwwwwkkwwwwk..",
      "...kwwwwwwwwk...",
      "...kkkkkkkkkk...",
      "...kwwwwwwwwk...",
      "...kwwwwwwwwk...",
      "...kwkwwwwkwk...",
      "...kwkkkkkkwk...",
      "...kk......kk...",
    ],
    Bunny: [
      "....kk....kk....",
      "...kwwk..kwwk...",
      "...kwwk..kwwk...",
      "...kwwk..kwwk...",
      "...kwwk..kwwk...",
      "...kwwkkkkwwk...",
      "..kwwwwwwwwwwk..",
      "..kwwwwwwwwwwk..",
      "..kwwkwwwwkwwk..",
      "..kwwkwwwwkwwk..",
      "..kwwwwkkwwwwk..",
      "..kwwwwwwwwwwk..",
      "...kkwwwwwwkk...",
      "...kwwwwwwwwk...",
      "...kwkkkkkkwk...",
      "...kk......kk...",
    ],
    Kid: [
      ".....kkkkkk.....",
      "....kwwwwwwk....",
      "...kwwwwwwwwk...",
      "...kwkwwwwkwk...",
      "...kwkwwwwkwk...",
      "...kwwwwwwwwk...",
      "...kwwkkkkwwk...",
      "....kwwwwwwk....",
      ".....kkkkkk.....",
      "...kkkwwwwkkk...",
      "..kwwkwwwwkwwk..",
      "..kkkkwwwwkkkk..",
      ".....kwwwwk.....",
      ".....kwkkwk.....",
      ".....kwkkwk.....",
      ".....kk..kk.....",
    ],
  };

  // Stamps: x is the colour you've chosen, k is ink, w is white, and the rest are
  // their own colour. Most are small enough for a Small canvas.
  const STAMPS = {
    "Dot eye": ["kk", "kk"],
    "Shiny eye": ["wkk", "kkk", "kkk"],
    "Big eye": [".kkk.", "kwwkk", "kwwkk", "kkkkk", ".kkk."],
    "Happy eye": [".kk.", "k..k"],
    "Sleepy eye": ["kkkk"],
    "Lashes": ["k...k", ".kkk.", ".kkk."],
    "Smile": ["k...k", ".kkk."],
    "Big smile": ["kkkkk", "krrrk", ".kkk."],
    "Oh!": [".k.", "k.k", ".k."],
    "Cat mouth": ["k.k.k", ".k.k."],
    "Blush": ["ppp"],
    "Heart": [".xx.xx.", "xxxxxxx", "xxxxxxx", ".xxxxx.", "..xxx..", "...x..."],
    "Tiny heart": ["x.x", "xxx", ".x."],
    "Star": ["...x...", "..xxx..", "xxxxxxx", ".xxxxx.", ".xx.xx.", "x.....x"],
    "Sparkle": ["..w..", ".www.", "wwwww", ".www.", "..w.."],
    "Flower": [".x.x.", "xxxxx", ".xyx.", "xxxxx", ".x.x."],
    "Bow": ["xx...xx", "xxx.xxx", "xxxyxxx", "xxx.xxx", "xx...xx"],
    "Crown": ["y..y..y", "yy.y.yy", "yyyyyyy", "yrybyry"],
    "Glasses": ["kkkkk.kkkkk", "k...kkk...k", "k...k.k...k", "kkkkk.kkkkk"],
    "Note": ["..kkk", "..k.k", "..k..", "kkk..", "kkk.."],
  };
  const STAMP_INK = {k: "#1b1530", w: "#ffffff", p: "#ff8fc7", r: "#e8294f", y: "#ffd93b", b: "#2f6fe4"};

  function blank(size) { return new Array(size * size).fill(-1); }

  function encode(frame) {
    return Array.from(frame, n => n < 0 ? "." : LETTERS[n]).join("");
  }
  function decode(text) {
    return Array.from(text, ch => ch === "." ? -1 : LETTERS.indexOf(ch));
  }
  function fromRows(rows) {
    return Array.from(rows.join(""), ch => ch === "k" ? INK : ch === "w" ? WHITE : -1);
  }

  // ---- Shapes: each hands back [x, y] squares, and the caller decides what
  // they mean (brushes, mirroring, the edges of the canvas). --------------------
  function line(x0, y0, x1, y1) {
    const out = [], dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
    const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    let err = dx + dy, x = x0, y = y0;
    for (;;) {
      out.push([x, y]);
      if (x === x1 && y === y1) return out;
      const e2 = 2 * err;
      if (e2 >= dy) { err += dy; x += sx; }
      if (e2 <= dx) { err += dx; y += sy; }
    }
  }

  function box(x0, y0, x1, y1, solid) {
    const out = [];
    const [left, right] = [Math.min(x0, x1), Math.max(x0, x1)];
    const [top, bottom] = [Math.min(y0, y1), Math.max(y0, y1)];
    for (let y = top; y <= bottom; y++) for (let x = left; x <= right; x++) {
      if (solid || x === left || x === right || y === top || y === bottom) out.push([x, y]);
    }
    return out;
  }

  // The circle that fits inside the box between two corners. An outline square
  // is an inside square with a neighbour outside.
  function circle(x0, y0, x1, y1, solid) {
    const [left, right] = [Math.min(x0, x1), Math.max(x0, x1)];
    const [top, bottom] = [Math.min(y0, y1), Math.max(y0, y1)];
    const cx = (left + right) / 2, cy = (top + bottom) / 2;
    const rx = (right - left + 1) / 2, ry = (bottom - top + 1) / 2;
    const inside = (x, y) => ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1;
    const out = [];
    for (let y = top; y <= bottom; y++) for (let x = left; x <= right; x++) {
      if (!inside(x, y)) continue;
      if (solid || !inside(x - 1, y) || !inside(x + 1, y) || !inside(x, y - 1) || !inside(x, y + 1)) {
        out.push([x, y]);
      }
    }
    return out;
  }

  // Every square joined to (x, y) by squares of the same colour.
  function flood(frame, size, x, y) {
    const target = frame[y * size + x], seen = new Set([y * size + x]), todo = [[x, y]], out = [];
    while (todo.length) {
      const [cx, cy] = todo.pop();
      out.push([cx, cy]);
      for (const [nx, ny] of [[cx - 1, cy], [cx + 1, cy], [cx, cy - 1], [cx, cy + 1]]) {
        const at = ny * size + nx;
        if (nx < 0 || ny < 0 || nx >= size || ny >= size || seen.has(at) || frame[at] !== target) continue;
        seen.add(at);
        todo.push([nx, ny]);
      }
    }
    return out;
  }

  function flip(frame, size) {
    return frame.map((_, i) => frame[(i - i % size) + size - 1 - i % size]);
  }

  // Slide the picture along. What falls off one side comes back on the other,
  // so nothing is lost.
  function shift(frame, size, dx, dy) {
    const out = blank(size);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      out[((y + dy + size) % size) * size + (x + dx + size) % size] = frame[y * size + x];
    }
    return out;
  }

  // A quarter turn clockwise.
  function turn(frame, size) {
    const out = blank(size);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      out[x * size + size - 1 - y] = frame[y * size + x];
    }
    return out;
  }

  // The empty squares that touch the drawing, which is where an outline goes.
  function outline(frame, size) {
    const out = [];
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      if (frame[y * size + x] >= 0) continue;
      const near = [[x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]];
      if (near.some(([nx, ny]) => nx >= 0 && ny >= 0 && nx < size && ny < size && frame[ny * size + nx] >= 0)) {
        out.push(y * size + x);
      }
    }
    return out;
  }

  // A colour one step darker or lighter. Pixel artists lean shadows towards blue
  // and highlights towards yellow, which looks far richer than adding black.
  function shade(hex, way) {
    const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
    const hi = Math.max(r, g, b), lo = Math.min(r, g, b), d = hi - lo;
    let h = 0, l = (hi + lo) / 2;
    let s = d ? d / (1 - Math.abs(2 * l - 1)) : 0;
    if (d) h = hi === r ? ((g - b) / d + 6) % 6 : hi === g ? (b - r) / d + 2 : (r - g) / d + 4;
    h *= 60;
    const aim = way < 0 ? 250 : 55, gap = ((aim - h + 540) % 360) - 180;
    if (s > .05) h = (h + Math.max(-14, Math.min(14, gap)) + 360) % 360;
    l = Math.max(.03, Math.min(.97, l + way * .13));
    s = Math.min(1, s + (way < 0 ? .06 : 0));
    const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs(h / 60 % 2 - 1)), m = l - c / 2;
    const [a, e, f] = [[c, x, 0], [x, c, 0], [0, c, x], [0, x, c], [x, 0, c], [c, 0, x]][Math.floor(h / 60) % 6];
    return "#" + [a, e, f].map(v => Math.round((v + m) * 255).toString(16).padStart(2, "0")).join("");
  }

  // ---- GIF: an animated picture needs its own file format, and browsers can
  // only read this one, not write it. ---------------------------------------
  function lzw(pixels, minSize) {
    const clear = 1 << minSize, end = clear + 1, bytes = [];
    let table = new Map(), next = end + 1, width = minSize + 1, held = 0, bits = 0;
    const emit = code => {
      held |= code << bits;
      bits += width;
      while (bits >= 8) { bytes.push(held & 255); held >>>= 8; bits -= 8; }
    };
    emit(clear);
    let run = pixels[0];
    for (let i = 1; i < pixels.length; i++) {
      const key = run * 256 + pixels[i], known = table.get(key);
      if (known !== undefined) { run = known; continue; }
      emit(run);
      if (next === 4096) {
        emit(clear);
        table = new Map();
        next = end + 1;
        width = minSize + 1;
      } else {
        if (next >= 1 << width) width++;
        table.set(key, next++);
      }
      run = pixels[i];
    }
    emit(run);
    emit(end);
    if (bits) bytes.push(held & 255);
    return bytes;
  }

  function gif(frames, size, scale, palette, fps) {
    let depth = 2;                                  // colour 0 is see-through
    while (1 << depth < palette.length + 1) depth++;
    const px = size * scale, delay = Math.round(100 / fps), out = [];
    const word = n => out.push(n & 255, n >> 8);
    out.push(...Array.from("GIF89a", ch => ch.charCodeAt(0)));
    word(px); word(px);
    out.push(0x80 | (depth - 1), 0, 0);
    for (let i = 0; i < 1 << depth; i++) {
      const hex = palette[i - 1] || "#000000";
      out.push(parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16));
    }
    out.push(0x21, 0xff, 11, ...Array.from("NETSCAPE2.0", ch => ch.charCodeAt(0)), 3, 1, 0, 0, 0);
    for (const frame of frames) {
      out.push(0x21, 0xf9, 4, 0b1001, delay & 255, delay >> 8, 0, 0);   // wipe between frames
      out.push(0x2c); word(0); word(0); word(px); word(px); out.push(0);
      const pixels = new Array(px * px);
      for (let y = 0; y < px; y++) for (let x = 0; x < px; x++) {
        pixels[y * px + x] = frame[Math.floor(y / scale) * size + Math.floor(x / scale)] + 1;
      }
      const data = lzw(pixels, depth);
      out.push(depth);
      for (let i = 0; i < data.length; i += 255) {
        const part = data.slice(i, i + 255);
        out.push(part.length);
        for (const b of part) out.push(b);
      }
      out.push(0);
    }
    out.push(0x3b);
    return new Uint8Array(out);
  }

  return {PALETTE, STARTERS, STAMPS, STAMP_INK, INK, blank, encode, decode, fromRows,
          line, box, circle, flood, flip, shift, turn, outline, shade, gif};
})();

if (typeof module !== "undefined") module.exports = PixelArt;
