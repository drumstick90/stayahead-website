<?php
header('Content-Type: application/json');
header("Access-Control-Allow-Origin: http://127.0.0.1:5500");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

try {
    // Get the POST data
    $data = json_decode(file_get_contents('php://input'), true);

    $email = filter_var($data['email'] ?? '', FILTER_SANITIZE_EMAIL);
    $interest = htmlspecialchars($data['interest'] ?? '');
    $subInterest = htmlspecialchars($data['subInterest'] ?? '');

    if (filter_var($email, FILTER_VALIDATE_EMAIL) && !empty($interest) && !empty($subInterest)) {
        // Connect to SQLite database
        $db = new PDO('sqlite:' . dirname(__FILE__) . '/emails.db');
        $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        // Create table if it doesn't exist
        $db->exec("
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                interest TEXT NOT NULL,
                sub_interest TEXT NOT NULL
            )
        ");

        // Insert data
        $stmt = $db->prepare("INSERT INTO emails (email, interest, sub_interest) VALUES (:email, :interest, :sub_interest)");
        $stmt->bindParam(':email', $email);
        $stmt->bindParam(':interest', $interest);
        $stmt->bindParam(':sub_interest', $subInterest);
        $stmt->execute();

        echo json_encode(["success" => true, "message" => "Email and preferences saved successfully!"]);
    } else {
        echo json_encode(["success" => false, "error" => "Invalid email address or preferences."]);
    }
} catch (Exception $e) {
    // Log the error (do not expose sensitive details to the client)
    error_log("Error in save_email.php: " . $e->getMessage());
    echo json_encode(["success" => false, "error" => "Server error occurred. Please try again later."]);
}
?>
