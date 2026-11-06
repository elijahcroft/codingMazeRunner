// 🔮 Predict it on a student's page: a question from the teacher, four answers,
// and the result after the reveal. Needs the page's $, post, me, SFX and toast.
// The rules are in planet_predict.py, and the class screen is planet_predict.html.

const PREDICT_POLL_MS = 2000;     // while the question is up, a quicker look for the reveal
const predict = {n: null, closed: null, choice: null, timer: 0, revealed: false};

function predictPaint(q) {
  const mine = predict.choice, box = $("predictOptions");
  box.replaceChildren(...q.options.map(n => {
    const b = document.createElement("button");
    b.textContent = n; b.disabled = q.revealed;
    b.classList.toggle("mine", n === mine);
    b.classList.toggle("right", q.revealed && n === q.answer);
    b.addEventListener("click", () => predictVote(q, n));
    return b;
  }));
  $("predictSay").textContent = q.revealed
    ? mine === q.answer ? `It was ${q.answer}. You got it! 🎉`
      : mine == null ? `It was ${q.answer}. Watch the rover on the class screen.`
      : `It was ${q.answer}, and you said ${mine}. Watch the rover on the class screen to see why.`
    : mine == null ? "" : `You said ${mine}. You can change your mind until your teacher presses Reveal.`;
}
async function predictVote(q, choice) {
  SFX.wake();
  const out = await post("/planet/predict", {id: me, choice}).catch(() => null);
  if (!out) { $("predictSay").textContent = "Your answer didn't get through. Press it again."; return; }
  predict.choice = out.voted;
  predictPaint(q);
}
// What the page heard from the server: a question, or nothing.
function predictHear(q) {
  clearTimeout(predict.timer);
  if (!q) {
    $("predict").hidden = true;
    predict.n = null;
    return;
  }
  if (q.n !== predict.n) Object.assign(predict, {n: q.n, closed: null, choice: null, revealed: false});
  if (q.n === predict.closed) return;
  if ($("predict").hidden) {
    $("predictCode").textContent = q.code;
    $("predict").hidden = false;
  }
  if (q.revealed && !predict.revealed) SFX.play(predict.choice === q.answer ? "badge" : "beep");
  predict.revealed = q.revealed;
  predictPaint(q);
  if (!q.revealed) predict.timer = setTimeout(predictLook, PREDICT_POLL_MS);
}
async function predictLook() {
  const out = await fetch("/planet/predict/view").then(r => r.json()).catch(() => null);
  if (out) predictHear(out.student); else predict.timer = setTimeout(predictLook, PREDICT_POLL_MS);
}
function predictClose() {
  clearTimeout(predict.timer);
  predict.closed = predict.n;
  $("predict").hidden = true;
}
function predictEscape() {
  if ($("predict").hidden) return false;
  predictClose();
  return true;
}
function predictWire() {
  $("predictClose").addEventListener("click", predictClose);
}
