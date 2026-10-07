let currentStatusFilter = 'all';
let currentSeverityFilter = 'all';

function filterTable(query) {
    const rows = document.querySelectorAll('#allControlsTable tbody tr');
    const q = query.toLowerCase();
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matchText = !q || text.includes(q);
        const status = row.dataset.status;
        const severity = row.dataset.severity;
        const matchStatus = currentStatusFilter === 'all' || status === currentStatusFilter;
        const matchSev = currentSeverityFilter === 'all' || severity === currentSeverityFilter;
        row.style.display = matchText && matchStatus && matchSev ? '' : 'none';
    });
}

function filterStatus(status, btn) {
    currentStatusFilter = status;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filterTable(document.getElementById('searchInput').value);
}

function filterSeverity(severity, btn) {
    currentSeverityFilter = severity === currentSeverityFilter ? 'all' : severity;
    filterTable(document.getElementById('searchInput').value);
}
