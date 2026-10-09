import requests
U=open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0]+'/api'
def login(e,p):
    c=requests.get(U+'/auth/captcha').json(); a,o,b=c['question'].split()[:3]; a,b=int(a),int(b)
    ans={'+':a+b,'-':a-b}.get(o,a*b)
    return {'Authorization':'Bearer '+requests.post(U+'/auth/login',json={'email':e,'password':p,'captcha_id':c['captcha_id'],'captcha_answer':str(ans)}).json()['token']}
A=login('admin@market.com','Admin@123'); B=login('buyer@market.com','Buyer@123')
r=requests.post(U+'/vendor/products/bulk',headers=A,json={'text':'Name: TEST_SO 1\nRegion: EU\nkey a\n-----\nName: TEST_SO 2\nRegion: US\nkey b','public_lines':[1],'title_line':0,'category':'Templates','price':1}).json()
lst=lambda q: [p['title'] for p in requests.get(U+'/products',params={'q':q}).json()]
print('before', lst('TEST_SO'), requests.get(U+'/site').json()['product_count'])
pid=[p for p in requests.get(U+'/products',params={'q':'TEST_SO 1'}).json()][0]['id']
requests.post(U+'/admin/deposits/manual',headers=A,json={'email':'buyer@market.com','amount':1,'note':'test sold out'})
print(requests.post(U+'/orders',headers=B,json={'product_id':pid}).status_code)
print('after', lst('TEST_SO'), requests.get(U+'/site').json()['product_count'], [f['key'] for f in requests.get(U+'/products/facets').json()])
print('detail', requests.get(U+f'/products/{pid}').status_code)
print(requests.delete(U+f"/vendor/batches/{r['batch_id']}",headers=A).json())
