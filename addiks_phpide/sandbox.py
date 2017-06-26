from .PHP.phplexer import token_get_all

filePath = "/usr/workspace/b24_oms/src/Brille24/SalesBundle/Controller/OrdersController.php"

with open(filePath, "r", encoding = "ISO-8859-1") as f:
    code = f.read()

tokens = token_get_all(code)

print(tokens)
