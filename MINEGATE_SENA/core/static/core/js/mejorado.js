// ========================================
// FUNCIONALIDAD DE COLAPSO DEL SIDEBAR
// ========================================

document.addEventListener("DOMContentLoaded", function () {
  const sidebar = document.getElementById("sidebar");
  
  // Solo activar el colapso en pantallas grandes (no móviles)
  if (window.innerWidth > 768) {
    // Contraer sidebar al inicio
    sidebar.classList.add("collapsed");
    
    // Expandir cuando el mouse entra
    sidebar.addEventListener("mouseenter", function() {
      sidebar.classList.remove("collapsed");
    });
    
    // Contraer cuando el mouse sale
    sidebar.addEventListener("mouseleave", function() {
      sidebar.classList.add("collapsed");
    });
  }
  
  // Remover el colapso en móviles cuando se redimensiona la ventana
  window.addEventListener("resize", function() {
    if (window.innerWidth <= 768) {
      sidebar.classList.remove("collapsed");
    } else {
      sidebar.classList.add("collapsed");
    }
  });
});