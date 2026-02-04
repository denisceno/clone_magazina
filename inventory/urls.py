from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.inventory_home, name="inventory-home"),
    path("depot/<int:depot_id>/", views.depot_detail, name="depot-detail"),
    path("product/add/", views.add_product, name="add-product"),
    path("product/<int:product_id>/add/", views.add_quantity, name="add-quantity"),
    path("product/<int:product_id>/edit/", views.edit_product, name="edit-product"),
    path("product/<int:product_id>/delete/", views.delete_product, name="delete-product"),
    path("products/", views.all_products, name="all-products"),
    path("product/<int:product_id>/", views.product_detail, name="product-detail"),

    path("employees/", views.employees_view, name="employee-list"),
    path("employees/<int:employee_id>/", views.employees_view, name="employee-detail"),
    path("my-returnables/", views.my_returnables, name="my-returnables"),
    path("withdraw/", views.create_withdrawal, name="create-withdrawal"),

    path("return/<int:withdrawal_item_id>/", views.return_item, name="return-item"),
    path("withdraw/<int:id>/", views.withdraw_detail, name="withdraw-detail"),
]
