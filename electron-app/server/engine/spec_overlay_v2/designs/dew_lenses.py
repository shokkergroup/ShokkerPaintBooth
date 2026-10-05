# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 94.9; invariant nearest 0.5393 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Dew Lenses. Identity declared before rendering/scoring."""
from ..liquid_designs import dew_lenses
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_dew_lenses',
 'display_name': 'Dew Lenses - spec overlay',
 'promise': 'Dew Lenses assembles convex dew lenses, pinned contact rims, coalescence necks, dry dust '
            'islands and satellite bead collars.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Dew Lenses assembles convex dew lenses, pinned contact rims, coalescence necks, '
                    'dry dust islands and satellite bead collars. Geometry is independently authored in '
                    'liquid_designs.py:dew_lenses.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to convex dew lenses, pinned '
                 'contact rims, coalescence necks, dry dust islands, satellite bead collars.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'convex_dew_lenses',
                 'role': 'Convex dew lenses use M/R/Cc intervals [(12, 234), (0, 216), (16, 248)] in '
                         'their own geometry.'},
                {'name': 'pinned_contact_rims',
                 'role': 'Pinned contact rims use M/R/Cc intervals [(132, 254), (0, 94), (0, 108)] in '
                         'their own geometry.'},
                {'name': 'coalescence_necks',
                 'role': 'Coalescence necks use M/R/Cc intervals [(46, 202), (92, 230), (126, 252)] in '
                         'their own geometry.'},
                {'name': 'dry_dust_islands',
                 'role': 'Dry dust islands use M/R/Cc intervals [(0, 96), (182, 255), (172, 255)] in '
                         'their own geometry.'},
                {'name': 'satellite_bead_collars',
                 'role': 'Satellite bead collars use M/R/Cc intervals [(94, 226), (24, 110), (56, 208)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['convex_dew_lenses',
                            'pinned_contact_rims',
                            'coalescence_necks',
                            'dry_dust_islands',
                            'satellite_bead_collars'],
                      'R': ['convex_dew_lenses',
                            'pinned_contact_rims',
                            'coalescence_necks',
                            'dry_dust_islands',
                            'satellite_bead_collars'],
                      'Cc': ['convex_dew_lenses',
                             'pinned_contact_rims',
                             'coalescence_necks',
                             'dry_dust_islands',
                             'satellite_bead_collars']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Dew Lenses must visibly separate through convex dew lenses, '
                                      'pinned contact rims, coalescence necks and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_capillary_rivulets',
                        'difference': 'Dew Lenses must visibly separate through convex dew lenses, '
                                      'pinned contact rims, coalescence necks and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Unequal wind-shaped droplet clusters have offset contact rims.',
                                     'convex dew lenses is present in the native named-feature coverage '
                                     'probe.',
                                     'pinned contact rims is present in the native named-feature '
                                     'coverage probe.',
                                     'coalescence necks is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/dew_lenses/independent-feature-carrier',
 'spec_key': 'spec-v2/dew_lenses/named-material-bindings'}

render = build_renderer(dew_lenses, IDENTITY_CONTRACT)
