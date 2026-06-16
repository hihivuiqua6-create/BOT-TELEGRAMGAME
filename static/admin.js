(function(){
  document.addEventListener('DOMContentLoaded', function(){
    var btn = document.querySelector('[data-menu-btn]');
    var side = document.querySelector('[data-sidebar]');
    var ov = document.querySelector('[data-overlay]');
    function close(){ side && side.classList.remove('open'); ov && ov.classList.remove('show'); }
    function open(){ side && side.classList.add('open'); ov && ov.classList.add('show'); }
    btn && btn.addEventListener('click', function(){
      if(side.classList.contains('open')) close(); else open();
    });
    ov && ov.addEventListener('click', close);
    document.querySelectorAll('.nav a').forEach(function(a){ a.addEventListener('click', close); });
    // ESC closes
    document.addEventListener('keydown', function(e){ if(e.key === 'Escape') close(); });
    // Confirm destructive
    document.querySelectorAll('a.btn.red, button.btn.red, a[data-confirm]').forEach(function(el){
      el.addEventListener('click', function(e){
        var msg = el.getAttribute('data-confirm') || 'Bạn chắc chắn muốn thực hiện?';
        if(!confirm(msg)) e.preventDefault();
      });
    });
  });
})();
