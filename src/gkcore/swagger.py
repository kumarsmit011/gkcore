import os

def includeme(config):
    config.include("pyramid_openapi3")
    config.pyramid_openapi3_spec_directory(
        os.path.join(os.path.dirname(__file__), "spec/main.yaml"), route="/spec"
    )
    # launch the swagger ui at /docs/
    config.pyramid_openapi3_add_explorer(route="/docs/", ui_version="5.1.0")
