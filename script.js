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
    toggleSidebar(); 
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

    if(heroSection) heroSection.style.display = 'none';

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

// ==========================================
// VIDEO PLAYER, SEASON & EPISODE SWITCHER LOGIC
// ==========================================
let currentSeason = 1;
let currentEpisode = 1;
let currentServer = 'vidhide';

function getEmbedLink(server, season, episode) {
    // Alag-alag seasons ke hisab se video/embed links yahan generate honge
    if (server === 'vidhide') {
        return `https://vidhideembed.su/embed/solo-leveling-s${season}-ep-${episode}`;
    } else {
        return `https://streamhg.com/embed/solo-leveling-s${season}-ep-${episode}`;
    }
}

function switchSeason(seasonNum) {
    currentSeason = Number(seasonNum);
    currentEpisode = 1; // Season badalne par default Episode 1 par set ho jayega

    const btn1 = document.getElementById('seasonBtn1');
    const btn2 = document.getElementById('seasonBtn2');

    if (currentSeason === 1) {
        if (btn1) btn1.className = "bg-[#ff5500] text-white px-3 py-1 rounded-lg text-xs font-bold transition shadow cursor-pointer";
        if (btn2) btn2.className = "bg-[#1a1a2b] hover:bg-gray-800 text-gray-300 border border-gray-700 px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer";
    } else {
        if (btn2) btn2.className = "bg-[#ff5500] text-white px-3 py-1 rounded-lg text-xs font-bold transition shadow cursor-pointer";
        if (btn1) btn1.className = "bg-[#1a1a2b] hover:bg-gray-800 text-gray-300 border border-gray-700 px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer";
    }

    selectEpisode(currentEpisode);
}

function selectEpisode(epNum) {
    currentEpisode = Number(epNum);
    const iframe = document.getElementById('animeVideoPlayer');
    const spinner = document.getElementById('loadingSpinner');
    const text = document.getElementById('currentPlayingText');
    
    if (spinner) spinner.style.display = 'flex';
    if (text) text.innerText = `S${currentSeason} - Episode ${currentEpisode}`;
    
    if (iframe) {
        iframe.src = getEmbedLink(currentServer, currentSeason, currentEpisode);
    }

    // Highlight active episode button correctly
    document.querySelectorAll('.ep-btn').forEach(btn => {
        const btnEp = Number(btn.getAttribute('data-ep'));
        if (btnEp === currentEpisode) {
            btn.className = "ep-btn bg-[#ff5500] text-white border border-[#ff5500] py-2.5 rounded-lg text-xs font-bold transition cursor-pointer";
        } else {
            btn.className = "ep-btn bg-[#1a1a2b] hover:bg-[#ff5500]/30 border border-gray-700 py-2.5 rounded-lg text-xs font-medium transition cursor-pointer";
        }
    });
}

function switchServer(serverName) {
    currentServer = serverName;
    const btn1 = document.getElementById('serverBtn1');
    const btn2 = document.getElementById('serverBtn2');
    const spinner = document.getElementById('loadingSpinner');

    if (spinner) spinner.style.display = 'flex';

    if (serverName === 'vidhide') {
        if (btn1) btn1.className = "bg-[#ff5500] text-white px-3 py-1 rounded-lg text-xs font-bold transition shadow cursor-pointer";
        if (btn2) btn2.className = "bg-[#1a1a2b] hover:bg-gray-800 text-gray-300 border border-gray-700 px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer";
    } else {
        if (btn2) btn2.className = "bg-[#ff5500] text-white px-3 py-1 rounded-lg text-xs font-bold transition shadow cursor-pointer";
        if (btn1) btn1.className = "bg-[#1a1a2b] hover:bg-gray-800 text-gray-300 border border-gray-700 px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer";
    }

    const iframe = document.getElementById('animeVideoPlayer');
    if (iframe) {
        iframe.src = getEmbedLink(currentServer, currentSeason, currentEpisode);
    }
}

function changeEpisode(direction) {
    if (direction === 'next') {
        if (currentEpisode < 12) {
            selectEpisode(currentEpisode + 1);
        }
    } else if (direction === 'prev') {
        if (currentEpisode > 1) {
            selectEpisode(currentEpisode - 1);
        }
    }
}

function hideSpinner() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.style.display = 'none';
    }
}

window.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('animeVideoPlayer')) {
        selectEpisode(1);
    }
});
