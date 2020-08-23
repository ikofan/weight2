from django.urls import path
from .views import index, tracker, rules, fund, check_weight, fund_list, fund_details

urlpatterns = [
    path('', index, name='index'),
    path('tracker/', tracker, name='tracker'),
    path('rules/', rules, name='rules'),
    path('fund/', fund, name='fund'),
    path('fund_list/', fund_list, name='fund_list'),
    path('fund_list/<int:batch_id>', fund_details, name='fund_details'),
    path('check/', check_weight, name='check')
]
