// Private Consumet API Endpoint (Vercel)
const API_BASE_URL = 'https://api-consumet-org-tau-five.vercel.app';

// 1. Target URL Dynamic Navigation
function openAnimePage(animeSlug) {
    if(!animeSlug) return;
    const targetPage = animeSlug.toLowerCase() + '_videoplayer.html';
    window.location.href = targetPage;
}

// 2. Real-time Live Search Engine Logic
const searchInput = document.getElementById('searchInput');
const noResults = document.getElementById('noResults');

function executeSearch() {
    const query = searchInput.value.trim().toLowerCase();
    const cards = document.querySelectorAll('.anime-card');
    let matchCount = 0;

    cards.forEach(card => {
        const title = card.querySelector('.card-title').innerText.toLowerCase();
        if (title.includes(query)) {
            card.style.display = "block";
            matchCount++;
        } else {
            card.style.display = "none";
        }
    });

    if (matchCount === 0 && query !== "") {
        noResults.style.display = "block";
    } else {
        noResults.style.display = "none";
    }
}

if(searchInput) {
    searchInput.addEventListener('input', executeSearch);
}

// 3. API Fetch Helper Example (Future use ke liye)
async function fetchAnimeData(animeQuery) {
    try {
        const response = await fetch(`${API_BASE_URL}/anime/gogoanime/${animeQuery}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API Error:', error);
    }
}
