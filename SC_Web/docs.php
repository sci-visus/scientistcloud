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

// Simple markdown to HTML converter (basic implementation)
function markdownToHtml($markdown) {
    $html = htmlspecialchars($markdown);
    
    // Headers
    $html = preg_replace('/^### (.*?)$/m', '<h3>$1</h3>', $html);
    $html = preg_replace('/^## (.*?)$/m', '<h2>$1</h2>', $html);
    $html = preg_replace('/^# (.*?)$/m', '<h1>$1</h1>', $html);
    
    // Code blocks
    $html = preg_replace('/```(\w+)?\n(.*?)```/s', '<pre><code class="language-$1">$2</code></pre>', $html);
    
    // Inline code
    $html = preg_replace('/`([^`]+)`/', '<code>$1</code>', $html);
    
    // Bold
    $html = preg_replace('/\*\*(.*?)\*\*/', '<strong>$1</strong>', $html);
    
    // Italic
    $html = preg_replace('/\*(.*?)\*/', '<em>$1</em>', $html);
    
    // Links
    $html = preg_replace('/\[([^\]]+)\]\(([^\)]+)\)/', '<a href="$2">$1</a>', $html);
    
    // Lists
    $html = preg_replace('/^\* (.*?)$/m', '<li>$1</li>', $html);
    $html = preg_replace('/^- (.*?)$/m', '<li>$1</li>', $html);
    $html = preg_replace('/^(\d+)\. (.*?)$/m', '<li>$2</li>', $html);
    
    // Wrap consecutive list items in ul tags
    $html = preg_replace('/(<li>.*<\/li>\n?)+/s', '<ul>$0</ul>', $html);
    
    // Tables (basic)
    $lines = explode("\n", $html);
    $inTable = false;
    $tableHtml = '';
    foreach ($lines as $line) {
        if (preg_match('/^\|(.+)\|$/', $line)) {
            if (!$inTable) {
                $tableHtml .= '<table class="table table-bordered table-striped">';
                $inTable = true;
            }
            $cells = explode('|', trim($line, '|'));
            $tableHtml .= '<tr>';
            foreach ($cells as $cell) {
                $tag = (strpos($line, '---') !== false) ? 'th' : 'td';
                $tableHtml .= "<$tag>" . trim($cell) . "</$tag>";
            }
            $tableHtml .= '</tr>';
        } else {
            if ($inTable) {
                $tableHtml .= '</table>';
                $inTable = false;
            }
        }
    }
    if ($inTable) {
        $tableHtml .= '</table>';
    }
    
    // Paragraphs
    $html = preg_replace('/\n\n/', '</p><p>', $html);
    $html = '<p>' . $html . '</p>';
    
    // Clean up empty paragraphs
    $html = preg_replace('/<p><\/p>/', '', $html);
    $html = preg_replace('/<p>(<h[1-6]>)/', '$1', $html);
    $html = preg_replace('/(<\/h[1-6]>)<\/p>/', '$1', $html);
    $html = preg_replace('/<p>(<pre>)/', '$1', $html);
    $html = preg_replace('/(<\/pre>)<\/p>/', '$1', $html);
    $html = preg_replace('/<p>(<ul>)/', '$1', $html);
    $html = preg_replace('/(<\/ul>)<\/p>/', '$1', $html);
    $html = preg_replace('/<p>(<table)/', '$1', $html);
    $html = preg_replace('/(<\/table>)<\/p>/', '$1', $html);
    
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
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }
    .docs-sidebar {
      background: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      margin-bottom: 20px;
    }
    .docs-content {
      background: white;
      border-radius: 8px;
      padding: 40px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      min-height: 600px;
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
  </style>
</head>
<body>
  <div class="docs-container">
    <div class="back-link">
      <a href="index.php"><i class="fas fa-arrow-left"></i> Back to Portal</a>
    </div>
    
    <div class="row">
      <div class="col-md-3">
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
      </div>
      
      <div class="col-md-9">
        <div class="docs-content">
          <?php echo $htmlContent; ?>
        </div>
      </div>
    </div>
  </div>
  
  <script>
    // Initialize syntax highlighting
    hljs.highlightAll();
  </script>
</body>
</html>

