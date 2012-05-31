"""
Social Wire Notification System

Models to:
  - describe notification types in the system
  - store notification settings per user
  - store notificatins sent to users

Includes custom manager functions to fetch extra info

"""

from django.db import models
from django.contrib.auth import models as authmodels
from django.contrib.contenttypes import models as ctmodels
from django.contrib.contenttypes import generic

from swcomments import models as swcmodels
from swnotif import signals


def _lookup_NotificationType(name_or_type):
  """
  Given a string (name), return the NotificationType that matches the name.
  If the object passed is already a NotificationType, just return it.
  Will raise an exception on failure to match (or if passed an unexpected type).
  """
  if isinstance(name_or_type, (str,unicode)):
    # Notification type was passed as a string, get the actual NotificationType object
    try:
      nt = NotificationType.objects.get(name=name_or_type)
    except:
      raise TypeError("A NotificationType with the name '%s' not found" % (name_or_type,))
  elif isinstance(name_or_type, NotificationType):
    nt = name_or_type
  else:
    raise TypeError("The 'name_or_type' parameter must be a string or a NotificationType instance")
  return nt

class NotificationCategory(models.Model):
  """
  Categorization for notifications
  """

  name        = models.CharField("Name", max_length=200)
  code        = models.CharField("Code", max_length=50, null=True, blank=True, help_text="Internal name")

  def __unicode__(self):
    return u'%s (%s)' % (self.name, self.code or 'no code')

class NotificationType(models.Model):
  """
  A single notification type.  Includes its internal name, description, default value and
  whether its internal (ie. user settable or not).
  """

  name        = models.CharField("Internal Name", max_length=50)
  description = models.CharField("Description", max_length=255)

  default     = models.BooleanField("Set by default?")
  internal    = models.BooleanField("Internal only?")

  template    = models.TextField("Template to use", blank=True, null=True, help_text="(for email, etc)")
  subject     = models.CharField("Subject to use", max_length=200, blank=True, null=True, help_text="(for email)")
  email       = models.CharField("Email to", max_length=200, blank=True, null=True, help_text="Separate by commas")

  active      = models.BooleanField("Active?", default=True, help_text="Is this notification currently being used by your platform")

  category    = models.ForeignKey(NotificationCategory)

  def __unicode__(self):
    return u'%s' % (self.name,)

class NotificationSettingManager(models.Manager):
  """
  Special manager that allows to query certain useful things from the database such as notification settings
  (whether they're set or not), etc.
  """

  def for_user(self, user, as_string=False, all_notifications=False):
    """
    Given a user, return a dictionary of all notifications with their values (booleans).
    If 'as_string' is True, the keys will be the 'name' of the NotificationType, otherwise it will be a NotificationType object.
    Makes sure to return all active notifications, regardless of whether the user has a value saved for it (will use default).
    """
    qs = super(NotificationSettingManager, self).get_query_set().filter(user=user)
    d = dict([ (n.notificationtype, n) for n in qs ])   # User's current settings, as { NotificationType: NotificationSetting }
    alln = NotificationType.objects.filter(internal=False, active=True)
    r = {}
    for n in alln:
      if n not in d:
        if all_notifications: r[n] = n.default
      else:
        r[n] = d[n].value
    if as_string:
      r = dict([ (k.name,v) for k,v in r.items() ])
    return r

  def all_for_user(self, user, as_string=False):
    return self.for_user(user, as_string, all_notifications=True)

  def value_for_user(self, user, name_or_type):
    """
    Given a user and a notification name or type (name string or NotificationType object), return
    a boolean true/false value.
    This function makes sure to return the default value for the requested notification type in the
    case where the user does not have a value saved.
    """
    if isinstance(name_or_type, (str,unicode)):
      # Notification type was passed as a string, get the actual NotificationType object
      try:
        nt = NotificationType.objects.get(name=name_or_type)
      except:
        raise TypeError("A NotificationType with the name '%s' not found" % (name_or_type,))
    elif isinstance(name_or_type, NotificationType):
      nt = name_or_type
    else:
      raise TypeError("The 'name_or_type' parameter must be a string or a NotificationType instance")

    qs = super(NotificationSettingManager, self).get_query_set()
    try:
      return qs.get(user=user, notificationtype=nt).value
    except:
      return nt.default

class NotificationSetting(models.Model):
  """
  A Notification Setting for a single User.
  """

  user = models.ForeignKey(authmodels.User)
  notificationtype = models.ForeignKey(NotificationType)
  value = models.BooleanField("Set?")

  objects = NotificationSettingManager()

  def __unicode__(self):
    return "%s=%s" % (self.notificationtype, self.value)

class Notification(models.Model):
  """
  A list of notifications that were sent out.

  Create a new one with:

    Notification(user=user, notificationtype=nt, content_object=x).save()

  You can optionally include a description (a title for this specific notification).  
  When checking for the description, make sure to fall back to the NotificationType's 
  description in case description is blank.

  A signal will be triggered on save.
  """

  user = models.ForeignKey(authmodels.User)
  notificationtype = models.ForeignKey(NotificationType)

  senton = models.DateTimeField(auto_now_add=True)
  viewed = models.BooleanField("Viewed?", default=False)
  clicked = models.BooleanField("Clicked?", default=False)
  emailed = models.BooleanField("Emailed?", default=False)

  description = models.CharField("Description (title)", max_length=200, blank=True, null=True)  

  # Misc. object we're attaching to this notification.
  content_type = models.ForeignKey(ctmodels.ContentType)
  object_id = models.PositiveIntegerField()
  content_object = generic.GenericForeignKey('content_type', 'object_id')

  @classmethod
  def create_for_user(cls, user, notificationtype, content_object=None, description=None, ctxd=None):
    """
    Class method that creates a Notification for a given user.
    Requires:
      - user: django.contrib.auth.models.User instance
      - notificationtype: either a NotificationType instance, or a string that matches one by name
      - content_object: an optional object to save along with the notification
      - ctxd: (optional) context dictionary to use when rendering description
      - description: an optional description for this notification (will render notificationtype.description otherwise)
    Returns the Notification object just created.
    """
    nt = _lookup_NotificationType(notificationtype)
    if not description:
      # if description is empty, render the one found in notificationtype
      #description = nt.description
      description = nt.subject or nt.description  # USING SUBJECT NOW, nt.description is a generic description of notif, not a specific one

      if content_object:
        from django.template import Template, Context
        from django.contrib.comments import models as commentmodels

        obj = content_object
        comment = None

        # If this is a comment, use its content_object instead...
        if isinstance(obj, (commentmodels.Comment, swcmodels.BaseComment)):
          comment = obj
          obj = obj.content_object

        # Prepare context dictionary
        d = {}
        if hasattr(obj, 'swnotif_context') and callable(obj.swnotif_context):
          d = obj.swnotif_context()
          if not isinstance(d, dict):
            d = None
          else:
            if 'obj' not in d: d['obj'] = obj
        if not d:
          d = { 'obj' : obj }

        # Add comment into context if it doesn't already exist
        if comment and 'comment' not in d: d['comment'] = comment

        # We gotta render email 1st, as we might need that one in the other templates
        description = Template(description).render(Context(d))

    n = cls(user=user, notificationtype=nt, content_object=content_object, description=description)
    n.save()
    return n

  def save(self, **kw):
    """
    Override to do actions when we save a new notification.
    Right now it calls signals (saved, notify) on save.
    """
    created = self.id is None
    super(Notification, self).save(**kw)
    # Saved signal
    signals.saved.send(sender=self, instance=self, created=created)
    # Only call signal if user wants to be notified
    if NotificationSetting.objects.value_for_user(self.user, self.notificationtype):
      signals.notify.send(sender=self, instance=self, created=created)

  def renotify(self):
    """
    Manually renotify when something changes (using the renotify signal).
    """
    # Only call signal if user wants to be notified
    if NotificationSetting.objects.value_for_user(self.user, self.notificationtype):
      signals.renotify.send(sender=self, instance=self)

