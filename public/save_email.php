<?php
header('Content-Type: application/json');
header("Access-Control-Allow-Origin: http://127.0.0.1:5500");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header("Access-Control-Allow-Methods: POST, OPTIONS");
    header("Access-Control-Allow-Headers: Content-Type");
    exit(0);
}

try {
    // Define database path
    $dbPath = dirname(__FILE__) . '/emails.db';
    
    // Get the POST data
    $data = json_decode(file_get_contents('php://input'), true);

    error_log("Received data: " . json_encode($data)); // Debugging
    error_log("Database path: " . $dbPath); // Debugging database path

    $email = filter_var($data['email'] ?? '', FILTER_SANITIZE_EMAIL);
    $interest = htmlspecialchars($data['interest'] ?? '');
    $subInterest = htmlspecialchars($data['subInterest'] ?? '');

    error_log("Sanitized data: email=$email, interest=$interest, subInterest=$subInterest"); // Debugging

    if (filter_var($email, FILTER_VALIDATE_EMAIL) && !empty($interest) && !empty($subInterest)) {
        // Connect to SQLite database with file path
        $db = new PDO('sqlite:' . $dbPath);
        $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        error_log("Database connection established"); // Debugging

        // Create table if it doesn't exist
        $db->exec("
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                email TEXT NOT NULL,
                interest TEXT NOT NULL,
                sub_interest TEXT NOT NULL
            )
        ");
        error_log("Table creation successful or already exists"); // Debugging

        // Check directory permissions
        $dbDir = dirname($dbPath);
        if (!is_writable($dbDir)) {
            error_log("Directory is not writable: " . $dbDir);
            throw new Exception("Database directory is not writable");
        }

        // Insert data
        $stmt = $db->prepare("INSERT INTO emails (email, interest, sub_interest) VALUES (:email, :interest, :sub_interest)");
        $stmt->bindParam(':email', $email);
        $stmt->bindParam(':interest', $interest);
        $stmt->bindParam(':sub_interest', $subInterest);
        $stmt->execute();
        error_log("Data insertion successful"); // Debugging

        // Retrieve the inserted data for the response
        $stmt = $db->query("SELECT * FROM emails ORDER BY id DESC LIMIT 1");
        $insertedData = $stmt->fetch(PDO::FETCH_ASSOC);

        // Send detailed success response
        echo json_encode([
            "success" => true,
            "message" => "Email and preferences saved successfully!",
            "email" => $insertedData['email'],
            "interest" => $insertedData['interest'],
            "subInterest" => $insertedData['sub_interest'],
            "createdAt" => $insertedData['created_at']
        ]);
    } else {
        error_log("Invalid email or empty preferences"); // Debugging
        echo json_encode(["success" => false, "error" => "Invalid email address or preferences."]);
    }
} catch (Exception $e) {
    // Log the error (do not expose sensitive details to the client)
    error_log("Error in save_email.php: " . $e->getMessage());
    echo json_encode(["success" => false, "error" => "Server error occurred. Please try again later."]);
}
?>