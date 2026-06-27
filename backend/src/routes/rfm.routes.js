const router = require('express').Router();
const ctrl = require('../controllers/rfm.controller');

router.post('/trigger', ctrl.trigger);
router.get('/status/:batchUuid', ctrl.getStatus);
router.get('/result', ctrl.getResult);
router.get('/result/:userId', ctrl.getUserDetail);

module.exports = router;
