const express = require('express');
const crypto = require('crypto');
const helmet = require('helmet');
const app = express();
const port = 6969;
const PARTNER_KEY = process.env.PARTNER_KEY;

app.use(express.json({ limit: '128kb' }));
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      connectSrc: ["'self'", '*']
    }
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: false
  }
}));
app.enable('trust proxy');

const REQUIRED_FIELDS = [
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
  'telco'
];
const VALID_STATUSES = new Set(['1', '2', '3', '99']);

const verifyCallbackSignature = body => crypto
  .createHash('md5')
  .update(PARTNER_KEY + (body.code || '') + (body.serial || ''))
  .digest('hex') === body.callback_sign;

const validateRequest = body => {
  if (!body || typeof body !== 'object') return { status: 400, message: 'Invalid JSON payload' };
  const missingField = REQUIRED_FIELDS.find(field => body[field] === undefined || body[field] === null);
  if (missingField) return { status: 400, message: `Missing required field: ${missingField}` };
  if (!VALID_STATUSES.has(body.status)) return { status: 400, message: `Invalid status: must be one of ${[...VALID_STATUSES]}` };
  if (!PARTNER_KEY || !verifyCallbackSignature(body)) return { status: 401, message: 'Invalid callback signature' };
  return null;
};

const processCallbackData = body => ({
  status: body.status,
  message: body.message,
  request_id: body.request_id,
  trans_id: body.trans_id,
  declared_value: Number(body.declared_value) || 0,
  value: Number(body.value) || 0,
  amount: Number(body.amount) || 0,
  code: body.code,
  serial: body.serial,
  telco: body.telco
});

app.post('/callback', async (req, res, next) => {
  try {
    const error = validateRequest(req.body);
    if (error) return res.status(error.status).json({ status: 'error', message: error.message });

    const responseData = processCallbackData(req.body);
    res.json({
      status: 'success',
      message: 'Callback processed',
      data: responseData
    });
  } catch (error) {
    next(error);
  }
});

app.use((err, req, res) => res.status(500).json({ status: 'error', message: 'Internal server error' }));

app.listen(port, () => console.log(`Callback server running on port ${port}`));
