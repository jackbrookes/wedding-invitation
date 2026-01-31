/**
 * Wedding Invitation - JavaScript
 * Handles scroll reveal animations
 */

document.addEventListener('DOMContentLoaded', () => {
    initScrollReveal();
    initContactInfo();
});

function initContactInfo() {
    const p = ['44', '7707', '028', '037'];
    const num = p.join('');
    const formatted = '+' + p[0] + ' ' + p[1] + ' ' + p[2] + ' ' + p[3];

    // Set WhatsApp link
    const waLink = document.getElementById('wa-link');
    if (waLink) {
        waLink.href = 'https://wa' + '.me/' + num;
    }

    // Set display number
    const phoneDisplay = document.getElementById('phone-display');
    if (phoneDisplay) {
        phoneDisplay.textContent = formatted;
    }
}

/**
 * Initialize scroll reveal animations using IntersectionObserver
 * More performant and smoother than scroll event listeners
 */
function initScrollReveal() {
    const revealElements = document.querySelectorAll('.reveal');

    const observerOptions = {
        root: null,
        rootMargin: '0px 0px -50px 0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    revealElements.forEach(element => {
        observer.observe(element);
    });
}
