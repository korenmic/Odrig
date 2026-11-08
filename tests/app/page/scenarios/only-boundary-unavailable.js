export const withoutTheApp = true;

export default async function(app) {
  let missing = false;
  let attempts = 0;
  window.Capacitor = {
    isNativePlatform: () => true,
    nativePromise: async (_plugin, _method, request) => {
      const line = request.line;
      let answer;
      if (line === 'status') answer = {ok:true,on:true,brightness:40,playing:60007,
        animation:null,fps:50,error:null,clocks:true,clock_mode:'only',
        clock_only:{folder:60007,state:'playing'}};
      else if (line.startsWith('list in')) {
        if (missing) {
          attempts++;
          answer = {ok:false,error:attempts > 5 ? 'busy' : 'unknown-id'};
        } else answer = {ok:true,items:[{id:60003,file:'clocks/c.odrg',bytes:100,external:true}],next:null};
      } else if (line.startsWith('list')) answer = {ok:true,items:[],next:null};
      else if (line === 'catalog') answer = {ok:true,internal:{state:'none',uncataloged:0},external:{state:'absent'},rebuild:null};
      else if (line === 'space') answer = {ok:true,free:1000,total:2000};
      else answer = {ok:false,error:'unknown-command'};
      return {status:200,body:JSON.stringify(answer)};
    },
  };
  const client = await import('/client.js');
  client.showing('animations');client.keptKeysReady();client.begin();
  await app.until(() => client.state.animations?.length === 1,'initial Clocks list');
  missing = true;
  client.refreshContent();
  await app.sleep(200);
  return {path:client.state.level.path,id:client.state.level.id,attempts};
}
