const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const User = require('../models/User'); // adjust path if different

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Register
router.post('/register', async (req, res) => {
  const { username, email, password, role } = req.body;

  try {
    const existingUser = await User.findOne({ email });
    if (existingUser)
      return res.status(400).json({ message: 'Email already registered' });

    // Create user without manually hashing password
    const user = new User({
      username,
      email,
      password,  // let the User model hash it via pre-save middleware
      role: role || 'client',
    });

    await user.save();
    res.status(201).json({ message: 'User registered successfully' });
  } catch (err) {
    res.status(500).json({ message: 'Registration failed', error: err.message });
  }
});

// Login
router.post('/login', async (req, res) => {
  const { identifier, email, username, password } = req.body;

  try {
    const loginId = (identifier || email || username || '').trim();
    if (!loginId || !password) {
      return res.status(400).json({ message: 'Username/email and password are required' });
    }

    const safeExactRegex = new RegExp(`^\\s*${escapeRegex(loginId)}\\s*$`, 'i');
    const safeEmailPrefixRegex = new RegExp(`^\\s*${escapeRegex(loginId)}@`, 'i');

    // Support login by:
    // 1) full email, 2) username (case-insensitive), 3) email prefix before @
    const candidates = await User.find({
      $or: [
        { email: safeExactRegex },
        { username: safeExactRegex },
        { email: safeEmailPrefixRegex },
      ],
    }).limit(10);

    const normalizedLoginId = loginId.trim().toLowerCase();
    const matchingCandidates = candidates.filter((u) => {
      const emailValue = String(u.email || '').trim().toLowerCase();
      const usernameValue = String(u.username || '').trim().toLowerCase();
      const emailPrefix = emailValue.split('@')[0] || '';
      return (
        emailValue === normalizedLoginId ||
        usernameValue === normalizedLoginId ||
        emailPrefix === normalizedLoginId
      );
    });
    if (matchingCandidates.length === 0)
      return res.status(400).json({ message: 'Invalid credentials' });

    // Try password against all matched users (handles duplicate/old records safely)
    let user = null;
    for (const candidate of matchingCandidates) {
      const ok = await bcrypt.compare(password, candidate.password);
      if (ok) {
        user = candidate;
        break;
      }
    }

    if (!user)
      return res.status(400).json({ message: 'Invalid credentials' });

    const token = jwt.sign({ id: user._id }, process.env.JWT_SECRET, {
      expiresIn: '1d',
    });

    res.status(200).json({
      token,
      user: {
        username: user.username,
        email: user.email,
        role: user.role,
      },
    });
  } catch (err) {
    res.status(500).json({ message: 'Login failed', error: err.message });
  }
});

module.exports = router;
