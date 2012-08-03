#-*- coding: utf-8 -*-
from filer.models import File, Folder

class FilerPermissionBackend(object):
    def has_perm(self, user_obj, perm, obj=None):
#        import ipdb; ipdb.set_trace()
        if not obj:
            return False
        if not perm.startswith('filer.can_'):
            return False
        if not isinstance(obj, File) or isinstance(obj, Folder)):
            return False
        app, perm_name = perm.split('.')
        print user_obj, perm, obj

        if perm_name.startswith('can_delete_'):
            return obj.can_delete(user_obj)
        elif perm_name.startswith('can_change_'):
            return obj.can_change(user_obj)
        elif perm.startswith('can_add_'):
            return obj.can_add(user_obj)
        return False
