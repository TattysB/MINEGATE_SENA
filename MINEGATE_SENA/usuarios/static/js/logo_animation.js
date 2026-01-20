document.addEventListener('DOMContentLoaded', () => {
    const senaLogo = document.getElementById('sena-logo');
    const mineElements = document.getElementById('mine-elements');
    const minegateText = document.getElementById('minegate-text');
    const pico = document.getElementById('pico');
    const carrito = document.getElementById('carrito');
    const mina = document.getElementById('mina');

    // Verificar que todos los elementos existan antes de aplicar animaciones
    if (!senaLogo || !mineElements || !minegateText || !pico || !carrito || !mina) {
        console.warn('⚠️ Algunos elementos de la animación del logo no se encontraron en el DOM');
        return;
    }

    setTimeout(() => {
        senaLogo.style.transform = 'rotateY(90deg)'; // Rotación para la salida
        senaLogo.style.opacity = 0;

        mineElements.style.opacity = 1;
        mineElements.style.transform = 'rotateY(0deg)'; // Rotación para la entrada

        pico.style.transform = 'translate(0px)';
        pico.style.transition = 'transform 1.5s ease-out 0.5s';

        carrito.style.transform = 'translate(0px)';
        carrito.style.transition = 'transform 1.5s ease-out 0.8s';

        mina.style.width = '120px';
        mina.style.height = '90px';
        mina.style.transition = 'width 1s ease-in-out 1.2s, height 1s ease-in-out 1.2s';

        setTimeout(() => {
            minegateText.style.opacity = 1;
            minegateText.style.bottom = '-5px';
        }, 2500);
    }, 2000);
});
