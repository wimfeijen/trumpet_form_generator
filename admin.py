from cms.autoform.models import AutoForm, AutoFormField
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

class AutoFormField_Inline(admin.StackedInline):
    model = AutoFormField

class AutoFormOptions(admin.ModelAdmin):
    inlines = [AutoFormField_Inline]
    list_display = ('name', 'email_to', 'is_active', 'url', 'copy', 'download_csv')
    prepopulated_fields = {'identifier': ('name',)}
    filter_horizontal = ('allowed_groups',)
    class Media:
        js = (
            settings.ADMIN_MEDIA_PREFIX + 'tinymce3/tiny_mce.js',
            settings.ADMIN_MEDIA_PREFIX + 'cms/js/page_tinymce.js',
        )

admin.site.register(AutoForm, AutoFormOptions)

