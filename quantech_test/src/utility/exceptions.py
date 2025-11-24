from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats all API responses consistently.

    Format:
    {
        "data": <response_data>,
        "message": <message>,
        "status": <status_code>
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Format error response
        custom_response_data = {
            'data': None,
            'message': str(exc) if hasattr(exc, 'detail') else 'An error occurred',
            'status': response.status_code
        }

        # If there's detail in the exception, use it
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                custom_response_data['data'] = exc.detail
            else:
                custom_response_data['message'] = str(exc.detail)

        response.data = custom_response_data

    return response


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    """
    Helper function to create consistent success responses.

    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code

    Returns:
        Response object with formatted data
    """
    return Response({
        'data': data,
        'message': message,
        'status': status_code
    }, status=status_code)


def error_response(message="Error", data=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Helper function to create consistent error responses.

    Args:
        message: Error message
        data: Additional error data
        status_code: HTTP status code

    Returns:
        Response object with formatted error
    """
    return Response({
        'data': data,
        'message': message,
        'status': status_code
    }, status=status_code)
