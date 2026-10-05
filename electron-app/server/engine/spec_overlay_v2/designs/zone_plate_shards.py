# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 93.4; invariant nearest 0.43805 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Zone Plate Shards. Identity declared before rendering/scoring."""
from ..optical_designs import zone_plate_shards
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_zone_plate_shards',
 'display_name': 'Zone Plate Shards - spec overlay',
 'promise': 'Zone Plate Shards assembles broken zone plate sectors, sector facet boundaries, shard edge '
            'losses, recessed focus arclets and detached plate grains.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Zone Plate Shards assembles broken zone plate sectors, sector facet boundaries, '
                    'shard edge losses, recessed focus arclets and detached plate grains. Geometry is '
                    'independently authored in optical_designs.py:zone_plate_shards.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to broken zone plate sectors, '
                 'sector facet boundaries, shard edge losses, recessed focus arclets, detached plate '
                 'grains.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'broken_zone_plate_sectors',
                 'role': 'Broken zone plate sectors use M/R/Cc intervals [(18, 246), (24, 214), (24, '
                         '248)] in their own geometry.'},
                {'name': 'sector_facet_boundaries',
                 'role': 'Sector facet boundaries use M/R/Cc intervals [(144, 255), (16, 108), (0, '
                         '112)] in their own geometry.'},
                {'name': 'shard_edge_losses',
                 'role': 'Shard edge losses use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'recessed_focus_arclets',
                 'role': 'Recessed focus arclets use M/R/Cc intervals [(56, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'detached_plate_grains',
                 'role': 'Detached plate grains use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['broken_zone_plate_sectors',
                            'sector_facet_boundaries',
                            'shard_edge_losses',
                            'recessed_focus_arclets',
                            'detached_plate_grains'],
                      'R': ['broken_zone_plate_sectors',
                            'sector_facet_boundaries',
                            'shard_edge_losses',
                            'recessed_focus_arclets',
                            'detached_plate_grains'],
                      'Cc': ['broken_zone_plate_sectors',
                             'sector_facet_boundaries',
                             'shard_edge_losses',
                             'recessed_focus_arclets',
                             'detached_plate_grains']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Zone Plate Shards must visibly separate through broken zone '
                                      'plate sectors, sector facet boundaries, shard edge losses and '
                                      'the remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Zone Plate Shards must visibly separate through broken zone '
                                      'plate sectors, sector facet boundaries, shard edge losses and '
                                      'the remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Bounded broken fragments retain concentric zone-plate bands.',
                                     'broken zone plate sectors is present in the native named-feature '
                                     'coverage probe.',
                                     'sector facet boundaries is present in the native named-feature '
                                     'coverage probe.',
                                     'shard edge losses is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/zone_plate_shards/independent-feature-carrier',
 'spec_key': 'spec-v2/zone_plate_shards/named-material-bindings'}

render = build_renderer(zone_plate_shards, IDENTITY_CONTRACT)
