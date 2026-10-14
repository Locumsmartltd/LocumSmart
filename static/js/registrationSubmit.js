// Submits the locum registration form in the background so the applicant sees
// what is happening: large photos are shrunk in the browser first, oversized
// files are caught before uploading, and the button shows upload progress and
// cannot be clicked twice. Validation errors from the server are shown as toasts
// without clearing the form. Where any of this is unsupported the form simply
// submits the normal way.
(function () {
    var form = document.querySelector('form[data-async-submit]');
    if (!form || !window.FormData || !window.XMLHttpRequest || !window.DOMParser) return;

    var MAX_FILE_MB = 10;
    var MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024;
    var SHRINK_OVER_BYTES = 500 * 1024;   // photos smaller than this are sent as they are
    var MAX_IMAGE_SIDE = 2000;            // px; documents stay easy to read
    var JPEG_QUALITY = 0.82;

    var button = form.querySelector('button[type="submit"]');
    var buttonHtml = button ? button.innerHTML : '';
    var progress = null;
    var busy = false;

    function fieldLabel(input) {
        var wrapper = input.closest('.field');
        var label = wrapper && wrapper.querySelector('label');
        if (!label) return 'This file';
        var clone = label.cloneNode(true);
        clone.querySelectorAll('.req, .hint').forEach(function (el) { el.remove(); });
        return clone.textContent.replace(/\s+/g, ' ').trim() || 'This file';
    }

    function toast(message, type) {
        if (window.rsToast) window.rsToast(message, type);
    }

    function isShrinkable(file) {
        return /^image\/(jpeg|png|webp)$/.test(file.type) && file.size > SHRINK_OVER_BYTES;
    }

    function tooLargeMessage(input, file) {
        return fieldLabel(input) + ': "' + file.name + '" is larger than ' + MAX_FILE_MB +
            ' MB. Please upload a smaller file or a compressed PDF.';
    }

    // Warn as soon as a file is picked; photos are only checked after shrinking.
    form.addEventListener('change', function (event) {
        var input = event.target;
        if (input.type !== 'file' || !input.files.length) return;
        var file = input.files[0];
        if (file.size > MAX_FILE_BYTES && !isShrinkable(file)) {
            toast(tooLargeMessage(input, file), 'error');
        }
    });

    // Resolves with a smaller JPEG copy of a large photo, or the original file
    // when it cannot be shrunk (unsupported format or browser, or no saving).
    function shrinkImage(file) {
        if (!isShrinkable(file) || !window.createImageBitmap) return Promise.resolve(file);
        return createImageBitmap(file).then(function (bitmap) {
            var scale = Math.min(1, MAX_IMAGE_SIDE / Math.max(bitmap.width, bitmap.height));
            var canvas = document.createElement('canvas');
            canvas.width = Math.round(bitmap.width * scale);
            canvas.height = Math.round(bitmap.height * scale);
            var context = canvas.getContext('2d');
            context.fillStyle = '#fff';   // transparent PNG areas become white, not black
            context.fillRect(0, 0, canvas.width, canvas.height);
            context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
            if (bitmap.close) bitmap.close();
            return new Promise(function (resolve) {
                canvas.toBlob(function (blob) {
                    try {
                        if (!blob || blob.size >= file.size) return resolve(file);
                        var name = file.name.replace(/\.[^.]+$/, '') + '.jpg';
                        resolve(new File([blob], name, { type: 'image/jpeg', lastModified: file.lastModified }));
                    } catch (e) {
                        resolve(file);
                    }
                }, 'image/jpeg', JPEG_QUALITY);
            });
        }).catch(function () { return file; });
    }

    function setBusy(text, fraction) {
        if (!button) return;
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        button.innerHTML = '<span class="rs-spinner" aria-hidden="true"></span>';
        button.appendChild(document.createTextNode(text));
        if (!progress) {
            progress = document.createElement('div');
            progress.className = 'rs-upload-progress';
            progress.innerHTML = '<div class="rs-upload-progress-bar"></div>';
            button.insertAdjacentElement('afterend', progress);
        }
        progress.hidden = fraction === undefined;
        if (fraction !== undefined) {
            progress.firstChild.style.width = Math.round(fraction * 100) + '%';
        }
    }

    function setIdle() {
        busy = false;
        if (!button) return;
        button.disabled = false;
        button.removeAttribute('aria-busy');
        button.innerHTML = buttonHtml;
        if (progress) progress.hidden = true;
    }

    // The server re-renders the form with its messages; show those toasts here
    // instead, so the applicant keeps everything they have filled in.
    function showServerMessages(html) {
        var page = new DOMParser().parseFromString(html, 'text/html');
        var toasts = page.querySelectorAll('#toastStack .rs-toast');
        Array.prototype.forEach.call(toasts, function (el) {
            var type = (el.className.match(/rs-toast-(error|success|warning|info)\b/) || [])[1] || 'info';
            var text = el.querySelector('.rs-toast-text');
            toast((text || el).textContent.trim(), type);
        });
        return toasts.length > 0;
    }

    function failed() {
        setIdle();
        toast('Your registration could not be submitted. Please check your connection and try again.', 'error');
    }

    function send(data) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', form.action);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.upload.addEventListener('progress', function (event) {
            if (!event.lengthComputable) return;
            if (event.loaded < event.total) {
                setBusy('Uploading documents… ' + Math.round(event.loaded / event.total * 100) + '%',
                        event.loaded / event.total);
            } else {
                setBusy('Saving your registration…', 1);
            }
        });
        xhr.addEventListener('load', function () {
            var type = xhr.getResponseHeader('Content-Type') || '';
            if (xhr.status === 200 && type.indexOf('application/json') === 0) {
                var redirect = null;
                try { redirect = JSON.parse(xhr.responseText).redirect; } catch (e) { /* handled below */ }
                if (redirect) {
                    // Stay busy while the confirmation page loads
                    window.location.href = redirect;
                    return;
                }
            } else if (xhr.status === 200 && type.indexOf('text/html') === 0 &&
                       showServerMessages(xhr.responseText)) {
                setIdle();
                return;
            }
            failed();
        });
        xhr.addEventListener('error', failed);
        xhr.addEventListener('abort', failed);
        xhr.send(data);
    }

    // Runs after registrationForm.js, which cancels the submit when fields are invalid.
    form.addEventListener('submit', function (event) {
        if (event.defaultPrevented) return;
        event.preventDefault();
        if (busy) return;
        busy = true;
        setBusy('Preparing documents…');

        var data = new FormData(form);
        if (button && button.name) data.append(button.name, button.value);

        var inputs = Array.prototype.filter.call(form.querySelectorAll('input[type="file"]'), function (input) {
            return input.name && input.files.length;
        });
        Promise.all(inputs.map(function (input) {
            return shrinkImage(input.files[0]).then(function (file) {
                return { input: input, file: file };
            });
        })).then(function (picked) {
            var oversized = picked.filter(function (p) { return p.file.size > MAX_FILE_BYTES; });
            if (oversized.length) {
                setIdle();
                oversized.forEach(function (p) { toast(tooLargeMessage(p.input, p.file), 'error'); });
                oversized[0].input.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }
            picked.forEach(function (p) { data.set(p.input.name, p.file, p.file.name); });
            setBusy('Uploading documents… 0%', 0);
            send(data);
        }).catch(failed);
    });
})();
