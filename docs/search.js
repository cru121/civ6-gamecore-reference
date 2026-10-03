let idx=null;const q=document.getElementById('q'),res=document.getElementById('res');
q.addEventListener('input',async()=>{if(!idx){idx=await (await fetch(ROOT+'search.json')).json()}
const t=q.value.toLowerCase().trim();res.innerHTML='';if(t.length<2)return;
idx.filter(e=>e.t.toLowerCase().includes(t)||e.k.includes(t)).slice(0,40).forEach(e=>{const a=document.createElement('a');a.href=ROOT+e.u;a.textContent=e.t;res.appendChild(a)})});