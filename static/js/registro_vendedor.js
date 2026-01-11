// ShopFusion — registro_vendedor.js (ajustado a username + retiros)
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('form-registro');

  const metodoPago = document.getElementById('metodo_pago');
  const bankBlocks = document.querySelectorAll('[data-bank]');
  const paypalField = document.querySelector('[data-paypal]');
  const paypalInput = document.getElementById('paypal_email');
  const retiroHint = document.getElementById('retiro_hint');

  const pass1 = document.getElementById('password');
  const pass2 = document.getElementById('password2');
  const username = document.getElementById('username');

  // Mostrar/ocultar campos según método de pago + hint dinámico
  const togglePaymentFields = () => {
    const isBank = metodoPago.value === 'banco';
    const isPaypal = metodoPago.value === 'paypal';

    bankBlocks.forEach(b => b.hidden = !isBank);
    paypalField.hidden = !isPaypal;

    bankBlocks.forEach(b => b.querySelectorAll('select,input').forEach(el => el.required = isBank));
    paypalInput.required = isPaypal;

    if (isPaypal) {
      retiroHint.textContent = "PayPal: retiro inmediato sin comisión.";
    } else if (isBank) {
      retiroHint.textContent = "Transferencias: semanal, quincenal o mensual. Otros bancos pueden cobrar comisión.";
    } else {
      retiroHint.textContent = "Selecciona un método para ver detalles.";
    }
  };
  metodoPago.addEventListener('change', togglePaymentFields);
  togglePaymentFields();

  // Validación username (regex coincide con constraint de DB)
  const USER_RE = /^[a-z0-9._-]{3,32}$/;
  username.addEventListener('input', () => {
    const ok = USER_RE.test(username.value);
    username.setCustomValidity(ok ? '' : 'Solo minúsculas, números, punto, guion y guion bajo (3-32).');
  });

  // Confirmar contraseñas iguales
  const checkPasswords = () => {
    pass2.setCustomValidity('');
    if (pass1.value && pass2.value && pass1.value !== pass2.value) {
      pass2.setCustomValidity('Las contraseñas no coinciden');
    }
  };
  pass1.addEventListener('input', checkPasswords);
  pass2.addEventListener('input', checkPasswords);

  // Envío
  form.addEventListener('submit', (e) => {
    if (!form.checkValidity()) {
      e.preventDefault();
      form.reportValidity();
    }
  });
});
