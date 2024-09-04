




<?php
header('Content-Type: application/json');
header("Access-Control-Allow-Origin: http://127.0.0.1:800");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// Enable error reporting
ini_set('display_errors', 1);
error_reporting(E_ALL);

$debug = [];

try {
    // Log received data
    $debug[] = 'Received data: ' . file_get_contents('php://input');

    // Connect to SQLite database
    $db = new PDO('sqlite:../emails.db');
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $debug[] = "Connected to database";

    // Get the POST data
    $data = json_decode(file_get_contents('php://input'), true);
    $email = filter_var($data['email'], FILTER_SANITIZE_EMAIL);
    $interest = isset($data['interest']) ? filter_var($data['interest'], FILTER_SANITIZE_STRING) : '';
    $subInterest = isset($data['subInterest']) ? filter_var($data['subInterest'], FILTER_SANITIZE_STRING) : '';

    $debug[] = "Processed data - Email: $email, Interest: $interest, Sub-interest: $subInterest";

    if (filter_var($email, FILTER_VALIDATE_EMAIL) && !empty($interest) && !empty($subInterest)) {
        // Insert email, interest, and sub-interest into the database
        $stmt = $db->prepare("INSERT INTO emails (email, interest, sub_interest) VALUES (:email, :interest, :sub_interest)");
        $stmt->bindParam(':email', $email);
        $stmt->bindParam(':interest', $interest);
        $stmt->bindParam(':sub_interest', $subInterest);
        $stmt->execute();

        $debug[] = "Data inserted successfully";
        echo json_encode(["success" => true, "message" => "Email and preferences saved successfully!", "debug" => $debug]);
    } else {
        $debug[] = "Invalid data - Email valid: " . (filter_var($email, FILTER_VALIDATE_EMAIL) ? 'true' : 'false') . 
                   ", Interest empty: " . (empty($interest) ? 'true' : 'false') . 
                   ", Sub-interest empty: " . (empty($subInterest) ? 'true' : 'false');
        echo json_encode(["success" => false, "error" => "Invalid email address or preferences.", "debug" => $debug]);
    }
} catch (PDOException $e) {
    $debug[] = "Database error: " . $e->getMessage();
    echo json_encode(["success" => false, "error" => $e->getMessage(), "debug" => $debug]);
}
?>