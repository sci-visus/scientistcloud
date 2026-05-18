<?php
/**
 * Shown after Auth0 database signup when email verification is required.
 * Point Auth0 "Redirect To" / verification links here (not the legacy IP login_error.php).
 */
require_once(__DIR__ . '/config.php');

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$loginPath = $isLocal ? '/login.php' : '/portal/login.php';
$deployServer = rtrim(SC_SERVER_URL, '/');
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify your email — ScientistCloud</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex align-items-center justify-content-center min-vh-100">
    <div class="card shadow-sm" style="max-width: 420px;">
        <div class="card-body text-center p-4">
            <h1 class="h4 mb-3">Check your email</h1>
            <p class="text-muted mb-4">
                We sent a verification link. Open it, then sign in with your email and password.
            </p>
            <a class="btn btn-primary" href="<?php echo htmlspecialchars($loginPath); ?>">Continue to login</a>
        </div>
    </div>
</body>
</html>
