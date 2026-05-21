<?php
/**
 * Post-logout landing page — does not auto-redirect to Auth0 (unlike login.php).
 */
require_once(__DIR__ . '/includes/session_cookie_params.php');
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}
require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/includes/auth.php');

// If still authenticated, send to portal home (stale session edge case)
if (isAuthenticated()) {
    header('Location: ' . getPostLoginRedirectUrl());
    exit;
}

$loginUrl = rtrim(SC_SERVER_URL, '/') . scPortalPathPrefix() . '/login.php';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Signed out — ScientistCloud</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .card-box {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 1rem;
            padding: 2rem;
            max-width: 420px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="card-box">
        <h1><i class="fas fa-cloud"></i> ScientistCloud</h1>
        <p class="text-muted mt-3">You have been signed out.</p>
        <a href="<?php echo htmlspecialchars($loginUrl); ?>" class="btn btn-primary mt-3">
            Sign in again
        </a>
    </div>
</body>
</html>
