/* SIC Mockups — theme toggle (dark ↔ light) */
(function () {
  var KEY = 'sic-theme';

  function saved() { return localStorage.getItem(KEY) || 'dark'; }

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(KEY, theme);
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    if (theme === 'dark') {
      btn.textContent = '☾';
      btn.title = 'Mudar para modo claro';
      btn.classList.remove('active');
    } else {
      btn.textContent = '☀';
      btn.title = 'Mudar para modo escuro';
      btn.classList.add('active');
    }
  }

  /* Apply immediately to avoid flash */
  apply(saved());

  document.addEventListener('DOMContentLoaded', function () {
    apply(saved());
    var btn = document.getElementById('theme-toggle');
    if (btn) btn.addEventListener('click', function () {
      apply(saved() === 'dark' ? 'light' : 'dark');
    });
  });
})();
