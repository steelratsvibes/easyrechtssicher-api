<?php
// Copy to config/easyrechtssicher.php; compatible with Laravel config:cache.
return [
    'mode' => env('EASYRECHTSSICHER_MODE', 'stack'),
    'api_key' => env('EASYRECHTSSICHER_API_KEY'),
];
