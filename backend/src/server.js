require('dotenv').config();

const app = require('./app');
const pool = require('./config/db');
const { initDatabase } = pool; // 或者 const initDatabase = require('./config/db').initDatabase;

const PORT = process.env.PORT || 3000;

process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

initDatabase()
  .then(() => {
    const server = app.listen(PORT, '0.0.0.0', () => {
      console.log(`🚀 Server running on http://0.0.0.0:${PORT}`);
      console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
    });

    process.on('SIGTERM', () => {
      console.log('Received SIGTERM, closing server...');
      server.close(() => {
        console.log('Server closed.');
        process.exit(0);
      });
    });
  })
  .catch(err => {
    console.error('❌ Fatal error during database init:', err);
    process.exit(1);
  });