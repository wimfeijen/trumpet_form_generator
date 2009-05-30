# Copyright 2008 (c) Estrate

from hashlib import sha1
import hmac
from base64 import b32encode
import re
import random

def nice_hash(*args):
    """ Takes the unicode representation of every argument as input for a SHA
    hash. Returns the BASE32 encoded version of the hash to use inside URL's
    or e-mails. BASE32 is more compact then hexdigest but still case insensitive
    unlike BASE64. SHA1 is 160 bits which translates into 32 BASE32 characters."""
    h = sha1()
    for item in args:
        h.update(unicode(item))
    return b32encode(h.digest())

def nice_username(email):
    """
    When the Django user is authenticating by e-mail address then a username
    must still be used and unique. This function creates a username that is
    both readable by administrators (not just one large hash value) but still
    extremely likely to be unique.
    """
    clean_email = re.sub(r'\W', '', email.replace('@', '_')).lower()
    hash = b32encode(sha1(email + str(random.random())).digest()).strip('=').lower()
    return u'%s_%s' % (clean_email[:20], hash[:6])

def hotp(secret, count, digits=None):
    """
    Calculates the HOTP value for a counter + a secret.
    The secret must be a string with a secret key.
    Counter must be an integer.
    Digits determines the number for digits returned, 6 is the default.
    See http://www.ietf.org/rfc/rfc4226.txt for the HOTP standard.

    A test is included at the bottom of this file.
    """
    if not digits:
        digits = 6

    count_hex = '%x' % count

    count_hex = '0' * (16-len(count_hex)) + count_hex

    result = ""
    for i in xrange(0, 8):
        result += count_hex[i*2:i*2+2].decode('hex')

    hash = hmac.new(secret, result, digestmod=sha1).hexdigest()

    offset = int(hash[-1], 16)

    part = hash[(offset*2):(offset*2)+8]

    part_int = int(part, 16) & int("7fffffff", 16)

    return part_int % 10**digits

def add_message(request, msg, style_class=None):
    if not style_class:
        style_class = ''
    new_msg = {unicode(msg): {'msg': unicode(msg), 'class': unicode(style_class)}}
    try:
        request.session['cms_messages'].update(new_msg)
    except (KeyError, AttributeError):
        # KeyError -> no cms_messages key
        # AttributeError -> cms_messages doesn't contain a dictionary
        request.session['cms_messages'] = new_msg

def get_translated_attribute(actual_object, attribute_name, translated):
    """ Helper function for translate_content template tag.
    This function returns the translation of an attribute of an object.
    The "translated" argument must be a queryset of all the translated
    versions (only in the desired language) of the actual object.
    """
    from django.conf import settings
    if len(settings.LANGUAGES) > 1 and translated.count() and hasattr(translated[0], attribute_name):
        return getattr(translated[0], attribute_name)
    elif hasattr(actual_object, attribute_name):
        return getattr(actual_object, attribute_name)
    else:
        return None

html_comments = re.compile(u'<!--.*?-->')

def clean_tinymce(input):
    """ Clean the input from TinyMCE. This could correct bugs in TinyMCE
    or just removes unnecessary HTML (like comments).
    """
    result = input
    result = result.replace(u'<#document-fragment>', u'') # A strange bug that the NIVE client experiences but that we can't reproduce.
    result = result.replace(u'&lt;#document-fragment&gt;', u'') # A strange bug that the NIVE client experiences but that we can't reproduce.
    result = html_comments.sub(u'', result)
    return result

if __name__ == '__main__':
    print 'HOTP test: print values for first 10 codes and check with values in http://www.ietf.org/rfc/rfc4226.txt :'
    secret = '12345678901234567890'
    count = 0
    digits = 6
    for count in xrange(0, 1000):
        value = hotp(secret, count, digits)
        print '%04d    %06d' % (count, value) 
