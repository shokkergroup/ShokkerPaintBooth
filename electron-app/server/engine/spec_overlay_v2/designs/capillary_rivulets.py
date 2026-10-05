# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 93.62; invariant nearest 0.26475 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Capillary Rivulets. Identity declared before rendering/scoring."""
from ..liquid_designs import capillary_rivulets
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_capillary_rivulets',
 'display_name': 'Capillary Rivulets - spec overlay',
 'promise': 'Capillary Rivulets assembles branching wet channels, asymmetric wetting lobes, receded '
            'channel edges, junction reservoir pits and detached capillary beads.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Capillary Rivulets assembles branching wet channels, asymmetric wetting lobes, '
                    'receded channel edges, junction reservoir pits and detached capillary beads. '
                    'Geometry is independently authored in liquid_designs.py:capillary_rivulets.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to branching wet channels, '
                 'asymmetric wetting lobes, receded channel edges, junction reservoir pits, detached '
                 'capillary beads.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'branching_wet_channels',
                 'role': 'Branching wet channels use M/R/Cc intervals [(18, 244), (24, 214), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'asymmetric_wetting_lobes',
                 'role': 'Asymmetric wetting lobes use M/R/Cc intervals [(146, 255), (16, 108), (0, '
                         '112)] in their own geometry.'},
                {'name': 'receded_channel_edges',
                 'role': 'Receded channel edges use M/R/Cc intervals [(0, 100), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'junction_reservoir_pits',
                 'role': 'Junction reservoir pits use M/R/Cc intervals [(56, 206), (102, 232), (68, '
                         '210)] in their own geometry.'},
                {'name': 'detached_capillary_beads',
                 'role': 'Detached capillary beads use M/R/Cc intervals [(96, 228), (54, 184), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['branching_wet_channels',
                            'asymmetric_wetting_lobes',
                            'receded_channel_edges',
                            'junction_reservoir_pits',
                            'detached_capillary_beads'],
                      'R': ['branching_wet_channels',
                            'asymmetric_wetting_lobes',
                            'receded_channel_edges',
                            'junction_reservoir_pits',
                            'detached_capillary_beads'],
                      'Cc': ['branching_wet_channels',
                             'asymmetric_wetting_lobes',
                             'receded_channel_edges',
                             'junction_reservoir_pits',
                             'detached_capillary_beads']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Capillary Rivulets must visibly separate through branching wet '
                                      'channels, asymmetric wetting lobes, receded channel edges and '
                                      'the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Capillary Rivulets must visibly separate through branching wet '
                                      'channels, asymmetric wetting lobes, receded channel edges and '
                                      'the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Short three-way wetting junctions contain unequal lobes and '
                                     'reservoirs.',
                                     'branching wet channels is present in the native named-feature '
                                     'coverage probe.',
                                     'asymmetric wetting lobes is present in the native named-feature '
                                     'coverage probe.',
                                     'receded channel edges is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/capillary_rivulets/independent-feature-carrier',
 'spec_key': 'spec-v2/capillary_rivulets/named-material-bindings'}

render = build_renderer(capillary_rivulets, IDENTITY_CONTRACT)
