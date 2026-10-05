from __future__ import annotations

import numpy as np
import pytest

from engine.spec_sculpt import decal_local_features as local


def _wordmark(text="EIBACH"):
    if local.cv2 is None: pytest.skip("OpenCV unavailable")
    image=np.full((80,220,3),(220,20,30),np.uint8)
    local.cv2.putText(image,text,(10,58),local.cv2.FONT_HERSHEY_DUPLEX,1.5,(245,245,245),4,local.cv2.LINE_AA)
    return image


def test_local_features_match_rotated_scaled_wordmark_and_reject_other():
    base=_wordmark(); transformed=np.rot90(_wordmark())
    transformed=local.cv2.resize(transformed,(120,330))
    other=_wordmark("HOOSIER")
    a=local.extract_local_feature_signature(base);b=local.extract_local_feature_signature(transformed);c=local.extract_local_feature_signature(other)
    match=local.local_feature_similarity(a,b);negative=local.local_feature_similarity(a,c)
    assert match.good_matches>=8
    assert match.score>negative.score
    assert 0.0 <= match.match_fraction <= 1.0
    assert 0.0 <= match.score <= 1.0
    assert a.descriptors.flags.writeable is False


def test_local_feature_library_requires_repeated_geometric_support():
    a=local.extract_local_feature_signature(_wordmark());b=local.extract_local_feature_signature(np.rot90(_wordmark()));q=local.extract_local_feature_signature(_wordmark())
    refs=[local.LocalFeatureReference("a","logo:eibach","sponsors",a),local.LocalFeatureReference("b","logo:eibach","sponsors",b)]
    assert local.query_local_feature_library(q,refs[:1]).status=="abstained"
    result=local.query_local_feature_library(q,refs,min_similarity=0.12,min_good_matches=6)
    assert result.status=="corroborated"
    assert result.casts_votes is False and result.ownership_authority is False
