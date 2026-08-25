from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


class CompanyUserAccessToken(AccessToken):
    """
    Access token issued to regular company users.
    Carries token_type: company_user.
    """
    token_type = "company_user"


class PlatformAdminAccessToken(AccessToken):
    """
    Access token issued exclusively to Platform Super Admins.
    Carries token_type: platform_admin.
    """
    token_type = "platform_admin"


class CompanyUserRefreshToken(RefreshToken):
    """
    Refresh token for company users that generates CompanyUserAccessToken.
    """
    access_token_class = CompanyUserAccessToken

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token["email"] = user.email
        token["user_type"] = "company_user"
        token.access_token["email"] = user.email
        token.access_token["user_type"] = "company_user"
        return token


class PlatformAdminRefreshToken(RefreshToken):
    """
    Refresh token for platform super admins that generates PlatformAdminAccessToken.
    """
    access_token_class = PlatformAdminAccessToken

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token["email"] = user.email
        token["user_type"] = "platform_admin"
        token.access_token["email"] = user.email
        token.access_token["user_type"] = "platform_admin"
        return token
