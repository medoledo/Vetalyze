from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def public_key_view(request):
    """
    Provides the public key for JWT verification.
    """
    return Response({'public_key': settings.SIMPLE_JWT['VERIFYING_KEY']})

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
