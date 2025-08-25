from django.urls import path
from . import views

urlpatterns = [
    path('register_product/',views.register_product,name='registerProduct'),
]