# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.65; invariant nearest 0.50172 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Fisheye Crater. Identity declared before rendering/scoring."""
from ..liquid_designs import fisheye_crater
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_fisheye_crater',
 'display_name': 'Fisheye Crater - spec overlay',
 'promise': 'Fisheye Crater assembles dewetting crater slopes, raised coating rings, contaminant cores, '
            'radial coat tears and residue splashes.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of liquid surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nature.com/articles/nature10344']},
 'carrier_grammar': 'Fisheye Crater assembles dewetting crater slopes, raised coating rings, '
                    'contaminant cores, radial coat tears and residue splashes. Geometry is '
                    'independently authored in liquid_designs.py:fisheye_crater.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to dewetting crater slopes, '
                 'raised coating rings, contaminant cores, radial coat tears, residue splashes.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'dewetting_crater_slopes',
                 'role': 'Dewetting crater slopes use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'raised_coating_rings',
                 'role': 'Raised coating rings use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'contaminant_cores',
                 'role': 'Contaminant cores use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'radial_coat_tears',
                 'role': 'Radial coat tears use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'residue_splashes',
                 'role': 'Residue splashes use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['dewetting_crater_slopes',
                            'raised_coating_rings',
                            'contaminant_cores',
                            'radial_coat_tears',
                            'residue_splashes'],
                      'R': ['dewetting_crater_slopes',
                            'raised_coating_rings',
                            'contaminant_cores',
                            'radial_coat_tears',
                            'residue_splashes'],
                      'Cc': ['dewetting_crater_slopes',
                             'raised_coating_rings',
                             'contaminant_cores',
                             'radial_coat_tears',
                             'residue_splashes']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_tidal_meniscus',
                        'difference': 'Fisheye Crater must visibly separate through dewetting crater '
                                      'slopes, raised coating rings, contaminant cores and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_dew_lenses',
                        'difference': 'Fisheye Crater must visibly separate through dewetting crater '
                                      'slopes, raised coating rings, contaminant cores and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Offset dewetting cavities interrupt each other’s raised rims.',
                                     'dewetting crater slopes is present in the native named-feature '
                                     'coverage probe.',
                                     'raised coating rings is present in the native named-feature '
                                     'coverage probe.',
                                     'contaminant cores is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/fisheye_crater/independent-feature-carrier',
 'spec_key': 'spec-v2/fisheye_crater/named-material-bindings'}

render = build_renderer(fisheye_crater, IDENTITY_CONTRACT)
