document.addEventListener('DOMContentLoaded', function() {
    // Get all input boxes within .input-box
    const inputBoxes = document.querySelectorAll('.input-box input, .input-box textarea');

    // Loop through each input box
    inputBoxes.forEach(inputBox => {
        // Add event listener for input event
        inputBoxes.forEach(inputBox => {
            inputBox.addEventListener('input', () => {
                inputBox.nextElementSibling.style.opacity = '1';
                inputBox.nextElementSibling.style.visibility = 'visible';
            });
        });
    });
});
