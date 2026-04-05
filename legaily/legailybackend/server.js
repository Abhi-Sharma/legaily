// legaily_backend/server.js
const path = require('path');
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config({ path: path.join(__dirname, '.env') });

const mongoUri = (process.env.MONGO_URI || '').trim();
if (!mongoUri) {
  console.error('❌ MONGO_URI is empty. Add it to:', path.join(__dirname, '.env'));
} else {
  const ats = mongoUri.match(/@/g) || [];
  if (ats.length !== 1) {
    console.warn(
      '⚠️  MONGO_URI should have exactly ONE "@" (before the hostname). ' +
        'If your password contains @, use %40 instead (e.g. anmol%40123).'
    );
  }
  const parsed = mongoUri.match(/^mongodb\+srv:\/\/([^:]+):[^@]+@([^/?]+)\/([^?]+)/);
  if (parsed) {
    console.log(`📎 MongoDB URI: user="${parsed[1]}" → host "${parsed[2]}" / db "${parsed[3]}"`);
  } else {
    console.warn('⚠️  MONGO_URI should look like: mongodb+srv://USER:PASSWORD@cluster.../legaily?...');
  }
}

const authRoutes = require('./routes/authRoutes');

const app = express();
app.use(cors());
app.use(express.json());

// Root route for sanity check
app.get('/', (req, res) => {
  res.send('✅ Backend server is running');
});

// Routes
app.use('/api/auth', authRoutes);

const PORT = 5001;

mongoose.connect(mongoUri || process.env.MONGO_URI)
  .then(() => {
    console.log("✅ MongoDB connected");
  })
  .catch(err => {
    console.error('❌ MongoDB connection error:', err);
  });

// Add this to log the database name once connection opens
mongoose.connection.once('open', () => {
  console.log('✅ MongoDB connection is open to database:', mongoose.connection.name);
});

app.listen(PORT, () => console.log(`🚀 Server running on http://localhost:${PORT}`));
