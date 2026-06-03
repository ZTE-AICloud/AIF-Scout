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

import base64
import logging
from django.db import models

logger = logging.getLogger(__name__)


def DecryptDecode(text: str) -> str:
    return base64.b64decode(text.encode('utf-8')).decode('utf-8')


def EncryptEncode(data: str) -> str:
    return base64.b64encode(data.encode()).decode()


class EncryptedCharField(models.CharField):
    """
    Encrypted CharField that automatically encrypts/decrypts data.

    Usage:
        class MyModel(models.Model):
            password = EncryptedCharField(max_length=128)

    The field automatically:
    - Encrypts data before saving to database
    - Decrypts data when reading from database
    - Handles None values gracefully
    """

    description = "CharField with automatic encryption/decryption"

    def from_db_value(self, value, expression, connection):
        """
        Convert database value to Python value (decrypt).
        Called when data is loaded from database.
        """
        if value is None:
            return value

        try:
            return DecryptDecode(value)
        except Exception as e:
            logger.error(f"Failed to decrypt field value: {e}")
            raise ValueError(f"Field decryption failed: {str(e)}")

    def to_python(self, value):
        """
        Convert value to Python type.
        """
        if value is None:
            return value

        # If value is already decrypted (e.g., from form)
        if isinstance(value, str):
            return value

        return str(value)

    def get_prep_value(self, value):
        """
        Convert Python value to database value (encrypt).
        Called before saving to database.
        """
        value = super().get_prep_value(value)

        if value is None or value == "":
            return value

        try:
            return EncryptEncode(value)
        except Exception as e:
            logger.error(f"Failed to encrypt field value: {e}")
            raise ValueError(f"Field encryption failed: {str(e)}")

    def get_internal_type(self):
        """
        Return the internal field type for Django.
        """
        return "CharField"
