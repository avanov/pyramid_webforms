from .api import Form
from .api import CSRF_TOKEN_KEY
from .api import form_errors



def includeme(config):
    """Pyramid configuration entry point"""
    from .api import forms_renderer_factory
    config.add_renderer('.p_wf_mako', forms_renderer_factory)
    config.add_translation_dirs('pyramid_webforms:locale/')
