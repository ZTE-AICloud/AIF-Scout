# Copyright 2025 ZTE Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist, ValidationError, BadRequest, PermissionDenied, RequestAborted

logger = logging.getLogger(__name__)


def handle_exceptions(custom_message=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            msg = custom_message
            try:
                return view_func(request, *args, **kwargs)
            except ObjectDoesNotExist as e:
                error_msg = f"{msg or 'Resource not found'}: {e}"
                logger.error(error_msg)
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_404_NOT_FOUND
                )
            except (ValueError, TypeError, AttributeError) as e:
                error_msg = f"{msg or 'Bad request parameter'}: {e}"
                logger.error(error_msg)
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except ValidationError as e:
                error_msg = f"{msg or 'Request parameter is invalid'}: {e}"
                logger.error(error_msg)
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except PermissionDenied as e:
                error_msg = f"{msg or 'Invalid Permission'}: {e}"
                logger.error(error_msg)
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_403_FORBIDDEN
                )
            except RequestAborted as e:
                error_msg = f"{msg or 'Request is aborted'}: {e}"
                logger.error(error_msg)
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_403_FORBIDDEN
                )
            except BadRequest as e:
                error_msg = f"{msg or 'Bad request'}: {e}"
                logger.error(error_msg)
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                error_msg = f"{msg or 'Internal server error'}: {e}"
                logger.error(error_msg)
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return _wrapped_view
    return decorator
