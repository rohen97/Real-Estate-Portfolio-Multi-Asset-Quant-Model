from __future__ import annotations
CORE_RULES={
 'Residential':['RESIDENTIAL','RESIDENTIAL WITH COMMERCIAL AT 1ST STOREY'],
 'Commercial':['COMMERCIAL'],
 'Mixed Use':['COMMERCIAL & RESIDENTIAL','WHITE'],
 'Industrial':['BUSINESS 1','BUSINESS 2','BUSINESS PARK','INDUSTRIAL'],
 'Hotel':['HOTEL'],
 'Institutional':['EDUCATIONAL INSTITUTION','HEALTH & MEDICAL CARE','CIVIC & COMMUNITY INSTITUTION','PLACE OF WORSHIP'],
 'Transport':['TRANSPORT FACILITIES','MASS RAPID TRANSIT','LIGHT RAPID TRANSIT','ROAD'],
 'Open Space':['OPEN SPACE','PARK','NATURE RESERVE','WATERBODY','BEACH AREA'],
 'Special':['RESERVE SITE','SPECIAL USE','UTILITY','CEMETERY','AGRICULTURE','PORT / AIRPORT']}
def core_class(land_use):
 name=(land_use or '').upper()
 for core,values in CORE_RULES.items():
  if name in values:return core
 return 'Other'
def gpr_band(gpr):
 if gpr is None:return 'EVA/NA'
 x=float(gpr)
 if x<=1.4:return 'Low density <=1.4'
 if x<=2.1:return 'Medium density 1.4-2.1'
 if x<=2.8:return 'Medium-high 2.1-2.8'
 if x<=4.2:return 'High density 2.8-4.2'
 return 'Very high density >4.2'
