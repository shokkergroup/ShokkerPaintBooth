"""A renamed finish keeps saved-paint IDs without inheriting retired intent."""
from scripts.spb_workbook_compute_m2 import intent_tokens

def test_renamed_neon_is_not_judged_as_black():
    tokens,source=intent_tokens('base:rad_bezel_black',{'intentDisplayName':'Arcade: Neon Bezel Inlay'})
    assert tokens==['bezel']
    assert source=='current-name-filtered-id'

def test_real_black_promise_is_retained():
    tokens,_=intent_tokens('base:black_satin',{'intentDisplayName':'Black Satin'})
    assert tokens==['black','satin']

def test_collection_name_does_not_turn_ceramic_into_chrome():
    tokens,_=intent_tokens('base:cbp_porcelain_face',{'intentDisplayName':'Chrome: Opal Ceramic'})
    assert tokens==[]

def test_new_marketing_adjective_does_not_add_physical_expectations():
    tokens,_=intent_tokens('base:rad_jazz_cup',{'intentDisplayName':'Memphis: Electric Brush'})
    assert 'electric' not in tokens

def test_existing_rows_keep_legacy_behavior():
    assert intent_tokens('base:chrome_mirror',{})==(['chrome','mirror'],'legacy-id')
    assert intent_tokens('base:chrome_mirror',{'intentDisplayName':'  '})==(['chrome','mirror'],'legacy-id')
