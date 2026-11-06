// Pixel Pals: playing together. Everyone's pal is on one stage at the same moment,
// and what one child taps, everyone sees. Words are tapped from a list unless the
// teacher turns typing on, and the 🔴 button turns a scene into a page of the book.
"use strict";

let roomStage = null, stopRoom = null, roomInfo = null, roomJoining = false, roomPane = "do";

const ROOM_PANES = {
  do: [["👋", "Wave", "move", "wave"], ["💃", "Dance", "move", "dance"], ["🦘", "Jump", "move", "jump"], ["🎉", "Cheer", "move", "cheer"],
       ["🌀", "Spin", "move", "spin"], ["😴", "Nap", "move", "nap"], ["😊", "Happy", "feel", "happy"], ["😢", "Sad", "feel", "sad"],
       ["😮", "Wow", "feel", "surprised"], ["😠", "Cross", "feel", "angry"], ["🤪", "Silly", "feel", "silly"], ["😎", "Cool", "feel", "cool"]],
  party: [["💕", "Hearts", "fx", "hearts"], ["🌸", "Petals", "fx", "petals"], ["🎊", "Confetti", "fx", "confetti"], ["⭐", "Stars", "fx", "stars"],
          ["💐", "Flowers", "fx", "bouquet"], ["🔔", "Bells", "fx", "bells"], ["🎵", "Wedding music", "fx", "march"], ["🎂", "Cake", "fx", "cake"]],
};
const PLACE_ICONS = {wedding: "💒", stage: "🎭", park: "🌳", beach: "🏖️", night: "🌙", snowy: "⛄", candy: "🍭", space: "🚀", castle: "🏰"};

function fitRoomScreen() {
  const host = $("roomHost"), wrap = host.parentElement;
  const width = Math.min(wrap.clientWidth - 8, (wrap.clientHeight - 8) * 16 / 9);
  host.style.width = Math.max(120, Math.floor(width)) + "px";
}

function tap(what, more = {}) {
  return post("/pixel/room/do", Object.assign({id: me, what}, more)).catch(() => null);
}

function buildRoomButtons() {
  document.querySelectorAll("[data-pane]").forEach(b => b.setAttribute("aria-pressed", b.dataset.pane === roomPane));
  const box = $("roomButtons");
  box.classList.toggle("words", roomPane === "say");
  const big = ([icon, word, what, name]) => `<button data-tap="${what}" data-name="${name}"><span>${icon}</span>${esc(word)}</button>`;
  if (roomPane === "say") {
    box.innerHTML = Object.entries(S.room_words).map(([group, words]) =>
      `<h4>${esc(group)}</h4>` + words.map(w => `<button data-tap="say" data-name="${esc(w)}">${esc(w)}</button>`).join("")).join("");
  } else if (roomPane === "place") {
    box.innerHTML = S.kit.scenes.map(n => big([PLACE_ICONS[n] || "🏞️", n[0].toUpperCase() + n.slice(1), "scene", n])).join("");
  } else box.innerHTML = ROOM_PANES[roomPane].map(big).join("");
}

function roomState(data) {
  roomInfo = data;
  const open = data.open;
  $("roomClosed").hidden = open;
  $("roomButtons").style.visibility = open ? "" : "hidden";
  $("filmGo").hidden = !open;
  $("roomType").hidden = !open || !data.words;
  if (open && !data.you && !roomJoining) {
    roomJoining = true;
    tap("join").finally(() => { roomJoining = false; });
  }
  const film = data.film, mine = film && film.seat === data.you;
  $("filmGo").textContent = mine ? "⏹ Stop filming" : film ? `🔴 ${film.by} is filming` : "🔴 Film it for the book";
  $("filmGo").disabled = !!film && !mine;
  $("filmGo").classList.toggle("on", !!mine);
  $("roomNews").classList.toggle("rec", !!film);
  $("roomNews").textContent = film ? "🔴 Filming!" : "";
  for (const e of data.events) {
    if (e.kind === "scene" && e.seat !== data.you) tipFor(`${e.by} took everyone somewhere new!`);
    if (e.kind === "film_stop" && e.seat === data.you && e.kept) openPageSheet(true);
  }
}
let tipTimer = 0;
const ROOM_TIP = "Click anywhere and your pal walks there. Click your pal to jump!";
function tipFor(text) {
  $("roomTip").textContent = text;
  clearTimeout(tipTimer);
  tipTimer = setTimeout(() => { $("roomTip").textContent = ROOM_TIP; }, 3500);
}

function openRoom() {
  if (!roomStage) roomStage = PalStage.create($("roomCanvas"), $("roomHost"));
  if (stopRoom) return;
  roomStage.setPal(S.pip);
  roomStage.fresh();
  roomStage.state.visible = false;
  roomStage.state.scene = "wedding";
  buildRoomButtons();
  fitRoomScreen();
  stopRoom = PalStage.follow(roomStage, {id: me, onState: roomState});
}
function closeRoom() {
  if (!stopRoom) return;
  stopRoom();
  stopRoom = null;
  tap("leave");
  roomStage.roomStop();
}

function myMember() {
  const st = roomStage && roomStage.state;
  return st && st.room && st.room.find(m => m.seat === st.you);
}
function walkTo(x, y) {
  const mine = myMember();
  if (!mine) return;
  roomStage.roomApply({kind: "walk", seat: mine.seat, x, y});     // at once, without waiting for the server
  tap("walk", {x: Math.round(x), y: Math.round(y * 100) / 100});
}

new ResizeObserver(fitRoomScreen).observe($("roomHost").parentElement);
$("roomTabs").addEventListener("click", e => {
  const b = e.target.closest("[data-pane]");
  if (b) { roomPane = b.dataset.pane; buildRoomButtons(); }
});
$("roomButtons").addEventListener("click", e => {
  const b = e.target.closest("[data-tap]");
  if (!b) return;
  PalStage.SFX.wake();
  const {tap: what, name: word} = b.dataset;
  if (what === "say") tap("say", {text: word}); else tap(what, {name: word});
});
$("roomCanvas").addEventListener("click", e => {
  const r = $("roomCanvas").getBoundingClientRect(), mine = myMember();
  const x = (e.clientX - r.left) / r.width * PalStage.W, y = (e.clientY - r.top) / r.height * PalStage.H;
  if (!mine) return;
  PalStage.SFX.wake();
  if (Math.abs(x - mine.x) < 26 && y > 90 && y < 172) { tap("move", {name: "jump"}); return; }
  walkTo(Math.max(8, Math.min(312, x)), y < 140 ? mine.ty : Math.max(0, Math.min(1, (y - 140) / 30)));
});
addEventListener("keydown", e => {
  if ($("liveView").hidden || $("storyView").hidden || e.target.matches("input, textarea") || !["ArrowLeft", "ArrowRight"].includes(e.key)) return;
  const mine = myMember();
  if (!mine) return;
  e.preventDefault();
  walkTo(Math.max(8, Math.min(312, mine.tx + (e.key === "ArrowLeft" ? -26 : 26))), mine.ty);
});
$("roomType").addEventListener("submit", e => {
  e.preventDefault();
  const text = $("roomWords").value.trim();
  if (!text) return;
  $("roomWords").value = "";
  tap("say", {text});
});
$("filmGo").addEventListener("click", () => {
  const film = roomInfo && roomInfo.film;
  tap(film ? "film_stop" : "film_start");
});
addEventListener("pagehide", () => {
  if (stopRoom) navigator.sendBeacon("/pixel/room/do", new Blob([JSON.stringify({id: me, what: "leave"})], {type: "application/json"}));
});
