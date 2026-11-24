export const withoutTheApp = true;

export default async function(app) {
  const sent = [];
  let mode = 'only';
  window.Capacitor = {
    isNativePlatform: () => true,
    nativePromise: async (_plugin, _method, request) => {
      const line = request.line;
      sent.push(line);
      let answer;
      if (line === 'status') answer = {ok:true, on:true, brightness:40,
        playing:60007, animation:null, fps:50, error:null, clocks:mode !== 'off',
        clock_mode:mode, clock_only:mode === 'only' ? {folder:60007,state:'playing'} : null};
      else if (line.startsWith('list')) answer = {ok:true, items:line.startsWith('list in') ?
        [{id:60003,file:'clocks/c.odrg',bytes:100,external:true}] :
        [{id:60007,playlist:'clocks',files:1,external:true}],next:null};
      else if (line === 'catalog') answer = {ok:true,internal:{state:'none',uncataloged:0},external:{state:'none'},rebuild:null};
      else if (line.startsWith('upload begin')) {
        if (app.settings.case === 'upload-race') {mode='only';await app.sleep(1100);}
        answer={ok:true,chunk:1500,replacing:false};
      } else if (line.startsWith('upload data')) answer={ok:true,received:4};
      else if (line.startsWith('upload end') || line === 'upload cancel') answer={ok:true};
      else if (line === 'space') answer={ok:true,free:1000,total:2000};
      else answer={ok:false,error:'unknown-command'};
      return {status:200,body:JSON.stringify(answer)};
    },
  };
  const client=await import('/client.js');
  client.showing('animations');client.keptKeysReady();client.begin();
  await app.until(() => client.state.status?.clockMode === 'only' && client.state.animations?.length === 1,'confirmed Only');
  if (['upload-snapshot','upload-snapshot-race'].includes(app.settings.case)) {
    if (app.settings.case === 'upload-snapshot-race') {
      mode='off';await app.until(() => client.state.status?.clockMode === 'off','confirmed Off');mode='only';
    }
    let error=null;
    try {await client.uploadSnapshot({path:'',id:null});} catch(caught) {error=caught.code ?? caught.message;}
    return {error,mode:client.state.status.clockMode};
  }
  if (app.settings.case === 'upload-race') {
    mode='off';await app.until(() => client.state.status?.clockMode === 'off','confirmed Off');
  }
  const upload=await import('/upload.js');let ended=null;
  client.upload(upload.uploading({id:2,file:'outside.odrg',bytes:new Uint8Array([1,2,3,4]),create:true},
    {report(){},end(how){ended=how;},wake:client.wake}));
  await app.until(() => ended !== null,'root upload ends');
  return {begins:sent.filter(line => line.startsWith('upload begin')).length,
    ends:sent.filter(line => line.startsWith('upload end')).length,
    cancels:sent.filter(line => line === 'upload cancel').length,error:ended.error?.code ?? null,done:ended.done === true};
}
