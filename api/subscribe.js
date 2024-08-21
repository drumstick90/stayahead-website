import mongoose from 'mongoose';

const URI = process.env.MONGODB_URI;

const emailSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true },
  timestamp: { type: Date, default: Date.now }
});

let Email;
if (mongoose.models.Email) {
  Email = mongoose.model('Email');
} else {
  Email = mongoose.model('Email', emailSchema);
}

let cachedConnection = null;

async function connectToDatabase() {
  if (cachedConnection) {
    return cachedConnection;
  }

  const connection = await mongoose.connect(URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
  });

  cachedConnection = connection;
  return connection;
}

export default async function handler(req, res) {
  if (req.method === 'POST') {
    try {
      await connectToDatabase();
      
      const { email } = req.body;

      const newEmail = new Email({ email });
      await newEmail.save();
      
      res.status(201).json({ message: 'Email subscribed successfully' });
    } catch (error) {
      if (error.code === 11000) {
        return res.status(400).json({ message: 'Email already subscribed' });
      }
      res.status(500).json({ message: 'Error subscribing email', error: error.message });
    } finally {
      // Close the connection
      if (cachedConnection) {
        await mongoose.disconnect();
        cachedConnection = null;
      }
    }
  } else {
    res.setHeader('Allow', ['POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}