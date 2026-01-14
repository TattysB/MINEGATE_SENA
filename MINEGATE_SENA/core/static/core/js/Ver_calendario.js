// BOTÓN VER CALENDARIO - Muestra/Oculta visitas
  document.addEventListener("DOMContentLoaded", () => {
    const btnCalendario = document.getElementById("toggleVisitas");
    const listaVisitas = document.getElementById("listaVisitas");

    btnCalendario.addEventListener("click", () => {
      if (listaVisitas.style.display === "none") {
        listaVisitas.style.display = "block";
        btnCalendario.textContent = "Ocultar calendario";
      } else {
        listaVisitas.style.display = "none";
        btnCalendario.textContent = "Ver calendario";
      }
    });
  });