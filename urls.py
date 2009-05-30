from django.conf.urls.defaults import *

urlpatterns = patterns('cms.autoform.views',
    (r'^(?P<identifier>[a-z0-9\-]+)/$', 'show_form'),
    (r'^(?P<identifier>[a-z0-9\-]+)/success/$', 'show_success'),
    (r'^copy/(?P<id>\d+)/$', 'make_copy'),
    (r'^csv/(?P<identifier>[a-z0-9\-]+)-(?P<selection>last7days|last30days|thisyear|lastyear|all)\.csv$', 'download_csv'),
)
