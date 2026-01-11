/* =============================
   ShopFusion — vendedores_info.js (v2)
   - Animación on-scroll
   - Letras animadas del H1
   - Carrusel para UL de cada sección (auto, botones, drag)
   ============================= */

(() => {
  // ===== 1) On-scroll reveal =====
  const sections = document.querySelectorAll('.vendedores-page section');
  sections.forEach(s => s.classList.add('reveal'));
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting){
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.14, rootMargin: "0px 0px -10%" });
  sections.forEach(s => io.observe(s));

  // ===== 2) Letras animadas del H1 =====
  const h1 = document.querySelector('header h1');
  if (h1){
    const text = h1.textContent;
    h1.textContent = '';
    const wrapper = document.createElement('span');
    wrapper.className = 'letters';
    [...text].forEach((ch, i) => {
      const span = document.createElement('span');
      span.textContent = ch;
      // Pequeño retardo por carácter (incluye espacios)
      span.style.animationDelay = `${0.02 * i}s`;
      wrapper.appendChild(span);
    });
    h1.appendChild(wrapper);
  }

  // ===== 3) Convertir UL en carrusel =====
  function makeCarousel(ul){
    // Crear contenedor
    const carousel = document.createElement('div');
    carousel.className = 'carousel';

    // Crear pista
    const track = document.createElement('div');
    track.className = 'carousel-track';

    // Cada LI pasa a "tarjeta"
    [...ul.children].forEach(li => {
      const item = document.createElement('div');
      item.className = 'carousel-item';
      // Mover contenido del li dentro del item
      item.innerHTML = li.innerHTML;
      track.appendChild(item);
    });

    // Botones
    const nav = document.createElement('div');
    nav.className = 'nav';

    const prev = document.createElement('button');
    prev.className = 'prev';
    prev.setAttribute('aria-label', 'Anterior');
    prev.setAttribute('data-dir', 'prev');
    prev.innerHTML = '‹';

    const next = document.createElement('button');
    next.className = 'next';
    next.setAttribute('aria-label', 'Siguiente');
    next.setAttribute('data-dir', 'next');
    next.innerHTML = '›';

    nav.appendChild(prev);
    nav.appendChild(next);

    carousel.appendChild(track);
    carousel.appendChild(nav);

    // Reemplazar UL por carrusel
    ul.replaceWith(carousel);

    // Lógica de scroll
    const itemWidth = () => track.querySelector('.carousel-item')?.getBoundingClientRect().width || 280;
    const gap = 8; // coincide aprox con CSS

    function scrollByDir(dir){
      const delta = (itemWidth() + gap) * (window.innerWidth < 560 ? 1 : 2);
      track.scrollBy({ left: dir === 'next' ? delta : -delta, behavior: 'smooth' });
    }
    prev.addEventListener('click', () => scrollByDir('prev'));
    next.addEventListener('click', () => scrollByDir('next'));

    // Arrastre con mouse/touch
    let isDown = false, startX = 0, scrollLeft = 0;
    const onDown = (e) => {
      isDown = true;
      track.classList.add('dragging');
      startX = (e.touches?.[0]?.pageX ?? e.pageX) - track.offsetLeft;
      scrollLeft = track.scrollLeft;
    };
    const onLeave = () => { isDown = false; track.classList.remove('dragging'); };
    const onUp = () => { isDown = false; track.classList.remove('dragging'); };
    const onMove = (e) => {
      if(!isDown) return;
      e.preventDefault();
      const x = (e.touches?.[0]?.pageX ?? e.pageX) - track.offsetLeft;
      const walk = (x - startX);
      track.scrollLeft = scrollLeft - walk;
    };
    track.addEventListener('mousedown', onDown);
    track.addEventListener('mouseleave', onLeave);
    track.addEventListener('mouseup', onUp);
    track.addEventListener('mousemove', onMove);

    track.addEventListener('touchstart', onDown, {passive:true});
    track.addEventListener('touchend', onUp);
    track.addEventListener('touchmove', onMove, {passive:false});

    // Auto-scroll suave (se detiene al interactuar)
    let autoplay = setInterval(() => scrollByDir('next'), 3500);
    const stop = () => { clearInterval(autoplay); autoplay = null; };
    const resume = () => { if(!autoplay) autoplay = setInterval(() => scrollByDir('next'), 3500); };
    carousel.addEventListener('mouseenter', stop);
    carousel.addEventListener('mouseleave', resume);
    carousel.addEventListener('touchstart', stop, {passive:true});
  }

  // Seleccionar UL “ricas” (3+ items) dentro de cada section
  document.querySelectorAll('.vendedores-page section ul').forEach(ul => {
    const liCount = ul.querySelectorAll('li').length;
    if (liCount >= 3) makeCarousel(ul);
  });

  // ===== 4) Tecla Tab = modo focus visible global (útil accesibilidad) =====
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Tab'){
      document.documentElement.classList.add('kbd-nav');
    }
  });
})();
