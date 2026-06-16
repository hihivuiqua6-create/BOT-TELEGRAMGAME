(function(){
  const body=document.body;
  const btn=document.querySelector('[data-menu-btn]');
  const overlay=document.querySelector('.mobile-overlay');
  function close(){ body.classList.remove('nav-open'); }
  function open(){ body.classList.add('nav-open'); }
  if(btn){btn.addEventListener('click',()=>body.classList.contains('nav-open')?close():open());}
  if(overlay){overlay.addEventListener('click',close);}
  document.querySelectorAll('.nav a').forEach(a=>a.addEventListener('click',close));
  window.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
})();



// ===== AUTO REALTIME FIX V2 =====
(function(){
    const _fetch = window.fetch;
    if(_fetch){
        window.fetch = function(url, options){
            try{
                if(typeof url === "string"){
                    url += (url.includes("?") ? "&" : "?") + "t=" + Date.now();
                }
            }catch(e){}
            return _fetch(url, options);
        }
    }

    setInterval(()=>{
        try{
            if(typeof getLatest === "function") getLatest();
            if(typeof loadLatest === "function") loadLatest();
            if(typeof loadData === "function") loadData();
            if(typeof fetchData === "function") fetchData();
            if(typeof loadPhiênMoi === "function") loadPhiênMoi();
        }catch(e){}
    }, 3000);
})();
