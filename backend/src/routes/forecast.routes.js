const router = require('express').Router();
const ctrl = require('../controllers/forecast.controller');

router.post('/trigger', ctrl.trigger);
router.get('/status/:batchUuid', ctrl.getStatus);
router.get('/result', ctrl.getResult);

module.exports = router;
