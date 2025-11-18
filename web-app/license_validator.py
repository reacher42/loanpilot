#!/usr/bin/env python3
"""
License Validation Module
Provides time-limited access control with HMAC-signed tokens
"""

import os
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Secret key for HMAC signature - embedded in code
# In production, this would be unique per build or customer
SECRET_KEY = b"loanpilot-2024-secure-key-change-per-customer"


class LicenseValidator:
    """Validates time-limited licenses with HMAC signatures"""

    def __init__(self, license_token: Optional[str] = None, secret_key: bytes = SECRET_KEY):
        """
        Initialize license validator

        Args:
            license_token: License token in format "YYYY-MM-DD:signature"
            secret_key: Secret key for HMAC verification
        """
        self.secret_key = secret_key
        self.license_token = license_token or os.getenv('LICENSE_TOKEN', '')

        # Fallback to simple expiry date if no token
        if not self.license_token:
            self.license_expiry = os.getenv('LICENSE_EXPIRY', '')
        else:
            self.license_expiry = None

    def generate_license_token(self, expiry_date: str, customer_id: str = "") -> str:
        """
        Generate signed license token

        Args:
            expiry_date: Expiry date in YYYY-MM-DD format
            customer_id: Optional customer identifier

        Returns:
            Signed token in format "YYYY-MM-DD:customer:signature"
        """
        message = f"{expiry_date}:{customer_id}".encode()
        signature = hmac.new(
            self.secret_key,
            message,
            hashlib.sha256
        ).hexdigest()[:16]

        if customer_id:
            return f"{expiry_date}:{customer_id}:{signature}"
        return f"{expiry_date}:{signature}"

    def verify_license_token(self) -> Tuple[bool, str, Optional[datetime]]:
        """
        Verify signed license token

        Returns:
            Tuple of (is_valid, message, expiry_date)
        """
        if not self.license_token:
            return self._verify_simple_expiry()

        try:
            parts = self.license_token.split(':')

            if len(parts) == 2:
                date_str, signature = parts
                customer_id = ""
            elif len(parts) == 3:
                date_str, customer_id, signature = parts
            else:
                return False, "Invalid license token format", None

            # Parse expiry date
            try:
                expiry_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return False, f"Invalid date format in license: {date_str}", None

            # Verify signature
            message = f"{date_str}:{customer_id}".encode()
            expected_sig = hmac.new(
                self.secret_key,
                message,
                hashlib.sha256
            ).hexdigest()[:16]

            if signature != expected_sig:
                logger.error("License signature verification failed")
                return False, "Invalid license signature - license may be tampered", None

            # Check expiry
            now = datetime.now()
            if now > expiry_date:
                days_expired = (now - expiry_date).days
                return False, f"License expired {days_expired} days ago on {date_str}", expiry_date

            days_remaining = (expiry_date - now).days

            # Warning if expiring soon
            if days_remaining <= 30:
                customer_msg = f" (Customer: {customer_id})" if customer_id else ""
                return True, f"⚠️  License expires in {days_remaining} days{customer_msg}", expiry_date

            customer_msg = f" for {customer_id}" if customer_id else ""
            return True, f"License valid until {date_str}{customer_msg}", expiry_date

        except Exception as e:
            logger.error(f"License validation error: {e}")
            return False, f"License validation failed: {str(e)}", None

    def _verify_simple_expiry(self) -> Tuple[bool, str, Optional[datetime]]:
        """
        Fallback to simple expiry date check (no signature)
        Less secure but backwards compatible
        """
        if not self.license_expiry:
            return False, "No license configuration found (LICENSE_TOKEN or LICENSE_EXPIRY required)", None

        try:
            expiry_date = datetime.strptime(self.license_expiry, '%Y-%m-%d')
            now = datetime.now()

            if now > expiry_date:
                days_expired = (now - expiry_date).days
                return False, f"License expired {days_expired} days ago on {self.license_expiry}", expiry_date

            days_remaining = (expiry_date - now).days

            if days_remaining <= 30:
                return True, f"⚠️  License expires in {days_remaining} days", expiry_date

            return True, f"License valid until {self.license_expiry}", expiry_date

        except ValueError:
            return False, f"Invalid date format in LICENSE_EXPIRY: {self.license_expiry}", None
        except Exception as e:
            return False, f"License validation error: {str(e)}", None

    def check_license(self) -> Tuple[bool, str]:
        """
        Main license check method

        Returns:
            Tuple of (is_valid, message)
        """
        is_valid, message, expiry_date = self.verify_license_token()
        return is_valid, message

    def get_expiry_info(self) -> dict:
        """
        Get detailed license information

        Returns:
            Dictionary with license details
        """
        is_valid, message, expiry_date = self.verify_license_token()

        info = {
            "is_valid": is_valid,
            "message": message,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
        }

        if expiry_date:
            now = datetime.now()
            if expiry_date > now:
                info["days_remaining"] = (expiry_date - now).days
                info["expires_soon"] = info["days_remaining"] <= 30
            else:
                info["days_expired"] = (now - expiry_date).days

        return info


# Global validator instance
_global_validator = None


def get_license_validator() -> LicenseValidator:
    """Get or create global license validator instance"""
    global _global_validator
    if _global_validator is None:
        _global_validator = LicenseValidator()
    return _global_validator


def check_license() -> Tuple[bool, str]:
    """
    Convenience function for license checking

    Returns:
        Tuple of (is_valid, message)
    """
    validator = get_license_validator()
    return validator.check_license()


# Friendly error messages for customers
LICENSE_EXPIRED_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LoanPilot - License Expired</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}
        .container {{
            background: white;
            padding: 50px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }}
        h1 {{
            color: #dc2626;
            margin-bottom: 20px;
        }}
        .icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        .message {{
            color: #4b5563;
            font-size: 18px;
            margin-bottom: 30px;
            line-height: 1.6;
        }}
        .contact {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
        }}
        .contact h3 {{
            margin-top: 0;
            color: #1f2937;
        }}
        .contact-info {{
            color: #4b5563;
            margin: 10px 0;
        }}
        a {{
            color: #667eea;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🔒</div>
        <h1>License Expired</h1>
        <div class="message">
            {message}
            <br><br>
            To continue using LoanPilot, please renew your license.
            License renewal typically takes 1-2 business days.
        </div>
        <div class="contact">
            <h3>Contact Support</h3>
            <div class="contact-info">
                📧 Email: <a href="mailto:support@loanpilot.com">support@loanpilot.com</a>
            </div>
            <div class="contact-info">
                📞 Phone: 1-800-LOAN-PILOT
            </div>
        </div>
    </div>
</body>
</html>
"""


def get_license_expired_html(message: str) -> str:
    """Get HTML page for license expiry"""
    return LICENSE_EXPIRED_HTML.format(message=message)


if __name__ == "__main__":
    # Test license generation and validation
    logging.basicConfig(level=logging.INFO)

    validator = LicenseValidator()

    # Generate test token
    test_token = validator.generate_license_token("2025-12-31", "ACME-Corp")
    print(f"Generated token: {test_token}")

    # Test validation
    validator.license_token = test_token
    is_valid, message = validator.check_license()
    print(f"Validation result: {is_valid}")
    print(f"Message: {message}")

    # Get detailed info
    info = validator.get_expiry_info()
    print(f"License info: {info}")
