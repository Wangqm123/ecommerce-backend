require('dotenv').config();

const app = require('./app');
const { initDatabase } = require('./config/db');

const PORT = process.env.PORT || 3000;

// 先初始化数据库表，再启动服务器
initDatabase().then(() => {
  app.listen(PORT, () => {
    console.log(`🚀 Server running on http://localhost:${PORT}`);
    console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
  });
}).catch(err => {
  console.error('❌ Fatal error during database init:', err);
  process.exit(1);
});