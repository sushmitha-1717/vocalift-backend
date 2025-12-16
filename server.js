const express = require('express');
const multer = require('multer');
const cors = require('cors');
const fs = require('fs');
const { exec } = require('child_process');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());

// Ensure uploads directory exists
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
  console.log('Created uploads folder:', uploadDir);
}

// Multer storage configuration
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, 'uploads/'),
  filename: (req, file, cb) => cb(null, Date.now() + '-' + file.originalname)
});
const upload = multer({ storage });

// -----------------------------
// Video Upload + Analysis Route
// -----------------------------
app.post('/upload', upload.single('video'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No video file uploaded.' });

  const videoPath = path.join(__dirname, req.file.path);
  console.log('Video uploaded:', videoPath);

  // Call Python script to analyze the uploaded video
  exec(`python3 analyze_video.py "${videoPath}"`, (error, stdout, stderr) => {
    if (error) {
      console.error('Exec error:', error.message);
      return res.status(500).json({ error: 'Video analysis failed.' });
    }

    if (stderr) {
      console.warn('Python stderr:', stderr);
    }

    try {
      const feedback = JSON.parse(stdout);
      res.json({ message: 'Video analyzed successfully.', feedback });
    } catch (err) {
      console.error('JSON parse error:', err);
      console.log('Raw output:', stdout);
      res.status(500).json({ error: 'Invalid analysis output.' });
    }
  });
});

// -----------------------------
// Start the server
// -----------------------------
const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});


