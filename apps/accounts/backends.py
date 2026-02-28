from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class PhoneOrEmailBackend(ModelBackend):
    """
    Authentication backend that allows users to log in with
    either phone number or email, with priority on phone.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate using phone number or email.
        """
        if username is None:
            username = kwargs.get('phone_number') or kwargs.get('email')
        
        if username is None or password is None:
            return None
        
        try:
            # Try to find user by phone number first (priority)
            user = User.objects.get(
                Q(phone_number=username) | Q(email=username),
                is_active=True
            )
        except User.DoesNotExist:
            # Run the default password hasher once to reduce timing
            # difference between existing and non-existing users
            User().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None