// A local story adventure. Coordinates are world tiles; the camera follows the pal.
"use strict";
const PixelIsland = (() => {
  const places = [
    {name: "Town square", x: 12, y: 12, color: "#edb755", roof: "#db655f", activity: "Meet the island guide"},
    {name: "Cocoa café", x: 5, y: 7, color: "#f5c28c", roof: "#c16f91", activity: "Serve a café order"},
    {name: "Crystal pond", x: 21, y: 6, color: "#a5d9ed", roof: "#397ea4", activity: "Go fishing"},
    {name: "Music club", x: 23, y: 19, color: "#c6b6ed", roof: "#7960bb", activity: "Play the dance pattern"},
    {name: "Sunny garden", x: 8, y: 24, color: "#f4d998", roof: "#5f9e69", activity: "Grow a flower"},
    {name: "Lookout lodge", x: 28, y: 29, color: "#d2c5ae", roof: "#628aaa", activity: "Find the lost stars"},
  ];
  const stars = [{x: 3, y: 18}, {x: 18, y: 28}, {x: 29, y: 10}];
  let cv, g, pup, active = false, frame = 0, last = 0, player = {x: 12, y: 15}, target = {...player};
  let save, key, nearby = -1, camera = {x: 0, y: 0}, game = null, note = "";
  const clamp = n => Math.max(1, Math.min(31, n));
  const project = (x, y) => ({x: (x - y) * 43, y: (x + y) * 23});
  function persist() {
    try { localStorage.setItem(key, JSON.stringify(save)); }
    catch (_) { note = "Storage is unavailable; progress lasts for this visit."; }
    status();
  }
  function status() {
    $("islandProgress").textContent = `${save.coins} coins · ${save.stamps.length}/6 stamps · ${save.stars.length}/3 stars`;
    $("islandJournal").textContent = note || "Help the island get ready for its story festival. Try every activity to fill your passport!";
    document.querySelectorAll("[data-island-place]").forEach((b, i) => { b.textContent = `${save.stamps.includes(i) ? "✓ " : ""}${places[i].name}`; });
  }
  function reward(i, words) {
    save.coins += 5;
    if (!save.stamps.includes(i)) save.stamps.push(i);
    note = words + " +5 coins!";
    if (save.stamps.length === 6) note += " Festival passport complete! You are an Island Storykeeper.";
    persist();
  }
  function panel(title, text, choices) {
    $("islandActivity").hidden = false;
    $("islandActivityTitle").textContent = title;
    $("islandActivityText").textContent = text;
    const box = $("islandChoices"); box.replaceChildren();
    for (const [label, fn] of choices) {
      const b = document.createElement("button"); b.className = "btn"; b.textContent = label;
      b.onclick = fn; box.append(b);
    }
  }
  function done(i, words) { game = null; reward(i, words); panel(places[i].name, note, [["Keep exploring", dismiss]]); }
  function dismiss() { game = null; $("islandActivity").hidden = true; cv.focus(); }
  function interact() {
    if (nearby < 0) return;
    const i = nearby;
    if (i === 0) {
      panel("Welcome to the story festival", "I'm Pip, your island guide! Visit the café, pond, club, garden and lodge. Each activity earns a passport stamp. Your first job: choose our festival greeting.",
        ["Hello, explorers!", "Let’s make a story!", "Welcome, pals!"].map(s => [s, () => done(0, `Pip hangs up your greeting: “${s}”`)]));
    } else if (i === 1) {
      const orders = [["cocoa", "marshmallows"], ["tea", "honey"], ["milk", "cinnamon"]];
      const order = orders[Math.floor(Math.random() * orders.length)];
      panel("Café • take an order", `A visitor asks for ${order[0]} with ${order[1]}. Pick the drink first.`,
        orders.map(([drink]) => [drink, () => {
          if (drink !== order[0]) { $("islandActivityText").textContent = `Try again: the visitor asked for ${order[0]} with ${order[1]}.`; return; }
          panel("Café • finishing touch", `Add the topping for ${order[0]} with ${order[1]}.`, orders.map(([, topping]) => [topping, () => {
            if (topping === order[1]) done(1, "A perfect order! The visitor is ready for the festival.");
            else $("islandActivityText").textContent = `Almost! Add ${order[1]}.`;
          }]));
        }]));
    } else if (i === 2) {
      game = {kind: "fish", cast: performance.now(), delay: 1800 + Math.random() * 1800};
      panel("Crystal pond • fishing", "Your float is drifting. Wait for ‘Bite!’ then reel it in.", [["Reel in", () => {
        if (!game || game.kind !== "fish") return;
        const elapsed = performance.now() - game.cast;
        if (elapsed < game.delay) { $("islandActivityText").textContent = "Too early! Leave the float a little longer…"; return; }
        done(2, "You caught a sparkling storyfish and released it back into the pond.");
      }]]);
    } else if (i === 3) {
      const names = ["Clap", "Step", "Spin"], pattern = Array.from({length: 4}, () => names[Math.floor(Math.random() * 3)]);
      game = {kind: "dance", pattern, at: 0};
      panel("Music club • follow the beat", `Play this pattern: ${pattern.join(" → ")}`, names.map(n => [n, () => {
        if (!game || game.kind !== "dance") return;
        if (n !== pattern[game.at]) { game.at = 0; $("islandActivityText").textContent = `Try from the start: ${pattern.join(" → ")}`; return; }
        game.at++;
        if (game.at === pattern.length) done(3, "The whole club joins your festival dance!");
        else $("islandActivityText").textContent = `${game.at}/4 moves! Next: ${pattern.slice(game.at).join(" → ")}`;
      }]));
    } else if (i === 4) {
      panel("Sunny garden • plant a seed", "Pick a flower to grow for the festival.", ["Sunflower", "Bluebell", "Poppy"].map(flower => [flower, () => {
        panel("Sunny garden • care for it", `Your ${flower.toLowerCase()} needs a drink.`, [["Water the seed", () => {
          panel("Sunny garden • almost there", "A tiny green shoot appears. Give it some sunshine!", [["Move it into the sun", () => {
            save.flower = flower; done(4, `Your ${flower.toLowerCase()} blooms beside the garden!`);
          }]]);
        }]]);
      }]));
    } else if (save.stars.length === 3) done(5, "You returned all three lost stars. The lookout beacon shines again!");
    else panel("Lookout lodge • star search", `Find three gold stars around the island (${save.stars.length}/3 found). Walk close to collect them. Hints: west woodland, south meadow, east shore. Then return here.`, [["Start searching", dismiss]]);
  }
  function poly(points, fill) { g.fillStyle = fill; g.beginPath(); points.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fill(); }
  function ground(x, y, color) { const p = project(x, y); poly([[p.x, p.y-23], [p.x+43,p.y], [p.x,p.y+23], [p.x-43,p.y]], color); }
  function building(p) {
    const a = project(p.x, p.y); g.fillStyle = "#244b4933"; g.beginPath(); g.ellipse(a.x+15,a.y+12,85,24,0,0,Math.PI*2); g.fill();
    poly([[a.x-57,a.y-80],[a.x,a.y-53],[a.x,a.y+6],[a.x-57,a.y-23]],p.color);
    poly([[a.x,a.y-53],[a.x+57,a.y-80],[a.x+57,a.y-23],[a.x,a.y+6]],"#917d83");
    poly([[a.x-67,a.y-82],[a.x,a.y-120],[a.x+67,a.y-82],[a.x,a.y-45]],p.roof);
    g.fillStyle = "#ffefb5"; g.fillRect(a.x-42,a.y-62,18,20); g.fillStyle = "#473f59"; g.fillRect(a.x+12,a.y-36,19,31);
    label(p.name, a.x, a.y-135);
  }
  function label(text, x, y) {
    g.font = "bold 14px sans-serif"; const w = g.measureText(text).width + 18;
    g.fillStyle = "#fff9e9"; g.fillRect(x-w/2,y-15,w,23); g.fillStyle = "#273950"; g.textAlign = "center"; g.fillText(text,x,y+1);
  }
  function draw(now) {
    if (!active) return;
    const dt = Math.min((now-last)/1000 || 0, .05); last = now;
    if (!game && $("islandActivity").hidden) {
      const dx = target.x-player.x, dy = target.y-player.y, dist = Math.hypot(dx,dy), step = Math.min(dist,dt*5);
      if (dist > .01) { player.x += dx/dist*step; player.y += dy/dist*step; }
    }
    const pos = project(player.x,player.y); camera = {x: cv.width/2-pos.x, y: cv.height/2-pos.y+45};
    g.clearRect(0,0,cv.width,cv.height); g.fillStyle = "#80c7db"; g.fillRect(0,0,cv.width,cv.height);
    g.save(); g.translate(camera.x,camera.y);
    for (let x=0;x<33;x++) for (let y=0;y<33;y++) {
      const pond = x>17 && x<25 && y>2 && y<9;
      ground(x,y,pond ? ((x+y)%2 ? "#54afc9" : "#62bad1") : x===12 || y===15 || x===23 || y===24 ? "#e6d6ad" : (x+y)%2 ? "#8cbe83" : "#95c68c");
    }
    const objects = places.map(p => ({depth:p.x+p.y, draw:() => building(p)}));
    for (let n=0;n<40;n++) {
      const x=(n*7+2)%32, y=(n*11+3)%32;
      if (x===12 || x===23 || y===15 || y===24 || places.some(p=>Math.hypot(x-p.x,y-p.y)<3) || (x>17&&x<25&&y<9)) continue;
      objects.push({depth:x+y,draw:()=>{const p=project(x,y);g.fillStyle="#71594c";g.fillRect(p.x-5,p.y-32,10,34);poly([[p.x-25,p.y-22],[p.x,p.y-80],[p.x+25,p.y-22]],"#397964");poly([[p.x-20,p.y-43],[p.x,p.y-92],[p.x+20,p.y-43]],"#4c9774");}});
    }
    stars.forEach((s,i)=> {
      if (save.stars.includes(i)) return;
      const p=project(s.x,s.y); label("★",p.x,p.y-8);
      if (Math.hypot(player.x-s.x,player.y-s.y)<1.2) { save.stars.push(i); note=`Found a lost star! ${save.stars.length}/3 — return to Lookout lodge when you have them all.`; persist(); }
    });
    if (save.flower) { const p=project(9,25); label(save.flower+" garden",p.x,p.y-15); }
    objects.push({depth:player.x+player.y,draw:()=>{
      g.fillStyle="#244b4955";g.beginPath();g.ellipse(pos.x,pos.y,20,8,0,0,Math.PI*2);g.fill();
      pup.draw(g,0,{},pos.x,pos.y,{flip:target.x<player.x}); label("You",pos.x,pos.y-66);
    }});
    objects.sort((a,b)=>a.depth-b.depth).forEach(o=>o.draw()); g.restore();
    const next = places.findIndex(p=>Math.hypot(player.x-p.x,player.y-p.y)<3.5);
    if (next!==nearby) { nearby=next; $("islandInteract").disabled=next<0; $("islandInteract").textContent=next<0?"Walk to a destination":places[next].activity+" (E)"; $("islandLocation").textContent=next<0?"Island trails":places[next].name; }
    // Compact overview with a live location marker.
    g.fillStyle="#fff9e9ed";g.fillRect(12,12,120,120);g.fillStyle="#85b985";g.fillRect(20,20,104,104);
    places.forEach(p=>{g.fillStyle=p.roof;g.fillRect(20+p.x*3,20+p.y*3,6,6);});
    g.fillStyle="#213755";g.beginPath();g.arc(23+player.x*3,23+player.y*3,4,0,Math.PI*2);g.fill();
    if(game && game.kind==="fish" && now-game.cast>=game.delay) $("islandActivityText").textContent="Bite! Your float dips under — reel in your fish!";
    frame=requestAnimationFrame(draw);
  }
  function open() {
    if (active) return;
    cv=$("islandCanvas");g=cv.getContext("2d");cv.width=960;cv.height=600;
    key="pixel-island-v1:"+me;
    let raw;try {raw=JSON.parse(localStorage.getItem(key));}catch(_){}
    save={coins:0,stamps:[],stars:[],flower:null};
    if(raw && typeof raw==="object") {
      save.coins=Number.isFinite(raw.coins)?Math.max(0,raw.coins):0;
      for(const k of ["stamps","stars"]) save[k]=Array.isArray(raw[k])?[...new Set(raw[k].filter(n=>Number.isInteger(n)&&n>=0&&n<(k==="stars"?3:6)))]:[];
      save.flower=["Sunflower","Bluebell","Poppy"].includes(raw.flower)?raw.flower:null;
    }
    pup=PalStage.puppet(currentPal(),2);nearby=-2;status();active=true;last=0;frame=requestAnimationFrame(draw);
  }
  function close() { active=false;cancelAnimationFrame(frame);game=null;$("islandActivity").hidden=true; }
  function setup() {
    $("islandDestinations").innerHTML=places.map((p,i)=>`<button class="btn" data-island-place="${i}">${p.name}</button>`).join("");
    $("islandDestinations").onclick=e=>{const b=e.target.closest("[data-island-place]");if(!b)return;const p=places[Number(b.dataset.islandPlace)];dismiss();target={x:p.x,y:p.y+2};};
    $("islandInteract").onclick=interact;$("islandDismiss").onclick=dismiss;
    $("islandCanvas").onclick=e=>{if(!active)return;const r=cv.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*cv.width-camera.x,y=(e.clientY-r.top)/r.height*cv.height-camera.y;target={x:clamp((y/23+x/43)/2),y:clamp((y/23-x/43)/2)};cv.focus();};
    $("islandCanvas").onkeydown=e=>{
      if(!active)return;
      if(e.key.toLowerCase()==="e"){e.preventDefault();interact();return;}
      const d={ArrowUp:[-1,-1],ArrowDown:[1,1],ArrowLeft:[-1,1],ArrowRight:[1,-1],w:[-1,-1],s:[1,1],a:[-1,1],d:[1,-1]}[e.key];
      if(d){e.preventDefault();target={x:clamp(player.x+d[0]*1.5),y:clamp(player.y+d[1]*1.5)};}
    };
  }
  setup(); return {open,close};
})();
