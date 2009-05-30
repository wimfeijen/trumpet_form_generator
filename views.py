import csv, pickle, re
from datetime import datetime, timedelta

from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import loader, RequestContext, Template
from django import forms
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_str, force_unicode
from django.utils.safestring import mark_safe

from models import AutoForm

def show_form(request, identifier):
    try:
        autoform = AutoForm.objects.visible().get(identifier=identifier)
    except AutoForm.DoesNotExist:
        raise Http404('Form does not exist')
    if not autoform.get_permission(request.user):
        return HttpResponseRedirect('%s?next=%s' % (settings.LOGIN_URL, autoform.get_absolute_url()))

    class CustomForm(forms.Form):
        def __init__(self, *args, **kwargs):
            super(CustomForm, self).__init__(*args, **kwargs)
            self._autoform = autoform
            for field in autoform.autoformfield_set.all():
                self.fields[field.field_name()] = field.form_field()
            self.base_fields = self.fields

    if request.method == 'POST':
        form = CustomForm(request.POST)
        if form.is_valid():
            autoform.process(form.cleaned_data, request.META)
            return HttpResponseRedirect('./success/')
    else:
        form = CustomForm()

    template = loader.get_template('autoform/base.html')
    context = RequestContext(request,{'title': autoform.name, 'autoform': autoform, 'form': form})
    return HttpResponse(template.render(context))
    
def show_success(request, identifier):
    try:
        autoform = AutoForm.objects.visible().get(identifier=identifier)
    except AutoForm.DoesNotExist:
        raise Http404('Form does not exist')
    if not autoform.get_permission(request.user):
        return HttpResponseRedirect('/accounts/login/?next=%s' % autoform.get_absolute_url())
    template = loader.get_template('autoform/success.html')
    context = RequestContext(request,{'title': autoform.name, 'autoform': autoform, 'media_url': settings.MEDIA_URL})
    return HttpResponse(template.render(context))
        
        
def make_copy(request, id):
    """Create an exact copy of the object with the exact same fields attached to it. This view is used from the admin page."
    """
    autoform = AutoForm.objects.get(id=int(id))
    fields = autoform.autoformfield_set.all()
    autoform.id = None
    
    old_identifier = autoform.identifier
    unique = False
    counter = 1
    while not unique and counter < 100:
        autoform.identifier = '%s-%s' % (old_identifier[:46], counter)
        try:
            x = AutoForm.objects.get(identifier=autoform.identifier)
        except AutoForm.DoesNotExist:
            unique = True
        else:
            counter += 1
    autoform.name = u'%s %s' % (autoform.name[:46], counter)
        
    autoform.save()
    for field in fields:
        field.id = None
        autoform.autoformfield_set.add(field)
    return HttpResponseRedirect('/admin/autoform/autoform/')
make_copy = staff_member_required(make_copy)

def download_csv(request, identifier, selection):
    """
    Selection can be:
     * all
     * last7days
     * last30days
     * thisyear
     * lastyear
    """
    autoform = AutoForm.objects.get(identifier=identifier)
    fields = autoform.autoformfield_set.all()
    if selection == 'last7days':
        results = autoform.autoformresult_set.filter(submit_timestamp__gte = datetime.now()-timedelta(days=7))
    elif selection == 'last30days':
        results = autoform.autoformresult_set.filter(submit_timestamp__gte = datetime.now()-timedelta(days=30))
    elif selection == 'thisyear':
        results = autoform.autoformresult_set.filter(submit_timestamp__year = datetime.now().year)
    elif selection == 'lastyear':
        results = autoform.autoformresult_set.filter(submit_timestamp__year = datetime.now().year-1)
    elif selection == 'all':
        results = autoform.autoformresult_set.all()
    else:
        raise Http404('Invalid selection.')

    response = HttpResponse(mimetype='text/csv')
    
    if results.count():
        writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_ALL)
        # write field names
        row = [smart_str(_('date time'))]
        for field in fields:
            row.append(smart_str(field.name))
        writer.writerow(row)
        # write registrations
        for r in results:
            dict = pickle.loads(smart_str(r.content, 'latin1'))
            row = [r.submit_timestamp.strftime('%Y-%m-%dT%H:%M')]
            for field in fields:
                if dict.get(field.name):
                    row.append(smart_str(dict.get(field.name), 'utf8'))
                else:
                    row.append('')
            writer.writerow(row)
        return response
    else:
        return HttpResponse(_('Resultset is empty.'))
download_csv = staff_member_required(download_csv)
