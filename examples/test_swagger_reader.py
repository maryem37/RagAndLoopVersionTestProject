from tools.swagger_parser import load_swagger_file, get_api_context_multi

swagger_auth = load_swagger_file("examples/sample_swagger1.json.json")
swagger_leave = load_swagger_file("examples/sample_swagger2.json.json")

swagger_specs = {
    "auth": swagger_auth,
    "leave": swagger_leave
}

api_context = get_api_context_multi(swagger_specs)
print(api_context)
