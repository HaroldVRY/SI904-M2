# validate_html.py
from html.parser import HTMLParser

class HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        # Tags that don't close
        if tag in ['img', 'input', 'br', 'hr', 'meta', 'link']:
            return
        self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in ['img', 'input', 'br', 'hr', 'meta', 'link']:
            return
        if not self.stack:
            self.errors.append(f"Tag de cierre </{tag}> sin tag de apertura correspondiente en línea {self.getpos()[0]}")
            return
        
        last_tag, pos = self.stack.pop()
        if last_tag != tag:
            self.errors.append(f"Tag de cierre </{tag}> en línea {self.getpos()[0]} no coincide con el tag de apertura <{last_tag}> de la línea {pos[0]}")
            # Intentar recuperarse
            self.stack.append((last_tag, pos))

    def validate(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
        self.feed(html_content)
        while self.stack:
            tag, pos = self.stack.pop()
            self.errors.append(f"Tag de apertura <{tag}> en la línea {pos[0]} nunca fue cerrado.")
        
        if not self.errors:
            print("HTML balanceado perfectamente. No hay etiquetas mal cerradas.")
        else:
            print("ERRORES DETECTADOS:")
            for err in self.errors:
                print(f" - {err}")

if __name__ == '__main__':
    validator = HTMLValidator()
    validator.validate('templates/index.html')
