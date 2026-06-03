<?php
/**
 * Shown when email/password sign-up or login requires inbox verification.
 * Stays on the portal (does not bounce back to Auth0) so users know to check email.
 */
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

require_once(__DIR__ . '/config.php');
require_once(__DIR__ . '/includes/auth0_management.php');
require_once(__DIR__ . '/includes/auth.php');

$isLocal = (strpos(SC_SERVER_URL, 'localhost') !== false || strpos(SC_SERVER_URL, '127.0.0.1') !== false);
$loginPath = $isLocal ? '/login.php' : '/portal/login.php';
$signupPath = $isLocal ? '/signup.php' : '/portal/signup.php';
$googleLoginPath = getPortalGoogleLoginUrl();

$flash = null;
$email = '';

if (!empty($_SESSION['pending_verification_email'])) {
    $email = (string) $_SESSION['pending_verification_email'];
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && !isset($_GET['verified'])) {
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
$emailVerified = isset($_GET['verified']) && $_GET['verified'] === '1';
if (!$emailVerified && isset($_GET['email']) && trim((string) $_GET['email']) !== '') {
    $email = trim((string) $_GET['email']);
}
if ($emailVerified && isset($_GET['email']) && $_GET['email'] !== '') {
    $email = trim((string) $_GET['email']);
    scClearPendingEmailVerification();
} elseif (!$emailVerified) {
    scMarkEmailVerificationPending($email !== '' ? $email : null);
}
$signInAfterVerifyUrl = $loginPath . '?verification_retry=1';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $emailVerified ? 'Email verified' : 'Check your email'; ?> — ScientistCloud</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex align-items-center justify-content-center min-vh-100">
    <div class="card shadow-sm" style="max-width: 520px;">
        <div class="card-body p-4">
            <?php if ($emailVerified) { ?>
                <h1 class="h4 mb-3 text-success"><i class="fas fa-check-circle"></i> Email verified</h1>
                <p class="text-muted mb-4">
                    <?php if ($email !== '') { ?>
                        <strong><?php echo htmlspecialchars($email); ?></strong> is verified.
                    <?php } else { ?>
                        Your email is verified.
                    <?php } ?>
                    You can sign in now.
                </p>
                <a class="btn btn-primary w-100" href="<?php echo htmlspecialchars($signInAfterVerifyUrl); ?>">
                    Sign in
                </a>
            <?php } else { ?>
                <h1 class="h4 mb-3"><i class="fas fa-envelope"></i> Check your email to continue</h1>

                <div class="alert alert-info mb-4" role="alert">
                    <strong>We sent a verification link to your inbox.</strong>
                    Open that email from Auth0 and click the link <em>before</em> trying to sign in again.
                    Signing in without verifying will not work.
                </div>

                <?php if ($justSignedUp) { ?>
                    <p class="text-muted">
                        Your account was created with email and password.
                        You must verify your email address before you can use ScientistCloud.
                    </p>
                <?php } else { ?>
                    <p class="text-muted">
                        Email/password accounts require verification. Use the link in your email — not the login button — to activate your account.
                    </p>
                <?php } ?>

                <?php if ($email !== '') { ?>
                    <p class="mb-3">
                        Waiting for verification for
                        <strong><?php echo htmlspecialchars($email); ?></strong>.
                    </p>
                <?php } ?>

                <?php if ($flash) { ?>
                    <div class="alert alert-<?php echo $flash['ok'] ? 'success' : 'warning'; ?>" role="alert">
                        <?php echo htmlspecialchars($flash['message']); ?>
                    </div>
                <?php } ?>

                <ul class="small text-muted mb-4">
                    <li>Check <strong>spam</strong>, junk, and promotions folders.</li>
                    <li>Delivery can take a few minutes.</li>
                    <li>Use the same email address you used to sign up.</li>
                </ul>

                <form method="post" class="mb-4">
                    <label class="form-label" for="email">Did not get the email? Resend verification link</label>
                    <div class="input-group">
                        <input type="email" class="form-control" id="email" name="email" required
                            placeholder="you@example.com" value="<?php echo htmlspecialchars($email); ?>">
                        <button type="submit" class="btn btn-outline-primary">Resend</button>
                    </div>
                </form>

                <div class="d-grid gap-2">
                    <a class="btn btn-primary" href="<?php echo htmlspecialchars($signInAfterVerifyUrl); ?>">
                        I verified my email — sign in
                    </a>
                    <a class="btn btn-outline-secondary" href="<?php echo htmlspecialchars($googleLoginPath); ?>">
                        Sign in with Google instead
                    </a>
                </div>
                <p class="small text-muted mt-3 mb-0 text-center">
                    Wrong email?
                    <a href="<?php echo htmlspecialchars($signupPath); ?>">Create a different account</a>
                </p>
            <?php } ?>
        </div>
    </div>
</body>
</html>
