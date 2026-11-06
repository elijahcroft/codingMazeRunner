// Pixel Pals: the class story. One book, with a page from each student. A page is
// a short show made with the usual code, plus one sentence for the book. Played
// in order they make a film, with everyone's pals taking a bow at the end.
"use strict";

let book = null, filmStage = null, playingBook = false;

const storyUi = {
  line(words, small) {
    $("storyWords").textContent = words;
    $("storySmall").textContent = small || "";
  },
  page(i) {
    const leaves = document.querySelectorAll("#bookPages .leaf");
    leaves.forEach((el, n) => el.classList.toggle("now", n === i));
    if (leaves[i]) leaves[i].scrollIntoView({block: "nearest"});
  },
};

function fitStoryScreen() {
  const host = $("storyHost"), wrap = host.parentElement;
  const width = Math.min(wrap.clientWidth - 8, (wrap.clientHeight - 8) * 16 / 9);
  host.style.width = Math.max(120, Math.floor(width)) + "px";
}

async function loadBook() {
  const data = await get("/pixel/story?id=" + encodeURIComponent(me)).catch(() => null);
  if (data) book = data;
  return book;
}
let storyPane = "live", bookTimer = 0;
function showPane(pane) {
  storyPane = pane;
  $("liveView").hidden = pane !== "live";
  $("bookView").hidden = pane !== "book";
  $("segLive").setAttribute("aria-pressed", pane === "live");
  $("segBook").setAttribute("aria-pressed", pane === "book");
  if (pane === "book") { fitStoryScreen(); if (book) paintBook(); } else { stopBook(); fitRoomScreen(); }
}
async function openStory() {
  if (!filmStage) filmStage = PalStage.create($("storyCanvas"), $("storyHost"));
  filmStage.setPal(currentPal());
  filmStage.fresh();
  filmStage.state.scene = "wedding";
  openRoom();
  showPane(storyPane);
  await loadBook();
  if (book) paintBook();
  clearInterval(bookTimer);
  bookTimer = setInterval(watchBook, 2500);        // pages turn up as they're added
}
// The book updates itself, so everyone sees a new page as soon as it's in.
async function watchBook() {
  if (playingBook || $("storyView").hidden) return;
  const had = book ? book.pages.length : 0, wait = book && book.waiting ? book.waiting.id : 0;
  await loadBook();
  if (!book || playingBook) return;
  const fresh = book.pages.length > had ? book.pages[book.pages.length - 1] : null;
  if (fresh || wait !== (book.waiting ? book.waiting.id : 0)) paintBook();
  if (fresh && had) showRewards({badges: [{icon: "📖", name: `${fresh.by} added a page!`}]});
}
function stopBook() {
  if (!playingBook) return;
  playingBook = false;
  filmStage.stop();
  $("playStory").textContent = "▶ Play our story";
}
function closeStory() {
  clearInterval(bookTimer);
  stopBook();
  closeRoom();
}

function paintBook() {
  $("bookTitle").textContent = book.title;
  $("bookStart").textContent = book.start;
  const leaf = (page, i) => `<button class="leaf" data-leaf="${i + 1}"><canvas></canvas><span>${esc(page.line)}<small>Page ${i + 1} by ${esc(page.by)}</small></span></button>`;
  const mine = book.waiting ? `<div class="leaf waits"><canvas></canvas><span>${esc(book.waiting.line)}<small>Waiting for your teacher. <button class="btn" style="padding:0 6px;font-size:13px;box-shadow:none" data-take-leaf="${book.waiting.id}">Take it back</button></small></span></div>` : "";
  $("bookPages").innerHTML = book.pages.map(leaf).join("") + mine
    || `<div class="leaf-empty">No pages yet.<br>You could write page 1!</div>`;
  const pics = [...book.pages, ...(book.waiting ? [book.waiting] : [])];
  $("bookPages").querySelectorAll("canvas").forEach((cv, i) => {
    const pal = pics[i].pal;
    thumbInto(cv, A.decode(pal.frames[0]), pal.size, pal.palette);
  });
  storyUi.line(book.pages.length ? "Press ▶ to watch it, or click a page." : book.start, book.pages.length ? `${book.pages.length} page${book.pages.length === 1 ? "" : "s"} so far` : book.title);
  $("playStory").disabled = !book.pages.length;
  $("addPage").textContent = book.waiting ? "✏️ Change my page" : "✏️ Add a page";
  const joined = book.joined;
  $("joinCast").disabled = !!joined;
  $("joinCast").textContent = joined === "waiting" ? "💌 Waiting for your teacher" : joined ? "🌟 Your pal is in the story" : "🙋 Put my pal in the story";
  $("storyCast").textContent = book.cast.length ? `In the story: ${book.cast.join(", ")}. Use  friend("name")  to bring them on.` : "";
}

async function playBook(from) {
  if (playingBook) { stopBook(); return; }
  const film = await get("/pixel/film").catch(() => null);
  if (!film || !film.pages.length) return;
  playingBook = true;
  $("playStory").textContent = "■ Stop";
  PalStage.SFX.wake();
  const start = from ? from - 1 : 0;
  await PalStage.playFilm(filmStage, film, storyUi, start);
  document.querySelectorAll("#bookPages .leaf").forEach(el => el.classList.remove("now"));
  if (playingBook) {
    playingBook = false;
    $("playStory").textContent = "▶ Play our story";
  }
}

async function startPage() {
  await showView("stage");
  saveCode();
  dropRun();
  await loadBook();
  ideaAt = 0;
  openFree(book);
}
// Classmates' pals sit by the editor, so they're one click away.
function castChips() {
  if (!book) return;
  $("chips").insertAdjacentHTML("afterbegin", book.cast.filter(who => who.toLowerCase() !== name.toLowerCase()).slice(0, 5).map(pal =>
    `<button class="chip py" data-chip='friend("${esc(pal)}")' title="Bring ${esc(pal)}'s pal on stage">friend("${esc(pal)}")</button>`).join(""));
}
let addingFilm = false;
function openPageSheet(film = false) {
  addingFilm = film;
  $("pageTitle").textContent = film ? "Add your film to the book" : "Add your page to the story";
  $("pageNote").textContent = "";
  $("pageWords").value = !film && book && book.waiting ? book.waiting.line : "";
  $("pageSheet").hidden = false;
  $("pageWords").focus();
}
async function addMyPage() {
  saveCode();
  const out = await post(addingFilm ? "/pixel/story/live" : "/pixel/story/add",
                         {id: me, code: $("code").value, line: $("pageWords").value}).catch(() => null);
  if (!out) { $("pageNote").textContent = "The computer didn't answer. Try again."; return; }
  if (out.error) { $("pageNote").textContent = out.error; return; }
  book = out.story;
  $("pageSheet").hidden = true;
  showRewards({badges: [...out.badges, out.waiting ? {icon: "💌", name: "Sent to your teacher!"} : {icon: "📖", name: "It's in the book!"}]});
  if (addingFilm) return;
  store(codeKey("story"), "");
  storyPane = "book";
  await showView("story");
}
async function takeLeaf(id) {
  await post("/pixel/story/take", {id: me, page: id}).catch(() => {});
  await loadBook();
  paintBook();
}
async function joinTheCast() {
  const out = await post("/pixel/story/cast", {id: me}).catch(() => null);
  if (out && out.error) { storyUi.line(out.error); return; }
  await loadBook();
  paintBook();
}

new ResizeObserver(fitStoryScreen).observe($("storyHost").parentElement);
$("playStory").addEventListener("click", () => playBook(0));
$("addPage").addEventListener("click", startPage);
$("segLive").addEventListener("click", () => showPane("live"));
$("segBook").addEventListener("click", () => showPane("book"));
$("joinCast").addEventListener("click", joinTheCast);
$("pageGo").addEventListener("click", addMyPage);
$("pageNo").addEventListener("click", () => { $("pageSheet").hidden = true; });
$("pageWords").addEventListener("keydown", e => { if (e.key === "Enter") addMyPage(); });
