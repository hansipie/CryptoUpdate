from django.urls import path

from . import views

urlpatterns = [
    path('upload/', views.upload, name='upload'),
    path('success/url/', views.success, name='success'),  # Ajoutez une vue de succès
    # path('list/', views.list, name='list'),
    # path('delete/<int:id>/', views.delete, name='delete'),
    # path('update/<int:id>/', views.update, name='update'),
]
