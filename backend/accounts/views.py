from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FCMToken
from .serializers import ChangePasswordSerializer, ProfileSerializer


class FCMTokenRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response(
                {"detail": "token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_name = request.data.get("device_name", "")
        fcm_token, created = FCMToken.objects.update_or_create(
            token=token,
            defaults={
                "user": request.user,
                "device_name": device_name,
                "is_active": True,
            },
        )
        return Response(
            {
                "id": fcm_token.id,
                "token": fcm_token.token,
                "device_name": fcm_token.device_name,
                "is_active": fcm_token.is_active,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FCMTokenDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, token):
        updated = FCMToken.objects.filter(user=request.user, token=token).update(is_active=False)
        if not updated:
            return Response({"detail": "Token not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProfileSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated successfully."})
