document.addEventListener('click', e => {
  const a = e.target.closest('a[href*="approve"],a[href*="reject"],a[href*="clearlogs"]');
  if(a && !confirm('Xác nhận thao tác này?')) e.preventDefault();
});
