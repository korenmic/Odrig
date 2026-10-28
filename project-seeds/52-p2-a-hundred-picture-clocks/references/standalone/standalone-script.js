/* Time Isn’t the Time / זה לא הזמן
 * Offline animation demos, authored from public share's six presentation descriptions.
 * Deterministic 60x60 Canvas renderer, no external dependencies.
 * API: TimeAnimations.draw(ctx,sceneId,tSeconds), duration=18, 60x60 pixels.
 */
(function(global){
'use strict';
const W=60,H=60, DURATION=18, TAU=Math.PI*2;
const C={bg:'#050910',white:'#f1f5ff',muted:'#44617f',cyan:'#42e9ff',blue:'#4d85ff',violet:'#a68dff',pink:'#ff5dbd',gold:'#ffc95a',orange:'#ff8654',red:'#ff4667',green:'#65ffd4'};
const SCENES=[
  {id:'two_times',he:'אותה שנייה, שני זמנים',en:'The same second, two times',description:'Two hands begin together. The white hand advances regularly; the cyan hand nearly stops, accelerates and catches up.'},
  {id:'never_zero',he:'עוד שנייה זה קורה',en:'The countdown never reaches zero',description:'Countdown from 10 to 01; the last second stretches, glitches, jumps backwards to 02, and never reaches zero.'},
  {id:'reverse_hourglass',he:'החול חוזר למעלה',en:'Sand regrets / reverse hourglass',description:'Sand drains down through an hourglass, then reverses and climbs back into the upper chamber.'},
  {id:'we_were_here',he:'כבר היינו כאן',en:'We have been here before',description:'A bright dot traverses a path, halts, retraces it in reverse, and leaves faint ghosts of earlier loops.'},
  {id:'time_bands',he:'כל שורה בזמן אחר',en:'Each row has a different time',description:'The top band runs forward, the middle slows, and the bottom moves backwards; they briefly realign.'},
  {id:'melting_clock',he:'השעון נוזל',en:'The melting clock',description:'A clock face softens, stretches and drips while its hands keep moving.'}
];
function clamp(x,a=0,b=1){return Math.max(a,Math.min(b,x));}
function mix(a,b,u){return a+(b-a)*u;}
function fract(x){return x-Math.floor(x);}
function sstep(a,b,x){let t=clamp((x-a)/(b-a));return t*t*(3-2*t);}
function line(ctx,x1,y1,x2,y2,color,w=1){ctx.strokeStyle=color;ctx.lineWidth=w;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();}
function dot(ctx,x,y,r,color){ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,Math.max(.1,r),0,TAU);ctx.fill();}
function poly(ctx,pts,fill,stroke=null,sw=1){ctx.beginPath();ctx.moveTo(pts[0][0],pts[0][1]);for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i][0],pts[i][1]);ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=sw;ctx.stroke();}}
function glow(ctx,x,y,r,color,alpha=.5){ctx.save();ctx.globalAlpha=alpha;const rad=ctx.createRadialGradient(x,y,0,x,y,r);rad.addColorStop(0,color);rad.addColorStop(.3,color);rad.addColorStop(1,'transparent');ctx.fillStyle=rad;ctx.fillRect(x-r,y-r,r*2,r*2);ctx.restore();}
function bg(ctx,id){ctx.fillStyle=C.bg;ctx.fillRect(0,0,W,H);ctx.fillStyle='rgba(71,115,155,.14)';for(let i=0;i<20;i++){let x=(i*31+id*23)%58+1,y=(i*47+id*7)%58+1;ctx.fillRect(x,y,1,1);}ctx.strokeStyle='#16263b';ctx.lineWidth=.6;ctx.strokeRect(.5,.5,59,59);}
function face(ctx,x,y,r,ringColor=C.muted){glow(ctx,x,y,r+6,ringColor,.08);ctx.strokeStyle=ringColor;ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.stroke();for(let k=0;k<12;k++){let a=TAU*k/12-Math.PI/2,scale=k%3===0?2.8:1.6;line(ctx,x+Math.cos(a)*(r-3),y+Math.sin(a)*(r-3),x+Math.cos(a)*(r-3-scale),y+Math.sin(a)*(r-3-scale),'#a5bad6',k%3===0?1.4:.7);}}
function hand(ctx,x,y,ang,len,color,w=1.8){line(ctx,x,y,x+Math.cos(ang)*len,y+Math.sin(ang)*len,color,w);dot(ctx,x+Math.cos(ang)*len,y+Math.sin(ang)*len,w*.65,color);}
function twoTimes(ctx,t){face(ctx,30,30,24,'#567999');let u=(t%DURATION)/DURATION;let base=u*TAU-Math.PI/2;
  let warped=u-0.15*Math.sin(TAU*u)-.025*Math.sin(2*TAU*u);let alt=warped*TAU-Math.PI/2;
  hand(ctx,30,30,base,19,C.white,1.6);hand(ctx,30,30,alt,17,C.cyan,2.1);dot(ctx,30,30,2,C.white);
  for(let k=0;k<18;k++){let a=base-.02*k;dot(ctx,30+Math.cos(a)*23,30+Math.sin(a)*23,.35,C.white);} 
  glow(ctx,30+Math.cos(alt)*17,30+Math.sin(alt)*17,5,C.cyan,.25);
}
const DIGITS={0:'1111110',1:'0110000',2:'1101101',3:'1111001',4:'0110011',5:'1011011',6:'1011111',7:'1110000',8:'1111111',9:'1111011'};
function segment(ctx,x,y,w,h,color){let seg=(a,b,c,d)=>poly(ctx,[[x+a,y+b],[x+c,y+b],[x+c-1,y+d],[x+a+1,y+d]],color);}
function digit(ctx,dx,dy,value,color,opacity=1){let s=DIGITS[value];if(!s)return;let w=14,h=29,T=2.8;const parts=[[[2,0],[12,0],[10,3],[4,3]],[[12,1],[14,3],[14,12],[11,14]],[[12,16],[14,18],[14,27],[11,29]],[[3,27],[11,27],[12,30],[2,30]],[[0,18],[3,16],[3,27],[0,28]],[[0,3],[3,1],[3,14],[0,12]],[[2,14],[12,14],[10,17],[4,17]]];ctx.save();ctx.translate(dx,dy);ctx.globalAlpha=opacity;for(let k=0;k<7;k++)if(s[k]==='1')poly(ctx,parts[k],color);ctx.restore();}
function countdown(ctx,t){let u=(t%DURATION);let n=u<9?Math.max(1,10-Math.floor(u)):1; if(u>10&&u<16){let cyc=Math.floor((u-10)*2.2);if(cyc===2||cyc===5||cyc===9)n=2;}
 let flicker=(u>9)?((Math.sin(u*26)>0.86)?0.33:1):1;
 glow(ctx,30,29,27,C.red,.13);line(ctx,11,10,49,10,C.red,1);
 ctx.fillStyle='#899eb3';ctx.font='bold 6px monospace';ctx.textAlign='center';ctx.fillText('T  −',30,8);
 digit(ctx,13,17,Math.floor(n/10),C.red,flicker);digit(ctx,33,17,n%10,C.red,flicker);
 if(u>9){let g=(Math.sin(u*21)+1)/2;line(ctx,12,36+(g*4),49,36+(g*4),C.cyan,.5);}
 for(let k=0;k<10;k++)ctx.fillStyle=k<Math.min(10,Math.floor(u))?C.red:'#253047',ctx.fillRect(8+k*4.6,54,3,2);
}
function glassSandShape(ctx,p,top,color){ // approximate fill of triangular sand chamber via clipped polygon
 ctx.save();ctx.beginPath();if(top){ctx.moveTo(14,12);ctx.lineTo(46,12);ctx.lineTo(30,30);}else{ctx.moveTo(30,30);ctx.lineTo(46,48);ctx.lineTo(14,48);}ctx.closePath();ctx.clip();
 ctx.fillStyle=color;let bottom=48,topY=12,height=18;
 if(top){let level=12+height*(1-Math.sqrt(clamp(p)));ctx.fillRect(12,level,36,30-level);}else{let level=48-height*(1-Math.sqrt(clamp(p)));ctx.fillRect(12,level,36,50-level);}ctx.restore();}
function hourglass(ctx,t){let cyc=fract(t/DURATION);let f=cyc<.5?(1-2*cyc):(cyc-.5)*2;let up=cyc>=.5;
 glow(ctx,30,31,24,C.gold,.10);
 poly(ctx,[[14,10],[46,10],[46,12],[32,29],[46,48],[46,50],[14,50],[14,48],[28,29],[14,12]],'rgba(55,106,139,.12)',C.cyan,1.1);
 line(ctx,12,9,48,9,C.gold,2.5);line(ctx,12,51,48,51,C.gold,2.5);
 glassSandShape(ctx,f,true,C.gold);glassSandShape(ctx,1-f,false,C.orange);
 let drift=up?-1:1;
 for(let k=0;k<12;k++){let v=fract(cyc*5+k*.179);let y=30+drift*(v*16-8);let x=30+Math.sin(k*23+v*13)*(.8+Math.abs(y-30)*.09);dot(ctx,x,y,.4+(k%3)*.12,k%3?C.gold:C.white);}
 line(ctx,53,43,53,16,up?C.cyan:C.gold,.9);poly(ctx,up?[[50,20],[53,15],[56,20]]:[[50,39],[53,44],[56,39]],up?C.cyan:C.gold);
}
function pathPos(q){let a=-Math.PI/2+q*TAU;return [30+21*Math.cos(a),30+19*Math.sin(a)+3*Math.sin(3*a)];}
function wasHere(ctx,t){let u=fract(t/DURATION),f=u<.48?sstep(0,.48,u):u<.55?1:(1-sstep(.55,1,u));
 glow(ctx,30,30,30,C.violet,.08);
 ctx.strokeStyle='#2d3867';ctx.lineWidth=.8;ctx.beginPath();for(let i=0;i<=64;i++){let [x,y]=pathPos(i/64);i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();
 for(let k=0;k<7;k++){let [x,y]=pathPos(fract((k*.175+.12)));dot(ctx,x,y,.55,'#30437d');}
 for(let i=0;i<22;i++){let prev=clamp(f-i*.009),[x,y]=pathPos(prev);ctx.save();ctx.globalAlpha=.02+(22-i)/38;dot(ctx,x,y,.35+(22-i)/45,i%5===0?C.violet:C.cyan);ctx.restore();}
 let [x,y]=pathPos(f);glow(ctx,x,y,8,C.cyan,.46);dot(ctx,x,y,2.4,C.white);dot(ctx,x,y,1,C.cyan);
 if(u>.5)for(let k=0;k<7;k++){let [gx,gy]=pathPos(k/7);dot(ctx,gx,gy,.7,'#594b83');}
}
function timeBands(ctx,t){let u=fract(t/DURATION);let v=[u*2.5, .5*u + .06*Math.sin(TAU*u), -u*1.35];let unify=sstep(.87,.985,u);let colors=[C.cyan,C.gold,C.pink];let ranges=[[0,22],[22,40],[40,60]];
 for(let i=0;i<3;i++){let ph=mix(v[i],u,unify);let a=TAU*ph-Math.PI/2;ctx.save();ctx.beginPath();ctx.rect(0,ranges[i][0],60,ranges[i][1]-ranges[i][0]);ctx.clip();glow(ctx,30,30,32,colors[i],.13);face(ctx,30,30,24,colors[i]);hand(ctx,30,30,a,20,C.white,1.7);hand(ctx,30,30,a/12-Math.PI/4,13,colors[i],1.7);dot(ctx,30,30,2,C.white);ctx.restore();}
 line(ctx,6,22,54,22,'#b1caff',.8);line(ctx,6,40,54,40,'#b1caff',.8);
 for(let i=0;i<3;i++)dot(ctx,5,10+i*20,1.7,colors[i]);
}
function warpPoint(x,y,m){let edge=(x-30)/26;return [x+Math.sin((y+x)*.24)*m*.9,y+Math.pow((y+1)/53,2.8)*m*(7+4*Math.sin(x*.24)) + Math.max(0,m-0.2)*2*Math.max(0,Math.sin(x*.37))];}
function melting(ctx,t){let u=fract(t/DURATION),m=sstep(.08,.83,u)*(1-sstep(.87,1,u));
 glow(ctx,30,33,30,C.violet,.13);
 ctx.strokeStyle=C.violet;ctx.lineWidth=2;ctx.beginPath();for(let i=0;i<=100;i++){let a=TAU*i/100-Math.PI/2,x=30+23*Math.cos(a),y=29+23*Math.sin(a),[xx,yy]=warpPoint(x,y,m);i?ctx.lineTo(xx,yy):ctx.moveTo(xx,yy);}ctx.closePath();ctx.stroke();
 for(let i=0;i<12;i++){let a=TAU*i/12-Math.PI/2,x=30+19*Math.cos(a),y=29+19*Math.sin(a),[xx,yy]=warpPoint(x,y,m);dot(ctx,xx,yy,i%3===0?1.2:.65,C.gold);}
 let ang=u*TAU*2-Math.PI/2;
 for(let [aa,ll,col,w] of [[ang,18,C.white,1.7],[ang/10-Math.PI/2,12,C.cyan,2]]){let [sx,sy]=warpPoint(30,29,m),[ex,ey]=warpPoint(30+Math.cos(aa)*ll,29+Math.sin(aa)*ll,m);line(ctx,sx,sy,ex,ey,col,w);}dot(ctx,...warpPoint(30,29,m),1.9,C.white);
 for(let k=0;k<4;k++){let x=16+k*9,drop=m*(((k+1)*5)%9+4);let [wx,wy]=warpPoint(x,50,m);if(drop>1){line(ctx,wx,wy,wx+.5,Math.min(59,wy+drop*.7),k%2?C.violet:C.cyan,1.6);dot(ctx,wx+.5,Math.min(59,wy+drop*.7),1.3,k%2?C.violet:C.cyan);}}
}
const methods={two_times:twoTimes,never_zero:countdown,reverse_hourglass:hourglass,we_were_here:wasHere,time_bands:timeBands,melting_clock:melting};
function draw(ctx,id,t=0){const scene=typeof id==='number'?SCENES[id]:SCENES.find(s=>s.id===id);if(!scene)throw Error('Unknown scene: '+id);ctx.save();ctx.imageSmoothingEnabled=false;bg(ctx,SCENES.indexOf(scene));methods[scene.id](ctx,((t%DURATION)+DURATION)%DURATION);ctx.restore();}
global.TimeAnimations=Object.freeze({size:60,duration:DURATION,scenes:SCENES,draw});
})(globalThis);
