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

