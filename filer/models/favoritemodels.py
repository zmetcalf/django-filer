from django.db import models
from django.contrib.auth import models as auth_models

from filer.models.foldermodels import Folder

class FavoriteFolder(models.Model):
    user = models.ForeignKey(auth_models.User)
    folder = models.ForeignKey(Folder)
    def __unicode__(self):
        return u"%s: %s" % (self.user, self.folder)
    class Meta:
        app_label = 'filer'
        unique_together = (('user','folder',),)