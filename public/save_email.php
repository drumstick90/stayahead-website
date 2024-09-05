<?php
ini_set('log_errors', 1);
ini_set('error_log', dirname(__FILE__) . '/error_log.txt');
error_log("Script started");

header('Content-Type: application/json');
header("Access-Control-Allow-Origin: http://127.0.0.1:5500");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

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
    $interest = isset($data['interest']) ? htmlspecialchars($data['interest']) : '';
    $subInterest = isset($data['subInterest']) ? htmlspecialchars($data['subInterest']) : '';

    // Extract the category name from the subInterest URL
    if ($subInterest !== 'All') {
        $queryString = parse_url($subInterest, PHP_URL_QUERY);
        if ($queryString) {
            parse_str($queryString, $params);
            $subInterest = isset($params['category']) ? urldecode($params['category']) : $subInterest;
        }
    }

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
    echo json_encode([
        "success" => false, 
        "error" => "Database error: " . $e->getMessage(),
        "debug" => $debug
    ]);
}
?>
