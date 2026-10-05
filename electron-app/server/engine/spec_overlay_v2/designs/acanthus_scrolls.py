# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.41; invariant nearest 0.48859 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Acanthus Scrolls. Identity declared before rendering/scoring."""
from ..engraved_designs import acanthus_scrolls
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_acanthus_scrolls',
 'display_name': 'Acanthus Scrolls - spec overlay',
 'promise': 'Acanthus Scrolls assembles acanthus leaf lobes, engraved leaf spines, recessed scroll '
            'eyes, lobed leaf serrations and curled leaf tips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Acanthus Scrolls assembles acanthus leaf lobes, engraved leaf spines, recessed '
                    'scroll eyes, lobed leaf serrations and curled leaf tips. Geometry is independently '
                    'authored in engraved_designs.py:acanthus_scrolls.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to acanthus leaf lobes, '
                 'engraved leaf spines, recessed scroll eyes, lobed leaf serrations, curled leaf tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'acanthus_leaf_lobes',
                 'role': 'Acanthus leaf lobes use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'engraved_leaf_spines',
                 'role': 'Engraved leaf spines use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'recessed_scroll_eyes',
                 'role': 'Recessed scroll eyes use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'lobed_leaf_serrations',
                 'role': 'Lobed leaf serrations use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'curled_leaf_tips',
                 'role': 'Curled leaf tips use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['acanthus_leaf_lobes',
                            'engraved_leaf_spines',
                            'recessed_scroll_eyes',
                            'lobed_leaf_serrations',
                            'curled_leaf_tips'],
                      'R': ['acanthus_leaf_lobes',
                            'engraved_leaf_spines',
                            'recessed_scroll_eyes',
                            'lobed_leaf_serrations',
                            'curled_leaf_tips'],
                      'Cc': ['acanthus_leaf_lobes',
                             'engraved_leaf_spines',
                             'recessed_scroll_eyes',
                             'lobed_leaf_serrations',
                             'curled_leaf_tips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Acanthus Scrolls must visibly separate through acanthus leaf '
                                      'lobes, engraved leaf spines, recessed scroll eyes and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_damascene_inlay',
                        'difference': 'Acanthus Scrolls must visibly separate through acanthus leaf '
                                      'lobes, engraved leaf spines, recessed scroll eyes and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Lobed ornamental leaves curl around separate engraved scroll '
                                     'eyes.',
                                     'acanthus leaf lobes is present in the native named-feature '
                                     'coverage probe.',
                                     'engraved leaf spines is present in the native named-feature '
                                     'coverage probe.',
                                     'recessed scroll eyes is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/acanthus_scrolls/independent-feature-carrier',
 'spec_key': 'spec-v2/acanthus_scrolls/named-material-bindings'}

render = build_renderer(acanthus_scrolls, IDENTITY_CONTRACT)
