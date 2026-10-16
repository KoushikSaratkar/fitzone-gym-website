document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach(button => {
    button.addEventListener('click', event => { if (!window.confirm(button.dataset.confirm)) event.preventDefault(); });
  });
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => {
      const button = form.querySelector('button[type="submit"], button:not([type])');
      if (button && form.checkValidity()) {
        button.dataset.originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Please wait…';
      }
    });
  });
});
