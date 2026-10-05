# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 93.87; invariant nearest 0.50216 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Spray Coalescence. Identity declared before rendering/scoring."""
from ..liquid_designs import spray_coalescence
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_spray_coalescence',
 'display_name': 'Spray Coalescence - spec overlay',
 'promise': 'Spray Coalescence assembles merged spray islands, scalloped island edges, three drop '
            'junctions, satellite mist drops and dry spray necks.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Spray Coalescence assembles merged spray islands, scalloped island edges, three '
                    'drop junctions, satellite mist drops and dry spray necks. Geometry is '
                    'independently authored in liquid_designs.py:spray_coalescence.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to merged spray islands, '
                 'scalloped island edges, three drop junctions, satellite mist drops, dry spray necks.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'merged_spray_islands',
                 'role': 'Merged spray islands use M/R/Cc intervals [(18, 244), (0, 246), (20, 248)] in '
                         'their own geometry.'},
                {'name': 'scalloped_island_edges',
                 'role': 'Scalloped island edges use M/R/Cc intervals [(146, 255), (0, 94), (0, 110)] '
                         'in their own geometry.'},
                {'name': 'three_drop_junctions',
                 'role': 'Three drop junctions use M/R/Cc intervals [(0, 104), (176, 255), (142, 254)] '
                         'in their own geometry.'},
                {'name': 'satellite_mist_drops',
                 'role': 'Satellite mist drops use M/R/Cc intervals [(52, 202), (94, 228), (68, 200)] '
                         'in their own geometry.'},
                {'name': 'dry_spray_necks',
                 'role': 'Dry spray necks use M/R/Cc intervals [(94, 226), (52, 176), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['merged_spray_islands',
                            'scalloped_island_edges',
                            'three_drop_junctions',
                            'satellite_mist_drops',
                            'dry_spray_necks'],
                      'R': ['merged_spray_islands',
                            'scalloped_island_edges',
                            'three_drop_junctions',
                            'satellite_mist_drops',
                            'dry_spray_necks'],
                      'Cc': ['merged_spray_islands',
                             'scalloped_island_edges',
                             'three_drop_junctions',
                             'satellite_mist_drops',
                             'dry_spray_necks']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Spray Coalescence must visibly separate through merged spray '
                                      'islands, scalloped island edges, three drop junctions and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Spray Coalescence must visibly separate through merged spray '
                                      'islands, scalloped island edges, three drop junctions and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Scalloped wet splash lobes join through short drying necks.',
                                     'merged spray islands is present in the native named-feature '
                                     'coverage probe.',
                                     'scalloped island edges is present in the native named-feature '
                                     'coverage probe.',
                                     'three drop junctions is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/spray_coalescence/independent-feature-carrier',
 'spec_key': 'spec-v2/spray_coalescence/named-material-bindings'}

render = build_renderer(spray_coalescence, IDENTITY_CONTRACT)
