(() => {
  const booking = document.querySelector('#staffing-booking');
  if (!booking || typeof booking.showModal !== 'function') return;

  const body = booking.querySelector('[data-booking-body]');
  const feedback = document.querySelector('.staffing-feedback');
  let bookingUrl;
  let bookingTrigger;
  let bookingLoad = 0;
  let rotaLoad = 0;

  async function load(url, options) {
    const response = await fetch(url, options);
    const page = new DOMParser().parseFromString(await response.text(), 'text/html');
    const notices = [...page.querySelectorAll('.rs-toast-text')].map(item => item.textContent.trim());
    if (!response.ok && response.status !== 400) {
      throw new Error('This action could not be completed. Refresh the rota and try again.');
    }
    return {page, url: response.url, notices};
  }

  function showRequestErrors() {
    const dialog = document.querySelector('#staff-request[data-show-dialog]');
    if (!dialog) return;
    if (dialog.open) dialog.close();
    dialog.showModal();
  }

  async function refreshRota(url, options, preserveScroll = false) {
    const loadId = ++rotaLoad;
    const result = await load(url, options);
    if (loadId !== rotaLoad) return;
    const fresh = result.page.querySelector('#staffing-calendar-content');
    if (!fresh) throw new Error('The rota is unavailable. Refresh to check your sign-in.');
    const current = document.querySelector('#staffing-calendar-content');
    const scroller = current.querySelector('.staffing-table-wrap');
    const scroll = preserveScroll && scroller ? [scroller.scrollLeft, scroller.scrollTop] : [0, 0];
    const openDialog = current.querySelector('dialog[open]');
    if (openDialog) openDialog.close();
    current.replaceWith(fresh);
    fresh.querySelector('.staffing-table-wrap')?.scrollTo(...scroll);
    history.replaceState(null, '', result.url);
    feedback.textContent = result.notices.join(' ');
    showRequestErrors();
  }

  function renderBooking(result) {
    const content = result.page.querySelector('#staffing-position-content');
    if (!content) throw new Error('This booking is unavailable. Refresh the rota and try again.');
    const heading = booking.querySelector('[data-booking-subtitle]');
    heading.textContent = content.dataset.subtitle;
    const notice = document.createElement('p');
    notice.className = 'staffing-dialog-notice';
    notice.setAttribute('role', 'status');
    notice.textContent = result.notices.join(' ');
    body.replaceChildren(notice, content);
  }

  async function openBooking(link) {
    const loadId = ++bookingLoad;
    bookingUrl = link.href;
    bookingTrigger = link;
    booking.querySelector('[data-booking-subtitle]').textContent = '';
    body.textContent = 'Loading booking…';
    booking.showModal();
    try {
      const result = await load(bookingUrl);
      if (booking.open && loadId === bookingLoad) {
        renderBooking(result);
        const target = {approve: '[value="approve"]', hours: '[name="paid_hours"]',
          'no-show': '[value="issue"]'}[link.dataset.focus];
        if (target) body.querySelector(target)?.focus();
      }
    } catch (error) {
      if (booking.open && loadId === bookingLoad) body.textContent = error.message;
    }
  }

  booking.addEventListener('close', () => {
    bookingLoad++;
    const currentTrigger = bookingTrigger?.isConnected ? bookingTrigger :
      [...document.querySelectorAll('[data-booking]')].find(link => link.href === bookingUrl);
    currentTrigger?.focus({preventScroll: true});
  });

  document.addEventListener('click', event => {
    const dialog = event.target.closest('dialog');
    if (event.target.closest('[data-close-dialog]') || (dialog && event.target === dialog)) {
      dialog?.close();
      return;
    }
    if (event.target.closest('[data-add-date]')) {
      const dates = dialog.querySelector('[data-shift-dates]');
      if (dates.children.length >= Number(dates.dataset.maxDates)) return;
      dates.append(dialog.querySelector('[data-date-template]').content.cloneNode(true));
      dates.lastElementChild.querySelector('input').focus();
      return;
    }
    const removeDate = event.target.closest('[data-remove-date]');
    if (removeDate) {
      const row = removeDate.closest('.staffing-date-row');
      if (row.parentElement.children.length > 1) {
        const nextFocus = row.nextElementSibling || row.previousElementSibling;
        row.remove();
        nextFocus.querySelector('input').focus();
      }
      return;
    }
    if (event.target.closest('[data-print]')) {
      window.print();
      return;
    }
    const branchEditor = event.target.closest('[data-branch-editor]');
    if (branchEditor) {
      const editor = document.querySelector('#staffing-branch');
      editor.querySelector('h2').textContent = branchEditor.dataset.branch ? 'Rename branch' : 'Add branch';
      editor.querySelector('[name="branch"]').value = branchEditor.dataset.branch || '';
      editor.querySelector('[name="name"]').value = branchEditor.dataset.branchName || '';
      editor.showModal();
      return;
    }

    const link = event.target.closest('a[data-request-staff], a[data-booking], a[data-rota-view]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (link.hasAttribute('data-booking')) {
      openBooking(link);
    } else if (link.hasAttribute('data-request-staff')) {
      const request = document.querySelector('#staff-request');
      const form = request.querySelector('form');
      form.reset();
      const [first, ...additional] = form.querySelectorAll('.staffing-date-row');
      additional.forEach(row => row.remove());
      if (link.dataset.branch) form.elements.branch.value = link.dataset.branch;
      if (link.dataset.day) first.querySelector('input').value = link.dataset.day;
      request.showModal();
    } else {
      refreshRota(link.href).catch(error => { feedback.textContent = error.message; });
    }
  });

  document.addEventListener('change', event => {
    const form = event.target.closest('[data-rota-filter]');
    if (form && event.target.matches('select')) form.requestSubmit();
  });

  document.addEventListener('submit', async event => {
    const form = event.target;
    const inBooking = booking.contains(form);
    if (!inBooking && !form.matches('[data-calendar-form], [data-rota-filter]')) return;
    event.preventDefault();
    if (form.matches('[data-rota-filter]')) {
      const url = new URL(form.action);
      url.search = new URLSearchParams(new FormData(form));
      url.hash = '';
      const selectName = form.querySelector('select').name;
      try {
        await refreshRota(url);
        document.querySelector(`[data-rota-filter] select[name="${selectName}"]`)?.focus({preventScroll: true});
      } catch {
        location.assign(url);
      }
      return;
    }

    if (form.dataset.submitting) return;
    const data = new FormData(form, event.submitter);
    form.dataset.submitting = 'true';
    const button = event.submitter;
    if (button) button.disabled = true;
    try {
      const options = {method: 'POST', body: data};
      if (inBooking) {
        const loadId = bookingLoad;
        const result = await load(form.hasAttribute('action') ? form.action : bookingUrl, options);
        if (booking.open && loadId === bookingLoad) renderBooking(result);
        await refreshRota(location.href, undefined, true);
      } else {
        await refreshRota(form.hasAttribute('action') ? form.action : location.href, options, true);
      }
    } catch (error) {
      const notice = document.createElement('p');
      notice.className = 'staffing-dialog-notice';
      notice.setAttribute('role', 'alert');
      notice.textContent = error.message;
      if (form.isConnected) form.prepend(notice);
      else feedback.textContent = error.message;
    } finally {
      delete form.dataset.submitting;
      if (button) button.disabled = false;
    }
  });

  showRequestErrors();
})();
