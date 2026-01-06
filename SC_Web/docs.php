<?php
/**
 * ScientistCloud Data Portal - Documentation Router
 * Serves documentation pages at /portal/docs/
 */

// Start session if not already started
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

// Include configuration
require_once(__DIR__ . '/config.php');

// Get the requested documentation page
$page = $_GET['page'] ?? 'index';
$page = preg_replace('/[^a-z0-9_-]/i', '', $page); // Sanitize page name

// List of available documentation pages
$availablePages = [
    'index' => 'index.md',
    'api' => 'api.md',
    'api-authentication' => 'api-authentication.md',
    'api-upload' => 'api-upload.md',
    'api-datasets' => 'api-datasets.md',
    'curl-scripts' => 'curl-scripts.md',
    'python-examples' => 'python-examples.md',
    'getting-started' => 'getting-started.md'
];

// Check if page exists
if (!isset($availablePages[$page])) {
    $page = 'index';
}

$docFile = __DIR__ . '/docs/' . $availablePages[$page];

// If file doesn't exist, show index
if (!file_exists($docFile)) {
    $page = 'index';
    $docFile = __DIR__ . '/docs/index.md';
}

// Read markdown content
$markdown = file_exists($docFile) ? file_get_contents($docFile) : '# Documentation Not Found';

// Simple markdown to HTML converter (improved implementation)
function markdownToHtml($markdown) {
    // First, protect code blocks from processing
    $codeBlocks = [];
    $codeBlockIndex = 0;
    
    // Extract code blocks
    $markdown = preg_replace_callback('/```(\w+)?\n(.*?)```/s', function($matches) use (&$codeBlocks, &$codeBlockIndex) {
        $placeholder = "___CODE_BLOCK_{$codeBlockIndex}___";
        $codeBlocks[$codeBlockIndex] = [
            'lang' => $matches[1] ?? '',
            'code' => $matches[2]
        ];
        $codeBlockIndex++;
        return $placeholder;
    }, $markdown);
    
    // Extract inline code
    $inlineCode = [];
    $inlineIndex = 0;
    $markdown = preg_replace_callback('/`([^`]+)`/', function($matches) use (&$inlineCode, &$inlineIndex) {
        $placeholder = "___INLINE_CODE_{$inlineIndex}___";
        $inlineCode[$inlineIndex] = $matches[1];
        $inlineIndex++;
        return $placeholder;
    }, $markdown);
    
    // Process tables BEFORE escaping HTML
    $tables = [];
    $tableIndex = 0;
    $lines = explode("\n", $markdown);
    $processedLines = [];
    $tableRows = [];
    $inTable = false;
    
    foreach ($lines as $line) {
        $trimmedLine = trim($line);
        
        // Check if this is a table row
        if (preg_match('/^\|(.+)\|$/', $trimmedLine)) {
            if (!$inTable) {
                $inTable = true;
                $tableRows = [];
            }
            
            // Check if this is a separator row (|---|---|)
            if (preg_match('/^[\|\s\-:]+$/', $trimmedLine)) {
                // Skip separator row, it just indicates header/data boundary
                continue;
            }
            
            // Parse table cells
            $cells = array_map('trim', explode('|', trim($trimmedLine, '|')));
            $tableRows[] = $cells;
        } else {
            // End of table
            if ($inTable && count($tableRows) > 0) {
                $placeholder = "___TABLE_{$tableIndex}___";
                $tables[$tableIndex] = $tableRows;
                $tableIndex++;
                $processedLines[] = $placeholder;
                $tableRows = [];
                $inTable = false;
            }
            
            if (!$inTable) {
                $processedLines[] = $line;
            }
        }
    }
    
    // Handle table at end of document
    if ($inTable && count($tableRows) > 0) {
        $placeholder = "___TABLE_{$tableIndex}___";
        $tables[$tableIndex] = $tableRows;
        $tableIndex++;
        $processedLines[] = $placeholder;
    }
    
    $markdown = implode("\n", $processedLines);
    
    // Now escape HTML
    $html = htmlspecialchars($markdown, ENT_QUOTES, 'UTF-8');
    
    // Restore tables as HTML
    foreach ($tables as $index => $rows) {
        $tableHtml = '<table class="table table-bordered table-striped">';
        
        foreach ($rows as $rowIndex => $row) {
            $tableHtml .= '<tr>';
            foreach ($row as $cell) {
                $tag = ($rowIndex === 0) ? 'th' : 'td';
                // Process inline formatting in cells
                $cellHtml = $cell;
                $cellHtml = preg_replace('/\*\*(.*?)\*\*/', '<strong>$1</strong>', $cellHtml);
                $cellHtml = preg_replace('/\*(.*?)\*/', '<em>$1</em>', $cellHtml);
                // Restore inline code in cells
                foreach ($inlineCode as $icIndex => $icCode) {
                    $cellHtml = str_replace("___INLINE_CODE_{$icIndex}___", "<code>" . htmlspecialchars($icCode) . "</code>", $cellHtml);
                }
                $tableHtml .= "<$tag>" . $cellHtml . "</$tag>";
            }
            $tableHtml .= '</tr>';
        }
        
        $tableHtml .= '</table>';
        $html = str_replace("___TABLE_{$index}___", $tableHtml, $html);
    }
    
    // Headers
    $html = preg_replace('/^### (.*?)$/m', '<h3>$1</h3>', $html);
    $html = preg_replace('/^## (.*?)$/m', '<h2>$1</h2>', $html);
    $html = preg_replace('/^# (.*?)$/m', '<h1>$1</h1>', $html);
    
    // Bold and italic (bold first to avoid conflicts)
    $html = preg_replace('/\*\*(.*?)\*\*/', '<strong>$1</strong>', $html);
    $html = preg_replace('/\*(.*?)\*/', '<em>$1</em>', $html);
    
    // Links
    $html = preg_replace('/\[([^\]]+)\]\(([^\)]+)\)/', '<a href="$2">$1</a>', $html);
    
    // Lists
    $html = preg_replace('/^\* (.*?)$/m', '<li>$1</li>', $html);
    $html = preg_replace('/^- (.*?)$/m', '<li>$1</li>', $html);
    $html = preg_replace('/^(\d+)\. (.*?)$/m', '<li>$2</li>', $html);
    
    // Wrap consecutive list items in ul tags
    $html = preg_replace('/(<li>.*?<\/li>\s*)+/s', '<ul>$0</ul>', $html);
    
    // Restore code blocks
    foreach ($codeBlocks as $index => $block) {
        $lang = $block['lang'] ? ' class="language-' . htmlspecialchars($block['lang']) . '"' : '';
        $code = htmlspecialchars($block['code']);
        $html = str_replace("___CODE_BLOCK_{$index}___", "<pre><code{$lang}>{$code}</code></pre>", $html);
    }
    
    // Restore inline code
    foreach ($inlineCode as $index => $code) {
        $html = str_replace("___INLINE_CODE_{$index}___", "<code>" . htmlspecialchars($code) . "</code>", $html);
    }
    
    // Paragraphs - split by double newlines, but preserve block elements
    $paragraphs = preg_split('/\n\s*\n/', $html);
    $processedParagraphs = [];
    
    foreach ($paragraphs as $para) {
        $para = trim($para);
        if (empty($para)) continue;
        
        // Don't wrap if it's already a block element
        if (preg_match('/^<(h[1-6]|pre|ul|ol|table|div)/', $para)) {
            $processedParagraphs[] = $para;
        } else {
            $processedParagraphs[] = '<p>' . $para . '</p>';
        }
    }
    
    $html = implode("\n\n", $processedParagraphs);
    
    return $html;
}

$htmlContent = markdownToHtml($markdown);

?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ScientistCloud Data Portal - Documentation</title>
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- FontAwesome Icons -->
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <!-- Highlight.js for code syntax highlighting -->
  <link href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <style>
    body {
      background-color: #f8f9fa;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    .docs-container {
      width: 100%;
      max-width: 100%;
      margin: 0;
      padding: 20px;
      display: flex;
      flex-direction: column;
    }
    .docs-row {
      display: flex;
      flex-direction: row;
      gap: 20px;
      width: 100%;
    }
    .docs-sidebar {
      background: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      margin-bottom: 20px;
      flex: 0 0 250px;
      min-width: 200px;
      max-width: 300px;
    }
    .docs-content {
      background: white;
      border-radius: 8px;
      padding: 40px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      min-height: 600px;
      flex: 1 1 auto;
      min-width: 0;
    }
    .docs-sidebar h5 {
      color: #333;
      margin-bottom: 15px;
      font-weight: 600;
    }
    .docs-sidebar .nav-link {
      color: #666;
      padding: 8px 12px;
      border-radius: 4px;
      margin-bottom: 4px;
      text-decoration: none;
      display: block;
    }
    .docs-sidebar .nav-link:hover {
      background-color: #f0f0f0;
      color: #007bff;
    }
    .docs-sidebar .nav-link.active {
      background-color: #007bff;
      color: white;
    }
    .docs-content h1 {
      color: #333;
      border-bottom: 3px solid #007bff;
      padding-bottom: 10px;
      margin-bottom: 30px;
    }
    .docs-content h2 {
      color: #444;
      margin-top: 40px;
      margin-bottom: 20px;
      padding-top: 20px;
      border-top: 1px solid #eee;
    }
    .docs-content h3 {
      color: #555;
      margin-top: 30px;
      margin-bottom: 15px;
    }
    .docs-content code {
      background-color: #f4f4f4;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 0.9em;
    }
    .docs-content pre {
      background-color: #f8f8f8;
      border: 1px solid #e0e0e0;
      border-radius: 4px;
      padding: 15px;
      overflow-x: auto;
    }
    .docs-content pre code {
      background-color: transparent;
      padding: 0;
    }
    .docs-content table {
      margin: 20px 0;
    }
    .docs-content table th {
      background-color: #f8f9fa;
      font-weight: 600;
    }
    .back-link {
      margin-bottom: 20px;
    }
    .back-link a {
      color: #007bff;
      text-decoration: none;
    }
    .back-link a:hover {
      text-decoration: underline;
    }
    @media (max-width: 768px) {
      .docs-row {
        flex-direction: column;
      }
      .docs-sidebar {
        flex: 0 0 auto;
        max-width: 100%;
      }
    }
  </style>
</head>
<body>
  <div class="docs-container">
    <div class="back-link">
      <a href="index.php"><i class="fas fa-arrow-left"></i> Back to Portal</a>
    </div>
    
    <div class="docs-row">
      <div class="docs-sidebar">
        <h5><i class="fas fa-book"></i> Documentation</h5>
        <nav class="nav flex-column">
          <a class="nav-link <?php echo $page === 'index' ? 'active' : ''; ?>" href="?page=index">Overview</a>
          <a class="nav-link <?php echo $page === 'getting-started' ? 'active' : ''; ?>" href="?page=getting-started">Getting Started</a>
          <a class="nav-link <?php echo $page === 'api' ? 'active' : ''; ?>" href="?page=api">API Overview</a>
          <a class="nav-link <?php echo $page === 'api-authentication' ? 'active' : ''; ?>" href="?page=api-authentication">Authentication API</a>
          <a class="nav-link <?php echo $page === 'api-upload' ? 'active' : ''; ?>" href="?page=api-upload">Upload API</a>
          <a class="nav-link <?php echo $page === 'api-datasets' ? 'active' : ''; ?>" href="?page=api-datasets">Datasets API</a>
          <a class="nav-link <?php echo $page === 'curl-scripts' ? 'active' : ''; ?>" href="?page=curl-scripts">Curl Scripts</a>
          <a class="nav-link <?php echo $page === 'python-examples' ? 'active' : ''; ?>" href="?page=python-examples">Python Examples</a>
        </nav>
      </div>
      
      <div class="docs-content">
        <?php echo $htmlContent; ?>
      </div>
    </div>
  </div>
  
  <script>
    // Initialize syntax highlighting
    hljs.highlightAll();
  </script>
</body>
</html>

