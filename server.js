const express = require('express');
const path = require('path');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const fs = require('fs');
const app = express();
const port = 3000;

// Middleware
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// CSV setup
const csvFilePath = path.join(__dirname, 'subscribers.csv');

// Create CSV file if it doesn't exist
if (!fs.existsSync(csvFilePath)) {
    fs.writeFileSync(csvFilePath, 'email,areaOfInterest,signupDate\n');
}

const csvWriter = createCsvWriter({
    path: csvFilePath,
    header: [
        {id: 'email', title: 'email'},
        {id: 'areaOfInterest', title: 'areaOfInterest'},
        {id: 'signupDate', title: 'signupDate'}
    ],
    append: true
});

// Routes
app.get('/', (req, res) => {
    res.send('Hello World!');
});

app.post('/api/register', async (req, res) => {
    const { email, areaOfInterest } = req.body;
    const signupDate = new Date().toISOString();

    try {
        await csvWriter.writeRecords([{ email, areaOfInterest, signupDate }]);
        res.json({ message: 'Registration successful' });
    } catch (error) {
        console.error('Error writing to CSV:', error);
        res.status(500).json({ error: 'Error registering user' });
    }
});

// Start the server
app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});