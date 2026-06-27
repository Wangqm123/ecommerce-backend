const router = require('express').Router();
const ctrl = require('../controllers/region.controller');

router.get('/analysis', ctrl.getAnalysis);
router.get('/detail/:province', ctrl.getProvinceDetail);

module.exports = router;
