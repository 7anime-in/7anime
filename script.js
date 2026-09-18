// Private Consumet API Endpoint
const API_BASE_URL = 'https://api-consumet-org-tau-five.vercel.app';

// 1. Target URL Dynamic Navigation
function openAnimePage(animeSlug) {
    if(!animeSlug) return;
    const targetPage = animeSlug.toLowerCase() + '_videoplayer.html';
    window.location.href = targetPage;
}

// 2. Sidebar Drawer Toggle
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}

// 3. 18+ Age Limit Modal Logic
function openAgeModal() {
    toggleSidebar(); // Close sidebar
    document.getElementById('ageModal').classList.add('active');
}

function confirmAge(is18Plus) {
    const ageModal = document.getElementById('ageModal');
    ageModal.classList.remove('active');

    if (is18Plus) {
        loadHentaiPage();
    } else {
        alert("Aap is section ko access nahi kar sakte.");
    }
}

// 4. Hentai Content Filter Logic
function loadHentaiPage() {
    const cards = document.querySelectorAll('.anime-card');
    const heroSection = document.getElementById('heroSection');
    const sectionTitle = document.getElementById('sectionTitle');

    // Hero section hide karna
    if(heroSection) heroSection.style.display = 'none';

    // Title update karna
    if(sectionTitle) {
        sectionTitle.innerHTML = '<i class="fa-solid fa-fire" style="color:#ff0055;"></i> 18+ Hentai Collection';
    }

    let hentaiFound = 0;

    cards.forEach(card => {
        const tags = card.getAttribute('data-tags') || '';
        if (tags.toLowerCase().includes('hentai')) {
            card.style.display = 'flex';
            hentaiFound++;
        } else {
            card.style.display = 'none';
        }
    });

    const noResults = document.getElementById('noResults');
    if (noResults) {
        if (hentaiFound === 0) {
            noResults.innerText = "No Hentai content found.";
            noResults.style.display = 'block';
        } else {
            noResults.style.display = 'none';
        }
    }
}

// 5. Search Engine Logic
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
            noResults.innerText = "No anime found matching your search.";
            noResults.style.display = "block";
        } else {
            noResults.style.display = "none";
        }
    }
}

if(searchInput) {
    searchInput.addEventListener('input', executeSearch);
}
