const express = require('express');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs').promises;
const axios = require('axios');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3001;
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Ensure uploads directory exists
const UPLOADS_DIR = path.join(__dirname, '..', 'uploads');
fs.mkdir(UPLOADS_DIR, { recursive: true }).catch(console.error);

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, UPLOADS_DIR);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  }
});

const upload = multer({ 
  storage,
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'application/pdf') {
      cb(null, true);
    } else {
      cb(new Error('Only PDF files are allowed'), false);
    }
  },
  limits: { fileSize: 50 * 1024 * 1024 } // 50MB limit
});

// Health check
app.get('/api/health', async (req, res) => {
  try {
    // Check if Python API is available
    const response = await axios.get(`${PYTHON_API_URL}/health`, { timeout: 2000 });
    res.json({ 
      status: 'ok', 
      python_api: 'connected',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.json({ 
      status: 'ok', 
      python_api: 'disconnected',
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// Delete uploaded file - must be before any catch-all routes
app.delete('/api/uploads/:filename', async (req, res) => {
  try {
    const filename = decodeURIComponent(req.params.filename);
    console.log('Delete request received for:', filename);
    console.log('UPLOADS_DIR:', UPLOADS_DIR);
    
    // Try multiple possible paths
    const possiblePaths = [
      path.join(UPLOADS_DIR, filename),
      path.join(__dirname, '..', 'uploads', filename),
      path.resolve(UPLOADS_DIR, filename)
    ];
    
    console.log('Trying paths:', possiblePaths);
    
    let filePath = null;
    for (const testPath of possiblePaths) {
      try {
        await fs.access(testPath);
        filePath = testPath;
        console.log('File found at:', filePath);
        break;
      } catch (err) {
        console.log('Path not found:', testPath, err.message);
        // Continue to next path
      }
    }
    
    if (!filePath) {
      console.error('File not found in any of the paths');
      return res.status(404).json({ error: `File not found: ${filename}. Checked paths: ${possiblePaths.join(', ')}` });
    }

    // Delete the file
    try {
      await fs.unlink(filePath);
      console.log('File deleted successfully:', filePath);
    } catch (unlinkError) {
      console.error('Failed to unlink file:', unlinkError);
      return res.status(500).json({ error: `Failed to delete file: ${unlinkError.message}` });
    }
    
    // Optionally, try to remove from Python API's vector store
    try {
      await axios.delete(`${PYTHON_API_URL}/uploads/${encodeURIComponent(filename)}`, {
        timeout: 2000
      });
      console.log('Python API delete call succeeded');
    } catch (apiError) {
      // Ignore if Python API doesn't support delete or isn't available
      console.log('Python API delete call failed (non-critical):', apiError.message);
    }

    res.json({ message: 'File deleted successfully', filename });
  } catch (error) {
    console.error('Delete error:', error);
    res.status(500).json({ error: error.message || 'Failed to delete file' });
  }
});

// List uploaded files
app.get('/api/uploads', async (req, res) => {
  try {
    const response = await axios.get(`${PYTHON_API_URL}/uploads`);
    res.json(response.data);
  } catch (error) {
    try {
      // Fallback: read from uploads directory
      const files = await fs.readdir(UPLOADS_DIR);
      const fileList = await Promise.all(
        files
          .filter(f => f.endsWith('.pdf'))
          .map(async (filename) => {
            const filePath = path.join(UPLOADS_DIR, filename);
            const stats = await fs.stat(filePath);
            return {
              name: filename,
              path: filePath,
              size: stats.size,
              updated: stats.mtime.getTime() / 1000
            };
          })
      );
      res.json({ files: fileList });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  }
});

// Upload and ingest PDFs
app.post('/api/ingest', upload.array('files', 10), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ error: 'No files uploaded' });
    }

    // Create FormData for Python API
    const FormData = require('form-data');
    const formData = new FormData();
    
    for (const file of req.files) {
      const fileStream = require('fs').createReadStream(file.path);
      formData.append('files', fileStream, {
        filename: file.originalname,
        contentType: 'application/pdf'
      });
    }

    try {
      const response = await axios.post(`${PYTHON_API_URL}/ingest`, formData, {
        headers: formData.getHeaders(),
        maxContentLength: Infinity,
        maxBodyLength: Infinity
      });
      res.json(response.data);
    } catch (apiError) {
      // If Python API fails, return basic success
      res.json({
        ingested: req.files.map(f => ({
          file: f.originalname,
          path: f.path,
          ingested_pages: 'unknown'
        }))
      });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Ask document question
app.post('/api/document/ask', async (req, res) => {
  try {
    const { path: docPath, question } = req.body;
    
    if (!docPath || !question) {
      return res.status(400).json({ error: 'Document path and question are required' });
    }

    const response = await axios.post(`${PYTHON_API_URL}/document/ask`, {
      path: docPath,
      question: question
    });
    
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ 
      error: error.response?.data?.detail || error.message 
    });
  }
});

// Run synthesis
app.post('/api/synthesis', async (req, res) => {
  try {
    const { query } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Query is required' });
    }

    const response = await axios.post(`${PYTHON_API_URL}/synthesis`, { query });
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ 
      error: error.response?.data?.detail || error.message 
    });
  }
});

// Get layman summary
app.post('/api/layman', async (req, res) => {
  try {
    const { path: docPath } = req.body;
    
    if (!docPath) {
      return res.status(400).json({ error: 'Document path is required' });
    }

    const response = await axios.post(`${PYTHON_API_URL}/layman`, { path: docPath });
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ 
      error: error.response?.data?.detail || error.message 
    });
  }
});

// Get related papers
app.post('/api/related-papers', async (req, res) => {
  try {
    const { path: docPath, limit } = req.body;
    
    if (!docPath) {
      return res.status(400).json({ error: 'Document path is required' });
    }

    const response = await axios.post(`${PYTHON_API_URL}/related-papers`, {
      path: docPath,
      limit: limit || 10
    });
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ 
      error: error.response?.data?.detail || error.message 
    });
  }
});

// Search Semantic Scholar
app.post('/api/semantic-scholar/search', async (req, res) => {
  try {
    const { query, limit } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Search query is required' });
    }

    const response = await axios.post(`${PYTHON_API_URL}/semantic-scholar/search`, {
      query,
      limit: limit || 10
    });
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ 
      error: error.response?.data?.detail || error.message 
    });
  }
});

// Serve static files in production
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, '../frontend-react/build')));
  
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend-react/build', 'index.html'));
  });
}

// Log all registered routes for debugging
app._router.stack.forEach((middleware) => {
  if (middleware.route) {
    const methods = Object.keys(middleware.route.methods).join(', ').toUpperCase();
    console.log(`Route registered: ${methods} ${middleware.route.path}`);
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Athena Backend Server running on http://localhost:${PORT}`);
  console.log(`📡 Python API URL: ${PYTHON_API_URL}`);
  console.log('✅ Delete route should be available at: DELETE /api/uploads/:filename');
});

