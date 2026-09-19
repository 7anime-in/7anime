// Automatically inject search dropdown CSS via JavaScript
const searchStyle = document.createElement('style');
searchStyle.innerHTML = `
    .search-box {
        position: relative !important;
    }
    .search-dropdown {
        position: absolute !important;
        top: 100% !important;
        right: 0 !important;
        width: 260px !important;
        background-color: #151522 !important;
        border: 1px solid #2d2d3d !important;
        border-radius: 8px !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
        z-index: 1000 !important;
        max-height: 250px !important;
        overflow-y: auto !important;
        margin-top: 6px !important;
        display: none;
    }
    .search-item {
        padding: 10px 14px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 10px;
        border-bottom: 1px solid #2d2d3d;
        font-size: 13px;
        color: #e5e7eb;
        transition: background 0.2s;
    }
    .search-item:hover {
        background-color: #1a1a2b;
    }
`;
document.head.appendChild(searchStyle);

// Live Dropdown Search Engine Logic
const globalSearchInput = document.getElementById('globalSearchInput');
const searchDropdown = document.getElementById('searchResultsDropdown');

if (globalSearchInput && searchDropdown) {
    globalSearchInput.addEventListener('input', function() {
        const query = this.value.trim().toLowerCase();
        
        if (query.length === 0) {
            searchDropdown.style.display = 'none';
            searchDropdown.innerHTML = '';
            return;
        }

        const cards = document.querySelectorAll('.anime-card');
        let resultsHTML = '';
        let count = 0;

        cards.forEach(card => {
            const titleEl = card.querySelector('.card-title');
            const tagsEl = card.querySelector('.card-tags');
            if (titleEl) {
                const title = titleEl.innerText;
                if (title.toLowerCase().includes(query) && count < 5) {
                    const tagsText = tagsEl ? tagsEl.innerText.toLowerCase() : '';
                    const isMovie = tagsText.includes('movie') || title.toLowerCase().includes('movie');
                    const badgeClass = isMovie ? 'search-badge-movie' : 'search-badge-series';
                    const badgeText = isMovie ? 'MOVIE' : 'SERIES';
                    
                    const onclickAttr = card.getAttribute('onclick');
                    let targetUrl = '#';
                    
                    if (onclickAttr) {
                        const match = onclickAttr.match(/'([^']+)'/);
                        if (match) {
                            let slug = match[1];
                            if (onclickAttr.includes('openAnimePage')) {
                                targetUrl = slug.toLowerCase() + '_videoplayer.html';
                            } else {
                                targetUrl = slug;
                            }
                        }
                    }

                    resultsHTML += `
                        <div class="search-item" onclick="window.location.href='${targetUrl}'">
                            <span class="${badgeClass}" style="background: rgba(255,85,0,0.2); color: #ff5500; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">${badgeText}</span>
                            <span style="font-weight: 500;">${title}</span>
                        </div>
                    `;
                    count++;
                }
            }
        });

        if (resultsHTML !== '') {
            searchDropdown.innerHTML = resultsHTML + `<div class="search-item" style="justify-content: center; font-size: 11px; color: #9ca3af; background: #151522; cursor: default;">More results</div>`;
            searchDropdown.style.display = 'block';
        } else {
            searchDropdown.innerHTML = `<div class="search-item" style="color: #9ca3af; cursor: default;">No results found</div>`;
            searchDropdown.style.display = 'block';
        }
    });

    document.addEventListener('click', function(e) {
        if (!globalSearchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
            searchDropdown.style.display = 'none';
        }
    });
}
