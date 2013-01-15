from webhelpers.html.tags import *
from webhelpers.html.tags import __all__
from webhelpers.html import tags, HTML
from webhelpers.misc import NotGiven


# Override Webhelpers text field to support html5 input types
def text(name, value=None, id=NotGiven, **attrs):
    """Create a standard text field.

    ``value`` is a string, the content of the text field.

    ``id`` is the HTML ID attribute, and should be passed as a keyword
    argument.  By default the ID is the same as the name filtered through
    ``_make_safe_id_component()``.  Pass None to suppress the
    ID attribute entirely.


    Options:

    * ``disabled`` - If set to True, the user will not be able to use
        this input.
    * ``size`` - The number of visible characters that will fit in the
        input.
    * ``maxlength`` - The maximum number of characters that the browser
        will allow the user to enter.

    The remaining keyword args will be standard HTML attributes for the tag.

    """
    field_type = attrs.get('type', "text")
    tags._set_input_attrs(attrs, field_type, name, value)
    tags._set_id_attr(attrs, id, name)
    tags.convert_boolean_attrs(attrs, ["disabled"])
    return HTML.input(**attrs)
