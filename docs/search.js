let idx=null;const q=document.getElementById('q'),res=document.getElementById('res');
q.addEventListener('input',async()=>{if(!idx){idx=await (await fetch(ROOT+'search.json')).json()}
const w=q.value.toLowerCase().trim().split(/\s+/).filter(Boolean);res.innerHTML='';if(!w.length||q.value.trim().length<2)return;
const hits=[];for(const e of idx){const h=((e.s||'')+'.'+e.t+' '+e.t+' '+(e.s||'')).toLowerCase();if(!w.every(x=>h.includes(x)&&true)&&!w.every(x=>e.k&&e.k.includes(x)))continue;
const t=e.t.toLowerCase(),f=w.join(' ');let r=t===f?0:(t.startsWith(f)||((e.s||'')+'.'+e.t).toLowerCase().startsWith(f))?1:t.endsWith('.'+f)||t.endsWith('::'+f)?2:t.includes(f)?3:w.every(x=>h.includes(x))?4:5;if(e.s&&r<5)r+=0.5;hits.push([r,e])}
hits.sort((a,b)=>a[0]-b[0]);const n=hits.length;
hits.slice(0,60).forEach(([r,e])=>{const a=document.createElement('a');a.href=ROOT+e.u;a.textContent=e.t;if(e.s){const s=document.createElement('small');s.textContent=' - '+e.s;a.appendChild(s)}res.appendChild(a)});
if(n>60){const m=document.createElement('div');m.textContent=(n-60)+' more, refine the search';m.style.fontSize='12px';res.appendChild(m)}if(!n){res.textContent='No match. For engine functions try All functions (search).'}});
(function(){const f=new URLSearchParams(location.search).get('find');if(!f)return;const h=f.toLowerCase();
for(const td of document.querySelectorAll('main td:first-child')){if(td.textContent.trim().toLowerCase()===h){td.scrollIntoView({block:'center'});td.parentElement.style.outline='2px solid #d9922b';break}}})();