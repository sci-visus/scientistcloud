/**
 * Team create / manage UI (used standalone and when embedded in portal viewer).
 */
(function (global) {
    'use strict';

    function apiBase() {
        if (global.SC_PORTAL_API_BASE) {
            return String(global.SC_PORTAL_API_BASE).replace(/\/$/, '');
        }
        const isLocal = global.location.hostname === 'localhost' || global.location.hostname === '127.0.0.1';
        return isLocal ? '/api' : '/portal/api';
    }

    function parseEmailList(text) {
        const emails = new Set();
        const raw = String(text || '');
        const re = /[a-zA-Z0-9._%+\'-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
        let match;
        while ((match = re.exec(raw)) !== null) {
            const email = match[0].toLowerCase().trim();
            if (email) {
                emails.add(email);
            }
        }
        return Array.from(emails);
    }

    function reloadTeamPage() {
        if (global.uploadManager && typeof global.uploadManager.showCreateTeamPage === 'function') {
            global.uploadManager.showCreateTeamPage();
            return;
        }
        global.location.reload();
    }

    function apiPost(path, body) {
        return fetch(`${apiBase()}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(body),
        }).then((response) =>
            response.json().then((data) => ({
                ok: response.ok,
                data,
            }))
        );
    }

    function checkCreateFormValidity() {
        const teamName = document.getElementById('team_name');
        const bulk = document.getElementById('team_emails_bulk');
        const btn = document.getElementById('create_team_btn');
        if (!teamName || !bulk || !btn) {
            return;
        }
        const emails = parseEmailList(bulk.value);
        btn.disabled = !(teamName.value.trim() && emails.length > 0);
    }

    function handleCreateTeam(ownerEmail) {
        const teamName = document.getElementById('team_name')?.value.trim() || '';
        const parentTeam = document.getElementById('team_parent')?.value || '';
        const bulk = document.getElementById('team_emails_bulk')?.value || '';
        const emails = parseEmailList(bulk);

        if (!teamName || emails.length === 0) {
            alert('Enter a team name and at least one member email.');
            return;
        }

        const btn = document.getElementById('create_team_btn');
        if (btn) {
            btn.disabled = true;
        }

        apiPost('/create-team.php', {
            team_name: teamName,
            emails,
            parents: parentTeam ? [parentTeam] : [],
            owner_email: ownerEmail || '',
        })
            .then((result) => {
                if (result.ok && result.data.success) {
                    alert(`Team "${teamName}" created successfully (${emails.length} member(s)).`);
                    reloadTeamPage();
                } else {
                    alert(`Error creating team: ${result.data.error || result.data.message || 'Unknown error'}`);
                }
            })
            .catch((err) => {
                console.error(err);
                alert(`Error creating team: ${err.message}`);
            })
            .finally(() => checkCreateFormValidity());
    }

    function confirmDeleteTeam(teamUuid, teamName) {
        const name = teamName || 'this team';
        const msg =
            `Delete team "${name}"?\n\n` +
            'This cannot be undone. All members lose access via this team.';
        if (!global.confirm(msg)) {
            return;
        }
        const typed = global.prompt(`Type the team name exactly to confirm deletion:\n\n${name}`);
        if (typed !== name) {
            alert('Deletion cancelled (team name did not match).');
            return;
        }
        apiPost('/delete-team.php', { team_uuid: teamUuid })
            .then((result) => {
                if (result.ok && result.data.success) {
                    alert('Team deleted successfully.');
                    reloadTeamPage();
                } else {
                    alert(`Error deleting team: ${result.data.error || 'Unknown error'}`);
                }
            })
            .catch((err) => {
                console.error(err);
                alert('Error deleting the team.');
            });
    }

    function removeMember(teamId, memberEmail) {
        if (!global.confirm(`Remove member ${memberEmail}?`)) {
            return;
        }
        apiPost('/remove-member.php', {
            team_uuid: teamId,
            member_email: memberEmail,
        })
            .then((result) => {
                if (result.ok && result.data.success) {
                    reloadTeamPage();
                } else {
                    alert(`Error removing member: ${result.data.error || 'Unknown error'}`);
                }
            })
            .catch((err) => {
                console.error(err);
                alert('Error removing the member.');
            });
    }

    function toggleAddMember(teamId) {
        const el = document.getElementById(`add-member-container-${teamId}`);
        if (!el) return;
        el.style.display = el.style.display === 'none' || el.style.display === '' ? 'block' : 'none';
    }

    function toggleEditTeamName(teamId) {
        const displayElement = document.getElementById(`team-name-display-${teamId}`);
        const editElement = document.getElementById(`team-name-edit-${teamId}`);
        if (!displayElement || !editElement) return;

        if (editElement.style.display === 'none') {
            displayElement.style.display = 'none';
            editElement.style.display = 'inline';
            editElement.focus();
        } else {
            const newName = editElement.value.trim();
            if (!newName) {
                alert('Team name cannot be empty.');
                return;
            }
            apiPost('/update-team-name.php', {
                team_uuid: teamId,
                team_name: newName,
            })
                .then((result) => {
                    if (result.ok && result.data.success) {
                        reloadTeamPage();
                    } else {
                        alert(`Error updating team name: ${result.data.error || 'Unknown error'}`);
                    }
                })
                .catch((err) => {
                    console.error(err);
                    alert('Error updating the team name.');
                });
        }
    }

    function memberAlreadyListed(teamId, email) {
        const container = document.getElementById(`add-member-container-${teamId}`);
        if (!container) return false;
        const teamEl = container.closest('.team');
        if (!teamEl) return false;
        return Array.from(teamEl.querySelectorAll('.member-email')).some(
            (span) => span.textContent.trim().toLowerCase() === email.toLowerCase()
        );
    }

    function appendMemberRow(teamId, email) {
        const container = document.getElementById(`add-member-container-${teamId}`);
        if (!container) return;
        const section = container.closest('.add-member-section');
        if (!section) return;
        const li = document.createElement('li');
        const span = document.createElement('span');
        span.className = 'member-email';
        span.textContent = email;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'remove-btn';
        btn.textContent = 'Remove';
        btn.addEventListener('click', () => removeMember(teamId, email));
        li.appendChild(span);
        li.appendChild(btn);
        section.parentNode.insertBefore(li, section);
    }

    function updateTeam(teamId) {
        const input = document.getElementById(`new-member-${teamId}`);
        const raw = input?.value.trim() || '';
        if (!raw) {
            alert('Paste or type at least one email address.');
            return;
        }
        apiPost('/update-team.php', {
            team_uuid: teamId,
            new_member_email: raw,
        })
            .then((result) => {
                const data = result.data || {};
                if (!result.ok || !data.success) {
                    alert(`Error updating the team: ${data.error || 'Unknown error'}`);
                    return;
                }
                const added = data.added || [];
                let appended = 0;
                added.forEach((email) => {
                    if (!memberAlreadyListed(teamId, email)) {
                        appendMemberRow(teamId, email);
                        appended++;
                    }
                });
                if (input) {
                    input.value = '';
                }
                const parts = [];
                if (appended > 0) {
                    parts.push(`Added ${appended} member(s).`);
                } else if (added.length > 0) {
                    parts.push('Those addresses were already on the team.');
                }
                if (data.invalid && data.invalid.length) {
                    parts.push(`Skipped invalid: ${data.invalid.join(', ')}`);
                }
                if (parts.length) {
                    alert(parts.join(' '));
                }
            })
            .catch((err) => {
                console.error(err);
                alert('Error updating the team.');
            });
    }

    function initTeamManagement(ownerEmail) {
        const form = document.getElementById('team_form');
        if (form) {
            form.addEventListener('submit', (e) => e.preventDefault());
        }
        const createBtn = document.getElementById('create_team_btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => handleCreateTeam(ownerEmail));
        }
        const teamName = document.getElementById('team_name');
        const bulk = document.getElementById('team_emails_bulk');
        if (teamName) teamName.addEventListener('input', checkCreateFormValidity);
        if (bulk) bulk.addEventListener('input', checkCreateFormValidity);

        document.querySelectorAll('.delete-team-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                confirmDeleteTeam(btn.dataset.teamUuid, btn.dataset.teamName);
            });
        });

        document.querySelectorAll('.sc-team-add-member-btn').forEach((btn) => {
            btn.addEventListener('click', () => toggleAddMember(btn.dataset.teamUuid));
        });

        document.querySelectorAll('.sc-team-edit-name-btn').forEach((btn) => {
            btn.addEventListener('click', () => toggleEditTeamName(btn.dataset.teamUuid));
        });

        document.querySelectorAll('.sc-team-update-members-btn').forEach((btn) => {
            btn.addEventListener('click', () => updateTeam(btn.dataset.teamUuid));
        });

        document.querySelectorAll('.sc-team-remove-member-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                removeMember(btn.dataset.teamUuid, btn.dataset.memberEmail);
            });
        });

        checkCreateFormValidity();
    }

    global.scParseEmailList = parseEmailList;
    global.scInitTeamManagement = initTeamManagement;
    global.scConfirmDeleteTeam = confirmDeleteTeam;
})(typeof window !== 'undefined' ? window : globalThis);
