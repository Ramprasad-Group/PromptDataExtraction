# Usage: python -m pytest -v tests/test_dataset.py -s

from backend.data.dataset_pranav import GroundDataset

def test_ground_datasets():
    ds = GroundDataset()
    gnd, cur = ds.create_dataset('bandgap')
    assert len(gnd) > 0
