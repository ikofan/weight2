from django.contrib import admin
from .models import LoWe, Name, Tracker, StartLowe


@admin.register(LoWe)
class LoWeAdmin(admin.ModelAdmin):
    list_display = ('name', 'sex', 'batches', 's_weight', 'target', 'fund', 'refund_weight', 'refund', 'result', 'e_weight',  'rc_refund',
                    'created_time')
    list_filter = ['name', ]
    search_fields = ['name__name']

    actions_on_top = True
    actions_on_bottom = True

    # 编辑页面
    save_on_top = True


@admin.register(Name)
class NameAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_time')


@admin.register(Tracker)
class TrackerAdmin(admin.ModelAdmin):
    list_display = ('name', 'check_date', 'weight', 'created_time')


@admin.register(StartLowe)
class StartLoweAdmin(admin.ModelAdmin):
    list_display = ('batches', 's_date', 'e_date')
