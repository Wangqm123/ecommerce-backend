const mysql = require('mysql2/promise');
const fs = require('fs');
const path = require('path');

let poolConfig = {};

// 从环境变量获取数据库连接信息（优先使用 MYSQL_URL）
const dbUrl = process.env.MYSQL_URL || process.env.DATABASE_URL;

if (dbUrl) {
  try {
    const url = new URL(dbUrl);
    poolConfig = {
      host: url.hostname,
      port: parseInt(url.port) || 3306,
      user: url.username,
      password: decodeURIComponent(url.password || ''),
      database: url.pathname.replace(/^\//, ''),
      connectionLimit: parseInt(process.env.DB_CONNECTION_LIMIT) || 10,
      charset: 'utf8mb4',
      timezone: '+08:00',
      dateStrings: true,
      waitForConnections: true,
      queueLimit: 0,
    };
    console.log('✅ Parsed database config from MYSQL_URL');
  } catch (err) {
    console.error('❌ Failed to parse MYSQL_URL:', err.message);
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
    console.log('⚠️  Using fallback DB config from individual env vars');
  }
} else {
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
  console.log('ℹ️  Using DB config from individual env vars');
}

const pool = mysql.createPool(poolConfig);

console.log('✅ MySQL connection pool created successfully.');
console.log('🔍 Pool has query method?', typeof pool.query === 'function');

/**
 * 初始化数据库表结构
 */
async function initDatabase() {
  try {
    const schemaPath = path.join(__dirname, '../sql/schema.sql');
    const schemaSQL = fs.readFileSync(schemaPath, 'utf8');
    const statements = schemaSQL.split(';').filter(stmt => stmt.trim().length > 0);
    for (const stmt of statements) {
      await pool.query(stmt); // 改用 query
    }
    console.log('✅ Database schema initialized successfully.');
  } catch (err) {
    console.error('❌ Failed to initialize database schema:', err.message);
  }
}

// 直接导出连接池，并附加 initDatabase
module.exports = pool;
module.exports.initDatabase = initDatabase;