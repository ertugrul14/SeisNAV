// Replace with your valid Mapbox access token
mapboxgl.accessToken = 'pk.eyJ1IjoiZXJ0dWdydWxha2RlbWlyIiwiYSI6ImNtNDhvOWIwcDAxa3Uyc3I2OW9xMmcyejQifQ.yHQkT4KBp8kzyf2YQDQQlQ';

// Initialize the map with the official Dark Mode style
const map = new mapboxgl.Map({
    container: 'map', // ID of the container where the map is rendered
    style: 'mapbox://styles/mapbox/dark-v11', // Dark mode style
    center: [36.6200, 37.0180], // Center coordinates for your AOI
    zoom: 13 // Initial zoom level
});

// Add draggable start and end markers to the map
let startMarker = new mapboxgl.Marker({ draggable: true, color: 'lime' })
    .setLngLat([36.6100, 37.0000]) // Starting marker position
    .addTo(map);

let endMarker = new mapboxgl.Marker({ draggable: true, color: 'red' })
    .setLngLat([36.6500, 37.0300]) // Ending marker position
    .addTo(map);

// Function to calculate and display the shortest path
document.getElementById("calculate-path-btn").addEventListener("click", () => {
    const startCoords = startMarker.getLngLat();
    const endCoords = endMarker.getLngLat();

    // Fetch shortest path data from the backend
    fetch('/shortest-path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            start: [startCoords.lng, startCoords.lat],
            end: [endCoords.lng, endCoords.lat],
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }

        // Process the path coordinates
        const path = data.path.map(coord => [coord[0], coord[1]]);

        // Add or update the shortest path on the map
        if (map.getSource("shortest-path")) {
            map.getSource("shortest-path").setData({
                type: "Feature",
                geometry: { type: "LineString", coordinates: path },
            });
        } else {
            map.addSource("shortest-path", {
                type: "geojson",
                data: {
                    type: "Feature",
                    geometry: { type: "LineString", coordinates: path },
                },
            });

            map.addLayer({
                id: "shortest-path",
                type: "line",
                source: "shortest-path",
                paint: {
                    "line-color": "#00FF00", // Green line for the path
                    "line-width": 4
                }
            });
        }
    })
    .catch(error => {
        console.error("Error fetching the shortest path:", error);
        alert("An error occurred while calculating the path. Please try again.");
    });
});

// Function to load and generate circles further from collapsed buildings
function generateCirclesFurtherFromCollapsedBuildings(collapsedBuildings) {
    const circles = [];
    const colors = ['#FF6347', '#32CD32', '#FFD700']; // Red, Green, Yellow

    collapsedBuildings.features.forEach((feature, index) => {
        // Create a buffer range (500-1000 meters) around the collapsed building
        const outerBuffer = turf.buffer(feature, 1000, { units: 'meters' });
        const innerBuffer = turf.buffer(feature, 500, { units: 'meters' });
        const difference = turf.difference(outerBuffer, innerBuffer);

        if (difference) {
            // Generate a random point within the buffer difference
            const randomPoint = turf.randomPoint(1, { bbox: turf.bbox(difference) }).features[0];

            // Ensure the point is not inside the original collapsed building
            if (!turf.booleanPointInPolygon(randomPoint, feature)) {
                // Ensure the circle doesn't intersect with roads
                const circle = turf.circle(randomPoint.geometry.coordinates, 15, {
                    steps: 64, units: 'meters'
                });

                // Check for intersections with the road layer
                const features = map.queryRenderedFeatures(map.project(randomPoint.geometry.coordinates), { layers: ['road'] });

                // Only add the circle if it does not intersect with a road
                if (features.length === 0) {
                    circle.properties = { color: colors[index % colors.length] }; // Cycle through colors
                    circles.push(circle);
                }
            }
        }
    });

    // Save circles to localStorage as JSON
    localStorage.setItem('circles', JSON.stringify(circles));

    return turf.featureCollection(circles);
}

// Add Circles Layer from localStorage
function loadCircles() {
    const savedCircles = localStorage.getItem('circles');
    if (savedCircles) {
        // If circles are already saved in localStorage, use them
        const circles = JSON.parse(savedCircles);
        map.addSource('random-circles', {
            type: 'geojson',
            data: turf.featureCollection(circles)
        });

        map.addLayer({
            id: 'random-circles-layer',
            type: 'fill',
            source: 'random-circles',
            paint: {
                'fill-color': ['get', 'color'],
                'fill-opacity': 0.6
            }
        });

        // Separate circles by color
        addCircleLayers(circles);
    } else {
        // If circles are not saved, generate new ones and save them
        loadCollapsedPolygons(collapsedBuildings => {
            const circles = generateCirclesFurtherFromCollapsedBuildings(collapsedBuildings);
            map.addSource('random-circles', {
                type: 'geojson',
                data: circles
            });

            map.addLayer({
                id: 'random-circles-layer',
                type: 'fill',
                source: 'random-circles',
                paint: {
                    'fill-color': ['get', 'color'],
                    'fill-opacity': 0.6
                }
            });

            // Separate circles by color
            addCircleLayers(circles);
        });
    }
}

function addCircleLayers(circles) {
    // Separate circles by color
    const redCircles = circles.filter(circle => circle.properties.color === '#FF6347');
    const greenCircles = circles.filter(circle => circle.properties.color === '#32CD32');
    const yellowCircles = circles.filter(circle => circle.properties.color === '#FFD700');

    // Add red circles layer
    map.addSource('red-circles', {
        type: 'geojson',
        data: turf.featureCollection(redCircles)
    });
    map.addLayer({
        id: 'red-circles-layer',
        type: 'fill',
        source: 'red-circles',
        paint: {
            'fill-color': '#FF6347',
            'fill-opacity': 0.6
        },
        layout: { visibility: 'none' }
    });

    // Add green circles layer
    map.addSource('green-circles', {
        type: 'geojson',
        data: turf.featureCollection(greenCircles)
    });
    map.addLayer({
        id: 'green-circles-layer',
        type: 'fill',
        source: 'green-circles',
        paint: {
            'fill-color': '#32CD32',
            'fill-opacity': 0.6
        },
        layout: { visibility: 'none' }
    });

    // Add yellow circles layer
    map.addSource('yellow-circles', {
        type: 'geojson',
        data: turf.featureCollection(yellowCircles)
    });
    map.addLayer({
        id: 'yellow-circles-layer',
        type: 'fill',
        source: 'yellow-circles',
        paint: {
            'fill-color': '#FFD700',
            'fill-opacity': 0.6
        },
        layout: { visibility: 'none' }
    });
}

// Toggle Circles by Color
document.getElementById('toggle-red-circles-btn').addEventListener('click', () => {
    toggleCircleLayer('red-circles-layer');
});

document.getElementById('toggle-green-circles-btn').addEventListener('click', () => {
    toggleCircleLayer('green-circles-layer');
});

document.getElementById('toggle-yellow-circles-btn').addEventListener('click', () => {
    toggleCircleLayer('yellow-circles-layer');
});

function toggleCircleLayer(layerId) {
    const currentVisibility = map.getLayoutProperty(layerId, 'visibility');
    const newVisibility = currentVisibility === 'visible' ? 'none' : 'visible';
    map.setLayoutProperty(layerId, 'visibility', newVisibility);
}

// Toggle Collapsed Buildings
document.getElementById('toggle-collapsed-btn').addEventListener('click', () => {
    if (!map.getLayer('collapsed-polygons')) {
        loadCollapsedPolygons(() => {
            document.getElementById('toggle-collapsed-btn').innerText = 'Hide Collapsed Buildings';
            collapsedLayerVisible = true;
        });
    } else {
        collapsedLayerVisible = !collapsedLayerVisible;
        map.setLayoutProperty('collapsed-polygons', 'visibility', collapsedLayerVisible ? 'visible' : 'none');
        document.getElementById('toggle-collapsed-btn').innerText = collapsedLayerVisible
            ? 'Hide Collapsed Buildings'
            : 'Show Collapsed Buildings';
    }
}

map.on('load', () => {
    loadCircles(); // Load circles from localStorage or generate them
});
