document.addEventListener('DOMContentLoaded', function() {
    // Coordenadas exactas de OFICINA GICEMIN
    const lat = 5.7307142; 
    const lng = -72.8948405;

    // Inicializar el mapa
    const map = L.map('map').setView([lat, lng], 14); 

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // CAPA DE ETIQUETAS (Opcional: para ver nombres de calles sobre el satélite)
    L.tileLayer('https://stamen-tiles-{s}.a.colors.com/toner-labels/{z}/{x}/{y}{r}.png', {
        attribution: 'Labels &copy; Stamen Design',
        subdomains: 'abcd',
        opacity: 0.7
    }).addTo(map);

    // URL de Google Maps para "Cómo llegar"
    const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;

    // Marcador
    L.marker([lat, lng]).addTo(map)
        .bindPopup(`
            <div style="text-align: center;">
                <strong style="color: #0056b3;">SENA CENTRO MINERO</strong><br>
                <span style="font-size: 0.85em;">Kilometro 7 Vereda Morca, Sector Bata, Sogamoso, Boyacá</span><br><br>
                <a href="${googleMapsUrl}" target="_blank" 
                   style="padding: 8px 12px; background: #0056b3; color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">
                   Cómo llegar
                </a>
            </div>
        `)
        .openPopup();
});
