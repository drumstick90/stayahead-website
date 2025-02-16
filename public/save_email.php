<?php
// save_email.php
// This script processes incoming JSON data, sanitizes it, saves customer email and preferences into customers.db,
// and returns a proper JSON response.

// Disable error display for production; errors will be logged.
ini_set('display_errors', 0);
error_reporting(E_ALL);

// Set response header to JSON.
header('Content-Type: application/json');

// Retrieve the raw POST input.
$rawData = file_get_contents("php://input");
if (!$rawData) {
    error_log("No input received in save_email.php");
    echo json_encode(["success" => false, "error" => "No input received."]);
    exit;
}

// Decode the JSON input.
$data = json_decode($rawData, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    error_log("JSON decode error in save_email.php: " . json_last_error_msg());
    echo json_encode(["success" => false, "error" => "Invalid JSON input."]);
    exit;
}

// Retrieve and trim input values.
$email = isset($data['email']) ? trim($data['email']) : '';
$field = isset($data['interest']) ? trim($data['interest']) : '';
$category = isset($data['subInterest']) ? trim($data['subInterest']) : '';

// Validate required fields.
if (!filter_var($email, FILTER_VALIDATE_EMAIL) || empty($field) || empty($category)) {
    error_log("Invalid input in save_email.php: email: $email, field: $field, category: $category");
    echo json_encode(["success" => false, "error" => "Invalid email or missing field/category."]);
    exit;
}

// Sanitize inputs using modern filters.
$email = filter_var($email, FILTER_SANITIZE_EMAIL);
$field = filter_var($field, FILTER_SANITIZE_FULL_SPECIAL_CHARS);
$category = filter_var($category, FILTER_SANITIZE_FULL_SPECIAL_CHARS);

// Set the path to the SQLite database (customers.db in app/db)
$dbFile = __DIR__ . "/../db/customers.db";

try {
    // Connect to the SQLite database.
    $db = new PDO("sqlite:" . $dbFile);
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    error_log("Database connection error in save_email.php: " . $e->getMessage());
    echo json_encode(["success" => false, "error" => "Database connection failed."]);
    exit;
}

try {
    // Create the customers table if it doesn't exist.
    // Using CURRENT_TIMESTAMP as the default for created_at.
    $db->exec("CREATE TABLE IF NOT EXISTS customers (
        email TEXT PRIMARY KEY,
        field TEXT NOT NULL,
        category TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )");
} catch (PDOException $e) {
    error_log("Error creating table in save_email.php: " . $e->getMessage());
    echo json_encode(["success" => false, "error" => "Database setup failed."]);
    exit;
}

try {
    // Insert or update the customer record.
    $stmt = $db->prepare("INSERT INTO customers (email, field, category) 
                          VALUES (?, ?, ?)
                          ON CONFLICT(email) DO UPDATE SET field = excluded.field, category = excluded.category");
    $stmt->execute([$email, $field, $category]);

    // Retrieve the record to include the created_at value in the response.
    $stmt = $db->prepare("SELECT email, field, category, created_at FROM customers WHERE email = ?");
    $stmt->execute([$email]);
    $insertedData = $stmt->fetch(PDO::FETCH_ASSOC);

    echo json_encode([
        "success" => true,
        "message" => "Email and preferences saved successfully!",
        "email" => $insertedData['email'],
        "field" => $insertedData['field'],
        "category" => $insertedData['category'],
        "createdAt" => $insertedData['created_at']
    ]);
} catch (PDOException $e) {
    error_log("Database insertion error in save_email.php: " . $e->getMessage());
    echo json_encode(["success" => false, "error" => "Database insertion error."]);
    exit;
}
?>