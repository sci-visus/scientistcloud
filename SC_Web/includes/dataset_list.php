<?php
/**
 * Dataset List Module for ScientistCloud Data Portal
 * Displays user's datasets in a tree structure
 */

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/auth.php');
require_once(__DIR__ . '/dataset_manager.php');
require_once(__DIR__ . '/sclib_client.php');

// Get current user
$user = getCurrentUser();
if (!$user) {
    echo '<p>Please log in to view your datasets.</p>';
    exit;
}

// Get user's datasets
$datasets = getUserDatasets($user['id']);
$folders = getDatasetFolders($user['id']);

// Group datasets by folder (similar to list_conversions_treeview_fromJSON.php)
$groupedDatasets = [];
$rootDatasets = [];
foreach ($datasets as $dataset) {
    $folderUuid = $dataset['folder_uuid'] ?? null;
    if (empty($folderUuid) || $folderUuid === 'No_Folder_Selected' || $folderUuid === 'root') {
        $rootDatasets[] = $dataset;
    } else {
        if (!isset($groupedDatasets[$folderUuid])) {
            $groupedDatasets[$folderUuid] = [];
        }
        $groupedDatasets[$folderUuid][] = $dataset;
    }
}

// Function to get file format icon
function getFileFormatIcon($sensor) {
    $icons = [
        'TIFF' => 'fas fa-image',
        'TIFF_RGB' => 'fas fa-image',
        'NETCDF' => 'fas fa-database',
        'HDF5' => 'fas fa-database',
        '4D_NEXUS' => 'fas fa-cube',
        'RGB DRONE' => 'fas fa-drone',
        'MapIR DRONE' => 'fas fa-drone'
    ];
    
    return $icons[$sensor] ?? 'fas fa-file';
}

// Function to get status color
function getStatusColor($status) {
    $colors = [
        'done' => 'success',
        'Ready' => 'success',
        'processing' => 'warning',
        'error' => 'danger',
        'pending' => 'info'
    ];
    
    return $colors[$status] ?? 'secondary';
}

// Function to format file size
function formatFileSize($bytes) {
    if ($bytes == 0) return '0 B';
    
    $units = ['B', 'KB', 'MB', 'GB', 'TB'];
    $bytes = max($bytes, 0);
    $pow = floor(($bytes ? log($bytes) : 0) / log(1024));
    $pow = min($pow, count($units) - 1);
    
    $bytes /= pow(1024, $pow);
    
    return round($bytes, 2) . ' ' . $units[$pow];
}
?>

<!-- Dataset List Container - JavaScript will replace this content -->
<div class="dataset-list">
<!-- My Datasets -->
<div class="dataset-section">
    <a class="nav-link" data-bs-toggle="collapse" data-bs-target="#myDatasets">
        <span class="arrow-icon" id="arrow-my">&#9656;</span>My Datasets
    </a>
    <div class="collapse ps-4 w-100" id="myDatasets">
        <?php if (empty($datasets)): ?>
            <p class="text-muted">No datasets found. Upload your first dataset to get started.</p>
        <?php else: ?>
            <!-- Root level datasets (no folder) -->
            <?php foreach ($rootDatasets as $dataset): ?>
                <div class="dataset-item" data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>">
                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                       data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>"
                       data-dataset-name="<?php echo htmlspecialchars($dataset['name']); ?>"
                       data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid']); ?>"
                       data-dataset-server="<?php echo $dataset['google_drive_link'] ? 'true' : 'false'; ?>">
                        <i class="<?php echo getFileFormatIcon($dataset['sensor']); ?> me-2"></i>
                        <span class="dataset-name"><?php echo htmlspecialchars($dataset['name']); ?></span>
                        <span class="badge bg-<?php echo getStatusColor($dataset['status']); ?> ms-2">
                            <?php echo htmlspecialchars($dataset['status']); ?>
                        </span>
                    </a>
                </div>
            <?php endforeach; ?>
            
            <!-- Folder datasets (grouped by folder_uuid) -->
            <?php foreach ($groupedDatasets as $folderUuid => $folderDatasets): ?>
                <div class="folder-group">
                    <details class="folder-details" open>
                        <summary class="folder-summary">
                            <span class="arrow-icon">&#9656;</span>
                            <span class="folder-name"><?php echo htmlspecialchars($folderUuid); ?></span>
                            <span class="badge bg-secondary ms-2"><?php echo count($folderDatasets); ?></span>
                        </summary>
                        <ul class="nested folder-datasets">
                            <?php foreach ($folderDatasets as $dataset): ?>
                                <li class="dataset-item" data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>">
                                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                                       data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>"
                                       data-dataset-name="<?php echo htmlspecialchars($dataset['name']); ?>"
                                       data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid']); ?>"
                                       data-dataset-server="<?php echo $dataset['google_drive_link'] ? 'true' : 'false'; ?>">
                                        <i class="<?php echo getFileFormatIcon($dataset['sensor']); ?> me-2"></i>
                                        <span class="dataset-name"><?php echo htmlspecialchars($dataset['name']); ?></span>
                                        <span class="badge bg-<?php echo getStatusColor($dataset['status']); ?> ms-2">
                                            <?php echo htmlspecialchars($dataset['status']); ?>
                                        </span>
                                    </a>
                                </li>
                            <?php endforeach; ?>
                        </ul>
                    </details>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>
    </div>
</div>

<!-- Shared Datasets -->
<div class="dataset-section">
    <a class="nav-link" data-bs-toggle="collapse" data-bs-target="#sharedDatasets">
        <span class="arrow-icon" id="arrow-shared">&#9656;</span>Shared with Me
    </a>
    <div class="collapse ps-4 w-100" id="sharedDatasets">
        <?php
        // Get shared datasets via SCLib API
        $sharedDatasets = [];
        try {
            $sclib = getSCLibClient();
            $allDatasets = $sclib->getUserDatasets($user['id']);
            
            // Filter for shared datasets
            foreach ($allDatasets as $dataset) {
                if (in_array($user['id'], $dataset['shared_with'] ?? [])) {
                    $sharedDatasets[] = $dataset;
                }
            }
            
            $sharedDatasets = array_map('formatDataset', $sharedDatasets);
        } catch (Exception $e) {
            logMessage('ERROR', 'Failed to get shared datasets', ['error' => $e->getMessage()]);
        }
        
        // Group shared datasets by folder
        $sharedGroupedDatasets = [];
        $sharedRootDatasets = [];
        foreach ($sharedDatasets as $dataset) {
            $folderUuid = $dataset['folder_uuid'] ?? null;
            if (empty($folderUuid) || $folderUuid === 'No_Folder_Selected' || $folderUuid === 'root') {
                $sharedRootDatasets[] = $dataset;
            } else {
                if (!isset($sharedGroupedDatasets[$folderUuid])) {
                    $sharedGroupedDatasets[$folderUuid] = [];
                }
                $sharedGroupedDatasets[$folderUuid][] = $dataset;
            }
        }
        ?>
        
        <?php if (empty($sharedDatasets)): ?>
            <p class="text-muted">No shared datasets found.</p>
        <?php else: ?>
            <!-- Root level shared datasets -->
            <?php foreach ($sharedRootDatasets as $dataset): ?>
                <div class="dataset-item" data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>">
                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                       data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>"
                       data-dataset-name="<?php echo htmlspecialchars($dataset['name']); ?>"
                       data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid']); ?>"
                       data-dataset-server="<?php echo $dataset['google_drive_link'] ? 'true' : 'false'; ?>">
                        <i class="<?php echo getFileFormatIcon($dataset['sensor']); ?> me-2"></i>
                        <span class="dataset-name"><?php echo htmlspecialchars($dataset['name']); ?></span>
                        <span class="badge bg-info ms-2">Shared</span>
                    </a>
                </div>
            <?php endforeach; ?>
            
            <!-- Folder grouped shared datasets -->
            <?php foreach ($sharedGroupedDatasets as $folderUuid => $folderDatasets): ?>
                <div class="folder-group">
                    <details class="folder-details" open>
                        <summary class="folder-summary">
                            <span class="arrow-icon">&#9656;</span>
                            <span class="folder-name"><?php echo htmlspecialchars($folderUuid); ?></span>
                            <span class="badge bg-secondary ms-2"><?php echo count($folderDatasets); ?></span>
                        </summary>
                        <ul class="nested folder-datasets">
                            <?php foreach ($folderDatasets as $dataset): ?>
                                <li class="dataset-item" data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>">
                                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                                       data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>"
                                       data-dataset-name="<?php echo htmlspecialchars($dataset['name']); ?>"
                                       data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid']); ?>"
                                       data-dataset-server="<?php echo $dataset['google_drive_link'] ? 'true' : 'false'; ?>">
                                        <i class="<?php echo getFileFormatIcon($dataset['sensor']); ?> me-2"></i>
                                        <span class="dataset-name"><?php echo htmlspecialchars($dataset['name']); ?></span>
                                        <span class="badge bg-info ms-2">Shared</span>
                                    </a>
                                </li>
                            <?php endforeach; ?>
                        </ul>
                    </details>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>
    </div>
</div>

<!-- Team Datasets -->
<?php if ($user['team_id']): ?>
<div class="dataset-section">
    <a class="nav-link" data-bs-toggle="collapse" data-bs-target="#teamDatasets">
        <span class="arrow-icon" id="arrow-team">&#9656;</span>Team Datasets
    </a>
    <div class="collapse ps-4 w-100" id="teamDatasets">
        <?php
        // Get team datasets via SCLib API
        $teamDatasets = [];
        try {
            $sclib = getSCLibClient();
            $allDatasets = $sclib->getUserDatasets($user['id']);
            
            // Filter for team datasets
            foreach ($allDatasets as $dataset) {
                if ($dataset['team_id'] === $user['team_id']) {
                    $teamDatasets[] = $dataset;
                }
            }
            
            $teamDatasets = array_map('formatDataset', $teamDatasets);
        } catch (Exception $e) {
            logMessage('ERROR', 'Failed to get team datasets', ['error' => $e->getMessage()]);
        }
        ?>
        
        <?php
        // Group team datasets by folder
        $teamGroupedDatasets = [];
        $teamRootDatasets = [];
        foreach ($teamDatasets as $dataset) {
            $folderUuid = $dataset['folder_uuid'] ?? null;
            if (empty($folderUuid) || $folderUuid === 'No_Folder_Selected' || $folderUuid === 'root') {
                $teamRootDatasets[] = $dataset;
            } else {
                if (!isset($teamGroupedDatasets[$folderUuid])) {
                    $teamGroupedDatasets[$folderUuid] = [];
                }
                $teamGroupedDatasets[$folderUuid][] = $dataset;
            }
        }
        ?>
        
        <?php if (empty($teamDatasets)): ?>
            <p class="text-muted">No team datasets found.</p>
        <?php else: ?>
            <!-- Root level team datasets -->
            <?php foreach ($teamRootDatasets as $dataset): ?>
                <div class="dataset-item" data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>">
                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                       data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>"
                       data-dataset-name="<?php echo htmlspecialchars($dataset['name']); ?>"
                       data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid']); ?>"
                       data-dataset-server="<?php echo $dataset['google_drive_link'] ? 'true' : 'false'; ?>">
                        <i class="<?php echo getFileFormatIcon($dataset['sensor']); ?> me-2"></i>
                        <span class="dataset-name"><?php echo htmlspecialchars($dataset['name']); ?></span>
                        <span class="badge bg-primary ms-2">Team</span>
                    </a>
                </div>
            <?php endforeach; ?>
            
            <!-- Folder grouped team datasets -->
            <?php foreach ($teamGroupedDatasets as $folderUuid => $folderDatasets): ?>
                <div class="folder-group">
                    <details class="folder-details" open>
                        <summary class="folder-summary">
                            <span class="arrow-icon">&#9656;</span>
                            <span class="folder-name"><?php echo htmlspecialchars($folderUuid); ?></span>
                            <span class="badge bg-secondary ms-2"><?php echo count($folderDatasets); ?></span>
                        </summary>
                        <ul class="nested folder-datasets">
                            <?php foreach ($folderDatasets as $dataset): ?>
                                <li class="dataset-item" data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>">
                                    <a class="nav-link dataset-link" href="javascript:void(0)" 
                                       data-dataset-id="<?php echo htmlspecialchars($dataset['id']); ?>"
                                       data-dataset-name="<?php echo htmlspecialchars($dataset['name']); ?>"
                                       data-dataset-uuid="<?php echo htmlspecialchars($dataset['uuid']); ?>"
                                       data-dataset-server="<?php echo $dataset['google_drive_link'] ? 'true' : 'false'; ?>">
                                        <i class="<?php echo getFileFormatIcon($dataset['sensor']); ?> me-2"></i>
                                        <span class="dataset-name"><?php echo htmlspecialchars($dataset['name']); ?></span>
                                        <span class="badge bg-primary ms-2">Team</span>
                                    </a>
                                </li>
                            <?php endforeach; ?>
                        </ul>
                    </details>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>
    </div>
</div>
<?php endif; ?>
</div>
<!-- End Dataset List Container -->

<style>
.dataset-section {
    margin-bottom: 1rem;
}

.dataset-item {
    margin-bottom: 0.25rem;
}

.dataset-link {
    display: flex;
    align-items: center;
    padding: 0.5rem;
    border-radius: 0.25rem;
    transition: background-color 0.2s;
}

.dataset-link:hover {
    background-color: rgba(255, 255, 255, 0.1);
}

.dataset-name {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.badge {
    font-size: 0.75rem;
}

.folder-group {
    margin-bottom: 0.5rem;
}

.folder-details {
    margin-bottom: 0.5rem;
}

.folder-summary {
    display: flex;
    align-items: center;
    padding: 0.5rem;
    cursor: pointer;
    list-style: none;
    user-select: none;
    border-radius: 0.25rem;
    transition: background-color 0.2s;
}

.folder-summary:hover {
    background-color: rgba(255, 255, 255, 0.1);
}

.folder-summary::-webkit-details-marker {
    display: none;
}

.folder-summary .arrow-icon {
    display: inline-block;
    transition: transform 0.2s;
    width: 1em;
    text-align: center;
    margin-right: 0.5rem;
}

.folder-details[open] .folder-summary .arrow-icon {
    transform: rotate(90deg);
}

.folder-name {
    flex: 1;
    font-weight: 500;
}

.nested.folder-datasets {
    list-style: none;
    padding-left: 1.5rem;
    margin-top: 0.25rem;
}

.nested.folder-datasets li {
    margin-bottom: 0.25rem;
}

.arrow-icon {
    display: inline-block;
    transition: transform 0.2s;
    width: 1em;
    text-align: center;
    margin-right: 0.5rem;
}

.arrow-icon.open {
    transform: rotate(90deg);
}
</style>

<script>
// Handle dataset selection
document.addEventListener('DOMContentLoaded', function() {
    // Handle dataset clicks
    document.querySelectorAll('.dataset-link').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const datasetId = this.dataset.datasetId;
            const datasetName = this.dataset.datasetName;
            const datasetUuid = this.dataset.datasetUuid;
            const datasetServer = this.dataset.datasetServer;
            
            // Update active state
            document.querySelectorAll('.dataset-link').forEach(function(l) {
                l.classList.remove('active');
            });
            this.classList.add('active');
            
            // Load dataset details
            loadDatasetDetails(datasetId);
            
            // Load dashboard
            loadDashboard(datasetId, datasetName, datasetUuid, datasetServer);
        });
    });
    
    // Handle folder collapse/expand
    document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(function(trigger) {
        trigger.addEventListener('click', function() {
            const target = document.querySelector(this.dataset.bsTarget);
            const arrow = document.querySelector('#arrow-' + this.dataset.bsTarget.replace('#', ''));
            
            if (target) {
                target.addEventListener('show.bs.collapse', function() {
                    if (arrow) arrow.classList.add('open');
                });
                target.addEventListener('hide.bs.collapse', function() {
                    if (arrow) arrow.classList.remove('open');
                });
            }
        });
    });
});
</script>
