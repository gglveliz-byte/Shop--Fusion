// Seleccionamos los elementos
const navToggle = document.querySelector('.nav-toggle');
const navMenu = document.getElementById('nav-menu');

// Función para abrir/cerrar menú
navToggle.addEventListener('click', () => {
    const isActive = navMenu.classList.toggle('active'); // agrega/quita la clase 'active'
    navToggle.setAttribute('aria-expanded', isActive);  // mejora accesibilidad
});

let lastScroll = 0;
const header = document.querySelector('header');

window.addEventListener('scroll', () => {
    const currentScroll = window.scrollY;

    if (currentScroll > lastScroll && currentScroll > 50) {
        // Bajar → esconder header
        header.classList.add('hidden');
    } else {
        // Subir → mostrar header
        header.classList.remove('hidden');
    }

    lastScroll = currentScroll;
});

document.querySelectorAll('.media-slider').forEach(slider => {
    const items = slider.querySelectorAll('.product-media');
    let index = 0;

    function showSlide(i){
        items.forEach((el, idx) => el.style.display = idx === i ? 'block' : 'none');
    }

    showSlide(index);

    // Aquí puedes agregar eventos para las flechas
});

