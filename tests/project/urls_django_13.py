#-*- coding: utf-8 -*-
import re
from django.conf import settings
from django.conf.urls.defaults import patterns, url
from project.urls import urlpatterns

urlpatterns = urlpatterns + patterns('',
        url(r'^%s(?P<path>.*)$' % re.escape(settings.STATIC_URL.lstrip('/')), 'django.views.static.serve'),
    )
