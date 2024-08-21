const mongoose = require('mongoose');

let conn = null;

const URI = process.env.MONGODB_URI;

const emailSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true },
  timestamp: { type: Date, default: Date.now }
});

module.exports = async (req, res) => {
  if (req.method === 'POST') {
    if (!conn) {
      conn = await mongoose.connect(URI, {
        useNewUrlParser: true,
        useUnifiedTopology: true,
      });
    }
    
    const Email = mongoose.models.Email || mongoose.model('Email', emailSchema);

    const { email } = req.body;

    try {
      const newEmail = new Email({ email });
      await newEmail.save();
      res.status(201).json({ message: 'Email subscribed successfully' });
    } catch (error) {
      if (error.code === 11000) {
        return res.status(400).json({ message: 'Email already subscribed' });
      }
      res.status(500).json({ message: 'Error subscribing email', error: error.message });
    }
  } else {
    res.setHeader('Allow', ['POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
};