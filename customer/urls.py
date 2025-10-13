from django.urls import path
from . import views

urlpatterns = [
    # path('admin_dashboard/',views.admin_dashboard, name='admindashboard'),
    path('add_recipe/',views.register_recipe, name='addrecipe'),
    path('menu/',views.menu_view,name='menu'),
    path('order_confirmation/', views.order_confirmation, name='orderConfirmation'),
    path('recipe_view/',views.recipe_view,name='recipeView'),
    path('recipe_management/', views.recipe_management, name='recipe_management'),
    path('search_recipes/', views.search_recipes, name='search_recipes'),
    path('edit_recipe/<int:recipe_id>/', views.edit_recipe, name='edit_recipe'),
    path('delete_recipe/<int:recipe_id>/', views.delete_recipe, name='delete_recipe'),
    path('cashier_report/',views.cashier_report, name='cashierReport'),
    # path('search_cashier_report/', views.search_cashier_report, name='search_cashier_report'),
    # path('export_cashier_report_pdf/', views.export_cashier_report_pdf, name='export_cashier_report_pdf'),
      path('search_cashier_report/', views.search_cashier_report, name='search_cashier_report'),
]