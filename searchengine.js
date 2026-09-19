// Live Dropdown Search Engine Logic (Index Cards Synchronized)
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
                    
                    // Card ke onclick attribute se exact target URL nikalna
                    const onclickAttr = card.getAttribute('onclick');
                    let targetUrl = '#';
                    
                    if (onclickAttr) {
                        const match = onclickAttr.match(/'([^']+)'/);
                        if (match) {
                            let slug = match[1];
                            // Agar openAnimePage function hai toh uske format ke mutabiq videoplayer page URL banana
                            if (onclickAttr.includes('openAnimePage')) {
                                targetUrl = slug.toLowerCase() + '_videoplayer.html';
                            } else {
                                targetUrl = slug; // Direct link jaise ki hentai card ke liye hai
                            }
                        }
                    }

                    resultsHTML += `
                        <div class="search-item" onclick="window.location.href='${targetUrl}'" style="padding: 10px 14px; cursor: pointer; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid #2d2d3d; font-size: 13px; color: #e5e7eb; transition: background 0.2s;">
                            <span class="${badgeClass}" style="background: rgba(255,85,0,0.2); color: #ff5500; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">${badgeText}</span>
                            <span style="font-weight: 500;">${title}</span>
                        </div>
                    `;
                    count++;
                }
            }
        });

        if (resultsHTML !== '') {
            searchDropdown.innerHTML = resultsHTML + `<div class="search-item more-results-item" style="padding: 8px 14px; text-align: center; font-size: 11px; color: #9ca3af; background: #151522;">More results</div>`;
            searchDropdown.style.display = 'block';
        } else {
            searchDropdown.innerHTML = `<div class="search-item no-match-item" style="padding: 10px 14px; font-size: 12px; color: #9ca3af;">No results found</div>`;
            searchDropdown.style.display = 'block';
        }
    });

    // Input ke baahar click karne par dropdown hide ho jaye
    document.addEventListener('click', function(e) {
        if (!globalSearchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
            searchDropdown.style.display = 'none';
        }
    });
}
