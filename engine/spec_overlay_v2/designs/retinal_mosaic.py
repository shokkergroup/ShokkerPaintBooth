# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 95.88; invariant nearest 0.28629 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Retinal Mosaic. Identity declared before rendering/scoring."""
from ..skin_designs import retinal_mosaic
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_retinal_mosaic',
 'display_name': 'Retinal Mosaic - spec overlay',
 'promise': 'Retinal Mosaic assembles cone receptor bodies, elongate rod pairs, receptor membrane lips, '
            'synaptic contact bridges and pigment granule pockets.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Retinal Mosaic assembles cone receptor bodies, elongate rod pairs, receptor '
                    'membrane lips, synaptic contact bridges and pigment granule pockets. Geometry is '
                    'independently authored in skin_designs.py:retinal_mosaic.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to cone receptor bodies, '
                 'elongate rod pairs, receptor membrane lips, synaptic contact bridges, pigment granule '
                 'pockets.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'cone_receptor_bodies',
                 'role': 'Cone receptor bodies use M/R/Cc intervals [(16, 244), (28, 216), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'elongate_rod_pairs',
                 'role': 'Elongate rod pairs use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'receptor_membrane_lips',
                 'role': 'Receptor membrane lips use M/R/Cc intervals [(0, 100), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'synaptic_contact_bridges',
                 'role': 'Synaptic contact bridges use M/R/Cc intervals [(58, 206), (102, 232), (68, '
                         '212)] in their own geometry.'},
                {'name': 'pigment_granule_pockets',
                 'role': 'Pigment granule pockets use M/R/Cc intervals [(96, 228), (54, 184), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['cone_receptor_bodies',
                            'elongate_rod_pairs',
                            'receptor_membrane_lips',
                            'synaptic_contact_bridges',
                            'pigment_granule_pockets'],
                      'R': ['cone_receptor_bodies',
                            'elongate_rod_pairs',
                            'receptor_membrane_lips',
                            'synaptic_contact_bridges',
                            'pigment_granule_pockets'],
                      'Cc': ['cone_receptor_bodies',
                             'elongate_rod_pairs',
                             'receptor_membrane_lips',
                             'synaptic_contact_bridges',
                             'pigment_granule_pockets']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Retinal Mosaic must visibly separate through cone receptor '
                                      'bodies, elongate rod pairs, receptor membrane lips and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Retinal Mosaic must visibly separate through cone receptor '
                                      'bodies, elongate rod pairs, receptor membrane lips and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Mixed rod and cone apertures form varied photoreceptor packets.',
                                     'cone receptor bodies is present in the native named-feature '
                                     'coverage probe.',
                                     'elongate rod pairs is present in the native named-feature '
                                     'coverage probe.',
                                     'receptor membrane lips is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/retinal_mosaic/independent-feature-carrier',
 'spec_key': 'spec-v2/retinal_mosaic/named-material-bindings'}

render = build_renderer(retinal_mosaic, IDENTITY_CONTRACT)
