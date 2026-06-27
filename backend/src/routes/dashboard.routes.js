const router = require('express').Router();
const ctrl = require('../controllers/dashboard.controller');

router.get('/kpis', ctrl.getKPIs);
router.get('/trend', ctrl.getTrend);

module.exports = router;
