import re

file_path = r'C:\Bureau\Bureau\project_test\agents\test_writer.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_rules = (
    '\"STRICT RULES:\\n\"'
    '\"1. ONLY valid Java code.\\n\"'
    '\"2. Ensure parameter names and types in @Given/@When/@Then annotations match the method signatures exactly. DO NOT modify the text of the Cucumber steps when generating the annotations; use the EXACT wording passed (e.g. if the step is \\'the status is \\\\\"Pending\\\\\"\\', use @Then(\\\\\\"the status is {string}\\\\\")).\\n\"'
    '\"3. If a step involves logging in, use System.getenv(\\\\"TEST_USER_EMAIL\\\\") (defaulting to \\\\"admin@test.com\\\\") and System.getenv(\\\\"TEST_USER_PASSWORD\\\\") (defaulting to \\\\"admin123\\\\"). Extract the token as jsonPath().getString(\\\\"jwt\\\\").\\n\"'
    '\"4. If a step checks for an error message, extract it using esponse.jsonPath().getString(\\\\"error\\\\") because the API returns JSON errors (e.g. {\\\\"error\\\\": \\\\"message\\\\"}). Do NOT use esponse.getBody().asString().\\n\"'
    '\"5. For unauthorized expectations, accept both 401 and 403 status codes.\\n\"'
    '\"6. Provide ONLY the method implementations, NO markdown wrapping.\"'
)

content = re.sub(
    r'\"STRICT RULES:\\n\".*?\"4\.\s+Provide ONLY the method implementations, NO markdown wrapping\."',
    new_rules,
    content,
    flags=re.DOTALL
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated STRICT RULES successfully.')
