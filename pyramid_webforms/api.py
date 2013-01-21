# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import copy
import inspect

import six
import formencode
from webhelpers.html import literal, tags
from pyramid.renderers import render
from pyramid.httpexceptions import exception_response
from pyramid.mako_templating import MakoRendererFactoryHelper
from pyramid.i18n import get_localizer, TranslationString, TranslationStringFactory



_ = original_gettext = TranslationStringFactory('pyramid_webforms')
forms_renderer_factory = MakoRendererFactoryHelper('p_wf_mako.')


class FormencodeState(object):
    """"Dummy" state class for formencode"""
    # This is the only possible way to make
    # formencode i18n messages session-related.
    # Each form validator should receive an
    # instance of FormencodeState with the "_"
    # attribute as an i18n-translator.
    _ = staticmethod(original_gettext)

    def __init__(self, **kwargs):
        for arg in kwargs:
            self.__dict__[arg] = kwargs[arg]


class PrototypeSchema(formencode.Schema):
    allow_extra_fields = True
    filter_extra_fields = True


class CSRFTokenValidator(formencode.validators.UnicodeString):
    not_empty = True
    strip = True

    def validate_python(self, value, state):
        super(CSRFTokenValidator, self).validate_python(value, state)
        request = state.request
        token = request.session.get_csrf_token()
        if token != value:
            localizer = get_localizer(request)
            raise formencode.Invalid(localizer.translate(_('Invalid CSRF token.')), value, state)


CSRF_TOKEN_KEY = "_at"
CSRF_TOKEN_FIELD = {
    'type': 'hidden',
    'value': '',
    'validator':CSRFTokenValidator
}


csrf_detected_message = ("Cross-site request forgery detected, request denied. See "
                         "http://en.wikipedia.org/wiki/Cross-site_request_forgery for more "
                         "information.")


def authenticated_form(request):
    submitted_token = request.POST.get(CSRF_TOKEN_KEY)
    token = request.session.get_csrf_token()
    return submitted_token is not None and submitted_token == token


def authenticate_form(func):
    def inner(context, request):
        if not request.POST:
            return func(context, request)
        if authenticated_form(request):
            return func(context, request)
        raise exception_response(403, detail=csrf_detected_message)
    return inner


def _secure_form(action, method="POST", multipart=False, **kwargs):
    """Start a form tag that points the action to an url. This
    form tag will also include the hidden field containing
    the auth token.

    The ``action`` option should be given either as a string, or as a
    ``request.route_url()`` function. The method for the form defaults to POST.

    Options:

    ``multipart``
        If set to True, the enctype is set to "multipart/form-data".
    ``method``
        The method to use when submitting the form, usually either
        "GET" or "POST". If "PUT", "DELETE", or another verb is used, a
        hidden input with name _method is added to simulate the verb
        over POST.

    """
    #token = request.session.get_csrf_token()
    #token = hidden(CSRF_TOKEN_KEY, token)
    #token = HTML.div(token, style="display:none;")
    #token = ''
    #form = tags.form(action, method, multipart, **kwargs)
    #return literal("{}\n{}".format(form, token))
    return literal(tags.form(action, method, multipart, **kwargs))


class FieldError(Exception):
    pass


class DeclarativeMeta(type):
    def __new__(mcs, class_name, bases, new_attrs):
        cls = type.__new__(mcs, class_name, bases, new_attrs)
        cls.__classinit__.__func__(cls, new_attrs)
        return cls


FORM_ATTRIBUTES_RE = re.compile("_[a-z0-9][a-z0-9_]*[a-z0-9]_", re.IGNORECASE)
ACTION_CALL_SAME_VIEW = ''


class Form(object):
    __metaclass__ = DeclarativeMeta
    _fields = {}
    _hidden = {}
    _params = {
        'fieldsets': [],
        'filter': [],
        'validation_schema': None,
        'method': 'post'
    }
    Invalid = formencode.Invalid

    def __classinit__(self, new_attrs):
        self._fields = copy.copy(self._fields)
        self._hidden = copy.copy(self._hidden)
        # We should create deepcopy here because we have nested
        # mutable objects inside _params.
        self._params = copy.deepcopy(self._params)

        for name, val in new_attrs.items():
            if (name.startswith('__') or inspect.ismethod(val) or
                isinstance(val, classmethod) or val is formencode.Invalid):
                continue

            elif FORM_ATTRIBUTES_RE.match(name):
                if name == '_fieldsets_':
                    self._params['fieldsets'] = self._compose_fieldsets(val)
                else:
                    self._params[name[1:-1]] = val

            else:
                if val.get('type') == 'hidden':
                    self._hidden[name] = val
                else:
                    self._fields[name] = val

        # Remove filtered fields
        for item in self._params['filter']:
            try:
                self._fields.pop(item)
            except KeyError:
                self._hidden.pop(item)

            for fieldset in self._params['fieldsets']:
                new_fields_list = []
                for idx, field in enumerate(fieldset['fields']):
                    if field != item:
                        new_fields_list.append(field)
                fieldset['fields'] = new_fields_list
            # Clear cls._params['filter'] in order to properly handle
        # inheritance of filtered forms (otherwise
        # cls._fields.pop(item) will raise KeyError on inherited forms).
        self._params['filter'] = []

        # Add CSRF token field to all POST forms
        if self._params.get('method', 'post') == 'post':
            if CSRF_TOKEN_KEY not in self._hidden:
                self._hidden[CSRF_TOKEN_KEY] = CSRF_TOKEN_FIELD
        else:
            if CSRF_TOKEN_KEY in self._hidden:
                del self._hidden[CSRF_TOKEN_KEY]

        # Generate validation schema
        self._params['validation_schema'] = self._compose_validator()


    @classmethod
    def _compose_fieldsets(cls, val):
        fieldsets = []
        for fieldset in val:
            data = {}
            for item in fieldset:
                if isinstance(item, TranslationString):
                    data['name'] = item
                elif isinstance(item, six.string_types):
                    data['optional'] = item == 'optional'
                elif isinstance(item, list):
                    data['fields'] = item
                else:
                    continue
            fieldsets.append(data)
        return fieldsets


    @classmethod
    def _compose_validator(cls):
        schema = PrototypeSchema()
        for name in cls._fields:
            # Fields without validators cannot be retrieved
            # in controllers.
            validator = cls._fields[name].get('validator')
            if validator:
                schema.add_field(name, validator)
        for name in cls._hidden:
            validator = cls._hidden[name].get('validator')
            if validator:
                schema.add_field(name, validator)

        # Add chained validators if needed
        chained_validators = cls._params.pop('chained_validators', [])
        for validator in chained_validators:
            schema.add_chained_validator(validator)
        return schema


    @classmethod
    def validate(cls, request, state=None):
        if cls._params['method'] == 'post':
            data = request.POST
        elif cls._params['method'] == 'get':
            data = request.GET
        else:
            data = request.params

        if state is None:
            state = FormencodeState(request=request)

        data = cls._params['validation_schema'].to_python(data, state)
        return data


    def __init__(self, data=None):
        if data is None:
            data = {}
        self.data = data
        self._cached_parts = {}


    def __call__(self, request, part='all'):
        localizer = get_localizer(request)
        # Explicitly add CSRF token value to data dict if form is POST
        if self._params.get('method', 'post') == 'post':
            self.data[CSRF_TOKEN_KEY] = {'value': request.session.get_csrf_token()}
            # Prepare buttons
        if self._cached_parts.get('buttons') is None:
            alternate_url = self._params.get('alternate_url', '')
            if alternate_url:
                if isinstance(alternate_url, dict):
                    url_kw = copy.copy(alternate_url)
                    name = url_kw.pop('name', None)
                    alternate_url = request.route_path(name, **url_kw)

                template_path = request.registry.settings.get(
                    'pyramid_webforms.submit_alternate_tpl',
                    'pyramid_webforms:templates/submit_alternate.p_wf_mako'
                )
                submit_btn = render(
                    template_path,
                    {
                        'submit_text': self._params.get('submit_text', localizer.translate(_('Submit'))),
                        'or_text': self._params.get('or_text', localizer.translate(_('or'))),
                        'alternate_url': alternate_url,
                        'alternate_text': self._params.get('alternate_text', '')
                    },
                    request
                )
            else:
                template_path = request.registry.settings.get(
                    'pyramid_webforms.submit_tpl',
                    'pyramid_webforms:templates/submit.p_wf_mako'
                )
                submit_btn = render(
                    template_path,
                    {'submit_text': self._params.get('submit_text', localizer.translate(_('Submit')))},
                    request
                )
            self._cached_parts['buttons'] = literal(submit_btn)

        # Prepare fields
        if self._cached_parts.get('fields') is None:
            output = []
            for fields in self._params['fieldsets']:
                output.append(self._generate_fields(request, fields, self.data))
            self._cached_parts['fields'] = literal(''.join(output))

        # Prepare form attributes
        if self._cached_parts.get('attributes') is None:
            # try to get action url from instance data
            action = self.data.get('_action_')
            if action is None:
                action_params = self._params.get('action', {})
                if action_params:
                    url_kw = copy.copy(action_params)
                    name = url_kw.pop('name', None)
                    action = request.route_path(name, **url_kw)
                else:
                    action = ACTION_CALL_SAME_VIEW

            hidden_fields = []
            for name, data in self._hidden.items():
                value = self.data.get(name, {}).get('value', data.get('value'))
                hidden_fields.append(tags.__dict__['hidden'](name, value))

            self._cached_parts['attributes'] = literal('{}{}'.format(
                _secure_form(
                    action,
                    id=self._params.get('id'),
                    class_=self._params.get('class'),
                    method=self._params.get('method', 'post'),
                    multipart=self._params.get('multipart'),
                    target=self._params.get('target'),
                    style=self._params.get('style'),
                    **self._params.get('html5_attrs', {})
                ),
                ''.join(hidden_fields)
            ))

        # Prepare form footer
        if self._cached_parts.get('footer') is None:
            self._cached_parts['footer'] = literal('</form>')

        if part == 'attributes':
            return self._cached_parts['attributes']
        elif part == 'fields':
            return self._cached_parts['fields']
        elif part == 'buttons':
            return self._cached_parts['buttons']
        elif part == 'footer':
            return self._cached_parts['footer']
        else:
            # part == 'all'
            template_path = request.registry.settings.get(
                'pyramid_webforms.form_tpl',
                'pyramid_webforms:templates/form.p_wf_mako'
            )
            return literal(
                render(
                    template_path,
                    {
                        'attributes': self._cached_parts['attributes'],
                        'fields': self._cached_parts['fields'],
                        'buttons': self._cached_parts['buttons'],
                        'footer': self._cached_parts['footer']
                    },
                    request
                )
            )

    @classmethod
    def _generate_fields(self, request, fields_list, override_data):
        html = []
        for name in fields_list['fields']:
            field = self._fields[name]

            values = {'with_tip':self._params.get('with_tip', True)}
            values.update(field)
            data = override_data.get(name, {})
            values.update(data)

            values.pop('validator', None)
            input = InputField(name=name, **values)
            html.append(input(request))

        # Don't show empty fieldsets
        if not html:
            return ''

        caption = fields_list.get('name', '')
        template_path = request.registry.settings.get(
            'pyramid_webforms.fieldset_tpl',
            'pyramid_webforms:templates/fieldset.p_wf_mako'
        )
        return literal(
            render(
                template_path,
                {
                    'caption': caption,
                    'fields': literal(''.join(html))
                },
                request
            )
        )


class InputField(object):
    tag_types = {
        'date': 'text'
    }
    def __init__(self, type='html', name='', value=None, selected=False,
                 title='', tip='', **kw):
        if type != 'html':
            try:
                assert type in tags.__dict__
            except AssertionError:
                if type not in self.tag_types:
                    raise FieldError('HTML field type "{}" is not supported by '
                                     'webhelpers package'.format(type))
        self.type = type
        self.tag_type = self.tag_types.get(type, type)
        self.name = name
        self.value = value
        self.selected = selected
        self.title = title
        self.tip = tip
        self.kw = kw

    def _prepare_date(self):
        return self._prepare_text()

    def _prepare_textarea(self):
        kwargs = {
            'name': self.name,
            'id': self.kw.get('id'),
            'class_': self.kw.get('class', ''),
            'content': self.value,
            'cols': self.kw.get('cols', 30),
            'rows': self.kw.get('rows', 7),
            'wrap': self.kw.get('wrap', 'SOFT'),
            'required': self.kw.get('required', None)
        }
        return kwargs

    def _prepare_select(self):
        return {
            'name': self.name,
            'id': self.kw.get('id'),
            'class_': self.kw.get('class', ''),
            'selected_values': self.value,
            'options': self.kw.get('options'),
            'multiple': self.kw.get('multiple', False)
        }

    def _prepare_text(self):
        return {
            'name': self.name,
            'type': self.type,
            'id': self.kw.get('id'),
            'class_': self.kw.get('class', ''),
            'value': self.value,
            'size': self.kw.get('size'),
            'maxlength': self.kw.get('maxlength'),
            'required': self.kw.get('required', None)
        }

    def _prepare_password(self):
        kwargs = self._prepare_text()
        kwargs['type'] = 'password'
        return kwargs

    def _prepare_checkbox(self):
        if self.value is None:
            value = 1
        else:
            value = self.value
        return {
            'name': self.name,
            'id': self.kw.get('id'),
            'class_': self.kw.get('class', ''),
            'value': value,
            'checked': self.selected,
            }

    def _prepare_file(self):
        return {
            'name': self.name,
            'id': self.kw.get('id'),
            'class_': self.kw.get('class', ''),
            'multiple': self.kw.get('multiple') and 'multiple'
        }


    def __call__(self, request, name=None, value=None, selected=None,
                 title=None, tip=None, data=None, **kwargs):
        # self.kw is global so we need thread-local kw dictionary here
        kw = {}
        if data is None:
            data = {}
        if title is None:
            title = self.title
        if tip is None:
            tip = self.tip

        if self.type == 'html':
            input = value or self.value
        else:
            kw.update(self.kw)
            kw.update(**data)

            if name is None:
                name = self.name

            kwargs = self.__getattribute__('_prepare_{}'.format(self.type))()
            with_tip = self.kw.get('with_tip', kwargs.get('with_tip', True))
            kwargs['class_'] = '{var}{const}'.format(
                var=kwargs.get('class_', self.type),
                const=(with_tip and ' with-tip' or '')
            )
            kwargs.update(self.kw.get('html5_attrs', {}))
            input = tags.__dict__[self.tag_type](**kwargs)

        extra_html = literal(kw.pop('extra_html', ''))
        tip_escape = kw.pop('tip_escape', False)
        input_only = kw.pop('input_only', False)

        if input_only:
            # input is already a literal type
            return input

        error = request.tmpl_context.form_errors.get(name, '')
        if error:
            error = field_error(request, error)
        template_path = request.registry.settings.get(
            'pyramid_webforms.field_tpl',
            'pyramid_webforms:templates/field.p_wf_mako'
        )
        return literal(
            render(template_path,
                {
                    'name': name,
                    'title': title,
                    'error_message': error,
                    'input': input,
                    'tip': self.tooltip(request, tip, tip_escape),
                    'extras': extra_html
                },
                request
            )
        )


    def tooltip(self, request, tip='', escape_html=True):
        """Render a tip for current field"""
        if not tip:
            return ''
        if not escape_html:
            tip = literal(tip)
        template_path = request.registry.settings.get(
            'pyramid_webforms.tooltip_tpl',
            'pyramid_webforms:templates/tooltip.p_wf_mako'
        )
        return literal(
            render(template_path,
                {'tip': tip},
                request
            )
        )


def form_errors(request):
    if request.tmpl_context.form_errors:
        template_path = request.registry.settings.get(
            'pyramid_webforms.form_error_tpl',
            'pyramid_webforms:templates/form_error.p_wf_mako'
        )
        localizer = get_localizer(request)
        return literal(
            render(template_path,
                {'error_message': localizer.translate(_("Please correct your input parameters."))},
                request
            )
        )
    return ''


def field_error(request, error):
    template_path = request.registry.settings.get(
        'pyramid_webforms.field_error_tpl',
        'pyramid_webforms:templates/field_error.p_wf_mako'
    )
    localizer= get_localizer(request)
    return literal(
        render(template_path,
            {'label': localizer.translate(_('Error')), 'text': error},
            request
        )
    )
