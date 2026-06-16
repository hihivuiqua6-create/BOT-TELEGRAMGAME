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
