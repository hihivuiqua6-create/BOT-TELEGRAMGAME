<?php
// KINGBOT backup.php - bản chống lỗi RemoteDisconnected cho InfinityFree/shared host.
// Upload file này lên host PHP, tạo thư mục data nếu chưa có.
// Đổi SECRET giống "Backup Secret" trong Web Admin Python.

@ini_set('display_errors', '0');
@ini_set('log_errors', '1');
@ini_set('memory_limit', '256M');
@ini_set('max_execution_time', '30');

$SECRET = 'CHANGE_ME_123';
$dataDir = __DIR__ . '/data';
$file = $dataDir . '/kingbot_latest_backup.json';
$logFile = $dataDir . '/backup_log.txt';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Connection: close');

function safe_mkdir($dir) {
    if (!is_dir($dir)) @mkdir($dir, 0755, true);
}
function out_json($arr, $code = 200) {
    http_response_code($code);
    echo json_encode($arr, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}
function logx($s) {
    global $logFile;
    @file_put_contents($logFile, date('Y-m-d H:i:s') . ' ' . $s . "\n", FILE_APPEND | LOCK_EX);
}
function read_json_body() {
    $raw = file_get_contents('php://input');
    if (!$raw && isset($_POST['data'])) $raw = $_POST['data'];
    $j = json_decode($raw, true);
    return [$raw, $j];
}

safe_mkdir($dataDir);

// Test nhanh: backup.php?ping=1
if (isset($_GET['ping'])) {
    out_json(['ok' => true, 'message' => 'backup_php_alive', 'time' => date('Y-m-d H:i:s')]);
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    list($raw, $j) = read_json_body();
    if (!is_array($j)) {
        logx('bad_json len=' . strlen((string)$raw));
        out_json(['ok' => false, 'error' => 'bad_json'], 400);
    }
    if (($j['secret'] ?? '') !== $SECRET) {
        logx('bad_secret_post');
        out_json(['ok' => false, 'error' => 'bad_secret'], 403);
    }
    if (!isset($j['payload']) || !is_array($j['payload'])) {
        logx('missing_payload');
        out_json(['ok' => false, 'error' => 'missing_payload'], 400);
    }

    $payload = $j['payload'];
    $payload['_backup_saved_at'] = date('Y-m-d H:i:s');
    $payload['_reason'] = $j['reason'] ?? 'unknown';

    $tmp = $file . '.tmp';
    $encoded = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($encoded === false) out_json(['ok' => false, 'error' => 'json_encode_failed'], 500);
    if (@file_put_contents($tmp, $encoded, LOCK_EX) === false) {
        logx('write_tmp_failed');
        out_json(['ok' => false, 'error' => 'write_failed'], 500);
    }
    @rename($tmp, $file);
    logx('SAVE reason=' . ($j['reason'] ?? 'unknown') . ' bytes=' . strlen($encoded));
    out_json(['ok' => true, 'message' => 'backup_saved', 'time' => $payload['_backup_saved_at'], 'bytes' => strlen($encoded)]);
}

$secret = $_GET['secret'] ?? '';
if ($secret !== $SECRET) out_json(['ok' => false, 'error' => 'bad_secret'], 403);
if (!file_exists($file)) out_json(['ok' => false, 'error' => 'no_backup_yet'], 404);

$raw = @file_get_contents($file);
$payload = json_decode($raw, true);
if (!is_array($payload)) out_json(['ok' => false, 'error' => 'backup_corrupt'], 500);
out_json(['ok' => true, 'payload' => $payload]);
