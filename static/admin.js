document.addEventListener('DOMContentLoaded',()=>{const btn=document.querySelector('[data-menu-btn]');const side=document.querySelector('.sidebar');const ov=document.querySelector('.mobile-overlay');function close(){side&&side.classList.remove('open');ov&&ov.classList.remove('show')}btn&&btn.addEventListener('click',()=>{side&&side.classList.toggle('open');ov&&ov.classList.toggle('show')});ov&&ov.addEventListener('click',close);document.querySelectorAll('.nav a').forEach(a=>a.addEventListener('click',close));});



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
