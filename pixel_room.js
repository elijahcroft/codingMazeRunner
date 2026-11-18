// Pixel Pals: the Hang out. Everyone's pal is in one soft little world at the same
// moment, and what one child taps, everyone sees. Words are tapped from a list unless
// the teacher turns typing on.
"use strict";

let roomStage = null, stopRoom = null, stopBack = null, roomInfo = null, roomJoining = false, roomPane = "do";
let artArmed = null, moveReadyAt = 0, clapFor = null, clapTimer = 0, bannerTimer = 0, placesSeen = "";
let furnArmed = null, buyArmed = null, fishing = null, homeSeen = "", peopleSeen = "", coinsSeen = null;
let weddingAsk = null, weddingSeen = "";
let muralInk = 0, muralWhoMode = false;     // 🖼️ the colour picked, and "who painted?" instead of painting
// At home: ✋ moving things (a click picks one up, instead of playing with it), and which room is on screen.
let moving = false, roomInView = 0;
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
                     snowy: ["⛄", "Snowy hill"], candy: ["🍭", "Candy land"], space: ["🚀", "Space"], sea: ["🌊", "Under the sea"],
                     village: ["❄️", "Snow Village"]};
const SLOT_NAMES = {hat: "Hats", face: "Faces", sparkle: "Sparkles"};
const ROOM_TIP = "Walk to the edge to explore! Gold ring: sit. Pink ring: play. Blue ring: fish. Find 💎 gems and 🧰 chests!";
const HOME_TIP = "Click the floor to walk. Walk through a doorway to the next room! Click a thing to play with it. The brown door goes outside.";
// While you're in a round, the tip under the world says what to do in that game.
function gameTip(g) {
  const you = roomInfo.you, it = g.it === you;
  if (g.kind === "tag") return it ? "You're IT! Click near a friend to tag them." : "Run! Click the ground to get away from IT.";
  if (g.kind === "hide" && g.phase === "hiding") return it ? "You're counting. Everyone else is hiding!" : "Hide! Pick a hiding place on the right.";
  if (g.kind === "hide") return it ? "Click a hiding place to walk there and look." : "Stay still! The seeker is looking.";
  if (g.kind === "race") return "Green light: press Run or → again and again. Red light: stop!";
  if (g.kind === "dance") return "Tap the lit-up move on the right, in order.";
  if (g.kind === "apples") return "Walk onto apples! Golden ones are worth 3. Most apples when time is up wins.";
  if (g.kind === "ball") {
    const team = (g.teams || {})[you];
    return team === "blue" ? "🔵 Blue: walk into the ball to kick it right, into the blue goal!"
      : team === "orange" ? "🟠 Orange: walk into the ball to kick it left, into the orange goal!"
      : "Cheer for your friends! Wait for the next round to play.";
  }
  if (g.kind === "draw") return g.pause ? "Look! The next picture is coming." : g.drawer === you ? "You're drawing! Click squares on the right. No letters!"
    : (g.guessed || []).includes(you) ? "You got it! Watch the picture grow." : "What is it? Tap the picture on the right!";
  if (g.kind === "code") return (g.bonus || []).includes(you) ? "Bonus done! Clap for your friends while they finish."
    : (g.solved || []).includes(you) ? "You solved it! Try the 🌟 Bonus on the right, or clap for your friends." : "Build your code on the right, then press ▶ Run my code.";
  if (g.kind === "fashion") return g.phase === "dressing" ? "Dress up! Tap your things on the right, then Ready!"
    : g.phase === "runway" ? (g.walker === you ? "🌟 You're on the runway! Strike a pose!" : "Watch the runway! Tap 👏 😍 or ✨ on the right.")
    : "🌈 Every walker got a kind ribbon!";
  return ROOM_TIP;
}
// At a 🧰 chest, the tip under the world keeps the puzzle in view, even when a small laptop scrolls the code box.
const chestTip = () => { const c = roomPane === "chest" && chestNow(); return c && !c.open ? `🧰 ${c.job} ${c.icons}` : ""; };
const weddingTip = () => inWedding() && !(roomInfo && roomInfo.wedding)
  ? "💒 Tap 🎉 Party, then Hold a wedding, to marry a friend in the garden!" : "";
const roomTipNow = () => (atHome() ? HOME_TIP : inRound() ? gameTip(currentGame()) : chestTip() || weddingTip() || ROOM_TIP);

function fitRoomScreen() {
  const host = $("roomHost"), wrap = host.parentElement, main = wrap.parentElement;
  const tall = main.clientHeight - $("meterBar").closest(".hang-meter").offsetHeight - $("roomTip").offsetHeight - $("gameStatus").offsetHeight - 62;     // the gaps and the frame
  const width = Math.min(wrap.clientWidth - 16, tall * 16 / 9);
  host.style.width = Math.max(120, Math.floor(width)) + "px";
}

function tap(what, more = {}) {
  return post("/pixel/room/do", Object.assign({id: me, what}, more)).catch(() => null);
}

// ---- 💒 Weddings: pick a friend, one-tap yes, then watch the ceremony -------------------
const weddingCouple = e => e.partner_name ? `${e.host_name} and ${e.partner_name}` : e.host_name;
function inWedding() {
  const m = myMember(), places = roomStage && roomStage.state && roomStage.state.places;
  return !!(m && !atHome() && places && places[Math.floor(m.x / PalStage.W)] === "wedding");
}
function weddingButtonHtml() {
  if (!inWedding()) return "";
  if (roomInfo && roomInfo.wedding)
    return `<button data-wedding-start="1" disabled><span>💒</span>A wedding is on!<small>Watch the couple</small></button>`;
  return `<button data-wedding-start="1"><span>💒</span>Hold a wedding<small>Pick a friend from the garden</small></button>`;
}
function clearWeddingCard() {
  weddingAsk = null;
  const el = $("weddingCard");
  if (el) { el.hidden = true; el.innerHTML = ""; }
}
function paintWeddingCard() {
  const el = $("weddingCard");
  if (!el) return;
  if (!weddingAsk) { el.hidden = true; el.innerHTML = ""; return; }
  let html = "";
  if (weddingAsk.mode === "pick") {
    html = `<h3>💒 Who will you marry?</h3><p>Pick a friend here in the Wedding garden.</p><div class="wedding-list">` +
      (weddingAsk.candidates || []).map(c => `<button data-wedding="pick" data-seat="${c.seat}" data-name="${esc(c.name)}">💍 ${esc(c.name)}</button>`).join("") +
      `</div><button class="wedding-no" data-wedding="cancel">Not now</button>`;
  } else if (weddingAsk.mode === "waiting") {
    html = `<h3>💍 Waiting for ${esc(weddingAsk.name)}…</h3><p>Your friend has one tap: <b>Yes! 💍</b> or <b>Not now</b>.</p>` +
      `<button class="wedding-no" data-wedding="cancel">Stop the wedding</button>`;
  } else if (weddingAsk.mode === "invite") {
    html = `<h3>💍 ${esc(weddingAsk.from)} asks you!</h3><p>Will you say "I do" at the Wedding garden?</p>` +
      `<div class="wedding-pair"><button class="wedding-yes" data-wedding="yes">Yes! 💍</button><button class="wedding-no" data-wedding="no">Not now</button></div>`;
  } else if (weddingAsk.mode === "declined") {
    html = `<h3>💍 Not this time</h3><p>${esc(weddingAsk.name)} ${weddingAsk.noAnswer ? "did not answer" : 'said "Not now"'}. Ask another friend from the garden!</p>` +
      `<div class="wedding-pair"><button class="wedding-yes" data-wedding="retry">Ask another friend</button><button class="wedding-no" data-wedding="dismiss">OK</button></div>`;
  } else if (weddingAsk.mode === "note") {
    html = `<h3>💒 Wedding</h3><p>${esc(weddingAsk.text)}</p><button class="wedding-no" data-wedding="dismiss">OK</button>`;
  }
  el.innerHTML = html;
  el.hidden = !html;
}
async function startWedding() {
  if (weddingAsk) return;
  PalStage.SFX.wake();
  const out = await tap("wedding");
  if (!out || !out.ok) { tipFor((out && out.error) || "Couldn't start a wedding. Try again.", 6000); return; }
  PalStage.SFX.play("ding");
  weddingAsk = {mode: "pick", candidates: out.candidates || []};
  paintWeddingCard();
}
async function pickWeddingPartner(seat, name) {
  const out = await tap("wedding_pick", {seat: +seat});
  if (!out || !out.ok) { tipFor((out && out.error) || "Pick another friend.", 6000); return; }
  PalStage.SFX.play("ding");
  weddingAsk = {mode: "waiting", name};
  paintWeddingCard();
}
async function answerWedding(yes) {
  const out = await tap(yes ? "wedding_yes" : "wedding_no");
  if (!out || !out.ok) {
    tipFor((out && out.error) || "That invite has ended.", 6000);
    if (!out || !/garden/i.test(out.error || "")) clearWeddingCard();
    return;
  }
  clearWeddingCard();
  if (!yes) tipFor("No wedding this time. Maybe another day!", 4000);
}
async function cancelWedding() {
  await tap("wedding_cancel");
  clearWeddingCard();
  tipFor("No wedding this time.", 3000);
}
function weddingEvent(e, you) {
  const mine = myMember(), places = roomStage && roomStage.state && roomStage.state.places;
  const atGarden = !!(mine && !atHome() && places && places[Math.floor(mine.x / PalStage.W)] === "wedding");
  const forMe = e.to === you || e.host === you || e.partner === you || e.catcher === you;
  if (e.phase === "pick") {
    if (atGarden && e.host !== you) banner(`💒 ${esc(e.host_name)} is getting married!`, 3500);
  } else if (e.phase === "invite") {
    if (e.to === you) {
      weddingAsk = {mode: "invite", from: e.host_name};
      paintWeddingCard();
      PalStage.SFX.play("ding");
      if (atGarden) banner("💍 A friend asks you to a wedding!", 3000);
    } else if (atGarden) {
      banner(`💍 ${esc(e.host_name)} asked ${esc(e.partner_name)}…`, 3500);
    }
  } else if (e.phase === "start") {
    clearWeddingCard();
    if (atGarden || forMe) {
      banner(`💒 ${esc(weddingCouple(e))}'s wedding!<small>Here comes the couple!</small>`, 5000, true, true);
      PalStage.SFX.play("bells");
    }
  } else if (e.phase === "rings") {
    if (atGarden) banner("💍 Do you promise?<small>I do!</small>", 3200);
  } else if (e.phase === "bouquet") {
    if (atGarden) banner("💐 Catch the flowers!", 3000);
  } else if (e.phase === "catch") {
    if (atGarden) banner(`💐 ${esc(e.catcher_name)} caught the flowers!`, 4000, true);
  } else if (e.phase === "done") {
    clearWeddingCard();
    if (atGarden || forMe) {
      banner(`💒 ${esc(weddingCouple(e))} are married!<small>Congratulations!</small>`, 6000, true, true);
      PalStage.SFX.play("yay");
    }
  } else if (e.phase === "declined") {
    if (e.host === you) {
      weddingAsk = {mode: "declined", name: e.by_name || e.partner_name || "Your friend", noAnswer: e.reason === "no_answer"};
      paintWeddingCard();
      PalStage.SFX.play("nope");
    } else clearWeddingCard();
  } else if (e.phase === "cancelled") {
    if (e.host === you) {
      weddingAsk = {mode: "note", text: e.reason === "couple_left" ? "The wedding stopped because someone left the garden." : "The wedding stopped. Ask a friend again!"};
      paintWeddingCard();
    } else clearWeddingCard();
  }
}

// ---- The buttons ----------------------------------------------------------------------
function buildRoomButtons() {
  if (bannerHeld && !chestBusy()) { const held = bannerHeld; bannerHeld = null; setTimeout(() => banner(...held), 600); }
  document.querySelectorAll("[data-pane]").forEach(b => b.setAttribute("aria-pressed", b.dataset.pane === roomPane));
  const box = $("roomButtons"), keepScroll = box.scrollTop;
  box.classList.remove("games-pane");
  box.classList.toggle("words", roomPane === "say");
  $("hangView").classList.toggle("chesting", roomPane === "chest");
  box.classList.toggle("me-pane", ["me", "art", "shop", "home", "mural"].includes(roomPane));
  const big = ([icon, word, what, name]) => {
    const code = tapCode(what, name);
    return `<button data-tap="${what}" data-name="${name}"><span>${icon}</span>${esc(word)}${code ? `<code class="tap-code">${esc(code).replace("(", "(<wbr>")}</code>` : ""}</button>`;
  };
  if (roomPane === "games") {
    buildGamePane(box);
  } else if (roomPane === "chest") {
    buildChestPane(box);
  } else if (roomPane === "tree") {
    buildTreePane(box);
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
  } else if (roomPane === "mural") {
    buildMuralPane(box);
  } else if (roomPane === "do") {
    box.innerHTML = ROOM_PANES.do.map(big).join("") +
      (S.free_open && S.hang.free_show
        ? `<button data-perform="1"><span>🎤</span>My show<small>Play your Free stage show for everyone</small></button>` : "") +
      weddingButtonHtml();
  } else box.innerHTML = ROOM_PANES[roomPane].map(big).join("") + (roomPane === "party" ? weddingButtonHtml() : "");
  box.scrollTop = keepScroll;     // a poll refreshes the same pane in place, not back to the top
}
// ---- Coins and the shop ---------------------------------------------------------------------
function paintCoins(data) {
  if (data && data.coins !== undefined) {
    if (coinsSeen !== null && data.coins > coinsSeen) {
      const bar = $("coinBar");
      bar.classList.remove("bump"); void bar.offsetWidth; bar.classList.add("bump");
    }
    if (data.coins !== coinsSeen && roomPane === "shop") { S.hang.coins = data.coins; buildRoomButtons(); }
    const wish = S.hang.wish && S.hang.shop[S.hang.wish];
    if (wish && coinsSeen !== null && coinsSeen < wish.price && data.coins >= wish.price) {
      banner(`⭐ YOU SAVED UP! ⭐<small>You have enough for the ${esc(wish.name)}! Buy it in 🛍️ Shop.</small>`, 6000, true);
      PalStage.SFX.play("fanfare");
    }
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
    coinsDone = data.play_left <= 0;
  }
  $("coinCount").textContent = S.hang.coins;
  // What they're ⭐ saving up for, and how close they are.
  const wish = S.hang.wish && S.hang.shop[S.hang.wish];
  $("coinNote").textContent = coinsDone ? "All of today's play coins! Missions still pay." : "";
  $("coinWish").hidden = !wish;
  if (wish) {
    $("coinWishName").textContent = `⭐ ${wish.name}: ${Math.min(S.hang.coins, wish.price)} / ${wish.price}`;
    $("coinWishBar").style.width = Math.min(100, S.hang.coins / wish.price * 100) + "%";
  }
  showStars();
}
let coinsDone = false, shopTab = "furniture";
const SHOP_TABS = [["furniture", "🛋️", "Furniture"], ["room", "🔨", "Rooms"], ["look", "🎨", "Walls & floors"], ["wear", "🧢", "To wear"]];
function buildShopPane(box) {
  const {shop, coins, gifts, stuff, wish} = S.hang;
  const picture = (key, item) => item.kind === "wear" ? `<canvas data-pic="${key}"></canvas>`
    : item.kind === "furniture" ? `<canvas data-furnpic="${key}"></canvas>`
    : `<canvas class="roompic" data-roompic="${key}"></canvas>`;
  const kinds = {furniture: ["furniture"], room: ["room"], look: ["wall", "floor"], wear: ["wear"]}[shopTab];
  // Furniture can be bought again and again. Everything else is bought once.
  const mine = (key, item) => item.kind !== "furniture" && (gifts.includes(key) || stuff.includes(key));
  const all = Object.entries(shop).filter(([, item]) => kinds.includes(item.kind)).sort(([, a], [, b]) => a.price - b.price);
  const tile = ([key, item]) => {
    const have = stuff.filter(k => k === key).length, own = mine(key, item), dear = !own && coins < item.price;
    const short = item.price - coins;
    const word = own ? (item.kind === "room" ? "✔ Built" : "✔ Yours") : buyArmed === key ? "Click again to buy!"
      : wish === key && short > 0 ? `⭐ ${short} more` : `🪙 ${item.price}${have ? ` · you have ${have}` : ""}`;
    const fancy = item.kind === "wear" && item.price >= S.hang.fancy ? "✨ " : "", star = wish === key ? "⭐ " : "";
    return `<button data-buy="${key}" ${own ? "disabled" : ""} class="${dear ? "dear" : ""}${item.kind === "room" ? " room-tile" : ""}" aria-pressed="${buyArmed === key || wish === key}">` +
      `${picture(key, item)}${star}${fancy}${item.icon && item.kind === "room" ? item.icon + " " : ""}${esc(item.name)}<small>${word}</small></button>`;
  };
  const now = all.filter(([key, item]) => !mine(key, item) && coins >= item.price), later = all.filter(([key, item]) => !mine(key, item) && coins < item.price);
  const done = all.filter(([key, item]) => mine(key, item));
  box.innerHTML = `<div class="shop-tabs">` + SHOP_TABS.map(([tab, icon, word]) =>
      `<button data-shoptab="${tab}" aria-pressed="${shopTab === tab}"><span>${icon}</span>${word}</button>`).join("") + `</div>` +
    (shopTab === "furniture" ? `<p class="me-note">Buy things more than once! At home, ✋ pick one up to paint it.</p>` : "") +
    (now.length ? `<h4>🪙 You can buy these now</h4>` + now.map(tile).join("") : "") +
    (later.length ? `<h4>💰 Save up: click one to ⭐ wish for it</h4>` + later.map(tile).join("") : "") +
    (shopTab === "wear" ? `<button class="wide" data-pane="me"><span>✏️</span>Wear your own drawing: 🪙 ${S.hang.my_wear_price}<small>Make it in 🧢 Me</small></button>` : "") +
    (done.length ? `<h4>✔ Yours already</h4>` + done.map(tile).join("") : "");
  paintPanePictures(box);
}
function paintPanePictures(box) {
  const copy = (cv, img) => { cv.width = img.width; cv.height = img.height; cv.getContext("2d").drawImage(img, 0, 0); };
  box.querySelectorAll("[data-pic]").forEach(cv => wearInto(cv, cv.dataset.pic, 3));
  box.querySelectorAll("[data-furnpic]").forEach(cv => copy(cv, PalHang.furniturePicture(cv.dataset.furnpic, +(cv.dataset.paint || 0))));
  box.querySelectorAll("[data-roompic]").forEach(cv => {     // a room as it'll look, or a wall or floor in a plain room
    const key = cv.dataset.roompic, room = S.hang.rooms[key];
    copy(cv, room ? PalHang.roomPicture(key, room.wall, room.floor)
      : PalHang.roomPicture("", key in S.hang.walls ? key : "w_cream", key in S.hang.floors ? key : "f_wood"));
  });
}
async function wishFor(key) {
  const out = await tap("wish", {key});
  if (!out || !out.ok) return;
  buyArmed = null;        // a wish isn't the first click of a purchase
  S.hang.wish = out.wish;
  if (key) { PalStage.SFX.play("ding"); tipFor(`⭐ Saving up for the ${S.hang.shop[key].name}! You need ${S.hang.shop[key].price - S.hang.coins} more coins. A coding mission pays the most!`, 5000); }
  paintCoins();
  buildRoomButtons();
}
async function buy(key) {
  const item = S.hang.shop[key];
  if (S.hang.coins < item.price) { wishFor(S.hang.wish === key ? null : key); return; }
  if (buyArmed !== key) { buyArmed = key; buildRoomButtons(); return; }
  buyArmed = null;
  const out = await tap("buy", {key});
  if (!out || !out.ok) { if (out && out.error) tipFor(out.error); buildRoomButtons(); return; }
  Object.assign(S.hang, {coins: out.coins, gifts: out.gifts, stuff: out.stuff});
  coinsSeen = out.coins;
  PalStage.SFX.play("gift");
  if (S.hang.wish === key) S.hang.wish = null;
  const here = myHome() && item.kind === "furniture";
  tipFor(item.kind === "room" ? `You built a ${item.name.toLowerCase()}! ${myHome() ? "It's at the end of your home: walk through the doorways!" : "Go to 🏠 Home and walk through the doorways to see it."}`
    : here ? `🛍️ Got it: ${item.name}! 👉 Now click the floor to put it there.`
    : `🛍️ Got it: ${item.name}! ${item.kind === "wear" ? "Put it on in 🧢 Me." : "Put it out in 🏠 Home."}`, 5000);
  if (here) { roomPane = "home"; furnArmed = {key}; moving = false; }     // straight to putting it out
  homeGrew(out.grew);
  paintCoins();
  buildRoomButtons();
  if (here) $("roomButtons").scrollTop = 0;     // straight to the top, to put the new thing out
}

// ---- A home of your own -----------------------------------------------------------------------
// It's a row of rooms to walk through, and it grows by levels as it fills up (pixel.py
// HOME_LEVELS). Each level wins a prize.
const homeFree = item => !item.price && !item.prize && !item.room;
function homeLevelCard(home) {
  const levels = S.hang.levels, now = levels[home.level], after = levels[home.level + 1];
  const part = after ? Math.max(0, Math.min(100, Math.round((home.points - now[1]) / (after[1] - now[1]) * 100))) : 100;
  return `<p class="me-note home-level"><b>🏡 ${esc(home.mine ? "Your home" : home.name + "'s home")}: ${esc(now[0])}</b>
    <span>⭐ ${home.points} points · ❤️ ${home.hearts} heart${home.hearts === 1 ? "" : "s"}</span>
    <i class="goal-bar"><i style="width:${part}%"></i></i>
    <small>${after ? `${after[1] - home.points} more point${after[1] - home.points === 1 ? "" : "s"} to <b>${esc(after[0])}</b>` : "The best home there is! 👑"}</small></p>`;
}
function homeGrew(name) {
  if (!name) return;
  banner(`🏡 YOUR HOME GREW! 🏡<small>It's a ${esc(name)} now! Look in 🏠 Home for your prize.</small>`, 6000, true);
  PalStage.SFX.play("fanfare");
}
const roomNow = () => Math.min(roomInView, roomInfo.home.rooms.length - 1);
function buildHomePane(box) {
  const {furniture, walls, floors, stuff, levels} = S.hang, home = roomInfo && roomInfo.home;
  const others = ((roomInfo && roomInfo.people) || []).filter(m => m.seat !== roomInfo.you);
  const rooms = home ? `<h4>🚪 ${home.mine ? "Your rooms" : "Rooms"}</h4>` + home.rooms.map((r, i) =>
    `<button data-goroom="${i}" aria-pressed="${i === roomNow()}"><span>${(S.hang.rooms[r.kind] || {icon: "🛋️"}).icon}</span>${esc(r.name)}</button>`).join("") +
    (home.mine && home.more ? `<button data-pane="shop" data-roomshop="1"><span>🔨</span>Build a room<small>in the 🛍️ Shop</small></button>` : "") : "";
  const visit = others.length ? `<h4>🚪 Visit a friend's home</h4>` + others.map(m => `<button data-home="${m.seat}"><span>🏡</span>${esc(m.name)}</button>`).join("") : "";
  if (!home || !home.mine) {
    const heart = home ? `<button class="wide" data-heart="1" ${home.hearted ? "disabled" : ""}><span>❤️</span>${home.hearted ? "You gave this home a heart" : "Give this home a heart"}</button>` : "";
    box.innerHTML = (home ? homeLevelCard(home) : "") + `<p class="me-note">${home ? `You're visiting ${esc(home.name)}'s home. Walk through the doorways and click their things to play!`
      : "Everyone has a home. Fill yours with things from the 🛍️ Shop, build more rooms, and make it grow into a castle!"}</p>` + heart +
      `<button class="wide" data-home="mine"><span>🏠</span>Go to my home</button>${home ? `<button class="wide" data-home="out"><span>🚪</span>Go back outside</button>` : ""}` +
      (home ? rooms : "") + visit;
    return;
  }
  const kindOf = key => (key in furniture ? furniture : key in walls ? walls : floors)[key];
  const have = key => homeFree(kindOf(key)) || stuff.includes(key);
  const copies = key => stuff.filter(k => k === key).length || 1, outOf = key => home.items.filter(i => i.key === key).length;
  const n = roomNow(), room = home.rooms[n], armed = furnArmed && furniture[furnArmed.key];
  const held = furnArmed && furnArmed.piece && home.items.find(i => i.id === furnArmed.piece);
  const note = held ? `✋ You picked up the ${armed.name}! Click the floor to put it down, or change it here.`
    : armed ? `👉 Click the floor to put it there: ${armed.name}!`
    : moving ? "✋ Click one of your things in the picture to pick it up." : "Pick one of 🛋️ Your things below, then click the floor to put it there.";
  // A thing that's picked up can be painted, flipped and sized. It's free.
  const style = held ? `<h4>🎨 Paint it</h4><div class="paint-row">` + Array.from({length: S.hang.paints}, (_, i) =>
      `<button data-paint="${i}" aria-pressed="${(held.paint || 0) === i}" title="${i ? "Paint it" : "How it came"}"><canvas data-furnpic="${held.key}" data-paint="${i}"></canvas></button>`).join("") + `</div>` +
    `<h4>📏 Make it</h4>` + ["Small", "Normal", "Big"].map((word, i) =>
      `<button data-size="${i}" aria-pressed="${(held.size === undefined ? 1 : held.size) === i}"><span>${["🐭", "🙂", "🐘"][i]}</span>${word}</button>`).join("") +
    `<button class="wide" data-flip="1"><span>🔁</span>Flip it round</button>` : "";
  const prizes = Object.entries({...furniture, ...walls, ...floors}).filter(([key, item]) => item.prize && !stuff.includes(key));
  box.innerHTML = (held ? "" : homeLevelCard(home) +     // a thing in hand: what to do with it comes first
    `<p class="me-note">Get points: ⭐ 1 for each thing you put out, ⭐ 2 for a drawing with code, ⭐ 3 for each room you build, ⭐ 1 for each ❤️ from a friend.</p>`) +
    `<p class="me-note"><b>${esc(room.name)}</b> · ${note}</p>` +
    `<button class="wide" data-moving="1" aria-pressed="${moving || !!held}"><span>✋</span>${moving || held ? "Done" : "Move, paint or resize my things"}</button>` +
    style + (held ? `<button class="wide" data-away="${furnArmed.piece}"><span>📦</span>Put it away</button>` : "") +
    `<h4>🛋️ Your things</h4>` + Object.keys(furniture).filter(have).map(key =>
      `<button data-furn="${key}" aria-pressed="${!!furnArmed && !furnArmed.piece && furnArmed.key === key}"><canvas data-furnpic="${key}"></canvas>${esc(furniture[key].name)}<small>${outOf(key)} of ${copies(key)} out</small></button>`).join("") +
    `<p class="me-note">Want more? You can buy things more than once in the 🛍️ Shop.</p>` + rooms +
    `<h4>🎨 Walls and floors for the ${esc(room.name.toLowerCase())}</h4>` + [...Object.keys(walls), ...Object.keys(floors)].filter(have).map(key =>
      `<button data-look="${key}" aria-pressed="${room.wall === key || room.floor === key}"><i class="swatch" style="background:${PalHang.lookColour(key)}"></i>${esc(kindOf(key).name)}</button>`).join("") +
    (prizes.length ? `<h4>🏆 Prizes still to win</h4>` + prizes.map(([key, item]) =>
      `<button class="locked" data-prize="${key}">${key in furniture ? `<canvas data-furnpic="${key}"></canvas>` : `<i class="swatch" style="background:${PalHang.lookColour(key)}"></i>`}${esc(item.name)}<small>🔒 ${esc(levels[item.prize][0])}</small></button>`).join("") : "") +
    `<h4>🛠️ Make your own furniture</h4>
     <p class="me-note">Draw a chair, a lamp, a magic bed... anything! Put it in your home from 🖼️ Art, then give it code.</p>
     <button class="wide" data-drawthing="1"><span>✏️</span>Draw new furniture</button>
     <button class="wide" data-pane="art"><span>🖼️</span>Put a drawing in my home</button>` + thingTiles() +
    `<button class="wide" data-home="out"><span>🚪</span>Go back outside</button>` + visit;
  paintPanePictures(box);
  box.querySelectorAll("[data-artpic]").forEach(cv => drawingInto(cv, shelfList.find(p => p.key === cv.dataset.artpic)));
}
async function goHome(where) {
  fishing = null; furnArmed = artArmed = null; moving = false;
  PalStage.SFX.wake();
  const out = await tap("home", where === "out" ? {out: true} : where === "mine" ? {} : {seat: +where});
  if (out && out.error) tipFor(out.error);
  else if (out && out.ok && where !== "out") { roomPane = "home"; buildRoomButtons(); $("roomButtons").scrollTop = 0; homeGrew(out.grew); }
}
async function furnish(data) {
  PalStage.SFX.play("pop");
  const out = await tap("furnish", data);
  if (out && out.error && out.error.length > 8) tipFor(out.error, 5000);
  homeGrew(out && out.grew);
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
  const out = ((roomStage && roomStage.state.placed) || []).filter(p => p.mine && (!atHome() || Math.floor(p.x / PalStage.W) === roomNow())).length;
  const max = atHome() ? S.hang.art_max : S.hang.place_max, where = atHome() ? "wall or floor of this room" : "world";
  const note = atHome() && !myHome() ? "You can hang drawings up in your own home, or outside."
    : !pics.length ? "Draw something first, then come back and put it up!"
    : artArmed ? `👉 Now click the ${where} where you want it!`
    : `Pick a drawing, then click the ${where} to put it there. Click one you put out to take it back. (${out} of ${max} out${out >= max ? ": a new one replaces your oldest" : ""})`;
  box.innerHTML = `<p class="me-note">${note}</p>` +
    `<button class="wide" data-pane="mural"><span>🖼️</span>Class mural<small>Paint a square with everyone, live!</small></button>` +
    pics.map(d =>
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
// ---- 🖼️ The class mural ------------------------------------------------------------------
// The same 40 x 24 grid as the server. One tap paints one square; the server says
// whether it took, and everyone else sees the batch of new squares within a second.
const MURAL_WHO = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
const muralData = () => roomInfo && roomInfo.mural;
function muralPainters(m) {
  const counts = new Map();
  for (const ch of m.who) {
    if (ch === ".") continue;
    const name = m.names[MURAL_WHO.indexOf(ch)];
    if (name) counts.set(name, (counts.get(name) || 0) + 1);
  }
  return [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}
function paintMuralBoard() {
  const cv = $("muralBoard"), m = muralData();
  if (!cv || !m) return;
  cv.width = m.w; cv.height = m.h;
  const g = cv.getContext("2d");
  g.clearRect(0, 0, m.w, m.h);
  for (let i = 0; i < m.w * m.h; i++) {
    const x = i % m.w, y = Math.floor(i / m.w), ink = m.grid[i];
    if (ink && ink !== ".") g.fillStyle = m.colours[parseInt(ink, 16)] || "#fffdf6";
    else g.fillStyle = (x + y) % 2 ? "#f4f0e4" : "#fffdf6";
    g.fillRect(x, y, 1, 1);
  }
}
function muralMineWords(m) {
  const today = m.painted_today || 0, mine = m.mine || 0, at = m.reward_at || 10;
  if (m.reward_done) return `You painted ${today} square${today === 1 ? "" : "s"} today. 🖼️ Treat earned! You have ${mine} up now.`;
  const left = Math.max(0, at - today);
  return `You painted ${today} today${left ? ` · ${left} more for a little treat` : ""}. You have ${mine} square${mine === 1 ? "" : "s"} up now.`;
}
function mergeMural(full) {
  // A clear/remove arrives as the whole picture for everyone. Keep this screen's
  // own "today" numbers, and work out its squares again from the who string.
  const m = muralData();
  if (!m) { if (roomInfo) roomInfo.mural = full; return; }
  for (const key of ["w", "h", "grid", "who", "names", "colours", "idea", "total"]) if (key in full) m[key] = full[key];
  if (full.me !== undefined && full.me !== null) {
    m.me = full.me;
    if (full.mine !== undefined) m.mine = full.mine;
  } else if (m.me !== null && m.me !== undefined) {
    const ch = MURAL_WHO[m.me];
    m.mine = [...m.who].filter(owner => owner === ch).length;
  }
}
function muralRefresh() {
  const m = muralData(), mine = $("muralMine"), painters = $("muralPainters");
  if (!m) return;
  paintMuralBoard();
  if (mine) mine.textContent = muralMineWords(m);
  if (painters) {
    const list = muralPainters(m);
    painters.innerHTML = list.length ? "Painted by " + list.map(([name, n]) => `<b>${esc(name)}</b> ${n}`).join(" · ") : "Nobody has painted yet. You can be first!";
  }
}
function applyMuralCell(i, ch, by) {
  const m = muralData();
  if (!m || !(i >= 0 && i < m.grid.length)) return;
  m.grid = m.grid.slice(0, i) + ch + m.grid.slice(i + 1);
  if (ch === ".") m.who = m.who.slice(0, i) + "." + m.who.slice(i + 1);
  else if (by) {
    let slot = m.names.indexOf(by);
    if (slot < 0 && m.names.length < MURAL_WHO.length) { m.names.push(by); slot = m.names.length - 1; }
    m.who = m.who.slice(0, i) + (slot >= 0 ? MURAL_WHO[slot] : ".") + m.who.slice(i + 1);
  }
}
function buildMuralPane(box) {
  const m = muralData();
  if (!m) { box.innerHTML = `<p class="me-note">The class mural is getting ready. Try again in a moment.</p>`; return; }
  box.classList.add("me-pane");
  box.innerHTML = `<p class="me-note mural-idea">🖼️ Today's idea: <b>${esc(m.idea)}</b></p>
    <div class="mural-wrap"><canvas id="muralBoard" width="${m.w}" height="${m.h}" aria-label="The class mural. Tap a square to paint it."></canvas><i id="muralHover" hidden></i></div>
    <div class="mural-inks">` +
    m.colours.map((c, i) => `<button data-mural-ink="${i}" style="background:${c}" aria-pressed="${muralInk === i}" title="Colour ${i + 1}"></button>`).join("") +
    `<button class="mural-eraser" data-mural-ink="-1" aria-pressed="${muralInk === -1}" title="Eraser">🧽</button></div>
    <div class="mural-tools">
      <button data-mural-undo="1"><span>↶</span>Undo my last</button>
      <button data-mural-who="1" aria-pressed="${muralWhoMode}"><span>🔍</span>${muralWhoMode ? "Painting again" : "Who painted?"}</button>
    </div>
    <p class="me-note">Tap a colour, then a square. One tap = one square.</p>
    <p class="me-note" id="muralMine"></p>
    <p class="me-note" id="muralPainters"></p>`;
  muralRefresh();
  const cv = $("muralBoard"), hover = $("muralHover");
  const at = e => {
    const r = cv.getBoundingClientRect();
    const col = Math.floor((e.clientX - r.left) / r.width * m.w), row = Math.floor((e.clientY - r.top) / r.height * m.h);
    return col >= 0 && col < m.w && row >= 0 && row < m.h ? {col, row, i: row * m.w + col} : null;
  };
  cv.addEventListener("pointermove", e => {
    const p = at(e);
    hover.hidden = !p;
    if (!p) return;
    hover.style.left = p.col / m.w * 100 + "%"; hover.style.top = p.row / m.h * 100 + "%";
    hover.style.width = 100 / m.w + "%"; hover.style.height = 100 / m.h + "%";
  });
  cv.addEventListener("pointerleave", () => { hover.hidden = true; });
  cv.addEventListener("click", e => {
    const p = at(e);
    if (!p) return;
    PalStage.SFX.wake();
    if (muralWhoMode) {
      const mm = muralData() || m, ch = mm.who[p.i], name = ch && ch !== "." ? mm.names[MURAL_WHO.indexOf(ch)] : "";
      tipFor(name ? `🖼️ That square is by ${name}.` : "🖼️ Nobody has painted that square yet.", 4000);
      return;
    }
    PalStage.SFX.play("click");
    post("/pixel/room/do", {id: me, what: "mural", action: "paint", cell: p.i, ink: muralInk}).then(out => {
      if (!out) return;
      if (out.error) { tipFor(out.error === "wait" ? "Slow down a little! 3 squares a second." : out.error, 3500); return; }
      applyMuralCell(out.cell, out.ink, out.by);
      const m2 = muralData();
      if (m2) {
        if (out.me !== undefined && out.me !== null) m2.me = out.me;
        if (out.mine !== undefined) m2.mine = out.mine;
        if (out.painted_today !== undefined) m2.painted_today = out.painted_today;
        if (out.reward_done !== undefined) m2.reward_done = out.reward_done;
      }
      muralRefresh();
      if (out.coins || (out.badges && out.badges.length)) {
        showRewards({coins: out.coins, badges: out.badges});
        if (out.coins) tipFor(`🖼️ 10 squares painted! +${out.coins} 🪙 for you.`, 5000);
      }
    });
  });
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
                    rounds: ["🎮", n => `Play ${n} game rounds`], stars: ["⭐", n => `Earn ${n} mission stars`],
                    chests: ["🧰", n => `Code ${n} chests open`], presents: ["🎁", n => `Find ${n} presents in winter`],
                    snowballs: ["⛄", n => `Roll ${n} snowballs onto the class snowman`]};
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
  return `The ${item.name} can come out of a 🎁 gift box. Finish a mission, play a game, or do all 3 of today's 🎯 jobs to get one!`;
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
  box.innerHTML = hide + who + ownWearHtml(pics) + goals + (gifts.length ? "" : `<p class="me-note">Finish a mission or all 3 of today's 🎯 jobs to get a gift box! Click a 🔒 thing to see how to get it.</p>`) + slots +
    `<h4>🙌 Friends you've high-fived: ${friends.length}</h4><p class="me-note">${friends.length ? friends.map(esc).join(", ") : "Click a friend's pal to high-five them."}</p>` +
    `<h4>🎣 Fish book: ${Object.keys(fish).length} of ${Object.keys(book).length}</h4><p class="me-note fish-book">${Object.keys(book).map(k =>
      fish[k] ? `<span title="${esc(book[k][1])}">${book[k][0]}<small>×${fish[k]}</small></span>` : "❔").join(" ")}</p>` +
    (Object.keys(fish).length ? "" : `<p class="me-note">Click the pier at the Beach (the blue ring) to go fishing.</p>`);
  box.querySelectorAll("[data-pic]").forEach(cv => wearInto(cv, cv.dataset.pic, 3));
  box.querySelectorAll("[data-palpic]").forEach(cv => drawingInto(cv, pics.find(p => p.key === cv.dataset.palpic)));
  box.querySelectorAll("[data-sewpic]").forEach(cv => drawingInto(cv, pics.find(p => p.key === cv.dataset.sewpic)));
  box.querySelectorAll("[data-ownpic]").forEach(cv => {
    const own = (S.hang.mywear || []).find(w => w.key === cv.dataset.ownpic), img = own && PalStage.wearPicture("", own.art);
    if (!img) return;
    const zoom = Math.max(1, Math.floor(30 / Math.max(img.width, img.height)));
    cv.width = img.width * zoom; cv.height = img.height * zoom;
    const g = cv.getContext("2d");
    g.imageSmoothingEnabled = false;
    g.drawImage(img, 0, 0, cv.width, cv.height);
  });
}
// ✏️ Wear your own drawing: pick a drawing, then hat or face. It's a copy, so it stays the same.
let sewPick = null, sewBin = false;
function ownWearHtml(pics) {
  const own = S.hang.mywear || [], price = S.hang.my_wear_price, wear = S.hang.wear, full = own.length >= S.hang.my_wear_max;
  let html = `<h4>✏️ Wear your own drawing <small>🪙 ${price} each</small></h4>`;
  html += own.map(w => sewBin
    ? `<button data-unsew="${esc(w.key)}"><canvas data-ownpic="${esc(w.key)}"></canvas>${esc(w.name)}<small>🗑 Click to throw away</small></button>`
    : `<button data-wear="${esc(w.key)}" data-slot="${w.slot}" aria-pressed="${wear[w.slot] === w.key}"><canvas data-ownpic="${esc(w.key)}"></canvas>${esc(w.name)}<small>${w.slot === "hat" ? "🎩 Hat" : "👓 Face"}</small></button>`).join("");
  if (own.length) html += `<button data-sewbin="1" aria-pressed="${sewBin}"><span>🗑</span>${sewBin ? "Done" : "Throw one away"}</button>`;
  if (!pics.length) return html + `<p class="me-note">Draw a hat or some glasses in ✏️ Draw. Then come back and wear it!</p>`;
  if (full) return html + `<p class="me-note">You have ${own.length}, the most you can have. Throw one away to make a new one.</p>`;
  if (!sewPick) return html + `<button class="wide" data-sew="start"><span>🧵</span>Make a new one</button>`;
  if (sewPick === "pick") return html + `<p class="me-note">👉 Which drawing do you want to wear?</p>` +
    pics.map(d => `<button data-sewkey="${esc(d.key)}"><canvas data-sewpic="${esc(d.key)}"></canvas>${esc(d.title || "My drawing")}</button>`).join("") +
    `<button data-sew="cancel"><span>✖</span>Not now</button>`;
  const short = price - S.hang.coins;
  return html + `<p class="me-note">👉 Where does it go? ${short > 0 ? `You need ${short} more 🪙 coins. A coding mission pays the most!` : `It costs 🪙 ${price}.`}</p>
    <button data-sewslot="hat" ${short > 0 ? "disabled" : ""}><span>🎩</span>On my head</button>
    <button data-sewslot="face" ${short > 0 ? "disabled" : ""}><span>👓</span>On my face</button>
    <button data-sew="cancel"><span>✖</span>Not now</button>`;
}
async function sew(slot) {
  const key = sewPick;
  sewPick = null;
  const out = await tap("sew", {key, slot});
  if (!out || !out.ok) { tipFor((out && out.error) || "Couldn't reach the Hang out. Please try again."); buildRoomButtons(); return; }
  Object.assign(S.hang, {coins: out.coins, mywear: out.mywear, wear: out.wear});
  coinsSeen = out.coins;
  PalStage.SFX.play("gift");
  tipFor(`✏️ You're wearing ${out.item.name}! Everyone can see it.`, 5000);
  paintCoins();
  buildRoomButtons();
}
async function unsew(key) {
  const out = await tap("unsew", {item: key});
  if (!out || !out.ok) return;
  Object.assign(S.hang, {mywear: out.mywear, wear: out.wear});
  if (!out.mywear.length) sewBin = false;
  buildRoomButtons();
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
  b.hidden = !move && !open;      // locked, it only repeats what 💻 Next mission says, so it waits out of the way
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
  if (fix) return {key: fix.key, fix: true, name: fix.name};
  return S.free_open ? {key: "free", free: true, name: "Free stage"} : null;     // all done: there's always a show to make
}
function paintNextMission() {
  const b = $("nextMission"), next = nextCoding();
  b.hidden = !next;
  if (!next) return;
  const giftLeft = Object.entries(S.hang.catalog).some(([k, g]) => !g.class && !g.price && !g.goal && !S.hang.gifts.includes(k));
  b.innerHTML = next.free
    ? `<b>🎬 Free stage</b><small>Make any show you like, with stage toys</small>`
    : next.fix
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
  if (!out || !out.ok) {
    // The server says "wait" if a show is playing. Say so, rather than doing nothing.
    if (out && out.error === "wait") tipFor("One thing at a time! Wait for the show to finish.", 4000);
    else if (out && out.error && out.error.length > 8) tipFor(out.error, 5000);
    return;
  }
  const wait = Math.max(6000, out.ms);
  moveReadyAt = performance.now() + wait;
  paintMoveButton();
  setTimeout(paintMoveButton, wait + 50);
}
async function pressPerform() {
  PalStage.SFX.wake();
  const out = await tap("perform");
  if (!out || !out.ok) {
    tipFor((out && out.error) || "Couldn't start your show. Try again.", 6000);
    return;
  }
  // A show and a My Move use the same pal for everyone: hold My Move until it ends.
  const wait = Math.max(6000, out.ms || 0);
  moveReadyAt = performance.now() + wait;
  paintMoveButton();
  setTimeout(paintMoveButton, wait + 50);
  if (out.badges && out.badges.length) showRewards({badges: out.badges});
}

// ---- What just happened -------------------------------------------------------------------
// While a student codes at a shut 🧰 chest, nothing covers the world: small news is skipped,
// and big news waits until they open it or leave. The teacher's class photo still shows.
let bannerHeld = null;
const chestBusy = () => roomPane === "chest" && chestNow() && !chestNow().open;
function banner(html, ms, big = false, now = false) {
  if (!now && chestBusy()) { if (big) bannerHeld = [html, ms, big]; return; }
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
  if (e.kind === "mural") {                  // a batch of new squares from everyone
    if (e.mural) mergeMural(e.mural);
    else if (Array.isArray(e.cells) && roomInfo && roomInfo.mural) for (const cell of e.cells) applyMuralCell(cell[0], cell[1], cell[2] || "");
    if (roomPane === "mural") muralRefresh();
    return;
  }
  if ((e.kind === "place" || e.kind === "unplace") && roomPane === "art") buildRoomButtons();
  if (e.kind === "game" && e.message) {
    // "The seeker is counting!" is said to everyone, but the seeker is the one who
    // has to count, so their tip comes from the game itself ("You're counting...").
    const g = (roomStage && roomStage.state.game) || currentGame();     // the event's state, not the last poll's
    tipFor(g && g.kind === "hide" && g.phase === "hiding" ? gameTip(g) : e.message);
    if (g && g.kind === "fashion" && e.moment) banner(esc(e.message), 3500);
  } else if (e.kind === "mymove") {
    banner(e.perform ? `🎤 <b>${esc(e.by)}</b>'s show` : `✨ <b>${esc(e.by)}</b>: ${esc(e.title)}`, e.ms + 700);
    if (e.seat !== you) showClap(e.seat, e.by, e.ms + 700);
  } else if (e.kind === "party") {
    banner(`🎉 CLASS PARTY! 🎉${e.reward ? `<small>New for everyone: ${esc(e.reward.name)}</small>` : ""}`, 6000, true);
    if (e.reward && e.reward.kind === "gift" && !S.hang.gifts.includes(e.reward.key)) S.hang.gifts.push(e.reward.key);
    if (roomPane === "me") buildRoomButtons();
  } else if (e.kind === "photo") {             // the teacher's class photo: everyone lined up in the Park
    banner(`📸 Class photo! Say cheese!<small>Look at the big screen</small>`, 5000, true, true);
    PalStage.SFX.play("ding");
  } else if (e.kind === "danceparty") {        // 3 pals danced at once
    roomStage.roomApply({kind: "fx", name: "confetti", x: e.x}, false);
    banner(`🪩 Dance party! 🪩<small>${e.seats.length} pals dancing together · +1 for the class party</small>`, 4000, true);
    PalStage.SFX.play("yay");
  } else if (e.kind === "shower") {
    banner("🌠 Star shower! Run and catch them!", 3500);
  } else if (e.kind === "tree") {
    roomStage.state.tree = e.tree;
    if (roomPane === "tree") buildRoomButtons();
  } else if (e.kind === "snowman") {
    roomStage.state.snowman = {balls: e.balls, need: e.need, built: e.built};
    if (roomPane === "games" && !currentGame()) buildRoomButtons();
    if (e.done) {
      roomStage.state.snowmanDone = performance.now();
      roomStage.roomApply({kind: "fx", name: "confetti", x: e.x}, false);
      banner(`⛄ The class built a snowman! ⛄<small>That's ${e.built} today · +2 for the class party</small>`, 5000, true);
      PalStage.SFX.play("yay");
    }
  } else if (e.kind === "five" && (e.fresh || []).includes(you)) {
    const other = roomStage.state.room.find(m => m.seat === (e.seat === you ? e.other : e.seat));
    if (other && !S.hang.friends.includes(other.name)) S.hang.friends.push(other.name);
    if (other) tipFor(`🙌 New friend: ${other.name}! That's ${S.hang.friends.length}.`);
    if (roomPane === "me") buildRoomButtons();
  } else if (e.kind === "wedding") {
    weddingEvent(e, you);
  }
}
function roomState(data) {
  const wasMural = roomInfo && roomInfo.mural;
  roomInfo = data;
  if (!data.mural && wasMural) data.mural = wasMural;     // snapshots carry the picture; small updates keep it
  paintGameState(data);
  let freshStuff = false;       // prizes and new rooms arrive here, not only from a buy
  if (data.stuff) {
    const oldStuff = JSON.stringify(S.hang.stuff || []);
    if (oldStuff !== JSON.stringify(data.stuff)) {
      S.hang.stuff = data.stuff;
      freshStuff = true;
    }
  }
  const open = data.open;
  $("roomClosed").hidden = open;
  $("roomButtons").style.visibility = open ? "" : "hidden";
  $("myMove").style.visibility = open ? "" : "hidden";
  $("roomType").hidden = !open || !data.words;
  paintMeter(data.meter);
  paintCoins(data);
  paintJobs(data.jobs);
  if (roomStage) {
    roomStage.state.snowman = data.snowman || null;
    roomStage.state.wedding = data.wedding || null;
    if (data.tree) roomStage.state.tree = data.tree;
    if ("ornament" in data) myOrnament = data.ornament;
  }
  const wedding = JSON.stringify(data.wedding || null);
  if (wedding !== weddingSeen) {
    weddingSeen = wedding;
    if (roomPane === "do" || roomPane === "party") buildRoomButtons();
  }
  if (!open) clearWeddingCard();
  const home = JSON.stringify(data.home), people = JSON.stringify(data.people);
  if (home !== homeSeen || people !== peopleSeen || freshStuff) {
    if (!data.home !== (homeSeen === "null" || !homeSeen)) { furnArmed = artArmed = null; fishing = null; moving = false; $("roomTip").textContent = roomTipNow(); }
    homeSeen = home; peopleSeen = people;
    if (["home", "art", "shop"].includes(roomPane)) buildRoomButtons();
  }
  if (open && !data.you && !roomJoining) {
    roomJoining = true;
    tap("join").finally(() => { roomJoining = false; });
  }
  const places = data.places.join() + "|" + data.people.filter(m => !m.loc).map(m => m.seat + m.name).join();     // places, and who's outside to go to
  if (places !== placesSeen) { placesSeen = places; if (roomPane === "place") buildRoomButtons(); }
  for (const e of data.events) roomEvent(e, data.you);
  if (data.mural && roomPane === "mural") muralRefresh();
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
      `${j.key === "star" && !jobDone(j) ? `<button class="job-go" data-go-code="1">💻 Go code</button>` : ""}` +
      `${j.key === "chest" && !jobDone(j) ? `<button class="job-go" data-go-chest="1">🧰 Take me</button>` : ""}</p>` +
      (j.how && !jobDone(j) ? `<p class="job-how">${esc(j.how)}</p>` : "")).join("") + `</div>`;
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
  const inView = Math.max(0, Math.floor((st.camX + PalStage.W / 2) / PalStage.W));
  if (inView !== roomInView) { roomInView = inView; if (atHome() && ["home", "art"].includes(roomPane)) buildRoomButtons(); }
  if (place && $("hangView").dataset.place !== place) $("hangView").dataset.place = place;
}
function lookForGem(mine) {
  tintPage();
  gameTick(mine);
  fishTick(mine);
  if (inRound()) return;
  roomStage.state.chests = S.hang.chests;
  lookForChest(mine);
  lookForWinter(mine);
  const st = roomStage.state, key = PalHang.gemAt(st.places || ["park"], mine.x, mine.y, st.found);
  if (!key) return;
  st.found.add(key);
  tap("find", {key}).then(out => {
    if (!out || !out.ok) return;
    if (!S.hang.found.includes(key)) S.hang.found.push(key);     // so the gem stays found when you come back
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
      moveEnded: m => { if (m.me && m.claps) tipFor(`👏 ${m.claps} clap${m.claps === 1 ? "" : "s"} for your ${m.perform ? "show" : "move"}!`); },
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
  $("roomButtons").scrollTop = 0;
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
  $("roomButtons").scrollTop = 0;
  banner(`🎉 Welcome to the Hang out!<small>Click the ground to walk. Today's 🎯 jobs are in Games, on the right.</small>`, 7000, true);
}
function closeRoom() {
  if (!stopRoom) return;
  clearWeddingCard();
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
  // Walking onto a shut 🧰 chest stops beside it, so the pal doesn't hide it.
  const places = roomStage.state.places || ["park"], c = !atHome() && PalHang.chestAt(places, x, y, S.hang.chests);
  if (c) { const cx = places.indexOf(c.place) * PalStage.W + c.x; x = cx + (mine.x < cx ? -22 : 22); }
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
$("weddingCard").addEventListener("click", e => {
  const b = e.target.closest("[data-wedding]");
  if (!b) return;
  const what = b.dataset.wedding;
  if (what === "pick") pickWeddingPartner(b.dataset.seat, b.dataset.name || "your friend");
  else if (what === "yes") answerWedding(true);
  else if (what === "no") answerWedding(false);
  else if (what === "cancel") cancelWedding();
  else if (what === "retry") { clearWeddingCard(); startWedding(); }
  else if (what === "dismiss") clearWeddingCard();
});
$("roomTabs").addEventListener("click", e => {
  const b = e.target.closest("[data-pane]");
  if (b) { roomPane = b.dataset.pane; artArmed = furnArmed = buyArmed = null; moving = false; buildRoomButtons(); $("roomButtons").scrollTop = 0; }
});
$("roomButtons").addEventListener("click", e => {
  // dataset keys are camelCase: data-mural-ink is dataset.muralInk
  const pick = name => { const el = e.target.closest(`[data-${name}]`); return el && !el.disabled ? el.dataset[name.replace(/-(\w)/g, (_, c) => c.toUpperCase())] : null; };
  if (e.target.closest("[data-wedding-start]")) { startWedding(); return; }
  if (pick("perform")) { pressPerform(); return; }
  if (pick("mural-ink")) {
    muralInk = +pick("mural-ink");
    PalStage.SFX.wake(); PalStage.SFX.play("click");
    $("roomButtons").querySelectorAll("[data-mural-ink]").forEach(b => b.setAttribute("aria-pressed", +b.dataset.muralInk === muralInk));
    return;
  }
  if (pick("mural-who")) {
    muralWhoMode = !muralWhoMode;
    PalStage.SFX.play("click");
    buildRoomButtons();
    return;
  }
  if (pick("mural-undo")) {
    PalStage.SFX.wake();
    post("/pixel/room/do", {id: me, what: "mural", action: "undo"}).then(out => {
      if (!out) return;
      if (out.error) { tipFor(out.error === "nothing" ? "You haven't painted a square yet." : out.error, 3500); return; }
      applyMuralCell(out.cell, out.ink, "");
      const m = muralData();
      if (m) {
        if (out.me !== undefined && out.me !== null) m.me = out.me;
        if (out.mine !== undefined) m.mine = out.mine;
        if (out.painted_today !== undefined) m.painted_today = out.painted_today;
      }
      PalStage.SFX.play("pop");
      muralRefresh();
    });
    return;
  }
  if (pick("buy")) { buy(pick("buy")); return; }
  if (pick("shoptab")) { shopTab = pick("shoptab"); buyArmed = null; buildRoomButtons(); $("roomButtons").scrollTop = 0; return; }
  if (furnArmed && furnArmed.piece && (pick("paint") || pick("size") || pick("flip"))) {
    const held = roomInfo.home.items.find(i => i.id === furnArmed.piece);
    if (!held) return;
    const change = pick("paint") ? {paint: +pick("paint")} : pick("size") ? {size: +pick("size")} : {flip: !held.flip};
    Object.assign(held, change);     // shows at once; the server's copy follows
    PalStage.SFX.play(pick("flip") ? "whoosh" : "pop");
    tap("style", Object.assign({piece: furnArmed.piece}, change)).then(out => { if (out && out.error && out.error.length > 8) tipFor(out.error); });
    buildRoomButtons();
    return;
  }
  if (pick("home")) { goHome(pick("home")); return; }
  if (pick("friend")) { PalStage.SFX.wake(); tap("go", {seat: +pick("friend")}).then(out => { if (out && out.error) tipFor(out.error); }); return; }
  if (pick("goroom")) { walkTo(+pick("goroom") * PalStage.W + PalStage.W / 2, .5); return; }
  if (pick("furn")) { furnArmed = furnArmed && !furnArmed.piece && furnArmed.key === pick("furn") ? null : {key: pick("furn")}; moving = false; buildRoomButtons(); return; }
  if (pick("moving")) { moving = !moving && !(furnArmed && furnArmed.piece); furnArmed = null; buildRoomButtons(); return; }
  if (pick("away")) { tap("unfurnish", {piece: +pick("away")}); furnArmed = null; buildRoomButtons(); return; }
  if (pick("look")) { PalStage.SFX.wake(); tap("look", {key: pick("look"), room: roomNow()}); return; }
  if (pick("prize")) {
    const item = S.hang.furniture[pick("prize")] || S.hang.walls[pick("prize")] || S.hang.floors[pick("prize")];
    tipFor(`Make your home a ${S.hang.levels[item.prize][0]} to win the ${item.name.toLowerCase()}!`, 5000);
    return;
  }
  if (pick("heart")) {
    tap("heart").then(out => {
      if (out && out.error) { tipFor(out.error); return; }
      PalStage.SFX.play("ding");
      tipFor(`❤️ You gave ${roomInfo.home.name}'s home a heart! That gives them coins and points.`, 5000);
    });
    return;
  }
  if (pick("code")) { openThing(pick("code")); return; }
  if (pick("pane")) {
    if (e.target.closest("[data-roomshop]")) shopTab = "room";
    roomPane = pick("pane"); artArmed = furnArmed = buyArmed = null; moving = false; buildRoomButtons();
    $("roomButtons").scrollTop = 0; return;
  }
  if (pick("drawthing")) { drawFurniture(); return; }
  if (e.target.closest("[data-hidename]")) { hideMyName(); return; }
  if (pick("sew")) { sewPick = pick("sew") === "start" ? "pick" : null; buildRoomButtons(); return; }
  if (pick("sewkey")) { sewPick = pick("sewkey"); buildRoomButtons(); return; }
  if (pick("sewslot")) { sew(pick("sewslot")); return; }
  if (pick("sewbin")) { sewBin = !sewBin; buildRoomButtons(); return; }
  if (pick("unsew")) { unsew(pick("unsew")); return; }
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
    const {wear: key, slot} = worn.dataset, wear = S.hang.wear, before = {...wear};
    if (wear[slot] === key) delete wear[slot]; else wear[slot] = key;
    PalStage.SFX.wake();
    buildRoomButtons();
    tap("wear", {slot, item: wear[slot] || null}).then(out => {
      if (out && out.ok) return;
      S.hang.wear = before;       // a game (or a moved-on screen) refused it: put it back
      tipFor((out && out.error && out.error.length > 3 && out.error !== "bad") ? out.error
             : "Couldn't change that right now. Try again.", 5000);
      if (roomPane === "me") buildRoomButtons();
    });
    return;
  }
  const b = e.target.closest("[data-tap]");
  if (!b) return;
  PalStage.SFX.wake();
  const {tap: what, name: word} = b.dataset;
  const request = what === "say" ? tap("say", {text: word}) : tap(what, {name: word});
  request.then(out => {
    if (!out || !out.error || out.error.length < 4) return;
    tipFor(out.error === "wait" ? "One moment! Let that finish." : out.error, 4500);
  });
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
$("roomButtons").addEventListener("click", e => { if (e.target.closest("[data-go-code]")) goCode(); if (e.target.closest("[data-go-chest]")) goToChest(); });     // the ⭐ job's way to the missions
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
  if (!atHome() && PalHang.muralAt(roomStage.state.places, x, y)) {     // click the wall itself to open the mural
    roomPane = "mural"; artArmed = furnArmed = buyArmed = null; moving = false; muralWhoMode = false;
    PalStage.SFX.wake();
    buildRoomButtons(); $("roomButtons").scrollTop = 0;
    tipFor("🖼️ The class mural! Pick a colour, then tap a square.", 5000);
    return;
  }
  const depth = Math.round(Math.max(0, Math.min(1, (y - PalStage.GROUND_TOP) / PalStage.GROUND_DEEP)) * 100) / 100;
  if (artArmed) {
    const key = artArmed;
    artArmed = null;
    buildRoomButtons();
    tap("place", {key, x: Math.round(Math.max(8, Math.min(worldEnd(), x))), y: depth}).then(out => { if (out && out.error && out.error.length > 8) tipFor(out.error); });
    return;
  }
  if (furnArmed && myHome()) {
    const {key, piece} = furnArmed;
    furnArmed = null;
    buildRoomButtons();
    furnish(Object.assign(piece ? {piece} : {key}, {x: Math.round(Math.max(16, Math.min(worldEnd() - 8, x))), y: depth}));
    return;
  }
  if (moving && myHome()) {     // ✋ picks a thing up, to put it down somewhere else
    const thing = PalHang.furnitureAt(roomInfo.home, x, y);
    if (thing) {
      furnArmed = {key: thing.key, piece: thing.id};
      PalStage.SFX.play("click");
      tipFor(`Got it: ${S.hang.furniture[thing.key].name}! Click the floor to put it down. For another room, press that room in 🚪 Your rooms first.`, 6000);
      buildRoomButtons();
      $("roomButtons").scrollTop = 0;     // 🎨 paint, size and flip are at the top
      return;
    }
  }
  if (atHome() && PalHang.doorAt(x, y)) { goHome("out"); return; }
  const chestHere = !atHome() && PalHang.chestAt(roomStage.state.places, x, depth, S.hang.chests);
  if (chestHere && chestHere.place === chestDismissed) chestDismissed = null;     // a click on the chest asks for it again
  const pier = !atHome() && PalHang.fishAt(roomStage.state.places, x, y);
  const front = pier && palAt(x, y);
  if (pier && (!front || front.me)) {
    fishing = {walk: pier};
    walkTo(pier.x, pier.y);
    tipFor("🎣 Walking to the pier...");
    return;
  }
  const hit = palAt(x, y);
  const thing = roomPane !== "art" && thingAt(x, y);
  // A friend under the click is a high-five, even if a coded drawing is under them.
  if (thing && !(hit && !hit.me)) { pokeThing(thing); return; }
  const snowy = !atHome() && PalHang.villageAt(roomStage.state.places, x, y);
  if (snowy && !hit) { clickVillage(snowy, mine); return; }
  if (roomPane === "art") {
    const own = roomStage.state.placed.find(p => p.mine && Math.abs(x - p.x) < 22 && y > PalStage.groundOf(p) - 44 && y < PalStage.groundOf(p) + 6);
    if (own) { tap("unplace", {piece: own.id}); return; }
  }
  const places = roomStage.state.places, seat = PalHang.seatAt(places, x, y);
  const piece = atHome() && PalHang.furnitureAt(roomInfo.home, x, y), pieceToy = piece && (S.hang.furniture[piece.key] || {}).toy;
  const toy = PalHang.toyAt(places, x, y) || (pieceToy ? {x: piece.x, y: piece.y, fx: pieceToy} : null);     // at home, the things are toys
  if (hit && hit.me && !seat && !toy && !chestHere) { tap("move", {name: "jump"}); return; }     // a chest under the click wins over your own pal
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

// ---- ❄️ The Snow Village: presents to find, a snowman to roll together, and the class tree --------------
let myOrnament = null, treeNear = false, snowWalk = false, villageHello = false;
const winterOn = () => !!(S.hang.winter && S.hang.winter.on);
function lookForWinter(mine) {
  if (!winterOn()) { roomStage.state.presents = null; return; }
  const st = roomStage.state, places = st.places || ["park"];
  st.presents = S.hang.winter.presents;
  const i = PalHang.presentAt(places, mine.x, mine.y, st.presents);
  if (i >= 0) {
    st.presents[i].found = true;
    tap("present", {i}).then(out => {
      if (!out || !out.ok || out.coins === undefined) return;      // found already
      S.hang.winter.count = out.count;
      PalStage.SFX.play("gift");
      banner(`🎁 You found a present!<small>${out.found} of ${out.of} today${out.coins ? ` · +${out.coins} 🪙` : ""}</small>`, 3500);
      if (S.hang.progress) S.hang.progress.presents = out.count;
    });
  }
  const v = places.indexOf("village"), near = v >= 0 && Math.abs(mine.x - v * PalStage.W - 92) < 30 && mine.y < .45;
  if (!near && treeNear && roomPane === "tree") {     // walking away puts the usual buttons back
    roomPane = "do"; artArmed = furnArmed = buyArmed = null;
    buildRoomButtons();
    tipFor("Walk back to the tree to hang a drawing.", 3500);
  }
  if (near && !treeNear) {
    roomPane = "tree"; artArmed = furnArmed = buyArmed = null;
    buildRoomButtons();
    PalStage.SFX.play("ding");
  }
  treeNear = near;
  if (snowWalk && v >= 0 && Math.abs(mine.x - v * PalStage.W - 238) < 40 && Math.abs(mine.x - mine.tx) < 3) { snowWalk = false; rollSnowball(); }
  if (!villageHello && v >= 0) {           // once a winter on each computer: where the Snow Village is
    villageHello = true;
    const key = "pixelVillageHello:" + me + ":" + new Date().getFullYear();
    try { if (!localStorage.getItem(key)) { localStorage.setItem(key, "1"); setTimeout(() => banner("❄️ The Snow Village is open!<small>Find it in 🏞️ Go to. Hang a drawing on the class tree!</small>", 6000, true), 8000); } } catch (_) {}
  }
}
function clickVillage(spot, mine) {
  if (spot.what === "tree") {
    walkTo(spot.x + (mine.x < spot.x ? -24 : 24), spot.y);
    roomPane = "tree"; buildRoomButtons();
    return;
  }
  if (Math.abs(mine.x - spot.x) < 40) { rollSnowball(); return; }
  snowWalk = true;
  walkTo(spot.x + (mine.x < spot.x ? -22 : 22), spot.y);
  tipFor("⛄ Walking to the snowman...");
}
async function rollSnowball() {
  PalStage.SFX.wake();
  const out = await tap("snowball");
  if (!out || out.error === "wait") return;
  if (out.error) { tipFor(out.error); return; }
  PalStage.SFX.play("pop");
  if (S.hang.progress) S.hang.progress.snowballs = out.snowballs;
  if (!out.done) tipFor("⛄ You rolled a snowball! Click the snowman again to roll another.");
}
// At the top of Games while the Snow Village is open: what there is to do in it today.
function winterCard() {
  if (!winterOn()) return "";
  const found = S.hang.winter.presents.filter(p => p.found).length, man = (roomStage && roomStage.state.snowman) || {balls: 0, need: 30};
  return `<div class="jobs winter"><h4>❄️ Snow Village <small>open until 31 December</small></h4>
    <p class="job${found === S.hang.winter.presents.length ? " done" : ""}"><span>🎁</span>Presents found today <b>${found}/${S.hang.winter.presents.length}</b></p>
    <p class="job"><span>⛄</span>Class snowman <b>${man.balls}/${man.need}</b></p>
    <p class="job"><span>🎄</span>Hang a drawing on the class tree${myOrnament ? " ✅" : ""}<button class="job-go" data-go-village="1">❄️ Take me</button></p></div>`;
}
function buildTreePane(box) {
  const pics = finishedDrawings(), tree = (roomStage && roomStage.state.tree) || [];
  box.classList.add("me-pane");
  if (!winterOn()) { box.innerHTML = `<p class="me-note">The Snow Village is closed until next winter.</p>`; return; }
  box.innerHTML = `<h4>🎄 The class tree <small>· ${tree.length} drawing${tree.length === 1 ? "" : "s"} on it</small></h4>
    <p class="me-note">${myOrnament ? "Your drawing is on the tree! Pick another to swap it." : "Hang one of your drawings on the tree, for everyone to see!"}${tree.length < 10 ? ` The star on top lights up at 10.` : " ⭐ The star is lit!"}</p>` +
    (pics.length ? pics.map(d => `<button data-ornament="${esc(d.key)}" aria-pressed="${myOrnament === d.key}"><canvas data-treepic="${esc(d.key)}"></canvas>${esc(d.title || "My drawing")}</button>`).join("")
      : `<p class="me-note">Draw something first in ✏️ Draw. Then come back!</p>`) +
    `<p class="me-note">⛄ Click the snowman to roll a snowball. Everyone rolls the same one!<br>🎁 Find today's presents: one in each place.</p>`;
  box.querySelectorAll("[data-treepic]").forEach(cv => drawingInto(cv, pics.find(p => p.key === cv.dataset.treepic)));
}
$("roomButtons").addEventListener("click", async e => {
  const b = e.target.closest("[data-ornament]");
  if (b) {
    PalStage.SFX.wake();
    const out = await tap("ornament", {key: b.dataset.ornament});
    if (!out || !out.ok) { tipFor("Couldn't hang it. Please try again."); return; }
    myOrnament = b.dataset.ornament;
    PalStage.SFX.play("gift");
    tipFor("🎄 Your drawing is on the class tree!", 4000);
    buildRoomButtons();
  } else if (e.target.closest("[data-go-village]")) {
    PalStage.SFX.wake();
    tap("go", {name: "village"}).then(out => { if (out && out.error) tipFor(out.error); });
  }
});
