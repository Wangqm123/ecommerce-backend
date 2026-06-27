const router = require('express').Router();

router.use('/dashboard', require('./dashboard.routes'));
router.use('/sales', require('./sales.routes'));
router.use('/category', require('./category.routes'));
router.use('/region', require('./region.routes'));
router.use('/upload', require('./upload.routes'));
router.use('/rfm', require('./rfm.routes'));
router.use('/association', require('./association.routes'));
router.use('/forecast', require('./forecast.routes'));

module.exports = router;
