/**
 * Administrator dashboard: usage, resources, allocations, cost, access, workflows.
 */

function adminApiBase() {
    const path = window.location.pathname || '';
    return path.includes('/portal/') ? '/portal/api' : '/api';
}

class AdminDashboard {
    constructor() {
        this.section = 'usage';
        this.catalog = [];
        this.teams = [];
        this.workflows = [];
        const button = document.getElementById('viewAdminBtn');
        if (button) {
            button.addEventListener('click', () => this.show());
        }
    }

    escape(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    formatBytes(bytes) {
        const n = Number(bytes);
        if (!Number.isFinite(n)) {
            return '—';
        }
        const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
        let size = n;
        let unit = 0;
        while (size >= 1024 && unit < units.length - 1) {
            size /= 1024;
            unit += 1;
        }
        return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
    }

    formatDuration(ms) {
        const n = Number(ms);
        if (!Number.isFinite(n) || n <= 0) {
            return '—';
        }
        const seconds = Math.round(n / 1000);
        if (seconds < 60) {
            return `${seconds}s`;
        }
        const minutes = Math.floor(seconds / 60);
        const rem = seconds % 60;
        if (minutes < 60) {
            return `${minutes}m ${rem}s`;
        }
        const hours = Math.floor(minutes / 60);
        return `${hours}h ${minutes % 60}m`;
    }

    formatMoney(value) {
        if (value === null || value === undefined || value === '') {
            return 'unset';
        }
        const n = Number(value);
        if (!Number.isFinite(n)) {
            return 'unset';
        }
        return n.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
    }

    async show() {
        if (window.usageTracker) {
            window.usageTracker.endStay(false);
        }
        const viewer = document.getElementById('viewerContainer');
        if (!viewer) {
            return;
        }
        const month = new Date().toISOString().slice(0, 7);
        viewer.innerHTML = `
            <div class="admin-dashboard">
                <div class="d-flex align-items-center justify-content-between mb-3">
                    <h4 class="mb-0">Administrator</h4>
                </div>
                <ul class="nav nav-tabs" id="adminTabs">
                    ${this.tab('usage', 'Usage')}
                    ${this.tab('resources', 'Resources')}
                    ${this.tab('allocations', 'Allocations')}
                    ${this.tab('cost', 'Cost')}
                    ${this.tab('access', 'Access')}
                    ${this.tab('workflows', 'Workflows')}
                </ul>
                <div class="admin-dashboard-body pt-3" id="adminBody"></div>
            </div>`;
        viewer.querySelectorAll('[data-admin-tab]').forEach((button) => {
            button.addEventListener('click', () => {
                this.section = button.getAttribute('data-admin-tab');
                viewer.querySelectorAll('[data-admin-tab]').forEach((el) => {
                    el.classList.toggle('active', el === button);
                });
                this.renderSection();
            });
        });
        this.month = month;
        this.renderSection();
    }

    tab(id, label) {
        const active = id === 'usage' ? ' active' : '';
        return `<li class="nav-item"><button type="button" class="nav-link${active}" data-admin-tab="${id}">${label}</button></li>`;
    }

    async renderSection() {
        const body = document.getElementById('adminBody');
        if (!body) {
            return;
        }
        body.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';
        try {
            if (this.section === 'usage') {
                body.innerHTML = this.usageForm();
                this.bindUsageForm();
                await this.loadUsage();
                return;
            }
            if (this.section === 'resources') {
                const data = await this.get('resources');
                body.innerHTML = this.resourcesHtml(data);
                return;
            }
            if (this.section === 'allocations') {
                const data = await this.get('allocations');
                body.innerHTML = this.allocationsHtml(data.allocations || []);
                this.bindAllocationForm();
                return;
            }
            if (this.section === 'cost') {
                body.innerHTML = this.costForm();
                this.bindCostForm();
                await this.loadCost();
                return;
            }
            if (this.section === 'access') {
                const data = await this.get('access');
                body.innerHTML = this.accessHtml(data);
                return;
            }
            if (this.section === 'workflows') {
                const data = await this.get('workflows');
                this.catalog = data.dashboards || [];
                this.teams = data.teams || [];
                this.workflows = data.workflows || [];
                body.innerHTML = this.workflowsHtml();
                this.bindWorkflowForm();
            }
        } catch (error) {
            body.innerHTML = `<div class="alert alert-danger">${this.escape(error.message)}</div>`;
        }
    }

    async get(section, params) {
        const query = new URLSearchParams({ section, ...(params || {}) });
        const response = await fetch(`${adminApiBase()}/admin-dashboard.php?${query}`, { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok || data.success === false) {
            throw new Error(data.error || 'Request failed');
        }
        return data;
    }

    async post(payload) {
        const response = await fetch(`${adminApiBase()}/admin-dashboard.php`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok || data.success === false) {
            throw new Error(data.error || 'Save failed');
        }
        return data;
    }

    usageForm() {
        return `
            <form id="adminUsageFilters" class="row g-2 align-items-end mb-3">
                <div class="col-md-3"><label class="form-label">User email</label><input class="form-control" name="user_email"></div>
                <div class="col-md-3"><label class="form-label">Dataset</label><input class="form-control" name="dataset"></div>
                <div class="col-md-2"><label class="form-label">Dashboard</label><input class="form-control" name="dashboard"></div>
                <div class="col-md-2"><label class="form-label">From</label><input class="form-control" type="date" name="from"></div>
                <div class="col-md-2"><label class="form-label">To</label><input class="form-control" type="date" name="to"></div>
                <div class="col-12"><button class="btn btn-primary" type="submit">Apply</button></div>
            </form>
            <div id="adminUsageResults"></div>`;
    }

    bindUsageForm() {
        const form = document.getElementById('adminUsageFilters');
        if (!form) {
            return;
        }
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            this.loadUsage();
        });
    }

    async loadUsage() {
        const results = document.getElementById('adminUsageResults');
        const form = document.getElementById('adminUsageFilters');
        if (!results || !form) {
            return;
        }
        const params = new URLSearchParams(new FormData(form));
        if (params.get('from')) {
            params.set('from', `${params.get('from')}T00:00:00+00:00`);
        }
        if (params.get('to')) {
            params.set('to', `${params.get('to')}T23:59:59+00:00`);
        }
        params.set('limit', '200');
        const response = await fetch(`${adminApiBase()}/usage.php?${params}`, { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok || data.success === false) {
            throw new Error(data.error || 'Could not load usage');
        }
        results.innerHTML = `
            ${this.summaryTable('By user', data.by_user || [], (row) => `<td>${this.escape(row.user_email)}</td><td>${row.opens}</td><td>${this.formatDuration(row.dwell_ms)}</td>`)}
            ${this.summaryTable('By dataset', data.by_dataset || [], (row) => `<td>${this.escape(row.dataset_name || row.dataset_uuid)}</td><td>${row.opens}</td><td>${this.formatDuration(row.dwell_ms)}</td>`)}
            ${this.summaryTable('By dashboard', data.by_dashboard || [], (row) => `<td>${this.escape(row.dashboard_id)}</td><td>${row.opens}</td><td>${this.formatDuration(row.dwell_ms)}</td>`)}
            <h6 class="mt-3">Recent views</h6>
            <div class="table-responsive"><table class="table table-sm">
                <thead><tr><th>User</th><th>Dataset</th><th>Dashboard</th><th>Load</th><th>Dwell</th><th>Started</th></tr></thead>
                <tbody>
                ${(data.rows || []).map((row) => `<tr>
                    <td>${this.escape(row.user_email)}</td>
                    <td>${this.escape(row.dataset_name || row.dataset_uuid)}</td>
                    <td>${this.escape(row.dashboard_id || '')}</td>
                    <td>${row.load_ms == null ? '—' : this.formatDuration(row.load_ms)}</td>
                    <td>${this.formatDuration(row.dwell_ms)}</td>
                    <td>${this.escape(row.started_at || '')}</td>
                </tr>`).join('') || '<tr><td colspan="6">No views recorded.</td></tr>'}
                </tbody></table></div>`;
    }

    summaryTable(title, rows, cell) {
        return `<h6>${title}</h6><div class="table-responsive"><table class="table table-sm"><thead><tr><th></th><th>Opens</th><th>Dwell</th></tr></thead><tbody>
            ${rows.slice(0, 20).map((row) => `<tr>${cell(row)}</tr>`).join('') || '<tr><td colspan="3">None</td></tr>'}
        </tbody></table></div>`;
    }

    resourcesHtml(data) {
        const disk = data.disk || {};
        return `
            <p>Data volume ${this.escape(disk.path || 'not mounted')}:
                ${this.formatBytes(disk.used_bytes)} used,
                ${this.formatBytes(disk.free_bytes)} free,
                ${this.formatBytes(disk.total_bytes)} capacity.</p>
            <h6>By user</h6>
            ${this.byteTable(data.users || [], (row) => this.escape(row.user_email), (row) => row.datasets)}
            <h6 class="mt-3">By team</h6>
            ${this.byteTable(data.teams || [], (row) => this.escape(row.team_name || row.team_uuid), (row) => row.datasets)}`;
    }

    byteTable(rows, label, count) {
        return `<div class="table-responsive"><table class="table table-sm"><thead><tr><th>Name</th><th>Datasets</th><th>Size</th></tr></thead><tbody>
            ${rows.map((row) => `<tr><td>${label(row)}</td><td>${count(row)}</td><td>${this.formatBytes(row.bytes)}</td></tr>`).join('') || '<tr><td colspan="3">None</td></tr>'}
        </tbody></table></div>`;
    }

    allocationsHtml(rows) {
        const existing = rows.map((row) => `<tr>
            <td>${this.escape(row.subject_type)}</td>
            <td>${this.escape(row.subject_id)}</td>
            <td>${row.seat_limit == null ? 'unset' : this.escape(row.seat_limit)}</td>
            <td>${this.formatMoney(row.usd_per_gb_month)}</td>
            <td>${this.formatMoney(row.usd_per_viewer_hour)}</td>
        </tr>`).join('');
        return `
            <form id="adminAllocationForm" class="row g-2 align-items-end mb-3">
                <div class="col-md-2"><label class="form-label">Type</label>
                    <select class="form-select" name="subject_type"><option value="user">User</option><option value="team">Team</option></select></div>
                <div class="col-md-3"><label class="form-label">Email or team UUID</label><input class="form-control" name="subject_id" required></div>
                <div class="col-md-2"><label class="form-label">Seats</label><input class="form-control" name="seat_limit" type="number" min="1" step="1"></div>
                <div class="col-md-2"><label class="form-label">USD / GB-month</label><input class="form-control" name="usd_per_gb_month" type="number" min="0" step="any"></div>
                <div class="col-md-2"><label class="form-label">USD / viewer-hour</label><input class="form-control" name="usd_per_viewer_hour" type="number" min="0" step="any"></div>
                <div class="col-12"><button class="btn btn-primary" type="submit">Save allocation</button> <span id="adminAllocationStatus"></span></div>
            </form>
            <p class="text-muted">Leave a number blank to leave that limit or rate unset. There is no upload size cap. Viewer time is priced here and is not cut off during a session.</p>
            <div class="table-responsive"><table class="table table-sm"><thead><tr>
                <th>Type</th><th>Subject</th><th>Seats</th><th>USD / GB-month</th><th>USD / viewer-hour</th>
            </tr></thead><tbody>${existing || '<tr><td colspan="5">No allocations yet.</td></tr>'}</tbody></table></div>`;
    }

    bindAllocationForm() {
        const form = document.getElementById('adminAllocationForm');
        if (!form) {
            return;
        }
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const status = document.getElementById('adminAllocationStatus');
            const data = new FormData(form);
            const seats = data.get('seat_limit');
            const gbRate = data.get('usd_per_gb_month');
            const hourRate = data.get('usd_per_viewer_hour');
            try {
                await this.post({
                    action: 'save_allocation',
                    subject_type: data.get('subject_type'),
                    subject_id: data.get('subject_id'),
                    space_bytes: null,
                    seat_limit: seats === '' ? null : Number(seats),
                    usd_per_gb_month: gbRate === '' ? null : Number(gbRate),
                    usd_per_viewer_hour: hourRate === '' ? null : Number(hourRate),
                });
                if (status) {
                    status.textContent = 'Saved.';
                }
                this.renderSection();
            } catch (error) {
                if (status) {
                    status.textContent = error.message;
                }
            }
        });
    }

    costForm() {
        const month = this.month || new Date().toISOString().slice(0, 7);
        return `
            <form id="adminCostForm" class="row g-2 align-items-end mb-3">
                <div class="col-md-3"><label class="form-label">Month</label><input class="form-control" type="month" name="month" value="${month}"></div>
                <div class="col-md-2"><button class="btn btn-primary" type="submit">Show</button></div>
            </form>
            <p class="text-muted">Costs are computed from bytes in use and viewer time recorded this month. Unset rates stay unset.</p>
            <div id="adminCostResults"></div>`;
    }

    bindCostForm() {
        const form = document.getElementById('adminCostForm');
        if (!form) {
            return;
        }
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            this.month = new FormData(form).get('month');
            this.loadCost();
        });
    }

    async loadCost() {
        const form = document.getElementById('adminCostForm');
        const results = document.getElementById('adminCostResults');
        if (!form || !results) {
            return;
        }
        const month = new FormData(form).get('month');
        const data = await this.get('cost', { month });
        const userRows = (data.users || []).map((row) => `<tr>
            <td>${this.escape(row.subject_id)}</td>
            <td>${this.formatBytes(row.bytes)}</td>
            <td>${this.formatDuration(row.dwell_ms)}</td>
            <td>${this.formatMoney(row.space_cost)}</td>
            <td>${this.formatMoney(row.time_cost)}</td>
            <td>${this.formatMoney(row.total_cost)}</td>
        </tr>`).join('');
        const teamRows = (data.teams || []).map((row) => `<tr>
            <td>${this.escape(row.team_name || row.subject_id)}</td>
            <td>${this.formatBytes(row.bytes)}</td>
            <td>${this.formatMoney(row.space_cost)}</td>
        </tr>`).join('');
        results.innerHTML = `
            <h6>Users</h6>
            <div class="table-responsive"><table class="table table-sm"><thead><tr>
                <th>Email</th><th>Space</th><th>Viewer time</th><th>Space cost</th><th>Time cost</th><th>Total</th>
            </tr></thead><tbody>${userRows || '<tr><td colspan="6">None</td></tr>'}</tbody></table></div>
            <h6 class="mt-3">Teams</h6>
            <div class="table-responsive"><table class="table table-sm"><thead><tr>
                <th>Team</th><th>Space</th><th>Space cost</th>
            </tr></thead><tbody>${teamRows || '<tr><td colspan="3">None</td></tr>'}</tbody></table></div>`;
    }

    accessHtml(data) {
        const counts = data.counts || {};
        const rows = (data.datasets || []).map((row) => `<tr>
            <td>${this.escape(row.name)}</td>
            <td>${this.escape(row.access)}</td>
            <td>${this.escape(row.owner_email)}</td>
            <td>${this.formatBytes(row.bytes)}</td>
        </tr>`).join('');
        return `
            <p>Public ${counts.public || 0} · Shared ${counts.shared || 0} · Private ${counts.private || 0}
            ${data.truncated ? ' · list shows the first 300 datasets' : ''}</p>
            <div class="table-responsive"><table class="table table-sm"><thead><tr>
                <th>Dataset</th><th>Access</th><th>Owner</th><th>Size</th>
            </tr></thead><tbody>${rows || '<tr><td colspan="4">None</td></tr>'}</tbody></table></div>`;
    }

    workflowsHtml() {
        const teamOptions = this.teams.map((team) => {
            const label = team.team_name || team.team_uuid;
            return `<option value="${this.escape(team.team_uuid)}">${this.escape(label)}</option>`;
        }).join('');
        const checks = this.catalog.map((dash) => `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" name="enabled" value="${this.escape(dash.id)}" id="wf-${this.escape(dash.id)}">
                <label class="form-check-label" for="wf-${this.escape(dash.id)}">${this.escape(dash.name)}</label>
            </div>`).join('');
        return `
            <form id="adminWorkflowForm">
                <div class="mb-2"><label class="form-label">Team</label>
                    <select class="form-select" name="team_uuid" id="adminWorkflowTeam">${teamOptions}</select></div>
                <div class="form-check mb-2">
                    <input class="form-check-input" type="checkbox" id="adminWorkflowRestricted">
                    <label class="form-check-label" for="adminWorkflowRestricted">Limit this team to the dashboards checked below</label>
                </div>
                <div id="adminWorkflowChecks">${checks}</div>
                <button class="btn btn-primary mt-3" type="submit">Save workflows</button>
                <span id="adminWorkflowStatus" class="ms-2"></span>
            </form>
            <p class="text-muted mt-3">A team with no saved limit keeps every dashboard. Saving a limit turns off any dashboard that is not checked.</p>`;
    }

    bindWorkflowForm() {
        const form = document.getElementById('adminWorkflowForm');
        const select = document.getElementById('adminWorkflowTeam');
        if (!form || !select) {
            return;
        }
        const apply = () => {
            const saved = this.workflows.find((row) => row.team_uuid === select.value);
            const restricted = document.getElementById('adminWorkflowRestricted');
            if (restricted) {
                restricted.checked = !!(saved && saved.restricted);
            }
            const enabled = new Set((saved && saved.enabled) || []);
            form.querySelectorAll('input[name="enabled"]').forEach((input) => {
                input.checked = enabled.has(input.value);
            });
        };
        select.addEventListener('change', apply);
        apply();
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const status = document.getElementById('adminWorkflowStatus');
            const restricted = document.getElementById('adminWorkflowRestricted');
            const enabled = Array.from(form.querySelectorAll('input[name="enabled"]:checked')).map((input) => input.value);
            try {
                await this.post({
                    action: 'save_workflows',
                    team_uuid: select.value,
                    restricted: !!(restricted && restricted.checked),
                    enabled,
                });
                if (status) {
                    status.textContent = 'Saved.';
                }
                this.renderSection();
            } catch (error) {
                if (status) {
                    status.textContent = error.message;
                }
            }
        });
    }
}

window.adminDashboard = new AdminDashboard();
