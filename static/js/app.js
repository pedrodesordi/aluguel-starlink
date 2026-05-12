function confirmar(msg) {
  return window.confirm(msg || 'Tem certeza?');
}

// Máscara de CPF
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.cpf-mask').forEach(function (el) {
    el.addEventListener('input', function () {
      let v = el.value.replace(/\D/g, '').slice(0, 11);
      if (v.length > 9) v = v.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, '$1.$2.$3-$4');
      else if (v.length > 6) v = v.replace(/(\d{3})(\d{3})(\d{1,3})/, '$1.$2.$3');
      else if (v.length > 3) v = v.replace(/(\d{3})(\d{1,3})/, '$1.$2');
      el.value = v;
    });
  });
});
