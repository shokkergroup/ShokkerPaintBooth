"""One stable collection, five construction-led subsections. SPB-105 2026-09-30."""
CHAPTER_DESCRIPTIONS={
'Discharge':'Branching burns, plasma filaments, charge fronts and conductor networks. Fine paths and their surrounding material share the same geometry.',
'Living Armor':'Overlapping scales, keels, scutes, granular skin and translucent shed layers. Each animal has its own surface architecture.',
'Optical Deception':'Prototype disguise, false depth, interference print and optical films. Printed illusions and physical optical surfaces have separate material rules.',
'Paint Alchemy':'Spray, flow, contamination, cure and protective glaze. Wet and dry states belong to actual paint features; quiet coatings stay quiet.',
'Filmcraft':'Applied sheets, folds, cuts, woven films, adhesive routing and polish. Layer edges, roofs, backing and seams determine the material response.'}

def metadata():
    from .catalog import TABLE,SELECTED_SWATCHES
    chapters=[dict(name=name,description=desc,ids=[fid for fid,row in TABLE.items() if row[2]==name]) for name,desc in CHAPTER_DESCRIPTIONS.items()]
    finishes={fid:dict(name=row[1],desc=row[3],subsection=row[2],category='SHOKK WORKS',swatch=SELECTED_SWATCHES[fid]) for fid,row in TABLE.items()}
    return chapters,finishes

def apply_groups(groups):
    """Keep owned IDs once in the API map; preserve every unrelated category."""
    chapters,finishes=metadata();bank=groups.setdefault('bases',{})
    for name,ids in list(bank.items()):
        if name=='SHOKK WORKS':continue
        remaining=[fid for fid in ids if fid not in finishes]
        if remaining:bank[name]=remaining
        elif len(remaining)!=len(ids):bank.pop(name)
    bank['SHOKK WORKS']=list(finishes)
    groups.setdefault('subsections',{})['SHOKK WORKS']=chapters
    return finishes
