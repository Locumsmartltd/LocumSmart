document.addEventListener('DOMContentLoaded', function () {
    // Add event listener for input boxes
    const inputBoxes = document.querySelectorAll('.input-box input, .input-box textarea');
    inputBoxes.forEach(inputBox => {
        inputBox.addEventListener('input', () => {
            inputBox.nextElementSibling.style.opacity = '1';
            inputBox.nextElementSibling.style.visibility = 'visible';
        });
    });


});

// jQuery for toggling section visibility
$(document).ready(function () {
    $('.toggle-section-btn').click(function () {
        var sectionContent = $(this).next('.section-content');
        if (sectionContent.is(':visible')) {
            sectionContent.hide();
            $(this).text('+');
        } else {
            sectionContent.show();
            $(this).text('-');
        }
    });
});

