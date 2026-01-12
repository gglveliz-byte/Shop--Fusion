// Support bubble JS: minimal, accessible, progressive enhancement
document.addEventListener('DOMContentLoaded', function(){
  const bubble = document.getElementById('support-bubble');
  const btn = document.getElementById('support-bubble-btn');
  const modal = document.getElementById('support-modal');
  const close = document.getElementById('support-modal-close');
  const form = document.getElementById('support-modal-form');
  const feedback = document.getElementById('sb-feedback');

  if(!btn || !modal || !bubble) return;

  // Ensure bubble is attached to document.body (fixes cases where transforms on ancestors hide fixed elements)
  if(bubble.parentNode !== document.body){
    try { document.body.appendChild(bubble); } catch (e) { /* ignore */ }
  }

  // Force fixed positioning to avoid being affected by container transforms
  bubble.style.position = 'fixed';
  // Use a larger bottom offset on small screens so the bubble sits above toolbars/footers
  const isMobileWidth = (window.innerWidth || document.documentElement.clientWidth) <= 640;
  bubble.style.right = isMobileWidth ? 'calc(12px + env(safe-area-inset-right, 0px))' : 'calc(16px + env(safe-area-inset-right, 0px))';
  bubble.style.bottom = isMobileWidth ? 'calc(140px + env(safe-area-inset-bottom, 0px))' : 'calc(16px + env(safe-area-inset-bottom, 0px))';
  bubble.style.zIndex = '100000';
  bubble.style.display = 'block';
  bubble.style.transform = 'none';

  function keepVisible(){
    try{
      const rect = bubble.getBoundingClientRect();
      const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
      const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
      // compute sensible defaults depending on width
      const defaultRight = vw <= 640 ? '12px' : '12px';
      const defaultBottom = vw <= 640 ? 'calc(140px + env(safe-area-inset-bottom, 0px))' : '12px';
      // if bubble is outside viewport, nudge it inside
      if(rect.right < 0 || rect.left > vw || rect.bottom < 0 || rect.top > vh){
        bubble.style.right = defaultRight;
        bubble.style.bottom = defaultBottom;
      }
      // ensure visible
      bubble.style.visibility = 'visible';
      bubble.style.pointerEvents = 'auto';
    }catch(e){}
  }

  // Adjust position when mobile keyboard/visual viewport changes
  function adjustForViewport(){
    try{
      const vwWidth = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
      const isMobile = vwWidth <= 640;
      const baseOffset = isMobile ? 140 : 16;
      if(window.visualViewport){
        const viewport = window.visualViewport;
        const kbHeight = (window.innerHeight || document.documentElement.clientHeight) - viewport.height;
        if(kbHeight > 0 && isMobile){
          // keyboard open - raise bubble above keyboard
          bubble.style.bottom = `calc(${baseOffset + kbHeight}px + env(safe-area-inset-bottom, 0px))`;
        } else {
          bubble.style.bottom = `calc(${baseOffset}px + env(safe-area-inset-bottom, 0px))`;
        }
      } else {
        bubble.style.bottom = `calc(${baseOffset}px + env(safe-area-inset-bottom, 0px))`;
      }
    }catch(e){}
  }

  // run on events that can change layout
  window.addEventListener('resize', keepVisible);
  window.addEventListener('orientationchange', keepVisible);
  window.addEventListener('scroll', keepVisible, {passive:true});
  if(window.visualViewport){
    window.visualViewport.addEventListener('resize', adjustForViewport);
    window.visualViewport.addEventListener('scroll', adjustForViewport);
  }
  window.addEventListener('focusin', adjustForViewport);
  window.addEventListener('focusout', function(){ setTimeout(adjustForViewport, 50); });
  keepVisible();
  adjustForViewport();

  function openModal(){
    modal.setAttribute('aria-hidden','false');
    // focus first input
    const first = modal.querySelector('input, textarea, button');
    if(first) first.focus();
    // prevent background scroll when modal open
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
  }
  function closeModal(){
    modal.setAttribute('aria-hidden','true');
    btn.focus();
    document.documentElement.style.overflow = '';
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', function(e){
    e.preventDefault();
    const hidden = modal.getAttribute('aria-hidden') === 'true';
    if(hidden) openModal(); else closeModal();
  });
  if(close) close.addEventListener('click', function(e){ e.preventDefault(); closeModal(); });

  // Close on Escape
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') closeModal(); });

  // Submit via AJAX to avoid leaving the page (progressive: the form still posts if JS disabled)
  if(form){
    form.addEventListener('submit', function(ev){
      ev.preventDefault();
      feedback.textContent = '';
      const data = new FormData(form);
      fetch(form.action, { method: 'POST', body: data, credentials: 'same-origin' })
        .then(r => r.text().then(t => ({ok: r.ok, status: r.status, text: t})))
        .then(res => {
          if(res.ok){
            feedback.style.color = 'green';
            feedback.textContent = '✅ Ticket enviado. Te responderemos pronto.';
            form.reset();
            setTimeout(closeModal, 1200);
          } else {
            feedback.style.color = 'crimson';
            feedback.textContent = 'No se pudo enviar el ticket. Intenta nuevamente.';
          }
        }).catch(err => {
          feedback.style.color = 'crimson';
          feedback.textContent = 'Error de red. Intenta otra vez.';
        });
    });
  }
});