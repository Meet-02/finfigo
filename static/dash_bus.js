document.addEventListener("DOMContentLoaded", function() {

    // --- Single-Page Navigation Logic ---
    const navLinks = document.querySelectorAll('.nav-link[data-page]');
    const pageContents = document.querySelectorAll('.page-content');

    function handleLinkClick(event) {
        event.preventDefault();
        const pageId = this.getAttribute('data-page');
        if (!pageId) return;

        navLinks.forEach(navLink => navLink.classList.remove('active'));
        this.classList.add('active');

        pageContents.forEach(content => {
            content.style.display = (content.id === pageId + '-content') ? 'block' : 'none';
        });
    }

    navLinks.forEach(link => {
        link.addEventListener('click', handleLinkClick);
    });

    // --- Enhanced Search Bar for Product GST Page ---
    const searchInput = document.getElementById('product-search');
    const gstCards = document.querySelectorAll('.gst-card');
    const clearSearchBtn = document.querySelector('.clear-search-btn');
    const noResultsMessage = document.getElementById('no-results-message');

    if (searchInput && gstCards.length > 0) {
        
        function handleSearch() {
            const searchTerm = searchInput.value.toLowerCase().trim();
            let visibleCardsCount = 0;

            if (searchTerm.length > 0) {
                clearSearchBtn.classList.add('visible');
            } else {
                clearSearchBtn.classList.remove('visible');
            }
            
            gstCards.forEach(card => {
                const cardText = card.textContent.toLowerCase();
                const isMatch = cardText.includes(searchTerm);
                card.style.display = isMatch ? 'block' : 'none';
                if (isMatch) {
                    visibleCardsCount++;
                }
            });

            if (visibleCardsCount === 0 && searchTerm.length > 0) {
                noResultsMessage.textContent = `No results found for "${searchInput.value}"`;
                noResultsMessage.style.display = 'block';
            } else {
                noResultsMessage.style.display = 'none';
            }
        }

        searchInput.addEventListener('input', handleSearch);

        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', function() {
                searchInput.value = '';
                handleSearch();
                searchInput.focus();
            });
        }
    }
});