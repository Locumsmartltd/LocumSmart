document.addEventListener('DOMContentLoaded', function() {
    // Get all input boxes within .input-box
    const inputBoxes = document.querySelectorAll('.input-box input, .input-box textarea');

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
function confirmDelete() {
    // Display a confirmation dialog
    if (confirm("Are you sure you want to delete this locum?")) {
        // If user confirms, submit the form
        document.getElementById("deleteLocumForm").submit();
        return true;
    } else {
        // If user cancels, do not submit the form
        return false;
    }
}