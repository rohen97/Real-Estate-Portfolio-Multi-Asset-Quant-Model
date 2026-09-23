import numpy as np
from packages.zoning.challenger import entropy,apply_temperature
from packages.zoning.discrepancy import compare_zoning
from packages.zoning.lulc_unet import blend_probability_patches
def test_entropy_and_temperature_calibration():
 peaked=np.array([[.9,.05,.05]]);uniform=np.array([[1/3,1/3,1/3]]);assert entropy(peaked[0])<entropy(uniform[0]);scaled=apply_temperature(peaked,2);assert scaled.shape==(1,3);assert abs(scaled.sum()-1)<1e-9
def test_probability_patch_blending():
 a=np.zeros((2,4,4));a[0]=.8;a[1]=.2;b=np.zeros((2,4,4));b[0]=.2;b[1]=.8;prob,classes,ent=blend_probability_patches([a,b],[(0,0),(0,2)],(2,4,6));assert prob.shape==(2,4,6);assert classes.shape==(4,6);assert ent.shape==(4,6);assert np.isfinite(prob).all()
def test_legal_prediction_discrepancy():
 prediction={'core':{'prediction':'Industrial','confidence':.82,'entropy':.3,'abstain':False},'subtype':{'prediction':'BUSINESS 1'},'gpr_band':{'prediction':'Medium-high 2.1-2.8'}};result=compare_zoning('RESIDENTIAL',2.8,prediction,'building','Residential');assert result['status']=='review';assert result['severity']==2
