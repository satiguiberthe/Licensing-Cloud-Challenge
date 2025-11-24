from rest_framework.response import Response
from rest_framework import status


class ResponseWrapper:
    """
    Wrapper for standardizing API responses across the application.

    All responses follow the format:
    {
        "data": <response_data>,
        "message": <optional_message>,
        "status": <http_status_code>
    }
    """

    @staticmethod
    def success(data=None, message=None, status_code=status.HTTP_200_OK):
        """
        Create a standardized success response.

        Args:
            data: The response data
            message: Optional success message
            status_code: HTTP status code (default: 200)

        Returns:
            Response object with wrapped data
        """
        response_data = {
            'data': data,
            'status': status_code
        }

        if message:
            response_data['message'] = message

        return Response(response_data, status=status_code)

    @staticmethod
    def created(data=None, message=None):
        """
        Create a standardized 201 Created response.

        Args:
            data: The created resource data
            message: Optional message

        Returns:
            Response object with wrapped data
        """
        return ResponseWrapper.success(
            data=data,
            message=message or 'Resource created successfully',
            status_code=status.HTTP_201_CREATED
        )

    @staticmethod
    def error(message, data=None, status_code=status.HTTP_400_BAD_REQUEST):
        """
        Create a standardized error response.

        Args:
            message: Error message
            data: Optional additional error data
            status_code: HTTP status code

        Returns:
            Response object with wrapped error
        """
        response_data = {
            'data': data,
            'message': message,
            'status': status_code
        }

        return Response(response_data, status=status_code)

    @staticmethod
    def not_found(message="Resource not found", data=None):
        """
        Create a standardized 404 Not Found response.

        Args:
            message: Error message
            data: Optional additional data

        Returns:
            Response object with wrapped error
        """
        return ResponseWrapper.error(
            message=message,
            data=data,
            status_code=status.HTTP_404_NOT_FOUND
        )

    @staticmethod
    def forbidden(message="Forbidden", data=None):
        """
        Create a standardized 403 Forbidden response.

        Args:
            message: Error message
            data: Optional additional data

        Returns:
            Response object with wrapped error
        """
        return ResponseWrapper.error(
            message=message,
            data=data,
            status_code=status.HTTP_403_FORBIDDEN
        )

    @staticmethod
    def unauthorized(message="Unauthorized", data=None):
        """
        Create a standardized 401 Unauthorized response.

        Args:
            message: Error message
            data: Optional additional data

        Returns:
            Response object with wrapped error
        """
        return ResponseWrapper.error(
            message=message,
            data=data,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    @staticmethod
    def too_many_requests(message="Too many requests", data=None):
        """
        Create a standardized 429 Too Many Requests response.

        Args:
            message: Error message
            data: Optional additional data

        Returns:
            Response object with wrapped error
        """
        return ResponseWrapper.error(
            message=message,
            data=data,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )
