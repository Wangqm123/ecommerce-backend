const mysql = require('mysql2/promise');
const fs = require('fs');
const path = require('path');

let poolConfig = {};

// 从环境变量获取数据库连接信息（优先使用 MYSQL_URL）
const dbUrl = process.env.MYSQL_URL || process.env.DATABASE_URL;

if (dbUrl) {
  // 手动解析 URL，避免 mysql2 的 uri 参数可能的问题
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
    // 如果解析失败，回退到独立变量
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
  // 没有 URL，使用独立变量
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

// 验证 pool 是否有效
console.log('✅ MySQL connection pool created successfully.');
console.log('🔍 Pool has execute method?', typeof pool.execute === 'function');

/**
 * 初始化数据库表结构（如果表不存在则自动创建）
 */
async function initDatabase() {
  try {
    const schemaPath = path.join(__dirname, '../sql/schema.sql');
    const schemaSQL = fs.readFileSync(schemaPath, 'utf8');
    // 分割 SQL 语句（按 ; 分割，但需避免分割字符串中的 ;）
    const statements = schemaSQL.split(';').filter(stmt => stmt.trim().length > 0);
    for (const stmt of statements) {
      await pool.execute(stmt);
    }
    console.log('✅ Database schema initialized successfully.');
  } catch (err) {
    console.error('❌ Failed to initialize database schema:', err.message);
    // 不抛出错误，让应用继续启动（可能已有表）
  }
}

module.exports = { pool, initDatabase };