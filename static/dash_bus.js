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
    const gstResultsContainer = document.getElementById('gst-results-container');
    const clearSearchBtn = document.querySelector('.clear-search-btn');
    const noResultsMessage = document.getElementById('no-results-message');

    if (searchInput && gstResultsContainer) {

        function displayResults(results) {
            gstResultsContainer.innerHTML = '';
            if (results && results.length > 0) {
                results.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'gst-card';
                    card.innerHTML = `
                        <h3>${item.description || 'N/A'}</h3>
                        <p>Chapter: ${item.chapter_heading || 'N/A'}</p>
                        <p>CGST: ${item.cgst_rate || 0}%, SGST: ${item.sgst_rate || 0}%, IGST: ${item.igst_rate || 0}%</p>
                    `;
                    gstResultsContainer.appendChild(card);
                });
                noResultsMessage.style.display = 'none';
            } else {
                noResultsMessage.textContent = `No results found for "${searchInput.value}"`;
                noResultsMessage.style.display = 'block';
            }
        }

        function handleSearch() {
            const searchTerm = searchInput.value.trim();

            if (searchTerm.length > 0) {
                clearSearchBtn.classList.add('visible');
                // Call the API
                fetch(`/gst_rates?data=${encodeURIComponent(searchTerm)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            displayResults([]);
                        } else {
                            displayResults(data);
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching GST rates:', error);
                        displayResults([]);
                    });
            } else {
                clearSearchBtn.classList.remove('visible');
                gstResultsContainer.innerHTML = '';
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