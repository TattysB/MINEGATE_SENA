

document.addEventListener('DOMContentLoaded', function() {
    const userDropdownBtn = document.getElementById('userDropdownBtn');
    const userDropdownMenu = document.getElementById('userDropdownMenu');
    
    if (!userDropdownBtn || !userDropdownMenu) {
        console.warn('Elementos desplegables del usuario no encontrados');
        return;
    }
    
    
    function toggleDropdown(e) {
        e.stopPropagation();
        userDropdownMenu.classList.toggle('active');
        userDropdownBtn.classList.toggle('active');
    }
    
       
    function closeDropdown() {
        userDropdownMenu.classList.remove('active');
        userDropdownBtn.classList.remove('active');
    }
    
    
    userDropdownBtn.addEventListener('click', toggleDropdown);
    
      
    document.addEventListener('click', function(e) {
        if (!userDropdownBtn.contains(e.target) && !userDropdownMenu.contains(e.target)) {
            closeDropdown();
        }
    });
    
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeDropdown();
        }
    });
    
     
    const dropdownItems = userDropdownMenu.querySelectorAll('.dropdown-item');
    dropdownItems.forEach(item => {
        item.addEventListener('click', function(e) {
            closeDropdown();
            
            this.classList.add('clicked');
            setTimeout(() => this.classList.remove('clicked'), 300);
        });
        
        item.addEventListener('mouseenter', function() {
            this.classList.add('hovered');
        });
        
        item.addEventListener('mouseleave', function() {
            this.classList.remove('hovered');
        });
    });
    
    console.log('User dropdown initialized successfully');
});
