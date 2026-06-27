const csv = require('csv-parser');
const fs = require('fs');

// 字段名映射：CSV中文/英文列名 → 数据库字段
const FIELD_MAP = {
  // 英文列名
  order_id: 'order_id',
  product_id: 'product_id',
  product_name: 'product_name',
  category: 'category',
  unit_price: 'unit_price',
  quantity: 'quantity',
  total_amount: 'total_amount',
  user_id: 'user_id',
  province: 'province',
  city: 'city',
  order_date: 'order_date',
  order_status: 'order_status',
  // 中文列名
  '订单ID': 'order_id',
  '商品ID': 'product_id',
  '商品名称': 'product_name',
  '品类': 'category',
  '单价': 'unit_price',
  '数量': 'quantity',
  '金额': 'total_amount',
  '用户ID': 'user_id',
  '省份': 'province',
  '城市': 'city',
  '订单日期': 'order_date',
  '订单状态': 'order_status',
};

function normalizeRow(row) {
  const normalized = {};
  for (const [key, value] of Object.entries(row)) {
    const field = FIELD_MAP[key] || FIELD_MAP[key.toLowerCase()] || key.toLowerCase();
    normalized[field] = (value || '').trim();
  }
  if (!normalized.order_status) normalized.order_status = 'completed';
  if (!normalized.city) normalized.city = '';
  return normalized;
}

function parseCSV(filePath) {
  return new Promise((resolve, reject) => {
    const rows = [];
    fs.createReadStream(filePath)
      .pipe(csv())
      .on('data', (row) => rows.push(normalizeRow(row)))
      .on('end', () => resolve(rows))
      .on('error', (err) => reject(err));
  });
}

module.exports = { parseCSV, FIELD_MAP };
