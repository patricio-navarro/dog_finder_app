
// State Variables
let reportMap, findMap;
let reportMarker;
let sightingMarkers = [];
let currentMode = 'report';
let mapClickListener;

// Find State
let nextCursor = null;
let isLoading = false;
let lastBounds = null;

// Map Configuration
const mapStyles = [
    { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] },
    { featureType: "road", elementType: "geometry", stylers: [{ color: "#38414e" }] },
    { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#212a37" }] },
    { featureType: "water", elementType: "geometry", stylers: [{ color: "#17263c" }] },
];

function initMaps() {
    const defaultLocation = { lat: 37.7749, lng: -122.4194 };

    // 1. Report Map
    reportMap = new google.maps.Map(document.getElementById("map"), {
        zoom: 12,
        center: defaultLocation,
        mapTypeControl: false,
        styles: mapStyles
    });

    reportMap.addListener("click", (e) => {
        placeReportMarker(e.latLng);
    });

    // 2. Find Map
    findMap = new google.maps.Map(document.getElementById("find-map"), {
        zoom: 12, // start zoomed out
        center: defaultLocation,
        mapTypeControl: false,
        streetViewControl: false,
        styles: mapStyles
    });

    findMap.addListener("dragend", () => {
        document.getElementById('search-area-btn').style.display = 'block';
    });
    findMap.addListener("zoom_changed", () => {
        document.getElementById('search-area-btn').style.display = 'block';
    });

    // Geolocation
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const pos = { lat: position.coords.latitude, lng: position.coords.longitude };
                reportMap.setCenter(pos);
                findMap.setCenter(pos);
            }
        );
    }
}

// Ensure initMaps is globally available for the Google Maps callback
window.initMap = initMaps;

function switchTab(mode) {
    currentMode = mode;

    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`button[onclick="switchTab('${mode}')"]`).classList.add('active');

    document.querySelectorAll('.section-content').forEach(el => el.classList.remove('active'));
    document.getElementById(`${mode}-section`).classList.add('active');

    if (mode === 'find') {
        // Resize map trigger because it was hidden
        if (findMap) google.maps.event.trigger(findMap, "resize");
        if (document.getElementById('sightings-list').children.length === 0) {
            searchCurrentArea(); // Initial load
        }
    }
}

function placeReportMarker(latLng) {
    if (reportMarker) {
        reportMarker.setPosition(latLng);
    } else {
        reportMarker = new google.maps.Marker({
            position: latLng,
            map: reportMap,
            animation: google.maps.Animation.DROP,
            icon: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png'
        });
    }
    reportMap.panTo(latLng);
    document.getElementById('lat').value = latLng.lat();
    document.getElementById('lng').value = latLng.lng();
}

// --- Find Logic ---

function searchCurrentArea() {
    document.getElementById('search-area-btn').style.display = 'none';
    resetAndFetch();
}

function resetAndFetch() {
    document.getElementById('sightings-list').innerHTML = '';
    clearSightingMarkers();
    nextCursor = null;
    fetchSightings();
}

async function fetchSightings() {
    if (isLoading) return;
    isLoading = true;

    const listContainer = document.getElementById('sightings-list');
    // Show loading if empty
    if (listContainer.children.length === 0) {
        listContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#888;">Scanning area...</div>';
    }

    try {
        // Params
        const bounds = findMap.getBounds();
        const rangeVal = document.getElementById('filter-date-range').value;

        const params = new URLSearchParams();
        if (bounds) {
            const ne = bounds.getNorthEast();
            const sw = bounds.getSouthWest();
            params.append('north', ne.lat());
            params.append('south', sw.lat());
            params.append('east', ne.lng());
            params.append('west', sw.lng());
        }

        // Calculate Date Range
        if (rangeVal !== 'all') {
            const days = parseInt(rangeVal);
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - days);
            // Format YYYY-MM-DD
            const startStr = startDate.toISOString().split('T')[0];
            params.append('start_date', startStr);
        }

        if (nextCursor) params.append('cursor', nextCursor);

        const response = await fetch(`/api/sightings?${params.toString()}`);
        const result = await response.json();

        if (listContainer.innerHTML.includes('Scanning area...')) {
            listContainer.innerHTML = '';
        }

        if (result.error) {
            showNotification('Error loading sightings', 'error');
            return;
        }

        // Process Data
        const sightings = result.data || [];
        nextCursor = result.next_cursor;

        if (sightings.length === 0 && listContainer.children.length === 0) {
            listContainer.innerHTML = '<div style="text-align:center; padding:20px;">No dogs found in this area/date range.</div>';
        }

        sightings.forEach(sighting => {
            renderSighting(sighting);
        });

        // Pagination Btn
        const loadMoreBtn = document.getElementById('load-more-btn');
        if (nextCursor) {
            loadMoreBtn.classList.remove('hidden');
        } else {
            loadMoreBtn.classList.add('hidden');
        }

    } catch (error) {
        console.error("Fetch error:", error);
        showNotification('Network error', 'error');
    } finally {
        isLoading = false;
    }
}

function loadMore() {
    fetchSightings();
}

function renderSighting(sighting) {
    const listContainer = document.getElementById('sightings-list');

    // 1. List Card
    const card = document.createElement('div');
    card.className = 'sighting-card';

    const locText = sighting.location_details ?
        (sighting.location_details.city || sighting.location_details.region || 'Unknown')
        : 'Unknown';

    // Highlight marker on hover
    card.onmouseenter = () => highlightMarker(sighting.id, true);
    card.onmouseleave = () => highlightMarker(sighting.id, false);
    card.onclick = () => {
        findMap.panTo(sighting.location);
        findMap.setZoom(15);
        infoWindow.open(findMap, marker);
    };

    // Safe DOM creation for Card
    const img = document.createElement('img');
    img.src = sighting.image_url.startsWith('gs://') ? '#' : sighting.image_url;
    img.alt = 'Dog';
    img.onerror = function () { this.src = '/static/placeholder.png'; };
    card.appendChild(img);

    const infoDiv = document.createElement('div');
    infoDiv.className = 'sighting-info';

    const locDiv = document.createElement('div');
    locDiv.className = 'sighting-loc';
    locDiv.textContent = locText;
    infoDiv.appendChild(locDiv);

    const dateDiv = document.createElement('div');
    dateDiv.className = 'sighting-date';
    dateDiv.textContent = `Sighted: ${sighting.sighting_date}`;
    infoDiv.appendChild(dateDiv);

    if (sighting.comments) {
        const commentDiv = document.createElement('div');
        commentDiv.style.cssText = "font-size:0.8rem; color:#666; margin-top:4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;";
        commentDiv.textContent = sighting.comments;
        infoDiv.appendChild(commentDiv);
    }
    card.appendChild(infoDiv);
    listContainer.appendChild(card);

    // 2. Map Marker
    const marker = new google.maps.Marker({
        position: sighting.location,
        map: findMap,
        title: locText,
        icon: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png'
    });

    // Info Window - Responsive sizing & Safe DOM creation
    const isMobile = window.innerWidth <= 640;
    const infoWidth = isMobile ? 160 : 240;

    const iwContent = document.createElement('div');
    iwContent.style.width = infoWidth + 'px';
    iwContent.style.maxWidth = infoWidth + 'px';

    const iwImg = document.createElement('img');
    iwImg.src = sighting.image_url.startsWith('gs://') ? '#' : sighting.image_url;
    iwImg.onerror = function () { this.src = '/static/placeholder.png'; };
    iwImg.style.cssText = `width:100%;height:${isMobile ? 70 : 140}px;object-fit:cover;border-radius:4px;margin-bottom:6px;`;
    iwContent.appendChild(iwImg);

    const iwLoc = document.createElement('div');
    iwLoc.textContent = locText;
    iwLoc.style.cssText = `font-weight:600; font-size:${isMobile ? '0.85rem' : '1rem'}; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;`;
    iwContent.appendChild(iwLoc);

    const iwDate = document.createElement('div');
    iwDate.textContent = sighting.sighting_date;
    iwDate.style.cssText = `color:#666; font-size:${isMobile ? '0.75rem' : '0.85rem'};`;
    iwContent.appendChild(iwDate);

    if (sighting.comments && !isMobile) {
        const iwComment = document.createElement('div');
        iwComment.textContent = `"${sighting.comments.substring(0, 60)}${sighting.comments.length > 60 ? '...' : ''}"`;
        iwComment.style.cssText = `margin-top:6px; padding-top:6px; border-top:1px solid #eee; font-size:${isMobile ? '0.75rem' : '0.85rem'}; color:#333; font-style:italic; max-height:40px; overflow:hidden;`;
        iwContent.appendChild(iwComment);
    }

    const infoWindow = new google.maps.InfoWindow({
        content: iwContent,
        maxWidth: infoWidth + 20
    });

    marker.addListener('click', () => {
        infoWindow.open(findMap, marker);
    });

    // Store ref for highlighting
    sightingMarkers.push({ id: sighting.id, marker: marker });
}

function clearSightingMarkers() {
    sightingMarkers.forEach(item => item.marker.setMap(null));
    sightingMarkers = [];
}

function highlightMarker(id, active) {
    const item = sightingMarkers.find(x => x.id === id);
    if (item) {
        if (active) {
            item.marker.setAnimation(google.maps.Animation.BOUNCE);
            // Stop bounce after a short time
            setTimeout(() => item.marker.setAnimation(null), 700);
        } else {
            item.marker.setAnimation(null);
        }
    }
}

function showNotification(message, type) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.remove('hidden');
    setTimeout(() => { notification.classList.add('hidden'); }, 5000);
}

// --- Utils & Event Listeners ---

document.addEventListener('DOMContentLoaded', () => {
    // Set default report date
    const dateInput = document.getElementById('date');
    if (dateInput) dateInput.valueAsDate = new Date();

    // File input
    const imageInput = document.getElementById('image');
    if (imageInput) {
        imageInput.addEventListener('change', function (e) {
            const fileName = e.target.files[0] ? e.target.files[0].name : "No file chosen";
            document.getElementById('file-name').textContent = fileName;
        });
    }

    // Report Form
    const sightingForm = document.getElementById('sighting-form');
    if (sightingForm) {
        sightingForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const lat = document.getElementById('lat').value;
            const lng = document.getElementById('lng').value;
            const date = document.getElementById('date').value;
            const comments = document.getElementById('comments').value;
            const imageFile = document.getElementById('image').files[0];

            if (!lat || !lng) {
                showNotification('Please select a location on the map.', 'error');
                return;
            }

            if (!imageFile) {
                showNotification('Please upload an image.', 'error');
                return;
            }

            const submitBtn = document.getElementById('submit-btn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';
            const formData = new FormData();
            formData.append('lat', lat);
            formData.append('lng', lng);
            formData.append('date', date);
            formData.append('comments', comments);
            formData.append('image', imageFile);

            try {
                const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
                const response = await fetch('/submit', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                });
                const result = await response.json();
                if (response.ok) {
                    showNotification('Report submitted successfully!', 'success');
                    sightingForm.reset();
                    document.getElementById('file-name').textContent = "No file chosen";
                    if (reportMarker) reportMarker.setMap(null);
                    reportMarker = null;
                    document.getElementById('date').valueAsDate = new Date();
                } else {
                    showNotification(result.error || 'Error', 'error');
                }
            } catch (error) {
                showNotification('Network error.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Submit Report';
            }
        });
    }
});
