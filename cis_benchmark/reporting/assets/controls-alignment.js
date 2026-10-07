'use strict';
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-controls-alignment]').forEach(panel => {
        const group = panel.querySelector('[data-ig-filter]');
        const search = panel.querySelector('[data-safeguard-search]');
        const unmapped = panel.querySelector('[data-show-unmapped]');
        const cards = Array.from(panel.querySelectorAll('[data-safeguard]'));
        const normalize = value => value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        const filter = () => {
            let visible = 0;
            const subset = cards.filter(card => !group.value || card.dataset.groups.split(' ').includes(group.value));
            const query = normalize(search.value.trim());
            cards.forEach(card => {
                card.hidden = (!unmapped.checked && card.dataset.mapped !== 'true') ||
                    (group.value && !card.dataset.groups.split(' ').includes(group.value)) ||
                    (query && !normalize(card.dataset.search).includes(query));
                if (!card.hidden) visible++;
            });
            panel.querySelector('[data-alignment-count]').textContent = `${visible} de ${subset.length} salvaguardas do grupo exibidas. ${subset.filter(card => card.dataset.mapped === 'true').length} relacionadas aos testes do projeto.`;
            panel.querySelector('[data-alignment-empty]').hidden = visible !== 0;
        };
        [group, search, unmapped].forEach(field => field.addEventListener('input', filter));
        filter();
        let printState;
        window.addEventListener('beforeprint', () => {
            if (printState) return;
            const details = panel.querySelector('.alignment-details');
            printState = {open: details.open, hidden: cards.map(card => card.hidden)};
            details.open = true;
            cards.forEach(card => { card.hidden = card.dataset.mapped !== 'true'; });
        });
        window.addEventListener('afterprint', () => {
            if (!printState) return;
            panel.querySelector('.alignment-details').open = printState.open;
            cards.forEach((card, index) => { card.hidden = printState.hidden[index]; });
            printState = null;
        });
    });
});
