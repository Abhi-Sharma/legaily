const express = require('express');
const router = express.Router();
const DiaryEntry = require('../models/DiaryEntry');
const authMiddleware = require('../middleware/authMiddleware');

// Get all diary entries for the logged-in user
router.get('/all', authMiddleware, async (req, res) => {
  try {
    const entries = await DiaryEntry.find({ userId: req.user.id });
    res.json(entries);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Server Error' });
  }
});

// Create a new diary entry
router.post('/create', authMiddleware, async (req, res) => {
  try {
    const newEntry = new DiaryEntry({
      ...req.body,
      userId: req.user.id
    });
    const savedEntry = await newEntry.save();
    res.status(201).json(savedEntry);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Server Error while saving entry' });
  }
});

// Update an entry
router.put('/update/:id', authMiddleware, async (req, res) => {
  try {
    let entry = await DiaryEntry.findOne({ _id: req.params.id, userId: req.user.id });
    if (!entry) return res.status(404).json({ message: 'Entry not found' });

    // Update fields
    Object.assign(entry, req.body);
    const updatedEntry = await entry.save();
    res.json(updatedEntry);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Server Error on update' });
  }
});

// Delete an entry
router.delete('/delete/:id', authMiddleware, async (req, res) => {
  try {
    const entry = await DiaryEntry.findOneAndDelete({ _id: req.params.id, userId: req.user.id });
    if (!entry) return res.status(404).json({ message: 'Entry not found' });
    res.json({ message: 'Entry removed' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Server Error on delete' });
  }
});

// Link a document to a diary entry
router.post('/:id/link-document', authMiddleware, async (req, res) => {
  try {
    const { title, type, content } = req.body;
    let entry = await DiaryEntry.findOne({ _id: req.params.id, userId: req.user.id });
    
    if (!entry) return res.status(404).json({ message: 'Entry not found' });

    entry.linkedDocuments.push({ title, type, content });
    await entry.save();
    res.json(entry);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Server Error on link document' });
  }
});

// Unlink a document
router.delete('/:id/unlink-document/:docId', authMiddleware, async (req, res) => {
  try {
    let entry = await DiaryEntry.findOne({ _id: req.params.id, userId: req.user.id });
    if (!entry) return res.status(404).json({ message: 'Entry not found' });

    entry.linkedDocuments = entry.linkedDocuments.filter(
      doc => doc._id.toString() !== req.params.docId
    );
    await entry.save();
    res.json(entry);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Server Error on unlink document' });
  }
});

module.exports = router;
