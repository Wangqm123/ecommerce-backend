// 校验单行 CSV 数据，返回 { valid, reason }
function validateRow(row, index) {
  const rowNum = index + 2; // CSV 行号（第1行是表头）

  if (!row.order_id) return { valid: false, row: rowNum, reason: 'order_id 为空' };
  if (!row.product_id) return { valid: false, row: rowNum, reason: 'product_id 为空' };
  if (!row.user_id) return { valid: false, row: rowNum, reason: 'user_id 为空' };
  if (!row.product_name) return { valid: false, row: rowNum, reason: 'product_name 为空' };
  if (!row.category) return { valid: false, row: rowNum, reason: 'category 为空' };
  if (!row.province) return { valid: false, row: rowNum, reason: 'province 为空' };

  if (isNaN(parseInt(row.product_id))) return { valid: false, row: rowNum, reason: 'product_id 非数字' };
  if (isNaN(parseInt(row.user_id))) return { valid: false, row: rowNum, reason: 'user_id 非数字' };

  const unitPrice = parseFloat(row.unit_price);
  if (isNaN(unitPrice) || unitPrice <= 0) return { valid: false, row: rowNum, reason: 'unit_price 必须为正数' };

  const quantity = parseInt(row.quantity);
  if (isNaN(quantity) || quantity < 1) return { valid: false, row: rowNum, reason: 'quantity 必须为正整数' };

  const totalAmount = parseFloat(row.total_amount);
  if (isNaN(totalAmount) || totalAmount < 0) return { valid: false, row: rowNum, reason: 'total_amount 不能为负数' };

  if (!/^\d{4}-\d{2}-\d{2}$/.test(row.order_date)) return { valid: false, row: rowNum, reason: 'order_date 格式错误，应为 YYYY-MM-DD' };
  const d = new Date(row.order_date);
  if (isNaN(d.getTime())) return { valid: false, row: rowNum, reason: 'order_date 不是合法日期' };

  return { valid: true };
}

// 批量校验，返回 { validRows, errors }
function validateRows(rows) {
  const validRows = [];
  const errors = [];
  for (let i = 0; i < rows.length; i++) {
    const result = validateRow(rows[i], i);
    if (result.valid) {
      validRows.push(rows[i]);
    } else {
      errors.push({ row: result.row, reason: result.reason });
    }
  }
  return { validRows, errors };
}

module.exports = { validateRow, validateRows };
