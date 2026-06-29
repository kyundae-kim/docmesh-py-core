from os import environ

from docmesh_py_core import ServiceFactoryRegistry, configure_logging, load_settings

configure_logging(force=True, env=environ)

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)

postgres = registry.create_client("postgres")
postgres.check()

registry.close_all()