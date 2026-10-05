# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.23; invariant nearest 0.52483 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Marangoni Fans. Identity declared before rendering/scoring."""
from ..liquid_designs import marangoni_fans
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_marangoni_fans',
 'display_name': 'Marangoni Fans - spec overlay',
 'promise': 'Marangoni Fans assembles fan flow lobes, flow separatrices, source meniscus, deposit fan '
            'fronts and bead pinning clusters.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Marangoni Fans assembles fan flow lobes, flow separatrices, source meniscus, '
                    'deposit fan fronts and bead pinning clusters. Geometry is independently authored '
                    'in liquid_designs.py:marangoni_fans.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to fan flow lobes, flow '
                 'separatrices, source meniscus, deposit fan fronts, bead pinning clusters.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'fan_flow_lobes',
                 'role': 'Fan flow lobes use M/R/Cc intervals [(18, 246), (24, 210), (20, 248)] in '
                         'their own geometry.'},
                {'name': 'flow_separatrices',
                 'role': 'Flow separatrices use M/R/Cc intervals [(142, 255), (16, 112), (0, 110)] in '
                         'their own geometry.'},
                {'name': 'source_meniscus',
                 'role': 'Source meniscus use M/R/Cc intervals [(0, 96), (174, 255), (144, 252)] in '
                         'their own geometry.'},
                {'name': 'deposit_fan_fronts',
                 'role': 'Deposit fan fronts use M/R/Cc intervals [(50, 202), (108, 236), (74, 206)] in '
                         'their own geometry.'},
                {'name': 'bead_pinning_clusters',
                 'role': 'Bead pinning clusters use M/R/Cc intervals [(92, 224), (42, 178), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['fan_flow_lobes',
                            'flow_separatrices',
                            'source_meniscus',
                            'deposit_fan_fronts',
                            'bead_pinning_clusters'],
                      'R': ['fan_flow_lobes',
                            'flow_separatrices',
                            'source_meniscus',
                            'deposit_fan_fronts',
                            'bead_pinning_clusters'],
                      'Cc': ['fan_flow_lobes',
                             'flow_separatrices',
                             'source_meniscus',
                             'deposit_fan_fronts',
                             'bead_pinning_clusters']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Marangoni Fans must visibly separate through fan flow lobes, '
                                      'flow separatrices, source meniscus and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Marangoni Fans must visibly separate through fan flow lobes, '
                                      'flow separatrices, source meniscus and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Radial flow lines spread through bounded liquid fans.',
                                     'fan flow lobes is present in the native named-feature coverage '
                                     'probe.',
                                     'flow separatrices is present in the native named-feature coverage '
                                     'probe.',
                                     'source meniscus is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/marangoni_fans/independent-feature-carrier',
 'spec_key': 'spec-v2/marangoni_fans/named-material-bindings'}

render = build_renderer(marangoni_fans, IDENTITY_CONTRACT)
