export const withoutTheApp = true;

// Keep the supplied page's layout, text rasterizer and animation code. Only its
// clock, random source and final decorative LED-dot canvas are instrumented.
export default async function(app) {
  const html = app.settings.html;
  const before = `
    window.__now=0; window.__capture=false; window.__rgb=new Uint8Array(10800);
    let rng=1, start=0;
    function random32(){rng^=rng<<13;rng^=rng>>>17;rng^=rng<<5;return rng>>>0;}
    window.__seed=(seed)=>{rng=seed||1;start=random32()%86400;};
    Math.random=()=>random32()/4294967296;
    window.Date=class {getHours(){return Math.floor(start/3600);}
      getMinutes(){return Math.floor(start/60)%60;} getSeconds(){return start%60;}};
    performance.now=()=>window.__now;
    requestAnimationFrame=(callback)=>{window.__frame=callback;return 1;};
    const original=HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext=function(...args){
      if(this.id!=='display')return original.apply(this,args);
      let at=0;
      return {fillStyle:'',fillRect(){},beginPath(){},
        arc(x,y){at=3*(Math.floor(y/15)*60+Math.floor(x/15));},
        fill(){if(!window.__capture)return;
          const c=this.fillStyle.match(/^rgba\\((\\d+),(\\d+),(\\d+),([\\d.eE+-]+)\\)$/);
          for(let i=0;i<3;i++)window.__rgb[at+i]=c?Math.round(Number(c[i+1])*Number(c[4])):0;
        }};
    };
  `;
  const after = `window.__review={reset(tab,seed){window.__seed(seed);reset();chooseSection(tab-1);},
    read(){return {section:section+1,index,elapsed,motionTime,stopAt,
      frozen:pendulumFrozenX,digits:clockDigits.slice(),caption:messageText(currentMessage())};}};`;
  const frame = app.frame;
  const ready = new Promise((resolve) => frame.addEventListener('load', resolve, {once:true}));
  frame.srcdoc = html.replace('<script>', `<script>${before}</script><script>`)
    .replace('</body>', `<script>${after}</script></body>`);
  document.body.append(frame);
  await ready;
  const w = frame.contentWindow, samples = [];
  for (const group of app.settings.groups) {
    w.__review.reset(group.tab, group.seed);
    w.__now=0; w.__frame(0);
    let now=0;
    for (const t of group.times) {
      while (now < t) {
        now=Math.min(t,now+20); w.__now=now;
        w.__capture=now===t; w.__frame(now);
      }
      if (t===0) {w.__capture=true;w.__frame(0);}
      let raw='';
      for(const value of w.__rgb)raw+=String.fromCharCode(value);
      samples.push({tab:group.tab,seed:group.seed,t,...w.__review.read(),rgb:btoa(raw)});
      w.__capture=false;
    }
  }
  return {samples};
}
