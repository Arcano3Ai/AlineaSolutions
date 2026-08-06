import requests
from bs4 import BeautifulSoup

# Test TARIC form structure
r = requests.get('https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp',
                 headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
soup = BeautifulSoup(r.text, 'lxml')
forms = soup.find_all('form')
print('Forms found:', len(forms))
for f in forms:
    action = f.get('action', '')
    method = f.get('method', 'GET')
    inputs = f.find_all('input')
    selects = f.find_all('select')
    print('  Form: action=%s, method=%s, inputs=%d, selects=%d' % (action, method, len(inputs), len(selects)))
    for inp in inputs[:8]:
        print('    Input: name=%s, type=%s' % (inp.get('name'), inp.get('type')))
    for sel in selects[:5]:
        opts = sel.find_all('option')
        print('    Select: name=%s, options=%d' % (sel.get('name'), len(opts)))
        for opt in opts[:3]:
            print('      Option: value=%s, text=%s' % (opt.get('value'), opt.text[:60]))
