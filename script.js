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
    if (!searchInput) return;
    const query = searchInput.value.trim().toLowerCase();
    const cards = document.querySelectorAll('.anime-card');
    let matchCount = 0;

    cards.forEach(card => {
        const titleElement = card.querySelector('.card-title') || card.querySelector('.anime-title');
        if (titleElement) {
            const title = titleElement.innerText.toLowerCase();
            if (title.includes(query)) {
                card.style.display = "flex";
                matchCount++;
            } else {
                card.style.display = "none";
            }
        }
    });

    if (noResults) {
        if (matchCount === 0 && query !== "") {
            noResults.style.display = "block";
        } else {
            noResults.style.display = "none";
        }
    }
}

if(searchInput) {
    searchInput.addEventListener('input', executeSearch);
}

// 3. API Fetch Helper (Anime Info & Episode Stream Links)
async function fetchAnimeData(animeQuery) {
    try {
        const response = await fetch(`${API_BASE_URL}/anime/gogoanime/${animeQuery}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API Search Error:', error);
        return null;
    }
}

async function fetchEpisodeStream(episodeId) {
    try {
        const response = await fetch(`${API_BASE_URL}/anime/gogoanime/watch/${episodeId}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API Stream Error:', error);
        return null;
    }
}
