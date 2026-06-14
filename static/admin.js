(() => {
  const btn = document.querySelector('[data-menu-btn]');
  const side = document.querySelector('.sidebar');
  const ov = document.querySelector('.mobile-overlay');
  const close = () => { side && side.classList.remove('open'); ov && ov.classList.remove('show'); };
  if (btn && side) btn.addEventListener('click', () => { side.classList.toggle('open'); ov && ov.classList.toggle('show'); });
  if (ov) ov.addEventListener('click', close);
  document.querySelectorAll('.nav a').forEach(a => a.addEventListener('click', close));
})();
