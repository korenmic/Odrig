const fs=require('fs'); const vm=require('vm');
const source=fs.readFileSync('app/www/client.js','utf8');
function actual(name){
  const match=source.match(new RegExp('(?:async )?function '+name+'\\([^]*?\\n}'));
  if(!match)throw Error(name); return match[0];
}
const context=vm.createContext({console});
vm.runInContext(`
let target=0, onlyOpened=false, connectionDue=false, statusTimer=null, statusDue=false;
let trail=[], listing=null, ordering=null, orderDue=false, listDue=false, askedFor=null;
let spaceDue=false,catalogDue=false,pageWait=null; const reads=[];
const STATUS_EVERY_MS=1000,LIST_WHEN_BUSY_MS=1000;
const state={link:'answers',statusFresh:true,statusCount:0,connectionVersion:1,
 level:{path:'',id:null},animations:[],folders:[],cycles:[],orderVersion:0,
 keys:{internal:{revision:'same-internal'},external:{revision:'same-external'}},keysVersion:0,
 catalogNone:false,pagesRefused:false};
const commands={status:async()=>({clockMode:'only',clockOnly:{folder:60002},animation:null,playing:null}),
 list:async()=>({items:[],next:null}),catalog:async()=>({external:{state:'absent'}})};
function changed(){} function next(){} function clearTimeout(){} function setTimeout(){return 1;}
function listAgainLater(){} function parentOf(s){return s.slice(0,s.lastIndexOf('/'));}
${['dropKeys','heard','askStatus','recoverLevel','toLevel'].map(actual).join('\n')}
`,context);
(async()=>{
 const result=await vm.runInContext(`(async()=>{
   await askStatus(); const initial={path:state.level.path,onlyOpened};
   await recoverLevel(target,state.level); await askStatus();
   const recovery={path:state.level.path,clockMode:state.status.clockMode,onlyOpened,animations:state.animations};
   state.link='no-answer'; listDue=false; catalogDue=false;
   const keysBefore=state.keys;heard();
   return {initial,recovery,reconnect:{keysBefore,keysAfter:state.keys,listDue,catalogDue,keysVersion:state.keysVersion}};
 })()`,context);
 if(result.initial.path!=='clocks'||result.recovery.path!==''||result.recovery.clockMode!=='only')throw Error('not reproduced');
 if(!result.reconnect.listDue||result.reconnect.keysAfter.internal!==null)throw Error('refresh not reproduced');
 fs.writeFileSync('build/seed67-app-reproduction.json',JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify(result,null,2));
})().catch(error=>{console.error(error);process.exitCode=1});
