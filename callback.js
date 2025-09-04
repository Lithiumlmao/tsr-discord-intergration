// Ts is made by Grok AI cuz i'm dumb and lazy
const express = require('express');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const app = express();
const port = 3000;

// Configuration
const PARTNER_KEY = process.env.PARTNER_KEY; // Load from environment variable
const LOG_FILE = path.join(__dirname, 'logs', 'transactions.log');

// Ensure log directory exists
fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });

// Middleware to parse JSON bodies
app.use(express.json());

// POST endpoint for callback
app.post('/callback', (req, res) => {
  // Validate required fields
  const requiredFields = [
    'callback_sign',
    'status',
    'message',
    'request_id',
    'trans_id',
    'declared_value',
    'value',
    'amount',
    'code',
    'serial',
    'telco',
  ];

  for (const field of requiredFields) {
    if (!req.body[field]) {
      return res.status(400).json({ status: 'error', message: `Missing required field: ${field}` });
    }
  }

  // Validate status
  const validStatuses = ['1', '2', '3', '99'];
  if (!validStatuses.includes(req.body.status)) {
    return res.status(400).json({ status: 'error', message: `Invalid status: must be one of ${validStatuses}` });
  }

  // Verify callback signature
  const calculatedSign = crypto
    .createHash('sha256') // Use SHA-256 instead of MD5 for security
    .update(PARTNER_KEY + req.body.code + req.body.serial)
    .digest('hex');

  if (req.body.callback_sign !== calculatedSign) {
    return res.status(401).json({ status: 'error', message: 'Invalid callback signature' });
  }

  // Log request data (for debugging, remove in production)
  const logEntry = `${req.body.status}|${req.body.message}|${new Date().toISOString()}\n`;
  fs.appendFileSync(LOG_FILE, logEntry, { encoding: 'utf8' });

  // Process the data
  const responseData = {
    status: req.body.status, // 1: valid card, 2: invalid card, 3: unusable card, 99: pending
    message: req.body.message,
    request_id: req.body.request_id, // Your transaction ID
    trans_id: req.body.trans_id, // Third-party transaction ID
    declared_value: req.body.declared_value, // Declared card value
    value: req.body.value, // Actual card value
    amount: req.body.amount, // Amount received (VND)
    code: req.body.code, // Card code
    serial: req.body.serial, // Card serial
    telco: req.body.telco, // Network provider
  };

  // TODO: Save responseData to a database or process further (e.g., update user balance)

  // Return success response
  res.json({ status: 'success', message: 'Callback processed', data: responseData });
});

// Start the server
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});mb
