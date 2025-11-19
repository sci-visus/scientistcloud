/**
 * Job Manager JavaScript
 * Handles viewing and monitoring of user jobs (uploads, conversions, etc.)
 */

// Helper function to get API base path
function getApiBasePath() {
    // Check if we're in a subdirectory (like /portal/)
    const path = window.location.pathname;
    if (path.includes('/portal/')) {
        return '/portal/api';
    }
    return '/api';
}

class JobManager {
    constructor() {
        this.activeJobs = [];
        this.refreshInterval = null;
        this.initialize();
    }

    /**
     * Initialize the job manager
     */
    initialize() {
        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // View Jobs button
        const viewJobsBtn = document.getElementById('viewJobsBtn');
        if (viewJobsBtn) {
            viewJobsBtn.addEventListener('click', () => {
                this.showJobsInterface();
            });
        }
    }

    /**
     * Show jobs interface
     */
    async showJobsInterface() {
        const viewerContainer = document.getElementById('viewerContainer');
        if (!viewerContainer) return;

        // Show loading state
        viewerContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading jobs...</p>
            </div>
        `;

        try {
            // Fetch jobs
            const jobs = await this.fetchJobs();
            this.activeJobs = jobs;

            // Render jobs interface
            this.renderJobsInterface(jobs);
        } catch (error) {
            console.error('Error loading jobs:', error);
            viewerContainer.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <h5><i class="fas fa-exclamation-triangle"></i> Error Loading Jobs</h5>
                    <p>Failed to load jobs: ${error.message}</p>
                    <button class="btn btn-primary" onclick="window.jobManager.showJobsInterface()">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </div>
            `;
        }
    }

    /**
     * Fetch jobs from API
     */
    async fetchJobs() {
        const response = await fetch(`${getApiBasePath()}/jobs.php`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch jobs');
        }
        return data.jobs || [];
    }

    /**
     * Render jobs interface
     */
    renderJobsInterface(jobs) {
        const viewerContainer = document.getElementById('viewerContainer');
        
        // Set up event listeners for log expansion after rendering
        setTimeout(() => {
            this.setupLogViewers();
        }, 100);
        
        // Group jobs by status (include converting status)
        const jobsByStatus = {
            'processing': jobs.filter(j => j.status === 'processing' || j.status === 'queued' || j.status === 'converting' || j.status === 'conversion queued'),
            'completed': jobs.filter(j => j.status === 'completed' || j.status === 'done'),
            'failed': jobs.filter(j => j.status === 'failed' || j.status === 'error' || j.status === 'conversion failed'),
            'cancelled': jobs.filter(j => j.status === 'cancelled')
        };

        const html = `
            <div class="jobs-interface container mt-4">
                <div class="card">
                    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">
                            <i class="fas fa-tasks"></i> Job Status
                        </h5>
                        <div>
                            <button class="btn btn-sm btn-light" onclick="window.jobManager.refreshJobs()" title="Refresh">
                                <i class="fas fa-sync-alt"></i> Refresh
                            </button>
                            <button class="btn btn-sm btn-light ms-2" onclick="window.jobManager.showJobsInterface()" title="Close">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <!-- Job Statistics -->
                        <div class="row mb-4">
                            <div class="col-md-3">
                                <div class="card bg-info text-white">
                                    <div class="card-body text-center">
                                        <h3>${jobsByStatus.processing.length}</h3>
                                        <p class="mb-0">Processing</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-success text-white">
                                    <div class="card-body text-center">
                                        <h3>${jobsByStatus.completed.length}</h3>
                                        <p class="mb-0">Completed</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-danger text-white">
                                    <div class="card-body text-center">
                                        <h3>${jobsByStatus.failed.length}</h3>
                                        <p class="mb-0">Failed</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-secondary text-white">
                                    <div class="card-body text-center">
                                        <h3>${jobs.length}</h3>
                                        <p class="mb-0">Total</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Jobs List -->
                        <div class="accordion" id="jobsAccordion">
                            ${this.renderJobSection('Processing', jobsByStatus.processing, 'processing')}
                            ${this.renderJobSection('Completed', jobsByStatus.completed, 'completed')}
                            ${this.renderJobSection('Failed', jobsByStatus.failed, 'failed')}
                            ${this.renderJobSection('Cancelled', jobsByStatus.cancelled, 'cancelled')}
                        </div>

                        ${jobs.length === 0 ? `
                            <div class="alert alert-info mt-4" role="alert">
                                <i class="fas fa-info-circle"></i> No jobs found. Upload a dataset to see jobs here.
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;

        viewerContainer.innerHTML = html;

        // Start auto-refresh for processing jobs
        if (jobsByStatus.processing.length > 0) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }

    /**
     * Render a job section
     */
    renderJobSection(title, jobs, statusId) {
        if (jobs.length === 0) {
            return '';
        }

        const isExpanded = statusId === 'processing';
        const jobsHtml = jobs.map((job, index) => this.renderJobItem(job, index)).join('');

        return `
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading${statusId}">
                    <button class="accordion-button ${isExpanded ? '' : 'collapsed'}" type="button" 
                            data-bs-toggle="collapse" data-bs-target="#collapse${statusId}" 
                            aria-expanded="${isExpanded}">
                        <i class="fas fa-${this.getStatusIcon(statusId)} me-2"></i>
                        ${title} (${jobs.length})
                    </button>
                </h2>
                <div id="collapse${statusId}" class="accordion-collapse collapse ${isExpanded ? 'show' : ''}" 
                     data-bs-parent="#jobsAccordion">
                    <div class="accordion-body">
                        ${jobsHtml}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render a single job item
     */
    renderJobItem(job, index) {
        const statusBadge = this.getStatusBadge(job.status);
        const progressBar = this.getProgressBar(job);
        const timeInfo = this.getTimeInfo(job);
        const jobId = job.job_id || job.id;
        const datasetUuid = job.dataset_uuid;
        
        // Show conversion logs for converting/processing jobs
        const showLogs = (job.status === 'processing' || job.status === 'converting' || job.status === 'queued') && datasetUuid;
        const logId = `logs-${jobId}`;

        return `
            <div class="card mb-3" data-job-id="${jobId}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="card-title">
                                ${job.dataset_name || job.name || 'Unnamed Dataset'}
                                ${statusBadge}
                            </h6>
                            <p class="card-text text-muted mb-2">
                                <small>
                                    <i class="fas fa-tag"></i> ${job.job_type || 'upload'} 
                                    ${datasetUuid ? `| <i class="fas fa-database"></i> ${datasetUuid.substring(0, 8)}...` : ''}
                                </small>
                            </p>
                            ${progressBar}
                            ${timeInfo}
                            ${job.error ? `
                                <div class="alert alert-danger alert-sm mt-2 mb-0">
                                    <i class="fas fa-exclamation-triangle"></i> 
                                    <strong>Error:</strong> ${job.error}
                                </div>
                            ` : ''}
                            ${showLogs ? `
                                <div class="mt-3">
                                    <button class="btn btn-sm btn-outline-info" type="button" data-bs-toggle="collapse" data-bs-target="#${logId}" aria-expanded="false" aria-controls="${logId}">
                                        <i class="fas fa-file-alt"></i> View Conversion Logs
                                    </button>
                                    <div class="collapse mt-2" id="${logId}">
                                        <div class="card card-body bg-dark text-light" style="max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 0.85rem;">
                                            <div class="conversion-logs" data-dataset-uuid="${datasetUuid}">
                                                <div class="text-center py-2">
                                                    <div class="spinner-border spinner-border-sm text-light" role="status">
                                                        <span class="visually-hidden">Loading logs...</span>
                                                    </div>
                                                    <p class="mt-2 mb-0">Loading conversion logs...</p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                        <div class="ms-3">
                            ${job.status === 'processing' || job.status === 'queued' || job.status === 'converting' ? `
                                <button class="btn btn-sm btn-outline-danger" onclick="window.jobManager.cancelJob('${jobId}')" title="Cancel Job">
                                    <i class="fas fa-times"></i>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get status badge HTML
     */
    getStatusBadge(status) {
        const badges = {
            'queued': '<span class="badge bg-secondary">Queued</span>',
            'processing': '<span class="badge bg-info">Processing</span>',
            'converting': '<span class="badge bg-info">Converting</span>',
            'conversion queued': '<span class="badge bg-secondary">Conversion Queued</span>',
            'completed': '<span class="badge bg-success">Completed</span>',
            'done': '<span class="badge bg-success">Done</span>',
            'failed': '<span class="badge bg-danger">Failed</span>',
            'conversion failed': '<span class="badge bg-danger">Conversion Failed</span>',
            'error': '<span class="badge bg-danger">Error</span>',
            'cancelled': '<span class="badge bg-secondary">Cancelled</span>'
        };
        return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
    }

    /**
     * Get progress bar HTML
     */
    getProgressBar(job) {
        const progress = job.progress_percentage || job.progress || 0;
        // Show progress for processing, converting, or queued jobs
        if (job.status === 'processing' || job.status === 'queued' || job.status === 'converting' || job.status === 'conversion queued') {
            // For converting status, show indeterminate progress if no specific progress
            const isIndeterminate = (job.status === 'converting' || job.status === 'conversion queued') && progress === 0;
            return `
                <div class="progress mt-2" style="height: 20px;">
                    <div class="progress-bar progress-bar-striped ${isIndeterminate ? 'progress-bar-animated' : ''}" 
                         role="progressbar" 
                         style="width: ${isIndeterminate ? '100' : progress}%"
                         aria-valuenow="${progress}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${isIndeterminate ? 'Converting...' : `${progress}%`}
                    </div>
                </div>
            `;
        }
        return '';
    }

    /**
     * Get time information HTML
     */
    getTimeInfo(job) {
        const times = [];
        if (job.created_at) {
            const created = new Date(job.created_at);
            times.push(`<i class="fas fa-clock"></i> Created: ${created.toLocaleString()}`);
        }
        if (job.updated_at) {
            const updated = new Date(job.updated_at);
            times.push(`<i class="fas fa-sync"></i> Updated: ${updated.toLocaleString()}`);
        }
        if (job.completed_at) {
            const completed = new Date(job.completed_at);
            times.push(`<i class="fas fa-check-circle"></i> Completed: ${completed.toLocaleString()}`);
        }
        return times.length > 0 ? `<small class="text-muted d-block mt-2">${times.join(' | ')}</small>` : '';
    }

    /**
     * Get status icon
     */
    getStatusIcon(statusId) {
        const icons = {
            'processing': 'spinner fa-spin',
            'completed': 'check-circle',
            'failed': 'exclamation-triangle',
            'cancelled': 'ban'
        };
        return icons[statusId] || 'circle';
    }

    /**
     * Refresh jobs
     */
    async refreshJobs() {
        try {
            const jobs = await this.fetchJobs();
            this.activeJobs = jobs;
            this.renderJobsInterface(jobs);
        } catch (error) {
            console.error('Error refreshing jobs:', error);
            alert('Failed to refresh jobs: ' + error.message);
        }
    }

    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
        this.stopAutoRefresh(); // Clear any existing interval
        this.refreshInterval = setInterval(() => {
            this.refreshJobs();
        }, 10000); // Refresh every 10 seconds
    }

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Setup log viewers - load logs when collapse is expanded
     */
    setupLogViewers() {
        // Find all log collapse elements
        const logCollapses = document.querySelectorAll('.collapse[id^="logs-"]');
        logCollapses.forEach(collapse => {
            // Add event listener for when collapse is shown
            collapse.addEventListener('show.bs.collapse', (e) => {
                const logContainer = collapse.querySelector('.conversion-logs');
                if (logContainer) {
                    const datasetUuid = logContainer.getAttribute('data-dataset-uuid');
                    if (datasetUuid && !logContainer.dataset.loaded) {
                        this.loadConversionLogs(datasetUuid, logContainer);
                        logContainer.dataset.loaded = 'true';
                    }
                }
            });
        });
    }

    /**
     * Load conversion logs for a dataset
     */
    async loadConversionLogs(datasetUuid, container) {
        try {
            // TODO: Implement log loading from API
            // For now, just show a message
            container.innerHTML = `
                <div class="text-center py-2">
                    <p class="text-muted">Log loading not yet implemented</p>
                </div>
            `;
        } catch (error) {
            console.error('Error loading conversion logs:', error);
            container.innerHTML = `
                <div class="text-center py-2">
                    <p class="text-danger">Error loading logs: ${error.message}</p>
                </div>
            `;
        }
    }

    /**
     * Cancel a job
     */
    async cancelJob(jobId) {
        if (!confirm('Are you sure you want to cancel this job?')) {
            return;
        }

        try {
            const response = await fetch(`${getApiBasePath()}/cancel-job.php`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ job_id: jobId })
            });

            const data = await response.json();
            if (data.success) {
                alert('Job cancelled successfully');
                this.refreshJobs();
            } else {
                alert('Error cancelling job: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error cancelling job:', error);
            alert('Failed to cancel job: ' + error.message);
        }
    }
}

// Initialize job manager
let jobManager;
document.addEventListener('DOMContentLoaded', () => {
    jobManager = new JobManager();
    window.jobManager = jobManager; // Make it globally accessible
});

