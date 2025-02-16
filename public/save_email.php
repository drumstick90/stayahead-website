<?php
declare(strict_types=1);

// Allow only POST requests.
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(["success" => false, "error" => "Method not allowed"]);
    exit;
}

// Read raw JSON input.
$input = json_decode(file_get_contents('php://input'), true);
if (!is_array($input)) {
    http_response_code(400);
    echo json_encode(["success" => false, "error" => "Invalid JSON"]);
    exit;
}

// Validate required fields.
$email       = $input['email']       ?? null;
$interest    = $input['interest']    ?? null;
$subInterest = $input['subInterest'] ?? null;
if (!$email || !$interest || !$subInterest) {
    http_response_code(400);
    echo json_encode(["success" => false, "error" => "Missing required fields."]);
    exit;
}

// Retrieve the database path from the environment variable.
$dbPath = getenv('STAYAHEAD_DB_PATH');
if (!$dbPath) {
    http_response_code(500);
    echo json_encode(["success" => false, "error" => "Database path not set"]);
    exit;
}

// Connect to the SQLite database.
try {
    $db = new SQLite3($dbPath, SQLITE3_OPEN_READWRITE | SQLITE3_OPEN_CREATE);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(["success" => false, "error" => "Database connection failed"]);
    exit;
}

// Prepare the INSERT statement.
$stmt = $db->prepare('INSERT INTO customers (email, field, category) VALUES (:email, :field, :category)');
$stmt->bindValue(':email', $email, SQLITE3_TEXT);
$stmt->bindValue(':field', $interest, SQLITE3_TEXT);
$stmt->bindValue(':category', $subInterest, SQLITE3_TEXT);

$result = $stmt->execute();

if ($result) {
    // Build response; the created_at timestamp is set by SQLite as a default.
    $insertedData = [
        'email'      => $email,
        'field'      => $interest,
        'category'   => $subInterest,
        'created_at' => date('Y-m-d H:i:s') // Optionally, query the DB for the real value.
    ];

    $response = [
        "success"   => true,
        "message"   => "Email and preferences saved successfully!",
        "email"     => $insertedData['email'],
        "field"     => $insertedData['field'],
        "category"  => $insertedData['category'],
        "createdAt" => $insertedData['created_at']
    ];
    header('Content-Type: application/json');
    echo json_encode($response);
} else {
    $errorMsg = $db->lastErrorMsg();
    error_log("Insert error: " . $errorMsg);
    http_response_code(500);
    echo json_encode(["success" => false, "error" => "Database insert failed: " . $errorMsg]);
    exit;
}