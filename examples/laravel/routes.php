<?php
// Include from the host application's routes/web.php. Keep examples outside public/.
use const EasyRechtssicherExample\KEY_ERROR;
use Illuminate\Support\Facades\Route;
require_once __DIR__ . '/../shared/client.php';
Route::get('/rechtstexte', function () {
    try {
        return response()->json(\EasyRechtssicherExample\run(config('easyrechtssicher.mode', 'stack'), null, [
            'EASYRECHTSSICHER_API_KEY' => config('easyrechtssicher.api_key'),
        ]))->header('Cache-Control', 'private, no-store');
    } catch (\Throwable $error) {
        $message = $error->getMessage() === KEY_ERROR ? KEY_ERROR : 'API request or response failed';
        return response()->json(['error' => $message], 502)->header('Cache-Control', 'private, no-store');
    }
});
