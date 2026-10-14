// Search-as-you-type for the admin lists (locums, locum requests, employers,
// staff and the calendar's job list). Each keystroke asks the server for the
// page filtered by the search - a prefix match on the table's indexed text
// columns - and swaps the matching rows into the table. Rows already on the
// page are reused rather than replaced, so ticked boxes and unsaved edits
// survive, and rows that are ticked or edited stay listed even when they no
// longer match. A dropdown under the box suggests values from the matching
// rows' columns (those whose heading has data-suggest) that start with what
// has been typed; picking one searches for it.
// Without fetch support the search box still works as a normal form.
(function () {
  var DEBOUNCE_MS = 120;
  var MAX_SUGGESTIONS = 8;

  function initAdminListSearch() {
    var input = document.querySelector('[data-admin-live-search]');
    var results = document.querySelector('[data-admin-search-results]');
    if (!input || !results || !window.fetch || !window.DOMParser) {
      return;
    }

    var form = input.closest('form');
    var clearBtn = document.querySelector('[data-admin-search-clear]');
    var lastQuery = input.value.trim();
    var timer = null;
    var controller = null;

    function normalise(text) {
      return (text || '').replace(/\s+/g, ' ').trim();
    }

    function keyedRows(tbody) {
      return Array.prototype.filter.call(tbody.rows, function (row) {
        return row.hasAttribute('data-row-key');
      });
    }

    // A row the admin has ticked or typed into
    function isSticky(row) {
      return Array.prototype.some.call(row.querySelectorAll('input, select, textarea'), function (field) {
        if (field.type === 'checkbox' || field.type === 'radio') {
          return field.checked !== field.defaultChecked;
        }
        if (field.tagName === 'SELECT') {
          return Array.prototype.some.call(field.options, function (option) {
            return option.selected !== option.defaultSelected;
          });
        }
        return field.value !== field.defaultValue;
      });
    }

    function emptyRow(table, incomingTbody) {
      var serverEmpty = incomingTbody && Array.prototype.filter.call(incomingTbody.rows, function (row) {
        return !row.hasAttribute('data-row-key');
      })[0];
      if (serverEmpty) {
        return document.importNode(serverEmpty, true);
      }
      var row = document.createElement('tr');
      row.className = 'admin-search-empty';
      var cell = document.createElement('td');
      cell.colSpan = table.querySelectorAll('thead th').length || 1;
      cell.textContent = 'No matching results.';
      row.appendChild(cell);
      return row;
    }

    function applyResults(incoming) {
      var table = results.querySelector('[data-admin-search-table]');
      var tbody = table && table.tBodies[0];
      var incomingTable = incoming.querySelector('[data-admin-search-table]');
      var incomingTbody = incomingTable && incomingTable.tBodies[0];

      if (!tbody) {
        // Nothing to keep (the page showed "No ... found"): take the new block as it is
        results.innerHTML = incoming.innerHTML;
        return;
      }

      var current = {};
      keyedRows(tbody).forEach(function (row) {
        current[row.getAttribute('data-row-key')] = row;
      });
      var matched = {};
      var rows = (incomingTbody ? keyedRows(incomingTbody) : []).map(function (row) {
        var key = row.getAttribute('data-row-key');
        matched[key] = true;
        return current[key] || document.importNode(row, true);
      });
      var sticky = keyedRows(tbody).filter(function (row) {
        return !matched[row.getAttribute('data-row-key')] && isSticky(row);
      });
      rows = sticky.concat(rows);

      var fragment = document.createDocumentFragment();
      rows.forEach(function (row) { fragment.appendChild(row); });
      if (!rows.length) {
        fragment.appendChild(emptyRow(table, incomingTbody));
      }
      while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
      }
      tbody.appendChild(fragment);
      table.dispatchEvent(new CustomEvent('admin-search:updated'));
    }

    // ---- Suggestions dropdown ----

    var listbox = document.createElement('ul');
    listbox.id = 'admin-search-suggestions';
    listbox.className = 'admin-suggest';
    listbox.setAttribute('role', 'listbox');
    listbox.hidden = true;
    var host = input.parentNode;
    if (window.getComputedStyle(host).position === 'static') {
      host.style.position = 'relative';
    }
    host.appendChild(listbox);
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', listbox.id);
    input.setAttribute('aria-expanded', 'false');

    var suggestions = [];
    var active = -1;
    var skipSuggestions = false;   // set when a suggestion was just picked

    function cellValue(cell) {
      // Editable calendar cells hold their value in a text box
      var field = cell.querySelector('input[type="text"], input:not([type])');
      return normalise(field ? field.value : cell.textContent);
    }

    // Where the query starts in the value: at the beginning or at a word
    function matchAt(value, query) {
      var lower = value.toLowerCase();
      var at = lower.indexOf(query);
      while (at > 0 && /[\w]/.test(lower.charAt(at - 1))) {
        at = lower.indexOf(query, at + 1);
      }
      return at;
    }

    function collectSuggestions(table, query) {
      if (!table || !table.tBodies[0] || !query) {
        return [];
      }
      var lowerQuery = query.toLowerCase();
      var columns = [];
      Array.prototype.forEach.call(table.querySelectorAll('thead th'), function (th, index) {
        if (th.hasAttribute('data-suggest')) {
          columns.push({ index: index, label: normalise(th.textContent) });
        }
      });
      var seen = {};
      var found = [];
      keyedRows(table.tBodies[0]).forEach(function (row) {
        columns.forEach(function (column) {
          var cell = row.cells[column.index];
          var value = cell ? cellValue(cell) : '';
          var key = value.toLowerCase();
          if (!value || value === 'N/A' || seen[key]) {
            return;
          }
          var at = matchAt(value, lowerQuery);
          if (at < 0) {
            return;
          }
          seen[key] = true;
          found.push({ value: value, label: column.label, at: at });
        });
      });
      // Values that start with the query first, then alphabetical
      found.sort(function (a, b) {
        return (a.at > 0) - (b.at > 0) || a.value.localeCompare(b.value);
      });
      return found.slice(0, MAX_SUGGESTIONS);
    }

    function setOpen(open) {
      listbox.hidden = !open;
      input.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (!open) {
        setActive(-1);
      }
    }

    function setActive(index) {
      active = index;
      Array.prototype.forEach.call(listbox.children, function (option, i) {
        option.classList.toggle('is-active', i === index);
        option.setAttribute('aria-selected', i === index ? 'true' : 'false');
      });
      if (index >= 0) {
        input.setAttribute('aria-activedescendant', listbox.children[index].id);
        listbox.children[index].scrollIntoView({ block: 'nearest' });
      } else {
        input.removeAttribute('aria-activedescendant');
      }
    }

    function showSuggestions(items, query) {
      suggestions = items;
      listbox.innerHTML = '';
      items.forEach(function (item, i) {
        var option = document.createElement('li');
        option.id = listbox.id + '-' + i;
        option.className = 'admin-suggest-option';
        option.setAttribute('role', 'option');

        var text = document.createElement('span');
        text.className = 'admin-suggest-text';
        var typed = document.createElement('strong');
        typed.textContent = item.value.slice(item.at, item.at + query.length);
        text.appendChild(document.createTextNode(item.value.slice(0, item.at)));
        text.appendChild(typed);
        text.appendChild(document.createTextNode(item.value.slice(item.at + query.length)));

        var label = document.createElement('span');
        label.className = 'admin-suggest-label';
        label.textContent = item.label;

        option.appendChild(text);
        option.appendChild(label);
        // mousedown, so the box does not lose focus (and close the list) first
        option.addEventListener('mousedown', function (event) {
          event.preventDefault();
          pick(i);
        });
        listbox.appendChild(option);
      });
      setOpen(items.length > 0 && document.activeElement === input);
    }

    function pick(index) {
      input.value = suggestions[index].value;
      setOpen(false);
      skipSuggestions = true;
      clearTimeout(timer);
      search();
    }

    // ---- Searching ----

    function search(force) {
      var query = normalise(input.value);
      if (query === lastQuery && !force) {
        return;
      }
      lastQuery = query;
      if (!query) {
        showSuggestions([], query);
      }

      var url = new URL(window.location.href);
      if (query) {
        url.searchParams.set('search', query);
      } else {
        url.searchParams.delete('search');
      }

      // Only the latest search matters; drop any still in flight
      if (controller) {
        controller.abort();
      }
      controller = window.AbortController ? new AbortController() : null;
      results.setAttribute('aria-busy', 'true');

      fetch(url.toString(), {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        signal: controller ? controller.signal : undefined
      }).then(function (response) {
        if (!response.ok) {
          throw new Error('Search failed: ' + response.status);
        }
        return response.text();
      }).then(function (html) {
        results.removeAttribute('aria-busy');
        var incoming = new DOMParser().parseFromString(html, 'text/html')
          .querySelector('[data-admin-search-results]');
        if (!incoming) {
          // Not the list page (e.g. the session expired): load it properly
          window.location.href = url.toString();
          return;
        }
        applyResults(incoming);
        if (skipSuggestions) {
          skipSuggestions = false;
        } else {
          showSuggestions(collectSuggestions(incoming.querySelector('[data-admin-search-table]'), query), query);
        }
        // Refresh, back and shared links keep the search
        window.history.replaceState(null, '', url.pathname + url.search + url.hash);
      }).catch(function (error) {
        if (error.name === 'AbortError') {
          return;
        }
        results.removeAttribute('aria-busy');
        lastQuery = null;   // let the next keystroke or Enter retry
        if (window.rsToast) {
          window.rsToast('Search could not be completed. Please try again.', 'error');
        }
      });
    }

    input.addEventListener('input', function () {
      skipSuggestions = false;
      clearTimeout(timer);
      timer = setTimeout(search, DEBOUNCE_MS);
    });

    input.addEventListener('keydown', function (event) {
      if (listbox.hidden) {
        if (event.key === 'ArrowDown' && suggestions.length) {
          event.preventDefault();
          setOpen(true);
          setActive(0);
        }
        return;
      }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        var step = event.key === 'ArrowDown' ? 1 : -1;
        setActive((active + step + suggestions.length) % suggestions.length);
      } else if (event.key === 'Enter' && active >= 0) {
        event.preventDefault();
        pick(active);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        setOpen(false);
      }
    });

    input.addEventListener('blur', function () {
      setOpen(false);
    });

    input.addEventListener('focus', function () {
      if (suggestions.length && input.value.trim()) {
        setOpen(true);
      }
    });

    if (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        clearTimeout(timer);
        setOpen(false);
        skipSuggestions = true;   // Enter means "show me the results"
        search(true);
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', function (event) {
        event.preventDefault();
        clearTimeout(timer);
        input.value = '';
        search();
        input.focus();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminListSearch);
  } else {
    initAdminListSearch();
  }
})();
