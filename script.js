// Private Consumet API Endpoint
const API_BASE_URL = 'https://api-consumet-org-tau-five.vercel.app';

// 1. Open Player Page Function
function openAnimePage(animeSlug) {
    if(!animeSlug) return;
    const targetPage = animeSlug.toLowerCase() + '_videoplayer.html';
    window.location.href = targetPage;
}

// 2. Sidebar Drawer Open/Close Logic
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar && overlay) {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
    }
}

// 3. Open Age Limit Modal
function openAgeModal() {
    toggleSidebar(); // Pehle sidebar close karenge
    const modal = document.getElementById('ageModal');
    if (modal) {
        modal.classList.add('active');
    }
}

// 4. Confirm Age (18+)
function confirmAge(is18Plus) {
    const modal = document.getElementById('ageModal');
    if (modal) {
        modal.classList.remove('active');
    }

    if (is18Plus) {
        loadHentaiPage();
    } else {
        alert("Aap is section ko access nahi kar sakte.");
    }
}

// 5. Load Only Hentai Content
function loadHentaiPage() {
    const cards = document.querySelectorAll('.anime-card');
    const heroSection = document.getElementById('heroSection');
    const sectionTitle = document.getElementById('sectionTitle');

    // Hero section hide karna
    if(heroSection) heroSection.style.display = 'none';

    // Title change karna
    if(sectionTitle) {
        sectionTitle.innerHTML = '<i class="fa-solid fa-fire" style="color:#ff0055;"></i> 18+ Hentai Collection';
    }

    let hentaiCount = 0;

    cards.forEach(card => {
        const tags = card.getAttribute('data-tags') || '';
        if (tags.toLowerCase().includes('hentai')) {
            card.style.display = 'flex';
            hentaiCount++;
        } else {
            card.style.display = 'none';
        }
    });

    const noResults = document.getElementById('noResults');
    if (noResults) {
        if (hentaiCount === 0) {
            noResults.innerText = "No Hentai content found.";
            noResults.style.display = 'block';
        } else {
            noResults.style.display = 'none';
        }
    }
}

// 6. Universal Cross-Page Search Engine Logic
const globalSearchInput = document.getElementById('globalSearchInput');
const globalSearchBtn = document.getElementById('globalSearchBtn');

function performSearch() {
    if (!globalSearchInput) return;
    const query = globalSearchInput.value.trim().toLowerCase();
    
    if (query === "") return;

    // Check karein ki user index.html par hai ya kisi video player page par
    const isMainPage = document.getElementById('animeGrid') !== null;

    if (isMainPage) {
        // Agar user main page par hai, toh wahi par cards filter kar do
        const cards = document.querySelectorAll('.anime-card');
        let matchCount = 0;

        cards.forEach(card => {
            const titleElement = card.querySelector('.card-title');
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

        const noResults = document.getElementById('noResults');
        if (noResults) {
            noResults.style.display = (matchCount === 0) ? "block" : "none";
        }
    } else {
        // Agar user kisi video player page par hai, toh search query ke sath main page par redirect kar do
        window.location.href = `index.html?search=${encodeURIComponent(query)}`;
    }
}

// Event Listeners for Input (Enter key) and Magnifying Glass Click
if (globalSearchInput) {
    globalSearchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

if (globalSearchBtn) {
    globalSearchBtn.addEventListener('click', performSearch);
}

// Auto-handle search query if redirected from another page with URL parameters
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const searchQuery = urlParams.get('search');
    
    if (searchQuery && globalSearchInput) {
        globalSearchInput.value = searchQuery;
        
        const cards = document.querySelectorAll('.anime-card');
        let matchCount = 0;
        
        cards.forEach(card => {
            const titleElement = card.querySelector('.card-title');
            if (titleElement) {
                const title = titleElement.innerText.toLowerCase();
                if (title.includes(searchQuery.toLowerCase())) {
                    card.style.display = "flex";
                    matchCount++;
                } else {
                    card.style.display = "none";
                }
            }
        });

        const noResults = document.getElementById('noResults');
        if (noResults) {
            noResults.style.display = (matchCount === 0) ? "block" : "none";
        }
    }
});
