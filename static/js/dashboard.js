(function () {
    const toast = document.getElementById('toast');
    const createBtn = document.getElementById('create-btn');
    const modal = document.getElementById('create-modal');
    const newTitle = document.getElementById('new-title');
    const confirmCreate = document.getElementById('confirm-create');
    const cancelCreate = document.getElementById('cancel-create');

    function showToast(msg, type) {
        toast.textContent = msg;
        toast.className = 'toast show ' + (type || '');
        setTimeout(() => toast.className = 'toast', 2200);
    }

    createBtn.addEventListener('click', () => {
        newTitle.value = '未命名白板';
        modal.hidden = false;
        newTitle.focus();
        newTitle.select();
    });

    cancelCreate.addEventListener('click', () => {
        modal.hidden = true;
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.hidden = true;
    });

    newTitle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') confirmCreate.click();
        if (e.key === 'Escape') modal.hidden = true;
    });

    confirmCreate.addEventListener('click', async () => {
        const title = newTitle.value.trim() || '未命名白板';
        try {
            const res = await fetch('/boards', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title})
            });
            const data = await res.json();
            if (!data.ok) {
                showToast(data.msg || '创建失败', 'error');
                return;
            }
            window.location.href = '/boards/' + data.board.id;
        } catch (err) {
            showToast('网络错误，请重试', 'error');
        }
    });

    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            if (!confirm('确定删除该白板？此操作不可撤销。')) return;
            try {
                const res = await fetch('/boards/' + id + '/delete', {method: 'POST'});
                const data = await res.json();
                if (!data.ok) {
                    showToast(data.msg || '删除失败', 'error');
                    return;
                }
                const card = btn.closest('.board-card');
                if (card) card.remove();
                showToast('已删除', 'success');
            } catch (err) {
                showToast('网络错误，请重试', 'error');
            }
        });
    });
})();
