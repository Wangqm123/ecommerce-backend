const router = require('express').Router();
const upload = require('../middleware/upload');
const ctrl = require('../controllers/upload.controller');

router.post('/csv', upload.single('file'), ctrl.uploadCSV);
router.get('/history', ctrl.getHistory);
router.get('/history/:batchId', ctrl.getBatchDetail);

module.exports = router;
