import os,tempfile,unittest
class TestOptimizer(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();os.environ["B27B_STATE_DIR"]=self.tmp.name
  import importlib,research.optimizer_controller as o
  self.o=importlib.reload(o)
 def tearDown(self):self.tmp.cleanup()
 def test_locked(self):
  self.assertFalse(self.o.LOCKED["live_authorized"]);self.assertEqual(self.o.LOCKED["former_coverage_gate"],.90)
 def test_dedupe_and_failure_memory(self):
  ok,_=self.o.should_run("x","a");self.assertTrue(ok)
  self.o.record("x","a","complete",0)
  ok,why=self.o.should_run("x","a");self.assertFalse(ok);self.assertEqual(why,"deduplicated")
  self.o.record("y","b","failed",0)
  ok,why=self.o.should_run("y","b",cooldown=9999999999);self.assertFalse(ok);self.assertEqual(why,"failure_cooldown")
 def test_priority(self):
  rows=[{"symbol":"A","former":False,"completeness":0},{"symbol":"B","former":True,"completeness":.8}]
  self.assertEqual(self.o.rank(rows)[0]["symbol"],"B")
if __name__=="__main__":unittest.main()
