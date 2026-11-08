const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../../app/www/client.js'), 'utf8');
function body(name, required = true) {
  const match = source.match(new RegExp('(?:async )?function ' + name + '\\([^]*?\\n}'));
  if (!match && required) throw Error(name + ' missing');
  return match?.[0] ?? '';
}
const context = vm.createContext({console});
vm.runInContext(`
let target = 0, connectionDue = false, onlyActive = false, onlyFolder = null, onlyDesired = 'clocks';
let statusTimer = null, statusDue = false;
const trail = [], paths = [];
let listing = null, ordering = null, orderDue = false, listDue = false, askedFor = null;
const STATUS_EVERY_MS = 1000, LIST_WHEN_BUSY_MS = 1000;
const state = {link:'answers', statusFresh:true, statusCount:0, onlyUnavailable:false,
  level:{path:'', id:null}, animations:[], folders:[], cycles:[], orderVersion:0};
let mode = 'only';
const commands = {
  status: async () => ({clockMode:mode, clockOnly:{folder:${process.argv[2] === 'initial' ? 'null' : '60002'}}, animation:null, playing:null}),
  list: async () => ({items:[], next:null}),
  catalog: async () => {
    if (${JSON.stringify(process.argv[2])} === 'busy') throw new commands.Refusal('busy');
    return {external:{state:${JSON.stringify(['damaged', 'loading'].includes(process.argv[2]) ? process.argv[2] : 'absent')}}};
  },
  Refusal: class extends Error { constructor(code) { super(code); this.code = code; } },
};
function heard() { state.link = 'answers'; }
function changed() { paths.push(state.level.path); }
function next() {}
function clearTimeout() {}
function setTimeout() { return 1; }
function listAgainLater() {}
function parentOf(value) { return value.slice(0, value.lastIndexOf('/')); }
${['inClocks', 'unavailableClocks', 'reconcileOnly', 'takeStatus'].map(name => body(name, false)).join('\n')}
${['askStatus', 'recoverLevel', 'toLevel'].map(name => body(name)).join('\n')}
`, context);
(async () => {
  const result = await vm.runInContext(`(async () => {
    await askStatus();
    if (${JSON.stringify(process.argv[2])} !== 'initial') await recoverLevel(target, state.level);
    if (${JSON.stringify(process.argv[2])} === 'unknown') mode = null;
    await askStatus();
    return {paths, level:state.level, unavailable:state.onlyUnavailable};
  })()`, context);
  console.log(JSON.stringify(result));
  if (result.paths.includes('') || result.level.path !== 'clocks' ||
      result.level.id !== null || !result.unavailable) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
