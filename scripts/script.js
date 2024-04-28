
// smooting in the webiste
document.addEventListener("DOMContentLoaded", function() {
    const sections = document.querySelectorAll('section');
    const config = {
        rootMargin: '0px',
        threshold: 0.1
    };

    let observer = new IntersectionObserver(function(entries, self) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = 1;
                self.unobserve(entry.target);
            }
        });
    }, config);

    sections.forEach(section => {
        observer.observe(section);
    });
});

// current year :
document.addEventListener("DOMContentLoaded", function() {
    const year = new Date().getFullYear(); // Gets the current year
    const yearSpan = document.getElementById('current-year');
    yearSpan.textContent = year; // Sets the text content to the current year
});

// Dark mode
document.getElementById('theme-toggle').addEventListener('click', function() {
    document.body.classList.toggle('dark-mode');
    var mode = document.body.classList.contains('dark-mode') ? 'Light Mode' : 'Dark Mode';
    this.textContent = mode;
});

if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    // Automatically set to dark mode if the OS is set to dark
    document.body.classList.add('dark-mode');
    document.getElementById('theme-toggle').textContent = 'Light Mode';
}
