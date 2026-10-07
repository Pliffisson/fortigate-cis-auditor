'use strict';

document.addEventListener('DOMContentLoaded', () => {
    const key = 'fortigate-company-logo';
    const input = document.getElementById('logo-file');
    const logo = document.getElementById('company-logo');
    const fallback = document.getElementById('default-brand-icon');
    const remove = document.getElementById('remove-logo');
    const status = document.getElementById('logo-status');
    let revision = 0;
    const message = text => { status.textContent = text; status.hidden = !text; };
    const display = source => {
        if (source) logo.src = source;
        else logo.removeAttribute('src');
        logo.hidden = !source;
        fallback.hidden = Boolean(source);
        remove.hidden = !source;
    };
    try {
        const saved = localStorage.getItem(key);
        if (saved && saved.length < 1000000 && saved.startsWith('data:image/png;base64,')) display(saved);
    } catch (_) { /* Selection remains available when browser storage is disabled. */ }
    logo.addEventListener('error', () => display(null));
    input.addEventListener('change', async () => {
        const file = input.files[0];
        const current = ++revision;
        input.value = '';
        if (!file) return;
        if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
            message('Selecione uma imagem PNG, JPG ou WebP.');
            return;
        }
        if (!file.size || file.size > 2 * 1024 * 1024) {
            message('A imagem deve ter conteúdo e no máximo 2 MB.');
            return;
        }
        try {
            const source = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
            const picture = new Image();
            picture.src = source;
            await picture.decode();
            const scale = Math.min(1, 320 / picture.naturalWidth, 128 / picture.naturalHeight);
            const canvas = document.createElement('canvas');
            canvas.width = Math.max(1, Math.round(picture.naturalWidth * scale));
            canvas.height = Math.max(1, Math.round(picture.naturalHeight * scale));
            canvas.getContext('2d').drawImage(picture, 0, 0, canvas.width, canvas.height);
            const normalized = canvas.toDataURL('image/png');
            if (current !== revision) return;
            display(normalized);
            try {
                localStorage.setItem(key, normalized);
                message('Logo atualizada neste navegador.');
            } catch (_) { message('Logo aplicada. O navegador não permitiu salvar para próximas visitas.'); }
        } catch (_) {
            if (current === revision) message('Não foi possível abrir a imagem. Selecione outro arquivo.');
        }
    });
    remove.addEventListener('click', () => {
        ++revision;
        display(null);
        try { localStorage.removeItem(key); message('Logo removida.'); }
        catch (_) { message('Logo removida da tela. O navegador não permitiu atualizar o armazenamento.'); }
    });
});
