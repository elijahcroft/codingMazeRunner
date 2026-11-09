// Run with: node test_pixel_interiors.js
// Exercise room scenarios, recovery, rendering and save migration without a server.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor() { this.hidden=true; this.children=[]; this.dataset={}; this.classList={toggle(){}}; }
  replaceChildren(...children) { this.children=children; }
  setAttribute() {}
  focus() {}
}
const elements=new Map();
const $=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
let time=10000;
const context=vm.createContext({$,performance:{now:()=>time},addEventListener(){},document:{createElement:()=>new Element(),querySelectorAll:()=>$('interiorStations').children}});
vm.runInContext(fs.readFileSync(__dirname+'/pixel_interiors.js','utf8')+'\nglobalThis.roomsApi=PixelInteriors;',context);
const rooms=context.roomsApi;
const save={adventure:rooms.clean(null),stars:[],flower:null};
let menu=[],awards=[],title='';
const api={save,persist(){},reward(i){awards.push(i);},panel(t,d,choices){title=t;menu=choices;$('islandActivity').hidden=false;},dismiss(){$('islandActivity').hidden=true;menu=[];},onExit(){}};
const g=new Proxy({roundRect(x,y,w,h,r){assert.equal(typeof r,'number','roundRect radius must be numeric');}},{get:(o,k)=>k in o?o[k]:()=>{}});
function station(id) {
  const button=$('interiorStations').children.find(b=>b.dataset.station===id);
  assert.ok(button,'Missing station '+id);button.onclick();
  for(let n=0;n<120;n++){time+=50;rooms.draw(g,{width:960,height:610},.05,time,{draw(){}});}
  assert.ok(menu.length,'No activity at '+id);
}
function choose(label){const b=menu.find(([text])=>text===label);assert.ok(b,`Missing choice ${label} in ${title}: ${menu.map(x=>x[0])}`);b[1]();}
function enter(i){rooms.leave();rooms.enter(i,api);}
function step(i){return save.adventure.rooms[i].step;}
// A full three-customer café shift, including recovery from a wrong recipe.
enter(1);
const orders=[['Cocoa','Marshmallows'],['Tea','Honey'],['Milk','Cinnamon']];
for(let i=0;i<3;i++){
  station('till');choose('Write down the order');station('pantry');
  if(i===0){choose('Tea');choose('Honey');station('brew');choose('Brew and stir');assert.equal(step(1),1);choose('Back to the shelf');for(let n=0;n<120;n++)rooms.draw(g,{width:960,height:610},.05,time+=50,{draw(){}});}
  choose(orders[i][0]);choose(orders[i][1]);station('brew');choose('Brew and stir');station('table');choose('Serve with a friendly greeting');station('sink');choose('Wash and rinse');choose('Put it away');
}
assert.equal(step(1),5);assert.ok(save.adventure.inventory.includes('Café picnic'));
enter(0);station('board');choose('Space rescue');station('costume');choose('Star cape');station('desk');choose('The café crew');station('stage');choose('A visitor needs our help!');station('board');choose('Welcome everyone to the festival');
enter(2);station('map');choose('Pack my field guide');station('bait');choose('Seeds');assert.equal(step(2),1);choose('Choose again');choose('Worms');station('pier');choose('Cast line');choose('Reel in');assert.equal(step(2),2);time+=2200;choose('Reel in');station('tank');choose('Silverfin');station('log');choose('Record and release');
enter(3);station('dj');choose('Ocean groove');station('lights');choose('Pink');assert.equal(step(3),1);choose('Blue');station('costume');choose('Sparkle jacket');station('stage');for(const move of ['Step','Spin','Clap','Step'])choose(move);station('dj');choose('Start the performance');
enter(4);station('seeds');choose('Sunflower');station('pot');choose('Fill with soil');choose('Plant the seed');station('water');choose('1 scoop');assert.equal(step(4),2);choose('2 scoops');station('sun');choose('Set it beside the window');station('bouquet');choose('Gold ribbon');
enter(5);station('map');choose('Copy the symbols');station('books');choose('South');assert.equal(step(5),1);choose('North');station('scope');choose('Moon constellation');station('bench');choose('Blue lens');station('beacon');choose('Light the lantern');
assert.equal(awards.length,6);assert.equal(save.adventure.inventory.length,6);
// Save/restore keeps completed work and role-play settings; replay resets only one room.
$('interiorMood').onclick();choose('Rainy afternoon');$('interiorProps').onclick();choose('Festival bouquet');
const restored=rooms.clean(JSON.parse(JSON.stringify(save.adventure)));
assert.equal(restored.rooms[5].values.sceneMood,'Rainy afternoon');assert.equal(restored.rooms[5].values.storyProp,'Festival bouquet');assert.equal(restored.rooms[1].step,5);
$('interiorReplay').onclick();assert.equal(step(5),0);assert.equal(step(1),5);assert.equal(save.adventure.inventory.length,6);
rooms.leave();assert.equal(rooms.active,false);
const corrupt=rooms.clean({rooms:[{step:99,round:-1,role:'unknown',values:{theme:'x'.repeat(200)}}],inventory:['bogus','Café picnic','Café picnic'],journal:['ok',null,44]});
assert.equal(corrupt.rooms[0].step,0);assert.equal(corrupt.rooms[0].round,0);assert.equal(corrupt.inventory.length,1);assert.equal(corrupt.journal.length,1);
console.log('Passed: all six scenarios, wrong-choice recovery, three café customers, room rendering, save migration, role play, replay and exits.');
