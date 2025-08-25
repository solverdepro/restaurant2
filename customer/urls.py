from django.urls import path
from . import views

urlpatterns = [
    path('',views.home, name='homeview'),
    path('admin_dashboard/',views.admin_dashboard, name='admindashboard'),
    path('add_recipe/',views.register_recipe, name='addrecipe'),
]