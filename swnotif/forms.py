"""
Notification Form class.
"""

from swnotif import models as nmodels
from swnotif import signals as nsignals
from django import forms

formname = 'NotificationForm'

class BaseNotificationForm(forms.Form):
  def save(self, user):
    """
    Save the parsed form for a given user.
    Note that this will only work if you created the NotificationForm class
    from a posted html form.
    Returns None (nothing).
    """
    # map of user's existing NotificationSetting objects, keyed by NotificationType.name
    ud = dict([ (n.notificationtype.name, n) for n in user.notificationsetting_set.all() ])
    # map of all existing NotificationType objects, keyed by name
    nd = dict([ (nt.name,nt) for nt in nmodels.NotificationType.objects.all() ])
    # data we received from the form.  Note that this will only save settings that were in the form.
    cd = self.cleaned_data
    for n in cd.keys():
      if n not in nd: continue   # This shouldn't happen, but just in case.
      ns = ud.get(n)             # See if we have an existing NotificationSetting
      if ns is None or ns.value != cd[n]:
        if ns:                   # Exists, so update it
          ns.value = cd[n]  
        else:                    # Create new one
          ns = nmodels.NotificationSetting(user=user, notificationtype=nd[n], value=cd[n])
        ns.save()
    nsignals.notifications_changed.send(sender=user)

def MakeNotificationForm():
  """
  The NotificationForm can be changed at any time as it consists of fields that are defined
  in the database rather than statically (in the NotificationType model).  So we can't define
  the Form at start time -- we have to create the class everytime we need it (in case a 
  notification has been added/removed or changed.
  """
  bases = (BaseNotificationForm,)
  attribs = {}
  for n in nmodels.NotificationType.objects.filter(internal=False):
    f = forms.BooleanField(required=False, initial=n.default, help_text=n.description)
    attribs[n.name] = f
  return type(formname, bases, attribs)

