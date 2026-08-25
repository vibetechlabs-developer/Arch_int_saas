from rest_framework import serializers

from apps.users.serializers import UserSerializer


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login credentials.
    """

    email = serializers.EmailField(
        required=True,
        help_text="User's registered email address.",
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="User's plaintext password.",
    )

    def validate_email(self, value: str) -> str:
        """
        Normalize email to lowercase and stripped whitespace.
        """
        return value.strip().lower()


class TokenRefreshSerializer(serializers.Serializer):
    """
    Serializer for exchanging a refresh token for new access and refresh tokens.
    """

    refreshToken = serializers.CharField(
        required=True,
        help_text="The valid JWT refresh token string.",
    )


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for invalidating/blacklisting a refresh token on logout.
    """

    refreshToken = serializers.CharField(
        required=True,
        help_text="The refresh token to be revoked/blacklisted.",
    )


class AuthResponseSerializer(serializers.Serializer):
    """
    Response serializer for successful authentication endpoints.
    """

    accessToken = serializers.CharField()
    refreshToken = serializers.CharField()
    user = UserSerializer(required=False)


class TokenRefreshResponseSerializer(serializers.Serializer):
    """
    Response serializer for token refresh endpoint.
    """

    accessToken = serializers.CharField()
    refreshToken = serializers.CharField()


class LogoutResponseSerializer(serializers.Serializer):
    """
    Response serializer for logout endpoint.
    """

    message = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset email.
    """

    email = serializers.EmailField(
        required=True,
        help_text="User's registered email address.",
    )

    def validate_email(self, value: str) -> str:
        """
        Normalize email to lowercase and stripped whitespace.
        """
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for resetting password using a secure reset token.
    """

    token = serializers.CharField(
        required=True,
        write_only=True,
        help_text="Cryptographically secure password reset token.",
    )
    newPassword = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="The new password meeting complexity requirements.",
    )


class MessageResponseSerializer(serializers.Serializer):
    """
    Standard message response serializer.
    """

    message = serializers.CharField()

