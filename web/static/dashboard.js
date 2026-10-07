function showFile(input) {
    const name = document.getElementById("fileName");
    const file = input.files && input.files[0];
    const panel = document.getElementById('selected-file');
    const error = document.getElementById('file-error');
    let message = '';
    if (file && !file.name.toLowerCase().endsWith('.conf')) message = 'Formato inválido. Selecione um arquivo com extensão .conf.';
    else if (file && file.size === 0) message = 'O arquivo está vazio. Selecione a configuração completa.';
    else if (file && file.size > Number(input.dataset.maxBytes)) message = 'O arquivo excede o limite do envio. Selecione um arquivo menor.';
    input.setCustomValidity(message);
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
    error.textContent = message;
    error.hidden = !message;
    panel.hidden = !file;
    name.textContent = file ? 'Arquivo selecionado' : 'Arraste seu arquivo .conf';
    if (file) {
        document.getElementById('selected-file-name').textContent = file.name;
        const units = file.size >= 1024 * 1024 ? [1024 * 1024, 'MB'] : [1024, 'KB'];
        document.getElementById('selected-file-size').textContent = `${(file.size / units[0]).toLocaleString('pt-BR', {maximumFractionDigits: 2})} ${units[1]}`;
    }
}



document.addEventListener("DOMContentLoaded", function () {
    const navigation = document.querySelector('.assessment-nav');
    if (navigation) {
        const links = Array.from(navigation.querySelectorAll('a'));
        const sections = links.map(link => document.getElementById(link.hash.slice(1))).filter(Boolean);
        let scheduled = false;
        const updateNavigation = () => {
            scheduled = false;
            const threshold = Math.max(navigation.getBoundingClientRect().bottom + 16,
                ...sections.map(section => parseFloat(getComputedStyle(section).scrollMarginTop) || 0)) + 2;
            let active = sections[0];
            sections.forEach(section => { if (section.getBoundingClientRect().top <= threshold) active = section; });
            links.forEach(link => {
                if (active && link.hash === `#${active.id}`) link.setAttribute('aria-current', 'location');
                else link.removeAttribute('aria-current');
            });
        };
        window.addEventListener('scroll', () => {
            if (!scheduled) { scheduled = true; window.requestAnimationFrame(updateNavigation); }
        }, {passive: true});
        window.addEventListener('resize', updateNavigation);
        updateNavigation();
    }
    const normalize = value => value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    const viewKey = document.querySelector('[data-view-key]')?.dataset.viewKey;
    document.querySelectorAll('[data-controls-panel]').forEach(panel => {
        const search = panel.querySelector('[data-search]');
        const level = panel.querySelector('select[data-level]');
        const category = panel.querySelector('select[data-category]');
        const status = panel.querySelector('select[data-status]');
        const sort = panel.querySelector('[data-sort]');
        const fields = {search, level, category, status, sort};
        const storageKey = viewKey ? `audit-filters:${viewKey}:${panel.id}` : null;
        try {
            const saved = storageKey ? JSON.parse(sessionStorage.getItem(storageKey)) : null;
            if (saved && typeof saved === 'object') {
                Object.entries(fields).forEach(([name, field]) => {
                    if (field && typeof saved[name] === 'string') {
                        if (field.tagName !== 'SELECT' || Array.from(field.options).some(option => option.value === saved[name])) field.value = saved[name];
                    }
                });
            }
        } catch (_) { /* Filtering remains available when browser storage is disabled. */ }
        const rows = Array.from(panel.querySelectorAll('[data-control-row]'));
        const filter = () => {
            const query = normalize(search.value.trim());
            let count = 0;
            rows.forEach(row => {
                const visible = (!query || normalize(row.dataset.searchText).includes(query)) &&
                    (!level.value || row.dataset.level === level.value) &&
                    (!category.value || row.dataset.category === category.value) &&
                    (!status || !status.value || row.dataset.status === status.value);
                row.hidden = !visible;
                if (visible) count++;
            });
            panel.querySelector('[data-filter-count]').textContent = `${count} de ${rows.length} controles exibidos`;
            panel.querySelector('[data-filter-empty]').hidden = count !== 0;
            const cisOrder = (a, b) => a.dataset.ruleId.localeCompare(b.dataset.ruleId, undefined, {numeric: true});
            const weights = {CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1};
            rows.sort((a, b) => {
                if (sort.value === 'level') return Number(a.dataset.level) - Number(b.dataset.level) || cisOrder(a, b);
                if (sort.value === 'severity') return (weights[b.dataset.severity] || 0) - (weights[a.dataset.severity] || 0) || cisOrder(a, b);
                return cisOrder(a, b);
            });
            const tbody = panel.querySelector('tbody');
            rows.forEach(row => tbody.appendChild(row));
            try {
                if (storageKey) sessionStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(
                    Object.entries(fields).filter(([, field]) => field).map(([name, field]) => [name, field.value])
                )));
            } catch (_) { /* Optional browser persistence. */ }
        };
        search.addEventListener('input', filter);
        [level, category, status, sort].filter(Boolean).forEach(field => field.addEventListener('change', filter));
        panel.querySelector('[data-clear-filters]').addEventListener('click', () => {
            [search, level, category, status].filter(Boolean).forEach(field => { field.value = ''; });
            sort.value = 'cis';
            filter();
            search.focus();
        });
        document.querySelectorAll('[data-status-shortcut]').forEach(link => {
            if (link.getAttribute('href') !== `#${panel.id}` || !status) return;
            link.addEventListener('click', () => {
                [search, level, category].forEach(field => { field.value = ''; });
                status.value = link.dataset.statusShortcut;
                filter();
                panel.querySelector('h3').setAttribute('tabindex', '-1');
                panel.querySelector('h3').focus({preventScroll: true});
            });
        });
        filter();
    });

    document.querySelectorAll('.copy-cli').forEach(button => {
        button.addEventListener('click', async () => {
            const details = button.closest('.cli-details');
            const code = details.querySelector('code');
            const status = details.querySelector('.copy-status');
            let copied = false;
            button.disabled = true;
            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(code.textContent);
                    copied = true;
                }
            } catch (_) { /* Try the user-initiated HTTP-compatible copy below. */ }
            if (!copied) {
                const field = document.createElement('textarea');
                field.value = code.textContent;
                field.setAttribute('readonly', '');
                field.style.position = 'fixed';
                field.style.left = '-9999px';
                document.body.appendChild(field);
                field.select();
                try { copied = document.execCommand('copy'); } catch (_) { copied = false; }
                field.remove();
            }
            button.disabled = false;
            button.focus();
            button.textContent = copied ? '✓ Copiado' : 'Copiar comandos';
            status.textContent = copied ? 'Comandos copiados.' : 'Selecione o texto dos comandos e copie manualmente.';
            if (copied) setTimeout(() => { button.textContent = 'Copiar comandos'; }, 2500);
        });
    });

    // Print all failures and pending controls, independently of active filters.
    let printState = null;
    const preparePrint = () => {
        if (printState) return;
        const rows = Array.from(document.querySelectorAll('[data-control-row]'));
        const details = Array.from(document.querySelectorAll('.control-details, .cli-details, .methodology'));
        printState = {rows: rows.map(row => [row, row.hidden]), details: details.map(detail => [detail, detail.open])};
        rows.forEach(row => {
            row.classList.toggle('print-omit', row.closest('#all-controls') !== null && !['MANUAL_REVIEW', 'ERROR'].includes(row.dataset.status));
            row.hidden = false;
        });
        details.forEach(detail => { detail.open = true; });
    };
    const restorePrint = () => {
        if (!printState) return;
        printState.rows.forEach(([row, hidden]) => { row.hidden = hidden; row.classList.remove('print-omit'); });
        printState.details.forEach(([detail, open]) => { detail.open = open; });
        printState = null;
    };
    window.addEventListener('beforeprint', preparePrint);
    window.addEventListener('afterprint', restorePrint);
    document.querySelector('[data-print-summary]')?.addEventListener('click', () => { window.print(); });

    const fileInput = document.getElementById('config-file');
    if (fileInput) {
        fileInput.addEventListener('change', function () { showFile(fileInput); });
        document.getElementById('replace-file')?.addEventListener('click', () => fileInput.click());
        showFile(fileInput);
    }

    const form = document.querySelector('.upload form');
    const button = form ? form.querySelector('.analyze') : null;

    if (!form || !button) {
        return;
    }

    form.addEventListener("submit", function (event) {

        /* Evita múltiplos envios */
        if (button.classList.contains("loading")) {
            event.preventDefault();
            return;
        }

        /* Estado visual de processamento */
        button.classList.add("loading");

        button.disabled = true;

        button.textContent =
            "ANALISANDO CONFIGURAÇÃO...";

    });

});
