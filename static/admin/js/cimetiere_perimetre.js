// Attend que la carte Leaflet de Django soit chargée
window.addEventListener('load', function() {
    setTimeout(function() {
        // Trouve la carte Leaflet injectée par Django
        var mapElement = document.querySelector('#id_coordonnees_centre_map');
        var leafletMap = null;
        
        if (mapElement && mapElement._leaflet_map) {
            leafletMap = mapElement._leaflet_map;
        }

        if (leafletMap) {
            var superficieInput = document.getElementById('id_superficie_totale');
            var latInput = document.querySelector('input[name="coordonnees_centre_0"]'); 
            var lngInput = document.querySelector('input[name="coordonnees_centre_1"]'); 

            function drawPerimeter() {
                var superficie = parseFloat(superficieInput ? superficieInput.value : 0);
                var lat = parseFloat(latInput ? latInput.value : 0);
                var lng = parseFloat(lngInput ? lngInput.value : 0);

                if (superficie > 0 && lat !== 0 && lng !== 0) {
                    var coteMetres = Math.sqrt(superficie);
                    var demiCote = coteMetres / 2.0;
                    
                    var offsetLat = demiCote / 111111.0;
                    var offsetLng = demiCote / (111111.0 * Math.cos(lat * Math.PI / 180));

                    var bounds = [
                        [lat + offsetLat, lng - offsetLng],
                        [lat + offsetLat, lng + offsetLng],
                        [lat - offsetLat, lng + offsetLng],
                        [lat - offsetLat, lng - offsetLng]
                    ];

                    if (window.cimetierePolygone) {
                        leafletMap.removeLayer(window.cimetierePolygone);
                    }

                    window.cimetierePolygone = L.polygon(bounds, {
                        color: '#8e44ad',
                        weight: 2,
                        fillColor: '#9b59b6',
                        fillOpacity: 0.2,
                        dashArray: '5, 5'
                    }).addTo(leafletMap);
                }
            }

            setTimeout(drawPerimeter, 1000);

            if (superficieInput) superficieInput.addEventListener('change', drawPerimeter);
            if (latInput) latInput.addEventListener('change', drawPerimeter);
            if (lngInput) lngInput.addEventListener('change', drawPerimeter);
        }
    }, 1500);
});