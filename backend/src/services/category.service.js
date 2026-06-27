const pool = require('../config/db');

async function getAnalysis(startDate, endDate) {
  const params = [];
  let dateFilter = '';
  if (startDate && endDate) {
    dateFilter = 'AND o.order_date BETWEEN ? AND ?';
    params.push(startDate, endDate);
  }

  const [rows] = await pool.execute(
    `SELECT
      p.category,
      SUM(o.quantity)      AS sales_volume,
      SUM(o.total_amount)  AS sales_amount,
      COUNT(DISTINCT o.order_id) AS order_count,
      COUNT(DISTINCT o.product_id) AS product_count
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
    WHERE o.order_status = 'completed' ${dateFilter}
    GROUP BY p.category
    ORDER BY sales_amount DESC`,
    params
  );

  const totalSales = rows.reduce((s, r) => s + parseFloat(r.sales_amount), 0);
  const totalVolume = rows.reduce((s, r) => s + r.sales_volume, 0);

  const categories = rows.map(r => ({
    category: r.category,
    salesAmount: parseFloat(r.sales_amount),
    salesVolume: r.sales_volume,
    orderCount: r.order_count,
    productCount: r.product_count,
    amountPercent: totalSales > 0 ? parseFloat(((parseFloat(r.sales_amount) / totalSales) * 100).toFixed(2)) : 0,
    volumePercent: totalVolume > 0 ? parseFloat(((r.sales_volume / totalVolume) * 100).toFixed(2)) : 0,
  }));

  return { categories, totalSales };
}

async function getTrend(category, startDate, endDate, granularity = 'day') {
  let format;
  switch (granularity) {
    case 'week': format = '%Y-%u'; break;
    case 'month': format = '%Y-%m'; break;
    default: format = '%Y-%m-%d'; break;
  }

  const [rows] = await pool.execute(
    `SELECT
      DATE_FORMAT(o.order_date, ?) AS period,
      SUM(o.total_amount) AS sales_amount,
      SUM(o.quantity)     AS sales_volume
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
    WHERE o.order_status = 'completed' AND p.category = ? AND o.order_date BETWEEN ? AND ?
    GROUP BY period
    ORDER BY period`,
    [format, category, startDate, endDate]
  );

  return {
    category,
    trends: rows.map(r => ({
      period: r.period,
      salesAmount: parseFloat(r.sales_amount),
      salesVolume: r.sales_volume,
    })),
  };
}

module.exports = { getAnalysis, getTrend };
