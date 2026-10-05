"""Owner scale exception is scoped; it cannot disable other identity rules."""
import copy,json,unittest
from pathlib import Path
from scripts.spb_finish_identity import validate_identity_contract
ROOT=Path(__file__).resolve().parents[1]

class EraScaleAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.contract=json.loads((ROOT/'engine/paint_v2/era_image_2026/contracts/rad_chrome_type.json').read_text())
        # Installed Chrome now legitimately carries the owner exception.
        # Start each test from a default-scale fixture so the negative case
        # continues to test absence of authorization, not mutable live metadata.
        self.contract.pop('owner_scale_authorization',None)
        self.contract.pop('fine_detail_scale_px',None)
        self.contract['native_scale_px']=[8,32]
    def test_default_fine_contract_still_passes(self):
        self.assertTrue(validate_identity_contract(self.contract,'rad_chrome_type').ok)
    def test_large_scale_needs_documented_authorization(self):
        self.contract['native_scale_px']=[60,220]
        self.assertFalse(validate_identity_contract(self.contract,'rad_chrome_type').ok)
        self.contract.update(owner_scale_authorization='ERA120-20260917-reviewed-concepts',fine_detail_scale_px=[1,16])
        self.assertTrue(validate_identity_contract(self.contract,'rad_chrome_type').ok)
    def test_authorization_does_not_apply_to_other_finishes(self):
        self.contract.update(finish_id='unrelated_finish',native_scale_px=[60,220],owner_scale_authorization='ERA120-20260917-reviewed-concepts',fine_detail_scale_px=[1,16])
        self.assertFalse(validate_identity_contract(self.contract,'unrelated_finish').ok)
    def test_other_identity_requirements_remain_enforced(self):
        self.contract.update(native_scale_px=[60,220],owner_scale_authorization='ERA120-20260917-reviewed-concepts',fine_detail_scale_px=[1,16],mark_types=[])
        self.assertFalse(validate_identity_contract(self.contract,'rad_chrome_type').ok)

if __name__=='__main__':unittest.main()
