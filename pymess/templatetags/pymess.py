from urllib.parse import urlencode

import functools

from django import template
from django.conf import settings
from django.template.base import Node, TemplateSyntaxError, render_value_in_context
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.html import format_html

register = template.Library()


class RaiseIfNoneNode(Node):

    def __init__(self, variable_name, email_slug, check_variable, assign_to):
        self.variable_name = variable_name
        self.email_slug = email_slug
        self.check_variable = check_variable
        self.assign_to = assign_to

    def render(self, context):
        value = self.variable_name.resolve(context)
        if not value and not self.check_variable.resolve(context):
            raise ValueError('Email with slug {} missing variable named {}'.format(self.email_slug.resolve(context),
                                                                                   force_text(self.variable_name)))
        if not value:
            value = '{{{{ {} }}}}'.format(force_text(self.variable_name))

        if self.assign_to:
            context[self.assign_to] = render_value_in_context(value, context)
            return ''
        else:
            return render_value_in_context(value, context)

    def __repr__(self):
        return '<SnippetNode>'


@register.tag
def get_or_raise(parser, token):
    bits = token.split_contents()
    assign_to = None
    if len(bits) == 4 and bits[2] == 'as':
        assign_to = bits[3]
    elif len(bits) != 2:
        raise TemplateSyntaxError("%r tag takes one argument: the rendered value" % bits[0])
    variable_name = parser.compile_filter(bits[1])
    check_variable = parser.compile_filter('EMAIL_DISABLE_VARIABLE_VALIDATOR')
    email_slug = parser.compile_filter('EMAIL_SLUG')
    return RaiseIfNoneNode(variable_name, email_slug, check_variable, assign_to)


def check_tag_arguments(f):
    """
    Decorator that checks that all arguments of a simple tag are defined.

    Raises:
        ValueError if any argument is None or empty string.
    """
    @functools.wraps(f)
    def wrapper_decorator(context, **kwargs):
        for k, v in kwargs.items():
            if not context.get('EMAIL_DISABLE_VARIABLE_VALIDATOR') and (v is None or v == ''):
                raise ValueError(
                    'Tag "{tag}" in email slug "{slug}" received an empty argument "{arg}" ({kwargs})'.format(
                        tag=f.__name__,
                        slug=context.get('EMAIL_SLUG'),
                        arg=k,
                        kwargs=kwargs
                    )
                )
        return f(context, **kwargs)
    return wrapper_decorator
