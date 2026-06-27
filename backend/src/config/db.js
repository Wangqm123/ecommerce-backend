const mysql = require('mysql2/promise');

let poolConfig = {};

if (process.env.DATABASE_URL) {
  // 如果使用 Railway 提供的 DATABASE_URL（MySQL 格式：mysql://user:pass@host:port/db）
  poolConfig = {
    uri: process.env.DATABASE_URL,
    connectionLimit: parseInt(process.env.DB_CONNECTION_LIMIT) || 10,
    charset: 'utf8mb4',
    timezone: '+08:00',
    dateStrings: true,
    waitForConnections: true,
    queueLimit: 0,
  };
} else {
  // 本地开发环境，使用独立的环境变量
  poolConfig = {
    host: process.env.DB_HOST || '127.0.0.1',
    port: parseInt(process.env.DB_PORT) || 3306,
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'ecommerce_analysis',
    connectionLimit: parseInt(process.env.DB_CONNECTION_LIMIT) || 10,
    charset: 'utf8mb4',
    timezone: '+08:00',
    dateStrings: true,
    waitForConnections: true,
    queueLimit: 0,
  };
}

const pool = mysql.createPool(poolConfig);

module.exports = pool;