(function () {
  const STATUS_REFRESH_EVENT = 'sasutena:refreshStatus';

  const getCsrfToken = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  };

  const setupStatusSummary = () => {
    const section = document.getElementById('statusSummary');
    if (!section || section.dataset.statusInitialized === '1') {
      return;
    }

    const endpoint = section.dataset.statusEndpoint || '';
    const tbody = document.getElementById('statusSummaryBody');

    if (!endpoint || !tbody) {
      return;
    }

    const placeholderRow = () => {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.colSpan = 2;
      cell.className = 'py-3 text-muted';
      cell.textContent = '情報を取得できませんでした。';
      row.appendChild(cell);
      return row;
    };

    const renderRows = (rows) => {
      tbody.innerHTML = '';
      if (!Array.isArray(rows) || rows.length === 0) {
        tbody.appendChild(placeholderRow());
        return;
      }

      rows.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.className = index === 0 ? 'border-top-0' : 'border-top';

        const th = document.createElement('th');
        th.scope = 'row';
        th.className = 'fw-normal text-muted py-3';
        th.textContent = row.label || '';

        const td = document.createElement('td');
        td.className = 'py-3 text-end';

        const valueSpan = document.createElement('span');
        valueSpan.className = 'fs-5 fw-semibold text-primary';
        valueSpan.textContent = typeof row.value === 'number' ? row.value : (row.value || '0');

        const unitSpan = document.createElement('span');
        unitSpan.className = 'ms-1 text-muted';
        unitSpan.textContent = row.unit || '';

        td.appendChild(valueSpan);
        if (row.unit) {
          td.appendChild(unitSpan);
        }

        tr.appendChild(th);
        tr.appendChild(td);
        tbody.appendChild(tr);
      });
    };

    const refresh = () => {
      fetch(endpoint, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error('failed');
          }
          return response.json();
        })
        .then((data) => {
          renderRows(data && data.rows);
        })
        .catch(() => {
          renderRows(null);
        });
    };

    const intervalMs = parseInt(section.dataset.refreshInterval || '0', 10);
    if (!Number.isNaN(intervalMs) && intervalMs > 0) {
      setInterval(refresh, intervalMs);
    }

    document.addEventListener(STATUS_REFRESH_EVENT, refresh);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        refresh();
      }
    });

    section.dataset.statusInitialized = '1';
    refresh();
  };

  document.addEventListener('DOMContentLoaded', () => {
    setupStatusSummary();

    const editBtn = document.getElementById('profileEditBtn');
    const editor = document.getElementById('profileBioEditor');
    const display = document.getElementById('profileBioDisplay');
    const textEl = document.getElementById('profileBioText');
    const saveBtn = document.getElementById('saveBio');
    const cancelBtn = document.getElementById('cancelBio');
    const textarea = document.getElementById('bioText');
    const messageEl = document.getElementById('profileBioMessage');
    const dataEl = document.getElementById('initial-profile-bio');
    const updateUrl = editor && editor.dataset ? (editor.dataset.updateUrl || '') : '';

    if (!editBtn || !editor || !display || !textEl || !saveBtn || !cancelBtn || !textarea || !updateUrl) {
      return;
    }

    let currentBio = '';
    if (dataEl) {
      try {
        currentBio = JSON.parse(dataEl.textContent || '""');
      } catch (_error) {
        currentBio = textarea.value || '';
      }
    } else {
      currentBio = textarea.value || '';
    }

    const csrfToken = getCsrfToken();

    const escapeHtml = (value) => String(value || '').replace(/[&<>'"]/g, (char) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));

    const renderBio = (value) => {
      const trimmed = (value || '').trim();
      if (!textEl) {
        return;
      }
      if (trimmed) {
        textEl.classList.remove('text-muted');
        textEl.innerHTML = escapeHtml(value).replace(/\r?\n/g, '<br>');
        display.dataset.hasBio = '1';
      } else {
        textEl.classList.add('text-muted');
        textEl.textContent = '自己紹介はまだ設定されていません。';
        display.dataset.hasBio = '0';
      }
    };

    const toggleEditor = (show) => {
      if (show) {
        editor.classList.remove('d-none');
        display.classList.add('d-none');
        textarea.focus();
      } else {
        editor.classList.add('d-none');
        display.classList.remove('d-none');
      }
    };

    const showMessage = (text, variant) => {
      if (!messageEl) {
        return;
      }
      messageEl.classList.remove('alert-success', 'alert-danger');
      if (!text) {
        messageEl.classList.add('d-none');
        messageEl.textContent = '';
        return;
      }
      messageEl.textContent = text;
      messageEl.classList.remove('d-none');
      messageEl.classList.add(variant === 'danger' ? 'alert-danger' : 'alert-success');
    };

    editBtn.addEventListener('click', () => {
      textarea.value = currentBio;
      showMessage('', '');
      toggleEditor(true);
    });

    cancelBtn.addEventListener('click', () => {
      textarea.value = currentBio;
      toggleEditor(false);
      showMessage('', '');
    });

    saveBtn.addEventListener('click', () => {
      const newBio = textarea.value.trim();
      if (newBio.length > 100) {
        showMessage('自己紹介は100文字以内で入力してください。', 'danger');
        return;
      }

      saveBtn.disabled = true;
      showMessage('', '');

      fetch(updateUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({content_profile: newBio}),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error('failed');
          }
          return response.json();
        })
        .then((data) => {
          if (!data || !data.success) {
            throw new Error('failed');
          }
          currentBio = data.bio || '';
          renderBio(currentBio);
          toggleEditor(false);
          showMessage('プロフィールを更新しました。', 'success');
        })
        .catch(() => {
          showMessage('保存に失敗しました。時間をおいて再度お試しください。', 'danger');
        })
        .finally(() => {
          saveBtn.disabled = false;
        });
    });

    renderBio(currentBio);
  });

  window.SasutenaStatus = {
    refresh() {
      document.dispatchEvent(new CustomEvent(STATUS_REFRESH_EVENT));
    },
  };

  window.addEventListener('pageshow', () => {
    if (!document.hidden) {
      window.SasutenaStatus.refresh();
    }
  });
})();