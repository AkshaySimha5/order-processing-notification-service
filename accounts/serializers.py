from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    # only used for user creation, never sent back to the client

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            email=validated_data["email"],
        )
        return user

    def to_representation(self, instance):
        # original response data (id and username)
        data = super().to_representation(instance)

        # generate tokens for the new user instance
        refresh = RefreshToken.for_user(instance)

        # tokens send back to the client
        data['tokens'] = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        return data
