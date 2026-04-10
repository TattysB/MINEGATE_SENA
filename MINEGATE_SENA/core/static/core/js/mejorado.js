
document.addEventListener("DOMContentLoaded", function () {
  const sidebar = document.getElementById("sidebar");
  
  if (window.innerWidth > 768) {
    sidebar.classList.add("collapsed");
    
    sidebar.addEventListener("mouseenter", function() {
      sidebar.classList.remove("collapsed");
    });
    
    sidebar.addEventListener("mouseleave", function() {
      sidebar.classList.add("collapsed");
    });
  }
  
  window.addEventListener("resize", function() {
    if (window.innerWidth <= 768) {
      sidebar.classList.remove("collapsed");
    } else {
      sidebar.classList.add("collapsed");
    }
  });
});