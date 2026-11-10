import bootstrap
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from checkpoint_io import save_checkpoint,load_latest,acquire_training_lock

def state(step):return dict(head={},optimizer={},step=step,epoch=2,cursor=2724,manifest='test',base='test',batch_size=4)
class Checkpoints(unittest.TestCase):
    def test_transient_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'last.pt';original=Path.replace;attempts=[]
            def replace(source,target):
                attempts.append(1)
                if len(attempts)<3:raise PermissionError('simulated Windows lock')
                return original(source,target)
            with patch.object(Path,'replace',replace),patch('checkpoint_io.time.sleep'):
                save_checkpoint(state(1),p)
            self.assertEqual(load_latest(p)['step'],1)
    def test_persistent_lock_and_legacy_recovery(self):
        import torch
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'last.pt';save_checkpoint(state(1),p)
            torch.save(state(2),p.with_suffix('.tmp'))
            self.assertEqual(load_latest(p)['step'],2)
            with patch.object(Path,'replace',side_effect=PermissionError('simulated lock')),patch('checkpoint_io.time.sleep'):
                saved=save_checkpoint(state(3),p)
            self.assertTrue(saved.exists());self.assertEqual(load_latest(p)['step'],3)
    def test_duplicate_process_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            handle=acquire_training_lock(folder)
            try:
                with self.assertRaises(RuntimeError):acquire_training_lock(folder)
            finally:handle.close()
if __name__=='__main__':unittest.main()
