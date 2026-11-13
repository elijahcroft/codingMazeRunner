// Pixel Pals: the stage. It draws at 320 by 180 and scales up with hard edges,
// so scenes, pals and sparkles all share the same chunky pixels. The student
// page and the projector both use this one file.
"use strict";

const PalStage = (() => {
  const W = 320, H = 180, FLOOR = 158;
  const spotX = spot => 26 + spot * 26.8;
  // In the Hang out, y runs from the back of the ground (0) to the front (1).
  const GROUND_TOP = 128, GROUND_DEEP = 42;
  const groundOf = m => GROUND_TOP + m.y * GROUND_DEEP;
  // Calm mode: fewer bits flying about, and nothing shakes or flashes.
  let calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  try { const saved = localStorage.getItem("pixelCalm"); if (saved !== null) calm = saved === "1"; } catch (_) {}

  // ---- Sounds, made on the spot so there are no files to load -------------------
  const SFX = (() => {
    let ac = null, muted = false, voice = 420;
    try { muted = localStorage.getItem("pixelMute") === "1"; } catch (_) {}
    const wake = () => {
      if (!ac) { try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (_) { return null; } }
      if (ac.state === "suspended") ac.resume();
      return ac;
    };
    const tone = (freq, at, length, type = "square", volume = .05, slide = 0) => {
      const o = ac.createOscillator(), g = ac.createGain(), t = ac.currentTime + at;
      o.type = type;
      o.frequency.setValueAtTime(freq, t);
      if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t + length);
      g.gain.setValueAtTime(volume, t);
      g.gain.exponentialRampToValueAtTime(.0005, t + length);
      o.connect(g).connect(ac.destination);
      o.start(t);
      o.stop(t + length + .02);
    };
    const notes = (list, gap, length = .12, type = "square") => list.forEach((f, i) => tone(f, i * gap, length, type));
    const SOUNDS = {
      ding: () => notes([988, 1319], .07, .25, "triangle"),
      boing: () => tone(180, 0, .22, "square", .05, 520),
      pop: () => tone(700, 0, .07, "square", .05, -500),
      tada: () => notes([523, 659, 784, 1047], .09, .22),
      meow: () => { tone(620, 0, .14, "sawtooth", .03, 260); tone(880, .14, .24, "sawtooth", .03, -420); },
      drum: () => { tone(120, 0, .14, "sine", .14, -70); tone(120, .2, .14, "sine", .14, -70); },
      whoosh: () => tone(220, 0, .3, "sawtooth", .025, 900),
      yay: () => notes([659, 784, 988, 1319, 988, 1319], .07, .1),
      bells: () => { notes([1319, 1047, 1319, 1047, 1319, 1047], .24, .55, "sine"); },
      // Here Comes the Bride. It's 170 years old, so it's anyone's to play.
      march: () => {
        const C = 262, E = 330, F = 349, G = 392, A = 440, Bb = 466;
        const tune = [[C, 1], [F, .75], [F, .25], [F, 2], [C, 1], [G, .75], [E, .25], [F, 2],
                      [C, 1], [F, .75], [Bb, .25], [Bb, 1], [A, .75], [G, .25], [F, 1], [E, .75], [F, .25], [G, 2]];
        let at = 0;
        for (const [freq, beats] of tune) {
          tone(freq, at, beats * .42, "triangle", .08);
          tone(freq * 2, at, beats * .3, "sine", .025);
          at += beats * .46;
        }
        [0, 2, 4, 6].forEach(i => tone(F / 2, i * .92, .8, "sine", .06));
      },
      jig: () => { notes([523, 659, 784, 659, 880, 784, 659, 784, 523, 659, 784, 659, 988, 880, 784, 1047], .112, .1, "triangle");
                   [0, 4, 8, 12].forEach(i => tone(131, i * .112, .1, "sine", .07)); },
      nope: () => notes([233, 196], .13, .18, "triangle"),
      step: () => tone(150, 0, .04, "square", .018),
      blip: () => tone(voice * (.9 + Math.random() * .25), 0, .05, "triangle", .035),
      jump: () => tone(300, 0, .16, "square", .03, 420),
      eat: () => notes([330, 262, 330], .09, .06),
      click: () => tone(900, 0, .03, "square", .02),
      clap: () => { tone(1800, 0, .05, "sawtooth", .025, -1200); tone(1500, .04, .05, "sawtooth", .02, -1000); },
      five: () => { tone(1400, 0, .06, "sawtooth", .04, -900); notes([784, 1047, 1319], .06, .12, "triangle"); },
      gift: () => notes([523, 659, 784, 1047, 1319, 1568], .07, .18, "triangle"),
      party: () => { notes([523, 523, 523, 659, 784, 659, 784, 1047, 1047, 1319], .13, .16); [0, 4, 8].forEach(i => tone(131, i * .13, .2, "sine", .08)); },
      fanfare: () => notes([392, 523, 659, 784, 659, 784, 1047], .1, .2, "triangle"),
    };
    return {
      wake,
      /** Each pal has its own pitch to talk at. */
      voiceAt(pitch) { voice = pitch; },
      play(name) { if (!muted && wake() && SOUNDS[name]) SOUNDS[name](); },
      /** A note that climbs with each one in a row, for stars and combos. */
      climb(n) { if (!muted && wake()) notes([1, 1.5].map(k => 523 * 2 ** (Math.min(n, 14) / 12) * k), .06, .16, "triangle"); },
      get muted() { return muted; },
      toggle() {
        muted = !muted;
        try { localStorage.setItem("pixelMute", muted ? "1" : "0"); } catch (_) {}
        return muted;
      },
    };
  })();

  // ---- Little drawings ------------------------------------------------------------
  const PROP_ART = {
    star: {rows: ["......kk......", ".....kyyk.....", ".....kyyk.....", "kkkkkyyyykkkkk", "kyyyyyyyyyyyyk", ".kyyyyyyyyyyk.",
                  "..kyyyyyyyyk..", "..kyyyyyyyyk..", ".kyyyyyyyyyyk.", ".kyyykkkkyyyk.", "kyykk....kkyyk", "kkk........kkk"], ink: {k: "#1b1530", y: "#ffd93b"}},
    gem:  {rows: ["...kkkkkkkk...", "..kbbwwbbbbk..", ".kbbwwbbbbbbk.", "kbbbbbbbbbbbbk", "kkkkkkkkkkkkkk", ".kbbbbbbbbbbk.",
                  "..kbbbbbbbbk..", "...kbbbbbbk...", "....kbbbbk....", ".....kbbk.....", "......kk......"], ink: {k: "#1b1530", b: "#35d0bd", w: "#ffffff"}},
    cake: {rows: ["......kk......", "......ry......", "....kkkkkk....", "..kkwwwwwwkk..", ".kwwwwwwwwwwk.", ".kpwpwpwpwpwk.",
                  ".kppppppppppk.", ".kppppppppppk.", ".kbbbbbbbbbbk.", ".kbbbbbbbbbbk.", ".kkkkkkkkkkkk."], ink: {k: "#1b1530", w: "#ffffff", p: "#ff8fc7", b: "#c68642", r: "#e8294f", y: "#ffd93b"}},
    ball: {rows: ["....kkkkkk....", "..kkrrrwwrkk..", ".krrrrwwwrrrk.", ".krrrrrrrrrrk.", "kwwwwwwwwwwwwk", "kwwwwwwwwwwwwk",
                  "kbbbbbbbbbbbbk", "kbbbbbbbbbbbbk", ".kbbbbbbbbbbk.", ".kbbbbbbbbbbk.", "..kkbbbbbbkk..", "....kkkkkk...."], ink: {k: "#1b1530", r: "#e8294f", w: "#ffffff", b: "#2f6fe4"}},
  };
  // Things to wear in the Hang out. Hats sit on the head, and faces on the eyes.
  const WEAR_ART = {
    party: {rows: ["....y....", "...kpk...", "...kpk...", "..kpypk..", "..kpypk..", ".kpypypk.", ".kpypypk.", "kpypypypk", "kkkkkkkkk"], ink: {k: "#1b1530", p: "#ff5fa2", y: "#ffd93b"}},
    tophat: {rows: ["..kkkkkkkk..", "..kddddddk..", "..kddddddk..", "..kddddddk..", "..krrrrrrk..", "kkkkkkkkkkkk", "kddddddddddk", "kkkkkkkkkkkk"], ink: {k: "#1b1530", d: "#3a3358", r: "#e8294f"}},
    flower: {rows: ["..pp.pp..", ".pppppp..", "..pyyp...", "pppyypppp", ".ppyypp..", "..pppp...", "...gg....", "..ggg...."], ink: {p: "#ff8fc7", y: "#ffd93b", g: "#2fa84f"}},
    bow: {rows: ["rr.....rr", "rrrr.rrrr", "rrrrkrrrr", "rrrr.rrrr", "rr.....rr"], ink: {r: "#e8294f", k: "#8f1d3a"}},
    cap: {rows: ["...kkkkkk...", "..kbbbbbbk..", ".kbbwwbbbbk.", ".kbbbbbbbbk.", "kkkkkkkkkkkk", "........kbbk", "........kkkk"], ink: {k: "#1b1530", b: "#2f6fe4", w: "#ffffff"}},
    wizard: {rows: [".....k.....", "....kpk....", "...kpypk...", "...kpppk...", "..kpppypk..", "..kpypppk..", ".kpppppppk.", ".kpppyppyk.", "kkkkkkkkkkk"], ink: {k: "#1b1530", p: "#7a3fe4", y: "#ffd93b"}},
    crown: {rows: ["k...k...k", "ky.kyk.yk", "kyykyykyk", "kyyyyyyyk", "kyryyyryk", "kkkkkkkkk"], ink: {k: "#8a5a00", y: "#ffd93b", r: "#e8294f"}},
    shades: {rows: ["kkkkk.kkkkk", "kdddkkkdddk", "kdwdk.kdwdk", ".kkk...kkk."], ink: {k: "#1b1530", d: "#3a3358", w: "#9a96a8"}},
    heartglasses: {rows: [".pp.pp.pp.pp.", "pppppp.pppppp", ".pppp...pppp.", "..pp.....pp.."], ink: {p: "#ff5fa2"}},
    moustache: {rows: ["..kk...kk..", ".kkkk.kkkk.", "kkkkkkkkkkk", "kk..k.k..kk"], ink: {k: "#4a2c1d"}},
    // from the shop
    beanie: {rows: ["...www...", "...www...", "..rrrrr..", ".yyyyyyy.", "ggggggggg", "bbbbbbbbb", "kkkkkkkkk"], ink: {w: "#ffffff", r: "#ff5fa2", y: "#ffd93b", g: "#35d0bd", b: "#7ab8ff", k: "#3a3358"}},
    bunny: {rows: [".kk...kk.", "kwwk.kwwk", "kwpk.kpwk", "kwpk.kpwk", "kwpk.kpwk", "kwpk.kpwk", "kwwk.kwwk", ".kk...kk."], ink: {k: "#3a3358", w: "#ffffff", p: "#ff8fc7"}},
    catears: {rows: ["k.......k", "kk.....kk", "kpk...kpk", "kppk.kppk", "kkkkkkkkk"], ink: {k: "#3a3358", p: "#ff8fc7"}},
    pirate: {rows: ["...kkkkk...", "..kkkkkkk..", ".kkkwkwkkk.", ".kkkkwkkkk.", "kkkkwkwkkkk", "kkkkkkkkkkk", "yyyyyyyyyyy"], ink: {k: "#1b1530", w: "#ffffff", y: "#ffd93b"}},
    halo: {rows: [".yyyyyyy.", "yy.....yy", ".yyyyyyy.", ".........", "........."], ink: {y: "#ffd93b"}},
    starglasses: {rows: ["..y.......y..", ".yyy.....yyy.", "yyyyykkkyyyyy", ".yyy.....yyy.", "..y.......y.."], ink: {y: "#ffd93b", k: "#8a5a00"}},
    frog: {rows: [".ggg...ggg.", "gwwwg.gwwwg", "gwkwgggwkwg", "ggggggggggg", "gdddddddddg", "ggggggggggg"], ink: {g: "#5cc96a", w: "#ffffff", k: "#1b1530", d: "#2fa84f"}},
    witch: {rows: [".....kk....", "....kpk....", "....kpk....", "...kpppk...", "...kpppk...", "..kpppppk..", "..kgggggk..", "kkkkkkkkkkk"], ink: {k: "#1b1530", p: "#5a3a8c", g: "#8ee06b"}},
    flowercrown: {rows: [".p...y...b.", "pyp.yoy.bwb", ".p...y...b.", "ggggggggggg"], ink: {p: "#ff8fc7", y: "#ffd93b", o: "#ff9a3c", b: "#7ab8ff", w: "#ffffff", g: "#2fa84f"}},
    unicorn: {rows: ["..w..", "..y..", ".py..", ".yp..", ".pyp.", ".ypy.", "pypyp", "kkkkk"], ink: {w: "#ffffff", y: "#ffd93b", p: "#ff8fc7", k: "#c5a3ff"}},
    monocle: {rows: [".........kkk.", "........kwwwk", "........kwwwk", ".........kkk.", "...........y.", "............y"], ink: {k: "#8a5a00", w: "#d6f4ff", y: "#ffd93b"}},
    heromask: {rows: ["rrrrrrrrrrrrr", "rr...rrr...rr", "rr...r.r...rr", ".rrrr...rrrr."], ink: {r: "#2f6fe4"}},
    // from gift boxes
    tiara: {rows: ["....p....", "...ypy...", "y..yyy..y", "yy.yby.yy", "yyyyyyyyy"], ink: {p: "#ff5fa2", y: "#ffd93b", b: "#7ab8ff"}},
    chef: {rows: ["..ooo.oo..", ".owwwowwo.", "owwwwwwwwo", ".owwwwwwo.", "..owwwwo..", "..owwwwo..", "..oooooo.."], ink: {o: "#9a96a8", w: "#ffffff"}},
    cowboy: {rows: ["...bbbbb...", "..bbbdbbb..", "..bbbbbbb..", "..rrrrrrr..", "b.bbbbbbb.b", "bbbbbbbbbbb", ".bbbbbbbbb."], ink: {b: "#a0673a", d: "#7a4a26", r: "#e8294f"}},
    headphones: {rows: ["...kkkkk...", "..k.....k..", ".k.......k.", "k.........k", "pp.......pp", "pp.......pp", "pp.......pp"], ink: {k: "#3a3358", p: "#ff5fa2"}},
    roundglasses: {rows: [".kkk...kkk.", "kwwwkkkwwwk", "kwwwk.kwwwk", ".kkk...kkk."], ink: {k: "#4a2c1d", w: "#d6f4ff"}},
    clownnose: {rows: [".rr.", "rwrr", "rrrr", ".rr."], ink: {r: "#e8294f", w: "#ffffff"}},
    blush: {rows: ["pp.......pp", "pp.......pp"], ink: {p: "#e8406f"}},
    // unlocked by reaching a goal
    gemcrown: {rows: ["k...k...k", "kb.kpk.gk", "kyykyykyk", "kyyyyyyyk", "kbyryygyk", "kkkkkkkkk"], ink: {k: "#8a5a00", y: "#ffd93b", r: "#e8294f", b: "#7ab8ff", g: "#35d0bd", p: "#ff5fa2"}},
    fishhat: {rows: ["...oooo...o", ".oooooooooo", "owkoooyooo.", ".oooooooooo", "...oooo...o"], ink: {o: "#ff9a3c", w: "#ffffff", k: "#1b1530", y: "#ffd93b"}},
    goldshades: {rows: ["yyyyy.yyyyy", "ykkkyyykkky", "ykwky.ykwky", ".yyy...yyy."], ink: {y: "#ffd93b", k: "#1b1530", w: "#9a96a8"}},
    dragon: {rows: ["g.........g", "gg.......gg", ".gg.....gg.", ".ggg...ggg.", "..gg...gg.."], ink: {g: "#9a7ae4"}},
    astro: {rows: ["...wwwww...", "..wbbbbbw..", ".wbbcbbbbw.", ".wbbbbbbbw.", "wwwwwwwwwww", "wrwwwwwwwrw"], ink: {w: "#f5f2ff", b: "#2f3a72", c: "#ffffff", r: "#e8294f"}},
  };
  // Sparkles are a few colours that fly off a pal while it moves.
  const SPARKLE_INK = {goldspark: ["#ffd93b", "#fff2a6"], heartspark: ["#ff5fa2", "#ffc9e3"], rainbow: ["#ff5fa2", "#ffd93b", "#35d0bd", "#7ab8ff", "#c5a3ff"],
                       icespark: ["#7ab8ff", "#d6f4ff", "#ffffff"], leafspark: ["#35d0bd", "#8ee06b", "#eaffd6"],
                       galaxyspark: ["#7a3fe4", "#c5a3ff", "#2f6fe4", "#ffffff"], candyspark: ["#ff8fc7", "#ffffff", "#7ab8ff"],
                       firespark: ["#ff9a3c", "#ffd93b", "#e8294f"], friendspark: ["#ff5fa2", "#ffd93b", "#8ee06b", "#7ab8ff"],
                       superspark: ["#ffd93b", "#ffffff", "#ff9a3c", "#ffd93b"]};
  const FRIEND_INK = {cat: "#ffc266", bunny: "#c5a3ff", kid: "#7ab8ff", bean: "#8ee06b"};
  const FRIEND_ART = {cat: "Cat", bunny: "Bunny", kid: "Kid", bean: "Bean"};

  function sprite(w, h) {
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    return cv;
  }
  function rowsSprite(rows, ink, scale = 1) {
    const cv = sprite(rows[0].length * scale, rows.length * scale), g = cv.getContext("2d");
    rows.forEach((row, y) => Array.from(row).forEach((ch, x) => {
      if (ch === ".") return;
      g.fillStyle = ink[ch];
      g.fillRect(x * scale, y * scale, scale, scale);
    }));
    return cv;
  }

  // ---- A pal made of moving parts --------------------------------------------------
  // Each frame gets its own rig, built the first time it's needed. Pictures of poses
  // are kept, because a pose comes round again and again.
  function puppet(pal, scale, seed = 1) {
    const frames = pal.frames.map(PixelArt.decode), rigs = [], kept = new Map();
    const rigOf = i => rigs[i] || (rigs[i] = PixelRig.build(frames[i] || frames[0], pal.size, pal.palette, i === 0 ? pal.marks || "" : ""));
    const lifeline = PixelRig.life(seed);
    function picture(i, pose) {
      const rig = rigOf(i), tidy = PixelRig.tidy(pose), key = i + JSON.stringify(tidy);
      let cv = kept.get(key);
      if (cv) return cv;
      const out = PixelRig.render(rig, frames[i] || frames[0], tidy), wide = rig.wide;
      cv = sprite(wide * scale, wide * scale);
      const g = cv.getContext("2d");
      for (let n = 0; n < out.length; n++) {
        if (out[n] < 0) continue;
        g.fillStyle = pal.palette[out[n]];
        g.fillRect(n % wide * scale, Math.floor(n / wide) * scale, scale, scale);
      }
      if (kept.size > 500) kept.clear();
      kept.set(key, cv);
      return cv;
    }
    const names = pal.names || [];
    return {rigOf, picture, lifeline, scale, frames: frames.length, names,
            // Where the picture goes so the feet land on (x, base).
            draw(g, i, pose, x, base, {flip = false, squeeze = 1, size = 1, tilt = 0} = {}) {
              const rig = rigOf(i), img = picture(i, pose), s = scale * size, w = rig.wide * s;
              g.save();
              g.translate(Math.round(x), Math.round(base));
              if (tilt) g.rotate(tilt);
              g.scale((flip ? -1 : 1) * squeeze, 1);
              g.drawImage(img, -(rig.pad + rig.axis + .5) * s, -(rig.pad + rig.feet + 1) * s, w, w);
              g.restore();
            }};
  }
  // What a pal looks like right now, from what it's doing and how it feels.
  function livePose(rig, lifeline, t, {move, moveT, jump, mood, talk, aim, facing}) {
    const p = move ? Object.assign({}, PixelRig.pose(move, move === "jump" ? jump : moveT, rig))
                   : Object.assign({}, PixelRig.pose("idle", t, rig));
    const face = mood && PixelRig.MOODS[mood];
    if (face && !p.eyes) Object.assign(p, face);
    if (!p.eyes || p.eyes === "open") {
      const glance = lifeline.eyes(t, aim || (face && face.look));
      if (glance.eyes === "shut") p.eyes = "shut"; else if (!p.eyes) p.eyes = "open";
      if (!p.look) p.look = glance.look;
    }
    if (aim) {                     // the head turns with the eyes
      const k = Math.max(1, Math.round(rig.size / 16));
      p.headX = (p.headX || 0) + aim[0] * k;
      p.headY = (p.headY || 0) + aim[1] * k;
    }
    if (talk) p.mouth = Math.floor(t * 8) % 2 ? "open" : p.mouth;
    return p;
  }

  // ---- Scenes: each one is drawn once and kept ----------------------------------------
  function dots(g, list, size = 1) { for (const [x, y] of list) g.fillRect(x, y, size, size); }
  function seeded(n) { let s = n; return () => (s = s * 16807 % 2147483647) / 2147483647; }
  function hill(g, y, height, width, shift, colour) {
    g.fillStyle = colour;
    for (let x = 0; x < W; x++) g.fillRect(x, y - Math.round(Math.sin((x + shift) / width) * height), 1, H);
  }
  function cloud(g, x, y, colour = "#ffffff") {
    g.fillStyle = colour;
    g.fillRect(x + 6, y, 18, 4); g.fillRect(x, y + 4, 32, 6); g.fillRect(x + 10, y - 3, 8, 3);
  }
  function tree(g, x, y) {
    g.fillStyle = "#6e4426"; g.fillRect(x + 6, y + 18, 5, 16);
    g.fillStyle = "#1f8a4c"; g.fillRect(x, y + 6, 18, 14); g.fillRect(x + 3, y, 12, 24);
    g.fillStyle = "#35b868"; g.fillRect(x + 3, y + 4, 8, 6);
  }
  function pine(g, x, y) {
    g.fillStyle = "#5a3b24"; g.fillRect(x + 7, y + 26, 4, 6);
    for (let i = 0; i < 4; i++) {
      g.fillStyle = "#14633a"; g.fillRect(x + 6 - i * 2, y + i * 7, 6 + i * 4, 7);
      g.fillStyle = "#ffffff"; g.fillRect(x + 6 - i * 2, y + i * 7, 6 + i * 4, 2);
    }
  }
  const SCENE_ART = {
    wedding(g) {
      g.fillStyle = "#bfe6ff"; g.fillRect(0, 0, W, H);
      g.fillStyle = "#e3f4ff"; g.fillRect(0, 60, W, 50);
      cloud(g, 26, 20); cloud(g, 250, 14); cloud(g, 110, 34, "#f6fbff");
      hill(g, 118, 12, 46, 20, "#a7e3a0");
      hill(g, 130, 7, 30, 120, "#7fd38d");
      tree(g, 14, 94); tree(g, 288, 92);
      g.fillStyle = "#59c170"; g.fillRect(0, 140, W, 40);
      // The path down the middle.
      for (let y = 140; y < H; y++) {
        const half = 14 + (y - 140) * .9;
        g.fillStyle = y % 6 < 3 ? "#ffd3e6" : "#ffc2dc";
        g.fillRect(160 - half, y, half * 2, 1);
      }
      // The arch, with flowers all the way round.
      g.fillStyle = "#ffffff";
      g.fillRect(118, 62, 7, 84); g.fillRect(195, 62, 7, 84);
      for (let a = 0; a <= 28; a++) {
        const t = Math.PI * a / 28, x = 160 - Math.cos(t) * 40, y = 62 - Math.sin(t) * 34;
        g.fillStyle = "#ffffff"; g.fillRect(x - 3, y - 3, 7, 7);
      }
      const rnd = seeded(23), bloom = ["#ff8fc7", "#ff5fa2", "#ffd93b", "#ffffff", "#c5a3ff"];
      for (let a = 0; a <= 40; a++) {
        const t = Math.PI * a / 40, x = 160 - Math.cos(t) * 40, y = 62 - Math.sin(t) * 34;
        g.fillStyle = bloom[Math.floor(rnd() * bloom.length)];
        g.fillRect(x - 3 + rnd() * 5, y - 3 + rnd() * 5, 3, 3);
      }
      for (let y = 66; y < 144; y += 3) for (const x of [118, 124, 195, 201]) {
        g.fillStyle = bloom[Math.floor(rnd() * bloom.length)];
        g.fillRect(x + rnd() * 3 - 1, y, 3, 3);
      }
      // A heart hanging in the arch.
      g.fillStyle = "#ff5fa2";
      for (const [x, y, w] of [[153, 70, 5], [160, 70, 5], [152, 72, 15], [153, 75, 13], [155, 77, 9], [157, 79, 5], [159, 81, 1]]) g.fillRect(x, y, w, 2);
      // Chairs for the guests.
      for (const side of [0, 1]) for (let i = 0; i < 3; i++) {
        const x = side ? 216 + i * 26 : 80 - i * 26;
        g.fillStyle = "#ffffff"; g.fillRect(x, 128, 16, 3); g.fillRect(x, 118, 3, 20); g.fillRect(x + 13, 130, 3, 8);
        g.fillStyle = "#ff8fc7"; g.fillRect(x, 116, 4, 4);
      }
      // Flags along the top.
      for (let x = 6; x < W; x += 22) {
        g.fillStyle = ["#ff8fc7", "#ffd93b", "#7ab8ff", "#c5a3ff"][(x - 6) / 22 % 4];
        for (let i = 0; i < 8; i++) g.fillRect(x + i, 4 + Math.floor(x / 22) % 2 * 2, 16 - i * 2, 1);
      }
      for (let i = 0; i < 40; i++) { g.fillStyle = bloom[i % 5]; g.fillRect(rnd() * W, 146 + rnd() * 32, 2, 2); }
    },
    stage(g) {
      g.fillStyle = "#2a1140"; g.fillRect(0, 0, W, H);
      g.fillStyle = "#3b1a59"; g.fillRect(44, 20, W - 88, 130);
      const rnd = seeded(7); g.fillStyle = "#6a4a8c";
      for (let i = 0; i < 26; i++) g.fillRect(50 + rnd() * (W - 100), 26 + rnd() * 100, 1, 1);
      for (const side of [0, 1]) for (let i = 0; i < 6; i++) {
        const x = side ? W - 8 - i * 8 : i * 8, tuck = Math.max(0, 5 - i) * 5;
        g.fillStyle = i % 2 ? "#a81c3f" : "#d42a52";
        g.fillRect(x, 0, 8, 150 - (5 - i) * 2 + tuck / 5);
      }
      for (let i = 0; i < 20; i++) { g.fillStyle = i % 2 ? "#a81c3f" : "#d42a52"; g.fillRect(i * 16, 0, 16, 14 + (i % 2) * 4); }
      g.fillStyle = "#ffd93b"; g.fillRect(0, 14, W, 2);
      g.fillStyle = "#b66f30"; g.fillRect(0, 150, W, 30);
      g.fillStyle = "#94551f"; for (let x = 0; x < W; x += 40) g.fillRect(x, 150, 1, 30);
      g.fillStyle = "#d18a45"; g.fillRect(0, 150, W, 2);
    },
    park(g) {
      g.fillStyle = "#8fd8ff"; g.fillRect(0, 0, W, H);
      g.fillStyle = "#ffe066"; g.fillRect(264, 18, 20, 20); g.fillRect(260, 22, 28, 12);
      cloud(g, 34, 22); cloud(g, 150, 38); cloud(g, 214, 14);
      hill(g, 112, 16, 40, 0, "#7fd38d");
      hill(g, 128, 9, 26, 90, "#59c170");
      tree(g, 40, 92); tree(g, 248, 86); tree(g, 136, 100);
      g.fillStyle = "#49ad5f"; g.fillRect(0, 140, W, 40);
      g.fillStyle = "#e5c98f"; g.fillRect(0, 150, W, 16);
      g.fillStyle = "#cdae70"; g.fillRect(0, 150, W, 1); g.fillRect(0, 165, W, 1);
      const rnd = seeded(11); g.fillStyle = "#ff8fc7";
      for (let i = 0; i < 16; i++) g.fillRect(rnd() * W, 169 + rnd() * 9, 2, 2);
      g.fillStyle = "#ffd93b";
      for (let i = 0; i < 16; i++) g.fillRect(rnd() * W, 169 + rnd() * 9, 2, 2);
    },
    beach(g) {
      g.fillStyle = "#ffd9a8"; g.fillRect(0, 0, W, 50);
      g.fillStyle = "#ffbf8f"; g.fillRect(0, 50, W, 40);
      g.fillStyle = "#ff7a55"; g.fillRect(140, 60, 44, 30); g.fillRect(146, 54, 32, 6);
      for (let i = 0; i < 6; i++) { g.fillStyle = i % 2 ? "#1aa7c9" : "#22bfdc"; g.fillRect(0, 88 + i * 8, W, 8); }
      g.fillStyle = "#fff"; dots(g, [[30, 100], [90, 110], [200, 96], [270, 118], [150, 124]], 6);
      g.fillStyle = "#f6dfa3"; g.fillRect(0, 136, W, 44);
      g.fillStyle = "#e7c982"; const rnd = seeded(5); for (let i = 0; i < 60; i++) g.fillRect(rnd() * W, 140 + rnd() * 38, 2, 1);
      g.fillStyle = "#8a5a2c"; for (let i = 0; i < 8; i++) g.fillRect(262 + i, 70 + i * 10, 5, 12);
      g.fillStyle = "#2fa84f"; g.fillRect(238, 62, 58, 7); g.fillRect(250, 56, 34, 6); g.fillRect(232, 68, 12, 8); g.fillRect(288, 68, 12, 8);
    },
    night(g) {
      g.fillStyle = "#141238"; g.fillRect(0, 0, W, H);
      g.fillStyle = "#211e55"; g.fillRect(0, 70, W, 70);
      const rnd = seeded(3); g.fillStyle = "#ffffff";
      for (let i = 0; i < 70; i++) g.fillRect(rnd() * W, rnd() * 100, rnd() > .8 ? 2 : 1, 1);
      g.fillStyle = "#fff2a6"; g.fillRect(250, 20, 24, 24); g.fillRect(246, 24, 32, 16);
      g.fillStyle = "#141238"; g.fillRect(258, 16, 24, 24);
      for (let i = 0; i < 12; i++) {
        const h = 26 + rnd() * 44, x = i * 28;
        g.fillStyle = "#0c0b26"; g.fillRect(x, 146 - h, 26, h);
        g.fillStyle = "#ffd93b";
        for (let w = 0; w < 5; w++) g.fillRect(x + 4 + (rnd() * 18 | 0), 146 - h + 4 + (rnd() * (h - 8) | 0), 3, 3);
      }
      g.fillStyle = "#2c2a55"; g.fillRect(0, 146, W, 34);
      g.fillStyle = "#3b3970"; g.fillRect(0, 146, W, 2);
    },
    snowy(g) {
      g.fillStyle = "#cfe9ff"; g.fillRect(0, 0, W, H);
      g.fillStyle = "#e7f4ff"; g.fillRect(0, 40, W, 60);
      hill(g, 116, 22, 50, 40, "#ffffff");
      pine(g, 26, 92); pine(g, 70, 104); pine(g, 232, 96); pine(g, 280, 88);
      g.fillStyle = "#f4faff"; g.fillRect(0, 138, W, 42);
      g.fillStyle = "#d6e8f7"; const rnd = seeded(9); for (let i = 0; i < 30; i++) g.fillRect(rnd() * W, 142 + rnd() * 36, 6, 1);
      g.fillStyle = "#ffffff"; g.fillRect(150, 118, 18, 18); g.fillRect(153, 104, 12, 14);
      g.fillStyle = "#1b1530"; dots(g, [[156, 108], [161, 108], [158, 122], [158, 128]], 2);
      g.fillStyle = "#ff8a2a"; g.fillRect(158, 111, 7, 2);
    },
    candy(g) {
      g.fillStyle = "#ffd3ec"; g.fillRect(0, 0, W, H);
      g.fillStyle = "#ffe9f6"; g.fillRect(0, 60, W, 40);
      cloud(g, 40, 24, "#fff"); cloud(g, 216, 18, "#c5f2ff");
      hill(g, 118, 14, 34, 10, "#c5a3ff");
      for (const [x, y, a, b] of [[60, 76, "#ff5fa2", "#ffffff"], [240, 70, "#35d0bd", "#ffffff"], [160, 92, "#ffd93b", "#ff8a2a"]]) {
        g.fillStyle = "#ffffff"; g.fillRect(x - 2, y + 14, 4, 60);
        for (let r = 16; r > 0; r -= 4) { g.fillStyle = r % 8 ? a : b; g.fillRect(x - r, y - r / 2, r * 2, r); g.fillRect(x - r / 2, y - r, r, r * 2); }
      }
      g.fillStyle = "#a2642f"; g.fillRect(0, 140, W, 40);
      for (let x = 0; x < W; x += 16) { g.fillStyle = ["#ff5fa2", "#ffffff", "#7ab8ff"][(x / 16) % 3]; g.fillRect(x, 140, 16, 6 + (x / 16 % 2) * 4); }
      const rnd = seeded(13);
      for (let i = 0; i < 40; i++) { g.fillStyle = ["#ffd93b", "#ff8fc7", "#8ee06b", "#ffffff"][i % 4]; g.fillRect(rnd() * W, 152 + rnd() * 26, 3, 1); }
    },
    space(g) {
      g.fillStyle = "#07061c"; g.fillRect(0, 0, W, H);
      const rnd = seeded(17);
      for (let i = 0; i < 110; i++) { g.fillStyle = ["#ffffff", "#c5a3ff", "#7ab8ff"][i % 3]; g.fillRect(rnd() * W, rnd() * 140, rnd() > .85 ? 2 : 1, 1); }
      g.fillStyle = "#ff8a2a"; g.fillRect(232, 24, 40, 40); g.fillRect(224, 32, 56, 24);
      g.fillStyle = "#d9651a"; g.fillRect(232, 40, 44, 6); g.fillRect(226, 52, 40, 4);
      g.fillStyle = "#ffe0a8"; g.fillRect(212, 42, 80, 3);
      g.fillStyle = "#35d0bd"; g.fillRect(40, 40, 18, 18); g.fillRect(36, 44, 26, 10);
      g.fillStyle = "#8c8aa8"; g.fillRect(0, 142, W, 38);
      g.fillStyle = "#a8a6c4"; g.fillRect(0, 142, W, 3);
      g.fillStyle = "#6c6a88"; dots(g, [[30, 154], [110, 166], [190, 150], [260, 168], [80, 150]], 7);
    },
    castle(g) {
      g.fillStyle = "#b9a7ff"; g.fillRect(0, 0, W, H);
      g.fillStyle = "#d5c8ff"; g.fillRect(0, 50, W, 60);
      cloud(g, 24, 26); cloud(g, 250, 16);
      g.fillStyle = "#8f83bd"; g.fillRect(90, 60, 140, 84);
      for (const x of [70, 150, 230]) {
        g.fillStyle = "#a79bd6"; g.fillRect(x, 34, 22, 110);
        g.fillStyle = "#e8294f"; g.fillRect(x - 3, 28, 28, 6); g.fillRect(x + 2, 20, 18, 8); g.fillRect(x + 7, 12, 8, 8);
        g.fillStyle = "#ffd93b"; g.fillRect(x + 8, 60, 6, 10);
      }
      for (let x = 92; x < 228; x += 14) { g.fillStyle = "#8f83bd"; g.fillRect(x, 54, 8, 6); }
      g.fillStyle = "#3b2a6a"; g.fillRect(146, 110, 28, 34); g.fillRect(150, 104, 20, 6);
      g.fillStyle = "#59c170"; g.fillRect(0, 144, W, 36);
      g.fillStyle = "#49ad5f"; g.fillRect(0, 144, W, 2);
    },
  };
  const sceneCache = {};
  function sceneArt(name) {
    if (!sceneCache[name]) {
      const cv = sprite(W, H);
      SCENE_ART[name](cv.getContext("2d"));
      sceneCache[name] = cv;
    }
    return sceneCache[name];
  }

  // ---- One stage on the page -----------------------------------------------------------
  function create(canvas, host) {
    canvas.width = W; canvas.height = H;
    const g = canvas.getContext("2d");
    g.imageSmoothingEnabled = false;
    let names = [], palW = 64, palVoice = 420, pup = null, palScale = 4, friendPups = {}, started = performance.now();
    let crowd = 0;
    let state, sparks = [], bubbles = {}, run = 0, rate = 1, loop = 0, livePal = null;

    function fresh() {
      return {scene: "stage", x: spotX(2), spot: 2, y: 0, frame: 0, flip: false, squeeze: 1, tilt: 0,
              size: 1, visible: true, shakeX: 0, napping: false,
              move: null, moveFrom: 0, jump: 0, mood: null, talk: false, aim: null,
              friend: null, crew: [],
              marks: [], props: {}, score: null, weather: null};
    }

    function setPal(pal) {
      livePal = pal;
      palScale = Math.max(1, Math.floor(68 / pal.size));
      // Small pals squeak and big ones rumble a bit, and no two sound quite alike.
      palVoice = 300 + (pal.frames[0].length * 7 + pal.frames[0].replace(/\./g, "").length * 13) % 320;
      palW = pal.size * palScale;
      pup = puppet(pal, palScale, pal.frames[0].length + pal.palette.length * 7);
      names = pal.names || [];
    }

    function friendPup(kind) {
      if (!friendPups[kind]) {
        const pal = {size: 16, palette: ["#1b1530", FRIEND_INK[kind]], frames: [PixelArt.encode(PixelArt.fromRows(PixelArt.STARTERS[FRIEND_ART[kind]]).map(n => n === PixelArt.INK ? 0 : n < 0 ? -1 : 1))]};
        friendPups[kind] = puppet(pal, 3, kind.length * 37);
      }
      return friendPups[kind];
    }

    function paint() {
      const s = state;
      if (s.soft) g.clearRect(0, 0, W, H); else g.drawImage(sceneArt(s.scene), 0, 0);
      if (s.weather === "rain") { g.fillStyle = "rgba(20,30,70,.25)"; g.fillRect(0, 0, W, H); }
      if (s.weather === "sun") { g.fillStyle = "rgba(255,230,120,.16)"; g.fillRect(0, 0, W, H); }
      for (const spot of s.marks) {
        const x = spotX(spot);
        g.fillStyle = "rgba(255,240,170,.3)";
        g.beginPath(); g.moveTo(x - 6, 0); g.lineTo(x + 6, 0); g.lineTo(x + 24, FLOOR + 6); g.lineTo(x - 24, FLOOR + 6); g.fill();
        g.fillStyle = "rgba(255,240,170,.75)"; g.fillRect(x - 24, FLOOR + 2, 48, 5);
      }
      for (const [spot, prop] of Object.entries(s.props)) {
        const img = PROPS[prop], bob = Math.round(Math.sin(performance.now() / 260 + +spot) * 2);
        g.drawImage(img, Math.round(spotX(+spot) - img.width / 2), FLOOR - img.height - 8 + bob);
      }
      const now = performance.now(), t = (now - started) / 1000;
      for (const m of s.crew) {
        const fp = friendPup(m.kind), rig = fp.rigOf(0);
        const pose = livePose(rig, fp.lifeline, t + 3 + m.kind.length, {move: m.move, moveT: t + m.kind.length * .17, talk: m.talk});
        fp.draw(g, 0, pose, m.x, FLOOR + 4 - m.y, {flip: m.x > s.x});
      }
      if (s.room) { g.save(); g.translate(-Math.round(s.camX), 0); paintRoom(now, t); }
      if (s.visible && pup) {
        const rig = pup.rigOf(s.frame);
        const pose = livePose(rig, pup.lifeline, t, {move: s.move, moveT: (now - s.moveFrom) / 1000, jump: s.jump,
                                                     mood: s.mood, talk: s.talk, aim: s.aim});
        pup.draw(g, s.frame, pose, s.x + s.shakeX, FLOOR + 4 - s.y, {flip: s.flip, squeeze: s.squeeze, size: s.size, tilt: s.tilt});
      }
      paintCrowd();
      for (const p of sparks) {
        g.globalAlpha = Math.min(1, p.life / 300);
        if (p.img) g.drawImage(p.img, Math.round(p.x), Math.round(p.y));
        else { g.fillStyle = p.colour; g.fillRect(Math.round(p.x), Math.round(p.y), p.w || 2, p.h || 2); }
      }
      g.globalAlpha = 1;
      if (s.room) g.restore();
      if (s.score !== null) {
        g.fillStyle = "#1b1530"; g.fillRect(4, 4, 52, 15);
        g.fillStyle = "#ffd93b"; g.font = "bold 12px monospace"; g.textBaseline = "top";
        g.fillText(`★ ${s.score}`, 9, 6);
      }
      placeBubbles();
    }

    // ---- The Hang out: every pal moves on its own, whenever someone taps ----------
    const ROOM_LASTS = {wave: 1400, dance: 2400, cheer: 1400, nap: 3200, jump: 620, spin: 560};
    const MOVE_SOUND = {jump: "jump", dance: "jig", cheer: "yay", wave: "ding", spin: "whoosh", nap: "pop"};
    let hooks = {}, stars = [];

    const BUDDY_SPOTS = [[-34, .12], [34, .12], [-58, -.1]];
    const worldW = () => (state.places || ["park"]).length * W;
    const clampX = x => Math.max(8, Math.min(worldW() - 8, x)), clampY = y => Math.max(0, Math.min(1, y));
    function placedThing(p) {
      const look = p.look || {};
      return {placed: true, id: p.id, x: p.x, y: p.y, mine: p.mine, coded: !!p.coded, pup: puppet(p.pal, Math.max(1, Math.round(38 / p.pal.size)), p.id + 1),
              frame: look.frame || 0, size: look.size || 1, hidden: !!look.hidden, queue: null, queueAt: 0, act: null, actFrom: 0, actMs: 0, grew: 1};
    }
    // A thing someone drew and coded plays the steps of one click, one after another.
    const THING_SIZES = [1, 1.35, 1.7];
    function thingStep(th, s, now, sound) {
      th.act = s.do; th.actFrom = now; th.actMs = s.ms;
      if (s.do === "say") { bubble("t" + th.id, s.text, Math.min(5200, 1300 + s.text.length * 55)); if (sound) SFX.play("blip"); }
      else if (s.do === "sound") { if (sound) SFX.play(s.name); }
      else if (s.do === "size") { th.grew = THING_SIZES[th.size - 1] || 1; th.size = s.to; if (sound) SFX.play("boing"); }
      else if (s.do === "hide" || s.do === "appear") { th.hidden = s.do === "hide"; pop(th.x, roomBase(th) - 20, ["#ffffff", "#c5a3ff"]); if (sound) SFX.play("whoosh"); }
      else if (s.do === "pose") { th.frame = s.frame; pop(th.x, roomBase(th) - 24, ["#ffd93b", "#ffffff"], 8); if (sound) SFX.play("click"); }
      else if (s.do === "hearts" || s.do === "stars" || s.do === "confetti") { roomFx(s.do, th.x); if (sound) SFX.play(FX_SOUND[s.do]); }
      else if (MOVE_SOUND[s.do] && sound) SFX.play(MOVE_SOUND[s.do]);
    }
    function stepThings(now) {
      for (const th of state.placed) {
        if (!th.queue || now < th.queueAt) continue;
        const s = th.queue.shift();
        if (!s) { th.queue = null; th.act = null; continue; }
        thingStep(th, s, now, th.qSound);
        th.queueAt = now + s.ms;
      }
    }
    function paintThing(th, now, t) {
      const held = Math.min(1, (now - th.actFrom) / (th.actMs || 1)), act = held < 1 ? th.act : null;
      let frame = th.frame, size = THING_SIZES[th.size - 1] || 1;
      if (act === "play") frame = Math.floor(held * th.pup.frames * 2) % th.pup.frames;
      if (act === "size") size = th.grew + (size - th.grew) * held;
      const rig = th.pup.rigOf(frame);
      if (rig.empty) return;
      const hop = act === "jump" ? Math.sin(held * Math.PI) * 30 : 0;
      const squeeze = act === "spin" ? Math.cos(held * Math.PI * 4) : 1;
      const shake = act === "shake" ? Math.sin(held * Math.PI * 10) * 3 : 0;
      if (th.hidden) {
        if (!th.mine && act !== "hide") return;      // the owner still sees a faint one, to click it back
        g.globalAlpha = act === "hide" ? 1 - held * (th.mine ? .75 : 1) : .25;
      } else if (act === "appear") g.globalAlpha = held;
      th.pup.draw(g, frame, livePose(rig, th.pup.lifeline, t + th.id * 1.7, {}), th.x + shake, roomBase(th) - hop, {squeeze, size});
      g.globalAlpha = 1;
      if (th.coded && !calm && !th.queue && Math.sin(t * 2 + th.id) > .97) sparks.push({x: th.x - 10 + Math.random() * 20, y: roomBase(th) - 10 - Math.random() * 30, vy: -.3, vx: 0, colour: "#ffd93b", w: 2, h: 2, life: 500});
    }
    function roomBuddy(m, pal, i) {
      const x = clampX(m.x + BUDDY_SPOTS[i][0]), y = clampY(m.y + BUDDY_SPOTS[i][1]);
      return {buddy: true, x, y, tx: x, ty: y, flip: false, walking: false, wanderAt: 0, seat: m.seat * 10 + i,
              pup: puppet(pal, Math.max(1, Math.round(30 / pal.size)), m.seat * 10 + i + 1)};
    }
    function roomMember(m, you) {
      const member = makeMember(m, you);
      member.buddies = buddiesOf(member, m.buddies || []);
      return member;
    }
    const buddiesOf = (member, pals) => pals.map((pal, i) => Object.assign(roomBuddy(member, pal, i), {host: member}));
    const memberPuppet = (pal, seat) => puppet(pal, Math.max(1, Math.round((state.room && state.room.length > 11 ? 32 : 46) / pal.size)), seat + 1);
    function makeMember(m, you) {
      return {seat: m.seat, name: m.name, x: m.x, y: m.y, tx: m.x, ty: m.y, flip: false, mood: m.mood, move: null, moveFrom: 0, until: 0,
              talkUntil: 0, me: m.seat === you, rest: m.rest || null, restNext: null, wear: m.wear || {}, size: m.pal.size, queue: null, spotUntil: 0, trail: false, sparked: 0,
              pal: m.pal, pup: memberPuppet(m.pal, m.seat), concealed: !!m.concealed, tucked: !!m.tucked, playing: !!m.playing, role: m.role || "", prop: !!m.prop, hid: !!m.hid};
    }
    function roomStart(data, you) {
      roomStop();
      state.visible = false;
      state.soft = true;
      state.scene = data.scene || state.scene;
      state.room = data.members.map(m => roomMember(m, you));
      state.camX = 0;
      state.placed = (data.placed || []).map(placedThing);
      state.you = you;
      stars = (data.shower || []).map(fallingStar);
    }
    function roomSync(rows, you) {
      if (!state.room) return;
      const seats = new Set(rows.map(r => r.seat));
      for (const m of state.room) if (!seats.has(m.seat)) { clearTag(m); clearBubble("s" + m.seat); }
      state.room = state.room.filter(m => seats.has(m.seat));
      for (const row of rows) {
        let m = state.room.find(m => m.seat === row.seat);
        if (!m) { m = roomMember(row, you); state.room.push(m); }
        if (row.playing || m.playing) {
          m.x = row.x; m.y = row.y; m.tx = row.tx ?? row.x; m.ty = row.ty ?? row.y;
          m.queue = null; m.trail = false; m.spotUntil = 0; m.fiveWith = 0;
          m.rest = m.restNext = m.toyNext = null;
          clearBubble("s" + m.seat);
        }
        m.concealed = !!row.concealed; m.tucked = !!row.tucked; m.playing = !!row.playing; m.role = row.role || ""; m.prop = !!row.prop; m.hid = !!row.hid;
        if (m.concealed && m.tag) m.tag.style.display = "none";
      }
    }
    /** Which pal on this stage is yours. It's only known once you've joined. */
    function roomYou(you) {
      state.you = you;
      for (const m of state.room || []) {
        m.me = m.seat === you;
        if (m.tag) m.tag.classList.toggle("me", m.me);
      }
    }
    function roomStop() {
      if (state && state.room) for (const m of state.room) clearTag(m);
      if (state) state.room = null;
      stars = [];
      for (const key of Object.keys(bubbles)) if (key.startsWith("s")) clearBubble(key);
    }
    function clearTag(m) { if (m.tag) m.tag.remove(); }
    const roomBase = groundOf;
    function setMove(m, name, now) {
      m.move = name; m.moveFrom = now; m.until = now + ROOM_LASTS[name]; m.bigHop = false;
    }
    function fallingStar(s) { return {id: s.id, x: s.x, delay: s.delay, born: performance.now(), asked: false}; }
    const STAR_FALL = 1800, STAR_REST = roomBase({y: .5}) - 8;
    function starY(star, now) {
      const t = (now - star.born - star.delay) / STAR_FALL;
      return t < 0 ? -20 : Math.min(STAR_REST, -20 + (STAR_REST + 20) * Math.min(1, t * t));
    }
    // One step of a My Move, played by this pal on every screen.
    function moveStep(m, s, now, sound) {
      if (s.do === "walk") { m.tx = s.x; }
      else if (s.do === "say") { say(m, s.text, now, sound); }
      else if (s.do === "feel") { m.mood = s.mood === "calm" ? null : s.mood; }
      else if (ROOM_LASTS[s.do]) { setMove(m, s.do, now); if (sound) SFX.play(MOVE_SOUND[s.do]); }
      else if (s.do === "hearts" || s.do === "stars" || s.do === "confetti") { roomFx(s.do, m.x); if (sound) SFX.play(FX_SOUND[s.do]); }
    }
    function say(m, text, now, sound) {
      const ms = Math.min(5200, 1300 + text.length * 55);
      bubble("s" + m.seat, text, ms);
      m.talkUntil = now + Math.min(ms, 300 + text.length * 70);
      if (sound) { SFX.voiceAt(300 + m.seat * 53 % 320); SFX.play("blip"); }
    }
    function endMove(m, now) {
      m.queue = null;
      m.trail = false;
      m.mood = m.moodBefore;
      if (m.bigFinish) {
        roomFx("confetti", m.x);
        if (m.qSound) SFX.play("fanfare");
        setMove(m, "cheer", now);
      }
      if (hooks.moveEnded) hooks.moveEnded(m);
    }
    function roomStep(dt, now) {
      for (const m of state.room) {
        const gx = m.tx - m.x, gy = m.ty - m.y, far = Math.hypot(gx, gy * GROUND_DEEP);
        if (far > 1) {
          const go = Math.min(1, dt * .085 / far);
          m.x += gx * go; m.y += gy * go;
          if (Math.abs(gx) > 1) m.flip = gx < 0;
          if (!m.move || m.move === "walk") { if (m.move !== "walk") m.moveFrom = now; m.move = "walk"; m.until = now + 200; }
        } else if (m.fiveWith) {
          const other = state.room.find(x => x.seat === m.fiveWith);
          m.fiveWith = 0;
          if (other) highFive(m, other, now);
        }
        if (far <= 1 && m.restNext) { m.rest = m.restNext; m.restNext = null; }
        if (far <= 1 && m.toyNext) { playToy(m, m.toyNext, now); m.toyNext = null; }
        if (m.move && now > m.until) m.move = null;
        if (m.queue && now >= m.queueAt) {
          const s = m.queue.shift();
          if (!s) endMove(m, now);
          else { moveStep(m, s, now, m.qSound); m.queueAt = now + s.ms; }
        }
        const sparkle = m.trail ? ["#ffd93b", "#ffffff", "#ff8fc7"] : SPARKLE_INK[m.wear.sparkle];
        if (!m.playing && sparkle && now > m.sparked && !calm && (m.trail || m.move)) {
          m.sparked = now + (m.trail ? 45 : 110);
          const i = Math.floor(Math.random() * sparkle.length);
          sparks.push({x: m.x - 12 + Math.random() * 24, y: roomBase(m) - Math.random() * 44 - (m.hop || 0), vy: -.3 - Math.random() * .4, vx: 0, colour: sparkle[i], w: 2, h: 2, life: 650});
        }
      }
      for (const m of state.room) stepBuddies(m, dt, now);
      stepThings(now);
      const mine = state.room.find(m => m.me);
      if (mine && hooks.tick) hooks.tick(mine);
      // The camera follows your pal, unless the page has its own idea (the projector does).
      const aim = Math.max(0, Math.min(worldW() - W, state.camera ? state.camera() : mine ? mine.x - W / 2 : state.camX));
      state.camX = Math.abs(aim - state.camX) > W * 1.5 ? aim : state.camX + (aim - state.camX) * Math.min(1, dt * .006);
      if (mine && !mine.playing && hooks.caught) for (const star of stars) {
        if (!star.asked && Math.abs(star.x - mine.x) < 24 && starY(star, now) > STAR_REST - 50) { star.asked = true; hooks.caught(star.id); }
      }
    }
    // Buddies wander near their pal. Each screen picks its own wandering, which is fine:
    // it's only company, and nobody can click them.
    function stepBuddies(m, dt, now) {
      m.buddies.forEach((b, i) => {
        if (now > b.wanderAt || Math.abs(b.tx - m.tx) > 60) {
          b.wanderAt = now + 2000 + Math.random() * 3500;
          const roam = calm || m.rest || m.restNext ? 0 : 1, [sx, sy] = BUDDY_SPOTS[i];
          b.tx = clampX(m.tx + sx + roam * (Math.random() - .5) * 30);
          b.ty = clampY(m.ty + sy + roam * (Math.random() - .5) * .25);
        }
        const gx = b.tx - b.x, gy = b.ty - b.y, far = Math.hypot(gx, gy * GROUND_DEEP);
        b.walking = far > 1;
        if (!b.walking) return;
        const go = Math.min(1, dt * .085 / far);
        b.x += gx * go; b.y += gy * go;
        if (Math.abs(gx) > 1) b.flip = gx < 0;
      });
    }
    function highFive(a, b, now) {
      a.flip = a.x > b.x; b.flip = !a.flip;
      setMove(a, "jump", now); setMove(b, "jump", now);
      state.x = (a.x + b.x) / 2;
      pictureRain(HEART, 12);
      if (a.me || b.me || hooks.everySound) SFX.play("five");
    }
    function drawWear(m, base) {
      const rig = m.pup.rigOf(0);
      if (rig.empty) return;
      const px = m.pup.scale, zoom = Math.max(1, Math.round(px * m.size / 16)), way = m.flip ? -1 : 1;
      const place = (key, cx, y, under) => {
        const img = WEAR_SPRITES[key];
        if (!img) return;
        const w = img.width * zoom, h = img.height * zoom;
        g.drawImage(img, Math.round(m.x + way * (cx - rig.axis - .5) * px - w / 2), Math.round(base + (y - rig.feet - 1) * px - (under ? h : h / 2)), w, h);
      };
      const eyes = rig.eyes;
      if (m.wear.face && eyes.length) {
        const cx = eyes.reduce((sum, e) => sum + (e.left + e.right + 1) / 2, 0) / eyes.length;
        const cy = eyes.reduce((sum, e) => sum + (e.top + e.bottom + 1) / 2, 0) / eyes.length;
        const below = {moustache: [2, 6], clownnose: [1, 10], blush: [1, 9]}[m.wear.face];     // these sit under the eyes
        place(m.wear.face, cx, below ? cy + Math.max(below[0], m.size / below[1]) : cy);
      }
      if (m.wear.hat) place(m.wear.hat, rig.axis + .5, rig.top + 1, true);
    }
    // An open book held in front of the tummy, sized to the pal.
    function drawBook(m, rig) {
      const tall = (rig.feet - rig.top + 1) * m.pup.scale, half = Math.max(5, Math.round(tall * .24)), high = Math.round(half * 1.2);
      const x = Math.round(m.x), y = Math.round(roomBase(m) - tall * .42);
      g.fillStyle = "#e8558f"; g.fillRect(x - half - 1, y - 1, half * 2 + 2, high + 2);
      g.fillStyle = "#fffdf6"; g.fillRect(x - half, y, half * 2, high);
      g.fillStyle = "#c9b8a0"; g.fillRect(x, y, 1, high);
    }
    // A buddy joins in with its pal's dance, nap, wave or cheer, and sits when it sits.
    // Which drawn frame a pal in the Hang out shows: its walk frames in turn while it walks,
    // its jump frame while it jumps, and its first frame otherwise. Same rule as the stage.
    function roomFrame(pup, move, now) {
      if (move === "walk") {
        const walk = pup.names.map((n, i) => n === "walk" ? i : -1).filter(i => i >= 0);
        if (walk.length) return [0, ...walk][Math.floor(now / 170) % (walk.length + 1)];
      }
      if (move === "jump" && pup.names.includes("jump")) return pup.names.indexOf("jump");
      return 0;
    }
    function paintBuddy(b, now, t) {
      const m = b.host;
      const copied = m.move === "nap" ? "sleep" : ["dance", "wave", "cheer"].includes(m.move) ? m.move : null;
      const move = b.walking ? "walk" : copied || (m.rest ? "sit" : null), frame = roomFrame(b.pup, move, now), rig = b.pup.rigOf(frame);
      const pose = livePose(rig, b.pup.lifeline, t + b.seat * 1.3, {move, moveT: copied && !b.walking ? (now - m.moveFrom) / 1000 : t + b.seat, mood: m.mood});
      b.pup.draw(g, frame, pose, b.x, roomBase(b), {flip: b.flip});
    }
    // A prop is drawn like the scenery: one drawing pixel is one scene pixel, with a one pixel
    // edge in a deep shade of its own colour (the same rule the Hang out uses for its trees and
    // bushes), so it blends in with the things around it.
    function propSprite(m) {
      if (m.propArt && m.propArt.pal === m.pal) return m.propArt.art;
      const pup = puppet(m.pal, 1), rig = pup.rigOf(0);
      let art = null;
      if (!rig.empty) {
        const img = pup.picture(0, {}), w = img.width + 2, h = img.height + 2, cv = sprite(w, h), c = cv.getContext("2d", {willReadFrequently: true});
        c.drawImage(img, 1, 1);
        const data = c.getImageData(0, 0, w, h), d = data.data, from = new Uint8ClampedArray(d);
        const solid = i => from[i * 4 + 3] >= 200;
        for (let y = 0, i = 0; y < h; y++) for (let x = 0; x < w; x++, i++) {
          if (solid(i)) continue;
          const n = y + 1 < h && solid(i + w) ? i + w : y && solid(i - w) ? i - w : x && solid(i - 1) ? i - 1 : x + 1 < w && solid(i + 1) ? i + 1 : -1;
          if (n < 0) continue;
          d[i * 4] = from[n * 4] * .36 + 10; d[i * 4 + 1] = from[n * 4 + 1] * .28 + 6; d[i * 4 + 2] = from[n * 4 + 2] * .42 + 26; d[i * 4 + 3] = 255;
        }
        c.putImageData(data, 0, 0);
        let left = w, right = 0;     // how wide the bottom row is, for the shadow
        const feetRow = rig.pad + rig.feet + 1;
        for (let x = 0; x < w; x++) if (solid(feetRow * w + x)) { left = Math.min(left, x); right = Math.max(right, x); }
        art = {cv, axis: rig.pad + rig.axis + 1.5, feet: rig.pad + rig.feet + 2, feetWide: right >= left ? right - left + 1 : rig.wide / 2};
      }
      m.propArt = {pal: m.pal, art};
      return art;
    }
    function paintRoom(now, t) {
      // Hiding places are painted on the soft canvas underneath. Going from the back to the
      // front, each one cuts its own shape out of the pals already drawn, so a pal standing
      // behind a hiding place is hidden by it and a pal in front of it is not.
      const covers = typeof PalHang === "undefined" ? [] : (state.cover || []).map(c => ({cover: c, y: c.y}));
      for (const m of [...covers, ...state.placed, ...state.room.flatMap(p => [p, ...p.buddies])].sort((a, b) => a.y - b.y)) {
        if (m.cover) {
          // Your own hidden pal ducks down behind its hiding place, with just the top peeking over.
          // Nobody else is sent where you are, so only you see this.
          const me = state.game && state.game.hiding === m.cover.key && state.room.find(p => p.me && p.tucked);
          if (me) {
            const rig = me.pup.rigOf(0), feet = roomBase(m), tall = (rig.feet - rig.top + 1) * me.pup.scale;
            g.save();
            g.beginPath(); g.rect(m.cover.x - 60, 0, 120, feet); g.clip();
            if (!rig.empty) me.pup.draw(g, 0, livePose(rig, me.pup.lifeline, t, {}), m.cover.x, feet + Math.max(0, tall - PalHang.coverHigh(m.cover) - 6));
            g.restore();
          }
          g.save(); g.globalCompositeOperation = "destination-out";
          PalHang.cutCover(g, m.cover);
          g.restore();
          continue;
        }
        if (m.placed) { paintThing(m, now, t); continue; }
        if (m.buddy) { if (!m.host.playing && !m.host.concealed && !m.host.prop) paintBuddy(m, now, t); continue; }
        if (m.concealed) { if (m.tag) m.tag.style.display = "none"; continue; }
        if (m.prop) {          // prop hunt: the drawing turned into a piece of the scenery, no face, no tag
          const art = propSprite(m);
          if (art) {
            const x = Math.round(m.x), base = Math.round(roomBase(m));
            g.fillStyle = "#234a3526";     // the same soft shadow the hiding places have
            g.beginPath(); g.ellipse(x, base + 2, Math.max(6, art.feetWide / 2 + 3), Math.max(2, art.feetWide / 8), 0, 0, Math.PI * 2); g.fill();
            g.save(); g.translate(x, base); g.scale(m.flip ? -1 : 1, 1);
            g.drawImage(art.cv, -art.axis, -art.feet);
            g.restore();
          }
          if (m.me && host) placeTag(m); else if (m.tag) m.tag.style.display = "none";
          continue;
        }
        if (m.tucked) {
          if (m.me && host) placeTag(m);
          continue;
        }
        const frame = roomFrame(m.pup, m.move, now), rig = m.pup.rigOf(frame), held = (now - m.moveFrom) / ROOM_LASTS[m.move];
        const moveName = m.move === "nap" ? "sleep" : m.move === "spin" ? null : m.move || m.rest;
        const pose = livePose(rig, m.pup.lifeline, t + m.seat * 1.3, {move: moveName, moveT: (now - m.moveFrom) / 1000, jump: Math.min(1, held || 0),
                                                                       mood: m.mood, talk: now < m.talkUntil});
        const hop = m.move === "jump" ? Math.sin(Math.min(1, held) * Math.PI) * (m.bigHop ? 90 : 44) : 0;
        m.hop = hop;
        const squeeze = m.move === "spin" ? Math.cos(held * Math.PI * 4) : 1;
        m.pup.draw(g, frame, pose, m.x, roomBase(m) - hop, {flip: m.flip, squeeze});
        if (Math.abs(squeeze) > .4) drawWear(m, roomBase(m) - hop);
        if (m.rest === "read" && !m.move && !rig.empty) drawBook(m, rig);
        if (host) placeTag(m);
      }
      for (const star of stars) {
        const y = starY(star, now);
        if (y < -10) continue;
        const bob = calm ? 0 : Math.round(Math.sin(now / 220 + star.id) * 2);
        g.drawImage(PROPS.star, Math.round(star.x - PROPS.star.width / 2), Math.round(y) + bob);
      }
    }
    function placeTag(m) {
      if (!m.tag) {
        m.tag = document.createElement("div");
        m.tag.className = "tag" + (m.me ? " me" : "");
        m.tag.textContent = m.name;
        host.appendChild(m.tag);
      }
      m.tag.textContent = m.tucked && m.me ? "You · Hidden" : m.hid && m.me ? "You · Name hidden" : m.name + (m.role ? " · " + m.role : "");
      const x = m.x - state.camX;
      m.tag.style.display = x < -30 || x > W + 30 || (m.hid && !m.me) ? "none" : "";
      m.tag.style.left = x / W * 100 + "%";
      m.tag.style.top = (roomBase(m) + 2) / H * 100 + "%";
    }
    /** Words that float up from a spot on the stage: claps, combos, new friends. */
    function floatUp(text, x, y, kind = "") {
      const onScreen = x - (state.room ? state.camX : 0);
      if (!host || onScreen < -20 || onScreen > W + 20) return;
      const el = document.createElement("div");
      el.className = "float " + kind;
      el.textContent = text;
      el.style.left = Math.max(6, Math.min(94, onScreen / W * 100)) + "%";
      el.style.top = y / H * 100 + "%";
      host.appendChild(el);
      setTimeout(() => el.remove(), 1500);
    }
    function roomFx(name, x) {
      state.x = x;
      if (name === "hearts") pictureRain(HEART, 18);
      else if (name === "stars") pictureRain(TWINKLE, 16);
      else if (name === "confetti") burst(i => ({x: x - W / 2 + Math.random() * W, y: -Math.random() * 60, vx: (Math.random() - .5), vy: 1 + Math.random() * 1.4,
                                                 colour: ["#ff5fa2", "#ffd93b", "#35d0bd", "#7ab8ff", "#c5a3ff"][i % 5], w: 3, h: 3, life: 2400}), 90);
      else if (name === "petals") burst(i => ({x: x - W / 2 + Math.random() * W, y: -Math.random() * 90, vx: .4 + Math.random() * .6, vy: .6 + Math.random() * .7,
                                               colour: ["#ff8fc7", "#ffc9e3", "#ffffff"][i % 3], w: 3, h: 2, life: 3200}), 70);
      else if (name === "bouquet") sparks.push({x: x - 8, y: GROUND_TOP - 20, vx: x < W / 2 ? 1.3 : -1.3, vy: -3.4, g: .075, img: BOUQUET, life: 1900});
      else if (name === "cake") sparks.push({x: x - 14, y: GROUND_TOP - 8, vy: 0, img: PROPS.cake, life: 6000});
      else if (name === "march" || name === "bells") burst(i => ({x: x - 130 + Math.random() * 260, y: GROUND_TOP - 10 - Math.random() * 40, vy: -.5, vx: (Math.random() - .5) * .4, img: NOTE, life: 1700}), name === "march" ? 14 : 8);
    }
    const TOY_FX = {
      splash: {ink: ["#8ed6e0", "#d9f4f7", "#ffffff"], sound: "whoosh", word: "Splash!"}, bounce: {ink: ["#ffd93b", "#ff8fc7"], sound: "boing", word: "Boing!", jump: true},
      apples: {ink: ["#e8553f", "#f2b56b"], sound: "pop", word: "Apples!", fall: true}, bells: {ink: ["#ffd93b", "#ffffff"], sound: "bells", word: "Ding dong!"},
      cake: {ink: ["#ff8fa8", "#fffdf6"], sound: "tada", word: "Yum!"}, petals: {ink: ["#ff8fc7", "#ffc9e3"], sound: "whoosh", word: "So pretty!", fall: true},
      sand: {ink: ["#e9cf95", "#f8ecc9"], sound: "pop", word: "Sand castle!"}, coconut: {ink: ["#8a6a4a", "#62b083"], sound: "drum", word: "Bonk!", fall: true},
      sparks: {ink: ["#ffa95c", "#ffe39a"], sound: "whoosh", word: "Whoosh!"}, fireflies: {ink: ["#fff2a0", "#fff8c8"], sound: "ding", word: "Glowy!"},
      stars: {ink: ["#ffd93b", "#ffffff", "#c5a3ff"], sound: "ding", word: "Wow, stars!"}, snow: {ink: ["#ffffff", "#d6ecfa"], sound: "whoosh", word: "Brrr!", fall: true},
      candy: {ink: ["#ff8fa8", "#ffd27a", "#8fd0c8"], sound: "yay", word: "Sweet!", fall: true}, rocket: {ink: ["#ffa95c", "#ffe39a", "#ffffff"], sound: "fanfare", word: "Blast off!"},
    };
    // A toy goes off for everyone, once the pal has walked over to it.
    function playToy(m, name, now) {
      const fx = TOY_FX[name], base = roomBase(m);
      if (fx.fall) burst(i => ({x: m.x - 34 + Math.random() * 68, y: base - 90 - Math.random() * 30, vx: 0, vy: 1 + Math.random(), g: .04, colour: fx.ink[i % fx.ink.length], w: 3, h: 3, life: 1500}), 30);
      else pop(m.x, base - 28, fx.ink, 30);
      if (name === "rocket") sparks.push({x: m.x - 12, y: base - 60, vy: -2.6, img: PROPS.rocket, life: 2400});
      floatUp(fx.word, m.x, base - 74);
      setMove(m, fx.jump ? "jump" : "cheer", now);
      m.bigHop = !!fx.jump;
      if (m.toySound) SFX.play(fx.sound);
    }
    const FX_SOUND = {hearts: "ding", stars: "ding", confetti: "yay", petals: "whoosh", bouquet: "whoosh", bells: "bells", march: "march", cake: "tada"};
    /** One thing that happened in the room. `sound` is off for other people's taps. */
    function roomApply(e, sound) {
      if (!state.room) return;
      const m = state.room.find(x => x.seat === e.seat), now = performance.now();
      if (e.kind === "join") {
        if (!state.room.some(x => x.seat === e.member.seat)) state.room.push(roomMember(e.member, state.you));
      } else if (e.kind === "leave" && m) {
        clearTag(m);
        clearBubble("s" + m.seat);
        state.room = state.room.filter(x => x !== m);
      } else if (e.kind === "walk" && m) {
        m.tx = e.x; m.ty = e.y; m.fiveWith = 0; m.rest = m.restNext = m.toyNext = null;
        if (m.queue) endMove(m, now);
      } else if (e.kind === "toy" && m) {
        m.tx = e.x; m.ty = e.y; m.fiveWith = 0; m.rest = m.restNext = null; m.toyNext = e.name; m.toySound = sound;
        if (m.queue) endMove(m, now);
      } else if (e.kind === "go" && m) {
        m.x = m.tx = e.x; m.y = m.ty = e.y; m.rest = m.restNext = m.toyNext = null;
        for (const b of m.buddies) { b.x = b.tx = clampX(e.x + (b.seat % 2 ? 30 : -30)); b.y = b.ty = e.y; }
        pop(m.x, roomBase(m) - 28, ["#ffffff", "#ffd93b", "#c5a3ff"]);
        if (sound) SFX.play("whoosh");
      } else if (e.kind === "place") {
        const thing = placedThing(Object.assign({}, e.item, {mine: e.seat === state.you}));
        state.placed.push(thing);
        pop(thing.x, roomBase(thing) - 20, ["#ff8fc7", "#ffd93b", "#35d0bd"]);
        if (sound) SFX.play("pop");
      } else if (e.kind === "unplace") {
        state.placed = state.placed.filter(p => !e.ids.includes(p.id));
      } else if (e.kind === "recode") {
        const at = state.placed.findIndex(p => p.id === e.item.id);
        if (at >= 0) state.placed[at] = placedThing(Object.assign({}, e.item, {mine: state.placed[at].mine}));
      } else if (e.kind === "poke") {
        const th = state.placed.find(p => p.id === e.piece);
        if (th) { th.queue = e.steps.slice(); th.queueAt = now; th.qSound = sound || hooks.everySound; }
      } else if (e.kind === "found" && m) {
        pop(m.x, roomBase(m) - 28, ["#7ab8ff", "#ffffff", "#ff8fc7"]);
        floatUp("💎", m.x, roomBase(m) - 70, "combo");
        if (sound) SFX.play("gift");
      } else if (e.kind === "cast" && m) {
        m.flip = false;
        floatUp("🎣", m.x, roomBase(m) - 70, "combo");
        if (sound) SFX.play("whoosh");
      } else if (e.kind === "fished" && m) {
        pop(m.x, roomBase(m) - 40, ["#8ed6e0", "#d9f4f7", "#ffffff"]);
        floatUp(e.icon, m.x, roomBase(m) - 74, "combo");
        setMove(m, "cheer", now);
        if (sound) SFX.play("gift");
      } else if (e.kind === "rest" && m) {
        m.tx = e.x; m.ty = e.y; m.fiveWith = 0; m.rest = null; m.restNext = e.name;
        if (m.queue) endMove(m, now);
        if (sound) SFX.play("pop");
      } else if (e.kind === "move" && m) {
        setMove(m, e.name, now);
        if (sound) SFX.play(MOVE_SOUND[e.name]);
      } else if (e.kind === "feel" && m) {
        m.mood = e.name === "calm" ? null : e.name;
        if (sound) SFX.play("pop");
      } else if (e.kind === "say" && m) {
        say(m, e.text, now, sound);
      } else if (e.kind === "fx") {
        roomFx(e.name, e.x || W / 2);
        if (sound) SFX.play(FX_SOUND[e.name]);
      } else if (e.kind === "pal" && m) {
        m.size = e.pal.size;
        m.pal = e.pal;
        m.pup = memberPuppet(e.pal, m.seat);
        m.buddies = buddiesOf(m, e.buddies);
        pop(m.x, roomBase(m) - 28, ["#ff8fc7", "#ffd93b", "#ffffff"]);
        if (sound) SFX.play("pop");
      } else if (e.kind === "prop" && m) {
        m.prop = !!e.on;
        if (m.tag) m.tag.style.display = m.prop && !m.me ? "none" : "";
        pop(m.x, roomBase(m) - 28, ["#ffffff", "#d3d0dc"]);
        if (sound) SFX.play("pop");
      } else if (e.kind === "name" && m) {
        m.name = e.name; m.hid = !!e.hid;
        if (m.tag && !m.me) m.tag.style.display = m.hid ? "none" : "";
      } else if (e.kind === "wear" && m) {
        m.wear = e.wear;
        if (sound) SFX.play("pop");
      } else if (e.kind === "mymove" && m) {
        m.moodBefore = m.mood;
        m.rest = m.restNext = null;
        m.queue = e.steps.slice();
        m.queueAt = now + 250;
        m.qSound = sound;
        m.trail = e.loop;
        m.bigFinish = e.big;
        m.spotUntil = now + e.ms + 700;
        m.claps = 0;
        if (sound) SFX.play("tada");
      } else if (e.kind === "clap" && m) {
        m.claps = e.claps;
        floatUp(calm ? "👏" : ["👏", "👏👏", "🙌"][e.claps % 3], m.x - 22 + Math.random() * 44, roomBase(m) - 56, "clap");
        if (sound || hooks.everySound) SFX.play("clap");
      } else if (e.kind === "five" && m) {
        m.tx = e.x; m.ty = e.y; m.fiveWith = e.other; m.rest = m.restNext = null;
        if (m.queue) endMove(m, now);
      } else if (e.kind === "shower") {
        stars = e.stars.map(fallingStar);
        if (hooks.everySound || state.you) SFX.play("gift");
      } else if (e.kind === "shower_end") {
        stars = [];
      } else if (e.kind === "catch") {
        const star = stars.find(s => s.id === e.star);
        stars = stars.filter(s => s.id !== e.star);
        const x = star ? star.x : m ? m.x : W / 2;
        pop(x, STAR_REST, ["#ffd93b", "#fff2a6", "#ffffff"], 14);
        if (m) floatUp(e.combo > 1 ? `×${e.combo}` : "+1", x, STAR_REST - 14, e.combo > 1 ? "combo" : "");
        if (sound) SFX.climb(e.combo);
      } else if (e.kind === "party") {
        for (const pal of state.room) { pal.move = "dance"; pal.moveFrom = now; pal.until = now + 8000; }
        roomFx("confetti", state.camX + W / 2);
        setTimeout(() => { if (state.room) roomFx("confetti", state.camX + W / 2); }, 1400);
        if (state.you || hooks.everySound) SFX.play("party");
      }
    }

    // The audience: a row of heads along the front of the theatre.
    function paintCrowd() {
      if (state.scene !== "stage") return;
      const colours = ["#2a1140", "#35174f", "#2f1447"];
      for (let i = 0; i < 16; i++) {
        const hop = crowd > 0 ? Math.abs(Math.sin(performance.now() / 110 + i * 1.3)) * 5 : 0;
        const x = i * 22 - 4, y = 166 - hop + (i % 2) * 3;
        g.fillStyle = colours[i % 3];
        g.fillRect(x + 3, y, 14, 10); g.fillRect(x, y + 8, 20, 12);
      }
    }

    // However many hands are on the button, there's always a stage left to see.
    function burst(make, count) { for (let i = 0; i < (calm ? Math.min(count, 6) : count) && sparks.length < 220; i++) sparks.push(make(i)); }
    function step(dt) {
      for (const p of sparks) {
        p.x += (p.vx || 0) * dt / 16; p.y += (p.vy || 0) * dt / 16;
        p.vy += (p.g || 0) * dt / 16;
        p.life -= dt;
      }
      sparks = sparks.filter(p => p.life > 0 && p.y < H + 8);
      if (crowd > 0) crowd -= dt;
    }

    let last = 0;
    function frameLoop(now) {
      loop = requestAnimationFrame(frameLoop);
      const dt = Math.min(50, now - (last || now));
      step(dt);
      if (state.room) roomStep(dt, performance.now());
      last = now;
      paint();
    }

    // ---- Speech bubbles, in page text so they stay sharp ---------------------------------
    function bubble(who, text, ms) {
      if (!host) return;
      if (bubbles[who]) bubbles[who].el.remove();
      const el = document.createElement("div");
      el.className = "bubble" + (who === "pal" ? "" : " friend");
      el.textContent = text;
      host.appendChild(el);
      bubbles[who] = {el, until: performance.now() + ms};
    }
    function placeBubbles() {
      const now = performance.now();
      for (const who of Object.keys(bubbles)) {
        const b = bubbles[who];
        if (now > b.until) { b.el.remove(); delete bubbles[who]; continue; }
        const thing = who[0] === "t" && (state.placed || []).find(p => "t" + p.id === who);
        const inRoom = (state.room || []).find(c => "s" + c.seat === who) || thing;
        const m = inRoom || state.crew.find(c => c.kind === who);
        const x = (m ? m.x : state.x) - (inRoom ? state.camX : 0);
        b.el.style.display = x < -30 || x > W + 30 ? "none" : "";
        const left = Math.max(16, Math.min(84, x / W * 100));
        const tall = m ? 64 : palW * state.size;
        const floor = inRoom ? roomBase(inRoom) + 6 : FLOOR;
        const top = Math.max(2, (floor - tall - 12 - (m ? m.hop || (inRoom ? 0 : m.y) : state.y)) / H * 100);
        b.el.style.left = left + "%";
        b.el.style.top = top + "%";
      }
    }
    function clearBubbles() {
      for (const who of Object.keys(bubbles)) bubbles[who].el.remove();
      bubbles = {};
    }

    // ---- Timing --------------------------------------------------------------------------
    function sleep(ms, token) {
      return tween(ms, token, () => {});
    }
    // Time runs faster once `rate` goes up, even halfway through a move.
    function tween(ms, token, each) {
      return new Promise(resolve => {
        let done = 0, last = performance.now();
        const tick = now => {
          done += (now - last) * rate;
          last = now;
          if (token !== run) { resolve(); return; }      // a newer move took over
          const t = Math.min(1, done / ms);
          each(t);
          if (t >= 1) resolve(); else requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });
    }

    // A pal who has drawn its own walk frames uses them. Everyone else uses legs.
    const walkFrames = () => names.map((n, i) => n === "walk" ? i : -1).filter(i => i >= 0);
    async function babble(ms, t) {
      let said = -1;
      await tween(ms, t, u => {
        const n = Math.floor(u * ms / 95);
        if (n !== said) { said = n; if (rate === 1) SFX.play("blip"); }
      });
    }
    async function moving(name, ms, t) {
      state.move = name;
      state.moveFrom = performance.now();
      await sleep(ms, t);
      if (t === run) state.move = null;
    }

    function fall(kind, count, colours) {
      burst(() => ({x: Math.random() * W, y: -Math.random() * 90, vx: kind === "snow" ? (Math.random() - .5) * .5 : -.5,
                    vy: kind === "snow" ? .7 + Math.random() * .6 : 4, colour: colours[0],
                    w: kind === "snow" ? 2 : 1, h: kind === "snow" ? 2 : 5, life: 2600}), count);
    }
    function pictureRain(img, count) {
      const s = state;
      burst(() => ({x: s.x - 40 + Math.random() * 80, y: FLOOR - 20 - Math.random() * 40, vx: (Math.random() - .5) * 1.4,
                    vy: -1 - Math.random() * 1.6, g: .012, img, life: 1300 + Math.random() * 500}), count);
    }
    function pop(x, y, colours, count = 22) {
      burst(i => ({x, y, vx: (Math.random() - .5) * 4, vy: -Math.random() * 3.2, g: .1,
                   colour: colours[i % colours.length], w: 3, h: 3, life: 900}), count);
    }

    // ---- What each step looks like --------------------------------------------------------
    const PLAY = {
      async walk(s, t) {
        const from = state.x, to = spotX(s.to), squares = Math.max(1, Math.round(Math.abs(to - from) / 26.8) || s.by || 0);
        if (to !== from) state.flip = to < from;
        const drawn = walkFrames(), rest = state.frame;
        if (!drawn.length) { state.move = "walk"; state.moveFrom = performance.now(); }
        let beat = -1;
        await tween(170 * squares, t, u => {
          state.x = from + (to - from) * u;
          const n = Math.floor(u * squares * 2);
          if (n !== beat) {
            beat = n;
            SFX.play("step");
            if (drawn.length) state.frame = [rest, ...drawn][n % (drawn.length + 1)];
          }
        });
        if (t !== run) return;
        state.move = null;
        state.spot = s.to;
        state.frame = rest;
      },
      async jump(s, t) {
        const named = names.indexOf("jump"), rest = state.frame;
        if (named >= 0) state.frame = named;
        state.move = "jump";
        state.jump = 0;
        await tween(110, t, u => { state.jump = u * .2; });
        SFX.play("jump");
        await tween(400, t, u => { state.jump = .2 + u * .65; state.y = Math.sin(u * Math.PI) * 46; });
        state.y = 0;
        await tween(110, t, u => { state.jump = .85 + u * .15; });
        if (t !== run) return;
        state.move = null;
        state.frame = rest;
      },
      async giggle(s, t) { SFX.play("boing"); pictureRain(HEART, 5); await moving("giggle", 760, t); },
      async wave(s, t) { SFX.play("ding"); await moving("wave", 1200, t); },
      async dance(s, t) { SFX.play("jig"); await moving("dance", 1800, t); },
      async cheer(s, t) { SFX.play("yay"); await moving("cheer", 1200, t); },
      async look(s, t) {
        const way = {left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1]}[s.way] || null;
        // Facing the other way, its left is the stage's right.
        state.aim = way && state.flip ? [-way[0], way[1]] : way;
        SFX.play("click");
        await sleep(420, t);
      },
      async feel(s, t) {
        state.mood = s.mood;
        SFX.play("pop");
        await tween(260, t, u => { state.y = Math.sin(u * Math.PI) * 5; });
        state.y = 0;
      },
      async spin(s, t) {
        SFX.play("whoosh");
        await tween(560, t, u => { state.squeeze = Math.cos(u * Math.PI * 4); });
        state.squeeze = 1;
      },
      async shake(s, t) {
        await tween(420, t, u => { state.shakeX = Math.sin(u * 30) * 4 * (1 - u); });
        state.shakeX = 0;
      },
      async size(s, t) {
        const from = state.size, to = [1, 1.5, 2][s.to - 1];
        SFX.play("pop");
        await tween(300, t, u => { state.size = from + (to - from) * u; });
      },
      async hide(s, t) {
        SFX.play("pop");
        pop(state.x, FLOOR - 30, ["#ffffff", "#d3d0dc", "#c5a3ff"]);
        state.visible = false;
        await sleep(300, t);
      },
      async appear(s, t) {
        SFX.play("pop");
        state.visible = true;
        pop(state.x, FLOOR - 30, ["#ffffff", "#ffd93b", "#ff8fc7"]);
        await sleep(300, t);
      },
      async pose(s, t) {
        state.frame = s.frame;
        SFX.play("pop");
        await tween(220, t, u => { state.y = Math.sin(u * Math.PI) * 6; });
        state.y = 0;
      },
      async play(s, t) {
        if (pup.frames < 2) { await moving("happy", 500, t); return; }     // nothing to flip through
        const fps = livePal.speed || 6;
        for (let i = 0; i < pup.frames; i++) {
          state.frame = i;
          await sleep(1000 / fps, t);
        }
        state.frame = 0;
      },
      async wait(s, t) { await sleep(450 * s.beats, t); },
      async say(s, t) {
        const ms = Math.min(5200, 900 + s.text.length * 55);     // long enough to read
        bubble("pal", s.text, ms / rate);
        SFX.voiceAt(palVoice);
        state.talk = true;
        await babble(Math.min(ms, 300 + s.text.length * 70), t);
        state.talk = false;
        await sleep(Math.max(0, ms - (300 + s.text.length * 70)), t);
      },
      async friend_say(s, t) {
        const m = member(s.who);
        if (!m) return;
        const ms = Math.min(5200, 900 + s.text.length * 55);     // long enough to read
        bubble(m.kind, s.text, ms / rate);
        SFX.voiceAt(palVoice * (1.2 + (m.kind.length % 4) * .12));
        m.talk = true;
        await babble(Math.min(ms, 300 + s.text.length * 70), t);
        m.talk = false;
        await sleep(Math.max(0, ms - (300 + s.text.length * 70)), t);
      },
      async friend(s, t) {
        if (s.pal) friendPups[s.kind] = puppet(s.pal, Math.max(1, Math.floor(48 / s.pal.size)), s.kind.length * 41 + 3);
        if (s.stand_in) friendPups[s.kind] = friendPup(s.stand_in);
        // Friends line up from the far side of the stage, so there's room for each.
        const right = state.spot <= 7, slot = state.crew.length;
        const home = spotX(right ? 9.5 - slot * 1.9 : .5 + slot * 1.9), edge = right ? W + 40 : -40;
        const m = {kind: s.kind, x: edge, y: 0, move: "walk", talk: false};
        state.crew.push(m);
        state.friend = s.kind;
        await tween(520, t, u => { m.x = edge + (home - edge) * u; });
        m.move = null;
      },
      async friend_jump(s, t) {
        const m = member(s.who);
        if (!m) return;
        SFX.play("jump");
        await tween(430, t, u => { m.y = Math.sin(u * Math.PI) * 40; });
        m.y = 0;
      },
      async bye(s, t) {
        const m = member(s.who);
        if (!m) return;
        const from = m.x, edge = from < W / 2 ? -40 : W + 40;
        m.move = "walk";
        await tween(460, t, u => { m.x = from + (edge - from) * u; });
        state.crew = state.crew.filter(c => c !== m);
        state.friend = state.crew.length ? state.crew[state.crew.length - 1].kind : null;
        clearBubble(m.kind);
      },
      async everyone(s, t) {
        const move = {dance: "dance", wave: "wave", cheer: "cheer", jump: "happy"}[s.move];
        SFX.play(s.move === "dance" ? "jig" : "yay");
        for (const m of state.crew) m.move = move;
        await moving(move, 1800, t);
        for (const m of state.crew) m.move = null;
      },
      async hearts(s, t) { SFX.play("ding"); pictureRain(HEART, 16); await sleep(800, t); },
      async stars(s, t) { SFX.play("ding"); pictureRain(TWINKLE, 16); await sleep(800, t); },
      async confetti(s, t) {
        SFX.play("yay");
        burst(i => ({x: Math.random() * W, y: -Math.random() * 60, vx: (Math.random() - .5) * 1, vy: 1 + Math.random() * 1.4,
                     colour: ["#ff5fa2", "#ffd93b", "#35d0bd", "#7ab8ff", "#c5a3ff"][i % 5], w: 3, h: 3, life: 2400}), 90);
        await sleep(1000, t);
      },
      async rain(s, t) { fall("rain", 90, ["#7ab8ff"]); await sleep(1000, t); },
      async snow(s, t) { fall("snow", 70, ["#ffffff"]); await sleep(1000, t); },
      async sound(s, t) { SFX.play(s.name); await sleep(260, t); },
      async scene(s, t) {
        await tween(170, t, u => { canvas.style.filter = `brightness(${1 - u * .8})`; });
        state.scene = s.name;
        await tween(170, t, u => { canvas.style.filter = `brightness(${.2 + u * .8})`; });
        canvas.style.filter = "";
      },
      async eat(s, t) {
        SFX.play("eat");
        pictureRain(PROPS.cake, 1);
        state.talk = true;
        await tween(420, t, u => { state.squeeze = 1 + Math.sin(u * 18) * .08; });
        state.talk = false;
        state.squeeze = 1;
      },
      async nap(s, t) {
        const was = state.tilt;
        state.move = "sleep";
        state.moveFrom = performance.now();
        await tween(260, t, u => { state.tilt = u * .32; });
        burst(i => ({x: state.x + 14, y: FLOOR - 50, vx: .3, vy: -.5, img: ZED, life: 900 + i * 350}), 3);
        await sleep(1200, t);
        await tween(260, t, u => { state.tilt = (1 - u) * .32; });
        if (t !== run) return;
        state.move = null;
        state.tilt = was;
      },
      async noop() {},
      async snooze(s, t) {
        burst(i => ({x: state.x + 14, y: FLOOR - 50, vx: .3, vy: -.5, img: ZED, life: 900 + i * 350}), 2);
        await sleep(1800, t);
      },
      async put(s, t) {
        SFX.play("pop");
        state.props[s.at] = s.prop;
        await sleep(160, t);
      },
      async take(s, t) {
        const prop = state.props[s.at];
        delete state.props[s.at];
        if (prop) {
          SFX.play("ding");
          const x = spotX(s.at);
          sparks.push({x: x - 7, y: FLOOR - 26, vy: -1.6, img: PROPS[prop], life: 620});
        }
        await sleep(160, t);
      },
      async point(s, t) {
        state.score = s.score;
        SFX.play("ding");
        await sleep(200, t);
      },
      async mark(s) { state.marks.push(s.at); },
      async place(s) { state.spot = s.at; state.x = spotX(s.at); },
      async weather(s, t) { state.weather = s.kind; SFX.play("whoosh"); await sleep(300, t); },
      async event(s, t) {
        SFX.play("click");
        pop(state.x, FLOOR - 40, ["#ffffff", "#ffd93b"], 10);
        await sleep(320, t);
      },
    };
    // The friend a step means: the named one, or else the newest.
    function member(who) { return who ? state.crew.find(c => c.kind === who) : state.crew[state.crew.length - 1]; }
    function clearBubble(who) { if (bubbles[who]) { bubbles[who].el.remove(); delete bubbles[who]; } }

    return {
      setPal,
      fresh() {
        run++; rate = 1;
        roomStop();
        state = fresh();
        sparks = []; crowd = 0;
        clearBubbles();
        canvas.style.filter = "";
        if (!loop) loop = requestAnimationFrame(frameLoop);
      },
      /** Play steps in order. Resolves true if they all ran, false if stopped. */
      async play(steps, options = {}) {
        const token = ++run;
        rate = 1;
        // Whatever was going on stops here, wherever it had got to.
        Object.assign(state, {move: null, y: 0, tilt: 0, squeeze: 1, shakeX: 0, talk: false});
        for (const m of state.crew) Object.assign(m, {move: null, talk: false, y: 0});
        clearBubbles();
        for (const s of steps) {
          if (token !== run) return false;
          if (options.onStep) options.onStep(s);
          const fn = PLAY[s.do];
          if (fn) await fn(s, token);
        }
        return token === run;
      },
      /** Do one move straight away, for pals who are being poked. */
      act(name) {
        const token = ++run;
        rate = 1;
        const fn = PLAY[name];
        return fn ? fn({mood: name}, token) : Promise.resolve();
      },
      /** Look towards this point on the stage (0 to W), or stop. */
      aim(x, y) {
        if (x === null) { state.aim = null; return; }
        const gx = x - state.x, gy = y - (FLOOR - palW / 2);
        state.aim = [Math.abs(gx) > 14 ? Math.sign(gx) * (state.flip ? -1 : 1) : 0, Math.abs(gy) > 22 ? Math.sign(gy) : 0];
      },
      roomStart, roomApply, roomStop, roomYou, roomSync,
      /** What the page wants to know about: `caught(star)`, `moveEnded(pal)`, `everySound`. */
      roomHooks(h) { hooks = h; },
      /** Is this point on the stage on the pal? */
      touching(x, y) {
        return Math.abs(x - state.x) < palW / 2 + 6 && y > FLOOR - palW - state.y - 6 && y < FLOOR + 8 - state.y;
      },
      get state() { return state; },
      hurry() { rate = 6; },
      stop() { run++; clearBubbles(); },
      cheer() { crowd = 2400; SFX.play("yay"); pictureRain(HEART, 10); },
      sigh() { SFX.play("nope"); },
      get spot() { return state ? state.spot : 2; },
    };
  }

  const HEART = rowsSprite([".kk.kk.", "krrkrrk", "krrrrrk", ".krrrk.", "..krk..", "...k..."], {k: "#1b1530", r: "#ff5fa2"});
  const TWINKLE = rowsSprite(["...y...", "...y...", "..yyy..", "yyyyyyy", "..yyy..", "...y...", "...y..."], {y: "#ffd93b"}, 2);
  const NOTE = rowsSprite(["..kkk", "..k.k", "..k..", "kkk..", "kkk.."], {k: "#c2258c"}, 2);
  const BOUQUET = rowsSprite(["..pyp..", ".pyrpy.", "pyrpypy", ".prypr.", "..ggg..", "..ggg..", "...g..."], {p: "#ff8fc7", y: "#ffd93b", r: "#ff5fa2", g: "#2fa84f"}, 2);
  const ZED = rowsSprite(["kkkkk", "...k.", "..k..", ".k...", "kkkkk"], {k: "#1b1530"});
  const WEAR_SPRITES = {};
  for (const [key, {rows, ink}] of Object.entries(WEAR_ART)) WEAR_SPRITES[key] = rowsSprite(rows, ink);
  // Sparkles get a little star in their own colours.
  for (const [key, ink] of Object.entries(SPARKLE_INK)) {
    const dots = {};
    ink.forEach((c, i) => { dots["abcde"[i]] = c; });
    const at = ["....a....", "...aba...", "c..aba..d", ".aabbbaa.", "abbbbbbba", ".aabbbaa.", "e..aba..c", "...aba...", "....a...."];
    WEAR_SPRITES[key] = rowsSprite(at.map(r => r.replace(/[cde]/g, ch => (dots[ch] ? ch : "."))), dots);
  }
  /** A small picture of something to wear. */
  function wearPicture(key) { return WEAR_SPRITES[key] || null; }
  const PROPS = {};
  for (const [key, {rows, ink}] of Object.entries(PROP_ART)) PROPS[key] = rowsSprite(rows, ink, 2);
  PROPS.rocket = rowsSprite(["...rr...", "..rwwr..", "..wwww..", "..wbbw..", "..wbbw..", "..wwww..", ".rwwwwr.", "rrwwwwrr", "r.oyyo.r", "...oo..."],
                            {r: "#ff8fa8", w: "#f5f2ff", b: "#7fc8dc", o: "#ffa95c", y: "#ffe39a"}, 2);

  // Keeps a stage up to date with the Hang out. The server holds each request until
  // there's news, so a tap shows up everywhere straight away.
  // `loc` is for the class screen: which home to look into, or 0 for outside.
  function follow(stage, {id = "", everySound = false, onState = () => {}, loc = () => 0} = {}) {
    let after = -1, going = true, asked = null, wait = null;
    (async () => {
      while (going) {
        const where = loc();
        if (where !== asked) { asked = where; after = -1; }
        wait = new AbortController();
        const url = `/pixel/room?after=${after}&wait=1${id ? "&id=" + encodeURIComponent(id) : ""}${where ? "&loc=" + where : ""}`;
        const data = await fetch(url, {signal: wait.signal}).then(r => r.json()).catch(() => null);
        if (!going) return;
        if (loc() !== asked) continue;        // the screen moved while waiting: ask again for the new place
        if (!data) { await new Promise(r => setTimeout(r, 1500)); continue; }
        stage.state.places = data.places;
        stage.state.game = data.game;
        stage.state.cover = data.cover || [];
        stage.state.home = data.home || null;
        if (data.members) stage.roomStart(data, data.you);
        for (const e of data.events) stage.roomApply(e, everySound || e.seat === data.you);
        if (data.game_members) stage.roomSync(data.game_members, data.you);
        stage.roomYou(data.you);
        onState(data);
        after = data.open ? data.seq : -1;
        if (!data.open) await new Promise(r => setTimeout(r, 2000));
      }
    })();
    const stop = () => { going = false; };
    stop.now = () => wait && wait.abort();     // stop waiting and ask again straight away
    return stop;
  }

  return {create, puppet, livePose, follow, sceneArt, wearPicture, groundOf, HEART, PROPS, SFX, W, H, GROUND_TOP, GROUND_DEEP,
          get calm() { return calm; },
          set calm(on) { calm = on; try { localStorage.setItem("pixelCalm", on ? "1" : "0"); } catch (_) {} }};
})();

if (typeof module !== "undefined") module.exports = PalStage;
