from django.contrib import admin
from models import NotificationType, NotificationSetting, Notification, NotificationCategory

# decorator to add a 'short_description' attribute to a function
def short_description(desc):
  def func(f):
    f.short_description = desc
    return f
  return func

class NotificationCategoryAdmin(admin.ModelAdmin):
  list_display = [ "id", "name", "code" ]

class NotificationTypeAdmin(admin.ModelAdmin):
  list_display = [ "id", "active", "category_name", "name", "description", "default", "internal", "has_text" ]
  list_filter = [ "default", "internal", "active" ]
  search_fields = [ "name", "description" ]
  list_per_page = 50
  list_select_related = True

  @short_description('Category')
  def category_name(self, obj): return obj.category.name

  @short_description('Has Text')
  def has_text(self, obj): 
    return " ".join(filter(None, (obj.subject and 'S' or '', obj.email and 'E' or '', obj.template and 'T' or '')))

class NotificationSettingAdmin(admin.ModelAdmin):
  list_display = [ "id", "user", "notificationtype", "value" ]
  search_fields = [ 'user__username', 'notificationtype__description' ]

class NotificationAdmin(admin.ModelAdmin):
  list_display = [ "id", "user", "notificationtype", "senton", "description", "viewed", "clicked", "emailed" ]
  list_filter = [ "notificationtype" ]
  search_fields = [ 'user__username', 'notificationtype__description' ]
  raw_id_fields = ["user"]

admin.site.register(NotificationCategory, NotificationCategoryAdmin)
admin.site.register(NotificationType, NotificationTypeAdmin)
admin.site.register(NotificationSetting, NotificationSettingAdmin)
admin.site.register(Notification, NotificationAdmin)

