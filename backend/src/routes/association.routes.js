const router = require('express').Router();
const ctrl = require('../controllers/association.controller');

router.post('/trigger', ctrl.trigger);
router.get('/status/:batchUuid', ctrl.getStatus);
router.get('/result', ctrl.getResult);
router.get('/recommend/:productId', ctrl.recommend);

module.exports = router;
