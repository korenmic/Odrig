
(() => {
  const root=document.getElementById('ntt-preview');
  const out=root.querySelector('#ntt-led'), screen=out.getContext('2d');
  const tiny=document.createElement('canvas'); tiny.width=tiny.height=60;
  const c=tiny.getContext('2d',{willReadFrequently:true});
  const select=root.querySelector('#ntt-scene'), pause=root.querySelector('#ntt-pause');
  const caption=root.querySelector('#ntt-caption');
  const descriptions=[
    'המחוג הלבן מתקדם בקצב קבוע; התכלת מאיץ, כמעט נעצר ואז משיג אותו. מחזור הדגמה: 18 שניות.',
    'הספירה יורדת מ־10 עד 01. דווקא השנייה האחרונה נתקעת, מתחרטת וחוזרת אחורה. אפס לא מגיע.',
    'החול עולה דרך הצוואר וממלא מחדש את החלק העליון. אחרי ההתרוקנות, התנועה מתהפכת שוב.',
    'הנקודה נעה במסלול, נעצרת וחוזרת לאחור. באותו מקום נשאר הד חלש מהסיבוב הקודם.',
    'החלק העליון מתקדם, האמצע מתעכב והתחתון חוזר אחורה. פעם במחזור השעון מתאחד מחדש.',
    'שעון מוכר מתחיל להתרכך, להתארך ולטפטף. המחוג ממשיך לנוע גם כשהמסגרת מאבדת צורה.'
  ];
  const colors={white:'#d6e3e8',cyan:'#51e6df',pink:'#ef80bd',amber:'#ffc577',dim:'#354953'};
  let scene=0, elapsed=0, paused=matchMedia('(prefers-reduced-motion: reduce)').matches;
  let last=performance.now();
  const tau=Math.PI*2;
  function stroke(points,color,w=1){c.strokeStyle=color;c.lineWidth=w;c.lineCap='round';c.lineJoin='round';c.beginPath();points.forEach((p,i)=>i?c.lineTo(...p):c.moveTo(...p));c.stroke();}
  function dot(x,y,color,r=1){c.fillStyle=color;c.beginPath();c.arc(x,y,r,0,tau);c.fill();}
  function hand(a,r,color,cx=29.5,cy=29.5){stroke([[cx,cy],[cx+Math.sin(a)*r,cy-Math.cos(a)*r]],color,1.3);}
  function face(){for(let i=0;i<60;i++){const a=i*tau/60;dot(29.5+25*Math.sin(a),29.5-25*Math.cos(a),i%5===0?colors.white:colors.dim,i%5===0?.65:.3);}}
  const digits={0:['111','101','101','101','111'],1:['010','110','010','010','111'],2:['111','001','111','100','111'],3:['111','001','111','001','111'],4:['101','101','111','001','001'],5:['111','100','111','001','111'],6:['111','100','111','101','111'],7:['111','001','010','010','010'],8:['111','101','111','101','111'],9:['111','101','111','001','111']};
  function number(s,x,y,scale,color){c.fillStyle=color;[...s].forEach((ch,j)=>digits[ch].forEach((row,k)=>[...row].forEach((on,i)=>{if(on==='1')c.fillRect(x+(j*4+i)*scale,y+k*scale,scale-.3,scale-.3)})));}
  function clocks(t){face();const a=t*tau/18,b=a-.91*Math.sin(a);hand(a,22,colors.white);hand(b,19,colors.cyan);dot(29.5,29.5,colors.white,1.5);}
  function countdown(t){const q=t%16;const n=q<10?10-Math.floor(q):[1,1,2,1,3,1][Math.floor(q-10)];number(String(n).padStart(2,'0'),9,15,6,q<10?colors.white:colors.amber);const f=q<10?(q%1):((q-10)/6);stroke([[8,52],[52,52]],colors.dim,.7);stroke([[8,52],[8+44*f,52]],colors.cyan,1.2);}
  function sand(t){
    const q=t%16,up=q<8,u=up?q/8:1-(q-8)/8;
    stroke([[11,6],[49,6]],colors.white,1.7);stroke([[11,54],[49,54]],colors.white,1.7);
    stroke([[13,7],[14,15],[27,29],[27,31],[14,45],[13,53]],colors.dim,1.2);
    stroke([[47,7],[46,15],[33,29],[33,31],[46,45],[47,53]],colors.dim,1.2);
    for(let y=10;y<29;y++)for(let x=14;x<47;x++){
      if(Math.abs(x-30)<(29-y)*.8 && y>28-18*u)dot(x,y,colors.amber,.42);
    }
    for(let y=33;y<52;y++)for(let x=14;x<47;x++){
      if(Math.abs(x-30)<(y-31)*.86 && y>32+19*u)dot(x,y,colors.cyan,.42);
    }
    for(let i=0;i<13;i++){const k=(t*11+i*3.73)%38;dot(30+Math.sin(i*9)*.7,up?49-k:11+k,up?colors.cyan:colors.amber,.6);}
  }
  function deja(t){
    const q=t%10;let u=q<6?q/6:q<7?1:q<9?1-(q-7)/2:0;
    function pos(v){return [8+44*v,30+14*Math.sin(v*tau)];}
    const path=[];for(let i=0;i<=100;i++)path.push(pos(i/100));stroke(path,colors.dim,.5);
    for(let j=1;j<9;j++){c.globalAlpha=(1-j/9)*.45;const v=Math.max(0,Math.min(1,u-(q>=7&&q<9?-1:1)*j*.026));dot(...pos(v),colors.cyan,1.7);}
    c.globalAlpha=1;dot(...pos(u),q>=7&&q<9?colors.pink:colors.white,2.2);
    c.globalAlpha=.45;dot(...pos(Math.min(1,(q/6)%1)),colors.amber,.8);c.globalAlpha=1;
  }
  function slices(t){
    const strength=(1-Math.cos(t*tau/16))/2;
    for(let band=0;band<6;band++){
      c.save();c.beginPath();c.rect(0,band*10,60,10);c.clip();
      c.translate(Math.sin(band*1.7+t)*strength*2.5,0);face();
      hand(t*tau/18+strength*(band-2.5)*.85,22,band<2?colors.white:band<4?colors.cyan:colors.pink);
      hand(t*tau/90+strength*(band-2.5)*.3,12,colors.white);c.restore();
    }
  }
  function melt(t){
    const k=(1-Math.cos(t*tau/18))/2;
    function warp(x,y){const lower=Math.max(0,(y-22)/30);return[x+k*Math.sin(y*.16)*lower*3,y+k*lower*lower*(4+3*Math.sin(x*.37))];}
    const ring=[];for(let i=0;i<=160;i++){const a=i*tau/160;ring.push(warp(29.5+23*Math.sin(a),26-21*Math.cos(a)));}stroke(ring,colors.cyan,1);
    for(let i=0;i<12;i++){const a=i*tau/12;dot(...warp(29.5+20*Math.sin(a),26-18*Math.cos(a)),colors.white,.65);}
    for(const [r,a,col] of [[18,t*tau/18,colors.white],[11,t*tau/90,colors.amber]]){
      const pts=[];for(let j=0;j<=30;j++)pts.push(warp(29.5+Math.sin(a)*r*j/30,26-Math.cos(a)*r*j/30));stroke(pts,col,1.2);
    }
    if(k>.25)for(let i=0;i<3;i++){const y=48+((t*2+i*3)%10);c.globalAlpha=k*(58-y)/10;dot(20+i*10,y,colors.cyan,.7);}c.globalAlpha=1;
  }
  const draws=[clocks,countdown,sand,deja,slices,melt];
  function render(){
    c.fillStyle='#040609';c.fillRect(0,0,60,60);draws[scene](elapsed);
    const d=c.getImageData(0,0,60,60).data;
    screen.fillStyle='#040609';screen.fillRect(0,0,600,600);
    for(let y=0;y<60;y++)for(let x=0;x<60;x++){const i=(y*60+x)*4;screen.fillStyle=`rgb(${d[i]},${d[i+1]},${d[i+2]})`;screen.beginPath();screen.arc(x*10+5,y*10+5,3.5,0,tau);screen.fill();}
  }
  function update(){caption.textContent=descriptions[scene];out.setAttribute('aria-label',descriptions[scene]);render();}
  function syncPause(){pause.textContent=paused?'הפעלה':'השהיה';pause.setAttribute('aria-pressed',String(paused));}
  select.addEventListener('change',()=>{scene=Number(select.value);elapsed=0;update();});
  pause.addEventListener('click',()=>{paused=!paused;syncPause();});
  update();syncPause();
  let drawn=0;
  function loop(now){const dt=Math.min((now-last)/1000,.1);last=now;if(!paused&&!document.hidden){elapsed+=dt;if(now-drawn>40){render();drawn=now;}}requestAnimationFrame(loop);}
  requestAnimationFrame(loop);
})();
