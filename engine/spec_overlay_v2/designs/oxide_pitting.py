# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.02; invariant nearest 0.23244 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Oxide Pitting. Identity declared before rendering/scoring."""
from ..crack_designs import oxide_pitting
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_oxide_pitting',
 'display_name': 'Oxide Pitting - spec overlay',
 'promise': 'Oxide Pitting assembles oxidized pit slopes, undercut pit lips, deep corrosion pores, '
            'oxide growth needles and passivated bridge islets.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Oxide Pitting assembles oxidized pit slopes, undercut pit lips, deep corrosion '
                    'pores, oxide growth needles and passivated bridge islets. Geometry is '
                    'independently authored in crack_designs.py:oxide_pitting.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to oxidized pit slopes, '
                 'undercut pit lips, deep corrosion pores, oxide growth needles, passivated bridge '
                 'islets.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'oxidized_pit_slopes',
                 'role': 'Oxidized pit slopes use M/R/Cc intervals [(16, 238), (26, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'undercut_pit_lips',
                 'role': 'Undercut pit lips use M/R/Cc intervals [(144, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'deep_corrosion_pores',
                 'role': 'Deep corrosion pores use M/R/Cc intervals [(0, 96), (182, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'oxide_growth_needles',
                 'role': 'Oxide growth needles use M/R/Cc intervals [(54, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'passivated_bridge_islets',
                 'role': 'Passivated bridge islets use M/R/Cc intervals [(98, 226), (54, 178), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['oxidized_pit_slopes',
                            'undercut_pit_lips',
                            'deep_corrosion_pores',
                            'oxide_growth_needles',
                            'passivated_bridge_islets'],
                      'R': ['oxidized_pit_slopes',
                            'undercut_pit_lips',
                            'deep_corrosion_pores',
                            'oxide_growth_needles',
                            'passivated_bridge_islets'],
                      'Cc': ['oxidized_pit_slopes',
                             'undercut_pit_lips',
                             'deep_corrosion_pores',
                             'oxide_growth_needles',
                             'passivated_bridge_islets']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Oxide Pitting must visibly separate through oxidized pit slopes, '
                                      'undercut pit lips, deep corrosion pores and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Oxide Pitting must visibly separate through oxidized pit slopes, '
                                      'undercut pit lips, deep corrosion pores and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Fine pits interrupt oxide rings and growth needles.',
                                     'oxidized pit slopes is present in the native named-feature '
                                     'coverage probe.',
                                     'undercut pit lips is present in the native named-feature coverage '
                                     'probe.',
                                     'deep corrosion pores is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/oxide_pitting/independent-feature-carrier',
 'spec_key': 'spec-v2/oxide_pitting/named-material-bindings'}

render = build_renderer(oxide_pitting, IDENTITY_CONTRACT)
