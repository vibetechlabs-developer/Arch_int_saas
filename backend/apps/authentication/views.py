from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.serializers import (
    AuthResponseSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutResponseSerializer,
    LogoutSerializer,
    MessageResponseSerializer,
    ResetPasswordSerializer,
    TokenRefreshResponseSerializer,
    TokenRefreshSerializer,
)
from apps.authentication.services import AuthenticationService
from apps.common.responses import ApiResponse
from apps.users.serializers import UserSerializer


class LoginView(APIView):
    """
    Company User Login endpoint.
    Authenticates with email and password, returning JWT access and refresh tokens.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Company User Login",
        description="Authenticate a company user with email and password.",
        request=LoginSerializer,
        responses={
            status.HTTP_200_OK: AuthResponseSerializer,
        },
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthenticationService.login_company_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        user_data = UserSerializer(result["user"]).data
        response_data = {
            "accessToken": result["accessToken"],
            "refreshToken": result["refreshToken"],
            "user": user_data,
        }
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=response_data, request_id=request_id)


class PlatformLoginView(APIView):
    """
    Platform Super Admin Login endpoint.
    Authenticates platform administrators with email and password.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Platform Super Admin Login",
        description="Authenticate a platform super admin with email and password.",
        request=LoginSerializer,
        responses={
            status.HTTP_200_OK: AuthResponseSerializer,
        },
        tags=["Platform Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthenticationService.login_platform_admin(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        user_data = UserSerializer(result["user"]).data
        response_data = {
            "accessToken": result["accessToken"],
            "refreshToken": result["refreshToken"],
            "user": user_data,
        }
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=response_data, request_id=request_id)


class TokenRefreshView(APIView):
    """
    Token Refresh endpoint.
    Exchanges a valid refresh token for a new access token and rotated refresh token.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh Access Token",
        description="Exchange a refresh token for new access and rotated refresh tokens.",
        request=TokenRefreshSerializer,
        responses={
            status.HTTP_200_OK: TokenRefreshResponseSerializer,
        },
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthenticationService.refresh_token(
            refresh_token_str=serializer.validated_data["refreshToken"],
        )

        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=result, request_id=request_id)


class LogoutView(APIView):
    """
    Logout endpoint.
    Revokes / blacklists the provided refresh token.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="User Logout",
        description="Invalidate/blacklist the current session refresh token.",
        request=LogoutSerializer,
        responses={
            status.HTTP_200_OK: LogoutResponseSerializer,
        },
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthenticationService.logout(
            refresh_token_str=serializer.validated_data["refreshToken"],
        )

        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(
            data={"message": "Logged out successfully."},
            request_id=request_id,
        )


class MeView(APIView):
    """
    Current Authenticated User Identity endpoint.
    Returns the serialized user profile for the current access token.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Current User Identity",
        description="Retrieve the authenticated user identity.",
        responses={
            status.HTTP_200_OK: UserSerializer,
        },
        tags=["Authentication"],
    )
    def get(self, request: Request) -> Response:
        user_data = UserSerializer(request.user).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=user_data, request_id=request_id)


class ForgotPasswordView(APIView):
    """
    Forgot Password endpoint.
    Initiates the password reset workflow without revealing email existence.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Forgot Password",
        description="Trigger password reset email if account exists.",
        request=ForgotPasswordSerializer,
        responses={
            status.HTTP_200_OK: MessageResponseSerializer,
        },
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = AuthenticationService.request_password_reset(
            email=serializer.validated_data["email"],
        )

        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(
            data={"message": message},
            request_id=request_id,
        )


class ResetPasswordView(APIView):
    """
    Reset Password endpoint.
    Resets user password using a valid, unexpired, unconsumed reset token.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Reset Password",
        description="Complete password reset with secure token.",
        request=ResetPasswordSerializer,
        responses={
            status.HTTP_200_OK: MessageResponseSerializer,
        },
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = AuthenticationService.reset_password(
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["newPassword"],
        )

        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(
            data={"message": message},
            request_id=request_id,
        )

