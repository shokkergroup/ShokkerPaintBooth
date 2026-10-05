# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.3; invariant nearest 0.50018 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Peen Crater Cluster. Identity declared before rendering/scoring."""
from ..machine_designs import peen_crater_cluster
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_peen_crater_cluster',
 'display_name': 'Peen Crater Cluster - spec overlay',
 'promise': 'Peen Crater Cluster assembles impact bowls, raised crater lips, secondary strikes, radial '
            'tears and flattened crest.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Peen Crater Cluster assembles impact bowls, raised crater lips, secondary strikes, '
                    'radial tears and flattened crest. Geometry is independently authored in '
                    'machine_designs.py:peen_crater_cluster.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to impact bowls, raised crater '
                 'lips, secondary strikes, radial tears, flattened crest.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'impact_bowls',
                 'role': 'Impact bowls use M/R/Cc intervals [(8, 178), (0, 240), (24, 240)] in their '
                         'own geometry.'},
                {'name': 'raised_crater_lips',
                 'role': 'Raised crater lips use M/R/Cc intervals [(182, 255), (0, 70), (0, 146)] in '
                         'their own geometry.'},
                {'name': 'secondary_strikes',
                 'role': 'Secondary strikes use M/R/Cc intervals [(36, 156), (132, 248), (130, 252)] in '
                         'their own geometry.'},
                {'name': 'radial_tears',
                 'role': 'Radial tears use M/R/Cc intervals [(80, 220), (52, 198), (24, 200)] in their '
                         'own geometry.'},
                {'name': 'flattened_crest',
                 'role': 'Flattened crest use M/R/Cc intervals [(6, 90), (180, 255), (172, 250)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['impact_bowls',
                            'raised_crater_lips',
                            'secondary_strikes',
                            'radial_tears',
                            'flattened_crest'],
                      'R': ['impact_bowls',
                            'raised_crater_lips',
                            'secondary_strikes',
                            'radial_tears',
                            'flattened_crest'],
                      'Cc': ['impact_bowls',
                             'raised_crater_lips',
                             'secondary_strikes',
                             'radial_tears',
                             'flattened_crest']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Peen Crater Cluster must visibly separate through impact bowls, '
                                      'raised crater lips, secondary strikes and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Peen Crater Cluster must visibly separate through impact bowls, '
                                      'raised crater lips, secondary strikes and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Unequal impact bowls overlap and interrupt neighboring raised '
                                     'lips.',
                                     'impact bowls is present in the native named-feature coverage '
                                     'probe.',
                                     'raised crater lips is present in the native named-feature '
                                     'coverage probe.',
                                     'secondary strikes is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/peen_crater_cluster/independent-feature-carrier',
 'spec_key': 'spec-v2/peen_crater_cluster/named-material-bindings'}

render = build_renderer(peen_crater_cluster, IDENTITY_CONTRACT)
