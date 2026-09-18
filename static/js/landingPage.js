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

    //for search bar location
    const cities = [
        {% for city in cities %}
            "{{ city.city }}",
        {% endfor %}
    ];

    const locationInput = $('#locationInput');
    const optionsContainer = $('#locationOptionsContainer');

    locationInput.on('input', function() {
        const inputText = $(this).val().trim().toLowerCase();
        const filteredCities = cities.filter(city => city.toLowerCase().includes(inputText));

        console.log(filteredCities); // Debug: Check filtered cities

        renderOptions(filteredCities);
    });

    function renderOptions(filteredCities) {
        optionsContainer.empty();

        filteredCities.forEach(city => {
            const option = $('<div>')
                .text(city)
                .addClass('autocomplete-option')
                .on('click', function() {
                    locationInput.val(city);
                    optionsContainer.empty(); // Clear options after selection
                });

            optionsContainer.append(option);
        });
    }

    // Handle click outside of autocomplete options to close the container
    $(document).on('click', function(event) {
        if (!$(event.target).closest('#locationInput').length && !$(event.target).closest('#locationOptionsContainer').length) {
            optionsContainer.empty();
        }
    });



    // Intersection Observer to trigger image animations when 'information' section enters viewport
    const informationSection = document.querySelector('.information');

    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const imageCards = entry.target.querySelectorAll('.move-from-right, .move-from-left');
                imageCards.forEach(card => {
                    card.classList.add('visible');
                });
                observer.unobserve(entry.target); // Stop observing once animation starts
            }
        });
    });

    if (informationSection) {
        imageObserver.observe(informationSection); // Observe the 'information' section
    }

    // Get all input boxes
    const inputBoxes = document.querySelectorAll('.input-box input, .input-box select');

    // Loop through each input box
    inputBoxes.forEach(inputBox => {
        // Add event listener for input event
        inputBox.addEventListener('input', () => {
            // Toggle the visibility of the span based on whether the input has value
            if (inputBox.value.trim() !== '') {
                inputBox.nextElementSibling.style.opacity = '0';
                inputBox.nextElementSibling.style.visibility = 'hidden';
            } else {
                inputBox.nextElementSibling.style.opacity = '1';
                inputBox.nextElementSibling.style.visibility = 'visible';
            }
        });
    });

    
});
