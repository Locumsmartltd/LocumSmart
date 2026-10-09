(function () {
  function textOf(el) {
    return (el.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function initAdminListSearch() {
    var input = document.querySelector('[data-admin-live-search]');
    if (!input) {
      return;
    }

    var table = document.querySelector('[data-admin-search-table]') ||
      document.querySelector('.table-responsive table.table') ||
      document.querySelector('table.table');
    if (!table) {
      return;
    }

    var tbody = table.querySelector('tbody');
    if (!tbody) {
      return;
    }

    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr')).filter(function (row) {
      return !row.classList.contains('admin-search-empty');
    });

    var datalistId = input.getAttribute('list');
    var datalist = datalistId ? document.getElementById(datalistId) : null;
    if (datalist) {
      var suggestions = {};
      rows.forEach(function (row) {
        Array.prototype.forEach.call(row.querySelectorAll('td'), function (cell) {
          if (cell.querySelector('form, button, input')) {
            return;
          }
          var value = textOf(cell);
          if (value && value !== 'N/A' && value.length <= 80) {
            suggestions[value] = true;
          }
        });
      });
      Object.keys(suggestions).sort().forEach(function (value) {
        var option = document.createElement('option');
        option.value = value;
        datalist.appendChild(option);
      });
    }

    var emptyRow = tbody.querySelector('.admin-search-empty');
    if (!emptyRow) {
      emptyRow = document.createElement('tr');
      emptyRow.className = 'admin-search-empty';
      emptyRow.style.display = 'none';
      var colCount = table.querySelectorAll('thead th').length || 8;
      emptyRow.innerHTML = '<td colspan="' + colCount + '">No matching results.</td>';
      tbody.appendChild(emptyRow);
    }

    function applyFilter() {
      var query = (input.value || '').trim().toLowerCase();
      var visible = 0;
      rows.forEach(function (row) {
        var match = !query || textOf(row).toLowerCase().indexOf(query) !== -1;
        row.style.display = match ? '' : 'none';
        if (match) {
          visible += 1;
        }
      });
      emptyRow.style.display = visible ? 'none' : '';
    }

    input.addEventListener('input', applyFilter);
    applyFilter();

    var form = input.closest('form');
    if (form) {
      form.addEventListener('submit', function (event) {
        if ((input.value || '').trim()) {
          return;
        }
        event.preventDefault();
        clearSearch();
      });
    }

    var clearBtn = document.querySelector('[data-admin-search-clear]');
    if (clearBtn) {
      clearBtn.addEventListener('click', function (event) {
        event.preventDefault();
        clearSearch();
      });
    }

    function clearSearch() {
      var url = new URL(window.location.href);
      if (url.searchParams.has('search')) {
        url.searchParams.delete('search');
        var next = url.pathname;
        var remaining = url.searchParams.toString();
        if (remaining) {
          next += '?' + remaining;
        }
        window.location.href = next + url.hash;
        return;
      }
      input.value = '';
      applyFilter();
      input.focus();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminListSearch);
  } else {
    initAdminListSearch();
  }
})();
