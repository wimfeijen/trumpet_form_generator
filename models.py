"""
Copyright (c) 2006, 2007, 2008 Estrate
http://www.estrate.nl/
"""
from datetime import datetime
import pickle, os, re
from sets import Set

phone_regex = re.compile(r'^[0-9+\-() ]*$')

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.utils.encoding import smart_unicode, force_unicode
from django.contrib.sites.models import Site
from django import forms

from cms.utils import clean_tinymce

class AutoFormManager(models.Manager):
    def visible(self):
        return self.filter(is_active=True, effective_at__lte=datetime.now()).filter(Q(expire_at__isnull=True)|Q(expire_at__gte=datetime.now()))

class AutoForm(models.Model):
    name = models.CharField(_('name'), max_length=50)
    identifier = models.SlugField(_('identifier'), help_text=_('Don\'t touch this, unless you know the purpose.'), unique=True, db_index=True)
    intro_text = models.TextField(_('intro text'), blank=True, help_text=_('This text is shown above the form.'))
    submit_text = models.TextField(_('submit text'), blank=True, help_text=_('This text is shown above the submit button.'))
    success_text = models.TextField(_('success text'), help_text=_('This text is shown when the form is successfully submitted.'))
    email_to = models.CharField(_('e-mail to'), max_length=200, blank=True, help_text=_('Send to form to these e-mailaddress. Seperate multiple e-mailaddress by comma\'s.'))
    effective_at = models.DateTimeField(_('effective at'), default=datetime.now, help_text=_('Put online at this moment.'), db_index=True)
    expire_at = models.DateTimeField(_('expire at'), null=True, blank=True, help_text=_('Put offline at this moment, or leave empty to keep it online forever.'), db_index=True)
    template = models.FilePathField(_('template'), path=settings.TEMPLATE_DIRS[0], match='.html')
    template_name = models.CharField(_('template name'), max_length=50, editable=False, blank=True)
    is_active = models.BooleanField(_('is active'), default=True, db_index=True)
    allowed_groups = models.ManyToManyField(Group, verbose_name=_('allowed groups'), blank = True, null = True, help_text=_('Leave empty if it\'s a public form.'))

    objects = AutoFormManager()

    class Meta:
        verbose_name = _('autoform')
        verbose_name_plural = _('autoforms')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return '/autoform/%s/' % self.identifier
   
    def url(self):
        return u'<a href="http://%s%s">[link]</a>' % (Site.objects.get_current().domain, self.get_absolute_url())
    url.allow_tags = True
   
    def save(self):
        self.identifier = self.identifier.lower()
        self.template_name = os.path.basename(self.template)
        self.intro_text = clean_tinymce(self.intro_text)
        self.submit_text = clean_tinymce(self.submit_text)
        self.success_text = clean_tinymce(self.success_text)
        super(AutoForm, self).save()

    def process(self, cleaned_data, meta_headers):
        email_result = []
        result = {}
        for field in self.autoformfield_set.all():
            email_result.append(u'%s: %s' % (field.name, cleaned_data.get(field.field_name(), '-')))
            result[field.name] = cleaned_data.get(field.field_name())
        if self.email_to:
            subject = _(u'A message from your online form: %s' % self.name)
            send_mail(force_unicode(subject), u'\n\n'.join(email_result), settings.DEFAULT_FROM_EMAIL, self.email_to.split(u','))
        meta_headers = [u'%s: %s' % (key, meta_headers[key]) for key in meta_headers.keys()]
        self.autoformresult_set.create(content=unicode(pickle.dumps(result), 'latin1'), headers=u'\n'.join(meta_headers))
    
    def get_permission(self, user):
        """Get permission for provided user
        Returns True if user has permission to see the item,
        returns False if user doesn't have permission.
        """
        if self.allowed_groups.all():
            if user.is_anonymous():
                return False
            elif user.is_superuser:
                return True
            else:
                allowed_groups = Set([item.id for item in self.allowed_groups.all()])
                user_groups = Set([item.id for item in user.groups.all()])
                matching_groups = allowed_groups.intersection(user_groups)
                if len(matching_groups)>0:
                    return True
                else:
                    return False
        else:
            return True

    def copy(self):
        """ Copy the current form to a new form
        """
        return u'<a href="/autoform/copy/%s/">[copy]</a>' % self.id
    copy.allow_tags = True
    copy.short_description = _('Copy')
    
    def download_csv(self):
        result = []
        url = u'<a href="/autoform/csv/%s-%s.csv" target="_blank">[%s]</a>'
        selections = (
            ('last7days', 'Last 7 days'),
            ('last30days',  'Last 30 days'),
            ('all', 'All'),
        )
        for selection in selections:
            result.append(url % (self.identifier, selection[0], selection[1]))
        return u'<br />'.join(result)
    download_csv.allow_tags = True
    download_csv.short_description = _('Download CSV')

AUTO_FORM_FIELD_TYPE_LIST = (
    ('text', _('text')),
    ('integer', _('integer')),
    ('email', _('e-mail')),
    ('select', _('dropdown list')),
    ('radio', _('radio bottons')),
    ('checkbox', _('checkbox')),
    ('textarea', _('large textbox')),
    ('phone', _('phone number'))
)

class AutoFormField(models.Model):
    autoform = models.ForeignKey(AutoForm, verbose_name=_('autoform'), db_index=True)
    name = models.CharField(_('name'), max_length=50)
    type = models.CharField(_('type'), choices=AUTO_FORM_FIELD_TYPE_LIST, max_length=20)
    is_required = models.BooleanField(_('is required'), default=True)
    values = models.CharField(_('possible values'), blank=True, max_length=400, help_text=_('This is only used for dropdown lists and radio buttons. Seperate the values by comma\'s.'))
    default_value = models.CharField(_('default value'), blank=True, max_length=200)
    help_text = models.CharField(_('help text'), max_length=200, blank=True, help_text=_('The help text will be displayed just below the form field.'))
   
    class Meta:
        verbose_name = _('autoform field')
        verbose_name_plural = _('autoform fields')
        ordering = ('id',)

    def __unicode__(self):
        return self.name

    def choices(self):
        result = []
        for item in self.values.split(','):
            result.append((item.lower().strip(), item.strip()))
        return result
        
    def form_field(self):
        classes = [self.type]
        if self.is_required:
            classes.append('required')
        attrs = {'class': u' '.join(classes)}
        if self.type=='text':
            return forms.CharField(label=self.name, required=self.is_required, \
                initial=self.default_value, help_text=self.help_text, \
                max_length=200, widget=forms.TextInput(attrs=attrs))
        elif self.type=='integer':
            return forms.IntegerField(label=self.name, required=self.is_required, \
                initial=self.default_value, help_text=self.help_text, \
                widget=forms.TextInput(attrs=attrs))
        elif self.type=='email':
            return forms.EmailField(label=self.name, required=self.is_required, \
                initial=self.default_value, help_text=self.help_text, \
                widget=forms.TextInput(attrs=attrs))
        elif self.type=='select':
            return forms.ChoiceField(label=self.name, choices=self.choices(), \
                required=self.is_required, initial=self.default_value.lower(), \
                help_text=self.help_text, widget=forms.Select(attrs=attrs))
        elif self.type=='radio':
            return forms.ChoiceField(label=self.name, choices=self.choices(), \
                required=self.is_required, initial=self.default_value.lower(), \
                help_text=self.help_text, widget=forms.RadioSelect(attrs=attrs))
        elif self.type=='checkbox':
            return forms.BooleanField(label=self.name, required=self.is_required, \
                initial=self.default_value or False, help_text=self.help_text, \
                widget=forms.CheckboxInput(attrs=attrs))
        elif self.type=='textarea':
            return forms.CharField(label=self.name, required=self.is_required, \
                initial=self.default_value, help_text=self.help_text, \
                max_length=2000, widget=forms.Textarea(attrs=attrs))
        elif self.type=='phone':
            return forms.RegexField(label=self.name, required=self.is_required, \
                initial=self.default_value, help_text=self.help_text, \
                regex=phone_regex, error_messages={'invalid': _('Please use only digits, "+", "-", "(" or ")".')},
                max_length=20, widget=forms.TextInput(attrs=attrs))

    def field_name(self):
        return u'field_%s' % self.id

class AutoFormResult(models.Model):
    autoform = models.ForeignKey(AutoForm, verbose_name=_('autoform'), db_index=True)
    submit_timestamp = models.DateTimeField(_('submit timestamp'), auto_now_add=True)
    content = models.TextField(_('content'), help_text=_('pickled dictionary of result.'))
    headers = models.TextField(_('HTTP headers'), blank=True)

    class Meta:
        verbose_name = _('autoform result')
        verbose_name_plural = _('autoform results')
        ordering = ('-id',)
