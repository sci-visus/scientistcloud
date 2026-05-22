<?php
/**
 * Parse one or more email addresses from free-form text (comma/newline separated,
 * "Name <email@domain.com>", quoted names, etc.).
 *
 * @return array{valid: string[], invalid: string[]}
 */
function sc_parse_email_list($text): array
{
    $raw = trim((string) $text);
    if ($raw === '') {
        return ['valid' => [], 'invalid' => []];
    }

    $valid = [];
    $invalid = [];
    $seen = [];

    if (preg_match_all('/[a-zA-Z0-9._%+\'-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/', $raw, $matches)) {
        foreach ($matches[0] as $email) {
            $email = strtolower(trim($email));
            if ($email === '' || isset($seen[$email])) {
                continue;
            }
            if (filter_var($email, FILTER_VALIDATE_EMAIL)) {
                $seen[$email] = true;
                $valid[] = $email;
            } else {
                $invalid[] = $email;
            }
        }
    }

    // Fallback: split on commas/newlines and try plain tokens
    if ($valid === []) {
        $parts = preg_split('/[\s,;]+/', $raw) ?: [];
        foreach ($parts as $part) {
            $part = trim($part, " \t\n\r\0\x0B\"'<>");
            if ($part === '') {
                continue;
            }
            $part = strtolower($part);
            if (isset($seen[$part])) {
                continue;
            }
            if (filter_var($part, FILTER_VALIDATE_EMAIL)) {
                $seen[$part] = true;
                $valid[] = $part;
            } elseif (strpos($part, '@') !== false) {
                $invalid[] = $part;
            }
        }
    }

    return ['valid' => $valid, 'invalid' => $invalid];
}
