// Pixel Pals: the stage. It draws at 320 by 180 and scales up with hard edges,
// so scenes, pals and sparkles all share the same chunky pixels. The student
// page, the Theatre and the projector all play shows with this one file.
"use strict";

const PalStage = (() => {
  const W = 320, H = 180, FLOOR = 158;
  const spotX = spot => 26 + spot * 26.8;

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
    };
    return {
      wake,
      /** Each pal has its own pitch to talk at. */
      voiceAt(pitch) { voice = pitch; },
      play(name) { if (!muted && wake() && SOUNDS[name]) SOUNDS[name](); },
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
    return {rigOf, picture, lifeline, scale, frames: frames.length,
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
              move: null, moveFrom: 0, jump: 0, mood: null, talk: false, aim: null, bow: null,
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
      g.drawImage(sceneArt(s.scene), 0, 0);
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
      if (s.room) paintRoom(now, t);
      if (s.bow) paintBow(t);
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
      if (s.score !== null) {
        g.fillStyle = "#1b1530"; g.fillRect(4, 4, 52, 15);
        g.fillStyle = "#ffd93b"; g.font = "bold 12px monospace"; g.textBaseline = "top";
        g.fillText(`★ ${s.score}`, 9, 6);
      }
      placeBubbles();
    }

    // ---- The live room: every pal moves on its own, whenever someone taps ----------
    const ROOM_LASTS = {wave: 1400, dance: 2400, cheer: 1400, nap: 3200, jump: 620, spin: 560};
    function roomMember(m, you) {
      return {seat: m.seat, name: m.name, x: m.x, y: m.y, tx: m.x, ty: m.y, flip: false, mood: m.mood, move: null, moveFrom: 0, until: 0,
              talkUntil: 0, me: m.seat === you,
              pup: puppet(m.pal, Math.max(1, Math.round((state.room && state.room.length > 11 ? 32 : 46) / m.pal.size)), m.seat + 1)};
    }
    function roomStart(data, you) {
      roomStop();
      state.visible = false;
      state.scene = data.scene || state.scene;
      state.room = data.members.map(m => roomMember(m, you));
      state.you = you;
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
      for (const key of Object.keys(bubbles)) if (key.startsWith("s")) clearBubble(key);
    }
    function clearTag(m) { if (m.tag) m.tag.remove(); }
    const roomBase = m => FLOOR - 5 + m.y * 15;
    function roomStep(dt, now) {
      for (const m of state.room) {
        const gx = m.tx - m.x, gy = m.ty - m.y, far = Math.hypot(gx, gy * 15);
        if (far > 1) {
          const go = Math.min(1, dt * .085 / far);
          m.x += gx * go; m.y += gy * go;
          if (Math.abs(gx) > 1) m.flip = gx < 0;
          if (!m.move || m.move === "walk") { if (m.move !== "walk") m.moveFrom = now; m.move = "walk"; m.until = now + 200; }
        }
        if (m.move && now > m.until) m.move = null;
      }
    }
    function paintRoom(now, t) {
      for (const m of state.room.slice().sort((a, b) => a.y - b.y)) {
        const rig = m.pup.rigOf(0), held = (now - m.moveFrom) / ROOM_LASTS[m.move];
        const moveName = m.move === "nap" ? "sleep" : m.move === "spin" ? null : m.move;
        const pose = livePose(rig, m.pup.lifeline, t + m.seat * 1.3, {move: moveName, moveT: (now - m.moveFrom) / 1000, jump: Math.min(1, held || 0),
                                                                       mood: m.mood, talk: now < m.talkUntil});
        const hop = m.move === "jump" ? Math.sin(Math.min(1, held) * Math.PI) * 44 : 0;
        m.hop = hop;
        const squeeze = m.move === "spin" ? Math.cos(held * Math.PI * 4) : 1;
        m.pup.draw(g, 0, pose, m.x, roomBase(m) - hop, {flip: m.flip, squeeze});
        if (host) placeTag(m);
      }
    }
    function placeTag(m) {
      if (!m.tag) {
        m.tag = document.createElement("div");
        m.tag.className = "tag" + (m.me ? " me" : "");
        m.tag.textContent = m.name;
        host.appendChild(m.tag);
      }
      m.tag.style.left = m.x / W * 100 + "%";
      m.tag.style.top = (roomBase(m) + 2) / H * 100 + "%";
    }
    function roomFx(name, x) {
      state.x = x;
      if (name === "hearts") pictureRain(HEART, 18);
      else if (name === "stars") pictureRain(TWINKLE, 16);
      else if (name === "confetti") burst(i => ({x: Math.random() * W, y: -Math.random() * 60, vx: (Math.random() - .5), vy: 1 + Math.random() * 1.4,
                                                 colour: ["#ff5fa2", "#ffd93b", "#35d0bd", "#7ab8ff", "#c5a3ff"][i % 5], w: 3, h: 3, life: 2400}), 90);
      else if (name === "petals") burst(i => ({x: Math.random() * W, y: -Math.random() * 90, vx: .4 + Math.random() * .6, vy: .6 + Math.random() * .7,
                                               colour: ["#ff8fc7", "#ffc9e3", "#ffffff"][i % 3], w: 3, h: 2, life: 3200}), 70);
      else if (name === "bouquet") sparks.push({x: x - 8, y: FLOOR - 50, vx: x < W / 2 ? 1.3 : -1.3, vy: -3.4, g: .075, img: BOUQUET, life: 1900});
      else if (name === "cake") {
        if (state.props[5]) delete state.props[5]; else state.props[5] = "cake";
      } else if (name === "march" || name === "bells") burst(i => ({x: 30 + Math.random() * 260, y: FLOOR - 40 - Math.random() * 40, vy: -.5, vx: (Math.random() - .5) * .4, img: NOTE, life: 1700}), name === "march" ? 14 : 7);
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
        m.tx = e.x; m.ty = e.y;
      } else if (e.kind === "move" && m) {
        m.move = e.name; m.moveFrom = now; m.until = now + ROOM_LASTS[e.name];
        if (sound) SFX.play({jump: "jump", dance: "jig", cheer: "yay", wave: "ding", spin: "whoosh", nap: "pop"}[e.name]);
      } else if (e.kind === "feel" && m) {
        m.mood = e.name === "calm" ? null : e.name;
        if (sound) SFX.play("pop");
      } else if (e.kind === "say" && m) {
        const ms = Math.min(5200, 1300 + e.text.length * 55);
        bubble("s" + m.seat, e.text, ms);
        m.talkUntil = now + Math.min(ms, 300 + e.text.length * 70);
        if (sound) { SFX.voiceAt(300 + m.seat * 53 % 320); SFX.play("blip"); }
      } else if (e.kind === "fx") {
        roomFx(e.name, e.x || W / 2);
        if (sound) SFX.play(FX_SOUND[e.name]);
      } else if (e.kind === "scene") {
        state.scene = e.name;
        state.props = {};
        if (sound) SFX.play("whoosh");
      }
    }

    // The end of a story: everyone who made it, up and dancing.
    function paintBow(t) {
      const {pups, title} = state.bow;
      g.font = "900 26px ui-rounded, system-ui, sans-serif";
      const fits = Math.min(26, Math.floor(26 * (W - 24) / g.measureText(title).width));
      g.font = `900 ${fits}px ui-rounded, system-ui, sans-serif`;
      g.textAlign = "center";
      g.textBaseline = "top";
      g.lineWidth = 5;
      g.lineJoin = "round";
      g.strokeStyle = "#1b1530";
      g.strokeText(title, W / 2, 36);
      g.fillStyle = "#ffd93b";
      g.fillText(title, W / 2, 36);
      g.textAlign = "left";
      pups.forEach((p, i) => {
        const pose = livePose(p.rigOf(0), p.lifeline, t + i, {move: i % 2 ? "dance" : "cheer", moveT: t + i * .23});
        p.draw(g, 0, pose, W * (i + 1) / (pups.length + 1), FLOOR + 4);
      });
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
    function burst(make, count) { for (let i = 0; i < count && sparks.length < 220; i++) sparks.push(make(i)); }
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
        const m = state.crew.find(c => c.kind === who) || (state.room || []).find(c => "s" + c.seat === who);
        const x = m ? m.x : state.x;
        const left = Math.max(16, Math.min(84, x / W * 100));
        const tall = m ? 64 : palW * state.size;
        const top = Math.max(2, (FLOOR - tall - 12 - (m ? m.hop || (who.startsWith("s") ? 0 : m.y) : state.y)) / H * 100);
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
      async live(s, t) {
        const {base, events} = s.live, total = (events.length ? events[events.length - 1].t : 0) + 1600;
        roomStart(base, null);
        let i = 0;
        await tween(total, t, u => {
          while (i < events.length && events[i].t <= u * total) roomApply(events[i++], true);
        });
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
      roomStart, roomApply, roomStop, roomYou,
      /** The curtain call: these pals all dance under these words. */
      bow(pals, title) {
        state.visible = false;
        const tall = pals.length > 8 ? 26 : pals.length > 4 ? 40 : 56;
        state.bow = {title, pups: pals.slice(0, 14).map((pal, i) => puppet(pal, Math.max(1, Math.floor(tall / pal.size)), i + 7))};
      },
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
  const PROPS = {};
  for (const [key, {rows, ink}] of Object.entries(PROP_ART)) PROPS[key] = rowsSprite(rows, ink, 2);

  // A whole story: each page in turn, with its line of the book, then a curtain call.
  // `ui.line(words, small)` shows the book's words. Resolves false if it was stopped.
  async function playFilm(stage, film, ui, from = 0) {
    const pause = async ms => stage.play([{do: "wait", beats: ms / 450}]);
    let place = "stage";
    if (from === 0 && film.pages.length) {
      stage.setPal(film.pages[0].pal);
      stage.fresh();
      stage.bow([], film.title);
      ui.line(film.start, film.title);
      if (!await pause(Math.min(6000, 1800 + film.start.length * 45))) return false;
    }
    for (let i = from; i < film.pages.length; i++) {
      const page = film.pages[i];
      stage.setPal(page.pal);
      stage.fresh();
      stage.state.scene = place;
      ui.line(page.line, `Page ${i + 1} by ${page.by}`);
      if (ui.page) ui.page(i);
      if (!await pause(Math.min(5000, 1400 + page.line.length * 45))) return false;
      if (!await stage.play(page.steps)) return false;
      place = stage.state.scene;
      if (!await pause(700)) return false;
    }
    // Everyone takes a bow: the authors, and any pal who came on in a page.
    const seen = new Set(), pals = [], names = [], guests = [];
    const add = (key, pal) => { if (seen.has(key)) return false; seen.add(key); pals.push(pal); return true; };
    for (const page of film.pages) if (add(page.by.toLowerCase(), page.pal)) names.push(page.by);
    for (const page of film.pages) for (const s of page.steps) {
      if (s.do === "friend" && s.pal && add(s.kind, s.pal)) guests.push(s.kind[0].toUpperCase() + s.kind.slice(1));
      if (s.do === "live") for (const m of s.live.base.members) if (add(m.name.toLowerCase(), m.pal)) guests.push(m.name);
    }
    stage.fresh();
    stage.state.scene = place;
    stage.bow(pals, "The End");
    stage.cheer();
    ui.line(`Made by ${names.join(", ")}${guests.length ? `. Starring ${guests.join(", ")}` : ""}`, film.title);
    return stage.play([{do: "confetti"}, {do: "wait", beats: 9}]);
  }

  // Keeps a stage up to date with the live room. The server holds each request until
  // there's news, so a tap shows up everywhere straight away.
  function follow(stage, {id = "", everySound = false, onState = () => {}} = {}) {
    let after = -1, going = true;
    (async () => {
      while (going) {
        const url = `/pixel/room?after=${after}&wait=1${id ? "&id=" + encodeURIComponent(id) : ""}`;
        const data = await fetch(url).then(r => r.json()).catch(() => null);
        if (!going) return;
        if (!data) { await new Promise(r => setTimeout(r, 1500)); continue; }
        if (data.members) stage.roomStart(data, data.you);
        for (const e of data.events) stage.roomApply(e, everySound || e.seat === data.you);
        stage.roomYou(data.you);
        onState(data);
        after = data.open ? data.seq : -1;
        if (!data.open) await new Promise(r => setTimeout(r, 2000));
      }
    })();
    return () => { going = false; };
  }

  return {create, puppet, livePose, playFilm, follow, sceneArt, HEART, PROPS, SFX, W, H};
})();

if (typeof module !== "undefined") module.exports = PalStage;
