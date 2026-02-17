from django.contrib.auth.tokens import PasswordResetTokenGenerator

class CustomTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # We only use PK, Password, and Timestamp.
        # We REMOVE 'last_login' to prevent tokens from breaking if the user logs in.
        return (
            str(user.pk) + user.password + str(timestamp)
        )

# Create a single instance to import elsewhere
custom_token_generator = CustomTokenGenerator()