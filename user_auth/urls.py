from django.urls import path
from . import views

urlpatterns = [
    path('register_staff/',views.register_staff, name='addStaff'),
]