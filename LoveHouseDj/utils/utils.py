from rest_framework.authentication import BaseAuthentication


def jwt_response_payload_handler(token, user=None, request=None):

    return {
        'token': token,
        'id': user.id,
        'username': user.username
    }


class CustomSessionAuthentication(BaseAuthentication):
    """
    Use Django's session framework for authentication.
    """

    def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise returns `None`.
        """

        # Get the session-based user from the underlying HttpRequest object
        user = getattr(request._request, 'user', None)

        # Unauthenticated, CSRF validation not required
        if not user or not user.is_active:
            return None


        # CSRF passed with authenticated user
        return (user, None)