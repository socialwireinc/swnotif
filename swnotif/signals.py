from django import dispatch

# Signal is triggered whenever a set of NotificationSetting objects are changed for a given user (sender=User)
notifications_changed = dispatch.Signal()

# Signal is triggered when notification is saved (sender=Notification, instance=notif, created=True/False)
saved = dispatch.Signal(providing_args=["instance", "created"])

# Signal is triggered when notification is saved, and user subscribed for notification (sender=Notification, instance=notif, created=True/False)
notify = dispatch.Signal(providing_args=["instance", "created"])

# Signal is triggered when a Notification object's "renotify" method is called.
renotify = dispatch.Signal(providing_args=["instance"])

