from django.urls import path
from . import views

urlpatterns = [
    path('register_product/',views.add_product,name='registerProduct'),
    path('add_batch',views.add_batch, name='add_batch'),
    path('product_view/',views.product_view,name='productView'),
    path('update_product/<int:batch_id>/', views.update_product, name='update_product'),
    path('product/delete/<int:batch_id>/', views.delete_product, name='delete_product'),
    path('search_products/', views.search_products, name='search_products'),


]