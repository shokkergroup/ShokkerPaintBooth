# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 100.0; invariant nearest 0.21832 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Split Lenslets. Identity declared before rendering/scoring."""
from ..optical_designs import split_lenslets
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_split_lenslets',
 'display_name': 'Split Lenslets - spec overlay',
 'promise': 'Split Lenslets assembles left lens half, right registered half, diagonal registration '
            'slits, lens mount shoulders and alignment witness pairs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Split Lenslets assembles left lens half, right registered half, diagonal '
                    'registration slits, lens mount shoulders and alignment witness pairs. Geometry is '
                    'independently authored in optical_designs.py:split_lenslets.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to left lens half, right '
                 'registered half, diagonal registration slits, lens mount shoulders, alignment witness '
                 'pairs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'left_lens_half',
                 'role': 'Left lens half use M/R/Cc intervals [(14, 244), (26, 218), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'right_registered_half',
                 'role': 'Right registered half use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'diagonal_registration_slits',
                 'role': 'Diagonal registration slits use M/R/Cc intervals [(0, 100), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'lens_mount_shoulders',
                 'role': 'Lens mount shoulders use M/R/Cc intervals [(58, 204), (102, 232), (68, 210)] '
                         'in their own geometry.'},
                {'name': 'alignment_witness_pairs',
                 'role': 'Alignment witness pairs use M/R/Cc intervals [(96, 228), (54, 184), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['left_lens_half',
                            'right_registered_half',
                            'diagonal_registration_slits',
                            'lens_mount_shoulders',
                            'alignment_witness_pairs'],
                      'R': ['left_lens_half',
                            'right_registered_half',
                            'diagonal_registration_slits',
                            'lens_mount_shoulders',
                            'alignment_witness_pairs'],
                      'Cc': ['left_lens_half',
                             'right_registered_half',
                             'diagonal_registration_slits',
                             'lens_mount_shoulders',
                             'alignment_witness_pairs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Split Lenslets must visibly separate through left lens half, '
                                      'right registered half, diagonal registration slits and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Split Lenslets must visibly separate through left lens half, '
                                      'right registered half, diagonal registration slits and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Opposed cylindrical lens halves flank diagonal registration '
                                     'breaks.',
                                     'left lens half is present in the native named-feature coverage '
                                     'probe.',
                                     'right registered half is present in the native named-feature '
                                     'coverage probe.',
                                     'diagonal registration slits is present in the native '
                                     'named-feature coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/split_lenslets/independent-feature-carrier',
 'spec_key': 'spec-v2/split_lenslets/named-material-bindings'}

render = build_renderer(split_lenslets, IDENTITY_CONTRACT)
