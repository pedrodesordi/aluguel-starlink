function confirmar(msg) {
  return window.confirm(msg || 'Tem certeza?');
}

function formatarCpfCnpj(v) {
  v = v.replace(/\D/g, '').slice(0, 14);
  if (v.length > 11) {
    if (v.length > 12) return v.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2})/, '$1.$2.$3/$4-$5');
    if (v.length > 8)  return v.replace(/(\d{2})(\d{3})(\d{3})(\d{0,4})/, '$1.$2.$3/$4');
    if (v.length > 5)  return v.replace(/(\d{2})(\d{3})(\d{0,3})/, '$1.$2.$3');
    return v.replace(/(\d{2})(\d{0,3})/, '$1.$2');
  }
  if (v.length > 9) return v.replace(/(\d{3})(\d{3})(\d{3})(\d{0,2})/, '$1.$2.$3-$4');
  if (v.length > 6) return v.replace(/(\d{3})(\d{3})(\d{0,3})/, '$1.$2.$3');
  if (v.length > 3) return v.replace(/(\d{3})(\d{0,3})/, '$1.$2');
  return v;
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.cpf-mask').forEach(function (el) {
    el.addEventListener('input', function () { el.value = formatarCpfCnpj(el.value); });
    el.addEventListener('paste', function (e) {
      e.preventDefault();
      el.value = formatarCpfCnpj((e.clipboardData || window.clipboardData).getData('text'));
    });
  });
});
