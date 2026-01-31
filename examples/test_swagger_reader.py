from tools.swagger_parser import load_swagger_file, get_api_context

swagger_spec = load_swagger_file(r"examples\sample_swagger.json")
api_context = get_api_context(swagger_spec)

print(api_context)
