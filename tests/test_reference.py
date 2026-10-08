import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'public'))
import lattice_reference as model

class ReferenceTests(unittest.TestCase):
    def test_pinned_source_telemetry(self):
        fixture=json.loads(Path('src/lib/lattice/fixtures/python-migration-v0.2.0.json').read_text())
        self.assertEqual(np.__version__,fixture['numpyVersion'])
        source_root=Path(os.environ.get('LATTICE_SOURCE_ROOT','../qoft-lab-source')).resolve()
        source_path=source_root/'public/gu_qoft_toy.py'
        self.assertTrue(source_path.is_file(),
            'Python migration tests require the pinned original checkout; see docs/VALIDATION.md.')
        self.assertEqual(hashlib.sha256(source_path.read_bytes()).hexdigest(),fixture['sourceSha256'],
            'The comparison source must match the immutable original file.')
        spec=importlib.util.spec_from_file_location('pinned_original_reference',source_path)
        original=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=original
        spec.loader.exec_module(original)
        compared=0
        historical_hash_differences=0
        for case in fixture['scenarios']:
            cfg=case['config']
            with self.subTest(config=cfg):
                rows=model.run(model.Config(ticks=len(case['rowSha256']),seed=cfg['seed'],n=cfg['n'],
                    phase_flip=cfg['phaseFlipEnabled'],grid=cfg['grid'],matrix_step_size=cfg['matrixStepSize'],
                    neighbor_weight=cfg['neighborWeight'],matrix_weight=cfg['matrixWeight']))
                source_rows=original.run(original.Config(ticks=len(case['rowSha256']),seed=cfg['seed'],n=cfg['n'],
                    collapse=cfg['phaseFlipEnabled'],grid=cfg['grid'],epsilon_g=cfg['matrixStepSize'],
                    alpha=cfg['neighborWeight'],beta=cfg['matrixWeight']))
                for row,source_row,historical_hash in zip(rows,source_rows,case['rowSha256'],strict=True):
                    expected=dict(schemaVersion=2,tick=source_row['t'],stateNorm=source_row['stateNorm'],
                        neighborResidualNorm=source_row['gammaNbrNorm'],minDeterminant=source_row['det_g_min'],
                        meanMatrixCoupling=source_row['pullback_mean'],maxRelativePower=source_row['C_max'],
                        phaseFlipApplied=source_row['collapsed'],siteMappingOk=source_row['section_law_ok'])
                    actual_json=json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)
                    expected_json=json.dumps(expected,sort_keys=True,separators=(',',':'),allow_nan=False)
                    self.assertEqual(actual_json,expected_json,f"source parity at tick {row['tick']}")
                    compared+=1
                    historical_hash_differences+=hashlib.sha256(expected_json.encode()).hexdigest()!=historical_hash
        print(f'Python source parity: {compared} exact telemetry rows; '
              f'{historical_hash_differences} original-source rows differ from the historical runtime hashes.')
    def test_deterministic_replay(self):
        cfg=model.Config(ticks=32,seed=7,n=2,phase_flip=True)
        self.assertEqual(model.run(cfg),model.run(cfg))
        self.assertEqual(model.check_pass(model.run(cfg),cfg),(True,[]))
    def test_phase_flip_preserves_power_and_is_reversible(self):
        field=np.array([[2+3j,0.1-0.2j],[4-5j,0+0j]])
        changed,_,event=model.phase_flip_gate(field,True)
        self.assertEqual(event,1)
        np.testing.assert_array_equal(np.abs(changed)**2,np.abs(field)**2)
        restored,_,_=model.phase_flip_gate(changed,True)
        np.testing.assert_array_equal(restored,field)
    def test_power_ratio_and_matrix_independence(self):
        field=np.array([1+0j,0+2j])
        values,peak,mean=model.relative_power_metric(field)
        self.assertEqual(mean,2.5)
        np.testing.assert_array_equal(values,np.array([1,4])/(2.5+model.EPS_POWER))
        self.assertEqual(peak,values[1])
        self.assertTrue(model.relative_power_check_ok())
    def test_operational_order(self):
        model.assert_tick_equivalent()
    def test_site_mapping_detects_permutation(self):
        cfg=model.Config(ticks=1,seed=7,n=2,phase_flip=False)
        matrices,_,i,j=model.init_state(cfg,np.random.default_rng(7))
        self.assertEqual(model.site_mapping_ok(matrices,i,j),1)
        i[0,0]=1
        self.assertEqual(model.site_mapping_ok(matrices,i,j),0)

if __name__=='__main__':
    unittest.main()
