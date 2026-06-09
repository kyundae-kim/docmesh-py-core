from docmesh_py_core import ServiceFactoryRegistry, Settings

settings = Settings()
registry = ServiceFactoryRegistry(settings=Settings())
client = registry.create_client("keycloak")
print(client.check())
