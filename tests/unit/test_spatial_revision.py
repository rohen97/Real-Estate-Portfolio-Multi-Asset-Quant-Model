import pytest
from shapely.geometry import box, mapping, shape
from packages.zoning.envelope3d import EnvelopeInputs, generate_envelopes, to_local
from packages.zoning.viewshed import viewshed


def test_setbacks_cannot_be_relaxed_when_they_remove_the_whole_site():
    site=mapping(box(103.8,1.3,103.8001,1.3001))
    result=generate_envelopes(EnvelopeInputs(site,3.5,100,.45,setback_m=20))
    assert result['preferred'] is None
    assert result['options']==[]
    assert result['status']=='no_feasible_envelope'


def test_reported_built_area_reconciles_with_real_floors_and_legal_limit():
    site=mapping(box(103.8,1.3,103.801,1.301))
    result=generate_envelopes(EnvelopeInputs(site,2.73,100,.45))
    for option in result['options']:
        assert option['gross_gfa_sqm']==pytest.approx(option['floorplate_sqm']*option['storeys'],abs=.3)
        assert option['gross_gfa_sqm']<=result['legal_gfa_sqm']+.01
        assert option['height_m']<=100


def test_holes_remain_excluded_in_local_projection():
    site=box(103.8,1.3,103.801,1.301).difference(box(103.8003,1.3003,103.8007,1.3007))
    local,*_=to_local(site)
    assert len(local.interiors)==1


def test_missing_geometry_is_unknown_not_clear_and_bins_are_general():
    missing=viewshed(30,[],current_value_m=100)
    assert missing['blocked_azimuth_share'] is None
    assert missing['open_sky_share'] is None
    assert missing['view_premium_loss_m'] is None
    result=viewshed(30,[{'distance_m':50,'height_m':100,'width_m':30,'bearing_deg':359}],bins=72)
    assert len(result['horizon_angles_deg'])==72
    assert result['blocked_azimuth_share']>0
