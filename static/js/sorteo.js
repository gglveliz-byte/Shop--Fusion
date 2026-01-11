// ===============================
// ShopFusion — Sorteo (JS animado)
// ===============================
document.addEventListener('DOMContentLoaded', () => {
  // ---------- Utilidades ----------
  const $ = (sel, ctx = document) => ctx.querySelector(sel);

  // ---------- Modal Registro ----------
  const modal = $('#registro-modal');
  const closeBtn = $('#cerrarModal');

  const openModal = () => {
    if (!modal) return;

    // Forzar que se vea, aunque tenga display:none por CSS
    modal.style.display = 'flex';
    modal.classList.add('active');
    modal.removeAttribute('hidden');

    // Bloquear scroll del fondo
    document.body.style.overflow = 'hidden';

    // Si el modal no es fixed, al menos intentamos llevarlo al centro de la pantalla
    try {
      modal.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } catch (e) {
      console.warn('No se pudo hacer scrollIntoView para el modal:', e);
    }
  };

  const closeModal = () => {
    if (!modal) return;
    modal.classList.remove('active');
    setTimeout(() => {
      modal.setAttribute('hidden', '');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }, 220);
  };

  if (closeBtn) {
    closeBtn.addEventListener('click', closeModal);
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal();
      }
    });
  }

  // ---------- Abrir modal automáticamente después de pagar ----------
  let shouldOpenModal = false;

  // 1) Por querystring ?paid=1
  const params = new URLSearchParams(window.location.search);
  if (params.get('paid') === '1') {
    shouldOpenModal = true;
  }

  // 2) Por bandera en la sesión (script #pago-data en index.html)
  const pagoDataEl = document.getElementById('pago-data');
  if (pagoDataEl) {
    try {
      const flag = JSON.parse(pagoDataEl.textContent.trim());
      if (flag === true) {
        shouldOpenModal = true;
      }
    } catch (e) {
      console.warn('No se pudo leer pago-data:', e);
    }
  }

  if (shouldOpenModal) {
    // ✅ Aviso emergente que querías
    alert('✅ Pago realizado con éxito. Ahora ingresa tus datos para generar tu número de boleto.');
    openModal();
  }

  // ---------- PayPal ----------
  const ppContainer = $('#paypal-button-container');
  if (!ppContainer) {
    // No hay sorteo en esta página
    return;
  }

  // estado de carga visual
  ppContainer.classList.add('loading');
  ppContainer.style.zIndex = '1000';

  // helper: marcar "cargado" cuando aparece el iframe
  const watchIframes = () => {
    const iframes = ppContainer.querySelectorAll('iframe');
    if (iframes.length >= 1) {
      ppContainer.classList.remove('loading');
      // micro-animación de entrada
      ppContainer.animate(
        [
          { transform: 'translateY(10px)', opacity: 0 },
          { transform: 'translateY(0)', opacity: 1 }
        ],
        { duration: 320, easing: 'ease-out' }
      );
      return true;
    }
    return false;
  };

  // Polling suave hasta que PayPal inserte los iframes
  const waitForButtons = () => {
    if (watchIframes()) return;
    setTimeout(waitForButtons, 100);
  };
  waitForButtons();

  const startPayPal = () => {
    if (!(window.paypal && paypal.Buttons)) {
      setTimeout(startPayPal, 50);
      return;
    }

    paypal.Buttons({
      style: {
        layout: 'vertical', // PayPal + tarjeta en columna
        color: 'gold',
        shape: 'pill',
        label: 'pay',
        height: 45,
        tagline: false
      },
      funding: {
        allowed: [paypal.FUNDING.PAYPAL, paypal.FUNDING.CARD]
      },

      // Crear orden (PayPal la crea, pero no la capturamos aquí)
      createOrder: function (_, actions) {
        return actions.order.create({
          purchase_units: [
            {
              amount: {
                value: '1.00',          // precio del boleto
                currency_code: 'USD'
              },
              description: '🎁 Sorteo ShopFusion - Boleto de participación'
            }
          ]
        });
      },

      // Cuando el usuario aprueba el pago
      onApprove: function (data, actions) {
        // 👉 NO hacemos actions.order.capture() aquí.
        // Capturamos en tu backend /api/paypal/capture
        return fetch('/api/paypal/capture', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ orderID: data.orderID })
        })
          .then((res) => res.json())
          .then(async (resp) => {
            console.log('Respuesta /api/paypal/capture:', resp);

            if (resp.status === 'success' || resp.status === 'already_captured') {
              // Marcamos pago confirmado en la sesión (por si quieres usarlo)
              try {
                await fetch('/pago_confirmado', { method: 'POST' });
              } catch (e) {
                console.warn('No se pudo llamar a /pago_confirmado:', e);
              }

              // Redirigimos con ?paid=1 (el modal se abre solo al recargar)
              const redirect =
                ppContainer.dataset.redirect ||
                (window.location.origin + window.location.pathname);
              const url = new URL(redirect);
              url.searchParams.set('paid', '1');
              window.location.href = url.toString();
            } else {
              console.error('Error al capturar el pago en backend:', resp);
              alert(
                '⚠️ Hubo un problema verificando tu pago en PayPal.\nNo se ha registrado el boleto.'
              );
            }
          })
          .catch((err) => {
            console.error('Error llamando a /api/paypal/capture:', err);
            alert('⚠️ Error de comunicación con el servidor. Intenta nuevamente.');
          });
      },

      onCancel: function () {
        // Feedback sutil al cancelar
        ppContainer.animate(
          [
            { transform: 'scale(1.0)'},
            { transform: 'scale(0.985)'},
            { transform: 'scale(1.0)'}
          ],
          { duration: 220, easing: 'ease-out' }
        );
      },

      onError: function (err) {
        console.error('PayPal Error:', err);
        alert('Error al procesar el pago. Intenta nuevamente.');
        // sacudir suave si falla
        ppContainer.animate(
          [
            { transform: 'translateX(0)' },
            { transform: 'translateX(-6px)' },
            { transform: 'translateX(6px)' },
            { transform: 'translateX(0)' }
          ],
          { duration: 260, easing: 'ease-out' }
        );
      }
    }).render('#paypal-button-container');
  };

  startPayPal();
});
