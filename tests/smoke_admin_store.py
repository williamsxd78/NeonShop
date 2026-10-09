import requests
U=open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0]+'/api'
def login(e,p):
    c=requests.get(U+'/auth/captcha').json(); a,o,b=c['question'].split()[:3]; a,b=int(a),int(b)
    ans={'+':a+b,'-':a-b}.get(o,a*b)
    return {'Authorization':'Bearer '+requests.post(U+'/auth/login',json={'email':e,'password':p,'captcha_id':c['captcha_id'],'captcha_answer':str(ans)}).json()['token']}
A=login('admin@market.com','Admin@123'); B=login('buyer@market.com','Buyer@123')
p=requests.post(U+'/vendor/products',headers=A,json={'title':'TEST_Official','category':'Templates','price':5,'delivery_type':'content','delivery_content':'secret'}).json()
print('status',p['status'],p['vendor_name'])
d=requests.post(U+'/admin/deposits/manual',headers=A,json={'email':'buyer@market.com','amount':10,'coin':'USDT_TRC20','txid':'TEST_TX_manual1','note':'support ticket'}).json(); print(d['reference'],d['status'])
print('dup', requests.post(U+'/admin/deposits/manual',headers=A,json={'email':'buyer@market.com','amount':10,'txid':'TEST_TX_manual1','note':'again'}).json())
o=requests.post(U+'/orders',headers=B,json={'product_id':p['id']}).json(); print('order', o['order']['commission_pct'], o['order']['vendor_earning_cents'], o['balance_cents'])
print(requests.get(U+'/vendor/sales',headers=A).status_code)
print(requests.delete(U+f"/vendor/products/{p['id']}",headers=A).json())
