// Pixel Pals: the Hang out. Everyone's pal is in one soft little world at the same
// moment, and what one child taps, everyone sees. Words are tapped from a list unless
// the teacher turns typing on.
"use strict";

let roomStage = null, stopRoom = null, stopBack = null, roomInfo = null, roomJoining = false, roomPane = "do";
let artArmed = null, moveReadyAt = 0, clapFor = null, clapTimer = 0, bannerTimer = 0, placesSeen = "";
let furnArmed = null, buyArmed = null, fishing = null, homeSeen = "", peopleSeen = "", coinsSeen = null;
const atHome = () => !!(roomInfo && roomInfo.home), myHome = () => atHome() && roomInfo.home.mine;

const ROOM_PANES = {
  do: [["👋", "Wave", "move", "wave"], ["💃", "Dance", "move", "dance"], ["🦘", "Jump", "move", "jump"], ["🎉", "Cheer", "move", "cheer"],
       ["🌀", "Spin", "move", "spin"], ["😴", "Nap", "move", "nap"], ["🪑", "Sit", "rest", "sit"], ["📖", "Read", "rest", "read"], ["😊", "Happy", "feel", "happy"], ["😢", "Sad", "feel", "sad"],
       ["😮", "Wow", "feel", "surprised"], ["😠", "Cross", "feel", "angry"], ["🤪", "Silly", "feel", "silly"], ["😎", "Cool", "feel", "cool"]],
  party: [["💕", "Hearts", "fx", "hearts"], ["🌸", "Petals", "fx", "petals"], ["🎊", "Confetti", "fx", "confetti"], ["⭐", "Stars", "fx", "stars"],
          ["💐", "Flowers", "fx", "bouquet"], ["🔔", "Bells", "fx", "bells"], ["🎵", "Wedding music", "fx", "march"], ["🎂", "Cake", "fx", "cake"]],
};
// The Python for a Hang out button, so playing shows the code that does the same thing.
function tapCode(what, name) {
  if (what === "move" && name !== "nap") return name + "()";
  if (what === "feel") return `feel("${name}")`;
  if (what === "fx" && ["hearts", "stars", "confetti"].includes(name)) return name + "()";
  return "";
}
const PLACE_NAMES = {park: ["🌳", "Park"], wedding: ["💒", "Wedding"], beach: ["🏖️", "Beach"], night: ["🌙", "Night"],
                     snowy: ["⛄", "Snowy hill"], candy: ["🍭", "Candy land"], space: ["🚀", "Space"]};
const SLOT_NAMES = {hat: "Hats", face: "Faces", sparkle: "Sparkles"};
const ROOM_TIP = "Walk to the edge to explore! Gold ring: sit. Pink ring: play. Blue ring: fish. Find the 💎 gems!";
const HOME_TIP = "Click the floor to walk. Click a door to go through it.";
// While you're in a round, the tip under the world says what to do in that game.
function gameTip(g) {
  const you = roomInfo.you, it = g.it === you;
  if (g.kind === "tag") return it ? "You're IT! Click near a friend to tag them." : "Run! Click the ground to get away from IT.";
  if (g.kind === "hide" && g.phase === "hiding") return it ? "You're counting. Everyone else is hiding!" : "Hide! Pick a hiding place on the right.";
  if (g.kind === "hide") return it ? "Click a hiding place to walk there and look." : "Stay still! The seeker is looking.";
  if (g.kind === "race") return "Green light: press Run or → again and again. Red light: stop!";
  if (g.kind === "dance") return "Tap the lit-up move on the right, in order.";
  if (g.kind === "code") return (g.bonus || []).includes(you) ? "Bonus done! Clap for your friends while they finish."
    : (g.solved || []).includes(you) ? "You solved it! Try the 🌟 Bonus on the right, or clap for your friends." : "Build your code on the right, then press ▶ Run my code.";
  return ROOM_TIP;
}
const roomTipNow = () => (atHome() ? HOME_TIP : inRound() ? gameTip(currentGame()) : ROOM_TIP);

function fitRoomScreen() {
  const host = $("roomHost"), wrap = host.parentElement, main = wrap.parentElement;
  const tall = main.clientHeight - $("meterBar").closest(".hang-meter").offsetHeight - $("roomTip").offsetHeight - $("gameStatus").offsetHeight - 62;     // the gaps and the frame
  const width = Math.min(wrap.clientWidth - 16, tall * 16 / 9);
  host.style.width = Math.max(120, Math.floor(width)) + "px";
}

function tap(what, more = {}) {
  return post("/pixel/room/do", Object.assign({id: me, what}, more)).catch(() => null);
}

// ---- The buttons ----------------------------------------------------------------------
function buildRoomButtons() {
  document.querySelectorAll("[data-pane]").forEach(b => b.setAttribute("aria-pressed", b.dataset.pane === roomPane));
  const box = $("roomButtons");
  box.classList.remove("games-pane");
  box.classList.toggle("words", roomPane === "say");
  box.classList.toggle("me-pane", ["me", "art", "shop", "home"].includes(roomPane));
  const big = ([icon, word, what, name]) => {
    const code = tapCode(what, name);
    return `<button data-tap="${what}" data-name="${name}"><span>${icon}</span>${esc(word)}${code ? `<code class="tap-code">${esc(code).replace("(", "(<wbr>")}</code>` : ""}</button>`;
  };
  if (roomPane === "games") {
    buildGamePane(box);
  } else if (roomPane === "say") {
    // Wedding words come first at the Wedding, and last everywhere else.
    const me = myMember(), here = me && !atHome() && roomStage.state.places ? roomStage.state.places[Math.floor(me.x / PalStage.W)] : "";
    const groups = Object.entries(S.room_words).sort(([a], [b]) => (here !== "wedding") * ((a === "Wedding") - (b === "Wedding")));
    box.innerHTML = groups.map(([group, words]) =>
      `<h4>${esc(group)}</h4>` + words.map(w => `<button data-tap="say" data-name="${esc(w)}">${esc(w)}</button>`).join("")).join("");
  } else if (roomPane === "place") {
    const friends = ((roomInfo && roomInfo.people) || []).filter(m => !m.loc && m.seat !== roomInfo.you);
    box.innerHTML = ((roomInfo && roomInfo.world) || ["park"]).map(n => big([...PLACE_NAMES[n], "go", n])).join("") +
      `<button data-home="mine"><span>🏠</span>My home</button>` +
      (friends.length ? `<h4>👫 Go to a friend</h4>` + friends.map(m => `<button data-friend="${m.seat}"><span>🏃</span>${esc(m.name)}</button>`).join("") : "");
  } else if (roomPane === "shop") {
    buildShopPane(box);
  } else if (roomPane === "home") {
    buildHomePane(box);
  } else if (roomPane === "me") {
    buildMePane(box);
  } else if (roomPane === "art") {
    buildArtPane(box);
  } else box.innerHTML = ROOM_PANES[roomPane].map(big).join("");
}
// ---- Coins and the shop ---------------------------------------------------------------------
function paintCoins(data) {
  if (data && data.coins !== undefined) {
    if (coinsSeen !== null && data.coins > coinsSeen) {
      const bar = $("coinBar");
      bar.classList.remove("bump"); void bar.offsetWidth; bar.classList.add("bump");
    }
    if (data.coins !== coinsSeen && roomPane === "shop") { S.hang.coins = data.coins; buildRoomButtons(); }
    coinsSeen = S.hang.coins = data.coins;
    if (data.progress) S.hang.progress = data.progress;
    const fresh = (data.owned || []).filter(key => !S.hang.gifts.includes(key));
    if (fresh.length) {
      S.hang.gifts.push(...fresh);
      const got = fresh.filter(key => S.hang.catalog[key].goal);
      if (got.length) {
        banner(`🔓 UNLOCKED! 🔓<small>${got.map(key => esc(S.hang.catalog[key].name)).join(", ")}: put it on in 🧢 Me!</small>`, 6000, true);
        PalStage.SFX.play("gift");
      }
    }
    if (fresh.length && roomPane === "me") buildRoomButtons();
    $("coinNote").textContent = data.play_left <= 0 ? "All of today's play coins! Missions still pay." : "";
  }
  $("coinCount").textContent = S.hang.coins;
  showStars();
}
function buildShopPane(box) {
  const {shop, coins, gifts, stuff} = S.hang;
  const picture = (key, item) => item.kind === "wear" ? `<canvas data-pic="${key}"></canvas>`
    : item.kind === "furniture" ? `<canvas data-furnpic="${key}"></canvas>` : item.kind === "room" ? `<span>🚪</span>`
    : `<i class="swatch" style="background:${PalHang.lookColour(key)}"></i>`;
  const shelf = (title, kinds) => `<h4>${title}</h4>` + Object.entries(shop).filter(([, item]) => kinds.includes(item.kind)).map(([key, item]) => {
    const mine = gifts.includes(key) || stuff.includes(key);
    return `<button data-buy="${key}" ${mine ? "disabled" : ""} class="${!mine && coins < item.price ? "dear" : ""}" aria-pressed="${buyArmed === key}">${picture(key, item)}${esc(item.name)}<small>${mine ? "✔ Yours" : buyArmed === key ? "Click again to buy!" : "🪙 " + item.price}</small></button>`;
  }).join("");
  box.innerHTML = `<p class="me-note">You have 🪙 <b>${coins}</b>. Coding missions pay the most coins! Playing pays a few each day.</p>` +
    shelf("🧢 To wear", ["wear"]) + shelf("🛋️ For your home", ["furniture"]) + shelf("🎨 Walls and floors", ["wall", "floor"]) + shelf("🚪 More rooms", ["room"]);
  paintPanePictures(box);
}
function paintPanePictures(box) {
  box.querySelectorAll("[data-pic]").forEach(cv => wearInto(cv, cv.dataset.pic, 3));
  box.querySelectorAll("[data-furnpic]").forEach(cv => {
    const img = PalHang.furniturePicture(cv.dataset.furnpic);
    cv.width = img.width; cv.height = img.height;
    cv.getContext("2d").drawImage(img, 0, 0);
  });
}
async function buy(key) {
  const item = S.hang.shop[key];
  if (S.hang.coins < item.price) { tipFor(`You need ${item.price - S.hang.coins} more coins for that. A coding mission pays the most!`); return; }
  if (buyArmed !== key) { buyArmed = key; buildRoomButtons(); return; }
  buyArmed = null;
  const out = await tap("buy", {key});
  if (!out || !out.ok) { if (out && out.error) tipFor(out.error); buildRoomButtons(); return; }
  Object.assign(S.hang, {coins: out.coins, gifts: out.gifts, stuff: out.stuff});
  coinsSeen = out.coins;
  PalStage.SFX.play("gift");
  tipFor(`You bought ${item.kind === "room" ? "a new " + item.name.toLowerCase() : item.name}! ${item.kind === "wear" ? "Put it on in 🧢 Me."
    : item.kind === "room" ? "Go to 🏠 Home and click the blue door to go in." : "Use it in 🏠 Home."}`);
  paintCoins();
  buildRoomButtons();
}

// ---- A home of your own -----------------------------------------------------------------------
function buildHomePane(box) {
  const {furniture, walls, floors, stuff} = S.hang, home = roomInfo && roomInfo.home;
  const others = ((roomInfo && roomInfo.people) || []).filter(m => m.seat !== roomInfo.you);
  const rooms = home && home.rooms.length > 1 ? `<h4>🚪 Rooms</h4>` + home.rooms.map((r, i) =>
    `<button data-room="${r.loc}" aria-pressed="${i === home.at}"><span>🚪</span>${esc(r.name)}</button>`).join("") : "";
  const visit = others.length ? `<h4>🚪 Visit a friend's home</h4>` + others.map(m => `<button data-home="${m.seat}"><span>🏡</span>${esc(m.name)}</button>`).join("") : "";
  if (!home || !home.mine) {
    box.innerHTML = `<p class="me-note">${home ? `You're visiting ${esc(home.name)}'s home. This is the ${esc(home.rooms[home.at].name.toLowerCase())}.` : "Everyone has a home. Fill yours with things from the 🛍️ Shop!"}</p>
      <button class="wide" data-home="mine"><span>🏠</span>Go to my home</button>${home ? `<button class="wide" data-home="out"><span>🚪</span>Go back outside</button>` : ""}` + rooms + visit;
    return;
  }
  const have = key => !S.hang[key in furniture ? "furniture" : key in walls ? "walls" : "floors"][key].price || stuff.includes(key);
  const out = new Set(home.items.map(i => i.key));
  const note = furnArmed ? `👉 Click the floor to put the ${furniture[furnArmed].name.toLowerCase()} there!` : "Pick a thing, then click the floor to put it there. Pick it again to move it.";
  box.innerHTML = `<p class="me-note">You're in your ${esc(home.rooms[home.at].name.toLowerCase())}.${home.rooms.length > 1 ? "" : " Get more rooms in the 🛍️ Shop!"}</p>` + rooms + `<h4>🛠️ Make your own furniture</h4>
     <p class="me-note">Draw a chair, a lamp, a magic bed... anything! Put it in your home from 🖼️ Art, then give it code.</p>
     <button class="wide" data-drawthing="1"><span>✏️</span>Draw new furniture</button>
     <button class="wide" data-pane="art"><span>🖼️</span>Put a drawing in my home</button>` + thingTiles() +
    `<h4>🛋️ Your things</h4><p class="me-note">${note}</p>` +
    (furnArmed && out.has(furnArmed) ? `<button class="wide" data-away="${furnArmed}"><span>📦</span>Put it away</button>` : "") +
    Object.keys(furniture).filter(have).map(key =>
      `<button data-furn="${key}" aria-pressed="${furnArmed === key}"><canvas data-furnpic="${key}"></canvas>${esc(furniture[key].name)}<small>${out.has(key) ? "✔ Out" : ""}</small></button>`).join("") +
    `<h4>🎨 Walls and floors</h4>` + [...Object.keys(walls), ...Object.keys(floors)].filter(have).map(key =>
      `<button data-look="${key}" aria-pressed="${home.wall === key || home.floor === key}"><i class="swatch" style="background:${PalHang.lookColour(key)}"></i>${esc((walls[key] || floors[key]).name)}</button>`).join("") +
    `<p class="me-note">Get more things in the 🛍️ Shop.</p>
     <button class="wide" data-home="out"><span>🚪</span>Go back outside</button>` + visit;
  paintPanePictures(box);
  box.querySelectorAll("[data-artpic]").forEach(cv => drawingInto(cv, shelfList.find(p => p.key === cv.dataset.artpic)));
}
async function goHome(where) {
  fishing = null; furnArmed = artArmed = null;
  PalStage.SFX.wake();
  const out = await tap("home", where === "out" ? {out: true} : where === "mine" ? {} : {seat: +where});
  if (out && out.error) tipFor(out.error);
  else if (out && out.ok && where !== "out") { roomPane = "home"; buildRoomButtons(); }
}

async function goRoom(loc) {
  fishing = null; furnArmed = artArmed = null;
  PalStage.SFX.wake();
  const out = await tap("home", {to: loc});
  if (out && out.error) tipFor(out.error);
}

// ---- Fishing off the pier -----------------------------------------------------------------------
function fishTick(mine) {
  if (!fishing) return;
  const now = performance.now();
  if (fishing.walk) {
    if (Math.abs(mine.x - fishing.walk.x) > 5 || Math.abs(mine.y - fishing.walk.y) > .08) return;
    fishing = {casting: true};
    tap("fish", {action: "cast"}).then(out => {
      if (!fishing || !fishing.casting) return;
      if (!out || !out.ok) { fishing = null; if (out && out.error) tipFor(out.error); return; }
      fishing = {biteAt: performance.now() + out.wait * 1000};
      tipFor("🎣 Shh... wait for a bite. Then click fast!", 9000);
    });
  } else if (fishing.biteAt && !fishing.bitten && now >= fishing.biteAt) {
    fishing.bitten = true;
    PalStage.SFX.play("ding");
    banner("❗ A bite! Click now!", 2400);
    tipFor("❗ A bite! Click anywhere on the picture!", 2400);
  } else if (fishing.bitten && now > fishing.biteAt + 2400) {
    reelIn();
  }
}
async function reelIn() {
  fishing = null;
  const out = await tap("fish", {action: "reel"});
  if (!out || !out.ok) return;
  if (out.missed) { tipFor(`${out.missed} Click the pier to try again.`); return; }
  const [icon, name] = S.hang.fish_book[out.fish];
  S.hang.fish[out.fish] = (S.hang.fish[out.fish] || 0) + 1;
  banner(`${icon} You caught: ${esc(name)}!${out.new ? "<small>New in your fish book! Look in 🧢 Me.</small>" : ""}`, 3200);
  tipFor(`${icon} ${name}!${out.coins ? ` +${out.coins} 🪙` : ""} Click the pier to fish again.`);
  if (out.badges.length) showRewards({badges: out.badges});
  if (roomPane === "me") buildRoomButtons();
}

// Leaving your other drawings out in the world, for everyone to find.
function buildArtPane(box) {
  const pics = finishedDrawings();
  const out = ((roomStage && roomStage.state.placed) || []).filter(p => p.mine).length;
  const max = atHome() ? S.hang.art_max : S.hang.place_max, where = atHome() ? "wall or floor" : "world";
  const note = atHome() && !myHome() ? "You can hang drawings up in your own home, or outside."
    : !pics.length ? "Draw something first, then come back and put it up!"
    : artArmed ? `👉 Now click the ${where} where you want it!`
    : `Pick a drawing, then click the ${where} to put it there. Click one you put out to take it back. (${out} of ${max} out${out >= max ? ": a new one replaces your oldest" : ""})`;
  box.innerHTML = `<p class="me-note">${note}</p>` + pics.map(d =>
    `<button data-art="${esc(d.key)}" aria-pressed="${artArmed === d.key}"><canvas data-artpic="${esc(d.key)}"></canvas>${esc(d.title || "Drawing")}<small>${S.hang.things[d.key] ? "✨ Coded" : ""}</small></button>`).join("") + thingTiles();
  box.querySelectorAll("[data-artpic]").forEach(cv => drawingInto(cv, pics.find(p => p.key === cv.dataset.artpic)));
}
const finishedDrawings = () => shelfList.filter(d => /[^.]/.test(d.frames[0]));
function drawingInto(cv, d) {
  const pup = PalStage.puppet(d, Math.max(1, Math.round(40 / d.size)), 1);
  cv.width = cv.height = 54;
  cv.style.cssText = "width:54px;height:54px";
  pup.draw(cv.getContext("2d"), 0, PixelRig.pose("idle", 0, pup.rigOf(0)), 27, 50);
}
// Who you are in the Hang out. Switch and friends only show when there's more than one drawing to be.
function paintPalStrip() {
  const pics = finishedDrawings(), strip = $("palStrip");
  strip.hidden = !pics.length;
  if (strip.hidden) return;
  $("palSwitch").hidden = $("palFollow").hidden = pics.length < 2;
  const d = pics.find(p => p.key === S.pal) || S.pip;
  drawingInto($("palStripPic"), d);
  $("palStripName").textContent = d.title || "My drawing";
  const on = S.hang.buddies === true;
  $("palFollow").setAttribute("aria-pressed", on);
  $("palFollow").textContent = on ? "👯 Buddies: on" : "👯 Buddies: off";
  $("palFollow").title = "Your other drawings come along with your pal";
}
async function choosePal(key) {
  if (key === S.pal) return;
  PalStage.SFX.wake();
  const out = await tap("pal", {key});
  if (!out || !out.ok) return;
  S.pal = out.pal;
  paintPalStrip();
  if (roomPane === "me") buildRoomButtons();
}
// What a goal counts, as words for a child.
const GOAL_WORDS = {gems: ["💎", n => `Find ${n} gems`], fish: ["🎣", n => `Catch ${n} kinds of fish`], friends: ["🙌", n => `High-five ${n} friends`],
                    rounds: ["🎮", n => `Play ${n} game rounds`], stars: ["⭐", n => `Earn ${n} mission stars`]};
const goalLeft = key => { const [what, n] = S.hang.catalog[key].goal; return [Math.min(n, (S.hang.progress || {})[what] || 0), n, what]; };
// How a locked thing is got, short enough for a button.
function howToGet(key) {
  const item = S.hang.catalog[key];
  if (item.goal) { const [have, n, what] = goalLeft(key); return `${GOAL_WORDS[what][0]} ${have} / ${n}`; }
  if (item.price) return `🛍️ 🪙 ${item.price}`;
  if (item.class) return "🎉 Class party";
  return "🎁 Gift box";
}
function howToGetLong(key) {
  const item = S.hang.catalog[key];
  if (item.goal) { const [have, n, what] = goalLeft(key); return `${GOAL_WORDS[what][1](n)} to unlock the ${item.name}! You have ${have}.`; }
  if (item.price) return `The ${item.name} is in the 🛍️ Shop for 🪙 ${item.price}.`;
  if (item.class) return `The ${item.name} comes when the class party meter fills up!`;
  return `The ${item.name} can come out of a 🎁 gift box. Finish a mission or play a game to get one!`;
}
function buildMePane(box) {
  const {gifts, catalog, wear, friends} = S.hang, pics = finishedDrawings();
  const slots = Object.keys(SLOT_NAMES).map(slot => {
    const all = Object.keys(catalog).filter(key => catalog[key].slot === slot);
    const mine = all.filter(key => gifts.includes(key)), locked = all.filter(key => !gifts.includes(key));
    return `<h4>${SLOT_NAMES[slot]}: ${mine.length} of ${all.length}</h4>` + mine.map(key =>
      `<button data-wear="${key}" data-slot="${slot}" aria-pressed="${wear[slot] === key}"><canvas data-pic="${key}"></canvas>${esc(catalog[key].name)}</button>`).join("") +
      locked.map(key => `<button class="locked" data-locked="${key}"><canvas data-pic="${key}"></canvas>${esc(catalog[key].name)}<small>🔒 ${esc(howToGet(key))}</small></button>`).join("");
  }).join("");
  const next = Object.keys(catalog).filter(key => catalog[key].goal && !gifts.includes(key))
    .sort((a, b) => goalLeft(b)[0] / goalLeft(b)[1] - goalLeft(a)[0] / goalLeft(a)[1]).slice(0, 3);
  const goals = next.length ? `<h4>🔓 Next to unlock</h4>` + next.map(key => {
    const [have, n, what] = goalLeft(key);
    return `<button class="wide goal" data-locked="${key}"><canvas data-pic="${key}"></canvas><span><b>${esc(catalog[key].name)}</b>
      <small>${GOAL_WORDS[what][0]} ${esc(GOAL_WORDS[what][1](n))}: ${have} / ${n}</small><i class="goal-bar"><i style="width:${have / n * 100}%"></i></i></span></button>`;
  }).join("") : "";
  const who = pics.length > 1 ? `<h4>🎨 Pick who you are</h4>` + pics.map(d =>
    `<button data-pal="${esc(d.key)}" aria-pressed="${S.pal === d.key}"><canvas data-palpic="${esc(d.key)}"></canvas>${esc(d.title || "My drawing")}</button>`).join("") : "";
  const book = S.hang.fish_book, fish = S.hang.fish;
  const hide = `<button class="wide" data-hidename aria-pressed="${!!S.hang.hide_name}"><span>🙈</span>${S.hang.hide_name ? "Your name tag is invisible to others. Click to show it." : "Make my name tag disappear"}</button>`;
  box.innerHTML = hide + who + goals + (gifts.length ? "" : `<p class="me-note">Finish a mission to get a gift box! Click a 🔒 thing to see how to get it.</p>`) + slots +
    `<h4>🙌 Friends you've high-fived: ${friends.length}</h4><p class="me-note">${friends.length ? friends.map(esc).join(", ") : "Click a friend's pal to high-five them."}</p>` +
    `<h4>🎣 Fish book: ${Object.keys(fish).length} of ${Object.keys(book).length}</h4><p class="me-note fish-book">${Object.keys(book).map(k =>
      fish[k] ? `<span title="${esc(book[k][1])}">${book[k][0]}<small>×${fish[k]}</small></span>` : "❔").join(" ")}</p>` +
    (Object.keys(fish).length ? "" : `<p class="me-note">Click the pier at the Beach (the blue ring) to go fishing.</p>`);
  box.querySelectorAll("[data-pic]").forEach(cv => wearInto(cv, cv.dataset.pic, 3));
  box.querySelectorAll("[data-palpic]").forEach(cv => drawingInto(cv, pics.find(p => p.key === cv.dataset.palpic)));
}
// A picture of a gift. Sparkles have none, so they get their own little star.
function wearInto(cv, key, zoom) {
  const img = PalStage.wearPicture(key);
  if (!img) { cv.width = cv.height = 9 * zoom; const g = cv.getContext("2d"); g.font = `${7 * zoom}px sans-serif`; g.textBaseline = "top"; g.fillText("✨", 0, 0); return; }
  cv.width = img.width * zoom; cv.height = img.height * zoom;
  const g = cv.getContext("2d");
  g.imageSmoothingEnabled = false;
  g.drawImage(img, 0, 0, cv.width, cv.height);
}

function paintMoveButton() {
  const b = $("myMove"), move = S.hang.move;
  const open = S.chapters.flatMap(c => c.levels).find(l => l.key === "m1").open;
  b.classList.toggle("none-yet", !move);
  if (!move) {
    b.disabled = !open;
    b.innerHTML = open ? "<b>🌟 Make your My Move</b><small>Code a routine and it becomes this button</small>"
      : "<b>🔒 My Move</b><small>Finish the missions to make your own</small>";
    return;
  }
  const left = moveReadyAt - performance.now();
  b.disabled = left > 0;
  b.innerHTML = `<b>✨ ${esc(move.title)}</b><small>${left > 0 ? "Getting ready..." : "Press it and everyone sees!"}${move.loop ? " · sparkle trail" : ""}${move.big ? " · big finish" : ""}</small>`;
}
// The next thing to code, with its prize, so the Hang out leads back to the Code tab.
function nextCoding() {
  const order = S.chapters.flatMap(c => c.levels);
  const next = order.find(l => l.open && !l.stars[0]);
  if (next) return {key: next.key, turn: false, name: next.name};
  const turn = order.find(l => l.stars[0] && !l.remixed);
  if (turn) return {key: turn.key, turn: true, name: turn.name};
  const fix = order.find(l => l.stars[0] && l.fixed === false);
  return fix ? {key: fix.key, fix: true, name: fix.name} : null;
}
function paintNextMission() {
  const b = $("nextMission"), next = nextCoding();
  b.hidden = !next;
  if (!next) return;
  const giftLeft = Object.entries(S.hang.catalog).some(([k, g]) => !g.class && !g.price && !g.goal && !S.hang.gifts.includes(k));
  b.innerHTML = next.fix
    ? `<b>🐞 Fix it: ${esc(next.name)}</b><small>Find the bug in Pip's code · +15 🪙</small>`
    : next.turn
    ? `<b>🎨 Your turn: ${esc(next.name)}</b><small>Change the code your own way · +15 🪙</small>`
    : `<b>💻 Next mission: ${esc(next.name)}</b><small>Win up to 50 🪙${giftLeft ? " and a 🎁 gift box" : ""}</small>`;
}
async function goCode() {
  const next = nextCoding();
  if (!next) return;
  await showView("stage");
  await openMission(next.key);
  if (next.turn) startRemix();
  else if (next.fix) startFix();
}
async function pressMyMove() {
  if (!S.hang.move) { await showView("stage"); openMission("m1"); return; }
  if (performance.now() < moveReadyAt) return;
  PalStage.SFX.wake();
  const out = await tap("mymove");
  if (!out || !out.ok) return;
  const wait = Math.max(6000, out.ms);
  moveReadyAt = performance.now() + wait;
  paintMoveButton();
  setTimeout(paintMoveButton, wait + 50);
}

// ---- What just happened -------------------------------------------------------------------
function banner(html, ms, big = false) {
  const el = $("hangBanner");
  el.innerHTML = html;
  el.className = big ? "big" : "";
  el.hidden = false;
  clearTimeout(bannerTimer);
  bannerTimer = setTimeout(() => { el.hidden = true; }, ms);
}
function showClap(seat, by, ms) {
  clapFor = seat;
  $("clapGo").textContent = `👏 Clap for ${by}!`;
  $("clapGo").hidden = false;
  clearTimeout(clapTimer);
  clapTimer = setTimeout(() => { clapFor = null; $("clapGo").hidden = true; }, ms);
}
function paintMeter(m) {
  $("meterBar").style.width = Math.min(100, m.points / m.goal * 100) + "%";
  $("meterWords").textContent = `${m.points} of ${m.goal}`;
  $("meterNext").textContent = m.next ? `Next: ${m.next}` : "Next: a party!";
}
function roomEvent(e, you) {
  if ((e.kind === "place" || e.kind === "unplace") && roomPane === "art") buildRoomButtons();
  if (e.kind === "game" && e.message) {
    tipFor(e.message);
  } else if (e.kind === "mymove") {
    banner(`✨ <b>${esc(e.by)}</b>: ${esc(e.title)}`, e.ms + 700);
    if (e.seat !== you) showClap(e.seat, e.by, e.ms + 700);
  } else if (e.kind === "party") {
    banner(`🎉 CLASS PARTY! 🎉${e.reward ? `<small>New for everyone: ${esc(e.reward.name)}</small>` : ""}`, 6000, true);
    if (e.reward && e.reward.kind === "gift" && !S.hang.gifts.includes(e.reward.key)) S.hang.gifts.push(e.reward.key);
    if (roomPane === "me") buildRoomButtons();
  } else if (e.kind === "shower") {
    banner("🌠 Star shower! Run and catch them!", 3500);
  } else if (e.kind === "five" && (e.fresh || []).includes(you)) {
    const other = roomStage.state.room.find(m => m.seat === (e.seat === you ? e.other : e.seat));
    if (other && !S.hang.friends.includes(other.name)) S.hang.friends.push(other.name);
    if (other) tipFor(`🙌 New friend: ${other.name}! That's ${S.hang.friends.length}.`);
    if (roomPane === "me") buildRoomButtons();
  }
}
function roomState(data) {
  roomInfo = data;
  paintGameState(data);
  const open = data.open;
  $("roomClosed").hidden = open;
  $("roomButtons").style.visibility = open ? "" : "hidden";
  $("myMove").style.visibility = open ? "" : "hidden";
  $("roomType").hidden = !open || !data.words;
  paintMeter(data.meter);
  paintCoins(data);
  paintJobs(data.jobs);
  const home = JSON.stringify(data.home), people = JSON.stringify(data.people);
  if (home !== homeSeen || people !== peopleSeen) {
    if (!data.home !== (homeSeen === "null" || !homeSeen)) { furnArmed = artArmed = null; fishing = null; $("roomTip").textContent = roomTipNow(); }
    homeSeen = home; peopleSeen = people;
    if (["home", "art"].includes(roomPane)) buildRoomButtons();
  }
  if (open && !data.you && !roomJoining) {
    roomJoining = true;
    tap("join").finally(() => { roomJoining = false; });
  }
  const places = data.places.join() + "|" + data.people.filter(m => !m.loc).map(m => m.seat + m.name).join();     // places, and who's outside to go to
  if (places !== placesSeen) { placesSeen = places; if (roomPane === "place") buildRoomButtons(); }
  for (const e of data.events) roomEvent(e, data.you);
}
// ---- 🎯 Today's jobs: three small things to do, the same for the whole class each day ---------------
let jobsSeen = null;
const jobDone = j => j.have >= j.need;
function paintJobs(jobs) {
  if (!jobs) return;
  const was = jobsSeen;
  jobsSeen = jobs;
  if (JSON.stringify(was) === JSON.stringify(jobs)) return;
  if (roomPane === "games" && !currentGame()) buildRoomButtons();
  if (!was) return;                       // what was done before this screen opened isn't news
  const fresh = jobs.list.filter(j => jobDone(j) && !was.list.some(w => w.key === j.key && jobDone(w)));
  if (!fresh.length) return;
  if (jobs.done && !was.done) {
    const gift = jobs.gift && S.hang.catalog[jobs.gift];
    banner(`🎯 All 3 jobs done! 🎯<small>${gift ? `🎁 A new gift: ${esc(gift.name)}. Put it on in 🧢 Me!` : `+${jobs.coins} 🪙`}</small>`, 6000, true);
    PalStage.SFX.play("fanfare");
    if (roomPane === "me") buildRoomButtons();
  } else {
    banner(`🎯 Job done: ${esc(fresh[0].words)}!<small>${jobs.list.filter(jobDone).length} of ${jobs.list.length} jobs today</small>`, 3500);
    PalStage.SFX.play("ding");
  }
}
function jobsHtml() {
  if (!jobsSeen) return "";
  const done = jobsSeen.list.filter(jobDone).length;
  return `<div class="jobs"><h4>🎯 Today's jobs <small>${jobsSeen.done ? "All done! See you next time." : `${done} of ${jobsSeen.list.length} · do all ${jobsSeen.list.length} for a 🎁`}</small></h4>` +
    jobsSeen.list.map(j => `<p class="job${jobDone(j) ? " done" : ""}"><span>${jobDone(j) ? "✅" : j.icon}</span>${esc(j.words)}${j.need > 1 ? ` <b>${Math.min(j.have, j.need)}/${j.need}</b>` : ""}` +
      `${j.key === "star" && !jobDone(j) ? `<button class="job-go" data-go-code="1">💻 Go code</button>` : ""}</p>`).join("") + `</div>`;
}
const jobsWord = () => (jobsSeen && !jobsSeen.done ? `🎯 ${jobsSeen.list.filter(jobDone).length} of ${jobsSeen.list.length} jobs · ` : "");

let tipTimer = 0;
function tipFor(text, ms = 3500) {
  $("roomTip").textContent = text;
  clearTimeout(tipTimer);
  tipTimer = setTimeout(() => { tipTimer = 0; $("roomTip").textContent = roomTipNow(); }, ms);
}
// The everyday tip follows the game (IT changes, a solve), unless a short message is showing.
function tipKeepUp() {
  if (tipTimer || !roomInfo || $("hangView").hidden) return;
  const text = roomTipNow();
  if ($("roomTip").textContent !== text) $("roomTip").textContent = text;
}

// The page takes the colour of the place in the middle of the screen.
function tintPage() {
  const st = roomStage.state, place = (st.places || ["park"])[Math.floor((st.camX + PalStage.W / 2) / PalStage.W)];
  if (place && $("hangView").dataset.place !== place) $("hangView").dataset.place = place;
}
function lookForGem(mine) {
  tintPage();
  gameTick(mine);
  fishTick(mine);
  if (inRound()) return;
  const st = roomStage.state, key = PalHang.gemAt(st.places || ["park"], mine.x, mine.y, st.found);
  if (!key) return;
  st.found.add(key);
  tap("find", {key}).then(out => {
    if (!out || !out.ok) return;
    tipFor(`💎 You found a gem! That's ${out.found} of ${S.hang.gems}.`);
    if (out.badges.length) showRewards({badges: out.badges});
  });
}

// ---- Coming and going ------------------------------------------------------------------------
function openRoom() {
  if (!roomStage) {
    roomStage = PalStage.create($("roomCanvas"), $("roomHost"));
    roomStage.roomHooks({
      caught: star => tap("catch", {star}).then(out => { if (out && out.badges && out.badges.length) showRewards({badges: out.badges}); }),
      tick: lookForGem,
      moveEnded: m => { if (m.me && m.claps) tipFor(`👏 ${m.claps} clap${m.claps === 1 ? "" : "s"} for your move!`); },
    });
  }
  if (stopRoom) return;
  roomStage.setPal(S.pip);
  roomStage.fresh();
  roomStage.state.visible = false;
  roomStage.state.soft = true;
  roomStage.state.scene = "park";
  roomStage.state.found = new Set(S.hang.found);
  stopBack = PalHang.start($("hangBack"), () => roomStage.state);
  buildRoomButtons();
  paintMoveButton();
  paintNextMission();
  paintPalStrip();
  fitRoomScreen();
  stopRoom = PalStage.follow(roomStage, {id: me, onState: roomState});
  welcomeOnce();
}
// A student's first time in the Hang out says where to start, once. It's kept for each
// student on this computer; if the browser won't keep it, it stays quiet rather than repeat.
function welcomeOnce() {
  const key = "pixelHangHello:" + me;
  try { if (localStorage.getItem(key)) return; localStorage.setItem(key, "1"); } catch (_) { return; }
  roomPane = "games";
  buildRoomButtons();
  banner(`🎉 Welcome to the Hang out!<small>Click the ground to walk. Today's 🎯 jobs are in Games, on the right.</small>`, 7000, true);
}
function closeRoom() {
  if (!stopRoom) return;
  stopRoom();
  stopBack();
  stopRoom = null;
  tap("leave");
  roomStage.roomStop();
}

// ---- Walking and tapping --------------------------------------------------------------------
function myMember() {
  const st = roomStage && roomStage.state;
  return st && st.room && st.room.find(m => m.seat === st.you);
}
const worldEnd = () => roomStage.state.places.length * PalStage.W - 8;
function walkTo(x, y) {
  const mine = myMember();
  if (!mine) return;
  if (inRound()) { tap("walk", {x, y}).then(out => { if (out?.error) tipFor(out.error); }); return; }
  roomStage.roomApply({kind: "walk", seat: mine.seat, x, y});     // at once, without waiting for the server
  tap("walk", {x: Math.round(x), y: Math.round(y * 100) / 100});
}
// The nearest pal under the pointer, front ones first.
function palAt(x, y) {
  return roomStage.state.room.slice().sort((a, b) => b.y - a.y).find(m => {
    if (m.concealed || m.tucked) return false;
    const feet = PalStage.groundOf(m);
    return Math.abs(x - m.x) < 24 && y > feet - 62 && y < feet + 5;
  });
}

new ResizeObserver(fitRoomScreen).observe($("roomHost").closest(".hang-main"));
$("roomTabs").addEventListener("click", e => {
  const b = e.target.closest("[data-pane]");
  if (b) { roomPane = b.dataset.pane; artArmed = furnArmed = buyArmed = null; buildRoomButtons(); }
});
$("roomButtons").addEventListener("click", e => {
  const pick = name => { const el = e.target.closest(`[data-${name}]`); return el && !el.disabled ? el.dataset[name] : null; };
  if (pick("buy")) { buy(pick("buy")); return; }
  if (pick("home")) { goHome(pick("home")); return; }
  if (pick("friend")) { PalStage.SFX.wake(); tap("go", {seat: +pick("friend")}).then(out => { if (out && out.error) tipFor(out.error); }); return; }
  if (pick("room")) { goRoom(+pick("room")); return; }
  if (pick("furn")) { furnArmed = furnArmed === pick("furn") ? null : pick("furn"); buildRoomButtons(); return; }
  if (pick("away")) { tap("unfurnish", {key: pick("away")}); furnArmed = null; buildRoomButtons(); return; }
  if (pick("look")) { PalStage.SFX.wake(); tap("look", {key: pick("look")}); return; }
  if (pick("code")) { openThing(pick("code")); return; }
  if (pick("pane")) { roomPane = pick("pane"); artArmed = furnArmed = buyArmed = null; buildRoomButtons(); return; }
  if (pick("drawthing")) { drawFurniture(); return; }
  if (e.target.closest("[data-hidename]")) { hideMyName(); return; }
  const pal = e.target.closest("[data-pal]");
  if (pal) { choosePal(pal.dataset.pal); return; }
  const art = e.target.closest("[data-art]");
  if (art) { artArmed = artArmed === art.dataset.art ? null : art.dataset.art; buildRoomButtons(); return; }
  const locked = e.target.closest("[data-locked]");
  if (locked) {
    const key = locked.dataset.locked;
    if (S.hang.catalog[key].price) { roomPane = "shop"; buildRoomButtons(); }
    tipFor(howToGetLong(key), 5000);
    return;
  }
  const worn = e.target.closest("[data-wear]");
  if (worn) {
    const {wear: key, slot} = worn.dataset, wear = S.hang.wear;
    if (wear[slot] === key) delete wear[slot]; else wear[slot] = key;
    PalStage.SFX.wake();
    tap("wear", {slot, item: wear[slot] || null});
    buildRoomButtons();
    return;
  }
  const b = e.target.closest("[data-tap]");
  if (!b) return;
  PalStage.SFX.wake();
  const {tap: what, name: word} = b.dataset;
  if (what === "say") tap("say", {text: word}); else tap(what, {name: word});
});
async function hideMyName() {
  const out = await tap("hidename", {on: !S.hang.hide_name});
  if (!out || !out.ok) return;
  S.hang.hide_name = out.on;
  if (roomPane === "me") buildRoomButtons();
}
$("palFollow").addEventListener("click", async () => {
  const out = await tap("buddies", {on: S.hang.buddies !== true});
  if (!out || !out.ok) return;
  S.hang.buddies = out.on;
  paintPalStrip();
});
// Prop hunt: your pal turns into a still picture with no face and no name, so friends have to find you.
let propOn = false;
$("palProp").addEventListener("click", async () => {
  const out = await tap("prop", {on: !propOn});
  if (!out || !out.ok) return;
  propOn = out.on;
  $("palProp").setAttribute("aria-pressed", propOn);
  $("palProp").textContent = propOn ? "🙂 Be me again" : "🪑 Be a prop";
  tipFor(propOn ? "You're a prop! No face, no name. Stay still so friends have to find you." : "You're you again!", 5000);
});
$("palSwitch").addEventListener("click", () => { roomPane = "me"; artArmed = null; buildRoomButtons(); $("roomButtons").scrollTop = 0; });
$("myMove").addEventListener("click", pressMyMove);
$("nextMission").addEventListener("click", goCode);
$("clapGo").addEventListener("click", () => { if (clapFor !== null) tap("clap", {seat: clapFor}); });
$("roomButtons").addEventListener("click", e => { if (e.target.closest("[data-go-code]")) goCode(); });     // the ⭐ job's way to the missions
$("roomCanvas").addEventListener("click", async e => {
  const r = $("roomCanvas").getBoundingClientRect(), mine = myMember();
  const x = roomStage.state.camX + (e.clientX - r.left) / r.width * PalStage.W, y = (e.clientY - r.top) / r.height * PalStage.H;
  if (!mine) return;
  PalStage.SFX.wake();
  if (inRound()) {
    const cover = PalHang.coverAt(roomInfo.cover, x, y);
    if (cover && currentGame().kind === "hide") chooseGameCover(cover.key);
    else {
      gamePendingCover = null;
      walkTo(Math.max(8, Math.min(632, x)), Math.max(0, Math.min(1, (y - PalStage.GROUND_TOP) / PalStage.GROUND_DEEP)));
    }
    return;
  }
  if (fishing && fishing.bitten) { reelIn(); return; }
  fishing = null;
  const depth = Math.round(Math.max(0, Math.min(1, (y - PalStage.GROUND_TOP) / PalStage.GROUND_DEEP)) * 100) / 100;
  if (artArmed) {
    const key = artArmed;
    artArmed = null;
    buildRoomButtons();
    tap("place", {key, x: Math.round(Math.max(8, Math.min(worldEnd(), x))), y: depth}).then(out => { if (out && out.error && out.error.length > 8) tipFor(out.error); });
    return;
  }
  if (furnArmed && myHome()) {
    const key = furnArmed;
    furnArmed = null;
    PalStage.SFX.play("pop");
    tap("furnish", {key, x: Math.round(Math.max(16, Math.min(PalStage.W - 16, x))), y: depth});
    return;
  }
  const door = atHome() && PalHang.doorAt(x, y, roomInfo.home);
  if (door) {
    const {rooms, at} = roomInfo.home;
    if (door === "next") goRoom(rooms[at + 1].loc);
    else if (at > 0) goRoom(rooms[at - 1].loc);
    else goHome("out");
    return;
  }
  const pier = !atHome() && PalHang.fishAt(roomStage.state.places, x, y);
  const front = pier && palAt(x, y);
  if (pier && (!front || front.me)) {
    fishing = {walk: pier};
    walkTo(pier.x, pier.y);
    tipFor("🎣 Walking to the pier...");
    return;
  }
  const thing = roomPane !== "art" && thingAt(x, y);
  if (thing) { pokeThing(thing); return; }
  if (roomPane === "art") {
    const own = roomStage.state.placed.find(p => p.mine && Math.abs(x - p.x) < 22 && y > PalStage.groundOf(p) - 44 && y < PalStage.groundOf(p) + 6);
    if (own) { tap("unplace", {piece: own.id}); return; }
  }
  const hit = palAt(x, y);
  const places = roomStage.state.places, seat = PalHang.seatAt(places, x, y), toy = PalHang.toyAt(places, x, y);
  if (hit && hit.me && !seat && !toy) { tap("move", {name: "jump"}); return; }
  if (hit && !hit.me) {
    const out = await tap("five", {seat: hit.seat});
    if (out && out.badges && out.badges.length) showRewards({badges: out.badges});
    return;
  }
  if (seat) {     // friends on the same bench sit side by side
    tap("rest", {name: "sit", x: Math.max(8, Math.min(worldEnd(), seat.x + (mine.seat % 5 - 2) * 9)), y: seat.y});
    return;
  }
  if (toy) { tap("toy", {name: toy.fx, x: toy.x, y: toy.y}); return; }
  const {GROUND_TOP: top, GROUND_DEEP: deep} = PalStage;
  walkTo(Math.max(8, Math.min(worldEnd(), x)), y < top - 8 ? mine.ty : Math.max(0, Math.min(1, (y - top) / deep)));
});
addEventListener("keydown", e => {
  if ($("hangView").hidden || e.target.matches("input, textarea") || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
  const mine = myMember();
  if (!mine) return;
  e.preventDefault();
  gamePendingCover = null;
  fishing = null;
  const dx = {ArrowLeft: -26, ArrowRight: 26}[e.key] || 0, dy = {ArrowUp: -.25, ArrowDown: .25}[e.key] || 0;
  // In a round, step from where the pal is, so letting go of the key stops it.
  const [fromX, fromY] = inRound() ? [mine.x, mine.y] : [mine.tx, mine.ty];
  walkTo(Math.max(8, Math.min(worldEnd(), fromX + dx)), Math.max(0, Math.min(1, fromY + dy)));
});
$("roomType").addEventListener("submit", e => {
  e.preventDefault();
  const text = $("roomWords").value.trim();
  if (!text) return;
  $("roomWords").value = "";
  tap("say", {text});
});
addEventListener("pagehide", () => {
  if (stopRoom) navigator.sendBeacon("/pixel/room/do", new Blob([JSON.stringify({id: me, what: "leave"})], {type: "application/json"}));
});

// ---- Things you drew, with code -------------------------------------------------------------
// Any drawing can have a program. Put it out (🖼️ Art) and anyone who clicks it runs on_click.
const THING_IDEAS = {
  "🦘 Bouncy": 'def on_click():\n    jump()\n    sound("boing")\n    say("Hooray!")\n',
  "💡 Light switch": 'def on_click():\n    if clicks() % 2 == 1:\n        pose(2)\n        sound("ding")\n    else:\n        pose(1)\n        sound("pop")\n',
  "🎉 Party": 'def on_click():\n    spin()\n    for i in range(3):\n        jump()\n    confetti()\n    sound("tada")\n',
  "🎲 Surprise": 'def on_click():\n    pick = randint(1, 3)\n    if pick == 1:\n        hearts()\n    elif pick == 2:\n        stars()\n    else:\n        shake()\n',
  "👻 Peekaboo": 'def on_click():\n    hide()\n    wait(2)\n    appear()\n    sound("pop")\n',
  "🎈 Grow": 'def on_click():\n    if clicks() < 3:\n        grow()\n    else:\n        shrink()\n        shrink()\n',
};
let thingKey = null, thingClicks = 0, thingStage = null, thingSaved = "";
function thingTiles() {
  const pics = finishedDrawings();
  if (!pics.length) return "";
  return `<h4>💻 Code your drawings</h4><p class="me-note">Give a drawing code, then put it out. Anyone who clicks it makes it go!</p>` + pics.map(d =>
    `<button data-code="${esc(d.key)}"><canvas data-artpic="${esc(d.key)}"></canvas>${esc(d.title || "Drawing")}<small>${S.hang.things[d.key] ? "✨ Has code" : "+ Add code"}</small></button>`).join("");
}
function openThing(key) {
  const d = shelfList.find(p => p.key === key);
  if (!d) return;
  thingKey = key;
  thingSaved = S.hang.things[key] || "";
  $("thingTitle").textContent = `💻 Code: ${d.title || "My drawing"}`;
  $("thingCode").value = thingSaved || S.hang.thing_start;
  $("thingError").textContent = "";
  $("thingChips").innerHTML = Object.values(S.hang.thing_usage).map(u => `<button class="chip" data-put="${esc(u)}">${esc(u)}</button>`).join("");
  $("thingIdeas").innerHTML = Object.keys(THING_IDEAS).map(name => `<button class="btn" data-idea="${esc(name)}">${esc(name)}</button>`).join("");
  $("thingSheet").hidden = false;
  if (!thingStage) thingStage = PalStage.create($("thingCanvas"), $("thingHost"));
  thingAgain();
  $("thingCode").focus();
}
function thingAgain() {
  thingClicks = 0;
  $("thingClicks").textContent = "";
  thingStage.fresh();
  thingStage.setPal(shelfList.find(p => p.key === thingKey));
}
async function thingTry() {
  PalStage.SFX.wake();
  thingClicks += 1;
  const out = await post("/pixel/thing/try", {id: me, key: thingKey, code: $("thingCode").value, clicks: thingClicks}).catch(() => null);
  if (!out || out.error) {
    thingClicks -= 1;
    $("thingError").textContent = out ? "🐞 " + out.error : "Couldn't reach the computer. Try again.";
    return;
  }
  const said = out.steps.filter(s => s.do === "say" && !Object.values(S.room_words).flat().includes(s.text));
  $("thingError").textContent = said.length && !(roomInfo && roomInfo.words) ? "💬 Friends see your own words when your teacher turns on typing. Words from 💬 Say always show." : "";
  $("thingClicks").textContent = `Clicks: ${thingClicks}`;
  thingStage.play(out.steps);
}
async function thingSave() {
  const code = $("thingCode").value;
  const out = await post("/pixel/thing/save", {id: me, key: thingKey, code}).catch(() => null);
  if (!out || !out.ok) { $("thingError").textContent = "Couldn't save. Try again."; return false; }
  thingSaved = code;
  if (code.trim()) S.hang.things[thingKey] = code; else delete S.hang.things[thingKey];
  return true;
}
async function closeThing() {
  const changed = $("thingCode").value !== (thingSaved || S.hang.thing_start);
  if (changed && !(await thingSave())) return;
  $("thingSheet").hidden = true;
  if (thingStage) thingStage.fresh();
  if (changed) tipFor(S.hang.things[thingKey] ? "💾 Saved! Put it out from 🖼️ Art, then click it." : "Code taken off.");
  buildRoomButtons();
}
$("thingTry").addEventListener("click", thingTry);
$("thingAgain").addEventListener("click", thingAgain);
$("thingSave").addEventListener("click", async () => {
  if (await thingSave()) { $("thingError").textContent = "✔ Saved! Click it in the Hang out to see it go."; PalStage.SFX.play("ding"); }
});
$("closeThing").addEventListener("click", closeThing);
$("thingSheet").addEventListener("click", e => {
  const put = e.target.closest("[data-put]"), idea = e.target.closest("[data-idea]");
  const box = $("thingCode");
  if (put) {
    const at = box.selectionStart, lineStart = box.value.lastIndexOf("\n", at - 1) + 1;
    const blank = !box.value.slice(lineStart, at).trim();
    const text = (blank && at === lineStart ? "    " : "") + put.dataset.put;
    box.setRangeText(text, at, box.selectionEnd, "end");
    box.focus();
  } else if (idea) {
    box.value = THING_IDEAS[idea.dataset.idea];
    $("thingError").textContent = idea.dataset.idea.includes("Light") ? "💡 This one needs 2 frames: draw the second one in 🎨 Draw with + Copy frame." : "";
    thingAgain();
  }
});
// Tab puts in 4 spaces, and Enter after a : starts the next line 4 spaces further in.
$("thingCode").addEventListener("keydown", e => {
  const box = e.target, at = box.selectionStart;
  if (e.key === "Tab") { e.preventDefault(); box.setRangeText("    ", at, box.selectionEnd, "end"); }
  else if (e.key === "Enter") {
    const line = box.value.slice(box.value.lastIndexOf("\n", at - 1) + 1, at);
    const indent = line.match(/^ */)[0] + (line.trimEnd().endsWith(":") ? "    " : "");
    e.preventDefault();
    box.setRangeText("\n" + indent, at, box.selectionEnd, "end");
  }
});
/** The coded thing at this spot in the Hang out, if there is one. */
function thingAt(x, y) {
  return ((roomStage && roomStage.state.placed) || []).slice().reverse().find(p => {
    const big = [1, 1.35, 1.7][p.size - 1] || 1, base = PalStage.groundOf(p);
    return p.coded && Math.abs(x - p.x) < 22 * big && y > base - 46 * big && y < base + 6;
  });
}
async function pokeThing(th) {
  const out = await tap("poke", {piece: th.id});
  if (out && out.error && out.error.length > 8) tipFor("🐞 " + out.error, 6000);
}
async function drawFurniture() {
  await showView("draw");
  await openShelf();
  $("furnStart").scrollIntoView({block: "start"});
}
