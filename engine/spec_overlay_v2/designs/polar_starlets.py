# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.09; invariant nearest 0.25951 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Polar Starlets. Identity declared before rendering/scoring."""
from ..optical_designs import polar_starlets
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_polar_starlets',
 'display_name': 'Polar Starlets - spec overlay',
 'promise': 'Polar Starlets assembles polar facet stars, radial bevel spines, etched star centers, '
            'detached facet slivers and star tip witnesses.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Polar Starlets assembles polar facet stars, radial bevel spines, etched star '
                    'centers, detached facet slivers and star tip witnesses. Geometry is independently '
                    'authored in optical_designs.py:polar_starlets.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to polar facet stars, radial '
                 'bevel spines, etched star centers, detached facet slivers, star tip witnesses.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'polar_facet_stars',
                 'role': 'Polar facet stars use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'radial_bevel_spines',
                 'role': 'Radial bevel spines use M/R/Cc intervals [(144, 255), (16, 108), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'etched_star_centers',
                 'role': 'Etched star centers use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'detached_facet_slivers',
                 'role': 'Detached facet slivers use M/R/Cc intervals [(56, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'star_tip_witnesses',
                 'role': 'Star tip witnesses use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['polar_facet_stars',
                            'radial_bevel_spines',
                            'etched_star_centers',
                            'detached_facet_slivers',
                            'star_tip_witnesses'],
                      'R': ['polar_facet_stars',
                            'radial_bevel_spines',
                            'etched_star_centers',
                            'detached_facet_slivers',
                            'star_tip_witnesses'],
                      'Cc': ['polar_facet_stars',
                             'radial_bevel_spines',
                             'etched_star_centers',
                             'detached_facet_slivers',
                             'star_tip_witnesses']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Polar Starlets must visibly separate through polar facet stars, '
                                      'radial bevel spines, etched star centers and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Polar Starlets must visibly separate through polar facet stars, '
                                      'radial bevel spines, etched star centers and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Unequal paired four-point polar facets have separate etched '
                                     'centers, diagonal bevels and detached tip slivers.',
                                     'polar facet stars is present in the native named-feature coverage '
                                     'probe.',
                                     'radial bevel spines is present in the native named-feature '
                                     'coverage probe.',
                                     'etched star centers is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/polar_starlets/independent-feature-carrier',
 'spec_key': 'spec-v2/polar_starlets/named-material-bindings'}

render = build_renderer(polar_starlets, IDENTITY_CONTRACT)
