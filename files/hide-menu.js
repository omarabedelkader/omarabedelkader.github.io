(function() {
  function applyState(menu, toggle, hidden) {
    var ariaHidden = hidden ? 'true' : 'false';
    var ariaPressed = hidden ? 'false' : 'true';

    document.body.classList.toggle('menu-hidden', hidden);
    menu.setAttribute('aria-hidden', ariaHidden);

    toggle.textContent = hidden ? 'Show menu' : 'Hide menu';
    toggle.setAttribute('aria-pressed', ariaPressed);
    toggle.setAttribute('aria-expanded', ariaHidden);
    toggle.setAttribute('data-menu-hidden', hidden ? 'true' : 'false');
  }

  function initMenuToggle() {
    var menu = document.getElementById('menu');
    var toggle = document.getElementById('menu-toggle');

    if (!menu || !toggle) {
      return;
    }

    applyState(menu, toggle, true);

    toggle.addEventListener('click', function() {
      var isHidden = toggle.getAttribute('data-menu-hidden') === 'true';
      applyState(menu, toggle, !isHidden);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMenuToggle, { once: true });
  } else {
    initMenuToggle();
  }
})();