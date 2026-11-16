// Local DOM stubs test integration and interactions without a browser or network.
// This does not verify CSS layout, browser accessibility or visual rendering.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('web/index.html','utf8'),ids=[...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
assert.equal(new Set(ids).size,ids.length,'Duplicate HTML ids');
function el(id,value=''){return {id,value,innerHTML:'',textContent:'',hidden:false,dataset:{},handlers:{},classList:{toggle(){}},setAttribute(){},addEventListener(k,f){this.handlers[k]=f;}};}
const elements=new Map(ids.map(id=>[id,el(id)]));elements.set('main',el('main'));
elements.get('day-select').value='latest';elements.get('energy').value='20';elements.get('cap').value='5';
const buttons=['forecast','performance','method'].map(id=>{const e=el(id+'-tab');e.dataset.tab=id;return e;});
const document={querySelector:s=>{const key=s==='main'?'main':s.slice(1);assert(elements.has(key),'Unknown element '+s);return elements.get(key);},querySelectorAll:s=>s==='.tabs button'?buttons:s==='.view'?['forecast','performance','method'].map(id=>elements.get(id)):[],addEventListener:(event,fn)=>{if(event==='DOMContentLoaded')document.ready=fn;}};
const context={document,window:{},console,module:{exports:{}}};vm.createContext(context);
vm.runInContext(fs.readFileSync('dist/data.js','utf8'),context);
vm.runInContext(fs.readFileSync('web/app.js','utf8'),context);document.ready();
assert(elements.get('profile-chart').innerHTML.includes('<svg'));
assert(!elements.get('profile-chart').innerHTML.includes('NaN'));
assert(elements.get('performance-kpis').innerHTML.includes('MAE reduction'));
assert(elements.get('comparison-chart').innerHTML.includes('Ridge linear regression'));
assert(elements.get('revision-results').innerHTML.includes('not a fresh untouched test'));
assert(elements.get('monthly-eligibility').innerHTML.includes('2025-02'));
assert(elements.get('fold-table').innerHTML.includes('2026-10-01'));
buttons[1].handlers.click();assert.equal(elements.get('performance').hidden,false);assert.equal(elements.get('forecast').hidden,true);
buttons[2].handlers.click();assert.equal(elements.get('method').hidden,false);
elements.get('energy').value='0';elements.get('energy').handlers.input();assert(elements.get('scenario-result').innerHTML.includes('0.0 MWh'));
elements.get('day-select').value='2025-01-15';elements.get('day-select').handlers.change();assert(elements.get('day-note').textContent.includes('backtest'));assert(!elements.get('profile-chart').innerHTML.includes('NaN'));
for(const m of html.matchAll(/href="([^"]+)"/g)){const link=m[1];if(!link.startsWith('#')&&!link.startsWith('https:'))assert(fs.existsSync('dist/'+link),'Missing linked artifact '+link);}
console.log('PASS: dashboard initialization, SVG generation, tab switching, date selection, zero-energy slider, finite chart coordinates, unique IDs and local download targets. No browser/network used.');
