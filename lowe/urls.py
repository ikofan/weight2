from django.urls import path
from .views import index, tracker, rules, fund, check_weight

urlpatterns = [
    path('', index, name='index'),
    path('tracker/', tracker, name='tracker'),
    path('rules/', rules, name='rules'),
    path('fund/', fund, name='fund'),
    path('check/', check_weight, name='check')
]
