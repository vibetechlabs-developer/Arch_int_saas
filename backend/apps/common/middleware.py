import re
import uuid
from typing import Callable
from django.http import HttpRequest, HttpResponse

# Valid request ID format: req_<12 hexadecimal characters>
REQUEST_ID_REGEX = re.compile(r"^req_[0-9a-fA-F]{12}$")


def generate_request_id() -> str:
    """
    Generate a secure request ID formatted as req_<12 hex chars>.
    """
    return f"req_{uuid.uuid4().hex[:12]}"


def is_valid_request_id(request_id: str) -> bool:
    """
    Validate incoming request ID format against req_<12 hex chars>.
    """
    if not isinstance(request_id, str):
        return False
    return bool(REQUEST_ID_REGEX.match(request_id.strip()))


class RequestIDMiddleware:
    """
    Middleware that ensures every request has a validated or newly generated
    request_id attached to request.request_id and exposed as X-Request-ID response header.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming_id = request.headers.get("X-Request-ID") or request.META.get("HTTP_X_REQUEST_ID")

        if incoming_id and is_valid_request_id(incoming_id):
            request_id = incoming_id.strip()
        else:
            request_id = generate_request_id()

        # Attach request_id to request object
        request.request_id = request_id

        # Process request
        response = self.get_response(request)

        # Set X-Request-ID header on response
        response["X-Request-ID"] = request_id

        return response
