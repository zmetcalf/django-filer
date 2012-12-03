#-*- coding: utf-8 -*-
from functools import update_wrapper
import json
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from elfinder.connector import ElFinderConnector
from elfinder.volume_drivers.base import BaseVolumeDriver
from elfinder.volume_drivers.model_driver import ModelVolumeDriver
from filer.models import Folder, File, FolderRoot
from django.utils.translation import ugettext_lazy as _



class FilerVolumeDriver(ModelVolumeDriver):

    def __init__(self, collection_id=None,
                 directory_model=Folder,
                 file_model=File,
                 *args, **kwargs):

        super(ModelVolumeDriver, self).__init__(*args, **kwargs)
        self.root_directory = FolderRoot()
        self.directory_model = directory_model
        self.file_model = file_model

    def get_volume_id(self):
        """ Returns the volume ID for the volume, which is used as a prefix
            for client hashes.
        """
        return 'AA'

    def get_object(self, hash):
        if hash == '':
            return self.root_directory
        try:
            volume_id, object_hash = hash.split('_')
        except ValueError:
            raise Exception('Invalid target hash: %s' % hash)

        try:
            object_id = int(object_hash[1:])
        except ValueError:
            raise Exception('Invalid target hash: %s' % object_hash)

        # Figure which type of object is being requested
        if object_hash[0] == 'f':
            model = self.file_model
        elif object_hash[0] == 'd':
            model = self.directory_model
        else:
            raise Exception('Invalid target hash: %s' % object_hash)

        try:
            object = model.objects.get(pk=object_id)
        except model.DoesNotExist:
            raise Exception('Could not open target')

        return object


    def get_tree(self, target, ancestors=False, siblings=False):
        """ Returns a list of dicts describing children/ancestors/siblings of
            the target directory.

            Siblings of the root node are always excluded, as they refer to
            root directories of other file collections.
        """
        dir = self.get_object(target)
        tree = []

        # Add children to the tree first
        for item in dir.get_children():
            tree.append(item.get_info())
#        for item in dir.files:
#            tree.append(item.get_info())

        # Add ancestors next, if required
        if ancestors:
            for item in dir.get_ancestors(include_self=True):
                tree.append(item.get_info())
                for ancestor_sibling in item.get_siblings():
                    if ancestor_sibling.parent:
                        tree.append(ancestor_sibling.get_info())

        # Finally add siblings, if required
        if siblings:
            for item in dir.get_siblings():
                if item.parent:
                    tree.append(item.get_info())

        return tree



def index(request, coll_id=None):
    """ Displays the elFinder file browser template for the specified
        FileCollection.
    """
    return render_to_response("admin/filer/elfinder/elfinder.html",
        {'coll_id': 'AA'},
        RequestContext(request))


def connector_view(request, coll_id=None):
    """ Handles requests for the elFinder connector.
    """

    model_volume = FilerVolumeDriver()

    finder = ElFinderConnector([model_volume])
    finder.run(request)

    # Some commands (e.g. read file) will return a Django View - if it
    # is set, return it directly instead of building a response
    if finder.return_view:
        return finder.return_view

    response = HttpResponse(mimetype=finder.httpHeader['Content-type'])
    response.status_code = finder.httpStatusCode
    if finder.httpHeader['Content-type'] == 'application/json':
        response.content = json.dumps(finder.httpResponse)
    else:
        response.content = finder.httpResponse

    return response


def read_file(request, volume, file_hash, template="read_file.html"):
    """ Default view for responding to "open file" requests.

        coll: FileCollection this File belongs to
        file: The requested File object
    """
    return render_to_response(template,
        {'file': file_hash},
        RequestContext(request))




class ElFinder(Folder):
    class Meta:
        proxy = True
        app_label = 'filer'
        verbose_name = _("ElFinder")
        verbose_name_plural = _("ElFinders")


class ElFinderAdmin(admin.ModelAdmin):
    def get_urls(self):
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        urlpatterns = patterns('',
            url(r'^$',
                wrap(index),
                name='%s_%s_changelist' % info),
            url(r'^connector/$',
                wrap(connector_view),
                name='filer_elfinder_connector'),
#            url(r'^add/$',
#                wrap(self.add_view),
#                name='%s_%s_add' % info),
#            url(r'^(.+)/history/$',
#                wrap(self.history_view),
#                name='%s_%s_history' % info),
#            url(r'^(.+)/delete/$',
#                wrap(self.delete_view),
#                name='%s_%s_delete' % info),
#            url(r'^(.+)/$',
#                wrap(self.change_view),
#                name='%s_%s_change' % info),
        )
        return urlpatterns
#        return patterns('',
#            url(r'^(?P<coll_id>\d+)/$', 'elfinder.views.index', name='elfinder_index'),
#            url(r'^connector/(?P<coll_id>\d+)/$', 'elfinder.views.connector_view', name='elfinder_connector'),
#        )
