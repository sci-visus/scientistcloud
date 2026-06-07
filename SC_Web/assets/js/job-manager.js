/**
 * Job Manager — upload/conversion status for the current user (and all users for admins).
 */

function getApiBasePath() {
    const path = window.location.pathname;
    if (path.includes('/portal/')) {
        return '/portal/api';
    }
    return '/api';
}

class JobManager {
    constructor() {
        this.activeJobs = [];
        this.liveStatus = new Map();
        this.refreshInterval = null;
        this.isAdmin = false;
        this.adminView = false;
        this.scope = 'active';
        this.filterUserEmail = '';
        this.initialize();
    }

    initialize() {
        const viewJobsBtn = document.getElementById('viewJobsBtn');
        if (viewJobsBtn) {
            viewJobsBtn.addEventListener('click', () => this.showJobsInterface());
        }
        this.loadUserCapabilities();
    }

    async loadUserCapabilities() {
        try {
            const response = await fetch(`${getApiBasePath()}/user-info.php`);
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            this.isAdmin = !!(data.is_admin || data.user?.is_admin);
        } catch (e) {
            console.warn('Could not load user capabilities for jobs page:', e);
        }
    }

    async showJobsInterface() {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) {
            return;
        }

        viewerContainer.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading jobs...</p>
            </div>
        `;

        try {
            const jobs = await this.fetchJobs();
            this.activeJobs = jobs;
            await this.enrichActiveJobStatuses(jobs);
            this.renderJobsInterface(jobs);
        } catch (error) {
            console.error('Error loading jobs:', error);
            viewerContainer.innerHTML = `
                <div class="alert alert-danger m-4" role="alert">
                    <h5><i class="fas fa-exclamation-triangle"></i> Error Loading Jobs</h5>
                    <p class="mb-0">Failed to load jobs: ${this.escapeHtml(error.message)}</p>
                    <button class="btn btn-primary mt-3" type="button" onclick="window.jobManager.showJobsInterface()">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </div>
            `;
        }
    }

    buildJobsQuery() {
        const params = new URLSearchParams();
        params.set('limit', '100');
        params.set('scope', this.scope);
        if (this.adminView && this.isAdmin) {
            params.set('admin', '1');
            if (this.filterUserEmail.trim()) {
                params.set('user_email', this.filterUserEmail.trim());
            }
        }
        return params.toString();
    }

    async fetchJobs() {
        const response = await fetch(`${getApiBasePath()}/jobs.php?${this.buildJobsQuery()}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch jobs');
        }
        if (typeof data.is_admin === 'boolean') {
            this.isAdmin = data.is_admin;
        }
        return data.jobs || [];
    }

    isTerminalStatus(status) {
        const s = String(status || '').toLowerCase();
        return ['ready', 'uploaded', 'completed', 'done', 'failed', 'error', 'conversion failed', 'cancelled', 'canceled'].includes(s);
    }

    shouldPollUploadStatus(job) {
        const jobId = job.job_id || job.id;
        if (!jobId || String(jobId).startsWith('dataset_')) {
            return false;
        }
        return !this.isTerminalStatus(job.canonical_state || job.status);
    }

    async enrichActiveJobStatuses(jobs) {
        const toPoll = jobs.filter((job) => this.shouldPollUploadStatus(job));
        await Promise.all(toPoll.map(async (job) => {
            const jobId = job.job_id || job.id;
            try {
                const response = await fetch(`${getApiBasePath()}/upload-status.php?job_id=${encodeURIComponent(jobId)}`);
                if (!response.ok) {
                    return;
                }
                const status = await response.json();
                if (status.job_id) {
                    this.liveStatus.set(jobId, status);
                }
            } catch (e) {
                console.warn(`upload-status failed for ${jobId}:`, e);
            }
        }));
    }

    getJobDisplayFields(job) {
        const jobId = job.job_id || job.id;
        const live = this.liveStatus.get(jobId);
        return {
            status: live?.canonical_state || live?.status || job.canonical_state || job.status,
            progress: live?.progress_percentage ?? job.progress_percentage ?? job.progress ?? 0,
            message: live?.message || job.message || '',
            bytesUploaded: live?.bytes_uploaded ?? job.bytes_uploaded,
            bytesTotal: live?.bytes_total ?? job.bytes_total,
            error: live?.error || job.error,
        };
    }

    renderJobsInterface(jobs) {
        const viewerContainer = document.getElementById('viewerContainer');
        const enriched = jobs.map((job) => ({ job, display: this.getJobDisplayFields(job) }));

        const jobsByStatus = {
            processing: enriched.filter(({ display }) => {
                const s = String(display.status || '').toLowerCase();
                return ['processing', 'queued', 'converting', 'conversion queued', 'uploading', 'pending', 'running'].includes(s);
            }),
            completed: enriched.filter(({ display }) => {
                const s = String(display.status || '').toLowerCase();
                return ['completed', 'done', 'ready', 'uploaded'].includes(s);
            }),
            failed: enriched.filter(({ display }) => {
                const s = String(display.status || '').toLowerCase();
                return ['failed', 'error', 'conversion failed'].includes(s);
            }),
            cancelled: enriched.filter(({ display }) => String(display.status || '').toLowerCase() === 'cancelled'),
        };

        const adminControls = this.isAdmin ? `
            <div class="card mb-3 border-warning">
                <div class="card-body py-2">
                    <div class="form-check form-switch mb-2">
                        <input class="form-check-input" type="checkbox" id="jobsAdminViewToggle" ${this.adminView ? 'checked' : ''}>
                        <label class="form-check-label" for="jobsAdminViewToggle">Admin: show all users' jobs</label>
                    </div>
                    <div class="row g-2 ${this.adminView ? '' : 'd-none'}" id="jobsAdminFilters">
                        <div class="col-md-4">
                            <select class="form-select form-select-sm" id="jobsScopeSelect">
                                <option value="active" ${this.scope === 'active' ? 'selected' : ''}>Active only</option>
                                <option value="all" ${this.scope === 'all' ? 'selected' : ''}>Active + recent finished</option>
                            </select>
                        </div>
                        <div class="col-md-8">
                            <input type="email" class="form-control form-control-sm" id="jobsUserFilter"
                                   placeholder="Filter by owner email (optional)"
                                   value="${this.escapeHtml(this.filterUserEmail)}">
                        </div>
                    </div>
                    <small class="text-muted">Set <code>SC_PORTAL_ADMIN_EMAILS</code> on the server to grant admin access.</small>
                </div>
            </div>
        ` : '';

        viewerContainer.innerHTML = `
            <div class="jobs-interface container-fluid mt-3 mb-4">
                <div class="card">
                    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center flex-wrap gap-2">
                        <h5 class="mb-0"><i class="fas fa-tasks"></i> Jobs &amp; Upload Status</h5>
                        <div>
                            <button class="btn btn-sm btn-light" type="button" onclick="window.jobManager.refreshJobs()" title="Refresh">
                                <i class="fas fa-sync-alt"></i> Refresh
                            </button>
                            <button class="btn btn-sm btn-light ms-1" type="button" onclick="window.jobManager.closeJobsInterface()" title="Close">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <p class="text-muted small mb-3">
                            Live progress comes from <code>upload-status.php</code> (FastAPI). Browser uploads show here after the server accepts the file and returns a <code>job_id</code>.
                        </p>
                        ${adminControls}
                        <div class="row mb-4 g-2">
                            <div class="col-md-3"><div class="card bg-info text-white"><div class="card-body text-center py-2"><h4 class="mb-0">${jobsByStatus.processing.length}</h4><small>Active</small></div></div></div>
                            <div class="col-md-3"><div class="card bg-success text-white"><div class="card-body text-center py-2"><h4 class="mb-0">${jobsByStatus.completed.length}</h4><small>Completed</small></div></div></div>
                            <div class="col-md-3"><div class="card bg-danger text-white"><div class="card-body text-center py-2"><h4 class="mb-0">${jobsByStatus.failed.length}</h4><small>Failed</small></div></div></div>
                            <div class="col-md-3"><div class="card bg-secondary text-white"><div class="card-body text-center py-2"><h4 class="mb-0">${jobs.length}</h4><small>Listed</small></div></div></div>
                        </div>
                        <div class="accordion" id="jobsAccordion">
                            ${this.renderJobSection('Active', jobsByStatus.processing, 'processing')}
                            ${this.renderJobSection('Completed', jobsByStatus.completed, 'completed')}
                            ${this.renderJobSection('Failed', jobsByStatus.failed, 'failed')}
                            ${this.renderJobSection('Cancelled', jobsByStatus.cancelled, 'cancelled')}
                        </div>
                        ${jobs.length === 0 ? `<div class="alert alert-info mt-3 mb-0"><i class="fas fa-info-circle"></i> No jobs in this view. Try scope &quot;Active + recent finished&quot; or start an upload.</div>` : ''}
                    </div>
                </div>
            </div>
        `;

        this.bindJobsControls();
        setTimeout(() => this.setupLogViewers(), 100);
        if (jobsByStatus.processing.length > 0) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }

    bindJobsControls() {
        const adminToggle = document.getElementById('jobsAdminViewToggle');
        if (adminToggle) {
            adminToggle.addEventListener('change', (e) => {
                this.adminView = e.target.checked;
                const filters = document.getElementById('jobsAdminFilters');
                if (filters) {
                    filters.classList.toggle('d-none', !this.adminView);
                }
                this.showJobsInterface();
            });
        }
        const scopeSelect = document.getElementById('jobsScopeSelect');
        if (scopeSelect) {
            scopeSelect.addEventListener('change', (e) => {
                this.scope = e.target.value;
                this.showJobsInterface();
            });
        }
        const userFilter = document.getElementById('jobsUserFilter');
        if (userFilter) {
            userFilter.addEventListener('change', (e) => {
                this.filterUserEmail = e.target.value;
            });
            userFilter.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.filterUserEmail = e.target.value;
                    this.showJobsInterface();
                }
            });
        }
    }

    closeJobsInterface() {
        this.stopAutoRefresh();
        const viewerContainer = document.getElementById('viewerContainer');
        if (viewerContainer) {
            viewerContainer.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-chart-area fa-3x mb-3"></i>
                    <p>Select a dataset to view</p>
                </div>
            `;
        }
    }

    renderJobSection(title, items, statusId) {
        if (!items.length) {
            return '';
        }
        const isExpanded = statusId === 'processing';
        return `
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading${statusId}">
                    <button class="accordion-button ${isExpanded ? '' : 'collapsed'}" type="button"
                            data-bs-toggle="collapse" data-bs-target="#collapse${statusId}"
                            aria-expanded="${isExpanded}">
                        <i class="fas fa-${this.getStatusIcon(statusId)} me-2"></i>${title} (${items.length})
                    </button>
                </h2>
                <div id="collapse${statusId}" class="accordion-collapse collapse ${isExpanded ? 'show' : ''}" data-bs-parent="#jobsAccordion">
                    <div class="accordion-body">
                        ${items.map(({ job }, index) => this.renderJobItem(job, index)).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    formatBytes(value) {
        const n = Number(value);
        if (!n || n <= 0) {
            return null;
        }
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let pow = Math.floor(Math.log(n) / Math.log(1024));
        pow = Math.min(pow, units.length - 1);
        return `${(n / Math.pow(1024, pow)).toFixed(pow >= 2 ? 1 : 0)} ${units[pow]}`;
    }

    renderJobItem(job, index) {
        const display = this.getJobDisplayFields(job);
        const jobId = job.job_id || job.id;
        const datasetUuid = job.dataset_uuid;
        const statusBadge = this.getStatusBadge(display.status);
        const progressBar = this.getProgressBar(job, display);
        const timeInfo = this.getTimeInfo(job);
        const bytesLine = (display.bytesUploaded != null && display.bytesTotal != null)
            ? `<small class="text-muted d-block">Transferred: ${this.formatBytes(display.bytesUploaded)} / ${this.formatBytes(display.bytesTotal)}</small>`
            : '';
        const ownerLine = job.owner_email
            ? `<small class="text-muted d-block"><i class="fas fa-user"></i> ${this.escapeHtml(job.owner_email)}</small>`
            : '';
        const metaLine = [
            job.team_uuid ? `Team: ${this.escapeHtml(String(job.team_uuid))}` : '',
            job.folder ? `Folder: ${this.escapeHtml(String(job.folder))}` : '',
            job.sensor ? `Sensor: ${this.escapeHtml(String(job.sensor))}` : '',
        ].filter(Boolean).join(' · ');
        const showLogs = datasetUuid && !this.isTerminalStatus(display.status);
        const logId = `logs-${jobId}-${index}`.replace(/[^a-zA-Z0-9_-]/g, '_');

        return `
            <div class="card mb-3 job-status-card" data-job-id="${this.escapeHtml(jobId)}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start gap-2">
                        <div class="flex-grow-1">
                            <h6 class="card-title mb-1">
                                ${this.escapeHtml(job.dataset_name || job.name || 'Unnamed Dataset')}
                                ${statusBadge}
                            </h6>
                            <p class="card-text text-muted mb-1 small">
                                <i class="fas fa-tag"></i> ${this.escapeHtml(job.job_type || 'job')}
                                ${datasetUuid ? ` · <i class="fas fa-database"></i> <code>${this.escapeHtml(datasetUuid)}</code>` : ''}
                            </p>
                            ${ownerLine}
                            ${metaLine ? `<small class="text-muted d-block">${metaLine}</small>` : ''}
                            ${display.message ? `<small class="d-block mt-1">${this.escapeHtml(display.message)}</small>` : ''}
                            ${bytesLine}
                            ${progressBar}
                            ${timeInfo}
                            ${display.error ? `<div class="alert alert-danger py-1 px-2 mt-2 mb-0 small"><strong>Error:</strong> ${this.escapeHtml(display.error)}</div>` : ''}
                            ${showLogs ? `
                                <div class="mt-2">
                                    <button class="btn btn-sm btn-outline-info" type="button" data-bs-toggle="collapse" data-bs-target="#${logId}">
                                        <i class="fas fa-file-alt"></i> Conversion logs
                                    </button>
                                    <div class="collapse mt-2" id="${logId}">
                                        <pre class="job-logs-pre conversion-logs small mb-0" data-dataset-uuid="${this.escapeHtml(datasetUuid)}">Loading…</pre>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                        <div>
                            ${!this.isTerminalStatus(display.status) ? `
                                <button class="btn btn-sm btn-outline-danger" type="button" onclick="window.jobManager.cancelJob('${this.escapeHtml(jobId)}')" title="Cancel">
                                    <i class="fas fa-times"></i>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getStatusBadge(status) {
        const s = String(status || '').toLowerCase();
        const map = {
            queued: 'secondary', processing: 'info', converting: 'info',
            'conversion queued': 'secondary', uploading: 'info',
            completed: 'success', done: 'success', ready: 'success', uploaded: 'success',
            failed: 'danger', 'conversion failed': 'danger', error: 'danger',
            cancelled: 'secondary',
        };
        const color = map[s] || 'secondary';
        return `<span class="badge bg-${color} ms-1">${this.escapeHtml(status || 'unknown')}</span>`;
    }

    getProgressBar(job, display) {
        const progress = Number(display.progress) || 0;
        if (this.isTerminalStatus(display.status)) {
            return progress > 0 ? `
                <div class="progress mt-2" style="height: 18px;">
                    <div class="progress-bar bg-success" style="width: ${Math.min(100, progress)}%">${progress}%</div>
                </div>
            ` : '';
        }
        const indeterminate = progress <= 0;
        return `
            <div class="progress mt-2" style="height: 20px;">
                <div class="progress-bar progress-bar-striped ${indeterminate ? 'progress-bar-animated' : ''} bg-info"
                     style="width: ${indeterminate ? '100' : Math.min(100, progress)}%">
                    ${indeterminate ? 'In progress…' : `${progress}%`}
                </div>
            </div>
        `;
    }

    getTimeInfo(job) {
        const parts = [];
        const formatTime = (value) => (
            typeof formatPortalDate === 'function'
                ? formatPortalDate(value)
                : new Date(value).toLocaleString()
        );
        if (job.created_at) {
            parts.push(`Created: ${formatTime(job.created_at)}`);
        }
        if (job.updated_at) {
            parts.push(`Updated: ${formatTime(job.updated_at)}`);
        }
        return parts.length ? `<small class="text-muted d-block mt-2">${parts.join(' · ')}</small>` : '';
    }

    getStatusIcon(statusId) {
        const icons = { processing: 'spinner fa-spin', completed: 'check-circle', failed: 'exclamation-triangle', cancelled: 'ban' };
        return icons[statusId] || 'circle';
    }

    async refreshJobs() {
        try {
            const jobs = await this.fetchJobs();
            this.activeJobs = jobs;
            await this.enrichActiveJobStatuses(jobs);
            this.renderJobsInterface(jobs);
        } catch (error) {
            console.error('Error refreshing jobs:', error);
            alert('Failed to refresh jobs: ' + error.message);
        }
    }

    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => this.refreshJobs(), 8000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    setupLogViewers() {
        document.querySelectorAll('.collapse[id^="logs-"]').forEach((collapse) => {
            collapse.addEventListener('show.bs.collapse', () => {
                const pre = collapse.querySelector('.conversion-logs');
                if (pre && pre.dataset.datasetUuid && !pre.dataset.loaded) {
                    this.loadConversionLogs(pre.dataset.datasetUuid, pre);
                    pre.dataset.loaded = 'true';
                }
            });
        });
    }

    async loadConversionLogs(datasetUuid, container) {
        try {
            const response = await fetch(`${getApiBasePath()}/conversion-logs.php?dataset_uuid=${encodeURIComponent(datasetUuid)}`);
            const data = await response.json();
            if (data.success && data.logs) {
                container.textContent = data.logs;
            } else {
                container.textContent = data.error || 'No logs available.';
            }
        } catch (error) {
            container.textContent = 'Error loading logs: ' + error.message;
        }
    }

    async cancelJob(jobId) {
        if (!confirm('Cancel this job?')) {
            return;
        }
        try {
            const response = await fetch(`${getApiBasePath()}/cancel-job.php`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_id: jobId }),
            });
            const data = await response.json();
            if (data.success) {
                await this.refreshJobs();
            } else {
                alert('Error cancelling job: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Failed to cancel job: ' + error.message);
        }
    }

    escapeHtml(text) {
        if (text == null) {
            return '';
        }
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
}

let jobManager;
document.addEventListener('DOMContentLoaded', () => {
    jobManager = new JobManager();
    window.jobManager = jobManager;
});
