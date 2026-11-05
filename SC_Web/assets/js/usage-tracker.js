/**
 * Records one portal_usage stay per signed-in viewer session.
 * The server takes the user email from the Auth0 session.
 */

function usageApiBase() {
    const path = window.location.pathname || '';
    if (path.includes('/portal/')) {
        return '/portal/api';
    }
    return '/api';
}

class UsageTracker {
    constructor() {
        this.stayId = null;
        this.dataset = null;
        this.dashboardId = null;
        this.startedAt = 0;
        this.chain = Promise.resolve();
        this.timer = setInterval(() => this.heartbeat(), 30000);
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                this.endStay(true);
            } else {
                this.resumeIfViewing();
            }
        });
        window.addEventListener('pagehide', () => this.endStay(true));
    }

    enqueue(work) {
        this.chain = this.chain.then(work).catch((error) => {
            console.warn('Usage tracker:', error);
        });
        return this.chain;
    }

    beginDataset(dataset) {
        const next = {
            dataset_id: dataset?.dataset_id || dataset?.id || '',
            dataset_uuid: dataset?.dataset_uuid || dataset?.uuid || '',
            dataset_name: dataset?.dataset_name || dataset?.name || '',
        };
        if (!next.dataset_id && !next.dataset_uuid) {
            return;
        }
        this.enqueue(() => this._beginDataset(next));
    }

    async _beginDataset(dataset) {
        await this._end();
        this.dataset = dataset;
        this.dashboardId = null;
        this.startedAt = Date.now();
        const response = await fetch(`${usageApiBase()}/usage.php`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'start',
                dataset_id: dataset.dataset_id,
                dataset_uuid: dataset.dataset_uuid,
                dataset_name: dataset.dataset_name,
            }),
        });
        if (!response.ok) {
            this.stayId = null;
            return;
        }
        const data = await response.json();
        this.stayId = data.stay_id || null;
    }

    noteDashboard(dashboardId) {
        const id = String(dashboardId || '').trim();
        if (!id) {
            return;
        }
        this.enqueue(() => this._noteDashboard(id));
    }

    async _noteDashboard(dashboardId) {
        const current = window.datasetManager?.currentDataset;
        if (current && this.dataset) {
            if (current.id) {
                this.dataset.dataset_id = current.id;
            }
            if (current.uuid) {
                this.dataset.dataset_uuid = current.uuid;
            }
            if (current.name) {
                this.dataset.dataset_name = current.name;
            }
        }
        if (this.dashboardId && this.dashboardId !== dashboardId && this.dataset) {
            const dataset = this.dataset;
            await this._end();
            await this._beginDataset(dataset);
        }
        if (!this.stayId) {
            return;
        }
        const loadMs = this.startedAt ? Math.max(0, Date.now() - this.startedAt) : 0;
        this.dashboardId = dashboardId;
        const dataset = this.dataset || {};
        await fetch(`${usageApiBase()}/usage.php`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'dashboard',
                stay_id: this.stayId,
                dashboard_id: dashboardId,
                load_ms: loadMs,
                dataset_id: dataset.dataset_id || '',
                dataset_uuid: dataset.dataset_uuid || '',
                dataset_name: dataset.dataset_name || '',
            }),
        });
    }

    heartbeat() {
        if (!this.stayId || document.visibilityState === 'hidden') {
            return;
        }
        const stayId = this.stayId;
        fetch(`${usageApiBase()}/usage.php`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'heartbeat', stay_id: stayId }),
        }).catch(() => {});
    }

    endStay(useBeacon) {
        const stayId = this.stayId;
        this.stayId = null;
        if (!stayId) {
            return;
        }
        const payload = JSON.stringify({ action: 'end', stay_id: stayId });
        if (useBeacon && navigator.sendBeacon) {
            const blob = new Blob([payload], { type: 'application/json' });
            navigator.sendBeacon(`${usageApiBase()}/usage.php`, blob);
            return;
        }
        this.enqueue(() => fetch(`${usageApiBase()}/usage.php`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: payload,
        }));
    }

    async _end() {
        const stayId = this.stayId;
        this.stayId = null;
        if (!stayId) {
            return;
        }
        await fetch(`${usageApiBase()}/usage.php`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'end', stay_id: stayId }),
        });
    }

    resumeIfViewing() {
        if (this.stayId || !this.dataset || !document.getElementById('dashboardFrame')) {
            return;
        }
        const dataset = this.dataset;
        const dashboardId = this.dashboardId;
        this.enqueue(async () => {
            await this._beginDataset(dataset);
            if (dashboardId) {
                await this._noteDashboard(dashboardId);
            }
        });
    }

    async dashboardAllowed(dashboardId, teamUuid) {
        try {
            const params = new URLSearchParams({
                dashboard_id: dashboardId || '',
                team_uuid: teamUuid || '',
            });
            const response = await fetch(`${usageApiBase()}/dashboard-allowed.php?${params}`, {
                credentials: 'same-origin',
            });
            if (!response.ok) {
                return { ok: true };
            }
            const data = await response.json();
            if (data.allowed === false) {
                return { ok: false, reason: data.reason || 'This dashboard is turned off for this team.' };
            }
            return { ok: true };
        } catch (error) {
            return { ok: true };
        }
    }
}

window.usageTracker = new UsageTracker();
