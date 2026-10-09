import requests,json
U=open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0]+'/api'
def login(e,p):
    c=requests.get(U+'/auth/captcha').json(); a,o,b=c['question'].split()[:3]; a,b=int(a),int(b)
    ans={'+':a+b,'-':a-b}.get(o,a*b)
    return {'Authorization':'Bearer '+requests.post(U+'/auth/login',json={'email':e,'password':p,'captcha_id':c['captcha_id'],'captcha_answer':str(ans)}).json()['token']}
V=login('vendor@market.com','Vendor@123'); A=login('admin@market.com','Admin@123')
regions=['EU','US','EU','Asia']
blocks=[f"Name: TEST_Acct {i}\nplan: Pro\nRegion: {r}\nPass: s{i}" for i,r in enumerate(regions)]
r=requests.post(U+'/vendor/products/bulk',headers=V,json={'text':"\n-----\n".join(blocks),'public_lines':[1,2],'title_line':0,'category':'Subscriptions','price':3,'tags':[]}).json(); bid=r['batch_id']
requests.post(U+f'/admin/batches/{bid}/approve',headers=A,json={})
print('facets',requests.get(U+'/products/facets').json())
print('EU',len(requests.get(U+'/products',params={'attrs':json.dumps({'Region':'EU'})}).json()))
print('EU+Pro',len(requests.get(U+'/products',params={'attrs':json.dumps({'Region':'EU','Plan':'Pro'})}).json()))
ids=[p['id'] for p in requests.get(U+'/vendor/products',headers=V).json() if p.get('batch_id')==bid]
print(requests.post(U+'/vendor/products/bulk-price',headers=V,json={'ids':ids[:2],'price':7}).json())
print(requests.post(U+'/vendor/products/bulk-delete',headers=V,json={'ids':ids}).json())
