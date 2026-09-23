from __future__ import annotations
from pathlib import Path
import numpy as np
LULC_CLASSES=['building','road','paved','vegetation','water','construction','vacant_land']
def build_unet(input_channels=3,num_classes=len(LULC_CLASSES),base=32):
 try:import torch;from torch import nn
 except ImportError as exc:raise RuntimeError('Install requirements-imagery.txt to use the U-Net pipeline') from exc
 class ConvBlock(nn.Module):
  def __init__(self,a,b):super().__init__();self.net=nn.Sequential(nn.Conv2d(a,b,3,padding=1),nn.BatchNorm2d(b),nn.ReLU(),nn.Conv2d(b,b,3,padding=1),nn.BatchNorm2d(b),nn.ReLU())
  def forward(self,x):return self.net(x)
 class UNet(nn.Module):
  def __init__(self):
   super().__init__();self.pool=nn.MaxPool2d(2);self.e1=ConvBlock(input_channels,base);self.e2=ConvBlock(base,base*2);self.e3=ConvBlock(base*2,base*4);self.e4=ConvBlock(base*4,base*8);self.b=ConvBlock(base*8,base*16);self.up4=nn.ConvTranspose2d(base*16,base*8,2,2);self.d4=ConvBlock(base*16,base*8);self.up3=nn.ConvTranspose2d(base*8,base*4,2,2);self.d3=ConvBlock(base*8,base*4);self.up2=nn.ConvTranspose2d(base*4,base*2,2,2);self.d2=ConvBlock(base*4,base*2);self.up1=nn.ConvTranspose2d(base*2,base,2,2);self.d1=ConvBlock(base*2,base);self.out=nn.Conv2d(base,num_classes,1)
  def forward(self,x):
   e1=self.e1(x);e2=self.e2(self.pool(e1));e3=self.e3(self.pool(e2));e4=self.e4(self.pool(e3));b=self.b(self.pool(e4));d4=self.d4(torch.cat([self.up4(b),e4],1));d3=self.d3(torch.cat([self.up3(d4),e3],1));d2=self.d2(torch.cat([self.up2(d3),e2],1));d1=self.d1(torch.cat([self.up1(d2),e1],1));return self.out(d1)
 return UNet()
def patch_positions(height,width,patch_size=256,stride=128):
 ys=list(range(0,max(1,height-patch_size+1),stride));xs=list(range(0,max(1,width-patch_size+1),stride))
 if not ys or ys[-1]!=height-patch_size:ys.append(max(0,height-patch_size))
 if not xs or xs[-1]!=width-patch_size:xs.append(max(0,width-patch_size))
 return [(y,x) for y in sorted(set(ys)) for x in sorted(set(xs))]
def blend_probability_patches(patches:list[np.ndarray],positions:list[tuple[int,int]],output_shape:tuple[int,int,int]):
 classes,height,width=output_shape;acc=np.zeros(output_shape,dtype=np.float64);weights=np.zeros((height,width),dtype=np.float64);patch_h,patch_w=patches[0].shape[1:];wy=np.hanning(patch_h);wx=np.hanning(patch_w);window=np.maximum(np.outer(wy,wx),1e-3)
 for probabilities,(y,x) in zip(patches,positions):acc[:,y:y+patch_h,x:x+patch_w]+=probabilities*window;weights[y:y+patch_h,x:x+patch_w]+=window
 probabilities=acc/np.maximum(weights,1e-9);classes_map=np.argmax(probabilities,axis=0).astype(np.uint8);entropy=-np.sum(np.clip(probabilities,1e-12,1)*np.log(np.clip(probabilities,1e-12,1)),axis=0)/np.log(classes);return probabilities.astype(np.float32),classes_map,entropy.astype(np.float32)
def predict_large_image(model,image,patch_size=256,stride=128,batch_size=8,device='cpu'):
 import torch;model=model.to(device).eval();height,width=image.shape[-2:];positions=patch_positions(height,width,patch_size,stride);patches=[]
 with torch.no_grad():
  for start in range(0,len(positions),batch_size):
   batch=np.stack([image[:,y:y+patch_size,x:x+patch_size] for y,x in positions[start:start+batch_size]]);logits=model(torch.from_numpy(batch).float().to(device));patches.extend(torch.softmax(logits,1).cpu().numpy())
 return blend_probability_patches(patches,positions,(len(LULC_CLASSES),height,width))
