import sys
f = r'C:\Bureau\Bureau\project_test\agents\test_writer.py'
txt = open(f, 'r', encoding='utf-8').read()
old = 'not "token").\\n"'
new = old + '\n              "3.5. If the step says \'the system blocks the action\', assert that the response status code is 400, 401 or 403.\\n"\n              "3.6. Generate ONLY unique @Given/@When/@Then definitions. NO duplicates.\\n"'
txt = txt.replace(old, new)
open(f, 'w', encoding='utf-8').write(txt)
