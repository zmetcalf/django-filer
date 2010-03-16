from django.utils.translation import ugettext as _
from django.utils.text import truncate_words
from django.utils import simplejson
from django.db import models
from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from sorl.thumbnail.base import ThumbnailException
from filer.settings import FILER_STATICMEDIA_PREFIX
from django.conf import settings as globalsettings
from filer.fields.file import AdminFileWidget, AdminFileFormField, FilerFileField
from filer.models import Image

from django.db.models import signals as model_signals
from django.db.models import FieldDoesNotExist, PositiveIntegerField, CommaSeparatedIntegerField
from django.dispatch import dispatcher

from filer.fields import helpers



class AdminImageWidget(AdminFileWidget):
    pass

class AdminImageFormField(AdminFileFormField):
    widget = AdminImageWidget

class FilerImageField(FilerFileField):
    default_form_class = AdminImageFormField
    default_model_class = Image
    
    def __init__(self, **kwargs):
        # find any special attributes
        self.can_resize = kwargs.pop('can_resize', False)
        self.can_crop = kwargs.pop('can_crop', False)
        self.resize_width_fieldname = kwargs.pop('resize_width_fieldname', None)
        self.resize_height_fieldname = kwargs.pop('resize_height_fieldname', None)
        self.crop_region_fieldname = kwargs.pop('crop_region_fieldname', None)
        print kwargs
        print "can_resize: %s" % self.can_resize
        print "can_crop: %s" % self.can_crop
        if self.can_resize:
            pass
        return super(FilerImageField,self).__init__(**kwargs)
    
    def contribute_to_class(self, cls, name):
        super(FilerImageField, self).contribute_to_class(cls, name)
        model = cls
        opts = model._meta
        if self.can_resize:
            if self.resize_width_fieldname is None:
                self.resize_width_fieldname = '%s_resize_width' % name
            if self.resize_height_fieldname is None:
                self.resize_height_fieldname = '%s_resize_height' % name
            for fieldname in [self.resize_width_fieldname, self.resize_height_fieldname]:
                try:
                    opts.get_field(fieldname)
                except FieldDoesNotExist:
                    CommaSeparatedIntegerField(
                        db_index=True, editable=True, 
                        max_length=64, 
                        null=True, blank=True).contribute_to_class(model, fieldname)
        
        if self.can_crop:
            if self.crop_region_fieldname is None:
                self.crop_region_fieldname = '%s_crop_region' % name
            for fieldname in [self.crop_region_fieldname, ]:
                try:
                    opts.get_field(fieldname)
                except FieldDoesNotExist:
                    PositiveIntegerField(
                        db_index=True, editable=True, 
                        null=True, blank=True).contribute_to_class(model, fieldname)
        