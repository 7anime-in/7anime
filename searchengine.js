// 6. Naya Live Dropdown Search Engine Logic
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
                    // Movie ya Series identify karne ke liye tags check karein
                    const tagsText = tagsEl ? tagsEl.innerText.toLowerCase() : '';
                    const isMovie = tagsText.includes('movie') || title.toLowerCase().includes('movie');
                    const badgeClass = isMovie ? 'search-badge-movie' : 'search-badge-series';
                    const badgeText = isMovie ? 'MOVIE' : 'SERIES';
                    
                    // Card ka onclick action nikalna
                    const onclickAttr = card.getAttribute('onclick');
                    let targetUrl = '#';
                    if (onclickAttr && onclickAttr.includes('openAnimePage')) {
                        const match = onclickAttr.match(/'([^']+)'/);
                        if (match) targetUrl = match[1].toLowerCase() + '_videoplayer.html';
                    } else if (onclickAttr) {
                        const match = onclickAttr.match(/'([^']+)'/);
                        if (match) targetUrl = match[1];
                    }

                    resultsHTML += `
                        <div class="search-item" onclick="window.location.href='${targetUrl}'">
                            <span class="${badgeClass}">${badgeText}</span>
                            <span>${title}</span>
                        </div>
                    `;
                    count++;
                }
            }
        });

        if (resultsHTML !== '') {
            searchDropdown.innerHTML = resultsHTML + `<div class="search-item more-results-item">More results</div>`;
            searchDropdown.style.display = 'block';
        } else {
            searchDropdown.innerHTML = `<div class="search-item no-match-item">No results found</div>`;
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
