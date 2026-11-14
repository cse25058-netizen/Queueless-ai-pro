import os,tempfile,unittest
from pathlib import Path
class MultiTenantTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();os.environ['DATABASE_PATH']=str(Path(cls.tmp.name)/'test.db');os.environ['SECRET_KEY']='test-secret';import app as q;cls.q=q
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):
  self.c=self.q.app.test_client();self.c.get('/')
  with self.c.session_transaction() as sess:self.c.environ_base['HTTP_X_CSRF_TOKEN']=sess['csrf_token']
 def tenant(self,name,email):
  return self.c.post('/api/tenant/signup',json={'hospital_name':name,'owner_name':'Hospital Owner','email':email,'password':'StrongPassword123!','city':'Kolkata'})
 def patient(self):return self.c.post('/api/signup',json={'name':'Patient One','email':'patient'+str(id(self))+'@test.local','password':'PatientPassword123'})
 def test_tenant_registration_and_data_isolation(self):
  a=self.tenant('Hospital Alpha','alpha@test.local');self.assertEqual(a.status_code,201,a.json);ta=a.json['tenant']['id'];self.c.post('/api/admin/departments',json={'name':'Alpha Cardiology'});self.c.post('/api/logout')
  b=self.tenant('Hospital Beta','beta@test.local');self.assertEqual(b.status_code,201,b.json);tb=b.json['tenant']['id'];self.assertNotEqual(ta,tb)
  self.assertNotIn('Alpha Cardiology',[x['name'] for x in self.c.get('/api/departments?tenant_id='+str(tb)).json['items']])
 def test_patient_booking_and_cancel(self):
  self.tenant('Hospital Gamma','gamma@test.local');tid=self.c.get('/api/me').json['user']['tenant_id'];dep=self.c.get('/api/departments?tenant_id='+str(tid)).json['items'][0];self.c.post('/api/logout');self.assertEqual(self.patient().status_code,201)
  from datetime import date,timedelta
  day=(date.today()+timedelta(days=1)).isoformat();r=self.c.post('/api/book',json={'tenant_id':tid,'department_id':dep['id'],'visit_date':day,'slot':'10:00 AM'});self.assertEqual(r.status_code,201,r.json);self.assertTrue(r.json['token'].startswith('QL-'));self.assertEqual(len(self.c.get('/api/my-appointments').json['items']),1);self.assertEqual(self.c.post('/api/appointments/'+str(r.json['id'])+'/cancel').status_code,200)
 def test_admin_endpoint_role_protection(self):
  self.patient();self.assertEqual(self.c.get('/api/admin/summary').status_code,403)
if __name__=='__main__':unittest.main()
