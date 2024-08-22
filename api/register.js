// api/register.js
import { readFile, writeFile } from 'fs/promises';
import { parse } from 'csv-parse/sync';
import { stringify } from 'csv-stringify/sync';

export default async function handler(req, res) {
  if (req.method === 'POST') {
    try {
      const { email, areaOfInterest } = req.body;

      // Read the CSV file
      const fileContent = await readFile('users.csv', 'utf8');
      const records = parse(fileContent, { columns: true });

      // Check if email already exists
      if (records.some(record => record.email === email)) {
        return res.status(400).json({ error: 'Email already exists' });
      }

      // Add new user
      records.push({
        email,
        area_of_interest: areaOfInterest,
        subscription_date: new Date().toISOString().split('T')[0],
        subscription_status: 'active'
      });

      // Write back to CSV
      const output = stringify(records, { header: true });
      await writeFile('users.csv', output);

      res.status(200).json({ message: 'User registered successfully' });
    } catch (error) {
      console.error('Registration error:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  } else {
    res.setHeader('Allow', ['POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}