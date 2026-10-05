# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.52; invariant nearest 0.22389 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Varnish Lace. Identity declared before rendering/scoring."""
from ..liquid_designs import varnish_lace
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_varnish_lace',
 'display_name': 'Varnish Lace - spec overlay',
 'promise': 'Varnish Lace assembles varnish lace webs, thickened web junctions, broken film apertures, '
            'edge curl tabs and dust trapped beads.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Varnish Lace assembles varnish lace webs, thickened web junctions, broken film '
                    'apertures, edge curl tabs and dust trapped beads. Geometry is independently '
                    'authored in liquid_designs.py:varnish_lace.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to varnish lace webs, thickened '
                 'web junctions, broken film apertures, edge curl tabs, dust trapped beads.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'varnish_lace_webs',
                 'role': 'Varnish lace webs use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'thickened_web_junctions',
                 'role': 'Thickened web junctions use M/R/Cc intervals [(142, 255), (16, 108), (0, '
                         '114)] in their own geometry.'},
                {'name': 'broken_film_apertures',
                 'role': 'Broken film apertures use M/R/Cc intervals [(0, 98), (178, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'edge_curl_tabs',
                 'role': 'Edge curl tabs use M/R/Cc intervals [(56, 204), (102, 232), (70, 204)] in '
                         'their own geometry.'},
                {'name': 'dust_trapped_beads',
                 'role': 'Dust trapped beads use M/R/Cc intervals [(98, 230), (54, 180), (162, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['varnish_lace_webs',
                            'thickened_web_junctions',
                            'broken_film_apertures',
                            'edge_curl_tabs',
                            'dust_trapped_beads'],
                      'R': ['varnish_lace_webs',
                            'thickened_web_junctions',
                            'broken_film_apertures',
                            'edge_curl_tabs',
                            'dust_trapped_beads'],
                      'Cc': ['varnish_lace_webs',
                             'thickened_web_junctions',
                             'broken_film_apertures',
                             'edge_curl_tabs',
                             'dust_trapped_beads']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Varnish Lace must visibly separate through varnish lace webs, '
                                      'thickened web junctions, broken film apertures and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Varnish Lace must visibly separate through varnish lace webs, '
                                      'thickened web junctions, broken film apertures and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['A connected ruptured-film web encloses small open windows.',
                                     'varnish lace webs is present in the native named-feature coverage '
                                     'probe.',
                                     'thickened web junctions is present in the native named-feature '
                                     'coverage probe.',
                                     'broken film apertures is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/varnish_lace/independent-feature-carrier',
 'spec_key': 'spec-v2/varnish_lace/named-material-bindings'}

render = build_renderer(varnish_lace, IDENTITY_CONTRACT)
