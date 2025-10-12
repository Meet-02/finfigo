document.addEventListener("DOMContentLoaded", function() {

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

    const searchInput = document.getElementById('product-search');
    const gstInfoContainer = document.querySelector('.gst-info-container'); 
    const noResultsMessage = document.getElementById('no-results-message');
    const clearSearchBtn = document.querySelector('.clear-search-btn');

    if (searchInput) {
        
        if (gstInfoContainer) {
            gstInfoContainer.innerHTML = ''; 
        }

        /**
         * Fetches GST rates dynamically from the Flask API.
         * @param {string} searchTerm - The product name or chapter heading to search.
         */
        async function fetchGstRates(searchTerm) {
            if (searchTerm.length < 2) {
                if (gstInfoContainer) gstInfoContainer.innerHTML = '';
                noResultsMessage.style.display = 'none';
                return; 
            }

            const endpoint = `/gst_rates?data=${encodeURIComponent(searchTerm)}`;
            
            try {
                const response = await fetch(endpoint);
                const data = await response.json();

                if (gstInfoContainer) gstInfoContainer.innerHTML = '';

                if (response.status === 404) {
                    noResultsMessage.textContent = `No results found for "${searchTerm}"`;
                    noResultsMessage.style.display = 'block';
                } else if (response.ok) {
                    noResultsMessage.style.display = 'none';
                    
                    data.forEach(item => {
                        const card = document.createElement('div');
                        card.classList.add('gst-card', 'result-card');
                        card.innerHTML = `
                            <h3>Chapter: ${item.chapter_heading}</h3>
                            <p><strong>Description:</strong> ${item.description}</p>
                            <p class="rate"><strong>IGST Rate:</strong> ${item.igst_rate}% (Integrated GST)</p>
                            <p class="sub-rate">CGST: ${item.cgst_rate}% | SGST: ${item.sgst_rate}%</p>
                        `;
                        if (gstInfoContainer) gstInfoContainer.appendChild(card);
                    });
                } else {
                     // Handle general API/Database errors (status 500)
                    noResultsMessage.textContent = `Error fetching data: ${data.details || data.error}`;
                    noResultsMessage.style.display = 'block';
                }
            } catch (error) {
                console.error('Fetch network error:', error);
                noResultsMessage.textContent = 'Network or server connection failed.';
                noResultsMessage.style.display = 'block';
            }
        }

        function handleInput() {
            const searchTerm = searchInput.value.trim();

            if (searchTerm.length > 0) {
                clearSearchBtn.classList.add('visible');
            } else {
                clearSearchBtn.classList.remove('visible');
                if (gstInfoContainer) gstInfoContainer.innerHTML = '';
                noResultsMessage.style.display = 'none';
            }

            fetchGstRates(searchTerm);
        }

        searchInput.addEventListener('input', handleInput);

        // Event listener for the clear button
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', function() {
                searchInput.value = ''; 
                handleInput(); 
                searchInput.focus();
            });
        }
    }

});