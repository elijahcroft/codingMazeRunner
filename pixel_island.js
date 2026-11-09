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
    document.querySelectorAll("[data-island-place]").forEach((b, i) => { b.querySelector(".destination-name").textContent = places[i].name; b.classList.toggle("collected",save.stamps.includes(i)); b.setAttribute("aria-label",places[i].name+(save.stamps.includes(i)?", stamp collected":"")); b.querySelector(".destination-mark").textContent=save.stamps.includes(i)?"✓":"›"; });
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
    box.querySelector("button")?.focus();
  }
  function done(i, words) { game = null; reward(i, words); panel(places[i].name, note, [["Keep exploring", dismiss]]); }
  function dismiss() { game = null; $("islandActivity").hidden = true; cv.focus(); }
  function interact() {
    if(PixelInteriors.active){PixelInteriors.interact();return;}
    if(nearby<0)return;
    target={...player};
    PixelInteriors.enter(nearby,{save,persist,reward,panel,dismiss,onExit:()=>{nearby=-2;target={...player};}});
  }
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const routes = [[12,15,5,9],[12,15,21,8],[12,15,23,21],[12,15,8,26],[23,21,28,31]];
  const travelNotes = ["Meet Pip & say hello", "Warm drinks & little treats", "Cast a line by the water", "Find your festival rhythm", "Plant something lovely", "A little adventure awaits"];
  const symbols = ["☀", "☕", "≈", "♫", "✿", "★"];
  let terrain = null, scenery = [], faceLeft = false;
  function poly(points, fill, outline) {
    g.beginPath(); points.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath();
    g.fillStyle = fill; g.fill(); if (outline) { g.strokeStyle=outline;g.lineWidth=2;g.stroke(); }
  }
  function oval(x,y,rx,ry,color) {g.fillStyle=color;g.beginPath();g.ellipse(x,y,rx,ry,0,0,Math.PI*2);g.fill();}
  function round(x,y,w,h,r,color) {g.fillStyle=color;g.beginPath();g.roundRect(x,y,w,h,r);g.fill();}
  function line(points,color,width=2) {g.strokeStyle=color;g.lineWidth=width;g.lineCap="round";g.beginPath();points.forEach((p,i)=>i?g.lineTo(...p):g.moveTo(...p));g.stroke();}
  function text(words,x,y,size,color="#284e52") {g.font=`800 ${size}px ui-rounded, 'Trebuchet MS', sans-serif`;g.textAlign="center";g.fillStyle=color;g.fillText(words,x,y);}
  function label(words,x,y) {
    g.font="800 13px ui-rounded, sans-serif";const w=g.measureText(words).width+26;
    round(x-w/2,y-18,w,28,14,"#244d5660");round(x-w/2,y-21,w,28,14,"#fffdf0");text(words,x,y-2,13);
  }
  function flower(x,y,color) {line([[x,y],[x,y-10]],"#418257",2);for(let a=0;a<5;a++)oval(x+Math.cos(a*1.26)*4,y-11+Math.sin(a*1.26)*4,3,3,color);oval(x,y-11,2,2,"#ffe5a1");}
  function tree(x,y,seed) {
    const p=project(x,y), h=60+seed%30;
    oval(p.x+15,p.y+6,35,12,"#376f6030");line([[p.x,p.y],[p.x-2,p.y-h]],"#886848",11);
    line([[p.x,p.y-25],[p.x+18,p.y-49]],"#886848",5);
    oval(p.x,p.y-h,32,33,"#3b8363");oval(p.x-16,p.y-h-5,23,25,"#56a473");oval(p.x+12,p.y-h-20,26,22,"#78b77a");oval(p.x-12,p.y-h-25,16,12,"#91c983");
    if(seed%3===0) {oval(p.x-18,p.y-h,4,4,"#ffc286");oval(p.x+13,p.y-h-20,4,4,"#ffc286");}
  }
  function lamp(x,y) {const p=project(x,y);oval(p.x+8,p.y+2,13,5,"#376f6030");line([[p.x,p.y],[p.x,p.y-58]],"#395c60",5);round(p.x-8,p.y-75,16,20,4,"#fff1b4");poly([[p.x-13,p.y-75],[p.x,p.y-86],[p.x+13,p.y-75]],"#395c60");}
  function bench(x,y) {const p=project(x,y);for(const dx of [-23,23])line([[p.x+dx,p.y],[p.x+dx,p.y-23]],"#365f59",4);round(p.x-32,p.y-38,64,15,4,"#c48b58");round(p.x-34,p.y-17,68,10,4,"#edb879");}
  function fountain(x,y,t) {
    const p=project(x,y);oval(p.x+8,p.y+6,66,29,"#325b4930");oval(p.x,p.y-4,62,30,"#9aaea6");oval(p.x,p.y-12,62,30,"#f4ead3");oval(p.x,p.y-14,51,23,"#60c6ce");
    oval(p.x,p.y-17,40,16,"#91e2dc");round(p.x-8,p.y-55,16,38,6,"#d9dcca");oval(p.x,p.y-54,29,13,"#f6eedc");oval(p.x,p.y-57,23,8,"#66c7d1");
    for(let n=0;n<5;n++){const a=n*1.26;line([[p.x,p.y-83],[p.x+Math.cos(a)*15,p.y-72],[p.x+Math.cos(a)*23,p.y-58]],"#c5f8ed",2);}
    oval(p.x,p.y-84+(reducedMotion.matches?0:Math.sin(t*2)*2),5,7,"#d2fff7");
  }
  function building(p,i) {
    const a=project(p.x,p.y);g.save();g.translate(a.x,a.y);
    oval(15,7,100,30,"#295c5030");
    if(i===2) {
      // Fishing hut and a timber jetty projecting over the pond.
      for(let n=0;n<7;n++)poly([[-35+n*15,2+n*5],[-20+n*15,-6+n*5],[45+n*15,25+n*5],[30+n*15,33+n*5]],n%2?"#bd8e60":"#d5aa79","#ab7e55");
    }
    const roof=p.roof;
    poly([[-76,-90],[22,-75],[22,8],[-76,-12]],p.color,"#59716c");
    poly([[22,-75],[78,-108],[78,-22],[22,8]],i===3?"#677ba9":"#b9a382","#59716c");
    // Foundation and weatherboards.
    line([[-76,-12],[22,8],[78,-22]],"#efe4c9",9);
    for(let y=-65;y<-14;y+=15)line([[-72,y],[18,y+16]],"#ffffff30",2);
    poly([[-90,-94],[-24,-159],[92,-120],[27,-68]],roof,"#52666b");
    poly([[-90,-94],[-24,-159],[-18,-104],[27,-68]],i===3?"#ac9bd8":"#f5bc89");
    line([[-24,-159],[92,-120],[27,-68],[-90,-94]],"#fff0ca",6);
    for(let k=1;k<6;k++)line([[-24+k*17,-155+k*5],[ -16+k*17,-103+k*5]],"#ffffff29",2);
    // Lit windows, frames and a welcoming doorstep.
    round(-64,-75,28,31,5,"#fff3ce");round(-60,-71,20,23,3,"#7dcbd0");line([[-50,-71],[-50,-48]],"#ffefc2",3);line([[-60,-60],[-40,-60]],"#ffefc2",3);
    round(-20,-63,29,58,12,"#fff0cb");round(-15,-58,19,52,9,"#426b6c");oval(0,-31,2,2,"#ffd876");
    poly([[-25,0],[16,8],[8,15],[-32,7]],"#efdbc2");
    poly([[38,-69],[65,-84],[65,-53],[38,-38]],"#ffe7ac");line([[51,-76],[51,-45]],"#8d886f",3);
    if(i===1) {
      // Striped café canopy, chimney, and terrace table.
      for(let n=0;n<6;n++)poly([[-76+n*14,-40],[-62+n*14,-38],[-59+n*14,-23],[-73+n*14,-25]],n%2?"#fff4db":"#e58b78");
      round(36,-156,19,39,3,"#bd846a");round(32,-160,27,9,3,"#eed5b5");
      line([[-101,22],[-101,-9]],"#8c7253",5);oval(-101,-12,26,12,"#fff0ca");round(-110,-21,12,10,3,"#bd775e");
    } else if(i===3) {
      round(-64,-107,66,23,6,"#344967");text("♫ CLUB",-31,-91,14,"#b8f1ed");
      for(const dx of [-95,92]){round(dx,-46,21,44,5,"#394e68");oval(dx+10,-23,7,10,"#8aa0b4");}
    } else if(i===4) {
      for(let n=0;n<4;n++){round(-89+n*41,25,34,15,4,"#aa7650");flower(-74+n*41,24,["#f2b6b0","#fff0aa","#b5bcf4","#ffce80"][n]);}
    } else if(i===5) {
      round(29,-203,33,63,5,"#e5dbc3");round(24,-210,43,20,5,"#87c6d1");poly([[18,-211],[45,-239],[74,-211]],"#5a7c98");
      if(save.stars.length===3)oval(45,-201,12,7,"#fff4aa");
    } else if(i===0) {
      oval(-15,-118,16,16,"#fff0c7");line([[-15,-129],[-15,-118],[-7,-114]],"#506f76",3);
      line([[45,-155],[45,-197]],"#66796d",3);poly([[46,-197],[77,-187],[46,-180]],"#ee917e");
    }
    // Flowers frame the entrance, rather than plain floating labels.
    for(const dx of [-80,77]){round(dx-9,0,18,13,4,"#bb7d60");flower(dx,1,i%2?"#ffe7a2":"#f5b0bd");}
    label(p.name,0,-177-(i===5?70:0));g.restore();
  }
  function pathDistance(x,y,r) {const [ax,ay,bx,by]=r,dx=bx-ax,dy=by-ay,t=Math.max(0,Math.min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)));return Math.hypot(x-ax-t*dx,y-ay-t*dy);}
  function makeTerrain() {
    terrain=document.createElement("canvas");terrain.width=3000;terrain.height=1700;
    const screen=g;g=terrain.getContext("2d");g.translate(1500,60);
    const corners=[project(0,0),project(33,0),project(33,33),project(0,33)].map(p=>[p.x,p.y]);
    poly(corners.map(([x,y])=>[x,y+18]),"#499ba0");poly(corners,"#e7dbaf");
    poly([project(1,1),project(32,1),project(32,32),project(1,32)].map(p=>[p.x,p.y]),"#a9cc91");
    // Soft patches replace the distracting checkerboard ground.
    for(let n=0;n<220;n++){const x=2+(n*7.31)%29,y=2+(n*11.73)%29,p=project(x,y);oval(p.x,p.y,25+n%35,10+n%12,n%2?"#b6d69a":"#a2c88d");}
    for(const r of routes){const a=project(r[0],r[1]),b=project(r[2],r[3]);line([[a.x,a.y],[b.x,b.y]],"#90b581",68);line([[a.x,a.y],[b.x,b.y]],"#f1dfb6",57);line([[a.x,a.y-2],[b.x,b.y-2]],"#f9eacb",43);}
    const plaza=project(12,14);oval(plaza.x,plaza.y,235,113,"#91b787");oval(plaza.x,plaza.y-5,223,105,"#dccca8");oval(plaza.x,plaza.y-8,210,97,"#f3e5c6");
    for(let n=0;n<50;n++){const a=n/50*Math.PI*2;oval(plaza.x+Math.cos(a)*196,plaza.y-8+Math.sin(a)*87,4,2,"#ceb994");}
    const pond=project(22,5);oval(pond.x,pond.y,202,92,"#d9d8ad");oval(pond.x,pond.y-5,185,80,"#71c3c5");oval(pond.x-9,pond.y-10,163,66,"#8cdbd8");
    for(let n=0;n<18;n++){const x=pond.x-135+(n*43)%260,y=pond.y-40+(n*17)%75;line([[x,y],[x+14,y]],"#c4f1e4",2);}
    // Destination terraces give each activity its own little outdoor room.
    for(let x=0;x<4;x++)for(let y=0;y<3;y++){
      const p=project(22+x*.45,20+y*.45), colors=["#b9a8d4","#e7c4d2","#a5cfcb","#f0d4a0"];
      poly([[p.x,p.y-10],[p.x+19,p.y],[p.x,p.y+10],[p.x-19,p.y]],colors[(x+y)%4]);
    }
    for(let n=0;n<3;n++){
      const p=project(7+n*.75,25.5);poly([[p.x-22,p.y],[p.x,p.y-12],[p.x+38,p.y+7],[p.x+16,p.y+19]],"#ad8460");
      for(let k=0;k<3;k++)flower(p.x+k*10,p.y+k*4,["#ffe5a0","#eeb0ac","#c0b9e1"][n]);
    }
    scenery=[];
    for(let n=0;n<130;n++){
      const x=2+(n*7.37)%29,y=2+(n*11.71)%29;
      if(places.some(p=>Math.hypot(x-p.x,y-p.y)<3.3)||routes.some(r=>pathDistance(x,y,r)<1.1)||Math.hypot(x-12,y-14)<3.8||Math.hypot(x-22,y-5)<3.2)continue;
      scenery.push({x,y,kind:"tree",seed:n});const p=project(x+.5,y+.3);flower(p.x,p.y,n%2?"#fff3c0":"#e6a9b8");
    }
    for(const [x,y] of [[10,14],[14,15],[7,9],[23,22],[26,30]])scenery.push({x,y,kind:"lamp"});
    for(const [x,y] of [[10,16],[14,13],[19,8]])scenery.push({x,y,kind:"bench"});
    g=screen;
  }
  function visitor(x,y,color,t) {
    const p=project(x,y),bob=reducedMotion.matches?0:Math.sin(t*1.5+x)*1.5;
    oval(p.x,p.y,16,6,"#325b4930");oval(p.x-7,p.y-2,6,4,"#496b65");oval(p.x+7,p.y-2,6,4,"#496b65");
    oval(p.x,p.y-19+bob,17,22,color);oval(p.x,p.y-12+bob,10,11,"#fff3d4");
    oval(p.x-6,p.y-25+bob,2,3,"#34545c");oval(p.x+6,p.y-25+bob,2,3,"#34545c");oval(p.x,p.y-20+bob,3,2,"#de946d");
  }
  function draw(now) {
    if (!active) return;
    const dt=Math.min((now-last)/1000||0,.05);last=now;
    const moving=Math.hypot(target.x-player.x,target.y-player.y)>.08;
    if(!game&&$("islandActivity").hidden){const dx=target.x-player.x,dy=target.y-player.y,dist=Math.hypot(dx,dy),step=Math.min(dist,dt*5);if(dist>.01){faceLeft=dx-dy<0;player.x+=dx/dist*step;player.y+=dy/dist*step;}}
    if(PixelInteriors.active){PixelInteriors.draw(g,cv,dt,now,pup);frame=requestAnimationFrame(draw);return;}
    const pos=project(player.x,player.y);camera={x:cv.width/2-pos.x,y:cv.height/2-pos.y+65};
    g.fillStyle="#7bc6cb";g.fillRect(0,0,cv.width,cv.height);g.save();g.translate(camera.x,camera.y);
    g.drawImage(terrain,-1500,-60);
    const objects=places.map((p,i)=>({depth:p.x+p.y,draw:()=>building(p,i)}));
    for(const s of scenery){const p=project(s.x,s.y);if(p.x+camera.x < -100||p.x+camera.x>cv.width+100||p.y+camera.y < -50||p.y+camera.y>cv.height+150)continue;objects.push({depth:s.x+s.y,draw:()=>s.kind==="tree"?tree(s.x,s.y,s.seed):s.kind==="lamp"?lamp(s.x,s.y):bench(s.x,s.y)});}
    objects.push({depth:26.7,draw:()=>fountain(13,13.7,now/1000)});
    [[10.7,13.5,"#f3ba79"],[14,15.5,"#9ac6d6"],[5,9.5,"#d8b6cf"],[23,21,"#f0be80"]].forEach(([x,y,c])=>objects.push({depth:x+y,draw:()=>visitor(x,y,c,now/1000)}));
    // Bunting connects the plaza lamp posts.
    const a=project(10,14),b=project(14,15);
    line([[a.x,a.y-80],[(a.x+b.x)/2,(a.y+b.y)/2-60],[b.x,b.y-80]],"#6a8b78",2);
    for(let n=1;n<9;n++){const t=n/9,x=a.x+(b.x-a.x)*t,y=a.y+(b.y-a.y)*t-80+Math.sin(t*Math.PI)*18;poly([[x-6,y],[x+6,y+2],[x,y+15]],["#ec9687","#f3ce7b","#89bfc5"][n%3]);}
    stars.forEach((s,i)=>{if(save.stars.includes(i))return;const p=project(s.x,s.y);oval(p.x,p.y,16,6,"#ac945730");text("★",p.x,p.y-14+(reducedMotion.matches?0:Math.sin(now/450)*3),28,"#fff0a3");if(Math.hypot(player.x-s.x,player.y-s.y)<1.2){save.stars.push(i);note=`Found a lost star! ${save.stars.length}/3 — return to Lookout lodge when you have them all.`;persist();}});
    if(save.flower){const p=project(9,25);for(let n=0;n<6;n++)flower(p.x+n*10,p.y+n%2*6,save.flower==="Poppy"?"#e99788":save.flower==="Bluebell"?"#a5a9e3":"#ffe69a");}
    objects.push({depth:player.x+player.y,draw:()=>{
      oval(pos.x,pos.y,23,9,"#335b4940");
      const pose=PalStage.livePose(pup.rigOf(0),pup.lifeline,now/1000,{move:moving&&!reducedMotion.matches?"walk":null,moveT:now/160});
      pup.draw(g,0,pose,pos.x,pos.y,{flip:faceLeft});
      poly([[pos.x-5,pos.y-70],[pos.x+5,pos.y-70],[pos.x,pos.y-63]],"#fffdf1");
    }});
    objects.sort((a,b)=>a.depth-b.depth).forEach(o=>o.draw());
    if(moving){const p=project(target.x,target.y);g.strokeStyle="#fffbee";g.lineWidth=2;g.beginPath();g.ellipse(p.x,p.y,13,6,0,0,Math.PI*2);g.stroke();}
    g.restore();
    const next=places.findIndex(p=>Math.hypot(player.x-p.x,player.y-p.y)<3.5);
    if(next!==nearby){nearby=next;$("islandInteract").disabled=next<0;$("islandInteract").textContent=next<0?"Choose a place to explore":"Enter "+places[next].name+" · E";$("islandLocation").textContent=next<0?"Island trails":places[next].name;document.querySelectorAll("[data-island-place]").forEach((b,i)=>b.classList.toggle("here",i===next));}
    // The overview uses the same projection as the world.
    round(18,18,136,117,18,"#fffdf2ed");text("Island map",86,40,12);
    const mini=(x,y)=>({x:86+(x-y)*1.65,y:55+(x+y)*.95});
    poly([[86,50],[141,82],[86,115],[31,82]],"#9bc597");
    places.forEach((p,i)=>{const m=mini(p.x,p.y);oval(m.x,m.y,4,3,p.roof);});const m=mini(player.x,player.y);oval(m.x,m.y,5,5,"#fffdf0");oval(m.x,m.y,3,3,"#315f6a");
    if(game&&game.kind==="fish"&&now-game.cast>=game.delay&& !game.biting){game.biting=true;$("islandActivityText").textContent="Bite! Your float dips under — reel in your fish!";}
    frame=requestAnimationFrame(draw);
  }
  function open() {
    if (active) return;
    cv=$("islandCanvas");g=cv.getContext("2d");fitCanvas();
    key="pixel-island-v1:"+me;
    let raw;try {raw=JSON.parse(localStorage.getItem(key));}catch(_){}
    save={coins:0,stamps:[],stars:[],flower:null};
    if(raw && typeof raw==="object") {
      save.coins=Number.isFinite(raw.coins)?Math.max(0,raw.coins):0;
      for(const k of ["stamps","stars"]) save[k]=Array.isArray(raw[k])?[...new Set(raw[k].filter(n=>Number.isInteger(n)&&n>=0&&n<(k==="stars"?3:6)))]:[];
      save.flower=["Sunflower","Bluebell","Poppy"].includes(raw.flower)?raw.flower:null;
    }
    save.adventure=PixelInteriors.clean(raw?.adventure);
    const pal=currentPal();pup=PalStage.puppet(pal,Math.max(1,Math.round(48/pal.size)));if(!terrain)makeTerrain();nearby=-2;status();active=true;last=0;frame=requestAnimationFrame(draw);
  }
  function close() { if(PixelInteriors.active)PixelInteriors.leave();active=false;cancelAnimationFrame(frame);game=null;$("islandActivity").hidden=true; }
  function setup() {
    $("islandDestinations").innerHTML=places.map((p,i)=>`<button class="btn" data-island-place="${i}"><span class="destination-icon" aria-hidden="true">${symbols[i]}</span><span><span class="destination-name">${p.name}</span><small>${travelNotes[i]}</small></span><span class="destination-mark" aria-hidden="true">›</span></button>`).join("");
    $("islandDestinations").onclick=e=>{const b=e.target.closest("[data-island-place]");if(!b)return;if(PixelInteriors.active)PixelInteriors.leave();const p=places[Number(b.dataset.islandPlace)];dismiss();target={x:p.x,y:p.y+2};};
    $("islandInteract").onclick=interact;$("islandDismiss").onclick=dismiss;
    $("islandCanvas").onclick=e=>{if(!active)return;const rect=cv.getBoundingClientRect();if(PixelInteriors.active){PixelInteriors.click((e.clientX-rect.left)/rect.width*cv.width,(e.clientY-rect.top)/rect.height*cv.height,cv);cv.focus();return;}const r=cv.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*cv.width-camera.x,y=(e.clientY-r.top)/r.height*cv.height-camera.y;target={x:clamp((y/23+x/43)/2),y:clamp((y/23-x/43)/2)};cv.focus();};
    $("islandCanvas").onkeydown=e=>{
      if(!active)return;
      if(PixelInteriors.active){if(PixelInteriors.key(e))e.preventDefault();return;}
      if(e.key.toLowerCase()==="e"){e.preventDefault();interact();return;}
      const d={ArrowUp:[-1,-1],ArrowDown:[1,1],ArrowLeft:[-1,1],ArrowRight:[1,-1],w:[-1,-1],s:[1,1],a:[-1,1],d:[1,-1]}[e.key];
      if(d){e.preventDefault();target={x:clamp(player.x+d[0]*1.5),y:clamp(player.y+d[1]*1.5)};}
    };
  }
  function fitCanvas() {
    const canvas=$("islandCanvas"), r=canvas.getBoundingClientRect();
    if(r.width && r.height) { canvas.width=Math.max(540,Math.min(960,Math.round(r.width))); canvas.height=Math.round(canvas.width*r.height/r.width); }
  }
  new ResizeObserver(fitCanvas).observe($("islandCanvas"));
  setup(); return {open,close};
})();
