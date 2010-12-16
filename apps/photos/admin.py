from django.contrib import admin
from photos.models import Image, Pool
from photos.forms import PhotoAdminForm
from event_logs.models import EventLog
from perms.models import ObjectPermission
from perms.utils import is_admin, get_notice_recipients
from notification.context_processors import notification

class PhotoAdmin(admin.ModelAdmin):
    list_display = ('title', 'caption', 'update_dt', 'create_dt', 'tags',)

    fieldsets = (
        (None, {'fields': ('image', 'title', 'caption', 'tags')}),
        ('Administrative', {'fields': ('allow_anonymous_view','user_perms','group_perms','status','status_detail' )}),
    )
    form = PhotoAdminForm

    def log_deletion(self, request, object, object_repr):
        super(PhotoAdmin, self).log_deletion(request, object, object_repr)
        log_defaults = {
            'event_id' : 990300,
            'event_data': '%s (%d) deleted by %s' % (object._meta.object_name,
                                                    object.pk, request.user),
            'description': '%s deleted' % object._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': object,
        }
        EventLog.objects.log(**log_defaults)

    def log_change(self, request, object, message):
        super(PhotoAdmin, self).log_change(request, object, message)
        log_defaults = {
            'event_id' : 990200,
            'event_data': '%s (%d) edited by %s' % (object._meta.object_name,
                                                    object.pk, request.user),
            'description': '%s edited' % object._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': object,
        }
        EventLog.objects.log(**log_defaults)

    def log_addition(self, request, object):
        super(PhotoAdmin, self).log_addition(request, object)
        log_defaults = {
            'event_id' : 990100,
            'event_data': '%s (%d) added by %s' % (object._meta.object_name,
                                                   object.pk, request.user),
            'description': '%s added' % object._meta.object_name,
            'user': request.user,
            'request': request,
            'instance': object,
        }
        EventLog.objects.log(**log_defaults)

    def save_model(self, request, object, form, change):
        instance = form.save(commit=False)

        # setup user permission
        instance.allow_user_view, instance.allow_user_edit = form.cleaned_data['user_perms']

        # row level user
        if not change:
            instance.creator = request.user
            instance.creator_username = request.user.username
            instance.owner = request.user
            instance.owner_username = request.user.username

        # save the object
        instance.save()

        # permissions
        if not change:
            # assign permissions for selected groups
            ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], instance)
            # assign creator permissions
            ObjectPermission.objects.assign(instance.creator, instance)
        else:
            # assign permissions
            ObjectPermission.objects.remove_all(instance)
            ObjectPermission.objects.assign_group(form.cleaned_data['group_perms'], instance)
            ObjectPermission.objects.assign(instance.creator, instance)

        # notifications
        if not is_admin(request.user):
            # send notification to administrators
            recipients = get_notice_recipients('site', 'global', 'allnoticerecipients')
            if recipients:
                if notification:
                    extra_context = {
                        'object': instance,
                        'request': request,
                    }
                    notification.send_emails(recipients, notice_type, extra_context)

        return instance

admin.site.register(Image, PhotoAdmin)
