<?php
/**
 * Create Team Page
 * Allows users to create teams and manage existing teams
 */

require_once(__DIR__ . '/../config.php');
require_once(__DIR__ . '/../includes/auth.php');
require_once(__DIR__ . '/../includes/sclib_client.php');

// Start session if not already started
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

// Get user information
$user = getCurrentUser();
if (!$user) {
    // Redirect to login if not authenticated
    $isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
    $loginPath = $isLocal ? '/login.php' : '/portal/login.php';
    header('Location: ' . $loginPath);
    exit;
}

// Get user's teams
$myTeams = [];
$otherTeams = [];
try {
    $sharingClient = getSCLibSharingClient();
    if ($sharingClient) {
        $teamsResult = $sharingClient->getUserTeams($user['email']);
        if (isset($teamsResult['teams']) && is_array($teamsResult['teams'])) {
            foreach ($teamsResult['teams'] as $team) {
                if (isset($team['is_owner']) && $team['is_owner']) {
                    $myTeams[] = $team;
                } else {
                    $otherTeams[] = $team;
                }
            }
        }
    }
} catch (Exception $e) {
    error_log("Error fetching teams: " . $e->getMessage());
}

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$portalApiBase = $isLocal ? '/api' : '/portal/api';
$portalAssetsBase = $isLocal ? '/assets' : '/portal/assets';
$ownerEmailJs = json_encode($user['email'] ?? '');
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=2">
    <title>Create Team - ScientistCloud Data Portal</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- FontAwesome Icons -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <!-- Custom CSS -->
    <link href="<?php echo htmlspecialchars($portalAssetsBase); ?>/css/main.css" rel="stylesheet">
    <style>
        body {
            background-color: var(--bg-color);
            color: var(--fg-color);
            padding: 20px;
        }

        .panel {
            background-color: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
            margin-top: 5px;
        }

        .panel-heading {
            background-color: var(--primary-color);
            color: white;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 10px 15px;
            height: 40px;
        }

        .panel-title {
            font-size: 1.2em;
            margin: 0;
        }

        .panel-body {
            padding: 20px;
        }

        .panel-footer {
            background-color: var(--panel-bg);
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
            padding: 15px;
            text-align: right;
        }

        .form-horizontal .form-group {
            margin-left: 0;
            margin-right: 0;
        }

        .team-name-label, .email-label, .team-parent-label {
            margin-bottom: 10px;
            font-weight: bold;
        }

        .team-name-input, .email-input {
            margin-bottom: 20px;
        }

        .team-name-input-text, .email-input-text, .team-parent-select {
            width: 100%;
            padding: 8px;
            border: 1px solid var(--panel-border);
            border-radius: 4px;
            background-color: var(--bg-color);
            color: var(--fg-color);
        }

        .add-email-btn-container, .add-parent-team-btn-container {
            margin-top: 10px;
            margin-bottom: 10px;
        }

        .btn-secondary {
            background-color: #6c757d;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .btn-secondary:hover {
            background-color: #5a6268;
        }

        .btn-primary {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .btn-primary:hover {
            background-color: #0056b3;
        }

        .delete-icon {
            cursor: pointer;
            color: var(--primary-color);
            margin-left: 10px;
        }

        .teams {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }

        .team {
            background-color: var(--panel-bg);
            border: 1px solid var(--panel-border);
            padding: 15px;
            border-radius: 8px;
        }

        .team-info {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }

        .team-name {
            font-size: 1.5em;
            font-weight: bold;
            margin-right: 10px;
        }

        .team-name-edit {
            margin-right: 10px;
            font-size: 1em;
            padding: 5px;
            width: 100%;
            display: inline-block;
            margin-bottom: 10px;
            background-color: var(--bg-color);
            color: var(--fg-color);
            border: 1px solid var(--panel-border);
        }

        .edit-btn, .remove-btn, .add-btn, .delete-team-btn {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
            transition: background-color 0.3s ease;
        }

        .edit-btn:hover, .remove-btn:hover, .add-btn:hover, .delete-team-btn:hover {
            background-color: #0056b3;
        }

        .remove-btn {
            color: var(--fg-color) !important;
            background-color: var(--panel-bg) !important;
            border: 1px solid var(--panel-border) !important;
        }

        .member-list {
            list-style-type: none;
            padding: 0;
        }

        .member-list li {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }

        .add-member-btn {
            background: none;
            border: none;
            cursor: pointer;
            color: var(--primary-color);
            font-size: 1.5em;
            margin-right: 10px;
        }

        .add-member-container {
            display: flex;
            align-items: center;
            margin-top: 10px;
        }

        .add-member-container input {
            margin-right: 10px;
            padding: 8px;
            border: 1px solid var(--panel-border);
            border-radius: 4px;
            width: 100%;
            background-color: var(--bg-color);
            color: var(--fg-color);
        }

        .add-btn {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .add-btn:hover {
            background-color: #0056b3;
        }

        .member-email {
            margin-right: auto;
        }

        .delete-team-btn {
            background-color: var(--danger-color);
            color: white;
            margin-top: 10px;
        }

        .delete-team-btn:hover {
            background-color: #c82333;
        }

        .team-list-container {
            margin-top: 30px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
    </style>
</head>
<body>
<script>
    // Apply theme from localStorage on page load
    (function() {
        const theme = localStorage.getItem('theme') || 'dark';
        if (theme === 'light') {
            document.body.classList.add('light-theme');
        }
    })();
</script>
<div class="container" data-sc-owner-email="<?php echo htmlspecialchars($user['email'] ?? ''); ?>">
    <div class="panel panel-default">
        <div class="panel-heading">
            <h4 class="panel-title pull-left">
                Create a Team/Group
            </h4>
        </div>
        <div class="panel-body">
            <form class="form-horizontal" id="team_form" action="javascript:void(0)" method="post" onsubmit="return false;">
                <div class="form-group">
                    <label for="team_name" class="team-name-label">Team Name:</label>
                    <input type="text" class="team-name-input-text" id="team_name" name="team_name" autocomplete="organization" required/>
                </div>
                <div class="form-group">
                    <label for="team_parent" class="team-parent-label" id="team_parent_label">Parent Team: (optional)</label>
                    <select name="team_parent" id="team_parent" class="team-parent-select">
                        <option value="">Select Team</option>
                        <?php foreach ($myTeams as $team): ?>
                        <option value="<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>"><?php echo htmlspecialchars($team['team_name'] ?? ''); ?></option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="form-group">
                    <label for="team_emails_bulk" class="email-label">Member emails</label>
                    <textarea class="team-name-input-text" id="team_emails_bulk" name="team_emails_bulk" rows="6"
                        placeholder="Paste one or more addresses. Supports comma/newline lists and formats like Name &lt;email@domain.com&gt;"></textarea>
                    <small class="text-muted">Owner is added automatically. Paste a mailing list or spreadsheet column as-is.</small>
                </div>
                <div class="panel-footer">
                    <button id="create_team_btn" type="button" class="btn btn-primary" disabled>
                        Create Team
                    </button>
                </div>
            </form>
        </div>
    </div>

    <div class="panel panel-default">
        <div class="panel-heading">
            <h4 class="panel-title pull-left">
                My Teams
            </h4>
        </div>
        <div class="panel-body team-list-container">
            <?php if (!empty($myTeams)): ?>
                <div class="teams">
                    <?php foreach ($myTeams as $team): ?>
                        <div class="team">
                            <div class="team-info">
                                <span id="team-name-display-<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>" class="team-name"><?php echo htmlspecialchars($team['team_name'] ?? ''); ?></span>
                                <input type="text" id="team-name-edit-<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>" class="team-name-edit" value="<?php echo htmlspecialchars($team['team_name'] ?? ''); ?>" style="display:none;">
                                <button type="button" class="edit-btn sc-team-edit-name-btn"
                                    data-team-uuid="<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </div>
                            <p>Members:</p>
                            <ul class="member-list">
                                <?php 
                                $teamEmails = $team['emails'] ?? [];
                                foreach ($teamEmails as $email): 
                                ?>
                                    <li>
                                        <span class="member-email"><?php echo htmlspecialchars($email); ?></span>
                                        <button type="button" class="remove-btn sc-team-remove-member-btn"
                                            data-team-uuid="<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>"
                                            data-member-email="<?php echo htmlspecialchars($email); ?>">Remove</button>
                                    </li>
                                <?php endforeach; ?>
                                <div class="add-member-section">
                                    <button type="button" class="add-member-btn sc-team-add-member-btn"
                                        data-team-uuid="<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>">
                                        <i class="fas fa-plus"></i>
                                    </button>
                                    <div id="add-member-container-<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>" class="add-member-container" style="display:none;">
                                        <input type="text" id="new-member-<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>"
                                            placeholder="Paste emails (comma, newline, or Name &lt;email&gt;)" autocomplete="off">
                                        <button type="button" class="add-btn sc-team-update-members-btn"
                                            data-team-uuid="<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>">Add</button>
                                    </div>
                                </div>
                            </ul>
                            <button type="button" class="delete-team-btn"
                                data-team-uuid="<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>"
                                data-team-name="<?php echo htmlspecialchars($team['team_name'] ?? ''); ?>">Delete Team</button>
                        </div>
                    <?php endforeach; ?>
                </div>
            <?php else: ?>
                <p>You are not part of any teams as an owner.</p>
            <?php endif; ?>
        </div>
    </div>

    <div class="panel panel-default">
        <div class="panel-heading">
            <h4 class="panel-title pull-left">
                Other Teams
            </h4>
        </div>
        <div class="panel-body team-list-container">
            <?php if (!empty($otherTeams)): ?>
                <div class="teams">
                    <?php foreach ($otherTeams as $team): ?>
                        <div class="team">
                            <h3 class="team-title">Team Name: <?php echo htmlspecialchars($team['team_name'] ?? ''); ?></h3>
                            <p>Members:</p>
                            <ul class="member-list">
                                <?php 
                                $teamEmails = $team['emails'] ?? [];
                                foreach ($teamEmails as $email): 
                                ?>
                                    <li>
                                        <span class="member-email"><?php echo htmlspecialchars($email); ?></span>
                                    </li>
                                <?php endforeach; ?>
                            </ul>
                        </div>
                    <?php endforeach; ?>
                </div>
            <?php else: ?>
                <p>You are not part of any other teams.</p>
            <?php endif; ?>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    window.SC_PORTAL_API_BASE = <?php echo json_encode($portalApiBase); ?>;
    window.SC_PORTAL_ASSETS_BASE = <?php echo json_encode($portalAssetsBase); ?>;
</script>
<script src="<?php echo htmlspecialchars($portalAssetsBase); ?>/js/team-management.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function () {
        if (typeof scInitTeamManagement === 'function') {
            scInitTeamManagement(<?php echo $ownerEmailJs; ?>);
        }
    });
</script>

</body>
</html>

