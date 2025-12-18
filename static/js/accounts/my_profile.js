(function () {
  const getCsrfToken = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  };

  document.addEventListener('DOMContentLoaded', () => {
    const editBtn = document.getElementById('profileEditBtn');
    const editor = document.getElementById('profileBioEditor');
    const display = document.getElementById('profileBioDisplay');
    const textEl = document.getElementById('profileBioText');
    const saveBtn = document.getElementById('saveBio');
    const cancelBtn = document.getElementById('cancelBio');
    const textarea = document.getElementById('bioText');
    const messageEl = document.getElementById('profileBioMessage');
    const dataEl = document.getElementById('initial-profile-bio');
    const updateUrl = '{% url "accounts:update_profile_bio" %}';

    if (!editBtn || !editor || !display || !textEl || !saveBtn || !cancelBtn || !textarea) {
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
})();