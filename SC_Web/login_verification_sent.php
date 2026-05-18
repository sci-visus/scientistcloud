<?php
/**
 * Shown after Auth0 database signup when email verification is required.
 * Point Auth0 "Redirect To" here (not legacy IP login_error.php).
 */
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/includes/auth0_management.php');

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$loginPath = $isLocal ? '/login.php' : '/portal/login.php';
$signupPath = $isLocal ? '/signup.php' : '/portal/signup.php';

$flash = null;
$email = '';

if (!empty($_SESSION['pending_verification_email'])) {
    $email = (string) $_SESSION['pending_verification_email'];
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim((string) ($_POST['email'] ?? $email));
    if ($email !== '' && filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $flash = auth0_resend_verification_email($email);
        if ($flash['ok']) {
            $_SESSION['pending_verification_email'] = $email;
        }
    } else {
        $flash = ['ok' => false, 'message' => 'Enter a valid email address.'];
    }
}

$justSignedUp = isset($_GET['pending']) || isset($_GET['signup']);
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
    <div class="card shadow-sm" style="max-width: 480px;">
        <div class="card-body p-4">
            <h1 class="h4 mb-3">Verify your email to continue</h1>
            <?php if ($justSignedUp) { ?>
                <p class="text-muted">
                    Your account was created. We sent a verification link to your inbox.
                    You must click that link before you can sign in with email and password.
                </p>
            <?php } else { ?>
                <p class="text-muted">
                    Email/password accounts require verification. Check your inbox for the link from Auth0.
                </p>
            <?php } ?>

            <?php if ($flash) { ?>
                <div class="alert alert-<?php echo $flash['ok'] ? 'success' : 'warning'; ?>" role="alert">
                    <?php echo htmlspecialchars($flash['message']); ?>
                </div>
            <?php } ?>

            <ul class="small text-muted mb-4">
                <li>Check <strong>spam</strong> and promotions folders.</li>
                <li>Wait a few minutes — delivery can be delayed.</li>
                <li>Use the same email you used to sign up.</li>
            </ul>

            <form method="post" class="mb-4">
                <label class="form-label" for="email">Resend verification email</label>
                <div class="input-group">
                    <input
                        type="email"
                        class="form-control"
                        id="email"
                        name="email"
                        required
                        placeholder="you@example.com"
                        value="<?php echo htmlspecialchars($email); ?>"
                    >
                    <button type="submit" class="btn btn-outline-primary">Resend</button>
                </div>
            </form>

            <div class="d-flex flex-wrap gap-2">
                <a class="btn btn-primary" href="<?php echo htmlspecialchars($loginPath); ?>">Go to login</a>
                <a class="btn btn-link" href="<?php echo htmlspecialchars($signupPath); ?>">Sign up again</a>
            </div>
        </div>
    </div>
</body>
</html>
