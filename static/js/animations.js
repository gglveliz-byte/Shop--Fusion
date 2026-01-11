
document.addEventListener('DOMContentLoaded', () => {
    // Menú hamburguesa
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            const isActive = navMenu.classList.toggle('active');
            navToggle.setAttribute('aria-expanded', isActive);
            document.body.classList.toggle('nav-active', isActive);
        });

        // Desplazamiento suave para enlaces de navegación y cerrar menú
        const navLinks = navMenu.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                const targetSection = document.getElementById(targetId);
                if (targetSection) {
                    const headerHeight = document.querySelector('header').offsetHeight;
                    const targetPosition = targetSection.getBoundingClientRect().top + window.scrollY - headerHeight;
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
                navMenu.classList.remove('active');
                navToggle.setAttribute('aria-expanded', false);
                document.body.classList.remove('nav-active');
            });
        });
    }

    // Botones de navegación entre secciones (subir/bajar)
    const sectionNavButtons = document.querySelectorAll('.section-nav-btn');
    sectionNavButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetId = button.getAttribute('data-target');
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                const headerHeight = document.querySelector('header').offsetHeight;
                const targetPosition = targetSection.getBoundingClientRect().top + window.scrollY - headerHeight;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Ocultar/mostrar header en scroll
    const header = document.querySelector('header');
    let lastScroll = 0;
    window.addEventListener('scroll', () => {
        const currentScroll = window.scrollY;
        if (currentScroll > lastScroll && currentScroll > 50) {
            header.classList.add('hidden');
        } else {
            header.classList.remove('hidden');
        }
        lastScroll = currentScroll;
    });

    // Carrusel de productos
    document.querySelectorAll('.products-container').forEach(container => {
        const prevButton = container.previousElementSibling;
        const nextButton = container.nextElementSibling;
        if (prevButton && nextButton) {
            const scrollAmountClick = 300;
            const scrollAmountHover = 10;
            let scrollInterval = null;

            const startScroll = (direction) => {
                scrollInterval = setInterval(() => {
                    container.scrollBy({
                        left: direction === 'prev' ? -scrollAmountHover : scrollAmountHover,
                        behavior: 'smooth'
                    });
                }, 800);
            };

            const stopScroll = () => {
                if (scrollInterval) {
                    clearInterval(scrollInterval);
                    scrollInterval = null;
                }
            };

            prevButton.addEventListener('click', () => {
                container.scrollBy({
                    left: -scrollAmountClick,
                    behavior: 'smooth'
                });
            });

            nextButton.addEventListener('click', () => {
                container.scrollBy({
                    left: scrollAmountClick,
                    behavior: 'smooth'
                });
            });

            prevButton.addEventListener('mouseover', () => startScroll('prev'));
            nextButton.addEventListener('mouseover', () => startScroll('next'));
            prevButton.addEventListener('mouseout', stopScroll);
            nextButton.addEventListener('mouseout', stopScroll);

            const updateButtonVisibility = () => {
                const maxScroll = container.scrollWidth - container.clientWidth;
                prevButton.classList.toggle('hidden', container.scrollLeft <= 0);
                nextButton.classList.toggle('hidden', container.scrollLeft >= maxScroll - 1);
            };

            container.addEventListener('scroll', updateButtonVisibility);
            updateButtonVisibility();
            window.addEventListener('resize', updateButtonVisibility);
        }
    });

    // Carrusel de imágenes
    const carousels = document.querySelectorAll('.product-card .carousel');
    carousels.forEach(carousel => {
        const images = carousel.querySelectorAll('img');
        if (images.length > 0) {
            let currentIndex = 0;
            images.forEach(img => img.classList.remove('active'));
            images[currentIndex].classList.add('active');
            setInterval(() => {
                images[currentIndex].classList.remove('active');
                currentIndex = (currentIndex + 1) % images.length;
                images[currentIndex].classList.add('active');
            }, 9000);
        }
    });

    // Botones "Conocer más" solo para afiliados (tienen data-link)
    const botones = document.querySelectorAll('.product-card:not(.exclusive) .view-more-btn[data-link]');
    botones.forEach(boton => {
        boton.addEventListener('click', (e) => {
            e.stopPropagation();
            const enlace = boton.dataset.link;
            if (!enlace) return; // en exclusivos se maneja con modal, no con enlace directo
            window.open(
                enlace,
                '_blank',
                'width=2000,height=500,top=500,left=150,scrollbars=yes,resizable=yes,noopener,noreferrer'
            );
        });
    });

    // Interactividad de tarjetas de productos
    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach(card => {
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.view-more-btn')) {
                productCards.forEach(c => c.classList.remove('active'));
                card.classList.add('active');
            }
        });
    });

    // Remover clase active al hacer clic fuera de las tarjetas
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.product-card')) {
            productCards.forEach(c => c.classList.remove('active'));
        }
    });

    // Actualizar año en el footer
    document.getElementById('current-year').textContent = new Date().getFullYear();
});


(() => {
  const root = document.documentElement;
  const saved = localStorage.getItem('sf-theme');
  // Tema por defecto: oscuro. Si hay guardado, se aplica.
  if (saved) root.setAttribute('data-theme', saved);

  const toggle = document.querySelector('.theme-toggle');
  const setTheme = (t) => {
    root.setAttribute('data-theme', t);
    localStorage.setItem('sf-theme', t);
  };

  if (toggle){
    toggle.addEventListener('click', () => {
      const current = root.getAttribute('data-theme') || 'dark';
      setTheme(current === 'light' ? 'dark' : 'light');
    });
  }

  // (Opcional) Si no hay preferencia guardada, seguir el sistema:
  if (!saved){
    const mq = window.matchMedia('(prefers-color-scheme: light)');
    if (mq.matches) setTheme('light');
  }
})();

