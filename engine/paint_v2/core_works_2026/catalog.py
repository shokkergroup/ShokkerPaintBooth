"""SHOKK WORKS authored identity contracts and selected attempts.
SPB-105 / CORE-WORKS 2026-09-30. Every entry is a separate construction.
Production selections retain stable IDs; actual-output evidence is in the rebuild report.
"""
import importlib
import sys
from .common import bind, named_contract

NOAA='https://www.nssl.noaa.gov/education/svrwx101/lightning/types/'
SNAKE='https://www.nature.com/articles/srep23539'
FORD='https://media.ford.com/content/fordmedia/feu/at/en/news/2016/10/03/honey--where_d-you-park-the-car--how-an-optical-illusion-helps-s.html'
PPG='https://www.ppg.com/en-US/refinish/fisheyes'
FILM='https://multimedia.3m.com/mws/media/2398179O/3m-protection-wrap-film-product-bulletin-rev-a.pdf'

# module, name, subsection, description, carrier grammar, spec grammar, marks, source, neighbours
TABLE={
'lsk_lichtenberg':('discharge','Lichtenberg Burn','Discharge',
 'A dense dielectric burn forest: black ramifying scars, copper ash collars and pale conductive veins embedded in amber-violet glass.',
 'Recursive stochastic dielectric trees with interlocking tertiary branches; distance-defined char collars; individual glass-grain substrate; terminal punctures.',
 'Char scars suppress metal/coat and raise roughness; copper collars are tiered exposed metal; inner conductive veins polish; dielectric grains retain graded coat.',
 [('dendritic_scar','recursive burned dielectric channels'),('carbon_collar','matte char immediately around each branch'),('conductive_vein','polished inner path of a burned branch'),('copper_ash','oxidised deposited collar at char boundary'),('dielectric_grain','locally graded unburned glass substrate'),('terminal_puncture','small silver end point at a fine branch')],NOAA,
 [('lsk_carbon_track','contaminant tracking across an insulator rather than a radiating dielectric tree'),('astra_cryogenic_bloom','hexagonal fern crystals rather than branched char scars')]),
'slt_sunbeam_iris':('armor','Sunbeam Iridescence','Living Armor',
 'Swept overlapping lance scales with dark roots, luminous interference faces, fine striae and individually polished trailing lips.',
 'Wandering biological rows of asymmetrical lance scales; recessed shoulders and projecting tongue; scale-owned interference phase and clipped diagonal striae.',
 'Keratin roots are rough and subdued; interference faces use eight pearl tiers; trailing lips polish; striae vary coating inside their own scale.',
 [('lance_face','asymmetric overlapping scale face'),('receding_shoulder','dark rooted shoulder of each scale'),('trailing_lip','polished scale overlap edge'),('scale_stria','fine dermal ruling clipped within a scale'),('interference_region','regional spectral family carried by scale faces'),('interstitial_skin','matte connected skin between overlapping scales')],SNAKE,
 [('slt_cycloid_gloss','rounded wet cycloid shells rather than asymmetric iridescent lances'),('astra_duality_scales','two pigment populations on broader scales rather than interference travelling inside lance scales')]),
'mul_moire_defeat':('optical','Moire Defeat','Optical Deception',
 'Contradictory optical domains: two chirped rulings beat across silver print, copper crossings and fine lens seams.',
 'Per-domain curvilinear chirped gratings cross at different rates; beat envelopes emerge from their difference; contradiction edges have registration hatches.',
 'First print is matte dielectric; second print is coated translucent metal; overlapping rulings expose copper; lens domains and seam metal use local tiers.',
 [('first_ruling','curvilinear dark print ruling'),('second_ruling','crossing translucent print ruling'),('beat_envelope','emergent moire contrast between two rulings'),('copper_crossing','material exposed where two prints overlap'),('domain_seam','fine boundary between contradictory optical domains'),('registration_hatch','short registration lines on domain seams')],FORD,
 [('mul_wireframe','mesh projection rather than beat interference'),('wrap_holographic','security-foil rosettes rather than contradictory chirped rulings')]),
'bth_fisheye':('alchemy','Fisheye Lacquer','Paint Alchemy',
 'Candy lacquer draws away from contaminants into irregular craters: exposed metal floors, copper rolled rims and wet menisci over fine metallic pigment.',
 'Irregular contamination nuclei with per-crater radius, angular meniscus deformation and small satellite craters; continuous fine pigmented lacquer between them.',
 'Exposed metal floors are coat-reflection-minimized and rough; raised copper rims polish; wet menisci carry strong coat; pigment flakes are graded inside the intact lacquer.',
 [('exposed_floor','substrate visible at the contamination centre'),('rolled_rim','rounded raised lacquer meniscus'),('wet_meniscus','wet collar outside each crater'),('rim_crease','dark inner trench at the crater wall'),('pigment_flake','fine metallic pigment in intact lacquer'),('satellite_crater','small contamination satellite alongside a larger crater')],PPG,
 [('bth_solvent_pop','ruptured solvent blisters rather than paint retreating from contamination'),('wrap_microbubble','intact trapped-air domes rather than open lacquer craters')]),
'wrap_layered_cut':('filmcraft','Layered Cut Foil','Filmcraft',
 'Two independent laser-cut foil webs interpenetrate: openings reveal the lower sheet, deep backing, adhesive undercuts and polished cut rims.',
 'Two independent continuous pierced lattices cross obliquely; upper-sheet openings expose a separately cut lower sheet and backing; clipped print striae, registration punctures and adhesive undercuts prove layer topology.',
 'Upper foil is high-metal with eight polish tiers; lower print is subdued coated material; exposed adhesive is matte; cut lips polish and registration holes suppress coat.',
 [('upper_foil','asymmetrical upper cut sheet'),('lower_print','complementary lower printed sheet'),('exposed_backing','substrate between registered sheet cuts'),('adhesive_lip','warm matte adhesive along exposed cut'),('cut_edge','polished narrow registration edge'),('print_stria','fine print ruling clipped to the upper sheet'),('registration_hole','small puncture in a printed tongue')],FILM,
 [('wrap_overlap_ghost','transparent overlap counts rather than cut tongues and exposed adhesive'),('astra_causal_origami','folded faces rather than flat sheets with interlocking cuts')]),
'wrap_holographic':('filmcraft','Holographic Foil','Optical Deception',
 'Security foil filled with microscopic engraved rosettes, ruled diffraction sectors, pale register cores and gold ghost rings.',
 'Jittered individually lobed micro-rosettes with independently oriented straight diffraction rulings; alternating foil sectors; regional thin-film phase and sparse registered ghost rings.',
 'Foil sectors carry local metal/polish tiers; engraved trenches suppress metal and coat; ruled flashes and register cores polish; ink seams remain matte.',
 [('foil_sector','alternating etched foil sectors'),('rosette_engraving','lobed fine security-foil contours'),('diffraction_ruling','straight ruling at each foil nucleus'),('register_core','polished pale registration centre'),('ink_seam','dark print seam between foil patches'),('ghost_ring','rare gold registration ring inside a rosette')],FILM,
 [('wrap_laminate','printed CMYK rosettes under laminate rather than etched security foil'),('mul_moire_defeat','contradictory chirps rather than radial foil security engraving')])
}

from .identities_discharge import TABLE as DISCHARGE_IDENTITIES
TABLE.update(DISCHARGE_IDENTITIES)
from .identities_armor import TABLE as ARMOR_IDENTITIES
TABLE.update(ARMOR_IDENTITIES)
from .identities_optical import TABLE as OPTICAL_IDENTITIES
TABLE.update(OPTICAL_IDENTITIES)
from .identities_alchemy import TABLE as ALCHEMY_IDENTITIES
TABLE.update(ALCHEMY_IDENTITIES)
from .identities_filmcraft import TABLE as FILM_IDENTITIES
TABLE.update(FILM_IDENTITIES)
for _fid in ('lsk_return_stroke','lsk_spider_crawl','lsk_sprite','lsk_spark_gap','lsk_tesla_streamer','lsk_corona_ring'):
    TABLE[_fid]=('discharge_advanced',)+TABLE[_fid][1:]
for _fid in ('bth_solvent_pop','bth_sag_curtain','bth_mottling','bth_water_spot'):
    TABLE[_fid]=('alchemy_advanced',)+TABLE[_fid][1:]
for _fid in ('wrap_squeegee','wrap_heat_gun','wrap_ceramic_coat','wrap_flow_wrapline'):
    TABLE[_fid]=('film_advanced',)+TABLE[_fid][1:]
try:
    from .selection import WINNERS as SELECTED, SWATCHES as SELECTED_SWATCHES
except ImportError:
    SELECTED={fid:1 for fid in TABLE}
    SELECTED_SWATCHES={}
SWATCH={'lsk_lichtenberg':'#ad725e','slt_sunbeam_iris':'#456b8b','mul_moire_defeat':'#7894a2','bth_fisheye':'#376c8c','wrap_layered_cut':'#836674','wrap_holographic':'#938491'}
SWATCH.update({'lsk_return_stroke':'#626a9b','lsk_spider_crawl':'#43878f','lsk_st_elmo':'#7963b4','lsk_plasma_globe':'#aa568c','lsk_jacobs_ladder':'#789375','lsk_arc_weld':'#857989','lsk_sprite':'#af6387','lsk_static_creep':'#698796'})
SWATCH.update({'lsk_carbon_track':'#719693','lsk_bead':'#885b99','lsk_streamer_front':'#c0946b','lsk_fulgurite':'#a47e4d','lsk_spark_gap':'#a66a43','lsk_tesla_streamer':'#84505d','lsk_corona_ring':'#599ca2'})
SWATCH.update({'slt_reticulated':'#a58c7c','slt_keeled_viper':'#6f986f','slt_cycloid_gloss':'#6f9daf','slt_ventral_scute':'#b38a70','slt_boa_saddle':'#b59982','slt_sidewinder_micro':'#b7a783','slt_gaboon_geometric':'#a1807e','slt_milk_band':'#a66856','slt_corn_blotch':'#c98157','slt_shed_ecdysis':'#c9c3c9','slt_cobra_hood':'#708b96','slt_wart_tubercle':'#94779b','slt_diamondback':'#958a77','slt_anaconda_oval':'#68966b','slt_albino_translucent':'#d4bcbc'})
SWATCH.update({'mul_erlkonig_swirl':'#a49e91','mul_confusion_blob':'#808892','mul_shutline_fake':'#8297a4','mul_foam_clad':'#9c9a97','mul_bubble_clad':'#a2abb4','mul_countershade':'#a18788','mul_false_shadow':'#677ba0','mul_qr_scramble':'#7c9699','mul_wireframe':'#6b9c93','mul_matte_cover':'#30363f','mul_retro_patch':'#aea2b0','mul_tape_seam':'#666764','mul_pixel_break':'#657bad','mul_decoy_blackout':'#333341','mul_edge_chamfer':'#9d8796'})
SWATCH.update({'bth_solvent_pop':'#b26766','bth_sag_curtain':'#8e6a8d','bth_dry_spray':'#aa927d','bth_mottling':'#977a88','bth_tiger_stripe':'#a07e68','bth_die_back':'#85776d','bth_blush':'#c199ad','bth_lifting':'#8c7994','bth_sand_scratch':'#7b9da1','bth_dirt_nib':'#a28568','bth_edge_map':'#99878b','bth_buff_hologram':'#7186a3','bth_mask_bleed':'#a996b0','bth_tape_ridge':'#ac829a','bth_water_spot':'#849b9d'})

def adopt(module_name,fid):
    module=sys.modules[module_name]
    lane,name,chapter,desc,carrier,spec,marks,source,neighbors=TABLE[fid]
    module.FID,module.NAME,module.CHAPTER,module.DESCRIPTION=fid,name,chapter,desc
    module.SWATCH=SELECTED_SWATCHES.get(fid,SWATCH.get(fid,'#8c8b93'))
    module.ATTEMPT=SELECTED[fid]
    module.AUTHORED_SEED=42
    module.IDENTITY_CONTRACT=named_contract(fid,name,desc,carrier,marks,spec,source,neighbors)
    module.construct=getattr(importlib.import_module(__package__+'.'+lane),fid)
    module.paint,module.spec=bind(module)
    for fn in (module.paint,module.spec):
        fn._spb_picker_dependency_modules += (__name__, __package__+'.selection', __package__+'.identities_'+{'discharge':'discharge','discharge_advanced':'discharge','armor':'armor','optical':'optical','alchemy':'alchemy','alchemy_advanced':'alchemy','filmcraft':'filmcraft','detailed_film':'filmcraft','film_advanced':'filmcraft'}[lane])
    return module
