const express = require('express');
const crypto = require('crypto');
const app = express();
const port = 6969;


const PARTNER_KEY = process.env.PARTNER_KEY;


// Middleware
app.use(express.json());
app.enable('trust proxy');

// Danh sách các trường bắt buộc và trạng thái hợp lệ
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
  'telco',
];
const VALID_STATUSES = ['1', '2', '3', '99'];

// Hàm kiểm tra chữ ký callback
const verifyCallbackSignature = (body) => {
  const calculatedSign = crypto
    .createHash('md5')
    .update(PARTNER_KEY + body.code + body.serial)
    .digest('hex');
  return calculatedSign === body.callback_sign;
};

// Hàm kiểm tra các trường bắt buộc
const validateRequiredFields = (body) => {
  const missingField = REQUIRED_FIELDS.find((field) => !body[field]);
  return { isValid: !missingField, missingField };
};

// Hàm xử lý dữ liệu callback
const processCallbackData = (body) => ({
  status: body.status,
  message: body.message,
  request_id: body.request_id,
  trans_id: body.trans_id,
  declared_value: body.declared_value,
  value: body.value,
  amount: body.amount,
  code: body.code,
  serial: body.serial,
  telco: body.telco,
});

// Endpoint callback
app.post('/callback', (req, res, next) => {
  try {
    const { body } = req;

    // Kiểm tra các trường bắt buộc
    const { isValid, missingField } = validateRequiredFields(body);
    if (!isValid) {
      console.log(`Missing required field: ${missingField}`);
      return res.status(400).json({
        status: 'error',
        message: `Missing required field: ${missingField}`,
      });
    }

    // Kiểm tra trạng thái hợp lệ
    if (!VALID_STATUSES.includes(body.status)) {
      console.log(`Invalid status: ${body.status}`);
      return res.status(400).json({
        status: 'error',
        message: `Invalid status: must be one of ${VALID_STATUSES}`,
      });
    }

    // Xác minh chữ ký
    if (!verifyCallbackSignature(body)) {
      console.log('Invalid callback signature');
      return res.status(401).json({
        status: 'error',
        message: 'Invalid callback signature',
      });
    }

    // Xử lý dữ liệu
    const responseData = processCallbackData(body);

    // Ghi log thông tin callback
    console.log('Callback processed:', responseData);

    // TODO: Lưu responseData vào database hoặc xử lý thêm (ví dụ: cập nhật số dư người dùng)

    // Trả về phản hồi thành công
    res.json({
      status: 'success',
      message: 'Callback processed',
      data: responseData,
    });
  } catch (error) {
    next(error);
  }
});

// Middleware xử lý lỗi
app.use((err, req, res, next) => {
  console.error('Server error:', err.message);
  res.status(500).json({
    status: 'error',
    message: 'Internal server error',
  });
});

// Khởi động server
app.listen(port, () => {
  console.log(`Callback server running on port ${port}`);
});
