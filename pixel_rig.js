// Pixel Pals: makes a drawing alive. It works out where the eyes, arms, legs, ears
// and tail are, then moves those parts. Everything stays on the drawing's own
// squares, so a moving pal still looks hand-drawn. No page in here: the Studio,
// the Stage, the Theatre and the projector all use it, and node can test it.
"use strict";

const PixelRig = (() => {
  const KINDS = ["arm", "leg", "ear", "tail", "wing"];
  // What a student can mark by hand. "." leaves that square to the computer.
  const MARKS = {a: "arm", l: "leg", e: "ear", t: "tail", w: "wing", o: "eye", m: "mouth", b: "body"};

  // ---- Finding shapes --------------------------------------------------------------
  // Groups of joined squares. Each is {at: [...], left, right, top, bottom}.
  function groups(mask, size, corners = true) {
    const seen = new Uint8Array(mask.length), out = [];
    const near = corners ? [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]
                         : [[-1, 0], [1, 0], [0, -1], [0, 1]];
    for (let i = 0; i < mask.length; i++) {
      if (!mask[i] || seen[i]) continue;
      const g = {at: [], left: size, right: -1, top: size, bottom: -1}, todo = [i];
      seen[i] = 1;
      while (todo.length) {
        const n = todo.pop(), x = n % size, y = Math.floor(n / size);
        g.at.push(n);
        g.left = Math.min(g.left, x); g.right = Math.max(g.right, x);
        g.top = Math.min(g.top, y); g.bottom = Math.max(g.bottom, y);
        for (const [dx, dy] of near) {
          const nx = x + dx, ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= size || ny >= size) continue;
          const m = ny * size + nx;
          if (mask[m] && !seen[m]) { seen[m] = 1; todo.push(m); }
        }
      }
      out.push(g);
    }
    return out.sort((a, b) => b.at.length - a.at.length);
  }

  // The squares that a k-by-k block can reach while staying inside the shape. Thin
  // things, like arms, ears and tails, are what a block is too fat to get into.
  function core(mask, size, k) {
    const sum = new Int32Array((size + 1) * (size + 1)), side = size + 1, out = new Uint8Array(mask.length);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      sum[(y + 1) * side + x + 1] = mask[y * size + x] + sum[y * side + x + 1] + sum[(y + 1) * side + x] - sum[y * side + x];
    }
    for (let y = 0; y + k <= size; y++) for (let x = 0; x + k <= size; x++) {
      const inside = sum[(y + k) * side + x + k] - sum[y * side + x + k] - sum[(y + k) * side + x] + sum[y * side + x];
      if (inside !== k * k) continue;
      for (let dy = 0; dy < k; dy++) for (let dx = 0; dx < k; dx++) out[(y + dy) * size + x + dx] = 1;
    }
    return out;
  }

  function centre(at, size) {
    let sx = 0, sy = 0;
    for (const n of at) { sx += n % size; sy += Math.floor(n / size); }
    return [sx / at.length, sy / at.length];
  }

  function rgb(hex) { return [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)); }
  // An empty square inside a drawing, like a hollow head, counts as white paper.
  const inkOf = (palette, n) => n < 0 ? "#ffffff" : palette[n];
  function brightness(hex) { const [r, g, b] = rgb(hex); return .3 * r + .59 * g + .11 * b; }
  function gap(a, b) { const p = rgb(a), q = rgb(b); return Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]); }
  function nearestTo(palette, hex) {
    let best = 0, d = Infinity;
    palette.forEach((c, i) => { const e = gap(c, hex); if (e < d) { d = e; best = i; } });
    return best;
  }

  // ---- The face: eyes are little islands inside the skin, in a pair --------------------
  function findFace(frame, size, main, palette, axis) {
    const inMain = new Uint8Array(frame.length);
    for (const n of main.at) inMain[n] = 1;
    const tall = main.bottom - main.top + 1;
    const counts = new Map();
    for (const n of main.at) {
      if (Math.floor(n / size) - main.top <= tall * .75) counts.set(frame[n], (counts.get(frame[n]) || 0) + 1);
    }
    const skins = [...counts].sort((a, b) => b[1] - a[1]).slice(0, 4).map(c => c[0]);
    const limit = Math.max(4, main.at.length * .09);
    let best = null, lone = null;
    for (const skin of skins) for (const corners of [true, false]) {
      const other = new Uint8Array(frame.length);
      for (const n of main.at) if (frame[n] !== skin) other[n] = 1;
      const islands = groups(other, size, corners).filter(g => {
        if (g.at.length > limit) return false;
        return g.at.every(n => {
          const x = n % size, y = Math.floor(n / size);
          if (x === 0 || y === 0 || x === size - 1 || y === size - 1) return false;
          return inMain[n - 1] && inMain[n + 1] && inMain[n - size] && inMain[n + size];
        });
      });
      for (const g of islands) {
        g.mid = [(g.left + g.right) / 2, (g.top + g.bottom) / 2];
        const drawn = g.at.map(n => frame[n]).filter(n => n >= 0);
        g.ink = drawn.length ? darkest(drawn, palette) : nearestTo(palette, "#1b1530");
        g.pop = gap(inkOf(palette, drawn.length ? g.ink : -1), inkOf(palette, skin));
      }
      // A pair, level with each other. Near the middle, dark and high up all count,
      // so cheeks and buttons don't win. Side-on pals have both eyes at one end.
      for (let i = 0; i < islands.length; i++) for (let j = i + 1; j < islands.length; j++) {
        const a = islands[i], b = islands[j];
        const dy = Math.abs(a.mid[1] - b.mid[1]), apart = Math.abs(a.mid[0] - b.mid[0]);
        const big = Math.max(a.at.length, b.at.length), small = Math.min(a.at.length, b.at.length);
        const off = Math.abs((a.mid[0] + b.mid[0]) / 2 - axis);
        const high = ((a.mid[1] + b.mid[1]) / 2 - main.top) / tall;
        if (dy > Math.max(1, size / 12) || apart < 2 || big > small * 2.5 || high > .78) continue;
        if (apart > size * .75 || Math.max(a.pop, b.pop) < 60) continue;
        const pale = (brightness(inkOf(palette, a.ink)) + brightness(inkOf(palette, b.ink))) / 2;
        const score = dy * 3 + off * 16 / size + (big - small) * .5 + high * 8 - Math.min(a.pop, b.pop) / 40 + pale / 40;
        if (!best || score < best.score) {
          best = {score, skin, eyes: a.mid[0] < b.mid[0] ? [a, b] : [b, a], islands};
        }
      }
      const one = islands.filter(g => g.pop >= 60 && (g.mid[1] - main.top) / tall < .6
        && g.right - g.left <= (g.bottom - g.top + 1) * 1.6).sort((a, b) => b.at.length - a.at.length)[0];
      if (one && !lone) lone = {skin, eyes: [one], islands};
    }
    best = best || lone;
    if (!best) return {skin: skins[0], eyes: [], mouth: null};
    const {skin, eyes, islands} = best;
    const eyeBottom = Math.max(...eyes.map(e => e.bottom));
    const middle = eyes.reduce((s, e) => s + e.mid[0], 0) / eyes.length;
    const aMouth = g => !eyes.includes(g) && g.top > eyeBottom && g.top - eyeBottom <= Math.max(3, size / 5)
      && Math.abs(g.mid[0] - middle) <= Math.max(1.5, size / 10);
    let mouth = islands.filter(g => aMouth(g) && g.pop >= 40).sort((a, b) => a.top - b.top)[0] || null;
    if (!mouth) {
      // A mouth drawn against the chin isn't an island, but it's still one colour.
      for (const colour of new Set(main.at.map(n => frame[n]))) {
        if (colour === skin || colour < 0) continue;
        const same = new Uint8Array(frame.length);
        for (const n of main.at) if (frame[n] === colour) same[n] = 1;
        for (const g of groups(same, size)) {
          g.mid = [(g.left + g.right) / 2, (g.top + g.bottom) / 2];
          g.ink = colour;
          if (g.at.length <= limit && aMouth(g) && (!mouth || g.top < mouth.top)) mouth = g;
        }
      }
    }
    return {skin, eyes, mouth};
  }

  function darkest(list, palette) {
    return list.reduce((a, b) => brightness(palette[b]) < brightness(palette[a]) ? b : a);
  }

  // Wings are too fat to be told from a body by shape, but they come in pairs: two
  // big patches of one colour, mirrored either side of the middle.
  function findWings(frame, size, main, palette) {
    const mid = (main.left + main.right) / 2, tall = main.bottom - main.top + 1;
    const colours = [...new Set(main.at.map(n => frame[n]).filter(n => n >= 0))];
    if (colours.length < 2) return [];
    const ink = darkest(colours, palette), patches = [];
    for (const colour of colours) {
      if (colour === ink) continue;
      const mask = new Uint8Array(frame.length);
      for (const n of main.at) if (frame[n] === colour) mask[n] = 1;
      for (const g of groups(mask, size)) {
        const cy = centre(g.at, size)[1];
        if (g.at.length < Math.max(8, main.at.length * .06) || g.right - g.left < 2) continue;
        if (g.bottom - g.top + 1 < tall * .3 || (cy - main.top) / tall >= .75) continue;
        if (g.right < mid || g.left > mid) patches.push(Object.assign(g, {colour, cy}));
      }
    }
    const room = Math.max(2, size / 8), wings = [], used = new Set();
    for (const a of patches.filter(g => g.right < mid)) {
      const b = patches.find(g => g.left > mid && !used.has(g) && g.colour === a.colour
        && Math.abs(g.cy - a.cy) <= room && Math.abs((a.left + g.right) / 2 - mid) <= room
        && Math.max(g.at.length, a.at.length) <= Math.min(g.at.length, a.at.length) * 1.6);
      if (!b) continue;
      used.add(b);
      for (const [g, side] of [[a, -1], [b, 1]]) {
        const own = new Set(g.at), at = g.at.slice();
        // Its outline goes with it, unless that line is also the edge of something else.
        for (const n of main.at) {
          if (frame[n] !== ink || own.has(n)) continue;
          const x = n % size, near = [x > 0 ? n - 1 : -1, x < size - 1 ? n + 1 : -1, n - size, n + size].filter(m => m >= 0 && m < frame.length);
          if (near.some(m => own.has(m)) && near.every(m => frame[m] < 0 || frame[m] === ink || own.has(m))) at.push(n);
        }
        const inner = g.at.reduce((p, q) => {
          const score = n => Math.abs(n % size - mid) * 2 + Math.abs(Math.floor(n / size) - g.cy);
          return score(q) < score(p) ? q : p;
        });
        wings.push({kind: "wing", at, side, pivot: [inner % size, Math.floor(inner / size)], source: "auto"});
      }
    }
    return wings;
  }

  // ---- Reading a drawing -----------------------------------------------------------
  /** Work out the rig for one frame. `marks` is what the student painted by hand. */
  function build(frame, size, palette, marks = "") {
    const count = frame.length, pad = Math.ceil(size * .5), wide = size + pad * 2;
    const rig = {size, pad, wide, part: new Uint8Array(count), limbs: [], arms: [], legs: [], eyes: [], mouth: null,
                 skin: 0, axis: size / 2, neck: 0, hip: size, top: 0, feet: size - 1, empty: true, palette};
    // An outline with nothing inside is still a body, so holes count as solid.
    const solid = new Uint8Array(count), outside = new Uint8Array(count), todo = [];
    for (let i = 0; i < count; i++) {
      solid[i] = frame[i] >= 0 ? 1 : 0;
      const x = i % size, y = Math.floor(i / size);
      if (!solid[i] && (x === 0 || y === 0 || x === size - 1 || y === size - 1)) { outside[i] = 1; todo.push(i); }
    }
    while (todo.length) {
      const n = todo.pop(), x = n % size;
      for (const m of [x > 0 ? n - 1 : -1, x < size - 1 ? n + 1 : -1, n - size, n + size]) {
        if (m >= 0 && m < count && !solid[m] && !outside[m]) { outside[m] = 1; todo.push(m); }
      }
    }
    for (let i = 0; i < count; i++) if (!outside[i]) solid[i] = 1;
    const pieces = groups(solid, size);
    if (!pieces.length) return rig;
    rig.empty = false;
    const main = pieces[0];
    for (const p of pieces) for (const n of p.at) rig.part[n] = 1;
    rig.top = Math.min(...pieces.map(p => p.top));
    rig.feet = main.bottom;
    const mark = n => marks ? MARKS[marks[n]] : undefined;

    const mask = new Uint8Array(count);
    for (const n of main.at) mask[n] = 1;
    const tall = main.bottom - main.top + 1;
    const pairedWings = marks.includes("w") ? [] : findWings(frame, size, main, palette);
    for (const wing of pairedWings) for (const n of wing.at) mask[n] = 0;

    // The thick middle of the body. A block that's too fat misses a skinny body, so
    // it shrinks until the middle reaches most of the way down.
    let widest = 0;
    for (let y = main.top; y <= main.bottom; y++) {
      let n = 0;
      for (let x = 0; x < size; x++) n += mask[y * size + x];
      widest = Math.max(widest, n);
    }
    let block = Math.max(2, Math.ceil(widest * .4)), body = null;
    for (; block >= 2; block--) {
      const found = groups(core(mask, size, block), size)[0];
      if (found && found.bottom - found.top + 1 >= tall * .55) { body = found; break; }
    }
    if (!body) body = main;
    const inBody = new Uint8Array(count);
    for (const n of body.at) inBody[n] = 1;
    for (const wing of pairedWings) for (const n of wing.at) inBody[n] = 3;
    rig.axis = centre(body.at, size)[0];
    const face = findFace(frame, size, main, palette, rig.axis);
    const isFace = new Uint8Array(count);
    for (const eye of face.eyes) for (const n of eye.at) isFace[n] = 1;
    const eyesAt = face.eyes.length ? face.eyes.reduce((s, e) => s + e.mid[0], 0) / face.eyes.length : rig.axis;
    const middle = (main.left + main.right) / 2;
    const sideOn = face.eyes.length && Math.abs(eyesAt - middle) > Math.max(1.5, size / 10) ? Math.sign(eyesAt - middle) : 0;
    const eyeLine = face.eyes.length ? Math.max(...face.eyes.map(e => e.bottom)) + 1 : -1;

    rig.limbs.push(...pairedWings);

    // ---- Legs: the rows at the bottom with daylight between them.
    const runsIn = y => {
      const runs = [];
      for (let x = 0; x < size; x++) {
        if (!mask[y * size + x]) continue;
        if (runs.length && runs[runs.length - 1][1] === x - 1) runs[runs.length - 1][1] = x;
        else runs.push([x, x]);
      }
      return runs;
    };
    let gapTop = main.bottom + 1;
    for (let y = main.bottom; y >= main.top && runsIn(y).length >= 2; y--) gapTop = y;
    const gapRows = main.bottom + 1 - gapTop;
    const noAutoLegs = marks.includes("l");
    let hip = main.bottom + 1;
    if (gapRows >= 1 && gapRows < tall * .6 && !noAutoLegs) {
      // A short gap only shows the feet, so legs carry on up into the body a little.
      const legRows = Math.max(gapRows, Math.round(tall * .2));
      hip = main.bottom + 1 - legRows;
      const runs = runsIn(gapTop).filter(r => !(r[0] <= rig.axis && r[1] >= rig.axis && runsIn(gapTop).length > 2));
      if (runs.length >= 2) {
        const cuts = runs.slice(1).map((r, i) => Math.floor((runs[i][1] + r[0]) / 2));
        const legs = runs.map((r, i) => ({kind: "leg", at: [], side: 0, sway: i % 2}));
        for (let y = hip; y <= main.bottom; y++) for (let x = 0; x < size; x++) {
          const n = y * size + x;
          if (!mask[n]) continue;
          let which = 0;
          while (which < cuts.length && x > cuts[which]) which++;
          legs[which].at.push(n);
        }
        for (const leg of legs) {
          if (!leg.at.length) continue;
          const [mx] = centre(leg.at, size);
          leg.side = mx < rig.axis ? -1 : 1;
          leg.pivot = [mx, hip];
          leg.source = "auto";
          rig.limbs.push(leg);
          for (const n of leg.at) inBody[n] = 2;
        }
      } else hip = main.bottom + 1;
    }

    // ---- Whatever else sticks out of the middle.
    const rest = new Uint8Array(count);
    for (const n of main.at) if (!inBody[n]) rest[n] = 1;
    const smallest = Math.max(3, Math.round(4 * size / 16));
    const reach = Math.max(2, Math.round(size / 8));
    const bodyTop = body.top;
    const bodyTall = Math.max(1, Math.min(hip, body.bottom + 1) - bodyTop);
    const sticking = groups(rest, size);
    const found = [];
    // How far out a piece goes, counting squares from where it joins the body.
    const depthOf = (g, touching) => {
      const within = new Set(g.at), seen = new Map(touching.map(n => [n, 1]));
      const queue = touching.slice();
      let deepest = 1;
      while (queue.length) {
        const n = queue.shift(), x = n % size, d = seen.get(n);
        deepest = Math.max(deepest, d);
        for (const m of [x > 0 ? n - 1 : -1, x < size - 1 ? n + 1 : -1, n - size, n + size]) {
          if (within.has(m) && !seen.has(m)) { seen.set(m, d + 1); queue.push(m); }
        }
      }
      return deepest;
    };
    // On a round body the edge of the body joins on to the arm, and it mustn't wave
    // with it. An arm starts where the outline leaves the body's own curve.
    const trimArm = limb => {
      const edge = [], span = Math.round(size / 3);
      for (let y = main.top; y <= main.bottom; y++) {
        const row = [];
        for (let x = 0; x < size; x++) if (mask[y * size + x]) row.push(x);
        edge[y] = row.length ? (limb.side < 0 ? row[0] : row[row.length - 1]) : null;
      }
      const curve = y => {
        const near = [];
        for (let r = Math.max(main.top, y - span); r <= Math.min(main.bottom, y + span); r++) if (edge[r] !== null) near.push(edge[r]);
        near.sort((a, b) => a - b);
        return near[Math.floor(near.length / 2)];
      };
      const kept = limb.at.filter(n => {
        const bulge = (n % size - curve(Math.floor(n / size))) * limb.side;
        return bulge > 0;
      });
      if (kept.length < smallest || kept.length === limb.at.length) return;
      const keep = new Set(kept);
      for (const n of limb.at) if (!keep.has(n)) inBody[n] = 1;
      const joined = kept.filter(n => {
        const x = n % size;
        return [x > 0 ? n - 1 : -1, x < size - 1 ? n + 1 : -1, n - size, n + size].some(m => m >= 0 && m < count && mask[m] && !keep.has(m));
      });
      const [jx, jy] = centre(joined.length ? joined : kept, size);
      limb.at = kept;
      limb.pivot = [jx, jy];
    };
    for (const g of sticking) {
      const touches = corners => n => {
        const x = n % size, left = x > 0, right = x < size - 1;
        const near = [n - size, n + size, left ? n - 1 : -1, right ? n + 1 : -1];
        if (corners) near.push(left ? n - size - 1 : -1, right ? n - size + 1 : -1, left ? n + size - 1 : -1, right ? n + size + 1 : -1);
        return near.some(m => m >= 0 && m < count && inBody[m] === 1);
      };
      let touching = g.at.filter(touches(false));
      if (!touching.length) touching = g.at.filter(touches(true));
      if (g.at.length < smallest || !touching.length || depthOf(g, touching) < reach || g.at.some(n => isFace[n])) {
        for (const n of g.at) inBody[n] = 1;
        continue;
      }
      const [mx, my] = centre(g.at, size), [cx, cy] = centre(touching, size);
      const side = mx < rig.axis ? -1 : 1, height = (cy - bodyTop) / bodyTall;
      const upward = g.bottom <= bodyTop + 1 || (my < cy - 1 && Math.abs(my - cy) > Math.abs(mx - cx));
      const big = g.at.length >= body.at.length * .12 && g.bottom - g.top + 1 >= bodyTall * .3;
      const shoulder = touching.reduce((a, b) => Math.floor(a / size) < Math.floor(b / size) ? a : b);
      let kind;
      if (sideOn && side === -sideOn) kind = "tail";
      else if (big && (mx < body.left || mx > body.right)) kind = "wing";
      else if (upward || cy <= eyeLine || height < .3) kind = "ear";
      else if (g.bottom >= main.bottom - 1 && height > .8 && Math.abs(mx - cx) < Math.abs(my - cy)) kind = "leg";
      else kind = "arm";
      const pivot = kind === "arm" || kind === "wing" ? [shoulder % size, Math.floor(shoulder / size)] : [cx, cy];
      const limb = {kind, at: g.at, side, pivot, source: "auto"};
      if (kind === "arm") trimArm(limb);
      found.push(limb);
    }
    // Ears on a round head melt into the curve of it, but they're legs upside down:
    // rows at the top with daylight between them.
    if (!found.some(l => l.kind === "ear")) {
      let earRows = 0;
      while (main.top + earRows <= main.bottom && runsIn(main.top + earRows).length >= 2) earRows++;
      const lastRow = main.top + earRows - 1;
      const runs = earRows ? runsIn(lastRow) : [];
      if (earRows >= Math.max(2, Math.round(size / 12)) && earRows < tall * .4 && runs.length <= 3) {
        const cuts = runs.slice(1).map((r, i) => Math.floor((runs[i][1] + r[0]) / 2));
        const ears = runs.map(() => []);
        for (let y = main.top; y <= lastRow; y++) for (let x = 0; x < size; x++) {
          const n = y * size + x;
          if (!mask[n] || isFace[n]) continue;
          let which = 0;
          while (which < cuts.length && x > cuts[which]) which++;
          ears[which].push(n);
        }
        for (const at of ears) {
          if (at.length < 2) continue;
          const [mx] = centre(at, size);
          for (const n of at) inBody[n] = 3;
          found.push({kind: "ear", at, side: mx < rig.axis ? -1 : 1, pivot: [mx, lastRow + 1], source: "auto"});
        }
      }
    }
    // Pieces not joined on, like a robot's floating hands or a drawing's far-off ears.
    for (const p of pieces.slice(1)) {
      if (p.at.length < smallest) continue;
      const [mx, my] = centre(p.at, size), side = mx < rig.axis ? -1 : 1;
      const nearX = side < 0 ? p.right + 1 : p.left - 1;
      if (my < bodyTop) found.push({kind: "ear", at: p.at, side, pivot: [mx, p.bottom + 1], source: "auto"});
      else if (mx < body.left || mx > body.right) found.push({kind: "arm", at: p.at, side, pivot: [nearX, p.top], source: "auto"});
    }
    // One big piece with no partner isn't a wing: it's a side-on animal's long body.
    // Whatever is still thin on the end of it is the tail.
    const wings = found.filter(l => l.kind === "wing");
    if (wings.length === 1 && !marks.includes("w")) {
      const long = wings[0];
      found.splice(found.indexOf(long), 1);
      const piece = new Uint8Array(count);
      for (const n of long.at) { inBody[n] = 1; piece[n] = 1; }
      const fat = core(piece, size, Math.max(3, Math.round(size / 4)));
      const thin = new Uint8Array(count);
      for (const n of long.at) { if (!fat[n]) thin[n] = 1; }
      const end = groups(thin, size).filter(g => g.at.length >= smallest && Math.abs(centre(g.at, size)[0] - eyesAt) > size / 4)
        .sort((a, b) => Math.abs(centre(b.at, size)[0] - eyesAt) - Math.abs(centre(a.at, size)[0] - eyesAt))[0];
      if (end) {
        for (const n of end.at) inBody[n] = 0;
        const joined = end.at.filter(n => [n - 1, n + 1, n - size, n + size].some(m => m >= 0 && m < count && inBody[m] === 1));
        const [jx, jy] = centre(joined.length ? joined : end.at, size);
        found.push({kind: "tail", at: end.at, side: centre(end.at, size)[0] < eyesAt ? -1 : 1, pivot: [jx, jy], source: "auto"});
      }
      rig.axis = (main.left + main.right) / 2;
    }
    // One thing sticking out low down on one side only is a tail, not an arm.
    const arms = found.filter(l => l.kind === "arm");
    if (arms.length === 1 && (arms[0].pivot[1] - bodyTop) / bodyTall > .55) arms[0].kind = "tail";
    for (const limb of found) {
      if (marks.includes(Object.keys(MARKS).find(k => MARKS[k] === limb.kind))) {
        for (const n of limb.at) inBody[n] = 1;
        continue;
      }
      rig.limbs.push(limb);
    }

    // ---- What the student painted by hand beats what the computer guessed.
    if (marks) {
      for (const letter of Object.keys(MARKS)) {
        const kind = MARKS[letter];
        if (!KINDS.includes(kind)) continue;
        const painted = new Uint8Array(count);
        for (let n = 0; n < count; n++) if (marks[n] === letter && frame[n] >= 0) painted[n] = 1;
        for (const g of groups(painted, size)) {
          const [mx, my] = centre(g.at, size);
          const inner = g.at.reduce((a, b) => {
            const d = n => Math.abs(n % size - rig.axis) * 2 + (kind === "leg" ? Math.floor(n / size) : Math.abs(Math.floor(n / size) - my) * (kind === "arm" ? -.01 : 0));
            return d(b) < d(a) ? b : a;
          });
          const side = mx < rig.axis ? -1 : 1;
          const pivot = kind === "leg" ? [mx, g.top] : [inner % size, Math.floor(inner / size)];
          rig.limbs.push({kind, at: g.at, side, pivot, source: "hand", sway: side > 0 ? 1 : 0});
        }
      }
      rig.limbs = rig.limbs.map(limb => Object.assign(limb, {at: limb.at.filter(n => limb.source === "hand" || !mark(n))}))
                           .filter(limb => limb.at.length);
    }

    // ---- Where the head ends. The narrowest row under the head is the neck.
    const widths = [];
    for (let y = body.top; y <= body.bottom; y++) {
      let n = 0;
      for (let x = 0; x < size; x++) n += inBody[y * size + x] === 1 ? 1 : 0;
      widths[y] = n;
    }
    rig.skin = face.skin;
    rig.eyes = face.eyes.map(g => eyeInfo(g, frame, size, palette));
    rig.mouth = face.mouth ? mouthInfo(face.mouth, frame, size, palette) : null;
    if (marks) {
      const paintedFace = letter => {
        const m = new Uint8Array(count);
        for (let n = 0; n < count; n++) if (marks[n] === letter && frame[n] >= 0) m[n] = 1;
        return groups(m, size).map(g => Object.assign(g, {
          mid: [(g.left + g.right) / 2, (g.top + g.bottom) / 2], ink: darkest(g.at.map(n => frame[n]), palette)}));
      };
      const eyes = paintedFace("o");
      if (eyes.length) {
        rig.eyes = eyes.sort((a, b) => a.mid[0] - b.mid[0]).slice(0, 4).map(g => eyeInfo(g, frame, size, palette));
        rig.skin = aroundColour(eyes[0], frame, size);
      }
      const mouths = paintedFace("m");
      if (mouths.length) rig.mouth = mouthInfo(mouths[0], frame, size, palette);
    }
    let neck = -1, narrowest = Infinity, above = 0;
    const span = body.bottom - body.top + 1;
    for (let y = body.top; y <= body.bottom; y++) {
      const place = (y - body.top) / span;
      if (place >= .3 && place <= .75 && widths[y] < narrowest && widths[y] <= above * .8) { narrowest = widths[y]; neck = y; }
      above = Math.max(above, widths[y]);
    }
    const faceBottom = Math.max(-1, ...rig.eyes.map(e => e.bottom), rig.mouth ? rig.mouth.bottom : -1);
    if (neck < 0) neck = Math.round(body.top + span * .55);
    rig.neck = Math.max(neck, faceBottom + 1);
    rig.hip = Math.max(rig.neck + 1, hip);

    // Which group each square belongs to: 1 is the body, and limbs count from 2.
    rig.part.fill(0);
    for (const p of pieces) for (const n of p.at) rig.part[n] = 1;
    rig.limbs.forEach((limb, i) => {
      limb.id = i + 2;
      for (const n of limb.at) rig.part[n] = limb.id;
      const far = limb.at.reduce((a, b) => dist(b, limb.pivot, size) > dist(a, limb.pivot, size) ? b : a);
      limb.tip = [far % size, Math.floor(far / size)];
      limb.reach = Math.ceil(dist(far, limb.pivot, size)) + 1;
      const out = limb.side || 1;
      limb.rest = Math.atan2((limb.tip[0] - limb.pivot[0]) * out, limb.tip[1] - limb.pivot[1]) * 180 / Math.PI;
    });
    rig.arms = rig.limbs.filter(l => l.kind === "arm");
    rig.legs = rig.limbs.filter(l => l.kind === "leg");
    rig.scratch = new Int16Array(count);
    return rig;
  }

  function dist(n, [px, py], size) { return Math.hypot(n % size - px, Math.floor(n / size) - py); }

  // The colour next to a shape, which is what's there when the shape moves away.
  function aroundColour(g, frame, size) {
    const counts = new Map(), inside = new Set(g.at);
    for (const n of g.at) for (const m of [n - 1, n + 1, n - size, n + size]) {
      if (m < 0 || m >= frame.length || inside.has(m)) continue;
      counts.set(frame[m], (counts.get(frame[m]) || 0) + 1);
    }
    const top = [...counts].sort((a, b) => b[1] - a[1])[0];
    return top ? top[0] : -1;
  }

  function eyeInfo(g, frame, size, palette) {
    const light = g.at.filter(n => brightness(inkOf(palette, frame[n])) > 170);
    const dark = g.at.filter(n => brightness(inkOf(palette, frame[n])) <= 170);
    // A white eye with a dark pupil looks around with its pupil. A plain dot moves.
    const sclera = light.length >= dark.length * .6 && light.length >= 2 && dark.length >= 1;
    return {left: g.left, right: g.right, top: g.top, bottom: g.bottom, at: g.at, ink: g.ink, under: aroundColour(g, frame, size),
            pupil: sclera ? dark : null, mid: g.mid || [(g.left + g.right) / 2, (g.top + g.bottom) / 2]};
  }
  function mouthInfo(g, frame, size, palette) {
    return {left: g.left, right: g.right, top: g.top, bottom: g.bottom, at: g.at, ink: g.ink, mid: g.mid, under: aroundColour(g, frame, size)};
  }

  // ---- Drawing the face in a mood ------------------------------------------------------
  function dot(src, size, x, y, colour) {
    if (x >= 0 && y >= 0 && x < size && y < size) src[y * size + x] = colour;
  }
  function row(src, size, x0, x1, y, colour) { for (let x = x0; x <= x1; x++) dot(src, size, x, y, colour); }

  // Bigger drawings get thicker lines, so a face looks the same on any canvas.
  const lineFor = size => Math.max(1, Math.round(size / 16));
  function bar(src, size, x0, x1, y, colour, thick) {
    for (let t = 0; t < thick; t++) row(src, size, Math.min(x0, x1), Math.max(x0, x1), y - t, colour);
  }

  function paintEye(src, rig, eye, mood, look, frame) {
    const {size} = rig, skin = eye.under, ink = eye.ink, side = eye.mid[0] < rig.axis ? -1 : 1, k = lineFor(size);
    const wide = eye.right - eye.left + 1;
    if (mood === "wink") mood = side < 0 ? "open" : "shut";
    if (mood === "open" && !look[0] && !look[1]) return;
    for (const n of eye.at) src[n] = skin;
    // A tiny eye needs three squares to make a shape, and it grows outwards.
    const left = wide < 3 && side < 0 ? eye.right - 2 : eye.left, right = wide < 3 ? left + 2 : eye.right;
    const inner = side < 0 ? right : left, outer = side < 0 ? left : right, low = eye.bottom;
    const restore = () => { for (const n of eye.at) src[n] = frame[n]; };
    if (mood === "open") {
      if (eye.pupil) {
        restore();
        const pupil = new Set(eye.pupil), lights = eye.at.filter(n => !pupil.has(n));
        for (const n of eye.pupil) src[n] = lights.length ? frame[lights[0]] : skin;
        for (const n of eye.pupil) {
          const x = Math.max(eye.left, Math.min(eye.right, n % size + look[0]));
          const y = Math.max(eye.top, Math.min(eye.bottom, Math.floor(n / size) + look[1]));
          dot(src, size, x, y, frame[n]);
        }
      } else {
        for (const n of eye.at) dot(src, size, n % size + look[0], Math.floor(n / size) + look[1], frame[n]);
      }
    } else if (mood === "shut") {
      bar(src, size, left, right, low, ink, k);
    } else if (mood === "happy") {
      bar(src, size, left, left + k - 1, low, ink, k);
      bar(src, size, right - k + 1, right, low, ink, k);
      bar(src, size, left + k, right - k, low - k, ink, k);
    } else if (mood === "sad") {
      bar(src, size, outer, inner + side * k, low, ink, k);
      bar(src, size, inner, inner + side * (k - 1), low - k, ink, k);
    } else if (mood === "cross") {
      restore();
      if (!eye.pupil) bar(src, size, eye.left, eye.right, eye.top + k - 1, skin, k);
      const edge = side < 0 ? eye.left : eye.right, near = side < 0 ? eye.right : eye.left;
      bar(src, size, edge, edge - side * (k - 1), eye.top - 1, ink, k);
      bar(src, size, near, edge - side * k, eye.top + k - 1, ink, k);
    } else if (mood === "wide") {
      restore();
      if (!eye.pupil) {
        bar(src, size, eye.left, eye.right, eye.top - 1, ink, k);
        dot(src, size, side < 0 ? eye.left : eye.left, eye.top - k, nearestTo(rig.palette, "#ffffff"));
      }
    } else if (mood === "shades") {
      for (let y = eye.top; y <= eye.bottom; y++) row(src, size, eye.left - k, eye.right + k, y, ink);
    }
  }
  // Sunglasses need a bridge between the two lenses.
  function paintBridge(src, rig) {
    if (rig.eyes.length !== 2) return;
    const [a, b] = rig.eyes;
    row(src, rig.size, a.right + 1, b.left - 1, a.top, a.ink);
  }

  function paintMouth(src, rig, mood) {
    if (!mood || mood === "rest") return;
    const {size, mouth} = rig;
    if (!rig.eyes.length && !mouth) return;
    const k = lineFor(size), eye = rig.eyes[0];
    let x0, x1, y;
    if (mouth) {
      const tiny = mouth.right - mouth.left < 2 ? 1 : 0;
      x0 = mouth.left - tiny; x1 = mouth.right + tiny; y = mouth.bottom;
      for (const n of mouth.at) src[n] = mouth.under;
    } else {
      const middle = rig.eyes.reduce((s, e) => s + e.mid[0], 0) / rig.eyes.length;
      x0 = Math.floor(middle - k); x1 = Math.ceil(middle + k);
      y = Math.min(rig.neck - 1, Math.max(...rig.eyes.map(e => e.bottom)) + Math.max(2, Math.round(size / 6)));
    }
    const ink = mouth ? mouth.ink : eye.ink, red = nearestTo(rig.palette, "#b3123c"), pink = nearestTo(rig.palette, "#ff8fc7");
    if (mood === "open") {
      bar(src, size, x0, x1, y - k, ink, k);
      bar(src, size, x0 + k, x1 - k, y, red, k);
    } else if (mood === "o") {
      const mid = Math.floor((x0 + x1) / 2);
      bar(src, size, mid, mid + k, y, ink, k * 2);
    } else if (mood === "smile") {
      bar(src, size, x0, x0 + k - 1, y - k, ink, k);
      bar(src, size, x1, x1 - k + 1, y - k, ink, k);
      bar(src, size, x0 + k, x1 - k, y, ink, k);
    } else if (mood === "frown") {
      bar(src, size, x0, x0 + k - 1, y, ink, k);
      bar(src, size, x1, x1 - k + 1, y, ink, k);
      bar(src, size, x0 + k, x1 - k, y - k, ink, k);
    } else if (mood === "flat") {
      bar(src, size, x0, x1, y, ink, k);
    } else if (mood === "tongue") {
      bar(src, size, x0, x1, y - k, ink, k);
      bar(src, size, x1 - k * 2, x1 - k, y, pink, k);
    }
  }

  // ---- Putting it all together ----------------------------------------------------------
  /**
   * Draw a pose. Returns `out`, a wide-by-wide array of colours with room around
   * the pal for raised arms. Row `feet + pad` is the ground.
   * A pose is all optional: {lift, squash, lean, headX, headY, arm: [left, right],
   * legs: [{dx, dy}...], ear, tail, wing, eyes, look, mouth}.
   */
  function render(rig, frame, pose = {}, out = null) {
    const {size, pad, wide} = rig;
    if (!out) out = new Int16Array(wide * wide);
    out.fill(-1);
    if (rig.empty) return out;
    const src = rig.scratch;
    src.set(frame);
    const mood = pose.eyes || "open", look = pose.look || [0, 0];
    for (const eye of rig.eyes) paintEye(src, rig, eye, mood, look, frame);
    if (mood === "shades") paintBridge(src, rig);
    paintMouth(src, rig, pose.mouth);

    const lift = Math.round(pose.lift || 0), squash = pose.squash || 1, lean = pose.lean || 0;
    const headX = Math.round(pose.headX || 0), headY = Math.round(pose.headY || 0);
    const {neck, hip, axis} = rig, tallBody = Math.max(1, hip - neck);
    const newBody = Math.max(1, Math.round(tallBody * squash));
    const drop = tallBody - newBody + headY;
    const spread = 1 / Math.sqrt(squash);
    const height = Math.max(1, hip - rig.top);

    // The body bends, and the head rides on top of it in one piece, so a leaning
    // pal keeps its face.
    const lanes = y => Math.round(lean * (hip - Math.max(y, neck + drop)) / height);
    // Where a square of the drawing lands, before any lifting.
    const landsY = y => y >= hip ? y : y >= neck ? hip - (hip - y) * newBody / tallBody : y + drop;
    const landsX = (x, y) => {
      const pushed = y >= neck && y < hip ? axis + (x - axis) * spread : x;
      return pushed + lanes(landsY(y)) + (y < neck ? headX : 0);
    };

    const limbFrom = (limb, angle, dx, dy) => {
      const [px, py] = limb.pivot, ax = landsX(px, py) + dx, ay = landsY(py) + dy;
      const c = Math.cos(-angle), s = Math.sin(-angle), r = limb.reach + 1;
      for (let oy = Math.floor(ay - r); oy <= ay + r; oy++) for (let ox = Math.floor(ax - r); ox <= ax + r; ox++) {
        const rx = ox - ax, ry = oy - ay;
        const sx = Math.round(px + rx * c - ry * s), sy = Math.round(py + rx * s + ry * c);
        if (sx < 0 || sy < 0 || sx >= size || sy >= size) continue;
        const n = sy * size + sx;
        if (rig.part[n] !== limb.id) continue;
        const tx = ox + pad, ty = oy + pad - lift;
        if (tx < 0 || ty < 0 || tx >= wide || ty >= wide) continue;
        if (src[n] >= 0) out[ty * wide + tx] = src[n];
      }
    };
    const angleOf = limb => {
      if (limb.kind === "ear") return (pose.ear || 0) * limb.side * Math.PI / 180;
      if (limb.kind === "tail") return (pose.tail || 0) * Math.PI / 180;
      if (limb.kind === "wing") return (pose.wing || 0) * -limb.side * Math.PI / 180;
      if (limb.kind === "arm") {
        const value = pose.arm && pose.arm[limb.side < 0 ? 0 : 1];
        if (value === null || value === undefined) return 0;
        return (value - limb.rest) * -limb.side * Math.PI / 180;
      }
      return 0;
    };

    for (const limb of rig.limbs) if (limb.kind === "wing" || limb.kind === "tail" || limb.kind === "ear") limbFrom(limb, angleOf(limb), 0, 0);
    rig.limbs.filter(l => l.kind === "leg").forEach((limb, i) => {
      const step = (pose.legs && pose.legs[limb.sway || 0]) || {};
      limbFrom(limb, 0, Math.round(step.dx || 0), Math.round(step.dy || 0));
    });

    // The body: each row of the picture finds the row of the drawing it shows.
    for (let oy = 0; oy < wide; oy++) {
      const y = oy - pad + lift;
      let sy;
      const neckNow = neck + drop;
      if (y >= hip) sy = y;
      else if (y >= neckNow) sy = hip - 1 - Math.floor((hip - 1 - y) * tallBody / newBody);
      else sy = y - drop;
      if (sy < 0 || sy >= size) continue;
      const shift = lanes(y) + (y < neckNow ? headX : 0), body = sy >= neck && sy < hip;
      for (let ox = 0; ox < wide; ox++) {
        const x = ox - pad - shift;
        const sx = body ? Math.round(axis + (x - axis) / spread) : x;
        if (sx < 0 || sx >= size) continue;
        const n = sy * size + sx;
        if (rig.part[n] === 1 && src[n] >= 0) out[oy * wide + ox] = src[n];
      }
    }
    for (const limb of rig.limbs) if (limb.kind === "arm") limbFrom(limb, angleOf(limb), 0, 0);
    return out;
  }

  // ---- Moves. A move is a pose that changes with time; `t` counts in seconds. ----------
  const MOVES = {
    idle(t, rig) {
      const breath = Math.sin(t * Math.PI * .9);
      const swing = Math.sin(t * 1.4) * 5;
      return {squash: 1 + breath * .05, ear: Math.max(0, Math.sin(t * .9) - .92) * 240, tail: Math.sin(t * 2.2) * 14,
              wing: Math.sin(t * 3) * 7, arm: rig.arms.map(a => a.rest + swing)};
    },
    walk(t, rig) {
      const beat = t * Math.PI * 2 * 2.2, big = rig.size / 16;
      const legs = [0, Math.PI].map(p => ({dx: Math.cos(beat + p) * big, dy: -Math.max(0, Math.sin(beat + p)) * 2 * big}));
      const swing = rig.arms.map(a => a.rest + Math.sin(beat + (a.side < 0 ? 0 : Math.PI)) * 26);
      return {legs, arm: swing, lift: rig.legs.length ? Math.abs(Math.sin(beat)) * big : Math.abs(Math.sin(beat)) * 2 * big,
              lean: rig.legs.length ? 0 : Math.sin(beat) * 1.5 * big, tail: Math.sin(t * 16) * 18, ear: Math.sin(beat * 2) * 8, wing: Math.sin(t * 22) * 18};
    },
    wave(t, rig) {
      const flap = Math.sin(t * Math.PI * 7) * 24, side = rig.arms.find(a => a.side > 0) ? 1 : 0;
      const arm = [null, null];
      for (const a of rig.arms) arm[a.side < 0 ? 0 : 1] = a.rest;
      arm[side] = 150 + flap;
      return {arm, mouth: "smile", eyes: "happy", lean: rig.arms.length ? 0 : Math.sin(t * 12) * 2 * rig.size / 16};
    },
    cheer(t, rig) {
      const up = Math.abs(Math.sin(t * Math.PI * 3.2));
      return {arm: [150 + up * 20, 150 + up * 20], lift: up * 4 * rig.size / 16, squash: 1 + (up - .5) * .16, eyes: "happy", mouth: "open", wing: Math.sin(t * 26) * 22, tail: Math.sin(t * 24) * 20};
    },
    dance(t, rig) {
      const beat = t * Math.PI * 2 * 1.6, big = rig.size / 16;
      const sway = Math.sin(beat);
      return {lean: sway * 2.6 * big, headX: Math.round(sway * big), lift: Math.abs(Math.cos(beat)) * 2 * big,
              arm: [sway > 0 ? 160 : 60, sway > 0 ? 60 : 160], legs: [{dy: sway > 0 ? -1.4 * big : 0}, {dy: sway > 0 ? 0 : -1.4 * big}],
              squash: 1 + Math.cos(beat * 2) * .08, eyes: Math.sin(beat / 2) > .4 ? "happy" : "open", mouth: "smile", tail: sway * 26, ear: sway * 14, wing: sway * 18};
    },
    jump(t, rig) {
      // Crouch, leap, land: `t` runs from 0 to 1 here.
      const big = rig.size / 16;
      if (t < .2) return {squash: 1 - t * 1.5, arm: rig.arms.map(a => a.rest - 18)};
      if (t < .85) return {squash: 1.12, arm: [165, 165], eyes: "happy", mouth: "open", ear: -16, wing: 26, legs: [{dy: -big}, {dy: -big}]};
      return {squash: .78 + (t - .85) * 1.4, arm: rig.arms.map(a => a.rest)};
    },
    sad(t, rig) {
      return {squash: .93 + Math.sin(t * 2) * .02, headY: Math.round(rig.size / 16), eyes: "sad", mouth: "frown", ear: 34, tail: 28, wing: 40, arm: rig.arms.map(() => 8), look: [0, 1]};
    },
    happy(t, rig) {
      const beat = Math.abs(Math.sin(t * Math.PI * 2.4));
      return {eyes: "happy", mouth: "smile", lift: beat * 2 * rig.size / 16, squash: 1 + beat * .06, tail: Math.sin(t * 22) * 22, ear: beat * 10};
    },
    surprised(t, rig) {
      return {eyes: "wide", mouth: "o", squash: 1.1, arm: [130, 130], ear: -24, lift: t < .25 ? 3 * rig.size / 16 : 0, wing: 22};
    },
    cross(t, rig) {
      return {eyes: "cross", mouth: "frown", lean: Math.sin(t * 40) * rig.size / 16, arm: rig.arms.map(() => 42), ear: 26, tail: Math.sin(t * 30) * 8};
    },
    sleep(t, rig) {
      const breath = Math.sin(t * Math.PI * .7);
      return {eyes: "shut", mouth: "flat", squash: .95 + breath * .05, headY: Math.round(rig.size / 16), lean: rig.size / 16 * 1.2, ear: 22, tail: 22, wing: 30, arm: rig.arms.map(() => 12)};
    },
    giggle(t, rig) {
      return {eyes: "happy", mouth: "open", lean: Math.sin(t * 30) * rig.size / 16, lift: Math.abs(Math.sin(t * 15)) * rig.size / 16, squash: 1 + Math.sin(t * 30) * .05};
    },
    flap(t, rig) { return {wing: Math.sin(t * 28) * 30, arm: rig.arms.map(() => 90 + Math.sin(t * 28) * 40), lift: 2 + Math.sin(t * 7) * 2}; },
  };
  const LASTS = {jump: .62, wave: 1.6, cheer: 1.4, dance: 2.4, sad: 1.6, happy: 1.2, surprised: 1, cross: 1.4, sleep: 2.6, giggle: .8, flap: 1.4};

  // A mood stays on the face until another one replaces it.
  const MOODS = {
    happy: {eyes: "happy", mouth: "smile"},
    sad: {eyes: "sad", mouth: "frown"},
    surprised: {eyes: "wide", mouth: "o"},
    angry: {eyes: "cross", mouth: "frown"},
    sleepy: {eyes: "shut", mouth: "flat"},
    silly: {eyes: "wink", mouth: "tongue"},
    cool: {eyes: "shades", mouth: "smile"},
  };

  /** The pose for a move, `t` seconds in. Jump is special: 0 is take-off and 1 is landed. */
  function pose(move, t, rig) {
    const fn = MOVES[move] || MOVES.idle;
    return fn(t, rig);
  }

  // Blinks, glances and fidgets: a pal who isn't doing anything still isn't still.
  function life(seed) {
    let s = (seed * 2654435761 >>> 0) || 1;
    const rand = () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
    let blinkAt = 1 + rand() * 2, glanceAt = 2 + rand() * 3, look = [0, 0], glanceEnd = 0;
    return {
      /** What the eyes are doing at time t. `aim` overrides glancing. */
      eyes(t, aim) {
        if (t > blinkAt + .13) blinkAt = t + 1.6 + rand() * 3.4;
        const blinking = t >= blinkAt && t < blinkAt + .13;
        if (t > glanceAt) {
          look = [[-1, 0], [1, 0], [0, 0], [0, -1]][Math.floor(rand() * 4)];
          glanceEnd = t + .5 + rand();
          glanceAt = glanceEnd + 1.5 + rand() * 3;
        }
        if (t > glanceEnd) look = [0, 0];
        return {eyes: blinking ? "shut" : "open", look: aim || look};
      },
    };
  }

  // Whole numbers of small steps, so a pose repeats and its picture can be kept.
  function tidy(pose) {
    const out = {};
    for (const [key, value] of Object.entries(pose)) {
      if (value === undefined || value === null) continue;
      if (key === "squash") out[key] = Math.round(value * 40) / 40;
      else if (key === "lean" || key === "lift") out[key] = Math.round(value * 2) / 2;
      else if (key === "ear" || key === "tail" || key === "wing") out[key] = Math.round(value / 6) * 6;
      else if (key === "arm") out[key] = value.map(a => a === null || a === undefined ? null : Math.round(a / 6) * 6);
      else if (key === "legs") out[key] = value.map(l => ({dx: Math.round(l.dx || 0), dy: Math.round(l.dy || 0)}));
      else out[key] = value;
    }
    return out;
  }

  return {build, render, pose, life, tidy, groups, KINDS, MARKS, LASTS, MOODS, MOVES: Object.keys(MOVES)};
})();

if (typeof module !== "undefined") module.exports = PixelRig;
