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
        
        // Function to handle the search logic
        function handleSearch() {
            const searchTerm = searchInput.value.toLowerCase().trim();
            let visibleCardsCount = 0;

            // Show/hide the clear button based on input
            if (searchTerm.length > 0) {
                clearSearchBtn.classList.add('visible');
            } else {
                clearSearchBtn.classList.remove('visible');
            }
            
            // Filter cards based on search term
            gstCards.forEach(card => {
                const cardText = card.textContent.toLowerCase();
                const isMatch = cardText.includes(searchTerm);
                card.style.display = isMatch ? 'block' : 'none';
                if (isMatch) {
                    visibleCardsCount++;
                }
            });

            // Show or hide the "no results" message
            if (visibleCardsCount === 0) {
                noResultsMessage.textContent = `No results found for "${searchInput.value}"`;
                noResultsMessage.style.display = 'block';
            } else {
                noResultsMessage.style.display = 'none';
            }
        }

        // Event listener for user typing in the search bar
        searchInput.addEventListener('input', handleSearch);

        // Event listener for the clear button
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', function() {
                searchInput.value = ''; // Clear the input field
                handleSearch(); // Rerun the search logic to reset the view
                searchInput.focus(); // Put the cursor back in the search bar
            });
        }
    }
});