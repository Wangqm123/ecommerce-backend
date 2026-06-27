const router = require('express').Router();
const ctrl = require('../controllers/category.controller');

router.get('/analysis', ctrl.getAnalysis);
router.get('/trend', ctrl.getTrend);

module.exports = router;
