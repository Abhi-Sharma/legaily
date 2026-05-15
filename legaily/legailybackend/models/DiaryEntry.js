// legaily_backend/models/DiaryEntry.js
const mongoose = require('mongoose');

const linkedDocSchema = new mongoose.Schema({
  title: { type: String, required: true },
  type: { type: String, enum: ['AI_GENERATED', 'UPLOADED', 'DRAFT', 'SUMMARY', 'TRANSLATION'], default: 'AI_GENERATED' },
  content: { type: String }, // Either raw text if generated or URL
  createdAt: { type: Date, default: Date.now }
});

const diaryEntrySchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  caseNumber: { type: String },
  partyName: { type: String, required: true },
  date: { type: Date, required: true },
  time: { type: String },
  ampm: { type: String },
  notes: { type: String },
  linkedDocuments: [linkedDocSchema]
}, { timestamps: true });

module.exports = mongoose.model('DiaryEntry', diaryEntrySchema);
