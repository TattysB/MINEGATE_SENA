/**
 * Funcionalidad del menú desplegable del usuario
 * Maneja el menú desplegable del usuario en la barra superior
 */

document.addEventListener('DOMContentLoaded', function() {
    const userDropdownBtn = document.getElementById('userDropdownBtn');
    const userDropdownMenu = document.getElementById('userDropdownMenu');
    
    if (!userDropdownBtn || !userDropdownMenu) {
        console.warn('Elementos desplegables del usuario no encontrados');
        return;
    }
    
    /**
     * Alternar la visibilidad del menú desplegable
     */
    function toggleDropdown(e) {
        e.stopPropagation();
        userDropdownMenu.classList.toggle('active');
        userDropdownBtn.classList.toggle('active');
    }
    
       /**
     * Cerrar menú desplegable
     */
    function closeDropdown() {
        userDropdownMenu.classList.remove('active');
        userDropdownBtn.classList.remove('active');
    }
    
    /**
     *Evento de clic para el botón desplegable
     */
    userDropdownBtn.addEventListener('click', toggleDropdown);
    
      /**
     * Cerrar el menú desplegable al hacer clic fuera de él
     */
    document.addEventListener('click', function(e) {
        if (!userDropdownBtn.contains(e.target) && !userDropdownMenu.contains(e.target)) {
            closeDropdown();
        }
    });
    
    /**
     * Cerrar el menú desplegable al pulsar la tecla ESC.
     */
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeDropdown();
        }
    });
    
     /**
     * Gestionar los clics en los elementos del menú desplegable.
     */
    const dropdownItems = userDropdownMenu.querySelectorAll('.dropdown-item');
    dropdownItems.forEach(item => {
        item.addEventListener('click', function(e) {
            // Cerrar el menú desplegable después de hacer clic
            closeDropdown();
            
            // Añadir animación al hacer clic
            this.classList.add('clicked');
            setTimeout(() => this.classList.remove('clicked'), 300);
        });
        
        // Añadir efecto al pasar el cursor
        item.addEventListener('mouseenter', function() {
            this.classList.add('hovered');
        });
        
        item.addEventListener('mouseleave', function() {
            this.classList.remove('hovered');
        });
    });
    
    // Registro para depuración
    console.log('User dropdown initialized successfully');
});
