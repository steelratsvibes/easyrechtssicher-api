<?php
require_once __DIR__ . '/../shared/client.php';
header('Content-Type: application/json');
header('Cache-Control: private, no-store');
try { echo json_encode(\EasyRechtssicherExample\run(getenv('EASYRECHTSSICHER_MODE') ?: 'stack'), JSON_THROW_ON_ERROR); }
catch (\Throwable) { http_response_code(502); echo '{"error":"API request or response failed"}'; }
