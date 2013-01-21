Simple declarative web forms using FormEncode and WebHelpers
==============================================

Status: **Early Development, Unstable, Unpublished**.

Python Version: **2.7** (please contribute to `FormEncode Project`_ in order to make it 3.x compatible).

Installation
--------------

.. code-block:: bash

   pip install pyramid_webforms


Example
-------------

Consider the following pyramid project structure:

.. code-block:: plain

    my_pyramid_app/
        modules/
            signin/
                __init__.py
                forms.py
                validators.py
                views.py
            __init__.py
        templates/
            signin.mako
        __init__.py

Let's define a sign-in form, its fields, and validators.

.. code-block:: python

    # my_pyramid_app/modules/signin/forms.py
    from pyramid_webforms import Form
    from my_pyramid_app.i18n import _
    from . import validators


    login_or_email = {
        'type': 'text',
        'title': _('Login or Email'),
        'tip': _('Please enter your login or email that was used during your registration.'),
        'size': 30,
        'maxlength': 50,
        'validator': validators.UserLoginOrEmail
    }

    password = {
        'type': 'password',
        'title': _('Password'),
        'tip': _('A password can contain any character of any alphabet (minimum is 1, maximum is 64 characters). '
                 'For reliability we recommend using non-trivial and long passwords. Note that the case of '
                 'the letters matters.'),
        'size': 30,
        'maxlength': 64,
        'validator': validators.UserPassword,
        'value': '',
    }

    remember_me = {
        'type': 'checkbox',
        'title': _('Remember me'),
        'tip': _('Set this checkbox if you want your current browser to keep '
                 'your session for further visits.'),
        'selected': False,
        'validator': validators.RememberUserSession
    }

    class SignInForm(Form):
        # form attributes and metadata
        _id_ = 'signin-form'
        _submit_text_ = _('Sign in')
        _alternate_url_ = {'name': 'support.account_access'}
        _alternate_text_ = _("I cannot access my account")
        _fieldsets_ = [
            [['login_email', 'password', 'remember_me']]
        ]
        # form fields
        login_email = login_or_email
        password = password
        remember_me = remember_me


.. code-block:: python

    # my_pyramid_app/modules/signin/validators.py
    import re
    import formencode

    # logins are 3-16 characters long
    USERLOGINS = re.compile('[A-Za-z0-9][-A-Za-z0-9]{1,14}[A-Za-z0-9]', re.IGNORECASE)

    RememberUserSession = formencode.validators.Bool

    class UserLogin(formencode.validators.Regex):
        not_empty = True
        strip = True
        regex = USERLOGINS

    class UserEmail(formencode.validators.Email):
        not_empty = True
        strip = True
        max = 50
        def _to_python(self, email, state):
            email = super(UserEmail, self)._to_python(email, state)
            return email.lower()

    class UserLoginOrEmail(UserLogin):
        def _to_python(self, value, state):
            if '@' in value:
                validator = UserEmail
            else:
                validator = UserLogin
            value = validator.to_python(value, state)
            return value

        def validate_python(self, value, state):
            pass


    class UserPassword(formencode.validators.UnicodeString):
        not_empty = True
        max = 64


Now we can use our form in pyramid view callables.

.. code-block:: python

    # my_pyramid_app/modules/signin/views.py
    from pyramid.view import view_config
    from .forms import SignInForm


    class SignInView(object):

        @view_config(route_name='session.signin', renderer='templates/signin.mako')
        def signin_form(self):
            request = self.request
            if request.POST:
                try:
                    form = SignInForm.validate(request)
                except SignInForm.Invalid as error:
                    # redirect or error handling
                    pass
                else:
                    # sign in user using form data
                    pass

            return {'signin_form': forms.SignInForm()}


.. code-block:: mako

    ## my_pyramid_app/templates/signin.mako
    ${signin_form(request)}



Here are the key conceptual points:

- form fields are defined with plain dictionaries;
- the fields can be reused by any other module;
- each field record contains an assigned FormEncode-based validator;
- a form is defined with the simple declarative interface.


Configuration options
-----------------------

+---------------------------------------+------------+----------------------------------------------------------+
| Key                                   | Type       | Default                                                  |
+=======================================+============+==========================================================+
| pyramid_webforms.submit_tpl           | str        | pyramid_webforms:templates/submit_alternate.p_wf_mako    |
+---------------------------------------+------------+----------------------------------------------------------+
| pyramid_webforms.submit_alternate_tpl | str        | pyramid_webforms:templates/submit_alternate.p_wf_mako    |
+---------------------------------------+------------+----------------------------------------------------------+
| pyramid_webforms.form_tpl             | str        | pyramid_webforms:templates/form.p_wf_mako                |
+---------------------------------------+------------+----------------------------------------------------------+
| pyramid_webforms.fieldset_tpl         | str        | pyramid_webforms:templates/fieldset.p_wf_mako            |
+---------------------------------------+------------+----------------------------------------------------------+
| pyramid_webforms.field_tpl            | str        | pyramid_webforms:templates/field.p_wf_mako               |
+---------------------------------------+------------+----------------------------------------------------------+
| pyramid_webforms.tooltip_tpl          | str        | pyramid_webforms:templates/tooltip.p_wf_mako             |
+---------------------------------------+------------+----------------------------------------------------------+
| pyramid_webforms.form_error_tpl       | str        | pyramid_webforms:templates/form_error.p_wf_mako          |
+---------------------------------------+------------+----------------------------------------------------------+
| pyramid_webforms.field_error_tpl      | str        | pyramid_webforms:templates/field_error.p_wf_mako         |
+---------------------------------------+------------+----------------------------------------------------------+


See also
============

- `FormEncode Project`_
- `WebHelpers Project`_


.. _FormEncode Project: https://github.com/formencode/formencode
.. _WebHelpers Project: http://sluggo.scrapping.cc/python/WebHelpers/index.html
