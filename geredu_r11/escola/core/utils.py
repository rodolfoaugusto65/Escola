def render_smart(request, template, context=None):
    if context is None:
        context = {}

    if request.htmx:
        context["base_template"] = "core/base_partial.html"
    else:
        context["base_template"] = "core/base.html"

    return template, context