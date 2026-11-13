<?php
/**
 * Email portal admins when a ScientistCloud account is created for the first time.
 *
 * Recipients: SC_NEW_ACCOUNT_NOTIFY_EMAIL, otherwise SC_PORTAL_ADMIN_EMAILS.
 * Delivery: SendGrid (SENDGRID_API_KEY), otherwise SMTP (SC_SMTP_*), otherwise PHP mail().
 */

function scNewAccountNotifyRecipients(): array
{
    $raw = getenv('SC_NEW_ACCOUNT_NOTIFY_EMAIL');
    if ($raw === false || trim((string) $raw) === '') {
        $raw = getenv('SC_PORTAL_ADMIN_EMAILS') ?: 'amy@visus.net';
    }
    $recipients = [];
    foreach (explode(',', (string) $raw) as $entry) {
        $email = trim($entry);
        if ($email !== '' && filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $recipients[] = $email;
        }
    }
    return array_values(array_unique($recipients));
}

function scNotifyNewAccount(string $userEmail, string $userName): bool
{
    $userEmail = trim($userEmail);
    $userName = trim(str_replace(["\r", "\n"], ' ', $userName));
    if ($userEmail === '' || !filter_var($userEmail, FILTER_VALIDATE_EMAIL)) {
        return false;
    }

    $recipients = scNewAccountNotifyRecipients();
    if ($recipients === []) {
        error_log('New-account notify skipped: no recipient');
        return false;
    }

    $when = gmdate('Y-m-d H:i:s') . ' UTC';
    $subject = 'New ScientistCloud account: ' . $userEmail;
    $body = "A new account was created on https://scientistcloud.com/portal/\n\n"
        . "Name: {$userName}\n"
        . "Email: {$userEmail}\n"
        . "Time: {$when}\n";

    $from = trim((string) (getenv('SC_NOTIFY_FROM') ?: 'info@visoar.net'));
    if (!filter_var($from, FILTER_VALIDATE_EMAIL)) {
        $from = 'info@visoar.net';
    }

    $sent = false;
    foreach ($recipients as $to) {
        if (scSendNotifyMail($from, $to, $subject, $body)) {
            $sent = true;
        }
    }

    if (function_exists('logMessage')) {
        logMessage($sent ? 'INFO' : 'WARNING', 'New account notification', [
            'user_email' => $userEmail,
            'recipients' => $recipients,
            'sent' => $sent,
        ]);
    }
    return $sent;
}

function scSendNotifyMail(string $from, string $to, string $subject, string $body): bool
{
    $apiKey = trim((string) (getenv('SENDGRID_API_KEY') ?: ''));
    if ($apiKey !== '') {
        return scSendViaSendGrid($apiKey, $from, $to, $subject, $body);
    }

    $smtpHost = trim((string) (getenv('SC_SMTP_HOST') ?: ''));
    if ($smtpHost !== '') {
        $port = (int) (getenv('SC_SMTP_PORT') ?: 587);
        return scSendViaSmtp(
            $smtpHost,
            $port > 0 ? $port : 587,
            trim((string) (getenv('SC_SMTP_USER') ?: '')),
            (string) (getenv('SC_SMTP_PASSWORD') ?: ''),
            $from,
            $to,
            $subject,
            $body
        );
    }

    $headers = "From: ScientistCloud <{$from}>\r\n"
        . "Content-Type: text/plain; charset=UTF-8\r\n";
    $ok = @mail($to, $subject, $body, $headers);
    if (!$ok) {
        error_log('New-account notify: mail() failed and SENDGRID_API_KEY / SC_SMTP_HOST are not set');
    }
    return $ok;
}

function scSendViaSendGrid(string $apiKey, string $from, string $to, string $subject, string $body): bool
{
    $payload = json_encode([
        'personalizations' => [['to' => [['email' => $to]]]],
        'from' => ['email' => $from, 'name' => 'ScientistCloud'],
        'subject' => $subject,
        'content' => [['type' => 'text/plain', 'value' => $body]],
    ]);

    $ch = curl_init('https://api.sendgrid.com/v3/mail/send');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $payload,
        CURLOPT_HTTPHEADER => [
            'Authorization: Bearer ' . $apiKey,
            'Content-Type: application/json',
        ],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 15,
    ]);
    $response = curl_exec($ch);
    $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    curl_close($ch);

    if ($code === 202) {
        return true;
    }
    error_log('SendGrid new-account notify failed HTTP ' . $code . ': ' . substr((string) $response, 0, 300) . ' ' . $err);
    return false;
}

function scSmtpRead($fp, array $okCodes): bool
{
    $data = '';
    while (($line = fgets($fp, 515)) !== false) {
        $data .= $line;
        if (isset($line[3]) && $line[3] === ' ') {
            break;
        }
    }
    $code = (int) substr($data, 0, 3);
    if (!in_array($code, $okCodes, true)) {
        error_log('SMTP new-account notify failed: ' . trim($data));
        return false;
    }
    return true;
}

function scSendViaSmtp(
    string $host,
    int $port,
    string $user,
    string $pass,
    string $from,
    string $to,
    string $subject,
    string $body
): bool {
    $remote = $port === 465 ? "ssl://{$host}:465" : "tcp://{$host}:{$port}";
    $fp = @stream_socket_client($remote, $errno, $errstr, 15, STREAM_CLIENT_CONNECT);
    if (!$fp) {
        error_log("SMTP connect failed: {$errstr} ({$errno})");
        return false;
    }
    stream_set_timeout($fp, 15);

    $fail = function () use ($fp) {
        fclose($fp);
        return false;
    };

    if (!scSmtpRead($fp, [220])) {
        return $fail();
    }
    fwrite($fp, "EHLO scientistcloud.com\r\n");
    if (!scSmtpRead($fp, [250])) {
        return $fail();
    }

    if ($port === 587) {
        fwrite($fp, "STARTTLS\r\n");
        if (!scSmtpRead($fp, [220])) {
            return $fail();
        }
        if (!stream_socket_enable_crypto($fp, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
            error_log('SMTP STARTTLS failed');
            return $fail();
        }
        fwrite($fp, "EHLO scientistcloud.com\r\n");
        if (!scSmtpRead($fp, [250])) {
            return $fail();
        }
    }

    if ($user !== '') {
        fwrite($fp, "AUTH LOGIN\r\n");
        if (!scSmtpRead($fp, [334])) {
            return $fail();
        }
        fwrite($fp, base64_encode($user) . "\r\n");
        if (!scSmtpRead($fp, [334])) {
            return $fail();
        }
        fwrite($fp, base64_encode($pass) . "\r\n");
        if (!scSmtpRead($fp, [235])) {
            return $fail();
        }
    }

    fwrite($fp, "MAIL FROM:<{$from}>\r\n");
    if (!scSmtpRead($fp, [250])) {
        return $fail();
    }
    fwrite($fp, "RCPT TO:<{$to}>\r\n");
    if (!scSmtpRead($fp, [250, 251])) {
        return $fail();
    }
    fwrite($fp, "DATA\r\n");
    if (!scSmtpRead($fp, [354])) {
        return $fail();
    }

    $safeSubject = str_replace(["\r", "\n"], '', $subject);
    $message = "From: ScientistCloud <{$from}>\r\n"
        . "To: {$to}\r\n"
        . "Subject: {$safeSubject}\r\n"
        . "MIME-Version: 1.0\r\n"
        . "Content-Type: text/plain; charset=UTF-8\r\n"
        . "\r\n"
        . $body
        . "\r\n.";
    fwrite($fp, $message . "\r\n");
    if (!scSmtpRead($fp, [250])) {
        return $fail();
    }
    fwrite($fp, "QUIT\r\n");
    fclose($fp);
    return true;
}
