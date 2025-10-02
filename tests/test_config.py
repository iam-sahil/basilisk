import json
import os


def test_default_config_exists_and_has_expected_keys():
    root = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(root, '..'))
    cfg_path = os.path.join(project_root, 'configs', 'default.json')
    assert os.path.exists(cfg_path), 'configs/default.json must exist'

    # Use utf-8-sig to gracefully handle BOM if present
    with open(cfg_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)

    assert 'WPFFeature' in data and isinstance(data['WPFFeature'], list)
    assert 'WPFTweaks' in data and isinstance(data['WPFTweaks'], list)
    # minimal sanity: no duplicates
    assert len(set(data['WPFTweaks'])) == len(data['WPFTweaks'])


