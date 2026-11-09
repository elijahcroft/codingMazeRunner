// Walkable story rooms, with resumable scenarios and open-ended role play.
"use strict";
const PixelInteriors = (() => {
  const rooms = [
    {name:"Festival hall",wall:"#b8d7cb",floor:"#dec79f",accent:"#e29b71",role:["Host","Storyteller","Guest"],stations:[
      ["board","Planning board",200,325,"board"],["costume","Costume rail",720,330,"wardrobe"],["desk","Invitation desk",340,420,"desk"],["stage","Story stage",650,435,"stage"]]},
    {name:"Inside Cocoa café",wall:"#efd3b8",floor:"#d8b38e",accent:"#c98987",role:["Barista","Baker","Customer"],stations:[
      ["till","Order counter",200,320,"counter"],["pantry","Ingredient shelf",450,320,"shelf"],["brew","Cocoa machine",720,320,"machine"],["table","Window table",650,450,"table"],["sink","Wash-up sink",250,455,"sink"]]},
    {name:"Crystal boathouse",wall:"#b2d5dc",floor:"#c4b899",accent:"#519eac",role:["Angler","Marine scientist","Boat captain"],stations:[
      ["map","Lake guide",200,320,"board"],["bait","Tackle bench",450,325,"shelf"],["pier","Indoor fishing dock",740,390,"pier"],["tank","Observation tank",290,440,"tank"],["log","Field journal",570,465,"desk"]]},
    {name:"Inside the music club",wall:"#bcb7d5",floor:"#9b9bb8",accent:"#8171b2",role:["DJ","Dancer","Stage manager"],stations:[
      ["dj","DJ booth",200,325,"dj"],["lights","Lighting desk",470,320,"machine"],["costume","Dressing room",745,320,"wardrobe"],["stage","Dance floor",600,460,"stage"]]},
    {name:"Sunny greenhouse",wall:"#c4dcb7",floor:"#d9c799",accent:"#7da36b",role:["Gardener","Florist","Botanist"],stations:[
      ["seeds","Seed library",200,325,"shelf"],["pot","Potting bench",460,325,"planter"],["water","Water barrel",740,330,"sink"],["sun","Sunny growing bed",680,445,"planter"],["bouquet","Flower workshop",290,450,"table"]]},
    {name:"Inside Lookout lodge",wall:"#bed0da",floor:"#c9b399",accent:"#638ca7",role:["Explorer","Astronomer","Lighthouse keeper"],stations:[
      ["map","Expedition map",200,325,"board"],["books","Clue library",450,320,"shelf"],["scope","Telescope",745,340,"scope"],["bench","Lantern workbench",310,450,"machine"],["beacon","Signal lantern",650,460,"beacon"]]},
  ];
  const orders=[{who:"Milo",drink:"Cocoa",top:"Marshmallows"},{who:"Luna",drink:"Tea",top:"Honey"},{who:"Pip",drink:"Milk",top:"Cinnamon"}];
  let current=-1, api=null, state=null, at={x:480,y:535}, target={...at}, selected=null, queued=null, speech="", speechUntil=0, lastView="";
  const stages = [
    ["Choose a festival theme at the planning board.","Choose your costume at the rail.","Write invitations at the desk.","Rehearse your opening on the story stage.","Launch the festival from the planning board."],
    ["Take a customer's order at the counter.","Collect the requested ingredients from the shelf.","Brew the drink at the cocoa machine.","Deliver the drink to the window table.","Wash the cup and tidy the sink."],
    ["Read the lake guide to plan your expedition.","Choose bait at the tackle bench.","Cast a line from the indoor dock.","Identify your catch at the observation tank.","Record and release your catch in the field journal."],
    ["Pick your song at the DJ booth.","Set the matching lights at the lighting desk.","Choose a stage outfit in the dressing room.","Rehearse the pattern on the dance floor.","Start the performance from the DJ booth."],
    ["Choose a flower from the seed library.","Plant it at the potting bench.","Measure water at the barrel.","Move your plant to the sunny growing bed.","Arrange a festival bouquet in the workshop."],
    ["Study the expedition map.","Decode the symbols in the clue library.","Find the constellation through the telescope.","Build a lantern at the workbench.","Send the signal from the lantern stand."],
  ];
  const stationSequence=[ ["board","costume","desk","stage","board"],["till","pantry","brew","table","sink"],["map","bait","pier","tank","log"],["dj","lights","costume","stage","dj"],["seeds","pot","water","sun","bouquet"],["map","books","scope","bench","beacon"] ];
  function clean(raw) {
    const out={rooms:[],inventory:[],journal:[]};
    for(let i=0;i<6;i++){
      const r=raw?.rooms?.[i]||{};
      const values={};
      for(const k of ["theme","outfit","guests","opening","drink","top","song","light","seed","bait","bearing","lens","storyProp","sceneMood"])if(typeof r.values?.[k]==="string"&&r.values[k].length<70)values[k]=r.values[k];
      out.rooms.push({step:Number.isInteger(r.step)&&r.step>=0&&r.step<=5?r.step:0,round:Number.isInteger(r.round)&&r.round>=0&&r.round<3?r.round:0,role:rooms[i].role.includes(r.role)?r.role:rooms[i].role[0],values});
    }
    out.inventory=Array.isArray(raw?.inventory)?[...new Set(raw.inventory.filter(x=>["Festival invitation","Café picnic","Lake field notes","Concert recording","Festival bouquet","Explorer lantern"].includes(x)))]:[];
    out.journal=Array.isArray(raw?.journal)?raw.journal.filter(x=>typeof x==="string"&&x.length<200).slice(-8):[];
    return out;
  }
  function commit(line) {
    if(line){state.journal.push(line);state.journal=state.journal.slice(-8);}
    api.persist();refresh();
  }
  const task=()=>state.rooms[current];
  function refresh() {
    const r=task();
    $("interiorObjective").textContent=r.step===5?"Scenario complete! Replay it, or make up a scene with the props.":stages[current][r.step]+(current===1?` Customer ${r.round+1} of 3.`:"");
    $("interiorBag").textContent=state.inventory.length?"Backpack: "+state.inventory.join(", "):"Your backpack is empty. Complete scenarios to collect story props.";
    $("interiorRole").textContent="Playing as: "+r.role;
    $("interiorHistory").replaceChildren(...state.journal.slice(-4).map(s=>{const li=document.createElement("li");li.textContent=s;return li;}));
    $("interiorReplay").hidden=r.step!==5;
    document.querySelectorAll("[data-station]").forEach(b=>{b.classList.toggle("here",r.step<5&&b.dataset.station===stationSequence[current][r.step]);});
  }
  function enter(i, options) {
    current=i;api=options;state=api.save.adventure;at={x:480,y:535};target={...at};selected=null;queued=null;speech="";lastView="";
    $("islandDestinations").hidden=true;$("islandTravelTitle").hidden=true;$("interiorPanel").hidden=false;$("islandExit").hidden=false;
    $("islandLocation").textContent=rooms[i].name;$("islandInteract").textContent="Choose a prop to use";$("islandInteract").disabled=true;
    $("islandCanvas").setAttribute("aria-label",rooms[i].name+". Click a prop, or use arrow keys to walk and E to interact. Escape returns outside.");
    $("interiorStations").replaceChildren(...rooms[i].stations.map(s=>{const b=document.createElement("button");b.className="btn";b.dataset.station=s[0];b.textContent=s[1];b.onclick=()=>travel(s);return b;}));
    $("interiorRoles").replaceChildren(...rooms[i].role.map(role=>{const b=document.createElement("button");b.className="btn";b.textContent=role;b.onclick=()=>{task().role=role;commit();say("I'm the "+role.toLowerCase()+"!");};return b;}));
    api.dismiss();refresh();
  }
  function leave() {
    if(current<0)return;
    current=-1;queued=null;selected=null;$("islandExit").hidden=true;$("interiorPanel").hidden=true;$("islandDestinations").hidden=false;$("islandTravelTitle").hidden=false;
    api.dismiss();api.onExit();
    $("islandCanvas").setAttribute("aria-label","Isometric island. Click to walk or use arrow keys. E enters a nearby building.");
  }
  function say(words) {speech=words;speechUntil=performance.now()+4500;}
  function choice(title,description,options) {api.panel(title,description,options);}
  function advance(words) {task().step++;say(words);commit(words);api.dismiss();}
  function finish() {
    const souvenirs=["Festival invitation","Café picnic","Lake field notes","Concert recording","Festival bouquet","Explorer lantern"],r=task();
    r.step=5;if(!state.inventory.includes(souvenirs[current]))state.inventory.push(souvenirs[current]);
    const line=rooms[current].name+": scenario complete! Collected "+souvenirs[current]+".";
    commit(line);api.reward(current,line);choice("You did it!",line,[["Keep playing in this room",()=>{api.dismiss();refresh();}]]);
  }
  function travel(s) {api.dismiss();queued=s;target={x:s[2],y:Math.min(535,s[3]+65)};$("islandCanvas").focus();}
  function use(s) {
    queued=null;selected=s;
    const r=task(),expected=stationSequence[current][r.step];
    if(r.step===5||s[0]!==expected){
      choice(s[1],r.step===5?"Make up your own scene. Your role is "+r.role.toLowerCase()+".":stages[current][r.step],[["Use this prop in my story",()=>{say(propLine(s[0]));commit(r.role+": "+propLine(s[0]));api.dismiss();}],["Back to the room",api.dismiss]]);return;
    }
    const pick=(title,description,labels,key,next)=>choice(title,description,labels.map(v=>[v,()=>{r.values[key]=v;next(v);} ]));
    if(current===0){
      if(r.step===0)pick("Plan a festival","What story will everyone act out?",["Underwater adventure","Space rescue","Royal picnic"],"theme",v=>advance("Our theme is "+v.toLowerCase()+"!"));
      else if(r.step===1)pick("Dress the part","Choose a costume for "+r.values.theme+".",["Explorer scarf","Star cape","Flower crown"],"outfit",v=>advance("Costume ready: "+v+"."));
      else if(r.step===2)pick("Send invitations","Who should join your story?",["The café crew","The dance club","The garden team"],"guests",v=>advance(v+" will join our festival."));
      else if(r.step===3)pick("Rehearse the opening","Set the scene for "+r.values.theme+".",["We discovered a secret map!","A visitor needs our help!","The celebration is about to begin!"],"opening",v=>advance(v));
      else choice("Open the festival",`${r.values.theme}. ${r.values.guests} are invited. ${r.values.opening}`+(state.inventory.includes("Festival bouquet")?" Your greenhouse bouquet decorates the stage!":""),[["Welcome everyone to the festival",finish]]);
    } else if(current===1){
      const order=orders[r.round];
      if(r.step===0)choice("A customer arrives",`${order.who}: “I'd like ${order.drink.toLowerCase()} with ${order.top.toLowerCase()}, please.”`,[["Write down the order",()=>advance(`${order.who} ordered ${order.drink} + ${order.top}.`)]]);
      else if(r.step===1)pick("Pick the drink",`${order.who}'s order: ${order.drink} with ${order.top}.`,["Cocoa","Tea","Milk"],"drink",()=>pick("Pick the topping","Check the order before brewing.",["Marshmallows","Honey","Cinnamon"],"top",()=>advance("Ingredients collected. Time to brew!")));
      else if(r.step===2)choice("Brew station",`On your tray: ${r.values.drink} with ${r.values.top}.`,[["Brew and stir",()=>{
        if(r.values.drink!==order.drink||r.values.top!==order.top){r.step=1;commit();choice("Check the order",`${order.who} asked for ${order.drink} with ${order.top}. Choose the ingredients again.`,[["Back to the shelf",()=>travel(rooms[1].stations[1])]]);}else advance("One warm drink, ready to serve!");
      }]]);
      else if(r.step===3)choice("Serve the window table",`${order.who} is waiting for their drink.`,[["Serve with a friendly greeting",()=>advance(`${order.who}: “Thank you! That's just what I wanted.”`)]]);
      else choice("Wash-up time","Wash, rinse and put away the cup before the next customer.",[["Wash and rinse",()=>choice("A sparkling cup","Put the clean cup on the drying rack.",[["Put it away",()=>{if(r.round===2)finish();else{r.round++;r.step=0;r.values={};commit("The table is ready for the next customer.");api.dismiss();}}]])]]);
    } else if(current===2){
      if(r.step===0)choice("Lake field guide","The silverfin has silver scales and a blue tail. It likes worms. Observe one, then release it.",[["Pack my field guide",()=>advance("Look for a silver fish with a blue tail. Use worms.")]]);
      else if(r.step===1)pick("Tackle bench","Choose bait using your field guide.",["Worms","Seeds","Bread"],"bait",v=>{if(v==="Worms")advance("Worms packed. Ready for the dock!");else choice("Try the guide again","Silverfins like worms.",[["Choose again",()=>use(s)]]);});
      else if(r.step===2)choice("Cast from the dock","Cast your line and watch the float.",[["Cast line",()=>{r.castAt=performance.now();say("Watching the float…");choice("Line in the water","Wait two seconds, then check your float.",[["Reel in",()=>{if(performance.now()-r.castAt<2000){say("No bite yet. Give it another moment.");return;}advance("A silver fish with a blue tail! Take a closer look in the tank.");}]]);}]]);
      else if(r.step===3)choice("Observation tank","Silver scales. Blue tail. Which fish is it?",["Silverfin","Sunfish","Minnow"].map(n=>[n,()=>n==="Silverfin"?advance("Identified: silverfin!"):say("Look at the silver scales and blue tail.")]));
      else choice("Field journal","Record the silverfin's features and return it gently to the lake.",[["Record and release",finish]]);
    } else if(current===3){
      if(r.step===0)pick("Build your show","Choose the mood for tonight's performance.",["Ocean groove","Sunset swing"],"song",v=>advance(v+" is on the playlist."));
      else if(r.step===1)pick("Light the stage",r.values.song==="Ocean groove"?"The ocean song needs blue lights.":"The sunset song needs gold lights.",["Blue","Gold","Pink"],"light",v=>{if(v===(r.values.song==="Ocean groove"?"Blue":"Gold"))advance(v+" lights are ready.");else say("Try the color in the lighting cue.");});
      else if(r.step===2)pick("Choose your look","Pick an outfit for your performance.",["Sparkle jacket","Star cape","Rainbow scarf"],"outfit",v=>advance(v+" — ready for rehearsal."));
      else if(r.step===3){const pattern=r.values.song==="Ocean groove"?["Step","Spin","Clap","Step"]:["Clap","Step","Clap","Spin"];let beat=0;choice("Rehearse together",pattern.join(" → "),["Clap","Step","Spin"].map(move=>[move,()=>{if(move!==pattern[beat]){beat=0;say("Try again from the first move.");}else{beat++;say(move+"!");if(beat===4)advance("Rehearsal complete. Start the show at the DJ booth!");}}]));}
      else choice("It's showtime",`${r.values.song}, ${r.values.light.toLowerCase()} lights, and your ${r.values.outfit.toLowerCase()}.`,[["Start the performance",finish]]);
    } else if(current===4){
      if(r.step===0)pick("Seed library","Choose a flower. Sunflowers need two scoops of water; poppies and bluebells need one.",["Sunflower","Poppy","Bluebell"],"seed",v=>advance("Picked a "+v.toLowerCase()+" seed."));
      else if(r.step===1)choice("Potting bench","Fill a pot with soil, make a small hole, and plant your seed.",[["Fill with soil",()=>choice("Plant gently","Drop the seed in and cover it with soil.",[["Plant the seed",()=>advance("Your seed is planted.")]])]]);
      else if(r.step===2)choice("Measure the water",`${r.values.seed}: ${r.values.seed==="Sunflower"?"two scoops":"one scoop"} of water.`,[1,2,3].map(n=>[n+" scoop"+(n>1?"s":""),()=>n===(r.values.seed==="Sunflower"?2:1)?advance("Just the right amount of water!"):say("Check the seed instructions; try a different amount.")]));
      else if(r.step===3)choice("Choose a sunny spot","Your watered plant is ready to grow.",[["Set it beside the window",()=>{api.save.flower=r.values.seed;advance("Your "+r.values.seed.toLowerCase()+" blooms in the sunshine!");}]]);
      else pick("Arrange your bouquet","Choose a ribbon for your festival flowers.",["Gold ribbon","Blue ribbon","Pink ribbon"],"outfit",finish);
    } else {
      if(r.step===0)choice("The missing lantern signal","The map shows a star, a wave, and a moon. The clue library explains what they mean.",[["Copy the symbols",()=>advance("Clue copied: star → wave → moon.")],["Return outdoor lost stars",()=>{if(api.save.stars.length===3){commit("Returned all three lost stars to the lodge.");say("The lost stars are home!");}else say("There are three stars hidden outside. Keep exploring!");}]]);
      else if(r.step===1)choice("Decode the map","Star means north. Wave means blue. Moon means night. Which direction should the telescope face?",["North","South","West"].map(v=>[v,()=>{if(v==="North"){r.values.bearing=v;advance("Point north and look for the moon constellation.");}else say("Star means north. Try again.");}]));
      else if(r.step===2)choice("Through the telescope","You spot three constellations. The final symbol was a moon.",["Moon constellation","Dragon constellation","Crown constellation"].map(v=>[v,()=>v==="Moon constellation"?advance("Moon constellation found! The lantern needs the wave's color."):say("Match the last symbol on the map.")]));
      else if(r.step===3)pick("Build the signal lantern","Fit the colored lens from the wave clue.",["Blue lens","Red lens","Gold lens"],"lens",v=>v==="Blue lens"?advance("Blue lens fitted. The lantern is ready."):say("The wave symbol means blue."));
      else choice("Send the signal","Point the blue lantern north, toward the moon constellation.",[["Light the lantern",finish]]);
    }
  }
  function propLine(id) {return ({till:"Welcome! What would you like today?",pantry:"Let's invent a new recipe!",brew:"One special drink coming up!",table:"Let's sit down and plan our adventure.",sink:"I'll tidy up before our next scene.",stage:"Everyone, the show is about to begin!",scope:"I see something in the stars!",beacon:"Follow the light — we're over here!",board:"I have an idea for our next adventure!"})[id]||"Let's use this in our story!";}
  function interact(){if(selected)use(selected);}
  function key(e){if(e.key==="Escape"){leave();return true;}if(e.key.toLowerCase()==="e"){interact();return true;}const d={ArrowLeft:[-35,0],a:[-35,0],ArrowRight:[35,0],d:[35,0],ArrowUp:[0,-28],w:[0,-28],ArrowDown:[0,28],s:[0,28]}[e.key];if(d){queued=null;target={x:Math.max(115,Math.min(845,at.x+d[0])),y:Math.max(340,Math.min(550,at.y+d[1]))};return true;}return false;}
  function click(x,y,canvas){const scale=Math.min(canvas.width/960,canvas.height/610),ox=(canvas.width-960*scale)/2,oy=(canvas.height-610*scale)/2;x=(x-ox)/scale;y=(y-oy)/scale;if(x>=100&&x<=210&&y>=548&&y<=590){leave();return;}const s=rooms[current].stations.find(s=>Math.abs(x-s[2])<72&&y>s[3]-105&&y<s[3]+35);if(s){travel(s);return;}queued=null;target={x:Math.max(115,Math.min(845,x)),y:Math.max(340,Math.min(550,y))};}
  function draw(ctx,canvas,dt,now,pup) {
    if(current<0)return;
    const room=rooms[current],r=task(),g=ctx;
    const rect=(x,y,w,h,color,radius=6)=>{g.fillStyle=color;g.beginPath();g.roundRect(x,y,w,h,radius);g.fill();};
    const ellipse=(x,y,rx,ry,color)=>{g.fillStyle=color;g.beginPath();g.ellipse(x,y,rx,ry,0,0,Math.PI*2);g.fill();};
    const poly=(points,color)=>{g.fillStyle=color;g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.fill();};
    const line=(points,color,width=3)=>{g.strokeStyle=color;g.lineWidth=width;g.lineCap="round";g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.stroke();};
    const text=(s,x,y,size=14,color="#365452")=>{g.fillStyle=color;g.font=`800 ${size}px ui-rounded, sans-serif`;g.textAlign="center";g.fillText(s,x,y);};
    const cup=(x,y,c="#fff4db")=>{rect(x-7,y-15,14,17,c,3);ellipse(x+9,y-7,5,5,c);ellipse(x+9,y-7,2,3,room.floor);ellipse(x,y-15,6,2,"#916b53");};
    const plant=(x,y,bloom=false)=>{rect(x-9,y-14,18,17,"#b98664",4);line([[x,y-12],[x,y-45]],"#5b8b64",4);ellipse(x-8,y-29,11,5,"#81ab74");ellipse(x+8,y-38,10,5,"#8eb47b");if(bloom){for(let a=0;a<6;a++)ellipse(x+Math.cos(a)*8,y-48+Math.sin(a)*8,6,6,"#f1be7d");ellipse(x,y-48,5,5,"#c38b50");}};
    const moving=Math.hypot(at.x-target.x,at.y-target.y)>2;
    if($("islandActivity").hidden&&moving){const dx=target.x-at.x,dy=target.y-at.y,d=Math.hypot(dx,dy),v=Math.min(d,dt*220);at.x+=dx/d*v;at.y+=dy/d*v;}
    selected=room.stations.reduce((best,s)=>Math.hypot(s[2]-at.x,s[3]+55-at.y)<Math.hypot((best?.[2]??-999)-at.x,(best?.[3]??-999)+55-at.y)?s:best,null);
    if(selected&&Math.hypot(selected[2]-at.x,selected[3]+55-at.y)>110)selected=null;
    const view=selected?.[0]||"";
    if(view!==lastView){lastView=view;$("islandInteract").disabled=!selected;$("islandInteract").textContent=selected?"Use "+selected[1]+" · E":"Choose a prop to use";}
    if(queued&&!moving&&$("islandActivity").hidden){const s=queued;queued=null;use(s);}
    g.fillStyle="#dbe9e3";g.fillRect(0,0,canvas.width,canvas.height);
    const scale=Math.min(canvas.width/960,canvas.height/610),ox=(canvas.width-960*scale)/2,oy=(canvas.height-610*scale)/2;
    g.save();g.translate(ox,oy);g.scale(scale,scale);
    ellipse(480,565,435,32,"#58736b20");
    // Cutaway walls and a perspective floor keep every station visible.
    poly([[100,125],[860,125],[860,300],[100,300]],room.wall);
    poly([[100,125],[65,155],[65,340],[100,300]],"#94afa3");
    poly([[100,300],[860,300],[925,570],[35,570]],room.floor);
    poly([[35,570],[925,570],[925,585],[35,585]],"#a18d78");
    line([[100,300],[860,300]],"#fff2d4",10);
    for(let y=325;y<570;y+=30)line([[100-(y-300)*.24,y],[860+(y-300)*.24,y]],"#ffffff24",2);
    for(let x=145;x<860;x+=75)line([[x,300],[480+(x-480)*1.17,570]],"#8d77651c",2);
    // Windows overlook the island; shelves and framed art make the rooms lived in.
    for(const x of [315,585]){
      rect(x-54,150,108,102,"#ffefcd",7);rect(x-46,158,92,85,current===3||current===5||r.values.sceneMood==="Evening"?"#657a9e":"#a7dbdc",3);
      ellipse(x-15,230,43,18,"#9cbe91");ellipse(x+25,235,40,19,"#84aa82");ellipse(x+20,178,10,10,current===5?"#fff0bf":"#fff2c7");
      if(r.values.sceneMood==="Rainy afternoon")for(let drop=0;drop<12;drop++){const dx=x-38+(drop*23)%77,dy=166+(drop*19)%65;line([[dx,dy],[dx-3,dy+8]],"#edf8f4",2);}
      line([[x,157],[x,242]],"#fff3d5",5);line([[x-46,200],[x+46,200]],"#fff3d5",5);rect(x-60,244,120,9,"#fff1d3",3);
    }
    rect(418,120,124,62,room.accent,8);text(["Story festival","Cocoa & company","Lake explorers","Tonight: your show","Grow together","Look to the stars"][current],480,146,13,"#fff9e8");text(["Make a little magic","Made with a little care","Observe • learn • release","Music brings us together","A seed is a beginning","Every clue tells a story"][current],480,165,9,"#fff9e8");
    line([[110,138],[300,145],[480,152],[660,145],[850,138]],"#6a8173",2);
    for(let n=0;n<16;n++)ellipse(125+n*47,142+Math.sin(n/15*Math.PI)*14,4,6,n%2?"#fff0b4":"#f5c7a0");
    // Each room's rug and furniture share its own palette.
    ellipse(480,440,224,83,current===3?"#c1b4d5":"#ffffff21");
    if(current===3){const tint=r.values.light==="Blue"?"#9fdbdf":r.values.light==="Gold"?"#f4d592":"#d5b7df";poly([[210,155],[110,550],[410,550]],tint+"33");poly([[740,155],[520,550],[850,550]],tint+"33");}
    // Room-specific furnishings sit behind the walkable stations.
    if(current===0||current===3){
      for(const x of [112,827]){rect(x,165,22,136,current===3?"#84739e":"#ce9b82",3);for(let n=0;n<3;n++)line([[x+4+n*6,168],[x+4+n*6,295]],"#ffffff20",2);}
    }
    if(current===1){
      rect(122,166,100,67,"#69867b",6);text("Today's menu",172,185,12,"#fff5d8");text("Cocoa · Tea · Milk",172,203,9,"#fff5d8");text("Made to order",172,219,9,"#fff5d8");
      rect(777,414,53,70,"#c79383",10);rect(771,465,65,19,"#e4b6a1",7);
    }
    if(current===2){line([[132,155],[227,155]],"#a89170",6);ellipse(795,204,24,27,"#f4d3a0");ellipse(795,204,13,16,room.wall);}
    if(current===4){for(let x=120;x<850;x+=90){line([[x,130],[x,165]],"#809b7b",2);plant(x,192,true);}}
    if(current===5){line([[100,126],[860,126]],"#9a826b",15);for(let x=135;x<850;x+=65)text("✦",x,145+(x%3)*20,12,"#fff0c8");}
    const objects=room.stations.map(s=>({y:s[3],paint:()=>{
      const [id,name,x,y,kind]=s,isGoal=r.step<5&&id===stationSequence[current][r.step];
      ellipse(x+6,y+9,64,15,"#344e431c");
      if(["counter","desk","table","machine","dj","planter","sink"].includes(kind)){
        for(const dx of [-45,45])rect(x+dx-3,y-12,7,27,"#987756",2);
        rect(x-62,y-40,124,36,"#b68b62",5);poly([[x-62,y-40],[x-48,y-58],[x+74,y-58],[x+62,y-40]],"#eed9b5");
      }
      if(kind==="counter"){rect(x-45,y-87,39,33,"#648a83",5);rect(x-39,y-81,27,17,"#cbe3cb",2);text("ORDER",x+31,y-57,10);cup(x+30,y-42);}
      if(kind==="desk"){poly([[x-37,y-58],[x+4,y-60],[x+9,y-43],[x-32,y-42]],"#fff5d9");line([[x-28,y-52],[x-3,y-52]],"#99ad9f",2);line([[x-27,y-47],[x-8,y-47]],"#99ad9f",2);cup(x+37,y-45,"#b2c7b1");}
      if(kind==="table"){cup(x-17,y-48);cup(x+18,y-48);rect(x-39,y+19,28,11,"#bf9573",4);plant(x+45,y-48,current===4&&r.step>=4);}
      if(kind==="machine"){rect(x-42,y-113,85,65,current===3?"#576b85":"#679793",9);rect(x-35,y-105,70,20,"#d6e6d9",4);for(let n=0;n<3;n++)ellipse(x-22+n*23,y-77,5,5,["#ebc78f","#d9e8d1","#efb4a4"][n]);cup(x,y-47);}
      if(kind==="dj"){rect(x-55,y-83,110,34,"#475f74",5);ellipse(x-27,y-67,20,10,"#233a4e");ellipse(x+27,y-67,20,10,"#233a4e");ellipse(x-27,y-67,5,3,"#e7b3cb");ellipse(x+27,y-67,5,3,"#9ad4d3");}
      if(kind==="planter"){rect(x-50,y-69,100,24,"#a78054",5);for(let n=0;n<3;n++)plant(x-30+n*32,y-55,r.step>=4);}
      if(kind==="sink"){ellipse(x,y-48,35,10,"#8db6b6");ellipse(x,y-49,28,7,"#bddbd4");line([[x+38,y-54],[x+38,y-86],[x+17,y-86],[x+17,y-77]],"#6d9696",5);}
      if(kind==="shelf"||kind==="wardrobe"){
        rect(x-63,y-125,126,124,"#a88363",7);rect(x-55,y-116,110,108,"#dfc5a1",2);
        if(kind==="shelf")for(let row=0;row<3;row++){rect(x-55,y-27-row*33,110,7,"#a88363",2);for(let n=0;n<5;n++){rect(x-47+n*21,y-46-row*33,14,20,["#a3baa0","#d7a490","#9abfc1","#e6ce8d","#b6a8c8"][n],3);rect(x-47+n*21,y-49-row*33,14,4,"#fff1cd",1);}}
        else {line([[x-48,y-95],[x+48,y-95]],"#765f52",4);for(let n=0;n<3;n++){const xx=x-34+n*34;line([[xx,y-95],[xx,y-83]],"#e9d9b7",3);poly([[xx-12,y-81],[xx+12,y-81],[xx+16,y-24],[xx-16,y-24]],["#8cbabc","#dfb08e","#b6a1cc"][n]);}}
      }
      if(kind==="board"){rect(x-58,y-133,116,100,"#a88259",7);rect(x-50,y-125,100,83,"#f2e5c4",3);line([[x-37,y-101],[x-8,y-81],[x+18,y-107],[x+36,y-66]],"#91b4a0",3);for(const dx of [-51,51])rect(x+dx,y-34,6,39,"#947754",2);text(current===5?"★  ≈  ☾":"Our next adventure",x,y-116,11);}
      if(kind==="stage"){poly([[x-93,y-34],[x+80,y-34],[x+103,y+16],[x-105,y+16]],current===3?"#a59ac4":"#c7a27b");for(let a=0;a<4;a++)for(let b=0;b<2;b++)rect(x-79+a*41,y-22+b*16,37,13,["#dfc1c8","#a8d1cc","#f1d899","#bbb0d7"][(a+b)%4],2);line([[x+70,y-10],[x+70,y-90]],"#465b63",4);ellipse(x+70,y-92,8,11,"#536f78");}
      if(kind==="tank"){rect(x-62,y-91,124,83,"#88bdc3",8);rect(x-55,y-84,110,66,"#b7e6df",3);rect(x-62,y-12,124,14,"#a08360",3);for(let n=0;n<3;n++){ellipse(x-30+n*31,y-47+n%2*15,12,6,"#e2ddac");poly([[x-18+n*31,y-47+n%2*15],[x-9+n*31,y-53+n%2*15],[x-9+n*31,y-41+n%2*15]],"#7daacb");}}
      if(kind==="pier"){ellipse(x,y-8,90,49,"#8acbd1");for(let n=0;n<5;n++)rect(x-80+n*25,y-25,21,43,"#c4a47c",2);line([[x-18,y-17],[x+15,y-112],[x+65,y-61],[x+65,y-10]],"#6b7e75",3);ellipse(x+65,y-7,5,7,"#edab92");}
      if(kind==="scope"){line([[x,y-49],[x-31,y+8]],"#987d60",6);line([[x,y-49],[x+32,y+8]],"#987d60",6);g.save();g.translate(x,y-68);g.rotate(-.5);rect(-39,-16,85,31,"#688f9f",6);rect(36,-21,13,41,"#cedfda",3);g.restore();}
      if(kind==="beacon"){rect(x-28,y-15,56,26,"#aa8e6e",5);rect(x-24,y-104,48,88,"#58778b",6);rect(x-17,y-95,34,61,r.step>=4?"#a5e0ec":"#d1dfd9",5);poly([[x-32,y-104],[x,y-131],[x+32,y-104]],"#698ca2");}
      if(isGoal){ellipse(x+60,y-111,12,12,"#fff1b4");text("!",x+60,y-106,15,"#87703b");}
      const labelWidth=Math.min(170,name.length*7+18);rect(x-labelWidth/2,y+22,labelWidth,23,selected===s?"#315f61":"#fff9e9",11);text(name,x,y+38,11,selected===s?"#fff9e9":"#365452");
    }}));
    // Story characters stay in the room while you move between stations.
    const npc=(x,y,color,name)=>({y,paint:()=>{
      ellipse(x,y,16,6,"#45614b25");ellipse(x,y-23,18,24,color);ellipse(x,y-17,11,12,"#fff0d1");
      ellipse(x-6,y-31,2,3,"#405957");ellipse(x+6,y-31,2,3,"#405957");ellipse(x,y-25,4,2,"#cc956d");
      text(name,x,y-55,11);
    }});
    objects.push(npc(current===1?784:150,current===1?479:433,["#e5bb81","#b5c5d9","#92bbba","#c3b2d5","#b6c78c","#e3bd91"][current],current===1?orders[r.round].who:["Pip","","Skipper","Nova","Fern","Scout"][current]));
    objects.push({y:at.y,paint:()=>{
      ellipse(at.x,at.y,22,8,"#304e4330");pup.draw(g,0,{},at.x,at.y,{flip:target.x<at.x});
      if(current===1&&r.step>=2&&r.step<=3)cup(at.x+24,at.y-23);
      if(r.values.storyProp){
        if(r.values.storyProp==="Festival bouquet")plant(at.x+28,at.y-8,true);
        else {rect(at.x+18,at.y-28,23,21,room.accent,4);text("★",at.x+29,at.y-12,13,"#fff0bd");}
      }
      if(r.values.outfit){rect(at.x-18,at.y-32,36,5,room.accent,2);}
    }});
    objects.sort((a,b)=>a.y-b.y).forEach(o=>o.paint());
    plant(130,550,current===4);plant(837,545,current===4);
    rect(100,551,110,26,"#fff3d4",10);text("↙ Outside",155,569,12);
    if(speech&&now<speechUntil){const w=Math.min(520,speech.length*7+30);rect(480-w/2,60,w,40,"#fff9e9",15);text(speech.length>67?speech.slice(0,64)+"…":speech,480,85,13);}
    g.restore();
  }
  function setup(){
    $("islandExit").onclick=leave;
    addEventListener("keydown",e=>{if(current>=0&&e.key==="Escape"){e.preventDefault();leave();}});
    $("interiorLineForm").onsubmit=e=>{e.preventDefault();if(current<0)return;const words=$("interiorLine").value.trim().slice(0,80);if(!words)return;say(words);commit(task().role+": "+words);$("interiorLine").value="";$("islandCanvas").focus();};
    $("interiorProps").onclick=()=>choice("Choose a story prop",state.inventory.length?"Carry something from your adventures into this scene.":"Complete a scenario to earn a prop for your backpack.",state.inventory.length?state.inventory.map(prop=>[prop,()=>{task().values.storyProp=prop;commit(task().role+" brought a "+prop.toLowerCase()+" into the scene.");api.dismiss();}]):[["Back to the room",api.dismiss]]);
    $("interiorMood").onclick=()=>choice("Set the scene","Choose the time or weather for your story.",["Sunny morning","Rainy afternoon","Evening"].map(mood=>[mood,()=>{task().values.sceneMood=mood;commit("Scene: "+mood+".");api.dismiss();}]));
    $("interiorReplay").onclick=()=>{const role=task().role;state.rooms[current]={step:0,round:0,role,values:{}};commit("Started a new "+rooms[current].name+" scenario.");api.dismiss();};
    $("interiorTalk").onclick=()=>choice("Your next line","Choose a line to act out with the room's props.",["Welcome! How can I help?","Let's solve this together!","Something unexpected just happened!","It's time to celebrate!"].map(words=>[words,()=>{say(words);commit(task().role+": "+words);api.dismiss();}]));
  }
  setup();return {get active(){return current>=0;},clean,enter,leave,draw,key,click,interact};
})();
