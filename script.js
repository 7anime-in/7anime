// Base Configuration URLs
const API_BASE_URL = 'https://api-consumet-org-tau-five.vercel.app';
const BACKEND_URL = 'https://sevenanime-http-bot.onrender.com';

// Global Player State Variables
let currentSeason = 1;
let currentEpisode = 1;
let currentServer = 'fast';
let currentQuality = '720p';

// ----------------------------------------------------
// 1. PAGE NAVIGATION & SIDEBAR CONTROLS
// ----------------------------------------------------

/**
 * Open Anime Detail / Player Page
 * @param {string} animeSlug 
 */
function openAnimePage(animeSlug) {
    if (!animeSlug) return;
    const cleanSlug = animeSlug.toLowerCase().trim().replace(/\s+/g, '_');
    window.location.href = `videoplayer.html?anime=${cleanSlug}`;
}

/**
 * Toggle Sidebar Drawer Open / Close
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar && overlay) {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
    }
}

// ----------------------------------------------------
// 2. AGE VERIFICATION & 18+ FILTER (HENTAI)
// ----------------------------------------------------

/**
 * Open 18+ Verification Modal
 */
function openAgeModal() {
    toggleSidebar(); 
    const modal = document.getElementById('ageModal');
    if (modal) {
        modal.classList.add('active');
    }
}

/**
 * Handle Age Confirmation Logic
 * @param {boolean} is18Plus 
 */
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

/**
 * Filter and Render Only 18+ / Hentai Content
 */
function loadHentaiPage() {
    const cards = document.querySelectorAll('.anime-card');
    const heroSection = document.getElementById('heroSection');
    const sectionTitle = document.getElementById('sectionTitle');

    if (heroSection) heroSection.style.display = 'none';

    if (sectionTitle) {
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

// ----------------------------------------------------
// 3. VIDEO PLAYER CONTROLS & SPINNER HELPERS
// ----------------------------------------------------

/**
 * Hide Video Loading Spinner
 */
function hideSpinner() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.style.display = 'none';
    }
}

/**
 * Show Video Loading Spinner
 */
function showSpinner() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.style.display = 'flex';
    }
}

/**
 * Change Video Quality UI State
 * @param {string} quality ('1080p' | '720p' | '480p')
 */
function changeQuality(quality) {
    currentQuality = quality;

    document.querySelectorAll('.quality-btn').forEach(btn => {
        if (btn.innerText.trim() === quality) {
            btn.className = "quality-btn bg-[#ff5500] text-white border border-[#ff5500] px-2 py-0.5 rounded text-xs font-bold transition cursor-pointer";
        } else {
            btn.className = "quality-btn bg-[#1a1a2b] hover:bg-gray-800 text-gray-300 border border-gray-700 px-2 py-0.5 rounded text-xs font-medium transition cursor-pointer";
        }
    });

    if (typeof selectEpisode === 'function') {
        selectEpisode(currentEpisode);
    }
}

/**
 * Switch Streaming Server
 * @param {string} serverName 
 */
function switchServer(serverName) {
    currentServer = serverName;
    const btn1 = document.getElementById('serverBtn1');
    showSpinner();

    if (btn1) {
        btn1.className = "bg-[#ff5500] text-white px-3 py-1 rounded-lg text-xs font-bold transition shadow cursor-pointer";
    }

    if (typeof selectEpisode === 'function') {
        selectEpisode(currentEpisode);
    }
}

/**
 * Jump to Next or Previous Episode
 * @param {string} direction ('next' | 'prev')
 */
function changeEpisode(direction) {
    if (direction === 'next') {
        if (typeof selectEpisode === 'function') {
            selectEpisode(currentEpisode + 1);
        }
    } else if (direction === 'prev') {
        if (currentEpisode > 1) {
            if (typeof selectEpisode === 'function') {
                selectEpisode(currentEpisode - 1);
            }
        }
    }
}

// ----------------------------------------------------
// 4. LIVE SEARCH & AUTOCOMPLETE LOGIC
// ----------------------------------------------------

/**
 * Initialize Global Live Search Input Bar
 */
function initGlobalSearch() {
    const searchInput = document.getElementById('globalSearchInput');
    const dropdown = document.getElementById('searchResultsDropdown');

    if (!searchInput || !dropdown) return;

    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        clearTimeout(debounceTimer);

        if (query.length < 2) {
            dropdown.style.display = 'none';
            dropdown.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const res = await fetch(`${BACKEND_URL}/api/all-anime`);
                if (!res.ok) return;

                const allAnime = await res.json();
                const matchedKeys = Object.keys(allAnime).filter(key => 
                    key.includes(query.replace(/\s+/g, '_')) || 
                    (allAnime[key].title && allAnime[key].title.toLowerCase().includes(query))
                );

                if (matchedKeys.length === 0) {
                    dropdown.innerHTML = `<div class="p-3 text-xs text-gray-400">No results found</div>`;
                } else {
                    dropdown.innerHTML = matchedKeys.map(key => {
                        const item = allAnime[key];
                        return `
                            <div onclick="openAnimePage('${key}')" class="p-2.5 hover:bg-[#ff5500]/20 cursor-pointer flex items-center justify-between border-b border-gray-800/50 text-xs">
                                <span class="font-semibold text-gray-200">${item.title}</span>
                                <span class="text-[10px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">Anime</span>
                            </div>
                        `;
                    }).join('');
                }

                dropdown.style.display = 'block';
            } catch (err) {
                console.error("Search Error:", err);
            }
        }, 300);
    });

    // Close Dropdown On Outside Click
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

// ----------------------------------------------------
// 5. GLOBAL DOM CONTENT LOADED INITIALIZATION
// ----------------------------------------------------
window.addEventListener('DOMContentLoaded', () => {
    initGlobalSearch();
});
