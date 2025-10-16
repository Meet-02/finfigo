document.addEventListener("DOMContentLoaded", function () {
    const radioButtons = document.querySelectorAll('input[name="userType"]');
    const businessSection = document.getElementById('infobusiness');
    const jobSection = document.getElementById('infojob');

    businessSection.style.display = 'none';
    jobSection.style.display = 'none';

    radioButtons.forEach(radio => {
        radio.addEventListener('change', function () {
            if (this.value === 'Job Person') {
                jobSection.style.display = 'block';
                businessSection.style.display = 'none';
            } else if (this.value === 'Business Person') {
                businessSection.style.display = 'block';
                jobSection.style.display = 'none';
            }
        });
    });
});

const header = document.getElementById('header');
const formSection = document.querySelector('.form-section');

window.addEventListener('scroll', () => {
    const formTop = formSection.offsetTop;
    const headerHeight = header.offsetHeight;

    if (window.scrollY >= formTop - headerHeight - 10) {
        header.style.position = 'absolute';
        header.style.top = (formTop - headerHeight - 10) + 'px';
    } else {
        header.style.position = 'fixed';
        header.style.top = '10px';
    }
});

function nextStep(current) {
    const currentInputs = document.querySelectorAll(`#step-${current} input`);
    let allFilled = true;

    currentInputs.forEach(input => {
        if (!input.value.trim()) {
            allFilled = false;
            input.style.borderColor = "red";
        } else {
            input.style.borderColor = "";
        }
    });

    if (!allFilled) return; 

    document.querySelector(`.step[data-step="${current}"]`).classList.add("completed");

    document.getElementById(`step-${current}`).classList.add("hidden");
    const next = current + 1;
    if (document.getElementById(`step-${next}`)) {
        document.getElementById(`step-${next}`).classList.remove("hidden");
    }
}
document.addEventListener("DOMContentLoaded", () => {
    const sec80cInput = document.getElementById("sec80c");
    const note = document.getElementById("note80c");

    sec80cInput.addEventListener("focus", () => {
        note.style.display = "block"; // show note
    });

    sec80cInput.addEventListener("blur", () => {
        note.style.display = "none"; 
    });
});


document.addEventListener('DOMContentLoaded', function() {
    // 1. Get the input fields
    const grossIncomeInput = document.getElementById('gr-in');
    const otherIncomeInput = document.getElementById('oth-in');
    const totalRevenueInput = document.getElementById('total-revenue');

    function updateTotalRevenue() {
        const grossIncome = parseFloat(grossIncomeInput.value) || 0;
        const otherIncome = parseFloat(otherIncomeInput.value) || 0;
        
        const total = grossIncome + otherIncome;
        
        totalRevenueInput.value = total;
    }

    grossIncomeInput.addEventListener('input', updateTotalRevenue);
    otherIncomeInput.addEventListener('input', updateTotalRevenue);
});