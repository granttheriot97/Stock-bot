import csv,os,tempfile,unittest
from research.multi_strategy import load,rows_for,symbols

class MemoryBoundedLoaderTests(unittest.TestCase):
    def test_rows_are_numeric_sorted_and_symbol_scoped(self):
        fd,path=tempfile.mkstemp(suffix=".csv");os.close(fd)
        try:
            with open(path,"w",newline="") as h:
                w=csv.writer(h);w.writerow(["timestamp","symbol","open","high","low","close","volume"])
                w.writerow(["2026-01-02","ZZZ","2","3","1","2.5","20"])
                w.writerow(["2026-01-01","SPY","10","11","9","10.5","100"])
                w.writerow(["2026-01-01","ZZZ","1","2",".5","1.5","10"])
                w.writerow(["2026-01-02","SPY","11","12","10","11.5","110"])
            db,dbpath=load(path)
            try:
                self.assertEqual(symbols(db),["SPY","ZZZ"])
                z=rows_for(db,"ZZZ")
                self.assertEqual([r["timestamp"] for r in z],["2026-01-01","2026-01-02"])
                self.assertEqual([r["close"] for r in z],[1.5,2.5])
                self.assertTrue(all(isinstance(r["volume"],float) for r in z))
            finally:
                db.close()
                if os.path.exists(dbpath):os.unlink(dbpath)
        finally:
            if os.path.exists(path):os.unlink(path)

if __name__=="__main__":unittest.main()
