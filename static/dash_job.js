document.addEventListener("DOMContentLoaded", function() {

    // --- 1. Single-Page Navigation Logic ---
    const navLinks = document.querySelectorAll('.nav-link[data-page]');
    const pageContents = document.querySelectorAll('.page-content');

    function handleLinkClick(event) {
        event.preventDefault();
        const pageId = this.getAttribute('data-page');
        if (!pageId) return;

        navLinks.forEach(navLink => navLink.classList.remove('active'));
        this.classList.add('active');

        // Logic to show the corresponding content section
        pageContents.forEach(content => {
            content.style.display = (content.id === pageId + '-content') ? 'block' : 'none';
        });
    }

    navLinks.forEach(link => {
        link.addEventListener('click', handleLinkClick);
    });

    // --- 2. Dynamic Search for Product GST Page (Corrected Fetch Logic) ---
    const searchInput = document.getElementById('product-search');
    const gstInfoContainer = document.querySelector('.gst-info-container'); 
    const noResultsMessage = document.getElementById('no-results-message');
    const clearSearchBtn = document.querySelector('.clear-search-btn');

    if (searchInput) {
        
        // Initial setup: Clear the static GST slab cards if they were hardcoded
        if (gstInfoContainer) {
            gstInfoContainer.innerHTML = ''; 
        }

        /**
         * Fetches GST rates dynamically from the Flask API.
         * @param {string} searchTerm - The product name or chapter heading to search.
         */
        async function fetchGstRates(searchTerm) {
            // Only fetch if the term is long enough (e.g., 2 characters or more)
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

        // Function to manage the search bar input and button visibility
        function handleInput() {
            const searchTerm = searchInput.value.trim();

            if (searchTerm.length > 0) {
                clearSearchBtn.classList.add('visible');
            } else {
                clearSearchBtn.classList.remove('visible');
                if (gstInfoContainer) gstInfoContainer.innerHTML = '';
                noResultsMessage.style.display = 'none';
            }
            
            // Execute the API call
            fetchGstRates(searchTerm);
        }
        
        // Event listener for user typing (Input event triggers the search)
        searchInput.addEventListener('input', handleInput);

        // Event listener for the clear button
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', function() {
                searchInput.value = ''; // Clear the input field
                handleInput(); // Rerun the logic to reset the view
                searchInput.focus();
            });
        }
    }
    
    // --- 3. Chart Initialization Logic (Existing Code) ---
    if (typeof Chart !== 'undefined') { // Check if Chart.js is loaded
        const calculationLabels = JSON.parse('{{ labels | tojson }}');
        const grossIncomeData = JSON.parse('{{ gross_income_data | tojson }}');
        const taxData = JSON.parse('{{ tax_data | tojson }}');
        const netIncomeData = JSON.parse('{{ net_income_data | tojson }}');
        
        // Note: The template variables (e.g., {{ labels | tojson }}) assume this JS is rendered
        // via a Flask/Jinja2 template. I've left the placeholder syntax as provided.

        try {
            const revenueCtx = document.getElementById('revenuePieChart').getContext('2d');
            new Chart(revenueCtx, { type: 'line', data: { labels: calculationLabels, datasets: [{ label: 'Gross Income', data: grossIncomeData, fill: true, backgroundColor: 'rgba(0, 123, 255, 0.2)', borderColor: 'rgba(0, 123, 255, 1)', tension: 0.1 }, { label: 'Net Income', data: netIncomeData, fill: true, backgroundColor: 'rgba(40, 167, 69, 0.2)', borderColor: 'rgba(40, 167, 69, 1)', tension: 0.1 }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } } });
        } catch (e) { console.error("Error creating Revenue chart:", e); }
        
        try {
            const taxCtx = document.getElementById('netPayableTaxChart').getContext('2d');
            new Chart(taxCtx, { type: 'bar', data: { labels: calculationLabels, datasets: [{ label: 'Tax Paid (₹)', data: taxData, backgroundColor: 'rgba(220, 53, 69, 0.6)', borderColor: 'rgba(220, 53, 69, 1)', borderWidth: 1, borderRadius: 5 }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } } });
        } catch (e) { console.error("Error creating Tax chart:", e); }
    }
});

const mobileBtn = document.getElementById('mobile-menu-btn');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebar-overlay');
const closeBtn = document.getElementById('sidebar-close');

if (mobileBtn && sidebar && overlay) {
  mobileBtn.addEventListener('click', () => {
    sidebar.classList.add('active');
    overlay.classList.add('active');
    document.body.classList.add('sidebar-open');
  });

  overlay.addEventListener('click', () => {
    sidebar.classList.remove('active');
    overlay.classList.remove('active');
    document.body.classList.remove('sidebar-open');
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      sidebar.classList.remove('active');
      overlay.classList.remove('active');
      document.body.classList.remove('sidebar-open');
    });
  }
}
