class ResponseUtil {
  static success(data = null, message = 'success') {
    return { code: 200, message, data };
  }

  static created(data = null, message = 'created') {
    return { code: 201, message, data };
  }

  static fail(code = 400, message = 'fail', data = null) {
    return { code, message, data };
  }

  static paginate(rows, total, page, pageSize) {
    return {
      code: 200,
      message: 'success',
      data: {
        list: rows,
        pagination: {
          total,
          page,
          pageSize,
          totalPages: Math.ceil(total / pageSize),
        },
      },
    };
  }
}

module.exports = ResponseUtil;
