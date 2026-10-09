import requests
U=open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0]+'/api'
def login(e,p):
    c=requests.get(U+'/auth/captcha').json(); a,o,b=c['question'].split()[:3]; a,b=int(a),int(b)
    ans={'+':a+b,'-':a-b}.get(o,a*b)
    return {'Authorization':'Bearer '+requests.post(U+'/auth/login',json={'email':e,'password':p,'captcha_id':c['captcha_id'],'captcha_answer':str(ans)}).json()['token']}
A=login('admin@market.com','Admin@123')
s=requests.get(U+'/site').json(); print(s)
cats=[{'name':c,'original':c} for c in s['categories']]
cats[0]['name']='Software Keys'
r=requests.put(U+'/admin/site',headers=A,json={'categories':cats+[{'name':'Gift Cards','original':None}]}); print(r.status_code, r.json()['categories'])
print('renamed count', len(requests.get(U+'/products',params={'category':'Software Keys'}).json()))
r=requests.put(U+'/admin/site',headers=A,json={'categories':[{'name':'Software Keys','original':'Software Keys'}]}); print('remove w/ products', r.status_code, r.json()['detail'])
back=[{'name':c,'original':c} for c in s['categories']]; back[0]['original']='Software Keys'
r=requests.put(U+'/admin/site',headers=A,json={'categories':back}); print('restore', r.status_code, r.json()['categories'])
