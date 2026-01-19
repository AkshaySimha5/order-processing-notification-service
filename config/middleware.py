import uuid
import time
import logging

logger = logging.getLogger(__name__)


class RequestIdMiddleware:
    """
    Middleware that:
    1. Generates a unique request ID (or reuses X-Request-ID header if provided)
    2. Attaches request ID to the request object
    3. Logs request details (method, path, user, request_id)
    4. Logs response details (status code, duration, request_id)
    5. Adds X-Request-ID header to the response
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate or reuse request ID from incoming header
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.request_id = request_id

        # Start timer for duration calculation
        start_time = time.time()

        # Log incoming request
        logger.info(
            "[REQUEST] %s %s | request_id=%s",
            request.method,
            request.path,
            request_id,
        )

        response = self.get_response(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Get user info (available after AuthenticationMiddleware)
        user = getattr(request, 'user', None)
        user_info = 'anonymous'
        if user and getattr(user, 'is_authenticated', False):
            user_info = f"user_id={user.id}"

        # Log response
        logger.info(
            "[RESPONSE] %s %s | status=%s | duration=%.2fms | %s | request_id=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            user_info,
            request_id,
        )

        # Attach request ID to response header
        response['X-Request-ID'] = request_id

        return response
