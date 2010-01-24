from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.contrib.admin.util import unquote, flatten_fieldsets, get_deleted_objects, model_ngettext, model_format_dict
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib import admin
from django import forms
from django.db.models import Q
from django.conf import settings
from filer.admin.permissions import PrimitivePermissionAwareModelAdmin
from filer.models import Folder, FolderRoot, UnfiledImages, ImagesWithMissingData, File
from filer.admin.tools import *
from filer.models import tools
from filer.settings import FILER_MEDIA_PREFIX
ADMIN_MEDIA_PREFIX = settings.ADMIN_MEDIA_PREFIX

from django.http import HttpResponse, HttpResponseNotFound
from django.utils import simplejson
from pprint import pprint
def build_file_dict(file):
    file = file.subtype()
    r = {}
    #{ title : "Node title", icon : "path_to/icon.pic", attributes : {"key" : "value" } }
    #pprint (file.icons)
    r['data'] = { 'title' : unicode(file.label), 'icon' : file.icons.get('16', '')}
    r['attributes'] = {'id': file.id, "rel":"file" }
    return r

def build_folder_dict(folder, id_override=None, include_files=True, max_depth=None, hint_children=True, depth=0):
    r = {}
    r['data'] = unicode(folder)
    if id_override is None:
        r['attributes'] = {'id': folder.id, "rel":"folder" }
    else:
        r['attributes'] = {'id': id_override, "rel":"folder" }
    children = folder.children.all()
    #print "handling '%s' children: %s depth: %s max_depth: %s" % (folder, len(children), depth, max_depth)
    r['children'] = []
    if len(children):
        if max_depth is None or max_depth>depth:
            print u"%s creating children for '%s' because %s is larger than %s" % (" "*depth, folder, max_depth, depth )
            for child in children:
                r['children'].append(build_folder_dict(child, include_files=include_files, max_depth=max_depth, hint_children=hint_children, depth=depth+1))
        else:
            if hint_children:
                r['state'] = 'closed'
    if include_files:
        files = folder.files
        if len(files):
            for file in folder.files:
                r['children'].append(build_file_dict(file))
    if not len(r['children']):
        del r['children']
    return r

def build_category_node(title,name,children):
    return {"data":
            {"title":title, 
                 #"clickable":False,"renameable":False, "deleteable":False, "createable":False,"draggable":False,
                 "attributes":{"class":"noicon"}
             },
             "state": "open", 
             "attributes":{"id":name,
                           "class":"noicon",
                           "rel":"category",
                           }, 
             "children":children,
            }


# Forms
class AddFolderPopupForm(forms.ModelForm):
    folder = forms.HiddenInput()
    class Meta:
        model=Folder
        fields = ('name',)

# ModelAdmins
class FolderAdmin(PrimitivePermissionAwareModelAdmin):
    list_display = ('name',)
    exclude = ('parent',)
    list_per_page = 20
    list_filter = ('owner',)
    search_fields = ['name', 'files__name' ]
    raw_id_fields = ('owner',)
    save_as=True # see ImageAdmin
    #hide_in_app_index = True # custom var handled in app_index.html of image_filer
    
    def changelist_view(self, request, extra_context=None):
        print "CHANGELIST VIEW!"
        return super(FolderAdmin, self).changelist_view(request, extra_context)
    
    def ajax_folder(self, request, extra_context=None):
        structured_data = []
        folder_id = request.REQUEST.get('id', None)
        print folder_id
        if folder_id is None:
            return HttpResponse(simplejson.dumps([]),mimetype='application/json')
        elif folder_id == UnfiledImages.id:
            print 'unifiled'
            data = build_folder_dict(UnfiledImages())
        elif folder_id == ImagesWithMissingData.id:
            print 'missing'
            data = build_folder_dict(ImagesWithMissingData())
        else:
            print "normal id"
            folder = Folder.objects.get(pk=folder_id)
            data = build_folder_dict(folder, max_depth=1)
        if 'children' in data:
            structured_data = data['children']
        else:
            structured_data = []
        return HttpResponse(simplejson.dumps(structured_data),mimetype='application/json')
    def ajax_move(self, request, extra_context=None):
        #TODO: Permission checking!!!!!
        #return HttpResponseForbidden('no way you can do that!')
        try:
            src_objtype = request.POST.get('src_objtype', None)
            src_id = request.POST.get('src_id', None)
            ref_objtype = request.POST.get('ref_objtype', None) 
            ref_id = request.POST.get('ref_id', None) 
            ref_type = request.POST.get('ref_type', None) 
            print "src_type: %s src_id: %s ref_objtype: %s ref_id: %s ref_type: %s" % (src_objtype, src_id, ref_objtype, ref_id, ref_type)
            if src_objtype in ['folder','file','category'] and src_id and ref_objtype and ref_id and ref_type:
                if ref_objtype == 'folder':
                    reference_obj = Folder.objects.get(id=ref_id)
                    if ref_type in ['before','after']:
                        # the destination obj is on the same level as reference_obj
                        if reference_obj.parent:
                            destination_obj = reference_obj.parent
                        else:
                            destination_obj = None
                    else: #'inside'
                        destination_obj = reference_obj
                elif ref_objtype == 'file':
                    reference_obj = File.objects.get(id=ref_id)
                    if ref_type in ['before','after']:
                        destination_obj = reference_obj.folder
                    else:
                        # this is illegal. a file cant have subitems!
                        destination_obj = reference_obj.folder
                
                print u"got destination folder '%s'" % destination_obj
                
                if src_objtype == 'folder':
                    src_folder = Folder.objects.get(id=src_id)
                    src_folder.parent = destination_obj
                    src_folder.save()
                    print "moved folder"
                elif src_objtype == 'file':
                    src_file = File.objects.get(id=src_id)
                    src_file.folder = destination_obj
                    src_file.save()
                    print "moved file"
                elif src_objtype is 'category' and src_id is 'favorites':
                    print "category type"
                else:
                    print "unknown type"
            else:
                print "somethign is wrong"
        except Exception, e:
            print e
            HttpResponse(simplejson.dumps({'result':'failed'}),mimetype='application/json')
        return HttpResponse(simplejson.dumps({'result':'ok'}),mimetype='application/json')
    
    def directory_browser_view(self, request, extra_context=None):
        root_folders = []
        folders = Folder.objects.filter(parent=None).order_by('name')
        for folder in folders:
            root_folders.append(build_folder_dict(folder, include_files=False, max_depth=0, hint_children=False))
        root_folders_category = build_category_node("FOLDERS", "rootFoldersCategory", root_folders)
        
        special_folders = [
            build_folder_dict(UnfiledImages(), include_files=False, hint_children=False, max_depth=0 ),
            build_folder_dict(ImagesWithMissingData(), include_files=False, hint_children=False, max_depth=0)
        ]
        special_folders_category = build_category_node("SPECIAL FOLDERS", "specialCategory", special_folders)
        favorite_folders = []
        for folder in Folder.objects.filter(favoritefolder__user=request.user).order_by('name'):
            favorite_folders.append(build_folder_dict(folder, include_files=False, max_depth=0, hint_children=False))
        favorites_category = build_category_node("FAVORITES", "favoritesCategory", favorite_folders)
        categories_data = [root_folders_category, special_folders_category, favorites_category]
        
        # TODO: catch if there are no root folders!
        folders_data = []
        for child in folders[0].children.order_by('name'):
            folders_data.append(build_folder_dict(child))
        #print structured_data
        return render_to_response('admin/filer/folder/jstree/browser.html', {
                'folders_json':simplejson.dumps(folders_data),
                'folders_dict': folders_data,
                'categories_initial_selected': folders[0].id,
                'categories_json':simplejson.dumps(categories_data),
                'categories_dict':categories_data,
            }, context_instance=RequestContext(request))
    
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        parent_id = request.REQUEST.get('parent_id', None)
        if parent_id:
            return AddFolderPopupForm
        else:
            return super(FolderAdmin, self).get_form(request, obj=None, **kwargs)
    def save_form(self, request, form, change):
        """
        Given a ModelForm return an unsaved instance. ``change`` is True if
        the object is being changed, and False if it's being added.
        """
        r = form.save(commit=False)
        parent_id = request.REQUEST.get('parent_id', None)
        if parent_id:
            parent = Folder.objects.get(id=parent_id)
            r.parent = parent
        return r
    def response_change(self, request, obj):
        '''
        Overrides the default to be able to forward to the directory listing
        instead of the default change_list_view
        '''
        r = super(FolderAdmin, self).response_change(request, obj)
        if r['Location']:
            print r['Location']
            print obj
            # it was a successful save
            if r['Location'] in ['../']:
                if obj.parent:
                    url = reverse('admin:filer-directory_listing', 
                                  kwargs={'folder_id': obj.parent.id})
                else:
                    url = reverse('admin:filer-directory_listing-root')
                return HttpResponseRedirect(url)
            else:
                # this means it probably was a save_and_continue_editing
                pass
        return r
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        extra_context = {'show_delete': True}
        context.update(extra_context)
        return super(FolderAdmin, self).render_change_form(request=request, context=context, add=False, change=False, form_url=form_url, obj=obj)
    
    def delete_view(self, request, object_id, extra_context=None):
        '''
        Overrides the default to enable redirecting to the directory view after
        deletion of a folder.
        
        we need to fetch the object and find out who the parent is
        before super, because super will delete the object and make it impossible
        to find out the parent folder to redirect to.
        '''
        parent_folder = None
        try:
            obj = self.queryset(request).get(pk=unquote(object_id))
            parent_folder = obj.parent
        except self.model.DoesNotExist:
            obj = None
        
        r = super(FolderAdmin, self).delete_view(request=request, object_id=object_id, extra_context=extra_context)
        url = r.get("Location", None)
        if url in ["../../../../","../../"]:
            if parent_folder:
                url = reverse('admin:filer-directory_listing', 
                                  kwargs={'folder_id': parent_folder.id})
            else:
                url = reverse('admin:filer-directory_listing-root')
            return HttpResponseRedirect(url)
        return r
    def icon_img(self,xs):
        return mark_safe('<img src="%simg/icons/plainfolder_32x32.png" alt="Folder Icon" />' % FILER_MEDIA_PREFIX)
    icon_img.allow_tags = True
    
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(FolderAdmin, self).get_urls()
        from filer import views
        url_patterns = patterns('',
            # we override the default list view with our own directory listing of the root directories
            url(r'^$', self.admin_site.admin_view(self.directory_listing), name='filer-directory_listing-root'),
            url(r'^(?P<folder_id>\d+)/list/$', self.admin_site.admin_view(self.directory_listing), name='filer-directory_listing'),
            
            url(r'^jstree/$', self.admin_site.admin_view(self.directory_browser_view), name='filer-directory_browser'),
            url(r'^jstree/getchildren/$', self.admin_site.admin_view(self.ajax_folder), name='filer-directory_browser-getchildren'),
            url(r'^jstree/move/$', self.admin_site.admin_view(self.ajax_move), name='filer-directory_browser-move'),
            
            url(r'^(?P<folder_id>\d+)/make_folder/$', self.admin_site.admin_view(views.make_folder), name='filer-directory_listing-make_folder'),
            url(r'^make_folder/$', self.admin_site.admin_view(views.make_folder), name='filer-directory_listing-make_root_folder'),
            
            url(r'^images_with_missing_data/$', self.admin_site.admin_view(self.directory_listing), {'viewtype': 'images_with_missing_data'}, name='filer-directory_listing-images_with_missing_data'),
            url(r'^unfiled_images/$', self.admin_site.admin_view(self.directory_listing), {'viewtype': 'unfiled_images'}, name='filer-directory_listing-unfiled_images'),
        )
        url_patterns.extend(urls)
        return url_patterns
    
    
    # custom views
    def directory_listing(self, request, folder_id=None, viewtype=None):
        clipboard = tools.get_user_clipboard(request.user)
        if viewtype=='images_with_missing_data':
            folder = ImagesWithMissingData()
        elif viewtype=='unfiled_images':
            folder = UnfiledImages()
        elif folder_id == None:
            folder = FolderRoot()
        else:
            try:
                folder = Folder.objects.get(id=folder_id)
            except Folder.DoesNotExist:
                raise Http404
            
        # search
        def filter_folder(qs, terms=[]):
            for term in terms:
                qs = qs.filter(Q(name__icontains=term) | Q(owner__username__icontains=term) | Q(owner__first_name__icontains=term) | Q(owner__last_name__icontains=term)  )  
            return qs
        def filter_file(qs, terms=[]):
            for term in terms:
                qs = qs.filter( Q(name__icontains=term) | Q(original_filename__icontains=term ) | Q(owner__username__icontains=term) | Q(owner__first_name__icontains=term) | Q(owner__last_name__icontains=term) )
            return qs
        q = request.GET.get('q', None)
        if q:
            search_terms = q.split(" ")
        else:
            search_terms = []
        limit_search_to_folder = request.GET.get('limit_search_to_folder', False) in (True, 'on')
    
        if len(search_terms)>0:
            if folder and limit_search_to_folder and not folder.is_root:
                folder_qs = folder.get_descendants()
                file_qs = File.objects.filter(folder__in=folder.get_descendants())
            else:
                folder_qs = Folder.objects.all()
                file_qs = File.objects.all()
            folder_qs = filter_folder(folder_qs, search_terms)
            file_qs = filter_file(file_qs, search_terms)
                
            show_result_count = True
        else:
            folder_qs = folder.children.all()
            file_qs = folder.files.all()
            show_result_count = False
        
        folder_qs = folder_qs.order_by('name')
        file_qs = file_qs.order_by('name')
        
        folder_children = []
        folder_files = []
        if folder.is_root:
            folder_children += folder.virtual_folders
        
        for f in folder_qs:
            f.perms = userperms_for_request(f, request)
            if hasattr(f, 'has_read_permission'):
                if f.has_read_permission(request):
                    #print "%s has read permission for %s" % (request.user, f)
                    folder_children.append(f)
                else:
                    pass#print "%s has NO read permission for %s" % (request.user, f)
            else:
                folder_children.append(f) 
        for f in file_qs:
            f.perms = userperms_for_request(f, request)
            if hasattr(f, 'has_read_permission'):
                if f.has_read_permission(request):
                    #print "%s has read permission for %s" % (request.user, f)
                    folder_files.append(f)
                else:
                    pass#print "%s has NO read permission for %s" % (request.user, f)
            else:
                folder_files.append(f)
        try:
            permissions = {
                'has_edit_permission': folder.has_edit_permission(request),
                'has_read_permission': folder.has_read_permission(request),
                'has_add_children_permission': folder.has_add_children_permission(request),
            }
        except:
            permissions = {}
        #print admin.site.root_path
        return render_to_response('admin/filer/folder/directory_listing.html', {
                'folder':folder,
                'folder_children':folder_children,
                'folder_files':folder_files,
                'permissions': permissions,
                'permstest': userperms_for_request(folder, request),
                'current_url': request.path,
                'title': u'Directory listing for %s' % folder.name,
                'search_string': ' '.join(search_terms),
                'show_result_count': show_result_count,
                'limit_search_to_folder': limit_search_to_folder,
                'is_popup': popup_status(request),
                'select_folder': selectfolder_status(request),
                'root_path': "/%s" % admin.site.root_path, # needed in the admin/base.html template for logout links and stuff 
            }, context_instance=RequestContext(request))
