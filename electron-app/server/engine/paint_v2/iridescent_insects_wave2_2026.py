"""IRIDESCENT INSECTS 2026 wave 2 — five individually authored beetle surfaces."""
from __future__ import annotations

import numpy as np
from engine.paint_v2.iridescent_insects_2026 import _xy, _apply, _mix, _state


def _tortoise(shape, seed):
    y, x = _xy(shape)
    qx = (x + 5*np.sin(y/57 + seed)) / 23.0
    qy = (y + 4*np.sin(x/49 + seed*.7) + (np.floor(qx)%2)*10) / 21.0
    fx, fy = qx-np.floor(qx)-.5, qy-np.floor(qy)-.5
    shield = np.clip(1 - ((fx/.43)**2 + (fy/.40)**2), 0, 1)
    ring = np.clip(1 - np.abs(shield-.46)*7.0, 0, 1)
    bead = np.clip(np.sin((x*.51-y*.37)*np.pi/12)*.5+.5,0,1)
    key=np.clip((shield*4.2+ring*2.3+bead*2.1).astype(np.int32),0,8)
    return key,shield,ring,bead

def paint_beetle_tortoise(paint, shape, mask, seed, pm, bb):
    key,shield,ring,bead=_tortoise(shape,seed)
    col=_mix([(0.018,.022,.026),(.045,.075,.070),(.090,.155,.130),(.180,.260,.190),(.350,.410,.240),(.620,.590,.270),(.760,.690,.360),(.520,.700,.520),(.760,.880,.720)],key/8)
    col=col*(.66+shield[:,:,None]*.27+ring[:,:,None]*.08)+bead[:,:,None]*np.array([.015,.02,.016],np.float32)
    return _apply(paint,mask,pm,np.clip(col,0,1))

def spec_beetle_tortoise(shape, seed, sm, base_m, base_r):
    key,shield,ring,bead=_tortoise(shape,seed)
    m=_state([20,46,83,122,155,194,226,168,245],key); r=_state([181,132,91,63,45,28,15,52,10],key); c=_state([208,159,111,76,52,25,10,44,2],key)
    return (np.clip(m+shield*23+ring*18,0,255)*sm).astype(np.float32),np.clip(r-shield*17+ring*12+bead*8,15,255).astype(np.float32),np.clip(c-shield*22+ring*18-bead*9,0,255).astype(np.float32)


def _tiger(shape, seed):
    y,x=_xy(shape); flow=5*np.sin(y/37+seed)+3*np.sin(x/61)
    lane=np.mod(x*.62+y*.34+flow,30.0); cusp=np.abs(lane-15.0)
    chevron=np.clip((8.4-cusp)*.24,0,1)
    fork=np.clip(np.sin((x*.10-y*.22+flow)*np.pi/18)*.5+.5,0,1)
    stitch=np.clip(np.sin((x*.72+y*.19)*np.pi/10)*.5+.5,0,1)
    key=np.clip((chevron*4.1+fork*2.0+stitch*2.0).astype(np.int32),0,8)
    return key,chevron,fork,stitch

def paint_beetle_tiger(paint,shape,mask,seed,pm,bb):
    key,chev,fork,stitch=_tiger(shape,seed)
    col=_mix([(.006,.012,.014),(.008,.030,.040),(.012,.082,.115),(.018,.170,.205),(.025,.285,.285),(.060,.390,.250),(.175,.470,.150),(.470,.520,.080),(.760,.650,.090)],key/8)
    col=col*(.71+chev[:,:,None]*.24+stitch[:,:,None]*.05)+fork[:,:,None]*np.array([.008,.018,.020],np.float32)
    return _apply(paint,mask,pm,np.clip(col,0,1))

def spec_beetle_tiger(shape,seed,sm,base_m,base_r):
    key,chev,fork,stitch=_tiger(shape,seed)
    m=_state([34,67,110,154,190,225,250,211,236],key);r=_state([145,106,72,49,33,18,7,28,14],key);c=_state([192,138,91,58,35,14,1,23,8],key)
    return (np.clip(m+chev*21+fork*9,0,255)*sm).astype(np.float32),np.clip(r-chev*15+(1-fork)*14+stitch*6,15,255).astype(np.float32),np.clip(c-chev*19+(1-fork)*23,0,255).astype(np.float32)


def _chafer(shape,seed):
    y,x=_xy(shape); qx=x/16.; qy=(y+(np.floor(qx)%2)*8)/16.
    fx,fy=qx-np.floor(qx)-.5,qy-np.floor(qy)-.5; d=np.sqrt((fx*1.08)**2+(fy*.92)**2)
    scallop=np.clip((.48-d)*5.8,0,1); rim=np.clip(1-np.abs(d-.36)*12,0,1)
    hair=np.clip(np.sin((x*.36+y*.66+seed)*np.pi/8)*.5+.5,0,1)
    key=np.clip((scallop*3.6+rim*2.1+hair*2.2).astype(np.int32),0,8)
    return key,scallop,rim,hair

def paint_beetle_rose_chafer(paint,shape,mask,seed,pm,bb):
    key,scallop,rim,hair=_chafer(shape,seed)
    col=_mix([(.006,.020,.009),(.014,.065,.022),(.030,.140,.042),(.070,.250,.067),(.150,.370,.080),(.310,.520,.100),(.570,.660,.105),(.760,.740,.190),(.870,.910,.440)],key/8)
    col=col*(.70+scallop[:,:,None]*.24+rim[:,:,None]*.09)+hair[:,:,None]*np.array([.01,.018,.004],np.float32)
    return _apply(paint,mask,pm,np.clip(col,0,1))

def spec_beetle_rose_chafer(shape,seed,sm,base_m,base_r):
    key,scallop,rim,hair=_chafer(shape,seed)
    m=_state([12,33,69,109,145,178,208,231,188],key);r=_state([210,157,111,75,54,37,24,13,42],key);c=_state([221,172,121,80,52,33,17,5,34],key)
    return (np.clip(m+scallop*20+rim*17,0,255)*sm).astype(np.float32),np.clip(r-scallop*18+rim*10+(1-hair)*12,15,255).astype(np.float32),np.clip(c-scallop*24+rim*14+(1-hair)*18,0,255).astype(np.float32)


def _buprestid(shape,seed):
    y,x=_xy(shape); qx=(x+7*np.sin(y/81))/29.; qy=(y+5*np.sin(x/63))/25.
    fx,fy=qx-np.floor(qx)-.5,qy-np.floor(qy)-.5; rad=np.sqrt(fx*fx+fy*fy)
    anneal=np.clip(np.sin(rad*np.pi*10 + np.sin((fx-fy)*8))*0.5+.5,0,1)
    seam=np.clip((.11-np.abs(fx+fy*.62))*8.5,0,1); mica=np.clip(np.sin((x*.57-y*.43)*np.pi/9)*.5+.5,0,1)
    key=np.clip((anneal*3.3+seam*2.8+mica*2.2).astype(np.int32),0,8)
    return key,anneal,seam,mica

def paint_beetle_buprestid(paint,shape,mask,seed,pm,bb):
    key,anneal,seam,mica=_buprestid(shape,seed)
    col=_mix([(.028,.011,.008),(.080,.024,.012),(.180,.048,.017),(.340,.090,.025),(.580,.160,.035),(.760,.300,.060),(.700,.430,.110),(.480,.210,.170),(.260,.070,.180)],key/8)
    col=col*(.67+anneal[:,:,None]*.21+seam[:,:,None]*.12)+mica[:,:,None]*np.array([.024,.012,.008],np.float32)
    return _apply(paint,mask,pm,np.clip(col,0,1))

def spec_beetle_buprestid(shape,seed,sm,base_m,base_r):
    key,anneal,seam,mica=_buprestid(shape,seed)
    m=_state([45,76,112,151,190,226,250,203,164],key);r=_state([132,100,74,53,35,19,7,28,66],key);c=_state([172,132,93,60,34,14,1,24,81],key)
    return (np.clip(m+anneal*17+seam*23,0,255)*sm).astype(np.float32),np.clip(r-anneal*12-seam*11+mica*10,15,255).astype(np.float32),np.clip(c-anneal*18-seam*17+(1-mica)*13,0,255).astype(np.float32)


def _ground(shape,seed):
    y,x=_xy(shape); a=np.sin(x*.22+y*.15+seed); b=np.sin(x*.11-y*.29+seed*.6); c=np.sin(x*.39+y*.31)
    plate=np.clip((a+b*.7+c*.34+1.4)/3.2,0,1); edge=np.clip(1-np.abs(plate-.50)*9,0,1)
    scratch=np.clip(np.sin((x*.83-y*.12)*np.pi/13)*.5+.5,0,1); pore=np.clip(np.sin((x*.46+y*.69)*np.pi/7)*.5+.5,0,1)
    key=np.clip((plate*4.3+edge*1.9+scratch*1.3+pore*1.2).astype(np.int32),0,8)
    return key,plate,edge,scratch,pore

def paint_beetle_ground(paint,shape,mask,seed,pm,bb):
    key,plate,edge,scratch,pore=_ground(shape,seed)
    col=_mix([(.003,.006,.010),(.006,.013,.023),(.009,.027,.047),(.012,.055,.084),(.016,.092,.130),(.026,.140,.170),(.055,.180,.185),(.110,.220,.210),(.230,.300,.280)],key/8)
    col=col*(.65+plate[:,:,None]*.24+edge[:,:,None]*.08)+scratch[:,:,None]*np.array([.004,.009,.016],np.float32); col*=1-pore[:,:,None]*.18
    return _apply(paint,mask,pm,np.clip(col,0,1))

def spec_beetle_ground(shape,seed,sm,base_m,base_r):
    key,plate,edge,scratch,pore=_ground(shape,seed)
    m=_state([84,113,148,181,211,239,255,224,192],key);r=_state([96,72,55,38,25,15,7,20,47],key);c=_state([129,88,60,38,21,9,0,15,55],key)
    return (np.clip(m+edge*22-scratch*12,0,255)*sm).astype(np.float32),np.clip(r-edge*14+pore*42+(1-scratch)*6,15,255).astype(np.float32),np.clip(c-edge*18+pore*58+(1-scratch)*9,0,255).astype(np.float32)
