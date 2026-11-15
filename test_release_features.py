import os,tempfile,unittest
from pathlib import Path
class ReleaseFeatureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory()
  os.environ['DATABASE_PATH']=str(Path(cls.tmp.name)/'release.db')
  os.environ['SECRET_KEY']='test-release-secret'
  import app as q
  cls.q=q
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):
  self.c=self.q.app.test_client();self.c.get('/')
  with self.c.session_transaction() as sess:self.csrf=sess['csrf_token']
  self.h={'X-CSRF-Token':self.csrf}
 def post(self,path,data):
  return self.c.post(path,json=data,headers=self.h)
 def test_family_profile_and_notification(self):
  p=self.post('/api/signup',{'name':'Patient Example','email':f'p{id(self)}@test.local','password':'LongPatientPass123'})
  self.assertEqual(p.status_code,201,p.json)
  f=self.post('/api/family',{'name':'Family Example','relationship':'parent'})
  self.assertEqual(f.status_code,201,f.json)
  self.assertEqual(len(self.c.get('/api/family').json['items']),1)
 def test_hospital_analytics(self):
  h=self.post('/api/tenant/signup',{'hospital_name':'Release Hospital','owner_name':'Owner Person','email':f'h{id(self)}@test.local','password':'LongHospitalPass123!'})
  self.assertEqual(h.status_code,201,h.json)
  self.assertEqual(self.c.get('/api/admin/analytics').status_code,200)
 def test_health_endpoint(self):
  self.assertEqual(self.c.get('/health').json['status'],'ok')
if __name__=='__main__':unittest.main()
