$(document).ready(function() {
     
    // Function to update counter
    const updateCounter = (counterElement) => {
        const target = +counterElement.getAttribute("data-target");
        let count = 0;
        const speed = 30; // The lower the slower

        const incrementCounter = () => {
            if (count < target) {
                count++;
                counterElement.innerText = count;
                setTimeout(incrementCounter, speed);
            }
        };

        incrementCounter();
    };

    // Intersection Observer to trigger counter animations when 'options' section enters viewport
    const optionsSection = document.querySelector('.options');
    const counters = optionsSection ? optionsSection.querySelectorAll('.counter') : [];

    const counterObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                counters.forEach(counter => {
                    updateCounter(counter);
                });
                observer.unobserve(entry.target); // Stop observing once animation starts
            }
        });
    });

    if (optionsSection) {
        counterObserver.observe(optionsSection); // Observe the 'options' section
    }

 


});
