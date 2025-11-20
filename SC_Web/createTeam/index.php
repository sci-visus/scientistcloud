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
    <link href="../assets/css/main.css" rel="stylesheet">
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
<div class="container">
    <div class="panel panel-default">
        <div class="panel-heading">
            <h4 class="panel-title pull-left">
                Create a Team/Group
            </h4>
        </div>
        <div class="panel-body">
            <form class="form-horizontal" id="team_form">
                <div class="form-group">
                    <label for="team_name" class="team-name-label">Team Name:</label>
                    <input type="text" class="team-name-input-text" id="team_name" name="team_name" required/>
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
                <div class="form-group email-entries">
                    <div class="email-entry" id="email-entry-1">
                        <label for="email-1" class="email-label">Email Address 1:</label>
                        <input type="email" class="email-input-text" id="email-1" name="email[]" required/>
                    </div>
                </div>
                <div class="add-email-btn-container">
                    <button type="button" class="btn btn-secondary" onclick="addEmailEntry()">Add Another Email</button>
                </div>
                <div class="panel-footer">
                    <button id="create_team_btn" type="submit" class="btn btn-primary" disabled>
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
                                <button onclick="toggleEditTeamName('<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>')" class="edit-btn">
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
                                        <button onclick="removeMember('<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>', '<?php echo htmlspecialchars($email); ?>')" class="remove-btn">Remove</button>
                                    </li>
                                <?php endforeach; ?>
                                <div class="add-member-section">
                                    <button onclick="toggleAddMember('<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>')" class="add-member-btn">
                                        <i class="fas fa-plus"></i>
                                    </button>
                                    <div id="add-member-container-<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>" class="add-member-container" style="display:none;">
                                        <input type="email" id="new-member-<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>" placeholder="Add new member">
                                        <button onclick="updateTeam('<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>')" class="add-btn">Add</button>
                                    </div>
                                </div>
                            </ul>
                            <button onclick="deleteTeam('<?php echo htmlspecialchars($team['uuid'] ?? ''); ?>')" class="delete-team-btn">Delete Team</button>
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
    let emailEntryIndex = 1;

    function addEmailEntry() {
        emailEntryIndex++;
        var newEntry = '<div class="email-entry" id="email-entry-' + emailEntryIndex + '">' +
            '<label for="email-' + emailEntryIndex + '" class="email-label">Email Address ' + emailEntryIndex + ':</label>' +
            '<input type="email" class="email-input-text" id="email-' + emailEntryIndex + '" name="email[]" />' +
            '</div>';
        document.querySelector('.email-entries').insertAdjacentHTML('beforeend', newEntry);
        updateDeleteIcons();
        checkFormValidity();
    }

    function removeEmailEntry(index) {
        var entry = document.getElementById('email-entry-' + index);
        if (entry && entry.parentNode) {
            entry.parentNode.removeChild(entry);
            emailEntryIndex--;
            updateDeleteIcons();
            checkFormValidity();
        }
    }

    function updateDeleteIcons() {
        var entries = document.querySelectorAll('.email-entry');
        entries.forEach((entry, index) => {
            var label = entry.querySelector('.email-label');
            label.textContent = 'Email Address ' + (index + 1) + ':';
            var existingIcon = entry.querySelector('.delete-icon');
            if (existingIcon) {
                existingIcon.remove();
            }
            if (entries.length > 1) {
                var deleteIcon = document.createElement('span');
                deleteIcon.innerHTML = '<i class="fas fa-trash"></i>';
                deleteIcon.className = 'delete-icon';
                deleteIcon.onclick = function() { removeEmailEntry(index + 1); };
                entry.appendChild(deleteIcon);
            }
        });
    }

    function deleteTeam(teamId) {
        if (confirm("Are you sure you want to delete this team?")) {
            fetch('../api/delete-team.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ team_uuid: teamId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert("Team deleted successfully.");
                    location.reload();
                } else {
                    alert("Error deleting the team: " + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert("Error deleting the team.");
            });
        }
    }

    function removeMember(teamId, memberEmail) {
        if (confirm("Are you sure you want to remove this member?")) {
            fetch('../api/remove-member.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    team_uuid: teamId,
                    member_email: memberEmail
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert("Member removed successfully.");
                    location.reload();
                } else {
                    alert("Error removing the member: " + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert("Error removing the member.");
            });
        }
    }

    function toggleAddMember(teamId) {
        var addMemberContainer = document.getElementById('add-member-container-' + teamId);
        if (addMemberContainer.style.display === 'none' || addMemberContainer.style.display === '') {
            addMemberContainer.style.display = 'block';
        } else {
            addMemberContainer.style.display = 'none';
        }
    }

    function toggleEditTeamName(teamId) {
        var displayElement = document.getElementById('team-name-display-' + teamId);
        var editElement = document.getElementById('team-name-edit-' + teamId);

        if (editElement.style.display === 'none') {
            displayElement.style.display = 'none';
            editElement.style.display = 'inline';
            editElement.focus();
        } else {
            var newName = editElement.value.trim();
            if (newName === '') {
                alert("Team name cannot be empty.");
                return;
            }
            displayElement.textContent = newName;
            displayElement.style.display = 'inline';
            editElement.style.display = 'none';
            updateTeamName(teamId, newName);
        }
    }

    function updateTeamName(teamId, newName) {
        if (newName.trim() === '') {
            alert("Team name cannot be empty.");
            return;
        }

        fetch('../api/update-team-name.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                team_uuid: teamId,
                team_name: newName
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Team name updated successfully.");
                location.reload();
            } else {
                alert("Error updating the team name: " + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("Error updating the team name.");
        });
    }

    function updateTeam(teamId) {
        var newMemberEmail = document.getElementById('new-member-' + teamId).value.trim();

        if (newMemberEmail === '') {
            alert("Please enter an email address.");
            return;
        }

        fetch('../api/update-team.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                team_uuid: teamId,
                new_member_email: newMemberEmail
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Team updated successfully.");
                location.reload();
            } else {
                alert("Error updating the team: " + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("Error updating the team.");
        });
    }

    function checkFormValidity() {
        var teamName = document.getElementById('team_name').value.trim();
        var emailInputs = document.querySelectorAll('.email-input-text');
        var validEmails = Array.from(emailInputs).filter(input => input.value.trim() !== '').length;

        var createButton = document.getElementById('create_team_btn');
        if (teamName !== '' && validEmails > 0) {
            createButton.disabled = false;
        } else {
            createButton.disabled = true;
        }
    }

    // Handle form submission
    document.getElementById('team_form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var teamName = document.getElementById('team_name').value.trim();
        var parentTeam = document.getElementById('team_parent').value;
        var emailInputs = document.querySelectorAll('.email-input-text');
        var emails = Array.from(emailInputs)
            .map(input => input.value.trim())
            .filter(email => email !== '');
        
        if (teamName === '' || emails.length === 0) {
            alert('Please fill in all required fields.');
            return;
        }

        var parents = parentTeam ? [parentTeam] : [];

        fetch('../api/create-team.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                team_name: teamName,
                emails: emails,
                parents: parents,
                owner_email: '<?php echo htmlspecialchars($user['email'] ?? ''); ?>'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Team created successfully!');
                location.reload();
            } else {
                alert('Error creating team: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error creating team: ' + error.message);
        });
    });

    document.getElementById('team_name').addEventListener('input', checkFormValidity);
    document.querySelector('.email-entries').addEventListener('input', checkFormValidity);

    updateDeleteIcons();
    checkFormValidity();
</script>

</body>
</html>

