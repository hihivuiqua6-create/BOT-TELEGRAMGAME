<?php
// backup.php - Upload file này lên InfinityFree/shared hosting.
// Không cần secret theo yêu cầu. Ai biết link có thể đọc/ghi backup,
// nên chỉ dùng domain ít public hoặc đổi tên file nếu muốn kín hơn.

header('Content-Type: application/json; charset=utf-8');

$dataDir = __DIR__ . '/data';
if (!is_dir($dataDir)) mkdir($dataDir, 0755, true);
$file = $dataDir . '/kingbot_latest_backup.json';
$logFile = $dataDir . '/backup_log.txt';

function out($arr) {
    echo json_encode($arr, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit;
}
function logx($s) {
    global $logFile;
    @file_put_contents($logFile, date('Y-m-d H:i:s') . ' ' . $s . "\n", FILE_APPEND);
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = file_get_contents('php://input');
    $j = json_decode($raw, true);
    if (!is_array($j)) out(['ok' => false, 'error' => 'bad_json']);
    if (!isset($j['payload']) || !is_array($j['payload'])) out(['ok' => false, 'error' => 'missing_payload']);

    $payload = $j['payload'];
    $payload['_backup_saved_at'] = date('Y-m-d H:i:s');
    $payload['_reason'] = $j['reason'] ?? 'unknown';

    file_put_contents($file, json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    logx('SAVE reason=' . ($j['reason'] ?? 'unknown'));
    out(['ok' => true, 'message' => 'backup_saved', 'time' => $payload['_backup_saved_at']]);
}

if (!file_exists($file)) {
    out([
        'ok' => false,
        'error' => 'no_backup_yet',
        'message' => 'Chưa có backup. Bấm Đẩy backup ngay trong web admin bot trước.'
    ]);
}

$payload = json_decode(file_get_contents($file), true);
out(['ok' => true, 'payload' => $payload]);
